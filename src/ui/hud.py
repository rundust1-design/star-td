"""
HUD — 游戏信息栏（底部）
"""
import pygame
from src.core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT,
    COLOR_HUD_BG, COLOR_WHITE, COLOR_YELLOW, COLOR_GREEN,
    COLOR_GOLD, COLOR_RED, COLOR_DARK,
    RACE_CONFIG, make_font
)


class HUD:
    """底部信息栏"""

    def __init__(self):
        self.y = SCREEN_HEIGHT - HUD_HEIGHT
        self.tower_menu_active = False

        # 右侧三个按钮（缩小尺寸）
        btn_w, btn_h = 150, 28
        right_x = SCREEN_WIDTH - btn_w - 10
        self.start_wave_rect = pygame.Rect(
            right_x, self.y + 12, btn_w, btn_h
        )
        self.pause_rect = pygame.Rect(
            right_x, self.y + 44, btn_w, btn_h
        )
        self.settings_rect = pygame.Rect(
            right_x, self.y + 76, btn_w, btn_h
        )

        # 离开游戏按钮（中间波次下方）
        self.quit_rect = pygame.Rect(
            SCREEN_WIDTH // 2 - 60, self.y + 76, 120, 24
        )

        self.font_large = make_font(30)
        self.font_medium = make_font(22)
        self.font_small = make_font(18)
        self.font_tiny = make_font(14)
        self.font_button = make_font(14)  # 右侧按钮专用小字体

    def check_button_click(self, pos) -> str | None:
        """检测按钮点击，返回按钮标识"""
        if self.start_wave_rect.collidepoint(pos):
            return "start_wave"
        if self.pause_rect.collidepoint(pos):
            return "toggle_pause"
        if self.settings_rect.collidepoint(pos):
            return "settings"
        if self.quit_rect.collidepoint(pos):
            return "quit"
        return None

    def draw(self, surface: pygame.Surface, economy, wave_manager, game_state: str,
             selected_tower=None, lives: int = 20, player_race: str = "terran",
             enemy_race: str = "zerg", difficulty: str = "normal",
             paused: bool = False):
        """绘制 HUD"""
        # HUD 背景
        pygame.draw.rect(surface, COLOR_HUD_BG,
                         (0, self.y, SCREEN_WIDTH, HUD_HEIGHT))
        pygame.draw.line(surface, (68, 68, 102),
                         (0, self.y), (SCREEN_WIDTH, self.y), 2)

        race_cfg = RACE_CONFIG.get(player_race, RACE_CONFIG["terran"])

        # ── 左侧：种族 + 金钱 ──
        cx, cy = 20, self.y + 8
        # 种族名
        race_label = self.font_tiny.render(race_cfg["name"], True, race_cfg["color_light"])
        surface.blit(race_label, (cx, cy))

        money_text = self.font_large.render(f"${economy.money}", True, COLOR_GOLD)
        surface.blit(money_text, (cx, cy + 15))

        # ── 敌人信息 ──
        race_name_map = {"terran": "人族", "protoss": "神族", "zerg": "虫族", "random": "随机"}
        diff_name_map = {"easy": "简单", "normal": "普通", "hard": "困难", "insane": "疯狂"}
        enemy_text = self.font_tiny.render(
            f"敌人: {race_name_map.get(enemy_race, enemy_race)} / {diff_name_map.get(difficulty, difficulty)}",
            True, (170, 170, 200)
        )
        surface.blit(enemy_text, (cx, cy + 50))

        # ── 生命 ──
        lives_text = self.font_medium.render(f"生命: {lives}", True, COLOR_RED)
        surface.blit(lives_text, (cx, cy + 68))

        # ── 中间：波次信息 ──
        wave_text = self.font_large.render(
            f"波次 {wave_manager.get_current_wave_number()} / {wave_manager.get_total_waves()}",
            True, COLOR_WHITE
        )
        wave_rect = wave_text.get_rect(center=(SCREEN_WIDTH // 2, self.y + 30))
        surface.blit(wave_text, wave_rect)

        # 波次状态
        if wave_manager.wave_in_progress:
            status_str = f"战斗中 · 剩余 {wave_manager.get_active_enemy_count()} 个敌人"
            status_color = COLOR_YELLOW
        elif wave_manager.all_waves_complete:
            status_str = "所有波次已完成！"
            status_color = COLOR_GREEN
        else:
            status_str = "准备就绪"
            status_color = COLOR_WHITE

        status_text = self.font_small.render(status_str, True, status_color)
        status_rect = status_text.get_rect(center=(SCREEN_WIDTH // 2, self.y + 58))
        surface.blit(status_text, status_rect)

        # ── 右侧：选中塔信息 ──
        if selected_tower:
            rx = SCREEN_WIDTH - 180
            name_text = self.font_medium.render(selected_tower.name, True, COLOR_WHITE)
            surface.blit(name_text, (rx, self.y + 18))

            info = selected_tower.debug_info()
            info_text = self.font_small.render(info, True, (187, 187, 187))
            surface.blit(info_text, (rx, self.y + 40))

            sell_text = self.font_small.render(
                f"售价: ${selected_tower.sell_value()}", True, COLOR_GREEN
            )
            surface.blit(sell_text, (rx, self.y + 60))

        # ── 右侧三个小按钮 ──
        # 开始下一波
        if not wave_manager.wave_in_progress and not wave_manager.all_waves_complete:
            self._draw_small_button(surface, self.start_wave_rect, "▶ 开始下一波", COLOR_GREEN)

        # 继续/暂停
        pause_label = "▶ 继续" if paused else "⏸ 暂停"
        pause_color = COLOR_GREEN if paused else (170, 170, 200)
        self._draw_small_button(surface, self.pause_rect, pause_label, pause_color)

        # 设置
        self._draw_small_button(surface, self.settings_rect, "⚙ 设置", (140, 140, 200))

        # ── 中间波次下方：离开游戏按钮 ──
        self._draw_small_button(surface, self.quit_rect, "离开游戏", COLOR_RED)

    def _draw_button(self, surface: pygame.Surface, rect: pygame.Rect,
                     text: str, color):
        """绘制 HUD 按钮"""
        pygame.draw.rect(surface, color, rect)
        pygame.draw.rect(surface, COLOR_WHITE, rect, 1)

        txt_surf = self.font_small.render(text, True, COLOR_WHITE)
        txt_rect = txt_surf.get_rect(center=rect.center)
        surface.blit(txt_surf, txt_rect)

    def _draw_small_button(self, surface: pygame.Surface, rect: pygame.Rect,
                           text: str, color):
        """绘制小型 HUD 按钮（右侧和中间小按钮用）"""
        pygame.draw.rect(surface, color, rect)
        pygame.draw.rect(surface, COLOR_WHITE, rect, 1)

        txt_surf = self.font_button.render(text, True, COLOR_WHITE)
        txt_rect = txt_surf.get_rect(center=rect.center)
        surface.blit(txt_surf, txt_rect)
