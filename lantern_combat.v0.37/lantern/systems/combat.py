import pygame

from ..config import (ATTACK_BUFFER_TIME, ATTACK_COOLDOWN, BOSS_BODY_RADIUS, BOSS_TOWER_DAMAGE_MULTIPLIER,
                      ENEMY_HIT_RADIUS, FLAME_RADIUS, GOAL_LIGHT_RADIUS, HEAL_AMOUNT, HEAL_DROP_CHANCE,
                      HEAL_PICKUP_RANGE, HIT_FLASH_TIME, HURT_INVINCIBILITY, PLAYER_SIZE, SWING_TIME,
                      TOWER_DAMAGE_PER_SECOND, TRAP_DAMAGE)
from ..entities.projectiles import Flame, HealItem
from ..game_state import GameState, Phase
from ..world.trap import TrapState


class CombatSystem:
    def __init__(self, game):
        self.game = game
        self.flames = []
        self.heal_items = []

    def handle_attack_input(self, attacking, aim_pos):
        player = self.game.player
        if attacking:
            player.attack_buffer = max(player.attack_buffer, ATTACK_BUFFER_TIME)
        if player.attack_buffer > 0 and player.attack_timer <= 0:
            if self.try_attack(aim_pos):
                self.game.sounds.attack.play()

    def try_attack(self, aim_pos=None):
        game, player = self.game, self.game.player
        if (game.story.blocking or game.state != GameState.PLAYING
                or game.phase in (Phase.CINEMATIC, Phase.EPILOGUE) or game.raid.exit_dialog):
            return False
        if player.attack_timer > 0:
            player.attack_buffer = max(player.attack_buffer, ATTACK_BUFFER_TIME)
            return False
        player.attack_timer = ATTACK_COOLDOWN
        player.swing_timer = SWING_TIME
        direction = pygame.Vector2(aim_pos) - player.pos if aim_pos is not None else pygame.Vector2(player.facing, 0)
        if not direction.length_squared():
            direction = pygame.Vector2(player.facing, 0)
        direction = direction.normalize()
        self.flames.append(Flame(pos=player.pos.copy(), direction=direction, damage=player.damage))
        player.attack_buffer = 0.0
        return True

    def update_flames(self, dt):
        game = self.game
        boss = game.boss_fight.boss
        for flame in self.flames[:]:
            flame.advance(dt)
            hit = False
            if game.phase == Phase.BOSS and boss and boss.hp > 0:
                if flame.pos.distance_to(boss.pos) <= BOSS_BODY_RADIUS + FLAME_RADIUS:
                    game.boss_fight.damage(flame.damage)
                    game.sounds.hit.play()
                    hit = True
            if not hit:
                for enemy in game.enemies:
                    if (game.enemy_ai.is_active(enemy) and enemy.hp > 0 and
                            flame.pos.distance_to(enemy.pos) <= ENEMY_HIT_RADIUS + FLAME_RADIUS):
                        self.damage_enemy(enemy, flame.damage)
                        game.sounds.hit.play()
                        enemy.flash = HIT_FLASH_TIME
                        enemy.alert = True
                        hit = True
                        break
            if hit or flame.spent:
                if flame in self.flames:
                    self.flames.remove(flame)
            if game.story.blocking:
                break

    def damage_enemy(self, enemy, damage):
        if enemy.hp <= 0:
            return
        enemy.hp = max(0, enemy.hp-damage)
        enemy.flash = HIT_FLASH_TIME
        if enemy.hp == 0 and self.game.rng.random() < HEAL_DROP_CHANCE:
            pos = enemy.pos.copy()
            if not self.game.movement.can_stand(pos):
                pos = self.game.world.nearest_walkable_center(pos)
            self.heal_items.append(HealItem(pos=pos, room=enemy.room))

    def update_tower_damage(self, dt):
        game = self.game
        if game.story.blocking or game.raid.exit_dialog or game.state != GameState.PLAYING:
            return
        centers = [game.world.center(cell) for cell in game.lit_goals]
        for enemy in game.enemies:
            if enemy.hp > 0 and game.enemy_ai.is_active(enemy) and any(
                    enemy.pos.distance_to(c) <= GOAL_LIGHT_RADIUS for c in centers):
                self.damage_enemy(enemy, TOWER_DAMAGE_PER_SECOND*dt)
        boss = game.boss_fight.boss
        if game.phase == Phase.BOSS and boss and any(
                boss.pos.distance_to(c) <= GOAL_LIGHT_RADIUS for c in centers):
            game.boss_fight.damage(TOWER_DAMAGE_PER_SECOND*BOSS_TOWER_DAMAGE_MULTIPLIER*dt)

    def collect_healing(self):
        game, player = self.game, self.game.player
        if (game.story.blocking or game.raid.exit_dialog or game.state != GameState.PLAYING
                or player.hp >= player.max_hp):
            return
        for item in self.heal_items[:]:
            if player.pos.distance_to(item.pos) <= PLAYER_SIZE/2+HEAL_PICKUP_RANGE:
                player.hp = min(player.max_hp, player.hp+HEAL_AMOUNT)
                self.heal_items.remove(item)
                if player.hp >= player.max_hp:
                    break

    def update_traps(self):
        game = self.game
        if game.phase != Phase.EXPLORE:
            return
        for trap in game.world.traps:
            if trap.state(game.elapsed) == TrapState.ACTIVE:
                if game.player.rect.colliderect(trap.hit_rect(game.world.tile)):
                    self.hurt_player(TRAP_DAMAGE)
                    if game.state != GameState.PLAYING:
                        return

    def hurt_player(self, damage):
        game, player = self.game, self.game.player
        if (game.story.blocking or game.phase in (Phase.CINEMATIC, Phase.EPILOGUE)
                or game.raid.exit_dialog or player.hurt_timer > 0 or game.state != GameState.PLAYING):
            return
        player.hp = max(0, player.hp-damage)
        player.hurt_timer = HURT_INVINCIBILITY
        if player.hp == 0:
            game.state = GameState.LOSE
