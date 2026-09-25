// Layouts da aula: números calibrados à mão na origem, portados com o mesmo valor (base/aula-pipeline.md,
// risco 5). Trocar por proporções genéricas quebra a sobreposição cuidadosa com a interface do Reels.
// Só dados: nenhuma cor, fonte ou nome aqui (M13). A composição (index.tsx) desenha em cima disto.

// Faixas seguras do 9:16 ("faixas seguras p/ UI do Reels"). origem: cursos-ia/aula-skills/src/Aula9x16.tsx:37
export const SAFE = { top: 168, right: 56, bottom: 280, left: 56 } as const;

// Barra de título da janela do avatar e da janela da tela. origem: cursos-ia/radar-ia-09-jev-calibracao/src/Aula.tsx:14-15
export const PIP_BAR = 30;
export const TELA_BAR = 34;

// Gravação de tela editada (demo.mp4) sempre em 1920x1080. origem: cursos-ia/radar-ia-09-jev-calibracao/src/Aula.tsx:16-17
export const TELA_ORIGEM = { largura: 1920, altura: 1080 } as const;

// O avatar chega como o HeyGen devolve o twin 4:5: 1080x1350, com o conteúdo 16:9 centrado (faixa útil de
// 1080 x 9/16 = 607,5 px) e faixas claras em cima e embaixo; o PiP recorta pela faixa útil.
// origem: cursos-ia/radar-ia-09-jev-calibracao/src/Aula.tsx:11-13
export const AVATAR = { largura: 1080, altura: 1350, conteudo_h: (1080 * 9) / 16 } as const;

// O PiP some com fade de 15 quadros em duração - 1,5 s. origem: cursos-ia/radar-ia-09-jev-calibracao/src/Aula.tsx:10,136
export const FOLGA_FINAL_S = 1.5;
export const FADE_PIP_QUADROS = 15;

// Selo "N× acelerado" na barra da tela a partir de 1,5x. origem: cursos-ia/radar-ia-09-jev-calibracao/src/Aula.tsx:108
export const SELO_ACELERADO = 1.5;

// Transição da "câmera" do 9:16 entre dois pontos: ±0,3 s. origem: cursos-ia/radar-ia-09-jev-calibracao/src/Aula.tsx:83
export const TRANSICAO_CAMERA_S = 0.3;

// Itens de uma cena entram em 1,2 s + 1,3 s por item. origem: cursos-ia/radar-ia-09-jev-calibracao/src/Aula.tsx:244
export const ITEM_INICIO_S = 1.2;
export const ITEM_PASSO_S = 1.3;

export type Retangulo = { left: number; top: number; w: number; h: number };
// Posição em px; só as chaves que valem para o layout (a legenda do 16:9 é presa na base, a do 9:16 no topo).
export type Posicao = { left?: number; right?: number; top?: number; bottom?: number; width?: number };

export type Layout = {
  formato: "16:9" | "9:16";
  largura: number;
  altura: number;
  vertical: boolean;
  pad: string; // área das cenas (padding CSS)
  tela: Retangulo; // área do vídeo da tela, sem a barra de título
  pip: Retangulo; // janela do avatar, com a barra de título
  cartao: { left: number; top: number; w: number } | null; // cartão do passo (só no 16:9)
  legenda: Posicao;
  legendaFonte: number;
  cabecalho: { top: number; left: number; right: number };
  progresso: Posicao;
};

// 1920x1080: tela à esquerda; cartão do passo e avatar na coluna da direita.
// origem: cursos-ia/radar-ia-09-jev-calibracao/src/Aula.tsx:46-56
export const L16: Layout = {
  formato: "16:9",
  largura: 1920,
  altura: 1080,
  vertical: false,
  pad: "120px 440px 170px 110px",
  tela: { left: 48, top: 96 + TELA_BAR, w: 1392, h: 783 },
  pip: { left: 1484, top: 500, w: 380, h: 440 },
  cartao: { left: 1484, top: 130, w: 380 },
  legenda: { left: 48, width: 1392, bottom: 44 },
  legendaFonte: 28,
  cabecalho: { top: 38, left: 64, right: 64 },
  progresso: { left: 1484, width: 380, bottom: 60 },
};

// 1080x1920: faixas seguras do Reels; a área das cenas termina 760 px acima da base para caber a legenda
// (topo 1198) e o PiP (1318 a 1658). origem: cursos-ia/radar-ia-09-jev-calibracao/src/Aula.tsx:59-68
export const L9: Layout = {
  formato: "9:16",
  largura: 1080,
  altura: 1920,
  vertical: true,
  pad: `${SAFE.top}px ${SAFE.right}px 760px ${SAFE.left}px`,
  tela: { left: SAFE.left, top: SAFE.top + TELA_BAR, w: 968, h: 962 },
  pip: { left: (1080 - 272) / 2, top: 1318, w: 272, h: 340 },
  cartao: null,
  legenda: { left: SAFE.left, width: 1080 - SAFE.left - SAFE.right, top: 1198 },
  legendaFonte: 32,
  cabecalho: { top: 52, left: SAFE.left, right: SAFE.right },
  progresso: { left: SAFE.left, right: SAFE.right, bottom: 220 },
};

export const LAYOUTS: Record<Layout["formato"], Layout> = { "16:9": L16, "9:16": L9 };
