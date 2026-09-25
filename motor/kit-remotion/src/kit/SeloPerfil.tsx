import React from "react";
import { Img } from "remotion";
import { useAlma } from "./alma";
import { mola } from "./anim";
import { pilhaFonte, urlDoArquivo } from "./fontes";

// Selo de perfil de quem publica, fixo embaixo do conteúdo (lição do 1º reel sob medida: "faltava identidade de
// quem publica", vale para todos). Nome e retrato vêm do porta-voz da Alma, o @ do canal da Alma e as cores dos
// papéis da Alma; a peça pode vestir o selo com a paleta dela passando as cores por props.
// Nada de selo de verificado: a conta não é apresentada como algo que não é.
// origem: Instragram-Videos/remotion/src/kit/SeloPerfil.tsx:5-37
export const SeloPerfil: React.FC<{
  f: number;
  y: number; // topo do selo, no sistema do bloco centralizado
  fundo?: string;
  nome?: string;
  arroba?: string;
  anel?: string;
  entra?: number;
}> = ({ f, y, fundo, nome, arroba, anel, entra = 8 }) => {
  const alma = useAlma();
  const { cores, fontes, porta_voz: pv, canal } = alma;
  if (!pv && !canal) return null;
  // origem: Instragram-Videos/remotion/src/kit/SeloPerfil.tsx:18 (mola com damping 13, entrada no quadro 8)
  const s = mola(f, entra, 13);
  return (
    <div
      style={{
        position: "absolute", left: 0, right: 0, top: y, display: "flex", justifyContent: "center",
        transform: `translateY(${(1 - s) * 40}px)`, opacity: s,
      }}
    >
      <div
        style={{
          display: "flex", alignItems: "center", gap: 20, background: fundo ?? cores.fundo, borderRadius: 60,
          padding: pv?.retrato ? "10px 36px 10px 10px" : "18px 36px",
          // origem: Instragram-Videos/remotion/src/kit/SeloPerfil.tsx:23 (sombra preta a 14% de opacidade)
          boxShadow: "0 8px 22px rgba(0, 0, 0, 0.14)",
        }}
      >
        {pv?.retrato ? (
          <Img
            src={urlDoArquivo(pv.retrato)}
            style={{ width: 78, height: 78, borderRadius: 39, border: `4px solid ${anel ?? cores.destaque}`, objectFit: "cover" }}
          />
        ) : null}
        <div style={{ lineHeight: 1.15 }}>
          {pv ? (
            <div style={{ fontFamily: pilhaFonte(fontes.titulo), fontWeight: 800, fontSize: 32, color: nome ?? cores.texto }}>
              {pv.nome}
            </div>
          ) : null}
          {canal ? (
            <div style={{ fontFamily: pilhaFonte(fontes.texto), fontWeight: 600, fontSize: 26, color: arroba ?? cores.apoio }}>
              {canal.identificador}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
};
