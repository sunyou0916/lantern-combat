import math

import pygame

from ..easing import envelope, smooth
from ..story.script import BOSS_TITLE, STAT_NOTICE
from ..world.room import RoomStatus
from .fonts import korean_font, label, wrap_lines

GOLD = (255, 212, 119)


class StoryRenderer:
    def __init__(self, layers):
        self.layers = layers

    @staticmethod
    def orb(layer, point, radius=3, alpha=240, color=GOLD):
        point = (round(point[0]), round(point[1]))
        alpha = max(0, min(255, round(alpha)))
        pygame.draw.circle(layer, (*color, alpha//5), point, radius*3)
        pygame.draw.circle(layer, (*color, alpha), point, radius)

    def world(self, screen, game, camera):
        scene = game.story.active
        layer = self.layers.layer('world', screen.get_size())
        for room in game.world.rooms:
            self._draw_tower_orbs(layer, game, room, game.world.center(room.goal)-camera)
        if scene:
            t = scene.elapsed
            for particle in scene.particles:
                sampled = particle.sample(t)
                if sampled:
                    point, alpha = sampled
                    self.orb(layer, point-camera, particle.radius, alpha)
            if scene.kind == 'tower':
                self._draw_tower_wave(layer, game, camera, scene)
            elif scene.kind == 'boss_arrival':
                self._draw_cloud_gathering(layer, game.boss_fight.boss.pos-camera, t)
            elif scene.kind == 'ending':
                self._draw_cloud_fading(layer, game, camera, t)
        screen.blit(layer, (0, 0))

    def _draw_tower_orbs(self, layer, game, room, center):
        story, scene, clock = game.story, game.story.active, game.story.clock
        ready_alpha = 1.0 if room.status == RoomStatus.CLEARED else 0.0
        if scene and scene.kind == 'tower' and room.id == scene.context['room_id']:
            ready_alpha = 1-smooth(scene.elapsed/0.7)
        if ready_alpha:
            for i in range(12):
                angle = i*math.tau/12+clock*0.6
                point = center+pygame.Vector2(math.cos(angle)*36, -24+math.sin(angle)*22)
                self.orb(layer, point, 2, (100+45*math.sin(clock*2+i))*ready_alpha)
        brightness = story.tower_amount(room)
        if brightness:
            self.orb(layer, center+(0, -48), 7, min(255, 185*brightness))

    @staticmethod
    def _draw_tower_wave(layer, game, camera, scene):
        t = scene.elapsed
        target = game.world.center(game.world.rooms[scene.context['room_id']].goal)-camera
        spread = smooth((t-0.9)/1.9)
        alpha = 95*envelope(t, 0.9, 2.8, 0.6)
        if alpha > 0:
            pygame.draw.circle(layer, (255, 224, 149, round(alpha)), target, max(1, round(240*spread)), 2)

    def _draw_cloud_gathering(self, layer, center, t):
        for i in range(48):
            u = smooth((t-(i % 6)*0.06)/2.35)
            angle = i*2.399
            radius = (240+i % 11*25)*(1-u)+12
            point = center+pygame.Vector2(math.cos(angle), math.sin(angle))*radius
            self.orb(layer, point, 5+i % 4, 155*envelope(t, 0, 3.1, 0.7), (46, 39, 61))

    def _draw_cloud_fading(self, layer, game, camera, t):
        center = game.ending.origin-camera
        for i in range(40):
            angle = i*2.399
            radius = 10+(15+i % 7*7)*smooth(t/5.5)
            point = center+pygame.Vector2(math.cos(angle), math.sin(angle))*radius
            self.orb(layer, point, 4+i % 4, 130*envelope(t, 0, 5.5, 1.5), (62, 53, 73))
        beam = envelope(t, 2.8, 6.4, 1.0)
        for room in game.world.rooms:
            target = game.world.center(room.goal)-camera+(0, -48)
            if beam:
                pygame.draw.line(layer, (255, 220, 150, round(45*beam)), target, center, 3)
                pygame.draw.line(layer, (255, 244, 206, round(145*beam)), target, center, 1)

    def panel(self, screen, lines, opacity, top, font_size=26, compact=False):
        if not lines or opacity <= 0:
            return
        width = min(screen.get_width()-48, 1040)
        wrapped = wrap_lines(lines, korean_font(font_size), width-44)
        height = len(wrapped)*(font_size+10)+24
        panel = self.layers.layer('panel', (width, height))
        panel.fill((9, 14, 23, 200 if compact else 225))
        for i, line in enumerate(wrapped):
            text = label(line, font_size)
            panel.blit(text, text.get_rect(center=(width/2, 12+(font_size+10)*(i+0.5))))
        panel.set_alpha(round(255*opacity))
        screen.blit(panel, ((screen.get_width()-width)//2, min(top, screen.get_height()-height-8)))

    def overlay(self, screen, game, camera, zoom):
        story, size = game.story, screen.get_size()
        scene = story.active
        if scene and scene.kind == 'intro':
            mask = self.layers.layer('intro', size)
            mask.fill((4, 6, 13, round(255*(1-smooth(scene.elapsed/2.4)))))
            screen.blit(mask, (0, 0))
        if scene:
            hint = label('Enter  건너뛰기    Esc  일시정지    R  새 게임', 16, (196, 190, 173))
            screen.blit(hint, hint.get_rect(topright=(size[0]-24, 16)))
        if story.region_banner and not scene:
            self._draw_region_banner(screen, story, size)
        if scene and scene.kind == 'boss_arrival':
            title = label(BOSS_TITLE[0], 40)
            title.set_alpha(round(255*envelope(scene.elapsed, 1.2, 3.2)))
            screen.blit(title, title.get_rect(midtop=(size[0]//2, 86)))
        lines, alpha = story.caption()
        top = size[1]-166 if scene and scene.kind == 'tower' else size[1]-120
        if scene and scene.kind == 'ending':
            top = 76
        self.panel(screen, lines, alpha, top)
        if scene and scene.kind == 'tower':
            self.panel(screen, (STAT_NOTICE,), envelope(scene.elapsed, 0.2, 2.8), size[1]-72, 18, True)
        if game.paused:
            shade = self.layers.layer('pause', size)
            shade.fill((3, 6, 12, 180))
            screen.blit(shade, (0, 0))
            text = label('잠시 멈춤', 36)
            screen.blit(text, text.get_rect(center=(size[0]/2, size[1]/2)))

    def _draw_region_banner(self, screen, story, size):
        alpha = envelope(story.region_time, 0, 3.5)
        region = self.layers.layer('region', (450, 80))
        region.fill((9, 14, 23, 185))
        for i, line in enumerate(story.region_banner):
            text = label(line, 23 if i == 0 else 18)
            region.blit(text, (16, 8+i*34))
        region.set_alpha(round(255*alpha))
        screen.blit(region, (size[0]-466, 12))
