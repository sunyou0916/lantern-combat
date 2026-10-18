from pathlib import Path

import pygame


class ThemeBank:
    THEMES = ('earth', 'water', 'sky')

    def __init__(self, directory):
        directory = Path(directory)
        asset_root = directory.parent.parent
        tile_directory = asset_root / 'tiles'
        self.walk_sheets = {}
        self.attack_sheets = {}
        self.tower_sheets = {}
        self.tiles = {}
        self.tile_cache = {}
        self.tower_cache = {}
        self.ground_cache = {}
        for name in self.THEMES:
            self.walk_sheets[name] = self._load(directory / f'{name}_walk_sheet.png')
            self.attack_sheets[name] = self._load(directory / f'{name}_attack_sheet.png')
            self.tower_sheets[name] = self._load(directory / f'{name}_tower_states.png')
            self.tiles[name] = self._load(tile_directory / f'{name}_tile.png')

    @staticmethod
    def _load(path):
        image = pygame.image.load(str(path)).convert_alpha()
        image.set_colorkey(image.get_at((0, 0))[:3])
        return image

    @staticmethod
    def _frame(sheet, index, size, alpha=255):
        frame_width = sheet.get_width() // 4
        rect = pygame.Rect(index * frame_width, 0, frame_width, sheet.get_height())
        image = sheet.subsurface(rect).copy()
        image = pygame.transform.smoothscale(image, size)
        if alpha != 255:
            image.set_alpha(alpha)
        return image

    def enemy(self, theme, size=(58, 58), time=0.0, face_right=False, attacking=False):
        sheet = self.attack_sheets[theme] if attacking else self.walk_sheets[theme]
        frame = int(time * (10.0 if attacking else 7.0)) % 4
        if attacking:
            size = (round(size[0] * 1.12), round(size[1] * 1.12))
        image = self._frame(sheet, frame, size)
        return pygame.transform.flip(image, not face_right, False)

    def tower(self, theme, size=(92, 120), time=0.0, lit=False):
        key = (theme, size, lit)
        if key not in self.tower_cache:
            sheet = self.tower_sheets[theme]
            half_width = sheet.get_width() // 2
            panel = pygame.Rect(half_width if lit else 0, 0, half_width, sheet.get_height())
            self.tower_cache[key] = pygame.transform.smoothscale(sheet.subsurface(panel), size)
        return self.tower_cache[key]

    def draw_tower(self, screen, theme, point, amount):
        dark, lit = self.tower(theme), self.tower(theme, lit=True)
        rect = dark.get_rect(midbottom=(round(point.x), round(point.y+28)))
        screen.blit(dark, rect)
        lit.set_alpha(round(255*min(1.0, amount)))
        screen.blit(lit, rect)

    def terrain_tile(self, theme, size, alpha=220):
        key = (theme, tuple(size), alpha)
        if key not in self.tile_cache:
            image = pygame.transform.smoothscale(self.tiles[theme], size).copy()
            image.set_alpha(alpha)
            self.tile_cache[key] = image
        return self.tile_cache[key]

    def ground_tile(self, theme, size, base, edge, clean):
        key = theme, size, round(clean*255)
        if key not in self.ground_cache:
            tile = pygame.Surface(size).convert()
            tile.fill(base)
            art = self.terrain_tile(theme, size, alpha=205)
            art.set_alpha(round(205*(1-clean*0.7)))
            tile.blit(art, (0, 0))
            pygame.draw.rect(tile, edge, (0, 0, *size), 1)
            self.ground_cache[key] = tile
        return self.ground_cache[key]
