"""Routes that belong to no module: health, public configuration, the queue check."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from ailms.identity.api import CurrentUser, ErrorOut, Role, require_role
from ailms.platform import queue
from ailms.platform.settings import get_settings

router = APIRouter(tags=["system"])


class HealthOut(BaseModel):
    status: str
    version: str


class ConfigOut(BaseModel):
    demo_mode: bool
    signup_open: bool
    access_code_required: bool
    banner: str | None


class PingQueuedOut(BaseModel):
    token: uuid.UUID


class PingStatusOut(BaseModel):
    done: bool
    ran_at: datetime | None


@router.get("/health")
def health() -> HealthOut:
    return HealthOut(status="ok", version=get_settings().app_version)


@router.get("/config")
def config() -> ConfigOut:
    """What the sign-in page needs to know before anyone has signed in."""
    s = get_settings()
    return ConfigOut(
        demo_mode=s.demo_mode,
        signup_open=s.signup_is_open,
        access_code_required=s.access_code_required,
        banner=s.banner,
    )


_admin = require_role(Role.ADMIN)
_admin_errors = {401: {"model": ErrorOut}, 403: {"model": ErrorOut}}


@router.post("/admin/jobs/ping", status_code=202, responses=_admin_errors)
def queue_ping(user: CurrentUser = Depends(_admin)) -> PingQueuedOut:
    """Put a trivial job on the queue, to check that the worker is running."""
    return PingQueuedOut(token=queue.enqueue_ping())


@router.get("/admin/jobs/ping/{token}", responses=_admin_errors)
def ping_status(token: uuid.UUID, user: CurrentUser = Depends(_admin)) -> PingStatusOut:
    ran_at = queue.ping_ran_at(token)
    return PingStatusOut(done=ran_at is not None, ran_at=ran_at)
