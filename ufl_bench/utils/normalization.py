"""Uzbek Orthography & Linguistic Normalization Utility for ufl_bench.

Strictly adheres to:
- U+02BB (`ʻ`) for oʻ, gʻ
- U+02BB / U+02BC (`ʼ`) for tutuq belgisi
- Dual-script support: Latin (`uz-Latn`) and Cyrillic (`uz-Cyrl`)
- Polite `Siz` register
- System prompts
"""

import re
from typing import Tuple, Dict, Any, List, Optional

SYSTEM_PROMPT_UZ_LATN = "Siz foydalanuvchiga yordam beruvchi xavfsiz va aniq sunʼiy intellekt assistentisiz."
SYSTEM_PROMPT_UZ_CYRL = "Сиз фойдаланувчига ёрдам берувчи хавфсиз ва аниқ сунъий интеллект ассистентисиз."

# Verified SFT Production System Prompt (SYSTEM_BASE) recovered directly from SFT generation pipeline
SFT_PRODUCTION_SYSTEM_PROMPT = """Siz yuqori sifatli oʻzbekcha korporativ agent epizodlarini yozasiz. Epizod
ichidagi assistant — oʻzbek tilida ishlovchi umumiy va korporativ sunʼiy intellekt assistenti; uning
javoblari shu agentning tabiiy ovozida boʻlsin, epizod muallifining ovozida emas.
Faqat tabiiy, kanonik Uzbek Latin yozuvidan foydalaning; kirill yozmang.
Kod, buyruq, formula, UI nomi, mahsulot nomi, fayl nomi va API atamasi tabiiy boʻlsa inglizcha qolishi mumkin.
Har bir obyekt bitta toʻliq, real va oʻzaro mantiqan izchil trajectory boʻlsin.
Faqat berilgan tool katalogidan foydalaning. Tool natijasini koʻrmasdan muvaffaqiyat boʻldi demang.
Natija xato boʻlsa, xatoni yashirmang: xavfsiz tekshiring, tuzatilgan argument bilan urinib koʻring yoki aniq terminal holatda toʻxtang.
Xatodan keyin ayni toolni ayni argumentlar bilan koʻr-koʻrona takrorlamang va argument oʻzgarmagan boʻlsa uni toraytirildi deb aytmang.
Oʻchirish, ustiga yozish, yuborish, ruxsat/startup/service oʻzgartirish yoki moliyaviy majburiyat oldidan assistant_message orqali aniq tasdiq soʻrang. Assistant soʻrovi, keyingi user tasdigʻi va tool call bir xil confirmation_for hamda aynan bir xil confirmation_arguments obyektini ishlatsin. Foydalanuvchi rad etsa, confirmation metadata yozmang va amalni bajarmang.
Oddiy javob yetarli boʻlsa tool chaqirmang. Tool natijalari host qaytargan realistik JSON obyektlar sifatida yozilsin.
Assistant yakunidagi har bir raqam user soʻrovi yoki tool natijasida mavjud yoxud tool natijasidagi aniq ustun/list yigʻindisi yoki oʻrtachasi boʻlsin.
Katalogdagi overwrite parametri bor tool chaqirigʻida overwrite ni har doim aniq yozing; mavjud faylga ustiga yozish uchun tasdiq shart.
MAJBURIY YAKUN: har bir epizodning OXIRGI eventi assistant_final boʻlsin (yoki state=needs_user_input/needs_confirmation boʻlgan assistant_message). Epizodni HECH QACHON tool_result yoki assistant_tool_call bilan tugatmang.
HAQIQIY FOYDALANUVCHI USLUBI: user birinchi turni iloji boricha QISQA, ODDIY va KONKRET qilib yozing. Real foydalanuvchi odatda oʻzining ismi, kompaniyasi, lavozimi va boʻlimini koʻrsatmaydi:
  - "Kompyuter qotyapti."
  - "Hisobotni ber."
  - "Oʻtgan oynikini koʻrsat."
  - "Excelni tuzat."
  - "Yangiliklar nima?"
  - "Oxirgi faylni och."
  - "Serverga kira olmayapman."
  - "Shuni mijozga yubor."
  - "Buni oʻchir."
  - "Yoʻq, oʻchirma."
  - "Avval tekshir."
  - "Keyin yubor."
QUYIDAGILAR MUTLAQO TAQIQLANGAN user turnida:
  - "Hurmatli yordamchi" / "Hurmatli <ism>" murojaati;
  - "Men <ism> <kompaniya/tashkilot/boʻlim>da ishlayman" identifikatsiya;
  - "Assalomu alaykum, men ... analitik/buxgalter/meneger ...";
  - "Salom Nodir/Sardor/Lochin/Aziz" — agentning ismi yoʻq va u odam emas;"""

