#!/usr/bin/env python3
"""Validate the public marketplace, plugin manifest, and Skill frontmatter."""

from __future__ import annotations

import json
import os
import re
import stat
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MARKETPLACE_PATH = ROOT / ".agents" / "plugins" / "marketplace.json"
MAX_JSON_BYTES = 256 * 1024
MAX_SKILL_BYTES = 1024 * 1024


def safe_repo_path(path: Path, *, root: Path = ROOT, kind: str) -> Path:
    """Return a repository-contained path after rejecting links and special nodes."""
    lexical_root = Path(os.path.abspath(root))
    resolved_root = root.resolve()
    absolute = Path(os.path.abspath(path))
    try:
        relative = absolute.relative_to(lexical_root)
    except ValueError as exc:
        raise ValueError(f"路径超出仓库范围：{path}") from exc

    current = resolved_root
    for part in relative.parts:
        current /= part
        try:
            mode = current.lstat().st_mode
        except OSError as exc:
            raise ValueError(f"无法检查路径：{current}: {exc}") from exc
        if stat.S_ISLNK(mode):
            raise ValueError(f"不允许符号链接：{current}")

    mode = current.lstat().st_mode
    if kind == "file" and not stat.S_ISREG(mode):
        raise ValueError(f"必须是普通文件：{current}")
    if kind == "directory" and not stat.S_ISDIR(mode):
        raise ValueError(f"必须是目录：{current}")
    return current


def read_bounded_text(path: Path, *, max_bytes: int, root: Path = ROOT) -> str:
    safe_path = safe_repo_path(path, root=root, kind="file")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(safe_path, flags)
    except OSError as exc:
        raise ValueError(f"无法安全打开文件：{safe_path}: {exc}") from exc

    try:
        file_stat = os.fstat(descriptor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise ValueError(f"必须是普通文件：{safe_path}")
        if file_stat.st_size > max_bytes:
            raise ValueError(f"文件超过 {max_bytes} 字节限制：{safe_path}")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            raw = handle.read(max_bytes + 1)
        if len(raw) > max_bytes:
            raise ValueError(f"文件超过 {max_bytes} 字节限制：{safe_path}")
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"文件不是有效 UTF-8：{safe_path}") from exc
    finally:
        os.close(descriptor)


def load_json(path: Path, *, root: Path = ROOT) -> dict:
    try:
        return json.loads(read_bounded_text(path, max_bytes=MAX_JSON_BYTES, root=root))
    except json.JSONDecodeError as exc:
        raise ValueError(f"无法读取有效 JSON：{path}: {exc}") from exc


def read_frontmatter(path: Path, *, root: Path = ROOT) -> dict[str, str]:
    text = read_bounded_text(path, max_bytes=MAX_SKILL_BYTES, root=root)
    if not text.startswith("---\n"):
        raise ValueError(f"缺少 YAML frontmatter：{path}")

    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError(f"frontmatter 未闭合：{path}")

    values: dict[str, str] = {}
    for line in text[4:end].splitlines():
        match = re.match(r"^(name|description):\s*(.+?)\s*$", line)
        if match:
            values[match.group(1)] = match.group(2).strip('"\'')
    return values


def validate() -> list[str]:
    errors: list[str] = []
    try:
        marketplace = load_json(MARKETPLACE_PATH)
    except ValueError as exc:
        return [str(exc)]

    plugins = marketplace.get("plugins")
    if not isinstance(plugins, list) or not plugins:
        return ["Marketplace 未声明任何 Plugin"]

    for entry in plugins:
        name = entry.get("name")
        source_path = entry.get("source", {}).get("path")
        if not name or not isinstance(source_path, str) or not source_path:
            errors.append("Marketplace 条目缺少 name 或 source.path")
            continue

        source = Path(source_path)
        if source.is_absolute() or ".." in source.parts:
            errors.append(f"Marketplace source.path 必须是仓库内相对路径：{source_path}")
            continue

        try:
            plugin_dir = safe_repo_path(ROOT / source, kind="directory")
        except ValueError as exc:
            errors.append(str(exc))
            continue
        manifest_path = plugin_dir / ".codex-plugin" / "plugin.json"
        try:
            manifest = load_json(manifest_path)
        except ValueError as exc:
            errors.append(str(exc))
            continue

        if plugin_dir.name != name or manifest.get("name") != name:
            errors.append(f"Plugin 名称不一致：{name}")

        try:
            skills_dir = safe_repo_path(plugin_dir / "skills", kind="directory")
            skill_dirs: list[Path] = []
            for path in skills_dir.iterdir():
                mode = path.lstat().st_mode
                if stat.S_ISLNK(mode):
                    errors.append(f"Skill 目录不允许符号链接：{path}")
                elif stat.S_ISDIR(mode):
                    skill_dirs.append(path)
            skill_dirs.sort()
        except (OSError, ValueError) as exc:
            errors.append(str(exc))
            continue
        if not skill_dirs:
            errors.append(f"Plugin 没有 Skill：{name}")
            continue

        for skill_dir in skill_dirs:
            skill_file = skill_dir / "SKILL.md"
            try:
                frontmatter = read_frontmatter(skill_file)
            except ValueError as exc:
                errors.append(str(exc))
                continue
            if frontmatter.get("name") != skill_dir.name:
                errors.append(f"Skill 名称与目录不一致：{skill_dir}")
            if not frontmatter.get("description"):
                errors.append(f"Skill 缺少 description：{skill_dir}")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Repository validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
