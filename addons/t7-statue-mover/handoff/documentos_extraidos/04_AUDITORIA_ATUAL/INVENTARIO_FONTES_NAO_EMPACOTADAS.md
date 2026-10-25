# INVENTÁRIO DAS FONTES v1.2.21 NÃO TRANSPORTADAS EM BYTES

Este handoff NÃO inclui, como bytes originais, os dois arquivos anexados pelo usuário no chat de origem em 06/10/2026:

1. `T7-Statue-Mover-v1.2.21-CLAUDE-RUNTIME-AUDIT-REPORT.md` — **10.757 bytes** pelo metadado de anexo. O texto foi lido na conversa e está fielmente condensado em `RESUMO_RUNTIME_v1.2.21.md`, mas este sumário é um **novo documento**, NÃO o relatório original e não preserva seu hash.
2. `T7-Statue-Mover-v1.2.21-CLAUDE-RUNTIME-AUDIT-EVIDENCE.zip` — **2.538.042 bytes** pelo metadado de anexo; inclui first-pass seal, scripts de probe, logs, matiz PASS/FAIL e ambiente. No chat de origem houve verificação relatada **167/167** no manifesto e selo `c46ec89a2c4bdc33515a0ceabd9e4452108ec0264d0489a80daa5b4fc9786657`, mas a transferência atual não teve acesso ao ZIP original para revalidar seus bytes.

**Motivo:** embora os arquivos sejam visíveis como anexos e constem nos metadados de Files, eles não estavam acessíveis ao gerador local deste pacote. Foi preferido declarar a lacuna em vez de inventar `sandbox:/` ou criar evidência forjada.

**Instrução ao novo chat:** se precisar revisar/homologar a cadeia final da auditoria v1.2.21, pedir esses dois arquivos e validá-los antes de qualquer declaração probatória. Não é necessário para simplesmente orientar o teste GUI em arquivo de ensaio.

O arquivo `T7-Statue-Mover-v1.2.21-CLAUDE-RUNTIME-BUNDLE.zip` **incluído** é o bundle de ENTRADA do runtime e contém as provas anteriores v1.2.20 e as cheap audits v1.2.21, não as provas de SAÍDA do runtime v1.2.21. Não confundir.