USER_ASYMMETRIC_STYLE_GUIDE = {
    "user_register": "Fast, direct phrasing, informal imperative (e.g., -b ber, -b yubor, -chi, tuzat, och, o'chir, ko'rsat, solishtir), Telegram message style without bureaucratic fluff.",
    "assistant_register": "Respectful, safe, honorific Siz register with accurate tool execution and mandatory confirmation before mutations.",
}

REAL_USER_STYLE_EXAMPLES = [
    "shu narsani oddiy qilib tushuntirib ber",
    "buni qisqaroq ayt",
    "yana sodda qilib aytchi",
    "shu kodni tekshir",
    "nega ishlamayapti",
    "buni tezroq usuli bormi",
    "shu hisobotni qisqartirib ber",
    "asosiy raqamlarni qoldir",
    "ortiqcha gaplarni olib tashla",
    "Kompyuter qotyapti.",
    "Hisobotni ber.",
    "Oʻtgan oynikini koʻrsat.",
    "Excelni tuzat.",
    "Yangiliklar nima?",
    "Oxirgi faylni och.",
    "Serverga kira olmayapman.",
    "Shuni mijozga yubor.",
    "Buni oʻchir.",
    "Yoʻq, oʻchirma.",
    "Avval tekshir.",
    "Keyin yubor.",
]

FORBIDDEN_USER_PATTERNS = [
    r"hurmatli\s+(yordamchi|assistent|sun['ʼʻ]iy)",
    r"hurmatli\s+[A-ZА-Я][a-zа-я]+",
    r"men\s+[a-zа-я\s]+(da|kompaniyasi|tashkiloti|bo['ʼʻ]limida)\s+ishlayman",
    r"assalomu\s+alaykum,\s+men\s+.*(analitik|buxgalter|menedjer|menejer)",
    r"salom\s+(nodir|sardor|lochin|aziz)\b",
]


def validate_user_prompt_style(prompt: str) -> List[str]:
    """Validate that a user prompt adheres to the real asymmetric user style rules.

    Flags prohibited bureaucratic greetings or artificial identity declarations.
    """
    violations = []
    if not prompt:
        return violations
    prompt_clean = prompt.strip().lower()
    for pat in FORBIDDEN_USER_PATTERNS:
        if re.search(pat, prompt_clean, re.IGNORECASE):
            violations.append(f"User prompt violates asymmetric style rule matching forbidden pattern: '{pat}'")
    return violations


