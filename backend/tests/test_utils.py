import pytest
from app.utils import normalize_whatsapp,valid_gmail
def test_normaliza_whatsapp():assert normalize_whatsapp("71234567")=="59171234567"
def test_rechaza_numero_invalido():
    with pytest.raises(ValueError):normalize_whatsapp("123")
def test_gmail():assert valid_gmail("persona@gmail.com") and not valid_gmail("persona@otro.com")
