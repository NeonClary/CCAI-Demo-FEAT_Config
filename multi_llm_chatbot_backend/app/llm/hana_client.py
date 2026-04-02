"""
HANA BrainForge client — authenticates and discovers models with personas.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

import httpx

from app.config import get_settings

LOG = logging.getLogger(__name__)

_TOKEN_NAME = "WhiteLabelAdvisorPanel"
_CLIENT_ID = "white-label-advisor-panel"


class HanaClient:
    """Handles HANA API authentication and model/persona discovery."""

    def __init__(self) -> None:
        settings = get_settings()
        self._base = (settings.hana.base_url or "").rstrip("/")
        self._username = settings.hana.username or ""
        self._password = settings.hana.password or ""
        self._access_token: str = ""
        self._refresh_token: str = ""
        self._token_expiry: float = 0
        self._klatchat_access_token: str = ""
        self._klatchat_refresh_token: str = ""
        self._klatchat_token_expiry: float = 0
        self._client: Optional[httpx.AsyncClient] = None

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0)
        return self._client

    def _hana(self):
        return get_settings().hana

    @property
    def is_configured(self) -> bool:
        return bool(self._base and self._username and self._password)

    async def authenticate(self) -> None:
        client = self._get_client()
        resp = await client.post(
            f"{self._base}/auth/login",
            json={
                "username": self._username,
                "password": self._password,
                "token_name": _TOKEN_NAME,
                "client_id": _CLIENT_ID,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        self._access_token = data["access_token"]
        self._refresh_token = data["refresh_token"]
        self._token_expiry = data.get("expiration", time.time() + 3600)
        LOG.info("HANA auth success (user=%s)", data.get("username"))

    async def authenticate_klatchat(self) -> None:
        h = self._hana()
        uname = (h.username_klatchat or h.username or "").strip()
        pwd = (h.password_klatchat or "").strip()
        if not pwd:
            raise ValueError("hana.password_klatchat not set")
        client = self._get_client()
        resp = await client.post(
            f"{self._base}/auth/login",
            json={
                "username": uname,
                "password": pwd,
                "token_name": _TOKEN_NAME,
                "client_id": _CLIENT_ID,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        self._klatchat_access_token = data["access_token"]
        self._klatchat_refresh_token = data["refresh_token"]
        self._klatchat_token_expiry = data.get("expiration", time.time() + 3600)
        LOG.info("HANA klatchat auth success (user=%s)", data.get("username"))

    async def _ensure_token(self) -> None:
        if not self._access_token or time.time() >= self._token_expiry - 60:
            try:
                client = self._get_client()
                resp = await client.post(
                    f"{self._base}/auth/refresh",
                    json={
                        "access_token": self._access_token,
                        "refresh_token": self._refresh_token,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                self._access_token = data["access_token"]
                self._refresh_token = data["refresh_token"]
                self._token_expiry = data.get("expiration", time.time() + 3600)
                LOG.info("HANA token refreshed")
            except Exception:
                LOG.warning("Token refresh failed, re-authenticating")
                await self.authenticate()

    async def _ensure_klatchat_token(self) -> None:
        h = self._hana()
        if not (h.password_klatchat or "").strip():
            await self._ensure_token()
            return
        if not self._klatchat_access_token or time.time() >= self._klatchat_token_expiry - 60:
            try:
                client = self._get_client()
                resp = await client.post(
                    f"{self._base}/auth/refresh",
                    json={
                        "access_token": self._klatchat_access_token,
                        "refresh_token": self._klatchat_refresh_token,
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                self._klatchat_access_token = data["access_token"]
                self._klatchat_refresh_token = data["refresh_token"]
                self._klatchat_token_expiry = data.get("expiration", time.time() + 3600)
                LOG.info("HANA klatchat token refreshed")
            except Exception:
                LOG.warning("Klatchat token refresh failed, re-authenticating")
                await self.authenticate_klatchat()

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

    def _headers_klatchat(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._klatchat_access_token}",
            "Content-Type": "application/json",
        }

    def _parse_models_payload(self, data: dict[str, Any]) -> List[Dict[str, Any]]:
        models: List[Dict[str, Any]] = []
        for m in data.get("models", []):
            personas: List[Dict[str, Any]] = []
            for p in m.get("personas", []):
                personas.append({
                    "id": p.get("id", p.get("persona_name", "")),
                    "persona_name": p.get("persona_name", ""),
                    "description": p.get("description"),
                    "system_prompt": p.get("system_prompt"),
                    "enabled": p.get("enabled", True),
                })
            models.append({
                "name": m["name"],
                "version": m["version"],
                "model_id": f"{m['name']}@{m['version']}",
                "personas": personas,
            })
        return models

    async def get_models(self) -> List[Dict[str, Any]]:
        """Fetch all models with their personas from HANA BrainForge."""
        await self._ensure_token()
        client = self._get_client()
        resp = await client.post(
            f"{self._base}/brainforge/get_models",
            headers=self._headers,
            json={},
        )
        resp.raise_for_status()
        models = self._parse_models_payload(resp.json())
        seen = {m["model_id"] for m in models}

        h = self._hana()
        if (h.password_klatchat or "").strip():
            try:
                await self._ensure_klatchat_token()
                resp2 = await client.post(
                    f"{self._base}/brainforge/get_models",
                    headers=self._headers_klatchat(),
                    json={},
                )
                resp2.raise_for_status()
                for m in self._parse_models_payload(resp2.json()):
                    if m["model_id"] not in seen:
                        models.append(m)
                        seen.add(m["model_id"])
            except Exception as exc:
                LOG.warning("HANA get_models (klatchat) merge skipped: %s", exc)

        return models

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()


hana_client = HanaClient()
