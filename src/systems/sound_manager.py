"""
音效管理器 — 懒加载 StarCraft WAV 音效 + BGM + 设置
"""
import os
import pygame

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOUND_DIR = os.path.join(PROJECT_ROOT, "extracted", "stardat", "sound")
MUSIC_DIR = os.path.join(PROJECT_ROOT, "assets", "music")


class SoundManager:
    """全局音效管理器，懒加载 + 独立通道 + 音量控制 + 开关"""

    # 配置：key → (相对路径, 默认音量)
    _FIRE_CONFIGS = {
        "marine":            ("bullet/dragbull.wav", 0.3),
        "firebat":           ("terran/firebat/tfbfir00.wav", 0.3),
        "ghost":             ("bullet/tghfir00.wav", 0.3),
        "goliath":           ("bullet/tgofir00.wav", 0.3),
        "siege_tank":        ("bullet/ttafir00.wav", 0.4),
        "wraith":            ("bullet/tphfi100.wav", 0.3),
        "battlecruiser":     ("bullet/tbayam00.wav", 0.5),
        "valkyrie":          ("bullet/tvufir00.wav", 0.3),
        "bunker":            ("bullet/dragbull.wav", 0.3),
        "missile_turret":    ("bullet/hkmissle.wav", 0.3),
        "dragoon":           ("bullet/dragbull.wav", 0.3),
        "archon":            ("bullet/psiblade.wav", 0.4),
        "scout":             ("bullet/ptrfir00.wav", 0.3),
        "carrier":           ("bullet/ptrfir00.wav", 0.3),
        "arbiter":           ("bullet/ptrfir00.wav", 0.3),
        "photon_cannon":     ("bullet/psibolt.wav", 0.3),
        "zealot":            ("bullet/psiblade.wav", 0.3),
        "reaver":            ("bullet/blastgn2.wav", 0.4),
        "zergling":          ("zerg/hydra/spifir00.wav", 0.2),
        "hydralisk":         ("bullet/zhyfir00.wav", 0.3),
        "lurker":            ("bullet/zlufir00.wav", 0.3),
        "ultralisk":         ("bullet/blastgn2.wav", 0.4),
        "mutalisk":          ("bullet/zmufir00.wav", 0.3),
        "guardian":          ("bullet/zgufir00.wav", 0.4),
        "devourer":          ("bullet/zdeatt00.wav", 0.3),
        "queen":             ("bullet/zqufir00.wav", 0.3),
        "sunken_colony":     ("bullet/zhyfir00.wav", 0.3),
        "spore_colony":      ("bullet/zhyfir00.wav", 0.3),
    }

    _VOICE_CONFIGS = {
        "marine":            ("terran/marine/tmardy00.wav", 0.5),
        "firebat":           ("terran/firebat/tfbrdy00.wav", 0.5),
        "ghost":             ("terran/ghost/tghrdy00.wav", 0.5),
        "goliath":           ("terran/goliath/tgordy00.wav", 0.5),
        "siege_tank":        ("terran/tank/ttardy00.wav", 0.5),
        "wraith":            ("terran/phoenix/tphrdy00.wav", 0.5),
        "battlecruiser":     ("terran/battle/tbardy00.wav", 0.5),
        "valkyrie":          ("terran/vessel/tverdy00.wav", 0.5),
        "bunker":            ("misc/tbldgplc.wav", 0.4),
        "missile_turret":    ("misc/tbldgplc.wav", 0.4),
        "dragoon":           ("protoss/dragoon/pdrrdy00.wav", 0.5),
        "archon":            ("protoss/archon/parrdy00.wav", 0.4),
        "scout":             ("protoss/scout/pscrdy00.wav", 0.5),
        "carrier":           ("protoss/carrier/pcardy00.wav", 0.5),
        "arbiter":           ("protoss/arbiter/pabrdy00.wav", 0.5),
        "photon_cannon":     ("misc/pbldgplc.wav", 0.4),
        "zealot":            ("protoss/zealot/pzerdy00.wav", 0.5),
        "reaver":            ("misc/pbldgplc.wav", 0.4),
        "zergling":          ("zerg/zergling/zzerdy00.wav", 0.5),
        "hydralisk":         ("zerg/hydra/zhyrdy00.wav", 0.5),
        "lurker":            ("zerg/avenger/zavrdy00.wav", 0.5),
        "ultralisk":         ("zerg/ultra/zulrdy00.wav", 0.5),
        "mutalisk":          ("zerg/mutalid/zmurdy00.wav", 0.5),
        "guardian":          ("zerg/guardian/zgurdy00.wav", 0.5),
        "devourer":          ("zerg/defiler/zderdy00.wav", 0.5),
        "queen":             ("zerg/queen/zqurdy00.wav", 0.5),
        "sunken_colony":     ("misc/zbldgplc.wav", 0.4),
        "spore_colony":      ("misc/zbldgplc.wav", 0.4),
    }

    _EVENT_CONFIGS = {
        "ui_click":          ("glue/mousedown2.wav", 0.3),
        "ui_hover":          ("glue/mouseover.wav", 0.2),
        "wave_start":        ("misc/transmission.wav", 0.4),
        "enemy_reach":       ("misc/outofgas.wav", 0.3),
        "game_over":         ("misc/youlose.wav", 0.6),
        "victory":           ("misc/youwin.wav", 0.6),
        "hit_generic":       ("bullet/laserhit.wav", 0.3),
        "hit_protoss":       ("bullet/pshield.wav", 0.3),
        "explosion":         ("misc/explo1.wav", 0.4),
    }

    def __init__(self):
        pygame.mixer.init(frequency=22050, size=-16, channels=2)
        # 独立通道
        self.ch_sfx = pygame.mixer.Channel(0)
        self.ch_voice = pygame.mixer.Channel(1)
        self.ch_ui = pygame.mixer.Channel(2)
        self.ch_event = pygame.mixer.Channel(3)
        # 声音缓存 key → pygame.mixer.Sound
        self._cache: dict[str, pygame.mixer.Sound] = {}

        # ═══ 音量 / 开关 设置 ═══
        self.sfx_enabled = True
        self.music_enabled = True
        self.sfx_volume = 1.0    # 0.0 ~ 1.0
        self.music_volume = 0.5  # 0.0 ~ 1.0
        self._bgm_loaded = False

    # ── BGM ──

    def play_bgm(self, file_name: str = "bgm.ogg"):
        """开始循环播放背景音乐（使用 pygame.mixer.music）"""
        if not self.music_enabled:
            self._bgm_loaded = True  # 标记以便后来启用时自动播放
            return
        path = os.path.join(MUSIC_DIR, file_name)
        if not os.path.isfile(path):
            self._bgm_loaded = False
            return
        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self.music_volume)
            pygame.mixer.music.play(loops=-1)
            self._bgm_loaded = True
        except Exception:
            self._bgm_loaded = False

    def stop_bgm(self):
        """停止背景音乐"""
        pygame.mixer.music.stop()
        self._bgm_loaded = False

    def set_sfx_volume(self, vol: float):
        """设置 SFX 总音量 0.0-1.0"""
        self.sfx_volume = max(0.0, min(1.0, vol))

    def set_music_volume(self, vol: float):
        """设置 BGM 音量"""
        self.music_volume = max(0.0, min(1.0, vol))
        if self._bgm_loaded:
            pygame.mixer.music.set_volume(self.music_volume)

    def toggle_sfx(self, enabled: bool = None):
        """切换 SFX 启用/禁用"""
        if enabled is not None:
            self.sfx_enabled = enabled
        else:
            self.sfx_enabled = not self.sfx_enabled

    def toggle_music(self, enabled: bool = None):
        """切换 BGM 启用/禁用，立即停止或恢复播放"""
        if enabled is not None:
            self.music_enabled = enabled
        else:
            self.music_enabled = not self.music_enabled

        if self.music_enabled and self._bgm_loaded:
            pygame.mixer.music.set_volume(self.music_volume)
            if not pygame.mixer.music.get_busy():
                self.play_bgm()
        elif not self.music_enabled:
            pygame.mixer.music.set_volume(0.0)

    def get_sfx_volume(self) -> float:
        return self.sfx_volume

    def get_music_volume(self) -> float:
        return self.music_volume

    # ── 公开 API（原有 + 音量适配）──

    def play_fire(self, tower_type: str):
        """塔开火"""
        if not self.sfx_enabled:
            return
        cfg = self._FIRE_CONFIGS.get(tower_type)
        if not cfg:
            return
        path, vol = cfg
        snd = self._load(path)
        if snd:
            self.ch_sfx.play(snd)
            self.ch_sfx.set_volume(vol * self.sfx_volume)

    def play_voice_rdy(self, tower_type: str):
        """塔第一次建造完毕语音"""
        if not self.sfx_enabled:
            return
        cfg = self._VOICE_CONFIGS.get(tower_type)
        if not cfg:
            return
        path, vol = cfg
        snd = self._load(path)
        if snd:
            self.ch_voice.stop()  # 打断之前的语音
            self.ch_voice.play(snd)
            self.ch_voice.set_volume(vol * self.sfx_volume)

    def play_event(self, key: str):
        """播发事件音效 (wave_start, game_over, victory 等)"""
        if not self.sfx_enabled:
            return
        cfg = self._EVENT_CONFIGS.get(key)
        if not cfg:
            return
        path, vol = cfg
        snd = self._load(path)
        if snd:
            self.ch_event.stop()
            self.ch_event.play(snd)
            self.ch_event.set_volume(vol * self.sfx_volume)

    def play_ui(self, key: str):
        """播发 UI 音效 (click, hover)"""
        if not self.sfx_enabled:
            return
        cfg = self._EVENT_CONFIGS.get(key)
        if not cfg:
            return
        path, vol = cfg
        snd = self._load(path)
        if snd:
            self.ch_ui.play(snd)
            self.ch_ui.set_volume(vol * self.sfx_volume)

    def play_hit(self, tower_type: str = ""):
        """子弹命中音效"""
        if not self.sfx_enabled:
            return
        race_path = ""
        if tower_type:
            from src.entities.tower import Tower
            stats = Tower.TOWER_STATS.get(tower_type, {})
            race_path = stats.get("race", "")
        key = "hit_protoss" if race_path == "protoss" else "hit_generic"
        cfg = self._EVENT_CONFIGS.get(key)
        if not cfg:
            return
        path, vol = cfg
        snd = self._load(path)
        if snd:
            self.ch_sfx.play(snd)
        self.ch_sfx.set_volume(vol * self.sfx_volume)

    # ── 内部 ──

    def _load(self, rel_path: str) -> pygame.mixer.Sound | None:
        """懒加载 WAV 文件"""
        if rel_path in self._cache:
            return self._cache[rel_path]
        full = os.path.join(SOUND_DIR, rel_path.replace("/", os.sep))
        if not os.path.isfile(full):
            return None
        try:
            snd = pygame.mixer.Sound(full)
            self._cache[rel_path] = snd
            return snd
        except Exception:
            return None
