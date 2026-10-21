"""Renders the toolbar icons: "out" in white on a LinkedIn-blue tile (the promo video's logo)."""

import math
import pathlib

import cairo

ROOT = pathlib.Path(__file__).resolve().parent.parent


def logo_icon(ctx, s):
    r = s * 0.16
    ctx.new_sub_path()
    ctx.arc(s - r, r, r, -math.pi / 2, 0)
    ctx.arc(s - r, s - r, r, 0, math.pi / 2)
    ctx.arc(r, s - r, r, math.pi / 2, math.pi)
    ctx.arc(r, r, r, math.pi, 3 * math.pi / 2)
    ctx.close_path()
    ctx.set_source_rgb(0x0A / 255, 0x66 / 255, 0xC2 / 255)
    ctx.fill()
    ctx.select_font_face("Liberation Sans", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(s * 0.5)
    e = ctx.text_extents("out")
    ctx.move_to((s - e.width) / 2 - e.x_bearing, s * 0.8)
    ctx.set_source_rgb(1, 1, 1)
    ctx.show_text("out")


for size in (16, 32, 48, 128):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    logo_icon(cairo.Context(surf), size)
    surf.write_to_png(str(ROOT / "icons" / f"icon{size}.png"))
    print("wrote", f"icons/icon{size}.png")
