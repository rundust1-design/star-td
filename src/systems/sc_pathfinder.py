"""
星际地图路径提取 — 从地图数据中提取可行路径

流程:
  1. 从 MPQ 加载 tileset 的 CV5 文件，获取每个 tile 的可通行性
  2. 构建可通行网格 (bool)
  3. 从玩家起始位置到敌人起始位置 A* 寻路
  4. 从路径周围裁剪 32×20 区域作为游戏关卡
"""
import os
import struct
import math

# tileset ID → CV5 文件名
TILESET_CV5 = {
    0: "badlands", 1: "space", 2: "installation",
    3: "ashworld", 4: "jungle", 5: "desert",
    6: "arctic", 7: "twilight", 8: "ice",
}


def _read_mpq_single(archive_path: str, file_paths: list[str]) -> dict[str, bytes | None]:
    """从同一个 MPQ 中读取多个文件，只打开一次 archive。

    返回: {file_path: bytes | None}
    pympq 使用小写 + 反斜杠路径格式。
    """
    import pympq
    import os

    try:
        archive = pympq.open_archive(archive_path)
    except Exception:
        return {p: None for p in file_paths}

    result = {}
    for fp in file_paths:
        norm_path = fp.replace("/", "\\").lower()
        if not archive.has_file(norm_path):
            result[fp] = None
            continue
        tmp_path = archive_path + ".tmp_extract"
        try:
            archive.extract_file(norm_path, tmp_path)
            if os.path.exists(tmp_path):
                with open(tmp_path, "rb") as fh:
                    result[fp] = fh.read()
            else:
                result[fp] = None
        except Exception:
            result[fp] = None
        finally:
            try:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
            except Exception:
                pass

    return result


def _read_mpq(archive_path: str, internal_path: str) -> bytes | None:
    """从 MPQ 文件中读取单个内部文件

    pympq 的 C 扩展存在句柄泄漏问题（一个进程内不能打开两个 MPQ），
    而且其 GC 清理时的 segfault 导致子进程退出码非零。
    解决方案：在子进程中提取，写入临时文件，主进程读取，忽略子进程退出码。

    返回文件 bytes 或 None。
    """
    import subprocess
    import sys
    import os
    import tempfile

    try:
        # 使用临时文件传递数据，避免管道 segfault 干扰
        tmp_out = tempfile.mktemp(suffix=".cv5_data")

        script = (
            "import sys; sys.path.insert(0, " + repr(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))) + ")\n"
            "from src.core.constants import STARDAT_MPQ, BROODAT_MPQ\n"
            "import pympq, os\n"
            "ap = " + repr(archive_path) + "\n"
            "ip = " + repr(internal_path) + "\n"
            "out = " + repr(tmp_out) + "\n"
            "norm = ip.replace('/', '\\\\').lower()\n"
            "try:\n"
            "    a = pympq.open_archive(ap)\n"
            "except:\n"
            "    open(out, 'w').close(); sys.exit(2)\n"
            "if not a.has_file(norm):\n"
            "    open(out, 'w').close(); sys.exit(1)\n"
            "tmp = ap + '.tmp_extract'\n"
            "try:\n"
            "    a.extract_file(norm, tmp)\n"
            "    if os.path.exists(tmp):\n"
            "        with open(tmp, 'rb') as f:\n"
            "            data = f.read()\n"
            "        with open(out, 'wb') as f:\n"
            "            f.write(data)\n"
            "        os.unlink(tmp)\n"
            "except:\n"
            "    pass\n"
        )

        proc = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            timeout=30,
        )

        # 即使子进程 segfault，tempfile 也可能已经写入
        if os.path.exists(tmp_out) and os.path.getsize(tmp_out) > 0:
            with open(tmp_out, "rb") as f:
                data = f.read()
            try:
                os.unlink(tmp_out)
            except Exception:
                pass
            return data

        try:
            os.unlink(tmp_out)
        except Exception:
            pass
        return None
    except Exception:
        return None


def _read_mpq_batch_first_found(archive_paths: list[str], internal_path: str) -> bytes | None:
    """从多个 MPQ 中依次查找一个文件，找到即返回。
    因为 _read_mpq 使用子进程隔离，每个调用都是独立进程。
    """
    for archive_path in archive_paths:
        data = _read_mpq(archive_path, internal_path)
        if data is not None:
            return data
    return None


