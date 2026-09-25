# Produção de carrossel e post único (fábrica, séries, geradores, registro)

Como uma peça estática sai do pedido até PNG registrado: índice de séries (`series/INDEX.json`), orquestrador de geração com estado derivado do disco (`fabrica.py`), geradores por série (várias famílias de motor), fluxo de copy → revisão → render → revisão visual, e registro em `estado/geracoes.jsonl`. É a origem do registro que o contrato de peça padroniza (`ExpxMedia/docs/contrato/CONTRATO-peca.md:1-20`).

## Contrato de entrada

**Entrada de série** em `series/INDEX.json` (`Instagram-Carrosseis/series/INDEX.json:2-4`, exemplo completo `:102-152`):

| Campo | Papel | Exemplo / fonte |
|---|---|---|
| `id`, `nome`, `apelidos[]` | resolução por nome falado | `INDEX.json:103-109` |
| `pasta`, `guia` | onde mora e o GUIA que manda na forma | `INDEX.json:110-111` |
| `status`, `formato` (`carrossel` \| `post único`), `slides` | nº de imagens que conta como "item pronto" | `INDEX.json:112-114` |
| `motor`, `requer[]`, `cuidado` | texto livre lido pelo agente antes de prometer | `INDEX.json:115-120` |
| `catalogo{arquivo, chave, titulo[]}` | lista de itens com `id` inteiro | `INDEX.json:121-128` |
| `saida{dir, imagens}` | glob (ou lista de globs alternativos) das imagens do item | `INDEX.json:129-132`, `INDEX.json:402-407` |
| `gerar{cwd, cmd[]}` com `{id}` | comando do gerador | `INDEX.json:133-140` |
| `listar`, `testes` | opcionais | `INDEX.json:141-148`, `INDEX.json:253-259` |
| `publicacao.registro` | JSON de envios ao Expx Flow (várias séries dividem o mesmo) | `INDEX.json:149-151` |
| `sob_demanda`, `vaga_fixa` | fora do rodízio e da regra de nota | `INDEX.json:673`, `INDEX.json:492` |

**Comandos** (`Instagram-Carrosseis/fabrica.py:8-23`): `status [série]`, `resolver "<texto>"`, `proximo`, `ultima`, `gerar <série> [--id N|--proximo|--auto] [--dry-run] [--mesmo-desativada] --gancho <tipo> --leitor "<...>" --cta <forma> [--teste <id>]`, `registrar`, `fila`, `desativar --motivo [--pela-rotina]`, `reativar`, `cursor --a-partir-de N --motivo [--fila-antiga-ate]`, `ajustes`, `registrar-ajuste --tipo --o-que --por-que --evidencia [--commit] [--forcar]`, `avaliar-series`, `decisao`, `decisoes`, `validar`. Todos com `--json` (`fabrica.py:592-593`).

**Copy por item**: escrita pelo agente `copywriter` no arquivo que o gerador lê (catálogo ou `copy/<slug>.json`) (`Instagram-Carrosseis/.claude/agents/copywriter.md:47-49`); em série de galeria, no formato do `galeria.renderizar` (`Instagram-Carrosseis/series/recriacoes/gerar_carrossel.py:43-45`, `series/como-se-eu-tivesse-5/gerar_carrossel.py:39-45`).

**Contratos JSON** (Draft 2020-12, `Instagram-Carrosseis/.claude/rules/contratos/contratos-fonte-de-verdade.md:7-9`): bloco raiz `publication{contract_version:1, content_type, block_id, default_automation_ref, automations{ref:{keywords[], mensagem}}}` é o único comum entre séries (`Instagram-Carrosseis/contratos/README.md:12-29`); `fonte-publicacao.schema.json` exige `contract_version, tipo (carrossel|post-unico|cta), colecao, block_id, itens[{id,nome,legenda}]`; `automacao.schema.json` exige `keywords[]≥1, mensagem`, `link_label ≤ 20`, `public_reply_text` obrigatório se `public_reply_enabled` (`contratos/automacao.schema.json`); payload `carrossel.schema.json` 2 a 20 slides com `image_url` URI, `scheduled_at` XOR `publish_now`, `automation` XOR `automation_id` (`contratos/carrossel.schema.json`); `post-unico.schema.json` análogo com 1 `image_url`.

## Contrato de saída

- Pasta do item: `<saida.dir>/<NNN>-<slug>/slide_N.png` (ou `post-N.png`, `slide-N.png` conforme a série) + `legenda.txt`; séries de galeria também gravam `_prancha.png` e `fontes.md` (`como-se-eu-tivesse-5/gerar_carrossel.py:38-64`) (`Instagram-Carrosseis/.claude/rules/geradores/geradores-padrao-serie.md:3-7`).
- Linha em `estado/geracoes.jsonl` (append) por geração, ok ou falha (`fabrica.py:269-278`):

