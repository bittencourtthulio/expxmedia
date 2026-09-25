import React, { useEffect, useState } from "react";
import { AbsoluteFill, Sequence, cancelRender, continueRender, delayRender } from "remotion";
import { problemasAlma, type PropsAlma } from "../../kit/alma";
import { FPS } from "../../kit/constantes";
import { carregarFontes } from "../../kit/fontes";
import type { Composicao } from "../registro.generated";
import { CENAS, ProvedorTema, montarTema, type Deck } from "./cenas";

// A apresentação 16:9 inteira numa composição: um trecho de `framesPorSlide` quadros por slide, na ordem do deck.
// O runner renderiza o MP4 e tira um still do último quadro de cada trecho (o PNG do slide).
// Na origem era uma composição por slide (Root.tsx:44-56); aqui o registro é por pasta (D-46), então o deck
// vira uma composição só e o tamanho sai das props (calculateMetadata).

// origem: youtube-squad/apresentacoes/motion/src/deck.ts:43-45 (1920x1080, 240 quadros = 8 s por slide)
export const LARGURA = 1920;
export const ALTURA = 1080;
export const FRAMES_POR_SLIDE = 240;

export type PropsApresentacao = {
  alma: PropsAlma;
  deck: Deck;
  rotulo: string;
  empresa: string;
  idioma: string | null;
  framesPorSlide: number;
};

// Segura o render até as fontes da Alma carregarem e só então monta as cenas: o fitText com
// validateFontIsLoaded mede a fonte na primeira passada, e fonte ainda não carregada seria erro.
const ComFontes: React.FC<{ alma: PropsAlma; children: React.ReactNode }> = ({ alma, children }) => {
  const [pedido] = useState(() => delayRender("fontes da Alma"));
  const [pronto, setPronto] = useState(false);
  useEffect(() => {
    carregarFontes([alma.fontes.titulo, alma.fontes.texto])
      .then(() => {
        setPronto(true);
        continueRender(pedido);
      })
      .catch((e) => cancelRender(e));
    // as fontes são fixas durante o render
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pedido]);
  return pronto ? <>{children}</> : null;
};

const Apresentacao: React.FC<PropsApresentacao> = ({ alma, deck, rotulo, empresa, idioma, framesPorSlide }) => {
  const problemas = problemasAlma(alma);
  if (problemas.length) throw new Error(`Alma inválida nas props: ${problemas.join("; ")}`);
  const tema = montarTema(alma, deck, rotulo, empresa, idioma, framesPorSlide);
  return (
    <ComFontes alma={alma}>
      <ProvedorTema tema={tema}>
        <AbsoluteFill style={{ backgroundColor: alma.cores.fundo }}>
          {deck.slides.map((slide, i) => {
            const Cena = CENAS[slide.tipo];
            if (!Cena) throw new Error(`slide ${i + 1}: tipo sem cena: ${String(slide.tipo)}`);
            return (
              <Sequence key={i} from={i * framesPorSlide} durationInFrames={framesPorSlide} name={`slide-${i + 1}`}>
                <Cena index={i} />
              </Sequence>
            );
          })}
        </AbsoluteFill>
      </ProvedorTema>
    </ComFontes>
  );
};

// Alma e deck neutros de exemplo, só para o Studio abrir a composição sem props (nenhuma marca).
const EXEMPLO: PropsApresentacao = {
  alma: {
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
    porta_voz: null,
    canal: null,
  },
  deck: {
    titulo: "Exemplo",
    tema: null,
    slides: [
      { tipo: "titulo", kicker: "Exemplo", titulo: "Slide de <b>exemplo</b>", subtitulo: "Abra com props para ver um deck real" },
      { tipo: "cta", titulo: "Próximo passo", texto: null, url: null, imagem: null },
    ],
  },
  rotulo: "Exemplo",
  empresa: "Exemplo",
  idioma: null,
  framesPorSlide: FRAMES_POR_SLIDE,
};

export const composicao: Composicao<PropsApresentacao> = {
  id: "Apresentacao",
  component: Apresentacao,
  fps: FPS,
  width: LARGURA,
  height: ALTURA,
  durationInFrames: EXEMPLO.deck.slides.length * FRAMES_POR_SLIDE,
  defaultProps: EXEMPLO,
  calculateMetadata: ({ props }) => ({ durationInFrames: Math.max(1, props.deck.slides.length) * props.framesPorSlide }),
};
