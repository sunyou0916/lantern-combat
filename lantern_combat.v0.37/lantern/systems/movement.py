import math

import pygame

from ..config import GHOST_SPEED, PLAYER_SPEED
from ..entities.player import Player
from ..game_state import Phase


class PlayerMovement:
    def __init__(self, game):
        self.game = game

    def can_stand(self, pos):
        world = self.game.world
        if self.game.phase in (Phase.BOSS, Phase.EPILOGUE):
            return world.body_in_bounds(pos)
        return world.body_on_paths(pos)

    def walk(self, dt, direction):
        player = self.game.player
        previous_pos = player.pos.copy()
        player.face(direction)
        if direction.length_squared():
            self.move(direction.normalize() * PLAYER_SPEED * dt)
        player.moving = player.pos.distance_squared_to(previous_pos) > 0.001
        player.velocity = (player.pos - previous_pos) / max(dt, 1e-6)
        return previous_pos

    def fly(self, dt, direction):
        game, player = self.game, self.game.player
        player.moving = bool(direction.length_squared())
        player.side_walk = bool(direction.x)
        if direction.x:
            player.facing = 1 if direction.x > 0 else -1
        if player.moving:
            self.move(direction.normalize()*GHOST_SPEED*dt)
        if game.camera.follow:
            game.camera.pos = player.pos.copy()

    def move(self, delta):
        game = self.game
        if game.raid.exit_dialog or game.story.blocking:
            return
        world, raid, player = game.world, game.raid, game.player
        steps = max(1, math.ceil(delta.length()/4))
        step = delta/steps
        for _ in range(steps):
            for change in (pygame.Vector2(step.x, 0), pygame.Vector2(0, step.y)):
                if not change.length_squared():
                    continue
                candidate = player.pos+change
                if not self.can_stand(candidate):
                    continue
                exploring = game.phase == Phase.EXPLORE
                if exploring and raid.active_room is not None:
                    if not raid.active_room.rect.contains(Player.body_at(candidate)):
                        if raid.entry_grace <= 0:
                            raid.request_exit()
                        return
                old = player.pos.copy()
                player.pos = candidate
                if exploring and raid.active_room is None:
                    room = world.room_at(candidate)
                    if room and not room.completed:
                        raid.enter(room, world.center(world.cell_at(old)))
                        return
