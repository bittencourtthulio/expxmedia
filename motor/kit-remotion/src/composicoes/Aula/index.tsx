import React from "react";
import {
  AbsoluteFill,
  Audio,
  Img,
  interpolate,
  OffthreadVideo,
  Sequence,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { ProvedorAlma, useAlma, type PropsAlma } from "../../kit/alma";
import { FPS } from "../../kit/constantes";
import { pilhaFonte, urlDoArquivo } from "../../kit/fontes";
import type { Composicao } from "../registro.generated";
import {
  AVATAR,
  FADE_PIP_QUADROS,
  FOLGA_FINAL_S,
  ITEM_INICIO_S,
  ITEM_PASSO_S,
  LAYOUTS,
  PIP_BAR,
  SELO_ACELERADO,
  TELA_BAR,
  TELA_ORIGEM,
  TRANSICAO_CAMERA_S,
  type Layout,
} from "./layouts";

// Aula em 16:9 e 9:16 com a mesma fonte (base/aula-pipeline.md). Porta de
// origem: cursos-ia/radar-ia-09-jev-calibracao/src/Aula.tsx (versão mais evoluída, com tela e crop9)
// com três mudanças:
// 1. o conteúdo da aula (cenas, passos, resumo) chega por props, não é código por episódio (risco 7);
// 2. a marca vem da Alma: cores por papel, fontes e o nome do porta-voz no rótulo da janela do avatar (M13);
// 3. uma composição só; o formato vem das props e o tamanho sai do calculateMetadata (registro por pasta, D-46).
// Camadas, na ordem da origem (Aula.tsx:255-270): fundo + retícula + cantos, narração, cenas, tela,
// cartão, PiP até duração - 1,5 s, legenda, cabeçalho com barra de progresso.

export type Cues = { duration: number; cues: Record<string, number> };
export type Legenda = { start: number; end: number; lines: string[] };
export type PontoCamera = { t: number; cx: number };
export type Recorte = { x: number; y: number; w: number; h: number };
export type Segmento = {
  cue: string;
  de: number;
  ate: number;
  rate: number;
  janela: string;
  camera: PontoCamera[];
  crop: Recorte;
  crop9: Recorte;
};
// O demo.json de aula.editar_tela: tempos relativos ao início da tela (`inicio`, em segundos da aula).
export type Demo = { inicio: number; duracao: number; segmentos: Segmento[]; camera: PontoCamera[] };

// Uma cena por cue, na ordem da fala. `modo`: cena animada, trecho da gravação de tela, ou slide de uma
// apresentação que compõe a aula (imagem na mesma janela da tela).
export type Cena = {
  cue: string;
  modo: "cena" | "tela" | "slide";
  rotulo: string | null; // cabeçalho, à direita
  titulo: string | null;
  texto: string | null;
  itens: string[];
  passo: string | null; // cartão do passo (16:9): título da janela
  fato: string | null; // cartão do passo: o número que importa
  imagem: string | null; // modo slide: arquivo no public dir
};

export type PropsAula = {
  alma: PropsAlma;
  formato: "16:9" | "9:16";
  serie: string | null; // cabeçalho, à esquerda
  titulo: string;
  cues: Cues;
  cenas: Cena[];
  legendas: Legenda[];
  narracao: string | null; // arquivos relativos ao public dir do render (M9)
  avatar: string | null;
  tela: { video: string; demo: Demo } | null;
};

// Como uma cena de modo "cena" é desenhada; um template de aula pode trocar (props do componente Aula).
export type DesenharCena = React.FC<{ cena: Cena; l: Layout; indice: number }>;

const clamp = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;
const quadro = (s: number) => Math.round(s * FPS);
const mistura = (a: string, pct: number, b: string) => `color-mix(in srgb, ${a} ${pct}%, ${b})`;

// ---------------------------------------------------------------- animação (origem: cursos-ia/radar-ia-09-jev-calibracao/src/marca.tsx:37-47)

export const Pop: React.FC<{ at: number; children: React.ReactNode; style?: React.CSSProperties }> = ({ at, children, style }) => {
  const f = useCurrentFrame();
  const p = spring({ frame: f - at, fps: FPS, config: { damping: 18, stiffness: 260 } });
  return (
    <div style={{ opacity: f >= at ? 1 : 0, transform: `scale(${0.94 + 0.06 * p})`, transformOrigin: "top left", ...style }}>
      {children}
    </div>
  );
};

export const Rise: React.FC<{ at: number; children: React.ReactNode; style?: React.CSSProperties }> = ({ at, children, style }) => {
  const f = useCurrentFrame();
  const p = spring({ frame: f - at, fps: FPS, config: { damping: 200 } });
  return <div style={{ opacity: p, transform: `translateY(${(1 - p) * 30}px)`, ...style }}>{children}</div>;
};

// Janela com barra de título escura (origem: cursos-ia/radar-ia-09-jev-calibracao/src/marca.tsx:49-54)
export const Janela: React.FC<{ titulo: string; children: React.ReactNode; style?: React.CSSProperties }> = ({ titulo, children, style }) => {
  const { cores, fontes } = useAlma();
  return (
    <div style={{ border: `2px solid ${cores.texto}`, background: cores.fundo_alt, boxShadow: `6px 6px 0 ${cores.texto}`, ...style }}>
      <div style={{ background: cores.texto, color: cores.texto_inverso, fontFamily: pilhaFonte(fontes.titulo), fontSize: 26, lineHeight: 1, padding: "5px 10px 3px" }}>
        {titulo}
      </div>
      <div style={{ padding: "22px 26px", color: cores.texto }}>{children}</div>
    </div>
  );
};

// Rótulo invertido (origem: cursos-ia/radar-ia-09-jev-calibracao/src/marca.tsx:57-59)
export const Etiqueta: React.FC<{ children: React.ReactNode; tamanho?: number }> = ({ children, tamanho = 26 }) => {
  const { cores, fontes } = useAlma();
  return (
    <span style={{ background: cores.texto, color: cores.texto_inverso, fontFamily: pilhaFonte(fontes.titulo), fontSize: tamanho, padding: "0 8px", lineHeight: 1.15 }}>
      {children}
    </span>
  );
};

// ---------------------------------------------------------------- cena padrão

// Título grande, texto de apoio e itens que entram um a um (Intro/Outro da origem, com o conteúdo por props).
// origem: cursos-ia/radar-ia-09-jev-calibracao/src/Aula.tsx:212-253
export const CenaPadrao: DesenharCena = ({ cena, l }) => {
  const { cores, fontes } = useAlma();
  return (
    <AbsoluteFill style={{ padding: l.pad, justifyContent: "center" }}>
      <Rise at={0}>
        {cena.rotulo ? (
          <div style={{ marginBottom: 28 }}>
            <Etiqueta tamanho={34}>{cena.rotulo}</Etiqueta>
          </div>
        ) : null}
        {cena.titulo ? (
          <div style={{ fontFamily: pilhaFonte(fontes.titulo), fontWeight: 700, fontSize: l.vertical ? 96 : 112, lineHeight: 0.98,
            letterSpacing: "-0.03em", color: cores.texto }}>
            {cena.titulo}
          </div>
        ) : null}
        {cena.texto ? (
          <div style={{ marginTop: 28, fontFamily: pilhaFonte(fontes.texto), fontSize: 40, lineHeight: 1.3, color: cores.apoio }}>{cena.texto}</div>
        ) : null}
      </Rise>
      {cena.itens.length ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 14, alignItems: "flex-start", marginTop: 36 }}>
          {cena.itens.map((item, i) => (
            <Pop key={i} at={quadro(ITEM_INICIO_S + i * ITEM_PASSO_S)}>
              <Etiqueta tamanho={44}>{item}</Etiqueta>
            </Pop>
          ))}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------- tela e slide

const segmentoAtual = (demo: Demo, t: number): Segmento =>
  demo.segmentos.find((s) => t >= s.de && t < s.ate) ?? demo.segmentos[demo.segmentos.length - 1];

// Centro da câmera (px da gravação) no tempo t do demo. origem: cursos-ia/radar-ia-09-jev-calibracao/src/Aula.tsx:78-86
export const cameraX = (camera: PontoCamera[], t: number): number => {
  if (!camera.length) return TELA_ORIGEM.largura / 2;
  let cx = camera[0].cx;
  for (let i = 1; i < camera.length; i++) {
    const k = camera[i];
    cx = interpolate(t, [k.t - TRANSICAO_CAMERA_S, k.t + TRANSICAO_CAMERA_S], [cx, k.cx], clamp);
  }
  return cx;
};

const MolduraTela: React.FC<{ l: Layout; titulo: string; selo: string | null; children: React.ReactNode }> = ({ l, titulo, selo, children }) => {
  const { cores, fontes } = useAlma();
  const { w, h } = l.tela;
  return (
    <div style={{ position: "absolute", left: l.tela.left, top: l.tela.top - TELA_BAR, width: w, border: `2px solid ${cores.texto}`,
      background: cores.texto, boxShadow: `8px 8px 0 ${cores.texto}` }}>
      <div style={{ height: TELA_BAR, display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0 12px",
        color: cores.texto_inverso, fontFamily: pilhaFonte(fontes.titulo), fontSize: 26 }}>
        <span>{titulo}</span>
        {selo ? <span style={{ background: cores.destaque, color: cores.texto, padding: "0 8px" }}>{selo}</span> : null}
      </div>
      <div style={{ position: "relative", width: w, height: h, overflow: "hidden", background: cores.texto }}>{children}</div>
    </div>
  );
};

// Tela: 16:9 escala o crop para a largura da janela; 9:16 recorta dentro do crop9 e anda com a câmera.
// origem: cursos-ia/radar-ia-09-jev-calibracao/src/Aula.tsx:88-115
const Tela: React.FC<{ l: Layout; video: string; demo: Demo }> = ({ l, video, demo }) => {
  const t = useCurrentFrame() / FPS;
  const seg = segmentoAtual(demo, t);
  const { w, h } = l.tela;
  const crop = l.vertical ? seg.crop9 : seg.crop;
  let estilo: React.CSSProperties;
  if (l.vertical) {
    const escala = h / crop.h;
    const cx = Math.min(Math.max(cameraX(demo.camera, t), crop.x + w / escala / 2), crop.x + crop.w - w / escala / 2) * escala;
    estilo = { position: "absolute", top: -crop.y * escala, left: w / 2 - cx, width: TELA_ORIGEM.largura * escala, height: TELA_ORIGEM.altura * escala };
  } else {
    const escala = w / crop.w;
    estilo = { position: "absolute", top: -crop.y * escala, left: -crop.x * escala, width: TELA_ORIGEM.largura * escala, height: TELA_ORIGEM.altura * escala };
  }
  const selo = seg.rate >= SELO_ACELERADO ? `▶▶ ${seg.rate.toFixed(1).replace(".", ",")}× acelerado` : null;
  return (
    <MolduraTela l={l} titulo={seg.janela} selo={selo}>
      <OffthreadVideo src={urlDoArquivo(video)} muted style={estilo} />
    </MolduraTela>
  );
};

// Slide de uma apresentação que compõe a aula: a imagem inteira dentro da janela da tela.
const Slide: React.FC<{ l: Layout; cena: Cena }> = ({ l, cena }) => (
  <MolduraTela l={l} titulo={cena.rotulo ?? cena.titulo ?? ""} selo={null}>
    {cena.imagem ? (
      <Img src={urlDoArquivo(cena.imagem)} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "contain" }} />
    ) : null}
  </MolduraTela>
);

