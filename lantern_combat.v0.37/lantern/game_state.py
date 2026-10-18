from dataclasses import dataclass

from .config import ENDING_DURATION
from .easing import smooth


class Phase:
    EXPLORE = 'explore'
    BOSS = 'boss'
    CINEMATIC = 'cinematic'
    EPILOGUE = 'epilogue'


class GameState:
    PLAYING = 'playing'
    LOSE = 'lose'
    WIN = 'win'


class Notice:

    def __init__(self):
        self.text = ''
        self.timer = 0.0

    def show(self, text, seconds):
        self.text = text
        self.timer = seconds

    def clear(self):
        self.timer = 0.0

    def tick(self, dt):
        self.timer = max(0, self.timer-dt)

    @property
    def visible(self):
        return self.timer > 0


@dataclass
class EndingSequence:
    origin: object = None
    time: float = 0.0

    def begin(self, origin):
        self.origin = origin
        self.time = 0.0

    def radius(self, world_size):
        if self.origin is None:
            return 0
        width, height = world_size
        farthest = max(self.origin.distance_to(c) for c in
                       ((0, 0), (width, 0), (0, height), (width, height)))
        progress = max(0.0, min(1, (self.time-4)/(ENDING_DURATION-4)))
        return (farthest+80)*smooth(progress)
