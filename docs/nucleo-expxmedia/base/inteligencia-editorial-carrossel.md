# Inteligência editorial de carrossel e post (voz, gancho, CTA, visual, revisão, aprendizado)

O que decide **o conteúdo** de toda peça estática, separado da **forma** (que é do GUIA/template). Mora em `editorial/**` (decisões e resultados medidos) e nas skills `copy-artes-tech` e `legendas-tech` (método). Quando divergem, vale `editorial/`, "porque ela é a que muda com dado" (`Instagram-Carrosseis/editorial/README.md:34-36`). No núcleo, o método é genérico; voz, público, ofertas e aprendizados viram dado da Alma e do histórico da instalação.

## Contrato de entrada

Ordem de leitura obrigatória antes de escrever (`Instagram-Carrosseis/.claude/agents/copywriter.md:21-35`):
1. `editorial/voz.md`, `ganchos.md`, `cta.md`, `visual.md`, `aprendizados.md` ("Preferências em teste" já valem como direção; hipótese = preferência, regra validada = obrigação).
2. Regras do dono na daily (`python3 daily.py regras --serie <série>`), que valem **acima** de hipótese e preferência.
3. GUIA da série (forma: nº de slides, papel de cada slide, limites, glossário, campos).
4. O item e a copy dos 2–3 itens anteriores da mesma série (não repetir abertura).

Hierarquia de autoridade: daily do dono > regra validada > GUIA (na forma) > hipótese/preferência > skill (método) (`copywriter.md:29-39`, `Instagram-Carrosseis/.claude/rules/camada-editorial.md:6-8`). Conflito de forma: vence o GUIA naquele item e quem escreveu avisa; "ninguém altera o gerador para acomodar copy" (`editorial/README.md:30-32`).

Briefing aceito em linguagem natural; modelo opcional com `tema, formato (auto|post_estatico|carrossel), numero_slides, publico, nivel_tecnico, objetivo (educacao|autoridade|conversa_qualificada|leads|venda), consciencia, oferta{conteudo_confirmado, disponibilidade_confirmada, preco}, cta{acao, palavra_chave, entrega_confirmada}, provas_e_fontes, limites, modo_saida (publicacao|variacoes|auditoria|json)` (`Instagram-Carrosseis/.claude/skills/copy-artes-tech/SKILL.md:56-96`). Legenda: análogo, com `tamanho (curto|medio|longo)` (`Instagram-Carrosseis/.claude/skills/legendas-tech/SKILL.md:44-69`).

## Contrato de saída

- **Copy de arte**, modo publicação: `SLIDE N / Título / Texto / CTA` (rótulos não vão para a arte), todos os slides escritos, CTA só no fechamento (`copy-artes-tech/SKILL.md:292-318`); modo JSON: `{formato, publico, objetivo, tese, numero_slides, slides[{numero, tipo, titulo, texto, cta_texto}], cta{tipo, texto, destino, palavra_chave}, pronta_para_diagramar, pendencias[], fontes[]}` (`copy-artes-tech/SKILL.md:330-362`).
- **Legenda**: texto limpo, sem Markdown, sem rótulos, 3–6 blocos; JSON `{legenda, cta{...}, pronta_para_publicar, pendencias, fontes}` (`legendas-tech/SKILL.md:212-249`).
- **Retorno do copywriter** ao orquestrador: série/item, arquivo, leitor, tipo de gancho, forma do CTA e palavra, tese em uma frase, aprendizados aplicados, tensão com o GUIA (`copywriter.md:61-70`). Gancho e leitor **não** entram no catálogo; vão para `estado/geracoes.jsonl` via `fabrica.py` (`Instagram-Carrosseis/.claude/rules/camada-editorial.md:13-15`).
- **Revisão**: veredito `aprovado | ajustar`, tese, gancho (passa no teste da capa?), tabela `Slide | Campo | Gravidade | Achado | Sugestão`; achado bloqueante impede renderizar (`Instagram-Carrosseis/editorial/revisao.md:6-8`, `:47-56`).
- **Aprendizado** (só o `analista` escreve): entrada datada `Status (hipótese|validado|descartado) / Achado / Evidência / Origem / O que muda na escrita / Limite`, nova no topo, nada apagado (`Instagram-Carrosseis/editorial/aprendizados.md:1-27`).

## Limites e cotas

Faixas de densidade (referência editorial, GUIA prevalece) — `copy-artes-tech/SKILL.md:275-282`:

| Elemento | Título | Apoio | Conjunto preferido |
|---|---|---|---|
| Post estático | 4–11 palavras | 12–32; CTA 5–16 | ≤ 60 |
| Capa de carrossel | 4–11 | ≤ 18 | ≤ 28 |
| Slide de conteúdo | 3–9 | 18–42 | ≤ 50 |
| Slide final | 3–9 | breve + CTA | ≤ 45 |

