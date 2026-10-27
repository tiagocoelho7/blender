"""Blender Dedup v1.0.2-test1 -- CANDIDATA OFFLINE; NAO HOMOLOGADA.

Detecta malhas-base MESH isomorfas apos quantizacao float32 (5 casas),
sem depender de indices, G/R/S, materiais, UV ou modifiers. Ranking:
modifiers > shape-key blocks > nome. Analisa bpy.data.objects inteiro.

Plano integral + inventario conservador de referencias ANTES da exclusao;
qualquer inconclusivo aborta o arquivo inteiro com ZERO remove. Se a fase
3 falhar, interrompe, reconcilia e nao promete rollback. SEM AUTOSAVE.

PERIGO: ao EXECUTAR no Blender, REMOVE os DROPs elegiveis sem confirmacao.
Somente testes offline foram realizados; NAO USAR EM PRODUCAO.
"""
from collections import Counter, defaultdict
import ast
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
import hashlib
import json
import os
import re
import sys
import time
import copy
import threading

try:
    import numpy as np
except ImportError as exc:
    raise RuntimeError("Blender Dedup requer NumPy.") from exc
# Offline import never loads Blender. A future authorized runtime must already
# provide bpy; tests require bpy is None. No runtime validation is claimed.
bpy = sys.modules.get("bpy")

PRECISION = 5
FACTOR = 10 ** PRECISION
INT64_LIMIT = 2**63 - 1
VERSION = "1.0.2-test1-candidate-offline"

class PreflightAborted(RuntimeError):
    """Nenhuma exclusao pode comecar apos esta falha de preflight."""

class MutationDetected(PreflightAborted):
    pass

class ComplexityBudgetExceeded(PreflightAborted):
    pass

class UnsafeReference(PreflightAborted):
    pass

class IncompleteDiscovery(PreflightAborted):
    pass

@dataclass
class Limits:
    total_seconds: float = 300.0
    pair_seconds: float = 45.0
    comparisons: int = 50_000
    states_total: int = 2_000_000
    states_per_pair: int = 250_000
    mem_global_bytes: int = 2 * 1024 ** 3
    mem_pair_bytes: int = 512 * 1024 ** 2
    bucket_objects: int = 2048
    rna_nodes: int = 2_000_000
    text_bytes: int = 8 * 1024 * 1024


def _rss_bytes():
    """RSS atual estimado (ou None); nao constitui hard cap do SO."""
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss
    except (ImportError, OSError, AttributeError):
        pass
    if sys.platform.startswith("linux"):
        try:
            with open("/proc/self/statm", "r", encoding="ascii") as fp:
                return int(fp.read().split()[1]) * os.sysconf("SC_PAGE_SIZE")
        except (OSError, ValueError, IndexError):
            return None
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            class Pmc(ctypes.Structure):
                _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                            ("PeakWorkingSetSize", ctypes.c_size_t),
                            ("WorkingSetSize", ctypes.c_size_t),
                            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                            ("PagefileUsage", ctypes.c_size_t),
                            ("PeakPagefileUsage", ctypes.c_size_t)]
            counters = Pmc()
            counters.cb = ctypes.sizeof(Pmc)
            handle = ctypes.windll.kernel32.GetCurrentProcess()
            ok = ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb)
            return int(counters.WorkingSetSize) if ok else None
        except (AttributeError, OSError, ValueError):
            return None
    return None

class BudgetContext:
    """Limites cooperativos; sao estimativas, nao quotas rigidas de RAM."""
    def __init__(self, limits=None):
        self.limits = limits or Limits()
        self.started = time.perf_counter()
        self.initial_rss = _rss_bytes()
        if self.initial_rss is None:
            raise IncompleteDiscovery("Amostragem de RSS indisponivel; budget fisico nao verificavel")
        self.rss_peak = self.initial_rss or 0
        self.total_states = 0
        self.pair_states = 0
        self.comparisons = 0
        self.rna_nodes = 0
        self.pair_started = None
        self.pair_initial_rss = None
        self.pair_allocation_requests = 0
        self.global_allocation_peak_request = 0

    def checkpoint(self, label="checkpoint"):
        now = time.perf_counter()
        if now - self.started > self.limits.total_seconds:
            raise ComplexityBudgetExceeded("Tempo total excedido: " + label)
        if self.pair_started is not None and now-self.pair_started > self.limits.pair_seconds:
            raise ComplexityBudgetExceeded("Tempo por par excedido: " + label)
        rss = _rss_bytes()
        if rss is not None:
            self.rss_peak = max(self.rss_peak, rss)
            if self.pair_started is not None and self.pair_initial_rss is not None and rss-self.pair_initial_rss > self.limits.mem_pair_bytes:
                raise ComplexityBudgetExceeded("Crescimento de RSS do par excedido: " + label)
            if self.initial_rss is not None and rss-self.initial_rss > self.limits.mem_global_bytes:
                raise ComplexityBudgetExceeded("Crescimento de RSS global excedido: " + label)
        return now

    def allocation_bound(self, nbytes, label, stage="alloc"):
        nbytes = max(0, int(nbytes))
        self.checkpoint(stage+":"+label)
        if nbytes > self.limits.mem_pair_bytes:
            raise ComplexityBudgetExceeded("Alocacao individual supera memoria por par: " + label)
        if self.pair_started is not None:
            self.pair_allocation_requests += nbytes
            if self.pair_allocation_requests > self.limits.mem_pair_bytes:
                raise ComplexityBudgetExceeded("Estimativas de alocacao do par superam budget: " + label)
        self.global_allocation_peak_request = max(self.global_allocation_peak_request, nbytes)
        if nbytes > self.limits.mem_global_bytes:
            raise ComplexityBudgetExceeded("Estimativa de memoria global excedida: " + label)

    def state(self, label="state"):
        self.total_states += 1
        self.pair_states += 1 if self.pair_started is not None else 0
        if self.total_states > self.limits.states_total or self.pair_states > self.limits.states_per_pair:
            raise ComplexityBudgetExceeded("Limite de estados excedido: " + label)
        if self.total_states % 256 == 0:
            self.checkpoint(label)

    def node(self):
        self.rna_nodes += 1
        if self.rna_nodes > self.limits.rna_nodes:
            raise ComplexityBudgetExceeded("Inventario RNA excedeu numero de elementos")
        if self.rna_nodes % 1024 == 0:
            self.checkpoint("RNA")

    @contextmanager
    def pair(self):
        self.comparisons += 1
        if self.comparisons > self.limits.comparisons:
            raise ComplexityBudgetExceeded("Quantidade maxima de pares excedida")
        old_start, old_states, old_alloc = self.pair_started, self.pair_states, self.pair_allocation_requests
        old_rss = self.pair_initial_rss
        self.pair_initial_rss = _rss_bytes()
        self.pair_started, self.pair_states, self.pair_allocation_requests = time.perf_counter(), 0, 0
        try:
            self.checkpoint("inicio-par")
            yield
            self.checkpoint("fim-par")
        finally:
            self.pair_started, self.pair_states, self.pair_allocation_requests = old_start, old_states, old_alloc
            self.pair_initial_rss = old_rss

CURRENT_BUDGET = ContextVar("dedup_budget", default=None)
class _NullBudget:
    def checkpoint(self, *a, **k): return None
    def allocation_bound(self, *a, **k): return None
    def state(self, *a, **k): return None
    def node(self): return None
_NULL_BUDGET = _NullBudget()

def _budget():
    return CURRENT_BUDGET.get() or _NULL_BUDGET

@contextmanager
def bound_budget(budget):
    token = CURRENT_BUDGET.set(budget)
    try:
        yield
    finally:
        CURRENT_BUDGET.reset(token)

def _checked(iterable, label):
    """Check inside Python loops; native NumPy/sort calls remain cooperative."""
    for index, value in enumerate(iterable):
        if index % 128 == 0:
            _budget().checkpoint(label)
        yield value


def mesh_identity(mesh):
    """Identificador estavel do datablock, independentemente do proxy bpy."""
    ptr = getattr(mesh, 'as_pointer', None)
    return int(ptr()) if ptr is not None else id(mesh)


def mesh_counts(mesh):
    return (len(mesh.vertices), len(mesh.edges), len(mesh.polygons), len(mesh.loops))


