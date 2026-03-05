"""拉取 HowToCook 菜谱到 temp 目录

来源: https://github.com/Anduin2017/HowToCook
用于私家厨房测试数据的菜谱链接。
"""

import os
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMP_DIR = os.path.join(PROJECT_ROOT, "temp")
HOWTOCOOK_DIR = os.path.join(TEMP_DIR, "HowToCook")


def main():
    os.makedirs(TEMP_DIR, exist_ok=True)
    if os.path.exists(os.path.join(HOWTOCOOK_DIR, "dishes")):
        print("[OK] temp/HowToCook 已存在，跳过克隆")
        return 0
    print("正在克隆 HowToCook 到 temp/HowToCook ...")
    r = subprocess.run(
        ["git", "clone", "--depth", "1", "https://github.com/Anduin2017/HowToCook.git", HOWTOCOOK_DIR],
        cwd=PROJECT_ROOT,
    )
    if r.returncode != 0:
        print("克隆失败，请确保已安装 git")
        return 1
    print("[OK] 克隆完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
