import React, { createContext, useContext } from "react";
import { fitText } from "@remotion/layout-utils";
import { AbsoluteFill, Easing, Img, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import type { PropsAlma } from "../../kit/alma";
import { pilhaFonte, urlDoArquivo } from "../../kit/fontes";

// Cenas da apresentação 16:9, uma por tipo de slide do deck (motor/src/expxmedia/producao/apresentacao/deck.py).
// Porte de youtube-squad/apresentacoes/motion/src (scenes/*, components/*, theme.ts) com a marca trocada pela Alma
// (M13): a paleta sai dos papéis de cor, as famílias das fontes da Alma, e o tema do deck troca só o destaque.
// O tema vive num contexto React montado por render (a origem mutava um objeto global em theme.ts:66, o que
// misturava cores com dois decks no mesmo bundle). Medidas sempre derivadas do quadro (u = largura / 1920).
// Sem animação de saída: o último quadro fica parado para quem apresenta falar por cima.

// ---------------------------------------------------------------- schema do deck (espelho de deck.py)

export type Coluna = { titulo: string; itens: string[] };
export type Numero = { valor: number; sufixo?: string | null; rotulo: string; fonte: string };
export type No = { titulo: string; texto?: string | null };
export type SlideTitulo = { tipo: "titulo"; kicker?: string | null; titulo: string; subtitulo?: string | null };
export type SlideDeclaracao = { tipo: "declaracao"; texto: string; autor?: string | null };
export type SlideGrade = { tipo: "grade"; titulo: string; itens: { titulo: string; texto: string }[] };
export type SlideComparacao = { tipo: "comparacao"; titulo: string; esquerda: Coluna; direita: Coluna };
export type SlideEtapas = { tipo: "etapas"; titulo: string; itens: { titulo: string; texto: string }[] };
export type SlideEstatisticas = { tipo: "estatisticas"; titulo: string; numeros: Numero[] };
export type SlideFluxo = { tipo: "fluxo"; titulo: string; nos: No[] };
export type SlideScreenshot = { tipo: "screenshot"; titulo: string; legenda?: string | null; imagem?: string | null };
export type SlideCta = { tipo: "cta"; titulo?: string | null; texto?: string | null; url?: string | null; imagem?: string | null };
export type Slide =
  | SlideTitulo
  | SlideDeclaracao
  | SlideGrade
  | SlideComparacao
  | SlideEtapas
  | SlideEstatisticas
  | SlideFluxo
  | SlideScreenshot
  | SlideCta;
export type TipoSlide = Slide["tipo"];
export type TemaDeck = { nome: string; cor: string | null; logo: string | null };
// Imagens (logo do tema, imagem de slide) chegam como caminho relativo ao public dir do render, ou null.
export type Deck = { titulo: string; tema: TemaDeck | null; slides: Slide[] };

// ---------------------------------------------------------------- tema a partir da Alma

const HEX = /^#[0-9a-fA-F]{6}$/;
const hexParaRgb = (hex: string): [number, number, number] => [
  parseInt(hex.slice(1, 3), 16),
  parseInt(hex.slice(3, 5), 16),
  parseInt(hex.slice(5, 7), 16),
];
const rgbParaHex = (r: number, g: number, b: number) =>
  "#" + [r, g, b].map((v) => Math.max(0, Math.min(255, Math.round(v))).toString(16).padStart(2, "0")).join("").toUpperCase();

/** Mistura a cor com branco (fator 0 a 1). origem: youtube-squad/apresentacoes/motion/src/theme.ts:20-23 */
export const clarear = (cor: string, fator: number) => {
  if (!HEX.test(cor)) return `color-mix(in srgb, ${cor} ${Math.round((1 - fator) * 100)}%, white)`;
  const [r, g, b] = hexParaRgb(cor);
  return rgbParaHex(r + (255 - r) * fator, g + (255 - g) * fator, b + (255 - b) * fator);
};

/** A cor com opacidade (a origem concatenava alfa em hex e quebrava com rgb() ou hex curto). */
export const comAlfa = (cor: string, alfa: number) => {
  if (!HEX.test(cor)) return `color-mix(in srgb, ${cor} ${Math.round(alfa * 100)}%, transparent)`;
  const [r, g, b] = hexParaRgb(cor);
  return `rgba(${r}, ${g}, ${b}, ${alfa})`;
};

const misturar = (a: string, b: string, pesoB: number) => {
  if (!HEX.test(a) || !HEX.test(b)) return `color-mix(in srgb, ${a} ${Math.round((1 - pesoB) * 100)}%, ${b})`;
  const [r1, g1, b1] = hexParaRgb(a);
  const [r2, g2, b2] = hexParaRgb(b);
  return rgbParaHex(r1 + (r2 - r1) * pesoB, g1 + (g2 - g1) * pesoB, b1 + (b2 - b1) * pesoB);
};

export type Tema = {
  cores: {
    bg: string;
    bgSoft: string;
    surface: string;
    surface2: string;
    text: string;
    textSoft: string;
    line: string;
    accent: string;
    accent2: string;
    accent3: string;
    glow: string;
    casa: string; // o destaque da Alma: o CTA é sempre da casa, mesmo com o tema do deck
    sobreCasa: string;
  };
  fontes: { display: string; displayAlt: string; body: string; mono: string };
  deck: Deck;
  rotulo: string; // nome no cabeçalho: tema do deck ou empresa
  empresa: string; // nome da casa no CTA
  idioma: string | null; // formato dos números (a origem fixava o português)
  framesPorSlide: number;
};

// Curvas e molas. origem: youtube-squad/apresentacoes/motion/src/theme.ts:49-58
export const EASE = {
  out: Easing.bezier(0.16, 1, 0.3, 1),
  inOut: Easing.bezier(0.83, 0, 0.17, 1),
  in: Easing.bezier(0.7, 0, 0.84, 0),
};
export const SPRING = {
  snappy: { damping: 14, stiffness: 160, mass: 0.6 },
  smooth: { damping: 20, stiffness: 90, mass: 1 },
  bouncy: { damping: 11, stiffness: 170, mass: 0.7 },
};

/** Tema do render: paleta dos papéis da Alma; a cor do tema do deck troca só o destaque (theme.ts:61-73). */
export const montarTema = (
  alma: PropsAlma,
  deck: Deck,
  rotulo: string,
  empresa: string,
  idioma: string | null,
  framesPorSlide: number,
): Tema => {
  const c = alma.cores;
  const corTema = deck.tema?.cor && HEX.test(deck.tema.cor) ? deck.tema.cor.toUpperCase() : null;
  const accent = corTema ?? c.destaque;
  // origem: theme.ts:66-71 (accent2 = segunda cor ou clarear 18%; accent3 = clarear 45%; glow a 35%)
  const accent2 = corTema ? clarear(corTema, 0.18) : c.destaque_2;
  return {
    cores: {
      bg: c.fundo,
      bgSoft: misturar(c.fundo, c.texto, 0.04),
      surface: c.fundo_alt,
      surface2: misturar(c.fundo_alt, c.texto, 0.08),
      text: c.texto,
      textSoft: c.apoio,
      line: comAlfa(c.texto, 0.12),
      accent,
      accent2,
      accent3: clarear(accent, 0.45),
      glow: comAlfa(accent, 0.35),
      casa: c.destaque,
      sobreCasa: c.texto_inverso,
    },
    fontes: {
      display: pilhaFonte(alma.fontes.titulo),
      displayAlt: pilhaFonte(alma.fontes.titulo),
      body: pilhaFonte(alma.fontes.texto),
      mono: pilhaFonte(alma.fontes.texto),
    },
    deck,
    rotulo,
    empresa,
    idioma,
    framesPorSlide,
  };
};

const ContextoTema = createContext<Tema | null>(null);
export const ProvedorTema: React.FC<{ tema: Tema; children: React.ReactNode }> = ({ tema, children }) => (
  <ContextoTema.Provider value={tema}>{children}</ContextoTema.Provider>
);
export const useTema = (): Tema => {
  const t = useContext(ContextoTema);
  if (!t) throw new Error("cena da apresentação fora do ProvedorTema");
  return t;
};

// ---------------------------------------------------------------- componentes (components/*.tsx da origem)

/** Medidas derivadas do quadro. origem: scenes/Slide.tsx:16-20 */
export const useMedidas = () => {
  const { width, height } = useVideoConfig();
  const pad = Math.round(width * 0.05);
  return { width, height, pad, inner: width - pad * 2, altura: height - pad * 2, u: width / 1920 };
};

type Variante = "rise" | "fall" | "left" | "right" | "pop";
// origem: components/Entrance.tsx:12-17
const VARIANTES: Record<Variante, { axis: "x" | "y"; distance: number; from: number; config: keyof typeof SPRING }> = {
  rise: { axis: "y", distance: 40, from: 0.94, config: "smooth" },
  fall: { axis: "y", distance: -40, from: 0.94, config: "smooth" },
  left: { axis: "x", distance: 90, from: 0.96, config: "snappy" },
  right: { axis: "x", distance: -90, from: 0.96, config: "snappy" },
  pop: { axis: "y", distance: 14, from: 0.62, config: "bouncy" },
};
const varianteDe = (i: number): Variante => (["rise", "left", "fall", "right"] as Variante[])[i % 4];
const CLAMP = { extrapolateLeft: "clamp", extrapolateRight: "clamp" } as const;

/** Entrada: opacidade + deslocamento + escala juntas, nunca fade puro. origem: components/Entrance.tsx */
export const Entrance: React.FC<{
  delay?: number;
  rise?: number;
  variant?: Variante;
  config?: keyof typeof SPRING;
  style?: React.CSSProperties;
  children: React.ReactNode;
}> = ({ delay = 0, rise, variant = "rise", config, style, children }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const v = VARIANTES[variant];
  const p = spring({ frame: frame - delay, fps, config: SPRING[config ?? v.config] });
  const shift = interpolate(p, [0, 1], [rise ?? v.distance, 0], CLAMP);
  const move = v.axis === "y" ? `translateY(${shift}px)` : `translateX(${shift}px)`;
  return (
    <div style={{ opacity: p, transform: `${move} scale(${interpolate(p, [0, 1], [v.from, 1], CLAMP)})`, ...style }}>{children}</div>
  );
};

/** Lista escalonada, variante alternada por item. origem: components/Stagger.tsx */
const Stagger: React.FC<{
  items: React.ReactNode[];
  startAt?: number;
  offset?: number;
  variant?: Variante | "alternada";
  itemStyle?: React.CSSProperties;
  containerStyle?: React.CSSProperties;
}> = ({ items, startAt = 0, offset = 5, variant = "alternada", itemStyle, containerStyle }) => (
  <div style={containerStyle}>
    {items.map((item, i) => (
      <Entrance key={i} delay={startAt + i * offset} variant={variant === "alternada" ? varianteDe(i) : variant} style={itemStyle}>
        {item}
      </Entrance>
    ))}
  </div>
);

/** Palavras do texto e se estão em <b>. origem: components/WordReveal.tsx:9-20 */
export const parseDestaque = (raw: string): { text: string; accent: boolean }[] => {
  const tokens: { text: string; accent: boolean }[] = [];
  for (const part of raw.split(/(<b>.*?<\/b>)/g).filter(Boolean)) {
    const match = part.match(/^<b>(.*?)<\/b>$/);
    for (const word of (match ? match[1] : part).split(" ").filter(Boolean)) tokens.push({ text: word, accent: Boolean(match) });
  }
  return tokens;
};

/** Palavra a palavra; `fontSize` é teto e encolhe até a palavra mais longa caber (fitText com a fonte validada). */
const WordReveal: React.FC<{
  text: string;
  withinWidth: number;
  fontSize: number;
  delay?: number;
  per?: number;
  fontFamily?: string;
  accentColor?: string;
  style?: React.CSSProperties;
}> = ({ text, withinWidth, fontSize, delay = 0, per = 3, fontFamily, accentColor, style }) => {
  const t = useTema();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const tokens = parseDestaque(text);
  const family = fontFamily ?? t.fontes.display;
  const longest = tokens.reduce((acc, token) => (token.text.length > acc.length ? token.text : acc), "");
  // origem: components/WordReveal.tsx:41-49 (validateFontIsLoaded: fonte que não carregou é erro, não serifada).
  // O peso entra na medida: a origem usava uma display de peso único; a fonte da Alma tem vários.
  const fitted = fitText({
    text: longest,
    withinWidth,
    fontFamily: family,
    fontWeight: style?.fontWeight as number | string | undefined,
    textTransform: (style?.textTransform as "uppercase" | undefined) ?? "none",
    validateFontIsLoaded: true,
  });
  const size = Math.min(fontSize, fitted.fontSize);
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "0 0.26em", fontFamily: family, color: t.cores.text, ...style, fontSize: size, maxWidth: withinWidth }}>
      {tokens.map((token, i) => {
        const p = spring({ frame: frame - (delay + i * per), fps, config: SPRING.snappy });
        return (
          <span
            key={i}
            style={{
              display: "inline-block",
              opacity: p,
              color: token.accent ? accentColor ?? t.cores.accent : undefined,
              transform: `translateY(${interpolate(p, [0, 1], [30, 0], CLAMP)}px)`,
            }}
          >
            {token.text}
          </span>
        );
      })}
    </div>
  );
};

