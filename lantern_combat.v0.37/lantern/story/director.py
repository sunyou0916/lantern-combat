import math
import random
from collections import deque
from dataclasses import dataclass, field

import pygame

from ..config import PURIFICATION_SECONDS, TOWER_LIGHT_DELAY
from ..easing import envelope, smooth
from ..game_state import GameState, Phase
from ..world.room import RoomStatus
from .script import CAPTION_PAGES, DURATIONS, REGIONS, TOWER_CAPTION_TIME, TOWERS

REGION_BANNER_SECONDS = 3.5
MESSAGE_SECONDS = 4.0


@dataclass(frozen=True)
class LightParticle:
    start: tuple
    control: tuple
    end: tuple
    birth: float
    lifetime: float
    radius: int

    def sample(self, t):
        u = (t-self.birth)/self.lifetime
        if not -1e-9 <= u <= 1+1e-9:
            return None
        u = max(0.0, min(1.0, u))
        a, b, c = map(pygame.Vector2, (self.start, self.control, self.end))
        return a*(1-u)**2+b*2*u*(1-u)+c*u*u, 225*envelope(u, 0, 1, 0.18)


@dataclass
class Scene:
    kind: str
    context: dict = field(default_factory=dict)
    elapsed: float = 0.0
    committed: bool = False
    particles: tuple = ()

    @property
    def duration(self):
        return DURATIONS[self.kind]


