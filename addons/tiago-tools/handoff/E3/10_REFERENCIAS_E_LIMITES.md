# Fontes oficiais consultadas — 20/10/2026

- Blender Manual 5.2, *How to Create Extensions*: https://docs.blender.org/manual/en/5.2/advanced/extensions/getting_started.html — explica o manifesto, ZIP, e `blender --command extension validate add-on-package.zip`.
- Blender Manual 5.2, *Extensions Command Line Arguments*: https://docs.blender.org/manual/en/5.2/advanced/command_line/extension_arguments.html — sintaxe `validate [SOURCE_PATH]` e gestão de extensão.
- Blender Python API, *Operators (bpy.ops)*: https://docs.blender.org/api/current/bpy.ops.html — status `FINISHED`/`CANCELLED`, ausência de histórico de Undo em cancelamento.
- Blender Python API, *Operator Type Flag Items*: https://docs.blender.org/api/current/bpy_types_enum_items/operator_type_flag_items.html — `UNDO` cria etapa quando operador retorna `FINISHED`.

**Limites:** consulta a documentação não é teste no executável 5.0.0/5.2.2. Não foi executado `bpy` real, validação CLI, GUI, Undo real, `.blend` persistente ou performance de mesh real nesta rodada. Testes dos auditores usaram `bpy` simulado, e as conclusões sobre efeitos pós-exceção são hipóteses de runtime, não bugs nativos provados.