// ---------------------------------------------------------------- cartão, PiP, legenda, cabeçalho

const cenaAtual = (cenas: Cena[], cues: Cues, f: number): Cena | undefined =>
  [...cenas].reverse().find((c) => f >= quadro(cues.cues[c.cue] ?? 0));

// Cartão do passo (só no 16:9). origem: cursos-ia/radar-ia-09-jev-calibracao/src/Aula.tsx:117-131
const Cartao: React.FC<{ l: Layout; cenas: Cena[]; cues: Cues }> = ({ l, cenas, cues }) => {
  const f = useCurrentFrame();
  const { fontes } = useAlma();
  const c = cenaAtual(cenas, cues, f);
  if (!l.cartao || !c || !c.passo || !c.fato) return null;
  return (
    <div style={{ position: "absolute", left: l.cartao.left, top: l.cartao.top, width: l.cartao.w }}>
      <Pop at={quadro(cues.cues[c.cue] ?? 0)} key={c.cue}>
        <Janela titulo={c.passo}>
          <div style={{ fontFamily: pilhaFonte(fontes.texto), fontSize: 26, whiteSpace: "pre", lineHeight: 1.45 }}>{c.fato}</div>
        </Janela>
      </Pop>
    </div>
  );
};

// Janela do avatar: o vídeo 4:5 recortado pela faixa útil 16:9, sem som (o som é a narração), com o nome
// do porta-voz da Alma na barra. origem: cursos-ia/radar-ia-09-jev-calibracao/src/Aula.tsx:133-149
const Pip: React.FC<{ l: Layout; avatar: string; fim: number }> = ({ l, avatar, fim }) => {
  const f = useCurrentFrame();
  const { cores, fontes, porta_voz } = useAlma();
  const opacidade = interpolate(f, [fim - FADE_PIP_QUADROS, fim], [1, 0], clamp);
  const { w } = l.pip;
  const h = l.pip.h - PIP_BAR;
  const renderH = (h / AVATAR.conteudo_h) * AVATAR.altura;
  const renderW = renderH * (AVATAR.largura / AVATAR.altura);
  return (
    <div style={{ position: "absolute", left: l.pip.left, top: l.pip.top, width: w, border: `2px solid ${cores.texto}`,
      background: cores.texto, boxShadow: `6px 6px 0 ${cores.texto}`, opacity: opacidade }}>
      <div style={{ height: PIP_BAR, color: cores.texto_inverso, fontFamily: pilhaFonte(fontes.titulo), fontSize: 24,
        lineHeight: `${PIP_BAR}px`, padding: "0 10px", whiteSpace: "nowrap", overflow: "hidden" }}>
        {porta_voz?.nome ?? ""}
      </div>
      <div style={{ position: "relative", width: w, height: h, overflow: "hidden" }}>
        <OffthreadVideo src={urlDoArquivo(avatar)} muted
          style={{ position: "absolute", width: renderW, height: renderH, left: (w - renderW) / 2, top: (h - renderH) / 2 }} />
      </div>
    </div>
  );
};

