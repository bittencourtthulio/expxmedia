# Inteligência de roteiro do reel (roteiro, CTA, veracidade, curadoria genérica)

Fonte extraída: regras `voz-e-cta.md`, `roteirista/estrutura.md`, `veracidade.md`, `performance.md`,
`curadoria*.md` e o agente `roteirista` de `Instragram-Videos/.claude/`, mais as partes genéricas de
`pick_repo.py`, `pick_llm.py`, `pick_release.py`. Não há script que escreva roteiro: quem escreve é um
agente LLM seguindo estas regras (`Instragram-Videos/.claude/skills/gerar-reel-repo/SKILL.md:28-29`).

## Contrato de entrada

- Fonte baixada da peça, **lida inteira**: `readme.md` + `repo.json` (repositório), `site.md` + `modelo.json`
  (LLM), `site.md` + `release.json` (release) (`Instragram-Videos/.claude/agents/roteirista.md:33-36`).
- `performance.md` (o que a conta mediu) é regra obrigatória do roteirista (`Instragram-Videos/.claude/agents/roteirista.md:26`).
- Decisão do plano sobre abertura e tipo (quando houver) (`Instragram-Videos/.claude/commands/new-video.md:30-33`).
- Opcional, só leitura: cérebro e biblioteca da central (`python3 ../Instagram-Carrosseis/cerebro.py buscar …`),
  valendo como hipótese; onde contradiz `performance.md`, vale `performance.md`
  (`Instragram-Videos/.claude/rules/central.md:41-57`).

## Contrato de saída

- `roteiro.txt` — texto puro, parágrafos separados por linha em branco (`Instragram-Videos/.claude/rules/roteirista/estrutura.md:92`).
- `cta.txt` — só a palavra, CAIXA ALTA, sem acento (`Instragram-Videos/.claude/rules/roteirista/estrutura.md:93`;
  `Instragram-Videos/.claude/rules/voz-e-cta.md:143`).
- `impacto.txt` — até 3 linhas curtas em CAIXA ALTA (`Instragram-Videos/.claude/rules/roteirista/estrutura.md:94-95`).
- `abertura.txt` — prompt em inglês, quando a abertura estiver ligada (`Instragram-Videos/.claude/agents/roteirista.md:77-98`).
- Peças de publicação: `legenda.txt` e `dm.json` (`keywords`, `match_mode: any`)
  (`Instragram-Videos/.claude/agents/roteirista.md:101-118`; `Instragram-Videos/.claude/rules/voz-e-cta.md:216-229`).
- Duas declarações obrigatórias ao concluir: **corpo** (afirmação → linha da fonte que a sustenta) e
  **gancho** (qual promessa + qual coisa concreta nas dez primeiras palavras)
  (`Instragram-Videos/.claude/agents/roteirista.md:133-143`).
