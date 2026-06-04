"""
工具: 从 GRP 精灵文件解码为 PNG spritesheet

正确的 GRP 格式 (来自 sc_bw_viewer.py):
  2字节: frame_count (uint16)
  2字节: max_width (uint16)
  2字节: max_height (uint16)
  然后每帧8字节: ox(1) + oy(1) + sx(1) + sy(1) + 4字节文件偏移
  行偏移表: 每个 y 一个 uint16 (从文件偏移处开始)

RLE (从文件偏移+行偏移处开始):
  0x80: 透明跳过 (b & 0x7f = 像素数)
  0x40: 填充 (b & 0x3f = 像素数, 下一个字节 = palette索引)
  其他: 原始像素 (b = 像素数, 接下来 b 个字节 = palette索引们)

用法: python tools/grp_to_png.py --race all
      python tools/grp_to_png.py --unit marine
"""
import os
import struct
import argparse
from PIL import Image

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STARDAT_UNIT = os.path.join(PROJECT_ROOT, "extracted", "stardat", "unit")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "assets", "sprites")
TUNIT_PCX = os.path.join(PROJECT_ROOT, "extracted", "stardat", "game", "tunit.pcx")

UNIT_GRP_MAP = {
    "marine":        ("terran", "marine"),
    "firebat":       ("terran", "firebat"),
    "ghost":         ("terran", "ghost"),
    "goliath":       ("terran", "goliath"),
    "siege_tank":    ("terran", "tank"),
    "battlecruiser": ("terran", "battlecr"),
    "wraith":        ("terran", "wessel"),
    "valkyrie":      ("terran", "wesselt"),
    "zealot":        ("protoss", "zealot"),
    "dragoon":       ("protoss", "dragoon"),
    "dark_templar":  ("protoss", "dtemplar"),
    "archon":        ("protoss", "archon"),
    "scout":         ("protoss", "scout"),
    "carrier":       ("protoss", "carrier"),
    "arbiter":       ("protoss", "arbiter"),
    "high_templar":  ("protoss", "templar"),
    "zergling":      ("zerg", "zergling"),
    "hydralisk":     ("zerg", "hydra"),
    "lurker":        ("zerg", "lurker"),
    "guardian":      ("zerg", "guardian"),
    "queen":         ("zerg", "queen"),
    "ultralisk":     ("zerg", "ultra"),
    "mutalisk":      ("zerg", "mutalid"),
    "devourer":      ("zerg", "avenger"),
    "bullet":        ("bullet", "gemini"),
    "cannon_shot":   ("bullet", "psibeam"),
    "spine":         ("bullet", "spores"),
    "bullet_grenade":  ("bullet", "grenade"),
    "bullet_hks":      ("bullet", "hks"),
    "bullet_explo1":   ("bullet", "explo1"),
    "bullet_dragbull": ("bullet", "dragbull"),
    "bullet_ephfire":  ("bullet", "ephfire"),
    "bullet_eycbull":  ("bullet", "eycbull"),
    "bullet_epbbul":   ("bullet", "epbbul"),
    "bunker":        ("terran", "pillbox"),
    "missile_turret": ("terran", "missile"),
    "photon_cannon": ("protoss", "photon"),
}

RACE_GROUPS = {
    "terran":  ["marine","firebat","ghost","goliath","siege_tank","wraith","battlecruiser","valkyrie","bunker","missile_turret"],
    "protoss": ["zealot","dragoon","high_templar","dark_templar","archon","scout","carrier","arbiter","photon_cannon"],
    "zerg":    ["zergling","hydralisk","lurker","ultralisk","mutalisk","guardian","devourer","queen"],
    "bullet":  ["bullet","cannon_shot","spine","bullet_grenade","bullet_hks","bullet_explo1","bullet_dragbull","bullet_ephfire","bullet_eycbull","bullet_epbbul"],
}


def load_palette(path: str) -> list:
    """从 PCX 文件加载调色板 (最后768字节 + 0x0C标识符)"""
    with open(path, 'rb') as f:
        data = f.read()
    if len(data) > 769 and data[-769] == 0x0C:
        return [(data[-768+i*3], data[-768+i*3+1], data[-768+i*3+2]) for i in range(256)]
    return [(min(i*4, 255),) * 3 for i in range(256)]


