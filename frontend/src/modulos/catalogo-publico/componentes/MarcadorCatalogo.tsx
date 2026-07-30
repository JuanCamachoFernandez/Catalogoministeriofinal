import { Factory, PackageSearch } from "lucide-react";

export function MarcadorCatalogo({
  kind,
  name,
  large = false,
}: {
  kind: "unit" | "product";
  name: string;
  large?: boolean;
}) {
  const initials =
    name
      .trim()
      .split(/\s+/)
      .slice(0, 2)
      .map((word) => word[0])
      .join("")
      .toUpperCase() || (kind === "unit" ? "UP" : "PB");

  return (
    <div
      className={`${large ? "detail-image " : "card-media "}catalog-media-placeholder ${kind === "unit" ? "unit-placeholder" : "product-placeholder"}`}
      aria-label={`${name}, imagen no disponible`}
    >
      <span className="placeholder-orbit" aria-hidden="true" />
      <span className="placeholder-mark" aria-hidden="true">
        {kind === "unit" ? <Factory /> : <PackageSearch />}
      </span>
      <strong>{initials}</strong>
      <small>
        {kind === "unit" ? "Unidad Productiva" : "Producto boliviano"}
      </small>
    </div>
  );
}
