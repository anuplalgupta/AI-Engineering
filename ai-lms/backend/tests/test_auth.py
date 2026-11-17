"""Sign-in by email one-time code, sessions, cookies and demo mode."""

import re
from datetime import timedelta

from sqlalchemy import select

from ailms.identity.api import SESSION_COOKIE
from ailms.identity.models import LoginCode, User
from ailms.platform.db import scope_to_organisation, session_scope
from conftest import demo_login, run_jobs


def _code_from(mailer, email: str) -> str:
    to, subject, text = [m for m in mailer.sent if m[0] == email][-1]
    return re.search(r"\b(\d{6})\b", text).group(1)


def test_request_code_sends_six_digits_and_stores_only_a_hash(client, orgs, mailer):
    response = client.post("/api/auth/request-code", json={"email": "Student@Demo.example "})
    assert response.status_code == 204
    run_jobs()
    code = _code_from(mailer, "student@demo.example")
    assert len(code) == 6
    with session_scope() as session:
        scope_to_organisation(session, orgs.a)
        row = session.scalars(select(LoginCode)).one()
        assert code not in row.code_hash and len(row.code_hash) == 64


def test_verify_code_signs_in_and_sets_cookie(client, orgs, mailer):
    client.post("/api/auth/request-code", json={"email": "student@demo.example"})
    run_jobs()
    code = _code_from(mailer, "student@demo.example")
    response = client.post("/api/auth/verify-code", json={"email": "student@demo.example", "code": code})
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "student"
    cookie = response.headers["set-cookie"]
    assert f"{SESSION_COOKIE}=" in cookie
    assert "HttpOnly" in cookie and "SameSite=lax" in cookie and "Secure" not in cookie
    me = client.get("/api/me")
    assert me.status_code == 200
    assert me.json()["organisation"]["name"] == "Sample Institute"


def test_code_works_once(client, orgs, mailer):
    client.post("/api/auth/request-code", json={"email": "student@demo.example"})
    run_jobs()
    code = _code_from(mailer, "student@demo.example")
    body = {"email": "student@demo.example", "code": code}
    assert client.post("/api/auth/verify-code", json=body).status_code == 200
    assert client.post("/api/auth/verify-code", json=body).status_code == 400


def test_wrong_code_is_400_and_attempts_are_limited(client, orgs, mailer, settings):
    client.post("/api/auth/request-code", json={"email": "student@demo.example"})
    run_jobs()
    code = _code_from(mailer, "student@demo.example")
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(settings.login_code_max_attempts):
        response = client.post("/api/auth/verify-code", json={"email": "student@demo.example", "code": wrong})
        assert response.status_code == 400
        assert response.json() == {"detail": "That code is wrong or has expired. Ask for a new one."}
    # Even the right code is refused once the attempts are used up.
    response = client.post("/api/auth/verify-code", json={"email": "student@demo.example", "code": code})
    assert response.status_code == 400


def test_code_expires_after_ten_minutes(client, orgs, mailer, clock):
    client.post("/api/auth/request-code", json={"email": "student@demo.example"})
    run_jobs()
    code = _code_from(mailer, "student@demo.example")
    clock.advance(timedelta(minutes=10, seconds=1))
    response = client.post("/api/auth/verify-code", json={"email": "student@demo.example", "code": code})
    assert response.status_code == 400


def test_requests_per_email_are_rate_limited(client, orgs, mailer, settings, clock):
    for _ in range(settings.login_code_max_requests + 2):
        assert client.post("/api/auth/request-code", json={"email": "student@demo.example"}).status_code == 204
    run_jobs()
    assert len(mailer.sent) == settings.login_code_max_requests
    clock.advance(minutes=settings.login_code_minutes + 1)
    client.post("/api/auth/request-code", json={"email": "student@demo.example"})
    run_jobs()
    assert len(mailer.sent) == settings.login_code_max_requests + 1


def test_unknown_email_gets_same_answer_when_signup_closed(client, orgs, mailer, monkeypatch, settings):
    monkeypatch.setattr(settings, "signup_open", False)
    response = client.post("/api/auth/request-code", json={"email": "nobody@example.org"})
    assert response.status_code == 204
    run_jobs()
    assert mailer.sent == []


def test_signup_creates_student_when_open(client, orgs, mailer):
    client.post("/api/auth/request-code", json={"email": "new.person@example.org"})
    run_jobs()
    code = _code_from(mailer, "new.person@example.org")
    response = client.post("/api/auth/verify-code", json={"email": "new.person@example.org", "code": code})
    assert response.status_code == 200
    assert response.json()["user"]["role"] == "student"
    with session_scope() as session:
        scope_to_organisation(session, orgs.a)
        assert session.scalar(select(User).where(User.email == "new.person@example.org")) is not None