def decode_grp(path: str, pal: list) -> list:
    """用正确的 GRP 格式解码"""
    with open(path, 'rb') as f:
        data = f.read()
    fc = struct.unpack_from('<H', data, 0)[0]  # frame_count
    mw = struct.unpack_from('<H', data, 2)[0]  # max_width
    mh = struct.unpack_from('<H', data, 4)[0]  # max_height

    frames = []
    pos = 6
    for fi in range(fc):
        ox = data[pos]; oy = data[pos+1]
        sx = data[pos+2]; sy = data[pos+3]
        fo = struct.unpack_from('<I', data, pos+4)[0]
        pos += 8

        if sx > 400 or sy > 400 or sx == 0 or sy == 0:
            continue
        if fo >= len(data):
            continue

        # 行偏移表
        los = [struct.unpack_from('<H', data, fo + y * 2)[0] for y in range(sy)]

        # 构建像素图 (px[y][x] = (R,G,B,A))
        px = [[(0, 0, 0, 0)] * sx for _ in range(sy)]

        for y in range(sy):
            x_pos = 0
            p = fo + los[y]
            while x_pos < sx and p < len(data):
                b = data[p]; p += 1
                if b & 0x80:
                    # 透明跳过
                    c = b & 0x7f
                    if c > sx - x_pos:
                        c = sx - x_pos
                    x_pos += c
                elif b & 0x40:
                    # 颜色填充
                    c = b & 0x3f
                    if c > sx - x_pos:
                        c = sx - x_pos
                    ci = data[p] if p < len(data) else 0; p += 1
                    r, g, b2 = pal[ci] if ci < len(pal) else (255, 0, 255)
                    for dx in range(c):
                        px[y][x_pos + dx] = (r, g, b2, 255)
                    x_pos += c
                else:
                    # 原始像素
                    c = b
                    if c > sx - x_pos:
                        c = sx - x_pos
                    for dx in range(c):
                        if p < len(data):
                            ci = data[p]; p += 1
                            if ci == 0:
                                px[y][x_pos + dx] = (0, 0, 0, 0)
                            elif ci < len(pal):
                                r, g, b2 = pal[ci]
                                px[y][x_pos + dx] = (r, g, b2, 255)
                            else:
                                px[y][x_pos + dx] = (255, 0, 255, 255)
                    x_pos += c

        frames.append({'w': sx, 'h': sy, 'xo': ox, 'yo': oy, 'px': px})

    return frames


def save_sheet(frames: list, uid: str, out: str):
    if not frames:
        print(f"  ✗ 无帧"); return
    mx = min(f['xo'] for f in frames)
    Mx = max(f['xo']+f['w'] for f in frames)
    my = min(f['yo'] for f in frames)
    My = max(f['yo']+f['h'] for f in frames)
    fw, fh = max(1, Mx-mx), max(1, My-my)
    cols, gap = 8, 2
    rows = (len(frames)+cols-1)//cols
    tw, th = cols*(fw+gap), rows*(fh+gap)
    sheet = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    for idx, fr in enumerate(frames):
        c, r = idx % cols, idx // cols
        img = Image.new("RGBA", (fr['w'], fr['h']), (0, 0, 0, 0))
        for y in range(fr['h']):
            for x in range(fr['w']):
                img.putpixel((x, y), fr['px'][y][x])
        sheet.paste(img, (c*(fw+gap)+(fr['xo']-mx), r*(fh+gap)+(fr['yo']-my)))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sheet.save(out)
    print(f"  ✓ {len(frames)}帧 → {out}")

    # 写入帧元数据 JSON
    frame_rects = [{"w": fr['w'], "h": fr['h'], "xo": fr['xo'], "yo": fr['yo']} for fr in frames]
    meta = {
        "num_frames": len(frames),
        "cols": cols,
        "gap": gap,
        "fw": fw,
        "fh": fh,
        "mx": mx,
        "my": my,
        "width": tw,
        "height": th,
        "frames": frame_rects,
    }
    meta_path = os.path.splitext(out)[0] + "_meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        import json
        json.dump(meta, f, indent=2)
    print(f"  ✓ → {meta_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--race", choices=["terran", "protoss", "zerg", "all", "bullet"], default="all")
    ap.add_argument("--unit", type=str)
    args = ap.parse_args()

    pal = load_palette(TUNIT_PCX)
    print(f"调色板: {len(pal)} 色")

    if args.unit:
        units = [args.unit]
    elif args.race == "all":
        units = list(UNIT_GRP_MAP.keys())
    else:
        units = RACE_GROUPS.get(args.race, [])

    ok = fail = 0
    for uid in units:
        e = UNIT_GRP_MAP.get(uid)
        if not e:
            print(f"  ✗ {uid}: 无映射"); fail += 1; continue
        p = os.path.join(STARDAT_UNIT, e[0], f"{e[1]}.grp")
        if not os.path.exists(p):
            print(f"  ✗ {uid}: {p} 不存在"); fail += 1; continue
        print(f"  → {uid}")
        fr = decode_grp(p, pal)
        if fr:
            save_sheet(fr, uid, os.path.join(OUTPUT_DIR, e[0], f"{uid}.png"))
            ok += 1
        else:
            print(f"  ✗ 解码失败"); fail += 1
    print(f"\n✓ {ok}  ✗ {fail}")


if __name__ == "__main__":
    main()
