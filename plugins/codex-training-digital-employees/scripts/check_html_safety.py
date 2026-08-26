#!/usr/bin/env python3
"""Reject active or network-capable content in a generated local HTML artifact."""

from __future__ import annotations

import os
import stat
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


MAX_HTML_BYTES = 5 * 1024 * 1024
BLOCKED_TAGS = {"base", "embed", "form", "iframe", "link", "math", "object", "script", "svg"}
URL_ATTRIBUTES = {
    "action",
    "archive",
    "background",
    "codebase",
    "data",
    "dynsrc",
    "formaction",
    "href",
    "lowsrc",
    "manifest",
    "ping",
    "poster",
    "src",
    "srcset",
    "xlink:href",
}
REQUIRED_CSP = {
    "default-src": ("'none'",),
    "style-src": ("'unsafe-inline'",),
    "img-src": ("data:",),
    "base-uri": ("'none'",),
    "form-action": ("'none'",),
}


class SafetyParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.errors: list[str] = []
        self.csps: list[str] = []
        self.in_head = False
        self.in_style = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in BLOCKED_TAGS:
            self.errors.append(f"禁止活动元素：<{tag}>")
        if tag == "head":
            self.in_head = True
        elif tag == "body":
            self.in_head = False
        if tag == "style":
            self.in_style = True

        normalized: dict[str, str] = {}
        for name, value in attrs:
            normalized_name = name.lower()
            if normalized_name in normalized:
                self.errors.append(f"禁止重复属性：{normalized_name}")
            normalized[normalized_name] = value or ""
        if tag == "meta":
            http_equiv = normalized.get("http-equiv", "").strip().lower()
            if http_equiv == "refresh":
                self.errors.append("禁止 meta refresh")
            if http_equiv == "content-security-policy":
                if not self.in_head:
                    self.errors.append("Content-Security-Policy 必须位于 <head>")
                self.csps.append(normalized.get("content", ""))

        for name, value in normalized.items():
            if name.startswith("on"):
                self.errors.append(f"禁止事件属性：{name}")
            if name == "style" and self._unsafe_css(value):
                self.errors.append("禁止 CSS 外部资源或 @import")
            if name in URL_ATTRIBUTES and value and not self._safe_url(tag, name, value):
                self.errors.append(f"禁止可导航或外部 URL：{name}={value!r}")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "head":
            self.in_head = False
        if tag == "style":
            self.in_style = False

    def handle_data(self, data: str) -> None:
        if self.in_style and self._unsafe_css(data):
            self.errors.append("禁止 CSS 外部资源或 @import")

    @staticmethod
    def _unsafe_css(value: str) -> bool:
        lowered = value.lower()
        return "@import" in lowered or "url(" in lowered

    @staticmethod
    def _safe_url(tag: str, name: str, value: str) -> bool:
        value = value.strip()
        if name == "href" and value.startswith("#"):
            return True
        if tag == "img" and name == "src" and value.lower().startswith(
            ("data:image/png;", "data:image/jpeg;", "data:image/gif;", "data:image/webp;", "data:image/avif;")
        ):
            return True
        return not value or (not urlsplit(value).scheme and not value.startswith("//") and value.startswith("#"))


def parse_csp(value: str) -> dict[str, tuple[str, ...]] | None:
    directives: dict[str, tuple[str, ...]] = {}
    for raw_directive in value.split(";"):
        tokens = raw_directive.strip().lower().split()
        if not tokens:
            continue
        name = tokens[0]
        if name in directives:
            return None
        directives[name] = tuple(tokens[1:])
    return directives


def read_html(path: Path) -> str:
    mode = path.lstat().st_mode
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise ValueError("HTML 必须是非符号链接的普通文件")
    if path.stat().st_size > MAX_HTML_BYTES:
        raise ValueError(f"HTML 超过 {MAX_HTML_BYTES} 字节限制")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            raw = handle.read(MAX_HTML_BYTES + 1)
        if len(raw) > MAX_HTML_BYTES:
            raise ValueError(f"HTML 超过 {MAX_HTML_BYTES} 字节限制")
        return raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("HTML 不是有效 UTF-8") from exc
    finally:
        os.close(descriptor)


def validate_html(path: Path) -> list[str]:
    try:
        text = read_html(path)
    except (OSError, ValueError) as exc:
        return [str(exc)]

    parser = SafetyParser()
    parser.feed(text)
    parser.close()
    errors = parser.errors
    if len(parser.csps) != 1:
        errors.append("必须且只能声明一个 Content-Security-Policy")
    else:
        directives = parse_csp(parser.csps[0])
        if directives is None:
            errors.append("CSP 包含重复指令")
        elif set(directives) != set(REQUIRED_CSP):
            errors.append("CSP 指令集合必须与离线安全策略完全一致")
        else:
            for name, expected in REQUIRED_CSP.items():
                if directives[name] != expected:
                    errors.append(f"CSP 指令不安全：{name}")
    return errors


def main() -> int:
    if len(sys.argv) != 2:
        print("用法：check_html_safety.py <html-file>", file=sys.stderr)
        return 2
    errors = validate_html(Path(sys.argv[1]))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("HTML safety validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