def test_bad_email_is_422(client, orgs):
    response = client.post("/api/auth/request-code", json={"email": "not-an-email"})
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)


def test_logout_ends_session(client, orgs):
    demo_login(client, "student")
    assert client.get("/api/me").status_code == 200
    assert client.post("/api/auth/logout").status_code == 204
    client.cookies.clear()
    assert client.get("/api/me").status_code == 401


def test_logged_out_token_no_longer_works(client, orgs):
    demo_login(client, "student")
    token = client.cookies.get(SESSION_COOKIE)
    client.post("/api/auth/logout")
    client.cookies.set(SESSION_COOKIE, token)
    assert client.get("/api/me").status_code == 401


def test_session_expires(client, orgs, clock, settings):
    demo_login(client, "student")
    clock.advance(days=settings.session_days, seconds=1)
    assert client.get("/api/me").status_code == 401


def test_me_without_session_is_401(client, orgs):
    response = client.get("/api/me")
    assert response.status_code == 401
    assert response.json() == {"detail": "Please sign in."}


# --- demo mode (ADR 0008 section G) -----------------------------------------


def test_demo_login_for_each_role(client, orgs):
    for role in ("admin", "reviewer", "student"):
        user = demo_login(client, role)
        assert user["role"] == role
        assert user["organisation"]["id"] == str(orgs.a)
        assert client.get("/api/me").json()["role"] == role


def test_demo_login_is_404_when_demo_mode_off(client, orgs, monkeypatch, settings):
    monkeypatch.setattr(settings, "demo_mode", False)
    response = client.post("/api/auth/demo-login", json={"role": "admin"})
    assert response.status_code == 404
    config = client.get("/api/config").json()
    assert config["demo_mode"] is False and config["signup_open"] is False


def test_public_demo_needs_access_code(client, orgs, monkeypatch, settings):
    monkeypatch.setattr(settings, "public_demo", True)
    monkeypatch.setattr(settings, "demo_access_code", "letmein-123")
    assert client.post("/api/auth/demo-login", json={"role": "student"}).status_code == 403
    wrong = client.post("/api/auth/demo-login", json={"role": "student", "access_code": "nope"})
    assert wrong.status_code == 403
    right = client.post("/api/auth/demo-login", json={"role": "student", "access_code": "letmein-123"})
    assert right.status_code == 200
    config = client.get("/api/config").json()
    assert config == {
        "demo_mode": True,
        "signup_open": False,
        "access_code_required": True,
        "banner": "This is a demonstration site. It holds sample data only.",
    }


def test_public_demo_forces_signup_closed(client, orgs, mailer, monkeypatch, settings):
    monkeypatch.setattr(settings, "public_demo", True)
    monkeypatch.setattr(settings, "demo_access_code", "x" * 12)
    client.post("/api/auth/request-code", json={"email": "new.person@example.org"})
    run_jobs()
    assert mailer.sent == []


def test_settings_refuse_public_demo_without_access_code(monkeypatch):
    import pytest

    from ailms.platform.settings import Settings

    with pytest.raises(ValueError):
        Settings(public_demo=True, demo_mode=True, demo_access_code="")


# --- cookies behind the web server --------------------------------------------


def test_cookie_secure_when_trusted_proxy_says_https(client, orgs):
    response = client.post(
        "/api/auth/demo-login", json={"role": "student"}, headers={"X-Forwarded-Proto": "https"}
    )
    assert response.status_code == 200
    assert "Secure" in response.headers["set-cookie"]


def test_forwarded_proto_ignored_from_untrusted_peer(app, orgs):
    from fastapi.testclient import TestClient

    with TestClient(app, client=("172.30.0.99", 40000)) as other:
        response = other.post(
            "/api/auth/demo-login", json={"role": "student"}, headers={"X-Forwarded-Proto": "https"}
        )
    assert response.status_code == 200
    assert "Secure" not in response.headers["set-cookie"]


# --- slow guessing, flooding and account discovery -----------------------------------


def _fail_codes(client, email: str, times: int) -> None:
    for _ in range(times):
        response = client.post("/api/auth/verify-code", json={"email": email, "code": "abcdef"})
        assert response.status_code == 400