def quantized_vertices(mesh):
    """Extrai os vertices originais, nao a malha avaliada por modifiers.

    Usa a precisao real de armazenamento float32 das coordenadas do Blender.
    A multiplicacao e feita em float64 para evitar arredondamento adicional.
    """
    n = len(mesh.vertices)
    _budget().allocation_bound(n * 80, "quantizacao", stage="alloc")
    coords = np.empty(n * 3, dtype=np.float32)
    if n:
        mesh.vertices.foreach_get('co', coords)
    coords = coords.reshape((n, 3)).astype(np.float64)
    if not np.isfinite(coords).all():
        raise ValueError('A malha contem coordenadas nao finitas (NaN/Inf).')
    if coords.size and np.max(np.abs(coords)) * FACTOR >= INT64_LIMIT:
        raise ValueError('Coordenadas fora do intervalo aceito pela quantizacao.')
    out = np.rint(coords * FACTOR).astype(np.int64)
    _budget().checkpoint("quantizacao-pronta")
    return out


def get_edges(mesh):
    e = len(mesh.edges)
    _budget().allocation_bound(e * 64, "arestas", stage="alloc")
    out = np.empty(e * 2, dtype=np.int32)
    if e:
        mesh.edges.foreach_get('vertices', out)
    return out.reshape((e, 2))


def get_polygons(mesh):
    p, l = len(mesh.polygons), len(mesh.loops)
    _budget().allocation_bound(p * 80 + l * 40, "faces-e-loops", stage="alloc")
    starts = np.empty(p, dtype=np.int32)
    totals = np.empty(p, dtype=np.int32)
    loops = np.empty(l, dtype=np.int32)
    if p:
        mesh.polygons.foreach_get('loop_start', starts)
        mesh.polygons.foreach_get('loop_total', totals)
    if l:
        mesh.loops.foreach_get('vertex_index', loops)
    return starts, totals, loops


def coordinate_order(q):
    return np.lexsort((q[:, 2], q[:, 1], q[:, 0])) if len(q) else np.empty(0, dtype=np.int64)


def coarse_signature(mesh):
    """Filtro sem falsos negativos devido a permutacao de vertices.

    SHA-256 e usado APENAS como indice de candidatos; a exclusao necessita
    da confirmacao estrutural exata (apos arredondar 5 casas).
    """
    q = quantized_vertices(mesh)
    order = coordinate_order(q)
    digest = hashlib.sha256()
    digest.update(np.ascontiguousarray(q[order], dtype='<i8').tobytes())
    return (mesh_counts(mesh), digest.hexdigest())


def _canonical_cycle(seq):
    """Menor rotacao ciclica; NAO inverte winding/normais.

    Booth em O(n); funciona inclusive para valores repetidos e n-gons.
    """
    seq = tuple(int(x) for x in seq)
    n = len(seq)
    if n < 2:
        return seq
    double = seq + seq
    i, j, k = 0, 1, 0
    steps = 0
    while i < n and j < n and k < n:
        steps += 1
        if steps % 128 == 0: _budget().checkpoint("ciclo-orientado")
        a, b = double[i + k], double[j + k]
        if a == b:
            k += 1
            continue
        if a > b:
            i += k + 1
            if i <= j:
                i = j + 1
        else:
            j += k + 1
            if j <= i:
                j = i + 1
        k = 0
    start = min(i, j)
    return double[start:start+n]


def _canon_rows(rows):
    """Normaliza inicio de loops de faces curtas usando vetorizacao."""
    if len(rows) == 0:
        return rows
    length = rows.shape[1]
    best = rows.copy()
    for shift in range(1, length):
        _budget().checkpoint("normalizacao-faces")
        candidate = np.roll(rows, -shift, axis=1)
        eq = np.ones(len(rows), dtype=np.bool_)
        smaller = np.zeros(len(rows), dtype=np.bool_)
        for col in range(length):
            smaller |= eq & (candidate[:, col] < best[:, col])
            eq &= candidate[:, col] == best[:, col]
        if smaller.any():
            best[smaller] = candidate[smaller]
    return best


def _sorted_rows(rows):
    if not len(rows):
        return rows
    # lexsort considera a ultima chave como primaria.
    order = np.lexsort(tuple(rows[:, col] for col in reversed(range(rows.shape[1]))))
    return rows[order]


def topology_equal(mesh_a, mesh_b, ids_a, ids_b):
    """Verificacao EXATA das arestas e faces sob dois rotulos de vertices.

    ids_a e ids_b devem mapear os indices locais de cada mesh para um mesmo
    conjunto de rotulos. Preserva multiplicidades e winding das faces.
    """
    if mesh_counts(mesh_a) != mesh_counts(mesh_b):
        return False
    if len(ids_a) != len(mesh_a.vertices) or len(ids_b) != len(mesh_b.vertices):
        return False
    ea = get_edges(mesh_a)
    eb = get_edges(mesh_b)
    if len(ea):
        ra = np.sort(ids_a[ea], axis=1)
        rb = np.sort(ids_b[eb], axis=1)
        if not np.array_equal(_sorted_rows(ra), _sorted_rows(rb)):
            return False
    del ea, eb

    starts_a, totals_a, loops_a = get_polygons(mesh_a)
    starts_b, totals_b, loops_b = get_polygons(mesh_b)
    if not np.array_equal(np.sort(totals_a), np.sort(totals_b)):
        return False
    for length in np.unique(totals_a):
        _budget().checkpoint("comparacao-topologica")
        length = int(length)
        fa = starts_a[totals_a == length]
        fb = starts_b[totals_b == length]
        if length <= 12:
            offsets = np.arange(length, dtype=np.int64)
            ra = ids_a[loops_a[fa[:, None] + offsets[None, :]]]
            rb = ids_b[loops_b[fb[:, None] + offsets[None, :]]]
            ra = _sorted_rows(_canon_rows(ra))
            rb = _sorted_rows(_canon_rows(rb))
            if not np.array_equal(ra, rb):
                return False
        else:
            # Evita memoria O(numero_faces * tamanho_ngon) em faces gigantes.
            ta = sorted(_canonical_cycle(ids_a[loops_a[s:s+length]]) for s in fa)
            tb = sorted(_canonical_cycle(ids_b[loops_b[s:s+length]]) for s in fb)
            if ta != tb:
                return False
    return True


def _localized_signatures(qclasses, edges, polygons, ambiguous):
    """Caracteristicas locais invariantes para restringir busca exata."""
    amb = set(ambiguous)
    neigh = defaultdict(list)
    corners = defaultdict(list)
    for index, (u, v) in enumerate(edges):
        if index % 2048 == 0: _budget().checkpoint("assinatura-local")
        u, v = int(u), int(v)
        if u in amb:
            neigh[u].append(int(qclasses[v]))
        if v in amb:
            neigh[v].append(int(qclasses[u]))
    starts, totals, loops = polygons
    for index, (start, size) in enumerate(zip(starts, totals)):
        if index % 2048 == 0: _budget().checkpoint("faces-locais")
        start, size = int(start), int(size)
        indices = loops[start:start+size]
        for j, raw in _checked(enumerate(indices), "cantos-locais"):
            v = int(raw)
            if v in amb:
                prev = int(qclasses[int(indices[(j-1) % size])])
                nxt = int(qclasses[int(indices[(j+1) % size])])
                corners[v].append((size, prev, nxt))
    return {v: (int(qclasses[v]), tuple(sorted(neigh[v])), tuple(sorted(corners[v])))
            for v in _checked(amb, "assinaturas-vertices")}


