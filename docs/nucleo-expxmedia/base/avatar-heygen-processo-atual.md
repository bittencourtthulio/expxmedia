# Avatar HeyGen: processo atual (cursos-ia)

Área: como o vídeo do porta-voz falando (`public/avatar.mp4`) é produzido hoje e encaixado no PiP da aula.
Capacidade alvo `avatar`, provedor `heygen`, satisfeita por `HEYGEN_API_KEY`
(`ExpxMedia/docs/contrato/CONTRATO-capacidades.md:39,158`). A API em si está descrita em `api-heygen.md`
desta base; este arquivo registra só o processo de origem. **Não há script**: o passo é manual/assistido
em todos os episódios.

## Contrato de entrada

- Entrada é o **áudio** da narração do ElevenLabs, nunca o texto do roteiro: "Gerar o avatar a partir do
  áudio `public/narracao.mp3` (upload como asset e `create_video_from_avatar` com `audio_asset_id`)"
  (`cursos-ia/aula-skills-2/plano-gravacao.md:57-63`). Mesma instrução em
  `cursos-ia/radar-ia-01-jev/README.md:13-14` ("asset de áudio").
- Parâmetros usados: twin `<twin HeyGen do dono na origem>` ("estante branca"), 4:5, 1080p
  (`cursos-ia/aula-skills-2/plano-gravacao.md:65`; `cursos-ia/radar-ia-01-jev/README.md:13-14`).
- Motor: Avatar IV até a aula 07; Avatar III em 08 e 09 porque "os créditos do Avatar IV acabaram na aula
  07" (`cursos-ia/radar-ia-08-jev-cascata/README.md:44`; `cursos-ia/radar-ia-09-jev-calibracao/README.md:48`).
- Canal de acesso: servidor MCP HTTP `heygen` (`https://mcp.heygen.com/mcp/v1/`) configurado para o
  projeto cursos-ia na configuração de usuário do Claude Code (`.claude.json`, bloco do projeto
  `cursos-ia`, `mcpServers.heygen`, linha 4065). O `.env` de cursos-ia não tem chave HeyGen (só
  `elevenlabs_apikey`). O nome `create_video_from_avatar` do plano é ferramenta desse MCP; a forma de
  autenticação do MCP: NÃO DOCUMENTADO.
- Arquivo enviado: cada episódio de 01 a 09 tem `raw/narracao-heygen.mp3`, cópia de
  `public/narracao.mp3` com 1 byte a menos (`cursos-ia/radar-ia-09-jev-calibracao/raw/` 4 716 294 contra
  `public/` 4 716 295 bytes). Conferido com `cmp`/`xxd`: a única diferença é o cabeçalho ID3 (`ID3 v2.3`
  na cópia, `v2.4` no original); mesma duração, 44,1 kHz, 128 kbps (ffprobe). Motivo da conversão: NÃO
  DOCUMENTADO. Comando usado: NÃO DOCUMENTADO.

## Contrato de saída

- `public/avatar.mp4`: H.264 1080×1350 + AAC 48 kHz; duração igual à do áudio com diferença de ~12 ms
  (ffprobe: 294,696 s contra 294,708 s em `radar-ia-09`; 73,175 contra 73,189 em `radar-ia-01`).
- O HeyGen devolve o twin 16:9 centralizado num canvas 1080×1350 "com faixas claras em cima e embaixo"
  (`cursos-ia/aula-skills-2/plano-gravacao.md:66-67`; `cursos-ia/aula-skills-2/src/AulaSkills2.tsx:33-34`).
- Encaixe no PiP (`cursos-ia/radar-ia-09-jev-calibracao/src/Aula.tsx:11-13,133-149`):
  `AVATAR_SRC_W = 1080`, `AVATAR_SRC_H = 1350`, faixa útil `AVATAR_CONTENT_H = 1080 × 9/16 = 607,5`;
  altura renderizada `renderH = (h_pip / 607,5) × 1350`, centrada, cortando as laterais, para que só a
  faixa com conteúdo preencha o PiP. Barra de título de 30 px (`PIP_BAR`, `:14`).
- Sincronia: roda em 1× desde o frame 0, sem ajuste, porque foi gerado do mesmo MP3
  (`cursos-ia/aula-skills-2/src/AulaSkills2.tsx:30-31`); some com fade de 15 frames em
  `duration - 1,5 s` (`Aula.tsx:10,135-136`). Vídeo `muted`: o som vem da narração (`Aula.tsx:145`).
- Na compilação, cada parte usa o `avatar.mp4` do seu episódio com o mesmo `trim` da parte, dentro de uma
  moldura fixa (`cursos-ia/radar-ia-jev-completo/src/JevCompleto.tsx:88-111`).
