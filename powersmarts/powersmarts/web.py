from __future__ import annotations

from pathlib import Path
from typing import Any

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from powersmarts.engine import PollingEngine
from powersmarts.home_assistant import HomeAssistantClient, HomeAssistantError
from powersmarts.models import DeviceAutomation, EntityRef
from powersmarts.storage import ConfigError, ConfigStore, automation_from_dict

PACKAGE_DIR = Path(__file__).resolve().parent
INGRESS_PROXY_IP = "172.30.32.2"


class IngressRootPathMiddleware:
    """Honor Home Assistant Ingress subpaths and restrict the listener."""

    def __init__(self, app: ASGIApp, *, ingress_only: bool) -> None:
        self.app = app
        self._ingress_only = ingress_only

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in {"http", "websocket"}:
            headers = {key.decode("latin-1"): value.decode("latin-1") for key, value in scope.get("headers", [])}
            ingress_path = headers.get("x-ingress-path")
            if ingress_path:
                scope = dict(scope)
                scope["root_path"] = ingress_path.rstrip("/")
            if self._ingress_only:
                client = scope.get("client")
                client_ip = client[0] if client else ""
                if client_ip not in {INGRESS_PROXY_IP, "127.0.0.1", "::1"}:
                    response = Response("Forbidden", status_code=403, media_type="text/plain")
                    await response(scope, receive, send)
                    return
        await self.app(scope, receive, send)


class NoCacheMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response


def create_web_app(
    store: ConfigStore,
    engine: PollingEngine,
    home_assistant: HomeAssistantClient,
    *,
    ingress_only: bool = False,
    lifespan: Callable[[FastAPI], AbstractAsyncContextManager[None]] | None = None,
) -> FastAPI:
    app = FastAPI(title="Powersmarts", docs_url=None, redoc_url=None, lifespan=lifespan)
    app.add_middleware(NoCacheMiddleware)
    app.add_middleware(IngressRootPathMiddleware, ingress_only=ingress_only)
    app.mount("/static", StaticFiles(directory=PACKAGE_DIR / "static"), name="static")
    templates = Jinja2Templates(directory=str(PACKAGE_DIR / "templates"))
    templates.env.globals["app_url"] = _app_url

    app.state.store = store
    app.state.engine = engine
    app.state.home_assistant = home_assistant
    app.state.templates = templates

    @app.get("/", response_class=HTMLResponse)
    async def index(request: Request) -> HTMLResponse:
        config = store.load()
        return templates.TemplateResponse(
            request,
            "index.html",
            {"automations": config.automations},
        )

    @app.get("/automations/new", response_class=HTMLResponse)
    async def new_automation(request: Request) -> HTMLResponse:
        return await _render_form(request, automation=None)

    @app.post("/automations/new")
    async def create_automation(request: Request) -> Response:
        return await _save_automation(request, await _form_payload(request), automation_id=None)

    @app.get("/automations/{automation_id}/edit", response_class=HTMLResponse)
    async def edit_automation(request: Request, automation_id: str) -> Response:
        automation = store.get(automation_id)
        if automation is None:
            return RedirectResponse(_app_url(request, "/"), status_code=303)
        return await _render_form(request, automation=automation)

    @app.post("/automations/{automation_id}/edit")
    async def update_automation(request: Request, automation_id: str) -> Response:
        existing = store.get(automation_id)
        if existing is None:
            return RedirectResponse(_app_url(request, "/"), status_code=303)
        payload = await _form_payload(request)
        payload["id"] = existing.id
        payload["request_headers"] = existing.request_headers
        return await _save_automation(request, payload, automation_id=existing.id)

    @app.post("/automations/{automation_id}/delete")
    async def delete_automation(request: Request, automation_id: str) -> Response:
        store.delete(automation_id)
        await engine.reload()
        return RedirectResponse(_app_url(request, "/"), status_code=303)

    async def _render_form(
        request: Request,
        *,
        automation: DeviceAutomation | None,
        error: str | None = None,
        form: dict[str, Any] | None = None,
    ) -> HTMLResponse:
        switches, entity_error = await _load_switches()
        return templates.TemplateResponse(
            request,
            "form.html",
            {
                "automation": automation,
                "form": form or {},
                "error": error,
                "entity_error": entity_error,
                "switches": switches,
                "selected": _selected_entities(automation, form),
            },
            status_code=400 if error else 200,
        )

    async def _save_automation(
        request: Request,
        payload: dict[str, Any],
        *,
        automation_id: str | None,
    ) -> Response:
        try:
            automation = automation_from_dict(payload, generate_id=automation_id is None)
            if automation_id is not None:
                automation.id = automation_id
            store.upsert(automation)
        except ConfigError as exc:
            existing = store.get(automation_id) if automation_id else None
            return await _render_form(request, automation=existing, error=str(exc), form=payload)
        await engine.reload()
        return RedirectResponse(_app_url(request, "/"), status_code=303)

    async def _load_switches() -> tuple[list[EntityRef], str | None]:
        try:
            return await home_assistant.list_switches(), None
        except HomeAssistantError as exc:
            return [], str(exc)

    return app


def _selected_entities(automation: DeviceAutomation | None, form: dict[str, Any] | None) -> list[str]:
    if form and "target_entities" in form:
        value = form["target_entities"]
        if isinstance(value, list):
            return [str(item) for item in value]
        if value:
            return [str(value)]
        return []
    if automation is not None:
        return list(automation.target_entities)
    return []


async def _form_payload(request: Request) -> dict[str, Any]:
    form = await request.form()
    return {
        "name": str(form.get("name") or ""),
        "poll_url": str(form.get("poll_url") or ""),
        "poll_interval_seconds": str(form.get("poll_interval_seconds") or "5"),
        "enabled": form.get("enabled") is not None,
        "target_entities": [str(value) for value in form.getlist("target_entities")],
    }


def _app_url(request: Request, path: str) -> str:
    root = (request.scope.get("root_path") or "").rstrip("/")
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{root}{path}"
