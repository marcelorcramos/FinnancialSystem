"""Report category filter: any mix of labels and kinds (see docs/DECISIONS.md)."""

import uuid
from dataclasses import dataclass, field

from app.domain.enums import LabelKind


@dataclass(frozen=True, slots=True)
class CategoryFilter:
    """Selects entries whose label is listed or whose label kind is listed.

    Labels and kinds combine as a union (Food + every investment label). An empty filter
    selects every label.
    """

    label_ids: frozenset[uuid.UUID] = field(default_factory=frozenset)
    kinds: frozenset[LabelKind] = field(default_factory=frozenset)

    @property
    def is_empty(self) -> bool:
        return not self.label_ids and not self.kinds

    def matches(self, label_id: uuid.UUID, kind: LabelKind) -> bool:
        return self.is_empty or label_id in self.label_ids or kind in self.kinds
