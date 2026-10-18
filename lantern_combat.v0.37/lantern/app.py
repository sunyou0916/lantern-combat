import pygame

from .audio import SoundBoard, ThemeBGM, music_theme_for
from .config import (ASSETS_DIR, AUDIO_DIR, BGM_SAMPLE_RATE, FPS, MAP_PATH, MAX_FRAME_DT, SCREEN_H, SCREEN_W,
                     THEME_ASSETS_DIR)
from .game import Game
from .input import InputController
from .render.fonts import clear_font_caches
from .render.renderer import GameRenderer, screen_to_world
from .render.sprites import SpriteBank
from .render.themes import ThemeBank

CAPTION = 'Lantern Combat v0.37'


class GameApp:
    def __init__(self):
        pygame.mixer.pre_init(BGM_SAMPLE_RATE, -16, 2, 512)
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption(CAPTION)
        self.clock = pygame.time.Clock()
        font = pygame.font.Font(None, 25)
        big_font = pygame.font.Font(None, 70)
        self.game = Game(MAP_PATH, sounds=SoundBoard.load(AUDIO_DIR))
        sprites = SpriteBank(ASSETS_DIR)
        themes = ThemeBank(THEME_ASSETS_DIR)
        self.music = ThemeBGM(AUDIO_DIR)
        self.renderer = GameRenderer(font, big_font, sprites, themes)
        self.input = InputController(self.game, self.music)

    def run(self):
        game = self.game
        while True:
            dt = min(self.clock.tick(FPS)/1000, MAX_FRAME_DT)
            commands = self.input.poll()
            if not commands.running:
                break
            direction, attacking = self.input.held_controls(commands.attack_pressed)
            if not commands.skip_update:
                aim_pos = screen_to_world(game, pygame.mouse.get_pos())
                game.update(dt, direction, attacking, aim_pos)
            self.music.update(music_theme_for(game))
            self.renderer.draw(self.screen, game, self.music)
            pygame.display.flip()
        self.shutdown()

    def shutdown(self):
        self.music.stop()
        clear_font_caches()
        pygame.quit()


def main():
    GameApp().run()