/** Número animado. origem: components/Counter.tsx (formatado no idioma do navegador de render) */
const Counter: React.FC<{ target: number; delay?: number; suffix?: string }> = ({ target, delay = 0, suffix = "" }) => {
  const t = useTema();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const casas = Number.isInteger(target) ? 0 : 1;
  const p = spring({ frame: frame - delay, fps, config: SPRING.smooth });
  const value = interpolate(p, [0, 1], [0, target], CLAMP);
  return (
    <span style={{ fontFamily: t.fontes.mono, fontVariantNumeric: "tabular-nums", color: t.cores.accent }}>
      {value.toLocaleString(t.idioma ?? undefined, { minimumFractionDigits: casas, maximumFractionDigits: casas })}
      {suffix}
    </span>
  );
};

// origem: components/KenBurns.tsx:6-10
const ZOOM = { slow: { from: 1.0, to: 1.03 }, normal: { from: 1.02, to: 1.06 }, fast: { from: 1.0, to: 1.1 } } as const;

/** Ken Burns em toda imagem estática, mesma curva no pan e no zoom. origem: components/KenBurns.tsx */
const KenBurns: React.FC<{ src: string; speed?: keyof typeof ZOOM; dir?: 1 | -1; panPx?: number }> = ({ src, speed = "normal", dir = 1, panPx = -20 }) => {
  const frame = useCurrentFrame();
  const { framesPorSlide } = useTema();
  const range = ZOOM[speed];
  const from = dir > 0 ? range.from : range.to;
  const to = dir > 0 ? range.to : range.from;
  const opts = { easing: EASE.inOut, ...CLAMP };
  const scale = interpolate(frame, [0, framesPorSlide], [from, to], opts);
  const pan = interpolate(frame, [0, framesPorSlide], [0, panPx * dir], opts);
  return <Img src={urlDoArquivo(src)} style={{ width: "100%", height: "100%", objectFit: "cover", transform: `scale(${scale}) translateX(${pan}px)` }} />;
};

