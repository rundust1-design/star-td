"""
敌人阵容生成器 — 根据种族、波数、难度动态生成敌人队列

规则:
  1. 从该种族最便宜的兵种开始，随着波数提升解锁更贵的兵种
  2. 难度影响: 生成速度、每波总敌人数量、兵种质量
  3. 随机种族: 每波从三个种族中随机选一个
"""
import math
import random

# 三族的兵种（从 tower.py 的 TOWER_STATS 获取费用信息）
# 每个条目: (兵种id, 费用, 中文名, target类型, is_air)
# target: "ground"=仅对地兵种, "air"=空中单位(前3波不出), "both"=地面单位但可对空
RACE_UNITS = {
    "terran": [
        ("marine", 50, "机枪兵", "both"),
        ("firebat", 50, "火焰兵", "ground"),
        ("ghost", 75, "幽灵", "both"),
        ("goliath", 100, "巨人", "both"),
        ("siege_tank", 150, "攻城坦克", "ground"),
        ("wraith", 150, "科学球", "air"),        # 空中单位
        ("valkyrie", 250, "瓦尔基里", "air"),     # 空中单位
        ("battlecruiser", 400, "大和舰", "both"),
    ],
    "protoss": [
        ("zealot", 100, "狂热者", "ground"),
        ("archon", 100, "执政官", "both"),
        ("dragoon", 125, "龙骑", "both"),
        ("dark_templar", 125, "黑暗圣堂武士", "ground"),
        ("scout", 275, "侦察机", "air"),          # 空中单位
        ("carrier", 350, "航空母舰", "both"),
        ("arbiter", 250, "仲裁者", "both"),
    ],
    "zerg": [
        ("zergling", 25, "小狗", "ground"),
        ("hydralisk", 75, "刺蛇", "both"),
        ("mutalisk", 100, "飞龙", "air"),         # 空中单位
        ("queen", 100, "女王", "ground"),
        ("lurker", 125, "潜伏者", "ground"),
        ("guardian", 150, "守护者", "ground"),
        ("devourer", 200, "吞噬者", "air"),       # 空中单位
        ("ultralisk", 200, "大象", "ground"),
    ],
}

# 按费用排序的索引
RACE_UNITS_SORTED = {}
for race, units in RACE_UNITS.items():
    RACE_UNITS_SORTED[race] = sorted(units, key=lambda u: u[1])

# 难度配置
DIFFICULTY = {
    "easy": {
        "name": "简单",
        "multiplier": 0.6,          # 总敌人数量系数
        "spawn_delay_base": 1.5,     # 基础生成间隔（秒）
        "spawn_delay_min": 0.6,      # 最小生成间隔
        "budget_per_wave": 1.0,      # 波次预算系数
        "quality_curve": 0.6,        # 兵种质量展缓（0-1，越低越晚出高级兵）
        "enemy_extra_hp": 0.8,       # 敌人血量系数
    },
    "normal": {
        "name": "普通",
        "multiplier": 1.0,
        "spawn_delay_base": 1.2,
        "spawn_delay_min": 0.5,
        "budget_per_wave": 1.0,
        "quality_curve": 1.0,
        "enemy_extra_hp": 1.0,
    },
    "hard": {
        "name": "困难",
        "multiplier": 1.5,
        "spawn_delay_base": 0.9,
        "spawn_delay_min": 0.35,
        "budget_per_wave": 1.3,
        "quality_curve": 1.3,
        "enemy_extra_hp": 1.2,
    },
    "insane": {
        "name": "疯狂",
        "multiplier": 2.2,
        "spawn_delay_base": 0.7,
        "spawn_delay_min": 0.2,
        "budget_per_wave": 1.6,
        "quality_curve": 1.6,
        "enemy_extra_hp": 1.5,
    },
}


def _available_units_for_wave(race: str, wave_index: int, difficulty: str) -> list:
    """
    根据波数返回该波可用的兵种列表。
    波数越低只能用便宜兵种，波数越高解锁更多。
    """
    diff_cfg = DIFFICULTY.get(difficulty, DIFFICULTY["normal"])
    units = RACE_UNITS_SORTED.get(race, RACE_UNITS_SORTED["zerg"])

    # 根据 quality_curve 和波数计算当前最大可解锁费用
    max_cost = 25 + int(375 * min(1.0, (wave_index / 6) ** (1.0 / max(0.3, diff_cfg["quality_curve"]))))

    available = []
    for uid, cost, cname, target in units:
        # 前3波不出空中单位（air 类型）
        if target == "air" and wave_index < 3:
            continue
        if cost <= max_cost:
            available.append((uid, cost, cname, target))

    if not available:
        available = [units[0]]

    return available


