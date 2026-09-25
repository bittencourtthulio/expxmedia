# Banco de imagens — Pexels foto e vídeo (capacidade `banco_imagens`)

Dois usos hoje, em dois projetos, com filosofias opostas de escolha:

- **Vídeo (b-roll)** em `Instragram-Videos/pipeline/broll.py` (199 linhas): quem escreve o plano
  escolhe o **termo**; o script pega **o primeiro resultado** que serve, sem olho.
- **Foto (ilustração de slide)** em `Instagram-Carrosseis/galeria/_galeria.py:444-698`: o script
  filtra e baixa **candidatas**; um agente (`galerista`) abre cada imagem e **aprova ou recusa por
  escrito**; só aprovada entra na arte.

O contrato do núcleo (`ExpxMedia/docs/contrato/CONTRATO-capacidades.md:43`, `:160`, `:167-168`)
unifica os dois em `banco_imagens` (provedor `pexels`, variável `PEXELS_API_KEY`).

## Contrato de entrada

### Vídeo — `broll.py`

- CLI (`Instragram-Videos/pipeline/broll.py:31-38`):
  - `--plano`: imprime a fala por frase (de `alignment.json`) com instante e as regras; cria
    `brolls_plano.json` esqueleto se não existir (`:103-130`);
  - `--buscar "termo"`: lista até 8 resultados (id, duração, resolução, autor, url) (`:67-72`);
  - execução sem flag: lê `brolls_plano.json` = `[{t, dur, termo, por_que}]` (`:132-136`);
  - `--nenhum`: registra corte sem b-roll (`:96-99`);
  - `--baixar "termo" --saida broll/x.mp4`: modo do formato recriado, sem `corte.json` (`:74-91`).
- Requisição (`Instragram-Videos/pipeline/broll.py:29`, `:46-54`): `GET https://api.pexels.com/videos/search`
  com `query`, `per_page=12`, `orientation=portrait` (padrão; `landscape` como segunda tentativa, `:165`),
  cabeçalho `Authorization: <chave>`, timeout 40 s.
- Termo **em inglês, descrevendo a imagem, não o conceito** (`:122-123`;
  `Instragram-Videos/.claude/rules/curadoria-corte.md:277-280`).
- Regras de colocação cobradas antes de baixar (`Instragram-Videos/pipeline/broll.py:137-155`,
  constantes em `Instragram-Videos/pipeline/lib.py:142-148`):

| regra | valor | fonte |
|---|---|---|
| duração de cada inserção | 2,0–4,0 s | `lib.py:144` |
| abertura livre (rosto) | 3,0 s | `lib.py:145` |
| fecho livre | 2,0 s | `lib.py:146` |
| respiro entre inserções | 4,0 s | `lib.py:147` |
| teto do total | 40 % da duração do corte | `lib.py:148` |
| termo obrigatório | — | `broll.py:148-149` |

### Foto — `galeria.py ilustracoes`

- CLI (`Instagram-Carrosseis/galeria/_galeria.py:1911-1925`): `--buscar TERMO --para "<slide e o
  que precisa mostrar>" [--limite 3] [--orientacao portrait|landscape|square]`; `--aprovar|--recusar
  ARQ --porque "..." [--sem-fundo --modelo-rembg u2netp]`; `--esquecer ARQ`; `--status`; listagem
  sem flag. `--gerar` (OpenRouter) é outra capacidade (`imagem_ia`).
- Requisição (`Instagram-Carrosseis/galeria/_galeria.py:447`, `:476-487`): `GET
  https://api.pexels.com/v1/search` com `query`, `per_page = max(3, min(limite × 3, 30))` (pede o
  triplo porque o descarte filtra depois), `orientation`; cabeçalhos `Authorization` e `User-Agent` de
  navegador (`:94`); timeout 30 s.
- `--para` com ≥ 20 caracteres, senão recusa a busca (`:540-541`); orientação em
  `ORIENTACOES` (`:452`, `:542-543`).
- Julgamento: `--porque` com ≥ `JULGAMENTO_MINIMO` = 40 caracteres (`:453`, `:600-602`).

### Chave

- Vídeos: `.env` por regex `(?im)^\s*pexels[_-]?api[_-]?key\s*=` (aceita `PEXELS_API_KEY`,
  `PEXELS_APIKEY`, minúsculas), senão ambiente `PEXELS_API_KEY` ou `PEXELS_KEY`
  (`Instragram-Videos/pipeline/lib.py:181-192`).
- Carrosseis: ambiente `PEXELS_APIKEY` ou linha `PEXELS_APIKEY=` do `.env` da raiz, exato
  (`Instagram-Carrosseis/galeria/_galeria.py:463-473`); testado em
  `Instagram-Carrosseis/tests/test_galeria.py:723-728`.
