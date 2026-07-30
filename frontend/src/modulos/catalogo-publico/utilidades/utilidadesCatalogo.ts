export function construirItemsWhatsapp(quantities: Record<string, number>) {
  return Object.entries(quantities)
    .filter(([, quantity]) => Number.isInteger(quantity) && quantity > 0)
    .map(([product_id, quantity]) => ({ product_id, quantity }));
}

export function formatearFechaBoliviana(value: string) {
  return new Intl.DateTimeFormat("es-BO", { dateStyle: "long", timeZone: "America/La_Paz" }).format(new Date(`${value}T12:00:00`));
}

export function formatearBolivianos(value: number | null) {
  return value === null ? "Consultar precio" : new Intl.NumberFormat("es-BO", { style: "currency", currency: "BOB" }).format(value);
}