/** Respiro: elemento parado por mais de 2 s nunca fica imóvel. origem: components/Timeline.ts:29-31 */
const breathe = (frame: number, fps: number, amplitude = 4, seconds = 4) => Math.sin((frame / (fps * seconds)) * Math.PI * 2) * amplitude;

/** Fundo com textura, proporcional ao quadro. origem: components/Layers.tsx:8-53 */
const BgMesh: React.FC<{ accent?: string }> = ({ accent }) => {
  const t = useTema();
  const frame = useCurrentFrame();
  const cor = accent ?? t.cores.accent;
  const cor2 = accent ? clarear(accent, 0.18) : t.cores.accent2;
  const { width, height } = useVideoConfig();
  const d1 = Math.sin(frame / 55) * width * 0.03;
  const d2 = Math.cos(frame / 70) * width * 0.025;
  const grande = Math.round(Math.max(width, height) * 0.7);
  const medio = Math.round(Math.max(width, height) * 0.5);
  return (
    <AbsoluteFill style={{ background: t.cores.bg }}>
      <div style={{ position: "absolute", width: grande, height: grande, borderRadius: "50%", top: -grande * 0.42, left: -grande * 0.18 + d1, filter: "blur(70px)", background: `radial-gradient(circle, ${comAlfa(cor, 0.14)}, transparent 60%)` }} />
      <div style={{ position: "absolute", width: medio, height: medio, borderRadius: "50%", bottom: -medio * 0.45, right: -medio * 0.22 - d2, filter: "blur(90px)", background: `radial-gradient(circle, ${comAlfa(cor2, 0.1)}, transparent 62%)` }} />
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: `linear-gradient(${t.cores.line} 1px, transparent 1px), linear-gradient(90deg, ${t.cores.line} 1px, transparent 1px)`,
          backgroundSize: `${Math.round(width / 24)}px ${Math.round(width / 24)}px`,
          opacity: 0.35,
          maskImage: "radial-gradient(ellipse at center, black 30%, transparent 78%)",
          WebkitMaskImage: "radial-gradient(ellipse at center, black 30%, transparent 78%)",
        }}
      />
    </AbsoluteFill>
  );
};

