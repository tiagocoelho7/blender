"""Limpador de objetos MESH duplicados em todo o .blend -- CANDIDATA v1.0.

Criterio: mesma malha-base (coordenadas arredondadas a cinco casas,
arestas e faces, inclusive orientacao), independente dos indices internos,
ordem das arestas/faces e transformacoes do objeto. Ignora materiais,
UVs, modifiers, shape keys e animacoes para identificar duplicatas.

Mantem o objeto com mais modifiers; desempata pelo numero de shape keys;
em novo empate usa nome e identificador determinista da sessao.

AVISO: REMOVE os objetos duplicados imediatamente do arquivo EM MEMORIA.
Nao salva o .blend automaticamente; salve manualmente apos conferir.
Nao execute sem backups. Testado offline com simulacoes; requer validacao
no Blender 5.0 real antes de uso em producao.
"""

from collections import Counter, defaultdict
import hashlib

try:
    import numpy as np
except ImportError as exc:
    raise RuntimeError('Este script requer NumPy, normalmente incluso no Blender.') from exc

try:
    import bpy
except ImportError:
    bpy = None  # Permite testes offline sem executar o Blender.

PRECISION = 5
FACTOR = 10 ** PRECISION
INT64_LIMIT = 2**63 - 1


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
    coords = np.empty(n * 3, dtype=np.float32)
    if n:
        mesh.vertices.foreach_get('co', coords)
    coords = coords.reshape((n, 3)).astype(np.float64)
    if not np.isfinite(coords).all():
        raise ValueError('A malha contem coordenadas nao finitas (NaN/Inf).')
    if coords.size and np.max(np.abs(coords)) * FACTOR >= INT64_LIMIT:
        raise ValueError('Coordenadas fora do intervalo aceito pela quantizacao.')
    return np.rint(coords * FACTOR).astype(np.int64)


def get_edges(mesh):
    e = len(mesh.edges)
    out = np.empty(e * 2, dtype=np.int32)
    if e:
        mesh.edges.foreach_get('vertices', out)
    return out.reshape((e, 2))


def get_polygons(mesh):
    p, l = len(mesh.polygons), len(mesh.loops)
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
    while i < n and j < n and k < n:
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
    for u, v in edges:
        u, v = int(u), int(v)
        if u in amb:
            neigh[u].append(int(qclasses[v]))
        if v in amb:
            neigh[v].append(int(qclasses[u]))
    starts, totals, loops = polygons
    for start, size in zip(starts, totals):
        start, size = int(start), int(size)
        indices = loops[start:start+size]
        for j, raw in enumerate(indices):
            v = int(raw)
            if v in amb:
                prev = int(qclasses[int(indices[(j-1) % size])])
                nxt = int(qclasses[int(indices[(j+1) % size])])
                corners[v].append((size, prev, nxt))
    return {v: (int(qclasses[v]), tuple(sorted(neigh[v])), tuple(sorted(corners[v])))
            for v in amb}


def _ambiguous_isomorphism(mesh_a, mesh_b, q_a, q_b, order_a, order_b):
    """Busca exata em vertices coincidentes (iterativa, sem limite de profundidade).

    Verifica isomorfismo que preserve coordenada quantizada, arestas,
    multiplicidades e sequencias orientadas de faces. Pode ser caro em
    malhas patologicamente simetricas; NUNCA aceita so por hash.
    """
    n = len(q_a)
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
    for cls, (start, stop) in enumerate(zip(starts, stops)):
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
    for i, key in sig_a.items():
        groups_a[key].append(i)
    for i, key in sig_b.items():
        groups_b[key].append(i)
    if {key: len(v) for key, v in groups_a.items()} != {key: len(v) for key, v in groups_b.items()}:
        return False
    remaining = set()
    candidates = {}
    for key, verts_a in groups_a.items():
        verts_b = groups_b[key]
        if len(verts_a) == 1:
            a, b = verts_a[0], verts_b[0]
            mapping[a] = b
            reverse[b] = a
        else:
            remaining.update(verts_a)
            for a in verts_a:
                candidates[a] = tuple(sorted(verts_b))

    # Preparar adjacencias somente dos vertices ambiguos (economiza memoria).
    adj_a = {a: Counter() for a in ambiguous_a}
    adj_b = {b: Counter() for b in ambiguous_b}
    for u, v in edges_a:
        u, v = int(u), int(v)
        if u in adj_a:
            adj_a[u][v] += 1
        if v in adj_a:
            adj_a[v][u] += 1
    for u, v in edges_b:
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
        for start, size in zip(starts_, totals_):
            raw = tuple(int(i) for i in loops_[int(start):int(start)+int(size)])
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
    available_b = Counter(_canonical_cycle(f) for f in faces_b)

    def consume_complete_faces(affected_ids):
        changed = []
        for face_id in affected_ids:
            face = faces_a[face_id]
            if any(mapping[v] < 0 for v in face):
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
        for v, count in adj_a[a].items():
            mapped = int(mapping[v])
            if mapped >= 0 and adj_b[b].get(mapped, 0) != count:
                return False
        for w, count in adj_b[b].items():
            inverse = int(reverse[w])
            if inverse >= 0 and adj_a[a].get(inverse, 0) != count:
                return False
        return True

    def frame():
        # Explora primeiro fronteiras conectadas aos vertices ja mapeados.
        # Ordem de escolha nao influencia completude, so o desempenho.
        def rank(a):
            mapped_neighbors = sum(int(mapping[v] >= 0) for v in adj_a[a])
            free = sum(int(reverse[b] < 0) for b in candidates[a])
            return (0 if mapped_neighbors else 1, free, -mapped_neighbors, -len(adj_a[a]), a)
        a = min(remaining, key=rank)
        bs = [b for b in candidates[a] if compatible(a, b)]
        return {'a': a, 'bs': bs, 'pos': 0, 'b': None, 'faces': None}

    stack = [frame()]
    while stack:
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
    if mesh_identity(mesh_a) == mesh_identity(mesh_b):
        return True
    if mesh_counts(mesh_a) != mesh_counts(mesh_b):
        return False
    qa = quantized_vertices(mesh_a)
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


