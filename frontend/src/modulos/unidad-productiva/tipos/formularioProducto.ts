export type BorradorProducto = {
  nombre_comercial: string;
  descripcion_tecnica: string;
  materia_prima: string;
  dimensiones: string;
  colores_disponibles: string;
  certificaciones: string;
  presentacion_empaque: string;
  precio_referencia: string;
  capacidad_produccion_stock: string;
};
export type ErroresBorradorProducto = Partial<Record<keyof BorradorProducto, string>>;