// Grão procedural, sem asset. origem: components/Layers.tsx:65-79
const RUIDO = `url("data:image/svg+xml,%3Csvg xmlns='http%3A%2F%2Fwww.w3.org%2F2000%2Fsvg' width='220' height='220'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/%3E%3C/filter%3E%3Crect width='220' height='220' filter='url(%23n)' opacity='0.5'/%3E%3C/svg%3E")`;

/** Acabamento: tinta da marca em soft-light, grão e vinheta. origem: components/Layers.tsx:56-93 */
const Finish: React.FC<{ gradeOpacity?: number; accent?: string }> = ({ gradeOpacity = 0.12, accent }) => {
  const t = useTema();
  const frame = useCurrentFrame();
  return (
    <>
      <AbsoluteFill style={{ pointerEvents: "none" }}>
        <AbsoluteFill style={{ backgroundColor: accent ?? t.cores.accent, mixBlendMode: "soft-light", opacity: gradeOpacity }} />
        <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,0.12), transparent 26%, transparent 74%, rgba(0,0,0,0.22))" }} />
      </AbsoluteFill>
      <AbsoluteFill style={{ pointerEvents: "none", backgroundImage: RUIDO, backgroundSize: "220px", backgroundPosition: `${(frame * 7) % 220}px ${(frame * 13) % 220}px`, opacity: 0.05, mixBlendMode: "multiply" }} />
      <AbsoluteFill style={{ pointerEvents: "none", background: "radial-gradient(ellipse at center, transparent 56%, rgba(0,0,0,0.24) 100%)" }} />
    </>
  );
};

/** Cabeçalho `NN / TOTAL` + logo do tema (ou ponto) + nome. origem: scenes/Slide.tsx:22-52 */
const Cabecalho: React.FC<{ index: number; marcaTexto?: string; cor?: string; semLogo?: boolean }> = ({ index, marcaTexto, cor, semLogo }) => {
  const t = useTema();
  const { u } = useMedidas();
  const logo = semLogo ? null : t.deck.tema?.logo ?? null;
  return (
    <Entrance delay={0} rise={16}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontFamily: t.fontes.mono, fontSize: 24 * u, color: t.cores.textSoft, letterSpacing: 2 }}>
        <span>
          {String(index + 1).padStart(2, "0")} / {String(t.deck.slides.length).padStart(2, "0")}
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 14 * u, color: cor ?? t.cores.textSoft }}>
          {logo ? (
            <Img src={urlDoArquivo(logo)} style={{ width: 36 * u, height: 36 * u, objectFit: "contain", borderRadius: 8 * u }} />
          ) : (
            <span style={{ width: 12 * u, height: 12 * u, borderRadius: "50%", background: cor ?? t.cores.accent, display: "inline-block" }} />
          )}
          <span style={{ textTransform: "uppercase" }}>{marcaTexto ?? t.rotulo}</span>
        </span>
      </div>
    </Entrance>
  );
};

/** Moldura de todo slide: fundo, cabeçalho, conteúdo respirando e acabamento. origem: scenes/Slide.tsx:54-85 */
const Moldura: React.FC<{ index: number; marcaTexto?: string; cor?: string; gradeOpacity?: number; semLogo?: boolean; children: React.ReactNode }> = ({
  index,
  marcaTexto,
  cor,
  gradeOpacity,
  semLogo,
  children,
}) => {
  const t = useTema();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { pad } = useMedidas();
  return (
    <AbsoluteFill style={{ fontFamily: t.fontes.displayAlt, color: t.cores.text }}>
      <BgMesh accent={cor} />
      <AbsoluteFill style={{ padding: pad }}>
        <Cabecalho index={index} marcaTexto={marcaTexto} cor={cor} semLogo={semLogo} />
        <div style={{ flex: 1, display: "flex", flexDirection: "column", justifyContent: "center", transform: `translateY(${breathe(frame, fps, 3, 5)}px)` }}>
          {children}
        </div>
      </AbsoluteFill>
      <Finish gradeOpacity={gradeOpacity} accent={cor} />
    </AbsoluteFill>
  );
};

const slideDe = <T extends TipoSlide>(deck: Deck, index: number, tipo: T) => {
  const s = deck.slides[index];
  if (!s || s.tipo !== tipo) throw new Error(`slide ${index + 1} não é do tipo ${tipo}`);
  return s as Extract<Slide, { tipo: T }>;
};

/** Título de seção, tipográfico. origem: scenes/Slide.tsx:103-123 */
const TituloDeSecao: React.FC<{ texto: string; delay?: number }> = ({ texto, delay = 4 }) => {
  const t = useTema();
  const { inner, u } = useMedidas();
  return (
    <Entrance delay={delay} rise={24}>
      <h2 style={{ margin: 0, marginBottom: 40 * u, fontFamily: t.fontes.displayAlt, fontWeight: 700, fontSize: 58 * u, lineHeight: 1.08, maxWidth: inner * 0.8, letterSpacing: -0.5 }}>
        {texto}
      </h2>
    </Entrance>
  );
};

export type CenaProps = { index: number };

// ---------------------------------------------------------------- cenas (scenes/*.tsx da origem)

