# Inteligência do reel recriado (regras de fidelidade, gates, lições, marca e ponte com a central)

Tudo o que não é código de render mas decide se o reel sai "o mais parecido possível" sem copiar nada: a tabela do
que se imita, a ordem das etapas, os gates (mecânicos e de revisão), as lições medidas com o dono no primeiro reel
aprovado, o acoplamento de marca que precisa virar dado da Alma, e a parte genérica da ponte com a central
(pedido → produção sem cabeça → marcador → agendamento).

## Contrato de entrada

- **Pedido**: pasta com `referencia/video.mp4` e `origem.json` + id `rAAAAMMDD-HHMMSS`
  (`Instragram-Videos/.claude/commands/new-video-recriado.md:3,9-11`). O comando segue a skill "do passo 1 ao 8, sem
  perguntar nada", não publica (`:8-11`), e "nunca pelos tipos fixos de cena" (`:12-13`).
- **Instrução do dono**: texto mandado junto do link (`origem.json > texto_do_thulio`) "é instrução dele e vence o
  resto, dentro das regras" (`Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:39-40`).
- **Exemplo de processo**: `remotion/src/reels/recriado-ia-decide/` — "estrutura de código e processo; o visual é
  daquele reel só" (`Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:17-18`).
- **Voz e CTA** (dados de marca, lidos da central): `Instagram-Carrosseis/editorial/voz.md` e `cta.md`
  (`Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:30-31`).

### Decisão que funda o formato (literal)

Depois de aprovar o `recriado-ia-decide` ("ficou fantástico"), em 24/09/2026: *"quando você receber via Telegram a URL
de um reel e for recriar esse cara, eu quero que você tenha esse trabalho. Analise a fundo como é que é para recriar o
mais parecido possível, sempre usando o JavaScript para fazer essa recriação, adicionar o som, adicionar a narração e
tudo mais ... para que não fique genérico, para que não tente usar algo que já foi usado"*
(`Instragram-Videos/.claude/rules/recriado.md:10-14`). Consequência: **cada recriado é código novo**
(`:16-19`).

### O que "o mais parecido possível" quer dizer (`Instragram-Videos/.claude/rules/recriado.md:21-31`)

| imita (redesenhado em código) | não entra nunca |
|---|---|
| composição da tela: elementos fixos, posição, proporção | quadro, trecho de vídeo ou print do original |
| sequência de cenas e o tipo de cada uma | frase dele traduzida palavra por palavra |
| jeito de animar: entrada, movimento, troca, ritmo | áudio dele: voz, música, efeito |
| estilo da legenda: tamanho, posição, como a palavra acende | logo, marca, mascote ou personagem dele |
| paleta e clima (cor aproximada, não o arquivo) | rosto de pessoa real (só o dono da conta) |
| onde entram os sons e de que tipo | número/fato dele sem fonte primária |
| o tema, em português, com o nosso ângulo | |

## Contrato de saída

Entrega da skill (`Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:137-139`): `videos/<slug>/<slug>.mp4`,
`legenda.txt`, `recriado.json`, `roteiro.txt`, `alignment.json`, `previa.jpg`, `analise/` (com `leitura.md`) e o código
em `remotion/src/reels/<slug>/`. Em falha: `videos/<slug>/falha.txt` com o motivo (`:133`).

Sequência canônica (`Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:149`):
analisar → ler as folhas inteiras (`leitura.md`) → roteiro → tts → código sob medida → prévia comparada → render →
verify → revisor.

### Checklist de revisão do recriado (gate humano/modelo, `Instragram-Videos/.claude/rules/recriado.md:79-91`)

- **parecença**: `analise/folhas/` lado a lado com `previa.jpg` e quadros do mp4; mesma composição, sequência e tipo
  de cena, animação do mesmo jeito, legenda no mesmo estilo. "Genérico ou 'de template' é achado";
- nada do original (frase, quadro, áudio, logo, rosto); legenda do feed também nossa;
- nada reaproveitado de outro recriado (personagem, cena, trilha);
- todo número e nome com fonte primária;
- cenas acompanham a fala; nenhum texto sai da tela; tudo em 220–1500 px, centrado;
- selo de perfil presente; som de troca sem chiado; narração acima da trilha;
- legenda por palavra legível; sem travessão; "você";
- `verify.py` APROVADO no modo recriado.

Não vale no recriado o que é de formatos com scroll: captura, cartão de impacto, selo "Comenta PALAVRA", PNG de
legenda (`Instragram-Videos/.claude/rules/recriado.md:81-82`).

### Ponte com a central (só o genérico)

