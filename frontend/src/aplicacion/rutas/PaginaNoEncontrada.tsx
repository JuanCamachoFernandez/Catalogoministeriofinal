import { Link } from "react-router-dom";
import { EncabezadoPublico } from "../../modulos/catalogo-publico/componentes/EncabezadoPublico";
import { EstadoVacio } from "../../compartido/componentes";
export function PaginaNoEncontrada() {
  return (
    <>
      <EncabezadoPublico />
      <main className="container public-main">
        <EstadoVacio title="Página no encontrada" />
        <Link className="btn" to="/catalogo">
          Ir al catálogo
        </Link>
      </main>
    </>
  );
}