/** Título: kicker, título palavra a palavra com o <b> em destaque, linha e subtítulo. origem: scenes/Titulo.tsx */
export const Titulo: React.FC<CenaProps> = ({ index }) => {
  const t = useTema();
  const s = slideDe(t.deck, index, "titulo");
  const { inner, u } = useMedidas();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const linha = spring({ frame: frame - 30, fps, config: SPRING.smooth });
  return (
    <Moldura index={index}>
      {s.kicker ? (
        <Entrance delay={4} rise={18}>
          <p style={{ margin: 0, marginBottom: 28 * u, fontFamily: t.fontes.mono, fontSize: 26 * u, letterSpacing: 4, textTransform: "uppercase", color: t.cores.accent }}>{s.kicker}</p>
        </Entrance>
      ) : null}
      <WordReveal text={s.titulo} delay={8} per={3} withinWidth={inner * 0.88} fontSize={138 * u} style={{ lineHeight: 0.98, textTransform: "uppercase", fontWeight: 700 }} />
      <div style={{ marginTop: 30 * u, height: 6 * u, width: interpolate(linha, [0, 1], [0, 220 * u], CLAMP), background: t.cores.accent, borderRadius: 3 }} />
      {s.subtitulo ? (
        <Entrance delay={36} rise={24}>
          <p style={{ margin: 0, marginTop: 30 * u, fontFamily: t.fontes.body, fontSize: 40 * u, lineHeight: 1.3, color: t.cores.textSoft, maxWidth: inner * 0.7 }}>{s.subtitulo}</p>
        </Entrance>
      ) : null}
    </Moldura>
  );
};

/** Declaração: frase grande, aspas no destaque, autor. origem: scenes/Declaracao.tsx */
export const Declaracao: React.FC<CenaProps> = ({ index }) => {
  const t = useTema();
  const s = slideDe(t.deck, index, "declaracao");
  const { inner, u } = useMedidas();
  return (
    <Moldura index={index}>
      <div style={{ display: "flex", gap: 40 * u, alignItems: "flex-start", maxWidth: inner * 0.92 }}>
        <Entrance delay={2} variant="pop">
          <span style={{ fontFamily: t.fontes.display, fontSize: 220 * u, lineHeight: 0.7, color: t.cores.accent, opacity: 0.9 }}>{"“"}</span>
        </Entrance>
        <div>
          <WordReveal text={s.texto} delay={8} per={3} withinWidth={inner * 0.78} fontSize={82 * u} fontFamily={t.fontes.displayAlt} style={{ lineHeight: 1.12, fontWeight: 700 }} />
          {s.autor ? (
            <Entrance delay={44} rise={20}>
              <p style={{ margin: 0, marginTop: 36 * u, fontFamily: t.fontes.mono, fontSize: 26 * u, letterSpacing: 3, textTransform: "uppercase", color: t.cores.textSoft }}>
                <span style={{ display: "inline-block", width: 40 * u, height: 2, background: t.cores.line, verticalAlign: "middle", marginRight: 16 * u }} />
                {s.autor}
              </p>
            </Entrance>
          ) : null}
        </div>
      </div>
    </Moldura>
  );
};

