"""
目标选择系统 — 塔选择攻击目标的策略
"""
import math


class TargetingSystem:
    """提供各种目标选择策略的静态方法"""

    @staticmethod
    def enemies_in_range(tower_pos: tuple[int, int], enemies: list,
                         tower_range: float, target_type: str = "ground"):
        """
        返回射程内的敌人列表

        参数:
            tower_pos: (x, y) 塔的像素中心
            enemies: Enemy 对象列表
            tower_range: 射程（像素）
            target_type: "ground", "air", "both"
        """
        in_range = []
        for enemy in enemies:
            if not enemy.alive:
                continue
            # 按 target_type 过滤：ground 只打地面，air 只打空中，both 打所有
            if target_type == "ground" and getattr(enemy, "is_air", False):
                continue
            if target_type == "air" and not getattr(enemy, "is_air", False):
                continue
            epos = enemy.get_position()
            dist = math.sqrt((epos[0] - tower_pos[0]) ** 2 +
                             (epos[1] - tower_pos[1]) ** 2)
            if dist <= tower_range:
                in_range.append(enemy)
        return in_range

    @staticmethod
    def first(enemies, tower_pos, tower_range, target_type="ground", tower=None):
        """
        选择路径上最靠前的敌人（进度最大）
        """
        candidates = TargetingSystem.enemies_in_range(
            tower_pos, enemies, tower_range, target_type
        )
        if not candidates:
            return None
        return max(candidates, key=lambda e: e.progress)

    @staticmethod
    def last(enemies, tower_pos, tower_range, target_type="ground", tower=None):
        """选择路径上最靠后的敌人"""
        candidates = TargetingSystem.enemies_in_range(
            tower_pos, enemies, tower_range, target_type
        )
        if not candidates:
            return None
        return min(candidates, key=lambda e: e.progress)

    @staticmethod
    def strongest(enemies, tower_pos, tower_range, target_type="ground", tower=None):
        """选择血量最高的敌人"""
        candidates = TargetingSystem.enemies_in_range(
            tower_pos, enemies, tower_range, target_type
        )
        if not candidates:
            return None
        return max(candidates, key=lambda e: e.max_hp)

    @staticmethod
    def weakest(enemies, tower_pos, tower_range, target_type="ground", tower=None):
        """选择血量最低的敌人"""
        candidates = TargetingSystem.enemies_in_range(
            tower_pos, enemies, tower_range, target_type
        )
        if not candidates:
            return None
        return min(candidates, key=lambda e: e.hp)

    @staticmethod
    def nearest(enemies, tower_pos, tower_range, target_type="ground", tower=None):
        """选择距离最近的敌人"""
        candidates = TargetingSystem.enemies_in_range(
            tower_pos, enemies, tower_range, target_type
        )
        if not candidates:
            return None
        return min(candidates,
                   key=lambda e: math.sqrt(
                       (e.get_position()[0] - tower_pos[0]) ** 2 +
                       (e.get_position()[1] - tower_pos[1]) ** 2
                   ))
