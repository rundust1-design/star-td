"""
路径系统 — 定义敌人行走的路线
"""
from src.core.constants import TILE_SIZE


class Path:
    """固定路径，由一系列网格坐标路径点定义"""

    def __init__(self, waypoints: list[tuple[int, int]]):
        """
        参数:
            waypoints: [(col, row), ...] 网格坐标路径点
        """
        self.waypoints = waypoints
        self.segments = []  # 每个线段的像素坐标和长度
        self.total_length = 0.0

        # 将网格坐标转换为像素坐标（格子中心）
        self.pixel_points = []
        for col, row in waypoints:
            px = col * TILE_SIZE + TILE_SIZE // 2
            py = row * TILE_SIZE + TILE_SIZE // 2
            self.pixel_points.append((px, py))

        # 计算每段长度和总长度
        import math
        for i in range(len(self.pixel_points) - 1):
            x1, y1 = self.pixel_points[i]
            x2, y2 = self.pixel_points[i + 1]
            dx = x2 - x1
            dy = y2 - y1
            length = math.sqrt(dx * dx + dy * dy)
            angle = math.atan2(dy, dx)
            self.segments.append({
                "start": (x1, y1),
                "end": (x2, y2),
                "length": length,
                "angle": angle,
                "dx": dx,
                "dy": dy,
            })
            self.total_length += length

    def get_position_at(self, progress: float) -> tuple[float, float]:
        """
        根据进度返回路径上的像素位置

        参数:
            progress: 0.0 ~ 1.0 路径进度

        返回:
            (x, y) 像素坐标
        """
        if progress <= 0.0:
            return self.pixel_points[0]
        if progress >= 1.0:
            return self.pixel_points[-1]

        target_dist = progress * self.total_length
        accumulated = 0.0

        for seg in self.segments:
            if accumulated + seg["length"] >= target_dist:
                seg_progress = (target_dist - accumulated) / seg["length"]
                x = seg["start"][0] + seg["dx"] * seg_progress
                y = seg["start"][1] + seg["dy"] * seg_progress
                return (x, y)
            accumulated += seg["length"]

        return self.pixel_points[-1]

    def get_direction_at(self, progress: float) -> float:
        """返回当前路径段的角度（弧度）"""
        if progress >= 1.0:
            return self.segments[-1]["angle"]

        target_dist = progress * self.total_length
        accumulated = 0.0

        for seg in self.segments:
            if accumulated + seg["length"] >= target_dist:
                return seg["angle"]
            accumulated += seg["length"]

        return self.segments[-1]["angle"]

    def get_occupied_tiles(self, buffer: int = 1) -> set[tuple[int, int]]:
        """
        返回路径占用的格子集合（含缓冲区）

        参数:
            buffer: 路径两侧多少格不可建造

        返回:
            set[(col, row), ...]
        """
        occupied = set()
        for i in range(len(self.waypoints) - 1):
            c1, r1 = self.waypoints[i]
            c2, r2 = self.waypoints[i + 1]

            # 水平线段
            if r1 == r2:
                for c in range(min(c1, c2), max(c1, c2) + 1):
                    for b in range(-buffer, buffer + 1):
                        occupied.add((c, r1 + b))
            # 垂直线段
            elif c1 == c2:
                for r in range(min(r1, r2), max(r1, r2) + 1):
                    for b in range(-buffer, buffer + 1):
                        occupied.add((c1 + b, r))
            # 斜线段（简单处理，覆盖矩形区域）
            else:
                for c in range(min(c1, c2), max(c1, c2) + 1):
                    for r in range(min(r1, r2), max(r1, r2) + 1):
                        for b in range(-buffer, buffer + 1):
                            occupied.add((c, r + b))

        return occupied