def _units_budget(wave_index: int, difficulty: str) -> int:
    """计算该波的总预算（用于买兵，按费用分配敌人的总价值）"""
    diff_cfg = DIFFICULTY.get(difficulty, DIFFICULTY["normal"])

    # 基础: 第1波100，第7波700
    base_budget = 80 + wave_index * 100
    return int(base_budget * diff_cfg["budget_per_wave"] * diff_cfg["multiplier"])


def generate_wave(
    enemy_race: str,
    wave_index: int,
    total_waves: int,
    difficulty: str,
    player_hp: int = 20,
) -> list[dict]:
    """
    生成一波敌人配置。

    返回:
        [{"type": "zergling", "count": 5, "delay": 1.0}, ...]
    """
    diff_cfg = DIFFICULTY.get(difficulty, DIFFICULTY["normal"])

    # 随机种族: 每波随机选一个
    if enemy_race == "random":
        race = random.choice(["terran", "protoss", "zerg"])
    else:
        race = enemy_race

    # 获取可用兵种
    available = _available_units_for_wave(race, wave_index, difficulty)
    if not available:
        return [{"type": "zergling", "count": 3, "delay": 1.2}]

    # 计算预算
    budget = _units_budget(wave_index, difficulty)

    # 分配预算到各种兵种
    groups = []
    remaining_budget = budget

    # 兵种选择倾向于便宜的（早期波次）或贵一些的（后期波次，加随机）
    total_units = max(1, int((wave_index + 3) * diff_cfg["multiplier"]))

    # 根据波数决定是用更贵的还是多种混合
    # 越靠近后期，越杂（多种混合）
    diversity = min(1.0, wave_index / 4)  # 第4波开始完全多样化

    used_types = set()

    # 如果预算大，分多组制作
    max_groups = min(5, max(2, int(2 + diversity * 3)))
    attempts = 0

    while remaining_budget > 0 and len(groups) < max_groups and attempts < 20:
        attempts += 1

        # 选择兵种: 预算范围内随机，但更低的波次倾向便宜兵种
        candidates = [
            u for u in available if u[1] <= remaining_budget * 0.8 + 5
        ]
        if not candidates:
            candidates = available

        # 加权重: 便宜（小）的高频出现，贵的低频出现
        weights = []
        unit_budget_portion = max(30, remaining_budget // max(1, max_groups - len(groups)))
        for unit_cost in [u[1] for u in candidates]:
            if unit_cost <= unit_budget_portion:
                weights.append(3.0)
            elif unit_cost <= unit_budget_portion * 2:
                weights.append(1.5)
            else:
                weights.append(0.3)

        chosen = random.choices(candidates, weights=weights, k=1)[0]
        uid, cost, cname, target = chosen

        # 决定数量: 预算 ÷ 兵种费用 × 一些随机
        budget_for_this_group = int(remaining_budget * random.uniform(0.25, 0.6))
        max_count = max(1, budget_for_this_group // max(1, cost))
        count = min(max_count, max(1, total_units // max(1, len(groups) + 1) + random.randint(-1, 2)))
        count = max(1, min(15, count))  # 每组最多15个

        # 生成延迟取决于难度
        delay = max(diff_cfg["spawn_delay_min"],
                    diff_cfg["spawn_delay_base"] - wave_index * 0.05 + random.uniform(-0.1, 0.1))
        delay = max(diff_cfg["spawn_delay_min"], delay)

        # 检查是否已有这个类型的组
        type_key = (uid, race)
        existing = None
        for g in groups:
            if g["type"] == uid:
                existing = g
                break

        if existing:
            existing["count"] += count
        else:
            groups.append({
                "type": uid,
                "count": count,
                "delay": round(delay, 2),
            })

        used_types.add(uid)
        remaining_budget -= cost * count

    if not groups:
        # 保底
        default = available[0]
        groups.append({
            "type": default[0],
            "count": 3,
            "delay": 1.2,
        })

    # 从便宜到贵排列
    cost_map = {u[0]: u[1] for u in available}
    groups.sort(key=lambda g: cost_map.get(g["type"], 999))

    return groups


def generate_all_waves(
    enemy_race: str,
    difficulty: str,
    num_waves: int = 7,
) -> list:
    """生成完整的波次列表"""
    waves = []
    for wi in range(num_waves):
        wave_groups = generate_wave(enemy_race, wi, num_waves, difficulty)
        waves.append({"groups": wave_groups})
    return waves
