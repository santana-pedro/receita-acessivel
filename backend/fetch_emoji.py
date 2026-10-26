"""Monta o banco de imagens (frontend/emoji/) a partir do catálogo (symbols.py).

Uso (em backend/): ../.venv/Scripts/python.exe fetch_emoji.py
Baixa as imagens que faltam (Health Icons ou Noto Emoji), remove as que não são mais
usadas e regrava catalog.json.
"""

import json
import sys
import urllib.request
from pathlib import Path

from symbols import HEALTH_ICONS, SYMBOLS, health_icon_path, image_name, noto_name, normalize

# Versões fixas, para o banco de imagens ser reprodutível.
NOTO_TAG = "v2026-09-24-unicode18_0"  # Noto Emoji, Apache 2.0
NOTO_URL = f"https://raw.githubusercontent.com/googlefonts/noto-emoji/{NOTO_TAG}"
HEALTH_ICONS_SHA = "4e0717e76ea26c8caee9cac70a42f6620c669c20"  # Health Icons, CC0
HEALTH_ICONS_URL = (
    f"https://raw.githubusercontent.com/resolvetosavelives/healthicons/{HEALTH_ICONS_SHA}"
    "/public/icons/svg/filled"
)

EMOJI_DIR = Path(__file__).resolve().parent.parent / "frontend" / "emoji"

NOTICE = f"""Banco de imagens do modo Analfabetismo.

- emoji_u*.svg: Noto Emoji ({NOTO_TAG}), https://github.com/googlefonts/noto-emoji
  Licença Apache 2.0 (ver LICENSE).
- hi_*.svg: Health Icons (commit {HEALTH_ICONS_SHA[:7]}), https://healthicons.org
  Domínio público (CC0), atribuição não exigida.

Gerado por backend/fetch_emoji.py a partir de backend/symbols.py.
"""


def download(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read()


def source_url(symbol: str) -> str:
    path = health_icon_path(symbol)
    if path:
        return f"{HEALTH_ICONS_URL}/{path}.svg"
    return f"{NOTO_URL}/2D/svg/{noto_name(symbol)}"


def main() -> int:
    catalog_symbols = {normalize(s) for s in SYMBOLS}
    orphans = [s for s in HEALTH_ICONS if normalize(s) not in catalog_symbols]
    if orphans:
        print("HEALTH_ICONS tem símbolos fora do catálogo:", *orphans)
        return 1

    EMOJI_DIR.mkdir(parents=True, exist_ok=True)
    failed = []
    for symbol in SYMBOLS:
        target = EMOJI_DIR / image_name(symbol)
        if target.exists():
            continue
        url = source_url(symbol)
        try:
            data = download(url)
        except Exception as exc:  # noqa: BLE001
            failed.append(f"{symbol} ({url}): {exc}")
            continue
        if not data.lstrip().startswith(b"<"):
            failed.append(f"{symbol} ({url}): resposta não é SVG")
            continue
        target.write_bytes(data)
        print(f"baixado {symbol} -> {target.name}")

    # Remove imagens que nenhum símbolo do catálogo usa mais.
    in_use = {image_name(s) for s in SYMBOLS}
    for svg in EMOJI_DIR.glob("*.svg"):
        if svg.name not in in_use:
            svg.unlink()
            print(f"removido {svg.name} (não usado)")

    license_file = EMOJI_DIR / "LICENSE"
    if not license_file.exists():
        license_file.write_bytes(download(f"{NOTO_URL}/LICENSE"))
    (EMOJI_DIR / "NOTICE.txt").write_text(NOTICE, encoding="utf-8")

    # Catálogo para o frontend: símbolo normalizado -> imagem e significado.
    catalog = {
        normalize(s): {"file": image_name(s), "alt": alt} for s, alt in SYMBOLS.items()
    }
    (EMOJI_DIR / "catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    if failed:
        print("Falharam:", *failed, sep="\n  ")
        return 1
    print(f"OK: {len(SYMBOLS)} símbolos ({len(HEALTH_ICONS)} do Health Icons) em {EMOJI_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
