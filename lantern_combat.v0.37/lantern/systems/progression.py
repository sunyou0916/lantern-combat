from ..config import ENDING_DURATION, INITIAL_VISION_RADIUS, STAGES, TOWER_LIGHT_DELAY, VISION_DECAY
from ..entities.boss import BossAnim
from ..game_state import Phase
from ..story.script import GHOST_START, OBJECTIVE
from ..world.room import RoomStatus

TOWER_INVINCIBILITY = 1.0


class Progression:
    def __init__(self, game):
        self.game = game

    def check_goal_contact(self):
        game = self.game
        for cell in game.world.goals:
            if game.player.rect.colliderect(game.world.goal_rect(cell)):
                self.visit_goal(cell)
                if game.story.blocking:
                    return True
        return False

    def visit_goal(self, cell):
        game = self.game
        if game.story.blocking:
            return
        room = game.world.room_for_goal(cell)
        if room is None or room.status != RoomStatus.CLEARED or game.raid.active_room_id != room.id:
            return
        if cell in game.lit_goals:
            return
        room.status = RoomStatus.LIGHTING
        game.story.start('tower', room_id=room.id, theme=room.theme,
                         ordinal=len(game.lit_goals)+1, previous_vision=game.player.vision)

    def complete_tower_light(self, room_id):
        game, player = self.game, self.game.player
        room = game.world.rooms[room_id]
        cell = room.goal
        if cell in game.lit_goals:
            return
        room.status = RoomStatus.COMPLETED
        game.raid.active_room_id = None
        game.lit_goals.add(cell)
        game.enemies = [enemy for enemy in game.enemies if enemy.theme != room.theme]
        player.apply_stage(min(len(game.lit_goals), len(STAGES)-1))
        game.fog_enabled = True
        player.vision = max(1.0, INITIAL_VISION_RADIUS * (VISION_DECAY ** len(game.lit_goals)))
        player.hp = player.max_hp
        player.hurt_timer = TOWER_INVINCIBILITY
        game.notice.clear()

    def update_purification(self, dt):
        scene = self.game.story.active
        for room in self.game.world.rooms:
            if room.status == RoomStatus.COMPLETED:
                room.purify(dt)
            elif room.status == RoomStatus.LIGHTING:
                if scene and scene.kind == 'tower' and scene.context['room_id'] == room.id:
                    before, after = scene.elapsed, min(scene.duration, scene.elapsed+dt)
                    lit_dt = max(0.0, after-TOWER_LIGHT_DELAY)-max(0.0, before-TOWER_LIGHT_DELAY)
                    room.purify(lit_dt)

    def on_boss_defeated(self):
        game = self.game
        boss = game.boss_fight.boss
        frame_time = boss.animation_time()
        boss_loop = boss.anim_state != BossAnim.ATTACK
        game.phase = Phase.CINEMATIC
        game.ending.begin(boss.pos.copy())
        game.boss_fight.cancel_attacks()
        game.combat.flames.clear()
        game.player.moving = False
        game.raid.exit_dialog = False
        game.story.start('ending', boss_frame_time=frame_time, boss_loop=boss_loop)

    def on_story_finished(self, kind, context):
        game = self.game
        if kind == 'intro':
            game.story.say('objective', OBJECTIVE)
        elif kind == 'tower' and len(game.lit_goals) == len(game.world.goals) and game.boss_fight.boss is None:
            game.phase = Phase.BOSS
            game.boss_fight.spawn()
            game.story.start('boss_arrival')
        elif kind == 'boss_arrival':
            game.camera.pos = game.player.pos.copy()
            game.notice.clear()
        elif kind == 'ending':
            game.ending.time = ENDING_DURATION
            game.phase = Phase.EPILOGUE
            game.camera.follow_target(game.player.pos)
            game.camera.zoom = 1.0
            game.story.say('ghost_start', GHOST_START)
