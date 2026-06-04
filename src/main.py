"""
星际争霸 塔防 — 入口 (Pygame 版本)
"""
import sys
import os
import json
import pygame

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, LEVELS_DIR, FPS
)
from src.core.game import Game


def load_level(filename: str) -> dict:
    """加载关卡配置文件"""
    filepath = os.path.join(LEVELS_DIR, filename)
    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)
    data["path"] = [(p[0], p[1]) for p in data["path"]]
    return data


def main():
    """程序入口"""
    pygame.init()
    pygame.font.init()

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("星际争霸 塔防 — StarCraft Tower Defense")

    # 设置窗口图标
    icon_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "StarCraft108B", "StarCraft.ico")
    try:
        icon = pygame.image.load(icon_path)
        pygame.display.set_icon(icon)
    except Exception:
        pass  # 图标加载失败不影响运行
    clock = pygame.time.Clock()

    # 创建游戏
    game = Game(screen)

    # 加载关卡数据
    level_data = load_level("level_01.json")
    game.level_data = level_data

    # 显示主菜单
    game.show_menu()

    # 游戏循环
    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0  # 秒

        # 事件处理
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEMOTION:
                game.on_mouse_move(event)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:      # 左键
                    game.on_mouse_click(event)
                elif event.button == 3:     # 右键
                    game.on_right_click(event)
                elif event.button in (4, 5):  # 滚轮
                    dy = 1 if event.button == 4 else -1
                    game.screens.handle_scroll(dy)
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    game.toggle_pause()

        # 更新
        game.update(dt)

        # 渲染
        screen.fill(game.bg_color)
        game.render()
        pygame.display.flip()

        if not game.running:
            running = False

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