def _ambiguous_isomorphism(mesh_a, mesh_b, q_a, q_b, order_a, order_b):
    """Busca exata em vertices coincidentes (iterativa, sem limite de profundidade).

    Verifica isomorfismo que preserve coordenada quantizada, arestas,
    multiplicidades e sequencias orientadas de faces. Pode ser caro em
    malhas patologicamente simetricas; NUNCA aceita so por hash.
    """
    n = len(q_a)
    _budget().allocation_bound(n * 2048 + n * n * 16 + (len(mesh_a.loops) + len(mesh_b.loops))*512 + (len(mesh_a.edges) + len(mesh_b.edges))*512, "grafo-ambiguo", stage="alloc")
    same = np.all(q_a[order_a][1:] == q_a[order_a][:-1], axis=1)
    # 'same' tem True nas fronteiras internas de grupos repetidos.
    separators = np.flatnonzero(~same) + 1
    starts = np.r_[0, separators]
    stops = np.r_[separators, n]
    mapping = np.full(n, -1, dtype=np.int64)
    reverse = np.full(n, -1, dtype=np.int64)
    qclasses_a = np.empty(n, dtype=np.int64)
    qclasses_b = np.empty(n, dtype=np.int64)
    ambiguous_a, ambiguous_b = [], []
    for cls, (start, stop) in _checked(enumerate(zip(starts, stops)), "classes-coordenadas"):
        ia = order_a[start:stop]
        ib = order_b[start:stop]
        qclasses_a[ia] = cls
        qclasses_b[ib] = cls
        if stop - start == 1:
            mapping[ia[0]] = ib[0]
            reverse[ib[0]] = ia[0]
        else:
            ambiguous_a.extend(int(x) for x in ia)
            ambiguous_b.extend(int(x) for x in ib)

    edges_a = get_edges(mesh_a)
    edges_b = get_edges(mesh_b)
    poly_a = get_polygons(mesh_a)
    poly_b = get_polygons(mesh_b)
    sig_a = _localized_signatures(qclasses_a, edges_a, poly_a, ambiguous_a)
    sig_b = _localized_signatures(qclasses_b, edges_b, poly_b, ambiguous_b)
    groups_a, groups_b = defaultdict(list), defaultdict(list)
    for i, key in _checked(sig_a.items(), "grupos-A"):
        groups_a[key].append(i)
    for i, key in _checked(sig_b.items(), "grupos-B"):
        groups_b[key].append(i)
    if {key: len(v) for key, v in groups_a.items()} != {key: len(v) for key, v in groups_b.items()}:
        return False
    # Refine coordinate/local partitions jointly, never use them as positive proof.
    # Orientation and multiplicity remain checked by the final exact witness.
    for refinement in range(4):
        keys = sorted(set(sig_a.values()) | set(sig_b.values()))
        colors = {key: index for index, key in enumerate(keys)}
        ca, cb = qclasses_a.copy(), qclasses_b.copy()
        for v in _checked(ambiguous_a, "refino-A"): ca[v] = len(starts) + colors[sig_a[v]]
        for v in _checked(ambiguous_b, "refino-B"): cb[v] = len(starts) + colors[sig_b[v]]
        na = _localized_signatures(ca, edges_a, poly_a, ambiguous_a)
        nb = _localized_signatures(cb, edges_b, poly_b, ambiguous_b)
        if Counter(na.values()) != Counter(nb.values()): return False
        sig_a, sig_b = na, nb
    groups_a, groups_b = defaultdict(list), defaultdict(list)
    for i, key in _checked(sig_a.items(), "grupos-A"): groups_a[key].append(i)
    for i, key in _checked(sig_b.items(), "grupos-B"): groups_b[key].append(i)
    remaining = set()
    candidates = {}
    for key, verts_a in _checked(groups_a.items(), "particoes"):
        verts_b = groups_b[key]
        if len(verts_a) == 1:
            a, b = verts_a[0], verts_b[0]
            mapping[a] = b
            reverse[b] = a
        else:
            remaining.update(verts_a)
            shared = tuple(sorted(verts_b))
            for a in _checked(verts_a, "candidatos-compartilhados"):
                candidates[a] = shared

    # Preparar adjacencias somente dos vertices ambiguos (economiza memoria).
    adj_a = {a: Counter() for a in ambiguous_a}
    adj_b = {b: Counter() for b in ambiguous_b}
    for u, v in _checked(edges_a, "adjacencias-A"):
        u, v = int(u), int(v)
        if u in adj_a:
            adj_a[u][v] += 1
        if v in adj_a:
            adj_a[v][u] += 1
    for u, v in _checked(edges_b, "adjacencias-B"):
        u, v = int(u), int(v)
        if u in adj_b:
            adj_b[u][v] += 1
        if v in adj_b:
            adj_b[v][u] += 1

    # Faces que contem vertices com coordenadas repetidas.
    # Todas as outras serao verificadas na comparacao final completa.
    def indexed_faces(polys, amb):
        starts_, totals_, loops_ = polys
        amb_set = set(amb)
        result = []
        touching = defaultdict(list)
        for start, size in _checked(zip(starts_, totals_), "indexacao-faces"):
            raw = tuple(int(i) for i in _checked(loops_[int(start):int(start)+int(size)], "indices-face"))
            touched = amb_set.intersection(raw)
            if touched:
                idx = len(result)
                result.append(raw)
                for v in touched:
                    touching[v].append(idx)
        return result, touching

    faces_a, face_by_a = indexed_faces(poly_a, ambiguous_a)
    faces_b, _ = indexed_faces(poly_b, ambiguous_b)
    if len(faces_a) != len(faces_b):
        return False
    available_b = Counter(_canonical_cycle(f) for f in _checked(faces_b, "faces-disponiveis"))

    def consume_complete_faces(affected_ids):
        changed = []
        for face_id in _checked(affected_ids, "poda-faces"):
            _budget().state("faces-consumidas")
            face = faces_a[face_id]
            if any(mapping[v] < 0 for v in _checked(face, "face-completa")):
                continue
            key = _canonical_cycle(mapping[list(face)])
            if available_b[key] <= 0:
                for ck in changed:
                    available_b[ck] += 1
                return None
            available_b[key] -= 1
            changed.append(key)
        return changed

    # Faces totalmente determinadas antes da busca.
    already = consume_complete_faces(range(len(faces_a)))
    if already is None:
        return False

    if not remaining:
        return topology_equal(mesh_a, mesh_b, mapping, np.arange(n, dtype=np.int64))

    def compatible(a, b):
        if reverse[b] >= 0:
            return False
        for v, count in _checked(adj_a[a].items(), "compatibilidade-A"):
            mapped = int(mapping[v])
            if mapped >= 0 and adj_b[b].get(mapped, 0) != count:
                return False
        for w, count in _checked(adj_b[b].items(), "compatibilidade-B"):
            inverse = int(reverse[w])
            if inverse >= 0 and adj_a[a].get(inverse, 0) != count:
                return False
        return True

    def frame():
        # Explora primeiro fronteiras conectadas aos vertices ja mapeados.
        # Ordem de escolha nao influencia completude, so o desempenho.
        free_by_class = {}
        for a in _checked(remaining, "classes-livres"):
            shared = candidates[a]
            if id(shared) not in free_by_class:
                free_by_class[id(shared)] = sum(int(reverse[b] < 0) for b in _checked(shared, "contagem-livres"))
        def rank(a):
            mapped_neighbors = sum(int(mapping[v] >= 0) for v in _checked(adj_a[a], "ranking-adjacencias"))
            free = free_by_class[id(candidates[a])]
            return (0 if mapped_neighbors else 1, free, -mapped_neighbors, -len(adj_a[a]), a)
        _budget().state("frame-backtracking")
        a = min(_checked(remaining, "ranking-vertices"), key=rank)
        bs = [b for b in _checked(candidates[a], "ranking-candidatos") if compatible(a, b)]
        return {'a': a, 'bs': bs, 'pos': 0, 'b': None, 'faces': None}

    stack = [frame()]
    while stack:
        _budget().state("busca-exata")
        current = stack[-1]
        a = current['a']
        # Retornar de uma tentativa de ramo (ou preparar o proximo candidato).
        if current['b'] is not None:
            for key in current['faces']:
                available_b[key] += 1
            b = current['b']
            mapping[a] = -1
            reverse[b] = -1
            remaining.add(a)
            current['b'] = None
            current['faces'] = None
        if current['pos'] >= len(current['bs']):
            stack.pop()
            continue
        b = current['bs'][current['pos']]
        current['pos'] += 1
        if not compatible(a, b):
            continue
        mapping[a] = b
        reverse[b] = a
        remaining.remove(a)
        consumed = consume_complete_faces(face_by_a.get(a, ()))
        if consumed is None:
            mapping[a] = -1
            reverse[b] = -1
            remaining.add(a)
            continue
        current['b'] = b
        current['faces'] = consumed
        if not remaining:
            if topology_equal(mesh_a, mesh_b, mapping, np.arange(n, dtype=np.int64)):
                return True
        else:
            stack.append(frame())
    return False


def meshes_equal(mesh_a, mesh_b):
    """Equivalencia completa (5 casas), sem depender de indices ou ordem."""
    if mesh_counts(mesh_a) != mesh_counts(mesh_b):
        return False
    # Mesmo Mesh datablock nao pode contornar a validacao numerica.
    qa = quantized_vertices(mesh_a)
    if mesh_identity(mesh_a) == mesh_identity(mesh_b):
        return True
    qb = quantized_vertices(mesh_b)
    if np.array_equal(qa, qb):
        ids = np.arange(len(qa), dtype=np.int64)
        if topology_equal(mesh_a, mesh_b, ids, ids):
            return True
    oa, ob = coordinate_order(qa), coordinate_order(qb)
    sorted_a, sorted_b = qa[oa], qb[ob]
    if not np.array_equal(sorted_a, sorted_b):
        return False
    if len(qa) < 2 or np.all(np.any(sorted_a[1:] != sorted_a[:-1], axis=1)):
        ids_a = np.empty(len(qa), dtype=np.int64)
        ids_b = np.empty(len(qb), dtype=np.int64)
        ids_a[oa] = np.arange(len(qa))
        ids_b[ob] = np.arange(len(qb))
        return topology_equal(mesh_a, mesh_b, ids_a, ids_b)
    return _ambiguous_isomorphism(mesh_a, mesh_b, qa, qb, oa, ob)



