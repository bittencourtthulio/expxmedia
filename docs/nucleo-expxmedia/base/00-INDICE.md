---
expx_schema: 1
expx_tool: sprintx
kind: base_indice
trabalho_id: nucleo-expxmedia
atualizado_em: 2026-09-24
areas:
  - arquivo: abertura-higgsfield.md
    titulo: Abertura gerada com Higgsfield (capacidades `video_ia` e `rosto_ia`)
    lacunas: 0
  - arquivo: agendador-local-por-so.md
    titulo: Agendador local residente por sistema operacional (`agendar` via `meta_graph`)
    lacunas: 1
  - arquivo: api-elevenlabs.md
    titulo: ElevenLabs
    lacunas: 0
  - arquivo: api-heygen.md
    titulo: HeyGen
    lacunas: 2
  - arquivo: api-openrouter-imagem.md
    titulo: OpenRouter — geracao de imagem
    lacunas: 1
  - arquivo: api-pexels.md
    titulo: Pexels
    lacunas: 1
  - arquivo: apresentacao-deck.md
    titulo: Apresentacao- deck animado e palco (youtube-squad)
    lacunas: 1
  - arquivo: aula-pipeline.md
    titulo: Pipeline de aula (cursos-ia)
    lacunas: 1
  - arquivo: avatar-heygen-processo-atual.md
    titulo: Avatar HeyGen- processo atual (cursos-ia)
    lacunas: 1
  - arquivo: banco-imagens-pexels.md
    titulo: Banco de imagens — Pexels foto e video (capacidade `banco_imagens`)
    lacunas: 1
  - arquivo: capturar-pagina.md
    titulo: Capturar pagina (capacidade `capturar_pagina`)
    lacunas: 1
  - arquivo: cli-higgsfield.md
    titulo: Higgsfield (CLI `higgsfield`)
    lacunas: 1
  - arquivo: corte-e-reenquadramento.md
    titulo: Corte de video longo em reel (fonte, escolha do trecho, reenquadramento 9-16, montagem)
    lacunas: 2
  - arquivo: galeria-layouts-e-validacao.md
    titulo: Galeria de layouts- ingestao, decomposicao, validacao e adocao
    lacunas: 1
  - arquivo: gravacao-de-tela.md
    titulo: Gravacao de tela e edicao da demo (cursos-ia)
    lacunas: 1
  - arquivo: harness-reel-agentes.md
    titulo: Harness do reel (commands, skills, agents, hooks, rules)
    lacunas: 1
  - arquivo: imagens-retratos-e-ilustracoes.md
    titulo: Imagens da peca- retratos, ilustracoes de banco (Pexels), imagens geradas (OpenRouter) e Soul (Higgsfield)
    lacunas: 0
  - arquivo: infra-escrita-atomica.md
    titulo: Infraestrutura- escrita atomica, JSONL com trava e utilitarios (youtube-squad `comum.py`)
    lacunas: 0
  - arquivo: infra-estado-e-plano.md
    titulo: Infraestrutura de estado, plano do dia, validacao de contrato e padrao de painel
    lacunas: 1
  - arquivo: inteligencia-editorial-carrossel.md
    titulo: Inteligencia editorial de carrossel e post (voz, gancho, CTA, visual, revisao, aprendizado)
    lacunas: 0
  - arquivo: inteligencia-reel-recriado.md
    titulo: Inteligencia do reel recriado (regras de fidelidade, gates, licoes, marca e ponte com a central)
    lacunas: 1
  - arquivo: inteligencia-roteiro-reel.md
    titulo: Inteligencia de roteiro do reel (roteiro, CTA, veracidade, curadoria generica)
    lacunas: 1
  - arquivo: legendar.md
    titulo: Legendar (capacidade `legendar`)
    lacunas: 1
  - arquivo: montagem-reel-ffmpeg.md
    titulo: Montagem de reel com ffmpeg (capacidade `editar_video`)
    lacunas: 0
  - arquivo: narrar-elevenlabs.md
    titulo: Narrar com ElevenLabs (capacidade `narrar`)
    lacunas: 2
  - arquivo: playwright-render.md
    titulo: Playwright (Python)
    lacunas: 1
  - arquivo: producao-carrossel-e-post.md
    titulo: Producao de carrossel e post unico (fabrica, series, geradores, registro)
    lacunas: 1
  - arquivo: publicar-expxflow.md
    titulo: Publicacao pelo Expx Flow (provedor `expxflow` de `publicar`, `agendar`, `automacao_dm`)
    lacunas: 1
  - arquivo: publicar-meta-graph.md
    titulo: Publicacao direta pela Graph API da Meta (provedor `meta_graph` de `publicar` e `agendar`)
    lacunas: 2
  - arquivo: reel-recriado-analise.md
    titulo: Reel recriado- leitura do video de referencia
    lacunas: 2
  - arquivo: reel-recriado-roteiro-e-cenas.md
    titulo: Reel recriado- roteiro, cenas, linha do tempo e trilha
    lacunas: 1
  - arquivo: remotion-render-e-licenca.md
    titulo: Remotion — render e licenca
    lacunas: 1
  - arquivo: renderizar-html.md
    titulo: Renderizacao HTML → PNG (motor `galeria.renderizar`)
    lacunas: 2
  - arquivo: renderizar-motion-remotion.md
    titulo: Renderizar motion com Remotion (projeto, render, previa, normalizacao e gate)
    lacunas: 1
  - arquivo: transcrever-whisper.md
    titulo: Transcricao com tempo por palavra (capacidade `transcrever`)
    lacunas: 1
  - arquivo: tunel-url-publica.md
    titulo: URL publica temporaria por tunel (apoio de `publicar` e `agendar`)
    lacunas: 0
  - arquivo: verificar-reel-gates.md
    titulo: Verificacao e gates do reel
    lacunas: 0
