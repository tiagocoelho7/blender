# HANDOFF T7 STATUE MOVER — v1.2.21
**Data de consolidação:** 23/10/2026  
**Novo chat:** continuidade técnica do add-on **T7 Statue Mover**.  
**Status correto:** **v1.2.21-candidate CONGELADA; GO COM CONDIÇÕES em Blender/bpy 5.0.0 headless; GUI Windows e gates interativos PENDENTES; sem homologação irrestrita de produção.**  
**Não confundir:** T7 Pré-Remesh é OUTRO projeto, separado.

---

## 0. Como ler este handoff e o que pode ser afirmado

Este handoff é um ponto de transferência de continuidade, **não** uma decisão de lançamento e **não** uma nova auditoria runtime. O ZIP atual foi montado em 23/10/2026 a partir de pacotes locais previamente produzidos e verificados. A candidata dentro dele é byte a byte a candidata congelada v1.2.21. O relatório de runtime v1.2.21 foi recebido anteriormente neste chat e seu conteúdo é detalhadamente transcrito/condensado em `04_AUDITORIA_ATUAL/RESUMO_RUNTIME_v1.2.21.md`, **mas o ZIP bruto de evidências de runtime v1.2.21 e o relatório MD original não puderam ser transportados como bytes para este handoff**. Eles foram anexados pelo usuário no chat original em 06/10/2026 com os nomes listados no inventário. Não chamar esse resumo de relatório original nem de substituto das provas brutas. O novo chat deve solicitar/anexar os dois arquivos originais se for revisar a cadeia de custódia ou realizar homologação probatória final. Os pacotes históricos de entrada de runtime da v1.2.21, as três auditorias cheap e o runtime anterior v1.2.20 estão preservados no bundle de entrada da rodada.

Este é **exclusivamente um plugin/add-on pessoal de Blender**, usado no fluxo legítimo de engenharia e produção de estátuas. Engenharia de software, QA, debugging, auditoria defensiva, preservação de dados e testes em arquivos próprios. **Não** é atividade de cybersecurity ofensiva, pentest, invasão, bypass de autenticação, malware, obtenção de credenciais, nem comprometimento de terceiros.

Distinguir sempre: **FATO confirmado no registro existente**, **RELATO do auditor**, **PENDÊNCIA de interface** e **REQUISITO FUTURO**. Não inferir aprovação de produção do GO condicionado.

---

## 1. O que é o add-on e qual seu contrato

**Função:** mover/rotacionar/escalar proporcionalmente todas as partes gerenciadas de uma estátua a partir do corpo final/guia selecionado, preservando uma base/referência católica fixa e a possibilidade de restaurar o estado original.

Fluxo pretendido (nomes reais dos operadores inspecionados no ZIP):

1. Abrir um `.blend` de trabalho **já salvo em disco**; fazer backup.
2. Opcionalmente importar a base/referência externa por **Importar Base + Referência**; escolher o guia, base fixa e coleção-alvo no painel `T7 Statue Mover` (barra lateral `N`).
3. **Preparar Estátua** (`t7sm.prepare`): congelar estado, geometria, modifiers e identidade; desligar temporariamente os modifiers de viewport pesados nos alvos gerenciados.
4. Manipular **apenas o guia** com G, R e S **uniforme e positivo**.
5. **Aplicar Transformação** (`t7sm.apply_displacement`) para propagar a mesma diferença world a todas as peças gerenciadas.
6. **Finalizar / Manter Nova Posição** (`t7sm.finalize`) OU **Restaurar Estado Inicial** (`t7sm.restore_initial`). Há ainda **Restaurar Modifiers** (`t7sm.restore_modifiers`).

Matemática:

```text
D = world_atual_guia @ inverse(world_original_guia)
novo_world_de_cada_alvo = D @ world_original_do_alvo
```

Requisitos não negociáveis:

- A **base/referência fixa nunca acompanha** a transformação do corpo/guia.
- Objetos de collections **hidden/disabled/excluded** que pertençam ao conjunto gerenciado também precisam acompanhar, sem depender de `matrix_world` stale.
- Sem novo parenting permanente para fazer a propagação.
- Escala G/R/S do guia **uniforme, estritamente positiva**. Rejeitar escala zero/negativa, não-uniforme, shear material, transformações semanticamente ambíguas.
- Preservar parents, `matrix_parent_inverse`, delta transforms, e BONE parenting, se suportados pelo contrato validado.
- `Restore` exato, modifiers readback/verificação e cleanup fail-closed.
- `Finalize` só elimina snapshot/backup depois de validar geometria, estado aplicado e influências dinâmicas.
- Se operação não puder ser provada segura, **CANCELLED** mantendo snapshot e possibilidade de Restore.
- Estado da restauração externo/ligado ao arquivo salvo deve sobreviver a `Prepare -> fechar sem salvar -> reabrir` para `.blend` previamente salvo; sem gravar indevidamente arquivo de trabalho.
- Não mover nem alterar silenciosamente objetos do usuário fora do escopo gerenciado.
- Sem autoexecução remota, subprocessos ou atuação em terceiros.

### Tipos de geometria e segurança

O add-on possui fingerprints/sentinelas para Mesh, Curve/Surface, Text, Armature, Lattice, Meta e PointCloud; geometria não suportada é recusada; objetos explicitamente sem geometria podem seguir allowlist. Impedir que constraints, Action, NLA, drivers/animators externos e influência de pose-bones tornem Apply/Finalize falsamente bem-sucedidos. Se a Armature for relevante, política conservadora para constraints de pose-bones.

### Base/referência

Planejado um `.blend` católico fixo de cerca de 12 MB em `assets/base_reference.blend`, **mas o asset real NÃO acompanha a candidata v1.2.21**; o ZIP inclui apenas `assets/README.txt`. Alternativa atual: configuração de caminho externo. O import considera `T7_BASE_REFERENCIA`, tagging, seleção desabilitada, `hide_render` na master, uma Scene de origem e avisos de unidades divergentes sem mudar unidades. Cleanup precisa realizar preflight de todos os IDs de Library e recusar remoção que atingiria conteúdo do usuário ou overrides não tagueados.

---

## 2. Ambiente, identidade exata e releases

- **Target estrito:** Blender **5.0.0**. A implementação falha fechado em versões diferentes. Não presumir Blender 5.2.2 LTS por ter outros projetos de migração.
- **Sistema de uso:** Blender GUI no Windows. Auditor runtime foi executado em **bpy 5.0.0 headless**, Python 3.11.15, build `a37564c4df7a` (registrado pelo auditor).
- **Candidata atual:** `t7-statue-mover-v1.2.21-candidate.zip`.
- **SHA-256 do ZIP:** `7d475cfb4453ba3abc34da32a56274e4c296caebb614a78363c4c63edd57044f`.
- **SHA-256 de `t7_statue_mover/__init__.py`:** `3678a278f60afa84850167618d0e659359948cfc913e671101195963fc7c8a7e`.
- **Add-on `bl_info.version`:** `(1, 2, 21)`.
- **Snapshot schema:** `6` (`_t7sm_snapshot_v6`).
- **Cadeia de origem:** v1.2.20 ZIP SHA `79692b6a128e19707b949ff14d0d4ffc3fe99d554ccaee5d4b647e6060ec3161`; v1.2.19 `bfac2b2bf1712c3a7c7a3613189477b5d8845f8c5f97b75c6b56ceb25e9e0552`; v1.2.18 `864567cbaa2deef5d7a66afb61b3f58f827c2a8c949f3c47c3efd24784262b88`.
- **v1.2.21 permanece congelada.** Qualquer mudança de byte na candidata exige outra versão (v1.2.22 ou superior), novo hash e novo gate proporcional.
- O proprietário retém a palavra final para **releases**, alterações destrutivas, merges e testes de produção.

### Como localizar o add-on para instalar

Neste handoff:

```text
02_CANDIDATA_CONGELADA/t7-statue-mover-v1.2.21-candidate.zip
```

No antigo Claude runtime bundle:

```text
T7-Statue-Mover-v1.2.21-CLAUDE-RUNTIME-BUNDLE/
  01_CANDIDATE/t7-statue-mover-v1.2.21-candidate.zip
```

