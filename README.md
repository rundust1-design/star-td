
# 星际争霸 塔防 — StarCraft Tower Defense

一款基于 **Pygame** 构建的塔防游戏，使用《星际争霸 1.08b》（含 Brood War）提取的素材。

## 快速开始

```bash
pip install -r requirements.txt
python src/main.py
```

或双击 `start_game.bat`（需 `.venv` 虚拟环境）。

### 依赖

- `pygame >= 2.5.0`
- `mpyq >= 0.2.5`
- `Pillow >= 11.0.0`
- `numpy >= 2.0.0`
- `pympq`（解析加密 MPQ 使用）

### 系统要求

- Windows（字体使用微软雅黑）
- Python 3.11+
- 固定分辨率 1024×768

## 游戏流程

1. **选择玩家种族** — 人族 / 神族 / 虫族
2. **选择敌人配置** — 敌人种族（人族/神族/虫族/随机）+ 难度（简单/普通/困难/疯狂）
3. **自动匹配地图** — 根据难度分配预渲染的地图背景
4. **开始游戏** — 建造炮塔抵御 7 波敌人进攻

## 炮塔列表

### 人族（10 种）

| 炮塔 | 费用 | 伤害 | 射程 | 射速 | 目标 | 溅射 |
|------|------|------|------|------|------|------|
| 机枪兵 Marine | $50 | 6 | 128 | 0.5s | 空地 | - |
| 火焰兵 Firebat | $50 | 8 | 80 | 0.7s | 地面 | - |
| 幽灵 Ghost | $75 | 10 | 192 | 1.0s | 空地 | - |
| 巨人 Goliath | $100 | 12 | 192 | 1.2s | 空地 | - |
| 攻城坦克 Siege Tank | $150 | 30 | 256 | 2.0s | 地面 | 48px |
| 科学球 Wraith | $150 | 8 | 160 | 1.0s | 空地 | - |
| 大和舰 Battlecruiser | $400 | 25 | 256 | 1.5s | 空地 | - |
| 瓦尔基里 Valkyrie | $250 | 6 | 192 | 0.3s | 空中 | 32px |
| 碉堡 Bunker | $100 | 12 | 160 | 0.6s | 地面 | - |
| 导弹塔 Missile Turret | $75 | 15 | 256 | 1.0s | 空中 | - |

### 神族（8 种）

| 炮塔 | 费用 | 伤害 | 射程 | 射速 | 目标 | 特殊 |
|------|------|------|------|------|------|------|
| 狂热者 Zealot | $50 | 8 | 48 | 0.6s | 地面 | 灵能刃（8s CD, 192 范围, 25 伤害） |
| 龙骑 Dragoon | $125 | 20 | 192 | 1.5s | 空地 | |
| 执政官 Archon | $100 | 30 | 80 | 1.0s | 空地 | 24px 溅射 |
| 侦察机 Scout | $275 | 28 | 192 | 1.2s | 空地 | 空中单位 |
| 航空母舰 Carrier | $350 | 8 | 256 | 0.4s | 空地 | 4 架拦截机 |
| 仲裁者 Arbiter | $250 | 10 | 192 | 1.0s | 空地 | 空中单位 |
| 金甲虫 Reaver | $200 | 40 | 192 | 3.0s | 地面 | 48px 溅射 |
| 光子炮台 Photon Cannon | $100 | 20 | 192 | 1.0s | 空地 | |

### 虫族（10 种）

| 炮塔 | 费用 | 伤害 | 射程 | 射速 | 目标 | 特殊 |
|------|------|------|------|------|------|------|
| 小狗 Zergling | $25 | 5 | 48 | 0.4s | 地面 | 最便宜的塔 |
| 刺蛇 Hydralisk | $75 | 10 | 160 | 0.7s | 空地 | |
| 潜伏者 Lurker | $125 | 20 | 96 | 1.5s | 地面 | 32px 溅射 |
| 大象 Ultralisk | $200 | 35 | 64 | 1.2s | 地面 | 近战重甲 |
| 飞龙 Mutalisk | $100 | 9 | 96 | 0.6s | 空地 | 16px 溅射 |
| 守护者 Guardian | $150 | 20 | 256 | 2.0s | 地面 | 空中单位 |
| 吞噬者 Devourer | $200 | 12 | 192 | 1.2s | 空中 | 24px 溅射 |
| 女王 Queen | $100 | 0 | 256 | - | 地面 | 寄生 DoT（5 伤害 + 50% 减速），20s CD |
| 地刺塔 Sunken Colony | $100 | 25 | 160 | 1.2s | 地面 | |
| 孢子塔 Spore Colony | $75 | 12 | 224 | 0.8s | 空中 | |

