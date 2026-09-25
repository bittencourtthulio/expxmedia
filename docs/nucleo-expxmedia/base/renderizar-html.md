# Renderização HTML → PNG (motor `galeria.renderizar`)

Porta de entrada única que transforma layout (HTML/CSS com slots) + copy em PNG medido. Hoje é usada pela prévia da galeria, pelo modo `--estresse` e pelas séries que adotaram layout (`recriacoes`, `como-se-eu-tivesse-5`). É a origem direta da capacidade `renderizar_html` (provedor `playwright`, `ExpxMedia/docs/contrato/CONTRATO-capacidades.md:33`).

## Contrato de entrada

Assinatura: `renderizar(layout, copy=None, saida=None, tema=None, base_copy=None, salvar_html=False, log=print, estresse=False)` (`Instagram-Carrosseis/galeria/_galeria.py:1562`).

| Parâmetro | O que aceita | Fonte |
|---|---|---|
| `layout` | dict de manifesto já carregado, id da galeria, id antigo (via `renomeados.json`) ou caminho de pasta com `layout.json` (inclusive a cópia adotada por série) | `_galeria.py:1564`, `_galeria.py:184-191` |
| `copy` | dict, ou caminho de JSON; `None` = usa `exemplo.json` do layout (modo prévia) | `_galeria.py:1567-1571` |
| `saida` | pasta de destino; `None` = `<layout>/previa/` | `_galeria.py:1576` |
| `tema` | sobrescreve `copy.tema`; precisa estar em `m.temas` | `_galeria.py:1572`, `_galeria.py:1038-1039` |
| `base_copy` | raiz contra a qual caminho relativo de imagem é resolvido; padrão = pasta do arquivo de copy | `_galeria.py:1571`, `_galeria.py:1495` |
| `estresse=True` | ignora `copy`/`saida`; gera copy com todo slot no `max` e grava em `previa/estresse/` | `_galeria.py:1565-1566`, `_galeria.py:1519-1538` |
| `salvar_html=True` | grava `slide_N.html` ao lado do PNG | `_galeria.py:1603-1604` |

Formato da copy (o que a série escreve) — `Instagram-Carrosseis/galeria/README.md:299-317`:

```json
{"layout": "<id, só informativo>", "tema": "referencia",
 "variaveis": {"--destaque": "#ff5a1f", "--fonte-titulo": "'Space Grotesk', sans-serif"},
 "fontes_google": ["Space Grotesk:wght@500;700"],
 "slides": [{"kind": "capa", "titulo": "..."}, {"kind": "passo", "titulo": "...", "itens": [{"titulo": "...", "texto": "..."}]}]}
```

