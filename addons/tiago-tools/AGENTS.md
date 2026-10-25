# AGENTS — Tiago Tools (escopo exclusivo deste addon)

Esta pasta pertence ao monorepositorio publico `tiagocoelho7/blender`.
Este arquivo foi acrescentado pelo **GitHub Master** para infraestrutura;
nao integra o pacote historico E3 nem altera a cadeia de custodia.

## Status e autoridade
- Versao congelada: **Tiago Tools 1.0.2**, GO apenas estatico para
  preparacao de testes E4 isolados, **HOLD PARA PRODUCAO**.
- E4 em Blender 5.0.0 / 5.2.2 LTS: **pendente de autorizacao expressa**.
- O GitHub Master cuida de repositorios/branches/PRs. O Master Tecnico
  decide tarefas, testes e gates. O proprietario autoriza releases e
  testes reais. O executor nao aprova sua propria candidata.

## Escopo e proibicoes
- Antes de trabalhar, ler `GITHUB_MASTER_IMPORT_README.md`,
  `handoff/E3/00_LEIA_ME_MASTER.md` e `handoff/E3/01_PARECER_MASTER_E3.md`.
- Nao alterar/remover/renomear **nada** em `handoff/`, nem os cinco
  arquivos em `snapshots/v1.0.2/`, sem novo gate de custodia.
- Nao executar Blender real, importar bpy real, abrir arquivos .blend,
  instalar addon, executar testes E4, editar outros addons, iniciar patch,
  efetuar merge ou publicar release sem autorizacao especifica.
- Tarefas futuras autorizadas: usar branch propria e novos diretorios de
  trabalho, fora do snapshot imutavel; revisao tecnica independente.
- Testes sintéticos sao apenas evidencias de QA, nao prova runtime.

## Referencias
- Verificador de custodia (somente leitura):
  `python3 addons/tiago-tools/GITHUB_MASTER_IMPORT_VERIFY.py` executado
  da raiz do repositorio, sem Blender ou bibliotecas externas.
- O ZIP instalavel original fica em
  `handoff/E3/06_CANDIDATA_E_BASELINES/tiago-tools-1.0.2.zip`.
