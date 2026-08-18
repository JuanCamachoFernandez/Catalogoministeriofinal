import type { BorradorProducto, ErroresBorradorProducto } from "../tipos/formularioProducto";

const alphanumericProductText = /^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9 ]+$/;
const packagingProductText = /^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ0-9 ,/\-]+$/;
const lettersOnlyProductText = /^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ ]+$/;

export function validarBorradorProducto(draft: BorradorProducto): ErroresBorradorProducto {
  const errors: ErroresBorradorProducto = {};
  const required: Array<keyof BorradorProducto> = [
    "nombre_comercial",
    "materia_prima",
    "presentacion_empaque",
    "precio_referencia",
    "capacidad_produccion_stock",
    "descripcion_tecnica",
  ];
  required.forEach((key) => {
    if (!draft[key].trim()) errors[key] = "Este campo es obligatorio.";
  });
  (
    ["nombre_comercial", "materia_prima"] as const
  ).forEach((key) => {
    const value = draft[key].trim();
    if (value && !alphanumericProductText.test(value))
      errors[key] = "Use solamente letras, números y espacios.";
  });
  if (
    draft.presentacion_empaque.trim() &&
    !packagingProductText.test(draft.presentacion_empaque.trim())
  )
    errors.presentacion_empaque =
      "Use letras, números, espacios y también /, coma o guion.";
  if (
    draft.precio_referencia &&
    !/^\d+(\.\d{1,2})?$/.test(draft.precio_referencia)
  )
    errors.precio_referencia =
      "Ingrese un número válido con hasta dos decimales.";
  if (
    draft.capacidad_produccion_stock &&
    !/^\d+$/.test(draft.capacidad_produccion_stock)
  )
    errors.capacidad_produccion_stock = "Ingrese únicamente un número entero.";
  if (
    draft.colores_disponibles.trim() &&
    !lettersOnlyProductText.test(draft.colores_disponibles.trim())
  )
    errors.colores_disponibles =
      "Los colores solo pueden contener letras y espacios.";
  return errors;
}