/** Grade de cartões (3 a 6), até 4 colunas, senão 3. origem: scenes/Grade.tsx */
export const Grade: React.FC<CenaProps> = ({ index }) => {
  const t = useTema();
  const s = slideDe(t.deck, index, "grade");
  const { u } = useMedidas();
  const cols = s.itens.length <= 4 ? Math.min(s.itens.length, 4) : 3;
  return (
    <Moldura index={index}>
      <TituloDeSecao texto={s.titulo} />
      <Stagger
        startAt={22}
        offset={5}
        containerStyle={{ display: "grid", gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))`, gap: 24 * u }}
        itemStyle={{ height: "100%" }}
        items={s.itens.map((item, i) => (
          <div key={i} style={{ height: "100%", boxSizing: "border-box", padding: 32 * u, borderRadius: 20 * u, background: t.cores.surface, border: `1px solid ${t.cores.line}`, borderTop: `4px solid ${t.cores.accent}` }}>
            <p style={{ margin: 0, fontFamily: t.fontes.mono, fontSize: 20 * u, color: t.cores.textSoft, letterSpacing: 2 }}>{String(i + 1).padStart(2, "0")}</p>
            <h3 style={{ margin: `${12 * u}px 0 ${14 * u}px`, fontFamily: t.fontes.displayAlt, fontWeight: 700, fontSize: 36 * u, lineHeight: 1.1 }}>{item.titulo}</h3>
            <p style={{ margin: 0, fontFamily: t.fontes.body, fontSize: 26 * u, lineHeight: 1.35, color: t.cores.textSoft }}>{item.texto}</p>
          </div>
        ))}
      />
    </Moldura>
  );
};

const ColunaComparacao: React.FC<{ col: Coluna; destaque: boolean; startAt: number }> = ({ col, destaque, startAt }) => {
  const t = useTema();
  const { u } = useMedidas();
  return (
    <div style={{ padding: 40 * u, borderRadius: 24 * u, background: destaque ? t.cores.surface : "transparent", border: `1px solid ${destaque ? t.cores.accent : t.cores.line}`, boxShadow: destaque ? `0 0 0 1px ${t.cores.line}` : undefined }}>
      <h3 style={{ margin: 0, marginBottom: 28 * u, fontFamily: t.fontes.displayAlt, fontWeight: 700, fontSize: 40 * u, color: destaque ? t.cores.accent : t.cores.textSoft, textTransform: "uppercase", letterSpacing: 1 }}>{col.titulo}</h3>
      <Stagger
        startAt={startAt}
        offset={5}
        variant="rise"
        containerStyle={{ display: "flex", flexDirection: "column", gap: 18 * u }}
        items={col.itens.map((item, i) => (
          <p key={i} style={{ margin: 0, display: "flex", gap: 18 * u, alignItems: "baseline", fontFamily: t.fontes.body, fontSize: 30 * u, lineHeight: 1.3, color: destaque ? t.cores.text : t.cores.textSoft }}>
            <span style={{ width: 12 * u, height: 12 * u, flex: "none", background: destaque ? t.cores.accent : t.cores.textSoft, transform: "translateY(-2px)", opacity: destaque ? 1 : 0.6 }} />
            {item}
          </p>
        ))}
      />
    </div>
  );
};

/** A contra B: coluna apagada à esquerda, coluna do destaque à direita. origem: scenes/Comparacao.tsx */
export const Comparacao: React.FC<CenaProps> = ({ index }) => {
  const t = useTema();
  const s = slideDe(t.deck, index, "comparacao");
  const { u } = useMedidas();
  return (
    <Moldura index={index}>
      <TituloDeSecao texto={s.titulo} />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 32 * u }}>
        <Entrance delay={18} variant="right">
          <ColunaComparacao col={s.esquerda} destaque={false} startAt={30} />
        </Entrance>
        <Entrance delay={24} variant="left">
          <ColunaComparacao col={s.direita} destaque startAt={36} />
        </Entrance>
      </div>
    </Moldura>
  );
};

/** Passo a passo (3 a 5): horizontal com 4 ou mais. origem: scenes/Etapas.tsx */
export const Etapas: React.FC<CenaProps> = ({ index }) => {
  const t = useTema();
  const s = slideDe(t.deck, index, "etapas");
  const { u, inner } = useMedidas();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const trilho = spring({ frame: frame - 26, fps, config: SPRING.smooth });
  const horizontal = s.itens.length >= 4;
  const pct = `${interpolate(trilho, [0, 1], [0, 100], CLAMP)}%`;
  return (
    <Moldura index={index}>
      <TituloDeSecao texto={s.titulo} />
      <div style={{ position: "relative" }}>
        <div style={{ position: "absolute", left: horizontal ? 0 : 34 * u, top: horizontal ? 34 * u : 0, height: horizontal ? 2 : pct, width: horizontal ? pct : 2, background: t.cores.line }} />
        <Stagger
          startAt={24}
          offset={6}
          variant={horizontal ? "rise" : "left"}
          containerStyle={horizontal ? { display: "grid", gridTemplateColumns: `repeat(${s.itens.length}, minmax(0, 1fr))`, gap: 28 * u } : { display: "flex", flexDirection: "column", gap: 26 * u, maxWidth: inner * 0.8 }}
          items={s.itens.map((item, i) => (
            <div key={i} style={{ display: "flex", flexDirection: horizontal ? "column" : "row", gap: 24 * u, alignItems: "flex-start" }}>
              <span style={{ flex: "none", width: 70 * u, height: 70 * u, borderRadius: "50%", background: t.cores.bg, border: `2px solid ${t.cores.accent}`, color: t.cores.accent, fontFamily: t.fontes.mono, fontSize: 30 * u, display: "flex", alignItems: "center", justifyContent: "center" }}>
                {i + 1}
              </span>
              <div>
                <h3 style={{ margin: 0, marginBottom: 10 * u, fontFamily: t.fontes.displayAlt, fontWeight: 700, fontSize: 36 * u, lineHeight: 1.1 }}>{item.titulo}</h3>
                <p style={{ margin: 0, fontFamily: t.fontes.body, fontSize: 26 * u, lineHeight: 1.35, color: t.cores.textSoft }}>{item.texto}</p>
              </div>
            </div>
          ))}
        />
      </div>
    </Moldura>
  );
};

/** Números (1 a 4) animados, com a fonte de cada um embaixo. origem: scenes/Estatisticas.tsx */
export const Estatisticas: React.FC<CenaProps> = ({ index }) => {
  const t = useTema();
  const s = slideDe(t.deck, index, "estatisticas");
  const { u } = useMedidas();
  const n = s.numeros.length;
  // origem: scenes/Estatisticas.tsx:12 (200 / 150 / 110 conforme 1, 2 ou 3+ números)
  const tamanho = n === 1 ? 200 : n === 2 ? 150 : 110;
  return (
    <Moldura index={index}>
      <TituloDeSecao texto={s.titulo} />
      <Stagger
        startAt={20}
        offset={6}
        variant="rise"
        containerStyle={{ display: "grid", gridTemplateColumns: `repeat(${n}, minmax(0, 1fr))`, gap: 32 * u }}
        items={s.numeros.map((num, i) => (
          <div key={i} style={{ padding: 36 * u, borderRadius: 24 * u, background: t.cores.surface, border: `1px solid ${t.cores.line}` }}>
            <div style={{ fontSize: tamanho * u, lineHeight: 1, letterSpacing: -2 }}>
              <Counter target={num.valor} delay={24 + i * 6} suffix={num.sufixo ?? ""} />
            </div>
            <p style={{ margin: `${18 * u}px 0 0`, fontFamily: t.fontes.displayAlt, fontWeight: 600, fontSize: 30 * u, textTransform: "uppercase", letterSpacing: 1 }}>{num.rotulo}</p>
            <p style={{ margin: `${10 * u}px 0 0`, fontFamily: t.fontes.mono, fontSize: 18 * u, color: t.cores.textSoft }}>fonte: {num.fonte}</p>
          </div>
        ))}
      />
    </Moldura>
  );
};

// origem: scenes/Fluxo.tsx:11-13
const FLUXO_INICIO = 24;
const FLUXO_POR_NO = 9;
const FLUXO_SETA_ATRASO = 5;
type Caixa = { x: number; y: number; w: number; h: number; linha: number };

/** Posição dos nós: 1 linha até 4, 2 linhas acima. origem: scenes/Fluxo.tsx:17-31 */
const caixas = (n: number, inner: number, u: number): { itens: Caixa[]; alturaTotal: number } => {
  const linhas = n <= 4 ? 1 : 2;
  const colunas = linhas === 1 ? n : Math.ceil(n / 2);
  const gapX = 96 * u;
  const gapY = 120 * u;
  const w = (inner - gapX * (colunas - 1)) / colunas;
  const h = (linhas === 1 ? 230 : 200) * u;
  const itens: Caixa[] = [];
  for (let i = 0; i < n; i++) {
    const linha = Math.floor(i / colunas);
    itens.push({ x: (i % colunas) * (w + gapX), y: linha * (h + gapY), w, h, linha });
  }
  return { itens, alturaTotal: linhas * h + (linhas - 1) * gapY };
};

/** Caminho da seta entre dois nós e o comprimento. origem: scenes/Fluxo.tsx:34-49 */
const seta = (a: Caixa, b: Caixa, u: number): { d: string; len: number } => {
  const folga = 14 * u;
  if (a.linha === b.linha) {
    const x1 = a.x + a.w + folga, x2 = b.x - folga, y = a.y + a.h / 2;
    return { d: `M ${x1} ${y} L ${x2} ${y}`, len: Math.max(1, x2 - x1) };
  }
  const x1 = a.x + a.w + folga, y1 = a.y + a.h / 2;
  const xDir = x1 + 34 * u;
  const yMeio = a.y + a.h + (b.y - (a.y + a.h)) / 2;
  const xEsq = b.x - 34 * u - folga;
  const x2 = b.x - folga, y2 = b.y + b.h / 2;
  const d = `M ${x1} ${y1} L ${xDir} ${y1} L ${xDir} ${yMeio} L ${xEsq} ${yMeio} L ${xEsq} ${y2} L ${x2} ${y2}`;
  return { d, len: xDir - x1 + (yMeio - y1) + (xDir - xEsq) + (y2 - yMeio) + (x2 - xEsq) };
};

/** Diagrama de fluxo (3 a 6 nós): setas se desenham, depois o brilho percorre os nós. origem: scenes/Fluxo.tsx */
export const Fluxo: React.FC<CenaProps> = ({ index }) => {
  const t = useTema();
  const s = slideDe(t.deck, index, "fluxo");
  const { u, inner } = useMedidas();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const n = s.nos.length;
  const { itens, alturaTotal } = caixas(n, inner, u);
  const fim = FLUXO_INICIO + n * FLUXO_POR_NO + 30;
  // origem: scenes/Fluxo.tsx:60 (um nó brilha por vez, a cada 1,2 s)
  const ativo = frame >= fim ? Math.floor((frame - fim) / (fps * 1.2)) % n : -1;
  const cor = t.cores.accent;
  const idPonta = `ponta-${index}`;
  return (
    <Moldura index={index}>
      <TituloDeSecao texto={s.titulo} />
      <div style={{ position: "relative", width: inner, height: alturaTotal }}>
        <svg width={inner} height={alturaTotal} style={{ position: "absolute", inset: 0, overflow: "visible" }}>
          <defs>
            <marker id={idPonta} markerWidth="12" markerHeight="12" refX="9" refY="6" orient="auto" markerUnits="userSpaceOnUse">
              <path d="M 1 1 L 10 6 L 1 11 z" fill={cor} />
            </marker>
          </defs>
          {itens.slice(0, -1).map((a, i) => {
            const { d, len } = seta(a, itens[i + 1], u);
            const p = spring({ frame: frame - (FLUXO_INICIO + (i + 1) * FLUXO_POR_NO + FLUXO_SETA_ATRASO), fps, config: SPRING.smooth });
            const brilhando = ativo === i || ativo === i + 1;
            return (
              <path
                key={i}
                d={d}
                fill="none"
                stroke={brilhando ? cor : t.cores.textSoft}
                strokeWidth={brilhando ? 4 * u : 3 * u}
                strokeLinejoin="round"
                strokeDasharray={len}
                strokeDashoffset={interpolate(p, [0, 1], [len, 0], CLAMP)}
                markerEnd={p > 0.97 ? `url(#${idPonta})` : undefined}
                opacity={brilhando ? 1 : 0.7}
              />
            );
          })}
        </svg>
        {s.nos.map((no, i) => {
          const c = itens[i];
          const brilha = ativo === i;
          return (
            <div key={i} style={{ position: "absolute", left: c.x, top: c.y, width: c.w, height: c.h }}>
              <Entrance delay={FLUXO_INICIO + i * FLUXO_POR_NO} variant={i % 2 === 0 ? "rise" : "fall"} style={{ height: "100%" }}>
                <div style={{ boxSizing: "border-box", height: "100%", padding: `${22 * u}px ${26 * u}px`, borderRadius: 18 * u, background: t.cores.surface, border: `2px solid ${brilha ? cor : t.cores.line}`, boxShadow: brilha ? `0 0 0 1px ${comAlfa(cor, 0.2)}, 0 0 40px ${comAlfa(cor, 0.33)}` : "none", display: "flex", flexDirection: "column", gap: 10 * u }}>
                  <span style={{ fontFamily: t.fontes.mono, fontSize: 20 * u, color: cor, letterSpacing: 2 }}>{String(i + 1).padStart(2, "0")}</span>
                  <h3 style={{ margin: 0, fontFamily: t.fontes.displayAlt, fontWeight: 700, fontSize: 32 * u, lineHeight: 1.1 }}>{no.titulo}</h3>
                  {no.texto ? <p style={{ margin: 0, fontFamily: t.fontes.body, fontSize: 23 * u, lineHeight: 1.3, color: t.cores.textSoft }}>{no.texto}</p> : null}
                </div>
              </Entrance>
            </div>
          );
        })}
      </div>
    </Moldura>
  );
};

