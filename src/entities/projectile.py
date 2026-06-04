"""
投射物 — 塔发射的子弹/飞弹
"""
import math
import pygame
from src.entities.sprite import PlaceholderSprite


class Projectile:
    """投射物实体"""

    sound_manager = None  # 由 game.py 设置

    def __init__(self, start_x: float, start_y: float,
                 target, damage: float, speed: float = 400,
                 splash: bool = False, splash_radius: float = 0,
                 sprite_key: str = "bullet"):
        self.x = start_x
        self.y = start_y
        self.target = target
        self.damage = damage
        self.speed = speed
        self.splash = splash
        self.splash_radius = splash_radius
        self.alive = True
        self.hit = False

        # 储存敌人列表引用，用于溅射
        self._enemies = None

        self.angle = 0.0
        self.sprite = PlaceholderSprite(sprite_key)
        self.sprite_key = sprite_key

        # 根据伤害调整投射物大小（伤害 1~50 对应缩放 0.5~2.0）
        dmg_scale = max(0.5, min(2.0, self.damage / 15))
        self.sprite.scale = dmg_scale

    def update(self, dt: float):
        if not self.alive:
            return
        if not self.target or not self.target.alive:
            self.alive = False
            return

        self.sprite.update(dt)  # 更新动画

        tx, ty = self.target.get_position()
        dx = tx - self.x
        dy = ty - self.y
        dist = math.sqrt(dx * dx + dy * dy)

        if dist < 10:
            self._on_hit()
            return

        move = min(dist, self.speed * dt)
        self.x += (dx / dist) * move
        self.y += (dy / dist) * move
        self.angle = math.atan2(dy, dx)

    def _on_hit(self):
        # 命中音效
        if self.__class__.sound_manager:
            self.__class__.sound_manager.play_hit(self.sprite_key)

        if self.target and self.target.alive:
            self.target.take_damage(self.damage)

        # 溅射 → 爆炸音效覆盖命中音效
        if self.splash and self.splash_radius > 0 and self._enemies is not None:
            if self.__class__.sound_manager:
                self.__class__.sound_manager.play_event("explosion")
            tx, ty = self.x, self.y
            for enemy in self._enemies:
                if not enemy.alive or enemy is self.target:
                    continue
                ex, ey = enemy.get_position()
                d = math.sqrt((ex - tx) ** 2 + (ey - ty) ** 2)
                if d <= self.splash_radius:
                    # 溅射伤害递减
                    ratio = 1.0 - (d / self.splash_radius) * 0.5
                    splash_dmg = max(1, int(self.damage * ratio))
                    enemy.take_damage(splash_dmg)

        self.hit = True
        self.alive = False

    def set_enemies(self, enemies: list):
        """设置敌人列表引用（用于溅射）"""
        self._enemies = enemies

    def get_position(self) -> tuple[float, float]:
        return (self.x, self.y)

    def draw(self, surface: pygame.Surface):
        if not self.alive:
            return
        self.sprite.draw(surface, self.x, self.y, self.angle)
