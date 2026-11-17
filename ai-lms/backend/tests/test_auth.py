"""Sign-in by email one-time code, sessions, cookies and demo mode."""

import re
from datetime import timedelta

from sqlalchemy import select

from ailms.identity.api import SESSION_COOKIE, LoginCode, User
from ailms.platform.db import scope_to_organisation, session_scope
from conftest import demo_login


def _code_from(mailer, email: str) -> str:
    to, subject, text = [m for m in mailer.sent if m[0] == email][-1]
    return re.search(r"\b(\d{6})\b", text).group(1)


def test_request_code_sends_six_digits_and_stores_only_a_hash(client, orgs, mailer):
    response = client.post("/api/auth/request-code", json={"email": "Student@Demo.example "})
    assert response.status_code == 204
    code = _code_from(mailer, "student@demo.example")
    assert len(code) == 6
    with session_scope() as session:
        scope_to_organisation(session, orgs.a)
        row = session.scalars(select(LoginCode)).one()
        assert code not in row.code_hash and len(row.code_hash) == 64


def test_verify_code_signs_in_and_sets_cookie(client, orgs, mailer):
    client.post("/api/auth/request-code", json={"email": "student@demo.example"})
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
    code = _code_from(mailer, "student@demo.example")
    body = {"email": "student@demo.example", "code": code}
    assert client.post("/api/auth/verify-code", json=body).status_code == 200
    assert client.post("/api/auth/verify-code", json=body).status_code == 400


def test_wrong_code_is_400_and_attempts_are_limited(client, orgs, mailer, settings):
    client.post("/api/auth/request-code", json={"email": "student@demo.example"})
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
    code = _code_from(mailer, "student@demo.example")
    clock.advance(timedelta(minutes=10, seconds=1))
    response = client.post("/api/auth/verify-code", json={"email": "student@demo.example", "code": code})
    assert response.status_code == 400


def test_requests_per_email_are_rate_limited(client, orgs, mailer, settings, clock):
    for _ in range(settings.login_code_max_requests + 2):
        assert client.post("/api/auth/request-code", json={"email": "student@demo.example"}).status_code == 204
    assert len(mailer.sent) == settings.login_code_max_requests
    clock.advance(minutes=settings.login_code_minutes + 1)
    client.post("/api/auth/request-code", json={"email": "student@demo.example"})
    assert len(mailer.sent) == settings.login_code_max_requests + 1


def test_unknown_email_gets_same_answer_when_signup_closed(client, orgs, mailer, monkeypatch, settings):
    monkeypatch.setattr(settings, "signup_open", False)
    response = client.post("/api/auth/request-code", json={"email": "nobody@example.org"})
    assert response.status_code == 204
    assert mailer.sent == []


def test_signup_creates_student_when_open(client, orgs, mailer):
    client.post("/api/auth/request-code", json={"email": "new.person@example.org"})
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