- Núcleo: `PEXELS_API_KEY` e nenhum nome antigo (`CONTRATO-capacidades.md:160`, `:167-168`).
- As duas implementações recusam imprimir o valor (`lib.py:182`; `_galeria.py:464`).

## Contrato de saída

### Vídeo

- Escolha do arquivo (`Instragram-Videos/pipeline/broll.py:57-64`): arquivos com `link` e altura
  ≥ 720; prefere vertical (altura ≥ largura); o de altura mais próxima de 1920 (`H`).
- Filtro de duração: clipe ≥ `dur + 1` s (`:163`, `:165`). Escolhe **`achados[0]`** (`:169`).
- Download para `broll/NN_src.mp4` (timeout 180 s, reaproveita se existir) (`:171-174`); corta o
  **miolo** do clipe (sobra dividida por 2 — "o primeiro segundo costuma ser a câmera entrando em
  regime", `:175-176`); normaliza para `scale+crop 1080×1920, fps 30, yuv420p, sem áudio, libx264
  medium crf 20` em `broll/NN.mp4` (`:177-185`).
- `brolls.json` = `{insercoes:[{t, dur, arquivo, termo, por_que, pexels_id, pagina, autor, autor_url,
  licenca}], total_s, fracao_do_corte}` (`:186-197`). Licença gravada como texto: "Pexels License —
  uso comercial permitido, atribuição não exigida" (`:191`).
- `--baixar` grava esquema **diferente** (sem `t`/`dur`, `url` em vez de `pagina`, sem `autor_url`,
  `licenca: "Pexels"`), baixa o primeiro resultado sem filtro de duração e **sem normalizar**
  (`:77-90`).
- Composição: `compose_cut.py` sobrepõe cada inserção em tela cheia com `enable=between(t,…)`
  (`Instragram-Videos/pipeline/compose_cut.py:51-57`).

### Foto

- Descarte automático antes de baixar (`Instagram-Carrosseis/galeria/_galeria.py:515-525`): id já
  fichado (qualquer status); lado curto < `LADO_MINIMO_ILUSTRACAO` = 1200 px (`:449`); `alt` casando
  `PESSOA_NA_FOTO` (`:456`: man, woman, person, people, face, portrait, team, crowd…).
- URL de download: `src.original?auto=compress&cs=tinysrgb&fit=clip&w=1620&h=1620`
  (`LADO_MAXIMO_ILUSTRACAO` = 1620, `:451`, `:528-533`); fallback `large2x`/`large`.
- Pós-download (`:557-571`): reabre com Pillow, `thumbnail(1620)`, grava JPEG qualidade 88;
  descarta se não abrir ou se lado curto < `LADO_MINIMO_NO_DISCO` = 1000 px (`:450`).
- Arquivo `galeria/ilustracoes/candidatas/pexels-<id>-<slug do termo, 24>.jpg` (`:554-556`).
- Ficha em `galeria/ilustracoes/ilustracoes.json`: `arquivo, status=candidata, fonte=pexels, pexels_id,
  busca, para, alt, autor, autor_url, url, licenca="Pexels", w, h, orientacao, baixada_em`
  (`:573-575`). Estados `candidata | aprovada | recusada` (`:454`).
- Retorno da busca: `{busca, para, candidatas, descartadas[{pexels_id, alt, motivo}], proximo}` (`:579-582`).
- `--aprovar`: move para `galeria/ilustracoes/`, grava `julgamento`, `julgada_em`; com `--sem-fundo`
  passa por `rembg` (padrão `u2netp`) e vira `-sem-fundo.png` (`:585-636`). `--recusar` apaga o arquivo e
  **mantém a ficha**, para a mesma foto não voltar (`:587`, `:629-630`); recusada não pode ser aprovada
  depois (`:598-599`). Retorna `referencia: ilustracao:<arquivo>` e `credito` (`:634-636`).
- Uso na arte: `ilustracao:<arquivo>` só resolve se ficha `aprovada` e arquivo presente
  (`:651-667`); no máximo `ILUSTRACOES_POR_PECA` = 1 por peça (`:448`, `:1091-1092`); slot com
  `pessoa: true` não aceita foto de banco (`:1079`).
- `validar_ilustracoes` reprova ficha sem arquivo, aprovada sem julgamento ≥ 40, aprovada Pexels sem
  `autor`+`url`, e arquivo na pasta sem ficha (`:677-698`).

## Limites e cotas

- Cota da API do Pexels: **NÃO DOCUMENTADO** no código de nenhum dos dois projetos. (Uma base anterior,
  `Instagram-Carrosseis/docs/galeria-processamento-imagem/base/08-pexels-api.md`, cita "200 req/h,
  20000 req/mês" da documentação pública, marcado como não conferido — não verificado aqui.)
- Cabeçalhos de cota (`X-Ratelimit-*`) não são lidos em nenhum dos dois: NÃO DOCUMENTADO.
- Paginação (`page`) não é usada: uma página por busca nos dois (`broll.py:47`; `_galeria.py:478`).
- Vídeo: 12 por busca, 1 escolhido; até 2 buscas por inserção (portrait, depois landscape)
  (`broll.py:46`, `:163-165`).
- Foto: 3 a 30 por busca; no máximo `--limite` (padrão 3) baixadas (`_galeria.py:478`, `:548-549`,
  `:1915`).
- Uma foto de banco por peça (`_galeria.py:448`); teto de 40 % de b-roll por corte (`lib.py:148`).
- Licença: vídeos gravam "uso comercial permitido, atribuição não exigida" (`broll.py:191`); o
  motivo da escolha do Pexels é licença comercial para postar na conta do cliente
  (`broll.py:4-8`; `curadoria-corte.md:260-265`). Pela regra do template, foto de banco **não** é
  asset `neutro` e não sobe para a galeria compartilhada (`CONTRATO-template.md:231-233`).

## Erros conhecidos e tratamento

| Erro | Vídeo (`broll.py`) | Foto (`_galeria.py`) |
|---|---|---|
| Chave ausente | `sys.exit` com link para gerar a chave (`lib.py:191-192`) | `SystemExit` (`:471-472`) |
| HTTP 401 | genérico: `sys.exit` com código e 300 caracteres do corpo (`:52-54`) | `SystemExit` específico, sem imprimir a chave (`:483-484`) |
| HTTP 403/429 (cota/bloqueio) | mesmo `sys.exit` genérico — sem distinção | `Bloqueio` → saída 2, "nada é descartado", rodada para (`:95`, `:485-486`, `:2005-2006`, `:2028-2029`); comando manda **não insistir na hora** (`Instagram-Carrosseis/.claude/commands/galeria-ilustrar.md:19`) |
| Erro de rede (`URLError`, timeout) | não tratado (exceção crua) | não tratado na busca; download via `baixar()` só trata 403/429 (`:1656-1664`) |
| Termo sem resultado | `sys.exit` "troque o termo… em inglês"; **nunca buraco** (`:166-168`; `:79`) | lista `candidatas` vazia + `descartadas` com motivo |
| Plano fora das regras | `sys.exit` listando todos os problemas (`:154-155`) | — |
| `brolls.json` ausente na montagem | aviso, segue sem b-roll (`compose_cut.py:24-26`); o `stop-gate` do agente `corte` reprova (`Instragram-Videos/.claude/hooks/corte/stop-gate.sh:39-41`) | — |
| b-roll invadindo abertura/fecho ou > 40 % | bloqueado no plano e de novo no `stop-gate.sh:42-53` | — |
| ffmpeg falha ao normalizar | `sys.exit` com 600 caracteres do stderr (`:184-185`) | — |
| Arquivo baixado menor que o prometido | — | descartado (`:568-571`) |
| Arquivo não abre como imagem | — | descartado (`:564-567`) |
| Arquivo posto à mão / ficha editada à mão | — | `validar` reprova (`:694-697`); `--aprovar` sem ficha recusa (`:594-597`) |
| `broll.py` sem `corte.json` e sem `--baixar` | `sys.exit` orientando `--baixar` (`:93-94`); coberto por `Instragram-Videos/tests/test_skill_recriado.py:38-40` | — |

## Riscos para a nossa implementação

1. **Dois modelos de escolha incompatíveis.** O vídeo escolhe `achados[0]` sem ninguém olhar
   (`broll.py:169`); a foto tem dois validadores (script + agente que abre a imagem) e o porquê gravado
   (`Instagram-Carrosseis/.claude/rules/galeria.md:69-78`). Unificar pelo lado do vídeo perde a trava
   de contexto que impede "enfeite"; unificar pelo lado da foto exige extrair quadro(s) do vídeo para
   julgar, o que não existe hoje (NÃO DOCUMENTADO). A capacidade deve expor `candidatas` + `julgar` e
   deixar o gate ao pack.
2. **Filtro de pessoa é regra de marca, não do banco.** "A pessoa das nossas artes é sempre o
   Thulio" (`_galeria.py:455-456`, `Instagram-Carrosseis/.claude/commands/galeria-ilustrar.md:29-30`) → no núcleo vira regra ligada aos
   `porta_vozes` da Alma e ao slot `pessoa` do template. O b-roll de vídeo **não** tem esse filtro.
   A regex é em inglês e só olha o `alt` (vídeos do Pexels não têm `alt` equivalente usado no código:
   NÃO DOCUMENTADO).
3. **Tratamento de cota divergente.** Só a foto trata 403/429 como "bloqueio, pare e não descarte";
   o vídeo morre com mensagem genérica no meio de um plano de várias inserções (arquivos já baixados
   ficam, mas `brolls.json` não é gravado). No núcleo, 429 tem que ser erro tipado único.
4. **Nomes de variável divergentes** (`PEXELS_APIKEY` × regex frouxa × `PEXELS_API_KEY`). O contrato
   manda só `PEXELS_API_KEY`; a migração precisa renomear no `.env` dos dois projetos ou a capacidade
   aparece desligada.
5. **Esquemas de registro divergentes**: `brolls.json` (dois esquemas no mesmo script:
   `broll.py:87-88` × `:186-192`) e `ilustracoes.json`. O núcleo precisa de um registro de proveniência
   único (id, autor, url, licença, termo, contexto/`para`, julgamento) por asset — é o que responde
   "de onde veio o que foi ao ar" (`broll.py:6-8`).
6. **Parâmetros de qualidade são específicos do destino**: 1080×1920 e altura ≥ 720 no vídeo;
   1200/1000/1620 px calibrados para slide 1080×1350 na foto (`_galeria.py:449-451`). Têm que vir do
   formato da peça, não ser constante do provedor.
7. **Heurísticas de busca são conhecimento, não código**: termo em inglês descrevendo a imagem;
   `per_page` triplicado para sobreviver ao descarte; miolo do clipe; fallback de orientação. Perder
   isso piora silenciosamente o resultado.
8. **Regras de colocação do b-roll (3 s/2 s/2–4 s/4 s/40 %) derivam da retenção de corte de fala**
   (`lib.py:142-143`) — são do formato "reel de corte", não do banco de imagens. Devem ir para o
   template/pack.
9. **Uso real de b-roll em cortes é zero** (16 de 16 cortes sem inserção, medido nos
   `Instragram-Videos/videos/yt-*/brolls.json`). O caminho de vídeo tem pouca validação em produção;
   o de foto tem testes (`Instagram-Carrosseis/tests/test_galeria.py:584-700`). Priorizar o
   comportamento testado.
10. `rembg` no `--aprovar --sem-fundo` usa `u2netp` por padrão (`_galeria.py:585`, `:1922`), mas a
    regra da galeria diz que `u2netp` "deixa fantasma de fundo" e o padrão de tratamento é `u2net`
    (`Instagram-Carrosseis/.claude/rules/galeria.md:63`). Divergência a decidir; não é do Pexels,
    mas viaja junto na extração.
11. Papéis/escopo: buscar é da rotina principal e de `geradores`; julgar é do `galerista`, que é
    bloqueado de ir ao Pexels por hook (`Instagram-Carrosseis/.claude/hooks/galerista/pre-bash-guard.sh:18`;
    `Instagram-Carrosseis/.claude/agents/galerista.md:139`). O núcleo precisa preservar a separação
    "quem busca não aprova".

## Fonte

- `Instragram-Videos/pipeline/broll.py:1-199` (lido inteiro); `lib.py:142-148`, `:181-192`;
  `compose_cut.py:23-26`, `:43-57`.
- `Instragram-Videos/.claude/rules/curadoria-corte.md:260-280`;
  `Instragram-Videos/.claude/commands/new-video-youtube-cut.md:92-100`;
  `Instragram-Videos/.claude/skills/gerar-reel-corte/SKILL.md:150-160`;
  `Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:104-106`;
  `Instragram-Videos/.claude/hooks/corte/stop-gate.sh:39-53`;
  `Instragram-Videos/tests/test_skill_recriado.py:38-40`.
- `Instagram-Carrosseis/galeria/_galeria.py:85-112`, `:444-698`, `:1079-1093`, `:1656-1664`,
  `:1905-1925`, `:1985-2030`.
- `Instagram-Carrosseis/.claude/rules/galeria.md:60-85`; `.claude/agents/galerista.md:100-140`;
  `.claude/commands/galeria-ilustrar.md:1-53`; `.claude/hooks/galerista/pre-bash-guard.sh`;
  `.claude/hooks/copywriter/pre-bash-guard.sh:13`; `tests/test_galeria.py:584-728`;
  `docs/galeria-processamento-imagem/base/08-pexels-api.md` (base anterior, só para cruzar).
- `ExpxMedia/docs/contrato/CONTRATO-capacidades.md:43`, `:160`, `:167-168`;
  `ExpxMedia/docs/contrato/CONTRATO-template.md:231-233`.
- Artefatos: `Instragram-Videos/videos/yt-*/brolls.json`;
  `Instagram-Carrosseis/galeria/ilustracoes/ilustracoes.json` (7 fichas: 5 aprovadas, 2 candidatas).
- `git log`: `Instragram-Videos` só `cc1e39d Initial commit`; `Instagram-Carrosseis` sem commit
  com "pexels" ou "ilustra" na mensagem.
