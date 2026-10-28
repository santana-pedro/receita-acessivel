"""Catálogo de símbolos do modo analfabetismo: a fonte única do padrão visual.

A IA escreve os emojis; cada um é exibido com uma imagem de frontend/emoji/ (o banco de
imagens). A imagem vem do Health Icons quando o símbolo está em HEALTH_ICONS (ícones que
mostram pessoas/objetos reais) e do Noto Emoji nos demais casos.
Para adicionar ou trocar um símbolo: edite aqui e rode `python fetch_emoji.py` (em backend/),
que baixa as imagens, remove as que não são mais usadas e atualiza frontend/emoji/catalog.json.
Revise visualmente cada imagem nova antes de adotá-la.
O prompt só permite à IA usar símbolos deste catálogo.
"""

import re

# símbolo -> significado (usado como texto alternativo da imagem)
SYMBOLS: dict[str, str] = {
    # Cor de cada remédio (para associar o cartão à caixa)
    "🔴": "vermelho",
    "🔵": "azul",
    "🟢": "verde",
    "🟡": "amarelo",
    "🟣": "roxo",
    "🟠": "laranja",
    "🟤": "marrom",
    "⚫": "preto",
    # Forma do remédio
    "💊": "comprimido",
    "🥄": "colher (xarope/líquido)",
    "💧": "gotas",
    "👃": "nariz (spray nasal)",
    "💨": "borrifada",
    "💉": "injeção",
    "🧴": "pomada ou creme",
    "👁️": "olho (colírio)",
    "🫁": "bombinha de asma",
    # Para que serve
    "🎯": "para que serve",
    "🤕": "dor",
    "🤒": "febre",
    "🤧": "alergia ou rinite",
    "😷": "tosse",
    "😮‍💨": "falta de ar",
    "🦠": "infecção",
    "❤️": "pressão ou coração",
    "🍬": "diabetes",
    "🤢": "enjoo",
    "😴": "sono",
    # Quando tomar
    "☀️": "manhã",
    "🌤️": "tarde",
    "🌙": "noite",
    "⏰": "horário",
    "⏳": "intervalo em horas",
    "🗓️": "dias de tratamento",
    "🔁": "repetir",
    "♾️": "sempre (uso contínuo)",
    # Se precisar
    "🆘": "se precisar",
    "➡️": "e depois",
    "✋": "esperar",
    "➕": "no máximo",
    # Como tomar e avisos
    "🍽️": "refeição",
    "🚰": "com água",
    "🚫": "proibido",
    "🍺": "bebida alcoólica",
    "🚗": "dirigir",
}

# Símbolos desenhados com o Health Icons (caminho em public/icons/svg/filled/ do repositório).
HEALTH_ICONS: dict[str, str] = {
    "🫁": "devices/asthma-inhaler",
    "🤕": "conditions/headache",
    "🤒": "conditions/chills-fever",
    "😷": "conditions/coughing-alt",
    "❤️": "symbols/heart-cardiogram",
    "🍬": "devices/diabetes-measure",
    "🤢": "conditions/nausea",
    "🍺": "nutrition/alcohol",
}

_VS16 = chr(0xFE0F)  # seletor de variação (emoji), opcional no texto da IA


def normalize(symbol: str) -> str:
    return symbol.replace(_VS16, "")


def image_name(symbol: str) -> str:
    """Arquivo no banco: Health Icons ('hi_headache.svg') ou Noto ('emoji_u2764.svg')."""
    path = health_icon_path(symbol)
    if path:
        return "hi_" + path.rsplit("/", 1)[-1] + ".svg"
    return noto_name(symbol)


def health_icon_path(symbol: str) -> str | None:
    wanted = normalize(symbol)
    return next((p for s, p in HEALTH_ICONS.items() if normalize(s) == wanted), None)


def noto_name(symbol: str) -> str:
    """Nome do arquivo no padrão Noto: '❤️' -> 'emoji_u2764.svg'."""
    return "emoji_u" + "_".join(f"{ord(c):x}" for c in normalize(symbol)) + ".svg"


# Maiores primeiro, para sequências de vários caracteres terem prioridade.
_PATTERN = re.compile(
    "|".join(re.escape(normalize(s)) for s in sorted(SYMBOLS, key=len, reverse=True))
)
_BY_NORMALIZED = {normalize(s): s for s in SYMBOLS}


def tokenize(text: str) -> list[tuple[str, str | None]]:
    """Divide em pedaços (texto, símbolo do catálogo ou None para texto comum)."""
    text = normalize(text)
    parts, pos = [], 0
    for match in _PATTERN.finditer(text):
        if match.start() > pos:
            parts.append((text[pos : match.start()], None))
        parts.append((match.group(), _BY_NORMALIZED[match.group()]))
        pos = match.end()
    if pos < len(text):
        parts.append((text[pos:], None))
    return parts