// Legenda com o texto do roteiro (D-23), 42x2 já quebrada pelo motor. origem: cursos-ia/radar-ia-09-jev-calibracao/src/Aula.tsx:151-164
const Legendas: React.FC<{ l: Layout; legendas: Legenda[] }> = ({ l, legendas }) => {
  const t = useCurrentFrame() / FPS;
  const { cores, fontes } = useAlma();
  const atual = legendas.find((c) => t >= c.start && t < c.end);
  if (!atual) return null;
  return (
    <div style={{ position: "absolute", ...l.legenda, display: "flex", justifyContent: "center", pointerEvents: "none" }}>
      <div style={{ background: cores.texto, padding: "8px 20px", fontFamily: pilhaFonte(fontes.texto), fontSize: l.legendaFonte,
        lineHeight: 1.35, textAlign: "center", color: cores.texto_inverso, border: `2px solid ${cores.texto_inverso}` }}>
        {atual.lines.map((linha, i) => (
          <div key={i}>{linha}</div>
        ))}
      </div>
    </div>
  );
};

// Cantos em L. origem: cursos-ia/radar-ia-09-jev-calibracao/src/Aula.tsx:166-178
const Cantos: React.FC = () => {
  const { cores } = useAlma();
  const m = 26;
  const t = 20;
  const st = (pos: React.CSSProperties, a: string, b: string): React.CSSProperties => ({
    position: "absolute", width: t, height: t, ...pos, [a]: `2px solid ${cores.texto}`, [b]: `2px solid ${cores.texto}`,
  });
  return (
    <>
      <div style={st({ top: m, left: m }, "borderTop", "borderLeft")} />
      <div style={st({ top: m, right: m }, "borderTop", "borderRight")} />
      <div style={st({ bottom: m, left: m }, "borderBottom", "borderLeft")} />
      <div style={st({ bottom: m, right: m }, "borderBottom", "borderRight")} />
    </>
  );
};