- No contrato alvo, o arquivo é `papel: avatar` (`ExpxMedia/docs/contrato/CONTRATO-peca.md:171,195`).

## Limites e cotas

- Créditos do Avatar IV esgotaram depois de 7 aulas (`cursos-ia/radar-ia-08-jev-cascata/README.md:44`);
  saldo, preço por minuto e plano: NÃO DOCUMENTADO.
- Maior áudio enviado: 294,7 s (`radar-ia-09`, ffprobe). Tamanho máximo aceito pelo processo atual: NÃO
  DOCUMENTADO (a API v3 aceita 32 MB por asset, `api-heygen.md`).
- Tempo de geração por minuto de áudio: NÃO DOCUMENTADO.

## Erros conhecidos e tratamento

- **Avatar gerado por texto não sincroniza**: "Com o texto, o HeyGen sintetiza outra locução com outra
  duração e o PiP nunca sincroniza com a narração do ElevenLabs"; o avatar antigo ficou em
  `raw/avatar-heygen-tts-antigo.mp4` (`cursos-ia/aula-skills-2/plano-gravacao.md:60-63,68`). Tratamento:
  sempre áudio.
- **Faixas claras no 4:5**: tratadas por recorte na composição, não na geração (`AulaSkills2.tsx:33-34`).
- **Créditos esgotados**: troca de motor para Avatar III sem outra mudança registrada
  (`radar-ia-08-jev-cascata/README.md:44`).
- **Narração regravada**: exige avatar novo (mesma duração é premissa do encaixe); nada no código detecta
  avatar desatualizado.

## Riscos para a nossa implementação

Acoplamentos de marca:

| Acoplamento | Onde | Vira |
|---|---|---|
| twin `<twin HeyGen do dono na origem>` | `cursos-ia/aula-skills-2/plano-gravacao.md:65`; `cursos-ia/radar-ia-01-jev/README.md:13-14` | id de avatar do porta-voz na Alma (`CONTRATO-capacidades.md:202-204`) |
| rótulo do PiP `thulio.mov` | `Aula.tsx:143`; `JevCompleto.tsx:99` | nome do porta-voz |
| proporção 4:5, 1080p, Avatar IV/III | `plano-gravacao.md:65`; READMEs 08/09 | config do porta-voz/provedor |
| MCP `heygen` em vez de `HEYGEN_API_KEY` | `.claude.json` (projeto cursos-ia) | o contrato manda chave no `.env`; é troca de mecanismo, não só de nome |

O que derruba a qualidade se extraído ingenuamente:

1. **Gerar o avatar a partir do texto** (o caminho "natural" da API) quebra a sincronia labial com a voz
   clonada. O motor tem de mandar o áudio do `narrar`.
2. **Ignorar o canvas 1080×1350**: tratar o avatar como 4:5 cheio mostra as faixas claras; o recorte pela
   faixa 16:9 (607,5 px) é o que deixa o PiP limpo. Se o núcleo pedir `aspect_ratio` diferente, a fórmula
   do encaixe muda.
3. **Cabeçalho ID3**: a cópia enviada ao HeyGen foi reescrita para ID3 v2.3 em todos os episódios; sem
   saber o motivo, pular esse passo pode reintroduzir uma falha que não está registrada.
4. **Duração como contrato**: toda a composição supõe `avatar.duration ≈ narracao.duration`; o núcleo
   deve verificar (tolerância observada ~12 ms) antes de renderizar.
5. **Motor pago por créditos**: acabar crédito no meio da produção trocou o motor sem aviso na peça; a
   peça deveria registrar o motor efetivamente usado em `producao.provedores`.

## Fonte

- `cursos-ia/aula-skills-2/plano-gravacao.md`, `cursos-ia/aula-skills-2/src/AulaSkills2.tsx`, `cursos-ia/aula-skills-2/src/AulaSkills2_9x16.tsx`
- `cursos-ia/radar-ia-01-jev/README.md`, `cursos-ia/radar-ia-0{2..7}-*/README.md`
- `cursos-ia/radar-ia-08-jev-cascata/README.md`, `cursos-ia/radar-ia-09-jev-calibracao/README.md`
- `cursos-ia/radar-ia-09-jev-calibracao/src/Aula.tsx`, `cursos-ia/radar-ia-jev-completo/src/JevCompleto.tsx`
- `cursos-ia/radar-ia-0{1,6,9}-*/public/{narracao.mp3, avatar.mp4}` e `raw/narracao-heygen.mp3` (ffprobe, cmp, xxd)
- `cursos-ia/.env` (só nomes de chave)
- `.claude.json` do usuário, bloco do projeto cursos-ia (`mcpServers.heygen`; valores de credencial não lidos)
- `ExpxMedia/docs/nucleo-expxmedia/base/api-heygen.md` (referência cruzada)