| Regra numérica | Valor | Fonte |
|---|---|---|
| Capa: uma afirmação | até 20 palavras | `Instagram-Carrosseis/editorial/ganchos.md:31-32`, `revisao.md:35-36` |
| Carrossel padrão (ponto de partida) | 8 slides | `copy-artes-tech/SKILL.md:102`, `:166-177` |
| Não repetir estrutura de abertura na mesma série | 14 dias (bloqueante) | `ganchos.md:38-40`, `revisao.md:26-27` |
| Capas alternativas antes de escolher | ≥ 3 | `copywriter.md:45-46` |
| Leitor vê em média | ~2 slides (visualizações/alcance 1,9 a 2,6) | `aprendizados.md:212-218` |
| Legenda curta / média / longa | 300–600 / 700–1.300 / 1.400–1.900 caracteres | `legendas-tech/SKILL.md:218` |
| Recursos de linguagem por peça | 2 ou 3 | `copy-artes-tech/SKILL.md:205`, `legendas-tech/SKILL.md:128` |
| Hipótese vira regra | teste com diferença ≥ 30% consistente, ou repetição em 2 análises de janelas sem sobreposição | `aprendizados.md:8-12` |
| Abrir teste | vantagem ≥ 25% com amostra pequena; hipótese parada > 7 dias; queda em 3 análises; platô < 0,5 por 7 dias; fila < 3 | `Instagram-Carrosseis/editorial/testes-gatilhos.md:12-30` |
| Não abrir teste | fila ≥ 10, duas variáveis, repetido | `testes-gatilhos.md:34-40` |
| KPI de conta | comparar só coletas na mesma hora do dia (régua 5h30); magnitude sempre com data e hora | `aprendizados.md:116-122` |
| Alcance de post de feed | ~92% do alcance de 9 h fechado na 5ª hora | `aprendizados.md:140-146` |
| Palavra-chave: comentários que o teclado estraga | 14% (17/121 e 8/56) | `Instagram-Carrosseis/editorial/cta.md:32-35` |

## Erros conhecidos e tratamento

**Bloqueantes da revisão** (`revisao.md:9-30`): travessão em qualquer campo; palavra-chave do CTA ≠ bloco `publication`; arte e legenda com ação/palavra/promessa diferentes; número/benchmark sem fonte e condições, resultado ou experiência sem relato; urgência/desconto/bônus/garantia/vagas não confirmados; estrutura ou limite de caracteres fora do GUIA; termo contra o glossário; capa promete quantidade que a peça não entrega; erro técnico factual; item da lista "não entra" de `voz.md`; **palavra sem acento** na arte **ou na legenda** ("há", "ção", "ões", "você", "é"); primeira frase com a mesma estrutura de item da série nos últimos 14 dias; "tu/teu/tua/teus/tuas/contigo".

**Checagens mecanizáveis** (`Instagram-Carrosseis/.claude/agents/revisor-editorial.md:26-28`, `copywriter.md:59`): `grep -n "—\|–"` vazio; palavra-chave contra `publication`; contagem de caracteres contra o GUIA; contrato via `auditar-contrato`.

**Melhorias (não bloqueiam)** (`revisao.md:32-45`): teste da capa; uma afirmação ≤ 20 palavras, ressalva vai para o slide 2 ou legenda; slide 2 como segunda capa; razão para comentar antes do último slide; fecha com "comente PALAVRA"; cada slide puxa o próximo ("dá para embaralhar?"); uma tese só; texto que só cabe porque o motor encolheu; abertura parecida com os 3 anteriores.

**Proibições de voz** (`Instagram-Carrosseis/editorial/voz.md:22-35`): travessão; número como estatística solta ("número aqui é demonstração, benchmark só com fonte e condições"); experiência atribuída ao autor sem relato; urgência etc. sem confirmação; promessa de alcance/algoritmo; clichês listados ("desbloqueie seu potencial", "o futuro chegou", "isso muda tudo", "o segredo que ninguém conta"…) e a fórmula "não é sobre X, é sobre Y" como muleta; frases picotadas, caixa alta generalizada, excesso de exclamação, tom professoral; emoji e hashtag na arte.

