import { useEffect } from "react";
import { useLocation } from "react-router-dom";

export function MetadatosRuta() {
  const { pathname } = useLocation();

  useEffect(() => {
    const title = pathname.startsWith("/admin")
      ? "Administración"
      : pathname.startsWith("/unidad-productiva")
        ? "Unidad Productiva"
        : pathname === "/solicitud-registro"
          ? "Solicitud de registro"
          : "Ferias y eventos activos";
    document.title = `${title} | Ferias Productivas Bolivia`;
  }, [pathname]);

  return null;
}