// Cabeçalho (série à esquerda, rótulo da cena à direita) e barra de progresso pontilhada.
// origem: cursos-ia/radar-ia-09-jev-calibracao/src/Aula.tsx:180-196
const Cabecalho: React.FC<{ l: Layout; serie: string | null; cenas: Cena[]; cues: Cues }> = ({ l, serie, cenas, cues }) => {
  const f = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const { cores, fontes } = useAlma();
  const rotulo = cenaAtual(cenas, cues, f)?.rotulo ?? "";
  return (
    <>
      <div style={{ position: "absolute", ...l.cabecalho, display: "flex", justifyContent: "space-between", alignItems: "center",
        fontFamily: pilhaFonte(fontes.titulo), fontSize: 32, color: cores.texto }}>
        <div>{serie ?? ""}</div>
        {rotulo ? <div style={{ background: cores.texto, color: cores.texto_inverso, padding: "0 8px" }}>{rotulo}</div> : <div />}
      </div>
      <div style={{ position: "absolute", ...l.progresso, height: 12, border: `2px solid ${cores.texto}`, background: cores.fundo_alt }}>
        <div style={{ width: `${(f / durationInFrames) * 100}%`, height: "100%",
          backgroundImage: `radial-gradient(${cores.texto} 1.3px, transparent 1.4px)`, backgroundSize: "4px 4px" }} />
      </div>
    </>
  );
};

