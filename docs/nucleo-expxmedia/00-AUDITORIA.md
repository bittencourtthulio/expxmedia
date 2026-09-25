# Auditoria — nucleo-expxmedia

Data: 2026-09-24 (auditoria 1)

| severidade | arquivo | problema | correção sugerida |
|---|---|---|---|
| ALTA | sprint-04/tasks.md, sprint-05/tasks.md; base/montagem-reel-ffmpeg.md; base/legendar.md | Nenhuma task porta a montagem do reel a partir de página capturada (compose.py + stitch.py): rolagem 90–230 px/s (ideal 160) com espera de 3,5 s, cartão de impacto (2,5 s, 3 linhas, escada 150→72, desvio do rosto), selo de CTA a partir de 5 s, duração cortada no fim do último cartão, adelay com all=1, tira com teto 16384 px, marcadores visual.json/montado_em depois do MP4; nem a legenda PNG com card final de CTA (end.png 88→48, 2,2 s), palavra do CTA destacada, termo multi-palavra, escada 78→54 com base em 1499 e os erros de CTA. capturar_pagina fica sem consumidor e as checagens 7, 10 e 11 do verify sem artefato. | Nova fase com legendar/reel.py gerando caps PNG, end.png e legendas.json; video/montar_pagina.py portando compose/stitch com golden; T-04.02 exercitando 7–11. |
| MÉDIA | sprint-01/tasks.md (T-01.07) | Goldens listados não cobrem os que testes posteriores exigem (Alma do golden, medidas do encaixe, áudio falado, deck, transcrição e trecho de momentos, léxico); fontes do Google para paridade não têm origem offline. | Listar cada golden com origem; incluir alma-golden.json e fontes; teste de presença exige todos. |
| MÉDIA | ORQUESTRADOR.md §4; sprint-01/sprint.md | Pré-requisitos de rede não declarados: uv sync, chrome-headless-shell do Remotion, playwright install chromium, Google Fonts no golden, arquivos da Inter. | Declarar no §4 e criar task de preparação do ambiente com teste de presença. |
| MÉDIA | sprint-04 (T-04.07); sprint-06 (T-06.01, T-06.04) | faster-whisper consulta o Hugging Face e o bloqueio de socket pode derrubar o teste; modelo, HF_HUB_OFFLINE e cache não fixados. | Fixar modelo small, HF_HUB_OFFLINE=1 na fixture e testar transcrição com rede bloqueada. |
| MÉDIA | 00-DECISOES.md (D-34); sprint-05 (T-05.05, T-05.06); sprint-07 (T-07.05) | Áudio silencioso do provedor de teste não atinge −14 LUFS; perfil aula não existe na origem; T-05.06 com 150 palavras é inviável na faixa 50–70 s com o piso de ritmo. | D-NN trocando silêncio por sinal audível sintético; loudnorm na mistura final; checagens do perfil aula e faixa do reel narrado; ajustar T-05.06. |
| MÉDIA | sprint-04 (T-04.04, T-04.06); sprint-07 (T-07.05); base/aula-pipeline.md | Aula tem calibragem própria de voz (0.85/0.15/0.94, timeout 300 s) diferente do reel; piso de ritmo pode acelerar a aula. Contradição sem D-NN. | D-NN com parâmetros de voz por tipo de peça; ritmo mínimo não se aplica à aula, com teste. |
| MÉDIA | sprint-04 (T-04.02) | Teste da verificação só discrimina dimensão; implementação com 2 das 11 checagens passa. | Teste parametrizado com um artefato defeituoso por checagem. |
| MÉDIA | sprint-06 (T-06.05, T-06.08) | Haar cascade não detecta rosto desenhado; sem fixture de rosto neutra; suavização, fronteira tela/painel e gancho do corte sem teste. | Fixture de rosto com licença livre; teste de estabilidade; item para o gancho. |
| MÉDIA | sprint-06 (T-06.08); base/montagem-reel-ffmpeg.md risco 7 | O teste emenda a abertura no início do reel, formato descartado na base (abertura é fundo sobreposto, narração em 0). | Duração total igual à do reel sem abertura, narração em t=0, montado_em depois do MP4. |
| MÉDIA | sprint-06 (T-06.07) | Vídeo sintético falado precisa de fala real; binário say não declarado. | Declarar say ou reutilizar narração golden; comprimento mínimo. |
| MÉDIA | sprint-10 (T-10.03) | Aceite subjetivo e autoavaliado; vídeo de referência não declarado. | Nomear a referência e tornar o aceite binário (exit 0, validador sem achado, 9 seções não vazias, 3 prévias, evidência por item). |
| MÉDIA | sprint-09 (T-09.04 a T-09.08); base/inteligencia-editorial-carrossel.md | Testes de skill só procuram palavras; bloqueantes mecanizáveis não viram código. | Listas-âncora em tests/fixtures/inteligencia/*.json exigidas nas skills; subcomando revisar copy com os bloqueantes. |
| MÉDIA | sprint-02, sprint-04, sprint-08 fases.md | Paralelismo falso entre fases: F-02.3∥F-02.2 (T-02.13→T-02.07), F-04.2∥F-04.1 (T-04.03→T-04.01), F-04.3∥F-04.1 (T-04.10→T-04.01), F-08.2∥F-08.1 (T-08.05→T-08.01). | Remover ∥ ou mover as tasks dependentes. |
| MÉDIA | sprint-02, sprint-03, sprint-06 tasks.md | Tasks paralelas que precisam de dependência nova não declaram pyproject/uv.lock. | Declarar todas as dependências em T-01.01. |
| MÉDIA | base/imagens-retratos-e-ilustracoes.md; sprint-03 | Nenhuma task porta tratamento de retrato com rembg (u2net), filtros de banco, slot pessoa só com retrato do porta-voz, teto diário de custo. | Task em F-03.2 com os números de origem e cota por provedor. |
| MÉDIA | ORQUESTRADOR.md §7 (D-33) | Carregamento do plugin com claude --plugin-dir não é verificado. | Validar plugin.json/hooks.json contra o schema ou rodar claude --plugin-dir em modo não interativo. |
| BAIXA | sprint-05 (T-05.05, T-05.07, T-05.10) | Root.tsx alterado por fases paralelas sem declaração. | Registro por arquivo gerado, um só escritor. |
| BAIXA | sprint-03, 05, 07 (templates) | Templates listam só README.md em cria. | Listar os arquivos de cada template. |
| BAIXA | sprint-03 (T-03.05) | 1% de pixels sem tolerância por canal. | Tolerância ≤ 8/255 e mesma build de Chromium. |
| BAIXA | sprint-07 (T-07.01, T-07.04) | Cue que pula espaços e números L16/L9 (SAFE 168/280, PiP 272×340, topo 1318) sem teste. | Uma asserção para cada. |
| BAIXA | ORQUESTRADOR.md §3 | Sprints estritamente sequenciais; sprint-08 poderia correr em paralelo; T-10.02→T-10.01 desnecessária. | Relaxar o portão onde o depende_de permite. |
| BAIXA | sprint-01 (T-01.07) | git status das origens instável; goldens embutem conteúdo da marca de origem. | Comparar hash dos arquivos lidos; documentar licença dos goldens. |
| BAIXA | 00-DECISOES.md (D-13); base/galeria-layouts-e-validacao.md, base/publicar-meta-graph.md, base/api-heygen.md | Ingestão e adoção de layouts, cota da Graph (50×100), limite de áudio do HeyGen (10×30 min) e mapeamento do enum de gancho sem tratamento nem D-NN. | D-NN de exclusão/adiamento e limites conservadores. |

VEREDITO: NÃO — o plano não está pronto para execução autônoma.

---

# Auditoria — nucleo-expxmedia (reauditoria 2)

Data: 2026-09-24

Todos os achados ALTA e MÉDIA da auditoria 1 foram endereçados (G3/G4 parcialmente: fonte e cores sem tratamento).

| severidade | arquivo | problema | correção sugerida |
|---|---|---|---|
| ALTA | sprint-04 a 07, 09, 10 tasks.md | Nenhuma task expõe no CLI narrar, transcrever, legendar, verificar, produzir reel/reel-pagina/corte/apresentacao/aula e os passos da referência; skills ficam sem comando; T-10.03 usa verificar inexistente. | Registro de subcomandos por módulo; uma task de CLI por sprint. |
| ALTA | sprint-01 (T-01.05, T-01.08) | Dependência invertida: T-01.08 prepara o kit que T-01.05 cria, e T-01.05 depende de T-01.08; @fontsource/inter não declarado; lock exige rede. | T-01.08 depende de T-01.05; declarar @fontsource/inter; lock gerado com rede em T-01.05. |
| MÉDIA | sprint-01 (T-01.07), sprint-04 (T-04.08, T-04.11) | Paridade G3/G4 impossível: Arial Black do sistema e cores fixas na origem. | alma-golden-reel.json com fonte local só nos testes; D-NN de exceção. |
| MÉDIA | T-01.01 e testes | Arquivos de teste de mesmo nome em pastas diferentes quebram o pytest. | --import-mode=importlib. |
| MÉDIA | ORQUESTRADOR §3; sprints 05–07 | Sprint 08 paralela às 05–07 com critério de suíte inteira. | Critério por pasta nas sprints 05–08. |
| MÉDIA | sprint-03/fases.md | F-03.1 ∥ F-03.2 com T-03.09 → T-03.01. | Mover T-03.09. |
| MÉDIA | sprint-05; D-46 | Composições paralelas no mesmo kit quebram bundle e registro gerado. | Bundle por composição; registro atômico. |
| MÉDIA | T-05.03, T-05.05, T-07.06; §4 | Runner multi-versão implica rede durante a suíte. | Cache preparado em T-01.08; testes sem instalar. |
| MÉDIA | T-01.08 | Teste roda npm ci e uv sync a cada suíte. | Script separado; teste só confere presença. |
| MÉDIA | T-04.07, T-06.07 | Faltam modelo medium beam 5 no alinhamento e o recasamento. | Parametrizar modelos; task de recasamento. |
| MÉDIA | T-04.02, T-06.07 | Corte não tem card de CTA; perfil reel sem sem_cta. | Opção sem_cta. |
| MÉDIA | T-03.09, T-04.12 | site.md ≥ 1200, overlays, seções h1–h3 e gate do roteirista sem task. | Ampliar T-03.09 e gate do roteiro. |
| MÉDIA | T-09.11 | Âncoras sem cobertura mínima. | Categorias e mínimos nomeados. |
| MÉDIA | T-10.03, T-10.05 | Artefatos em instalação temporária não são achados pela suíte final. | Caminho persistente declarado. |
| BAIXA | sprint-10/sprint.md | "três relatórios", só dois criados. | Corrigir critério. |
| BAIXA | T-06.08 | Fixture de rosto criada em fase paralela; números do Haar da abertura ausentes. | Fixture antes; citar números. |
| BAIXA | T-02.01 | Colisão de ids em 1000 gerações; deduplicação não mencionada. | Especificar deduplicação. |
| BAIXA | T-03.14 | Testes não distinguem u2net/u2netp nem os filtros. | Asserções. |
| BAIXA | T-06.05 | Fronteira tela/painel sem teste. | Vídeo com divisão conhecida. |
| BAIXA | F-03.2, F-04.3 | __init__.py criado por task irmã paralela. | Criar antes. |
| BAIXA | D-34 | Não marcada como substituída por D-39. | Marcar. |
| BAIXA | T-04.07 | Reserva openai-whisper não instalada. | Simular módulo. |
| BAIXA | base/apresentacao-deck.md | Score ≥ 80 sem task nem D-NN. | D-NN de exclusão. |
| BAIXA | §3 | Sequencialidade desnecessária em 09, 06, 10. | Relaxar portões. |

VEREDITO: NÃO — o plano não está pronto para execução autônoma.

---

# Auditoria — nucleo-expxmedia (reauditoria 3)

Data: 2026-09-24

Todos os achados ALTA e MÉDIA da reauditoria 2 foram endereçados.

| severidade | arquivo | problema | correção sugerida |
|---|---|---|---|
| MÉDIA | sprint-04/sprint.md; §3; T-09.11 | Critério de suíte inteira na sprint 04 com F-09.1 paralela; test_ancoras exigindo itens em skills que só nascem na F-09.2. | Critério por pasta na sprint 04; test_ancoras valida só fixtures e verificador. |
| MÉDIA | T-01.05 | Pacotes @remotion/* não listados. | Listar bundler, renderer, cli, fonts, captions, layout-utils, react-dom, typescript, @types/react. |
| MÉDIA | T-04.02, T-06.04, T-06.07, D-41 | Perfil de corte da origem sem task (50–185 s, aviso > 75, cauda ≤ 0,80 s, cta nulo); D-41 baixa o piso do reel de página sem justificativa. | Perfil corte; D-NN sobre a faixa do reel de página. |
| MÉDIA | T-09.05, T-09.06, T-09.11 | Nenhuma skill conduz reel de página e abertura; roteiro do revisor do reel narrado sem task nem âncora. | Estender T-09.05 com revisor do reel e fixture de âncoras. |
| BAIXA | T-03.03 | Par #CCCCCC/branco não discrimina o limiar. | Pares 2,8:1 e 3,2:1. |
| BAIXA | T-01.08 | Script não baixa modelos exigidos pelo teste. | Incluir download. |
| BAIXA | §3 | Sprint 07 poderia rodar junto da 06. | Declarar exceção. |

VEREDITO: SIM — o plano está pronto para execução autônoma.

---

# Auditoria — nucleo-expxmedia (reauditoria 4)

Data: 2026-09-24

Todos os achados da reauditoria 3 foram endereçados; as mudanças não introduziram dependência inexistente, ciclo, paralelismo falso, escrita concorrente nem decisão humana em execução.

| severidade | arquivo | problema | correção sugerida |
|---|---|---|---|
| BAIXA | sprint-04/tasks.md (T-04.02) | Teste não discrimina os pisos da D-49 (reel_pagina 50 s, corte 50 s). | Um MP4 de 40 s passa em reel e recebe achado de duração em reel_pagina e corte. |
| BAIXA | 00-DECISOES.md (D-41) | D-41 não marcada como parcialmente substituída pela D-49. | Marcar. |

VEREDITO: SIM — o plano está pronto para execução autônoma.