/** Evidência de tela numa moldura; sem imagem, a moldura mostra a legenda (nunca <Img> inexistente). origem: scenes/Screenshot.tsx */
export const Screenshot: React.FC<CenaProps> = ({ index }) => {
  const t = useTema();
  const s = slideDe(t.deck, index, "screenshot");
  const { u, inner, altura } = useMedidas();
  return (
    <Moldura index={index} gradeOpacity={0.06}>
      <Entrance delay={4} rise={20}>
        <h2 style={{ margin: 0, marginBottom: 22 * u, fontFamily: t.fontes.displayAlt, fontWeight: 700, fontSize: 48 * u, lineHeight: 1.1 }}>{s.titulo}</h2>
      </Entrance>
      <Entrance delay={14} rise={40} config="smooth">
        <div style={{ width: inner, height: altura * 0.66, borderRadius: 22 * u, overflow: "hidden", background: t.cores.bgSoft, border: `1px solid ${t.cores.line}`, boxShadow: `0 30px 80px rgba(0,0,0,0.45), 0 0 0 1px ${t.cores.line}`, position: "relative" }}>
          <div style={{ height: 34 * u, background: t.cores.surface2, display: "flex", alignItems: "center", gap: 8 * u, padding: `0 ${16 * u}px` }}>
            {[0, 1, 2].map((i) => (
              <span key={i} style={{ width: 11 * u, height: 11 * u, borderRadius: "50%", background: i === 0 ? t.cores.accent : t.cores.line }} />
            ))}
          </div>
          <div style={{ position: "absolute", top: 34 * u, left: 0, right: 0, bottom: 0 }}>
            {s.imagem ? (
              <KenBurns src={s.imagem} speed="slow" dir={index % 2 === 0 ? 1 : -1} />
            ) : (
              <div style={{ height: "100%", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: t.fontes.mono, fontSize: 28 * u, color: t.cores.textSoft, letterSpacing: 2 }}>
                {s.legenda ?? "captura não disponível"}
              </div>
            )}
          </div>
        </div>
      </Entrance>
      {s.legenda && s.imagem ? (
        <Entrance delay={30} rise={16}>
          <p style={{ margin: `${20 * u}px 0 0`, fontFamily: t.fontes.mono, fontSize: 24 * u, color: t.cores.textSoft, letterSpacing: 1 }}>{s.legenda}</p>
        </Entrance>
      ) : null}
    </Moldura>
  );
};

