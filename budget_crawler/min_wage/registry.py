"""State → scraper class mapping."""

from .base import StateLabourScraper
from .states.kerala import KeralaScraper
from .states.rajasthan import RajasthanScraper
from .states.tamil_nadu import TamilNaduScraper
from .states.uttar_pradesh import UttarPradeshScraper
from .states.madhya_pradesh import MadhyaPradeshScraper
from .states.static import StaticScraper
from pathlib import Path

# Mapping for states with dedicated scrapers.
_SPECIALIZED: dict[str, type[StateLabourScraper]] = {
    "kerala": KeralaScraper,
    "rajasthan": RajasthanScraper,
    "tamil-nadu": TamilNaduScraper,
    "uttar-pradesh": UttarPradeshScraper,
    "madhya-pradesh": MadhyaPradeshScraper,
}


def get(state: str) -> StateLabourScraper | type[StateLabourScraper]:
    """
    Returns a scraper instance or class.
    In the dynamic registry, we return an instance of StaticScraper for unknown states.
    """
    key = state.lower().replace(" ", "-").replace("_", "-")
    if key in _SPECIALIZED:
        return _SPECIALIZED[key]

    # Fallback: return a factory-lambda that creates a StaticScraper for this state
    def static_factory(data_root: Path):
        return StaticScraper(data_root, state_name=state)

    return static_factory


def all_states() -> list[str]:
    """Returns all states found in the honorarium reference CSV."""
    csv_path = Path(__file__).resolve().parents[2] / "data" / "aww_awh_state_honorarium_2024feb.csv"
    if not csv_path.exists():
        return sorted(_SPECIALIZED.keys())

    import csv
    with open(csv_path, encoding="utf-8") as f:
        # 'state' is the first column
        return sorted([row["state"] for row in csv.DictReader(f)])
