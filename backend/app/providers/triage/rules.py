"""Deterministic keyword triage. The fallback of last resort: no network, no
state, and no input it cannot handle."""

import re

from app.domain import Category, Priority
from app.providers.triage.base import TriageResult

# English plus common Urdu/Roman-Urdu terms citizens actually use
KEYWORDS: dict[Category, tuple[str, ...]] = {
    Category.water: (
        "water", "pipe", "pipeline", "leak", "leaking", "burst", "flood", "flooding",
        "sewer", "sewerage", "drain", "valve", "tanker", "supply line", "pani", "gutter",
    ),
    Category.electricity: (
        "electricity", "power", "transformer", "wire", "cable", "voltage", "spark",
        "sparking", "outage", "blackout", "feeder", "load shedding", "bijli", "meter",
    ),
    Category.sanitation: (
        "garbage", "trash", "waste", "rubbish", "dump", "kachra", "kundi", "safai",
        "dead animal", "rotting", "smell", "stink", "sweeper",
    ),
    Category.roads: (
        "road", "pothole", "potholes", "sinkhole", "crater", "manhole", "asphalt",
        "carpet", "footpath", "pavement", "sadak", "speed breaker",
    ),
    Category.streetlights: (
        "streetlight", "streetlights", "street light", "street lights", "lamp",
        "light pole", "bulb", "bulbs", "dark", "darkness", "batti", "khamba",
    ),
}

URGENT = (
    "burst", "flood", "flooding", "spark", "sparking", "fire", "smoke", "electrocution",
    "live wire", "hanging wire", "sinkhole", "manhole", "accident", "injury", "injured",
    "collapse", "emergency", "danger", "dangerous", "hazard", "contaminated",
    "contamination", "entering houses",
)
MINOR = ("cosmetic", "faded", "paint", "slow", "minor", "request")



def _whole_word(keyword: str) -> re.Pattern[str]:
    """Match the keyword (or its plural) as a whole word: 'pipes' yes, 'waterfall' no."""
    return re.compile(r"\b" + re.escape(keyword) + r"(?:s|es)?\b")


_WORD = {kw: _whole_word(kw) for kws in KEYWORDS.values() for kw in kws}
_URGENT = [_whole_word(kw) for kw in URGENT]
_MINOR = [_whole_word(kw) for kw in MINOR]


def _summary(text: str) -> str:
    one_line = " ".join(text.split())
    first_sentence = re.split(r"(?<=[.!?])\s", one_line, maxsplit=1)[0]
    return first_sentence if len(first_sentence) <= 140 else first_sentence[:137] + "..."


class RuleBasedTriage:
    name = "rules"

    async def triage(self, text: str, location: str) -> TriageResult:
        lowered = text.lower()

        scores = {
            category: sum(1 for kw in kws if _WORD[kw].search(lowered))
            for category, kws in KEYWORDS.items()
        }
        best = max(scores, key=lambda c: scores[c])
        category = best if scores[best] > 0 else Category.other

        if any(p.search(lowered) for p in _URGENT):
            priority = Priority.high
        elif any(p.search(lowered) for p in _MINOR) or category is Category.other:
            priority = Priority.low
        else:
            priority = Priority.normal

        return TriageResult(
            category=category,
            priority=priority,
            summary=_summary(text) or "Complaint received",
            confidence=0.6 if scores[best] > 0 else 0.3,
        )