- `variaveis`: nome precisa casar `^--[\w-]+$` e o valor não pode conter `;{}<>`, `url(` nem `\` (`_galeria.py:106`, `_galeria.py:1040-1042`). Entram como `style` inline na `<section>` (`_galeria.py:1508`, `_galeria.py:1511`).
- `fontes_google`: cada item casa `^[\w :;@,.+-]+$` (`_galeria.py:105`, `_galeria.py:1043`); vira `<link>` para `fonts.googleapis.com/css2?family=...&display=swap` (`_galeria.py:1504-1505`). Copy sem `fontes_google` herda a do manifesto.
- Valor de slot de imagem: caminho relativo "para baixo" da pasta da copy (`.png .jpg .jpeg .webp .svg`), `retrato:<arquivo>`, `ilustracao:<arquivo>` ou `data:image/...` já pronto (`_galeria.py:1097-1104`, `_galeria.py:1484-1499`).
- Marcação de texto: `*palavra*` vira `<em>`, `\n` vira `<br>`, tudo HTML-escapado (`_galeria.py:947-951`).

Dialeto de template ("mustache pequeno", `_galeria.py:943-1014`): `{{slot}}`, `{{#lista}}…{{/lista}}` com `{{.}}`, `{{@n}}`, `{{@nn}}`, `{{^slot}}` (substituto quando vazio), embutidos `{{_n}}`, `{{_nn}}`, `{{_total}}` (paginação). Qualquer outra marca (`{{{x}}}`, `{{! }}`) reprova (`_galeria.py:1009-1010`). Campo ausente num item de lista sai vazio e **não** herda o slot homônimo do slide (`_galeria.py:1500-1501`).

Dependências de runtime: `playwright` (Chromium) importado dentro da função (`_galeria.py:1584`); Pillow para medição e prancha; `rembg` opcional só se algum slot declarar `tratamento.sem_fundo` (`Instagram-Carrosseis/galeria/tratamento.py:88-93`).

## Contrato de saída

Retorno (`_galeria.py:1633-1641`):

```json
{"ok": true, "layout": "<id>", "saida": "<pasta>", "impressao": "<sha16>", "em": "AAAA-MM-DD",
 "slides": [{"slide": 1, "kind": "capa", "encaixe": "fixo | free=N shrink=N zoom=Z",
             "problemas": [], "avisos": [], "fontes_com_erro": []}],
 "prancha": "<pasta>/prancha.png"}
```

- Copy inválida não abre navegador: devolve `{"ok": false, "erros": [...], "slides": [], "saida": null}` (`_galeria.py:1573-1575`).
- Arquivos: `slide_N.png` 1080×1350 (ou o `canvas` do manifesto) em `saida/` (`_galeria.py:1618-1619`); `slide_N.html` se pedido.
- Só no modo prévia (sem copy): `prancha.png` (original à esquerda, reconstrução à direita) e `render.json` com o resultado inteiro (`_galeria.py:1635-1638`). Peça de série não grava prancha nem `render.json` (teste `Instagram-Carrosseis/tests/test_galeria.py:417-428`).
- `ok = not any(slide.problemas)` (`_galeria.py:1633`). Avisos não reprovam.
- Efeito colateral: com `ok` e fora de estresse/prévia, anota em `usada_em` da ficha de cada `retrato:`/`ilustracao:` usado (máx. 20 entradas por ficha, `_galeria.py:919-938`, `_galeria.py:933`); falha nesse registro é engolida (`_galeria.py:937-938`).
- `impressao`: sha256 (16 hex) do manifesto sem campos voláteis (`titulo, status, origem, estilos, serve_para, analise, decomposto_em, referencia`) + bytes de `layout.css`, `exemplo.json`, `slides/*.html`, `assets/**` (`_galeria.py:93`, `_galeria.py:1117-1124`). É o que diz se a prévia em disco "ainda vale" (`_galeria.py:1263`).

CLI: `python3 galeria.py renderizar <layout> [--copy x.json] [--saida p] [--tema t] [--html] [--estresse] [--json]` (`_galeria.py:1878-1884`); código de saída 0 se `ok`, 1 se reprovado (`_galeria.py:2026-2027`).

## Limites e cotas

| Item | Valor | Fonte |
|---|---|---|
| Canvas padrão | 1080×1350, `device_scale_factor=1` | `_galeria.py:319`, `_galeria.py:1589` |
| Espera após `set_content` | `wait_until="networkidle"` + `document.fonts.ready` + 150 ms | `_galeria.py:1605-1607` |
| Timeout de `set_content` | padrão do Playwright; séries documentam 30 s em `networkidle` | NÃO DOCUMENTADO no `_galeria.py`; `Instagram-Carrosseis/series/claude-code-features/GUIA-CARROSSEL-CLAUDE-CODE.md:72` |
| Encaixe: encolhimento | fonte × 0,96 por rodada, até 40 rodadas | `_galeria.py:1278-1279` |
| Encaixe: crescimento | zoom +0,02 enquanto `free > 40` px, até `zoom_max` 1,3 | `_galeria.py:84`, `_galeria.py:1284` |
| Encaixe: recuo | zoom −0,02 até `zoom_min` 0,8 se `free<0` ou texto estoura largura (tolerância 1 px) | `_galeria.py:84`, `_galeria.py:1282`, `_galeria.py:1285` |
| Meta do encaixe | `shrink=0` e zoom entre 1,0 e 1,3 com o exemplo | `Instagram-Carrosseis/galeria/README.md:280-281` |
| Aviso de zoom | zoom < 1 com `free > 40` px ⇒ "um texto estoura a largura da caixa" | `_galeria.py:1627-1629` |
| Fonte mínima de leitura | 28 px (tolerância 0,5 px) | `_galeria.py:86`, `_galeria.py:1305` |
| Piso de texto miúdo | 18 px | `_galeria.py:87` |
| Contraste mínimo | 3,0:1 (WCAG), no ponto pior do fundo | `_galeria.py:90`, `_galeria.py:1443` |
| Faixa vazia topo/rodapé | máx. 22% da altura | `_galeria.py:91`, `_galeria.py:1462` |
| Texto fora do slide | tolerância 1 px + `fit.margem` + "sobra de glifo" = `max(0, fs×1,2 − line-height)` | `_galeria.py:1307`, `_galeria.py:1317` |
| Texto cortado | `scrollWidth > clientWidth + 2` (ou altura + 2 + sobra) só com `overflow ≠ visible` | `_galeria.py:1320` |
| Texto sobre texto | interseção > 6 px nos dois eixos, caixas com 20% de folga vertical | `_galeria.py:1313`, `_galeria.py:1328` |
| Texto invisível | elemento com `opacity ≤ 0,05` ou `visibility:hidden` fica fora das caixas | `_galeria.py:1313` |
| Colunas soltas (aviso) | mais de 2 bordas esquerdas isoladas (±8 px) | `_galeria.py:1331-1334` |
| Leitura por pixel | caixa encolhida 2 px/1 px; ignora caixa < 8 px; "tinta" = pixel com distância RGB > 40 entre com-texto e sem-texto; texto sumido se tinta < 2% | `_galeria.py:1413-1426` |
| Fundo "do próprio texto" | pixels a ≤ 40 da cor da tinta saem da conta se forem < 15% da caixa | `_galeria.py:1436-1438` |
| Ponto pior do fundo | percentis 5% e 95% de luminância do que está atrás | `_galeria.py:1439-1442` |
| Cor dominante | baldes de 24 por canal | `_galeria.py:1393-1402` |
| Ocupação | imagem reduzida 1/8, linha a cada 8 px, pixel "não fundo" se distância > 36 | `_galeria.py:1454-1456` |
| Prancha | células 432×540, folga 16 px, fundo RGB (40,40,40) | `_galeria.py:1544-1546` |
| Tempo real de uma peça | 8 slides em 51,6 s e 57,5 s | `Instagram-Carrosseis/estado/geracoes.jsonl` (últimas linhas, 24/09/2026) |
| Suíte de testes da área | 163 testes em 71,5 s (galeria + processar + fabrica) | execução local em 24/09/2026 |

Rede: só `data:`, `about:`, `blob:` e `https://fonts.googleapis.com` / `fonts.gstatic.com` passam; tudo mais é abortado e vira PROBLEMA `rede barrada` (`_galeria.py:103`, `_galeria.py:1592-1598`, `_galeria.py:1611`). JavaScript da página desligado; o encaixe e a medição rodam por `page.evaluate` de fora (`_galeria.py:1587-1589`).

## Erros conhecidos e tratamento

Pipeline por slide, na ordem (`_galeria.py:1600-1631`): montar HTML → `set_content` → fontes → `FIT_JS` → `CHECK_JS` → rede barrada → fonte não carregada → screenshot → screenshot **sem tinta** → leitura por pixel → ocupação → aviso de zoom → log.

| Achado (texto do PROBLEMA) | Causa | Fonte |
|---|---|---|
| `texto fora da área do slide` | caixa de texto passa da borda/margem | `_galeria.py:1317` |
| `texto cortado` | `overflow` corta conteúdo | `_galeria.py:1320` |
| `texto de Npx (o mínimo é 28px)` | fonte abaixo do mínimo (ou do piso, se `miudo`) | `_galeria.py:1302-1305` |
| `fonte 'X' não é do layout` | família computada fora de `fontes_google` e das genéricas | `_galeria.py:1299-1301` |
| `fonte 'x' não carregou` | família pedida e usada em algum texto falhou em `document.fonts.check` (ex.: offline) | `_galeria.py:1612-1617` |
| `texto sobre texto: A × B` | colisão de duas caixas de texto sem `data-sobre` | `_galeria.py:1322-1329` |
| `o texto não aparece no PNG` | coberto por enfeite ou da mesma cor do fundo | `_galeria.py:1425-1427` |
| `contraste N:1 entre o texto e o fundo / o ponto pior...` | contraste abaixo de 3:1 | `_galeria.py:1443-1445` |
| `faixa vazia no topo/no rodapé: N%` | respiro > 22% sem `vazio_ok` no kind | `_galeria.py:1461-1464`, `_galeria.py:1624` |
| `o slide está vazio` | nenhuma linha diferente da cor dominante | `_galeria.py:1457-1458` |
| `rede barrada: o layout tentou buscar <host>` | recurso externo no HTML/CSS | `_galeria.py:1611` |
| `SystemExit` "imagem '...' não existe dentro de ..." | caminho de imagem fora da pasta da copy ou symlink para fora (`resolve()`) | `_galeria.py:1494-1499` |

Exceções que a medição conhece (declaradas, não escape):
- Cor com alfa e `color-mix()` (Chromium serializa `color(srgb 0.96 …)`) é composta com o fundo antes do contraste (`_galeria.py:1365-1372`, `Instagram-Carrosseis/galeria/README.md:161-162`). **Atenção:** `rgb_de` lê números com regex e espera 0–255; o README afirma suporte a `color(srgb 0..1)`, mas o código não reescala — comportamento com `color-mix` NÃO DOCUMENTADO por teste.
- Texto pintado pelo fundo (`background-clip:text`, `-webkit-text-fill-color: transparent`) sai das checagens de pixel (`_galeria.py:1316`, `_galeria.py:1420-1424`).
- `data-sobre` no elemento (ou ancestral) isenta de colisão e contraste: "palavra que é desenho, não leitura" (`_galeria.py:1315`, `_galeria.py:1328`, `Instagram-Carrosseis/galeria/README.md:164-167`).
- `decorativo` isenta de mínimo e das caixas de leitura (`_galeria.py:1302`, `_galeria.py:1336`).
- Texto SVG é medido pela caixa do elemento (reflete `textLength`), não pelo range do glifo (`_galeria.py:1310-1311`).

Problemas já resolvidos (a não reintroduzir):
- Grafismo `position:absolute` pintando por cima do título: pego por "texto não aparece" (teste `Instagram-Carrosseis/tests/test_galeria.py:892-897`).
- Título display com entrelinha 0,8 acusado como corte: resolvido pela "sobra de glifo" (`_galeria.py:1306-1307`; teste `tests/test_galeria.py:431-446`).
- Enfeite absoluto saindo da caixa derrubava o zoom: o zoom e a medição só olham elemento com nó de texto direto (`_galeria.py:1280-1282`).
- Fonte caindo no fallback do sistema e a peça "parecendo" certa: agora reprova (`_galeria.py:1612-1617`).
- `mix-blend-mode: multiply` como gambiarra para fundir foto: substituído por `tratamento` no slot (`Instagram-Carrosseis/galeria/tratamento.py:1-15`).
- Modelo de recorte `u2netp` deixava "fantasma" de fundo (refletor, névoa): padrão do render passou a `u2net`, e o modelo entra na impressão digital do cache para não servir o recorte velho (`tratamento.py:21-22`, `tratamento.py:60-67`; teste `tests/test_galeria.py:1130`). O `processar` CLI e `--aprovar --sem-fundo` ainda usam `u2netp` (`Instagram-Carrosseis/galeria/processar.py:90`, `_galeria.py:585`).
- `Page.set_content` com `networkidle` estourando 30 s quando o Google Fonts demora: tratamento documentado é "rodar de novo com rede" e conferir timestamp dos PNG (`series/claude-code-features/GUIA-CARROSSEL-CLAUDE-CODE.md:536`). O `galeria.renderizar` não tem retry: NÃO DOCUMENTADO.

Tratamento de imagem declarado no slot (`tratamento.py`): chaves `sem_fundo, pb, contraste, enquadrar, modo, modelo_recorte` (`tratamento.py:20`); chave desconhecida é erro (`tratamento.py:40-42`); `contraste` entre 0,2 e 3 (`tratamento.py:47-48`); `enquadrar` = `LxA` px; `modo` `cover|contain` (padrão `contain` no render, `tratamento.py:103`). Ordem fixa: tira fundo → cor → enquadra (`tratamento.py:76-78`). Cache em `galeria/tratadas/<stem[:40]>-<sha16>.png` (`tratamento.py:25`, `tratamento.py:83`). Sem `rembg`: `SystemExit` "o slot pede `sem_fundo` e rembg não está instalado" (`tratamento.py:92-93`).

## Riscos para a nossa implementação

- **Contraste medido no PNG, não no CSS.** A inteligência está na dupla captura (com tinta / sem tinta) e no ponto pior do fundo (percentis 5/95). Trocar por cálculo de contraste entre `color` e `background-color` computados perde texto sobre foto, forma e divisa de cor — exatamente os casos que o original pega (`_galeria.py:1405-1446`).
- **O encaixe depende de seletores declarados** (`fit.encolher`, `.vis` com um filho só). Template novo sem esses seletores "passa" com `shrink>0` sem encolher o card (`series/claude-code-features/GUIA-CARROSSEL-CLAUDE-CODE.md:549-558` descreve o mesmo defeito no motor irmão).
- **Tokens da Alma quebram a validação de família.** Hoje a família de fonte só é aceita se vier de `fontes_google` (`_galeria.py:1142-1164`, `_galeria.py:1299-1301`), e `@font-face` é proibido (`_galeria.py:99`). A Alma aceita `fontes.*.origem: local` (`ExpxMedia/docs/contrato/CONTRATO-alma.md:205`). Injetar fonte local exigirá um caminho seguro de `@font-face` controlado pelo motor, sem abrir a porta para o layout.
- **A lista de famílias da medição vem da copy** (`_galeria.py:1581`); se o motor injetar `--alma-fonte-*` sem passar as famílias nessa lista, todo texto reprova como "fonte não é do layout".
- **Rede só Google Fonts** (`_galeria.py:103`). Render isolado "sem rede" do contrato (`CONTRATO-template.md:202`) é compatível; fonte da Alma hospedada em outro host não carregará.
- **Tempo:** ~7 s por slide (57,5 s / 8, `estado/geracoes.jsonl`). Um navegador por chamada (`_galeria.py:1586`), sem pool: lote grande multiplica o custo de boot.
- **`networkidle` + Google Fonts = dependência de internet no render.** Sem rede, a fonte cai e a peça reprova (correto), mas não há modo offline com fonte embarcada.
- **Pillow `getdata()` depreciado** (remoção no Pillow 14, 2027-10-15) nas funções de leitura e ocupação (`_galeria.py:1416`, `_galeria.py:1454-1455`; aviso na suíte). Portar ingenuamente para versão nova quebra a medição.
- **Heurísticas numéricas afinadas por caso real** (40 de distância RGB, 2% de tinta, 15% de traço do texto, 20% de folga, 36 na ocupação, sobra de glifo 1,2). Mudar qualquer uma sem os testes de `tests/test_galeria.py:849-921` recalibra silenciosamente o que é "legível".
- **`vazio_max`, `minimo`, `piso`, `contraste` são sobrescrevíveis por layout** (`_galeria.py:1579`). O contrato de template fixa `contraste_min 3.0` e `fonte_min_px 28` (`CONTRATO-template.md:146-147`); se o template de terceiro puder baixar esses valores, a garantia some.
- **`embutir_assets` antes de `preencher`** é deliberado: texto da copy nunca vira data URI de asset (`_galeria.py:1502`). Inverter a ordem abre leitura de arquivo pela copy.
- **Acoplamentos de marca/ambiente a virar dado:**
  - canvas 1080×1350 fixo na ingestão (`_galeria.py:319`) e no prefixo 4:5 da README (`galeria/README.md:241`) → `formato`/`canvas` do template;
  - `RECHEIO` do estresse em vocabulário tech pt-BR ("agente contexto revisão código…") (`_galeria.py:1516`) → gerar a partir do idioma da Alma ou lorem com comprimento (o contrato prevê lorem no envio, `CONTRATO-template.md:294-295`);
  - tema `referencia` como padrão de render (`_galeria.py:1509`) → substituído por `tokens` da Alma;
  - `galeria/tratadas/` e `galeria/retratos/` como caminhos fixos sob `RAIZ` (`tratamento.py:24-25`, `_galeria.py:61-68`).

## Fonte

- `Instagram-Carrosseis/galeria/_galeria.py:1268-1641` (renderização, encaixe, medição, prancha), `:941-1014` (template), `:1117-1124` (impressão digital), `:1365-1465` (leitura e ocupação)
- `Instagram-Carrosseis/galeria/tratamento.py`, `Instagram-Carrosseis/galeria/processar.py`
- `Instagram-Carrosseis/galeria/README.md:123-176`, `:243-296`
- `Instagram-Carrosseis/tests/test_galeria.py:351-446`, `:849-921`, `:1060-1138`; `Instagram-Carrosseis/tests/conftest.py:1-26` (rede fechada em teste)
- `Instagram-Carrosseis/series/claude-code-features/GUIA-CARROSSEL-CLAUDE-CODE.md:454-558` (origem do algoritmo de encaixe e problemas conhecidos)
- `Instagram-Carrosseis/docs/galeria-processamento-imagem/00-DECISOES.md` (D-05 u2netp, depois superada em `tratamento.py:21`)
- Execução: `python3 -m pytest tests/test_galeria.py tests/test_processar.py tests/test_fabrica.py -q` → 163 passed em 71,49 s (24/09/2026)
