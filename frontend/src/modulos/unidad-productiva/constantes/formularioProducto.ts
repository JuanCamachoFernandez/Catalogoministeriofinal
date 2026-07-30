import type { BorradorProducto } from "../tipos/formularioProducto";

export const productoVacio: BorradorProducto = {
  nombre_comercial: "",
  descripcion_tecnica: "",
  materia_prima: "",
  dimensiones: "",
  colores_disponibles: "",
  certificaciones: "",
  presentacion_empaque: "",
  precio_referencia: "",
  capacidad_produccion_stock: "",
};

export const camposProducto: Array<{
  key: Exclude<keyof BorradorProducto, "descripcion_tecnica">;
  label: string;
  hint: string;
  placeholder: string;
  required?: boolean;
  type?: "text" | "number";
  inputMode?: "text" | "numeric" | "decimal";
  min?: string;
  step?: string;
  maxLength?: number;
}> = [
  {
    key: "nombre_comercial",
    label: "Nombre comercial",
    hint: "Ingrese el nombre con el que ofrece este producto.",
    placeholder: "Ej.: Miel Andina 500",
    required: true,
    maxLength: 200,
  },
  {
    key: "materia_prima",
    label: "Materia prima",
    hint: "Indique el material o ingrediente principal del producto.",
    placeholder: "Ej.: Algodón 100",
    required: true,
    maxLength: 2000,
  },
  {
    key: "presentacion_empaque",
    label: "Presentación o empaque",
    hint: "Explique cómo se entrega o empaca el producto.",
    placeholder: "Ej.: Caja 12 unidades",
    required: true,
    maxLength: 255,
  },
  {
    key: "precio_referencia",
    label: "Precio",
    hint: "Ingrese el precio de venta del producto en bolivianos.",
    placeholder: "Ej.: 55.00",
    required: true,
    type: "number",
    inputMode: "decimal",
    min: "0",
    step: "0.01",
  },
  {
    key: "capacidad_produccion_stock",
    label: "Capacidad o stock",
    hint: "Indique la cantidad disponible o capacidad de producción en unidades.",
    placeholder: "Ej.: 100",
    required: true,
    type: "number",
    inputMode: "numeric",
    min: "0",
    step: "1",
  },
  {
    key: "dimensiones",
    label: "Tallas o dimensiones",
    hint: "Ingrese la talla si es una prenda o las medidas si es otro producto.",
    placeholder: "Ej.: Talla M o 20 x 15 cm",
    maxLength: 255,
  },
  {
    key: "colores_disponibles",
    label: "Colores disponibles",
    hint: "Escriba los colores en los que ofrece el producto.",
    placeholder: "Ej.: Rojo azul",
    maxLength: 255,
  },
  {
    key: "certificaciones",
    label: "Certificaciones",
    hint: "Registre las certificaciones o registros que tenga el producto.",
    placeholder: "Ej.: SENASAG N.º 123/2026",
    maxLength: 2000,
  },
];