def test_wrong_codes_lock_the_address_for_a_day(client, orgs, mailer, settings, clock, monkeypatch):
    monkeypatch.setattr(settings, "client_max_code_checks_per_hour", 1000)
    email = "student@demo.example"
    # Spread the guesses over several codes and windows, as a patient attacker would.
    failures = 0
    while failures < settings.login_max_failures_per_day:
        client.post("/api/auth/request-code", json={"email": email})
        run_jobs()
        batch = min(settings.login_code_max_attempts, settings.login_max_failures_per_day - failures)
        _fail_codes(client, email, batch)
        failures += batch
        clock.advance(minutes=settings.login_code_minutes + 1)
    # Locked: no new code is sent, and even a right code is refused.
    sent_before = len(mailer.sent)
    client.post("/api/auth/request-code", json={"email": email})
    run_jobs()
    assert len(mailer.sent) == sent_before
    from ailms.platform import security

    with session_scope() as session:
        scope_to_organisation(session, orgs.a)
        session.add(LoginCode(email=email, code_hash=security.hash_login_code(email, "123456"),
                              created_at=clock.now(), expires_at=clock.now() + timedelta(minutes=10)))
    response = client.post("/api/auth/verify-code", json={"email": email, "code": "123456"})
    assert response.status_code == 400
    # A day later the address works again.
    clock.advance(hours=settings.login_lockout_hours)
    client.post("/api/auth/request-code", json={"email": email})
    run_jobs()
    code = _code_from(mailer, email)
    response = client.post("/api/auth/verify-code", json={"email": email, "code": code})
    assert response.status_code == 200


def test_codes_per_address_are_capped_per_day(client, orgs, mailer, settings, clock):
    for _ in range(settings.login_max_codes_per_day + 3):
        client.post("/api/auth/request-code", json={"email": "student@demo.example"})
        run_jobs()
        clock.advance(minutes=settings.login_code_minutes + 1)
    assert len(mailer.sent) == settings.login_max_codes_per_day


def test_requests_per_client_address_are_limited(client, orgs, mailer, settings, monkeypatch):
    monkeypatch.setattr(settings, "client_max_code_requests_per_hour", 3)
    monkeypatch.setattr(settings, "client_max_code_checks_per_hour", 2)
    for n in range(3):
        email = f"person{n}@example.org"
        assert client.post("/api/auth/request-code", json={"email": email}).status_code == 204
    response = client.post("/api/auth/request-code", json={"email": "one.more@example.org"})
    assert response.status_code == 429
    assert response.json() == {
        "detail": "Too many requests from this address. Please wait a while and try again."
    }
    body = {"email": "student@demo.example", "code": "000000"}
    assert client.post("/api/auth/verify-code", json=body).status_code == 400
    assert client.post("/api/auth/verify-code", json=body).status_code == 400
    assert client.post("/api/auth/verify-code", json=body).status_code == 429


def test_client_address_comes_from_the_trusted_web_server_only(app, orgs, settings, monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.setattr(settings, "client_max_code_requests_per_hour", 1)
    with TestClient(app) as proxied:
        # Behind the web server, each browser address has its own count.
        for address in ("198.51.100.1", "198.51.100.2"):
            response = proxied.post(
                "/api/auth/request-code", json={"email": "a@example.org"},
                headers={"X-Real-IP": address},
            )
            assert response.status_code == 204
    with TestClient(app, client=("172.30.0.99", 40000)) as direct:
        # Any other peer cannot choose its address with the header.
        statuses = [
            direct.post(
                "/api/auth/request-code", json={"email": "a@example.org"},
                headers={"X-Real-IP": f"203.0.113.{n}"},
            ).status_code
            for n in range(2)
        ]
    assert statuses == [204, 429]


def _queued_sign_in_jobs() -> list[dict]:
    from ailms.platform.db import get_admin_engine

    with get_admin_engine().connect() as conn:
        rows = conn.exec_driver_sql(
            "SELECT args FROM procrastinate_jobs WHERE task_name = 'identity.send_sign_in_code' "
            "AND status = 'todo' ORDER BY id"
        ).all()
    return [row[0] for row in rows]


def test_request_code_does_the_same_work_for_known_and_unknown_addresses(
    client, orgs, mailer, monkeypatch, settings
):
    # Sign-up closed: the setting where an unknown address must not be told apart.
    monkeypatch.setattr(settings, "signup_open", False)
    for email in ("student@demo.example", "nobody@example.org"):
        assert client.post("/api/auth/request-code", json={"email": email}).status_code == 204
    # Nothing is sent inside the request; both requests put one identical-looking job
    # on the queue, and the worker decides.
    assert mailer.sent == []
    jobs = _queued_sign_in_jobs()
    assert [sorted(job) for job in jobs] == [["email", "organisation_id"]] * 2
    assert {job["email"] for job in jobs} == {"student@demo.example", "nobody@example.org"}
    run_jobs()
    assert [m[0] for m in mailer.sent] == ["student@demo.example"]
