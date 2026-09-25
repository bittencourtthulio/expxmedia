import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { ProvedorAlma, useAlma, type ComAlma } from "../../kit/alma";
import { mola, rampa } from "../../kit/anim";
import { FPS } from "../../kit/constantes";
import { pilhaFonte } from "../../kit/fontes";
import type { Composicao } from "../registro.generated";

// Slide de vídeo do carrossel misto (D-06): um slide animado no formato do carrossel (4:5), com a mesma
// estrutura de um slide de imagem — etiqueta, título e texto —, em movimento. Cores e fontes só da Alma
// (papéis de cor); os textos chegam por props, dos slots do slide.

export const QUADRO = { largura: 1080, altura: 1350 } as const; // 4:5, o formato do carrossel

export type PropsSlideVideo = ComAlma & {
  etiqueta: string | null;
  titulo: string;
  texto: string | null;
  duracao_s: number;
};

const mistura = (a: string, pct: number, b: string) => `color-mix(in srgb, ${a} ${pct}%, ${b})`;

const Tela: React.FC<Omit<PropsSlideVideo, "alma">> = ({ etiqueta, titulo, texto, duracao_s }) => {
  const f = useCurrentFrame();
  const { cores, fontes } = useAlma();
  const total = Math.max(1, Math.round(duracao_s * FPS));
  const anel = mola(f, 0, 14, 90);
  const palavras = titulo.split(/\s+/).filter(Boolean);
  const fimTitulo = 8 + palavras.length * 4;
  return (
    <AbsoluteFill style={{ background: cores.fundo, overflow: "hidden" }}>
      <svg width={QUADRO.largura} height={QUADRO.altura} style={{ position: "absolute", left: 0, top: 0 }}>
        <circle cx={900} cy={230} r={260 * anel} fill={mistura(cores.destaque, 18, cores.fundo)} />
        <circle cx={900} cy={230} r={190} fill="none" stroke={cores.destaque} strokeWidth={12} strokeDasharray="30 22"
          transform={`rotate(${f * 1.2} 900 230)`} opacity={anel} />
        {[0, 1, 2].map((k) => (
          <circle key={k} cx={900 + Math.cos(f / 20 + k * 2.1) * 300} cy={230 + Math.sin(f / 20 + k * 2.1) * 300} r={16}
            fill={cores.destaque_2} opacity={anel} />
        ))}
        <circle cx={140} cy={1180} r={120 * mola(f, 10, 14, 90)} fill={mistura(cores.destaque_2, 16, cores.fundo)} />
        <rect x={90} y={1040} width={rampa(f, fimTitulo, fimTitulo + 24, 0, 420)} height={16} rx={8} fill={cores.destaque} />
        <rect x={90} y={1250} width={900} height={8} rx={4} fill={mistura(cores.apoio, 25, cores.fundo)} />
        <rect x={90} y={1250} width={900 * Math.min(1, f / total)} height={8} rx={4} fill={cores.apoio} />
      </svg>
      {etiqueta ? (
        <div style={{ position: "absolute", left: 90, top: 110, padding: "12px 28px", borderRadius: 40, background: cores.texto,
          color: cores.texto_inverso, fontFamily: pilhaFonte(fontes.titulo), fontWeight: 800, fontSize: 32, letterSpacing: 1,
          textTransform: "uppercase", transform: `scale(${mola(f, 2, 11, 170)})`, transformOrigin: "left center" }}>
          {etiqueta}
        </div>
      ) : null}
      <div style={{ position: "absolute", left: 90, right: 90, top: 380, display: "flex", flexWrap: "wrap", columnGap: 26,
        fontFamily: pilhaFonte(fontes.titulo), fontWeight: 800, fontSize: titulo.length > 34 ? 92 : 116, lineHeight: 1.04,
        letterSpacing: -1.5, color: cores.texto }}>
        {palavras.map((p, i) => {
          const s = mola(f, 8 + i * 4, 12, 180);
          return (
            <span key={i} style={{ display: "inline-block", opacity: s, transform: `translateY(${(1 - s) * 50}px)` }}>{p}</span>
          );
        })}
      </div>
      {texto ? (
        <div style={{ position: "absolute", left: 90, right: 160, top: 1080, fontFamily: pilhaFonte(fontes.texto), fontWeight: 600,
          fontSize: 40, lineHeight: 1.25, color: cores.apoio, opacity: rampa(f, fimTitulo + 6, fimTitulo + 20),
          transform: `translateY(${rampa(f, fimTitulo + 6, fimTitulo + 20, 24, 0)}px)` }}>
          {texto}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

const SlideVideo: React.FC<PropsSlideVideo> = ({ alma, ...resto }) => (
  <ProvedorAlma alma={alma}>
    <Tela {...resto} />
  </ProvedorAlma>
);

// Alma neutra de exemplo, só para o Studio abrir a composição sem props (nenhuma marca).
const EXEMPLO: PropsSlideVideo = {
  alma: {
    cores: {
      fundo: "#FFFFFF", fundo_alt: "#EEEEEE", texto: "#111111", texto_inverso: "#FFFFFF", apoio: "#666666",
      destaque: "#3366CC", destaque_2: "#33AA77", positivo: "#22AA55", negativo: "#CC3333",
    },
    fontes: { titulo: { familia: "sans-serif", arquivos: [] }, texto: { familia: "sans-serif", arquivos: [] } },
    porta_voz: null,
    canal: null,
  },
  etiqueta: "Exemplo",
  titulo: "Título do slide em movimento",
  texto: "Texto de apoio do slide.",
  duracao_s: 6,
};

export const composicao: Composicao<PropsSlideVideo> = {
  id: "SlideVideo",
  component: SlideVideo,
  fps: FPS,
  width: QUADRO.largura,
  height: QUADRO.altura,
  durationInFrames: EXEMPLO.duracao_s * FPS,
  defaultProps: EXEMPLO,
  calculateMetadata: ({ props }) => ({ durationInFrames: Math.max(1, Math.round(props.duracao_s * FPS)) }),
};
