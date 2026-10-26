from app.domain.default_labels import DEFAULT_LABELS
from app.domain.enums import LabelKind


def test_default_labels_cover_every_kind() -> None:
    assert {t.kind for t in DEFAULT_LABELS} == set(LabelKind)


def test_default_labels_have_unique_names_and_valid_colors() -> None:
    names = [t.name for t in DEFAULT_LABELS]
    assert len(names) == len(set(names))
    for template in DEFAULT_LABELS:
        assert template.color.startswith("#") and len(template.color) == 7
        assert template.icon