**Instalar o ZIP interior `candidate.zip` diretamente; não instalar o ZIP de auditoria/handoff.** Em Blender 5.0.0: Edit -> Preferences -> Get Extensions -> Install from Disk (ou fluxo equivalente do mesmo build). Confirmar que a entrada `T7 Statue Mover` habilita e que o painel aparece. Não extrair/reempacotar a candidata original para usar em auditoria.

---

## 3. Arquitetura que não deve ser simplificada sem contraprova

- Deltas `D @ M0`, world calculado a partir de canais, parent chain, `matrix_basis`, `matrix_parent_inverse`, BONE parenting e deltas; não confiar cegamente no depsgraph de objetos excluídos.
- Writer usa `obj.matrix_basis = local`, seguido de refinamento Euler **double** para os seis orders quando aplicável, sem trocar o writer de Quaternion/Axis-Angle.
- Projeção polar `_double_nearest_proper_rotation` corrige não-ortogonalidade float32 (~1e-7) antes de decomposição Euler; shear material permanece bloqueado.
- `EULER_SINGULAR_THRESHOLD = 1e-12` em v1.2.21 para evitar descarte prematuro de informação perto de ±90°.
- `set_channel_world_matrix()` captura `rotation_euler` **ANTES** de `obj.matrix_basis = local` e passa os canais originais à escolha de branches equivalentes; garante continuidade percebida pelo usuário na faixa testada.
- Equivalência de erro de reconstrução entre branches: `1e-12`; exatidão geométrica tem prioridade sobre proximidade de Euler.
- Gate Apply/FInalize: verificar estado real dos canais/raw readback antes de certificar `applied_world_valid`, sem deixar drift de escala ser mascarado.
- Orçamento atual de world sanity (N-53/N-51/N-48): **erro vetorial de coluna 2,5e-5**, **erro de comprimento 1e-5** e **cap por componente baseado no esperado com piso 0,0125**. Todos os gates simultâneos. A translação N-42 permanece verificada pelo vetor 3D com orçamento ULP do esperado.
- Snapshot schema 6 com baseline externo e `disk_state` separado; não migrar ou mexer em sidecars sem auditoria transacional.
- `Finalize` exige world readback e geometria/sentinelas corretos; `Restore` deve reconstituir transforms e modifiers exatos.
- `register()` respeita `_RestrictData`, sem percorrer `bpy.data.scenes` cedo demais.

**Cuidado especial:** não corrigir falso reject simplesmente relaxando tolerância numérica. No histórico isso reabriu falsos accepts graves (N-38/N-39/N-40/N-47/N-48/N-51).

---

## 4. Histórico cronológico de achados (resumido, porém completo até o gate atual)