```json
{"quando": "2026-09-24T21:22:46-03:00", "serie": "recriacoes", "id": 17, "titulo": "...", "tema": null,
 "pasta": "series/recriacoes/saida/017-...", "imagens": 8, "ok": true, "comando": "python3 gerar_carrossel.py --id 17",
 "origem": "fabrica.py gerar", "segundos": 57.5, "gancho_tipo": "processo", "leitor": "dev curioso por automação pessoal", "cta_forma": "salvar"}
```
  (exemplo real: `Instagram-Carrosseis/estado/geracoes.jsonl`, última linha em 24/09/2026). Em falha, `falha` com o motivo (`fabrica.py:324-328`).
- Estado derivado (nada guardado): `renderizados` = pasta `NNN-*` com ≥ `slides` imagens (`fabrica.py:116-130`); `publicados` = linhas com `http` 2xx no registro de publicação, com desambiguação por nome quando o registro é compartilhado (`fabrica.py:133-161`); `proximo_gerar`, `proximo_publicar`, `ultima_geracao`, `desempenho` (nota do placar) (`fabrica.py:198-219`).
- `fila` → `{ultima_serie, escolhida, repetiu_por_falta_de_opcao, fila[], fora_do_rodizio[{serie, motivo}]}` (`fabrica.py:222-252`).
- Marca de desativação: `series/<série>/DESATIVADA.md` com data, autor e como reativar; decisão registrada em `estado/decisoes.jsonl` (`fabrica.py:341-356`, `fabrica.py:461-468`).
- Ajustes: `editorial/ajustes.jsonl` com `estrutural`, `evidencia`, `commit`, `medir_a_partir_de`, `efeito` (`fabrica.py:405-411`).
- Códigos de saída: `validar` 1 com problema; `gerar` 1 se não `ok` (`fabrica.py:631-635`).

Mapeamento para `peca.json` (o que já existe e onde): `pack` ≈ projeto; `serie` = `serie`; `template` = `layout`/`adotado_de` (só séries de galeria); `conteudo.gancho_tipo`/`cta_forma` = campos de `geracoes.jsonl`; `slides[]` = PNGs da pasta; `producao.segundos` = `segundos`; `status` = derivado (`renderizados`/`publicados`); `publicacoes` = registro `publicar/publicacoes-*.json`. `peca_id`, `criada_em`, `vaga`, `oferta`, `porta_voz`, `arquivos[].papel`: NÃO DOCUMENTADO na origem.

## Limites e cotas

| Item | Valor | Fonte |
|---|---|---|
| Formato fixo | 1080×1350 (4:5), nunca outra proporção sem pedido | `Instagram-Carrosseis/.claude/rules/convencoes-gerais.md:19-21`, `Instagram-Carrosseis/CLAUDE.md:188` |
| Slides por série | 8 (maioria), 4 (150 prompts), 10 (como-se-eu-tivesse-5), 1 (posts) | `INDEX.json:19`, `INDEX.json:337`, `INDEX.json:637`, `INDEX.json:436` |
| Carrossel no payload | 2 a 20 slides | `contratos/carrossel.schema.json` (`minItems 2`, `maxItems 20`) |
| Frescor da saída | toda imagem com `mtime ≥ início − 1 s` | `fabrica.py:286`, `fabrica.py:320` |
| Carência de mudança estrutural (`capa, layout, slides, template`) | 3 dias por série | `fabrica.py:45-49`, `fabrica.py:401`, `Instagram-Carrosseis/editorial/cadencia.json:22` |
| Nota mínima da série | 4,0 (0 a 10) | `fabrica.py:414-418`, `cadencia.json:6` |
| Desativação automática | 2 avaliações abaixo do mínimo, confiança média/alta, separadas por ≥ 3 dias | `fabrica.py:429-448`, `cadencia.json:32` |
| Reavaliação de série desativada pela rotina | após 14 dias, via teste de série | `fabrica.py:449-453`, `cadencia.json:33` |
| Rodízio | nunca repete a série da última geração, salvo única disponível | `fabrica.py:247-250` |
| Voltas copy ↔ revisão | no máximo 2; depois leva o impasse ao usuário | `Instagram-Carrosseis/.claude/skills/gerar-carrossel/SKILL.md:48-50` |
| Tempo por carrossel de 8 slides (galeria) | 51,6 s e 57,5 s | `estado/geracoes.jsonl` (24/09/2026) |
| Tipos de gancho aceitos no registro | `aplicacao, entrega, diagnostico, contraste, processo, decisao, oportunidade` | `fabrica.py:290` |
| Palavra do CTA (série claude-code) | até 14 caracteres, única na série, idêntica a `automation.keywords` | `series/claude-code-features/GUIA-CARROSSEL-CLAUDE-CODE.md:496` |

