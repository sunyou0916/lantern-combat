from functools import lru_cache

import pygame

from ..config import GOAL_LIGHT_RADIUS, SCREEN_H, SCREEN_W
from ..easing import envelope, smooth
from ..game_state import Phase

DARKNESS = (3, 5, 10)
BOSS_REVEAL_RADIUS = 300


@lru_cache(maxsize=4)
def goal_light_mask(radius):
    mask = pygame.Surface((radius*2+1, radius*2+1), pygame.SRCALPHA)
    mask.fill((*DARKNESS, 255))
    fade = min(60, radius)
    for r in range(radius, 0, -1):
        alpha = round(255*max(0, (r-(radius-fade))/fade))
        pygame.draw.circle(mask, (*DARKNESS, alpha), (radius, radius), r)
    return mask


class LightingRenderer:
    def __init__(self, layers):
        self.layers = layers

    def darkness_mask(self, game, camera, size=(SCREEN_W, SCREEN_H)):
        darkness = self.layers.layer('darkness', size)
        darkness.fill((*DARKNESS, 255))
        strength = game.story.fog_strength()
        if not strength:
            darkness.fill((0, 0, 0, 0))
        else:
            self._cut_vision(darkness, game.player.pos-camera, game.story.visual_vision())
        self._add_tower_lights(darkness, game, camera, size)
        if game.phase == Phase.CINEMATIC:
            pygame.draw.circle(darkness, (0, 0, 0, 0), game.ending.origin-camera,
                               int(game.ending.radius(game.world.size)))
        scene = game.story.active
        if scene and scene.kind in ('boss_arrival', 'ending'):
            self._add_boss_reveal(darkness, game, camera, scene)
            if scene.kind == 'boss_arrival':
                strength *= 1-0.18*envelope(scene.elapsed, 0, scene.duration, 0.7)
        darkness.set_alpha(round(255*strength))
        return darkness

    @staticmethod
    def _cut_vision(darkness, center, vision):
        fade = min(100.0, vision * 0.28)
        inner = max(0.0, vision-fade)
        step = 10
        for radius in range(int(vision), int(inner)-1, -step):
            alpha = round(255 * (radius-inner) / max(1.0, fade))
            pygame.draw.circle(darkness, (*DARKNESS, max(0, min(255, alpha))), center, radius)
        pygame.draw.circle(darkness, (0, 0, 0, 0), center, int(inner))

    def _add_tower_lights(self, darkness, game, camera, size):
        light = goal_light_mask(GOAL_LIGHT_RADIUS)
        radius = GOAL_LIGHT_RADIUS
        for room in game.world.rooms:
            amount = game.story.tower_amount(room)
            if amount <= 0:
                continue
            center = game.world.center(room.goal)-camera
            if not pygame.Rect(round(center.x-radius), round(center.y-radius),
                               radius*2+1, radius*2+1).colliderect((0, 0, *size)):
                continue
            blended = light if amount >= 1.0 else self._faded('tower_light', light, amount)
            darkness.blit(blended, (round(center.x-radius), round(center.y-radius)),
                          special_flags=pygame.BLEND_RGBA_MIN)

    def _add_boss_reveal(self, darkness, game, camera, scene):
        center = game.boss_fight.boss.pos-camera
        reveal = goal_light_mask(BOSS_REVEAL_RADIUS)
        if scene.kind == 'boss_arrival':
            amount = envelope(scene.elapsed, 0, scene.duration, 0.7)
        else:
            amount = smooth(scene.elapsed/1.0)
        blended = reveal
        if 0 < amount < 1:
            blended = self._faded('boss_reveal', reveal, amount)
        elif amount <= 0:
            blended = self.layers.layer('boss_reveal', reveal.get_size())
            blended.fill((*DARKNESS, 255))
        darkness.blit(blended, (round(center.x-BOSS_REVEAL_RADIUS), round(center.y-BOSS_REVEAL_RADIUS)),
                      special_flags=pygame.BLEND_RGBA_MIN)

    def _faded(self, name, light, amount):
        blended = self.layers.layer(name, light.get_size())
        blended.blit(light, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        blended.fill((255, 255, 255, round(255*amount)), special_flags=pygame.BLEND_RGBA_MULT)
        blended.fill((0, 0, 0, round(255*(1-amount))), special_flags=pygame.BLEND_RGBA_ADD)
        return blended
