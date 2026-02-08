#!/usr/bin/env python3
"""项目打包脚本。

将项目打包为 tarball，便于部署到其他服务器。

打包内容：
- app/ 目录（应用代码）
- scripts/ 目录（工具脚本）
- templates/ 目录（服务模板，如果存在）
- uv.lock（依赖锁定文件）
- .env.example（环境变量示例）
- README.md（使用文档）
- alembic/ 目录（数据库迁移）
- alembic.ini（Alembic 配置）

排除内容：
- tests/ 目录
- .git/ 目录
- __pycache__/ 目录
- *.pyc 文件
- .env 文件（包含敏感信息）
- web/ 目录（前端代码，单独部署）
- openspec/ 目录（开发工作流）
- dist/ 目录（打包输出）
"""

import os
import subprocess
import sys
import tarfile
from datetime import datetime
from pathlib import Path


def get_version() -> str:
    """获取版本号。

    优先使用 git tag，如果没有 tag 则使用 commit hash。

    Returns:
        str: 版本号（例如：v1.0.0 或 abc1234）
    """
    try:
        # 尝试获取最新的 git tag
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode == 0 and result.stdout.strip():
            version = result.stdout.strip()
            print(f"✓ 使用 git tag 版本号：{version}")
            return version

    except Exception as e:
        print(f"⚠️  获取 git tag 失败：{e}")

    # 回退到 commit hash
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )

        commit_hash = result.stdout.strip()
        print(f"✓ 使用 commit hash 版本号：{commit_hash}")
        return commit_hash

    except Exception as e:
        print(f"✗ 获取 commit hash 失败：{e}")
        # 使用时间戳作为最后的回退
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        print(f"⚠️  使用时间戳版本号：{timestamp}")
        return timestamp


def collect_files(base_dir: Path) -> list[Path]:
    """收集需要打包的文件。

    Args:
        base_dir: 项目根目录

    Returns:
        list[Path]: 需要打包的文件列表
    """
    print("\n收集文件...")

    # 需要包含的目录和文件
    include_patterns = [
        "app/**/*.py",
        "scripts/**/*.py",
        "templates/**/*",
        "alembic/**/*.py",
        "alembic/**/*.mako",
        "uv.lock",
        ".env.example",
        "README.md",
        "alembic.ini",
        "pyproject.toml",
    ]

    # 需要排除的模式
    exclude_patterns = [
        "**/__pycache__",
        "**/*.pyc",
        "**/*.pyo",
        "**/.DS_Store",
        "**/tests",
        "**/.git",
        "**/.env",
        "**/web",
        "**/openspec",
        "**/dist",
        "**/.venv",
        "**/.pytest_cache",
    ]

    files = []

    # 收集文件
    for pattern in include_patterns:
        for file_path in base_dir.glob(pattern):
            # 检查是否应该排除
            should_exclude = False
            for exclude_pattern in exclude_patterns:
                if file_path.match(exclude_pattern):
                    should_exclude = True
                    break

            if not should_exclude and file_path.is_file():
                files.append(file_path)

    print(f"✓ 收集到 {len(files)} 个文件")
    return files


def validate_package_content(files: list[Path], base_dir: Path) -> bool:
    """验证包内容是否完整。

    Args:
        files: 文件列表
        base_dir: 项目根目录

    Returns:
        bool: 是否验证通过
    """
    print("\n验证包内容...")

    # 必需文件
    required_files = [
        "app/main.py",
        "uv.lock",
        ".env.example",
        "README.md",
    ]

    file_paths = {str(f.relative_to(base_dir)) for f in files}

    missing_files = []
    for required_file in required_files:
        if required_file not in file_paths:
            missing_files.append(required_file)

    if missing_files:
        print("✗ 缺少必需文件：")
        for missing_file in missing_files:
            print(f"  - {missing_file}")
        return False

    print("✓ 包内容验证通过")
    return True


def create_tarball(
    files: list[Path],
    base_dir: Path,
    output_dir: Path,
    version: str,
) -> Path:
    """创建 tarball 压缩包。

    Args:
        files: 文件列表
        base_dir: 项目根目录
        output_dir: 输出目录
        version: 版本号

    Returns:
        Path: 生成的 tarball 文件路径
    """
    print("\n创建 tarball...")

    # 创建输出目录
    output_dir.mkdir(parents=True, exist_ok=True)

    # 生成文件名
    tarball_name = f"stock-selector-{version}.tar.gz"
    tarball_path = output_dir / tarball_name

    # 创建 tarball
    with tarfile.open(tarball_path, "w:gz") as tar:
        for file_path in files:
            # 计算相对路径
            arcname = f"stock-selector/{file_path.relative_to(base_dir)}"
            tar.add(file_path, arcname=arcname)
            print(f"  添加：{file_path.relative_to(base_dir)}")

    print(f"\n✓ tarball 创建完成：{tarball_path}")
    return tarball_path


def get_file_size(file_path: Path) -> str:
    """获取文件大小（人类可读格式）。

    Args:
        file_path: 文件路径

    Returns:
        str: 文件大小（例如：1.5 MB）
    """
    size_bytes = file_path.stat().st_size

    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0

    return f"{size_bytes:.1f} TB"


def main():
    """主函数。"""
    print("\n" + "=" * 60)
    print("A 股智能选股系统 - 项目打包")
    print("=" * 60)

    # 1. 获取项目根目录
    base_dir = Path(__file__).resolve().parent.parent
    print(f"\n项目根目录：{base_dir}")

    # 2. 获取版本号
    version = get_version()

    # 3. 收集文件
    files = collect_files(base_dir)

    if not files:
        print("\n✗ 未找到任何文件，打包失败")
        return 1

    # 4. 验证包内容
    if not validate_package_content(files, base_dir):
        print("\n✗ 包内容验证失败，打包终止")
        return 1

    # 5. 创建 tarball
    output_dir = base_dir / "dist"
    tarball_path = create_tarball(files, base_dir, output_dir, version)

    # 6. 显示打包信息
    print("\n" + "=" * 60)
    print("打包完成")
    print("=" * 60)
    print(f"版本号：{version}")
    print(f"文件数量：{len(files)}")
    print(f"包大小：{get_file_size(tarball_path)}")
    print(f"输出路径：{tarball_path}")
    print()
    print("部署步骤：")
    print(f"  1. 传输到目标服务器：scp {tarball_path} user@server:/path/")
    print(f"  2. 解压：tar -xzf {tarball_path.name}")
    print("  3. 进入目录：cd stock-selector")
    print("  4. 安装依赖：uv sync")
    print("  5. 配置环境：cp .env.example .env && vim .env")
    print("  6. 初始化数据库：uv run alembic upgrade head")
    print("  7. 初始化数据：uv run python -m scripts.init_data")
    print("  8. 启动服务：uv run uvicorn app.main:app")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
