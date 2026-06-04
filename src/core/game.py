"""
游戏主循环 — Pygame 版本
"""
import math
import os
import pygame
from src.core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT, TILE_SIZE,
    GRID_COLS, GRID_ROWS, PLAY_AREA_HEIGHT, FPS,
    COLOR_DARK, COLOR_PATH, COLOR_PATH_BORDER, COLOR_GRID_LINE,
    COLOR_VALID_PLACEMENT, COLOR_INVALID_PLACEMENT,
    STARTING_MONEY, STARTING_LIVES, COLOR_WHITE, COLOR_DARKER,
    RACE_CONFIG, make_font
)
from src.entities.tower import Tower
from src.entities.wave_manager import WaveManager
from src.systems.path import Path
from src.systems.economy import Economy
from src.ui.hud import HUD
from src.ui.tower_menu import TowerMenu
from src.ui.screens import ScreenManager
from src.systems.sound_manager import SoundManager


class Game:
    """游戏主类"""

    STATE_MENU = "menu"
    STATE_PLAYING = "playing"
    STATE_GAME_OVER = "game_over"
    STATE_VICTORY = "victory"

    def __init__(self, screen: pygame.Surface):
        self.screen = screen
        self.bg_color = COLOR_DARK
        self.state = self.STATE_MENU
        self.running = True
        self.paused = False  # 暂停状态

        # 种族
        self.player_race = "terran"

        # 敌人配置
        self.enemy_race = "zerg"
        self.difficulty = "normal"
        self.num_waves = 7

        # 游戏组件
        self.economy = Economy(STARTING_MONEY)
        self.economy.lives = STARTING_LIVES
        self.path = None
        self.wave_manager = None
        self.towers: list[Tower] = []
        self.projectiles = []
        self.enemies = []
        self.occupied_tiles = set()
        self.selected_tower = None

        # 音效
        self.sound_manager = SoundManager()

        # UI
        self.tower_menu = TowerMenu(self.economy)
        self.screens = ScreenManager()
        self.hud = HUD()

        # 让实体可以播放音效
        from src.entities.tower import Tower
        Tower.sound_manager = self.sound_manager
        from src.entities.projectile import Projectile
        Projectile.sound_manager = self.sound_manager
        from src.entities.enemy import Enemy
        Enemy.sound_manager = self.sound_manager
        self.screens.set_sound_manager(self.sound_manager)

        # 关卡数据
        self.level_data = None

        # PNG 地图背景
        self._map_bg = None
        self._current_map_idx = 0

        # UI 状态
        self.placing_tower = None
        self.mouse_grid_x = 0
        self.mouse_grid_y = 0

        # 设置面板
        self.showing_settings = False

    def load_level(self, level_data: dict):
        """加载关卡"""
        self.level_data = level_data
        self.economy = Economy(level_data.get("starting_money", STARTING_MONEY))
        self.economy.lives = level_data.get("starting_lives", STARTING_LIVES)
        self.towers.clear()
        self.projectiles.clear()
        self.selected_tower = None
        self.placing_tower = None

        waypoints = level_data["path"]
        self.path = Path(waypoints)
        self.occupied_tiles = self.path.get_occupied_tiles(buffer=1)

        self.wave_manager = WaveManager(
            level_data["waves"],
            self.path,
            self.economy,
            self._on_enemy_reach_end
        )

        self._setup_menu_callbacks()

    def _setup_menu_callbacks(self):
        """按种族注册建造回调"""
        self.tower_menu.build_callbacks.clear()

        # 只注册当前种族的兵种
        race_units = Tower.RACE_TOWERS.get(self.player_race, [])
        for tw_type in race_units:
            if tw_type in Tower.TOWER_STATS:
                self.tower_menu.on_build(tw_type, self._enter_placement_mode)

        self.tower_menu.on_upgrade(self._upgrade_tower)
        self.tower_menu.on_sell(self._sell_tower)

    def _enter_placement_mode(self, grid_x: int, grid_y: int, tower_type: str):
        stats = Tower.TOWER_STATS[tower_type]
        if not self.economy.can_afford(stats["cost"]):
            return
        self.placing_tower = tower_type
        self.tower_menu.hide()

    def _place_tower(self, grid_x: int, grid_y: int):
        stats = Tower.TOWER_STATS.get(self.placing_tower)
        if not stats:
            return
        if not self.economy.can_afford(stats["cost"]):
            return
        is_air = stats.get("is_air", False)
        # 地面单位检查路径占用，空中单位不检查
        if not is_air and (grid_x, grid_y) in self.occupied_tiles:
            return
        if self._tower_at(grid_x, grid_y):
            return

        self.economy.spend(stats["cost"])
        tower = Tower(self.placing_tower, grid_x, grid_y)
        self.towers.append(tower)
        # 音效：建造声 + 单位语音
        self.sound_manager.play_voice_rdy(self.placing_tower)
        # 地面单位占用格子，空中单位不占用
        if not tower.is_air:
            self.occupied_tiles.add((grid_x, grid_y))
        self.placing_tower = None

    def _upgrade_tower(self, tower: Tower):
        if not tower.can_upgrade():
            return
        cost = tower.upgrade_cost()
        if not self.economy.can_afford(cost):
            return
        self.economy.spend(cost)
        tower.apply_upgrade()

    def _sell_tower(self, tower: Tower):
        refund = tower.sell_value()
        self.economy.earn(refund)
        if not tower.is_air:
            self.occupied_tiles.discard((tower.grid_col, tower.grid_row))
        self.towers.remove(tower)
        self.selected_tower = None

    def _tower_at(self, grid_x: int, grid_y: int) -> Tower | None:
        for t in self.towers:
            if t.grid_col == grid_x and t.grid_row == grid_y:
                return t
        return None

    def _on_enemy_reach_end(self, enemy):
        self.economy.lives -= enemy.damage_to_base
        self.sound_manager.play_event("enemy_reach")
        if self.economy.lives <= 0:
            self.economy.lives = 0
            self._game_over()

    def _on_start_wave(self):
        if self.wave_manager and not self.wave_manager.wave_in_progress:
            self.wave_manager.start_next_wave()
            self.sound_manager.play_event("wave_start")

    def _game_over(self):
        self.state = self.STATE_GAME_OVER
        self.sound_manager.stop_bgm()
        self.sound_manager.play_event("game_over")
        self.screens.draw_game_over(
            self.wave_manager.get_current_wave_number(),
            self._restart_level, self._go_to_menu
        )

    def _victory(self):
        self.state = self.STATE_VICTORY
        self.sound_manager.stop_bgm()
        self.sound_manager.play_event("victory")
        self.screens.draw_victory(
            self._restart_level, self._go_to_menu
        )

    def _restart_level(self):
        """再玩一次：重新选一张地图（同一难度），换地图"""
        self.screens.clear()
        # 保持当前难度，自动挑下一张地图
        self._pick_and_load_map()
        # 但 _pick_and_load_map 会设置 state，所以这里不需要再设
        # 注意：如果调用了 _pick_and_load_map，state 已经在里面设了

    def _go_to_menu(self):
        self.screens.clear()
        self.state = self.STATE_MENU
        self.screens.draw_race_select(self._on_race_selected, self._quit_game)

    def _on_race_selected(self, race: str):
        """玩家种族被选中 → 进入敌人配置选择"""
        self.player_race = race
        self.tower_menu.set_player_race(race)

        # 进入敌人配置界面
        self.screens.draw_enemy_select(race, self._on_enemy_config)

    def _on_enemy_config(self, enemy_race: str, difficulty: str):
        """敌人种族和难度确定 → 自动加载地图直接开始游戏"""
        self.enemy_race = enemy_race
        self.difficulty = difficulty

        # 根据难度自动挑选地图
        self._pick_and_load_map()

    def _pick_and_load_map(self):
        """按难度从 8 张 PNG 地图中挑选一张并开始游戏"""
        import random
        import pygame
        from src.core.constants import PROJECT_ROOT

        # 8 张地图的路径和对应预设路径
        self._all_png_maps = [
            {"idx": 1, "file": "01.png", "path": "easy"},
            {"idx": 2, "file": "02.png", "path": "easy"},
            {"idx": 3, "file": "03.png", "path": "normal"},
            {"idx": 4, "file": "04.png", "path": "normal"},
            {"idx": 5, "file": "05.png", "path": "hard"},
            {"idx": 6, "file": "06.png", "path": "hard"},
            {"idx": 7, "file": "07.png", "path": "insane"},
            {"idx": 8, "file": "08.png", "path": "insane"},
        ]

        # 已用过的地图索引
        if not hasattr(self, '_used_maps'):
            self._used_maps = set()

        difficulty_map = {"easy": "easy", "normal": "normal", "hard": "hard", "insane": "insane"}
        diff_cat = difficulty_map.get(self.difficulty, "normal")

        candidates = [m for m in self._all_png_maps
                      if m["path"] == diff_cat and m["idx"] not in self._used_maps]
        if not candidates:
            # 该难度的图用完了，允许跨难度用
            candidates = [m for m in self._all_png_maps if m["idx"] not in self._used_maps]
        if not candidates:
            self._used_maps.clear()
            candidates = [m for m in self._all_png_maps if m["path"] == diff_cat]

        chosen = random.choice(candidates)
        self._used_maps.add(chosen["idx"])

        map_dir = os.path.join(PROJECT_ROOT, "src", "map")
        map_path = os.path.join(map_dir, chosen["file"])
        self._current_map_idx = chosen["idx"]

        self.screens.clear()
        self._on_map_selected_png(map_path)

    def _on_enemy_select_back(self):
        """从地图选择返回敌人配置"""
        self.screens.draw_enemy_select(self.player_race, self._on_enemy_config)

    def _on_map_selected_png(self, map_path: str):
        """加载 PNG 地图背景并开始游戏"""
        import pygame

        self.screens.clear()

        # 加载 PNG 图片作为地图背景
        try:
            bg_raw = pygame.image.load(map_path).convert()
            # 缩放到游戏区域大小
            self._map_bg = pygame.transform.scale(bg_raw, (SCREEN_WIDTH, PLAY_AREA_HEIGHT))
        except Exception as e:
            print(f"加载地图图片失败: {e}")
            self._load_level_with_enemy_config()
            self.state = self.STATE_PLAYING
            self.sound_manager.play_bgm()
            return

        # 预设路径（网格坐标，按地图索引）
        preset = self._get_preset_path(self._current_map_idx)

        # 构建关卡数据
        from src.core.constants import STARTING_MONEY, STARTING_LIVES
        from src.systems.enemy_generator import generate_all_waves

        diff_money_mod = {"easy": 1.2, "normal": 1.0, "hard": 0.8, "insane": 0.6}
        diff_lives_mod = {"easy": 1.5, "normal": 1.0, "hard": 0.7, "insane": 0.5}

        level_data = {
            "name": f"地图_{self._current_map_idx:02d}",
            "path": preset,
            "starting_money": int(STARTING_MONEY * diff_money_mod.get(self.difficulty, 1.0)),
            "starting_lives": max(5, int(STARTING_LIVES * diff_lives_mod.get(self.difficulty, 1.0))),
            "waves": generate_all_waves(self.enemy_race, self.difficulty, self.num_waves),
        }

        self.load_level(level_data)
        self.state = self.STATE_PLAYING

        # 开始 BGM
        self.sound_manager.play_bgm()

    def _get_preset_path(self, map_idx: int) -> list:
        """根据地图索引返回预设网格坐标路径"""
        paths = {
            1: [(0, 10), (8, 10), (8, 3), (22, 3), (22, 14), (31, 14)],           # 01.png
            2: [(0, 10), (8, 10), (8, 3), (22, 3), (22, 14), (31, 14)],           # 02.png
            3: [(0, 10), (10, 10), (10, 4), (20, 4), (20, 14), (31, 14)],         # 03.png
            4: [(0, 10), (10, 10), (10, 4), (20, 4), (20, 14), (31, 14)],         # 04.png
            5: [(0, 9), (7, 9), (7, 3), (16, 3), (16, 15), (31, 15)],             # 05.png
            6: [(0, 9), (7, 9), (7, 3), (16, 3), (16, 15), (31, 15)],             # 06.png
            7: [(0, 8), (12, 8), (12, 2), (24, 2), (24, 16), (31, 16)],           # 07.png
            8: [(0, 8), (12, 8), (12, 2), (24, 2), (24, 16), (31, 16)],           # 08.png
        }
        return paths.get(map_idx, paths[1])

    def _load_level_with_enemy_config(self):
        """加载基础关卡，用动态敌人生成器覆盖 waves"""
        import json
        import os
        from src.core.constants import LEVELS_DIR
        from src.systems.enemy_generator import generate_all_waves

        level_path = os.path.join(LEVELS_DIR, "level_01.json")
        try:
            with open(level_path, "r", encoding="utf-8") as f:
                level_data = json.load(f)
        except Exception as e:
            print(f"加载关卡失败: {e}")
            return

        # 用动态生成的敌人阵容替换原始 waves
        level_data["waves"] = generate_all_waves(
            self.enemy_race,
            self.difficulty,
            self.num_waves,
        )

        # 根据难度调整初始资金
        diff_money_mod = {"easy": 1.2, "normal": 1.0, "hard": 0.8, "insane": 0.6}
        diff_lives_mod = {"easy": 1.5, "normal": 1.0, "hard": 0.7, "insane": 0.5}
        level_data["starting_money"] = int(level_data.get("starting_money", 200)
                                           * diff_money_mod.get(self.difficulty, 1.0))
        level_data["starting_lives"] = max(5, int(level_data.get("starting_lives", 20)
                                                  * diff_lives_mod.get(self.difficulty, 1.0)))

        self.load_level(level_data)

    def _quit_game(self):
        self.running = False

    def _quit_to_menu(self):
        """退出到主菜单"""
        self.state = self.STATE_MENU
        self.towers.clear()
        self.projectiles.clear()
        self.enemies.clear()
        self.selected_tower = None
        self.placing_tower = None
        self.tower_menu.hide()
        self.paused = False
        self.show_menu()

    def toggle_pause(self):
        """切换暂停状态（只在 playing 状态下有效）"""
        if self.state == self.STATE_PLAYING:
            self.paused = not self.paused

    def _open_settings(self):
        """打开设置面板"""
        if self.state == self.STATE_PLAYING and not self.paused:
            self.paused = True  # 自动暂停
        self.showing_settings = True
        self.screens.draw_settings(self._close_settings)

    def _close_settings(self):
        self.showing_settings = False

    def show_menu(self):
        self.sound_manager.stop_bgm()
        self.screens.draw_race_select(self._on_race_selected, self._quit_game)
        self.state = self.STATE_MENU

    # ── 游戏循环 ──

    def update(self, dt: float):
        if self.state != self.STATE_PLAYING:
            return

        if self.paused:
            return  # 暂停时只渲染，不更新游戏逻辑

        if not self.wave_manager:
            return

        spawned = self.wave_manager.update(dt)
        self.enemies = self.wave_manager.active_enemies

        for proj in self.projectiles[:]:
            proj.update(dt)
            if not proj.alive:
                self.projectiles.remove(proj)

        for tower in self.towers:
            tower.update(dt, self.enemies, self.projectiles)

        # 处理敌人上的寄生效果（减速+持续伤害）
        for enemy in self.enemies:
            if hasattr(enemy, 'parasite_timer') and enemy.parasite_timer > 0:
                enemy.parasite_timer -= dt
                if enemy.parasite_dps > 0:
                    enemy.take_damage(int(enemy.parasite_dps * dt * 60) + 1)
                enemy.speed_multiplier = 1.0 - (enemy.parasite_slow if hasattr(enemy, 'parasite_slow') else 0)
            else:
                enemy.speed_multiplier = 1.0

        if self.wave_manager.all_waves_complete and len(self.enemies) == 0:
            self._victory()

    # ── 渲染 ──

    def render(self):
        """渲染所有内容"""
        if self.state == self.STATE_MENU:
            self.screens.render(self.screen)
            # 设置面板覆盖（可在主菜单打开）
            if self.showing_settings:
                self.screens.render_settings_overlay(self.screen)
            return

        if self.state in (self.STATE_GAME_OVER, self.STATE_VICTORY):
            self.screens.render(self.screen)
            # 仍在 HUD 区域显示退出按钮
            self.hud.draw(self.screen, self.economy, self.wave_manager, self.state,
                          self.selected_tower, lives=self.economy.lives,
                          player_race=self.player_race,
                          enemy_race=self.enemy_race,
                          difficulty=self.difficulty,
                          paused=self.paused)
            # 设置面板覆盖
            if self.showing_settings:
                self.screens.render_settings_overlay(self.screen)
            return

        if self.state == self.STATE_PLAYING:
            if hasattr(self, '_map_bg') and self._map_bg:
                self._draw_terrain()
                self._draw_path_overlay()
                self._draw_entry_exit_markers()
            else:
                self._draw_grid()
                self._draw_path()

            # 投射物
            for proj in self.projectiles:
                proj.draw(self.screen)

            # 敌人
            for enemy in self.enemies:
                enemy.draw(self.screen)

            # 塔
            for tower in self.towers:
                tower.draw(self.screen)

            # 放置预览
            self._draw_placement_preview()

            # HUD（显示种族信息）
            self.hud.draw(
                self.screen, self.economy, self.wave_manager, self.state,
                self.selected_tower, lives=self.economy.lives,
                player_race=self.player_race,
                enemy_race=self.enemy_race,
                difficulty=self.difficulty,
                paused=self.paused,
            )

            # 塔菜单
            self.tower_menu.draw(self.screen)

	        # 暂停提示（不变暗）
            if self.paused:
                font = make_font(48)
                pause_text = font.render("⏸ 暂停中", True, COLOR_WHITE)
                pause_rect = pause_text.get_rect(center=(SCREEN_WIDTH // 2, PLAY_AREA_HEIGHT // 2))
                self.screen.blit(pause_text, pause_rect)
                hint_font = make_font(18)
                hint = hint_font.render("按 Space 继续 | 暂停中可进行建造/部署", True, (180, 180, 200))
                hint_rect = hint.get_rect(center=(SCREEN_WIDTH // 2, PLAY_AREA_HEIGHT // 2 + 50))
                self.screen.blit(hint, hint_rect)

        # 设置面板覆盖层（在所有状态的最上层）
        if self.showing_settings:
            self.screens.render_settings_overlay(self.screen)


    def _draw_grid(self):
        """绘制网格"""
        for c in range(GRID_COLS + 1):
            x = c * TILE_SIZE
            pygame.draw.line(self.screen, COLOR_GRID_LINE, (x, 0), (x, PLAY_AREA_HEIGHT), 1)
        for r in range(GRID_ROWS + 1):
            y = r * TILE_SIZE
            pygame.draw.line(self.screen, COLOR_GRID_LINE, (0, y), (SCREEN_WIDTH, y), 1)

    def _draw_path(self):
        """绘制柏油马路（黑色路面 + 白色中线）"""
        if not self.path:
            return
        pts = self.path.pixel_points
        road_w = TILE_SIZE - 4
        # 黑色路面
        for i in range(len(pts) - 1):
            pygame.draw.line(self.screen, COLOR_PATH,
                             pts[i], pts[i + 1], road_w)
            pygame.draw.line(self.screen, COLOR_PATH_BORDER,
                             pts[i], pts[i + 1], road_w)
        # 白色虚线中线
        dash_len = 12
        gap_len = 10
        for i in range(len(pts) - 1):
            x1, y1 = pts[i]
            x2, y2 = pts[i + 1]
            dx, dy = x2 - x1, y2 - y1
            seg_len = math.sqrt(dx * dx + dy * dy)
            if seg_len == 0:
                continue
            ux, uy = dx / seg_len, dy / seg_len
            d = 0.0
            while d < seg_len:
                start = d
                end = min(d + dash_len, seg_len)
                sx = int(x1 + ux * start)
                sy = int(y1 + uy * start)
                ex = int(x1 + ux * end)
                ey = int(y1 + uy * end)
                pygame.draw.line(self.screen, COLOR_WHITE, (sx, sy), (ex, ey), 2)
                d = end + gap_len

        # 路径点标记
        for i, (px, py) in enumerate(pts):
            pygame.draw.circle(self.screen, COLOR_WHITE, (px, py), 4)
            font = make_font(16)
            if i == 0:
                label = font.render("入口", True, (136, 255, 136))
                self.screen.blit(label, (px - 12, py - 22))
            elif i == len(pts) - 1:
                label = font.render("终点", True, (255, 136, 136))
                self.screen.blit(label, (px - 12, py - 22))

    def _draw_terrain(self):
        """绘制 PNG 地图背景"""
        if hasattr(self, '_map_bg') and self._map_bg:
            self.screen.blit(self._map_bg, (0, 0))

    def _draw_path_overlay(self):
        """在路径上绘制半透明覆盖层"""
        if not self.path:
            return
        pts = self.path.pixel_points
        overlay = pygame.Surface((SCREEN_WIDTH, PLAY_AREA_HEIGHT), pygame.SRCALPHA)
        for i in range(len(pts) - 1):
            pygame.draw.line(overlay, (74, 58, 42, 120),
                             pts[i], pts[i + 1], TILE_SIZE - 4)
            pygame.draw.line(overlay, (106, 90, 58, 180),
                             pts[i], pts[i + 1], TILE_SIZE - 2)
        self.screen.blit(overlay, (0, 0))

    def _draw_entry_exit_markers(self):
        """在地形上绘制入口和出口标记"""
        if not self.path:
            return
        pts = self.path.pixel_points
        font = make_font(14)
        if len(pts) > 0:
            px, py = pts[0]
            label = font.render("入口", True, (100, 255, 100))
            self.screen.blit(label, (px - 12, py - 20))
        if len(pts) > 1:
            px, py = pts[-1]
            label = font.render("出口", True, (255, 100, 100))
            self.screen.blit(label, (px - 12, py - 20))

    def _draw_placement_preview(self):
        """绘制放置预览"""
        if not self.placing_tower:
            return

        gx, gy = self.mouse_grid_x, self.mouse_grid_y

        if gx < 0 or gx >= GRID_COLS or gy < 0 or gy >= GRID_ROWS:
            return

        px = gx * TILE_SIZE
        py = gy * TILE_SIZE

        # 空中单位：不检查地面占用，只检查是否与其他单位重叠
        stats = Tower.TOWER_STATS.get(self.placing_tower)
        is_air_unit = stats.get("is_air", False) if stats else False

        if is_air_unit:
            # 空中单位只检查不与其他单位在同一格
            valid = not self._tower_at(gx, gy)
            color = COLOR_VALID_PLACEMENT if valid else COLOR_INVALID_PLACEMENT
            outline = (0, 255, 0) if valid else (255, 0, 0)
            # 用蓝色调标识空中单位
            color = (0, 0, 80) if valid else (80, 0, 0)
        else:
            valid = (gx, gy) not in self.occupied_tiles and not self._tower_at(gx, gy)
            color = COLOR_VALID_PLACEMENT if valid else COLOR_INVALID_PLACEMENT
            outline = (0, 255, 0) if valid else (255, 0, 0)

        pygame.draw.rect(self.screen, color, (px, py, TILE_SIZE, TILE_SIZE))
        pygame.draw.rect(self.screen, outline, (px, py, TILE_SIZE, TILE_SIZE), 2)

        if valid:
            stats = Tower.TOWER_STATS.get(self.placing_tower)
            if stats:
                font = make_font(14)
                name_surf = font.render(stats["name"], True, COLOR_WHITE)
                name_rect = name_surf.get_rect(center=(px + TILE_SIZE // 2, py + TILE_SIZE // 2))
                self.screen.blit(name_surf, name_rect)

    # ── 事件处理 ──

    def on_mouse_move(self, event):
        """鼠标移动"""
        self.mouse_grid_x = event.pos[0] // TILE_SIZE
        self.mouse_grid_y = event.pos[1] // TILE_SIZE

        # 更新建造菜单鼠标位置（用于 hover tooltip）
        self.tower_menu.update_mouse_pos(event.pos)

        if self.state == self.STATE_PLAYING and event.pos[1] < PLAY_AREA_HEIGHT:
            gx, gy = self.mouse_grid_x, self.mouse_grid_y
            tower = self._tower_at(gx, gy)
            if tower:
                tower.show_range = True
            for t in self.towers:
                if t != tower:
                    t.show_range = False

    def on_mouse_click(self, event):
        """鼠标点击"""
        pos = event.pos

        # 菜单/结束界面
        if self.state == self.STATE_MENU:
            self.screens.handle_click(pos)
            return

        if self.state in (self.STATE_GAME_OVER, self.STATE_VICTORY):
            # 退出按钮在所有状态下都可点
            if pos[1] >= SCREEN_HEIGHT - HUD_HEIGHT:
                btn = self.hud.check_button_click(pos)
                if btn == "quit":
                    self._quit_to_menu()
                    return
            self.screens.handle_click(pos)
            return

        if self.state != self.STATE_PLAYING:
            return

        gx = pos[0] // TILE_SIZE
        gy = pos[1] // TILE_SIZE

        # 设置面板覆盖层（在所有状态下优先）
        if self.showing_settings:
            self.screens.handle_settings_click(pos)
            return

        # HUD 按钮
        if pos[1] >= SCREEN_HEIGHT - HUD_HEIGHT:
            btn = self.hud.check_button_click(pos)
            if btn == "start_wave":
                self._on_start_wave()
            elif btn == "toggle_pause":
                self.toggle_pause()
            elif btn == "settings":
                self._open_settings()
            elif btn == "quit":
                self._quit_to_menu()
            return

        # 塔菜单点击
        if self.tower_menu.active:
            if self.tower_menu.handle_click(pos):
                return

        if gx < 0 or gx >= GRID_COLS or gy < 0 or gy >= GRID_ROWS:
            return

        # 放置模式
        if self.placing_tower:
            self._place_tower(gx, gy)
            return

        # 点击已有塔
        tower = self._tower_at(gx, gy)
        if tower:
            self.selected_tower = tower
            self.tower_menu.show_for_tower(tower, pos[0], pos[1])
            return

        # 点击空地 → 建造菜单
        if (gx, gy) not in self.occupied_tiles and not tower:
            self.selected_tower = None
            self.tower_menu.show_for_build(gx, gy, gx * TILE_SIZE, gy * TILE_SIZE)
            return

        # 点击空地（不可建造），取消选中
        self.selected_tower = None
        self.tower_menu.hide()

    def on_right_click(self, event):
        """右键 — 取消选中/取消放置"""
        self.selected_tower = None
        self.placing_tower = None
        self.tower_menu.hide()
