from functools import lru_cache

import pygame

from ..config import FONT_PATH


@lru_cache(maxsize=16)
def korean_font(size):
    return pygame.font.Font(str(FONT_PATH), size)


@lru_cache(maxsize=256)
def label(text, size, color=(244, 232, 204)):
    return korean_font(size).render(text, True, color)


def clear_font_caches():
    korean_font.cache_clear()
    label.cache_clear()


def wrap_lines(lines, font, width):
    result = []
    for line in lines:
        current = ''
        for char in line:
            if current and font.size(current+char)[0] > width:
                result.append(current)
                current = char
            else:
                current += char
        result.append(current)
    return result