# --- End geometry primitives from frozen v1.0; modified for budgets and numeric alias ---

# --- Deterministic object planner ---

def number_of_shape_keys(obj):
    keys = getattr(obj.data, "shape_keys", None)
    return len(keys.key_blocks) if keys is not None else 0


def preference(obj):
    return (-len(obj.modifiers), -number_of_shape_keys(obj), obj.name.casefold(), obj.name,
            int(getattr(obj, "session_uid", 0) or 0), stable_id(obj))


def stable_id(item):
    getter = getattr(item, "as_pointer", None)
    return int(getter()) if getter is not None else id(item)


def snapshot(item):
    """Never dereference removed bpy proxies: capture before deleting."""
    uid = getattr(item, "session_uid", None)
    return {"name": str(getattr(item, "name", "<unnamed>")),
            "kind": str(getattr(item, "id_type", type(item).__name__)),
            "pointer": stable_id(item),
            "session_uid": int(uid) if isinstance(uid, int) and uid > 0 else None}


def _check_structural_indices(mesh):
    """Validation of topology of mesh-base; no dependence on vertex ordering."""
    n = len(mesh.vertices)
    edges = get_edges(mesh)
    starts, totals, loops = get_polygons(mesh)
    if edges.size and (np.any(edges < 0) or np.any(edges >= n)):
        raise PreflightAborted("Malha tem arestas com indices invalidos")
    if loops.size and (np.any(loops < 0) or np.any(loops >= n)):
        raise PreflightAborted("Malha tem loops com indices invalidos")
    if np.any(starts < 0) or np.any(totals < 3):
        raise PreflightAborted("Malha tem faces com comprimentos/offsets invalidos")
    if len(starts) and np.any(starts.astype(np.int64) + totals.astype(np.int64) > len(loops)):
        raise PreflightAborted("Malha tem faces acessando loops inexistentes")
    if len(starts):
        order = np.argsort(starts)
        ordered_starts, ordered_totals = starts[order], totals[order]
        if ordered_starts[0] != 0 or np.any(ordered_starts[1:] != ordered_starts[:-1] + ordered_totals[:-1]):
            raise PreflightAborted("Offsets de faces sobrepostos ou com lacunas")
    if int(np.sum(totals, dtype=np.int64)) != len(loops):
        raise PreflightAborted("Malha tem loops soltos/compartilhados inconsistentes")


def plan_removals(objects, budget):
    """Calculates ALL clusters without mutation. No uncertainty interpreted as not duplicate."""
    with bound_budget(budget):
        malformed = [obj.name for obj in objects if obj.type == "MESH" and obj.data is None]
        if malformed:
            raise PreflightAborted("Objeto MESH sem datablock de geometria: " + repr(malformed[:3]))
        meshes = [obj for obj in objects if obj.type == "MESH" and obj.data is not None]
        by_counts = defaultdict(list)
        # Validate every distinct mesh, including singleton and alias; no NaN shortcut.
        signatures = {}
        for i, obj in enumerate(meshes):
            if i % 8 == 0:
                budget.checkpoint("validacao-global")
            if getattr(obj, "mode", None) != "OBJECT" or getattr(obj, "is_evaluated", True):
                raise UnsafeReference("MESH em modo/estado nao confiavel: " + obj.name)
            if getattr(obj.data, "is_editmode", False):
                raise UnsafeReference("Mesh em edicao: " + obj.name)
            mesh = obj.data
            ptr = mesh_identity(mesh)
            if ptr not in signatures:
                _check_structural_indices(mesh)
                signatures[ptr] = coarse_signature(mesh)
            by_counts[mesh_counts(mesh)].append(obj)
        equal_cache = {}
        clusters = []
        for group in by_counts.values():
            budget.checkpoint("grupos-por-contagem")
            if len(group) <= 1:
                continue
            buckets = defaultdict(list)
            for obj in group:
                buckets[signatures[mesh_identity(obj.data)]].append(obj)
            for members in buckets.values():
                if len(members) <= 1:
                    continue
                if len(members) > budget.limits.bucket_objects:
                    raise ComplexityBudgetExceeded("Bucket excedeu tamanho seguro: %d" % len(members))
                groups = []
                for obj in sorted(members, key=preference):
                    budget.checkpoint("classificacao-em-clusters")
                    for cl in groups:
                        keep = cl[0]
                        ka, kb = sorted((mesh_identity(obj.data), mesh_identity(keep.data)))
                        pair_id = (ka, kb)
                        if pair_id not in equal_cache:
                            with budget.pair():
                                if ka == kb:
                                    # Signature + topology validated for this datablock above.
                                    result = True
                                else:
                                    result = meshes_equal(obj.data, keep.data)
                            equal_cache[pair_id] = bool(result)
                        if equal_cache[pair_id]:
                            cl.append(obj)
                            break
                    else:
                        groups.append([obj])
                clusters.extend((group[0], tuple(group[1:])) for group in groups if len(group) > 1)
        # Deterministic plan. KEEP cannot be changed to make DROP easier to remove.
        clusters.sort(key=lambda pair: (preference(pair[0]), pair[0].name))
        return clusters, len(meshes)


# --- Dependency inventory across bpy.data and nested RNA/IDProperty ---

@dataclass
class Reference:
    owner: object
    target: object
    path: str
    surface: str
    category: str = "PENDENTE"
    why: str = ""

    def record(self, drop_keys, keep_keys=(), affected_drop=None):
        owner, target = snapshot(self.owner), snapshot(self.target)
        lifecycle = "DROP" if owner["pointer"] in drop_keys else ("KEEP" if owner["pointer"] in keep_keys else "SURVIVE")
        blocked = self.category in ("FUNCIONAL_DIRETA", "FUNCIONAL_INDIRETA", "DESCONHECIDA", "PENDENTE")
        return {"owner": owner, "owner_key": owner, "target": target, "target_key": target,
                "drop_key": target if target["pointer"] in drop_keys else affected_drop,
                "owner_lifecycle": lifecycle, "path": self.path, "rna_path": self.path,
                "surface": self.surface, "source_surface": self.surface,
                "relation_category": self.category, "scan_status": "INSPECTED",
                "action": "ABORT_GLOBAL" if blocked else "ALLOW_UNLINK" if self.category == "PERTENCIMENTO_AUTORIZADO" else "NO_REMAP",
                "evidence": {"method": "RNA/IDProperty enumeration", "path": self.path},
                "why": self.why, "reason": self.why,
                "drop_target": target["pointer"] in drop_keys}


_SKIP_INVERSE_PATHS = {
    # Blender computed backlinks; actual forward link is read from owners.
    ("Object", "children"), ("Object", "users_collection"),
    ("Object", "users_scene"), ("Collection", "all_objects"),
}
# These primitive geometrical RNA arrays contain numeric mesh elements, not
# pointers to Object/Collection. Custom IDProperties of the Mesh ID are scanned.
_MESH_PRIMITIVE_COLLECTIONS = {
    "vertices", "edges", "polygons", "loops", "loop_triangles",
    "attributes", "color_attributes", "uv_layers", "vertex_colors",
    "corner_normals", "vertex_normals", "edge_creases",
}
_DANGEROUS_NAME_LOOKUP = re.compile(
    r"(?:bpy\s*\.\s*data\s*\.\s*(?:objects|collections)|"
    r"bpy\s*\.\s*context\s*\.\s*(?:scene|view_layer))"
    r"\s*(?:\[|\.\s*get\s*\(|\.\s*objects\s*\[|\.\s*objects\s*\.\s*get\s*\()",
    re.IGNORECASE,
)


def _bl_type(value):
    return str(getattr(getattr(value, "bl_rna", None), "identifier", type(value).__name__))


def _idlike(value):
    if value is None:
        return False
    # Production uses actual bpy.types.ID; synthetic QA may expose compatible mocks.
    if bpy is not None and hasattr(bpy, "types") and hasattr(bpy.types, "ID"):
        return isinstance(value, bpy.types.ID)
    return hasattr(value, "id_type") and hasattr(value, "as_pointer")


def _iter_rna_properties(value):
    rna = getattr(value, "bl_rna", None)
    if rna is None:
        raise IncompleteDiscovery("Sem metadados RNA: " + _bl_type(value))
    props = getattr(rna, "properties", None)
    if props is None:
        raise IncompleteDiscovery("Propriedades RNA ausentes: " + _bl_type(value))
    try:
        return list(props)
    except Exception as exc:
        raise IncompleteDiscovery("Impossivel enumerar propriedades RNA") from exc


