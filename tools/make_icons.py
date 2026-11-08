#!/usr/bin/python3
"""Genera los íconos de TypeClip a partir del logo TC.png (monograma TC:
T blanca dentro de una C naranja, sobre tile oscuro) que está en la raíz
del repositorio. La fuente es 175×186 (no cuadrada): se centra sobre el
mismo color de fondo del logo y se escala con LANCZOS a cada tamaño."""
import os
from PIL import Image

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
SRC = os.path.join(ROOT, "TC.png")
OUT = os.path.join(ROOT, "typeclip", "icons")
BG = (21, 23, 24, 255)  # color de fondo del tile del logo

im = Image.open(SRC).convert("RGBA")
side = max(im.size)
sq = Image.new("RGBA", (side, side), BG)
sq.paste(im, ((side - im.width) // 2, (side - im.height) // 2), im)

os.makedirs(OUT, exist_ok=True)
for sz in (16, 32, 48, 128):
    sq.resize((sz, sz), Image.LANCZOS).save(os.path.join(OUT, f"icon{sz}.png"))
print(f"ok: iconos 16/32/48/128 desde {SRC} ({im.width}x{im.height})")