## Erros conhecidos e tratamento

- **Gerador rodado por fora do `fabrica.py`** ⇒ "último gerado" errado; corrigir com `fabrica.py registrar` (`gerar-carrossel/SKILL.md:63-65`, `:82`).
- **Gerador sai 0 mas não reescreve as imagens** ⇒ falha registrada "as imagens não foram reescritas nesta execução" (`fabrica.py:321-326`).
- **Várias revisões de copy com o mesmo prefixo numérico** ⇒ desempate pela pasta cujo nome casa com o título (`fabrica.py:102-113`).
- **Registros de publicação compartilhados com ids colidindo** (`publicacoes-features.json`) ⇒ só conta se `repositorio` bate com o nome do item (`fabrica.py:136-137`, `fabrica.py:143-155`).
- **Série resetada** (agendamentos apagados no painel) ⇒ `cursor` com `a_partir_de` e `fila_antiga_ate`; envio anterior ao reset não conta (`fabrica.py:156-159`, `fabrica.py:188-196`).
- **Duas numerações no catálogo** (`id` vs `dia_publicacao` em posts-lista) ⇒ gerador só por `--id` (`INDEX.json:442`).
- **Scripts destrutivos** (`build_features.py`, `_gerar*.py`, `atualizar_catalogo.py`, `_gerar_catalogo.py`) regravam catálogo e apagam edição manual ⇒ só com confirmação explícita (`Instagram-Carrosseis/CLAUDE.md:184-199`; `INDEX.json:120`, `:344`, `:599`).
- **Baseline de teste** (`001-minimax-m3`, `002-minimax-m27`) muda hash se regerado (`INDEX.json:221`).
- **Carrossel já publicado não se regenera**; mudança de gerador vale do próximo em diante, com cópia em `_publicados/` (`GUIA-CARROSSEL-CLAUDE-CODE.md:424-429`).
- **Legenda publicável** validada por regex no gerador claude-code: proíbe URL, domínio, "doc oficial", hashtag, menção a link, travessão; fallback limpa em vez de reprovar (`series/claude-code-features/gerar_carrossel.py:34-71`).
- **Acentuação**: catálogos gerados sem acento; dicionário `ACENTOS` corrige só palavras sem ambiguidade ("e/é", "esta/está" ficam para override manual) e corrompe inglês (`so`→`só`) (`series/claude-code-features/gerar_carrossel.py:70-105`, `GUIA-CARROSSEL-CLAUDE-CODE.md:502`). Já foi ao ar capa com "Ha 9 anos" e "mudanca" e 7 legendas sem acento (`Instagram-Carrosseis/editorial/revisao.md:23-25`).
- **Diagnóstico quebrava com série sem bloco `publication`** (`KeyError: 'publicacao'`) ⇒ pular série sem o bloco (`Instagram-Carrosseis/editorial/aprendizados.md:66-70`).
- **Automação de DM deduplicada por hash**: alterar um caractere do bloco duplica a automação (`INDEX.json:546`); `automation_id` nunca vai para o JSON de conteúdo (`contratos/README.md:31`).

## Riscos para a nossa implementação

