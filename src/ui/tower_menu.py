"""
塔菜单 — 建造/升级/出售界面
"""
import pygame
from src.core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, HUD_HEIGHT, TILE_SIZE,
    COLOR_HUD_BG, COLOR_WHITE, COLOR_GREEN, COLOR_YELLOW,
    COLOR_RED, COLOR_GOLD, COLOR_DARK, COLOR_TERRAN, COLOR_PROTOSS, COLOR_ZERG,
    RACE_CONFIG, make_font
)
from src.entities.tower import Tower
from src.entities.sprite import PlaceholderSprite


class TowerMenu:
    """塔建造/升级菜单"""

    # 兵种分类（地面/空中）
    TARGET_CATEGORY = {
        "ground": [],
        "air": [],
        "both": [],
    }

    @classmethod
    def get_units_for_race(cls, race: str) -> list[str]:
        """获取某一种族的所有可用兵种"""
        return Tower.RACE_TOWERS.get(race, [])

    @classmethod
    def is_air_unit(cls, stats) -> bool:
        """判断是否为纯空中单位"""
        targets = stats.get("targets", "ground")
        # 仅以"air"为目标的，视为纯空中单位
        if targets == "air":
            return True
        # 既有air也有both的，"air"优先，但both也在地面页显示
        return False

    def __init__(self, economy):
        self.economy = economy

        self.active = False
        self.grid_x = 0
        self.grid_y = 0
        self.screen_x = 0
        self.screen_y = 0
        self.existing_tower = None
        self.menu_type = None  # "build" or "tower"
        self.player_race = "terran"  # 默认人族，由外部设置

        # 分页
        self.build_tab = "ground"  # "ground" or "air"

        self.build_callbacks = []
        self.upgrade_callback = None
        self.sell_callback = None
        self.close_callback = None

        self.font_title = make_font(24)
        self.font_medium = make_font(20)
        self.font_small = make_font(18)
        self.font_tiny = make_font(14)

        # 可点击矩形区域
        self.build_card_rects: dict[str, pygame.Rect] = {}
        self.tab_rects: dict[str, pygame.Rect] = {}
        self.upgrade_rect = None
        self.sell_rect = None

        # 鼠标悬停状态
        self.mouse_pos = None  # 由外部更新

    def set_player_race(self, race: str):
        self.player_race = race

    def show_for_build(self, grid_x: int, grid_y: int, screen_x: int, screen_y: int):
        """显示建造菜单"""
        self.active = True
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.screen_x = screen_x
        self.screen_y = screen_y
        self.existing_tower = None
        self.menu_type = "build"
        self.build_tab = "ground"

    def show_for_tower(self, tower: Tower, screen_x: int, screen_y: int):
        """显示已有塔的菜单（升级/出售）"""
        self.active = True
        self.existing_tower = tower
        self.screen_x = screen_x
        self.screen_y = screen_y
        self.menu_type = "tower"

    def hide(self):
        self.active = False
        self.menu_type = None
        self.build_card_rects.clear()
        self.tab_rects.clear()
        self.upgrade_rect = None
        self.sell_rect = None

    def on_build(self, tower_type: str, callback):
        self.build_callbacks.append((tower_type, callback))

    def on_upgrade(self, callback):
        self.upgrade_callback = callback

    def on_sell(self, callback):
        self.sell_callback = callback

    def on_close(self, callback):
        self.close_callback = callback

    def handle_click(self, pos) -> bool:
        """处理点击事件，返回是否被菜单消费"""
        if not self.active:
            return False

        if self.menu_type == "build":
            # 分页切换
            for tab_name, tab_rect in self.tab_rects.items():
                if tab_rect.collidepoint(pos):
                    if hasattr(Tower, 'sound_manager') and Tower.sound_manager:
                        Tower.sound_manager.play_ui("ui_click")
                    self.build_tab = tab_name
                    self.build_card_rects.clear()
                    return True

            # 卡片点击
            for tw_type, rect in self.build_card_rects.items():
                if rect.collidepoint(pos):
                    if hasattr(Tower, 'sound_manager') and Tower.sound_manager:
                        Tower.sound_manager.play_ui("ui_click")
                    stats = Tower.TOWER_STATS[tw_type]
                    if self.economy.can_afford(stats["cost"]):
                        self._on_build_click(tw_type)
                    return True

            # 点击菜单外部
            mx, my = self._get_build_menu_rect()
            if not pygame.Rect(mx, my, 540, 180).collidepoint(pos):
                self.hide()
            return True

        elif self.menu_type == "tower":
            if self.upgrade_rect and self.upgrade_rect.collidepoint(pos):
                self._on_upgrade_click()
                return True
            if self.sell_rect and self.sell_rect.collidepoint(pos):
                self._on_sell_click()
                return True
            mx, my = self._get_tower_menu_rect()
            if not pygame.Rect(mx, my, 300, 150).collidepoint(pos):
                self.hide()
            return True

        return False

    def _get_build_menu_rect(self):
        return (SCREEN_WIDTH // 2 - 270, SCREEN_HEIGHT - HUD_HEIGHT - 180)

    def _get_tower_menu_rect(self):
        return (SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT - HUD_HEIGHT - 160)

    def get_race_color(self):
        config = RACE_CONFIG.get(self.player_race, RACE_CONFIG["terran"])
        return config["color"], config["color_light"], config["color_dark"]

    def draw(self, surface: pygame.Surface):
        """绘制当前菜单"""
        if not self.active:
            return

        if self.menu_type == "build":
            self._draw_build_menu(surface)
        elif self.menu_type == "tower":
            self._draw_tower_menu(surface)

    def update_mouse_pos(self, pos):
        """更新鼠标位置（供外部调用，用于 hover 检测）"""
        self.mouse_pos = pos

    def _draw_build_menu(self, surface: pygame.Surface):
        """绘制建造菜单 — 只显示当前种族的兵种"""
        self.build_card_rects.clear()
        self.tab_rects.clear()

        race_color, race_light, race_dark = self.get_race_color()
        mx, my = self._get_build_menu_rect()

        # 背景
        pygame.draw.rect(surface, COLOR_HUD_BG, (mx, my, 540, 175))
        pygame.draw.rect(surface, race_color, (mx, my, 540, 175), 2)

        # 标题
        race_cfg = RACE_CONFIG.get(self.player_race, RACE_CONFIG["terran"])
        title = self.font_medium.render(
            f"{race_cfg['name']} 部署选择", True, race_light
        )
        surface.blit(title, (mx + 200, my + 5))

        # 分页签
        tab_y = my + 30
        self._draw_tabs(surface, mx, tab_y, race_light, race_dark)

        # 获取当前种族兵种并分类
        race_units = self.get_units_for_race(self.player_race)

        # 分离地面和空中单位
        ground_units = []
        air_units = []
        for tw_type in race_units:
            stats = Tower.TOWER_STATS[tw_type]
            if stats.get("is_air", False):
                air_units.append(tw_type)
            else:
                ground_units.append(tw_type)

        current_units = air_units if self.build_tab == "air" else ground_units

        # 绘制兵种卡片
        y = tab_y + 32
        x = mx + 10
        cards_per_row = 4
        card_w = 125
        card_h = 65
        spacing = 8

        for i, tw_type in enumerate(current_units):
            stats = Tower.TOWER_STATS[tw_type]
            can_afford = self.economy.can_afford(stats["cost"])
            card_color = race_light if can_afford else (102, 102, 102)
            bg_color = race_dark if can_afford else (34, 34, 34)

            rect = pygame.Rect(x, y, card_w, card_h)
            self.build_card_rects[tw_type] = rect

            pygame.draw.rect(surface, bg_color, rect)
            pygame.draw.rect(surface, card_color, rect, 1)

            # ── 在卡片左侧绘制单位 PNG 预览图 ──
            preview_size = 36
            preview_sprite = PlaceholderSprite(tw_type)
            preview_sheet = preview_sprite.sheet
            if preview_sheet and len(preview_sheet.frames) > 0:
                # 有 PNG 帧，用第一帧缩放到预览尺寸
                frame = preview_sheet.get_frame(0)
                if frame:
                    fw, fh = frame.get_size()
                    scale = min(preview_size / max(fw, 1), preview_size / max(fh, 1))
                    nw, nh = max(1, int(fw * scale)), max(1, int(fh * scale))
                    if nw != fw or nh != fh:
                        frame = pygame.transform.scale(frame, (nw, nh))
                    # 钱不够时转灰度
                    if not can_afford:
                        gray_frame = pygame.Surface((nw, nh), pygame.SRCALPHA)
                        gray_frame.fill((80, 80, 80))
                        frame.blit(gray_frame, (0, 0), special_flags=pygame.BLEND_RGB_MULT)
                    # 居中绘制在卡片左上区域
                    px_pos = x + (preview_size - nw) // 2 + 2
                    py_pos = y + (preview_size - nh) // 2 + 2
                    surface.blit(frame, (px_pos, py_pos))
            else:
                # 无 PNG：用几何占位绘制
                preview_sprite.draw(surface, x + preview_size // 2 + 2,
                                    y + preview_size // 2 + 2,
                                    scale_to=(preview_size, preview_size))

            # 兵种名（在预览图右侧）
            name_x = x + preview_size + 8
            name_surf = self.font_small.render(stats["name"], True, card_color)
            surface.blit(name_surf, (name_x, y + 3))

            # 价格
            price_surf = self.font_tiny.render(f"${stats['cost']}", True,
                                               COLOR_GOLD if can_afford else (136, 136, 136))
            surface.blit(price_surf, (name_x, y + 22))

            # 属性
            attr_color = (170, 170, 170) if can_afford else (100, 100, 100)
            dmg_str = f"DMG:{stats['damage']} RNG:{stats['range']}"
            dmg_surf = self.font_tiny.render(dmg_str, True, attr_color)
            surface.blit(dmg_surf, (name_x, y + 36))

            # 目标标记
            target_str = stats.get("targets", "地面")
            target_label = {"ground": "对地", "air": "对空", "both": "全能"}.get(target_str, "地面")
            tgt_color = (140, 200, 140) if can_afford else (80, 120, 80)
            tgt_surf = self.font_tiny.render(target_label, True, tgt_color)
            surface.blit(tgt_surf, (name_x, y + 48))

            # ── 钱不够时：灰色半透明遮罩 + "不足" 标记 ──
            if not can_afford:
                gray_overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                gray_overlay.fill((80, 80, 80, 140))
                surface.blit(gray_overlay, rect.topleft)
                # 在遮罩上方再画一层降低饱和度
                sat_overlay = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
                sat_overlay.fill((60, 60, 60, 100))
                surface.blit(sat_overlay, rect.topleft)
                # "不足"标签
                na_surf = self.font_tiny.render("不足", True, (200, 80, 80))
                na_rect = na_surf.get_rect(bottomright=(rect.right - 4, rect.bottom - 4))
                surface.blit(na_surf, na_rect)

            x += card_w + spacing
            if (i + 1) % cards_per_row == 0:
                x = mx + 10
                y += card_h + spacing

        # 如果没有兵种可显示
        if not current_units:
            empty_surf = self.font_small.render("该分类没有可用兵种", True, (136, 136, 136))
            empty_rect = empty_surf.get_rect(center=(mx + 270, my + 100))
            surface.blit(empty_surf, empty_rect)

        # ── 鼠标悬停信息提示 ──
        if self.mouse_pos:
            hovered_type = None
            for tw_type, rect in self.build_card_rects.items():
                if rect.collidepoint(self.mouse_pos):
                    hovered_type = tw_type
                    break
            if hovered_type:
                self._draw_card_tooltip(surface, hovered_type, self.mouse_pos)

    def _wrap_text(self, font: pygame.font.Font, text: str, max_width: int) -> list[str]:
        """将一段文字按最大宽度拆成多行（保留原分句）"""
        if font.size(text)[0] <= max_width:
            return [text]
        lines = []
        # 尝试按空格、冒号、逗号拆分
        words = text.replace("：", ":").replace("，", ",").replace("  ", " ").split(" ")
        current_line = ""
        for word in words:
            test_line = (current_line + " " + word).strip()
            if font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        return lines

    def _draw_card_tooltip(self, surface, tw_type, pos):
        """在卡片上方显示悬浮提示（支持换行）"""
        stats = Tower.TOWER_STATS[tw_type]
        race_color, _, _ = self.get_race_color()

        # tooltip 内容
        lines = []
        # 第一行：名称 + 种族 + 价格
        race_prefix = {"terran": "T", "protoss": "P", "zerg": "Z"}.get(stats.get("race", ""), "?")
        lines.append(f"{stats['name']} [{race_prefix}]  ${stats['cost']}")

        # 第二行：伤害 + 射程 + 攻速
        fire_rate = stats.get('fire_rate', 0)
        if fire_rate > 0:
            lines.append(f"伤害:{stats['damage']}  射程:{stats['range']}  攻速:{fire_rate:.1f}s")
        else:
            lines.append(f"射程:{stats['range']}  (特殊能力)")

        # 第三行：目标 + 特殊
        target_str = {"ground": "对地", "air": "对空", "both": "全能"}.get(stats.get("targets", ""), "地面")
        special = stats.get("special", "")
        if special == "psi_storm":
            special_str = f"心灵风暴(CD:{stats.get('psi_storm_cooldown', 30)}s)"
        elif special == "parasite":
            special_str = f"寄生(CD:{stats.get('parasite_cooldown', 20)}s)"
        elif special == "interceptor":
            special_str = f"拦截机x{stats.get('interceptor_count', 4)}"
        elif special == "psionic_blade":
            special_str = f"灵能飞刃(CD:{stats.get('psionic_blade_cooldown', 8)}s)"
        else:
            special_str = ""

        if special_str:
            lines.append(f"{target_str}  {special_str}")
        else:
            lines.append(target_str)

        # 升级信息
        upgrades = stats.get("upgrades", [])
        if upgrades:
            upg_texts = []
            for lv, upg in enumerate(upgrades):
                cost = upg.get("cost", 0)
                upg_texts.append(f"Lv{lv+1}:${cost}")
            lines.append(f"升级: {' → '.join(upg_texts)}")

        # 计算 tooltip 尺寸（支持换行）
        pad = 8
        max_text_w = 240  # 最大文字宽度
        line_h = 20

        # 将长的行拆成多行
        wrapped_lines = []
        for line in lines:
            wrapped_lines.extend(self._wrap_text(self.font_tiny, line, max_text_w))
        lines = wrapped_lines

        tip_w = max_text_w + pad * 2
        tip_h = len(lines) * line_h + pad * 2

        # tooltip 位置（确保不越界）
        tip_x = pos[0] + 15
        tip_y = pos[1] - tip_h - 10
        if tip_x + tip_w > SCREEN_WIDTH:
            tip_x = pos[0] - tip_w - 15
        if tip_y < 0:
            tip_y = pos[1] + 20

        # 背景
        pygame.draw.rect(surface, (10, 10, 30), (tip_x, tip_y, tip_w, tip_h))
        pygame.draw.rect(surface, race_color, (tip_x, tip_y, tip_w, tip_h), 1)

        # 文字
        for j, line in enumerate(lines):
            color = COLOR_GOLD if j == 0 else (180, 180, 200)
            line_surf = self.font_tiny.render(line, True, color)
            surface.blit(line_surf, (tip_x + pad, tip_y + pad + j * line_h))

    def _draw_tabs(self, surface, mx, tab_y, race_light, race_dark):
        """绘制地面/空中分页"""
        tab_names = [
            ("ground", "地面单位"),
            ("air", "空中单位"),
        ]
        tab_w = 100
        tab_h = 24
        x = mx + 10
        for tab_key, tab_label in tab_names:
            is_active = self.build_tab == tab_key
            tab_color = race_light if is_active else race_dark
            rect = pygame.Rect(x, tab_y, tab_w, tab_h)
            self.tab_rects[tab_key] = rect

            pygame.draw.rect(surface, tab_color, rect)
            if is_active:
                pygame.draw.rect(surface, COLOR_WHITE, rect, 1)
            else:
                pygame.draw.rect(surface, (102, 102, 136), rect, 1)

            label_surf = self.font_tiny.render(tab_label, True, COLOR_WHITE)
            label_rect = label_surf.get_rect(center=rect.center)
            surface.blit(label_surf, label_rect)

            x += tab_w + 8

    def _draw_tower_menu(self, surface: pygame.Surface):
        """绘制已建塔的菜单（升级/出售）"""
        tower = self.existing_tower
        if not tower:
            return

        race_color, race_light, race_dark = self.get_race_color()

        self.upgrade_rect = None
        self.sell_rect = None
        mx, my = self._get_tower_menu_rect()

        # 背景
        pygame.draw.rect(surface, COLOR_HUD_BG, (mx, my, 300, 150))
        pygame.draw.rect(surface, race_color, (mx, my, 300, 150), 2)

        # 塔信息
        y = my + 15
        name_surf = self.font_medium.render(tower.name, True, race_light)
        surface.blit(name_surf, (mx + 10, y))
        y += 28

        info_surf = self.font_small.render(tower.debug_info(), True, (170, 170, 170))
        surface.blit(info_surf, (mx + 10, y))
        y += 35

        # 升级按钮
        if tower.can_upgrade():
            cost = tower.upgrade_cost()
            can_upgrade = self.economy.can_afford(cost)
            btn_color = COLOR_GREEN if can_upgrade else (102, 102, 102)

            upgrade_rect = pygame.Rect(mx + 15, y, 130, 36)
            self.upgrade_rect = upgrade_rect

            pygame.draw.rect(surface, btn_color, upgrade_rect)
            pygame.draw.rect(surface, COLOR_WHITE, upgrade_rect, 1)

            label = f"升级 ${cost}" if can_upgrade else f"升级 ${cost}(不足)"
            upg_surf = self.font_small.render(label, True, COLOR_WHITE)
            upg_rect = upg_surf.get_rect(center=upgrade_rect.center)
            surface.blit(upg_surf, upg_rect)
        else:
            max_surf = self.font_small.render("已满级", True, COLOR_GOLD)
            surface.blit(max_surf, (mx + 40, y + 10))

        # 出售按钮
        sell_value = tower.sell_value()
        sell_rect = pygame.Rect(mx + 155, y, 130, 36)
        self.sell_rect = sell_rect

        pygame.draw.rect(surface, COLOR_RED, sell_rect)
        pygame.draw.rect(surface, COLOR_WHITE, sell_rect, 1)

        sell_surf = self.font_small.render(f"出售 ${sell_value}", True, COLOR_WHITE)
        sell_rect_t = sell_surf.get_rect(center=sell_rect.center)
        surface.blit(sell_surf, sell_rect_t)

    def _on_build_click(self, tower_type):
        for tp, cb in self.build_callbacks:
            if tp == tower_type:
                cb(self.grid_x, self.grid_y, tower_type)
                self.hide()
                break

    def _on_upgrade_click(self):
        if self.upgrade_callback:
            self.upgrade_callback(self.existing_tower)
        self.hide()

    def _on_sell_click(self):
        if self.sell_callback:
            self.sell_callback(self.existing_tower)
        self.hide()
