from dataclasses import dataclass

from app.domain.enums import LabelKind


@dataclass(frozen=True, slots=True)
class LabelTemplate:
    name: str
    kind: LabelKind
    color: str
    icon: str  # nome do ícone em Material Symbols


DEFAULT_LABELS: tuple[LabelTemplate, ...] = (
    LabelTemplate("Aluguel", LabelKind.EXPENSE, "#E57373", "home"),
    LabelTemplate("Mercado", LabelKind.EXPENSE, "#FFB74D", "shopping_cart"),
    LabelTemplate("Água", LabelKind.EXPENSE, "#4FC3F7", "water_drop"),
    LabelTemplate("Luz", LabelKind.EXPENSE, "#FFD54F", "bolt"),
    LabelTemplate("Transporte", LabelKind.EXPENSE, "#9575CD", "directions_bus"),
    LabelTemplate("Poupança", LabelKind.SAVING, "#66BB6A", "savings"),
    LabelTemplate("Fundo de emergência", LabelKind.SAVING, "#26A69A", "health_and_safety"),
    LabelTemplate("Investimento", LabelKind.INVESTMENT, "#42A5F5", "trending_up"),
)