| Versão | Resultado / achado que explica a próxima versão |
|---|---|
| v1.2.0 | HOLD: identidade fraca de snapshot, modifiers, multi-Scene, Restore/cleanup. |
| v1.2.1 | HOLD R-01 a R-04: sentinel de origin/geometry, IDs importados, identidade, parent metadata. |
| v1.2.2 | HOLD H-01: Finalize sem geometry sentinel suficiente. |
| v1.2.3 | HOLD H-02: rename em `.blend` não salvo podia conflitar com baseline. |
| v1.2.4 | HOLD H-03: filepath não vazio aceito sem verificar arquivo existente em disco. |
| v1.2.5 | Runtime bpy 5.0.0 abriu N-01..N-19 (recovery, geometry, referências, multi-Scene, import/cleanup). |
| v1.2.6 | CRITICAL N-22: `CLASSES` não definido; N-20/N-21/N-23/N-24. |
| v1.2.7 | HOLD N-25 HIGH: Library cleanup poderia atingir IDs linked de usuário. |
| v1.2.8 | Runtime HOLD N-26 CRITICAL (`_RestrictData`), N-27/28/29 HIGH. |
| v1.2.9 | Runtime HOLD N-30 CRITICAL (aridade Prepare), N-31/32 HIGH (ancestors/animation). |
| v1.2.10 | Runtime HOLD N-36 HIGH (roundoff world), N-35 MEDIUM (bone scanner). |
| v1.2.11 | Cheap HOLD N-38 HIGH: tradução grande inflava tolerância linear. |
| v1.2.12 | Cheap HOLD N-39 HIGH: sibling grande na mesma matriz inflava budget. |
| v1.2.13 | Cheap HOLD N-40 HIGH: sibling mascarava outro componente já grande. |
| v1.2.14 | Runtime HOLD N-42 HIGH: parent rotacionado + grandes translações, falso reject. |
| v1.2.15 | Runtime HOLD N-45 HIGH: `matrix_basis` recomposta de canais Euler float32 (near-gimbal); N-46 LOW caso anisotrópico extremo. |
| v1.2.16 | Cheap HOLD N-47 HIGH: sanity coarse podia certificar world errado. |
| v1.2.17 | Cheap HOLD N-48 HIGH: coluna enorme mascarava componente pequeno. |
| v1.2.18 | Runtime HOLD N-50 HIGH: setter matrix->Euler errava perto de gimbal; N-51 MEDIUM admitia drift unitário de escala. |
| v1.2.19 | Runtime HOLD **N-54 HIGH** (filho com matriz ~1e-7 não ortogonal amplificada no gimbal), **N-53 HIGH** (budget vetor 1e-5 recusava hierarquia correta); N-52 MEDIUM branch distante. |
| v1.2.20 | Runtime HOLD **N-56 HIGH**: threshold singular 1e-6 descartava detalhe legítimo perto de ±90°, em world grande; N-52 persistia MEDIUM. N-54/N-53/N-51 fecharam. |
| **v1.2.21** | Cheap audits **GO COM CONDIÇÕES**; runtime Blender/bpy 5.0.0 **GO COM CONDIÇÕES**, **0 HIGH/CRITICAL**. **N-56 e N-52 fechados** nas baterias. GUI real segue pendente; N-57 LOW novo. |

### Detalhes críticos das três últimas transições

**v1.2.19 -> v1.2.20**: polar Newton double `X <- (X + inverse(X)^T)/2` resolve N-54; separa tolerância direcional `2.5e-5` de comprimento `1e-5` para N-53 sem reabrir N-51; branch empate em `1e-12` ajuda N-52. Porém threshold singular `1e-6` cria N-56 falso reject em janela ~89.99994..89.99997° com world grande, por cap N-48 absoluto, apesar de world independente correto.

**v1.2.20 -> v1.2.21**: somente dois ajustes funcionais estreitos: (1) singular threshold `1e-6 -> 1e-12`; (2) preservar continuidade Euler referenciada ao canal **pré-setter**, em vez de pós-setter. Sem mudar schema, D@M0, budgets, polar, referência ou persistence.

**v1.2.21 runtime**: auditor executou Blender/bpy 5.0.0 exato e relatou fechar N-56 96/96 com window 0/1152, e N-52 0/300 swaps + 0/360 ±3 voltas, mantendo produção p52 59/59 e N-51 t62/t63. Ver matriz detalhada em `04_AUDITORIA_ATUAL/RESUMO_RUNTIME_v1.2.21.md`.

---

## 5. Estado exato dos gates em 23/10/2026

| Gate | Status |
|---|---|
| Candidata congelada + hashes + manifesto interno | **PASS**, artefato verificado neste handoff |
| Cheap audits v1.2.21 independentes | **GO COM CONDIÇÕES**, três pareceres contidos no bundle de runtime de entrada |
| Runtime Blender/bpy 5.0.0 headless v1.2.21 | **GO COM CONDIÇÕES** no relatório recebido; não é production GO |
| N-56 (singular) | **FECHADO** no runtime; p59 96/96, window 0/1152 |
| N-52 (Euler branch) | **FECHADO** nos casos de usuário testados; 0/300 + 0/360 |
| N-54 (polar/parent/gimbal) | **FECHADO** em runtime herdado da v1.2.20 e revalidado v1.2.21 |
| N-53 (hierarquia/falso reject) | **FECHADO**: produção p52 59/59 |
| N-51 (+1.1e-5/+2e-5 drift de escala) | **FECHADO**: controles rejeitados t62/t63 |
| Restore/Finalize/reopen nos probes headless | **PASS** nos casos documentados, não equivale a GUI |
| **GUI real Windows / click / event loop / undo interativo** | **PENDENTE** |
| **Drivers/auto-exec via interação GUI** | **PENDENTE** |
| **Homologação de produção / release** | **NÃO AUTORIZADA/sem GO absoluto** |
| Aviso **DIM-300** | **REQUISITO FUTURO, NÃO IMPLEMENTADO na v1.2.21** |