**Método de escrita** (`copy-artes-tech/SKILL.md`):
- Princípio: promessa específica → entrega progressiva → mecanismo compreensível → valor para aquele leitor → próximo passo coerente (`:17`). A peça funciona sem a legenda (`:19`).
- Um leitor principal, uma tese, um CTA por peça (`:36`). Tabela de 5 leitores com situação e benefício (`:113-119`).
- Processo em 8 passos: entrega → tese → ângulo → argumento antes de cortar (capa por último) → sequência → CTA conectado → editar para a arte ("não resolva excesso sugerindo fonte menor") → auditar (`:127-134`).
- Teste da capa: assunto identificável, benefício/questão, promessa cabe, diferença concreta, funciona sem a sigla (`:152`); 7 ângulos com padrão de referência (`:140-148`).
- Arquitetura de 8 slides: capa, contexto com valor, mecanismo, desenvolvimento, demonstração, aplicação e limite, síntese/ponte, fechamento (`:168-177`); 9 regras de progressão (`:183-191`).
- Estruturas dominantes: demonstração técnica, PAS, AIDA, antes-depois-ponte, objeção-critério-demonstração (`:197-203`); recursos associados à PNL como instrumento, não controle (`:195`, `:205-214`).
- Substância: ≥ 1 mecanismo, exemplo, procedimento ou critério concreto por peça (`:218`); separar modelo/ferramenta/fluxo, contexto/treinamento, protótipo/solução, teste/cobertura (`:220`).
- CTA: ação + objeto/destino + razão; um por peça; "comente X que eu envio" exige material e entrega confirmados; "link na bio" só com destino confirmado (`:244-267`).
- 13 casos de aceitação (`:378-393`).

**Legenda** (`legendas-tech/SKILL.md`): **nunca link** — nem URL, domínio, encurtador, "link na bio", "acesse o link"; CTA vira ação sem link (`:28`, `:80`, `:172`); abertura com situação, contraste, consequência ou pergunta específica, sem "neste post você vai descobrir" (`:104`); 6 padrões de abertura com tensão técnica (`:145-150`); não encadear "curta, comente, salve, compartilhe e siga" (`:169`); não pedir dado pessoal em comentário (`:173`); mesma ação, palavra e promessa da arte (`:22`, `:79`).

**Aprendizados medidos (estado em 24/09/2026)**, todos com status explícito:
- Capa de uma frase com promessa comercial direta superou capa longa e cautelosa (hipótese; melhor post de 30 dias: 18 palavras, alcance 14.240, 703 salvamentos) (`aprendizados.md:172-178`, `ganchos.md:103-110`).
- "Comente PALAVRA" é o único CTA que gera conversa: 70 de 72 comentários; "link na bio" e "curta, salve e siga" com 0 (hipótese forte) (`aprendizados.md:180-186`, `cta.md:50-65`).
- Palavra-chave sobrevive ao teclado: palavra comum ganha; nada de letra dobrada; teclado pt-BR pluraliza (plural entra em `keywords`); palavra em inglês longa é corrigida inteira; lista de corruptelas continua obrigatória (`cta.md:32-48`).
- Razão para comentar e CTA visíveis cedo (slide 2 ou 3; nos reels, CTA na tela desde o 1º segundo: 4–8% comentam contra 0–3%) (`cta.md:25-31`).
- Capa dominada por número do item e tarja da série fica no fundo; a afirmação ocupa a área nobre, numeração é detalhe (`aprendizados.md:188-194`, `Instagram-Carrosseis/editorial/visual.md:12-16`).
- Gancho por molde repetido afunda (12 posts das 3 frases mais repetidas, índice 0,62); "a fórmula não condena, a repetição sim" (`aprendizados.md:196-202`, `ganchos.md:63-66`).
- Concreto antes de abstrato: robusto em vídeo (pulo nos 3 s 52–55% vs 62–70%); número nas 10 primeiras palavras **não** se reproduz nas capas (0,81 vs 1,00) ⇒ virou teste, não regra (`aprendizados.md:124-130`, `ganchos.md:45-62`).
- Slide 2 é a segunda capa (o carrossel ignorado volta ao feed aberto no slide 2) (`ganchos.md:41-44`).
- Tema claro vs escuro: hipótese enfraquecida, confundida com horário (`visual.md:21-29`).
- Volume alto derruba alcance por post de feed; menos post rende mais por post e menos no total (`aprendizados.md:162-171`).
- Cautela demais na capa custa alcance; "cena concreta vence conceito" (`voz.md:39-43`).
- Métrica nunca é estimada; sem CSV não há análise (`camada-editorial.md:16`); comparar dentro da mesma série antes de generalizar (`aprendizados.md:14-15`).

## Riscos para a nossa implementação

