"""
StarCraft Tower Defense - 常量定义
"""

import os

# ── 路径 ──
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SC_DIR = os.path.join(PROJECT_ROOT, "StarCraft108B")
ASSETS_DIR = os.path.join(PROJECT_ROOT, "assets")
EXTRACTED_DIR = os.path.join(ASSETS_DIR, "extracted", "spritesheets")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")
LEVELS_DIR = os.path.join(DATA_DIR, "levels")
MAPS_DIR = os.path.join(SC_DIR, "MAPS")

# ── 显示 ──
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
HUD_HEIGHT = 110                   # 底部 HUD 栏高度
PLAY_AREA_TOP = 0
PLAY_AREA_HEIGHT = SCREEN_HEIGHT - HUD_HEIGHT  # 658
FPS = 60

# ── 网格 ──
TILE_SIZE = 32
GRID_COLS = SCREEN_WIDTH // TILE_SIZE      # 32
GRID_ROWS = PLAY_AREA_HEIGHT // TILE_SIZE  # 20 (658 // 32 = 20)

# ── 颜色 (Pygame RGB 元组) ──
COLOR_WHITE = (255, 255, 255)
COLOR_BLACK = (0, 0, 0)
COLOR_RED = (255, 51, 51)
COLOR_GREEN = (51, 255, 51)
COLOR_BLUE = (51, 136, 255)
COLOR_YELLOW = (255, 255, 68)
COLOR_ORANGE = (255, 136, 0)
COLOR_PURPLE = (170, 68, 255)
COLOR_CYAN = (68, 255, 255)
COLOR_GRAY = (136, 136, 136)
COLOR_DARK = (26, 26, 46)
COLOR_DARKER = (15, 15, 26)
COLOR_HUD_BG = (30, 30, 48)
COLOR_PATH = (30, 30, 30)        # 柏油马路（深灰/黑）
COLOR_PATH_BORDER = (50, 50, 50) # 柏油马路边缘
COLOR_GRID_LINE = (42, 42, 62)
COLOR_VALID_PLACEMENT = (0, 51, 0)
COLOR_INVALID_PLACEMENT = (51, 0, 0)
COLOR_TOWER_RANGE = (0, 51, 102)
COLOR_HP_BAR = (68, 255, 68)
COLOR_HP_BG = (51, 51, 51)
COLOR_GOLD = (255, 215, 0)
COLOR_TERRAN = (74, 127, 181)
COLOR_TERRAN_LIGHT = (120, 180, 230)
COLOR_TERRAN_DARK = (40, 70, 110)
COLOR_PROTOSS = (138, 95, 181)
COLOR_PROTOSS_LIGHT = (190, 140, 230)
COLOR_PROTOSS_DARK = (80, 50, 120)
COLOR_ZERG = (106, 122, 42)
COLOR_ZERG_LIGHT = (150, 170, 70)
COLOR_ZERG_DARK = (60, 70, 20)

# 种族主题
RACE_CONFIG = {
    "terran": {
        "name": "人族 Terran",
        "color": COLOR_TERRAN,
        "color_light": COLOR_TERRAN_LIGHT,
        "color_dark": COLOR_TERRAN_DARK,
        "btn_color": (50, 80, 130),
        "btn_hover": (60, 100, 170),
    },
    "protoss": {
        "name": "神族 Protoss",
        "color": COLOR_PROTOSS,
        "color_light": COLOR_PROTOSS_LIGHT,
        "color_dark": COLOR_PROTOSS_DARK,
        "btn_color": (100, 60, 140),
        "btn_hover": (130, 80, 180),
    },
    "zerg": {
        "name": "虫族 Zerg",
        "color": COLOR_ZERG,
        "color_light": COLOR_ZERG_LIGHT,
        "color_dark": COLOR_ZERG_DARK,
        "btn_color": (80, 90, 30),
        "btn_hover": (110, 120, 50),
    },
}

# ── 游戏参数 ──
STARTING_MONEY = 200
STARTING_LIVES = 20
SELL_REFUND_RATIO = 1.0           # 出售退还比例（全额退款）

# ── 地图/关卡 ──
TILESETS_DIR = os.path.join(ASSETS_DIR, "tilesets")
LEVELS_CACHE_DIR = os.path.join(DATA_DIR, "levels", "cached")
CACHED_MAPS_FILE = os.path.join(LEVELS_CACHE_DIR, "_map_index.json")

# ── 动画 ──
ANIM_SPEED = 0.15                  # 帧切换间隔（秒）

# ── 文件扩展 ──
STARDAT_MPQ = os.path.join(SC_DIR, "StarDat.mpq")
BROODAT_MPQ = os.path.join(SC_DIR, "BrooDat.mpq")

# ── 字体 ──
FONT_PATH = "C:/Windows/Fonts/msyh.ttc"  # 微软雅黑，支持中文


def make_font(size: int) -> "pygame.font.Font":
    """创建支持中文的字体"""
    import pygame
    try:
        return pygame.font.Font(FONT_PATH, size)
    except Exception:
        return pygame.font.Font(None, size)