### LOW / INFO conhecidos, não ocultar

- **N-57 LOW novo:** preservação de múltiplas voltas Euler expõe quantização float32 em rotação muito grande de canais, cerca de >=100 voltas completas armazenadas. Com R no guia alguns Apply recusam; sempre fail-closed com Restore exato. Em até 30 voltas ensaiadas passou; não corrigir sem prioridade concreta e nova avaliação N-52.
- **N-55x LOW pré-existente:** ruído float32 em colunas world muito grandes (~65536 / ~4e5) pode disparar cap absoluto N-48 e gerar falso reject, sem certificar pose errada.
- **N-46 LOW:** transformações com escala extremamente anisotrópica sob parent rotacionado podem falhar fechado; não prometer suporte universal para escalas extremas.
- **N-49 INFO:** pequena janela direcional tolerada em componente grande; controle de risco documentado e historicamente observado.
- **Gates de teste legados**: t01 continha 9 falhas de injetor H03-D obsoleto; t50 1 caso N-46 LOW; t61 11 divergências já existentes no baseline e discutidas (inclui expectativas obsoletas e janela N-49). Não descrever a bateria como "100% todos os testes PASS" ignorando esses casos; comparar baseline e justificativas.

---

## 6. Gate imediato recomendado: GUI REAL WINDOWS BLENDER 5.0.0

**Objetivo**: última validação operacional na interface, em cópias de trabalho e sem alterar a candidata original.

**Antes do início**: verificar a versão 5.0.0 exatamente, hash da candidata, fazer backup do `.blend`, trabalhar em cópia de arquivo e selecionar coleções/objetos apropriados. Se o usuário tiver versões diferentes do add-on instaladas, desabilitar/uninstall com cautela antes de instalar a candidata correta. Verificar eventual sidecar de snapshot e não apagar arquivos de recovery sem prova de propriedade.

**Roteiro GUI mínimo (ordem recomendada):**

1. **Instalação**: instalar `t7-statue-mover-v1.2.21-candidate.zip` diretamente; habilitar, desabilitar, habilitar novamente; abrir barra `N` e conferir `T7 Statue Mover`; coletar screenshot/console de eventuais erros. Confirmar unregister/registro sem `_RestrictData`/duplicação.
2. **Cenário trivial de ensaio em cópia**: um guia, duas peças gerenciadas e uma base/referência NÃO gerenciada. Preparar, deslocar guia com `G`, rotacionar `R`, reduzir uniformemente com `S 0.5`; Aplicar; verificar world/posição de cada alvo e imobilidade da base; Finalizar. Não confundir scale do guia com magnitude absoluta do corpo; a mudança é **relativa**.
3. **Restore**: repetir em outra cópia, Preparar -> G/R/S -> Aplicar -> Restaurar Estado Inicial. Conferir transforms, origem, modifiers viewport/render e geometria antes/depois; snapshot removido só após sucesso.
4. **Hidden/Excluded**: ensaio de coleção escondida/excluída; alvo gerenciado deve acompanhar apesar de não visível; referência fica fixa.
5. **Parents/BONE/deltas**: ensaio conservador em arquivo de teste, sem constraints/animators proibidos; preservar relações e restaurar.
6. **Persistência**: em arquivo previamente salvo, Prepare -> fechar sem salvar -> reabrir; demonstrar caminho de recuperação/Restore de acordo com o fluxo documentado. Separadamente testar Apply -> Save -> Reopen -> Finalize e/ou Restore.
7. **Falhas esperadas**: tentar guia não-uniforme/negativo/zero ou transformação inválida em cópias; recusa clara, sem perda de snapshot nem modificação de peça externa. Constraints/animation relevantes devem falhar fechado.
8. **Undo e event loop**: verificar que operações clicadas pela UI, undo/redo em momentos relevantes, handlers `save_post`, reload de arquivo, cancelar e fechar Blender não criam falso estado `FINISHED`, desregistro incorreto, crash ou drift. Exigir observação explícita de limitações de Undo em vez de inferir equivalência automática.
9. **Drivers/auto-exec GUI**: checar com fixtures próprios controlados os casos que headless deixou pendentes; não rodar código de procedência desconhecida. Se não forem executados, manter PENDENTE no gate.
10. **Registro**: salvar screenshots, console, build/OS, hashes, `.blend` sintéticos (não arquivos reais sigilosos), sequência exata, resultado observado/esperado, vídeo opcional e classificação GO/HOLD/INCONCLUSIVO.

