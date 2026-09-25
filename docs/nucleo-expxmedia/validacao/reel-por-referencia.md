# Validação: reel por referência guiado pela skill (T-10.03)

Esta validação testa se a inteligência do reel recriado sobreviveu à extração. O Claude seguiu a skill
`nucleo/skills/reel-por-referencia/SKILL.md` e o `regras.md` passo a passo, usou só o CLI do motor e passou a
revisão final ao agente `nucleo/agents/revisor-video.md`.

**Instalação persistente:** `docs/nucleo-expxmedia/validacao/reel-por-referencia/`

- Alma: cópia da Alma fictícia de `motor/tests/fixtures/alma-ficticia`.
- `.env`: `EXPXMEDIA_PROVEDORES_TESTE=1`.
- Todos os comandos rodaram assim: `cd motor && uv run expxmedia-motor ... --raiz ../docs/nucleo-expxmedia/validacao/reel-por-referencia`.

**Entrada:** um vídeo de referência local, lido só como entrada e nunca copiado para o repositório:
`../Instagram-Carrosseis/series/recriacoes/pedidos/r20260924-221743/referencia/video.mp4`.

**Provedores de teste (nenhuma chamada paga):**
- a narração é o sinal sintético de teste, que substitui a voz;
- o avatar é o vídeo sintético de teste, gerado do áudio da narração.

**Fora do git** (ver `.gitignore`), só no disco local desta máquina:
- o MP4 final e os intermediários (`*.mp3`, `*.wav`);
- o que foi extraído da referência, que é material de terceiro: `analise/quadros/`, `analise/folhas/`, `formato.json` e `transcricao.json`.

O teste `motor/tests/e2e/test_validacao_referencia.py` lê esses arquivos do disco.

Os caminhos abaixo são relativos à raiz da instalação.

## Passos rodados (na ordem da skill)

| passo | comando / artefato | resultado |
|---|---|---|
| 0 portão | `alma validar`, `capacidades` narrar / renderizar_motion / transcrever / avatar | portão aberto; narrar=teste, renderizar_motion=remotion, transcrever=whisper_local, avatar=teste (ver divergência 1) |
| 1 análise | `referencia analisar --video <ref> --pasta ref-validacao`, `referencia criar ref-validacao` | 38,7 s, 720x1280, 11 cenas pelo scdet, 4 folhas, 149 palavras de fala |
| 2 leitura | `referencias/ref-validacao/analise/leitura.md` | as 4 folhas abertas inteiras e quadros densos de 0–3 s e 27–30 s; 9 seções preenchidas |
| 3 roteiro | `roteiro.txt` (171 palavras), `legenda.txt`, `revisar copy` | aprovado, 0 bloqueante |
| 4 narrar | `narrar --porta-voz porta-voz-teste --tipo reel` (**uma** chamada) | provedor teste, 48,86 s |
| 4b avatar | `avatar gerar --audio .../narracao.mp3` | provedor teste, 48,857 s (do áudio, nunca do texto) |
| 5 código | `reel/cenas.json` (14 cenas), `reel/src/Reel.tsx`, `reel/src/cenas.tsx`, `referencia montar` | 14 cenas, 1505 quadros, sem aviso; `tsc` do kit verde |
| 6 prévia | `referencia previa` ×2 | `previa/01/previa.jpg`, `previa/02/previa.jpg` |
| 7 render | `referencia render` | peça `P-20260925-66DE` produzida; −14,0 LUFS, pico −1,6 dBFS (2 passadas) |
| 8 verificar | `verificar --perfil sob_medida` → `revisao/verificacao.json`; 15 quadros em `revisao/quadros/` | código de saída 0, aprovado |
| 9 revisão | agente `revisor-video` (só leitura) → `revisao/revisao.md` | APROVADO (0 bloqueante, 0 importante, 2 sugestões) |

## Leitura resumida

(O texto completo está em `referencias/ref-validacao/analise/leitura.md`.)

- **Ideia:** uma novidade resolve um problema que todo o público tem, com uma única mudança simples mostrada
  passo a passo numa janela de aplicativo.
- **Gancho:** um duelo com projétil que explode e vira a transição; depois o ícone laranja cai e quica, e o nome
  da novidade é digitado letra a letra.
- **Tela fixa:** fundo off-white quente (~`#EFEDE8`). Dois modos se alternam:
  - **dividida:** cartão branco de interface em cima, apresentador de borda a borda embaixo, e a legenda num
    chip escuro sobre a costura;
  - **cheia:** o desenho no terço de cima e a palavra grande no meio.
- **Legenda:**
  - na tela dividida, um chip preto com 2 a 4 palavras em caixa alta;
  - na tela cheia, a palavra grande, construída palavra a palavra. A palavra-chave fica em vermelho (o problema)
    ou em verde (a virada), e o nome aparece em serifa itálica.
