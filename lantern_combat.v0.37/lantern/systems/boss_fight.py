import math

import pygame

from ..config import (BOSS_ATTACK_INTERVAL, BOSS_ATTACK_RANGE, BOSS_ATTACK_RECOVERY, BOSS_BODY_RADIUS,
                      BOSS_DAMAGE, BOSS_DASH_DISTANCE, BOSS_DASH_RADIUS, BOSS_DASH_RECOVERY,
                      BOSS_DASH_SPEED, BOSS_DASH_WARNING, BOSS_KEEP_DISTANCE, BOSS_LIGHTNING_DURATION,
                      BOSS_LIGHTNING_RADIUS, BOSS_PATTERNS, BOSS_PULSE_RADIUS, BOSS_PULSE_RING,
                      BOSS_PULSE_WARNING, BOSS_SPEED, BOSS_STORM_SPACING, BOSS_STORM_STRIKES,
                      BOSS_STORM_WARNING, BOSS_TARGET_WARNING, HIT_FLASH_TIME, PLAYER_SIZE)
from ..entities.boss import Boss, BossAnim, BossDash, DashPhase, Hazard
from ..game_state import GameState, Phase

WINDUPS = {'pulse': BOSS_PULSE_WARNING, 'target': BOSS_TARGET_WARNING,
           'storm': BOSS_STORM_WARNING, 'dash': BOSS_DASH_WARNING}


def segment_distance(point, start, end):
    delta = end-start
    if not delta.length_squared():
        return point.distance_to(start)
    fraction = max(0.0, min(1.0, (point-start).dot(delta)/delta.length_squared()))
    return point.distance_to(start+delta*fraction)


