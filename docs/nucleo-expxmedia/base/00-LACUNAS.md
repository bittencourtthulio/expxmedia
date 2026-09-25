# Lacunas — nucleo-expxmedia

35 lacunas. Formato: `arquivo da base | o que não foi encontrado | onde procurou`.

- banco-imagens-pexels.md | Cota da API Pexels e headers X-Ratelimit não lidos | Instragram-Videos/pipeline/broll.py, Instagram-Carrosseis/galeria/_galeria.py, rules, testes
- transcrever-whisper.md | Download automático do modelo, uso de GPU, initial_prompt/glossário | Instragram-Videos/pipeline/transcrever.py, analisar_reel.py, CLAUDE.md
- corte-e-reenquadramento.md | Tempo de CPU da detecção de rosto; comportamento com ffmpeg < 8 | Instragram-Videos/pipeline/cut.py, rules, CLAUDE.md
- corte-e-reenquadramento.md | Testes do caminho de corte (só existe test_broll_sem_corte_orienta_o_baixar) | Instragram-Videos/tests/
- reel-recriado-analise.md | Leitura/referência que geraram recriado-ia-decide (sem analise/ nem recriado.json) | Instragram-Videos/videos/recriado-ia-decide/, pedidos da central
- renderizar-motion-remotion.md | Versão de Node exigida e tempo real de render do caminho sob medida | Instragram-Videos/remotion/package.json (sem .nvmrc)
- reel-recriado-analise.md | Versões de ffmpeg e faster-whisper travadas | Instragram-Videos/pipeline/ (sem requirements)
- reel-recriado-roteiro-e-cenas.md | Testes de montar-reel.mjs, audio.mjs e do caminho sob medida | Instragram-Videos/tests/
- inteligencia-reel-recriado.md | Histórico git do ajuste (formato recriado fora do versionamento, 1 commit) | git log/git status de Instragram-Videos
- publicar-expxflow.md | Rate limit da API Expx Flow e limites de vídeo do post-api | Instragram-Videos/docs/expx-flow/llms.txt, Instagram-Carrosseis (cópia do llms.txt)
- publicar-meta-graph.md | Especificação de vídeo dentro de carrossel e obtenção de token de longa duração | guia/referências Content Publishing da Meta
- publicar-meta-graph.md | Cota diária de publicação: fonte diz 50 num lugar e 100 em outro | referência content_publishing_limit e guia Content Publishing
- agendador-local-por-so.md | Tolerância de atraso antes de marcar falhou; acordar máquina (macOS/Windows) | CONTRATO-capacidades.md, docs de launchd/schtasks
- infra-estado-e-plano.md | Alternativa ao fcntl no Windows | ExpxMeta/estado.py, Instagram-Carrosseis/daily.py
- renderizar-html.md | Timeout e retry de set_content em galeria.renderizar | Instagram-Carrosseis/galeria/_galeria.py:1562-1641, GUIA claude-code
- renderizar-html.md | Tratamento real de color(srgb 0..1) no contraste (README diz que trata, código não reescala) | Instagram-Carrosseis/galeria/_galeria.py:1365-1372, testes
- producao-carrossel-e-post.md | Equivalentes de peca_id, criada_em, vaga, oferta, porta_voz, arquivos[].papel no sistema atual | Instagram-Carrosseis/fabrica.py, estado/geracoes.jsonl, series/INDEX.json
- galeria-layouts-e-validacao.md | Motivo das mudanças (commits em lote, ~20 arquivos de galeria não commitados) | git log / git status de Instagram-Carrosseis
- narrar-elevenlabs.md | Timeout HTTP, erro de rede fora de HTTPError, cota/preço ElevenLabs | Instragram-Videos/pipeline/tts.py, rule narracao/elevenlabs
- narrar-elevenlabs.md | Campo da Alma para léxico de pronúncia e ritmo aprovado por voz | docs/contrato/CONTRATO-alma.md
- legendar.md | Geração de SRT no pipeline de reel | Instragram-Videos/pipeline/captions.py, rules
- capturar-pagina.md | Comportamento em Playwright/headless (fonte usa Chrome do usuário via CDP) | Instragram-Videos/pipeline/capture*.py, rule captura/cdp
- inteligencia-roteiro-reel.md | Mapeamento dos tipos de gancho do reel para o enum gancho_tipo | rules, CONTRATO-peca.md
- harness-reel-agentes.md | Histórico de decisões no git (1 commit, quase tudo não rastreado) | git log de Instragram-Videos
- gravacao-de-tela.md | Comando ffmpeg completo de captura, script frames→concat.txt e marcas→marks-rel.json | cursos-ia/*/gravacao/, raw/*.log, READMEs dos episódios 06-09
- avatar-heygen-processo-atual.md | Por que a cópia para o HeyGen troca ID3 v2.4 por v2.3 e com qual comando; auth do MCP; créditos e tempo de geração | cursos-ia raw/, READMEs, plano-gravacao.md
- aula-pipeline.md | Tempo de render e custo ElevenLabs por aula; por que só a compilação usa --timeout=120000 | cursos-ia READMEs, package.json, logs
- apresentacao-deck.md | Origem das pastas órfãs placeholder/ e ...-mudou/ | youtube-squad/apresentacoes/decks/
- api-heygen.md | Validade da URL de download; créditos por minuto | https://developers.heygen.com/reference/get-video.md
- api-heygen.md | Doc contraditória: duração máxima de áudio (10 vs 30 min) e proporções | https://developers.heygen.com/docs/usage-limits.md
- api-pexels.md | Termos da API (403 ao acessar) e corpo dos erros | https://www.pexels.com/api/terms/
- cli-higgsfield.md | Doc oficial do CLI (só README e --help), rate limit, status possíveis | https://docs.higgsfield.ai/llms.txt (404)
- api-openrouter-imagem.md | Pixels por proporção; image_config do Gemini via chat | https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request.md
- playwright-render.md | Se evaluate e file:// funcionam com JS desligado e rede bloqueada | https://playwright.dev/python/docs/api/class-page
- remotion-render-e-licenca.md | Se a licença de quem distribui cobre renders feitos pelos clientes | https://www.remotion.dev/docs/terms
