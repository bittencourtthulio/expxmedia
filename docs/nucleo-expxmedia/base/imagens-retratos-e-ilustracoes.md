# Imagens da peça: retratos, ilustrações de banco (Pexels), imagens geradas (OpenRouter) e Soul (Higgsfield)

Toda imagem que entra num slot de layout passa por um funil de dois validadores: o **script** (filtros mecânicos) e o **olho** (um agente abre a imagem, compara com o contexto e grava o porquê). Imagem sem ficha aprovada não renderiza. Corresponde às capacidades `banco_imagens`, `gerar_imagem`/`remover_fundo` e ao `porta_voz.retratos` da Alma (`ExpxMedia/docs/contrato/CONTRATO-capacidades.md:43`, `ExpxMedia/docs/contrato/CONTRATO-alma.md:163-172`).

## Contrato de entrada

Referências na copy (`Instagram-Carrosseis/galeria/_galeria.py:327`, `_galeria.py:446`):
- `retrato:<arquivo>` → arquivo em `galeria/retratos/` (nome simples, sem caminho nem `..`).
- `ilustracao:<arquivo>` → arquivo em `galeria/ilustracoes/` **com ficha `aprovada`**.
- caminho relativo à pasta da copy (print, SVG próprio) em slot que não é `pessoa`.

Comandos (`_galeria.py:1892-1926`):

| Comando | Entrada obrigatória | Fonte |
|---|---|---|
| `retratos [--uso x]` | — | `_galeria.py:345-364` |
| `retratos --fichar <arq> --enquadramento --fundo --descricao [--olhando] [--usos]` | enquadramento ∈ `rosto, busto, meio-corpo, corpo-inteiro`; fundo ∈ `neutro, ambiente, recortado`; olhando ∈ `camera, fora`; descrição ≥ 15 caracteres | `_galeria.py:328-330`, `_galeria.py:388-402` |
| `retratos --gerar "<prompt>" --base <foto>` | prompt ≥ 25 caracteres; base = retrato existente (OpenRouter, imagem→imagem) | `_galeria.py:704`, `_galeria.py:860-868` |
| `retratos --gerar "<prompt>"` (sem base) | Soul treinado (Higgsfield) | `_galeria.py:869-877` |
| `retratos --aprovar/--recusar <arq> --porque "..."` | porquê ≥ 40; aprovar exige ficha completa | `_galeria.py:453`, `_galeria.py:890-916` |
| `retratos --treinar-soul` / `--soul` | 5 a 20 JPG em `galeria/retratos/soul/treino` | `Instagram-Carrosseis/galeria/soul.py:85-98` |
| `ilustracoes --buscar "<termo>" --para "<slide>" [--limite 3] [--orientacao portrait]` | `para` ≥ 20 caracteres; orientação ∈ `portrait, landscape, square` | `_galeria.py:452`, `_galeria.py:536-543`, `_galeria.py:1914-1915` |
| `ilustracoes --gerar "<prompt>" --para "..." [--base retrato:|ilustracao:] [--modelo]` | prompt ≥ 25; com gente só com `--base retrato:` | `_galeria.py:823-834` |
| `ilustracoes --aprovar/--recusar <arq> --porque "..." [--sem-fundo] [--modelo-rembg u2netp]` | porquê ≥ 40 | `_galeria.py:585-636`, `_galeria.py:1921-1922` |
| `ilustracoes --modelos` | chave OpenRouter | `_galeria.py:725-730` |
| `processar <arq> --destino <pasta> --sem-fundo|--recortar-pessoa X,Y,WxH|--enquadrar LxA [--modo-enquadrar]|--redimensionar LxA|--normalizar` | exatamente uma operação | `Instagram-Carrosseis/galeria/processar.py:136-235` |

Credenciais (nunca impressas nem gravadas em ficha): `PEXELS_APIKEY`, `OPENROUTER_APIKEY` lidos do ambiente ou do `.env` da raiz do projeto; `OPENROUTER_MODELO_IMAGEM` opcional; CLI `higgsfield` autenticado (`_galeria.py:463-473`, `_galeria.py:712-722`, `_galeria.py:770`, `soul.py:60-72`).

## Contrato de saída

