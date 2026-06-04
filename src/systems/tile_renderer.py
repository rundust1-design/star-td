"""
地形渲染系统 — 将星际争霸 tileset 数据绘制到 Pygame 画布

流程:
  1. 从 map_parser 的 extract_level_data() 获取 tiles (32×20 tile ID 矩阵)
  2. 根据 tileset_id 选择对应的调色板
  3. 用程序化规则为每个 tile ID 生成颜色纹理
  4. 支持未来用 PNG 贴图替换程序化渲染

先程序化颜色渲染，后续通过 png 贴图替换。
"""
import os
import random
import pygame
from src.core.constants import (
    TILE_SIZE, ASSETS_DIR
)

# ── Tileset 调色板 ──
# 每个 tileset 有 4 种基本地形色: main, dirt, grass, rock, water, lava, etc.
# 颜色用 (R, G, B) 元组。取自 SC 原始 tileset 的大致色调。

TILESET_COLORS = {
    0: {  # badlands — 荒凉之地
        "name": "badlands",
        "main": (88, 68, 40),
        "dirt": (106, 78, 48),
        "grass": (60, 85, 35),
        "rock": (100, 82, 54),
        "water": (52, 60, 72),
        "lava": None,
    },
    1: {  # space — 太空平台
        "name": "space",
        "main": (50, 50, 60),
        "dirt": (38, 38, 48),
        "grass": None,
        "rock": (72, 72, 85),
        "water": None,
        "lava": None,
    },
    2: {  # installation — 基地设施
        "name": "installation",
        "main": (60, 60, 65),
        "dirt": (45, 45, 50),
        "grass": None,
        "rock": (75, 75, 82),
        "water": None,
        "lava": None,
    },
    3: {  # ashworld — 灰烬世界
        "name": "ashworld",
        "main": (70, 55, 45),
        "dirt": (55, 42, 35),
        "grass": (50, 65, 45),
        "rock": (82, 68, 55),
        "water": (48, 54, 60),
        "lava": None,
    },
    4: {  # jungle — 丛林
        "name": "jungle",
        "main": (25, 58, 30),
        "dirt": (65, 50, 32),
        "grass": (15, 70, 20),
        "rock": (80, 72, 55),
        "water": (35, 55, 70),
        "lava": None,
    },
    5: {  # desert — 沙漠
        "name": "desert",
        "main": (120, 88, 48),
        "dirt": (140, 100, 55),
        "grass": (90, 105, 45),
        "rock": (112, 95, 65),
        "water": None,
        "lava": None,
    },
    6: {  # arctic — 北极
        "name": "arctic",
        "main": (150, 155, 165),
        "dirt": (120, 125, 135),
        "grass": None,
        "rock": (100, 105, 115),
        "water": (60, 75, 100),
        "lava": None,
    },
    7: {  # twilight — 暮光
        "name": "twilight",
        "main": (72, 48, 72),
        "dirt": (55, 38, 55),
        "grass": (40, 55, 35),
        "rock": (85, 62, 80),
        "water": (38, 30, 55),
        "lava": (140, 50, 20),
    },
    8: {  # ice — 冰原
        "name": "ice",
        "main": (160, 175, 190),
        "dirt": (130, 145, 160),
        "grass": None,
        "rock": (112, 125, 138),
        "water": (55, 70, 95),
        "lava": None,
    },
}

# Tile ID 范围 → 地形类型映射（StarCraft 标准 tile 分区）
# 这些分区在不同 tileset 中略有差异，这里取通用近似
TILE_TERRAIN = {}


def _build_tile_terrain_map():
    """构建 tile_id → 地形类型映射"""
    global TILE_TERRAIN
    if TILE_TERRAIN:
        return

    m = {}
    for tid in range(1024):
        if tid < 16:
            m[tid] = "main"          # 基础地形
        elif tid < 32:
            m[tid] = "dirt"          # 泥土变体
        elif tid < 48:
            m[tid] = "grass"         # 草地
        elif tid < 64:
            m[tid] = "rock"          # 岩石
        elif tid < 80:
            m[tid] = "water"         # 水域
        elif tid < 96:
            m[tid] = "dirt"          # 更多泥土
        elif tid < 112:
            m[tid] = "grass"         # 更多草地
        elif tid < 128:
            m[tid] = "rock"          # 更多岩石
        elif tid < 160:
            m[tid] = "main"          # 基础变体
        elif tid < 196:
            m[tid] = "dirt"          # 泥土过渡
        elif tid < 256:
            m[tid] = "rock"          # 岩石过渡/装饰
        elif tid < 400:
            m[tid] = "main"          # 特殊地形
        elif tid < 600:
            m[tid] = "rock"          # 建筑地基
        else:
            m[tid] = "main"          # 其他默认为基础地形
    TILE_TERRAIN = m


_build_tile_terrain_map()


def _clamp(c: int) -> int:
    return max(0, min(255, c))


