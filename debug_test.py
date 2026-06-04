"""完整调试：从初始化到出敌人"""
# 跳过 pygame import，只测逻辑
import sys, os
sys.path.insert(0, 'f:/game/star_TD')

from src.core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, STARTING_MONEY, STARTING_LIVES, TILE_SIZE
from src.systems.enemy_generator import generate_all_waves
from src.systems.path import Path
from src.entities.wave_manager import WaveManager
from src.entities.enemy import Enemy
from src.systems.economy import Economy
from src.entities.tower import Tower

# 1. 模拟 _get_preset_path（现在返回网格坐标）
def get_preset_path(map_idx):
    paths = {
        1: [(0, 10), (8, 10), (8, 3), (22, 3), (22, 14), (31, 14)],
    }
    return paths.get(map_idx, paths[1])

grid_path = get_preset_path(1)
print(f"1. 路径网格坐标: {grid_path}")

# 2. 创建 Path（内部转换为像素坐标）
path = Path(grid_path)
print(f"2. Path total_length={path.total_length}")
print(f"   Path points: {path.pixel_points}")

# 3. 生成波次
waves = generate_all_waves('zerg', 'normal', 7)
print(f"3. 波次数: {len(waves)}")
print(f"   第1波数据: {waves[0]}")

# 4. 创建 WaveManager
eco = Economy(STARTING_MONEY)
eco.lives = STARTING_LIVES
def on_enemy_reach_end(enemy):
    print(f"   敌人到达终点: {enemy.type}, 扣生命")
    eco.lives -= enemy.damage_to_base

wm = WaveManager(waves, path, eco, on_enemy_reach_end)
print(f"4. WaveManager 创建完成")
print(f"   wave_in_progress={wm.wave_in_progress}")
print(f"   all_waves_complete={wm.all_waves_complete}")

# 5. 调用 start_next_wave
wm.start_next_wave()
print(f"5. 开始第一波后:")
print(f"   wave_in_progress={wm.wave_in_progress}")
print(f"   current_wave_index={wm.current_wave_index}")
print(f"   spawn_queue: {wm.spawn_queue}")
print(f"   wave_total_enemies={wm.wave_total_enemies}")

# 6. 模拟 update 60 帧（1秒）
print(f"\n6. 模拟 60 帧更新:")
enemies_spawned = 0
for frame in range(60):
    spawned = wm.update(1/60)  # dt = 1/60 second
    for s in spawned:
        enemies_spawned += 1
        pos = s.get_position()
        print(f"   帧{frame}: 生成 {s.type} 位置=({pos[0]:.0f},{pos[1]:.0f}) is_air={s.is_air}")

if enemies_spawned == 0:
    print("\n❌ 没有敌人被生成！")
    print(f"   spawn_index={wm.spawn_index}, wave_total_enemies={wm.wave_total_enemies}")
    print(f"   spawn_queue={wm.spawn_queue}")
    print(f"   spawn_timer={wm.spawn_timer}")
else:
    print(f"\n✅ 共生成了 {enemies_spawned} 个敌人")

print(f"\n活跃敌人: {len(wm.active_enemies)}")
print(f"剩余生命: {eco.lives}")
print("\n=== DONE ===")