Fichas (escritas só pelo script, nunca à mão, gravação atômica):
- `galeria/retratos/retratos.json` → `{"_": nota, "retratos": [{arquivo, enquadramento, fundo, olhando, usos[], descricao, fichado_em, status?, gerada_de?, fonte?, modelo?, prompt?, gerada_em?, julgamento?, julgada_em?, nota_do_modelo?, usada_em[]}]}` (`_galeria.py:340-342`, `_galeria.py:398-401`, `_galeria.py:880-881`).
- `galeria/ilustracoes/ilustracoes.json` → `{"_", "ilustracoes": [{arquivo, status candidata|aprovada|recusada, fonte pexels|openrouter, pexels_id, busca, para, alt, autor, autor_url, url, licenca, w, h, orientacao, baixada_em, modelo?, prompt?, base?, julgamento, julgada_em, sem_fundo?, modelo_rembg?, usada_em[]}]}` (`_galeria.py:573-575`, `_galeria.py:837-839`, `_galeria.py:632`).
- `galeria/retratos/soul/soul.json` → `{id, nome, tipo, status, modelo, treino[]}` (`soul.py:106-109`).
- Arquivos: candidatas em `ilustracoes/candidatas/` e `retratos/candidatas/` (não versionadas, `Instagram-Carrosseis/.gitignore:35-36`); aprovadas movidas para a pasta principal; recusada: arquivo apagado, ficha mantida "para a mesma foto não voltar" (`_galeria.py:630-633`, `_galeria.py:901-905`).
- Nomes: `pexels-<id>-<slug termo 24>.jpg`, `gerada-<data>-<slug prompt 28>.jpg`, `thulio-gerado-<data>-<slug prompt 24>.jpg`, `<base>-sem-fundo.png` (`_galeria.py:554`, `_galeria.py:835`, `_galeria.py:878`, `_galeria.py:615`).
- Cada busca/geração devolve `candidatas`, `descartadas` com motivo, e `proximo` (instrução literal do que o agente faz a seguir) (`_galeria.py:579-582`, `_galeria.py:841-845`).
- `validar` inclui `validar_retratos` e `validar_ilustracoes` (`_galeria.py:1807-1808`).
- Uso registrado em `usada_em` após render OK (`_galeria.py:919-938`): "é o que deixa variar a foto entre as peças" (`Instagram-Carrosseis/galeria/README.md:88-91`).

## Limites e cotas

| Item | Valor | Fonte |
|---|---|---|
| Foto de banco por peça | 1 | `_galeria.py:448`, `_galeria.py:1090-1093` |
| Lado curto mínimo na busca (Pexels) | 1200 px | `_galeria.py:449`, `_galeria.py:520-521` |
| Lado curto mínimo do arquivo entregue | 1000 px | `_galeria.py:450`, `_galeria.py:568-572` |
| Lado máximo salvo | 1620 px (1,5× o slide) | `_galeria.py:451` |
| JPEG salvo | q88 (Pexels), q90 (gerada) | `_galeria.py:562`, `_galeria.py:809` |
| Pexels `per_page` | `max(3, min(limite×3, 30))` | `_galeria.py:478` |
| Timeout Pexels / modelos OpenRouter / download | 30 s | `_galeria.py:480`, `_galeria.py:728`, `_galeria.py:1658` |
| Timeout geração OpenRouter | 300 s | `_galeria.py:780` |
| Teto de imagens geradas por dia (OpenRouter + Soul somados) | 12 | `_galeria.py:703`, `_galeria.py:743-746`, `_galeria.py:876` |
| Prompt mínimo | 25 caracteres | `_galeria.py:704` |
| `para` mínimo | 20 caracteres | `_galeria.py:540`, `_galeria.py:826` |
| Julgamento mínimo (`--porque`) | 40 caracteres | `_galeria.py:453` |
| Descrição de ficha mínima | 15 caracteres | `_galeria.py:395` |
| `usada_em` guardado | últimas 20 | `_galeria.py:933` |
| Modelo de imagem padrão | `google/gemini-3-pro-image` | `_galeria.py:702` |
| Soul: modelo, aspecto, qualidade, espera | `text2image_soul_v2`, `3:4`, `2k`, `10m` | `soul.py:22-26` |
| Soul: custo por imagem | ~0,12 crédito | `soul.py:22` |
| Soul: treino | 5 a 20 imagens | `soul.py:89-90` |
| Soul: timeouts CLI / treino / download | 900 s / 3600 s / 300 s | `soul.py:60`, `soul.py:103`, `soul.py:154` |
| Soul: prompt | preâmbulo fixo + prompt, cortado em 900 caracteres | `soul.py:129-138` |
| rembg: modelo no render / no processar e `--aprovar --sem-fundo` | `u2net` / `u2netp` | `Instagram-Carrosseis/galeria/tratamento.py:21`, `processar.py:90`, `_galeria.py:585` |
| `normalizar` | autocontrast `cutoff` 0,02, ganho 1,2 | `processar.py:70` |
| JPEG do `processar` | q92 | `processar.py:225` |

## Erros conhecidos e tratamento

