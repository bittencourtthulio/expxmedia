import React from "react";
import { AbsoluteFill } from "remotion";
import {
  Aula,
  Etiqueta,
  FPS,
  ITEM_INICIO_S,
  ITEM_PASSO_S,
  Janela,
  Pop,
  Rise,
  composicaoAula,
  pilhaFonte,
  useAlma,
  type DesenharCena,
  type PropsAula,
} from "@expxmedia/template";

// Template "padrão" de aula: a estrutura das aulas gravadas da origem — abertura com etiqueta, título grande e a
// pergunta numa janela com barra de título; passos na tela com o cartão do passo; resumo com itens marcados —,
// genérica. Os layouts calibrados (16:9 e 9:16, faixas seguras, janela do avatar 272x340 com topo em 1318 no
// 9:16), a tela gravada, o avatar e a legenda são da composição Aula do kit; aqui só o desenho das cenas.
// Tudo que é marca chega por props: cores e fontes pela Alma (useAlma), o nome do porta-voz na janela do avatar.
// origem: cursos-ia/radar-ia-09-jev-calibracao/src/marca.tsx:114-141 (Abertura e Fecho) e src/Aula.tsx:212-253

const quadro = (s: number) => Math.round(s * FPS);

// Abertura/fecho: etiqueta, título grande apertado e o texto de apoio dentro de uma janela que "abre" com um pop
// 1,5 s depois (perguntaAt = 45 quadros). origem: cursos-ia/radar-ia-09-jev-calibracao/src/marca.tsx:115
const CenaJanela: DesenharCena = ({ cena, l }) => {
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
          // origem: cursos-ia/radar-ia-09-jev-calibracao/src/marca.tsx:61-63 (0.92 de entrelinha, -0.055em)
          <div style={{ fontFamily: pilhaFonte(fontes.titulo), fontWeight: 700, fontSize: l.vertical ? 104 : 118, lineHeight: 0.92,
            letterSpacing: "-0.055em", color: cores.texto }}>
            {cena.titulo}
          </div>
        ) : null}
      </Rise>
      {cena.texto ? (
        <Pop at={45} style={{ marginTop: 44, alignSelf: "flex-start" }}>
          <Janela titulo={cena.passo ?? cena.rotulo ?? ""}>
            <div style={{ fontFamily: pilhaFonte(fontes.texto), fontSize: 30, lineHeight: 1.45 }}>{cena.texto}</div>
          </Janela>
        </Pop>
      ) : null}
      {cena.itens.length ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 14, alignItems: "flex-start", marginTop: 36 }}>
          {cena.itens.map((item, i) => (
            <Pop key={i} at={quadro(ITEM_INICIO_S + i * ITEM_PASSO_S)}>
              <Etiqueta tamanho={44}>✢ {item}</Etiqueta>
            </Pop>
          ))}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

const AulaPadrao: React.FC<PropsAula> = (props) => <Aula {...props} desenhar={CenaJanela} />;

export const composicao = { ...composicaoAula, component: AulaPadrao };