// ---------------------------------------------------------------- composição

const Conteudo: React.FC<Omit<PropsAula, "alma"> & { desenhar: DesenharCena }> = ({
  formato, serie, cues, cenas, legendas, narracao, avatar, tela, desenhar: Desenhar,
}) => {
  const { cores, fontes } = useAlma();
  const { durationInFrames } = useVideoConfig();
  const l = LAYOUTS[formato];
  if (!l) throw new Error(`formato de aula inválido: ${String(formato)} (use 16:9 ou 9:16)`);
  const fimPip = Math.floor((cues.duration - FOLGA_FINAL_S) * FPS);
  const inicios = cenas.map((c) => {
    const t = cues.cues[c.cue];
    if (typeof t !== "number") throw new Error(`a cena ${c.cue} não tem cue em cues.json`);
    return quadro(t);
  });
  return (
    <AbsoluteFill style={{ background: cores.fundo, color: cores.texto, fontFamily: pilhaFonte(fontes.texto) }}>
      <AbsoluteFill style={{ backgroundImage: `radial-gradient(${mistura(cores.texto, 60, "transparent")} 1.6px, transparent 1.8px)`,
        backgroundSize: "8px 8px", opacity: 0.55,
        WebkitMaskImage: "radial-gradient(circle at 100% 0%, black 0%, transparent 38%), radial-gradient(circle at 0% 100%, black 0%, transparent 30%)" }} />
      <Cantos />
      {narracao ? <Audio src={urlDoArquivo(narracao)} /> : null}
      {cenas.map((cena, i) => {
        const de = inicios[i];
        const ate = i + 1 < cenas.length ? inicios[i + 1] : durationInFrames;
        if (ate <= de) return null;
        return (
          <Sequence key={`${cena.cue}-${i}`} from={de} durationInFrames={ate - de} name={`cena-${cena.cue}`}>
            {cena.modo === "cena" ? <Desenhar cena={cena} l={l} indice={i} /> : null}
            {cena.modo === "slide" ? <Slide l={l} cena={cena} /> : null}
          </Sequence>
        );
      })}
      {tela && tela.demo.segmentos.length ? (
        <Sequence from={quadro(tela.demo.inicio)} durationInFrames={Math.max(1, quadro(tela.demo.duracao))} name="tela">
          <Tela l={l} video={tela.video} demo={tela.demo} />
        </Sequence>
      ) : null}
      <Cartao l={l} cenas={cenas} cues={cues} />
      {avatar && fimPip > 0 ? (
        <Sequence durationInFrames={fimPip} name="avatar">
          <Pip l={l} avatar={avatar} fim={fimPip} />
        </Sequence>
      ) : null}
      <Legendas l={l} legendas={legendas} />
      <Cabecalho l={l} serie={serie} cenas={cenas} cues={cues} />
    </AbsoluteFill>
  );
};

