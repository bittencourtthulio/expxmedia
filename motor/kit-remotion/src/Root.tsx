import React from "react";
import { Composition } from "remotion";
// Gerado por scripts/registrar.mjs a partir das pastas de src/composicoes/ (D-46).
// Nenhuma task edita este arquivo: uma composição nova é só uma pasta nova.
import { COMPOSICOES } from "./composicoes/registro.generated";

export const RemotionRoot: React.FC = () => (
  <>
    {COMPOSICOES.map((c) => (
      <Composition
        key={c.id}
        id={c.id}
        component={c.component}
        fps={c.fps}
        width={c.width}
        height={c.height}
        durationInFrames={c.durationInFrames}
        defaultProps={c.defaultProps}
        calculateMetadata={c.calculateMetadata}
      />
    ))}
  </>
);
