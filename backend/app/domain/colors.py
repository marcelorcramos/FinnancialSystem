"""Label colors: suggestions for the color picker and normalization.

Two labels of the same user never share the exact same color; similar colors are fine.
"""

import colorsys
from collections.abc import Collection

SUGGESTION_COUNT = 8

# Curated, clearly distinct colors offered first by the color picker.
PALETTE: tuple[str, ...] = (
    "#EF5350", "#EC407A", "#AB47BC", "#7E57C2", "#5C6BC0", "#42A5F5",
    "#29B6F6", "#26C6DA", "#26A69A", "#66BB6A", "#9CCC65", "#D4E157",
    "#FFEE58", "#FFCA28", "#FFA726", "#FF7043", "#8D6E63", "#78909C",
    "#C62828", "#AD1457", "#6A1B9A", "#283593", "#00695C", "#2E7D32",
)  # fmt: skip

_GOLDEN_ANGLE = 0.381966  # fraction of the hue circle; spreads generated hues evenly


def normalize_color(color: str) -> str:
    return color.strip().upper()


def suggest_colors(used: Collection[str], count: int = SUGGESTION_COUNT) -> list[str]:
    """Up to `count` colors that are not in `used`: palette first, then generated hues."""
    taken = {normalize_color(c) for c in used}
    suggestions = [c for c in PALETTE if c not in taken][:count]
    hue, attempts = 0.0, 0
    while len(suggestions) < count and attempts < 1000:
        hue = (hue + _GOLDEN_ANGLE) % 1.0
        attempts += 1
        r, g, b = colorsys.hls_to_rgb(hue, 0.55, 0.6)
        color = f"#{round(r * 255):02X}{round(g * 255):02X}{round(b * 255):02X}"
        if color not in taken and color not in suggestions:
            suggestions.append(color)
    return suggestions
