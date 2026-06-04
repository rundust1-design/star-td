"""
星际争霸地图解析器 — 从 .scm/.scx 文件读取 CHK 数据

SCM/SCX 文件是 MPQ 存档（可能带加密），用 pympq 解包。
解包后得到 scenario.chk，由 CHK 段组成，每段 8 字节头
(4 字节 tag + 4 字节 uint32 LE size)。

pympq 的 C 扩展有严重的 refcount 问题（exit 时 segfault）,
而且一个进程内同时只能打开一个 archive。
因此所有 MPQ 操作都通过子进程隔离。
"""
import os
import struct
from dataclasses import dataclass, field


@dataclass
class MapData:
    """解析后的地图数据"""
    width: int              # tile 宽度
    height: int             # tile 高度
    tileset_id: int         # 0=badlands ... 8=ice
    tiles: list[list[int]]  # [y][x] tile ID
    units: list             # [(type, x, y, owner), ...]
    start_locations: dict[int, tuple[int, int]]  # player_id -> (x, y)
    name: str = ""


TILESET_NAMES = {
    0: "badlands", 1: "space", 2: "installation", 3: "ashworld",
    4: "jungle", 5: "desert", 6: "arctic", 7: "twilight", 8: "ice",
}

# 起始位置单位 ID (SC标准)
START_LOCATION_TYPE = 214


def _run_mpq_subprocess(script_code: str, timeout: int = 30) -> int:
    """在子进程中运行 MPQ 操作脚本，返回退出码。"""
    import subprocess
    import sys
    proc = subprocess.run(
        [sys.executable, "-c", script_code],
        capture_output=True,
        timeout=timeout,
    )
    return proc.returncode


class MapParser:
    """解析 .scm/.scx 地图文件"""

    @staticmethod
    def read_map(filepath: str) -> MapData:
        """从 .scm/.scx 文件读取地图数据"""
        # 先用 mpyq 尝试（未加密的旧版本）
        import mpyq
        try:
            archive = mpyq.MPQArchive(filepath)
            files = archive.extract()
            map_raw = files.get(b"starcraft.map") or files.get("starcraft.map")
            if map_raw:
                return MapParser._parse_chk_data(map_raw, filepath)
        except Exception:
            pass

        # 用 pympq（支持加密），通过子进程隔离
        return MapParser._read_pympq(filepath)

    @staticmethod
    def _read_pympq(filepath: str) -> MapData:
        """用子进程中的 pympq 读取加密的 MPQ 并解析 scenario.chk

        pympq 退出时的 segfault 会破坏输出文件，
        所以采用两步：1) 提取到临时文件 2) 确认完整写入后退出
        """
        import sys
        import tempfile

        tmp_raw = tempfile.mktemp(suffix=".chk_raw")

        # 子进程脚本（注意缩进！）
        sc = []
        sc.append("import pympq, os, sys")
        sc.append("fp = " + repr(filepath))
        sc.append("raw_out = " + repr(tmp_raw))
        sc.append("try:")
        sc.append("    a = pympq.open_archive(fp)")
        sc.append("except:")
        sc.append("    sys.exit(2)")
        sc.append("for chk_name in ['staredit\\\\scenario.chk', 'starcraft.map', 'scenario.chk']:")
        sc.append("    if a.has_file(chk_name):")
        sc.append("        tmp = fp + '.tmp_chk'")
        sc.append("        try:")
        sc.append("            a.extract_file(chk_name, tmp)")
        sc.append("            if os.path.exists(tmp):")
        sc.append("                with open(tmp, 'rb') as f:")
        sc.append("                    d = f.read()")
        sc.append("                del a")
        sc.append("                with open(raw_out, 'wb') as f:")
        sc.append("                    f.write(d)")
        sc.append("                    f.flush()")
        sc.append("                    os.fsync(f.fileno())")
        sc.append("                os.unlink(tmp)")
        sc.append("                sys.exit(0)")
        sc.append("        except:")
        sc.append("            try:")
        sc.append("                if os.path.exists(tmp): os.unlink(tmp)")
        sc.append("            except:")
        sc.append("                pass")
        sc.append("sys.exit(1)")

        script = "\n".join(sc)

        _run_mpq_subprocess(script)

        if os.path.exists(tmp_raw) and os.path.getsize(tmp_raw) > 0:
            with open(tmp_raw, "rb") as f:
                raw = f.read()
            try:
                os.unlink(tmp_raw)
            except Exception:
                pass
            return MapParser._parse_chk_data(raw, filepath)

        try:
            os.unlink(tmp_raw)
        except Exception:
            pass
        raise ValueError(f"地图 {filepath} 中未找到 CHK 数据")

    @staticmethod
    def _parse_chk(binary: bytes) -> dict[bytes, bytes]:
        """
        解析 CHK 格式: 4 字节 tag + 4 字节 size (uint32 LE) + size 字节数据。
        遇到异常数据时单字节跳过恢复对齐。
        """
        sections = {}
        pos = 0
        while pos + 8 <= len(binary):
            tag = binary[pos:pos+4]
            size = struct.unpack("<I", binary[pos+4:pos+8])[0]
            if size > len(binary) - pos - 8 or size == 0:
                pos += 1
                continue
            chunk = binary[pos+8:pos+8+size]
            sections[tag] = chunk
            pos += 8 + size
        return sections

    @staticmethod
    def _parse_chk_data(raw: bytes, filepath: str) -> MapData:
        """从原始 CHK 二进制数据构建 MapData"""
        sections = MapParser._parse_chk(raw)

        data = MapData(
            width=0, height=0, tileset_id=0,
            tiles=[], units=[], start_locations={},
            name=os.path.splitext(os.path.basename(filepath))[0],
        )

        # DIM
        dim_data = sections.get(b"DIM ") or sections.get("DIM ")
        if dim_data and len(dim_data) >= 4:
            data.width, data.height = struct.unpack("<HH", dim_data[:4])

        # ERA
        era_data = sections.get(b"ERA ") or sections.get("ERA ")
        if era_data and len(era_data) >= 2:
            data.tileset_id = struct.unpack("<H", era_data[:2])[0]

        # MTXM — tile IDs (width*height*2 bytes)
        mtxm_data = sections.get(b"MTXM") or sections.get("MTXM")
        if mtxm_data and data.width > 0 and data.height > 0:
            raw_tiles = mtxm_data
            for y in range(data.height):
                row = []
                for x in range(data.width):
                    idx = (y * data.width + x) * 2
                    if idx + 2 <= len(raw_tiles):
                        tile_id = struct.unpack("<H", raw_tiles[idx:idx+2])[0]
                    else:
                        tile_id = 0
                    row.append(tile_id)
                data.tiles.append(row)

        # UNIT — 每个单位 36 字节（SC 标准 UNIT 段格式）
        # StarEdit 编码: offset 0-5 是编码的 type/x/y
        # offset 8-9 是真实的 SC unit ID (uint16 LE)
        # 坐标解码: tile = raw_word / 32
        unit_data = sections.get(b"UNIT") or sections.get("UNIT")
        if unit_data:
            REC = 36
            start_idx = 0
            for i in range(0, len(unit_data), REC):
                rec = unit_data[i:i+REC]
                if len(rec) < REC:
                    break
                sc_unit_id = struct.unpack("<H", rec[8:10])[0]
                x = struct.unpack("<H", rec[2:4])[0] // 32
                y = struct.unpack("<H", rec[4:6])[0] // 32
                owner = rec[10]
                data.units.append((sc_unit_id, x, y, owner))
                if sc_unit_id == START_LOCATION_TYPE:
                    data.start_locations[start_idx] = (x, y)
                    start_idx += 1

        return data

    @staticmethod
    def scan_maps() -> list[dict]:
        """扫描 MAPS 目录下的所有 .scm/.scx 文件

        结果缓存到 _map_index.json，仅在文件列表有变化时重建。
        """
        from src.core.constants import MAPS_DIR, CACHED_MAPS_FILE, LEVELS_CACHE_DIR
        import json

        # 计算目录摘要（快速 — 只读文件列表和修改时间）
        current_hash = _compute_maps_hash(MAPS_DIR)

        os.makedirs(LEVELS_CACHE_DIR, exist_ok=True)

        # 尝试读取缓存
        if os.path.exists(CACHED_MAPS_FILE):
            try:
                with open(CACHED_MAPS_FILE, "r", encoding="utf-8") as f:
                    cache = json.load(f)
                if cache.get("hash") == current_hash:
                    return cache["maps"]
            except Exception:
                pass

        # 缓存无效，完整扫描
        maps = _do_scan_maps(MAPS_DIR)

        # 写入缓存
        try:
            with open(CACHED_MAPS_FILE, "w", encoding="utf-8") as f:
                json.dump({"hash": current_hash, "maps": maps}, f)
        except Exception:
            pass

        return maps


