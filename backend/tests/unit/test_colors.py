from app.domain.colors import PALETTE, SUGGESTION_COUNT, normalize_color, suggest_colors


def test_suggests_eight_palette_colors_by_default() -> None:
    assert suggest_colors([]) == list(PALETTE[:SUGGESTION_COUNT])


def test_never_suggests_a_used_color_case_insensitively() -> None:
    used = [PALETTE[0].lower(), PALETTE[3]]
    suggestions = suggest_colors(used)
    assert len(suggestions) == SUGGESTION_COUNT
    assert not {normalize_color(c) for c in used} & set(suggestions)


def test_falls_back_to_generated_colors_when_palette_is_used_up() -> None:
    suggestions = suggest_colors(PALETTE)
    assert len(suggestions) == SUGGESTION_COUNT
    assert len(set(suggestions)) == SUGGESTION_COUNT
    assert not set(PALETTE) & set(suggestions)
    assert all(len(c) == 7 and c.startswith("#") for c in suggestions)