def _generate_tile_surface(tile_id: int, palette: dict) -> pygame.Surface:
    """为一个 tile_id 生成程序化颜色 surface（32×32）"""
    surf = pygame.Surface((TILE_SIZE, TILE_SIZE))
    terrain_type = TILE_TERRAIN.get(tile_id, "main")

    base = palette.get(terrain_type) or palette.get("main", (80, 60, 40))

    # 用 tile_id 做伪随机种子，确保颜色一致
    rng = random.Random(tile_id * 131 + 7)

    # 生成基础色块（绝大多数）
    surf.fill(base)

    # 添加纹理噪点（微小的颜色变化）
    # 约 20% 的像素做 ±10 的随机偏移
    for _ in range(TILE_SIZE * TILE_SIZE // 5):
        px = rng.randint(0, TILE_SIZE - 1)
        py = rng.randint(0, TILE_SIZE - 1)
        shade = rng.randint(-10, 10)
        r = _clamp(base[0] + shade)
        g = _clamp(base[1] + shade)
        b = _clamp(base[2] + shade)
        surf.set_at((px, py), (r, g, b))

    # 根据地形类型添加特殊纹理
    if terrain_type == "rock":
        # 岩石小斑块
        for _ in range(3):
            rx = rng.randint(2, TILE_SIZE - 4)
            ry = rng.randint(2, TILE_SIZE - 4)
            rw, rh = rng.randint(4, 10), rng.randint(3, 6)
            shade_c = rng.randint(8, 18)
            rc = (_clamp(base[0] + shade_c), _clamp(base[1] + shade_c), _clamp(base[2] + shade_c))
            pygame.draw.rect(surf, rc, (rx, ry, rw, rh))
    elif terrain_type == "grass":
        # 草点
        for _ in range(6):
            gx = rng.randint(0, TILE_SIZE - 1)
            gy = rng.randint(0, TILE_SIZE - 1)
            green_shade = rng.randint(-8, 12)
            gc = (_clamp(base[0]), _clamp(base[1] + green_shade), _clamp(base[2]))
            surf.set_at((gx, gy), gc)
            if gx + 1 < TILE_SIZE:
                surf.set_at((gx + 1, gy), gc)
    elif terrain_type == "water":
        # 水波纹
        for _ in range(4):
            wx = rng.randint(0, TILE_SIZE - 1)
            wy = rng.randint(0, TILE_SIZE - 1)
            wlen = rng.randint(4, 12)
            wc = (_clamp(base[0] + 5), _clamp(base[1] + 8), _clamp(base[2] + 5))
            for i in range(wlen):
                if wx + i < TILE_SIZE:
                    surf.set_at((wx + i, wy), wc)
    elif terrain_type == "dirt":
        # 泥土点
        for _ in range(4):
            dx = rng.randint(2, TILE_SIZE - 3)
            dy = rng.randint(2, TILE_SIZE - 3)
            dc = (_clamp(base[0] + rng.randint(-6, 6)), _clamp(base[1] + rng.randint(-6, 6)),
                  _clamp(base[2] + rng.randint(-6, 6)))
            pygame.draw.circle(surf, dc, (dx, dy), rng.randint(1, 3))

    # 轻微边缘变化（不是纯色块）
    for side in range(4):
        for _ in range(3):
            sp = rng.randint(0, TILE_SIZE - 1)
            if side == 0:   # 顶部
                px, py = sp, rng.randint(0, 2)
            elif side == 1:  # 右侧
                px, py = TILE_SIZE - 1 - rng.randint(0, 2), sp
            elif side == 2:  # 底部
                px, py = sp, TILE_SIZE - 1 - rng.randint(0, 2)
            else:  # 左侧
                px, py = rng.randint(0, 2), sp
            shade_e = rng.randint(-6, 6)
            se = (_clamp(base[0] + shade_e), _clamp(base[1] + shade_e), _clamp(base[2] + shade_e))
            surf.set_at((px, py), se)

    return surf


class TilesetRenderer:
    """地形渲染器 — 管理程序化 tile 缓存与渲染"""

    def __init__(self, tileset_id: int):
        self.tileset_id = tileset_id
        self.palette = TILESET_COLORS.get(tileset_id, TILESET_COLORS[0])
        self._cache: dict[int, pygame.Surface] = {}
        self._png_loaded = False
        self._png_dir = os.path.join(ASSETS_DIR, "tilesets", self.palette["name"])

    def get_tile(self, tile_id: int) -> pygame.Surface:
        """获取指定 tile_id 的 surface（缓存命中则返回，未命中则生成）"""
        if tile_id in self._cache:
            return self._cache[tile_id]

        # 尝试从 PNG 加载（如果已有预处理好的贴图）
        if not self._png_loaded:
            self._try_load_pngs()

        # 生成程序化 surface
        surf = _generate_tile_surface(tile_id, self.palette)
        self._cache[tile_id] = surf
        return surf

    def _try_load_pngs(self):
        """尝试加载预处理好的 PNG 贴图"""
        self._png_loaded = True
        if not os.path.isdir(self._png_dir):
            return

        # 查找 tile_*.png 文件
        for fn in os.listdir(self._png_dir):
            if fn.startswith("tile_") and fn.endswith(".png"):
                try:
                    tid_str = fn[5:-4]  # "tile_123.png" → "123"
                    tid = int(tid_str)
                    path = os.path.join(self._png_dir, fn)
                    surf = pygame.image.load(path).convert_alpha()
                    # 缩放到 TILE_SIZE
                    if surf.get_width() != TILE_SIZE or surf.get_height() != TILE_SIZE:
                        surf = pygame.transform.smoothscale(surf, (TILE_SIZE, TILE_SIZE))
                    self._cache[tid] = surf
                except (ValueError, OSError):
                    continue

    def render_terrain(self, target: pygame.Surface, tiles: list[list[int]],
                       offset_x: int = 0, offset_y: int = 0):
        """批量渲染地形格子到 target surface

        参数:
            target: 目标 surface
            tiles: 二维 tile ID 矩阵 [row][col]
            offset_x/y: 渲染偏移（像素）
        """
        for row_idx, row in enumerate(tiles):
            for col_idx, tile_id in enumerate(row):
                surf = self.get_tile(tile_id)
                px = offset_x + col_idx * TILE_SIZE
                py = offset_y + row_idx * TILE_SIZE
                target.blit(surf, (px, py))

    def clear_cache(self):
        """清除缓存（例如切换 tileset 时）"""
        self._cache.clear()
        self._png_loaded = False
