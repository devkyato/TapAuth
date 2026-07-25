import re


UID_SEPARATORS = re.compile(r"[\s:._-]+")


def canonicalize_nfc_uid(value):
    """Return one stable representation for text or raw-byte NFC UIDs."""
    if value is None:
        return ""
    if isinstance(value, (bytes, bytearray)):
        raw = bytes(value)
        if not raw:
            return ""
        try:
            text = raw.decode("ascii")
        except UnicodeDecodeError:
            return raw.hex().upper()
        if any(ord(character) < 32 and not character.isspace() for character in text):
            return raw.hex().upper()
    else:
        text = str(value)

    text = text.strip().upper()
    compact = UID_SEPARATORS.sub("", text)
    if compact.startswith("0X"):
        compact = compact[2:]
    if compact and re.fullmatch(r"[0-9A-F]+", compact):
        return compact
    return text
