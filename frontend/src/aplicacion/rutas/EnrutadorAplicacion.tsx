import { Suspense } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { EstadoCarga } from "../../compartido/componentes";
import { rutasAdministracion } from "./RutasAdministracion";
import { rutasAutenticacion } from "./RutasAutenticacion";
import { rutasRedireccionAnteriores } from "./RutasRedireccionAnteriores";
import { PaginaNoEncontrada } from "./PaginaNoEncontrada";
import { rutasUnidadProductiva } from "./RutasUnidadProductiva";
import { rutasPublicas } from "./RutasPublicas";
import { MetadatosRuta } from "./MetadatosRuta";

export default function EnrutadorAplicacion() {
  return (
    <>
      <MetadatosRuta />
      <Suspense fallback={<EstadoCarga label="Cargando página…" />}>
        <Routes>
          <Route path="/" element={<Navigate to="/catalogo" replace />} />
          {rutasPublicas}
          {rutasAutenticacion}
          {rutasAdministracion}
          {rutasUnidadProductiva}
          {rutasRedireccionAnteriores}
          <Route path="*" element={<PaginaNoEncontrada />} />
        </Routes>
      </Suspense>
    </>
  );
}
