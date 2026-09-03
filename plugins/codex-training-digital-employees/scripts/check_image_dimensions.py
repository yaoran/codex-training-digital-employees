#!/usr/bin/env python3
"""Verify that a local PNG has the exact dimensions requested by a design brief."""

from __future__ import annotations

import argparse
import os
import stat
import struct
import zlib
from pathlib import Path


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_PNG_BYTES = 50 * 1024 * 1024


def read_png_dimensions(path: Path) -> tuple[int, int]:
    mode = path.lstat().st_mode
    if stat.S_ISLNK(mode):
        raise ValueError("PNG 不允许是符号链接")
    if not stat.S_ISREG(mode):
        raise ValueError("PNG 必须是普通文件")
    if path.stat().st_size > MAX_PNG_BYTES:
        raise ValueError(f"PNG 超过 {MAX_PNG_BYTES} 字节限制")

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        file_stat = os.fstat(descriptor)
        if not stat.S_ISREG(file_stat.st_mode):
            raise ValueError("PNG 必须是普通文件")

        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            if handle.read(8) != PNG_SIGNATURE:
                raise ValueError("文件不是有效的 PNG")

            width = height = None
            has_idat = False
            has_iend = False
            first_chunk = True
            while not has_iend:
                chunk_header = handle.read(8)
                if len(chunk_header) != 8:
                    raise ValueError("PNG 数据被截断")
                length, chunk_type = struct.unpack(">I4s", chunk_header)
                if handle.tell() + length + 4 > file_stat.st_size:
                    raise ValueError("PNG 数据被截断")

                chunk_data = handle.read(length)
                chunk_crc = handle.read(4)
                if len(chunk_data) != length or len(chunk_crc) != 4:
                    raise ValueError("PNG 数据被截断")
                expected_crc = struct.unpack(">I", chunk_crc)[0]
                actual_crc = zlib.crc32(chunk_type + chunk_data) & 0xFFFFFFFF
                if actual_crc != expected_crc:
                    raise ValueError("PNG chunk CRC 校验失败")

                if first_chunk:
                    if chunk_type != b"IHDR" or length != 13:
                        raise ValueError("PNG 缺少有效的 IHDR")
                    width, height = struct.unpack(">II", chunk_data[:8])
                    first_chunk = False
                elif chunk_type == b"IHDR":
                    raise ValueError("PNG 包含重复的 IHDR")

                if chunk_type == b"IDAT":
                    has_idat = True
                elif chunk_type == b"IEND":
                    if length != 0 or handle.read(1):
                        raise ValueError("PNG 的 IEND 无效")
                    has_iend = True
    finally:
        os.close(descriptor)

    if not has_idat:
        raise ValueError("PNG 缺少 IDAT 图像数据")
    assert width is not None and height is not None
    if width == 0 or height == 0:
        raise ValueError("PNG 宽高必须大于 0")
    return width, height


def validate_png(path: Path, *, expected_width: int, expected_height: int) -> list[str]:
    if expected_width <= 0 or expected_height <= 0:
        return ["期望宽高必须是正整数"]

    try:
        width, height = read_png_dimensions(path)
    except (OSError, ValueError) as exc:
        return [str(exc)]

    if (width, height) != (expected_width, expected_height):
        return [
            f"PNG 实际尺寸为 {width}x{height}，期望尺寸为 "
            f"{expected_width}x{expected_height}"
        ]
    return []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="检查本地 PNG 的精确像素尺寸。")
    parser.add_argument("image", type=Path, help="待检查的 PNG 文件")
    parser.add_argument("--width", type=int, required=True, help="期望宽度（像素）")
    parser.add_argument("--height", type=int, required=True, help="期望高度（像素）")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    errors = validate_png(
        args.image,
        expected_width=args.width,
        expected_height=args.height,
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print(f"PNG dimension validation passed: {args.width}x{args.height}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
