"""The three product marks the recreated windows carry, where the real apps show one: drawn as
vector paths from open sources, in the official colours, unaltered (motion/reference/).

- GitHub: the mark-github octicon (primer/octicons, MIT), drawn in the header's text colour.
- Linear: the Linear logomark path from simple-icons (CC0), drawn in Mercury White (#f4f5f8),
  the monochrome use Linear's brand page asks for on a dark ground.
- Slack: the four-colour Slack icon (2019), the paths of the public SVG of the icon, in Slack's
  official colours #E01E5A, #36C5F0, #2EB67D and #ECB22E.

The marks are trademarks of their owners and are used only to identify the integrations."""

from functools import cache

import skia

GITHUB_MARK = ("M6.766 11.328c-2.063-.25-3.516-1.734-3.516-3.656 0-.781.281-1.625.75-2.188-.203-.515-.172-1.609.063-2.062"
               ".625-.078 1.468.25 1.968.703.594-.187 1.219-.281 1.985-.281.765 0 1.39.094 1.953.265.484-.437 1.344-.765 "
               "1.969-.687.218.422.25 1.515.046 2.047.5.593.766 1.39.766 2.203 0 1.922-1.453 3.375-3.547 3.64.531.344.89 "
               "1.094.89 1.954v1.625c0 .468.391.734.86.547C13.781 14.359 16 11.53 16 8.03 16 3.61 12.406 0 7.984 0 3.563 0 "
               "0 3.61 0 8.031a7.88 7.88 0 0 0 5.172 7.422c.422.156.828-.125.828-.547v-1.25c-.219.094-.5.156-.75.156-1.031 "
               "0-1.64-.562-2.078-1.609-.172-.422-.36-.672-.719-.719-.187-.015-.25-.093-.25-.187 0-.188.313-.328.625-.328"
               ".453 0 .844.281 1.25.86.313.452.64.655 1.031.655s.641-.14 1-.5c.266-.265.47-.5.657-.656")
LINEAR_MARK = ("M2.886 4.18A11.982 11.982 0 0 1 11.99 0C18.624 0 24 5.376 24 12.009c0 3.64-1.62 6.903-4.18 9.105L2.887 "
               "4.18ZM1.817 5.626l16.556 16.556c-.524.33-1.075.62-1.65.866L.951 7.277c.247-.575.537-1.126.866-1.65ZM.322 "
               "9.163l14.515 14.515c-.71.172-1.443.282-2.195.322L0 11.358a12 12 0 0 1 .322-2.195Zm-.17 4.862 9.823 9.824a12"
               ".02 12.02 0 0 1-9.824-9.824Z")
SLACK_MARK = [
    ("#E01E5A", ("M27.2 80c0 7.3-5.9 13.2-13.2 13.2C6.7 93.2.8 87.3.8 80c0-7.3 5.9-13.2 13.2-13.2h13.2V80zm6.6 0c0-7.3 "
                "5.9-13.2 13.2-13.2 7.3 0 13.2 5.9 13.2 13.2v33c0 7.3-5.9 13.2-13.2 13.2-7.3 0-13.2-5.9-13.2-13.2V80z")),
    ("#36C5F0", ("M47 27c-7.3 0-13.2-5.9-13.2-13.2C33.8 6.5 39.7.6 47 .6c7.3 0 13.2 5.9 13.2 13.2V27H47zm0 6.7c7.3 0 "
                "13.2 5.9 13.2 13.2 0 7.3-5.9 13.2-13.2 13.2H13.9C6.6 60.1.7 54.2.7 46.9c0-7.3 5.9-13.2 13.2-13.2H47z")),
    ("#2EB67D", ("M99.9 46.9c0-7.3 5.9-13.2 13.2-13.2 7.3 0 13.2 5.9 13.2 13.2 0 7.3-5.9 13.2-13.2 13.2H99.9V46.9zm-6.6 "
                "0c0 7.3-5.9 13.2-13.2 13.2-7.3 0-13.2-5.9-13.2-13.2V13.8C66.9 6.5 72.8.6 80.1.6c7.3 0 13.2 5.9 13.2 "
                "13.2v33.1z")),
    ("#ECB22E", ("M80.1 99.8c7.3 0 13.2 5.9 13.2 13.2 0 7.3-5.9 13.2-13.2 13.2-7.3 0-13.2-5.9-13.2-13.2V99.8h13.2zm0-6.6c"
                "-7.3 0-13.2-5.9-13.2-13.2 0-7.3 5.9-13.2 13.2-13.2h33.1c7.3 0 13.2 5.9 13.2 13.2 0 7.3-5.9 13.2-13.2 "
                "13.2H80.1z")),
]
LINEAR_WHITE = "#f4f5f8"   # Mercury White, linear.app/brand


@cache
def _dom(paths, box):
    body = "".join(f'<path fill="{c}" d="{d}"/>' for c, d in paths)
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{box}" height="{box}" viewBox="0 0 {box} {box}">{body}</svg>'
    dom = skia.SVGDOM.MakeFromStream(skia.MemoryStream(svg.encode(), True))
    if dom is None:
        raise RuntimeError("skia cannot parse a logo path")
    return dom


def _draw(canvas, paths, box, x, y, size, alpha):
    if alpha <= 0.002:
        return
    dom = _dom(tuple(paths), box)
    count = canvas.save()
    canvas.translate(x, y)
    canvas.scale(size / box, size / box)
    canvas.saveLayerAlpha(skia.Rect.MakeWH(box, box), round(alpha * 255))
    dom.render(canvas)
    canvas.restoreToCount(count)


def github(canvas, x, y, size, color, alpha=1.0):
    """The GitHub mark, `size` px square, top-left at (x, y)."""
    _draw(canvas, [(color, GITHUB_MARK)], 16, x, y, size, alpha)


def linear(canvas, x, y, size, alpha=1.0, color=LINEAR_WHITE):
    """The Linear logomark, `size` px square, top-left at (x, y)."""
    _draw(canvas, [(color, LINEAR_MARK)], 24, x, y, size, alpha)


def slack(canvas, x, y, size, alpha=1.0):
    """The four-colour Slack icon, `size` px square, top-left at (x, y)."""
    _draw(canvas, SLACK_MARK, 127, x, y, size, alpha)