每种炮塔均可升级 **2 次**，提升伤害、射程、射速。

## 敌人类型

地面敌人 19 种，空中敌人 5 种（第 4 波开始出现）。敌人按种族/难度动态生成，每波数量和强度递增。

**难度加成：**

| 难度 | 初始金钱 | 初始生命 |
|------|---------|---------|
| 简单 | ×1.2 | ×1.5 |
| 普通 | ×1.0 | ×1.0 |
| 困难 | ×0.8 | ×0.7 |
| 疯狂 | ×0.6 | ×0.5 |

## 操作方法

| 操作 | 说明 |
|------|------|
| 左键点击空地 | 建造炮塔 |
| 左键点击炮塔 | 打开升级/出售菜单 |
| 右键 | 取消放置 |
| 空格 Space | 暂停/继续 |
| 滚轮 | 地图选择界面滚动 |

## 项目结构

```
src/
  main.py                       # 入口
  core/
    game.py                     # 游戏主循环、状态管理
    constants.py                # 常量（颜色、路径、配置）
  entities/
    tower.py                    # 炮塔 + 统计数据
    enemy.py                    # 敌人 + 统计数据
    sprite.py                   # Spritesheet 加载 + 动画
    projectile.py               # 投射物
    wave_manager.py             # 波次管理
  systems/
    enemy_generator.py          # 动态敌人生成
    economy.py                  # 经济系统
    path.py                     # 路径系统
    targeting.py                # 索敌系统
    sound_manager.py            # 音效管理
    map_parser.py               # SCM/SCX 地图解析器
    sc_pathfinder.py            # A* 寻路
    tile_renderer.py            # 地形渲染器
  ui/
    screens.py                  # 菜单界面
    hud.py                      # 底部信息栏
    tower_menu.py               # 建造/升级菜单
  map/                          # 预渲染地图背景 (01.png - 08.png)
assets/
  sprites/                      # Spritesheet PNG (按种族分类)
  music/
    bgm.ogg                     # 背景音乐
StarCraft108B/
  StarCraft.ico                 # 窗口图标
  MAPS/                         # 原始星际争霸地图
  StarDat.mpq                   # 数据包（需自行获取）
  BrooDat.mpq                   # 数据包（需自行获取）
data/
  enemies.json                  # 敌人定义
  towers.json                   # 炮塔定义
  levels/                       # 关卡缓存
tools/
  grp_to_png.py                 # GRP → PNG 提取工具
```

## 音效

- 背景音乐：`assets/music/bgm.ogg`
- 音效文件需从原版星际争霸的 `StarDat.mpq`、`BrooDat.mpq` 中提取

## 地图

- **当前使用**：8 张预渲染 PNG 地图（`src/map/`），每难度 2 张，游戏中自动选择
- **支持解析**：标准 `.scm` / `.scx` 地图格式，包含 A* 路径查找和自动裁剪（未接入当前菜单流程，但功能完整）

## 构建说明

### 从原版星际争霸提取素材

将 `StarDat.mpq` 和 `BrooDat.mpq` 复制到 `StarCraft108B/` 目录即可启用路径解析和 TileSet 渲染。

### 提取 Spritesheet

```bash
python tools/grp_to_png.py <input.grp> <output.png>
```

## 技术栈

- **引擎**：Pygame
- **动画**：GRP spritesheet → PNG → 逐帧动画（含行走/攻击循环）
- **路径数据**：从 MPQ 读取 CV5（地形类型）+ 地图文件
- **寻路**：A\* 算法
- **碰撞**：网格系统（32×32 瓦片）

## 许可

本项目素材来源于《星际争霸 1.08b》，版权归 Blizzard Entertainment 所有。代码部分仅供学习交流使用。


