"""Strict Pokémon listing title parser & variant disambiguator.

Extracts grader, grade, CGC sub-tier, card number, edition, finish, language,
qualifiers, and red flags (lots, proxies, wrong-language, damaged) so junk
listings are filtered before comp matching or ROI scoring.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import re
from typing import Any

# Ordered most-specific first
_CGC_PRISTINE_RE = re.compile(r"\bPRISTINE\s*10\b|\bCGC\s*10\s+PRISTINE\b", re.IGNORECASE)
_CGC_GEM_RE = re.compile(r"\bGEM\s*MINT\s*10\b|\bCGC\s*10\s+GEM\s*MINT\b", re.IGNORECASE)
_CGC_BLUE_RE = re.compile(r"\b(?:OLD\s*)?BLUE\s*LABEL\b", re.IGNORECASE)
_GRADER_GRADE_RE = re.compile(
    r"\b(PSA|CGC|BGS|BECKETT|SGC)\s*[-#:]?\s*(10|9\.5|9|8\.5|8|7\.5|7|6|5|4|3|2|1)\b",
    re.IGNORECASE,
)
_CARD_NUM_SLASH_RE = re.compile(r"(?:#|\bNo\.?\s*)?(\d{1,3})\s*/\s*(\d{1,3})\b", re.IGNORECASE)
_CARD_NUM_PROMO_RE = re.compile(r"\b(SWSH\d{2,3}|SM\d{2,3}|XY\d{2,3}|BW\d{2,3}|SVP\d{2,3})\b", re.IGNORECASE)
_CARD_NUM_HASH_RE = re.compile(r"#\s*(\d{1,3})\b")
_YEAR_RE = re.compile(r"\b(199[5-9]|20[0-2]\d)\b")
_QUALIFIER_RE = re.compile(r"\b(OC|MC|MK|ST|PD|OF)\b")

_RED_FLAGS = {
    "lot_or_bundle": re.compile(r"\b(lot|bundle|collection|pick\s*your|you\s*pick|choose\s*card|mystery\s*pack)\b", re.IGNORECASE),
    "proxy_or_fake": re.compile(r"\b(proxy|orica|custom|replica|fan\s*art|metal\s*card|gold\s*foil\s*custom|reprint)\b", re.IGNORECASE),
    "empty_or_case": re.compile(r"\b(empty|box\s*only|case\s*only|slab\s*case|stand\s*only|display\s*only|digital|ptcgo|ptcgl)\b", re.IGNORECASE),
    "damaged": re.compile(r"\b(damaged|creased|bent|heavy\s*play|hp|poor|cracked\s*slab)\b", re.IGNORECASE),
}

_LANGUAGES = (
    ("Japanese", re.compile(r"\b(japanese|jpn|jp)\b", re.IGNORECASE)),
    ("Korean", re.compile(r"\b(korean|kor)\b", re.IGNORECASE)),
    ("Chinese", re.compile(r"\b(chinese|chs|cht)\b", re.IGNORECASE)),
    ("German", re.compile(r"\b(german|deutsch)\b", re.IGNORECASE)),
    ("French", re.compile(r"\b(french|francais|français)\b", re.IGNORECASE)),
    ("Spanish", re.compile(r"\b(spanish|espanol|español)\b", re.IGNORECASE)),
    ("Italian", re.compile(r"\b(italian|italiano)\b", re.IGNORECASE)),
    ("Dutch", re.compile(r"\b(dutch|nederlands)\b", re.IGNORECASE)),
    ("Portuguese", re.compile(r"\b(portuguese|portugu[eê]s)\b", re.IGNORECASE)),
    ("Indonesian", re.compile(r"\b(indonesian|bahasa indonesia)\b", re.IGNORECASE)),
    ("Thai", re.compile(r"\bthai\b", re.IGNORECASE)),
    ("Russian", re.compile(r"\b(russian|русский)\b", re.IGNORECASE)),
)


CARD_NAME_TYPOS = {
    'Charizard': 'Charzard',
    'Blastoise': 'Blastiose',
    'Gyarados': 'Gyrados',
    'Pikachu': 'Pickachu',
}


def repair_known_card_typos(title: str) -> str:
    for card, alias in CARD_NAME_TYPOS.items():
        title = re.sub(r'\b' + re.escape(alias) + r'\b', card, title, flags=re.IGNORECASE)
    return title


@dataclass(frozen=True)
class ParsedListing:
    raw_title: str
    grader: str | None
    grade: str | None
    cgc_sub_tier: str | None
    card_number: str | None
    set_size: str | None
    year: str | None
    edition: str
    finish: str
    language: str
    qualifiers: tuple[str, ...]
    red_flags: tuple[str, ...]
    confidence: float
    disqualified: bool
    normalized_tokens: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_title(title: str, *, expected_language: str | None = None) -> ParsedListing:
    """Parse an eBay / marketplace Pokémon card title into structured attributes."""
    raw = " ".join(str(title or "").split())
    lower = raw.lower()

    grader: str | None = None
    grade: str | None = None
    cgc_sub_tier: str | None = None

    m_grade = _GRADER_GRADE_RE.search(raw)
    if m_grade:
        g = m_grade.group(1).upper()
        grader = "BGS" if g == "BECKETT" else g
        grade = m_grade.group(2)

    if grader == "CGC" or "cgc" in lower:
        if _CGC_PRISTINE_RE.search(raw):
            grader = "CGC"
            grade = "10"
            cgc_sub_tier = "PRISTINE_10"
        elif _CGC_GEM_RE.search(raw):
            grader = "CGC"
            grade = "10"
            cgc_sub_tier = "GEM_MINT_10"
        elif _CGC_BLUE_RE.search(raw) and grade == "9.5" and re.search(r"gem\s*mint", lower):
            grader = "CGC"
            grade = grade or "9.5"
            cgc_sub_tier = "LEGACY_BLUE_9_5"
        elif grade == "10":
            cgc_sub_tier = "UNKNOWN_10"
        elif grade == "9.5":
            cgc_sub_tier = "MINT_PLUS_9_5" if re.search(r"mint\s*\+", lower) else "UNKNOWN_9_5"
    elif grader is None and re.search(r"\b(raw|ungraded|nm|near\s*mint)\b", lower):
        grader = "RAW"

    card_number: str | None = None
    set_size: str | None = None
    if m_slash := _CARD_NUM_SLASH_RE.search(raw):
        card_number = str(int(m_slash.group(1)))
        set_size = str(int(m_slash.group(2)))
    elif m_promo := _CARD_NUM_PROMO_RE.search(raw):
        card_number = m_promo.group(1).upper()
    elif m_hash := _CARD_NUM_HASH_RE.search(raw):
        card_number = str(int(m_hash.group(1)))

    year = m_y.group(1) if (m_y := _YEAR_RE.search(raw)) else None

    if re.search(r"\b(1st\s*ed(?:ition)?|first\s*edition)\b", lower):
        edition = "1st Edition"
    elif "shadowless" in lower:
        edition = "Shadowless"
    elif "promo" in lower or "black star" in lower:
        edition = "Promo"
    else:
        edition = "Unlimited" if "unlimited" in lower else "Unspecified"

    if re.search(r"\bnon[-\s]?holo\b", lower):
        finish = "Non-Holo"
    elif re.search(r"\b(?:reverse\s*(?:holo|foil)|rev[.\s-]*foil)\b", lower):
        finish = "Reverse Holo"
    elif re.search(r"\balt(?:ernate)?\s*art\b|\bfull\s*art\b|\bsir\b", lower):
        finish = "Full/Alt Art"
    elif re.search(r"\bholo(?:graphic|foil)?\b", lower):
        finish = "Holo"
    else:
        finish = "Unspecified"

    language = "English"
    for lang_name, lang_re in _LANGUAGES:
        if lang_re.search(raw):
            language = lang_name
            break

    qualifiers = tuple(sorted({m.group(1).upper() for m in _QUALIFIER_RE.finditer(raw)}))
    flags = [name for name, pat in _RED_FLAGS.items() if pat.search(raw)]
    if expected_language and language.lower() != expected_language.lower():
        flags.append(f"language_mismatch:{language}")
    if qualifiers:
        flags.append("graded_qualifier")

    conf = 0.25
    if grader:
        conf += 0.25
    if grade:
        conf += 0.15
    if card_number:
        conf += 0.20
    if finish != "Unspecified":
        conf += 0.10
    if year:
        conf += 0.05
    if flags:
        conf = max(0.0, conf - 0.35 * len(flags))
    conf = round(min(1.0, conf), 2)

    tokens = tuple(re.findall(r"[a-z0-9]+", lower))
    disqualified = any(
        f in flags for f in ("lot_or_bundle", "proxy_or_fake", "empty_or_case", "damaged", "graded_qualifier")
    ) or any(f.startswith("language_mismatch:") for f in flags)

    return ParsedListing(
        raw_title=raw,
        grader=grader,
        grade=grade,
        cgc_sub_tier=cgc_sub_tier,
        card_number=card_number,
        set_size=set_size,
        year=year,
        edition=edition,
        finish=finish,
        language=language,
        qualifiers=qualifiers,
        red_flags=tuple(flags),
        confidence=conf,
        disqualified=disqualified,
        normalized_tokens=tokens,
    )
