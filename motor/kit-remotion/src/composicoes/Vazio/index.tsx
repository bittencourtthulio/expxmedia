import React from "react";
import { AbsoluteFill } from "remotion";
import type { Composicao } from "../registro.generated";

// Composição mínima de teste do kit: fundo neutro, duração vinda das props.
export type PropsVazio = { duracaoFrames: number };

const Vazio: React.FC<PropsVazio> = () => <AbsoluteFill style={{ backgroundColor: "#000000" }} />;

export const composicao: Composicao<PropsVazio> = {
  id: "Vazio",
  component: Vazio,
  fps: 30,
  width: 1080,
  height: 1920,
  durationInFrames: 90,
  defaultProps: { duracaoFrames: 90 },
  calculateMetadata: ({ props }) => ({ durationInFrames: props.duracaoFrames }),
};