def load_cv5(tileset_id: int) -> list[list[int]]:
    """
    加载指定 tileset 的 CV5 文件。
    返回: cv5_entries, 每个 entry 是 16 个 uint16 subtile groups
    """
    from src.core.constants import STARDAT_MPQ, BROODAT_MPQ

    cv5_name = TILESET_CV5.get(tileset_id)
    if not cv5_name:
        return []

    # 尝试多种路径变体（StarDat: 小写, BrooDat: 大写或小写）
    candidates = [
        f"tileset\\{cv5_name.lower()}.cv5",
        f"tileset\\{cv5_name.lower()}.CV5",
        f"TILESET\\{cv5_name.upper()}.CV5",
        f"tileset\\{cv5_name.lower()}.cv5",
        f"TILESET\\SPACE.CV5",  # 特例：某些 maps 文件夹
    ]

    for cv5_path in candidates:
        data = _read_mpq_batch_first_found([BROODAT_MPQ, STARDAT_MPQ], cv5_path)
        if data is not None and len(data) > 0:
            break
    else:
        return []

    # CV5: 每 48 字节一个 entry
    ENTRY_SIZE = 48
    entries = []
    for i in range(0, len(data), ENTRY_SIZE):
        entry = data[i:i+ENTRY_SIZE]
        if len(entry) < ENTRY_SIZE:
            break
        # 前 32 字节 = 16 x uint16 微格 group 索引
        # 0x20-0x21 = 可通行掩码 (2 字节)
        walk_mask = struct.unpack("<H", entry[0x20:0x22])[0]
        # 提取 16 个微格 group
        groups = []
        for g in range(16):
            grp = struct.unpack("<H", entry[g*2:g*2+2])[0]
            groups.append(grp)
        entries.append({
            "groups": groups,
            "walk_mask": walk_mask,
        })

    return entries


def is_tile_walkable(tile_id: int, cv5_entries: list) -> bool:
    """判断一个 tile 是否可通行

    如果 tile_id 在 CV5 范围内，检查 walk_mask。
    如果超出 CV5 范围（装饰/覆盖 tile），默认视为可通行，
    因为大多数此类 tile 覆盖在可通行的基础地形上。
    """
    if tile_id < len(cv5_entries):
        entry = cv5_entries[tile_id]
        # walk_mask > 0 表示至少有一个微格可通行
        return entry["walk_mask"] > 0
    # 超出 CV5 范围的 tile（装饰/建筑覆盖层）
    # 大多数 SC 地图中这些 tile 是在可通行地形上的装饰
    return True


def _load_tileset_resource(tileset_id: int, ext: str, entry_size: int) -> list[int] | None:
    """通用函数：从 MPQ 加载 tileset 的 .vr4 / .vx4 等资源文件

    返回: list[int]（每个 entry 的 uint16 值），失败时返回 None
    """
    from src.core.constants import STARDAT_MPQ, BROODAT_MPQ

    tileset_name = TILESET_CV5.get(tileset_id)
    if not tileset_name:
        return None

    path = f"tileset\\{tileset_name.lower()}.{ext.lower()}"
    data = _read_mpq_batch_first_found([BROODAT_MPQ, STARDAT_MPQ], path)
    if data is None:
        return None

    values = []
    for i in range(0, len(data), entry_size):
        chunk = data[i:i + entry_size]
        if len(chunk) < entry_size:
            break
        val = struct.unpack("<H", chunk[:2])[0]
        values.append(val)
    return values


def load_vr4(tileset_id: int) -> list[int] | None:
    """加载 VR4 文件 — 将 CV5 group 索引映射到 GRP frame 索引

    VR4 是一个 uint16 数组，index = group_id, value = grp_frame_index
    """
    return _load_tileset_resource(tileset_id, "vr4", 2)


def load_vx4(tileset_id: int) -> list[int] | None:
    """加载 VX4 文件 — 覆盖层映射（同 VR4 格式）"""
    return _load_tileset_resource(tileset_id, "vx4", 2)


