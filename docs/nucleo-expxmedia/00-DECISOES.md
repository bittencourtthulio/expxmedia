---
expx_schema: 1
expx_tool: sprintx
kind: decisoes
trabalho_id: nucleo-expxmedia
atualizado_em: 2026-09-24
decisoes:
  - id: D-01
    decisao: Motor, pipelines e producao em Python; Remotion como backend de motion; kit TypeScript so para composicoes
    alternativa_descartada: Reescrever tudo em TypeScript
    motivo: Usuario decidiu; o codigo que funciona hoje e Python
    status: fechada
    bloqueante: false
  - id: D-02
    decisao: Nada de marca no codigo; toda marca vem da Alma ou do .env; testes usam uma Alma ficticia
    alternativa_descartada: Manter valores do Thulio como padrao
    motivo: Usuario decidiu; produto generico e vendavel (M13)
    status: fechada
    bloqueante: false
  - id: D-03
    decisao: Nucleo entrega motor de capacidades e producao generica dos cinco tipos de peca; nenhum pack; capacidades de canal ficam fora
    alternativa_descartada: Criar expx-instagram junto
    motivo: Usuario decidiu; packs vem depois em cima do nucleo
    status: fechada
    bloqueante: false
  - id: D-04
    decisao: Nao perder a inteligencia atual; heuristicas portadas com os mesmos numeros e o processo do modelo vira skills agentes e regras versionados no nucleo
    alternativa_descartada: Extrair so os scripts
    motivo: Usuario exigiu; a fidelidade do recriado mora no processo do modelo
    status: fechada
    bloqueante: false
  - id: D-05
    decisao: Template e reel de video levam codigo Remotion proprio com versao travada
    alternativa_descartada: Cenas declarativas sobre biblioteca fixa
    motivo: Usuario exigiu video igual ao original
    status: fechada
    bloqueante: false
  - id: D-06
    decisao: Carrossel misto e gerado e o adaptador Expx Flow envia filho de video assumindo que o servidor aceita
    alternativa_descartada: Bloquear carrossel misto no Expx Flow
    motivo: Usuario decidiu; se nao aceitar implementa depois no Expx Flow
    status: fechada
    bloqueante: false
  - id: D-07
    decisao: Publicacao por expxflow ou meta_graph com PROVEDOR_PUBLICAR no .env e sem troca silenciosa de provedor
    alternativa_descartada: Um provedor so
    motivo: Usuario decidiu
    status: fechada
    bloqueante: false
  - id: D-08
    decisao: Agendar via meta_graph usa agendador Python local instalado por sistema operacional
    alternativa_descartada: Exigir Expx Flow para agendar
    motivo: Usuario decidiu
    status: fechada
    bloqueante: false
  - id: D-09
    decisao: Sem campo de consentimento de porta-voz
    alternativa_descartada: Consentimento obrigatorio
    motivo: Usuario decidiu
    status: fechada
    bloqueante: false
  - id: D-10
    decisao: Repo com motor/ (pacote python expxmedia), motor/kit-remotion/ (kit TS), nucleo/ (plugin Claude Code) e templates/ (templates embarcados)
    alternativa_descartada: Varios repositorios separados
    motivo: Autonomia autorizada; um repo facilita versao unica do nucleo
    status: fechada
    bloqueante: false
  - id: D-11
    decisao: CLI expxmedia-motor com subcomandos por capacidade e por producao, entrada e saida JSON; skills chamam o CLI
    alternativa_descartada: Skills importando modulos python diretamente
    motivo: Autonomia autorizada; contrato estavel entre prompt e codigo e testavel
    status: fechada
    bloqueante: false
  - id: D-12
    decisao: Escopo inclui estado rastro ids alma ambiente capacidades peca template galeria local producao dos cinco tipos reel por referencia corte de video longo aula apresentacao publicacao agendador hooks de portao e segredo
    alternativa_descartada: So a biblioteca do motor
    motivo: Autonomia autorizada; sem skills e portao o nucleo nao produz sozinho
    status: fechada
    bloqueante: false
  - id: D-13
    decisao: Fora do escopo CLI instalador TS painel galeria compartilhada packs metricas plano do dia curadoria de pautas telegram gravacao automatizada de tela anuncios
    alternativa_descartada: Incluir parte da central
    motivo: Autonomia autorizada; ordem de construcao definida com o usuario
    status: fechada
    bloqueante: false
  - id: D-14
    decisao: Python 3.11 minimo com uv e pytest; suite offline com rede bloqueada; provedores testados contra stub HTTP local; binarios reais em testes marcados integracao_local
    alternativa_descartada: Testes chamando APIs reais
    motivo: Autonomia autorizada; padrao do Instragram-Videos (conftest bloqueia rede)
    status: fechada
    bloqueante: false
  - id: D-15
    decisao: Nenhuma chamada paga nem publicacao real na execucao; publicacao so em dry-run ou stub
    alternativa_descartada: Validar com chaves reais do usuario
    motivo: Autonomia autorizada; custo e acao externa nao pedidos
    status: fechada
    bloqueante: false
  - id: D-16
    decisao: Paridade verificada por testes golden comparando saida do nucleo com a do sistema atual nas mesmas entradas
    alternativa_descartada: Confiar em revisao visual
    motivo: Autonomia autorizada; prova mecanica de que a qualidade nao caiu
    status: fechada
    bloqueante: false
  - id: D-17
    decisao: Remotion com runner multi versao e cache por versao fora do projeto; kit base em 4.0.528 com React 19.3.0; fps numa constante unica do kit
    alternativa_descartada: Uma versao global do Remotion
    motivo: Autonomia autorizada; tres versoes coexistem hoje e o contrato trava versao por template
    status: fechada
    bloqueante: false
  - id: D-18
    decisao: Reel por referencia porta o caminho sob medida completo; tipos fixos legados nao sao portados
    alternativa_descartada: Portar roteiro_remotion e os sete tipos fixos
    motivo: Autonomia autorizada; tipos fixos foram reprovados pelo dono como genericos
    status: fechada
    bloqueante: false
  - id: D-19
    decisao: montar-reel.mjs e audio.mjs continuam em JavaScript dentro do kit, generalizados, com o mesmo PRNG e a mesma semente
    alternativa_descartada: Reescrever em Python
    motivo: Autonomia autorizada; preservar determinismo exato da trilha e da linha do tempo
    status: fechada
    bloqueante: false
  - id: D-20
    decisao: Render HTML porta galeria.renderizar com os mesmos limiares, tokens --alma-* e contraste medido no PNG
    alternativa_descartada: Reescrever o renderizador
    motivo: Autonomia autorizada; heuristicas calibradas em casos reais
    status: fechada
    bloqueante: false
  - id: D-21
    decisao: Toda fonte vem da Alma via Google Fonts em cache local; fonte padrao do motor e Inter embarcada; fontes de sistema proibidas
    alternativa_descartada: Manter Arial Black Rockwell e fontes do macOS
    motivo: Autonomia autorizada; fontes de sistema quebram fora do macOS e sao marca
    status: fechada
    bloqueante: false
  - id: D-22
    decisao: Narracao ElevenLabs with-timestamps com alinhamento no espaco do roteiro; parametros e lexico de pronuncia no porta-voz da Alma com padroes iguais aos atuais
    alternativa_descartada: Parametros fixos no codigo
    motivo: Autonomia autorizada; lexico e ritmo sao da voz de cada empresa
    status: fechada
    bloqueante: false
  - id: D-23
    decisao: Legenda sempre com texto do roteiro e tempos do TTS ou do whisper; blocos por ritmo no reel; 42 caracteres por 2 linhas na aula; SRT sempre gerado
    alternativa_descartada: Legenda pela transcricao direta
    motivo: Autonomia autorizada; transcricao direta erra nomes e numeros
    status: fechada
    bloqueante: false
  - id: D-24
    decisao: Transcricao com faster-whisper preferencial e openai-whisper de reserva; idioma da Alma
    alternativa_descartada: Idioma fixo pt
    motivo: Autonomia autorizada; empresa pode nao ser brasileira
    status: fechada
    bloqueante: false
  - id: D-25
    decisao: Captura de pagina com Playwright headless proprio
    alternativa_descartada: Chrome do usuario via CDP
    motivo: Autonomia autorizada; produto generico nao pode depender do navegador pessoal
    status: fechada
    bloqueante: false
  - id: D-26
    decisao: Avatar HeyGen API v3 sempre a partir do audio
    alternativa_descartada: API v2 ou avatar a partir do texto
    motivo: Autonomia autorizada; v2 sai do ar em 2026-10-31 e texto perde sincronia
    status: fechada
    bloqueante: false
  - id: D-27
    decisao: Higgsfield pelo CLI com parametros validados por model get antes de cada uso
    alternativa_descartada: Parametros fixos no codigo
    motivo: Autonomia autorizada; parametros mudam no servidor
    status: fechada
    bloqueante: false
  - id: D-28
    decisao: Pexels com PEXELS_API_KEY; foto e video pelo mesmo modulo; midia do Pexels nunca entra em template
    alternativa_descartada: Manter PEXELS_APIKEY e dois modulos
    motivo: Autonomia autorizada; licenca nao permite redistribuir
    status: fechada
    bloqueante: false
  - id: D-29
    decisao: POST de publicacao nunca retentado automaticamente; intencao gravada na peca antes do envio; Graph converte PNG em JPEG e valida proporcao e itens; midia servida por tunel cloudflared temporario
    alternativa_descartada: Retry generico em 5xx
    motivo: Autonomia autorizada; retry duplica publicacao
    status: fechada
    bloqueante: false
  - id: D-30
    decisao: Agendador verifica a cada minuto e publica ate 15 minutos depois do horario; depois disso marca falhou com motivo; trava com filelock
    alternativa_descartada: Publicar atrasado ao acordar
    motivo: Autonomia autorizada; contrato proibe publicar atrasado em silencio
    status: fechada
    bloqueante: false
  - id: D-31
    decisao: Galeria local minima no nucleo com ao menos um template embarcado por tipo neutralizado a partir dos atuais
    alternativa_descartada: Nucleo sem templates
    motivo: Autonomia autorizada; sem template o nucleo nao produz sozinho
    status: fechada
    bloqueante: false
  - id: D-32
    decisao: Aula aceita gravacao de tela como entrada e edita por cues; automacao de gravacao fica fora
    alternativa_descartada: Portar osascript e automacao do VS Code
    motivo: Autonomia autorizada; depende da maquina e do teclado do dono
    status: fechada
    bloqueante: false
  - id: D-33
    decisao: Plugin do nucleo chama expxmedia e e usavel em desenvolvimento com claude --plugin-dir nucleo
    alternativa_descartada: Esperar o instalador da central
    motivo: Autonomia autorizada; permite usar o nucleo antes da central
    status: fechada
    bloqueante: false
  - id: D-34
    decisao: Provedor de teste para narrar e avatar habilitado so por EXPXMEDIA_PROVEDORES_TESTE=1 (audio silencioso substituido por D-39)
    alternativa_descartada: Pular narracao nos testes
    motivo: Autonomia autorizada; validar pipeline narrado sem gastar credito
    status: fechada
    bloqueante: false
  - id: D-35
    decisao: Pronto quando a suite esta verde, a varredura de marca esta limpa e a Alma ficticia produz os cinco tipos sem chave com publicacao em dry-run
    alternativa_descartada: Pronto por revisao manual
    motivo: Autonomia autorizada; criterio binario
    status: fechada
    bloqueante: false
  - id: D-36
    decisao: Codigo de reel por referencia pode usar cores literais da paleta da referencia; marca, fontes e selo vem da Alma; validador de imports e APIs proibidas vale igual
    alternativa_descartada: Exigir so tokens da Alma no reel por referencia
    motivo: Autonomia autorizada na F3; o recriado imita o clima de cor da referencia e nao e marca
    status: fechada
    bloqueante: false
  - id: D-37
    decisao: Nenhuma task escreve nos projetos de origem; goldens e portes leem de la e executam em copia temporaria
    alternativa_descartada: Rodar scripts antigos no lugar
    motivo: Autonomia autorizada na F3; montar-reel.mjs reescreve registro.ts e public/ do projeto de origem
    status: fechada
    bloqueante: false
  - id: D-38
    decisao: Reel a partir de pagina capturada (rolagem, cartao de impacto, selo de CTA, legenda PNG, card final) entra no nucleo como producao de reel
    alternativa_descartada: Deixar o formato para um pack
    motivo: Auditoria 1 achado ALTA; captura e verificacao ficariam sem consumidor; formato e generico
    status: fechada
    bloqueante: false
  - id: D-39
    decisao: Provedor de teste de narracao gera sinal audivel sintetico por palavra e o loudnorm mede a mistura final
    alternativa_descartada: Audio silencioso
    motivo: Silencio nao atinge -14 LUFS; auditoria 1
    status: fechada
    bloqueante: false
  - id: D-40
    decisao: Parametros de voz por tipo de peca no porta-voz; padrao reel 0.45 0.8 0.25 speed 1.2 e aula similarity 0.85 style 0.15 speed 0.94 timeout 300; ritmo minimo so no reel
    alternativa_descartada: Um conjunto unico por porta-voz
    motivo: A aula tem calibragem propria na origem
    status: fechada
    bloqueante: false
  - id: D-41
    decisao: Perfis de verificacao (faixa de duracao SUBSTITUIDA em parte por D-49) reel 30 a 70 s; aula 1920x1080 e 1080x1920 30 fps h264 aac -14 LUFS pico -1 com SRT; sob_medida como na origem
    alternativa_descartada: Perfil aula indefinido
    motivo: A origem nao tem verify de aula; auditoria 1
    status: fechada
    bloqueante: false
  - id: D-42
    decisao: Todas as dependencias Python declaradas em T-01.01 e uma task de preparacao do ambiente com rede usada uma vez; sem rede vira bloqueio
    alternativa_descartada: Cada task acrescenta dependencia
    motivo: Evita escrita concorrente em pyproject e uv.lock; auditoria 1
    status: fechada
    bloqueante: false
  - id: D-43
    decisao: Fixture de rosto gerada de skimage.data.astronaut (dominio publico) e fala sintetica com say do macOS para os testes de corte
    alternativa_descartada: Rosto desenhado e video sem fala
    motivo: Haar nao detecta rosto desenhado; whisper precisa de fala
    status: fechada
    bloqueante: false
  - id: D-44
    decisao: Limites conservadores: Graph 50 publicacoes em 24 h conferido em content_publishing_limit; HeyGen audio ate 10 min; ingestao e adocao de layouts de referencia ficam para a camada galeria
    alternativa_descartada: Nao tratar
    motivo: Base registra fontes contraditorias; auditoria 1
    status: fechada
    bloqueante: false
  - id: D-45
    decisao: Bloqueantes mecanizaveis de copy viram o subcomando revisar copy parametrizado pela Alma, e as skills sao testadas contra listas-ancora extraidas da origem
    alternativa_descartada: Testar skills so por palavras
    motivo: Auditoria 1; bloqueantes ja causaram erro no ar
    status: fechada
    bloqueante: false
  - id: D-46
    decisao: Root do kit importa um registro gerado das pastas src/composicoes; nenhuma task edita o Root
    alternativa_descartada: Cada task edita o Root
    motivo: Evita escrita concorrente entre fases paralelas
    status: fechada
    bloqueante: false
  - id: D-47
    decisao: Goldens de legenda e montagem do reel de pagina usam alma-golden-reel com a fonte local do sistema usada na origem, so nos testes e sem copiar a fonte para o repositorio
    alternativa_descartada: Paridade impossivel ou fonte de sistema no codigo
    motivo: Reauditoria 2; D-21 continua valendo para o codigo do nucleo
    status: fechada
    bloqueante: false
  - id: D-48
    decisao: Score de viralizacao de pauta antes do render de apresentacao fica fora do nucleo e vai para a curadoria do pack
    alternativa_descartada: Portar o score no nucleo
    motivo: Reauditoria 2; score depende da estrategia de canal (D-13)
    status: fechada
    bloqueante: false
  - id: D-49
    decisao: Faixas de duracao por perfil iguais as da origem - reel de pagina 50 a 70 s, corte 50 a 185 s com aviso acima de 75 s, reel narrado em Remotion e recriado 30 a 70 s
    alternativa_descartada: Uma faixa unica de 30 a 70 s para todo reel
    motivo: Reauditoria 3; a origem calibrou cada formato separadamente
    status: fechada
    bloqueante: false
  - id: PENDENTE-01
    decisao: Licenca do Remotion para empresas clientes que renderizam
    alternativa_descartada: null
    motivo: null
    status: pendente
    bloqueante: false
  - id: PENDENTE-02
    decisao: Expx Flow aceitar video como filho de carrossel
    alternativa_descartada: null
    motivo: null
    status: pendente
    bloqueante: false
