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


def agent_view_png(world: World, region, path: str, markers: dict | None = None,
                   hands: dict | None = None, scale: int | None = None) -> str:
    """What a person standing at the table sees, as an image for an agent.

    Standing dominoes are dark bars across their line of fall with an orange tick
    on the side they'll fall toward; knocked-over ones lie flat in red; the start
    domino is ringed in green; people pointing show as a labelled circle; people
    working show their name where their hands are. Light grid lines every unit and
    labelled lines every 5 units let the viewer read rough coordinates."""
    _require_pil()
    from PIL import Image, ImageDraw, ImageFont
    x0, y0, x1, y1 = region.x0, region.y0, region.x1, region.y1
    if scale is None:
        scale = max(14, min(40, int(1080 / max(1e-9, x1 - x0))))
    pad = 28
    W, H = int((x1 - x0) * scale) + 2 * pad, int((y1 - y0) * scale) + 2 * pad
    img = Image.new("RGB", (W, H), (252, 250, 245))
    dr = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default(size=13)
    except TypeError:  # older Pillow
        font = ImageFont.load_default()

    def px(x, y):
        return (pad + (x - x0) * scale, pad + (y - y0) * scale)

    labels = []

    def label(cx, cy, text, color):
        labels.append((cx, cy, text, color))

    dr.rectangle([px(x0, y0), px(x1, y1)], fill=(244, 238, 226), outline=(190, 180, 160))
    for gx in range(int(x0), int(x1) + 1):
        col = (205, 196, 178) if gx % 5 == 0 else (233, 226, 212)
        dr.line([px(gx, y0), px(gx, y1)], fill=col, width=1)
        if gx % 5 == 0:
            dr.text((px(gx, y0)[0] - 6, 6), str(gx), fill=(110, 100, 85), font=font)
            dr.text((px(gx, y1)[0] - 6, H - pad + 8), str(gx), fill=(110, 100, 85), font=font)
    for gy in range(int(y0), int(y1) + 1):
        col = (205, 196, 178) if gy % 5 == 0 else (233, 226, 212)
        dr.line([px(x0, gy), px(x1, gy)], fill=col, width=1)
        if gy % 5 == 0:
            dr.text((4, px(x0, gy)[1] - 7), str(gy), fill=(110, 100, 85), font=font)
            dr.text((W - pad + 4, px(x0, gy)[1] - 7), str(gy), fill=(110, 100, 85), font=font)
    for d in world.dominoes.values():
        if not region.contains(d.x, d.y):
            continue
        rad = math.radians(d.angle)
        ux, uy = math.cos(rad), math.sin(rad)
        if d.state == "down":
            dr.line([px(d.x, d.y), px(d.x + 0.9 * ux, d.y + 0.9 * uy)], fill=(200, 60, 50), width=max(2, scale // 5))
            continue
        hx, hy = -uy * 0.25, ux * 0.25
        dr.line([px(d.x - hx, d.y - hy), px(d.x + hx, d.y + hy)], fill=(40, 40, 46), width=max(2, scale // 6))
        dr.line([px(d.x, d.y), px(d.x + 0.32 * ux, d.y + 0.32 * uy)], fill=(214, 120, 30), width=max(2, scale // 8))
        if d.start:
            cx, cy = px(d.x, d.y)
            r = 0.7 * scale
            dr.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(30, 150, 70), width=3)
            label(cx, cy - r - 16, "START", (30, 130, 60))
    for name, (x, y) in (hands or {}).items():
        if region.contains(x, y):
            cx, cy = px(x, y)
            dr.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=(60, 90, 160))
            label(cx + 8, cy + 8, f"{name}'s hands", (60, 90, 160))
    for name, (x, y) in (markers or {}).items():
        if region.contains(x, y):
            cx, cy = px(x, y)
            r = 0.9 * scale
            dr.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(150, 70, 170), width=3)
            label(cx + r + 4, cy - 8, f"{name} is pointing here", (130, 60, 150))
    for cx, cy, text, color in labels:       # labels last, on a light backing so they stay readable
        box = dr.textbbox((cx, cy), text, font=font)
        dr.rectangle([box[0] - 3, box[1] - 2, box[2] + 3, box[3] + 2], fill=(255, 255, 255), outline=color)
        dr.text((cx, cy), text, fill=color, font=font)
    img.save(path)
    return path


def sketch_points(s: dict) -> list:
    """Points of one scratch-pad stroke, in table coordinates."""
    t = s.get("type", "curve")
    try:
        if t in ("curve", "polyline"):
            return [(float(x), float(y)) for x, y in s.get("points", [])]
        if t == "line":
            return [(float(s["x0"]), float(s["y0"])), (float(s["x1"]), float(s["y1"]))]
        if t in ("circle", "arc"):
            cx, cy, r = float(s["cx"]), float(s["cy"]), float(s["r"])
            a0, a1 = float(s.get("a0", 0)), float(s.get("a1", 360))
            n = max(8, int(abs(a1 - a0) / 10))
            return [(cx + r * math.cos(math.radians(a0 + (a1 - a0) * k / n)),
                     cy + r * math.sin(math.radians(a0 + (a1 - a0) * k / n))) for k in range(n + 1)]
    except (KeyError, TypeError, ValueError):
        return []
    return []


def sketch_png(strokes: list, path: str, size: tuple = (60, 40), holder: str | None = None,
               scale: int = 14) -> str:
    """The scratch pad: pencil strokes and labels on paper, with the table's grid
    lightly marked so a sketch can be read against the table."""
    _require_pil()
    from PIL import Image, ImageDraw, ImageFont
    W, H = size
    pad = 26
    img = Image.new("RGB", (int(W * scale) + 2 * pad, int(H * scale) + 2 * pad + 30), (255, 253, 240))
    dr = ImageDraw.Draw(img)
    try:
        font = ImageFont.load_default(size=16)
    except TypeError:
        font = ImageFont.load_default()

    def px(x, y):
        return (pad + x * scale, pad + 30 + y * scale)

    title = "SCRATCH PAD" + (f" (held by {holder})" if holder else "")
    dr.text((pad, 6), title, fill=(120, 100, 60), font=font)
    for gx in range(0, int(W) + 1, 5):
        dr.line([px(gx, 0), px(gx, H)], fill=(226, 222, 200), width=1)
        dr.text((px(gx, 0)[0] - 5, pad + 12), str(gx), fill=(170, 160, 130), font=font)
    for gy in range(0, int(H) + 1, 5):
        dr.line([px(0, gy), px(W, gy)], fill=(226, 222, 200), width=1)
        dr.text((4, px(0, gy)[1] - 8), str(gy), fill=(170, 160, 130), font=font)
    for s in strokes:
        if s.get("type") == "label":
            try:
                dr.text(px(float(s["x"]), float(s["y"])), str(s.get("text", ""))[:24], fill=(60, 60, 140), font=font)
            except (KeyError, TypeError, ValueError):
                pass
            continue
        pts = [px(x, y) for x, y in sketch_points(s)]
        if len(pts) >= 2:
            dr.line(pts, fill=(50, 50, 60), width=4, joint="curve")
    img.save(path)
    return path
