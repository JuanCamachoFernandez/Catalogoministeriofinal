import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { ProveedoresAplicacion } from "./aplicacion/proveedores/ProveedoresAplicacion";
import "./compartido/estilos/tema.css";
import "./compartido/estilos/estilos-base.css";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ProveedoresAplicacion>
      <App />
    </ProveedoresAplicacion>
  </React.StrictMode>,
);