def _read_safe(value, prop):
    key = str(getattr(prop, "identifier", ""))
    if not key:
        raise IncompleteDiscovery("Property RNA sem identifier")
    try:
        return getattr(value, key)
    except Exception as exc:
        raise IncompleteDiscovery("Falha RNA: %s.%s" % (_bl_type(value), key)) from exc


def _text_lookup_risk(data, names):
    """Conservative static veto, not an interpreter of arbitrary Python.

    Any observable Blender namespace, import, reflection or dynamic code is
    indeterminate, including aliases/getattr/computed names. Benign labels and
    plain numeric IDProperties are allowed. External scripts remain unobservable.
    """
    if not isinstance(data, str) or not data.strip(): return False
    _budget().allocation_bound(len(data.encode("utf-8"))*32, "AST-texto")
    if re.search(r"\b(?:bpy|objects|collections|__import__|getattr|eval|exec|importlib|globals|locals)\b", data):
        return True
    try:
        tree = ast.parse(data)
    except (SyntaxError, ValueError):
        # Unknown source-like strings cannot certify absence of a name lookup.
        return any(token in data for token in ("[", ".get(", "(", "="))
    for node in _checked(ast.walk(tree), "AST-texto"):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.Call, ast.Subscript, ast.Attribute)):
            return True
    return False


