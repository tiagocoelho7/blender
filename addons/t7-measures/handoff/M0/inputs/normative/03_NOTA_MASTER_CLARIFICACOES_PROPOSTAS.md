# T7 Measures - Nota Master de interpretacao/fechamento PROPOSTA (R8.1)

**NAO e revisao que sobrescreve a R8 ou o adendo candidato R8.1.** Estes itens precisam ser explicitados no handoff e ratificados junto com os limites pertinentes. Se for alterado algoritmo, certificado ou nivel de risco, deve voltar a A/B. Nenhum valor numerico e ratificado por esta nota.

## I. Estados e ausencia de nominal

| Caso | Estado/publicacao sugerida |
|---|---|
| Certificado `[d_L,d_U]` valido, nominal nao disponivel, `0<d_L<=d_U` | Publicar faixa outward e estado positivo certificado; **sem** numero pontual ou `~` |
| Certificado `[0,d_U]` valido, nominal ausente | INDETERMINADO_COM_FAIXA, nunca contato inferido |
| Nominal **fornecido** NaN/Infinity/invalido/fora de faixa | Recusa fechada, limpar resultado atual, SEM_FAIXA, nao reaproveitar ultimo valor |
| Bounds obrigatorios ausentes, nao finitos ou invertidos | INDETERMINADO_SEM_FAIXA/recusa conforme causa, sem numero |
| Nominal valido e certificate da mesma grandeza, gates correspondentes PASS | Se permitido, exibir nominal aproximado + faixa conforme R8/R8.1 |
| Gate TOTAL de **area P** falha, gate geometrico P PASS, distancia independente certificada | Omitir area nominal, permitir apenas faixa da distancia certificada |

`A ausencia` na R8.1 deve ser entendida como ausencia de *dados obrigatorios*, nao como nominal opcional ausente. Caso de nominal contraditorio deve falhar fechado, jamais ser convertido para opcional ausente. Nenhum valor rounded 0 prova contato: resultado positivo pequeno deve manter intervalo aberto ao zero conforme limites internos.

## II. Contexto A/B

- O que deve permanecer entre A e B: `EDIT_MESH`, janela/area proprietaria, Scene, objeto, datablock, identidade/geracao, transformacao e unidade relevantes; snapshots byte a byte comparados a cada etapa requerida.
- O que pode mudar entre A e B: **tipo de selecao VERT/EDGE/FACE**, desde que cada captura selecione exatamente uma entidade permitida, cada clique seja validado e a geometria do snapshot permaneça consistente. Caso contrario V-F e E-F seriam artificialmente impossiveis.
- Mudanca de geracao, objeto, contexto ou dados entre A/B invalida e limpa o resultado anterior. UI de areas nao proprietarias nao mostra captura ativa. `Novo A` substitui sessoes anteriores sob politica de slot unico, se esta for ratificada.

## III. QA numerico e seguranca

- HALF_EVEN sobre valor **efetivamente representado/certificado**, nao empate decimal imaginado. `p=0` empate exato, `p=3` float(q/2) acima, `p=6` abaixo. Exercitar `nextafter`, bits binary32 + zero/subnormal, arredondamento outward, extremo finito e tipo invalido.
- Nao copiar o helper didatico para addon. Seu `outward_bounds` falha para finitos de grande magnitude; `mixed_face_state` nao valida bool exato ou aridade. Testar que todas as falhas sao tratadas e nao causam publicacao de numero incorreto.
- Normalizar `-0.000` apenas na camada de apresentacao, sem falsificar certificados de contato. Nomes `POSITIVO_CERTIFICADO`, `POSITIVO_CERTIFICADO_COM_FAIXA`, `POSITIVO_COM_FAIXA` requerem um mapeamento univoco entre enum interno, certificados e UI.
- Revisar QA Q19 para indicar `p=3` na expectativa sobre o lado de cima; integrar Q23 numa tabela Markdown valida e acrescentar Q24 para troca permitida de VERT para FACE.
- Testar model state com owner estruturado, identidade da sessao, geracao, ultimo resultado e falhas posteriores que devem limpar o valor.

## IV. Memoria e fases

- Work M0 pode, **se explicitamente autorizado**, estudar/formalizar estimadores conservadores de pico e recusas seguras usando somente fixtures offline. Nao exigir prova final de RSS **antes de iniciar este estudo**.
- M1/M2 ou qualquer consulta real em malhas dependem de limitacao efetiva/recusa fail-closed e auditoria; benchmarks e integracao em Blender 5.2.2 LTS sob autorizacao separada.
- A sugestao `128 MiB` e um budget agregado de projeto por instancia e slot; nao representa RSS garantido nem foi aprovado pelo proprietario.

## V. Proveniencia e limites

- A auditagem foi independente quanto aos **pareceres atuais da R8.1**, mas os originais preservam atribuicoes historicas A/B de R6 e R7. Nao dizer `cegamento historico completo`.
- Sem homologacao Blender, sem prova no-write do addon, sem teste de runtime ou da API especifica. D04=P somente como principio; parametros sao decisao futura.