/** O endereço como aparece no slide: sem esquema, sem `www.` e sem barra final. */
export const urlVisivel = (url?: string | null) =>
  (url ?? "").trim().replace(/^(?:[a-z][a-z0-9+.-]*:)?\/\//i, "").replace(/^www\./, "").replace(/\/+$/, "");

/** CTA final, sempre na cor da casa (destaque da Alma), com o destino da Alma. origem: scenes/Cta.tsx */
export const Cta: React.FC<CenaProps> = ({ index }) => {
  const t = useTema();
  const s = slideDe(t.deck, index, "cta");
  const { u, inner, altura } = useMedidas();
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const chip = spring({ frame: frame - 40, fps, config: SPRING.bouncy });
  const casa = t.cores.casa;
  const destino = urlVisivel(s.url);
  return (
    <Moldura index={index} marcaTexto={t.empresa} cor={casa} gradeOpacity={0.08} semLogo>
      <div style={{ display: "grid", gridTemplateColumns: "1.05fr 1fr", gap: 56 * u, alignItems: "center" }}>
        <div>
          {s.titulo ? (
            <WordReveal text={s.titulo} delay={8} per={3} withinWidth={inner * 0.5} fontSize={96 * u} accentColor={casa} style={{ lineHeight: 1.0, textTransform: "uppercase", fontWeight: 700 }} />
          ) : null}
          {s.texto ? (
            <Entrance delay={30} rise={22}>
              <p style={{ margin: `${26 * u}px 0 0`, fontFamily: t.fontes.body, fontSize: 32 * u, lineHeight: 1.35, color: t.cores.textSoft, maxWidth: inner * 0.46 }}>{s.texto}</p>
            </Entrance>
          ) : null}
          {destino ? (
            <div
              style={{
                display: "inline-block",
                marginTop: 36 * u,
                padding: `${20 * u}px ${34 * u}px`,
                borderRadius: 14 * u,
                background: casa,
                color: t.cores.sobreCasa,
                fontFamily: t.fontes.mono,
                fontSize: 30 * u,
                fontWeight: 500,
                letterSpacing: 1,
                opacity: chip,
                transform: `scale(${interpolate(chip, [0, 1], [0.7, 1], CLAMP)})`,
                boxShadow: `0 0 0 1px ${comAlfa(casa, 0.18)}, 0 0 32px ${comAlfa(casa, 0.28)}`,
              }}
            >
              {destino}
            </div>
          ) : null}
        </div>
        <Entrance delay={16} variant="left" config="smooth">
          <div style={{ height: altura * 0.62, borderRadius: 22 * u, overflow: "hidden", background: t.cores.bgSoft, border: `1px solid ${comAlfa(casa, 0.35)}`, boxShadow: "0 30px 80px rgba(0,0,0,0.5)", position: "relative", transform: "rotate(-1.5deg)" }}>
            {s.imagem ? (
              <KenBurns src={s.imagem} speed="slow" dir={-1} panPx={-12} />
            ) : (
              <div style={{ height: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 18 * u, textAlign: "center", padding: 40 * u }}>
                <span style={{ fontFamily: t.fontes.display, fontSize: 92 * u, lineHeight: 1, color: t.cores.text, letterSpacing: 1 }}>{t.empresa}</span>
                {destino ? <span style={{ fontFamily: t.fontes.mono, fontSize: 30 * u, color: t.cores.textSoft }}>{destino}</span> : null}
              </div>
            )}
          </div>
        </Entrance>
      </div>
    </Moldura>
  );
};

// Um tipo do deck -> uma cena 16:9. origem: youtube-squad/apresentacoes/motion/src/Root.tsx:20-30
export const CENAS: Record<TipoSlide, React.FC<CenaProps>> = {
  titulo: Titulo,
  declaracao: Declaracao,
  grade: Grade,
  comparacao: Comparacao,
  etapas: Etapas,
  estatisticas: Estatisticas,
  fluxo: Fluxo,
  screenshot: Screenshot,
  cta: Cta,
};