class ReferenceScanner:
    """Fail-closed inventory; uninspected surfaces preclude ALL removals.

    Scans every accessible bpy.data ID, including orphan IDs and embedded IDs
    discovered through nested RNA, and IDProperties. `user_map` is corroboration
    only. No geometric remapping of references is ever performed.
    """
    def __init__(self, blend_data, clusters, budget, removed=()):
        self.data = blend_data
        self.removed = set(removed)
        self.blockers = []
        self.strings = []
        self.clusters = clusters
        self.budget = budget
        self.drops = {stable_id(obj): obj for _, rem in clusters for obj in rem}
        self.drop_keys = set(self.drops)
        self.keepers = {stable_id(obj) for keep, _ in clusters for obj in (keep,)}
        self.refs = []
        self.visited_owners = set()
        self.owners = {}
        self.pending_ids = []
        self.uninspected = []
        self.excluded_surfaces = []
        self.affected_by_collection = defaultdict(set)
        self.belonging = defaultdict(set)
        self.parents_by_collection = defaultdict(set)
        self.coverage = Counter()
        self.names = {obj.name for obj in self.drops.values()}

    def _add_id(self, value):
        ptr = stable_id(value)
        if ptr in self.removed: return
        if ptr not in self.owners:
            self.owners[ptr] = value
            self.pending_ids.append(value)

    def _roots(self):
        if not hasattr(self.data, "user_map") or not callable(self.data.user_map):
            raise IncompleteDiscovery("bpy.data.user_map nao disponivel para cruzamento")
        # Blender BlendData RNA: every collection of datablocks is enumerated.
        for prop in _iter_rna_properties(self.data):
            name = str(getattr(prop, "identifier", ""))
            if name in ("rna_type",) or getattr(prop, "type", "") != "COLLECTION":
                continue
            try:
                sequence = getattr(self.data, name)
                for member in sequence:
                    if not _idlike(member):
                        raise IncompleteDiscovery("Blender data collection nao-ID: " + name)
                    self._add_id(member)
            except IncompleteDiscovery:
                raise
            except Exception as exc:
                raise IncompleteDiscovery("Nao foi possivel enumerar bpy.data." + name) from exc
        # Do not accept incomplete discoverability of bpy.data.objects itself.
        for obj in self.data.objects:
            if stable_id(obj) not in self.owners:
                raise IncompleteDiscovery("Object fora do inventario bpy.data")
        if not self.owners:
            raise IncompleteDiscovery("Inventario ID vazio/inacessivel")

    def _record_ref(self, owner, target, path, surface):
        rec = Reference(owner, target, path, surface)
        if stable_id(target) in self.removed and self._is_membership(rec): return rec
        self.refs.append(rec)
        self.coverage["rna_pointer_ids"] += 1
        return rec

    def _scan_idprops(self, value, owner, path, depth=0, seen=None):
        if depth > 32:
            raise IncompleteDiscovery("Profundidade IDProperties excedida: " + path)
        if seen is None:
            seen = set()
        if _idlike(value):
            self._add_id(value)
            self._record_ref(owner, value, path, "IDProperty")
            return
        if isinstance(value, str):
            self.strings.append((stable_id(owner), path, value))
            if _text_lookup_risk(value, self.names):
                self.blockers.append({"surface": "IDProperty", "path": path, "owner": snapshot(owner),
                    "reason": "Lookup dinamico/indeterminado em IDProperties", "action": "ABORT_GLOBAL"})
            return
        if isinstance(value, (int, float, bool, bytes, type(None))):
            return
        key = id(value)
        if key in seen:
            return
        seen.add(key)
        self.budget.node()
        if hasattr(value, "items") and callable(value.items):
            try:
                entries = list(value.items())
            except Exception as exc:
                raise IncompleteDiscovery("IDPropertyGroup nao enumeravel: " + path) from exc
            for subkey, subval in entries:
                self._scan_idprops(subval, owner, path + "[" + repr(subkey) + "]", depth+1, seen)
            return
        if isinstance(value, (tuple, list)):
            for index, item in enumerate(value):
                self._scan_idprops(item, owner, path + "[%d]" % index, depth+1, seen)
            return
        # Numeric arrays are not Object references; unsupported exotic types abort.
        if isinstance(value, np.ndarray) and value.dtype.kind in "fiub":
            return
        if (hasattr(value, "typecode") and getattr(value, "typecode", None) in
                ("b", "B", "h", "H", "i", "I", "l", "L", "q", "Q", "f", "d", "?")):
            # IDPropertyArray / array.array numeric types cannot store ID pointers.
            return
        raise IncompleteDiscovery("Tipo IDProperty desconhecido: %s (%s)" % (path, type(value).__name__))

    def _scan_struct(self, value, owner, path, seen, depth=0):
        if depth > 64:
            raise IncompleteDiscovery("RNA nested profundo demais: " + path)
        identifier = stable_id(value) if hasattr(value, "as_pointer") else id(value)
        if identifier in seen:
            return
        seen.add(identifier)
        self.budget.node()
        struct_type = _bl_type(value)
        self.coverage["rna_structs"] += 1
        # Do not recursively follow unrelated IDs: each is its own persisted owner.
        for prop in _iter_rna_properties(value):
            field_name = str(getattr(prop, "identifier", ""))
            if field_name in ("rna_type", "id_data", "original"):
                continue
            ptype = getattr(prop, "type", "")
            if ptype not in ("POINTER", "COLLECTION", "STRING"):
                continue
            if (struct_type, field_name) in _SKIP_INVERSE_PATHS:
                self.coverage["skipped_reverse_backlinks"] += 1
                self.excluded_surfaces.append({"path":path + "." + field_name,
                      "reason":"backlink RNA calculado; varredura usa referencia direta de owner"})
                continue
            if struct_type == "Mesh" and field_name in _MESH_PRIMITIVE_COLLECTIONS:
                self.coverage["skipped_numeric_mesh_structures"] += 1
                self.excluded_surfaces.append({"path":path + "." + field_name,
                    "reason":"elementos primitivos de geometria presumidos sem ID pointers; confirmar Blender 5.0"})
                continue
            child_path = path + "." + field_name
            result = _read_safe(value, prop)
            if ptype == "STRING":
                self.strings.append((stable_id(owner), child_path, str(result)))
                # Detect source strings/driver expressions without treating labels
                # or ordinary object names as dynamic Python lookups.
                if field_name in ("expression", "script", "text") and _text_lookup_risk(result, self.names):
                    self.blockers.append({"surface": struct_type, "path": child_path, "reason": "Codigo/expressao indeterminada", "action": "ABORT_GLOBAL"})
                continue
            if ptype == "POINTER":
                if result is None:
                    continue
                if _idlike(result):
                    self._record_ref(owner, result, child_path, struct_type)
                    self._add_id(result)
                else:
                    self._scan_struct(result, owner, child_path, seen, depth+1)
            else:
                if result is None:
                    raise IncompleteDiscovery("Colecao RNA None: " + child_path)
                try:
                    iterator = iter(result)
                except Exception as exc:
                    raise IncompleteDiscovery("Colecao RNA nao iteravel: " + child_path) from exc
                for index, member in enumerate(iterator):
                    self.budget.node()
                    subpath = child_path + "[%d]" % index
                    if _idlike(member):
                        self._record_ref(owner, member, subpath, struct_type)
                        self._add_id(member)
                    else:
                        self._scan_struct(member, owner, subpath, seen, depth+1)
        if hasattr(value, "items") and callable(value.items):
            try:
                entries = list(value.items())
            except Exception as exc:
                raise IncompleteDiscovery("IDProperties inacessiveis: " + path) from exc
            for key, item in entries:
                self._scan_idprops(item, owner, path + ".IDProperty[" + repr(key) + "]")

    def _scan_text(self, owner):
        if _bl_type(owner) != "Text":
            return
        if not hasattr(owner, "as_string"):
            raise IncompleteDiscovery("Text sem as_string()")
        try:
            content = owner.as_string()
        except Exception as exc:
            raise IncompleteDiscovery("Impossivel ler Text datablock") from exc
        if len(content.encode("utf-8")) > self.budget.limits.text_bytes:
            raise ComplexityBudgetExceeded("Text muito grande para varredura")
        self.strings.append((stable_id(owner), "Text.as_string", content))
        self.coverage["texts_scanned"] += 1
        if _text_lookup_risk(content, self.names):
            self.blockers.append({"surface": "Text", "path": owner.name, "reason": "Text com acesso dinamico/indeterminado", "action": "ABORT_GLOBAL"})

    def _scan_all(self):
        self._roots()
        while self.pending_ids:
            self.budget.checkpoint("inventario-ids")
            owner = self.pending_ids.pop()
            oid = stable_id(owner)
            if oid in self.visited_owners:
                continue
            self.visited_owners.add(oid)
            self.coverage["ids_scanned"] += 1
            try:
                self._scan_struct(owner, owner, _bl_type(owner), set())
                self._scan_text(owner)
            except ComplexityBudgetExceeded:
                self.uninspected.append({"owner": snapshot(owner), "reason": "budget", "scan_status": "INCOMPLETE"})
                raise
            except (PreflightAborted, ValueError, TypeError) as exc:
                self.uninspected.append({"owner": snapshot(owner), "reason": str(exc), "scan_status": "INCOMPLETE"})
                self.blockers.append({"owner": snapshot(owner), "reason": str(exc), "action": "ABORT_GLOBAL"})

    @staticmethod
    def _kind(value):
        return _bl_type(value)

    def _is_membership(self, ref):
        owner_kind = self._kind(ref.owner)
        p = ref.path
        # Collection -> Object membership, Scene/ViewLayer computed object sets.
        if owner_kind == "Collection" and (p.startswith("Collection.objects[") or p.startswith("Collection.all_objects[")):
            return True
        if owner_kind == "Scene" and (p.startswith("Scene.objects[") or ".objects[" in p and "view_layers" in p):
            return True
        return False

    def _is_hierarchy(self, ref):
        if self._kind(ref.owner) == "Collection" and ref.path.startswith("Collection.children["):
            return True
        if self._kind(ref.owner) == "Scene" and ref.path == "Scene.collection":
            return True
        if self._kind(ref.owner) == "Scene" and ".layer_collection" in ref.path and ref.path.endswith(".collection"):
            return True
        return False

    def _check_object_flags(self):
        for keep, _ in self.clusters:
            if getattr(keep, "mode", None) != "OBJECT" or getattr(keep, "is_evaluated", True):
                self.blockers.append({"owner": snapshot(keep), "reason": "KEEP em modo/estado nao confiavel", "action": "ABORT_GLOBAL"})
            if getattr(keep.data, "is_evaluated", False) or getattr(keep.data, "is_library_indirect", False):
                self.blockers.append({"owner": snapshot(keep), "reason": "Mesh KEEP nao confiavel", "action": "ABORT_GLOBAL"})
        for obj in self.drops.values():
            # KEEP may be linked/readonly: it is not mutated.
            try:
                linked = getattr(obj, "library", None) is not None
                indirect = bool(getattr(obj, "is_library_indirect"))
                override = getattr(obj, "override_library") is not None
                editable = bool(getattr(obj, "is_editable"))
                evaluated = bool(getattr(obj, "is_evaluated"))
                mode = str(getattr(obj, "mode"))
            except Exception as exc:
                raise IncompleteDiscovery("Flags de elegibilidade inacessiveis") from exc
            if linked or indirect or override or not editable or evaluated or mode != "OBJECT":
                self.blockers.append({"owner": snapshot(obj), "reason": "DROP nao elegivel linked=%s indirect=%s override=%s editable=%s evaluated=%s mode=%s" % (linked, indirect, override, editable, evaluated, mode), "action": "ABORT_GLOBAL"})
            mesh = obj.data
            # Data Mesh is never removed directly. Linked Mesh may stay linked,
            # but evaluated/indirect Mesh state is not trusted for safe planning.
            if getattr(mesh, "is_evaluated", False) or getattr(mesh, "is_library_indirect", False):
                self.blockers.append({"owner": snapshot(obj), "reason": "Mesh DROP nao confiavel", "action": "ABORT_GLOBAL"})
        self.coverage["eligibility_checked"] = len(self.drops)

    def _classify(self):
        drop_keys = self.drop_keys
        # Build parent closure for every collection with a candidate object.
        for ref in self.refs:
            if self._is_hierarchy(ref) and self._kind(ref.owner) == "Collection" and self._kind(ref.target) == "Collection":
                self.parents_by_collection[stable_id(ref.target)].add(stable_id(ref.owner))
            if (stable_id(ref.target) in drop_keys and self._is_membership(ref)):
                self.belonging[stable_id(ref.target)].add(stable_id(ref.owner))
        affected = set(c for children in self.belonging.values() for c in children)
        queue = list(affected)
        while queue:
            self.budget.node()
            child = queue.pop()
            for parent in self.parents_by_collection.get(child, ()):
                if parent not in affected:
                    affected.add(parent)
                    queue.append(parent)
        for drop, memberships in self.belonging.items():
            seen = set(memberships)
            todo = list(seen)
            while todo:
                self.budget.node()
                child = todo.pop()
                self.affected_by_collection[child].add(drop)
                for parent in self.parents_by_collection.get(child, ()):
                    if parent not in seen: seen.add(parent); todo.append(parent)
        for ref in self.refs:
            target_id = stable_id(ref.target)
            owner_id = stable_id(ref.owner)
            if target_id in drop_keys:
                if self._is_membership(ref):
                    # No write to a linked/readonly Collection or Scene is assumed
                    # safe merely because its relationship is membership.
                    if (getattr(ref.owner, "library", None) is not None or
                        not bool(getattr(ref.owner, "is_editable", False)) or
                        getattr(ref.owner, "override_library", None) is not None):
                        self.blockers.append({"path": ref.path, "reason": "Membership em owner nao editavel", "action": "ABORT_GLOBAL"})
                    ref.category = "PERTENCIMENTO_AUTORIZADO"
                    ref.why = "Unlink de Scene/Collection inerente ao remove"
                elif owner_id in drop_keys:
                    ref.category = "INTERNA_A_REMOVIDOS"
                    ref.why = "Owner tambem e DROP"
                else:
                    ref.category = "FUNCIONAL_DIRETA"
                    ref.why = "Owner sobrevivente referencia DROP"
                    self.blockers.append(ref.record(self.drop_keys, self.keepers))
            elif target_id in affected and self._kind(ref.target) == "Collection":
                if self._is_hierarchy(ref):
                    ref.category = "PERTENCIMENTO_AUTORIZADO"
                    ref.why = "Hierarquia Scene/Collection"
                elif owner_id in drop_keys:
                    ref.category = "INTERNA_A_REMOVIDOS"
                    ref.why = "Consumidor da Collection tambem sera removido"
                else:
                    ref.category = "FUNCIONAL_INDIRETA"
                    ref.why = "Collection contendo DROP consumida por owner sobrevivente"
                    self.blockers.extend(ref.record(self.drop_keys, self.keepers, snapshot(self.drops[key]))
                        for key in sorted(self.affected_by_collection[target_id]))
            else:
                ref.category = "FORA_DOS_ALVOS"
        self.coverage["candidate_collections"] = len(affected)

    def _user_map_corroborate(self):
        """Normalize forward users, excluding computed Scene.objects backlinks.

        Collection.objects is an actual comparable membership; Scene.objects and
        view-layer projections need not be ID users. Actual users must still have
        a discovered path. Missing keys are accepted only with no expected users.
        This policy requires future Blender API verification.
        """
        actual = self.data.user_map(subset=list(self.drops.values()))
        if not isinstance(actual, dict): raise IncompleteDiscovery("user_map tipo inesperado")
        discovered, comparable = defaultdict(set), defaultdict(set)
        for ref in self.refs:
            key = stable_id(ref.target)
            if key not in self.drop_keys: continue
            owner = stable_id(ref.owner)
            discovered[key].add(owner)
            if not (self._kind(ref.owner) == "Scene" and self._is_membership(ref)):
                comparable[key].add(owner)
        normalized = {}
        for target, owners in actual.items():
            key = stable_id(target)
            if key not in self.drop_keys or key in normalized:
                raise IncompleteDiscovery("user_map alvo inesperado/duplicado")
            normalized[key] = {stable_id(owner) for owner in owners}
        for key in self.drop_keys:
            got = normalized.get(key, set())
            missing, unknown = comparable[key] - got, got - discovered[key]
            if missing or unknown:
                self.blockers.append({"drop_key": snapshot(self.drops[key]), "surface": "user_map",
                    "reason": "user_map divergente", "missing_users": sorted(missing),
                    "unknown_users": sorted(unknown), "action": "ABORT_GLOBAL"})
        self.coverage["user_map_checked"] = len(self.drop_keys)

    def report(self):
        uninspected = list(self.uninspected)
        uninspected.extend({"owner": snapshot(o), "scan_status": "NOT_INSPECTED", "reason": "inventario interrompido"}
                           for key, o in self.owners.items() if key not in self.visited_owners)
        return {"coverage": dict(self.coverage),
                "references": [r.record(self.drop_keys, self.keepers, snapshot(self.drops[key]) if key is not None else None)
                    for r in self.refs if stable_id(r.target) in self.drop_keys or r.category == "FUNCIONAL_INDIRETA"
                    for key in (sorted(self.affected_by_collection[stable_id(r.target)]) if r.category == "FUNCIONAL_INDIRETA" else [None])],
                "blockers": list(self.blockers), "uninspected": uninspected,
                "excluded_by_assumption": list(self.excluded_surfaces),
                "external_sources": "NOT_OBSERVABLE: external Python/handlers require independent runtime gate"}

    def inspect(self):
        try:
            self._check_object_flags()
            self._scan_all()
            self._classify()
            self._user_map_corroborate()
            self.budget.checkpoint("fim-dependencias")
            if self.blockers or self.uninspected:
                raise UnsafeReference("Inventario bloqueado: %d diagnosticos" % len(self.blockers))
        except BaseException as exc:
            exc.inventory = self.report()
            raise
        return self.report()

