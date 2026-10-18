import math

from ..config import (RAID_BASE_DURATION, RAID_CANCEL_GRACE, RAID_ENEMY_LIMIT,
                      RAID_ENTRY_GRACE, RAID_SPAWN_INTERVAL, RAID_TIME_BONUS)
from ..entities.enemy import Enemy
from ..game_state import GameState
from ..story.script import RAID_READY
from ..world.room import RoomStatus

ESCAPE_INVINCIBILITY = 1.0


class RaidSystem:
    def __init__(self, game):
        self.game = game
        self.active_room_id = None
        self.exit_dialog = False
        self.exit_return = None
        self.entry_grace = 0.0

    @property
    def active_room(self):
        if self.active_room_id is None:
            return None
        return self.game.world.rooms[self.active_room_id]

    def tick(self, dt):
        self.entry_grace = max(0, self.entry_grace-dt)

    def enter(self, room, outside):
        game = self.game
        if game.story.blocking or room.completed or self.active_room_id is not None:
            return
        self.active_room_id = room.id
        self.exit_return = outside.copy()
        room.clamp(game.player.pos)
        self.entry_grace = RAID_ENTRY_GRACE
        if room.status == RoomStatus.IDLE:
            room.start_raid(RAID_BASE_DURATION * ((1 + RAID_TIME_BONUS) ** len(game.lit_goals)))
        game.notice.show(f'RAID {room.id+1}: defeat up to {RAID_ENEMY_LIMIT} enemies. E: request escape.', 4.0)
        game.story.enter_region(room.theme)

    def request_exit(self):
        game = self.game
        if (not game.input_guard and not game.paused and not game.story.blocking
                and game.state == GameState.PLAYING and self.active_room_id is not None):
            self.exit_dialog = True

    def answer_exit(self, yes):
        if not self.exit_dialog:
            return
        game, player = self.game, self.game.player
        self.exit_dialog = False
        game.input_guard = True
        if not yes:
            self.entry_grace = RAID_CANCEL_GRACE
            return
        player.hp = max(1, math.ceil(player.hp/2))
        room = self.active_room
        game.enemies = [e for e in game.enemies if e.room != room.id]
        room.reset_raid()
        player.pos = self.exit_return.copy()
        self.active_room_id = None
        player.hurt_timer = ESCAPE_INVINCIBILITY
        game.notice.show('Escaped: half current HP lost. The raid has reset.', 4.0)

    def update(self, dt):
        room = self.active_room
        if room is None or room.status != RoomStatus.FIGHTING:
            return
        game = self.game
        room.time_left = max(0.0, room.time_left - dt)
        room.spawn_timer = room.spawn_timer - dt
        if room.time_left > 0 and room.spawn_timer <= 0 and room.spawned_count < RAID_ENEMY_LIMIT:
            self._spawn_enemy(room)
        alive = any(e.hp > 0 and e.room == room.id for e in game.enemies)
        limit_reached = room.spawned_count >= RAID_ENEMY_LIMIT
        if (room.time_left <= 0 or limit_reached) and not alive:
            room.status = RoomStatus.CLEARED
            game.notice.clear()
            game.story.say(f'raid_ready:{room.id}:{len(game.story.events)}', RAID_READY)
            return
        game.notice.show(f'RAID {room.id+1}: {room.time_left:.0f}s '
                         f'| {room.spawned_count}/{RAID_ENEMY_LIMIT} spawned', 0.2)

    def _spawn_enemy(self, room):
        rng = self.game.rng
        pos = rng.choice(room.spawn_points())
        self.game.enemies.append(Enemy.raider(pos.copy(), room))
        room.spawned_count += 1
        room.spawn_timer = RAID_SPAWN_INTERVAL * rng.uniform(0.65, 1.35)
