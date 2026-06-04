"""
精灵系统 — 支持 PNG spritesheet 和占位几何图形

流程: 先尝试加载 assets/sprites/<race>/<key>.png，
如果找不到则使用几何图形占位。

帧提取使用 grp_to_png.py 同时生成的 *_meta.json 元数据文件，
通过格子公式计算每帧在 spritesheet 上的精确位置。

调试: 当 DEBUG_SAVE_FRAME 为 True 时，每次 draw() 保存一帧到磁盘
"""
import os
import json
import math
try:
    from PIL import Image as PILImage
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

DEBUG_SAVE_FRAME = False
DEBUG_FRAME_COUNT = 0

import pygame
from src.core.constants import (
    TILE_SIZE, COLOR_TERRAN, COLOR_PROTOSS, COLOR_ZERG,
    COLOR_GOLD, COLOR_GRAY, COLOR_WHITE, COLOR_RED, COLOR_YELLOW,
    COLOR_CYAN, COLOR_GREEN, COLOR_DARK, COLOR_DARKER, PROJECT_ROOT
)


class SpriteSheet:
    """加载 PNG spritesheet 并通过元数据精确提取每帧"""

    def __init__(self, path: str, num_frames: int = 1):
        self.frames = []
        try:
            # 用 PIL 裁剪每一帧，再逐帧用 frombuffer 转 Pygame surface
            pil_sheet = PILImage.open(path).convert("RGBA")
            sw, sh = pil_sheet.size
            self.frame_w = sw
            self.frame_h = sh
            num_frames = max(num_frames, 1)

            # ── 尝试加载同目录下的 *_meta.json 元数据 ──
            meta_path = os.path.splitext(path)[0] + "_meta.json"
            meta = None
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, "r", encoding="utf-8") as f:
                        meta = json.load(f)
                    # 用 meta 中的实际帧数覆盖
                    if "num_frames" in meta:
                        num_frames = meta["num_frames"]
                except Exception:
                    pass

            if meta:
                self._extract_frames_pil(pil_sheet, sw, sh, num_frames, meta)
            else:
                data = pil_sheet.tobytes()
                sheet = pygame.image.frombuffer(data, (sw, sh), 'RGBA')
                self.frames.append(sheet)

        except Exception as e:
            print(f'[SpriteSheet] 加载失败 {path}: {e}')

    def _extract_frames_pil(self, pil_sheet, sw, sh, num_frames, meta):
        """使用 PIL 裁剪每帧区域，然后通过 frombuffer 转 Pygame surface"""
        mx_ = meta.get("mx", 0)
        my_ = meta.get("my", 0)
        gap = meta.get("gap", 2)
        cols = meta.get("cols", 8)
        fw = meta.get("fw", 0)
        fh = meta.get("fh", 0)
        frame_rects = meta.get("frames", [])

        if not frame_rects or fw <= 0 or fh <= 0:
            data = pil_sheet.tobytes()
            sheet = pygame.image.frombuffer(data, (sw, sh), 'RGBA')
            self.frames.append(sheet)
            return

        cell_w = fw + gap
        cell_h = fh + gap

        for idx in range(min(num_frames, len(frame_rects))):
            fr = frame_rects[idx]
            w = fr["w"]
            h = fr["h"]
            xo = fr["xo"]
            yo = fr["yo"]
            col = idx % cols
            row = idx // cols

            fx = col * cell_w + (xo - mx_)
            fy = row * cell_h + (yo - my_)

            if fx < 0: fx = 0
            if fy < 0: fy = 0
            if fx + w > sw: w = sw - fx
            if fy + h > sh: h = sh - fy

            if w > 0 and h > 0:
                try:
                    pil_frame = pil_sheet.crop((fx, fy, fx + w, fy + h))
                    raw_data = pil_frame.tobytes()
                    pg_frame = pygame.image.frombuffer(raw_data, (w, h), 'RGBA')
                    self.frames.append(pg_frame)
                except Exception as e:
                    print(f'  [SpriteSheet] 帧{idx}提取失败: {e}')

    def __bool__(self):
        return len(self.frames) > 0

    def get_frame(self, index: int = 0):
        if not self.frames:
            return None
        return self.frames[index % len(self.frames)]


