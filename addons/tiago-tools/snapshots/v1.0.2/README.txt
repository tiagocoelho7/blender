TIAGO TOOLS 1.0.2 - CANDIDATA EM AUDITORIA
=================

Blender declarado: minimo 5.0.0; testes reais em 5.0.0 e 5.2.2 PENDENTES.
NAO instalar em perfil de producao antes da reauditoria e aprovacao do usuario.
Extensao atualizada a partir de Tiago Tools 1.0.1.

FERRAMENTAS
-----------
1. Desativar Modifiers (Viewport)
   - Todos: todos os objetos da Scene, incluindo collections ocultas.
   - Visiveis: objetos vinculados a collections visiveis no View Layer atual.
   - Nao altera o estado/visibilidade das collections.
   - So modifica modifier.show_viewport; nao modifica modifier.show_render.

2. Safe Sub
   - Adiciona um modifier Subdivision Surface ao objeto MESH ativo.
   - Cria o modifier e imediatamente define:
       show_viewport = False
       show_render = False
       levels = 0
       render_levels = 0
       show_in_editmode = False
       show_on_cage = False
   - Cria o modifier no objeto ativo; nao afeta outros objetos.

CORRECOES DE SEGURANCA NA 1.0.2
--------------------------------
- Safe Sub: se a configuracao falhar apos criar o modifier, tenta remover
  apenas o modifier criado. Se a remocao falhar, avisa e retorna FINISHED
  para permitir Undo do operador; confira o estado e use Ctrl+Z.
- Registro de classes: reverte registros parciais; falhas de remocao ficam
  registradas para permitir nova tentativa de unregister().
- Manifesto: schema_version fixo do formato 1.0.0; version do addon 1.0.2.

REMOVIDO NA 1.0.1
----------------
- 'Pintar cores aleatorias' foi totalmente removido (operador, painel,
  funcoes auxiliares e import random).
- Para cores distintas de exibicao sem alterar materiais: no 3D Viewport,
  abra o menu Shading (seta ao lado do icone Solid), selecione Color Type > Random.

ATUALIZAR DE 1.0.1 APOS APROVACAO
------------------
1. Salve seu trabalho.
2. Edit > Preferences > Extensions.
3. Desative/remova apenas 'Tiago Tools' 1.0.1 (nao 'Tiago Global Scripts').
4. Pelo menu de Extensions escolha Install from Disk e selecione
   tiago-tools-1.0.2.zip.
5. Habilite 'Tiago Tools', se necessario.
6. Volte a 3D Viewport > N > aba Tiago > painel Tiago Tools.
7. Verifique que existem apenas as secoes 'Modifiers' e 'Subdivision'.
8. Se o painel antigo permanecer, reinicie o Blender para limpar o registro.

NAO E NECESSARIO salvar o Startup File so para atualizar esta extensao.

RECOMENDACAO DE TESTE
--------------------
Teste em uma copia descartavel do seu .blend antes de usar em arquivos reais:
- Modifiers/Todos: todos os modifiers no viewport devem ficar desligados.
- Modifiers/Visiveis: collections ocultas nao devem ser processadas.
- Safe Sub: com uma mesh ativa, cria Subdivision com viewport/render desligados.
- A ferramenta de cores aleatorias nao deve aparecer.

Esta candidata preserva os comportamentos de "Todos", "Visiveis" por
collections, desativacao best-effort, e Safe Sub com criacao por clique.
Nao e certificacao Blender real nem garantia de ausencia de picos de avaliacao.