// O componente da aula; um template de aula passa `desenhar` para trocar o visual das cenas.
export const Aula: React.FC<PropsAula & { desenhar?: DesenharCena }> = ({ alma, desenhar, ...resto }) => (
  <ProvedorAlma alma={alma}>
    <Conteudo {...resto} desenhar={desenhar ?? CenaPadrao} />
  </ProvedorAlma>
);

// Duração da aula: ceil(duration x fps), a mesma nos dois formatos. origem: cursos-ia/radar-ia-09-jev-calibracao/src/Root.tsx:6
export const quadrosDaAula = (cues: Cues): number => Math.max(1, Math.ceil(cues.duration * FPS));

// Alma e aula neutras de exemplo, só para o Studio abrir a composição sem props (nenhuma marca).
export const EXEMPLO_AULA: PropsAula = {
  alma: {
    cores: {
      fundo: "#FFFFFF",
      fundo_alt: "#EEEEEE",
      texto: "#111111",
      texto_inverso: "#FFFFFF",
      apoio: "#666666",
      destaque: "#444444",
      destaque_2: "#888888",
      positivo: "#555555",
      negativo: "#333333",
    },
    fontes: { titulo: { familia: "sans-serif", arquivos: [] }, texto: { familia: "sans-serif", arquivos: [] } },
    porta_voz: null,
    canal: null,
  },
  formato: "16:9",
  serie: null,
  titulo: "Exemplo",
  cues: { duration: 3, cues: { s1: 0 } },
  cenas: [{ cue: "s1", modo: "cena", rotulo: null, titulo: "Aula de exemplo", texto: "Abra com props para ver uma aula real",
    itens: [], passo: null, fato: null, imagem: null }],
  legendas: [],
  narracao: null,
  avatar: null,
  tela: null,
};

export const composicao: Composicao<PropsAula> = {
  id: "Aula",
  component: Aula,
  fps: FPS,
  width: LAYOUTS["16:9"].largura,
  height: LAYOUTS["16:9"].altura,
  durationInFrames: quadrosDaAula(EXEMPLO_AULA.cues),
  defaultProps: EXEMPLO_AULA,
  calculateMetadata: ({ props }) => {
    const l = LAYOUTS[props.formato] ?? LAYOUTS["16:9"];
    return { durationInFrames: quadrosDaAula(props.cues), width: l.largura, height: l.altura };
  },
};