# --- Preflight, auto-delete, and nontransactional ledger ---

def _ledger(clusters, total_meshes, inventory, budget):
    return {
        "version": VERSION,
        "status": "PRE_DELETE_PLAN_UNCHANGED",
        "total_meshes": total_meshes,
        "clusters": [{"keep": snapshot(keep),
                      "keep_modifiers": len(keep.modifiers),
                      "keep_shape_keys": number_of_shape_keys(keep),
                      "drops": [snapshot(obj) for obj in drops]}
                     for keep, drops in clusters],
        "drops_count": sum(len(drops) for _, drops in clusters),
        "decisions": [{"drop_key": snapshot(obj), "keep_key": snapshot(keep),
            "owner_lifecycle": "DROP", "scan_status": "INSPECTED" if not inventory.get("blockers") else "BLOCKED",
            "action": "REMOVE_ONLY_IF_REVALIDATED" if not inventory.get("blockers") else "ABORT_GLOBAL",
            "reason": "Exact geometry witness and absolute R2 ranking; dependency inventory attached",
            "evidence": {"inventory_blockers": inventory.get("blockers", []), "mesh_counts": mesh_counts(obj.data)}}
            for keep, drops in clusters for obj in drops],
        "inventory": inventory,
        "budget": {"time_s": round(time.perf_counter() - budget.started, 5),
                   "states": budget.total_states,
                   "comparisons": budget.comparisons,
                   "rna_nodes": budget.rna_nodes,
                   "rss_start": budget.initial_rss, "rss_peak": budget.rss_peak,
                   "largest_estimated_allocation": budget.global_allocation_peak_request},
        "no_autosave": True,
        "runtime_blender_approved": False,
    }


def _object_state(blend_data, budget):
    """Raw base buffers, ranking and eligibility; no removed proxies retained."""
    rows = []
    cache = {}
    for obj in _checked(list(blend_data.objects), "snapshot-objects"):
        row = {"key": snapshot(obj), "type": str(obj.type),
               "mode": str(getattr(obj, "mode", None)),
               "flags": _flags(obj)}
        if obj.type == "MESH":
            mesh = obj.data
            if mesh is None: raise PreflightAborted("MESH sem dados")
            ptr = mesh_identity(mesh)
            if ptr not in cache:
                _check_structural_indices(mesh)
                quantized_vertices(mesh)  # validates NaN, Inf and overflow
                budget.allocation_bound(len(mesh.vertices)*16, "snapshot-coordenadas")
                raw = np.empty(len(mesh.vertices)*3, dtype=np.float32)
                if len(raw): mesh.vertices.foreach_get('co', raw)
                h = hashlib.sha256(raw.tobytes())
                del raw
                for array in (get_edges(mesh), *get_polygons(mesh)):
                    budget.checkpoint("snapshot-buffer")
                    h.update(array.tobytes())
                cache[ptr] = {"pointer": ptr, "counts": mesh_counts(mesh), "raw_sha256": h.hexdigest(),
                              "flags": _flags(mesh), "is_editmode": bool(getattr(mesh, "is_editmode", False))}
            row["mesh"] = cache[ptr]
            row["rank"] = preference(obj)
        rows.append(row)
    return sorted(rows, key=lambda row: row["key"]["pointer"])


def _flags(item):
    def token(value):
        if value is None or isinstance(value, (str, int, bool)): return value
        return stable_id(value)
    return {name: token(getattr(item, name, None)) for name in
            ("library", "is_library_indirect", "override_library", "is_editable", "is_evaluated")}


def _observed_state(blend_data, clusters, budget, removed=()):
    # Caller supplies live clusters: never inspect already removed object proxies.
    scanner = ReferenceScanner(blend_data, clusters, budget, removed)
    inventory = scanner.inspect()
    refs = []
    for ref in scanner.refs:
        if stable_id(ref.owner) in removed: continue
        if stable_id(ref.target) in removed and scanner._is_membership(ref): continue
        if stable_id(ref.target) in removed:
            raise UnsafeReference("Referencia funcional a objeto ja removido")
        path = ref.path
        if scanner._is_membership(ref): path = re.sub(r"\[\d+\]", "[*]", path)
        refs.append((stable_id(ref.owner), stable_id(ref.target), path, ref.surface))
    state = {"objects": _object_state(blend_data, budget),
             "owners": sorted((key, snapshot(owner), _flags(owner)) for key, owner in scanner.owners.items() if key not in removed),
             "refs": sorted(refs), "strings": sorted(scanner.strings)}
    return state, inventory


def _project_state(state, removed):
    """Only expected changes: absent DROP, outgoing edges and unlink membership.

    Real remove updates collections/scenes; fixtures may retain stale membership.
    Numeric membership indexes are normalized. All other changes abort.
    """
    return {"objects": [row for row in state["objects"] if row["key"]["pointer"] not in removed],
            "owners": [row for row in state["owners"] if row[0] not in removed],
            "strings": [row for row in state["strings"] if row[0] not in removed],
            "refs": [row for row in state["refs"] if row[0] not in removed and not
                     (row[1] in removed and (row[2].startswith("Collection.objects[") or
                      row[2].startswith("Scene.objects[") or "view_layers" in row[2] and ".objects[" in row[2]))]}


def preflight(blend_data, limits=None, *, context_mode="OBJECT", _budget_context=None):
    """Read-only global plan. Failure carries diagnostics; never calls remove."""
    if context_mode != "OBJECT": raise PreflightAborted("Blender precisa estar em Object Mode")
    if not hasattr(blend_data, "objects"): raise IncompleteDiscovery("bpy.data.objects indisponivel")
    budget = _budget_context or BudgetContext(limits)
    with bound_budget(budget):
        before = _object_state(blend_data, budget)
        objects = list(blend_data.objects)
        ids = [stable_id(obj) for obj in objects]
        if len(set(ids)) != len(ids): raise IncompleteDiscovery("Identidade ambigua em bpy.data.objects")
        clusters, total_meshes = plan_removals(objects, budget)
        if clusters:
            try:
                state, inventory = _observed_state(blend_data, clusters, budget)
            except BaseException as exc:
                exc.plan = _ledger(clusters, total_meshes, getattr(exc, "inventory", {}), budget)
                raise
            if state["objects"] != before: raise MutationDetected("Objects mudaram durante planejamento")
        else:
            state = None
            inventory = {"coverage": {}, "references": [], "blockers": [], "uninspected": [], "excluded_by_assumption": []}
        budget.checkpoint("fim-preflight")
        result = _ledger(clusters, total_meshes, inventory, budget)
        result["_stability"] = state
        return clusters, objects, result