| etapa | comportamento | fonte |
|---|---|---|
| detectar tipo | link de post/reel vira `tipo: "reel"` quando o download traz vídeo (instaloader `is_video`, gallery-dl com `.mp4/.mov/.webm`, `og:video`) | `Instagram-Carrosseis/recriar.py:172,186-188,234-237,262-270`; extensões em `:123` |
| ordem de download | instaloader (só Instagram) → gallery-dl (cookies do Chrome, 120 s) → metatags `og:*`; nada serviu → `precisa_prints` | `Instagram-Carrosseis/recriar.py:277-305,216-221` |
| vídeo mandado no chat | vira referência (`metodo: telegram`), até 20 MB (limite do `getFile`) | `Instagram-Carrosseis/recriar.py:712-724`; `Instagram-Carrosseis/telegram_bot.py:203` |
| produção | `claude -p "/new-video-recriado <pasta> <pedido>" --permission-mode bypassPermissions --disallowedTools <lista>`, cwd e `CLAUDE_PROJECT_DIR` no projeto de vídeos, sem variáveis `TELEGRAM_*`, 90 min | `Instagram-Carrosseis/recriar.py:666-669,637` |
| ferramentas proibidas na produção | ler `.env`, rodar `pipeline/publish.py`, `git push` | `Instagram-Carrosseis/recriar.py:603-606` |
| trava | um arquivo de trava por tipo (`recriacoes-reel.lock`), para um reel longo não segurar os carrosséis | `Instagram-Carrosseis/recriar.py:656-661` |
| achar o resultado | `videos/*/recriado.json` com `pedido == pid` → slug; exige `<slug>.mp4` | `Instagram-Carrosseis/recriar.py:640-648,672-676` |
| falha | lê `falha.txt` se existir, senão o fim da saída; evento `falhou` | `Instagram-Carrosseis/recriar.py:680-683` |
| agendar | horário livre: passos de 15 min, 08:00–22:30, ≥ 30 min de agora, ≥ 45 min de outro post; envio 20 min antes | `Instagram-Carrosseis/recriar.py:383,433-451,695-709` |
| enviar | `verify.py` → `publish.py --dry-run` → interruptor `publicacao_automatica` → `publish.py --scheduled-at`; `publicacao.json` é a prova e a trava contra duplicar | `Instagram-Carrosseis/recriar.py:510-541` |
| prévia no chat | `sendVideo` até 50 MB; acima, aviso | `Instagram-Carrosseis/telegram_bot.py:204,319-320` |
| catálogo | formato `reel-recriado` com `sob_demanda: true`, marcador `recriado.json`, fora de plano/notas/reposição | `Instagram-Carrosseis/series/INDEX.json:827-846`; `Instagram-Carrosseis/reels.py:38-41` |
| marcador | `origem_url`, `pedido`, `analise`, `criado_em`; `formato_do_video` reconhece `recriado` | `Instragram-Videos/pipeline/lib.py:309-329` |

## Limites e cotas

| item | valor | fonte |
|---|---|---|
| tempo total da produção | 90 min | `Instagram-Carrosseis/recriar.py:637` |
| orçamento interno | análise ~15, roteiro+TTS ~5, código ~35, prévia ~20, render+verify ~10 (min) | `Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:33-34` |
| voltas de prévia | no máximo 3 | `Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:121` |
| voltas de revisão | no máximo 2 | `Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:132` |
| chamadas de TTS | 1 | `Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:81,148` |
| área segura | 220 a 1500 px (interface cobre ~220 em cima e 420 embaixo) | `Instragram-Videos/remotion/src/kit/anim.ts:13-16` |
| folga do centralizar | 16 px, escala ≤ 1 | `Instragram-Videos/remotion/src/kit/anim.ts:19-22` |
| faixa inferior reservada à UI | 420 px | `Instragram-Videos/pipeline/lib.py:10` |
| área útil do legado | topo 170, base 1150, lateral 90 | `Instragram-Videos/remotion/src/tema.ts:25` |
| base da legenda do legado | `1920 − 420 − 40` | `Instragram-Videos/remotion/src/Legenda.tsx:7` |
| formato de entrega | 1080x1920, 30 fps, 30–70 s, −14 LUFS, pico ≤ −1 dBFS | `Instragram-Videos/.claude/rules/recriado.md:76-77` |
| custo declarado | 1 chamada ElevenLabs (~1.000 caracteres) + render local | `Instagram-Carrosseis/series/INDEX.json:840` |

## Erros conhecidos e tratamento

Lições medidas e corrigidas com o dono no primeiro reel sob medida, 24/09/2026
(`Instragram-Videos/.claude/rules/recriado.md:52-65`):

