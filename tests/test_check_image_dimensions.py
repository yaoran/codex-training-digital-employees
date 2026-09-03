from __future__ import annotations

import importlib.util
import struct
import tempfile
import unittest
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "codex-training-digital-employees"
CHECKER_PATH = PLUGIN / "scripts" / "check_image_dimensions.py"
SPEC = importlib.util.spec_from_file_location("check_image_dimensions", CHECKER_PATH)
assert SPEC and SPEC.loader
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


def png_chunk(kind: bytes, data: bytes) -> bytes:
    checksum = zlib.crc32(kind + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", checksum)


def make_png(width: int, height: int) -> bytes:
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    scanline = b"\x00" + b"\x00\x00\x00" * width
    return (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", ihdr)
        + png_chunk(b"IDAT", zlib.compress(scanline * height))
        + png_chunk(b"IEND", b"")
    )


class ImageDimensionTests(unittest.TestCase):
    def test_matching_png_dimensions_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "visual.png"
            image.write_bytes(make_png(64, 32))
            self.assertEqual(checker.validate_png(image, expected_width=64, expected_height=32), [])

    def test_mismatched_dimensions_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "visual.png"
            image.write_bytes(make_png(64, 32))
            errors = checker.validate_png(image, expected_width=32, expected_height=64)
            self.assertTrue(any("实际尺寸为 64x32" in error for error in errors), errors)
            self.assertTrue(any("期望尺寸为 32x64" in error for error in errors), errors)

    def test_non_png_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "visual.png"
            image.write_bytes(b"not a png")
            self.assertTrue(checker.validate_png(image, expected_width=64, expected_height=32))

    def test_truncated_png_header_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "visual.png"
            image.write_bytes(
                checker.PNG_SIGNATURE
                + b"\x00\x00\x00\rIHDR"
                + struct.pack(">II", 64, 32)
            )
            self.assertTrue(checker.validate_png(image, expected_width=64, expected_height=32))

    def test_corrupt_png_chunk_crc_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "visual.png"
            contents = bytearray(make_png(64, 32))
            contents[32] ^= 0x01
            image.write_bytes(contents)
            self.assertTrue(checker.validate_png(image, expected_width=64, expected_height=32))

    def test_png_without_iend_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "visual.png"
            image.write_bytes(make_png(64, 32)[:-12])
            self.assertTrue(checker.validate_png(image, expected_width=64, expected_height=32))

    def test_symlink_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.png"
            target.write_bytes(make_png(64, 32))
            link = root / "visual.png"
            link.symlink_to(target)
            errors = checker.validate_png(link, expected_width=64, expected_height=32)
            self.assertTrue(any("符号链接" in error for error in errors), errors)

    def test_non_positive_expected_dimensions_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            image = Path(directory) / "visual.png"
            image.write_bytes(make_png(64, 32))
            errors = checker.validate_png(image, expected_width=0, expected_height=-1)
            self.assertTrue(any("正整数" in error for error in errors), errors)


if __name__ == "__main__":
    unittest.main()
