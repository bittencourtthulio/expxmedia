import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { ProvedorAlma, useAlma, type ComAlma } from "../../kit/alma";
import { FPS, REEL } from "../../kit/constantes";
import { SeloPerfil } from "../../kit/SeloPerfil";
import type { Composicao } from "../registro.generated";

// Composição de teste do kit: só o selo de perfil sobre o fundo alternado da Alma. Serve para conferir que
// nome, @, retrato, fontes e cores chegam da Alma pelas props.

// y do selo no reel sob medida aprovado. origem: Instragram-Videos/remotion/src/reels/recriado-ia-decide/Reel.tsx:186
const Y_SELO = 1392;

const Tela: React.FC = () => {
  const f = useCurrentFrame();
  const { cores } = useAlma();
  return (
    <AbsoluteFill style={{ backgroundColor: cores.fundo_alt }}>
      <SeloPerfil f={f} y={Y_SELO} />
    </AbsoluteFill>
  );
};

const TesteSelo: React.FC<ComAlma> = ({ alma }) => (
  <ProvedorAlma alma={alma}>
    <Tela />
  </ProvedorAlma>
);

// Alma neutra de exemplo, só para o Studio abrir a composição sem props (nenhuma marca).
const ALMA_EXEMPLO: ComAlma["alma"] = {
  cores: {
    fundo: "#FFFFFF",
    fundo_alt: "#EEEEEE",
    texto: "#111111",
    texto_inverso: "#FFFFFF",
    apoio: "#666666",
    destaque: "#3366CC",
    destaque_2: "#33AA77",
    positivo: "#22AA55",
    negativo: "#CC3333",
  },
  fontes: { titulo: { familia: "sans-serif", arquivos: [] }, texto: { familia: "sans-serif", arquivos: [] } },
  porta_voz: { id: "exemplo", nome: "Pessoa Exemplo", retrato: null },
  canal: { canal: "instagram", identificador: "@exemplo" },
};

export const composicao: Composicao<ComAlma> = {
  id: "TesteSelo",
  component: TesteSelo,
  fps: FPS,
  width: REEL.largura,
  height: REEL.altura,
  durationInFrames: 2 * FPS,
  defaultProps: { alma: ALMA_EXEMPLO },
};
