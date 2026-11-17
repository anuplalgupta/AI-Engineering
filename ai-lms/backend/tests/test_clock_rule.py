"""One clock (ADR 0006 item 25): only platform/clock.py may ask the system for the time."""

import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from ailms.platform import clock

SOURCE = Path(__file__).resolve().parents[1] / "src" / "ailms"
ALLOWED = SOURCE / "platform" / "clock.py"

FORBIDDEN = re.compile(
    r"\bdatetime\s*\.\s*(?:now|utcnow|today)\b"
    r"|\bdate\s*\.\s*today\b"
    r"|\btime\s*\.\s*(?:time|time_ns|monotonic)\b"
    r"|\butcnow\s*\("
    r"|\bfrom\s+time\s+import\b[^\n]*\btime\b"
)


def test_no_other_file_reads_the_system_clock():
    offenders = []
    for path in sorted(SOURCE.rglob("*.py")):
        if path == ALLOWED:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            code = line.split("#", 1)[0]
            if FORBIDDEN.search(code):
                offenders.append(f"{path.relative_to(SOURCE)}:{number}: {line.strip()}")
    assert offenders == [], "use ailms.platform.clock instead:\n" + "\n".join(offenders)


def test_the_rule_catches_examples():
    for bad in ("x = datetime.now(UTC)", "datetime.utcnow()", "date.today()", "t = time.time()",
                "from time import time", "datetime.today()"):
        assert FORBIDDEN.search(bad), bad
    for fine in ("clock.now()", "time.sleep(1)", "created_at = now", "from time import sleep"):
        assert not FORBIDDEN.search(fine), fine


def test_the_allowed_file_really_reads_the_clock():
    assert "datetime.now(" in ALLOWED.read_text(encoding="utf-8")


def test_fixed_clock_moves_only_when_told():
    fixed = clock.FixedClock(datetime(2026, 1, 1, tzinfo=UTC))
    assert fixed.now() == fixed.now()
    fixed.advance(days=2)
    assert fixed.now() == datetime(2026, 1, 3, tzinfo=UTC)
    fixed.advance(timedelta(hours=1))
    assert fixed.now().hour == 1
    with pytest.raises(ValueError):
        clock.FixedClock(datetime(2026, 1, 1))


def test_system_clock_is_aware_utc():
    assert clock.SystemClock().now().tzinfo is UTC