def resolve_tile_frames(tile_id: int, cv5_entries: list, vr4_entries: list) -> list[int]:
    """将 tile_id 解析为 16 个微格的 GRP frame 索引

    CV5 中每个 tile 有 16 个微格 group 索引（4x4），
    VR4 将 group_id 映射到实际 GRP frame 索引。

    返回: 16 个 GRP frame 索引（按行优先顺序）
    """
    if not cv5_entries or not vr4_entries:
        return []

    if tile_id >= len(cv5_entries):
        return []

    entry = cv5_entries[tile_id]
    frames = []
    for group_id in entry["groups"]:
        if group_id < len(vr4_entries):
            frames.append(vr4_entries[group_id])
        else:
            frames.append(0)
    return frames


def build_walkability_grid(tiles: list[list[int]], cv5_entries: list) -> list[list[bool]]:
    """构建可通行网格"""
    height = len(tiles)
    width = len(tiles[0]) if height > 0 else 0
    grid = []
    for y in range(height):
        row = []
        for x in range(width):
            tile_id = tiles[y][x]
            row.append(is_tile_walkable(tile_id, cv5_entries))
        grid.append(row)
    return grid


def heuristic(a: tuple[int, int], b: tuple[int, int]) -> float:
    """曼哈顿距离"""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def find_path_on_grid(
    grid: list[list[bool]],
    start: tuple[int, int],
    end: tuple[int, int],
) -> list[tuple[int, int]] | None:
    """
    A* 寻路（4方向）
    返回: [(x, y), ...] 路径点列表（包含起终点），或 None
    """
    import heapq

    height = len(grid)
    width = len(grid[0]) if height > 0 else 0

    # 检查起点终点是否在范围内
    for (x, y) in [start, end]:
        if x < 0 or x >= width or y < 0 or y >= height:
            return None
        if not grid[y][x]:
            return None

    # 如果起终点相同，直接返回
    if start == end:
        return [start]

    open_set = []
    heapq.heappush(open_set, (0, start))
    came_from = {}
    g_score = {start: 0}
    f_score = {start: heuristic(start, end)}

    while open_set:
        current = heapq.heappop(open_set)[1]

        if current == end:
            # 重建路径
            path = []
            while current in came_from:
                path.append(current)
                current = came_from[current]
            path.append(start)
            path.reverse()
            return path

        cx, cy = current
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = cx + dx, cy + dy
            if nx < 0 or nx >= width or ny < 0 or ny >= height:
                continue
            if not grid[ny][nx]:
                continue

            neighbor = (nx, ny)
            tentative_g = g_score[current] + 1

            if neighbor not in g_score or tentative_g < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f = tentative_g + heuristic(neighbor, end)
                f_score[neighbor] = f
                heapq.heappush(open_set, (f, neighbor))

    return None


