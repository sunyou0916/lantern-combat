import math

import pygame

from ..config import SCREEN_H, SCREEN_W
from ..systems.camera import Camera
from .hud import HudRenderer
from .layers import LayerCache
from .lighting import LightingRenderer
from .story_renderer import StoryRenderer
from .world_renderer import WorldRenderer


def camera_origin(game, view_size=(SCREEN_W, SCREEN_H)):
    focus, _ = game.story.view()
    return Camera.view_origin(focus, view_size, game.world.size)


def screen_to_world(game, screen_pos):
    return camera_origin(game) + pygame.Vector2(screen_pos)


class GameRenderer:
    def __init__(self, font, big_font, sprites=None, themes=None):
        self.layers = LayerCache()
        self.lighting = LightingRenderer(self.layers)
        self.story = StoryRenderer(self.layers)
        self.world = WorldRenderer(font, sprites, themes, self.layers, self.lighting, self.story)
        self.hud = HudRenderer(font, big_font)

    def draw(self, screen, game, music=None):
        _, zoom = game.story.view()
        size = (math.ceil(SCREEN_W/zoom), math.ceil(SCREEN_H/zoom))
        camera = camera_origin(game, (SCREEN_W, SCREEN_H) if size == (SCREEN_W, SCREEN_H) else size)
        world = self.layers.canvas(size)
        self.world.draw(world, game, camera)
        if size == screen.get_size():
            screen.blit(world, (0, 0))
        else:
            pygame.transform.scale(world, screen.get_size(), screen)
        self.hud.draw(screen, game, music)
        self.story.overlay(screen, game, camera, zoom)
