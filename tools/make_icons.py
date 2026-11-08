#!/usr/bin/python3
"""Genera los íconos de TypeClip: un cursor de texto (I-beam) verde sobre fondo oscuro."""
from PIL import Image, ImageDraw

BG = (30, 34, 46, 255)        # gris azulado oscuro
FG = (122, 232, 170, 255)     # verde claro (acento "tipeo")
CARET = (250, 204, 21, 255)   # ámbar para el caret parpadeante

def rounded(draw, box, r, fill):
    draw.rounded_rectangle(box, radius=r, fill=fill)

def make(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # fondo con esquinas redondeadas
    rounded(d, (0, 0, size - 1, size - 1), max(2, size // 5), BG)
    s = size / 16.0  # unidad de grilla
    # haz del cursor de texto (I-beam): barra vertical + serifas arriba y abajo
    bar_w = max(1, round(1.6 * s))
    x0 = round(8 * s - bar_w / 2)
    x1 = x0 + bar_w - 1
    y0, y1 = round(3.2 * s), round(12.8 * s)
    d.rectangle((x0, y0, x1, y1), fill=FG)
    ser_w = round(3.6 * s)
    sx0, sx1 = round(8 * s - ser_w / 2), round(8 * s + ser_w / 2)
    sh = max(1, round(1.4 * s))
    d.rectangle((sx0, y0, sx1, y0 + sh - 1), fill=FG)
    d.rectangle((sx0, y1 - sh + 1, sx1, y1), fill=FG)
    # caret ámbar a la derecha del haz (parpadeo de escritura)
    cw = max(1, round(1.2 * s))
    ch = round(3.2 * s)
    cx = round(11.2 * s)
    d.rectangle((cx, y1 - ch, cx + cw - 1, y1), fill=CARET)
    return img

import os
out = os.path.join(os.path.dirname(__file__), "..", "typeclip", "icons")
for sz in (16, 32, 48, 128):
    make(sz).save(os.path.join(out, f"icon{sz}.png"))
print("ok")