- **O fluxo de qualidade é orquestração de agentes, não código**: `copywriter` (lê `editorial/**`, regras da daily, GUIA, 2–3 itens anteriores, escreve ≥ 3 capas e escolhe pelo teste da capa) → `revisor-editorial` passada 1 (checklist bloqueante) → `fabrica.py gerar` → `revisor-editorial` passada 2 (abre a prancha/imagens) (`copywriter.md:21-60`, `Instagram-Carrosseis/.claude/agents/revisor-editorial.md:19-49`, `gerar-carrossel/SKILL.md:39-73`). Um núcleo que só renderiza perde as duas revisões.
- **"Aprove só o que você viu"**: o revisor declara quando não abriu as imagens (`revisor-editorial.md:48-49`). Checagem visual final não é substituída pelas medições do render (a medição "não vê texto sobre forma ou desenho", `Instagram-Carrosseis/galeria/README.md:288`).
- **Enum de gancho e CTA diverge do contrato**: origem registra `aplicacao|entrega|diagnostico|contraste|processo|decisao|oportunidade` (`fabrica.py:290`) e `cta_forma` livre (`comente-palavra`, `salvar`, `link-bio`; `fabrica.py:590`); o contrato fixa `pergunta|contraste|numero|lista|historia|processo|polemica|outro` e `comentario|salvar|...` (`ExpxMedia/docs/contrato/CONTRATO-peca.md:172-173`). Migrar sem tabela de conversão quebra a análise "que tipo de gancho funciona" sobre o histórico.
- **Estado derivado do disco** (renderizado = pasta com N imagens) é o que mantém "o último gerado" verdadeiro sem banco. `peca.json` passa a ser fonte explícita; a checagem de frescor por `mtime` (`fabrica.py:286`) precisa continuar existindo, senão gerador que falha em silêncio conta como produzido.
- **Rodízio, carência e desativação por nota** são regras de produto, parametrizadas em `editorial/cadencia.json` (`fabrica.py:45-49`, `fabrica.py:414-418`). Extrair sem esses parâmetros vira gerador cego.
- **Motores heterogêneos**: Pillow puro (`publicar/gerar_slides.py`, carrossel-github), Playwright+HTML com encaixe próprio (claude-code, opencode, llms, 150 prompts, posts-lista, novidades-ia), CDP/browser-harness (MiniMax, GLM, expxdev), galeria (`recriacoes`, `como-se-eu-tivesse-5`) (`geradores-padrao-serie.md:8-22`, `INDEX.json:20`, `:64`, `:115`, `:217`, `:278`, `:389`, `:638`, `:674`). Só o motor da galeria tem validação medida; os demais têm checklists manuais por GUIA. O núcleo genérico deve partir do motor da galeria.
- **Duplicação conhecida não resolvida** (`ACENTOS`/`acentua`, `frases`, `prancha.py`, `resolver_automacao`) (`convencoes-gerais.md:33-38`).
- **Acoplamentos de marca/ambiente a virar dado da Alma ou `.env`:**
  - `AUTOR = "Thulio Bittencourt"`, `HANDLE = "@thuliobittencourt"` hardcoded nos geradores (`series/claude-code-features/gerar_carrossel.py:29-31`, `series/opencode-features/gerar_carrossel.py:32-33`, `series/novidades-ia/gerar_carrossel.py:53-54`, `series/carrossel-150-prompts-ia/gerar_carrossel.py:52-53`, `series/posts-lista/gerar_post_lista.py:41`, `series/post-proposito/gerar_post_proposito.py:42-43`) e no HTML do MiniMax (`series/carrossel-minimax-features/minimax_carousel/builder.py:30`);
  - CTA com palavra e oferta fixas ("Comente CLAUDE para receber o livro gratuitamente.", `series/claude-code-features/gerar_carrossel.py:33`); capa de livro com autor no alt (`series/carrossel-glm/glm_carousel/render.py:49`, `series/carrossel-minimax-features/minimax_carousel/layouts.py:68`);
  - paleta e fontes por série no CSS do gerador (laranja `#E27A55`, margens 100 px, Inter/JetBrains Mono) (`GUIA-CARROSSEL-CLAUDE-CODE.md:432-448`);
  - fontes do macOS por caminho absoluto: `/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf`, `Avenir Next.ttc`, `Menlo.ttc` (`series/carrossel-monetizacao-software/gerar_carrossel.py:59-61`, `INDEX.json:595`), `Arial Black.ttf` (`series/reel-narrado-soul/videos/001-quem-cuida-depois-do-lancamento/referencia-legendas-piloto.py:10`);
  - fontes baixadas de CDN de terceiro (`filecdn.minimax.chat`) (`series/carrossel-minimax-features/minimax_carousel/assets.py:11-13`);
  - integração de publicação "Expx Flow", `client_id`, registros `publicar/publicacoes-*.json` (`contratos/carrossel.schema.json`, `INDEX.json:45-47`);
  - público e assunto ("software house", IA, programação) embutidos nos GUIAs e skills (ver `inteligencia-editorial-carrossel.md`).

## Fonte

- `Instagram-Carrosseis/fabrica.py` (inteiro, 639 linhas); `Instagram-Carrosseis/series/INDEX.json` (inteiro, 850 linhas)
- `Instagram-Carrosseis/series/recriacoes/gerar_carrossel.py`, `series/como-se-eu-tivesse-5/gerar_carrossel.py`, `series/claude-code-features/gerar_carrossel.py:24-110`, `:545-663`, `series/claude-code-features/GUIA-CARROSSEL-CLAUDE-CODE.md:422-558`
- `Instagram-Carrosseis/contratos/*.schema.json`, `contratos/README.md`
- `Instagram-Carrosseis/.claude/skills/gerar-carrossel/SKILL.md`, `criar-serie-carrossel/SKILL.md`, `auditar-contrato/SKILL.md`; `.claude/agents/copywriter.md`, `revisor-editorial.md`, `geradores.md`, `contratos.md`; `.claude/rules/geradores/geradores-padrao-serie.md`, `convencoes-gerais.md`, `camada-editorial.md`, `contratos/contratos-fonte-de-verdade.md`
- `Instagram-Carrosseis/CLAUDE.md` (três fontes de verdade, regras que não se negociam, verificação `CLAUDE.md:202`)
- `Instagram-Carrosseis/tests/test_fabrica.py`, `tests/test_contracts.py`, `tests/test_migration.py`
