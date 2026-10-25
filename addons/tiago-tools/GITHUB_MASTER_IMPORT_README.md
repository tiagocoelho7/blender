# Tiago Tools — importacao documental no monorepositorio Blender

**Natureza:** importacao e cadeia de custodia, nao desenvolvimento.
**Destino:** `tiagocoelho7/blender/addons/tiago-tools/`.
**Versao principal congelada:** `v1.0.2` — **HOLD PARA PRODUCAO**.

## Conteudo e preservacao

- `handoff/ORIGINAL_MASTER_E3_CONSOLIDADO_2026-10-20.zip`: copia binaria
  integral do ZIP E3 recebido do proprietario, sem modificacoes.
- `handoff/E3/`: todos os **23 membros** desse ZIP, preservados byte a byte,
  inclusive 2 relatorios ZIP completos dos Auditores A/B, 3 ZIPs de codigo
  (v1.0.0, v1.0.1, v1.0.2), manifestos, logs, pareceres, diff e plano E4.
- `snapshots/v1.0.2/`: copia legivel dos **5 arquivos** contidos no ZIP
  instalavel v1.0.2, sem alteracoes. **Nao e uma versao ativa**.
- `AGENTS.md`, este README, `GITHUB_MASTER_IMPORT_MANIFEST.json` e
  `GITHUB_MASTER_IMPORT_VERIFY.py` sao arquivos **novos de infraestrutura**.

## Custodia conferida

- ZIP E3 recebido SHA-256: `42b8f6e3a503ba6b4a9b32203a5a56a1eff79d1792f383d4484ca2d4ab2bbf6b`.
- Manifesto E3: 22/22 arquivos com hashes iguais; o manifesto e o 23o
  arquivo, excluido da propria listagem para evitar autorreferencia.
- Auditor A E3 ZIP: `c55ae03ccaed596573ddec6850db14949816fb9794c2cd7a4f862821f39293ce`.
- Auditor B E3 ZIP: `30d7fa2806ebaf73d1f5897ab7eb83ca49a06d3fa7af449ad87548a9b8f7cd54`.
- Candidata `tiago-tools-1.0.2.zip`: `28cba4b80e058e726f1e802498588d80278897918a4163b554c6697edda5bad2`.
- Baseline 1.0.1: `30dc30ec35dc2b8444366bf4faea40dbe4106176cdea68b2604ae0750f191548`.
- Historico 1.0.0: `18f727f6cb58297e94ac14af4c656b7ae631e56f71076aaf68bf9bb863406e99`.
- Candidata interna `SHA256SUMS.txt`: 4/4 conteudos conferidos.
- Esta importacao esta limitada aos materiais **E3 consolidados**;
  bundles historicos externos E0/E1/E2 nao foram incluidos integralmente.

## Gates e limites

Os Auditores A e B produziram GO **estatico com restricoes** para a
passagem E3 -> E4, nao GO de producao. O parecer do Master E3 autoriza
exclusivamente preparar E4; **executar E4 real depende de autorizacao**.

Risco prioritario: falha combinada de setter/`remove()` no Safe Sub pode
deixar um modifier parcialmente configurado; eficacia do Undo real ainda
nao foi testada. Hipoteses de registro e efeitos pos-excecao foram
simuladas, nao demonstradas no Blender 5.0.0/5.2.2 LTS.

**Nenhum Blender real, bpy real, fixture `.blend`, teste E4, patch, merge
ou release e autorizado por esta importacao.**

## Historico complementar opcional (nao necessario para a E3)

Para uma futura rodada especifica de arquivamento historico E0-E2,
buscar os arquivos originais:
- `TIAGO_TOOLS_1_0_1_MASTER_E0_CUSTODIA_2026-10-20.zip`
- `TIAGO_TOOLS_V1_0_1_MASTER_E1_CONSOLIDADO_2026-10-20.zip`
- `TIAGO_TOOLS_V1_0_2_MASTER_E2_ENTREGA_2026-10-20.zip`
Sao extras; NAO substituem nem alteram a candidata E3 congelada.

## Verificacao da importacao

Na raiz do checkout, depois da extracao do pacote preparado:

```bash
python3 addons/tiago-tools/GITHUB_MASTER_IMPORT_VERIFY.py
```

Apenas le dados/hashes. O retorno PASS significa integridade documental,
e nao validade funcional Blender. A importacao deve ocorrer por branch e
Pull Request, sem merge automatico e sem publicar tags/releases.