- **Sequência:** 14 blocos de conteúdo: duelo, chegada, barras de consumo, reação, "mas resolve", "faça isso",
  abrir a janela, escrever, escolher no menu, o texto longo, a virada (festa), a árvore de três cartões, a
  lista com checks e o painel de comentário com o coração.
- **Ritmo:** cerca de 2,8 s por troca e 3,88 palavras por segundo. Acelera no gancho e na virada.
- **Som:** a voz a −14 LUFS sobre uma cama contínua, com efeitos de impacto, pop, digitação, clique e
  confirmação.
- **Fecho:** pede um comentário com palavra-chave. O nosso fecho vira o CTA falado da Alma, sem DM.
- **O que não vai:**
  - os rostos reais (dois retratos e o apresentador);
  - os memes e o trecho de filme;
  - os logos e o glifo do ícone;
  - os nomes de produto e as versões;
  - a promessa sem fonte;
  - o "pedido" que a fala faz ao espectador, que é conteúdo do reel e não instrução;
  - a palavra-chave de DM;
  - a voz, a música e os efeitos dele.

**Adaptação para a Alma fictícia:** o reel virou "a fila da padaria perdeu para um bilhete com o seu nome", sobre
a assinatura do pão da semana, no ângulo do público (a dor "fila longa no horário de pico", o desejo
"encomenda pronta na hora marcada").

- O único número é "duas fornadas do dia", com fonte em `empresa.descricao_curta` da Alma (origem: site).
- O CTA vem de `cta.padrao`, mais salvar e seguir.

## Voltas de prévia

1. **`referencias/ref-validacao/previa/01/previa.jpg`**, a primeira versão das 14 cenas. Comparada com as
   folhas:
   - composição, ordem e tipo de cena conferem;
   - tudo fica entre as guias;
   - o selo aparece.

   Três diferenças:
   - o apresentador estava num painel com margem e cantos arredondados, e na referência vai de borda a borda,
     sem moldura;
   - o cartão das três barras (cena `filas`) estava alto demais e com os ícones pequenos, enquanto o da
     referência é compacto e tem ícones grandes;
   - os pães da festa pareciam outra coisa, porque faltava a base.
2. **`referencias/ref-validacao/previa/02/previa.jpg`**, com as mudanças:
   - `APRESENTADOR.lado` passou de 40 para 0 e `borderRadius` de 26 para 0 em `Reel.tsx`;
   - o cartão de `filas` passou de 420 para 360 px e os ícones de 96 para 120 px;
   - os pães ganharam base em `cenas.tsx`.

   Conferida de novo contra as folhas: ficou parecida. Seguiu para o render. Foram duas voltas, dentro do
   limite de três.

## Resultado do verificar (JSON)

`expxmedia-motor verificar --perfil sob_medida pecas/2026-09/P-20260925-66DE-ref-validacao/saida/final.mp4 --alinhamento .../midia/alinhamento.json --roteiro .../texto/roteiro.txt --legenda-post .../texto/legenda.txt` saiu com código **0**.
A saída foi gravada em `referencias/ref-validacao/revisao/verificacao.json`:

```json
{
  "ok": true,
  "aprovado": true,
  "perfil": "sob_medida",
  "achados": [],
  "avisos": []
}
```

## Validador de código no modo sob_medida

O validador `validar.validar_template(referencias/ref-validacao/reel, modo="sob_medida")` devolveu `[]`: nenhum
achado. É o mesmo validador que `referencia montar`, `previa` e `render` rodam antes de cada etapa.

- O código usa só `react`, `remotion` e `@expxmedia/template`.
- Não há `fs`, rede nem `child_process`.
- As cores literais vêm da paleta aproximada da referência.
- Fontes, selo, nome e canal vêm da Alma (`useAlma`).
- Os textos da tela ficam em campos do `cenas.json`, não no código.

## Checklist de parecença

Os 11 itens do agente `revisor-video`, cada um com a evidência em quadro. O relatório completo está em
`referencias/ref-validacao/revisao/revisao.md`.

