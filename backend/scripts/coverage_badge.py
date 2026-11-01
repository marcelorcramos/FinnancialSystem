"""Write a coverage badge SVG. Usage: python scripts/coverage_badge.py 99 coverage.svg"""

import sys

TEMPLATE = """<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="20" role="img" \
aria-label="coverage: {value}">
<title>coverage: {value}</title>
<rect width="{label_w}" height="20" fill="#555"/>
<rect x="{label_w}" width="{value_w}" height="20" fill="{color}"/>
<g fill="#fff" font-family="Verdana,DejaVu Sans,sans-serif" font-size="11" text-anchor="middle">
<text x="{label_x}" y="14">coverage</text>
<text x="{value_x}" y="14">{value}</text>
</g>
</svg>
"""


def color(percent: int) -> str:
    if percent >= 95:
        return "#2b7a3f"
    if percent >= 80:
        return "#8a6d00"
    return "#b3403a"


def badge(percent: int) -> str:
    value = f"{percent}%"
    label_w, value_w = 62, 8 + 7 * len(value)
    return TEMPLATE.format(
        width=label_w + value_w,
        label_w=label_w,
        value_w=value_w,
        label_x=label_w / 2,
        value_x=label_w + value_w / 2,
        value=value,
        color=color(percent),
    )


if __name__ == "__main__":
    percent, path = round(float(sys.argv[1])), sys.argv[2]
    with open(path, "w", encoding="utf-8") as file:
        file.write(badge(percent))
