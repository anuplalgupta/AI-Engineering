"""SVG images are cleaned before they are stored."""

import pytest

from ailms.platform.storage import InMemoryStorage, store_file
from ailms.platform.svg import UnsafeSvgError, clean_svg

BAD = b"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" onload="alert(1)">
  <script>alert(1)</script>
  <foreignObject><div xmlns="http://www.w3.org/1999/xhtml">hi</div></foreignObject>
  <a href="https://example.org"><rect width="5" height="5"/></a>
  <image href="https://example.org/x.png"/>
  <use xlink:href="https://example.org/s.svg#a"/>
  <use href="#ok"/>
  <rect id="ok" width="10" height="10" fill="url(https://example.org/p)" stroke="url(#g)" onclick="x()"/>
  <text x="1" y="2" style="background:url(javascript:alert(1))">A<tspan dy="4">x</tspan></text>
</svg>"""


def test_scripts_handlers_and_external_links_are_removed():
    cleaned = clean_svg(BAD).decode()
    for gone in ("script", "onload", "onclick", "foreignObject", "example.org", "javascript",
                 "<a ", "<image"):
        assert gone not in cleaned, gone
    assert 'href="#ok"' in cleaned
    assert 'stroke="url(#g)"' in cleaned
    assert "<tspan" in cleaned


def test_entities_and_doctype_are_refused():
    bomb = (
        b'<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY a "aaaa">]>'
        b'<svg xmlns="http://www.w3.org/2000/svg"><text>&a;</text></svg>'
    )
    with pytest.raises(UnsafeSvgError):
        clean_svg(bomb)


def test_not_svg_or_too_large_is_refused():
    with pytest.raises(UnsafeSvgError):
        clean_svg(b'<html xmlns="http://www.w3.org/1999/xhtml"/>')
    with pytest.raises(UnsafeSvgError):
        clean_svg(b'<svg xmlns="http://www.w3.org/2000/svg">' + b" " * 600_000 + b"</svg>")


def test_store_file_cleans_svg_only():
    store = InMemoryStorage()
    store_file(store, "a.svg", BAD, "image/svg+xml")
    assert b"script" not in store.get("a.svg").data
    store_file(store, "b.png", b"\x89PNG<script>", "image/png")
    assert store.get("b.png").data == b"\x89PNG<script>"