def simplify_path(path: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """简化路径，去除共线的中间点"""
    if len(path) <= 2:
        return path

    simplified = [path[0]]
    for i in range(1, len(path) - 1):
        prev = path[i - 1]
        curr = path[i]
        nxt = path[i + 1]
        # 检查是否共线（方向改变）
        dx1 = curr[0] - prev[0]
        dy1 = curr[1] - prev[1]
        dx2 = nxt[0] - curr[0]
        dy2 = nxt[1] - curr[1]
        if dx1 != dx2 or dy1 != dy2:
            simplified.append(curr)
    simplified.append(path[-1])
    return simplified


def crop_to_32x20(path: list[tuple[int, int]], map_width: int, map_height: int) -> tuple[int, int, list[tuple[int, int]]]:
    """
    从地图中裁剪出 32×20 区域，使其包含路径中尽可能多的部分。

    策略: 把路径入口放在裁剪窗口的上部（或中部），路径出口在底部。
    如果路径高度超过 20，优先保留后半段（出口方向）。

    返回: (crop_x, crop_y, rel_path)
      - crop_x, crop_y: 裁剪窗口左上角 tile 坐标
      - rel_path: 路径点相对于裁剪窗口的坐标（仍在窗口外的点被丢弃）
    """
    CROP_W, CROP_H = 32, 20

    if not path:
        return (0, 0, [])

    xs = [p[0] for p in path]
    ys = [p[1] for p in path]

    # 路径起点（入口）和终点（出口）
    first = path[0]
    last = path[-1]

    # 如果路径较短，直接居中裁剪
    path_h = max(ys) - min(ys) + 1
    path_w = max(xs) - min(xs) + 1

    if path_h <= CROP_H and path_w <= CROP_W:
        # 居中裁剪
        crop_x = max(0, (min(xs) + max(xs)) // 2 - CROP_W // 2)
        crop_y = max(0, (min(ys) + max(ys)) // 2 - CROP_H // 2)
        if crop_x + CROP_W > map_width:
            crop_x = max(0, map_width - CROP_W)
        if crop_y + CROP_H > map_height:
            crop_y = max(0, map_height - CROP_H)
    else:
        # 路径太长：以路径出口（敌人进入点）为锚点
        # 把出口放在裁剪窗口的底部
        exit_x, exit_y = last
        crop_x = max(0, exit_x - CROP_W // 2)
        if crop_x + CROP_W > map_width:
            crop_x = max(0, map_width - CROP_W)

        crop_y = max(0, exit_y - CROP_H + 3)  # 出口在底部往上 3 格
        if crop_y + CROP_H > map_height:
            crop_y = max(0, map_height - CROP_H)

    # 过滤掉超出裁剪窗口的路径点
    rel_path = []
    for px, py in path:
        rx, ry = px - crop_x, py - crop_y
        # 只保留在窗口内或紧邻边缘的点
        if -2 <= rx < CROP_W + 2 and -2 <= ry < CROP_H + 2:
            # 裁剪到窗口边界
            rx = max(0, min(CROP_W - 1, rx))
            ry = max(0, min(CROP_H - 1, ry))
            rel_path.append((rx, ry))

    # 确保路径起点和终点在窗口中
    if not rel_path or rel_path[0] != (max(0, min(CROP_W - 1, first[0] - crop_x)),
                                       max(0, min(CROP_H - 1, first[1] - crop_y))):
        rel_path.insert(0, (max(0, min(CROP_W - 1, first[0] - crop_x)),
                            max(0, min(CROP_H - 1, first[1] - crop_y))))
    if not rel_path or rel_path[-1] != (max(0, min(CROP_W - 1, last[0] - crop_x)),
                                        max(0, min(CROP_H - 1, last[1] - crop_y))):
        rel_path.append((max(0, min(CROP_W - 1, last[0] - crop_x)),
                         max(0, min(CROP_H - 1, last[1] - crop_y))))

    return (crop_x, crop_y, rel_path)


def extract_level_data(
    map_filepath: str,
    player_idx: int = 0,
    enemy_idx: int = 7,
) -> dict | None:
    """
    从星际地图文件提取关卡数据。

    策略: 通过在地图上寻找一条从顶部到底部的贯穿路径来找到
    游戏关卡。

    返回: {
        "name": str,
        "tiles": list[list[int]],  # 裁剪后的 32x20 tile 矩阵
        "path": [(x, y), ...],     # 简化后的路径点（相对于裁剪窗口）
        "crop_x": int,
        "crop_y": int,
        "map_width": int,
        "map_height": int,
    }
    """
    from src.systems.map_parser import MapParser

    # 1. 读取地图
    map_data = MapParser.read_map(map_filepath)

    # 2. 加载 CV5
    cv5 = load_cv5(map_data.tileset_id)
    if not cv5:
        grid = [[tile_id < 50 for tile_id in row] for row in map_data.tiles]
    else:
        grid = build_walkability_grid(map_data.tiles, cv5)

    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    if width == 0 or height == 0:
        return None

    # 采样辅助函数：将列表分成 n 个桶取代表值，确保全覆盖
    def _sample_buckets(lst, n):
        if not lst or n <= 0:
            return lst or []
        if len(lst) <= n:
            return lst
        result = []
        for i in range(n):
            result.append(lst[int(i * len(lst) / n)])
        seen = set()
        unique = []
        for v in result:
            if v not in seen:
                seen.add(v)
                unique.append(v)
        return unique

    # 3. 寻找从地图边缘到对侧的贯穿路径（上下方向优先）
    raw_path = None
    num_buckets = 40

    # 收集所有顶部/底部边缘可通行点
    top_starts = [x for x in range(width) if grid[0][x]]
    bot_ends = [x for x in range(width) if grid[height - 1][x]]

    if top_starts and bot_ends:
        top_sampled = _sample_buckets(top_starts, num_buckets)
        bot_sampled = _sample_buckets(bot_ends, num_buckets)
        # 配对策略：按 x 坐标接近度排序（可通行的顶/底边缘 x 相近处更可能连通）
        # 避免嵌套循环带来的组合爆炸
        pairs = []
        for xt in top_sampled:
            for xb in bot_sampled:
                pairs.append((xt, xb))
        # 按 |xt - xb| 排序，相近的优先
        pairs.sort(key=lambda p: abs(p[0] - p[1]))
        max_attempts = min(len(pairs), 800)
        for i in range(max_attempts):
            xt, xb = pairs[i]
            path = find_path_on_grid(grid, (xt, 0), (xb, height - 1))
            if path:
                raw_path = path
                break

    # 如果上下没找到，尝试左右贯穿
    if raw_path is None:
        left_starts = [y for y in range(height) if grid[y][0]]
        right_ends = [y for y in range(height) if grid[y][width - 1]]
        if left_starts and right_ends:
            left_sampled = _sample_buckets(left_starts, num_buckets)
            right_sampled = _sample_buckets(right_ends, num_buckets)
            pairs = []
            for yl in left_sampled:
                for yr in right_sampled:
                    pairs.append((yl, yr))
            pairs.sort(key=lambda p: abs(p[0] - p[1]))
            max_attempts = min(len(pairs), 800)
            for i in range(max_attempts):
                yl, yr = pairs[i]
                path = find_path_on_grid(grid, (0, yl), (width - 1, yr))
                if path:
                    raw_path = path
                    break

    if raw_path is None:
        return None

    # 4. 简化路径
    path = simplify_path(raw_path)

    # 5. 裁剪 32×20
    crop_x, crop_y, rel_path = crop_to_32x20(path, width, height)

    # 6. 提取裁剪后的 tile
    cropped_tiles = []
    for y in range(crop_y, min(crop_y + 20, height)):
        row = []
        for x in range(crop_x, min(crop_x + 32, width)):
            if y < len(map_data.tiles) and x < len(map_data.tiles[y]):
                row.append(map_data.tiles[y][x])
            else:
                row.append(0)
        cropped_tiles.append(row)

    return {
        "name": map_data.name,
        "tiles": cropped_tiles,
        "path": rel_path,
        "crop_x": crop_x,
        "crop_y": crop_y,
        "map_width": width,
        "map_height": height,
        "tileset_id": map_data.tileset_id,
        "tiles_full": map_data.tiles,
        "start_locations": map_data.start_locations,
    }


def find_path_in_tiles(tiles: list[list[int]], cv5_entries: list) -> list[tuple[int, int]] | None:
    """从 tile 矩阵中找一条从左到右的贯穿路径

    使用 CV5 判断可通行性，A* 从左边缘到右边缘寻路。
    如果没有 CV5（全可通行），生成一条在地图中间的锯齿路径。

    返回: [(x, y), ...] 路径点列表，或 None
    """
    grid = build_walkability_grid(tiles, cv5_entries)
    if not grid:
        return None

    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    if width == 0 or height == 0:
        return None

    # 检查 CV5 是否可用（至少一个不可通行 tile）
    has_real_cv5 = any(not cell for row in grid for cell in row)

    if has_real_cv5:
        # 有真实 CV5 数据：使用 A* 寻路
        # 尝试从左边缘到右边缘
        left_starts = [y for y in range(height) if grid[y][0]]
        right_ends = [y for y in range(height) if grid[y][width - 1]]

        if left_starts and right_ends:
            for yl in left_starts:
                for yr in right_ends:
                    path = find_path_on_grid(grid, (0, yl), (width - 1, yr))
                    if path:
                        return simplify_path(path)

        # 尝试从上边缘到下边缘
        top_starts = [x for x in range(width) if grid[0][x]]
        bot_ends = [x for x in range(width) if grid[height - 1][x]]

        if top_starts and bot_ends:
            for xt in top_starts:
                for xb in bot_ends:
                    path = find_path_on_grid(grid, (xt, 0), (xb, height - 1))
                    if path:
                        return simplify_path(path)

    # 没有 CV5 或 A* 失败：生成一个在地图中部穿行的合理路径
    # 为了塔防的趣味性，让路径在地图中间穿行
    path = []
    mid = height // 2
    for x in range(width):
        y = mid + int(3 * math.sin(x * 2 * math.pi / 32))  # 轻微波浪
        y = max(1, min(height - 2, y))
        path.append((x, y))

    return simplify_path(path)