- **Perder a separação método × decisão × forma.** Se o núcleo embutir regras de `editorial/` no prompt da skill, um aprendizado deixa de "virar global mudando um arquivo" (`editorial/README.md:3-5`). No núcleo: método genérico no núcleo, decisões/aprendizados por instalação (histórico), forma no template.
- **Perder o ciclo hipótese → teste → regra** com critério numérico e registro de "descartado" (`aprendizados.md:6-12`, `testes-gatilhos.md`). Sem ele, a copy volta a seguir intuição e o sistema persegue ruído (motivação da carência de 3 dias, `Instagram-Carrosseis/fabrica.py:383-386`).
- **Perder o status do achado.** Muitos "achados" são hipótese fraca ou confundida (tema×hora, número×série). Extrair só "o que muda na escrita" sem o `Limite` transforma hipótese em regra (`aprendizados.md:124-130`, `visual.md:21-29`).
- **Perder as duas passadas de revisão e os bloqueantes mecanizáveis** (travessão, "tu", acento, palavra-chave ≠ `publication`, repetição de abertura em 14 dias). São baratos de automatizar e os que já causaram erro no ar (`revisao.md:23-30`, `voz.md:44-52`).
- **Acentuação**: é regra de revisão, não do motor; o motor da galeria não acentua. Geradores antigos corrigem por dicionário e corrompem inglês (`series/claude-code-features/gerar_carrossel.py:70-105`). Não portar o dicionário como "solução".
- **Enum de gancho**: os 7 tipos da origem (`ganchos.md:12-20`, `fabrica.py:290`) diferem do enum do contrato (`ExpxMedia/docs/contrato/CONTRATO-peca.md:172`). Sem mapeamento, a comparação de desempenho por tipo recomeça do zero.
- **Idioma e mercado fixos**: pt-BR, "sempre você", teclado pt-BR nas regras de palavra-chave (`voz.md:15-16`, `cta.md:40-41`). Alma em outro idioma precisa de variante das regras.
- **Acoplamentos de marca a virar dado da Alma:**
  - público "dono, gestor e equipe de software house; desenvolvedor e líder técnico; quem está entrando em IA e programação" (`voz.md:7-11`; tabela de leitores `copy-artes-tech/SKILL.md:113-119`, `legendas-tech/SKILL.md:86-92`) ⇒ `alma.publico`;
  - nicho "IA, programação e software houses" no papel da skill (`copy-artes-tech/SKILL.md:15`, `legendas-tech/SKILL.md:14`) ⇒ `alma.assunto`;
  - vozes por marca "Academia do Código… EXPX… Turbitenco" (`copy-artes-tech/SKILL.md:121`, `legendas-tech/SKILL.md:94`) ⇒ `alma.marcas[].voz`;
  - "Comente PALAVRA para receber o livro", automação de Direct no "Expx Flow" (`cta.md:7-15`) ⇒ `alma.ofertas` + capacidade de publicação;
  - conta `@thuliobittencourt`, séries e posts citados como referência de desempenho (`aprendizados.md:156-160`, `ganchos.md:103-110`) ⇒ histórico da instalação, nunca semente de outra marca;
  - "números de features, repositórios ou modelos são demonstração" (`copy-artes-tech/SKILL.md:228`) é regra do nicho de catálogo técnico ⇒ generalizar como "número do objeto ≠ estatística de mercado";
  - séries nomeadas em "Lugar desta skill neste repositório" (`copy-artes-tech/SKILL.md:23`) e caminhos `editorial/**`, `publicar/.env` citados dentro do prompt (`copy-artes-tech/SKILL.md:236`).
- **Referências externas como hipótese**: o que criadores ensinam (`cerebro/**`) e pautas de canais (`biblioteca/**`) são ponto de partida, nunca regra nem roteiro (`Instagram-Carrosseis/CLAUDE.md:14-24`); misturar com aprendizado medido destrói a confiança do sistema.

## Fonte

- `Instagram-Carrosseis/editorial/README.md`, `voz.md`, `ganchos.md`, `cta.md`, `visual.md`, `revisao.md`, `testes-gatilhos.md`, `aprendizados.md` (inteiros, lidos em 24/09/2026)
- `Instagram-Carrosseis/.claude/skills/copy-artes-tech/SKILL.md` (480 linhas), `.claude/skills/legendas-tech/SKILL.md` (341 linhas)
- `Instagram-Carrosseis/.claude/agents/copywriter.md`, `revisor-editorial.md`; `.claude/rules/camada-editorial.md`, `convencoes-gerais.md:22-26`
- `Instagram-Carrosseis/fabrica.py:290-296`, `:383-393`
- `Instagram-Carrosseis/series/claude-code-features/gerar_carrossel.py:33-105`
- Não lidos em detalhe (fora do recorte, outro agente): `editorial/cadencia.md`, `cadencia.json`, `testes.json`, `pendencias.json`, `editorial/analises/**`, `cerebro/**`, `biblioteca/**`
