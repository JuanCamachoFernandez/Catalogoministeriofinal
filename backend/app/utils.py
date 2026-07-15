import re, secrets, unicodedata

def slugify(value):
    value=unicodedata.normalize("NFKD",value).encode("ascii","ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+","-",value).strip("-")
def normalize_whatsapp(value):
    digits=re.sub(r"\D","",value or "")
    if len(digits)==8: digits="591"+digits
    if len(digits)!=11 or not digits.startswith("591") or digits[3] not in "67": raise ValueError("Número de WhatsApp boliviano inválido")
    return digits
def valid_gmail(value): return bool(re.fullmatch(r"[A-Za-z0-9._%+-]+@gmail\.com",value or "",re.I))
def temporary_password(): return secrets.token_urlsafe(12)+"aA1!"

