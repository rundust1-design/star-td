"""
界面屏幕 — 种族选择（玩家+敌人）、地图选择、游戏结束、胜利画面
"""
import os
import math
import pygame
from src.core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, COLOR_DARK, COLOR_DARKER,
    COLOR_WHITE, COLOR_YELLOW, COLOR_RED, COLOR_GREEN, COLOR_GOLD, COLOR_GRAY,
    COLOR_TERRAN, COLOR_PROTOSS, COLOR_ZERG,
    RACE_CONFIG, make_font, ASSETS_DIR, TILESETS_DIR
)

# 敌人可选种族（含随机）
ENEMY_RACES = [
    {"key": "terran", "label": "人族 Terran", "color": COLOR_TERRAN, "icon": "⚔",
     "desc": "远程为主的均衡部队"},
    {"key": "protoss", "label": "神族 Protoss", "color": COLOR_PROTOSS, "icon": "✦",
     "desc": "高血量高伤害的精锐"},
    {"key": "zerg", "label": "虫族 Zerg", "color": COLOR_ZERG, "icon": "◆",
     "desc": "数量庞大的快速部队"},
    {"key": "random", "label": "随机 Random", "color": (180, 180, 180), "icon": "?",
     "desc": "每波随机一个种族"},
]
# 难度级别
DIFFICULTIES = [
    {"key": "easy", "label": "简单", "desc": "慢速生成，少量敌人", "color": COLOR_GREEN},
    {"key": "normal", "label": "普通", "desc": "标准生成速度", "color": COLOR_YELLOW},
    {"key": "hard", "label": "困难", "desc": "快速生成，大量敌人", "color": (255, 120, 50)},
    {"key": "insane", "label": "疯狂", "desc": "超快生成，海量敌人", "color": COLOR_RED},
]

# Tileset 名称映射
TILESET_NAMES = {
    0: "Badlands", 1: "Space", 2: "Installation", 3: "Ashworld",
    4: "Jungle", 5: "Desert", 6: "Arctic", 7: "Twilight", 8: "Ice",
    9: "Ice",  # fallback
}

# 程序化 tileset 颜色预览（用于选图界面的缩略图）
TILESET_PREVIEW_COLORS = {
    0: (88, 68, 40), 1: (50, 50, 60), 2: (60, 60, 65), 3: (70, 55, 45),
    4: (25, 58, 30), 5: (120, 88, 48), 6: (150, 155, 165), 7: (72, 48, 72),
    8: (160, 175, 190),
}