---

# Índice da base — nucleo-expxmedia

37 arquivos, ingeridos em 2026-09-24 a partir de Instagram-Carrosseis, Instragram-Videos, cursos-ia, youtube-squad, ExpxMeta e da documentação oficial dos provedores.

| Arquivo | Área | Resumo |
|---|---|---|
| `abertura-higgsfield.md` | Abertura gerada com Higgsfield (capacidades `video_ia` e `rosto_ia`) | Abertura gerada (seedance/soul), instante em que o clipe vira a página, desvio do rosto, créditos |
| `agendador-local-por-so.md` | Agendador local residente por sistema operacional (`agendar` via `meta_graph`) | launchd, schtasks e systemd de usuário; trava de rotina; atraso |
| `api-elevenlabs.md` | ElevenLabs | TTS com timestamps, modelos, limites, concorrência, erros |
| `api-heygen.md` | HeyGen | API v3: upload de áudio, audio_asset_id, polling; v2 sai em 2026-10-31 |
| `api-openrouter-imagem.md` | OpenRouter — geração de imagem | Geração de imagem via OpenRouter (base64/data URL), proporções |
| `api-pexels.md` | Pexels | Busca de foto e vídeo, tamanhos, 200 req/h, licença sem redistribuição |
| `apresentacao-deck.md` | Apresentação: deck animado e palco (youtube-squad) | deck.json, 9 cenas Remotion, palco HTML, render.mjs, score, testes |
| `aula-pipeline.md` | Pipeline de aula (cursos-ia) | Roteiro [[sN]] → voz → whisper → legenda → Remotion L16/L9 → compilação |
| `avatar-heygen-processo-atual.md` | Avatar HeyGen: processo atual (cursos-ia) | Avatar a partir do áudio (processo manual atual), encaixe no PiP |
| `banco-imagens-pexels.md` | Banco de imagens — Pexels foto e vídeo (capacidade `banco_imagens`) | b-roll de vídeo e foto aprovada unificados em banco_imagens |
| `capturar-pagina.md` | Capturar página (capacidade `capturar_pagina`) | Captura por CDP de GitHub e sites, site.md, costura de rolagem |
| `cli-higgsfield.md` | Higgsfield (CLI `higgsfield`) | CLI 1.1.26: Soul 2.0, Seedance, login, validação por model get |
| `corte-e-reenquadramento.md` | Corte de vídeo longo em reel (fonte, escolha do trecho, reenquadramento 9:16, montagem) | Corte de vídeo longo, reenquadramento pelo rosto, screencast, gancho |
| `galeria-layouts-e-validacao.md` | Galeria de layouts: ingestão, decomposição, validação e adoção | Ingestão e decomposição de layouts, manifesto, validação, adotar |
| `gravacao-de-tela.md` | Gravação de tela e edição da demo (cursos-ia) | Gravador de navegador e VS Code, marcas de tempo, editar_demo |
| `harness-reel-agentes.md` | Harness do reel (commands, skills, agents, hooks, rules) | Comandos, skills, agentes, hooks e revisor do pipeline de reel |
| `imagens-retratos-e-ilustracoes.md` | Imagens da peça: retratos, ilustrações de banco (Pexels), imagens geradas (OpenRouter) e Soul (Higgsfield) | Retratos, Pexels, OpenRouter, Soul, rembg e os dois validadores |
| `infra-escrita-atomica.md` | Infraestrutura: escrita atômica, JSONL com trava e utilitários (youtube-squad `comum.py`) | comum.py: escrita atômica e jsonl com trava |
| `infra-estado-e-plano.md` | Infraestrutura de estado, plano do dia, validação de contrato e padrão de painel | JSONL com fcntl, plano do dia, validação por schema, token do painel |
| `inteligencia-editorial-carrossel.md` | Inteligência editorial de carrossel e post (voz, gancho, CTA, visual, revisão, aprendizado) | Voz, ganchos, CTA, visual, bloqueantes de revisão, ciclo de aprendizado |
| `inteligencia-reel-recriado.md` | Inteligência do reel recriado (regras de fidelidade, gates, lições, marca e ponte com a central) | O que se imita, checklist de parecença, lições de 24/09, acoplamentos |
| `inteligencia-roteiro-reel.md` | Inteligência de roteiro do reel (roteiro, CTA, veracidade, curadoria genérica) | 6 partes do roteiro, teste das 10 palavras, veracidade, palavra do CTA |
| `legendar.md` | Legendar (capacidade `legendar`) | Blocos de legenda por ritmo, desenho em PNG, card de CTA, legibilidade |
| `montagem-reel-ffmpeg.md` | Montagem de reel com ffmpeg (capacidade `editar_video`) | Rolagem, cartão de impacto, selo de CTA, loudnorm, emenda |
| `narrar-elevenlabs.md` | Narrar com ElevenLabs (capacidade `narrar`) | TTS com alinhamento por caractere, pronúncia, atempo, custos |
| `playwright-render.md` | Playwright (Python) | Screenshot com JS desligado, Chromium, bloqueio de rede via route |
| `producao-carrossel-e-post.md` | Produção de carrossel e post único (fábrica, séries, geradores, registro) | INDEX.json, fabrica.py, motores das séries, mapeamento para peca.json |
| `publicar-expxflow.md` | Publicação pelo Expx Flow (provedor `expxflow` de `publicar`, `agendar`, `automacao_dm`) | carousel-api e post-api, 207 parcial, DM, dry-run; carrossel só imagem |
| `publicar-meta-graph.md` | Publicação direta pela Graph API da Meta (provedor `meta_graph` de `publicar` e `agendar`) | Contêiner → status → media_publish; JPEG, 4:5..1.91:1, ≤10 itens; sem agendamento |
| `reel-recriado-analise.md` | Reel recriado: leitura do vídeo de referência | analisar_reel.py: scdet, quadros, folhas 6x2, whisper, leitura.md |
| `reel-recriado-roteiro-e-cenas.md` | Reel recriado: roteiro, cenas, linha do tempo e trilha | Caminho sob medida: cenas.json, âncoras, eventos, trilha, efeitos |
| `remotion-render-e-licenca.md` | Remotion — render e licença | CLI e renderMedia, Chrome, versão travada, licença v4/v5 |
| `renderizar-html.md` | Renderização HTML → PNG (motor `galeria.renderizar`) | Render Playwright sem JS, encaixe de texto, contraste no PNG, prancha |
| `renderizar-motion-remotion.md` | Renderizar motion com Remotion (projeto, render, prévia, normalização e gate) | Remotion 4.0.528, composições, prévia, normalização, verify recriado |
| `transcrever-whisper.md` | Transcrição com tempo por palavra (capacidade `transcrever`) | Whisper small/medium, formato ElevenLabs, recasar, fallback |
| `tunel-url-publica.md` | URL pública temporária por túnel (apoio de `publicar` e `agendar`) | cloudflared Quick Tunnel para URL pública temporária |
| `verificar-reel-gates.md` | Verificação e gates do reel | As 11 checagens do verify.py e os gates de saída |
