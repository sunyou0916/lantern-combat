import math

import pygame

from ..config import ATTACK_COOLDOWN, BOSS_BODY_RADIUS, BOSS_DASH_RADIUS, BOSS_DASH_WARNING, FLAME_RADIUS, PLAYER_SIZE
from ..easing import smooth
from ..entities.boss import BossAnim, DashPhase
from ..game_state import Phase
from ..world.room import RoomStatus
from ..world.trap import TrapState

THEME_COLORS = {'earth': (76, 67, 49), 'water': (42, 82, 98), 'sky': (78, 77, 101)}
THEME_EDGES = {'earth': (105, 88, 58), 'water': (57, 125, 143), 'sky': (112, 108, 146)}
CLEAN_COLORS = {'earth': (92, 135, 67), 'water': (67, 154, 179), 'sky': (151, 179, 199)}
NEUTRAL_COLOR, NEUTRAL_EDGE = (78, 91, 86), (98, 116, 112)
TRAP_COLORS = {TrapState.SAFE: (68, 75, 86), TrapState.WARNING: (245, 170, 45), TrapState.ACTIVE: (235, 65, 70)}


class WorldRenderer:
    def __init__(self, font, sprites, themes, layers, lighting, story_renderer):
        self.font = font
        self.sprites = sprites
        self.themes = themes
        self.layers = layers
        self.lighting = lighting
        self.story_renderer = story_renderer

    def draw(self, screen, game, camera):
        self._draw_background(screen, game)
        self._draw_ground(screen, game, camera)
        self._draw_earth_grass(screen, game, camera)
        self._draw_fish_and_wind(screen, game, camera)
        self._draw_room_borders(screen, game, camera)
        if game.phase == Phase.EXPLORE:
            self._draw_traps(screen, game, camera)
        self._draw_towers(screen, game, camera)
        self._draw_enemies(screen, game, camera)
        self._draw_heal_items(screen, game, camera)
        self._draw_boss_warnings(screen, game, camera)
        self._draw_dash_trail(screen, game, camera)
        self._draw_boss(screen, game, camera)
        self._draw_flames(screen, game, camera)
        self._draw_player(screen, game, camera)
        self._draw_lightning_strikes(screen, game, camera)
        self._draw_darkness_and_story(screen, game, camera)
        self._draw_vision_edge(screen, game, camera)

    @staticmethod
    def _draw_background(screen, game):
        light = 1.0 if game.phase == Phase.EPILOGUE else smooth((game.ending.time-4)/4.8)
        base_background = (47, 49, 63) if game.phase in (Phase.BOSS, Phase.CINEMATIC, Phase.EPILOGUE) else (22, 27, 35)
        screen.fill(tuple(round(a+(b-a)*light) for a, b in zip(base_background, (142, 169, 174))))

    def _draw_ground(self, screen, game, camera):
        view_w, view_h = screen.get_size()
        world, t, themes = game.world, game.world.tile, self.themes
        for row in range(int(camera.y)//t, min(world.rows, int(camera.y+view_h)//t+1)):
            for col in range(int(camera.x)//t, min(world.cols, int(camera.x+view_w)//t+1)):
                if (col, row) not in world.walkable:
                    continue
                rect = pygame.Rect(col*t-camera.x, row*t-camera.y, t, t)
                nearest, theme = world.visual_cells[(col, row)]
                base = THEME_COLORS.get(theme, NEUTRAL_COLOR)
                edge = THEME_EDGES.get(theme, NEUTRAL_EDGE)
                clean = nearest.purification if theme else 0.0
                target_color = CLEAN_COLORS.get(theme, base)
                base = tuple(round(a+(b-a)*clean) for a, b in zip(base, target_color))
                if theme and themes:
                    tile_art = themes.ground_tile(theme, (t, t), base, edge, clean)
                    screen.blit(tile_art, rect.topleft)
                else:
                    pygame.draw.rect(screen, base, rect)
                    pygame.draw.rect(screen, edge, rect, 1)
                if theme and (col * 17 + row * 31) % 23 == 0:
                    self._draw_ground_detail(screen, theme, pygame.Vector2(rect.center))

    @staticmethod
    def _draw_ground_detail(screen, theme, p):
        if theme == 'earth':
            pygame.draw.line(screen, (42, 35, 25), p + (-6, 8), p + (-2, -6), 2)
            pygame.draw.line(screen, (42, 35, 25), p + (-2, -2), p + (6, -7), 2)
        elif theme == 'water':
            pygame.draw.arc(screen, (101, 190, 198), (p.x-10, p.y-4, 20, 8), 0, math.pi, 1)
        else:
            pygame.draw.circle(screen, (154, 151, 190), p, 5, 1)

    @staticmethod
    def _purified_amounts(game):
        return {room.theme: room.purification
                for room in game.world.rooms if room.status in (RoomStatus.LIGHTING, RoomStatus.COMPLETED)}

    def _draw_earth_grass(self, screen, game, camera):
        earth_amount = self._purified_amounts(game).get('earth', 0.0)
        if earth_amount <= 0:
            return
        world, tile = game.world, game.world.tile
        visible = screen.get_rect()
        min_col = max(0, int(camera.x // tile) - 1)
        max_col = min(world.cols - 1, int((camera.x + screen.get_width()) // tile) + 1)
        min_row = max(0, int(camera.y // tile) - 1)
        max_row = min(world.rows - 1, int((camera.y + screen.get_height()) // tile) + 1)
        for row in range(min_row, max_row + 1):
            for col in range(min_col, max_col + 1):
                if (col, row) not in world.walkable:
                    continue
                point = pygame.Vector2((col + 0.5) * tile - camera.x,
                                       (row + 0.72) * tile - camera.y)
                if not visible.collidepoint(point):
                    continue
                nearest = world.nearest_room((col, row))
                if nearest.theme != 'earth':
                    continue
                distance = abs(col - nearest.goal[0]) + abs(row - nearest.goal[1])
                local_amount = earth_amount * max(0.08, 1.0 - distance / 32.0)
                threshold = ((col*37+row*71) % 100)/160
                growth = smooth((local_amount-threshold)/0.3)
                height = round(growth*(28+((col*11+row*5) % 6)))
                if height <= 0:
                    continue
                x, y = int(point.x), int(point.y)
                pygame.draw.rect(screen, (58, 133, 57), (x, y-height, 4, height), border_radius=1)
                pygame.draw.rect(screen, (103, 181, 66), (x-round(6*growth), y-height+round(5*growth), max(1, round(7*growth)), max(1, round(4*growth))))
                pygame.draw.rect(screen, (145, 211, 78), (x+round(3*growth), y-height+1, max(1, round(8*growth)), max(1, round(4*growth))))

    def _draw_fish_and_wind(self, screen, game, camera):
        amounts = self._purified_amounts(game)
        visible = screen.get_rect()
        tile = game.world.tile
        effects = self.layers.layer('nature', screen.get_size())
        for theme in ('water', 'sky'):
            amount = amounts.get(theme, 0.0)
            if amount <= 0:
                continue
            for i, (cell, phase, speed) in enumerate(game.story.environment[theme]):
                col, row = cell
                base_x = (col + 0.5) * tile - camera.x
                base_y = (row + 0.5) * tile - camera.y
                phase += game.story.clock*speed
                move_span = max(2, tile-34)/2
                x = base_x+math.sin(phase)*move_span
                y = base_y+math.cos(phase*0.7)*move_span*0.6
                alpha = round(255*smooth((amount-i*0.012)/0.18))
                if not visible.colliderect(pygame.Rect(int(x)-24, int(y)-16, 50, 32)):
                    continue
                if theme == 'water':
                    self._draw_fish(effects, int(x), int(y), alpha)
                else:
                    self._draw_wind(effects, x, y, alpha)
        screen.blit(effects, (0, 0))

    @staticmethod
    def _draw_fish(effects, x, y, alpha):
        pygame.draw.ellipse(effects, (214, 179, 74, alpha), (x-7, y-4, 14, 8))
        pygame.draw.polygon(effects, (193, 150, 55, alpha), [(x-7, y), (x-14, y-5), (x-14, y+5)])
        pygame.draw.rect(effects, (38, 62, 70, alpha), (x+3, y-2, 2, 2))
        pygame.draw.arc(effects, (110, 214, 220, alpha), (x-12, y+7, 18, 7), 0.1, 3.0, 1)

    @staticmethod
    def _draw_wind(effects, x, y, alpha):
        pygame.draw.line(effects, (172, 218, 239, alpha), (x-15, y+5), (x-3, y-1), 2)
        pygame.draw.line(effects, (222, 246, 255, alpha), (x-11, y+8), (x+12, y+1), 2)
        pygame.draw.line(effects, (123, 190, 224, alpha), (x-5, y-6), (x+14, y-10), 1)

    @staticmethod
    def _draw_room_borders(screen, game, camera):
        for room in game.world.rooms:
            border = room.rect.move(-camera.x, -camera.y)
            pygame.draw.rect(screen, (55, 100, 110) if room.completed else (155, 90, 65), border, 5)

    def _draw_traps(self, screen, game, camera):
        t = game.world.tile
        for trap in game.world.traps:
            x, y = trap.cell
            rect = pygame.Rect(x*t-camera.x+5, y*t-camera.y+5, t-10, t-10)
            state = trap.state(game.elapsed)
            pygame.draw.rect(screen, TRAP_COLORS[state], rect, border_radius=4)
            pygame.draw.rect(screen, (190, 180, 140), rect, 2, border_radius=4)
            if state == TrapState.ACTIVE:
                for i in range(3):
                    xx = rect.left+4+i*(rect.width-8)/3
                    pygame.draw.polygon(screen, (255, 225, 205), [(xx, rect.bottom-5), (xx+5, rect.top+6), (xx+10, rect.bottom-5)])
            elif state == TrapState.WARNING:
                text = self.font.render('!', True, (40, 30, 20))
                screen.blit(text, text.get_rect(center=rect.center))

    def _draw_towers(self, screen, game, camera):
        sprites, themes, world = self.sprites, self.themes, game.world
        for cell in world.goals:
            point = world.center(cell)-camera
            room = world.room_for_goal(cell)
            lit = cell in game.lit_goals
            locked = room.status not in (RoomStatus.CLEARED, RoomStatus.LIGHTING, RoomStatus.COMPLETED)
            color = (100, 230, 180) if lit else ((105, 108, 122) if locked else (255, 207, 63))
            if not sprites:
                pygame.draw.circle(screen, color, point, world.tile//2-3)
                continue
            pygame.draw.ellipse(screen, color, (point.x-19, point.y-8, 38, 16), 2)
            if themes:
                themes.draw_tower(screen, room.theme, point, game.story.tower_amount(room))
            elif 'goal_lit' in sprites.clips and 'goal_dark' in sprites.clips:
                sprites.draw(screen, 'goal_lit' if lit else 'goal_dark',
                             (point.x, point.y+14), game.elapsed)
            else:
                pygame.draw.circle(screen, color, point, world.tile//2-3)
            text = self.font.render('LIT' if lit else ('LOCK' if locked else 'READY'), True, color)
            screen.blit(text, text.get_rect(center=(point.x, point.y+27)))

    def _draw_enemies(self, screen, game, camera):
        sprites, themes = self.sprites, self.themes
        view = screen.get_rect()
        for enemy in game.enemies:
            if enemy.hp <= 0 or not game.enemy_ai.is_active(enemy):
                continue
            point = enemy.pos-camera
            body = pygame.Rect(round(point.x-13), round(point.y-13), 26, 26)
            if not view.colliderect(body.inflate(110, 130)):
                continue
            attacking = enemy.attack_anim > 0
            if themes:
                walking_phase = math.sin(game.elapsed * 10.0 + enemy.pos.x * 0.01) * 2.0 if enemy.moving else 0.0
                creature = themes.enemy(enemy.theme, time=game.elapsed,
                                        face_right=enemy.face_right, attacking=attacking)
                screen.blit(creature, creature.get_rect(center=(round(point.x), round(point.y + walking_phase))))
            elif sprites and 'enemy_move' in sprites.clips and 'enemy_attack' in sprites.clips:
                clip = 'enemy_attack' if attacking else 'enemy_move'
                animation_time = 0.55-enemy.attack_anim if attacking else (game.elapsed if enemy.moving else 0)
                sprites.draw(screen, clip, (point.x, point.y+13), animation_time,
                             flip=enemy.face_right, white=enemy.flash > 0,
                             loop=not attacking, play_duration=0.55 if attacking else None)
            else:
                pygame.draw.rect(screen, (225, 68, 78), body, border_radius=4)
            pygame.draw.rect(screen, (55, 25, 30), (point.x-17, point.y-53, 34, 5))
            pygame.draw.rect(screen, (255, 95, 102), (point.x-17, point.y-53, 34*enemy.hp/enemy.max_hp, 5))

    @staticmethod
    def _draw_heal_items(screen, game, camera):
        for item in game.combat.heal_items:
            p = item.pos-camera
            pygame.draw.circle(screen, (15, 65, 38), p, 11)
            pygame.draw.rect(screen, (75, 255, 125), (p.x-3, p.y-9, 6, 18), border_radius=1)
            pygame.draw.rect(screen, (75, 255, 125), (p.x-9, p.y-3, 18, 6), border_radius=1)

    def _draw_boss_warnings(self, screen, game, camera):
        effects = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        for hazard in game.boss_fight.hazards:
            hp = hazard.pos-camera
            radius = hazard.radius
            pygame.draw.circle(effects, (145, 55, 235, 115 if hazard.fired else 40), hp, radius)
            pygame.draw.circle(effects, (210, 135, 255, 255), hp, radius, 3)
            if not hazard.fired:
                progress = max(0, min(1, 1-hazard.timer/hazard.total))
                pygame.draw.circle(effects, (235, 195, 255, 180), hp, max(1, int(radius*progress)), 2)
                pygame.draw.line(effects, (225, 185, 255), hp+(-7, 0), hp+(7, 0), 2)
                pygame.draw.line(effects, (225, 185, 255), hp+(0, -7), hp+(0, 7), 2)
                if hazard.kind == 'target':
                    text = self.font.render(f'{max(0.0, hazard.timer):.1f}s', True, (240, 215, 255))
                    effects.blit(text, text.get_rect(center=(round(hp.x), round(hp.y+radius+14))))
        dash = self._boss_dash(game)
        if dash and dash.phase == DashPhase.WARNING:
            start, end = dash.start-camera, dash.end-camera
            side = pygame.Vector2(-dash.direction.y, dash.direction.x)*BOSS_DASH_RADIUS
            corners = [start+side, end+side, end-side, start-side]
            pygame.draw.polygon(effects, (150, 65, 225, 55), corners)
            pygame.draw.lines(effects, (220, 155, 255, 240), True, corners, 2)
            pygame.draw.circle(effects, (220, 155, 255, 240), end, BOSS_DASH_RADIUS, 2)
            progress = 1-max(0.0, dash.timer)/BOSS_DASH_WARNING
            pygame.draw.line(effects, (245, 210, 255, 230), start, start+(end-start)*progress, 4)
            tip = end-dash.direction*12
            pygame.draw.polygon(effects, (240, 200, 255),
                                [end, tip+side*0.3, tip-side*0.3])
        screen.blit(effects, (0, 0))

    @staticmethod
    def _boss_dash(game):
        boss = game.boss_fight.boss
        return boss.dash if boss else None

    def _draw_dash_trail(self, screen, game, camera):
        dash, sprites = self._boss_dash(game), self.sprites
        if dash and dash.phase == DashPhase.ACTIVE and sprites and 'fx_lightning_dash' in sprites.clips:
            direction = dash.direction
            angle = math.degrees(math.atan2(-direction.y, direction.x))
            sprites.draw(screen, 'fx_lightning_dash', game.boss_fight.boss.pos-direction*65-camera,
                         dash.elapsed, angle=angle)

    def _draw_boss(self, screen, game, camera):
        boss, sprites = game.boss_fight.boss, self.sprites
        ending = game.story.active if game.story.active and game.story.active.kind == 'ending' else None
        if not boss or not (boss.hp > 0 or ending):
            return
        bp = boss.pos-camera
        clip = 'boss_move' if boss.anim_state == BossAnim.DASH else 'boss_' + boss.anim_state
        if sprites and clip in sprites.clips:
            attacking = boss.anim_state == BossAnim.ATTACK
            animation_time = boss.animation_time()
            if ending:
                animation_time = ending.context['boss_frame_time']
            sprites.draw(screen, clip, bp, animation_time,
                         flip=not boss.face_right, white=not ending and boss.flash > 0,
                         loop=not attacking, opacity=game.story.boss_opacity())
        else:
            pygame.draw.circle(screen, (245, 200, 255) if boss.flash else (150, 70, 185), bp, BOSS_BODY_RADIUS)
            pygame.draw.circle(screen, (240, 130, 245), bp, BOSS_BODY_RADIUS, 3)

    def _draw_lightning_strikes(self, screen, game, camera):
        sprites = self.sprites
        for hazard in game.boss_fight.hazards:
            if hazard.fired and sprites and hazard.effect in sprites.clips:
                for strike in hazard.strikes:
                    sprites.draw(screen, hazard.effect, strike-camera, hazard.age, loop=False)

    @staticmethod
    def _draw_flames(screen, game, camera):
        for flame in game.combat.flames:
            fp = flame.pos-camera
            tail = fp - flame.direction * 18
            pygame.draw.line(screen, (255, 145, 35), tail, fp, 7)
            pygame.draw.circle(screen, (255, 238, 125), fp, FLAME_RADIUS)
            pygame.draw.circle(screen, (255, 255, 220), fp, 3)

    def _draw_player(self, screen, game, camera):
        player, story, sprites = game.player, game.story, self.sprites
        point = player.pos-camera
        if player.swing_timer > 0:
            pygame.draw.circle(screen, (255, 235, 153), point, player.vision, 3)
        blinking = player.hurt_timer > 0 and int(player.hurt_timer*18) % 2
        if not sprites:
            body = pygame.Rect(0, 0, PLAYER_SIZE, PLAYER_SIZE)
            body.center = point
            pygame.draw.rect(screen, (245, 250, 255) if blinking else (75, 159, 255), body, border_radius=5)
            return
        attacking = player.attack_timer > 0 and not story.blocking
        clip = 'player_attack' if attacking else ('player_side' if player.moving and player.side_walk else 'player_front')
        animation_time = ATTACK_COOLDOWN-player.attack_timer if attacking else (game.elapsed if player.moving else 0)
        sprites.draw(screen, clip, (point.x, point.y+PLAYER_SIZE/2), animation_time,
                     flip=player.facing < 0, white=not story.blocking and player.hurt_timer > 0 and int(player.hurt_timer*18) % 2 == 1,
                     loop=not attacking, play_duration=ATTACK_COOLDOWN if attacking else None,
                     opacity=story.player_opacity(), ghost=story.ghost_amount(),
                     flame=story.flame_amount())

    def _draw_darkness_and_story(self, screen, game, camera):
        ending_scene = game.story.active and game.story.active.kind == 'ending'
        if not ending_scene:
            self.story_renderer.world(screen, game, camera)
        if game.phase != Phase.EPILOGUE:
            screen.blit(self.lighting.darkness_mask(game, camera, screen.get_size()), (0, 0))
        if ending_scene:
            self.story_renderer.world(screen, game, camera)

    @staticmethod
    def _draw_vision_edge(screen, game, camera):
        if game.phase == Phase.CINEMATIC:
            radius = int(game.ending.radius(game.world.size))
            if radius > 0:
                center = game.ending.origin-camera
                pygame.draw.circle(screen, (255, 240, 165), center, radius, 5)
                for i in range(40):
                    angle = i*math.tau/40
                    p = center+pygame.Vector2(math.cos(angle), math.sin(angle))*radius
                    pygame.draw.line(screen, (255, 250, 215), p+(-4, 0), p+(4, 0), 2)
                    pygame.draw.line(screen, (255, 250, 215), p+(0, -4), p+(0, 4), 2)
        elif game.phase != Phase.EPILOGUE and not game.story.blocking:
            pygame.draw.circle(screen, (180, 155, 90), game.player.pos-camera, game.player.vision, 1)
