# E4 — Plano de testes nativos no Windows (PENDENTE de autorização)

**NÃO executar ainda sem autorização expressa do proprietário.** Apenas cenas leves/copias descartáveis. Não abrir nem salvar arquivos `.blend` de produção, nem instalar no perfil habitual.

## Preparação
1. Manter as instalações de Blender 5.0.0 e 5.2.2 independentes. Criar perfis temporários (preferivelmente outro usuário Windows ou sandbox/perfil realmente isolado) e verificar manualmente as pastas de extensões/configuração; `--factory-startup` isoladamente NÃO garante isolamento de disco.
2. Copiar `06_CANDIDATA_E_BASELINES/tiago-tools-1.0.2.zip` para uma pasta de teste; comparar SHA-256 com `28cba4b80e058e726f1e802498588d80278897918a4163b554c6697edda5bad2`.
3. Registrar `blender.exe --version`, `bpy.app.version_string`, `bpy.app.build_hash`, `sys.version`, Windows, caminhos dos perfis, stdout/stderr, exit codes. Verificar também se os dois executáveis possuem CLI de extensão esperado.

## Primeira passagem segura (somente validacao, não instala)
Em PowerShell, **após substituir os três caminhos pelas cópias de teste**:

```powershell
$blender50 = 'C:\CAMINHO\Blender50\blender.exe'
$blender52 = 'C:\CAMINHO\Blender522\blender.exe'
$zip = 'C:\TESTE_E4\tiago-tools-1.0.2.zip'
Get-FileHash -Algorithm SHA256 $zip
& $blender50 --version
& $blender50 --command extension validate $zip
$exit50 = $LASTEXITCODE
& $blender52 --version
& $blender52 --command extension validate $zip
$exit52 = $LASTEXITCODE
"validate50=$exit50 validate52=$exit52"
```

**Validação de metadados não equivale a instalação nem prova função.** Guardar stdout/stderr e códigos de saída. Em caso de CLI não suportada/falha, parar, guardar evidências, não instalar forçando.

## Matriz de testes funcionais isolados — ambos os Blender

| ID | Teste | Resultado esperado |
|---|---|---|
| E4-01 | CLI extension validate 5.0/5.2.2 | Exit 0 e metadados aceitos, ou registrar falha exata |
| E4-02 | Instalar/em cada perfil temporário, habilitar-desabilitar duas vezes, reiniciar | Sem classe/painel fantasma ou erro de RNA |
| E4-03 | Atualizar 1.0.1→1.0.2 em segundo perfil TEMPORÁRIO | Uma instância do painel, três classes previstas, sem interferir em outros addons |
| E4-04 | GUI `N > Tiago` | Todos / Visíveis / Adicionar desativado; sem Random Colors |
| E4-05 | Safe Sub na mesh simples | Um novo SUBSURF; 6 campos: `show_viewport=False`, `show_render=False`, `levels=0`, `render_levels=0`, `show_in_editmode=False`, `show_on_cage=False`; preexistentes intactos |
| E4-06 | Repetir Safe Sub e usar Undo via UI | Dois novos SUBSURF em dois cliques; Undo reverte conforme operação; registrar resultado real |
| E4-07 | Safe Sub em contexto não mesh/sem ativo/linked de fixture própria | Sem alteração indevida, relatórios e status compreensíveis |
| E4-08 | Batch Todos/Visíveis em scene pequena | Todos inclui collection oculta; Visíveis filtra por `LayerCollection.is_visible`, dedup objects; `show_render` intacto |
| E4-09 | Batch best-effort e Undo em fixture limitada | Falha de um objeto não corrompe os demais; registrar parcial e Undo |
| E4-10 | Teste pós-restart e salvar/reabrir apenas fixture | Estado preservado, sem supor que arquivo salvo em 5.2 abra no 5.0 |
| E4-11 | Avaliação de mesh incremental, começando mínima | Ausência de pico desproporcional/erro em caso de teste pequeno |

## Risco prioritário e não forçável

A dupla falha setter + `modifiers.remove()` (M-E3-01) **não foi reproduzida no bpy real**. Não instalar addons externos, não monkeypatchar RNA C nativa, não realizar injeções destrutivas e não gerar travamentos para simulá-la. Caso não possa ser causada de modo seguro, marcar `NÃO PROVOCADO — RISCO RESIDUAL` e avaliar separadamente se o risco é aceitável. Caso ocorra naturalmente, medir efeito e fazer Undo via interação do operador (não `execute()` isolado). Se Undo falhar, HOLD.

## Evidência e gate

Registrar resultado em `07_MODELO_RESULTADOS_E4.csv` com nome/hash de fixture, versão/build, comando exato, status, stdout/stderr, screenshots, estados RNA antes/depois/undo. Pare em falha de instalação, classe órfã real, alteração de mod preexistente, flags inesperadas, discrepância de batch, Undo quebrado ou travamento em fixture mínima. Remeter resultados ao Master para revisão independente após testes; **GO PRODUÇÃO não resulta automaticamente de um teste PASS**.