| Situação | Tratamento | Fonte |
|---|---|---|
| Pexels 401 | `SystemExit` pedindo conferir a chave (valor não impresso) | `_galeria.py:483-484` |
| Pexels/OpenRouter 403/429 | `Bloqueio`: rodada interrompida, nada descartado, saída 2 | `_galeria.py:485-486`, `_galeria.py:786-787`, `_galeria.py:2028-2029` |
| OpenRouter 401/403 | `SystemExit` com trecho de 200 caracteres do erro | `_galeria.py:783-785` |
| Modelo não devolve imagem | `SystemExit` com o que ele respondeu (200 caracteres) e dica `--modelos` | `_galeria.py:795-797` |
| Custo | cota conferida **antes** da chamada; contagem anotada **depois**, "mesmo que a resposta não sirva" (o que saiu do cartão conta) | `_galeria.py:778`, `_galeria.py:789` |
| Arquivo baixado/gerado não abre | apagado; descartada com motivo / `SystemExit` | `_galeria.py:564-567`, `_galeria.py:811-813` |
| API promete tamanho e entrega menor | descartada ("o que a API promete e o que ela entrega nem sempre batem") | `_galeria.py:568-572` |
| `large2x` do Pexels em retrato chega perto de 900 px | usa `original` com `fit=clip&w=1620&h=1620` | `_galeria.py:528-533` |
| Foto de banco com pessoa | descartada se `alt` casa `man|woman|person|people|portrait|face|team|...` | `_galeria.py:456`, `_galeria.py:522-524` |
| Prompt com gente sem `--base retrato:` | recusado; "sem pessoa"/"no people" não conta como pedido de gente | `_galeria.py:706-709`, `_galeria.py:830-832` |
| `--base` com referência de layout | recusado: "arte de terceiros não entra em prompt" | `_galeria.py:749-764` |
| Soul não treinado | `SemSoul` ⇒ "gere como variação: `--base`" | `soul.py:43-44`, `_galeria.py:874-875` |
| Saída do CLI Higgsfield muda de formato | varredura do JSON atrás da 1ª URL `.jpg/.png/.webp` (limite 5000 nós) | `soul.py:113-126` |
| URL assinada do Higgsfield | nunca impressa em log (é credencial de leitura) | `soul.py:61-62`, `soul.py:154` |
| `higgsfield` sem login | `SystemExit` "rode `higgsfield auth login`" | `soul.py:70-71` |
| rembg ausente | `ImportError` com instrução de instalação; `processar` sai 1 | `processar.py:94-100`, `processar.py:226-229` |
| Modelo rembg inexistente | `ValueError` com a lista oficial | `processar.py:101-107` |
| Symlink apontando para fora de retratos/ilustrações | recusado (não vira data URI) | `_galeria.py:381-385`, `_galeria.py:670-674` |
| Ficha órfã, aprovada sem julgamento, arquivo posto à mão, Pexels sem crédito, gerada sem modelo+prompt | reprova no `validar` | `_galeria.py:428-441`, `_galeria.py:677-695` |
| Primeiro prompt do Soul longo em português | saiu de perfil, outra roupa, outro fundo ⇒ prompt em inglês, curto, concreto, com lente e luz | `soul.py:133-137`, `Instagram-Carrosseis/.claude/rules/galeria.md:56-58` |

Critérios de julgamento (só no agente, não no código — `Instagram-Carrosseis/.claude/agents/galerista.md:107-137`):
- Ilustração: aprova quem mostra **o que o slide afirma** (não "tecnologia" vaga), sem pessoa em foco, sem marca/logotipo/texto legível, com área lisa que aguente o texto. "Na dúvida, recusa". "Nada aprovado é resposta legítima: o slide se resolve sem foto."
- Retrato gerado: "é ele?" — mesma pessoa, sem idealizar, sem mão/dedo/orelha/óculos deformados, sem texto inventado; abre variação e base lado a lado. "Recusar é barato; publicar um rosto que não é o dele, não."
- Prompt de variação com semelhança: "Use a pessoa da imagem exatamente como ela é: o mesmo rosto, a mesma identidade, sem idealizar, sem rejuvenescer e sem mudar traços. Gere uma foto nova dela, fotorrealista, em retrato 4:5, qualidade de estúdio." (`_galeria.py:865-866`).
- Preâmbulo do Soul: "photorealistic studio portrait photograph of the character, sharp focus, 85mm lens, natural skin texture, clean composition." (`soul.py:129-130`).
- Hierarquia de fonte de imagem: texto/forma SVG/print primeiro; Pexels só quando nada disso resolve; gerar quando nem o Pexels tem (`README.md:68-73`, `README.md:94-99`).
- Tratamento é do **layout**, não da foto: a mesma foto entra recortada num layout e inteira em outro; `retratos/` nunca é reescrito (`tratamento.py:9-11`).
- Divisão de papéis: buscar/gerar (vai à internet, custa) é da rotina principal; julgar é do agente que tem olho e escrita restrita (`Instagram-Carrosseis/galeria/ilustracoes/README.md:61-65`).