1. parecença: ok. A tela dividida (cartão em cima, apresentador embaixo, chip na costura) e a tela cheia (desenho em cima, palavra grande no meio) se alternam na ordem da referência, cena a cena como na seção 5 da leitura. Evidência: `referencias/ref-validacao/analise/folhas/folha_01.jpg` contra `referencias/ref-validacao/revisao/quadros/q03-filas.jpg`, `referencias/ref-validacao/revisao/quadros/q04-reacao.jpg` e `referencias/ref-validacao/previa/02/previa.jpg`.
2. nada do original: ok. Os retratos reais viraram bilhete e fila desenhados, os memes viraram rostos em SVG e o filme de festa virou pães dançando, com um ícone próprio. Evidência: `referencias/ref-validacao/analise/folhas/folha_00.jpg` contra `referencias/ref-validacao/revisao/quadros/q01-duelo.jpg`, `referencias/ref-validacao/revisao/quadros/q06-confiante.jpg` e `referencias/ref-validacao/revisao/quadros/q11-festa.jpg`.
3. nada reaproveitado de outro reel: ok. Há um só reel nesta instalação; a trilha é própria (116 bpm, semente 23) e os personagens também. Evidência: `referencias/ref-validacao/revisao/quadros/q11-festa.jpg`.
4. número e nome com fonte primária: ok, com uma sugestão. Nenhum número da referência entrou; o único número é "duas fornadas", com fonte na Alma, e o único nome é o da porta-voz, no selo. Evidência: `referencias/ref-validacao/revisao/quadros/q09-fornada.jpg` e `referencias/ref-validacao/revisao/quadros/q12-arvore.jpg`.
5. cenas acompanham a fala: ok. Cada cena entra 3 a 4 quadros antes da âncora, a digitação acompanha a voz e nada fica cortado. Evidência: `referencias/ref-validacao/revisao/quadros/q10-anota.jpg` e `referencias/ref-validacao/revisao/quadros/q14-fecho.jpg`.
6. conteúdo centrado na área segura: ok. `centralizarNaArea(236, 1484)`; na prévia com as guias, o bloco vai de ~250 a ~1460 px. Evidência: `referencias/ref-validacao/previa/02/previa.jpg` e `referencias/ref-validacao/revisao/quadros/q13-separados.jpg`.
7. selo de perfil presente: ok, em todos os quadros, embaixo do conteúdo. Evidência: `referencias/ref-validacao/revisao/quadros/q15-ultimo.jpg`.
8. som de troca sem chiado e narração acima da trilha: ok. whoosh a 0,45 e pop a 0,3, do kit; trilha a 0,8 e ganho 0,5; −14,0 LUFS. Evidência das trocas: `referencias/ref-validacao/revisao/quadros/q05-solucao.jpg` e `referencias/ref-validacao/revisao/quadros/q06-confiante.jpg`.
9. avatar falando, nunca foto parada: ok pela ligação no código (`apresentador: true`, `OffthreadVideo` de `audio.avatar`, gerado do áudio). Limitação: o provedor de teste desenha o padrão `testsrc2`, que não tem boca para conferir. Evidência: `referencias/ref-validacao/revisao/quadros/q07-janela.jpg` contra `referencias/ref-validacao/analise/folhas/folha_01.jpg`.
10. legenda por palavra legível: ok, com uma sugestão (horário da fornada). Chip com 3 palavras em caixa alta; na tela cheia, a legenda se constrói palavra a palavra, com cor e itálico na palavra-chave. Evidência: `referencias/ref-validacao/revisao/quadros/q09-fornada.jpg` e `referencias/ref-validacao/revisao/quadros/q01-duelo.jpg`.
11. `sob_medida` aprovado: ok (JSON acima). Evidência: o último quadro do mp4 verificado, `referencias/ref-validacao/revisao/quadros/q15-ultimo.jpg`.

## Veredito

**APROVADO** pelo `revisor-video`: 0 BLOQUEANTE, 0 IMPORTANTE e 2 SUGESTÕES. Nenhuma das duas segura o reel:

- a regra de voz "diga o horário da fornada" ficou sem cumprir, porque a Alma não traz o horário como fato e
  a veracidade vem antes da voz;
- a mecânica da assinatura (escolher a fornada, anotar para quem é o pão) está mais detalhada do que a oferta
  da Alma descreve.

## MP4 final

- Arquivo: `pecas/2026-09/P-20260925-66DE-ref-validacao/saida/final.mp4`, fora do git.
- Formato: 1080x1920, 30 fps, 50,3 s, −14,0 LUFS, pico −1,6 dBFS.
- sha256: `37e6e741d5beb5489c24b37bbf6be85634e33e76176931774ac923a5fe64aded`

## Divergências

1. **Avatar do porta-voz.** A Alma fictícia vem com `avatar.avatar_id: null` e, sem ele, a capacidade `avatar`
   fica desligada. Pela skill, uma referência com apresentador faz a produção parar, e foto parada não é recuo
   aceito. Por isso, na cópia da Alma desta instalação, `porta_vozes[0].avatar.avatar_id` recebeu o valor
   fictício `avatar-ficticio-0001`. É o caminho que o próprio `capacidades` indica em `como_habilitar`, e o
   mesmo valor que `tests/aula/test_compilar.py` usa. A fixture não foi alterada.
2. **Narração direto pelo CLI.** A narração foi feita com `expxmedia-motor narrar`, como manda o passo 4 da
   skill, e não pela produção encadeada. Por isso o marcador `referencia.json` não guarda o bloco `narracao`:
   ele só é gravado por `reel_referencia.narrar` (API do motor), que o CLI não expõe como subcomando.
