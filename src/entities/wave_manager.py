"""
波次管理器 — 管理敌人波次的生成
"""
from src.entities.enemy import Enemy


class WaveManager:
    """管理敌人波次的生成和追踪"""

    def __init__(self, waves_data: list, path, economy, on_enemy_reach_end):
        """
        参数:
            waves_data: wave 配置列表
            path: Path 对象
            economy: Economy 对象
            on_enemy_reach_end: 敌人到达终点时的回调函数
        """
        self.waves = waves_data
        self.path = path
        self.economy = economy
        self.on_enemy_reach_end = on_enemy_reach_end

        self.current_wave_index = -1  # -1 表示尚未开始
        self.spawn_queue: list[dict] = []  # 待生成的敌人队列
        self.spawn_timer = 0.0
        self.spawn_index = 0  # 当前波次中已生成的敌人数量
        self.wave_total_enemies = 0

        self.active_enemies: list[Enemy] = []
        self.wave_in_progress = False
        self.all_waves_complete = False
        self.between_wave_timer = 0.0
        self.wave_started_this_frame = False

    def start_next_wave(self):
        """开始下一波"""
        if self.current_wave_index >= len(self.waves) - 1:
            if not self.wave_in_progress and len(self.active_enemies) == 0:
                self.all_waves_complete = True
            return

        self.current_wave_index += 1
        wave = self.waves[self.current_wave_index]
        self.wave_in_progress = True
        self.wave_started_this_frame = True

        # 构建生成队列
        self.spawn_queue = []
        if isinstance(wave, list):
            # 简化格式: [{type: "zergling", count: 5, delay: 1.0}, ...]
            self.spawn_queue = list(wave)
        else:
            # 完整格式
            for entry in wave.get("groups", []):
                enemy_type = entry.get("type", "zergling")
                count = entry.get("count", 1)
                delay = entry.get("delay", 1.0)
                self.spawn_queue.append({
                    "type": enemy_type,
                    "count": count,
                    "delay": delay,
                })

        self.wave_total_enemies = sum(e.get("count", 1) for e in self.spawn_queue)
        self.spawn_index = 0
        self.spawn_timer = 0.0

    def update(self, dt: float) -> list[Enemy]:
        """每帧更新，返回本帧新生成的敌人列表"""
        spawned = []

        if not self.wave_in_progress:
            return spawned

        if self.spawn_index < self.wave_total_enemies:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0:
                new_enemy = self._spawn_next()
                if new_enemy:
                    spawned.append(new_enemy)
                    self.spawn_index += 1

        # 更新所有活跃敌人
        for enemy in self.active_enemies[:]:
            enemy.update(dt)
            if enemy.reached_end:
                self.active_enemies.remove(enemy)
                self.on_enemy_reach_end(enemy)
            elif not enemy.alive:
                self.active_enemies.remove(enemy)
                self.economy.earn(enemy.reward)

        # 检查波次是否完成
        if self._is_wave_complete():
            self.wave_in_progress = False
            # 如果是最后一波，自动标记全部完成（无需用户再点"下一波"）
            if self.current_wave_index >= len(self.waves) - 1:
                self.all_waves_complete = True

        return spawned

    def _spawn_next(self) -> Enemy | None:
        """从队列中生成下一个敌人"""
        if not self.spawn_queue:
            return None

        current = self.spawn_queue[0]
        enemy = Enemy(current["type"], self.path)
        self.active_enemies.append(enemy)

        current["count"] -= 1
        if current["count"] <= 0:
            self.spawn_queue.pop(0)
            self.spawn_timer = current.get("delay", 1.0)
        else:
            self.spawn_timer = current.get("delay", 1.0)

        return enemy

    def _is_wave_complete(self) -> bool:
        """检查当前波次是否完成"""
        return (self.spawn_index >= self.wave_total_enemies
                and len(self.active_enemies) == 0)

    def get_current_wave_number(self) -> int:
        """当前波次数（从 1 开始）"""
        if self.current_wave_index < 0:
            return 0
        return self.current_wave_index + 1

    def get_total_waves(self) -> int:
        """总波次数"""
        return len(self.waves)

    def get_active_enemy_count(self) -> int:
        """活跃敌人数"""
        return len(self.active_enemies)