class ScreenManager:
    """管理各种全屏界面"""

    def __init__(self):
        self.active_screen = None
        self.wave_reached = 0
        self.sound_manager = None  # 由 game.py 设置

    def set_sound_manager(self, sm):
        self.sound_manager = sm

        self.font_title = make_font(60)
        self.font_subtitle = make_font(26)
        self.font_button = make_font(24)
        self.font_small = make_font(18)
        self.font_race_btn = make_font(28)
        self.font_tiny = make_font(14)

        # 按钮区域和回调（在 draw_* 时构建）
        self.buttons = []  # [(rect, callback), ...]
        self.race_buttons = []  # [(rect, race_key, callback), ...]
        self.enemy_race_buttons = []
        self.difficulty_buttons = []

        # 地图选择相关
        self.map_buttons = []  # [(rect, map_idx, map_dict), ...]
        self.map_scroll = 0
        self.map_list = []

        # 存储选择结果
        self._player_race = None
        self._on_player_race_selected = None
        self._on_enemy_config = None
        self._selected_enemy_race = None

    def clear(self):
        self.active_screen = None
        self.buttons.clear()
        self.race_buttons.clear()
        self.enemy_race_buttons.clear()
        self.difficulty_buttons.clear()
        self.map_buttons.clear()
        self.map_scroll = 0
        self.map_list = []
        # 清除缓存的卡片背景图
        for attr in list(self.__dict__):
            if attr.startswith('_ecard_') or attr.startswith('_card_'):
                delattr(self, attr)
        # 设置面板数据
        self._settings_on_close = None
        self._settings_sfx_slider = None  # pygame.Rect
        self._settings_music_slider = None
        self._settings_sfx_toggle = None
        self._settings_music_toggle = None
        self._settings_dragging = None  # "sfx" or "music"
        self._settings_render_cache = None  # 缓存的背景截图

    def draw_menu(self, on_start_game, on_quit):
        """绘制主菜单 — 直接开始选择玩家种族"""
        self.draw_race_select(on_start_game, on_quit)

    def draw_settings(self, on_close):
        """绘制设置面板（覆盖在当前屏幕上）"""
        self._settings_on_close = on_close
        self._settings_render_cache = None  # 下次渲染时捕获背景

        panel_w, panel_h = 380, 340
        panel_x = (SCREEN_WIDTH - panel_w) // 2
        panel_y = (SCREEN_HEIGHT - panel_h) // 2

        # 滑块区域
        slider_w = 200
        slider_h = 20
        slider_x = panel_x + 140
        self._settings_sfx_slider = pygame.Rect(slider_x, panel_y + 80, slider_w, slider_h)
        self._settings_music_slider = pygame.Rect(slider_x, panel_y + 150, slider_w, slider_h)

        # 开关区域（勾选框）
        self._settings_sfx_toggle = pygame.Rect(slider_x, panel_y + 115, 24, 24)
        self._settings_music_toggle = pygame.Rect(slider_x, panel_y + 185, 24, 24)

        # 关闭按钮
        close_btn = pygame.Rect(panel_x + panel_w // 2 - 80, panel_y + 260, 160, 45)
        self.buttons = [(close_btn, on_close)]

        self._settings_dragging = None

    def draw_race_select(self, on_race_selected, on_quit=None):
        """第一步：选择玩家种族"""
        self.clear()
        self.active_screen = "race_select"
        self._on_player_race_selected = on_race_selected

        # 三个种族按钮
        btn_w, btn_h = 220, 260
        races = ["terran", "protoss", "zerg"]
        total_w = len(races) * btn_w + (len(races) - 1) * 30
        start_x = (SCREEN_WIDTH - total_w) // 2

        self.race_buttons.clear()
        for i, race in enumerate(races):
            x = start_x + i * (btn_w + 30)
            y = SCREEN_HEIGHT // 2 - btn_h // 2 + 30
            rect = pygame.Rect(x, y, btn_w, btn_h)
            self.race_buttons.append((rect, race))

        # 底部退出按钮
        self.buttons = [
            (pygame.Rect(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 + 160, 200, 50),
             on_quit or (lambda: None)),
        ]

    def draw_enemy_select(self, player_race, on_enemy_config):
        """第二步：选择敌人种族和难度"""
        self.clear()
        self.active_screen = "enemy_select"
        self._player_race = player_race
        self._on_enemy_config = on_enemy_config

        # 敌人种族按钮（横向）
        btn_w, btn_h = 170, 200
        total_w = len(ENEMY_RACES) * btn_w + (len(ENEMY_RACES) - 1) * 20
        start_x = (SCREEN_WIDTH - total_w) // 2

        self.enemy_race_buttons.clear()
        for i, er in enumerate(ENEMY_RACES):
            x = start_x + i * (btn_w + 20)
            y = SCREEN_HEIGHT // 2 - btn_h - 20
            rect = pygame.Rect(x, y, btn_w, btn_h)
            self.enemy_race_buttons.append((rect, er))

        # 难度级别按钮（点击即传递配置，无需预先选种族）
        diff_w, diff_h = 150, 80
        total_dw = len(DIFFICULTIES) * diff_w + (len(DIFFICULTIES) - 1) * 30
        dx = (SCREEN_WIDTH - total_dw) // 2

        self.difficulty_buttons.clear()
        for i, dd in enumerate(DIFFICULTIES):
            x = dx + i * (diff_w + 30)
            y = SCREEN_HEIGHT // 2 + 30
            rect = pygame.Rect(x, y, diff_w, diff_h)
            self.difficulty_buttons.append((rect, dd))

        # 底部按钮（返回玩家选择）
        self.buttons = [
            (pygame.Rect(SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT - 100, 200, 50),
             lambda: self.draw_race_select(self._on_player_race_selected, None)),
        ]

    def draw_map_select(self, maps: list[dict], on_map_selected, on_back,
                         difficulty: str = ""):
        """第三步：选择地图"""
        self.clear()
        self.active_screen = "map_select"
        self.map_list = list(maps)
        self._on_map_selected = on_map_selected
        self.map_scroll = 0
        self.map_buttons.clear()
        self._map_select_difficulty = difficulty

        # 底部返回按钮
        self.buttons = [
            (pygame.Rect(20, SCREEN_HEIGHT - 50, 150, 36),
             on_back or (lambda: None)),
        ]

    def draw_game_over(self, wave_reached: int, on_restart, on_menu):
        """绘制游戏结束画面"""
        self.clear()
        self.active_screen = "game_over"
        self.wave_reached = wave_reached
        self.buttons = [
            (pygame.Rect(SCREEN_WIDTH // 2 - 210, SCREEN_HEIGHT // 2 + 40, 200, 50), on_restart),
            (pygame.Rect(SCREEN_WIDTH // 2 + 10, SCREEN_HEIGHT // 2 + 40, 200, 50), on_menu),
        ]

    def draw_victory(self, on_restart, on_menu):
        """绘制胜利画面"""
        self.clear()
        self.active_screen = "victory"
        self.buttons = [
            (pygame.Rect(SCREEN_WIDTH // 2 - 210, SCREEN_HEIGHT // 2 + 40, 200, 50), on_restart),
            (pygame.Rect(SCREEN_WIDTH // 2 + 10, SCREEN_HEIGHT // 2 + 40, 200, 50), on_menu),
        ]

    def _play_ui_click(self):
        """播放 UI 点击音效"""
        if self.sound_manager:
            self.sound_manager.play_ui("ui_click")

    def handle_click(self, pos) -> bool:
        """处理点击事件，返回是否消费"""
        # 玩家种族选择
        if self.active_screen == "race_select":
            for rect, race in self.race_buttons:
                if rect.collidepoint(pos):
                    self._play_ui_click()
                    self._on_player_race_selected(race)
                    return True

        # 敌人种族+难度选择
        if self.active_screen == "enemy_select":
            for rect, er in self.enemy_race_buttons:
                if rect.collidepoint(pos):
                    self._play_ui_click()
                    self._selected_enemy_race = er["key"]
                    return True
            for rect, dd in self.difficulty_buttons:
                if rect.collidepoint(pos):
                    self._play_ui_click()
                    race = getattr(self, '_selected_enemy_race', None) or "zerg"
                    self._on_enemy_config(race, dd["key"])
                    return True

        # 地图选择
        if self.active_screen == "map_select":
            # 地图卡片
            for rect, idx, md in self.map_buttons:
                if rect.collidepoint(pos):
                    self._play_ui_click()
                    self._on_map_selected(md["full_path"])
                    return True
            # 滚动
            if pos[0] >= SCREEN_WIDTH - 30:
                bar_area = pygame.Rect(SCREEN_WIDTH - 30, 60, 24, SCREEN_HEIGHT - 120)
                if bar_area.collidepoint(pos):
                    rel_y = pos[1] - bar_area.y
                    total_h = bar_area.h
                    content_h = self._calc_map_grid_height()
                    if content_h > bar_area.h:
                        self.map_scroll = int((rel_y / total_h) * max(0, content_h - bar_area.h))
                    return True

        # 通用按钮（退出、重新开始等）
        for rect, callback in self.buttons:
            if rect.collidepoint(pos):
                self._play_ui_click()
                callback()
                return True
        return False

    def _calc_map_grid_height(self) -> int:
        """计算地图选择网格的总高度（像素）"""
        cols = 2
        card_h = 120
        gap = 10
        rows = math.ceil(len(self.map_list) / cols)
        return rows * (card_h + gap)

    def handle_scroll(self, dy: int):
        """处理鼠标滚轮"""
        if self.active_screen == "map_select":
            max_scroll = max(0, self._calc_map_grid_height() - (SCREEN_HEIGHT - 140))
            self.map_scroll = max(0, min(max_scroll, self.map_scroll - dy * 20))

    def handle_hover(self, pos):
        """处理鼠标悬停（改变鼠标样式）"""
        if self.active_screen == "race_select":
            for rect, race in self.race_buttons:
                if rect.collidepoint(pos):
                    return True
        if self.active_screen == "enemy_select":
            for rect, er in self.enemy_race_buttons:
                if rect.collidepoint(pos):
                    return True
            for rect, dd in self.difficulty_buttons:
                if rect.collidepoint(pos):
                    return True
        if self.active_screen == "map_select":
            for rect, idx, md in self.map_buttons:
                if rect.collidepoint(pos):
                    return True
        for rect, _ in self.buttons:
            if rect.collidepoint(pos):
                return True
        return False

    def render(self, surface: pygame.Surface):
        """渲染当前屏幕"""
        if self.active_screen == "race_select":
            self._render_race_select(surface)
        elif self.active_screen == "enemy_select":
            self._render_enemy_select(surface)
        elif self.active_screen == "map_select":
            self._render_map_select(surface)
        elif self.active_screen == "game_over":
            self._render_game_over(surface)
        elif self.active_screen == "victory":
            self._render_victory(surface)

    def render_settings_overlay(self, surface: pygame.Surface):
        """渲染设置面板覆盖层（不在 active_screen 中，通过 game.py 独立调用）"""
        self._render_settings(surface)

    def _render_button(self, surface: pygame.Surface,
                       rect: pygame.Rect, text: str, color):
        """渲染按钮"""
        pygame.draw.rect(surface, color, rect)
        pygame.draw.rect(surface, COLOR_WHITE, rect, 2)
        txt_surf = self.font_button.render(text, True, COLOR_WHITE)
        txt_rect = txt_surf.get_rect(center=rect.center)
        surface.blit(txt_surf, txt_rect)

    # ════════════════════════════════════════════
    # 种族选择界面
    # ════════════════════════════════════════════

    def _load_bg_image(self, race_key: str, card_w: int = 220, card_h: int = 260):
        """加载种族背景图并缩放到卡片尺寸"""
        name_map = {"terran": "人族", "protoss": "神族", "zerg": "虫族"}
        filename = f"{name_map.get(race_key, race_key)}.png"
        path = os.path.join(ASSETS_DIR, "sprites", filename)
        try:
            img = pygame.image.load(path).convert_alpha()
            return pygame.transform.smoothscale(img, (card_w, card_h))
        except Exception:
            return None

    def _render_race_select(self, surface: pygame.Surface):
        surface.fill(COLOR_DARK)

        # 装饰线
        pygame.draw.line(surface, COLOR_GOLD, (100, 100), (SCREEN_WIDTH - 100, 100), 2)

        # 标题
        title = self.font_title.render("星际争霸 塔防", True, COLOR_GOLD)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 50))
        surface.blit(title, title_rect)

        subtitle = self.font_subtitle.render("选择你的种族", True, COLOR_WHITE)
        sub_rect = subtitle.get_rect(center=(SCREEN_WIDTH // 2, 90))
        surface.blit(subtitle, sub_rect)

        # 装饰线
        pygame.draw.line(surface, COLOR_GOLD, (100, 110), (SCREEN_WIDTH - 100, 110), 2)

        # 种族按钮
        self._render_race_cards(surface)

        # 退出按钮
        for rect, _ in self.buttons:
            self._render_button(surface, rect, "退出", COLOR_RED)

        # 底部信息
        info = self.font_tiny.render("基于星际争霸 1.08b 素材制作", True, (102, 102, 136))
        info_rect = info.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 40))
        surface.blit(info, info_rect)

    # ════════════════════════════════════════════
    # 敌人选择界面
    # ════════════════════════════════════════════

    def _render_enemy_select(self, surface: pygame.Surface):
        surface.fill(COLOR_DARK)

        # 顶部信息
        player_race_names = {"terran": "人族", "protoss": "神族", "zerg": "虫族"}
        race_name = player_race_names.get(self._player_race, "未知")
        header = self.font_subtitle.render(
            f"玩家: {race_name}     —     选择敌人配置", True, COLOR_GOLD
        )
        header_rect = header.get_rect(center=(SCREEN_WIDTH // 2, 50))
        surface.blit(header, header_rect)

        pygame.draw.line(surface, COLOR_GOLD, (100, 75), (SCREEN_WIDTH - 100, 75), 2)

        # 敌人种族提示
        race_label = self.font_small.render("选择敌人种族", True, COLOR_WHITE)
        race_label_rect = race_label.get_rect(center=(SCREEN_WIDTH // 2, 105))
        surface.blit(race_label, race_label_rect)

        # 敌人种族按钮
        self._render_enemy_race_cards(surface)

        # 难度提示
        diff_label = self.font_small.render("选择难度", True, COLOR_WHITE)
        diff_label_rect = diff_label.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 10))
        surface.blit(diff_label, diff_label_rect)

        # 难度按钮
        self._render_difficulty_buttons(surface)

        # 底部提示
        hint = self.font_tiny.render("先点敌人种族，再点难度开始", True, (150, 150, 170))
        hint_rect = hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 135))
        surface.blit(hint, hint_rect)

        # 已选显示
        if hasattr(self, '_selected_enemy_race') and self._selected_enemy_race:
            race_label_map = {r["key"]: r["label"] for r in ENEMY_RACES}
            selected_text = f"已选敌人: {race_label_map.get(self._selected_enemy_race, self._selected_enemy_race)}"
            selected_surf = self.font_tiny.render(selected_text, True, COLOR_GOLD)
            selected_rect = selected_surf.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 110))
            surface.blit(selected_surf, selected_rect)

        # 返回按钮
        for rect, callback in self.buttons:
            self._render_button(surface, rect, "返回选择玩家", COLOR_GRAY)

    def _render_enemy_race_cards(self, surface: pygame.Surface):
        """渲染敌人种族卡片（带种族背景图）"""
        for rect, er in self.enemy_race_buttons:
            if er["key"] != "random":
                # 加载并缓存卡片背景图
                bg_key = f'_ecard_{er["key"]}'
                bg_img = getattr(self, bg_key, None)
                if bg_img is None:
                    bg_img = self._load_bg_image(er["key"], rect.width, rect.height)
                    setattr(self, bg_key, bg_img)

                if bg_img:
                    img_surf = bg_img.copy()
                    img_surf.fill((*er["color"][:3], 80), special_flags=pygame.BLEND_RGBA_MULT)
                    surface.blit(img_surf, rect.topleft)
                else:
                    bg_color = (*er["color"][:3], 180)
                    card_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                    card_surf.fill(bg_color)
                    surface.blit(card_surf, rect)
            else:
                # random 用纯色
                card_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                card_surf.fill((80, 80, 80, 180))
                surface.blit(card_surf, rect)

            border_color = er["color"] if er["key"] != "random" else (150, 150, 150)
            pygame.draw.rect(surface, border_color, rect, 3)

            # 图标
            icon_font = make_font(42)
            icon_surf = icon_font.render(er["icon"], True, er["color"] if er["key"] != "random" else (200, 200, 200))
            icon_rect = icon_surf.get_rect(center=(rect.centerx, rect.y + 45))
            surface.blit(icon_surf, icon_rect)

            # 名称
            name_surf = self.font_race_btn.render(er["label"], True, COLOR_WHITE)
            name_rect = name_surf.get_rect(center=(rect.centerx, rect.y + 90))
            surface.blit(name_surf, name_rect)

            # 描述
            desc_surf = self.font_tiny.render(er["desc"], True, (180, 180, 200))
            desc_rect = desc_surf.get_rect(center=(rect.centerx, rect.y + 125))
            surface.blit(desc_surf, desc_rect)

            # 选中高亮
            if hasattr(self, '_selected_enemy_race') and self._selected_enemy_race == er["key"]:
                highlight = pygame.Rect(rect.x - 3, rect.y - 3, rect.width + 6, rect.height + 6)
                pygame.draw.rect(surface, COLOR_GOLD, highlight, 3)

    def _render_difficulty_buttons(self, surface: pygame.Surface):
        """渲染难度按钮"""
        for rect, dd in self.difficulty_buttons:
            col = dd["color"]
            card_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
            card_surf.fill((*col[:3], 160))
            surface.blit(card_surf, rect)
            pygame.draw.rect(surface, col, rect, 3)

            name_surf = self.font_button.render(dd["label"], True, COLOR_WHITE)
            name_rect = name_surf.get_rect(center=(rect.centerx, rect.y + 25))
            surface.blit(name_surf, name_rect)

            desc_surf = self.font_tiny.render(dd["desc"], True, (180, 180, 200))
            desc_rect = desc_surf.get_rect(center=(rect.centerx, rect.y + 52))
            surface.blit(desc_surf, desc_rect)

    def _render_race_cards(self, surface: pygame.Surface):
        cfg_map = {
            "terran": RACE_CONFIG["terran"],
            "protoss": RACE_CONFIG["protoss"],
            "zerg": RACE_CONFIG["zerg"],
        }

        # 各族的描述信息
        race_desc = {
            "terran": ("人族 Terran", "适应性强的全能部队"),
            "protoss": ("神族 Protoss", "强大的高科技部队"),
            "zerg": ("虫族 Zerg", "数量庞大的生物部队"),
        }

        for rect, race in self.race_buttons:
            cfg = cfg_map[race]
            desc = race_desc[race]

            # ── 背景图（缩放到卡片尺寸，放在卡片内部作为装饰） ──
            bg_img = getattr(self, f'_card_{race}', None)
            if bg_img is None:
                bg_img = self._load_bg_image(race, rect.width, rect.height)
                setattr(self, f'_card_{race}', bg_img)

            if bg_img:
                # 背景图半透明叠加
                img_surf = bg_img.copy()
                img_surf.fill((*cfg["btn_color"][:3], 80), special_flags=pygame.BLEND_RGBA_MULT)
                surface.blit(img_surf, rect.topleft)
            else:
                # 无图时用纯色背景
                bg_color = (*cfg["btn_color"][:3], 200)
                card_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                card_surf.fill(bg_color)
                surface.blit(card_surf, rect)

            # 边框
            pygame.draw.rect(surface, cfg["color_light"], rect, 3)
            # 顶部高亮
            highlight = pygame.Rect(rect.x + 2, rect.y + 2, rect.width - 4, 6)
            pygame.draw.rect(surface, cfg["color_light"], highlight)

            # 种族符号
            symbols = {
                "terran": "⚔",
                "protoss": "✦",
                "zerg": "◆",
            }
            sym_font = make_font(48)
            sym_surf = sym_font.render(symbols[race], True, cfg["color_light"])
            sym_rect = sym_surf.get_rect(center=(rect.centerx, rect.y + 50))
            surface.blit(sym_surf, sym_rect)

            # 种族名称
            name_surf = self.font_race_btn.render(desc[0], True, COLOR_WHITE)
            name_rect = name_surf.get_rect(center=(rect.centerx, rect.y + 90))
            surface.blit(name_surf, name_rect)

            # 特点
            motto_surf = self.font_small.render(desc[1], True, cfg["color_light"])
            motto_rect = motto_surf.get_rect(center=(rect.centerx, rect.y + 120))
            surface.blit(motto_surf, motto_rect)

            # 底部点击提示
            hint_surf = self.font_tiny.render("点击选择", True, COLOR_GOLD)
            hint_rect = hint_surf.get_rect(center=(rect.centerx, rect.bottom - 15))
            surface.blit(hint_surf, hint_rect)

    # ════════════════════════════════════════════
    # 地图选择界面
    # ════════════════════════════════════════════

    def _render_map_select(self, surface: pygame.Surface):
        """渲染地图选择界面"""
        surface.fill(COLOR_DARK)

        # 标题 — 显示难度和玩家人数过滤
        diff_label = getattr(self, '_map_select_difficulty', '')
        label_map = {"easy": "简单 2P", "normal": "普通 4P",
                     "hard": "困难 6P", "insane": "疯狂 8P"}
        diff_str = label_map.get(diff_label, "")
        title_text = f"{diff_str} 地图" if diff_str else "选择地图"
        title = self.font_subtitle.render(title_text, True, COLOR_GOLD)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, 25))
        surface.blit(title, title_rect)

        pygame.draw.line(surface, COLOR_GOLD, (100, 45), (SCREEN_WIDTH - 100, 45), 1)

        # 统计信息
        info_text = f"共 {len(self.map_list)} 张地图  |  滚轮滚动  |  点击选择"
        info_surf = self.font_tiny.render(info_text, True, (150, 150, 180))
        info_rect = info_surf.get_rect(center=(SCREEN_WIDTH // 2, 62))
        surface.blit(info_surf, info_rect)

        # 地图网格
        self._render_map_grid(surface)

        # 返回按钮
        for rect, callback in self.buttons:
            self._render_button(surface, rect, "← 返回", COLOR_GRAY)

    def _render_map_grid(self, surface: pygame.Surface):
        """渲染可滚动的地图卡片网格"""
        self.map_buttons.clear()
        maps = self.map_list
        if not maps:
            empty = self.font_subtitle.render("没有找到地图", True, (150, 150, 150))
            empty_rect = empty.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2))
            surface.blit(empty, empty_rect)
            return

        cols = 2
        card_w = (SCREEN_WIDTH - 60) // cols - 10
        card_h = 120
        gap_x = 14
        gap_y = 10
        start_x = 30
        start_y = 80

        visible_top = start_y + 10
        visible_bot = SCREEN_HEIGHT - 60

        # 裁剪可见区域
        clip_rect = pygame.Rect(0, visible_top, SCREEN_WIDTH - 30, visible_bot - visible_top)

        for i, md in enumerate(maps):
            col = i % cols
            row = i // cols
            x = start_x + col * (card_w + gap_x)
            y = start_y + row * (card_h + gap_y) - self.map_scroll

            # 裁剪：只渲染可见区域内的卡片
            if y + card_h < visible_top or y > visible_bot:
                continue

            rect = pygame.Rect(x, y, card_w, card_h)

            # 保存点击区域
            self.map_buttons.append((rect, i, md))

            # ── 绘制卡片背景 ──
            # tileset 颜色示意
            tset_id = md.get("tileset_id", 0)
            base_color = TILESET_PREVIEW_COLORS.get(tset_id, (60, 50, 40))
            # 亮一些版本做卡片底色
            card_bg = tuple(min(255, c + 30) for c in base_color)

            pygame.draw.rect(surface, (*card_bg, 200), rect)
            pygame.draw.rect(surface, COLOR_GOLD, rect, 2)

            # ── 左侧：迷你地形预览（64×64） ──
            preview_rect = pygame.Rect(x + 6, y + (card_h - 64) // 2, 64, 64)
            # 填充 tileset 颜色
            for py in range(preview_rect.y, preview_rect.y + 64, 4):
                for px in range(preview_rect.x, preview_rect.x + 64, 4):
                    shade = ((px + py) * 3) % 20 - 10
                    c = tuple(_clamp(v + shade) for v in base_color)
                    pygame.draw.rect(surface, c, (px, py, 4, 4))
            pygame.draw.rect(surface, (200, 200, 200, 100), preview_rect, 1)

            # ── 地图信息 ──
            info_x = x + 78
            info_y = y + 8

            # 地图名
            name = md.get("name", "Unknown")
            if len(name) > 22:
                name = name[:20] + "..."
            name_surf = self.font_small.render(name, True, COLOR_WHITE)
            surface.blit(name_surf, (info_x, info_y))

            # 玩家人数标签
            players = md.get("players", 0)
            if players > 0:
                p_badge_color = (60, 140, 60) if players >= 4 else (140, 130, 60)
                badge_rect = pygame.Rect(info_x, info_y + 26, 70, 22)
                pygame.draw.rect(surface, p_badge_color, badge_rect)
                pygame.draw.rect(surface, COLOR_WHITE, badge_rect, 1)
                p_text = self.font_tiny.render(f"{players}P", True, COLOR_WHITE)
                p_rect = p_text.get_rect(center=badge_rect.center)
                surface.blit(p_text, p_rect)

            # Tileset 名称
            tset_name = TILESET_NAMES.get(tset_id, f"Unknown({tset_id})")
            tset_surf = self.font_tiny.render(tset_name, True, (180, 180, 200))
            surface.blit(tset_surf, (info_x, info_y + 54))

            # 地图尺寸
            dim = f"{md.get('width', '?')} x {md.get('height', '?')}"
            dim_surf = self.font_tiny.render(dim, True, (160, 160, 180))
            surface.blit(dim_surf, (info_x, info_y + 72))

            # 路径
            path_str = md.get("path", "")
            if path_str and path_str != "Unknown":
                path_surf = self.font_tiny.render(path_str, True, (140, 140, 160))
                surface.blit(path_surf, (info_x, info_y + 90))

            # 点击提示
            hint_surf = self.font_tiny.render("点击选择", True, COLOR_GOLD)
            hint_rect = hint_surf.get_rect(midright=(rect.right - 8, rect.centery))
            surface.blit(hint_surf, hint_rect)

        # ── 滚动条 ──
        total_h = self._calc_map_grid_height()
        view_h = visible_bot - visible_top
        if total_h > view_h:
            bar_x = SCREEN_WIDTH - 24
            bar_y = visible_top
            bar_h = view_h
            thumb_h = max(30, int(bar_h * (view_h / total_h)))
            thumb_y = bar_y + int((self.map_scroll / max(1, total_h - view_h)) * (bar_h - thumb_h))

            pygame.draw.rect(surface, (60, 60, 80), (bar_x, bar_y, 18, bar_h))
            pygame.draw.rect(surface, (120, 120, 150), (bar_x, thumb_y, 18, thumb_h))
            pygame.draw.rect(surface, (180, 180, 200), (bar_x, thumb_y, 18, thumb_h), 1)


    # ════════════════════════════════════════════
    # 游戏结束 / 胜利界面
    # ════════════════════════════════════════════

    def _render_game_over(self, surface: pygame.Surface):
        surface.fill(COLOR_DARKER)
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 15, 26, 200))
        surface.blit(overlay, (0, 0))

        title = self.font_title.render("游戏结束", True, COLOR_RED)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 80))
        surface.blit(title, title_rect)

        wave_text = self.font_subtitle.render(
            f"坚持到第 {self.wave_reached} 波", True, COLOR_WHITE
        )
        wave_rect = wave_text.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20))
        surface.blit(wave_text, wave_rect)

        self._render_button(surface, self.buttons[0][0], "重新开始", COLOR_GREEN)
        self._render_button(surface, self.buttons[1][0], "返回菜单", COLOR_YELLOW)

    # ── 胜利界面 ──

    def _render_victory(self, surface: pygame.Surface):
        surface.fill(COLOR_DARKER)
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((15, 15, 26, 200))
        surface.blit(overlay, (0, 0))

        title = self.font_title.render("胜利！", True, COLOR_GOLD)
        title_rect = title.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 80))
        surface.blit(title, title_rect)

        msg = self.font_subtitle.render("成功抵挡所有进攻！", True, COLOR_GREEN)
        msg_rect = msg.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 20))
        surface.blit(msg, msg_rect)

        self._render_button(surface, self.buttons[0][0], "再玩一次", COLOR_GREEN)
        self._render_button(surface, self.buttons[1][0], "返回菜单", COLOR_YELLOW)


    # ════════════════════════════════════════════
    # 设置面板
    # ════════════════════════════════════════════

    def _render_settings(self, surface: pygame.Surface):
        """渲染设置面板（半透明覆盖层）"""
        # 半透明遮罩
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 10, 20, 180))
        surface.blit(overlay, (0, 0))

        # 面板背景
        panel_w, panel_h = 380, 340
        panel_x = (SCREEN_WIDTH - panel_w) // 2
        panel_y = (SCREEN_HEIGHT - panel_h) // 2

        panel_surf = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel_surf.fill((30, 30, 50, 230))
        surface.blit(panel_surf, (panel_x, panel_y))
        pygame.draw.rect(surface, (100, 100, 140), (panel_x, panel_y, panel_w, panel_h), 2)

        # 标题
        title = make_font(28)
        title_surf = title.render("⚙ 设置 Settings", True, COLOR_GOLD)
        title_rect = title_surf.get_rect(center=(panel_x + panel_w // 2, panel_y + 30))
        surface.blit(title_surf, title_rect)

        # 分隔线
        pygame.draw.line(surface, (80, 80, 120), (panel_x + 20, panel_y + 50),
                         (panel_x + panel_w - 20, panel_y + 50), 1)

        sm = self.sound_manager

        # ── SFX 音量 ──
        label_sfx = make_font(20)
        label_sfx_surf = label_sfx.render("音效 SFX", True, COLOR_WHITE)
        surface.blit(label_sfx_surf, (panel_x + 30, panel_y + 78))

        if sm:
            self._render_slider(surface, self._settings_sfx_slider, sm.sfx_volume,
                                is_music=False)

            # 开关
            sfx_on = sm.sfx_enabled
            self._render_toggle(surface, self._settings_sfx_toggle, sfx_on,
                                panel_x + 180, panel_y + 116)

        # ── BGM 音量 ──
        label_music = make_font(20)
        label_music_surf = label_music.render("音乐 BGM", True, COLOR_WHITE)
        surface.blit(label_music_surf, (panel_x + 30, panel_y + 148))

        if sm:
            self._render_slider(surface, self._settings_music_slider, sm.music_volume,
                                is_music=True)

            # 开关
            music_on = sm.music_enabled
            self._render_toggle(surface, self._settings_music_toggle, music_on,
                                panel_x + 180, panel_y + 186)

        # 关闭按钮
        for rect, callback in self.buttons:
            self._render_button(surface, rect, "返回游戏", COLOR_GREEN)

    def _render_slider(self, surface: pygame.Surface, rect: pygame.Rect,
                       value: float, is_music: bool = False):
        """渲染音量滑块"""
        if not rect:
            return
        # 轨道
        track_color = (60, 60, 90)
        pygame.draw.rect(surface, track_color, rect)
        pygame.draw.rect(surface, (100, 100, 140), rect, 1)

        # 填充
        fill_w = int(rect.width * value)
        if fill_w > 0:
            fill_rect = pygame.Rect(rect.x, rect.y, fill_w, rect.height)
            color = (80, 160, 255) if not is_music else (160, 100, 220)
            pygame.draw.rect(surface, color, fill_rect)

        # 百分比文字
        font = make_font(14)
        pct = int(value * 100)
        label = font.render(f"{pct}%", True, COLOR_WHITE)
        label_rect = label.get_rect(center=(rect.x + rect.width + 32, rect.centery))
        surface.blit(label, label_rect)

    def _render_toggle(self, surface: pygame.Surface, rect: pygame.Rect,
                       enabled: bool, label_x: int, label_y: int):
        """渲染开关勾选框"""
        if not rect:
            return
        if enabled:
            pygame.draw.rect(surface, COLOR_GREEN, rect)
            check = make_font(18)
            check_surf = check.render("✓", True, COLOR_WHITE)
            check_rect = check_surf.get_rect(center=rect.center)
            surface.blit(check_surf, check_rect)
        else:
            pygame.draw.rect(surface, (80, 40, 40), rect)
        pygame.draw.rect(surface, COLOR_WHITE, rect, 1)

        font = make_font(16)
        label = "开启" if enabled else "关闭"
        label_surf = font.render(f"✓ {label}", True, COLOR_GREEN if enabled else (140, 140, 140))
        surface.blit(label_surf, (label_x, label_y))

    def handle_settings_click(self, pos) -> bool:
        """处理设置面板的点击事件（由 game.py 调用）"""
        sm = self.sound_manager
        if not sm:
            return False

        # 滑块拖动（点击轨道）
        if self._settings_sfx_slider and self._settings_sfx_slider.collidepoint(pos):
            rel_x = (pos[0] - self._settings_sfx_slider.x) / self._settings_sfx_slider.width
            vol = max(0.0, min(1.0, rel_x))
            sm.set_sfx_volume(vol)
            return True

        if self._settings_music_slider and self._settings_music_slider.collidepoint(pos):
            rel_x = (pos[0] - self._settings_music_slider.x) / self._settings_music_slider.width
            vol = max(0.0, min(1.0, rel_x))
            sm.set_music_volume(vol)
            return True

        # 开关切换
        if self._settings_sfx_toggle and self._settings_sfx_toggle.collidepoint(pos):
            sm.toggle_sfx()
            return True

        if self._settings_music_toggle and self._settings_music_toggle.collidepoint(pos):
            sm.toggle_music()
            return True

        # 按钮
        for rect, callback in self.buttons:
            if rect.collidepoint(pos):
                self._play_ui_click()
                callback()
                return True

        return False


def _clamp(c: int) -> int:
    return max(0, min(255, c))