class PlaceholderSprite:
    """智能精灵 — 使用 PNG 精灵或几何图形占位，支持帧动画"""

    SPRITE_CACHE = {}  # key -> SpriteSheet
    ANIM_TIMERS = {}   # id -> (frame_index, accumulator)

    # 各单位的绘制配置（用于占位/回退）
    UNIT_DRAWINGS = {
        # ── Terran ──
        "marine":          {"race": "terran", "shape": "rect", "size": (14, 16), "color": COLOR_TERRAN, "mark": "t"},
        "firebat":         {"race": "terran", "shape": "rect", "size": (18, 18), "color": (200, 80, 30), "mark": "t"},
        "ghost":           {"race": "terran", "shape": "rect", "size": (14, 18), "color": (70, 100, 140), "mark": "t"},
        "goliath":         {"race": "terran", "shape": "rect", "size": (22, 20), "color": COLOR_TERRAN, "mark": "t", "deco": "horizontal"},
        "siege_tank":      {"race": "terran", "shape": "rect", "size": (26, 18), "color": (120, 100, 60), "mark": "t", "deco": "horizontal"},
        "battlecruiser":   {"race": "terran", "shape": "rect", "size": (28, 22), "color": (40, 60, 100), "mark": "a", "deco": "cross"},
        "wraith":          {"race": "terran", "shape": "oval", "size": (18, 14), "color": (50, 80, 120), "mark": "a"},
        "valkyrie":        {"race": "terran", "shape": "oval", "size": (20, 16), "color": (60, 90, 130), "mark": "a"},
        "bunker":          {"race": "terran", "shape": "rect", "size": (22, 18), "color": (80, 120, 60), "mark": "t", "deco": "horizontal"},
        "missile_turret":  {"race": "terran", "shape": "rect", "size": (18, 22), "color": (60, 140, 60), "mark": "t", "deco": "cross"},
        # ── Protoss ──
        "dragoon":         {"race": "protoss", "shape": "rect", "size": (20, 20), "color": (70, 60, 140), "mark": "p"},
        "archon":          {"race": "protoss", "shape": "oval", "size": (24, 24), "color": (255, 180, 40), "mark": "p"},
        "scout":           {"race": "protoss", "shape": "oval", "size": (22, 18), "color": (60, 100, 180), "mark": "a"},
        "carrier":         {"race": "protoss", "shape": "rect", "size": (30, 24), "color": (80, 70, 160), "mark": "a", "deco": "cross"},
        "arbiter":         {"race": "protoss", "shape": "oval", "size": (24, 24), "color": (60, 160, 180), "mark": "a"},
        "zealot":          {"race": "protoss", "shape": "rect", "size": (18, 20), "color": (160, 100, 220), "mark": "p"},
        "reaver":          {"race": "protoss", "shape": "rect", "size": (24, 20), "color": (140, 100, 60), "mark": "p", "deco": "cross"},
        "photon_cannon":   {"race": "protoss", "shape": "rect", "size": (20, 20), "color": (180, 160, 80), "mark": "p", "deco": "cross"},
        # ── Zerg ──
        "zergling":        {"race": "zerg", "shape": "oval", "size": (14, 10), "color": (180, 60, 60), "mark": "z"},
        "hydralisk":       {"race": "zerg", "shape": "oval", "size": (18, 12), "color": (100, 160, 60), "mark": "z"},
        "lurker":          {"race": "zerg", "shape": "oval", "size": (20, 14), "color": (80, 120, 50), "mark": "z"},
        "ultralisk":       {"race": "zerg", "shape": "rect", "size": (24, 16), "color": (120, 40, 40), "mark": "z"},
        "mutalisk":        {"race": "zerg", "shape": "oval", "size": (20, 14), "color": (60, 140, 60), "mark": "a"},
        "guardian":        {"race": "zerg", "shape": "oval", "size": (22, 18), "color": (80, 160, 80), "mark": "a"},
        "devourer":        {"race": "zerg", "shape": "oval", "size": (20, 16), "color": (100, 80, 60), "mark": "a"},
        "queen":           {"race": "zerg", "shape": "oval", "size": (20, 20), "color": (140, 40, 120), "mark": "a"},
        "sunken_colony":   {"race": "zerg", "shape": "oval", "size": (22, 18), "color": (80, 160, 60), "mark": "z", "deco": "horizontal"},
        "spore_colony":    {"race": "zerg", "shape": "oval", "size": (20, 22), "color": (100, 180, 80), "mark": "z"},
        # ── 敌人 ──
        "marine_enemy":    {"race": "terran", "shape": "rect", "size": (12, 14), "color": COLOR_TERRAN},
        "zealot_enemy":    {"race": "protoss", "shape": "rect", "size": (16, 16), "color": COLOR_PROTOSS},
        "zergling_enemy":  {"race": "zerg", "shape": "oval", "size": (14, 10), "color": (180, 60, 60)},
        "hydralisk_enemy": {"race": "zerg", "shape": "oval", "size": (18, 12), "color": (100, 160, 60)},
        "ultralisk_enemy": {"race": "zerg", "shape": "rect", "size": (22, 14), "color": (120, 40, 40)},
        # ── 空中敌人 ──
        "wraith_enemy":    {"race": "terran", "shape": "oval", "size": (18, 14), "color": (50, 80, 120)},
        "valkyrie_enemy":  {"race": "terran", "shape": "oval", "size": (20, 16), "color": (60, 90, 130)},
        "scout_enemy":     {"race": "protoss", "shape": "oval", "size": (22, 18), "color": (60, 100, 180)},
        "mutalisk_enemy":  {"race": "zerg", "shape": "oval", "size": (20, 14), "color": (60, 140, 60)},
        "devourer_enemy":  {"race": "zerg", "shape": "oval", "size": (20, 16), "color": (100, 80, 60)},
        # ── 投射物 ──
        "bullet":          {"shape": "oval", "size": (4, 4), "color": COLOR_YELLOW},
        "cannon_shot":     {"shape": "oval", "size": (6, 6), "color": COLOR_CYAN},
        "spine":           {"shape": "rect", "size": (3, 8), "color": COLOR_GREEN},
        "bullet_grenade":   {"shape": "oval", "size": (6, 6), "color": (200, 120, 40)},
        "bullet_hks":       {"shape": "oval", "size": (5, 5), "color": (80, 120, 255)},
        "bullet_explo1":    {"shape": "oval", "size": (12, 12), "color": (255, 150, 50)},
        "psiblade":         {"shape": "oval", "size": (8, 4), "color": (180, 100, 255)},
        "bullet_dragbull":  {"shape": "rect", "size": (6, 4), "color": (180, 180, 100)},
        "bullet_ephfire":   {"shape": "oval", "size": (8, 6), "color": (255, 100, 30)},
        "bullet_eycbull":   {"shape": "oval", "size": (10, 8), "color": (60, 255, 60)},
        "bullet_epbbul":    {"shape": "oval", "size": (8, 6), "color": (100, 200, 255)},
        "explosion":       {"shape": "oval", "size": (12, 12), "color": (255, 200, 50)},
    }

    # 动画速度配置 (毫秒/帧) — 按帧数分档
    # 帧数越多→切换越快（看起来流畅），帧数少→切换慢些（不会闪）
    @classmethod
    def _anim_speed(cls, num_frames: int) -> float:
        """根据帧数返回合适的帧切换间隔（秒）"""
        if num_frames <= 1:
            return 0  # 不动画
        if num_frames <= 17:
            return 0.18
        if num_frames <= 50:
            return 0.12
        if num_frames <= 100:
            return 0.10
        return 0.09  # 大量帧时快速播放

    # 每个兵种的动画配置
    ANIM_CONFIG = {
        # key: (走路帧数, 攻击帧起始, 攻击帧数, 走路速度, 攻击速度)
        "marine":          (16, 20, 8, 0.10, 0.06),
        "firebat":         (12, 14, 6, 0.12, 0.08),
        "ghost":           (12, 14, 6, 0.10, 0.08),
        "goliath":         (16, 20, 8, 0.12, 0.08),
        "siege_tank":      (16, 20, 8, 0.15, 0.10),
        "battlecruiser":   (16,  0, 0, 0.15, 0.10),
        "wraith":          (1,   0, 0, 0,    0),
        "valkyrie":        (16,  0, 0, 0.12, 0.08),
        "dragoon":         (16, 20, 8, 0.10, 0.08),
        "zealot":          (16, 20, 8, 0.10, 0.08),
        "archon":          (12,  0, 0, 0.12, 0.08),
        "reaver":          (1,   0, 0, 0,    0),
        "scout":           (16, 20, 8, 0.12, 0.08),
        "carrier":         (16,  0, 0, 0.15, 0.10),
        "arbiter":         (16, 20, 6, 0.12, 0.08),
        "zergling":        (16, 20, 8, 0.08, 0.05),
        "hydralisk":       (16, 20, 8, 0.10, 0.06),
        "lurker":          (10, 12, 6, 0.12, 0.08),
        "ultralisk":       (12, 16, 8, 0.12, 0.08),
        "mutalisk":        (12, 16, 6, 0.10, 0.08),
        "guardian":        (12, 16, 6, 0.12, 0.08),
        "devourer":        (12, 16, 6, 0.10, 0.08),
        "queen":           (12, 16, 6, 0.12, 0.08),
        # 防御建筑
        "bunker":          (1,   0, 0, 0,    0),
        "missile_turret":  (1,   0, 0, 0,    0),
        "photon_cannon":   (1,   0, 0, 0,    0),
        "sunken_colony":   (1,   0, 0, 0,    0),
        "spore_colony":    (1,   0, 0, 0,    0),
        # 敌人
        "marine_enemy":    (16, 20, 8, 0.10, 0.06),
        "zealot_enemy":    (16, 20, 8, 0.10, 0.06),
        "zergling_enemy":  (16, 20, 8, 0.08, 0.05),
        "hydralisk_enemy": (16, 20, 8, 0.10, 0.06),
        "ultralisk_enemy": (12, 16, 8, 0.12, 0.08),
        # 空中敌人
        "wraith_enemy":    (1,   0, 0, 0,    0),
        "valkyrie_enemy":  (16,  0, 0, 0.12, 0.08),
        "scout_enemy":     (16, 20, 8, 0.12, 0.08),
        "mutalisk_enemy":  (12, 16, 6, 0.10, 0.08),
        "devourer_enemy":  (12, 16, 6, 0.10, 0.08),
        # 投射物
        "bullet":          (4,   0, 0, 0.08, 0),
        "cannon_shot":     (6,   0, 0, 0.08, 0),
        "spine":           (4,   0, 0, 0.10, 0),
        "bullet_grenade":   (4,   0, 0, 0.08, 0),
        "bullet_hks":       (17,  0, 0, 0.08, 0),
        "bullet_explo1":    (10,  0, 0, 0.08, 0),
        "bullet_dragbull":  (5,   0, 0, 0.08, 0),
        "bullet_ephfire":   (12,  0, 0, 0.08, 0),
        "bullet_eycbull":   (68,  0, 0, 0.08, 0),
        "bullet_epbbul":    (11,  0, 0, 0.08, 0),
        "explosion":       (1,   0, 0, 0,    0),
        "psiblade":        (6,   0, 0, 0.08, 0),
    }

    # 已知的 PNG spritesheet 帧数 (meta.json 会覆盖，这里为初始值)
    PNG_FRAME_COUNTS = {
        "marine": 229, "firebat": 170, "ghost": 229, "goliath": 170,
        "siege_tank": 51, "battlecruiser": 17, "wraith": 1, "valkyrie": 17,
        "bunker": 2, "missile_turret": 3,
        "dragoon": 415, "archon": 27, "scout": 34, "carrier": 17, "arbiter": 34,
        "zealot": 1, "reaver": 1, "psiblade": 6,
        "photon_cannon": 4, "sunken_colony": 1, "spore_colony": 1,
        "zergling": 296, "hydralisk": 297, "lurker": 34, "ultralisk": 265,
        "mutalisk": 85, "guardian": 119, "devourer": 85, "queen": 187,
        "bullet": 17, "cannon_shot": 27, "spine": 10, "explosion": 1,
    }

    SPRITES_DIR = os.path.join(PROJECT_ROOT, "assets", "sprites")

    @classmethod
    def _get_sheet(cls, key: str) -> SpriteSheet | None:
        if key in cls.SPRITE_CACHE:
            return cls.SPRITE_CACHE[key]

        cfg = cls.UNIT_DRAWINGS.get(key, {})
        race = cfg.get("race", "terran")
        frame_count = cls.PNG_FRAME_COUNTS.get(key, 1)
        path = os.path.join(cls.SPRITES_DIR, race, f"{key}.png")
        sheet = SpriteSheet(path, frame_count)
        cls.SPRITE_CACHE[key] = sheet if sheet else None
        return cls.SPRITE_CACHE[key]

    def __init__(self, key: str):
        self.key = key
        self.cfg = self.UNIT_DRAWINGS.get(key, self.UNIT_DRAWINGS.get("marine", {}))
        self._sheet = None
        self._anim_timer = 0.0
        self._frame_index = 0
        self._anim_speed_val = 0.1
        self.scale = 1.0  # 缩放系数（投射物按伤害调整）

        # 动画帧范围（来自 ANIM_CONFIG）
        cfg = self.ANIM_CONFIG.get(key, self.ANIM_CONFIG.get("marine", (16, 0, 0, 0.10, 0)))
        self._walk_end = cfg[0]          # 走路帧结束
        self._attack_start = cfg[1]      # 攻击帧起始
        self._attack_count = cfg[2]      # 攻击帧数
        self._walk_speed = cfg[3]        # 走路速度
        self._attack_speed = cfg[4] if len(cfg) > 4 else self._walk_speed

        self._anim_start = 0
        self._anim_end = max(1, self._walk_end)
        self._speed = self._walk_speed
        self._attacking = False
        self._attack_frame = 0

    @property
    def sheet(self) -> SpriteSheet | None:
        if self._sheet is None:
            self._sheet = self._get_sheet(self.key)
        return self._sheet

    def set_attacking(self, attacking: bool):
        """设置攻击状态 — 切换到攻击动画帧范围"""
        if attacking == self._attacking:
            return
        self._attacking = attacking
        if attacking and self._attack_count > 0:
            self._anim_start = self._attack_start
            self._anim_end = self._attack_start + self._attack_count
            self._frame_index = self._anim_start
            self._speed = self._attack_speed
        else:
            self._anim_start = 0
            self._anim_end = max(1, self._walk_end)
            self._frame_index = 0
            self._speed = self._walk_speed
        self._anim_timer = 0.0

    def update(self, dt: float):
        """更新动画计时 — 需要在游戏循环中调用"""
        sheet = self.sheet
        if not sheet:
            return
        n = len(sheet.frames)
        if n <= 1:
            self._frame_index = 0
            return

        end = min(self._anim_end, n)
        if end <= self._anim_start:
            self._frame_index = 0
            return

        self._anim_timer += dt
        if self._speed > 0 and self._anim_timer >= self._speed:
            self._anim_timer = 0
            self._frame_index += 1
            if self._frame_index >= end:
                if self._attacking:
                    self._frame_index = self._anim_start  # 攻击循环
                else:
                    self._frame_index = self._anim_start  # 走路循环

    def draw(self, surface: pygame.Surface, x: float, y: float, angle: float = 0,
             scale_to: tuple[int, int] | None = None):
        """绘制精灵 — 使用当前动画帧"""
        sheet = self.sheet
        if sheet:
            frame = sheet.get_frame(self._frame_index)
            if frame:
                frame = frame.convert_alpha(surface)
                # 应用缩放
                s = self.scale
                if scale_to:
                    s = 1.0
                if s != 1.0:
                    w, h = frame.get_size()
                    nw, nh = max(1, int(w * s)), max(1, int(h * s))
                    frame = pygame.transform.smoothscale(frame, (nw, nh))
                rect = frame.get_rect(center=(int(x), int(y)))
                surface.blit(frame, rect)
                return
        self._draw_placeholder(surface, x, y, angle)

    def _draw_placeholder(self, surface, x, y, angle):
        cfg = self.cfg
        shape = cfg.get("shape", "rect")
        w, h = cfg.get("size", (16, 16))
        color = cfg.get("color", COLOR_GRAY)

        s = pygame.Surface((max(w, h) + 4, max(w, h) + 4), pygame.SRCALPHA)
        ox = (s.get_width() - w) // 2
        oy = (s.get_height() - h) // 2

        if shape == "rect":
            pygame.draw.rect(s, color, (ox, oy, w, h))
            deco = cfg.get("deco", "none")
            if deco == "cross":
                pygame.draw.line(s, COLOR_GOLD, (ox, oy), (ox + w, oy + h), 2)
                pygame.draw.line(s, COLOR_GOLD, (ox + w, oy), (ox, oy + h), 2)
            elif deco == "horizontal":
                pygame.draw.line(s, COLOR_WHITE, (ox + 2, oy + h // 2), (ox + w - 2, oy + h // 2), 2)
        else:
            pygame.draw.ellipse(s, color, (ox, oy, w, h))

        pygame.draw.rect(s, (255, 255, 255, 100), (ox, oy, w, h), 1)

        if angle != 0:
            s = pygame.transform.rotate(s, -math.degrees(angle))
        rect = s.get_rect(center=(int(x), int(y)))
        surface.blit(s, rect)