---

# Decisões — nucleo-expxmedia

> O usuário autorizou explicitamente planejar e executar este trabalho de forma autônoma e pediu para ser consultado só no fim ("pode executar tudo de forma autônoma e só fala comigo agora quando você terminar"). Por isso a F2 não teve entrevista: **D-01 a D-09 são respostas dadas pelo usuário na conversa que definiu os contratos**; **D-10 a D-35 foram tomadas pela skill sob essa autorização**, com base em `base/`, e estão marcadas assim. As duas pendências são não bloqueantes pela mesma autorização, com a premissa registrada.

## Decisões

```
D-01 | Motor, pipelines e produção em Python; Remotion como backend de motion; kit TypeScript só para composições | reescrever tudo em TypeScript | usuário decidiu; o código que funciona hoje é Python
D-02 | Nada de marca no código; toda marca vem da Alma ou do .env; testes usam uma Alma fictícia | manter valores do Thulio como padrão | usuário decidiu; M13
D-03 | Núcleo = motor de capacidades + produção genérica dos cinco tipos; nenhum pack; capacidades de canal fora | criar expx-instagram junto | usuário decidiu
D-04 | Não perder a inteligência: heurísticas com os mesmos números; o processo do modelo vira skills, agentes e regras versionados | extrair só os scripts | usuário exigiu; a fidelidade do recriado mora no processo (base/inteligencia-reel-recriado.md, risco 1)
D-05 | Template e reel de vídeo levam código Remotion próprio com versão travada | cenas declarativas | usuário exigiu vídeo igual
D-06 | Carrossel misto é gerado; adaptador Expx Flow envia filho de vídeo assumindo aceite | bloquear | usuário decidiu (base/publicar-expxflow.md mostra que hoje só aceita imagem)
D-07 | expxflow ou meta_graph, PROVEDOR_PUBLICAR no .env, sem troca silenciosa | um provedor só | usuário decidiu
D-08 | Agendar via meta_graph usa agendador Python local por SO | exigir Expx Flow | usuário decidiu
D-09 | Sem campo de consentimento de porta-voz | consentimento obrigatório | usuário decidiu
D-10 | (autônoma) Repo: motor/ (pacote python `expxmedia`), motor/kit-remotion/ (kit TS), nucleo/ (plugin Claude Code), templates/ (embarcados) | vários repositórios | versão única do núcleo
D-11 | (autônoma) CLI `expxmedia-motor` com subcomandos por capacidade e produção, entrada/saída JSON; skills chamam o CLI | skills importando Python | contrato estável e testável entre prompt e código
D-12 | (autônoma) Escopo: estado, rastro, ids, Alma, ambiente, capacidades, peça, template, galeria local, produção dos 5 tipos, reel por referência, corte de vídeo longo, aula, apresentação, publicação, agendador, hooks de portão e segredo | só a biblioteca | sem skills e portão o núcleo não produz sozinho
D-13 | (autônoma) Fora: CLI instalador TS, painel, galeria compartilhada, packs, métricas, plano do dia, curadoria de pautas, Telegram, gravação automatizada de tela, anúncios | incluir parte da central | ordem de construção combinada
D-14 | (autônoma) Python ≥ 3.11, uv, pytest; suíte offline com rede bloqueada; provedores contra stub HTTP local; binários reais em testes `integracao_local` | testes com APIs reais | padrão do Instragram-Videos (base/verificar-reel-gates.md)
D-15 | (autônoma) Nenhuma chamada paga nem publicação real na execução; publicação só em dry-run/stub | validar com chaves do usuário | custo e ação externa não pedidos
D-16 | (autônoma) Paridade por testes golden: saída do núcleo × saída do sistema atual nas mesmas entradas | revisão visual | prova mecânica de que a qualidade não caiu
D-17 | (autônoma) Remotion multi-versão, cache por versão fora do projeto; kit base 4.0.528 + React 19.3.0; fps em constante única | versão global | três versões coexistem hoje (base/aula-pipeline.md, base/apresentacao-deck.md, base/renderizar-motion-remotion.md)
D-18 | (autônoma) Reel por referência porta o caminho sob medida completo; tipos fixos não | portar os 7 tipos | reprovados como genéricos (base/reel-recriado-roteiro-e-cenas.md)
D-19 | (autônoma) montar-reel.mjs e audio.mjs seguem em JS no kit, generalizados, com o mesmo PRNG e semente | reescrever em Python | determinismo exato (base/reel-recriado-roteiro-e-cenas.md, risco 5)
D-20 | (autônoma) Render HTML porta galeria.renderizar com os mesmos limiares, tokens --alma-*, contraste no PNG | reescrever | heurísticas calibradas (base/renderizar-html.md)
D-21 | (autônoma) Fontes da Alma via Google Fonts em cache; padrão Inter embarcada; fonte de sistema proibida | Arial Black/Rockwell | quebram fora do macOS
D-22 | (autônoma) ElevenLabs with-timestamps, alinhamento no espaço do roteiro; parâmetros e léxico no porta-voz da Alma, padrões = valores atuais | parâmetros fixos | base/narrar-elevenlabs.md
D-23 | (autônoma) Legenda = texto do roteiro + tempos; blocos por ritmo no reel; 42×2 na aula; SRT sempre | transcrição direta | base/aula-pipeline.md, base/legendar.md
D-24 | (autônoma) faster-whisper preferencial, openai-whisper reserva; idioma da Alma | idioma fixo pt | empresa pode não ser brasileira
D-25 | (autônoma) Captura com Playwright headless próprio | Chrome do usuário via CDP | produto genérico
D-26 | (autônoma) HeyGen API v3, sempre a partir do áudio | v2 ou texto | v2 sai em 2026-10-31 (base/api-heygen.md)
D-27 | (autônoma) Higgsfield pelo CLI, parâmetros validados por `model get` | parâmetros fixos | base/cli-higgsfield.md
D-28 | (autônoma) PEXELS_API_KEY; foto e vídeo num módulo; mídia do Pexels nunca em template | PEXELS_APIKEY, dois módulos | base/api-pexels.md (licença)
D-29 | (autônoma) POST de publicação nunca retentado; intenção gravada na peça antes; Graph: PNG→JPEG, valida proporção e itens; mídia por túnel cloudflared | retry em 5xx | base/publicar-meta-graph.md
D-30 | (autônoma) Agendador verifica a cada minuto, publica até 15 min depois do horário, senão `falhou`; trava com filelock | publicar atrasado | CONTRATO-capacidades; base/agendador-local-por-so.md
D-31 | (autônoma) Galeria local mínima com ≥ 1 template embarcado por tipo, neutralizado dos atuais | núcleo sem template | sem template não produz
D-32 | (autônoma) Aula aceita gravação de tela como entrada e edita por cues; automação de gravação fora | portar osascript/VS Code | depende da máquina (base/gravacao-de-tela.md)
D-33 | (autônoma) Plugin `expxmedia` usável em dev com `claude --plugin-dir nucleo` | esperar a central | usar o núcleo antes da central
D-34 | (autônoma) Provedor de teste para narrar/avatar (áudio silencioso — SUBSTITUÍDO por D-39) só com EXPXMEDIA_PROVEDORES_TESTE=1 | pular narração nos testes | validar pipeline narrado sem crédito
D-35 | (autônoma) Pronto = suíte verde + varredura de marca limpa + Alma fictícia produz os 5 tipos sem chave, publicação em dry-run | revisão manual | critério binário
D-36 | (autônoma, F3) Código de reel por referência pode usar cores literais da paleta da referência; marca, fontes e selo vêm da Alma; o validador de imports e APIs proibidas vale igual | exigir só tokens | o recriado imita o clima de cor da referência, que não é marca (base/inteligencia-reel-recriado.md)
D-37 | (autônoma, F3) Nenhuma task escreve nos projetos de origem; goldens e portes leem de lá e executam em cópia temporária | rodar scripts antigos no lugar | montar-reel.mjs reescreve registro.ts e public/ do projeto de origem (base/reel-recriado-roteiro-e-cenas.md)
D-38 | (autônoma, retorno da F5) Reel a partir de página capturada entra no núcleo como produção de reel | deixar para pack | auditoria 1, achado ALTA; formato genérico (base/montagem-reel-ffmpeg.md, base/legendar.md)
D-39 | (autônoma, retorno da F5) Provedor de teste gera sinal audível sintético por palavra; loudnorm mede a mistura final | áudio silencioso | silêncio não atinge −14 LUFS (auditoria 1)
D-40 | (autônoma, retorno da F5) Parâmetros de voz por tipo de peça; ritmo mínimo só no reel | conjunto único | a aula tem calibragem própria (base/aula-pipeline.md)
D-41 | (autônoma, retorno da F5) Perfis (faixa de duração SUBSTITUÍDA em parte por D-49): reel 30–70 s; aula 1920×1080/1080×1920, 30 fps, h264/aac, −14 LUFS, pico −1, SRT; sob_medida como na origem | perfil aula indefinido | auditoria 1
D-42 | (autônoma, retorno da F5) Dependências todas em T-01.01 e task de preparação de ambiente | cada task acrescenta a sua | escrita concorrente em pyproject/uv.lock (auditoria 1)
D-43 | (autônoma, retorno da F5) Rosto de skimage.data.astronaut (domínio público) e fala com say do macOS nos testes de corte | rosto desenhado | Haar não detecta rosto desenhado (auditoria 1)
D-44 | (autônoma, retorno da F5) Graph 50/24 h via content_publishing_limit; HeyGen áudio ≤ 10 min; ingestão/adoção de layouts fica para a camada galeria | não tratar | fontes contraditórias na base (auditoria 1)
D-45 | (autônoma, retorno da F5) Bloqueantes de copy viram revisar copy; skills testadas contra listas-âncora | testar skills só por palavras | auditoria 1
D-46 | (autônoma, retorno da F5) Root do kit importa registro gerado de src/composicoes | cada task edita o Root | auditoria 1, achado BAIXA
D-47 | (autônoma, reauditoria 2) Goldens G3/G4 usam alma-golden-reel com a fonte local da origem só nos testes, sem copiar a fonte | paridade impossível ou fonte de sistema no código | D-21 segue valendo para o código
D-48 | (autônoma, reauditoria 2) Score de pauta antes do render da apresentação fica para a curadoria do pack | portar no núcleo | depende da estratégia de canal (D-13)
D-49 | (autônoma, reauditoria 3) Faixas por perfil iguais às da origem: reel de página 50–70 s, corte 50–185 s com aviso acima de 75 s, reel narrado Remotion e recriado 30–70 s | faixa única de 30–70 s | a origem calibrou cada formato (base/verificar-reel-gates.md)
```

## Pendências

```
PENDENTE-01 (NÃO BLOQUEANTE) | Licença do Remotion para empresas clientes que renderizam | premissa: o núcleo usa Remotion e o /expxmedia:ambiente e o doctor informam os termos; decisão comercial do dono (base/remotion-render-e-licenca.md). Se a resposta for "não usar Remotion", o motor de motion precisa de outro provedor atrás da mesma capacidade.
PENDENTE-02 (NÃO BLOQUEANTE) | Expx Flow aceitar vídeo como filho de carrossel | premissa D-06: o adaptador envia; se o servidor recusar, a peça registra publicacao_falhou com o motivo e o ajuste é no Expx Flow.
```