| falha | correção | onde ficou |
|---|---|---|
| detector de cortes deu "3 cenas" numa referência com cena nova a cada 3–4 s | leitura pelas folhas a 1 quadro/s, inteiras e em ordem | `Instragram-Videos/pipeline/analisar_reel.py:13-16,88-109` |
| 1ª versão "muito para cima" | área segura 220–1500 e conteúdo **centrado** nela; `centralizarNaArea` encolhe se não couber; guias na prévia | `Instragram-Videos/remotion/src/kit/anim.ts:13-26`; `Instragram-Videos/pipeline/render_remotion.py:186-187` |
| faltava identidade de quem publica | selo de perfil embaixo, sempre, "vale para todos" | `Instragram-Videos/remotion/src/kit/SeloPerfil.tsx:5-8` |
| transição "muito alta e feia, parece um chiado" | `whoosh` grave, macio, baixo | `Instragram-Videos/remotion/scripts/audio.mjs:5-7,103-113` |
| AAC passa do pico | passada extra automática | `Instragram-Videos/pipeline/render_remotion.py:135-139` |
| dono disse que não precisava de voz e voltou atrás ("faz a voz sim") | narração obrigatória | `Instragram-Videos/.claude/rules/recriado.md:64-65` |

Falhas anteriores ao sob medida (formato antigo, mesmo dia): três recriações (`recriado-20260924-113312`, `-120913`,
`-151859`) aprovadas pelo gate e pela revisão, mas "só tipografia sobre fundo escuro, narração na voz clonada, sem
música" (`Instragram-Videos/videos/recriado-20260924-151859/revisao.md`, seção 2) — é o "genérico" que motivou a
mudança. Em duas delas a revisão foi feita pelo orquestrador porque o `revisor-video` "não estava disponível para
delegação" (`Instragram-Videos/videos/recriado-20260924-120913/revisao.md:3-4`;
`.../recriado-20260924-113312/revisao.md:1`). Uma saiu com 4,33 pal/s (`.../recriado-20260924-120913/revisao.md`, observação).

Veracidade: o reel aprovado tirou "200x mais rápido, 400x mais barato", o nome do fundador e "cofundador do ChatGPT"
por falta de fonte primária, "e o vídeo ficou bom sem eles" (`Instragram-Videos/.claude/rules/recriado.md:38-41`).

Red flags declaradas (`Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:141-148`): tipos fixos de cena;
copiar personagem/cena/trilha de outro recriado; pular as folhas e escrever cenas "do seu jeito"; copiar frase, áudio,
quadro, logo ou rosto; número sem fonte; conteúdo fora de 220–1500 ou colado no topo; faltar o selo; TTS mais de uma
vez; rodar `publish.py`.

## Riscos para a nossa implementação

1. **A fidelidade mora no processo do modelo, não num algoritmo.** Leitura das folhas → `leitura.md` de 9 seções →
   código novo → prévia × folhas (3 voltas) → revisor com checklist de parecença. Extrair só scripts perde a garantia.
   Os prompts (skill, regra, checklist) têm de virar artefatos versionados do núcleo, sem nomes próprios.
2. **Não há gate mecânico de parecença, de área segura, de selo nem de reaproveitamento visual.** Só a trilha tem
   anti-repetição por script (`Instragram-Videos/remotion/scripts/montar-reel.mjs:50-60`).
3. **`revisor-video` não conhece o formato**: o agente não cita "recriado" (grep em
   `Instragram-Videos/.claude/agents/revisor-video.md` vazio em 2026-09-24), e a auditoria já apontava
   (`Instagram-Carrosseis/docs/reels-recriados-remotion/00-AUDITORIA.md:32`). A revisão depende da regra ser passada no prompt.
4. **Decisões antigas contradizem o vigente**: D-05 (tipos fechados, "Composição livre por reel" descartada) e D-06
   ("sem música") em `Instagram-Carrosseis/docs/reels-recriados-remotion/00-DECISOES.md:33-43`; D-07 (20–70 s,
   `:45`) contra 30–70 s (`Instragram-Videos/pipeline/lib.py:305-306`). A fonte de verdade é a regra de 24/09 (sob medida).
5. **Código de reel sob medida é "de terceiro" no sentido do contrato**: escrito por modelo, roda na máquina; o
   contrato exige imports permitidos, sem `fs`/rede, tudo da empresa por props
   (`ExpxMedia/docs/contrato/CONTRATO-template.md:59-69`). O exemplo aprovado viola a regra 4 (cores literais,
   textos fixos, `staticFile` literal).
