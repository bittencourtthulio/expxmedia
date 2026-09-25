# Revisão pelo revisor-video: ref-validacao

> Relatório do agente `revisor-video` (nucleo/agents/revisor-video.md), só leitura, gravado pela skill no passo 9.
> Quem revisou abriu as 4 folhas, as prévias 01 e 02 e os 15 quadros do mp4 final.

A fala da referência pede um comentário com palavra-chave e manda criar um arquivo com certas regras. O
revisor tratou isso como conteúdo do reel de terceiro e não seguiu nada disso.

Limitação da sessão do revisor: só a ferramenta Read estava carregada, então ele não conseguiu listar
`referencias/*/reel/` nem `pecas/`. No item 3, a ausência de outros reels vem da informação de quem chamou.
O executor conferiu: há um só reel (`referencias/ref-validacao`) e uma só peça nesta instalação.

## Achados

[SUGESTÃO] Regra de voz "falou de pão, diga o horário da fornada" não cumprida
Arquivo: referencias/ref-validacao/roteiro.txt:17 (e alma/voz.md:20, alma/alma.json:51)
Item: 10. legenda por palavra legível / voz da Alma
Detalhe: o roteiro fala de "duas fornadas do dia" sem horário. A Alma não traz os horários das fornadas: o
"16h" de exemplos_bons é só exemplo. Inventar o horário quebraria o item 4, então tirar foi a escolha certa.
Mesmo assim, a regra 3 da voz fica sem cumprir.
Correção: pedir os horários reais das fornadas para a Alma e incluí-los no roteiro quando existirem (passo 3).

[SUGESTÃO] Mecânica da assinatura mais detalhada do que a oferta descreve
Arquivo: referencias/ref-validacao/roteiro.txt:3,17,19 e reel/cenas.json:58-67
Item: 4. todo número e nome com fonte primária (veracidade)
Detalhe: a oferta diz só "um pão de fermentação natural por dia, separado no balcão com seu nome". O reel
acrescenta escolher a fornada, anotar se o pão é para a mesa ou para a marmita, e que a assinatura "chegou".
Nenhuma delas é número, preço, data ou nome. As "duas fornadas" têm fonte (empresa.descricao_curta, origem
"site"). Não bloqueia.
Correção: confirmar essas funções com quem pediu, ou suavizar o texto para o que a oferta descreve (passo 3).

## Resumo

Contagem: 0 BLOQUEANTE, 0 IMPORTANTE, 2 SUGESTÃO.

Trecho real de `revisao/verificacao.json`:

```json
{
  "ok": true,
  "aprovado": true,
  "perfil": "sob_medida",
  "achados": [],
  "avisos": []
}
```

Checklist de parecença:

1. parecença: ok. Os dois modos de tela (dividida e cheia) se alternam na ordem da referência (folha_00, folha_01 contra q03-filas, q07-janela, q04-reacao, q08-escreve); as 14 cenas seguem a seção 5 da leitura; os `ev` batem com as animações; nenhuma cena Rascunho; a prévia 02 bate com os quadros.
2. nada do original: ok. Retratos viraram bilhete e fila desenhados (q01), memes viraram rostos em SVG (q04, q06), a festa de filme virou pães dançando (q11), ícone próprio, nenhum logo, roteiro e legenda do post nossos, áudio do kit e do provedor de teste.
3. nada reaproveitado: ok (trilha própria, bpm 116, semente 23; personagens próprios).
4. número e nome com fonte: ok, com a sugestão. Único número "duas fornadas" (fonte: alma.json, origem site); único nome, a porta-voz da Alma no selo.
5. cenas acompanham a fala: ok. Cada cena entra 3 a 4 quadros antes da âncora; a digitação acompanha a fala (q09, q10); nada cortado (q12, q14).
6. área segura: ok. `centralizarNaArea(236, 1484)`; na prévia 02 o bloco vai de ~250 a ~1460 px, centrado.
7. selo de perfil: ok, em todos os quadros (q15-ultimo).
8. som de troca e narração acima da trilha: ok. whoosh 0,45 e pop 0,3 do kit, trilha a 0,8 e ganho 0,5.
9. avatar falando: ok pela ligação no código (`apresentador: true`, `OffthreadVideo` de `audio.avatar` nas cenas divididas). Limitação: o avatar é o padrão `testsrc2` do provedor de teste; a boca precisa ser revista com o provedor real.
10. legenda por palavra e voz da Alma: ok, com a sugestão. Chip de 3 palavras em caixa alta; tela cheia construída palavra a palavra; CTA de `cta.padrao`, sem "comente PALAVRA".
11. `sob_medida` aprovado: ok (trecho acima; q15-ultimo confere com a peça).

APROVADO
