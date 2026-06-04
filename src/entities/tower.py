"""
塔实体 — 部署为炮台的兵种
"""
import math
import pygame
from src.core.constants import (
    TILE_SIZE, COLOR_TOWER_RANGE,
    SELL_REFUND_RATIO, COLOR_GOLD, COLOR_WHITE, make_font
)
from src.entities.sprite import PlaceholderSprite
from src.entities.projectile import Projectile
from src.systems.targeting import TargetingSystem


class Tower:
    """部署的单位（不可移动的炮台）"""

    sound_manager = None  # 由 game.py 设置

    RACE_TOWERS = {
        "terran": ["marine", "firebat", "ghost", "goliath", "siege_tank", "wraith", "battlecruiser", "valkyrie", "bunker", "missile_turret"],
        "protoss": ["zealot", "dragoon", "archon", "scout", "carrier", "arbiter", "reaver", "photon_cannon"],
        "zerg": ["zergling", "hydralisk", "lurker", "ultralisk", "mutalisk", "guardian", "devourer", "queen", "sunken_colony", "spore_colony"],
    }

    TOWER_STATS = {
        # ── Terran ──
        "marine": {
            "name": "机枪兵", "race": "terran",
            "cost": 50, "damage": 6, "range": 128, "fire_rate": 0.5,
            "targets": "both", "splash": False, "sprite_key": "marine",
            "proj_key": "bullet_dragbull", "proj_speed": 500,
            "upgrades": [
                {"cost": 50, "damage_bonus": 3, "range_bonus": 8, "fire_rate_bonus": -0.05},
                {"cost": 100, "damage_bonus": 6, "range_bonus": 16, "fire_rate_bonus": -0.1},
            ]
        },
        "firebat": {
            "name": "火焰兵", "race": "terran",
            "cost": 50, "damage": 8, "range": 80, "fire_rate": 0.7,
            "targets": "ground", "splash": False, "sprite_key": "firebat",
            "proj_key": "bullet_ephfire", "proj_speed": 400,
            "upgrades": [
                {"cost": 50, "damage_bonus": 4, "range_bonus": 8, "fire_rate_bonus": -0.05},
                {"cost": 100, "damage_bonus": 8, "range_bonus": 16, "fire_rate_bonus": -0.1},
            ]
        },
        "ghost": {
            "name": "幽灵", "race": "terran",
            "cost": 75, "damage": 10, "range": 192, "fire_rate": 1.0,
            "targets": "both", "splash": False, "sprite_key": "ghost",
            "proj_key": "bullet_epbbul", "proj_speed": 600,
            "upgrades": [
                {"cost": 75, "damage_bonus": 5, "range_bonus": 32, "fire_rate_bonus": -0.1},
                {"cost": 150, "damage_bonus": 10, "range_bonus": 48, "fire_rate_bonus": -0.15},
            ]
        },
        "goliath": {
            "name": "巨人", "race": "terran",
            "cost": 100, "damage": 12, "range": 192, "fire_rate": 1.2,
            "targets": "both", "splash": False, "sprite_key": "goliath",
            "proj_key": "bullet_grenade", "proj_speed": 500,
            "upgrades": [
                {"cost": 100, "damage_bonus": 6, "range_bonus": 16, "fire_rate_bonus": -0.1},
                {"cost": 200, "damage_bonus": 12, "range_bonus": 32, "fire_rate_bonus": -0.15},
            ]
        },
        "siege_tank": {
            "name": "攻城坦克", "race": "terran",
            "cost": 150, "damage": 30, "range": 256, "fire_rate": 2.0,
            "targets": "ground", "splash": True, "splash_radius": 48, "sprite_key": "siege_tank",
            "proj_key": "bullet_explo1", "proj_speed": 600,
            "upgrades": [
                {"cost": 150, "damage_bonus": 15, "range_bonus": 64, "fire_rate_bonus": -0.2},
                {"cost": 300, "damage_bonus": 30, "range_bonus": 96, "fire_rate_bonus": -0.3},
            ]
        },
        "wraith": {
            "name": "科学球", "race": "terran",
            "cost": 150, "damage": 8, "range": 160, "fire_rate": 1.0,
            "targets": "both", "splash": False, "sprite_key": "wraith",
            "proj_key": "bullet_epbbul", "proj_speed": 600,
            "is_air": True,
            "upgrades": [
                {"cost": 100, "damage_bonus": 4, "range_bonus": 16, "fire_rate_bonus": -0.1},
                {"cost": 200, "damage_bonus": 8, "range_bonus": 32, "fire_rate_bonus": -0.15},
            ]
        },
        "battlecruiser": {
            "name": "大和舰", "race": "terran",
            "cost": 400, "damage": 25, "range": 256, "fire_rate": 1.5,
            "targets": "both", "splash": False, "sprite_key": "battlecruiser",
            "proj_key": "bullet_hks", "proj_speed": 500,
            "is_air": True,
            "upgrades": [
                {"cost": 300, "damage_bonus": 15, "range_bonus": 32, "fire_rate_bonus": -0.2},
                {"cost": 500, "damage_bonus": 25, "range_bonus": 64, "fire_rate_bonus": -0.3},
            ]
        },
        "valkyrie": {
            "name": "瓦尔基里", "race": "terran",
            "cost": 250, "damage": 6, "range": 192, "fire_rate": 0.3,
            "targets": "air", "splash": True, "splash_radius": 32, "sprite_key": "valkyrie",
            "is_air": True,
            "proj_key": "bullet_eycbull", "proj_speed": 700,
            "upgrades": [
                {"cost": 200, "damage_bonus": 3, "range_bonus": 16, "fire_rate_bonus": -0.05},
                {"cost": 300, "damage_bonus": 6, "range_bonus": 32, "fire_rate_bonus": -0.08},
            ]
        },

        # ── Terran 防御建筑 ──
        "bunker": {
            "name": "碉堡", "race": "terran",
            "cost": 100, "damage": 12, "range": 160, "fire_rate": 0.6,
            "targets": "ground", "splash": False, "sprite_key": "bunker",
            "proj_key": "bullet_dragbull", "proj_speed": 1500,
            "upgrades": [
                {"cost": 100, "damage_bonus": 6, "range_bonus": 16, "fire_rate_bonus": -0.05},
                {"cost": 200, "damage_bonus": 12, "range_bonus": 32, "fire_rate_bonus": -0.1},
            ]
        },
        "missile_turret": {
            "name": "导弹塔", "race": "terran",
            "cost": 75, "damage": 15, "range": 256, "fire_rate": 1.0,
            "targets": "air", "splash": False, "sprite_key": "missile_turret",
            "proj_key": "bullet_hks", "proj_speed": 600,
            "upgrades": [
                {"cost": 75, "damage_bonus": 8, "range_bonus": 32, "fire_rate_bonus": -0.1},
                {"cost": 150, "damage_bonus": 15, "range_bonus": 48, "fire_rate_bonus": -0.15},
            ]
        },

        # ── Protoss ──
        "zealot": {
            "name": "狂热者", "race": "protoss",
            "cost": 50, "damage": 8, "range": 48, "fire_rate": 0.6,
            "targets": "ground", "splash": False, "sprite_key": "zealot",
            "proj_key": "psiblade", "proj_speed": 0,
            "special": "psionic_blade",
            "psionic_blade_damage": 25,
            "psionic_blade_range": 192,
            "psionic_blade_cooldown": 8.0,
            "psionic_blade_proj_speed": 800,
            "upgrades": [
                {"cost": 50, "damage_bonus": 4, "psionic_blade_damage": 10,
                 "fire_rate_bonus": -0.05, "psionic_blade_cooldown": -1.0},
                {"cost": 100, "damage_bonus": 8, "psionic_blade_damage": 15,
                 "fire_rate_bonus": -0.1, "psionic_blade_cooldown": -1.5},
            ]
        },
        "dragoon": {
            "name": "龙骑", "race": "protoss",
            "cost": 125, "damage": 20, "range": 192, "fire_rate": 1.5,
            "targets": "both", "splash": False, "sprite_key": "dragoon",
            "proj_key": "cannon_shot", "proj_speed": 400,
            "upgrades": [
                {"cost": 125, "damage_bonus": 10, "range_bonus": 16, "fire_rate_bonus": -0.15},
                {"cost": 250, "damage_bonus": 20, "range_bonus": 32, "fire_rate_bonus": -0.2},
            ]
        },
        "archon": {
            "name": "执政官", "race": "protoss",
            "cost": 100, "damage": 30, "range": 80, "fire_rate": 1.0,
            "targets": "both", "splash": True, "splash_radius": 24, "sprite_key": "archon",
            "proj_key": "cannon_shot", "proj_speed": 300,
            "upgrades": [
                {"cost": 100, "damage_bonus": 15, "range_bonus": 16, "fire_rate_bonus": -0.1},
                {"cost": 200, "damage_bonus": 30, "range_bonus": 32, "fire_rate_bonus": -0.15},
            ]
        },
        "scout": {
            "name": "侦察机", "race": "protoss",
            "cost": 275, "damage": 28, "range": 192, "fire_rate": 1.2,
            "targets": "both", "splash": False, "sprite_key": "scout",
            "proj_key": "bullet_epbbul", "proj_speed": 500,
            "is_air": True,
            "upgrades": [
                {"cost": 200, "damage_bonus": 14, "range_bonus": 32, "fire_rate_bonus": -0.1},
                {"cost": 350, "damage_bonus": 28, "range_bonus": 48, "fire_rate_bonus": -0.15},
            ]
        },
        "carrier": {
            "name": "航空母舰", "race": "protoss",
            "cost": 350, "damage": 8, "range": 256, "fire_rate": 0.4,
            "targets": "both", "splash": False, "sprite_key": "carrier",
            "proj_key": "bullet_epbbul", "proj_speed": 600,
            "is_air": True,
            "special": "interceptor",
            "interceptor_count": 4,
            "upgrades": [
                {"cost": 300, "interceptor_count": 2, "damage_bonus": 4, "range_bonus": 32},
                {"cost": 500, "interceptor_count": 2, "damage_bonus": 8, "range_bonus": 64},
            ]
        },
        "arbiter": {
            "name": "仲裁者", "race": "protoss",
            "cost": 250, "damage": 10, "range": 192, "fire_rate": 1.0,
            "targets": "both", "splash": False, "sprite_key": "arbiter",
            "proj_key": "bullet_epbbul", "proj_speed": 500,
            "is_air": True,
            "upgrades": [
                {"cost": 200, "damage_bonus": 5, "range_bonus": 32, "fire_rate_bonus": -0.1},
                {"cost": 400, "damage_bonus": 10, "range_bonus": 64, "fire_rate_bonus": -0.15},
            ]
        },

        # ── Protoss 地面重装 ──
        "reaver": {
            "name": "金甲虫", "race": "protoss",
            "cost": 200, "damage": 40, "range": 192, "fire_rate": 3.0,
            "targets": "ground", "splash": True, "splash_radius": 48,
            "sprite_key": "reaver", "proj_key": "bullet_explo1", "proj_speed": 400,
            "upgrades": [
                {"cost": 200, "damage_bonus": 20, "splash_radius_bonus": 8, "fire_rate_bonus": -0.3},
                {"cost": 400, "damage_bonus": 40, "splash_radius_bonus": 16, "fire_rate_bonus": -0.4},
            ]
        },

        # ── Protoss 防御建筑 ──
        "photon_cannon": {
            "name": "光子炮台", "race": "protoss",
            "cost": 100, "damage": 20, "range": 192, "fire_rate": 1.0,
            "targets": "both", "splash": False, "sprite_key": "photon_cannon",
            "proj_key": "cannon_shot", "proj_speed": 500,
            "upgrades": [
                {"cost": 100, "damage_bonus": 10, "range_bonus": 24, "fire_rate_bonus": -0.1},
                {"cost": 200, "damage_bonus": 20, "range_bonus": 48, "fire_rate_bonus": -0.15},
            ]
        },

        # ── Zerg ──
        "zergling": {
            "name": "小狗", "race": "zerg",
            "cost": 25, "damage": 5, "range": 48, "fire_rate": 0.4,
            "targets": "ground", "splash": False, "sprite_key": "zergling",
            "proj_key": "spine", "proj_speed": 0,
            "upgrades": [
                {"cost": 25, "damage_bonus": 3, "range_bonus": 0, "fire_rate_bonus": -0.05},
                {"cost": 50, "damage_bonus": 5, "range_bonus": 0, "fire_rate_bonus": -0.08},
            ]
        },
        "hydralisk": {
            "name": "刺蛇", "race": "zerg",
            "cost": 75, "damage": 10, "range": 160, "fire_rate": 0.7,
            "targets": "both", "splash": False, "sprite_key": "hydralisk",
            "proj_key": "spine", "proj_speed": 500,
            "upgrades": [
                {"cost": 75, "damage_bonus": 5, "range_bonus": 16, "fire_rate_bonus": -0.1},
                {"cost": 150, "damage_bonus": 10, "range_bonus": 32, "fire_rate_bonus": -0.15},
            ]
        },
        "lurker": {
            "name": "潜伏者", "race": "zerg",
            "cost": 125, "damage": 20, "range": 96, "fire_rate": 1.5,
            "targets": "ground", "splash": True, "splash_radius": 32, "sprite_key": "lurker",
            "proj_key": "spine", "proj_speed": 300,
            "upgrades": [
                {"cost": 125, "damage_bonus": 10, "range_bonus": 16, "fire_rate_bonus": -0.1},
                {"cost": 250, "damage_bonus": 20, "range_bonus": 32, "fire_rate_bonus": -0.2},
            ]
        },
        "ultralisk": {
            "name": "大象", "race": "zerg",
            "cost": 200, "damage": 35, "range": 64, "fire_rate": 1.2,
            "targets": "ground", "splash": False, "sprite_key": "ultralisk",
            "proj_key": "spine", "proj_speed": 0,
            "upgrades": [
                {"cost": 200, "damage_bonus": 15, "range_bonus": 8, "fire_rate_bonus": -0.1},
                {"cost": 400, "damage_bonus": 35, "range_bonus": 16, "fire_rate_bonus": -0.2},
            ]
        },
        "mutalisk": {
            "name": "飞龙", "race": "zerg",
            "cost": 100, "damage": 9, "range": 96, "fire_rate": 0.6,
            "targets": "both", "splash": True, "splash_radius": 16, "sprite_key": "mutalisk",
            "is_air": True,
            "proj_key": "bullet_dragbull", "proj_speed": 600,
            "upgrades": [
                {"cost": 100, "damage_bonus": 5, "range_bonus": 16, "fire_rate_bonus": -0.05},
                {"cost": 200, "damage_bonus": 9, "range_bonus": 32, "fire_rate_bonus": -0.1},
            ]
        },
        "guardian": {
            "name": "守护者", "race": "zerg",
            "cost": 150, "damage": 20, "range": 256, "fire_rate": 2.0,
            "targets": "ground", "splash": False, "sprite_key": "guardian",
            "is_air": True,
            "proj_key": "bullet_explo1", "proj_speed": 400,
            "upgrades": [
                {"cost": 150, "damage_bonus": 10, "range_bonus": 32, "fire_rate_bonus": -0.2},
                {"cost": 300, "damage_bonus": 20, "range_bonus": 64, "fire_rate_bonus": -0.3},
            ]
        },
        "devourer": {
            "name": "吞噬者", "race": "zerg",
            "cost": 200, "damage": 12, "range": 192, "fire_rate": 1.2,
            "targets": "air", "splash": True, "splash_radius": 24, "sprite_key": "devourer",
            "is_air": True,
            "proj_key": "spine", "proj_speed": 500,
            "upgrades": [
                {"cost": 150, "damage_bonus": 6, "range_bonus": 32, "fire_rate_bonus": -0.1},
                {"cost": 300, "damage_bonus": 12, "range_bonus": 48, "fire_rate_bonus": -0.15},
            ]
        },
        "queen": {
            "name": "女王", "race": "zerg",
            "cost": 100, "damage": 0, "range": 256, "fire_rate": 0,
            "targets": "ground", "splash": False, "sprite_key": "queen",
            "is_air": True,
            "proj_key": "spine", "proj_speed": 0,
            "special": "parasite",
            "parasite_damage": 5,
            "parasite_slow": 0.5,
            "parasite_cooldown": 20.0,
            "parasite_duration": 5.0,
            "upgrades": [
                {"cost": 100, "parasite_damage": 5, "parasite_duration": 3.0, "parasite_slow": 0.1},
                {"cost": 200, "parasite_damage": 10, "parasite_duration": 5.0, "parasite_slow": 0.15},
            ],
            "has_upgrade_special": True,
        },

        # ── Zerg 防御建筑 ──
        "sunken_colony": {
            "name": "地刺塔", "race": "zerg",
            "cost": 100, "damage": 25, "range": 160, "fire_rate": 1.2,
            "targets": "ground", "splash": False, "sprite_key": "sunken_colony",
            "proj_key": "spine", "proj_speed": 500,
            "upgrades": [
                {"cost": 100, "damage_bonus": 12, "range_bonus": 16, "fire_rate_bonus": -0.1},
                {"cost": 200, "damage_bonus": 25, "range_bonus": 32, "fire_rate_bonus": -0.2},
            ]
        },
        "spore_colony": {
            "name": "孢子塔", "race": "zerg",
            "cost": 75, "damage": 12, "range": 224, "fire_rate": 0.8,
            "targets": "air", "splash": False, "sprite_key": "spore_colony",
            "proj_key": "spine", "proj_speed": 500,
            "upgrades": [
                {"cost": 75, "damage_bonus": 6, "range_bonus": 24, "fire_rate_bonus": -0.05},
                {"cost": 150, "damage_bonus": 12, "range_bonus": 48, "fire_rate_bonus": -0.1},
            ]
        },
    }

    def __init__(self, unit_type: str, grid_col: int, grid_row: int):
        stats = self.TOWER_STATS[unit_type]
        self.type = unit_type
        self.name = stats["name"]
        self.race = stats["race"]
        self.grid_col = grid_col
        self.grid_row = grid_row

        self.px = grid_col * TILE_SIZE + TILE_SIZE // 2
        self.py = grid_row * TILE_SIZE + TILE_SIZE // 2

        # 战斗属性
        self.base_damage = stats["damage"]
        self.damage = stats["damage"]
        self.base_range = stats["range"]
        self.range = stats["range"]
        self.base_fire_rate = stats["fire_rate"] if stats["fire_rate"] > 0 else 999
        self.fire_rate = self.base_fire_rate
        self.targets = stats.get("targets", "ground")
        self.target_strategy = "first"

        # 溅射
        self.splash = stats.get("splash", False)
        self.splash_radius = stats.get("splash_radius", 0)

        # 投射物
        self.proj_key = stats.get("proj_key", "bullet")
        self.proj_speed = stats.get("proj_speed", 400)

        # 空中单位标记（不占用地面格子）
        self.is_air = stats.get("is_air", False)

        # 特殊能力
        self.special = stats.get("special", None)
        self.special_cooldown_timer = 0.0

        if self.special == "psi_storm":
            self.psi_storm_damage = stats.get("psi_storm_damage", 50)
            self.psi_storm_cooldown = stats.get("psi_storm_cooldown", 30.0)
            self.psi_storm_timer = 0.0
        elif self.special == "parasite":
            self.parasite_damage = stats.get("parasite_damage", 5)
            self.parasite_slow = stats.get("parasite_slow", 0.5)
            self.parasite_cooldown = stats.get("parasite_cooldown", 20.0)
            self.parasite_duration = stats.get("parasite_duration", 5.0)
            self.parasite_timer = 0.0
        elif self.special == "interceptor":
            self.interceptor_count = stats.get("interceptor_count", 4)
        elif self.special == "psionic_blade":
            self.psionic_blade_damage = stats.get("psionic_blade_damage", 25)
            self.psionic_blade_range = stats.get("psionic_blade_range", 192)
            self.psionic_blade_cooldown = stats.get("psionic_blade_cooldown", 8.0)
            self.psionic_blade_proj_speed = stats.get("psionic_blade_proj_speed", 800)
            self.psionic_blade_timer = 0.0

        # 升级
        self.level = 1
        self.max_level = len(stats["upgrades"]) + 1
        self.upgrade_data = stats["upgrades"]
        self.total_cost = stats["cost"]
        self.has_upgrade_special = stats.get("has_upgrade_special", False)

        self.cooldown = 0.0

        self.sprite = PlaceholderSprite(unit_type)
        self.show_range = False

    def update(self, dt: float, enemies: list, projectiles: list):
        """每帧更新"""
        self._all_enemies = enemies
        self.cooldown = max(0, self.cooldown - dt)

        # 判断是否在攻击状态（有目标在射程内）
        has_target = bool(self._find_target(enemies)) if enemies else False
        self.sprite.set_attacking(has_target)
        self.sprite.update(dt)  # 更新动画

        # 特殊能力
        if self.special == "psi_storm":
            self.psi_storm_timer -= dt
            if self.psi_storm_timer <= 0 and enemies:
                self._cast_psi_storm(enemies, projectiles)
                self.psi_storm_timer = self.psi_storm_cooldown
        elif self.special == "parasite":
            self.parasite_timer -= dt
            if self.parasite_timer <= 0 and enemies:
                self._cast_parasite(enemies)
                self.parasite_timer = self.parasite_cooldown
        elif self.special == "psionic_blade":
            self.psionic_blade_timer -= dt
            if self.psionic_blade_timer <= 0 and enemies:
                self._cast_psionic_blade(enemies, projectiles)
                self.psionic_blade_timer = self.psionic_blade_cooldown

        # 普通攻击
        if self.cooldown <= 0 and self.damage > 0:
            target = self._find_target(enemies)
            if target:
                self._fire(target, projectiles)
                self.cooldown = self.fire_rate

    def _find_target(self, enemies):
        """寻找目标"""
        return TargetingSystem.first(enemies, (self.px, self.py),
                                     self.range, self.targets)

    def _fire(self, target, projectiles):
        """开火"""
        # 开火音效
        if self.__class__.sound_manager:
            self.__class__.sound_manager.play_fire(self.type)

        if self.proj_speed <= 0:
            # 近战攻击（瞬间命中）
            target.take_damage(self.damage)
            if self.splash and self.splash_radius > 0:
                pass
        else:
            proj = Projectile(
                start_x=self.px, start_y=self.py,
                target=target,
                damage=self.damage,
                speed=self.proj_speed,
                splash=self.splash,
                splash_radius=self.splash_radius,
                sprite_key=self.proj_key
            )
            # 保存敌人列表引用给投射物用于溅射
            if self.splash and self.splash_radius > 0:
                proj.set_enemies(self._all_enemies)
            projectiles.append(proj)

    def _cast_psi_storm(self, enemies, projectiles):
        """心灵风暴 — 范围AOE伤害"""
        target = TargetingSystem.strongest(enemies, (self.px, self.py), self.range, "ground")
        if not target:
            target = TargetingSystem.first(enemies, (self.px, self.py), self.range, "ground")
        if not target:
            return

        tx, ty = target.get_position()
        storm_radius = self.splash_radius

        # 范围内的所有地面敌人受到伤害
        for enemy in enemies:
            if not enemy.alive:
                continue
            ex, ey = enemy.get_position()
            d = math.sqrt((ex - tx) ** 2 + (ey - ty) ** 2)
            if d <= storm_radius:
                enemy.take_damage(int(self.psi_storm_damage * 0.5))
                enemy.take_damage(int(self.psi_storm_damage * 0.3))
                # 第二段伤害略微延迟，用两个投射物表示
                if enemy.alive:
                    dummy_proj = Projectile(tx, ty, enemy, int(self.psi_storm_damage * 0.2), 999)
                    dummy_proj.x = tx
                    dummy_proj.y = ty
                    projectiles.append(dummy_proj)

    def _cast_parasite(self, enemies):
        """寄生 — 对最强敌人造成持续伤害+减速"""
        target = TargetingSystem.strongest(enemies, (self.px, self.py), self.range, "ground")
        if not target:
            target = TargetingSystem.first(enemies, (self.px, self.py), self.range, "ground")
        if not target:
            return

        # 为敌人添加寄生效果（标记在敌人上）
        target.parasite_timer = self.parasite_duration
        target.parasite_dps = self.parasite_damage / self.parasite_duration
        target.parasite_slow = self.parasite_slow

    def _cast_psionic_blade(self, enemies, projectiles):
        """灵能刃 — 远程投掷高伤害灵能飞刃"""
        target = TargetingSystem.strongest(enemies, (self.px, self.py),
                                            self.psionic_blade_range, "ground")
        if not target:
            target = TargetingSystem.first(enemies, (self.px, self.py),
                                            self.psionic_blade_range, "ground")
        if not target:
            return

        proj = Projectile(
            start_x=self.px, start_y=self.py,
            target=target,
            damage=self.psionic_blade_damage,
            speed=self.psionic_blade_proj_speed,
            splash=False,
            sprite_key="psiblade"
        )
        projectiles.append(proj)

    def can_upgrade(self) -> bool:
        return self.level < self.max_level

    def upgrade_cost(self) -> int:
        if not self.can_upgrade():
            return 999999
        return self.upgrade_data[self.level - 1]["cost"]

    def apply_upgrade(self):
        """应用升级"""
        if not self.can_upgrade():
            return
        data = self.upgrade_data[self.level - 1]
        self.damage += data.get("damage_bonus", 0)
        self.range += data.get("range_bonus", 0)
        self.fire_rate = max(0.3, self.fire_rate + data.get("fire_rate_bonus", 0))
        self.splash_radius += data.get("splash_radius_bonus", 0)
        self.total_cost += data["cost"]

        # 特殊能力升级
        if self.special == "psi_storm":
            self.psi_storm_damage += data.get("psi_storm_damage", 0)
        elif self.special == "parasite":
            self.parasite_damage += data.get("parasite_damage", 0)
            self.parasite_duration += data.get("parasite_duration", 0)
            self.parasite_slow += data.get("parasite_slow", 0)
            self.parasite_dps = self.parasite_damage / max(self.parasite_duration, 1)
        elif self.special == "interceptor":
            self.interceptor_count += data.get("interceptor_count", 0)
        elif self.special == "psionic_blade":
            self.psionic_blade_damage += data.get("psionic_blade_damage", 0)
            self.psionic_blade_cooldown += data.get("psionic_blade_cooldown", 0)
            self.psionic_blade_cooldown = max(2.0, self.psionic_blade_cooldown)

        self.level += 1

    def sell_value(self) -> int:
        return int(self.total_cost * SELL_REFUND_RATIO)

    def draw(self, surface: pygame.Surface):
        """在 Pygame surface 上绘制"""
        self.sprite.draw(surface, self.px, self.py)

        if self.show_range:
            pygame.draw.circle(surface, (68, 136, 255, 80),
                               (int(self.px), int(self.py)),
                               int(self.range), 1)

        if self.level > 1:
            # 等级标记 — 金色星星 +  Lv 文字
            font = make_font(14)
            stars = "★" * self.level
            lv_text = font.render(stars, True, COLOR_GOLD)
            lv_rect = lv_text.get_rect(center=(int(self.px), int(self.py - TILE_SIZE // 2 + 2)))
            surface.blit(lv_text, lv_rect)

            # 最下面显示 LvN
            font2 = make_font(11)
            lvl_num = font2.render(f"Lv{self.level}", True, COLOR_GOLD)
            lvl_rect = lvl_num.get_rect(center=(int(self.px + 14), int(self.py + 14)))
            surface.blit(lvl_num, lvl_rect)

    def debug_info(self) -> str:
        info = f"{self.name}[Lv{self.level}] DMG:{self.damage} RNG:{int(self.range)}"
        if self.splash:
            info += f" SPL:{int(self.splash_radius)}"
        return info