def number_of_shape_keys(obj):
    keys = getattr(obj.data, 'shape_keys', None)
    return len(keys.key_blocks) if keys else 0


def preference(obj):
    """Ordenacao: mais modifiers > mais shape keys > nome."""
    return (-len(obj.modifiers), -number_of_shape_keys(obj), obj.name.casefold(), obj.name)


def plan_removals(objects):
    """Toda a analise termina ANTES de iniciar a exclusao.

    Retorna (planos[(mantido, removidos...)], total_meshes).
    """
    meshes = [ob for ob in objects if ob.type == 'MESH' and ob.data is not None]
    by_counts = defaultdict(list)
    for ob in meshes:
        by_counts[mesh_counts(ob.data)].append(ob)
    sig_cache = {}
    equivalent_cache = {}
    planned = []
    for group in by_counts.values():
        if len(group) < 2:
            continue
        by_signature = defaultdict(list)
        for ob in group:
            ptr = mesh_identity(ob.data)  # bpy proxies podem ter id() instavel.
            if ptr not in sig_cache:
                sig_cache[ptr] = coarse_signature(ob.data)
            by_signature[sig_cache[ptr]].append(ob)
        for matches in by_signature.values():
            if len(matches) < 2:
                continue
            ranked = sorted(matches, key=preference)
            clusters = []
            for ob in ranked:
                for cluster in clusters:
                    leader = cluster[0]
                    pair = tuple(sorted((mesh_identity(ob.data), mesh_identity(leader.data))))
                    if pair not in equivalent_cache:
                        equivalent_cache[pair] = meshes_equal(ob.data, leader.data)
                    if equivalent_cache[pair]:
                        cluster.append(ob)
                        break
                else:
                    clusters.append([ob])
            for cluster in clusters:
                if len(cluster) > 1:
                    planned.append((cluster[0], cluster[1:]))
    # Opcionalmente valida dados ligados: exclusao parcial seria indesejavel.
    for keep, dropped in planned:
        for ob in dropped:
            if getattr(ob, 'library', None) is not None:
                raise RuntimeError('Objeto ligado de biblioteca externa: ' + ob.name + '. Nenhuma exclusao executada.')
    return planned, len(meshes)


def run_blender():
    if bpy is None:
        raise RuntimeError('Execute no Blender. Os testes offline so validam o algoritmo.')
    if bpy.context.mode != 'OBJECT':
        raise RuntimeError('Entre no Object Mode antes de executar. Nenhuma exclusao realizada.')
    print('\n[T7-Dedup] Iniciando analise de todos os objetos MESH do .blend...')
    all_objects = list(bpy.data.objects)
    planned, total = plan_removals(all_objects)
    remove_count = sum(len(group) for _, group in planned)
    print(f'[T7-Dedup] Analisados: {total} objetos MESH. Grupos duplicados: {len(planned)}. A remover: {remove_count}.')
    # Sem confirmacao: a exclusao foi expressamente solicitada pelo proprietario.
    removed = 0
    for keep, group in planned:
        print(f'[MANTER] {keep.name} | modifiers={len(keep.modifiers)}, shape_keys={number_of_shape_keys(keep)}')
        for ob in group:
            name = ob.name
            bpy.data.objects.remove(ob, do_unlink=True)
            removed += 1
            print(f'  [REMOVIDO] {name}')
    print(f'[T7-Dedup] Concluido: {removed} objetos removidos em memoria. Salve o .blend manualmente, se estiver correto.')
    return removed


if __name__ == '__main__':
    run_blender()
