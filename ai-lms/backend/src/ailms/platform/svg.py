"""Cleaning SVG images before they are stored (ADR 0007 item 5).

An SVG file is a picture description, but browsers will run scripts and follow
links inside it. Only a fixed list of drawing elements and attributes is kept;
scripts, event handlers, external links, foreign content and DTDs are removed
or refused.
"""

import re
import xml.etree.ElementTree as ET

from defusedxml import ElementTree as SafeET

SVG_NS = "http://www.w3.org/2000/svg"
XLINK_NS = "http://www.w3.org/1999/xlink"
MAX_BYTES = 512 * 1024

ET.register_namespace("", SVG_NS)
ET.register_namespace("xlink", XLINK_NS)

_ELEMENTS = {
    "svg", "g", "defs", "title", "desc", "marker", "symbol", "use",
    "path", "line", "polyline", "polygon", "rect", "circle", "ellipse",
    "text", "tspan", "linearGradient", "radialGradient", "stop", "clipPath", "mask", "pattern",
}

_ATTRIBUTES = {
    "id", "class", "viewBox", "width", "height", "x", "y", "x1", "y1", "x2", "y2",
    "cx", "cy", "r", "rx", "ry", "d", "points", "transform", "fill", "fill-opacity",
    "fill-rule", "stroke", "stroke-width", "stroke-opacity", "stroke-dasharray",
    "stroke-linecap", "stroke-linejoin", "opacity", "font-family", "font-size",
    "font-style", "font-weight", "text-anchor", "dominant-baseline", "dx", "dy",
    "role", "aria-label", "aria-labelledby", "aria-hidden", "preserveAspectRatio",
    "marker-start", "marker-mid", "marker-end", "markerWidth", "markerHeight",
    "markerUnits", "refX", "refY", "orient", "offset", "stop-color", "stop-opacity",
    "gradientUnits", "gradientTransform", "clip-path", "mask", "patternUnits",
    "letter-spacing", "style", "href", f"{{{XLINK_NS}}}href", "version",
}

# url(...) is allowed only when it points inside the same file: url(#id).
_EXTERNAL_URL = re.compile(r"url\(\s*['\"]?\s*(?!#)", re.IGNORECASE)
_BAD_VALUE = re.compile(r"javascript:|data:|@import|expression\(", re.IGNORECASE)


class UnsafeSvgError(ValueError):
    """The file is not an SVG image that can be cleaned."""


def _local(name: str) -> tuple[str | None, str]:
    if name.startswith("{"):
        ns, _, local = name[1:].partition("}")
        return ns, local
    return None, name


def _clean_element(element: ET.Element) -> None:
    for child in list(element):
        ns, local = _local(child.tag) if isinstance(child.tag, str) else (None, "")
        if ns != SVG_NS or local not in _ELEMENTS:
            element.remove(child)
            continue
        _clean_element(child)
    for name in list(element.attrib):
        value = element.attrib[name]
        ns, local = _local(name)
        keep = name in _ATTRIBUTES and not local.lower().startswith("on")
        if keep and local == "href" and not value.strip().startswith("#"):
            keep = False
        if keep and (_EXTERNAL_URL.search(value) or _BAD_VALUE.search(value)):
            keep = False
        if not keep:
            del element.attrib[name]


def clean_svg(data: bytes) -> bytes:
    """Return a cleaned copy of an SVG image, or raise UnsafeSvgError."""
    if len(data) > MAX_BYTES:
        raise UnsafeSvgError("the SVG image is larger than 512 KB")
    try:
        root = SafeET.fromstring(data)
    except Exception as error:  # noqa: BLE001 - any parse refusal means "not acceptable"
        raise UnsafeSvgError(f"the SVG image cannot be read safely: {error}") from error
    if root.tag != f"{{{SVG_NS}}}svg":
        raise UnsafeSvgError("the file is not an SVG image")
    _clean_element(root)
    return ET.tostring(root, encoding="utf-8", xml_declaration=False)
