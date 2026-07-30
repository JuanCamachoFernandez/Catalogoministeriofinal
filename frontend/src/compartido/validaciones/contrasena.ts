export function esContrasenaSegura(value: string) {
  return (
    value.length >= 10 &&
    /[A-Z]/.test(value) &&
    /[a-z]/.test(value) &&
    /[0-9]/.test(value) &&
    /[\W_]/.test(value)
  );
}