class BossFight:
    def __init__(self, game):
        self.game = game
        self.boss = None
        self.hazards = []

    def spawn(self):
        world = self.game.world
        self.boss = Boss(pos=pygame.Vector2(world.width/2, world.height/2))

    def _can_act(self):
        game = self.game
        return (not game.story.blocking and self.boss is not None
                and game.phase == Phase.BOSS and game.state == GameState.PLAYING)

    def cancel_attacks(self):
        self.hazards.clear()
        if self.boss:
            self.boss.dash = None
            self.boss.attack_kind = None

    def damage(self, amount):
        game, boss = self.game, self.boss
        if game.story.blocking or game.phase != Phase.BOSS or not boss or boss.hp <= 0:
            return
        boss.hp = max(0, boss.hp-amount)
        boss.flash = HIT_FLASH_TIME
        if boss.hp == 0:
            game.progression.on_boss_defeated()

    def start_attack(self, kind=None):
        boss = self.boss
        if not self._can_act():
            return
        kind = kind or BOSS_PATTERNS[boss.pattern % len(BOSS_PATTERNS)]
        if kind not in BOSS_PATTERNS:
            raise ValueError(f'Unknown boss attack: {kind}')
        windup = WINDUPS[kind]
        boss.anim_state, boss.anim_time = BossAnim.ATTACK, 0.0
        boss.attack_kind, boss.attack_windup = kind, windup
        boss.cooldown = BOSS_ATTACK_INTERVAL
        boss.pattern += 1
        player_pos = self.game.player.pos
        if kind == 'dash':
            self._prepare_dash(windup)
        elif kind == 'target':
            self._add_lightning(player_pos, BOSS_LIGHTNING_RADIUS, windup, kind)
        elif kind == 'storm':
            for pos in self.storm_positions():
                self._add_lightning(pos, BOSS_LIGHTNING_RADIUS, windup, kind)
        else:
            center = boss.pos.copy()
            strikes = [center] + [center+pygame.Vector2(math.cos(i*math.tau/8), math.sin(i*math.tau/8))*BOSS_PULSE_RING
                                  for i in range(8)]
            self._add_lightning(center, BOSS_PULSE_RADIUS, windup, kind, strikes)

    def _add_lightning(self, pos, radius, warning, kind, strikes=None):
        self.hazards.append(Hazard.lightning(pos, radius, warning, kind, strikes))

    def _prepare_dash(self, windup):
        boss, world = self.boss, self.game.world
        delta = self.game.player.pos-boss.pos
        direction = delta.normalize() if delta.length_squared() else pygame.Vector2(1 if boss.face_right else -1, 0)
        distance = float(BOSS_DASH_DISTANCE)
        for origin, component, limit in ((boss.pos.x, direction.x, world.width),
                                          (boss.pos.y, direction.y, world.height)):
            if abs(component) > 1e-8:
                boundary = limit-BOSS_DASH_RADIUS if component > 0 else BOSS_DASH_RADIUS
                distance = min(distance, max(0.0, (boundary-origin)/component))
        start = boss.pos.copy()
        boss.dash = BossDash(start=start, end=start+direction*distance, direction=direction,
                             distance=distance, timer=windup)
        if abs(direction.x) > 0.01:
            boss.face_right = direction.x > 0

    def storm_positions(self):
        world, rng, player_pos = self.game.world, self.game.rng, self.game.player.pos
        margin = BOSS_LIGHTNING_RADIUS + 8

        def clamp(point):
            return pygame.Vector2(max(margin, min(world.width-margin, point.x)),
                                  max(margin, min(world.height-margin, point.y)))

        positions = [clamp(player_pos)]
        for _ in range(100):
            angle = rng.uniform(0, math.tau)
            candidate = clamp(player_pos + pygame.Vector2(math.cos(angle), math.sin(angle))
                              * rng.uniform(145, 265))
            if all(candidate.distance_to(p) >= BOSS_STORM_SPACING for p in positions):
                positions.append(candidate)
                if len(positions) == BOSS_STORM_STRIKES:
                    return positions
        positions = [clamp(player_pos)]
        origin = positions[0].copy()
        offsets = [i*BOSS_STORM_SPACING for i in (-2, -1, 0, 1, 2)]
        for dx in offsets:
            for dy in offsets:
                candidate = clamp(origin + pygame.Vector2(dx, dy))
                if all(candidate.distance_to(p) >= BOSS_STORM_SPACING for p in positions):
                    positions.append(candidate)
                    if len(positions) == BOSS_STORM_STRIKES:
                        return positions
        return positions

    def update(self, dt, player_previous_pos=None):
        game, boss = self.game, self.boss
        if not self._can_act() or game.paused or game.raid.exit_dialog:
            return
        player_pos = game.player.pos
        player_previous_pos = player_pos if player_previous_pos is None else player_previous_pos
        boss.anim_time += dt
        boss.flash = max(0, boss.flash-dt)
        boss.cooldown -= dt
        if boss.dash:
            boss.moving = False
            self._update_dash(dt, player_previous_pos)
        else:
            self._follow_player(dt)
        self._update_hazards(dt)
        if game.state != GameState.PLAYING:
            return
        if (boss.cooldown <= 0 and boss.dash is None and boss.anim_state != BossAnim.ATTACK
                and player_pos.distance_to(boss.pos) < BOSS_ATTACK_RANGE):
            self.start_attack()

    def _follow_player(self, dt):
        boss, world = self.boss, self.game.world
        if (boss.anim_state == BossAnim.ATTACK and
                boss.anim_time >= boss.attack_windup+BOSS_ATTACK_RECOVERY):
            boss.set_animation(BossAnim.IDLE)
        delta = self.game.player.pos-boss.pos
        previous_pos = boss.pos.copy()
        if boss.anim_state != BossAnim.ATTACK and abs(delta.x) > 0.01:
            boss.face_right = delta.x > 0
        if delta.length() > BOSS_KEEP_DISTANCE:
            boss.pos += delta.normalize()*min(BOSS_SPEED*dt, delta.length()-BOSS_KEEP_DISTANCE)
            boss.pos.x = max(BOSS_BODY_RADIUS, min(world.width-BOSS_BODY_RADIUS, boss.pos.x))
            boss.pos.y = max(BOSS_BODY_RADIUS, min(world.height-BOSS_BODY_RADIUS, boss.pos.y))
        boss.moving = boss.pos.distance_squared_to(previous_pos) > 0.001
        if boss.anim_state != BossAnim.ATTACK:
            state = BossAnim.MOVE if boss.moving else BossAnim.IDLE
            if boss.anim_state != state:
                boss.set_animation(state)

    def _update_dash(self, dt, player_previous_pos):
        boss, dash = self.boss, self.boss.dash
        player_pos = self.game.player.pos
        remaining = dt
        if dash.phase == DashPhase.WARNING:
            consumed = min(remaining, dash.timer)
            dash.timer -= consumed
            remaining -= consumed
            if dash.timer > 1e-8:
                return
            dash.phase = DashPhase.ACTIVE
            boss.set_animation(BossAnim.DASH)
        if dash.phase == DashPhase.ACTIVE:
            distance_left = max(0.0, dash.distance-dash.travelled)
            travel_dt = min(remaining, distance_left/BOSS_DASH_SPEED)
            start = boss.pos.copy()
            boss.pos += dash.direction * (BOSS_DASH_SPEED*travel_dt)
            dash.travelled += BOSS_DASH_SPEED*travel_dt
            dash.elapsed += travel_dt
            boss.moving = travel_dt > 0
            t0 = (dt-remaining)/dt if dt else 0.0
            t1 = (dt-remaining+travel_dt)/dt if dt else 0.0
            player_start = player_previous_pos.lerp(player_pos, t0)
            player_end = player_previous_pos.lerp(player_pos, t1)
            if not dash.hit and segment_distance(pygame.Vector2(), start-player_start,
                                                 boss.pos-player_end) <= BOSS_DASH_RADIUS+PLAYER_SIZE/2:
                self.game.combat.hurt_player(BOSS_DAMAGE)
                dash.hit = True
            remaining -= travel_dt
            if dash.travelled < dash.distance-1e-8:
                return
            boss.pos = dash.end.copy()
            dash.phase, dash.timer = DashPhase.RECOVERY, BOSS_DASH_RECOVERY
            boss.set_animation(BossAnim.IDLE)
            boss.moving = False
        if dash.phase == DashPhase.RECOVERY:
            dash.timer -= remaining
            if dash.timer <= 1e-8:
                boss.dash = None

    def _update_hazards(self, dt):
        player_pos = self.game.player.pos
        for hazard in self.hazards[:]:
            if not hazard.fired:
                hazard.timer -= dt
                if hazard.timer <= 1e-8:
                    hazard.fired = True
                    hazard.age = max(0.0, -hazard.timer)
                    if player_pos.distance_to(hazard.pos) <= hazard.radius+PLAYER_SIZE/2:
                        self.game.combat.hurt_player(BOSS_DAMAGE)
            else:
                hazard.age += dt
            if hazard.fired and hazard.age >= BOSS_LIGHTNING_DURATION:
                self.hazards.remove(hazard)
