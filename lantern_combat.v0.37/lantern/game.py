import random

import pygame

from .audio import SoundBoard
from .entities.enemy import Enemy
from .entities.player import Player
from .game_state import EndingSequence, GameState, Notice, Phase
from .story.director import StoryDirector
from .systems.boss_fight import BossFight
from .systems.camera import Camera
from .systems.combat import CombatSystem
from .systems.enemy_ai import EnemyAI
from .systems.movement import PlayerMovement
from .systems.progression import Progression
from .systems.raid import RaidSystem
from .world.map_generator import MapGenerator
from .world.world_map import load_map_size


class Game:
    def __init__(self, map_path, seed=None, sounds=None):
        self.tile, self.cols, self.rows = load_map_size(map_path)
        self.rng = random.Random(seed)
        self.sounds = sounds or SoundBoard()
        self.movement = PlayerMovement(self)
        self.enemy_ai = EnemyAI(self)
        self.progression = Progression(self)
        self.reset()

    def reset(self):
        self.world = MapGenerator(self.tile, self.cols, self.rows, self.rng).generate()
        spawn = self.world.center(self.world.spawn)
        self.player = Player.spawn(spawn)
        self.camera = Camera(spawn.copy())
        self.enemies = [Enemy.wanderer(self.world.center(cell), self.world.theme_for_cell(cell))
                        for cell in self.world.enemy_cells]
        self.lit_goals = set()
        self.phase = Phase.EXPLORE
        self.state = GameState.PLAYING
        self.paused = False
        self.input_guard = False
        self.fog_enabled = False
        self.elapsed = 0.0
        self.notice = Notice()
        self.ending = EndingSequence()
        self.raid = RaidSystem(self)
        self.combat = CombatSystem(self)
        self.boss_fight = BossFight(self)
        self.story = StoryDirector(self)
        self.story.start('intro')

    def update(self, dt, direction, attacking=False, aim_pos=None):
        if self.state != GameState.PLAYING or self.raid.exit_dialog or self.paused:
            return
        self.progression.update_purification(dt)
        if self.story.blocking:
            self.story.update(dt)
            return
        self.story.update(dt)
        direction, attacking = self._filter_guarded_input(direction, attacking)
        if self.phase == Phase.EPILOGUE:
            self.elapsed += dt
            self.movement.fly(dt, direction)
            return
        self._tick_timers(dt)
        previous_pos = self.movement.walk(dt, direction)
        if self.raid.exit_dialog or self.story.blocking:
            self.player.moving = False
            return
        self.combat.handle_attack_input(attacking, aim_pos)
        self.combat.update_flames(dt)
        if self.state != GameState.PLAYING or self.phase == Phase.CINEMATIC:
            return
        self.combat.update_tower_damage(dt)
        if self.phase == Phase.CINEMATIC:
            return
        self.combat.collect_healing()
        self.raid.update(dt)
        if self.progression.check_goal_contact():
            return
        self.combat.update_traps()
        if self.state != GameState.PLAYING:
            return
        if self.phase == Phase.BOSS:
            self.boss_fight.update(dt, previous_pos)
            return
        self.enemy_ai.update(dt)

    def _filter_guarded_input(self, direction, attacking):
        if self.input_guard:
            if not attacking and not direction.length_squared():
                self.input_guard = False
            return pygame.Vector2(), False
        return direction, attacking

    def _tick_timers(self, dt):
        self.player.tick_timers(dt)
        self.notice.tick(dt)
        self.elapsed += dt
        self.raid.tick(dt)
