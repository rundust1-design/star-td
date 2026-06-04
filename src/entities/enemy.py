"""
敌人实体 — 沿路径行走的单位
"""
import math
import pygame
from src.core.constants import COLOR_HP_BAR, COLOR_HP_BG, TILE_SIZE


class Enemy:
    """敌人"""

    sound_manager = None  # 由 game.py 设置

    ENEMY_STATS = {
        # ── 地面单位 ──
        "zergling": {"name": "小狗", "hp": 35, "speed": 80, "armor": 0,
                     "reward": 10, "damage_to_base": 1, "sprite_key": "zergling", "is_air": False},
        "hydralisk": {"name": "刺蛇", "hp": 80, "speed": 60, "armor": 1,
                      "reward": 25, "damage_to_base": 1, "sprite_key": "hydralisk", "is_air": False},
        "marine": {"name": "机枪兵", "hp": 40, "speed": 55, "armor": 0,
                   "reward": 15, "damage_to_base": 1, "sprite_key": "marine", "is_air": False},
        "zealot": {"name": "狂热者", "hp": 100, "speed": 50, "armor": 1,
                   "reward": 30, "damage_to_base": 1, "sprite_key": "zealot", "is_air": False},
        "ultralisk": {"name": "大象", "hp": 200, "speed": 45, "armor": 2,
                      "reward": 50, "damage_to_base": 2, "sprite_key": "ultralisk", "is_air": False},
        # ── 敌方地面单位（与 enemy_generator RACE_UNITS 匹配）──
        "firebat": {"name": "火焰兵", "hp": 50, "speed": 55, "armor": 0,
                    "reward": 15, "damage_to_base": 1, "sprite_key": "firebat", "is_air": False},
        "ghost": {"name": "幽灵", "hp": 60, "speed": 60, "armor": 0,
                  "reward": 20, "damage_to_base": 1, "sprite_key": "ghost", "is_air": False},
        "goliath": {"name": "巨人", "hp": 100, "speed": 50, "armor": 1,
                    "reward": 25, "damage_to_base": 1, "sprite_key": "goliath", "is_air": False},
        "siege_tank": {"name": "攻城坦克", "hp": 150, "speed": 35, "armor": 2,
                       "reward": 35, "damage_to_base": 2, "sprite_key": "siege_tank", "is_air": False},
        "dragoon": {"name": "龙骑", "hp": 100, "speed": 50, "armor": 1,
                    "reward": 25, "damage_to_base": 1, "sprite_key": "dragoon", "is_air": False},
        "high_templar": {"name": "高阶圣堂武士", "hp": 60, "speed": 50, "armor": 0,
                         "reward": 20, "damage_to_base": 1, "sprite_key": "high_templar", "is_air": False},
        "dark_templar": {"name": "黑暗圣堂武士", "hp": 80, "speed": 60, "armor": 1,
                         "reward": 30, "damage_to_base": 2, "sprite_key": "dark_templar", "is_air": False},
        "archon": {"name": "执政官", "hp": 120, "speed": 45, "armor": 1,
                   "reward": 30, "damage_to_base": 1, "sprite_key": "archon", "is_air": False},
        "lurker": {"name": "潜伏者", "hp": 90, "speed": 50, "armor": 1,
                   "reward": 25, "damage_to_base": 1, "sprite_key": "lurker", "is_air": False},
        "guardian": {"name": "守护者", "hp": 130, "speed": 45, "armor": 1,
                     "reward": 30, "damage_to_base": 1, "sprite_key": "guardian", "is_air": False},
        "queen": {"name": "女王", "hp": 80, "speed": 55, "armor": 1,
                  "reward": 25, "damage_to_base": 1, "sprite_key": "queen", "is_air": False},
        "battlecruiser": {"name": "大和舰", "hp": 200, "speed": 40, "armor": 2,
                          "reward": 50, "damage_to_base": 2, "sprite_key": "battlecruiser", "is_air": False},
        "carrier": {"name": "航空母舰", "hp": 180, "speed": 35, "armor": 2,
                    "reward": 50, "damage_to_base": 2, "sprite_key": "carrier", "is_air": False},
        "arbiter": {"name": "仲裁者", "hp": 120, "speed": 50, "armor": 1,
                    "reward": 35, "damage_to_base": 1, "sprite_key": "arbiter", "is_air": False},
        # ── 空中单位（仅从第 4 波开始出现）──
        "wraith": {"name": "科学球", "hp": 60, "speed": 70, "armor": 0,
                   "reward": 20, "damage_to_base": 1, "sprite_key": "wraith_enemy", "is_air": True},
        "valkyrie": {"name": "瓦尔基里", "hp": 120, "speed": 75, "armor": 1,
                     "reward": 35, "damage_to_base": 1, "sprite_key": "valkyrie_enemy", "is_air": True},
        "scout": {"name": "侦察机", "hp": 80, "speed": 90, "armor": 0,
                  "reward": 25, "damage_to_base": 1, "sprite_key": "scout_enemy", "is_air": True},
        "mutalisk": {"name": "飞龙", "hp": 70, "speed": 85, "armor": 0,
                     "reward": 20, "damage_to_base": 1, "sprite_key": "mutalisk_enemy", "is_air": True},
        "devourer": {"name": "吞噬者", "hp": 150, "speed": 60, "armor": 1,
                     "reward": 40, "damage_to_base": 2, "sprite_key": "devourer_enemy", "is_air": True},
    }

    def __init__(self, enemy_type: str, path):
        stats = self.ENEMY_STATS[enemy_type]
        self.type = enemy_type
        self.name = stats["name"]
        self.max_hp = stats["hp"]
        self.hp = stats["hp"]
        self.speed = stats["speed"]
        self.armor = stats["armor"]
        self.reward = stats["reward"]
        self.damage_to_base = stats["damage_to_base"]
        self.sprite_key = stats["sprite_key"]
        self.is_air = stats.get("is_air", False)  # 是否为空中单位

        self.path = path
        self.progress = 0.0
        self.alive = True
        self.reached_end = False
        self.hit_flash_timer = 0.0

        # 动画精灵
        from src.entities.sprite import PlaceholderSprite
        self.sprite = PlaceholderSprite(self.sprite_key)

        # 状态效果（由特殊单位施加）
        self.speed_multiplier = 1.0
        self.parasite_timer = 0.0
        self.parasite_dps = 0.0
        self.parasite_slow = 0.0

    def update(self, dt: float):
        if not self.alive or self.reached_end:
            return
        effective_speed = self.speed * self.speed_multiplier
        self.progress += (effective_speed * dt) / self.path.total_length
        if self.progress >= 1.0:
            self.progress = 1.0
            self.reached_end = True
        if self.hit_flash_timer > 0:
            self.hit_flash_timer -= dt

        self.sprite.update(dt)  # 更新动画

    def take_damage(self, raw_damage: float) -> int:
        actual = max(1, int(raw_damage - self.armor))
        self.hp -= actual
        self.hit_flash_timer = 0.1
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            # 死亡音效
            if self.__class__.sound_manager:
                self.__class__.sound_manager.play_event("explosion")
        return actual

    def get_position(self) -> tuple[float, float]:
        return self.path.get_position_at(self.progress)

    def get_direction(self) -> float:
        return self.path.get_direction_at(self.progress)

    def get_hp_ratio(self) -> float:
        return self.hp / self.max_hp if self.max_hp > 0 else 0.0

    def draw(self, surface: pygame.Surface):
        """在 Pygame surface 上绘制敌人"""
        if not self.alive:
            return

        x, y = self.get_position()

        self.sprite.draw(surface, x, y, self.get_direction())

        # 血条
        bar_width = 24
        bar_height = 3
        bar_x = int(x - bar_width / 2)
        bar_y = int(y - 16)

        pygame.draw.rect(surface, COLOR_HP_BG, (bar_x, bar_y, bar_width, bar_height))
        hp_ratio = self.get_hp_ratio()
        if hp_ratio > 0:
            pygame.draw.rect(surface, COLOR_HP_BAR,
                             (bar_x, bar_y, int(bar_width * hp_ratio), bar_height))

        # 寄生效果
        if self.parasite_timer > 0:
            pygame.draw.circle(surface, (180, 40, 160), (int(x), int(y)), 12, 2)