def _compute_maps_hash(maps_dir: str) -> str:
    """快速计算地图目录的摘要（文件路径 + mtime）

    只要文件列表或修改时间不变，哈希就不变。
    """
    import hashlib
    h = hashlib.md5()
    for root, dirs, files in os.walk(maps_dir):
        for fn in sorted(files):
            if fn.lower().endswith((".scm", ".scx")):
                full = os.path.join(root, fn)
                try:
                    stat = os.stat(full)
                    # 文件名 + 大小 + mtime（精确到秒）作为摘要
                    h.update(f"{fn}:{stat.st_size}:{int(stat.st_mtime)}\n".encode())
                except OSError:
                    pass
    return h.hexdigest()


def _do_scan_maps(maps_dir: str) -> list[dict]:
    """完整扫描并解析 MAPS 目录"""
    maps = []
    for root, dirs, files in os.walk(maps_dir):
        for fn in sorted(files):
            if fn.lower().endswith((".scm", ".scx")):
                full_path = os.path.join(root, fn)
                try:
                    md = MapParser.read_map(full_path)
                    rel_path = os.path.relpath(full_path, maps_dir)
                    maps.append({
                        "name": os.path.splitext(fn)[0],
                        "path": rel_path,
                        "full_path": full_path,
                        "width": md.width,
                        "height": md.height,
                        "tileset": TILESET_NAMES.get(md.tileset_id, f"unknown({md.tileset_id})"),
                        "tileset_id": md.tileset_id,
                        "players": len(md.start_locations),
                    })
                except Exception:
                    pass
    # 按玩家数降序排（人多的地图更靠前）
    maps.sort(key=lambda m: m["players"], reverse=True)
    return maps
