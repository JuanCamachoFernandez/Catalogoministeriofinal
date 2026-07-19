const GMAIL_SUFFIX = "@gmail.com";

export function gmailLocalPart(email: string) {
  const normalized = email.trim();
  return normalized.toLowerCase().endsWith(GMAIL_SUFFIX)
    ? normalized.slice(0, -GMAIL_SUFFIX.length)
    : normalized.split("@")[0];
}

export function gmailAddress(localPart: string) {
  return `${localPart.trim().replace(/@.*$/, "")}@gmail.com`;
}

export function responsibleDisplayName(...parts: string[]) {
  return parts
    .map((value) => value.trim())
    .filter(Boolean)
    .join(" ");
}