## Riscos para a nossa implementação

- **O validador que importa é o humano/agente com visão**, e ele está em prompt, não em código. Portar só o script mantém os filtros (tamanho, alt com pessoa, duplicata) e perde o critério "mostra o que o slide afirma" e "é ele?". A qualidade das imagens depende desse passo.
- **Nome da variável de ambiente diverge**: código usa `PEXELS_APIKEY`/`OPENROUTER_APIKEY` (`_galeria.py:465`, `_galeria.py:714`); o contrato de capacidades usa `PEXELS_API_KEY` (`CONTRATO-capacidades.md:43`, `CONTRATO-capacidades.md:160`).
- **Licença**: o contrato diz que foto de Pexels não é asset `neutro` e deve ser slot preenchido na hora (`CONTRATO-template.md:231-233`). A ficha guarda crédito (`_galeria.py:574-575`); ao subir template, a ilustração aprovada não pode ir junto.
- **Teto diário único para duas carteiras** (OpenRouter e Higgsfield) em `estado/galeria.json` (`_galeria.py:733-740`, `_galeria.py:876`). No núcleo, custo precisa virar cota por capacidade/provedor, sem perder o "anota mesmo se falhar".
- **Regex de pessoa só em inglês no `alt`** (`_galeria.py:456`) e pt/en no prompt (`_galeria.py:706`). Alma em outro idioma ou busca em português deixa passar pessoa.
- **Modelo rembg diferente entre caminhos** (`u2net` no render, `u2netp` no processar e no `--aprovar --sem-fundo`): quem unificar em `u2netp` traz de volta o "fantasma de fundo" que motivou a troca (`tratamento.py:21-22`).
- **A regra "pessoa é sempre a mesma" é identidade de marca pessoal**. No núcleo vira: slot `pessoa` só aceita retrato do `porta_voz` da peça (`CONTRATO-alma.md:163-172`), e o template marca `exige_porta_voz` (`CONTRATO-template.md:118`). Sem porta-voz, o slot precisa de substituto desenhado (hoje: "slot opcional com substituto desenhado e uma linha no relato pedindo foto", `galerista.md:72-74`).
- **Acoplamentos de marca/ambiente a virar dado da Alma ou `.env`:**
  - nome da pessoa e conta: `NOTA_RETRATOS` ("A foto é do Thulio", `_galeria.py:331-333`), prefixo de arquivo `thulio-gerado-` (`_galeria.py:878`), nome padrão do Soul `"Thulio Bittencourt"` (`soul.py:85`, `soul.py:163`), docstrings e mensagens "é ele", "foto dele" (`_galeria.py:769`, `_galeria.py:885-887`);
  - cabeçalho `X-Title: Instagram Carrosseis` no OpenRouter (`_galeria.py:777`);
  - `.env` na raiz do projeto como fonte de chave (`_galeria.py:466-470`, `_galeria.py:715-719`);
  - modelo padrão e aspecto do Soul (`_galeria.py:702`, `soul.py:22-26`);
  - pastas fixas `galeria/retratos`, `galeria/ilustracoes`, `galeria/tratadas`, `galeria/retratos/soul` sob a raiz (`_galeria.py:61-68`, `soul.py:28-31`, `tratamento.py:24-25`) ⇒ `alma/assets/retratos/<porta_voz>/` no contrato (`CONTRATO-alma.md:72`);
  - autorizações datadas do dono ("autorizou a variação gerada em 20/09/2026", `rules/galeria.md:89-90`) ⇒ política configurável por instalação.

## Fonte

- `Instagram-Carrosseis/galeria/_galeria.py:325-938`, `:1076-1093`, `:1481-1499`, `:1892-2006`
- `Instagram-Carrosseis/galeria/soul.py`, `galeria/processar.py`, `galeria/tratamento.py`
- `Instagram-Carrosseis/galeria/README.md:50-121`, `:342-372`; `galeria/ilustracoes/README.md`; `galeria/retratos/README.md`
- `Instagram-Carrosseis/.claude/agents/galerista.md:107-150`; `.claude/rules/galeria.md:40-95`; `.claude/skills/galeria-layouts/SKILL.md:92-142`
- `Instagram-Carrosseis/docs/galeria-processamento-imagem/00-DECISOES.md` (D-01 a D-13)
- `Instagram-Carrosseis/tests/test_galeria.py:600-848`, `:970-1060` (Pexels, OpenRouter, retratos, Soul); `tests/test_processar.py`
