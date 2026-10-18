import math

import pygame

from ..config import BOSS_HP, FLAME_RANGE, NO_BUTTON, SCREEN_H, SCREEN_W, YES_BUTTON
from ..game_state import GameState, Phase
from .fonts import korean_font

TEXT_GOLD = (255, 235, 170)
BOSS_PATTERN_HINTS = {'pulse': 'LIGHTNING PULSE', 'target': 'TARGET BOLT - 0.5s',
                      'dash': 'DASH - Leave the path!', 'storm': 'LIGHTNING STORM'}


class HudRenderer:
    def __init__(self, font, big_font):
        self.font = font
        self.big_font = big_font

    def draw(self, screen, game, music=None):
        if game.story.blocking or game.paused:
            return
        if game.phase in (Phase.CINEMATIC, Phase.EPILOGUE):
            self._draw_victory_panel(screen, game, music)
            return
        self._draw_stats(screen, game, music)
        self._draw_objective(screen, game)
        if game.boss_fight.boss:
            self._draw_boss_bar(screen, game.boss_fight.boss)
        if game.notice.visible and not game.story.messages:
            text = self.font.render(game.notice.text, True, (255, 235, 160))
            screen.blit(text, text.get_rect(center=(SCREEN_W//2, SCREEN_H-25)))
        if game.raid.exit_dialog:
            self._draw_exit_dialog(screen, game)
        if game.state != GameState.PLAYING:
            self._draw_game_over(screen, game)

    def _draw_victory_panel(self, screen, game, music):
        font = self.font
        lines = ['VICTORY - The world returns to light...'] if game.phase == Phase.CINEMATIC else [
            'VICTORY - Free exploration (ghost)',
            'WASD: Fly   Wheel: Zoom   Right drag: Camera   F: Follow',
            f'Zoom {game.camera.zoom:.2f}x   M: Music   R: New game   ESC: Pause']
        panel = pygame.Surface((SCREEN_W, 32*len(lines)+12), pygame.SRCALPHA)
        panel.fill((10, 15, 25, 210))
        screen.blit(panel, (0, 0))
        for i, line in enumerate(lines):
            screen.blit(font.render(line, True, TEXT_GOLD), (14, 10+32*i))
        if music:
            text = font.render(music.status, True, (210, 225, 245))
            screen.blit(text, text.get_rect(topright=(SCREEN_W-15, 10)))

    def _draw_stats(self, screen, game, music):
        font, player = self.font, game.player
        pygame.draw.rect(screen, (40, 42, 52), (15, 15, 220, 24))
        pygame.draw.rect(screen, (75, 200, 120), (15, 15, 220*player.hp/player.max_hp, 24))
        screen.blit(font.render(f'HP {player.hp}/{player.max_hp}', True, 'white'), (22, 17))
        screen.blit(font.render(f'ATK {player.damage}   Sight: {int(player.vision)}   Flame range: {int(FLAME_RANGE)}', True, 'white'), (250, 18))
        screen.blit(font.render('WASD: Move   Space / LMB: Flame   E: Escape   M: Music   R: Restart', True, 'white'), (15, 48))
        if music:
            text = font.render(music.status, True, (210, 225, 245) if music.available else (180, 180, 180))
            screen.blit(text, text.get_rect(topright=(SCREEN_W-15, 18)))

    def _draw_objective(self, screen, game):
        font, world, player = self.font, game.world, game.player
        active = game.raid.active_room
        raid_left = sum(e.hp > 0 and e.room == game.raid.active_room_id for e in game.enemies)
        status = (f'Room {active.id+1}: {active.time_left:.0f}s - '
                  f'{raid_left} enemies') if active else 'Find a raid room'
        screen.blit(font.render(f'GOALS {len(game.lit_goals)}/3   {status}', True, (235, 210, 135)), (15, 74))
        remaining = [world.center(c) for c in world.goals if c not in game.lit_goals]
        alive = [e.pos for e in game.enemies if e.hp > 0 and game.enemy_ai.is_active(e)]
        if active:
            choices = alive if alive else [world.center(active.goal)]
        else:
            choices = remaining
        boss = game.boss_fight.boss
        target_name = 'BOSS' if boss else ('Raid' if active and alive else 'GOAL')
        target = boss.pos if boss else (min(choices, key=player.pos.distance_to) if choices else None)
        if target is None:
            return
        delta = target-player.pos
        distance = int(delta.length())
        screen.blit(font.render(f'{target_name}: {distance}px', True, (240, 210, 140)), (15, 100))
        if delta.length_squared():
            direction = delta.normalize()
            origin = pygame.Vector2(218, 109)
            tip = origin+direction*15
            side = pygame.Vector2(-direction.y, direction.x)
            pygame.draw.line(screen, (255, 215, 90), origin-direction*12, tip, 3)
            pygame.draw.polygon(screen, (255, 215, 90), [tip, tip-direction*9+side*5, tip-direction*9-side*5])

    @staticmethod
    def _draw_boss_bar(screen, boss):
        bar_w = min(600, SCREEN_W-240)
        bar_x = (SCREEN_W-bar_w)//2
        bar_y = SCREEN_H-70
        pygame.draw.rect(screen, (55, 25, 60), (bar_x, bar_y, bar_w, 18))
        pygame.draw.rect(screen, (185, 70, 200), (bar_x, bar_y, bar_w*boss.hp/BOSS_HP, 18))
        hint = BOSS_PATTERN_HINTS.get(boss.attack_kind, 'Dodge the purple markers!')
        text = korean_font(20).render(f'먹구름 {boss.hp:.0f}/{BOSS_HP} - {hint}', True, 'white')
        screen.blit(text, text.get_rect(center=(SCREEN_W//2, bar_y-17)))

    def _draw_exit_dialog(self, screen, game):
        font = self.font
        shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 205))
        screen.blit(shade, (0, 0))
        dialog_w, dialog_h = min(650, SCREEN_W-80), 225
        dialog_x, dialog_y = (SCREEN_W-dialog_w)//2, (SCREEN_H-dialog_h)//2
        pygame.draw.rect(screen, (35, 40, 55), (dialog_x, dialog_y, dialog_w, dialog_h), border_radius=14)
        hp = game.player.hp
        lines = ['Escape this raid?', f'Lose 50% current HP: {hp} -> {max(1, math.ceil(hp/2))}',
                 'Raid progress resets. Everything is PAUSED.']
        for i, line in enumerate(lines):
            text = font.render(line, True, (255, 230, 180))
            screen.blit(text, text.get_rect(center=(SCREEN_W//2, dialog_y+35+i*34)))
        for rect, caption, color in ((YES_BUTTON, 'YES [Y]', (150, 65, 65)), (NO_BUTTON, 'NO [N / ESC]', (55, 100, 110))):
            pygame.draw.rect(screen, color, rect, border_radius=8)
            text = font.render(caption, True, 'white')
            screen.blit(text, text.get_rect(center=rect.center))

    def _draw_game_over(self, screen, game):
        shade = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 185))
        screen.blit(shade, (0, 0))
        won = game.state == GameState.WIN
        title = self.big_font.render('VICTORY!' if won else 'GAME OVER', True,
                                     (255, 222, 100) if won else (255, 95, 100))
        screen.blit(title, title.get_rect(center=(SCREEN_W//2, SCREEN_H//2-25)))
        hint = self.font.render('M: Music     R: Restart     ESC: Quit', True, 'white')
        screen.blit(hint, hint.get_rect(center=(SCREEN_W//2, SCREEN_H//2+35)))
