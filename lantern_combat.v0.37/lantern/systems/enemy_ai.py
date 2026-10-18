import pygame

from ..config import (ENEMY_ATTACK_ANIM_TIME, ENEMY_ATTACK_COOLDOWN, ENEMY_ATTACK_RANGE, ENEMY_DAMAGE,
                      ENEMY_DETECT_RANGE, ENEMY_PREDICTION_TIME, ENEMY_REPATH_INTERVAL,
                      ENEMY_SEPARATION_PUSH, ENEMY_SEPARATION_RADIUS, ENEMY_SPEED)
from ..game_state import GameState, Phase
from ..world.pathfinding import GridNavigator
from ..world.room import RoomStatus


class EnemyAI:
    def __init__(self, game):
        self.game = game
        self.navigator = GridNavigator()

    def is_active(self, enemy):
        game = self.game
        if game.phase in (Phase.BOSS, Phase.CINEMATIC, Phase.EPILOGUE):
            return False
        if enemy.theme in {room.theme for room in game.world.rooms if room.status == RoomStatus.COMPLETED}:
            return False
        return enemy.room == game.raid.active_room_id

    def update(self, dt):
        game, player = self.game, self.game.player
        for enemy in game.enemies:
            if enemy.hp <= 0 or not self.is_active(enemy):
                continue
            enemy.cooldown = max(0, enemy.cooldown-dt)
            enemy.flash = max(0, enemy.flash-dt)
            enemy.attack_anim = max(0, enemy.attack_anim-dt)
            delta = player.pos - enemy.pos
            dist = delta.length()
            if abs(delta.x) > 0.01:
                enemy.face_right = delta.x > 0
            enemy.moving = dist > ENEMY_ATTACK_RANGE and (enemy.alert or dist <= ENEMY_DETECT_RANGE)
            if dist <= ENEMY_DETECT_RANGE:
                enemy.alert = True
            if not enemy.alert:
                continue
            if dist > ENEMY_ATTACK_RANGE:
                self._chase(enemy, dt)
            dist = player.pos.distance_to(enemy.pos)
            if dist <= ENEMY_ATTACK_RANGE + 0.01 and enemy.cooldown <= 0 and player.hurt_timer <= 0:
                game.combat.hurt_player(ENEMY_DAMAGE)
                enemy.attack_anim = ENEMY_ATTACK_ANIM_TIME
                enemy.cooldown = ENEMY_ATTACK_COOLDOWN
                if player.hp == 0:
                    game.state = GameState.LOSE
                    return

    def _chase(self, enemy, dt):
        game, world = self.game, self.game.world
        enemy.path_timer = max(0.0, enemy.path_timer-dt)
        if enemy.path_cell is None or enemy.path_timer <= 0:
            predicted = game.player.pos + game.player.velocity * ENEMY_PREDICTION_TIME
            enemy.path_cell = self.navigator.next_cell(enemy.pos, predicted, world.walkable, world.tile)
            enemy.path_timer = ENEMY_REPATH_INTERVAL
        waypoint = world.center(enemy.path_cell) if enemy.path_cell else None
        route = waypoint - enemy.pos if waypoint is not None else pygame.Vector2()
        if route.length_squared():
            enemy.pos += route.normalize() * min(ENEMY_SPEED*dt, route.length())
        if enemy.room is not None:
            world.rooms[enemy.room].clamp(enemy.pos)
        for other in game.enemies:
            if other is enemy or other.hp <= 0 or other.room != enemy.room:
                continue
            separation = enemy.pos - other.pos
            if 0 < separation.length_squared() < ENEMY_SEPARATION_RADIUS ** 2:
                enemy.pos += separation.normalize() * ENEMY_SEPARATION_PUSH
