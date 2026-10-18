import json
from dataclasses import dataclass
from pathlib import Path
from typing import NamedTuple

import pygame


class FrameVariants(NamedTuple):
    normal: pygame.Surface
    flipped: pygame.Surface
    white: pygame.Surface
    white_flipped: pygame.Surface

    def pick(self, flip, white):
        return self[int(flip)+2*int(white)]


@dataclass
class SpriteClip:
    frames: list
    durations: list
    total: float
    anchor: tuple


def is_fire_pixel(r, g, b):
    return r > 140 and g > 65 and b < min(r, g)*0.75


class SpriteBank:
    def __init__(self, directory):
        directory = Path(directory)
        data = json.loads((directory/'animations.json').read_text(encoding='utf-8-sig'))
        self.clips = {}
        self.ghost_frames = {}
        self.fire_frames = {}
        for name, spec in data.items():
            self.clips[name] = self._load_clip(directory, spec)
            if name.startswith('player_'):
                self._split_player_fire(name, self.clips[name])

    @staticmethod
    def _load_clip(directory, spec):
        frames, durations = [], []
        scale = spec['scale']
        for frame in spec['frames']:
            original = pygame.image.load(str(directory/frame['file'])).convert_alpha()
            size = (max(1, round(original.get_width()*scale)), max(1, round(original.get_height()*scale)))
            image = pygame.transform.scale(original, size)
            if spec['black_colorkey']:
                image.set_colorkey((0, 0, 0))
            flipped = pygame.transform.flip(image, True, False)
            white = image.copy()
            white.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGBA_ADD)
            if spec['black_colorkey']:
                white = image
            frames.append(FrameVariants(image, flipped, white, pygame.transform.flip(white, True, False)))
            durations.append(frame['duration'])
        return SpriteClip(frames=frames, durations=durations, total=sum(durations),
                          anchor=(round(spec['anchor'][0]*scale), round(spec['anchor'][1]*scale)))

    def _split_player_fire(self, name, clip):
        cooled, fire_frames = [], []
        for variants in clip.frames:
            original = variants.normal
            ghost = pygame.transform.grayscale(original)
            ghost.fill((155, 190, 210, 255), special_flags=pygame.BLEND_RGBA_MULT)
            body = original.copy()
            fire = pygame.Surface(original.get_size(), pygame.SRCALPHA)
            for y in range(original.get_height()):
                for x in range(original.get_width()):
                    r, g, b, a = original.get_at((x, y))
                    if is_fire_pixel(r, g, b):
                        ghost.set_at((x, y), (0, 0, 0, 0))
                        body.set_at((x, y), (0, 0, 0, 0))
                        fire.set_at((x, y), (r, g, b, a))
            cooled.append((ghost, pygame.transform.flip(ghost, True, False)))
            fire_frames.append((body, pygame.transform.flip(body, True, False),
                                fire, pygame.transform.flip(fire, True, False)))
        self.ghost_frames[name] = cooled
        self.fire_frames[name] = fire_frames

    def frame_index(self, name, time, loop=True, play_duration=None):
        clip = self.clips[name]
        time = max(0, time)
        if play_duration:
            time = time*clip.total/play_duration
        time = time % clip.total if loop else min(time, clip.total-1e-8)
        for i, duration in enumerate(clip.durations):
            if time < duration-1e-9:
                return i
            time -= duration
        return len(clip.frames)-1

    def draw(self, screen, name, pos, time=0, flip=False, white=False, loop=True, play_duration=None,
             opacity=255, angle=0, ghost=0.0, flame=1.0):
        clip = self.clips[name]
        i = self.frame_index(name, time, loop, play_duration)
        sprite = clip.frames[i].pick(flip, white)
        if flame < 1 and name in self.fire_frames:
            sprite = self._with_shrunk_flame(name, i, flip, flame)
        if ghost and name in self.ghost_frames:
            cooled = self.ghost_frames[name][i][int(flip)]
            if ghost >= 1:
                sprite = cooled
            else:
                sprite = sprite.copy()
                cooled = cooled.copy()
                cooled.set_alpha(round(255*ghost))
                sprite.blit(cooled, (0, 0))
        if opacity != 255:
            sprite = sprite.copy()
            sprite.set_alpha(opacity)
        ax, ay = clip.anchor
        if flip:
            ax = sprite.get_width()-ax
        if angle:
            offset = pygame.Vector2(sprite.get_width()/2-ax, sprite.get_height()/2-ay).rotate(-angle)
            rotated = pygame.transform.rotate(sprite, angle)
            center = pygame.Vector2(pos) + offset
            screen.blit(rotated, rotated.get_rect(center=(round(center.x), round(center.y))))
        else:
            screen.blit(sprite, (round(pos[0]-ax), round(pos[1]-ay)))

    def _with_shrunk_flame(self, name, index, flip, flame):
        fire_data = self.fire_frames[name][index]
        sprite = fire_data[int(flip)].copy()
        fire = fire_data[2+int(flip)]
        rect = fire.get_bounding_rect()
        if flame > 0 and rect.width and rect.height:
            small = pygame.transform.smoothscale(fire.subsurface(rect),
                                                 (max(1, round(rect.width*flame)), max(1, round(rect.height*flame))))
            small.set_alpha(round(255*min(1.0, flame*2)))
            sprite.blit(small, small.get_rect(midbottom=rect.midbottom))
        return sprite