**Critério**: qualquer HIGH/CRITICAL reproduzível ou alteração não intencional do arquivo => **HOLD** da v1.2.21. Se os testes GUI reais passam, emitir parecer **GO de produção condicionado à aceitação explícita dos LOW/INFO e do escopo não testado**, submetido ao proprietário. O novo chat NÃO deve declarar release automático.

---

## 7. Requisito futuro DIM-300 (não implementar dentro da candidata congelada)

Em conversa anterior, o proprietário solicitou:

**DIM-300:** avisar quando qualquer dimensão da estátua gerenciada passar de **300 metros**, sem bloquear a operação. Sugestão aprovada de comportamento: medir **bounding box combinado de todos os objetos gerenciados** em world-space, excluindo base/referência fixa; converter usando `scene.unit_settings.scale_length`; identificar eixo e dimensão. Checar em **Preparar Estátua** e **Aplicar Transformação**, incluindo estátua que só ficou gigante após `S`. Não alterar geometria, preço ou outros sistemas; apenas warning.

Exemplo textual desejado:

```text
AVISO: DIMENSÃO INCOMUM DA ESTÁTUA
Eixo Z: aproximadamente 412,6 metros.
Verifique escala/unidades antes de continuar.
```

**Política de versão**: guardar na fila após homologar ou encerrar gate GUI v1.2.21. Introduzir como nova candidata (provável v1.2.22, se não houver outra intervenção), sob autorização do proprietário, com unit tests de bounds e unidades e pelo menos teste runtime. Não reaproveitar o nome v1.2.21 para patch.

**Projeto distinto**: a ideia de add-on **T7 Pré-Remesh** (estimador de voxel vs polígonos) foi conscientemente deslocada para **outro chat/projeto**. Não introduzir no Statue Mover nem confundir features.

---

## 8. Política de desenvolvedor/auditores/artefatos

- Este chat era o chat principal de trabalho do T7 Statue Mover; no novo chat, continuar como coordenador técnico **sem supor autorização para executar alterações adicionais**.
- Manter candidatas, hashes e testes congelados. A palavra final de release/merge/alterações destrutivas permanece com o proprietário.
- Testes baratos independentes primeiro; runtime Blender exato quando exigido. Claude foi o executor que dispõe do ambiente Blender/bpy 5.0.0 real nas rodadas anteriores. Usar Work pesado como último recurso e apenas quando autorizado.
- Primeira passagem cega de cada auditor antes de abrir histórico e precheck; salvar `FIRST_PASS_SEALED.md` e SHA; depois evidências e contraprovas.
- Bundle completo e **autossuficiente** para próxima etapa contendo candidata, prompts, SHA-256, relatório, diffs, logs/harnesses e README/manifesto de uso. Limite de upload para auditor Claude: **30 MB**. Este handoff não é uma nova candidata e não altera qualquer original.
- Todo novo audit bundle deve conter `00_PROMPT_PARA_PROXIMO_CHAT.md`, preferencialmente cópia em `99_NEXT_CHAT/`, e o **mesmo prompt entregue separadamente como `.md`**.
- Identidade do add-on no prompt: projeto pessoal Blender de QA/engenharia defensiva; não cibersegurança ofensiva.
- Gatilho de HOLD: qualquer HIGH/CRITICAL reproduzível. LOW/INFO precisam ser documentados, nunca silenciosamente eliminados.
- Não declarar GO absoluto baseado só em cheap/static ou headless; não validar GUI/Undo sem GUI.
- Ao reproduzir testes, respeitar originais e trabalhar em cópias descartáveis. Provas brutas prevalecem sobre narrativa em caso de discrepância.