class StoryDirector:
    def __init__(self, game):
        self.game = game
        self.active = None
        self.clock = 0.0
        self.seen_regions = set()
        self.region_banner = None
        self.region_time = 0.0
        self.messages = deque()
        self.message_time = 0.0
        self.once = set()
        self.events = []
        self.environment = {}
        world = game.world
        for theme, seed, count in (('water', 2017, 24), ('sky', 3023, 30)):
            cells = sorted(cell for cell in world.walkable if world.theme_for_cell(cell) == theme)
            rng = random.Random(seed)
            self.environment[theme] = tuple((rng.choice(cells), rng.random()*math.tau,
                                             rng.uniform(0.6, 1.2)) for _ in range(count)) if cells else ()

    @property
    def blocking(self):
        return self.active is not None

    def start(self, kind, **context):
        if self.active is not None:
            raise RuntimeError('A story scene is already playing')
        game = self.game
        focus, zoom = self.view()
        context.update(start_focus=focus.copy(), start_zoom=zoom)
        self.active = Scene(kind, context)
        self.active.particles = self._make_particles(kind, context)
        self.messages.clear()
        self.message_time = 0.0
        self.region_banner = None
        self.events.append((kind, dict(context)))
        game.player.moving = False
        game.input_guard = True

    def _make_particles(self, kind, context):
        world = self.game.world
        start = self.game.player.pos+(-8, -14)
        targets = []
        if kind == 'tower':
            targets = [world.center(world.rooms[context['room_id']].goal)+(0, -48)]
        elif kind == 'ending':
            targets = [world.center(room.goal)+(0, -48) for room in world.rooms]
        particles = []
        for index, end in enumerate(targets):
            delta = end-start
            side = pygame.Vector2(-delta.y, delta.x)
            if side.length_squared():
                side.scale_to_length(min(100, max(26, delta.length()*0.18)))
            for i in range(24):
                bend = side*(0.45+(i % 5)*0.14)*(-1 if i % 2 else 1)
                control = start.lerp(end, 0.5)+bend
                birth = 0.05+i*0.037 if kind == 'tower' else 1.0+i*0.055+index*0.06
                life = 0.85+(i % 4)*0.06 if kind == 'tower' else 1.5+(i % 4)*0.12
                particles.append(LightParticle(tuple(start), tuple(control), tuple(end), birth, life, 2+i % 2))
        return tuple(particles)

    def _commit(self):
        scene = self.active
        if scene and not scene.committed:
            scene.committed = True
            if scene.kind == 'tower':
                self.game.progression.complete_tower_light(scene.context['room_id'])

    def finish(self):
        scene = self.active
        if scene is None:
            return
        game = self.game
        scene.elapsed = scene.duration
        focus, zoom = self.view()
        game.camera.pos = focus.copy()
        game.camera.zoom = zoom
        self._commit()
        self.active = None
        game.input_guard = True
        game.player.attack_buffer = 0.0
        game.progression.on_story_finished(scene.kind, scene.context)

    def skip(self):
        if not self.game.paused and self.blocking:
            if self.active.kind == 'tower':
                room = self.game.world.rooms[self.active.context['room_id']]
                room.purification = max(room.purification,
                                        (self.active.duration-TOWER_LIGHT_DELAY)/PURIFICATION_SECONDS)
            self.finish()

    def enter_region(self, theme):
        if theme in self.seen_regions:
            return
        self.seen_regions.add(theme)
        self.region_banner = REGIONS[theme]
        self.region_time = 0.0
        self.events.append(('region', {'theme': theme}))

    def say(self, key, lines, duration=MESSAGE_SECONDS):
        if key in self.once:
            return
        self.once.add(key)
        if isinstance(lines, str):
            lines = (lines,)
        self.messages.append((tuple(lines), duration, key))
        self.events.append((key, {}))

    def update(self, dt):
        game = self.game
        if game.paused or game.raid.exit_dialog or game.state != GameState.PLAYING:
            return
        self.clock += dt
        if self.active:
            scene = self.active
            scene.elapsed = min(scene.duration, scene.elapsed+dt)
            if scene.kind == 'ending':
                game.ending.time = scene.elapsed
            if scene.elapsed >= scene.duration-1e-9:
                self.finish()
            return
        if self.region_banner:
            self.region_time += dt
            if self.region_time >= REGION_BANNER_SECONDS:
                self.region_banner = None
        if self.messages:
            self.message_time += dt
            if self.message_time >= self.messages[0][1]:
                self.messages.popleft()
                self.message_time = 0.0

    def caption(self):
        scene = self.active
        if not scene:
            if self.messages:
                lines, duration, _ = self.messages[0]
                return lines, envelope(self.message_time, 0, duration)
            return (), 0.0
        t = scene.elapsed
        if scene.kind == 'tower':
            pages = [(*TOWER_CAPTION_TIME, (TOWERS[scene.context['theme']],))]
        else:
            pages = CAPTION_PAGES.get(scene.kind, [])
        for start, end, lines in pages:
            if start <= t < end:
                return lines, envelope(t, start, end)
        return (), 0.0

    def text(self):
        return self.caption()[0]

    def view(self):
        game, scene = self.game, self.active
        if not scene:
            if game.phase == Phase.EPILOGUE:
                return game.camera.pos, game.camera.zoom
            return game.player.pos, 1.0
        t, context = scene.elapsed, scene.context
        start, zoom = context['start_focus'], context['start_zoom']
        player_pos = game.player.pos
        if scene.kind == 'boss_arrival':
            center = game.boss_fight.boss.pos
            if t < 1.5:
                a = smooth(t/1.5)
                return start.lerp(center, a), zoom+(0.94-zoom)*a
            a = smooth((t-3.0)/1.8)
            return center.lerp(player_pos, a), 0.94+0.06*a
        if scene.kind == 'ending':
            center = game.ending.origin
            if t < 7.1:
                a = smooth(t/2.0)
                return start.lerp(center, a), zoom+(0.94-zoom)*a
            a = smooth((t-7.1)/2.4)
            return center.lerp(player_pos, a), 0.94+0.06*a
        a = smooth(t/scene.duration)
        return start.lerp(player_pos, a), zoom+(1.0-zoom)*a

    def tower_amount(self, room):
        scene = self.active
        if scene and scene.kind == 'tower' and room.id == scene.context['room_id']:
            return smooth((scene.elapsed-0.75)/1.75)
        if room.status == RoomStatus.COMPLETED:
            if scene and scene.kind == 'ending':
                return 1.0+0.4*smooth((scene.elapsed-3.0)/2.0)
            return 1.4 if self.game.phase == Phase.EPILOGUE else 1.0
        return 0.0

    def ghost_amount(self):
        if self.game.phase == Phase.EPILOGUE:
            return 1.0
        if self.active and self.active.kind == 'ending':
            return smooth((self.active.elapsed-7.0)/2.2)
        return 0.0

    def flame_amount(self):
        if self.game.phase == Phase.EPILOGUE:
            return 0.0
        if self.active and self.active.kind == 'ending':
            return 1-smooth((self.active.elapsed-5.0)/2.2)
        return 1.0

    def player_opacity(self):
        return round(255-145*self.ghost_amount())

    def boss_opacity(self):
        if self.active and self.active.kind == 'boss_arrival':
            return round(255*smooth((self.active.elapsed-0.6)/1.8))
        if self.active and self.active.kind == 'ending':
            return round(255*(1-smooth(self.active.elapsed/5.5)))
        return 255

    def visual_vision(self):
        scene = self.active
        if scene and scene.kind == 'tower':
            return scene.context['previous_vision']*(1-0.30*smooth((scene.elapsed-0.65)/2.0))
        return self.game.player.vision

    def fog_strength(self):
        scene = self.active
        if scene and scene.kind == 'tower' and scene.context['ordinal'] == 1:
            return smooth((scene.elapsed-0.65)/2.0)
        return float(self.game.fog_enabled)