- Para `peca.json`: `conteudo.gancho` (beat 1), `conteudo.gancho_tipo` (mapear "posse e receita / trabalho
  eliminado / dor + saída" para o enum — mapeamento NÃO DOCUMENTADO na fonte), `conteudo.cta`,
  `conteudo.cta_forma = "comentario"`, `conteudo.roteiro` e `conteudo.legenda` (caminhos).

## Limites e cotas

Estrutura em 6 beats, nesta ordem (`Instragram-Videos/.claude/rules/voz-e-cta.md:3-15`):
1. **Gancho** — promessa clara nos 3 primeiros segundos; nunca "Fala pessoal" nem o nome do repositório.
2. **O que é** — nome, quem fez, o que resolve, uma frase.
3. **Prova** — número concreto da fonte.
4. **Como usa** — linguagem, instalação, licença.
5. **Para quem** — frase de conexão com o público, **e termina aí** (emendar feature come o CTA).
6. **CTA** — comentário de **uma** palavra.

Voz: PT-BR, "você", frase curta, zero adjetivo vazio; 130–180 palavras (~60s); números **por extenso**;
sem emoji/markdown (`Instragram-Videos/.claude/rules/voz-e-cta.md:133-139`). Ler em voz alta; evitar sigla
soletrada no meio da frase (`Instragram-Videos/.claude/rules/roteirista/estrutura.md:85-88`).

Tipos de gancho, do mais forte ao mais fraco: **posse e receita** (embutir e cobrar, exige lastro de
licença) → **trabalho eliminado** → **dor + saída** na mesma frase; dor sem promessa não vai sozinha
(`Instragram-Videos/.claude/rules/voz-e-cta.md:17-29`).

**Teste das dez primeiras palavras** (≈3s a ~3,5 pal/s) — o achado mais forte da conta
(`Instragram-Videos/.claude/rules/voz-e-cta.md:31-50`; `Instragram-Videos/.claude/rules/performance.md:120-212`):
- Tem de nomear **uma coisa que dá para ver de olho fechado**; categoria ("sistema", "processo",
  "plataforma", "infraestrutura", "solução", "mudança", "mercado", "ciclo") e metáfora não passam.
  Medido: topo 52–56% de pulo nos 3s ("dez horas por semana", "lixo de terminal", "copiar dado de site
  na mão") × fundo 63–70% ("sistema de agentes com licença MIT", "processo de engenharia pronto")
  (`Instragram-Videos/.claude/rules/voz-e-cta.md:37-44`). Correlação de posto entre medições 0,96 e 0,973
  (`Instragram-Videos/.claude/rules/performance.md:171,190-191`).
- A coisa tem de ser **benefício ou dor, não inventário**: "diagrama de arquitetura" (visível, mas objeto
  que o time já tem) 71,8%; "vinte e uma aulas" 68,2% (`Instragram-Videos/.claude/rules/performance.md:195-199`).
- **Sem fração**: "um terço da conta de IA…" 69,1% — exige conta mental (`Instragram-Videos/.claude/rules/voz-e-cta.md:82-88`).
- Número concreto de dinheiro/quantidade na largada é o sinal mais forte **no corte** (4 melhores com
  número, 4 piores sem: 35,8% / 39,2% / 46,9% / 50,4%); no reel narrado o número sozinho não separou
  (média 59,2% × 58,4%, n=3) (`Instragram-Videos/.claude/rules/voz-e-cta.md:52-78`).
- Historinha de dor e promessa no fim do parágrafo gastam o gancho (64,5%) (`Instragram-Videos/.claude/rules/voz-e-cta.md:90-97`).
- Licença/jargão jurídico fora das dez palavras; lastro na frase seguinte (`Instragram-Videos/.claude/rules/voz-e-cta.md:49-50`).
- Status: **orientação, não gate** (`Instragram-Videos/.claude/rules/voz-e-cta.md:80`).

Veracidade (`Instragram-Videos/.claude/rules/veracidade.md:1-36`):
- Todo número, comparação e superlativo **dos beats 2 a 6** existe na fonte baixada; o revisor confere
  item por item citando a linha. **O beat 1 é isento** por decisão explícita do dono ("tira essas regras
  de veracidade, pois quero poder usar ganchos atrativos assim") (`Instragram-Videos/.claude/rules/veracidade.md:15-24`;
  `Instragram-Videos/.claude/rules/voz-e-cta.md:99-118`).
- Armadilhas genéricas: stars "mais de X", nunca exato; preservar o recorte do benchmark ("neste benchmark,
  contra estas"); idade por `created_at`; licença lida do dado, não do óbvio
  (`Instragram-Videos/.claude/rules/veracidade.md:97-104`); benchmark de página oficial é auto-declarado —
  atribuir ("a própria X mede") (`Instragram-Videos/.claude/rules/veracidade.md:55-58`); resumo de terceiro
  (descrição do OpenRouter) serve para curar, não para afirmar (`Instragram-Videos/.claude/rules/veracidade.md:65-67`);
  texto escrito pelos mantenedores (corpo do release) é fonte legítima (`Instragram-Videos/.claude/rules/veracidade.md:75-78`);
  depreciação ≠ quebra (`Instragram-Videos/.claude/rules/veracidade.md:88-89`); "crédito de autoria" (by @x in #123)
  não é prova (`:90-91`); fonte cortada na tela: prefira o que aparece (`:82-84`).
- Nenhum script confere veracidade (números por extenso impedem comparação automática) (`:26-30`).

Ângulo de revenda: posse/receita só com licença permissiva (MIT, Apache-2.0, BSD, ISC, Unlicense, 0BSD);
GPL/AGPL não; decidir pela licença, nunca pela ausência do eixo `revendavel` (regex de vocabulário)
(`Instragram-Videos/.claude/rules/voz-e-cta.md:120-131`; `Instragram-Videos/pipeline/pick_repo.py:33-34`).

**Palavra do CTA que sobrevive ao teclado do celular** (`Instragram-Videos/.claude/rules/voz-e-cta.md:150-214`):
- Até 8 letras, uma palavra; **ser** palavra do pt-BR, não quase ser (`LLAMA→Lama`); nenhuma letra dobrada
  (`DEER→Der`); sem `I`/`l` ambíguo; que se soletre de ouvido.
- Nome inventado/comprido → a coisa que ele faz em português (`coolify→SERVIDOR`, `archify→MAPA`).
- Medido: palavra que passa nos filtros perdeu 1,5–2,0% dos pedidos; que não passa, 9,9–13,1%
  (`Instragram-Videos/.claude/rules/voz-e-cta.md:158-176`; `Instragram-Videos/.claude/rules/performance.md:85-118`).
- `dm.json.keywords` no mínimo: a palavra; variante com espaço/hífen; nome completo; **plural em português**;
  2–3 corruptelas prováveis (tecla vizinha, letra dobrada a menos, `i` por `l`, palavra pt-BR vizinha);
  **sem a última letra**; tecla vizinha nas letras do meio. Nunca keyword genérica (`ia`, `link`, `eu`)
  (`Instragram-Videos/.claude/rules/voz-e-cta.md:216-229`).
- `cta.txt` é a fonte da verdade; a palavra tem de aparecer no roteiro (`:141-148`).

`impacto.txt` (cartão dos 2,5s iniciais) (`Instragram-Videos/.claude/rules/voz-e-cta.md:247-260`):
até 3 linhas, CAIXA ALTA, 2–3 palavras por linha; a coisa concreta do gancho (mesmo teste das dez palavras);
herda a isenção do gancho, mas licença/estrelas saem do dado; **não é CTA**.

`legenda.txt` do post (`Instragram-Videos/.claude/rules/voz-e-cta.md:270-313`): 1ª linha = CTA + promessa
concreta (75% nunca ouvem o CTA falado no segundo ~50; tempo assistido 6–16s —
`Instragram-Videos/.claude/rules/performance.md:247-265`); corpo com lista `→` (nome, licença, instalação,
número mais forte) para quem salvou (salvos/alcance ~5,2% no reel de repositório —
`Instragram-Videos/.claude/rules/performance.md:214-245`); fecha repetindo o CTA. Efeito da 1ª linha: **fraco,
confundido com a palavra** ("A palavra pesa, a linha é ruído") (`Instragram-Videos/.claude/rules/voz-e-cta.md:289-309`).

Onde procurar ganchos (`Instragram-Videos/.claude/rules/roteirista/estrutura.md:35-83`): tabela de benchmark
(comparação direta com ferramenta conhecida), seção de features, bloco de instalação ("como usa" em uma
linha), preço por milhão de tokens, janela de contexto traduzida ("a base de código inteira"), mudança que
quebra, ganho de desempenho com número; `fatos` do JSON é **conferência, não roteiro** (vira ficha técnica
falada). Beat 5 traduz vocabulário técnico em consequência de negócio.

Como ler métrica sem se enganar (`Instragram-Videos/.claude/rules/performance.md:37-55`): comparar por taxa
dentro da coorte; alcance < 150 não conclui nada (erro-padrão ~3,5 pontos com alcance 200); **abaixo de ~12h
de vida nem a taxa vale** (pulo andou −13,6 a +15,1 pontos em 10h); "média esconde distribuição"; cada achado
com grau de confiança; regra reabastecida por `/analise-reels`, inclusive para derrubar achados (achado 5 foi
derrubado — `:280-305`).

Curadoria genérica (o que não é marca):
- Piso de material: fonte com ≥ 1200 caracteres para sustentar 60s com prova
  (`Instragram-Videos/pipeline/pick_repo.py:120-121`; `Instragram-Videos/pipeline/pick_release.py:32-35`).
- Memória de uso: repositório e modelo nunca repetem; release repete a ferramenta mas não a tag
  (`Instragram-Videos/pipeline/pick_repo.py:165-166`; `Instragram-Videos/pipeline/pick_llm.py:265-280`;
  `Instragram-Videos/pipeline/pick_release.py:436-457`). Não repetir o mesmo autor/ferramenta antes de 3 vídeos
  (`Instragram-Videos/pipeline/pick_llm.py:28-30`; `Instragram-Videos/pipeline/pick_release.py:31`).
- Janela de novidade: 90 dias (modelo), 30 dias (release) (`Instragram-Videos/pipeline/pick_llm.py:27`;
  `Instragram-Videos/pipeline/pick_release.py:29`).
- Pontuação de potencial (`Instragram-Videos/pipeline/pick_repo.py:131-138`): tabela no README +20, número com
  unidade (ms, x faster, %, MB, GB) +15, "benchmark/comparison/vs" +10, bloco de código +10, stars/500 até 40.
  Release: novidade até +40, major +25/minor +15, corpo > 3000 +15, quebra +10, reações ≥ 200 +10
  (`Instragram-Videos/pipeline/pick_release.py:374-389`).
- Página oficial candidata é conferida com requisição real antes de virar fonte; mapa de sites é "lista de
  palpites"; nunca inventar URL (`Instragram-Videos/pipeline/pick_llm.py:43-49`).
- Assunto recusado pela regra não vira vídeo: "se a regra precisa mudar, muda-se a regra, não o caso"
  (`Instragram-Videos/CLAUDE.md:44-45`).

## Erros conhecidos e tratamento

| Erro medido | Correção registrada | Referência |
|---|---|---|
| Beat 5 emendado com feature | beat 5 termina na frase de conexão | `Instragram-Videos/.claude/rules/voz-e-cta.md:12-14` |
| CTA inferido pintando sigla | `cta.txt` obrigatório | `Instragram-Videos/.claude/rules/voz-e-cta.md:145-146` |
| `TRADINGAGENTS`, `LLAMA`, `DEER`, `VLLM`, `AUTOGPT`, `RUNX` destruídos pelo autocorretor | filtros + keywords de corruptela | `Instragram-Videos/.claude/rules/performance.md:57-83` |
| Revendabilidade decidida pelo regex de vocabulário | decidir pela licença | `Instragram-Videos/.claude/rules/voz-e-cta.md:126-131` |
| Algarismo no roteiro (TTS lê errado) | por extenso; gate do roteirista pega decimal | `Instragram-Videos/.claude/hooks/roteirista/stop-gate.sh:16` |
| Achado com < 12h / alcance < 150 | trava de leitura; achado 5 derrubado | `Instragram-Videos/.claude/rules/performance.md:43-52` |
| Dois posts no mesmo minuto (um afunda, fraco n=2) | não agendar no mesmo slot | `Instragram-Videos/.claude/rules/performance.md:374-385` |

## Riscos para a nossa implementação

Acoplamentos de marca (todos viram Alma ou dado de pack):
- Público "dono de software house" em toda a régua de gancho, beat 5 e curadoria
  (`Instragram-Videos/.claude/rules/voz-e-cta.md:5-15`; `Instragram-Videos/.claude/rules/roteirista/estrutura.md:15`)
  → `alma.publico`.
- Exemplos de gancho/CTA e as medições são **desta conta** (182.795–183.042 seguidores,
  `Instragram-Videos/.claude/rules/performance.md:7-21`). No núcleo, a **mecânica** (teste das dez palavras,
  filtros de teclado, trava de 12h/150, "média esconde distribuição") é genérica; os **números e exemplos**
  são aprendizados de uma Alma e precisam ir para o estado da instalação, não para código de pack.
- Copy "Comenta PALAVRA … para receber o link" e a mecânica comentário→DM → `alma.cta.variacoes` e
  capacidade `automacao_dm`.
- `DONO = "bittencourtthulio"` isenta a barreira de stars (`Instragram-Videos/pipeline/pick_repo.py:38-42`)
  → conta da Alma (`canais`).
- Barreira de marca do LLM (`roleplay|nsfw|…`) (`Instragram-Videos/pipeline/pick_llm.py:38-41`) →
  `alma.restricoes.temas_proibidos`.
- Lista `FERRAMENTAS` fechada é "posicionamento do canal" (`Instragram-Videos/CLAUDE.md:58-63`) → dado do pack.
- Idioma pt-BR e teclado pt-BR nos filtros do CTA → depende de `alma` (idioma não está no exemplo do contrato
  de Alma — NÃO DOCUMENTADO lá).

O que derruba a qualidade se extraído de forma ingênua:
1. **Tratar a lista de ganchos como gate** ou como receita fixa: a fonte insiste que é orientação medida e
   revisável; congelar derruba a capacidade de aprender.
2. **Perder a isenção do gancho / aplicar veracidade ao beat 1** → ganchos mornos (decisão do dono).
3. **Liberar o corpo junto com o gancho** → promessa sem lastro que queima autoridade.
4. **Perder as duas declarações do roteirista** → o revisor não tem o que auditar item por item.
5. **Copiar `fatos` do JSON em sequência** → ficha técnica falada.
6. **Escolher CTA pelo nome do repositório** sem os filtros → 5–7× mais leads perdidos.
7. **`dm.json` só com a palavra** → perde plural e corruptelas (4 leads de `tradingagents`).
8. **Concluir de métrica jovem** (<12h, alcance <150) → achados falsos (o achado 5 foi assim).
9. Stale: `roteirista.md:57` e skills ainda dizem "número é o sinal mais forte" sem sempre a ressalva do
   corte (`Instragram-Videos/.claude/skills/gerar-reel-repo/SKILL.md:103`) — a versão refinada está em
   `voz-e-cta.md:69-88`.

## Fonte

- `Instragram-Videos/.claude/rules/voz-e-cta.md` (1–319)
- `Instragram-Videos/.claude/rules/roteirista/estrutura.md` (1–97)
- `Instragram-Videos/.claude/rules/veracidade.md` (1–106)
- `Instragram-Videos/.claude/rules/performance.md` (1–450)
- `Instragram-Videos/.claude/rules/curadoria.md` (1–40), `central.md` (41–62)
- `Instragram-Videos/.claude/agents/roteirista.md` (1–143)
- `Instragram-Videos/pipeline/pick_repo.py` (18–166), `pick_llm.py` (20–75, 186–280), `pick_release.py` (25–40, 347–457)
- `Instragram-Videos/docs/performance/*.json` e `*-achados.json` (snapshots brutos; não lidos linha a linha)
- Testes: nenhum teste cobre regras de roteiro; o único gate executável é o stop-gate do roteirista.