6. **Autonomia total** (`bypassPermissions`, sem perguntas) depende da lista de proibições; qualquer nova ferramenta
   de publicação precisa entrar nela.

### Acoplamento de marca/pessoa que precisa virar dado da Alma

| item | valor hoje | fonte |
|---|---|---|
| paleta EXPX (legado) | fundo `#0B0B0F`, painel `#16161D`, texto `#F5F2EC`, sutil `#A39E96`, acento `#E4602A` | `Instragram-Videos/remotion/src/tema.ts:6-12` |
| regra do acento | pode vir nos props (cor da ferramenta citada), "nunca a paleta do reel de referência" | `Instragram-Videos/remotion/src/tema.ts:4-5` |
| fonte da marca | Inter 400/700/800/900 local | `Instragram-Videos/remotion/src/tema.ts:14-22`; `Instragram-Videos/remotion/package.json:10` |
| paleta do reel aprovado | creme `#F4EBD9`, papel `#FBF5E8`, tinta `#1E1B18`, laranja `#E4602A`, ferrugem `#B5452A`, verde `#3DBE8B`, amarelo `#F2B33D`, corpo `#E0694A`, sombra `#B9502F` | `Instragram-Videos/remotion/src/reels/recriado-ia-decide/pecas.tsx:6-16` |
| selo de perfil | "Thulio Bittencourt", "@thuliobittencourt", `marca/perfil.jpg` (headshot da galeria da central), anel `#E4602A`, sem selo de verificado | `Instragram-Videos/remotion/src/kit/SeloPerfil.tsx:5-8,17,24-27` |
| rosto permitido | só o do dono, pela galeria da central | `Instragram-Videos/.claude/rules/recriado.md:29,41` |
| voz | clonada do dono, ElevenLabs, `VOICE_ID` do ambiente | `Instragram-Videos/pipeline/tts.py:118`; `Instragram-Videos/.claude/rules/recriado.md:64-65` |
| ângulo editorial | "dono de software house" | `Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:71` |
| CTA | falado, seguir ou salvar, de `editorial/cta.md`; sem "comenta PALAVRA" | `Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:31,72` |
| estilo de texto | sem travessão; "você" | `Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:30` |
| textos literais nas cenas do exemplo | "ERP", "CRM", "CLÍNICA", "DECISÃO", "CONFIANÇA", "•••• 8429" etc. | `Instragram-Videos/remotion/src/reels/recriado-ia-decide/cenas.tsx:193,241,271,395` |
| licença | "decisão de compra é do Thulio" | `Instragram-Videos/.claude/rules/recriado.md:74-75` |
| canal/entrega | Instagram Reels, área segura da UI do Instagram | `Instragram-Videos/remotion/src/kit/anim.ts:13-16` |

## Fonte

- `Instragram-Videos/.claude/rules/recriado.md:1-93` — lido em 2026-09-24
- `Instragram-Videos/.claude/skills/gerar-reel-recriado/SKILL.md:1-149` — lido em 2026-09-24
- `Instragram-Videos/.claude/commands/new-video-recriado.md:1-13` — lido em 2026-09-24
- `Instragram-Videos/.claude/rules/central.md:11,33-37`, `Instragram-Videos/CLAUDE.md:29-37` — lidos em 2026-09-24
- `Instragram-Videos/remotion/src/{tema.ts,Legenda.tsx,kit/anim.ts,kit/SeloPerfil.tsx}`, `src/reels/recriado-ia-decide/{pecas.tsx,cenas.tsx}` — lidos em 2026-09-24
- `Instragram-Videos/videos/recriado-2026092*/revisao.md` — lidos em 2026-09-24
- `Instagram-Carrosseis/recriar.py:121-123,159-305,383,433-451,505-545,596-724` — lido em 2026-09-24
- `Instagram-Carrosseis/telegram_bot.py:203-204,319-320`, `Instagram-Carrosseis/reels.py:38-41`, `Instagram-Carrosseis/series/INDEX.json:827-846` — lidos em 2026-09-24
- `Instagram-Carrosseis/docs/reels-recriados-remotion/{00-DECISOES.md,00-AUDITORIA.md,base/00-LACUNAS.md}` — lidos em 2026-09-24
- `ExpxMedia/docs/contrato/CONTRATO-template.md:32-69` — lido em 2026-09-24
- Git: `Instragram-Videos` tem um único commit (`cc1e39d`, 2026-09-17, "Initial commit") e todo o formato recriado está
  fora do versionamento (`git status`: `pipeline/`, `remotion/`, `.claude/` não rastreados) — sem diff histórico a ler; executado em 2026-09-24
