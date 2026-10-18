from dataclasses import dataclass
from pathlib import Path

import pygame

from .config import BGM_SAMPLE_RATE, BGM_VOLUME, HIT_SFX_VOLUME, SFX_VOLUME, THEME_NAMES, THEME_REGION_TILES
from .game_state import Phase


def ensure_mixer():
    if not pygame.mixer.get_init():
        pygame.mixer.init(frequency=BGM_SAMPLE_RATE, size=-16, channels=2, buffer=512)


def music_theme_for(game):
    if game.phase == Phase.BOSS:
        return 'boss'
    if game.phase in (Phase.CINEMATIC, Phase.EPILOGUE):
        return None
    if game.raid.active_room is not None:
        return game.raid.active_room.theme
    world, pos = game.world, game.player.pos
    nearest = min(world.rooms, key=lambda r: pos.distance_to(world.center(r.goal)))
    if pos.distance_to(world.center(nearest.goal)) <= world.tile * THEME_REGION_TILES:
        return nearest.theme
    return None


class ThemeBGM:
    def __init__(self, audio_dir, volume=BGM_VOLUME):
        self.audio_dir = Path(audio_dir)
        self.volume = volume
        self.available = False
        self.muted = False
        self.current_theme = None
        self.water_sounds = []
        self.water_channels = []
        self.track_paths = {
            'earth': self.audio_dir / 'earth.mp3',
            'sky': self.audio_dir / 'sky.mp3',
            'boss': self.audio_dir / 'boss.wav',
        }
        try:
            ensure_mixer()
            self.water_sounds = [
                pygame.mixer.Sound(str(path))
                for path in sorted((self.audio_dir / 'water_music').glob('*.wav'))
            ]
            self.available = any(path.exists() for path in self.track_paths.values()) or bool(self.water_sounds)
        except pygame.error as exc:
            print(f'BGM unavailable: {exc}')

    @property
    def _current_volume(self):
        return 0.0 if self.muted else self.volume

    @property
    def status(self):
        if not self.available:
            return 'NO AUDIO'
        if self.muted:
            return 'MUSIC OFF'
        if self.current_theme:
            return f'{THEME_NAMES.get(self.current_theme, self.current_theme).upper()} MUSIC'
        return 'MUSIC ON'

    def toggle(self):
        if not self.available:
            return None
        self.muted = not self.muted
        pygame.mixer.music.set_volume(self._current_volume)
        for channel in self.water_channels:
            channel.set_volume(self._current_volume)
        return not self.muted

    def update(self, theme):
        if not self.available or theme == self.current_theme:
            return
        self.current_theme = theme
        pygame.mixer.music.fadeout(500)
        for channel in self.water_channels:
            channel.fadeout(500)
        self.water_channels = []
        if theme == 'water':
            self._play_water()
        elif theme in self.track_paths:
            self._play_track(self.track_paths[theme])

    def _play_track(self, path):
        if not path.exists():
            return
        try:
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.set_volume(self._current_volume)
            pygame.mixer.music.play(loops=-1, fade_ms=700)
        except pygame.error as exc:
            print(f'BGM track unavailable: {path.name}: {exc}')

    def _play_water(self):
        for sound in self.water_sounds:
            channel = sound.play(loops=-1, fade_ms=700)
            if channel:
                channel.set_volume(self._current_volume)
                self.water_channels.append(channel)

    def stop(self):
        pygame.mixer.music.fadeout(400)
        for channel in self.water_channels:
            channel.fadeout(400)


class SoundEffect:

    def __init__(self, path, volume, name='SFX'):
        self.available = False
        self.volume = volume
        self.sound = None
        path = Path(path)
        try:
            ensure_mixer()
            if path.exists():
                self.sound = pygame.mixer.Sound(str(path))
                self.sound.set_volume(self.volume)
                self.available = True
        except pygame.error as exc:
            print(f'{name} unavailable: {exc}')

    def play(self):
        if self.available:
            self.sound.play()


class Silent:
    available = False

    def play(self):
        pass


@dataclass
class SoundBoard:
    attack: object = Silent()
    hit: object = Silent()

    @classmethod
    def load(cls, audio_dir):
        audio_dir = Path(audio_dir)
        return cls(attack=SoundEffect(audio_dir / 'attack.wav', SFX_VOLUME, 'Attack SFX'),
                   hit=SoundEffect(audio_dir / 'hit.wav', HIT_SFX_VOLUME, 'Hit SFX'))