---

## 9. Evidências incluídas e limites de disponibilidade

| Caminho | Conteúdo / procedência |
|---|---|
| `02_CANDIDATA_CONGELADA/t7-statue-mover-v1.2.21-candidate.zip` | Candidata original e congelada (SHA exato acima) |
| `03_BUNDLE_ORIGINAL_ENTRADA_RUNTIME/T7-Statue-Mover-v1.2.21-CLAUDE-RUNTIME-BUNDLE.zip` | Bundle efetivamente enviado ao auditor runtime 5.0.0 em 06/10/2026; contém candidata, três cheap audits, relatório/evidências runtime v1.2.20, baseline, diff, prompt |
| `04_AUDITORIA_ATUAL/RESUMO_RUNTIME_v1.2.21.md` | Sumário fiel do relatório recebido (NÃO cópia original byte a byte) |
| `04_AUDITORIA_ATUAL/INVENTARIO_FONTES_NAO_EMPACOTADAS.md` | Localizadores/nome/tamanho dos **originais** v1.2.21 runtime report e evidence ZIP recebidos no chat; não foram transportados para este ZIP |
| `05_HISTORICO_REFERENCIAS/` | Candidatas congeladas v1.2.18–v1.2.20, diff v1.2.20->v1.2.21, Audit Delta v1.2.21, precheck developer, handoff anterior v1.2.19 |
| `06_PLANO_GUI/GUI_GATE_BLENDER_5.0.0.md` | Procedimento reproduzível para prova GUI real |
| `00_PROMPT_PARA_PROXIMO_CHAT.md` e `99_NEXT_CHAT/` | Prompt de abertura completo (byte-identical) |
| `MANIFEST.sha256` | Hashes somente dos arquivos transportados, sem hash auto-referente |

**Lacuna explícita**: no chat original o usuário anexou `T7-Statue-Mover-v1.2.21-CLAUDE-RUNTIME-AUDIT-EVIDENCE.zip` (**2.538.042 bytes**, conforme metadados de anexo) e `T7-Statue-Mover-v1.2.21-CLAUDE-RUNTIME-AUDIT-REPORT.md` (**10.757 bytes**), ambos auditados anteriormente na conversa; o relatório anterior atestou manifesto de evidência 167/167 e first-pass seal `c46ec89a2c4bdc33515a0ceabd9e4452108ec0264d0489a80daa5b4fc9786657`. O gerador de arquivos deste handoff, porém, não teve acesso aos **bytes** dos dois originais e não inventou cópias. Para auditoria de custódia independente no novo chat, anexá-los é obrigatório. Para planejamento e gate GUI, o sumário e as fontes de entrada bastam.

---

## 10. Instrução inicial ao sucessor

1. Ler `00_PROMPT_PARA_PROXIMO_CHAT.md`, o presente handoff e a matriz resumida do runtime v1.2.21.
2. Conferir `MANIFEST.sha256`, CRC e SHA da candidata. **Não alterar a v1.2.21**.
3. Tratar o próximo trabalho como **fechamento do gate GUI em Blender 5.0.0**, não como nova rodada de implementação.
4. Pedir ao proprietário o resultado de testes já feitos na GUI, **se houver**; não repetir perguntas respondidas. Se ainda não houve, instruir em apenas 2–3 passos de cada vez, com fixtures/cópias seguras.
5. Se houver blocker, registrar HOLD preciso e exigir autorização explícita antes de construir v1.2.22. Se tudo passou, consolidar parecer técnico GO condicionado, deixando o release para o proprietário.
6. Manter DIM-300 na fila separada e Pré-Remesh em projeto distinto.

---

## 11. Resumo de uma frase

**T7 Statue Mover v1.2.21 está congelada e passou a auditoria matemática/runtime headless Blender 5.0.0 com GO COM CONDIÇÕES; N-56/N-52/N-54/N-53/N-51 fecharam, persistem LOW documentados e falta verificar GUI Windows / event loop / Undo / autoexec antes de liberar produção; DIM-300 continua planejado para próxima versão, nunca para esta candidata.**
