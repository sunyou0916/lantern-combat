from dataclasses import dataclass

import pygame

from .config import NO_BUTTON, YES_BUTTON
from .game_state import Phase


@dataclass
class FrameCommands:
    running: bool = True
    attack_pressed: bool = False
    skip_update: bool = False


def _key(event, key):
    return event.type == pygame.KEYDOWN and event.key == key


class InputController:
    def __init__(self, game, music):
        self.game = game
        self.music = music

    def poll(self):
        commands = FrameCommands()
        for event in pygame.event.get():
            self._handle(event, commands)
        return commands

    def held_controls(self, attack_pressed):
        keys = pygame.key.get_pressed()
        direction = pygame.Vector2(
            int(keys[pygame.K_d] or keys[pygame.K_RIGHT])-int(keys[pygame.K_a] or keys[pygame.K_LEFT]),
            int(keys[pygame.K_s] or keys[pygame.K_DOWN])-int(keys[pygame.K_w] or keys[pygame.K_UP]))
        attacking = attack_pressed or keys[pygame.K_SPACE] or pygame.mouse.get_pressed()[0]
        if self.game.input_guard and keys[pygame.K_e]:
            direction = pygame.Vector2()
            attacking = True
        return direction, attacking

    def _handle(self, event, commands):
        game = self.game
        if event.type == pygame.QUIT:
            commands.running = False
        elif _key(event, pygame.K_r):
            game.reset()
            commands.skip_update = True
        elif _key(event, pygame.K_ESCAPE) and not game.raid.exit_dialog:
            game.paused = not game.paused
            commands.skip_update = True
        elif _key(event, pygame.K_RETURN) and game.story.blocking and not commands.skip_update:
            game.story.skip()
            commands.skip_update = True
        elif game.story.blocking or game.paused:
            return
        elif game.raid.exit_dialog:
            self._handle_exit_dialog(event, commands)
        elif commands.skip_update:
            return
        elif game.phase == Phase.EPILOGUE and event.type == pygame.MOUSEWHEEL:
            game.camera.zoom_by(event.y)
        elif game.phase == Phase.EPILOGUE and event.type == pygame.MOUSEMOTION and event.buttons[2]:
            game.camera.pan(event.rel, game.player.pos, game.world.size)
        elif event.type == pygame.KEYDOWN:
            self._handle_key(event, commands)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            commands.attack_pressed = True

    def _handle_exit_dialog(self, event, commands):
        raid = self.game.raid
        answer = None
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_y:
                answer = True
            elif event.key in (pygame.K_n, pygame.K_ESCAPE):
                answer = False
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if YES_BUTTON.collidepoint(event.pos):
                answer = True
            elif NO_BUTTON.collidepoint(event.pos):
                answer = False
        if answer is not None:
            raid.answer_exit(answer)
            commands.skip_update = True

    def _handle_key(self, event, commands):
        game = self.game
        if event.key == pygame.K_f and game.phase == Phase.EPILOGUE:
            game.camera.follow_target(game.player.pos)
        elif event.key == pygame.K_m:
            music_on = self.music.toggle()
            game.notice.show('Music unavailable on this audio device.' if music_on is None else (
                'Background music on.' if music_on else 'Background music off.'), 2.0)
            commands.skip_update = True
        elif event.key == pygame.K_e:
            game.raid.request_exit()
            commands.skip_update = True
        elif event.key == pygame.K_SPACE:
            commands.attack_pressed = True
