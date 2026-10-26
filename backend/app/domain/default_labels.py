from dataclasses import dataclass

from app.domain.enums import LabelKind


@dataclass(frozen=True, slots=True)
class LabelTemplate:
    name: str
    kind: LabelKind
    color: str
    icon: str  # icon name (Material Symbols for now)


DEFAULT_LABELS: tuple[LabelTemplate, ...] = (
    LabelTemplate("Investments", LabelKind.INVESTMENT, "#42A5F5", "trending_up"),
    LabelTemplate("Savings", LabelKind.SAVING, "#66BB6A", "savings"),
    LabelTemplate("Emergency Fund", LabelKind.SAVING, "#26A69A", "health_and_safety"),
    LabelTemplate("Food", LabelKind.EXPENSE, "#FFB74D", "restaurant"),
    LabelTemplate("Housing", LabelKind.EXPENSE, "#E57373", "home"),
    LabelTemplate("Electricity", LabelKind.EXPENSE, "#FFD54F", "bolt"),
    LabelTemplate("Water", LabelKind.EXPENSE, "#4FC3F7", "water_drop"),
)
