"""Views of the world: an ASCII map for agents, images for judges and the blog."""
from __future__ import annotations

import math

from .dominoes import World

ARROWS = ["→", "↘", "↓", "↙", "←", "↖", "↑", "↗"]   # y points down, so 90 deg = south


def arrow(angle: float) -> str:
    return ARROWS[int(round(angle / 45.0)) % 8]


def ascii_map(world: World, x0: float, y0: float, x1: float, y1: float,
              step: float = 1.0) -> str:
    """One character per `step` units. Arrows = standing dominoes (rough facing),
    S = start, x = knocked over, . = empty, : = outside any region."""
    cols = int(math.ceil((x1 - x0) / step))
    rows = int(math.ceil((y1 - y0) / step))
    grid = [["." for _ in range(cols)] for _ in range(rows)]
    for r in range(rows):
        for c in range(cols):
            if world.region_at(x0 + (c + 0.5) * step, y0 + (r + 0.5) * step) is None:
                grid[r][c] = ":"
    for d in sorted(world.dominoes.values(), key=lambda d: d.id):
        c = int((d.x - x0) // step)
        r = int((d.y - y0) // step)
        if 0 <= r < rows and 0 <= c < cols:
            ch = "S" if d.start and d.state == "up" else ("x" if d.state == "down" else arrow(d.angle))
            if grid[r][c] in ".:" or ch in "Sx":
                grid[r][c] = ch
    tens = "".join(str(int(x0 + c * step) // 10 % 10) if int(x0 + c * step) % 10 == 0 else " "
                   for c in range(cols))
    ones = "".join(str(int(x0 + c * step) % 10) for c in range(cols))
    lines = ["     " + tens, "     " + ones]
    for r in range(rows):
        lines.append(f"{int(y0 + r * step):>4} " + "".join(grid[r]))
    return "\n".join(lines)


def _require_pil():
    try:
        from PIL import Image, ImageDraw  # noqa: F401
    except ImportError as e:  # pragma: no cover
        raise RuntimeError("Pillow is needed for images: pip install pillow") from e


def picture_png(world: World, path: str, fallen: set | None = None, scale: int = 14,
                show_standing: bool = False, show_regions: bool = False,
                bounds: tuple | None = None) -> str:
    """Render the picture. By default only knocked-over dominoes are drawn (what a
    judge sees). `fallen` restricts to a set of ids (e.g. for animation frames)."""
    _require_pil()
    from PIL import Image, ImageDraw
    x0, y0, x1, y1 = bounds or (0, 0, world.width, world.height)
    W, H = int((x1 - x0) * scale), int((y1 - y0) * scale)
    img = Image.new("RGB", (W, H), (250, 248, 243))
    dr = ImageDraw.Draw(img)

    def px(x, y):
        return ((x - x0) * scale, (y - y0) * scale)

    if show_regions:
        for r in world.regions.values():
            fill = (240, 236, 226) if r.kind == "table" else (232, 238, 244)
            dr.rectangle([px(r.x0, r.y0), px(r.x1, r.y1)], fill=fill, outline=(205, 200, 190))
    lw = max(2, int(scale * 0.32))
    for d in world.dominoes.values():
        is_down = d.state == "down" if fallen is None else d.id in fallen
        rad = math.radians(d.angle)
        if is_down:
            ex, ey = d.x + 0.9 * math.cos(rad), d.y + 0.9 * math.sin(rad)
            dr.line([px(d.x, d.y), px(ex, ey)], fill=(34, 34, 40), width=lw)
        elif show_standing:
            hx, hy = -math.sin(rad) * 0.25, math.cos(rad) * 0.25   # standing = thin bar across the line
            dr.line([px(d.x - hx, d.y - hy), px(d.x + hx, d.y + hy)], fill=(170, 165, 155), width=2)
    img.save(path)
    return path


def topple_gif(world: World, times: dict, path: str, scale: int = 10, fps: int = 20,
               speedup: float = 1.0, bounds: tuple | None = None) -> str:
    """Animate a push. `times` is World.topple()'s result; call after toppling."""
    _require_pil()
    from PIL import Image
    import os
    import tempfile
    if not times:
        return ""
    t_end = max(times.values())
    n = max(2, int(t_end / speedup * fps) + fps)  # one extra second at the end
    frames = []
    tmp = tempfile.mkdtemp()
    early = {d.id for d in world.dominoes.values() if d.state == "down" and d.id not in times}
    for k in range(n):
        t = k * speedup / fps
        fallen = {i for i, ti in times.items() if ti <= t} | early
        p = os.path.join(tmp, f"f{k}.png")
        picture_png(world, p, fallen=fallen, scale=scale, show_standing=True, bounds=bounds)
        frames.append(Image.open(p).convert("P", palette=Image.ADAPTIVE))
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=int(1000 / fps), loop=0)
    return path