def _enumerate_current_snapshots(blend_data):
    """Only new proxies from bpy.data.objects; never touch invalid DROPs."""
    return [snapshot(obj) for obj in list(blend_data.objects)]


def reconcile(plan, blend_data):
    """Triple status. No claim if UID missing or enumeration uncertain."""
    original = [rec for group in plan["clusters"] for rec in group["drops"]]
    try:
        current = _enumerate_current_snapshots(blend_data)
    except BaseException as exc:
        return {"reconcile_error": type(exc).__name__,
                "items": [{"snapshot": item, "status": "INDETERMINADO"} for item in original]}
    valid_ids = [v["session_uid"] for v in current if v["session_uid"] is not None]
    duplicated_uids = len(valid_ids) != len(set(valid_ids))
    by_uid = {s["session_uid"]: s for s in current if s["session_uid"] is not None}
    by_pointer = {(s["pointer"], s["name"]): s for s in current}
    rows = []
    for item in original:
        sid = item["session_uid"]
        if sid is not None and not duplicated_uids:
            state = "CONFIRMADO_PRESENTE" if sid in by_uid else "CONFIRMADO_REMOVIDO"
            proof = "session_uid+enumeracao"
        elif (item["pointer"], item["name"]) in by_pointer:
            state = "CONFIRMADO_PRESENTE"
            proof = "nome+pointer-atual (sem UID unico)"
        else:
            state = "INDETERMINADO"
            proof = "sem session_uid confiavel, possivel rename/reuso"
        rows.append({"snapshot": item, "status": state, "proof": proof})
    return {"items": rows,
            "removed_confirmed": sum(x["status"] == "CONFIRMADO_REMOVIDO" for x in rows),
            "present_confirmed": sum(x["status"] == "CONFIRMADO_PRESENTE" for x in rows),
            "indeterminate": sum(x["status"] == "INDETERMINADO" for x in rows)}


def _log_json(prefix, data):
    # Printing MAY fail: any failure before first remove => zero removals;
    # after first => stop, reconcile and report possible partial failure.
    print(prefix + " " + json.dumps(data, ensure_ascii=False, sort_keys=True, default=str), flush=True)


_EXECUTE_LOCK = threading.Lock()
_REENTRY_EPOCH = 0


class ExecutionFailure(RuntimeError):
    """Nontransactional failure; ledger remains available if stdout is broken."""
    def __init__(self, ledger):
        self.ledger = ledger
        super().__init__("FALHA_PARCIAL_POSSIVEL: %d chamada(s); %s" %
                         (ledger["calls_attempted"], ledger["detail"]))


def execute(blend_data, *, context_mode="OBJECT", limits=None, emit=_log_json):
    """Exclusive, revalidated execution with detached logger payloads.

    Each callback and each remove is an untrusted boundary. Revalidation detects
    observable persistent changes; arbitrary concurrent writes/getter side effects
    inside a check/remove cannot be made atomic by this Python API. Runtime HOLD.
    """
    global _REENTRY_EPOCH
    if not _EXECUTE_LOCK.acquire(blocking=False):
        _REENTRY_EPOCH += 1
        exc = PreflightAborted("Reentrancia/concorrencia recusada (ZERO REMOCOES nesta chamada)")
        exc.ledger = {"status": "ABORT_POR_MUTACAO_ZERO_REMOVOES", "calls_attempted": 0}
        raise exc
    epoch = _REENTRY_EPOCH
    calls = 0
    plan = None
    removed = set()
    current_clusters = []
    try:
        budget = BudgetContext(limits)
        with bound_budget(budget):
            clusters, original_objects, plan = preflight(blend_data, limits, context_mode=context_mode, _budget_context=budget)
            baseline = plan.pop("_stability")
            # Capture every DROP identity before deletion; no post-remove reads.
            current_clusters = [(keep, [(obj, stable_id(obj), snapshot(obj)) for obj in drops]) for keep, drops in clusters]
            del original_objects

            def validate():
                if epoch != _REENTRY_EPOCH: raise MutationDetected("Tentativa de reentrancia observada")
                _enumerate_current_snapshots(blend_data)  # independent enumeration can fail closed
                if baseline is None:
                    return
                live = [(keep, tuple(obj for obj, key, snap in drops if key not in removed))
                        for keep, drops in current_clusters]
                try:
                    state, inventory = _observed_state(blend_data, live, budget, removed)
                except (UnsafeReference, IncompleteDiscovery) as exc:
                    changed = MutationDetected("Inventario deixou de ser seguro: " + str(exc))
                    changed.inventory = getattr(exc, "inventory", {})
                    raise changed from exc
                if _project_state(baseline, removed) != _project_state(state, removed):
                    raise MutationDetected("Geometria/flags/ranking/referencias/textos mudaram")
                budget.checkpoint("revalidacao-finalizada")

            def log_boundary(label, payload):
                # The callback can neither corrupt the internal ledger nor its status.
                emit(label, copy.deepcopy(payload))
                validate()

            log_boundary("[T7-DEDUP-LEDGER-PRE]", plan)
            if plan["drops_count"] == 0:
                log_boundary("[T7-DEDUP-RESULT]", {"status": "SEM_DUPLICATAS", "removed": 0})
                return {"plan": plan, "status": "SEM_DUPLICATAS", "reconciliation": {"items": []}}
            for keep, drops in current_clusters:
                for obj, key, obj_snapshot in drops:
                    log_boundary("[T7-DEDUP-BEFORE-REMOVE]", {"call": calls+1, "drop": obj_snapshot})
                    calls += 1
                    blend_data.objects.remove(obj, do_unlink=True)
                    removed.add(key)
                    validate()  # catches mutation even on the last removal
                    log_boundary("[T7-DEDUP-AFTER-REMOVE]", {"call": calls, "drop_snapshot": obj_snapshot})
            resolution = reconcile(plan, blend_data)
            if resolution.get("indeterminate", 1) or resolution.get("present_confirmed", 1):
                raise RuntimeError("Nao e possivel confirmar todas as remocoes")
            # No success is reported to an arbitrary callback before validating its effects.
            log_boundary("[T7-DEDUP-RESULT]", {"status": "PENDING_FINAL_VALIDATION", "calls": calls,
                                             "reconciliation": resolution})
            return {"status": "REMOVOES_CONFIRMADAS", "calls": calls, "plan": plan,
                    "reconciliation": resolution, "no_autosave": True}
    except BaseException as exc:
        if plan is None: plan = getattr(exc, "plan", None)
        status = ("ABORT_POR_MUTACAO_ZERO_REMOVOES" if isinstance(exc, MutationDetected)
                  else "INCONCLUSIVO_ZERO_REMOVOES") if calls == 0 else "FALHA_PARCIAL_POSSIVEL"
        ledger = {"status": status, "calls_attempted": calls, "zero_removals": calls == 0,
                  "exception": type(exc).__name__, "detail": str(exc), "plan": plan,
                  "inventory": getattr(exc, "inventory", plan.get("inventory") if plan else None),
                  "no_rollback": True, "no_autosave": True}
        if plan is not None:
            ledger["reconciliation"] = reconcile(plan, blend_data)
            ledger["decisions"] = [{"drop_key": row["snapshot"], "scan_status": "ABORTED",
                "action": "STOP_NO_MORE_REMOVALS", "reason": str(exc), "evidence": row}
                for row in ledger["reconciliation"]["items"]]
        try: emit("[T7-DEDUP-PREFLIGHT-ABORT]" if calls == 0 else "[T7-DEDUP-FALHA-PARCIAL]", copy.deepcopy(ledger))
        except BaseException: pass
        if calls == 0:
            failure = PreflightAborted("Preflight abortado (ZERO REMOCOES): " + str(exc))
            failure.ledger = ledger
            raise failure from exc
        raise ExecutionFailure(ledger) from exc
    finally:
        _EXECUTE_LOCK.release()


def run_blender():
    if bpy is None:
        raise RuntimeError("Execute somente em Blender real apos autorizacao/homologacao futura.")
    mode = getattr(getattr(bpy, "context", None), "mode", None)
    print("[T7-Dedup v1.0.2-test1 CANDIDATA] Inicio, sem autosave; analise global e remocao automatica segura.", flush=True)
    return execute(bpy.data, context_mode=mode)


if __name__ == "__main__":
    run_blender()