def normalize_uzbek_orthography(text: str) -> str:
    """Normalize Uzbek orthography for natural-language text fields ONLY.

    Strict rules:
    - oʻ and gʻ use modifier letter turned comma: U+02BB (`ʻ`)
    - tutuq belgisi uses modifier letter apostrophe: U+02BC (`ʼ`)
    - Code snippets, syntax, URLs, file paths, and AST expressions are strictly preserved.
    """
    if not text or not isinstance(text, str):
        return text or ""

    # Protect code blocks and inline code
    code_placeholders = []
    def _save_code(match):
        code_placeholders.append(match.group(0))
        return f"__CODE_SNIPPET_{len(code_placeholders)-1}__"

    # Protect fenced code blocks and inline backtick code
    text = re.sub(r"```[\s\S]*?```", _save_code, text)
    text = re.sub(r"`[^`\n]+`", _save_code, text)

    # Protect URLs and Windows/Unix file paths
    text = re.sub(r"https?://[^\s\"'<>)\]}]+", _save_code, text)
    text = re.sub(r"(?:[A-Za-z]:\\[^\s\"'<>)\]]+|/(?:usr|home|var|etc|opt|workspace|tmp)[^\s\"'<>)\]]+)", _save_code, text)

    # 1. Normalize oʻ / Oʻ (U+02BB)
    text = re.sub(r"([oO])[`'‘’´](?![A-Z])", "\\1\u02bb", text)

    # 2. Normalize gʻ / Gʻ (U+02BB)
    text = re.sub(r"([gG])[`'‘’´](?![A-Z])", "\\1\u02bb", text)

    # 3. Normalize tutuq belgisi between letters (U+02BC) (e.g. ma'lumot -> maʼlumot, ta'lim -> taʼlim)
    text = re.sub(r"([a-zA-Zа-яА-Я])[`'‘’´]([a-zA-Zа-яА-Я])", "\\1\u02bc\\2", text)

    # 4. Normalize word-ending tutuq belgisi (U+02BC) (e.g., sur'at, she'r, da'vo, san'at)
    text = re.sub(r"([a-zA-Zа-яА-Я])[`'‘’´](?!\w)", "\\1\u02bc", text)

    # Restore protected code snippets, paths, and URLs
    for idx, snippet in enumerate(code_placeholders):
        text = text.replace(f"__CODE_SNIPPET_{idx}__", snippet)

    return text


def detect_script(text: str) -> Tuple[str, str]:
    """Detect whether text is predominantly Latin (Latn) or Cyrillic (Cyrl).

    Returns:
        Tuple of (script_name, bcp47_code), e.g. ("Latn", "uz-Latn") or ("Cyrl", "uz-Cyrl").
    """
    if not text:
        return "Latn", "uz-Latn"
    latn_count = len(re.findall(r"[a-zA-Z]", text))
    cyrl_count = len(re.findall(r"[\u0400-\u04FF]", text))
    if cyrl_count > latn_count:
        return "Cyrl", "uz-Cyrl"
    return "Latn", "uz-Latn"


def is_cyrillic(text: str) -> bool:
    """Return True if text is detected as Cyrillic script."""
    script, _ = detect_script(text)
    return script == "Cyrl"


def validate_orthography(text: str) -> List[str]:
    """Audit text for prohibited orthographic patterns."""
    issues = []
    if not text:
        return issues

    bad_o = re.findall(r"[oO]['’‘`´]", text)
    if bad_o:
        issues.append(f"Found {len(bad_o)} unnormalized o' variants")

    bad_g = re.findall(r"[gG]['’‘`´]", text)
    if bad_g:
        issues.append(f"Found {len(bad_g)} unnormalized g' variants")

    return issues


def quasi_normalize_text(text: str) -> str:
    """Quasi-exact text normalizer for GAIA and NLP evaluation.

    - Strips leading/trailing punctuation and whitespace
    - Normalizes Uzbek orthography
    - Lowercases
    - Normalizes internal whitespace
    - Strips peripheral articles/brackets
    """
    if text is None:
        return ""
    text = str(text).strip()
    text = normalize_uzbek_orthography(text)
    text = text.lower()

    # Replace multiple whitespaces/newlines with single space
    text = re.sub(r"\s+", " ", text)

    # Strip surrounding quotation marks or brackets
    text = re.sub(r"^[\"\'`«»„“”\(\)\[\]\{\}]+|[\"\'`«»„“”\(\)\[\]\{\}]+$", "", text)

    # Remove trailing periods, colons, or commas often appended to sentences
    text = re.sub(r"[\.\,\;\:\!\?]+$", "", text)

    return text.strip()
