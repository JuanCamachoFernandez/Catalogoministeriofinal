export const displayDate = (value: string) =>
  new Intl.DateTimeFormat("es-BO", { dateStyle: "long" }).format(
    new Date(`${value}T12:00:00`),
  );
