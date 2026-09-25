import { interpolate, spring } from "remotion";
import { FPS, REEL } from "./constantes";

// Utilidades de animação comuns a todas as composições. O VISUAL de cada peça é dela; daqui só sai o que é
// mecânica: rampa, mola e a área segura. Porta de Instragram-Videos/remotion/src/kit/anim.ts.

// origem: Instragram-Videos/remotion/src/kit/anim.ts:6
export const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

// origem: Instragram-Videos/remotion/src/kit/anim.ts:8
export const rampa = (f: number, a: number, b: number, de = 0, ate = 1) => interpolate(f, [a, b], [de, ate], clamp);

// Mola com o fps da constante única (na origem o fps estava cravado aqui dentro).
// origem: Instragram-Videos/remotion/src/kit/anim.ts:10-11 (damping 12, stiffness 140)
export const mola = (f: number, inicio: number, damping = 12, stiffness = 140) =>
  spring({ frame: f - inicio, fps: FPS, config: { damping, stiffness } });

// Área segura do vídeo vertical em 1080x1920: a interface cobre ~220 px de cima e ~420 px de baixo. O conteúdo
// fica centrado nessa faixa, não no quadro inteiro (a 1ª versão do reel aprovado saiu "muito para cima").
// origem: Instragram-Videos/remotion/src/kit/anim.ts:13-16
export const AREA_SEGURA = { topo: 220, base: 1500 } as const;

// Transform que leva um bloco desenhado entre `topo` e `base` para o centro da área segura, encolhendo
// (escala ≤ 1) se não couber com a folga. origem: Instragram-Videos/remotion/src/kit/anim.ts:19-26 (folga 16)
export const centralizarNaArea = (topo: number, base: number, folga = 16) => {
  const alt = base - topo;
  const disp = AREA_SEGURA.base - AREA_SEGURA.topo - 2 * folga;
  const k = Math.min(1, disp / alt);
  const centro = (topo + base) / 2;
  const alvo = (AREA_SEGURA.topo + AREA_SEGURA.base) / 2;
  return { transformOrigin: `${REEL.largura / 2}px ${centro}px`, transform: `translateY(${alvo - centro}px) scale(${k})` };
};
