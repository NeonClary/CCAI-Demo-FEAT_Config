# NEON AI (TM) SOFTWARE, Software Development Kit & Application Framework
# All Rights Reserved 2008-2025
# Licensed under the BSD 3-Clause License
# https://opensource.org/licenses/BSD-3-Clause
#
# Copyright (c) 2008-2025, Neongecko.com Inc.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its contributors
#    may be used to endorse or promote products derived from this software
#    without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
"""
Centralised application configuration.

Reads ``config.yaml`` from the project root (two levels above this file) and
validates it with Pydantic models.  Every setting falls back to environment
variables when the YAML value is empty, so existing ``.env`` workflows keep
working.
"""

from __future__ import annotations

import os
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, validator, Field

LOG = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class FeatureConfig(BaseModel):
    """Single feature entry displayed on the homepage."""

    title: str = ""
    description: str = ""
    icon: str = "HelpCircle"


class UserAvatarOption(BaseModel):
    """Selectable user avatar option."""

    id: str
    icon: str = "User"
    color: str = "#6B7280"
    bg: str = "#F3F4F6"


class AppConfig(BaseModel):
    """Top-level application chrome settings."""

    title: str = "Advisor Canvas"
    subtitle: str = "AI-Powered Guidance"
    primary_color: str = "#7C3AED"
    footer_text: str = ""
    user_avatars: List[UserAvatarOption] = []


class HomepageConfig(BaseModel):
    """Homepage copy and feature list."""

    headline_prefix: str = "Get Guidance from"
    headline_highlight: str = "Advisor Personas"
    description: str = ""
    features_title: str = "Why Choose Our Advisory Panel?"
    features: List[FeatureConfig] = []


class AcademicStage(BaseModel):
    """Single academic-stage option for registration."""

    value: str = ""
    label: str = ""


class LoginConfig(BaseModel):
    """Login / signup page configuration."""

    subtitle: str = "Sign in to continue"
    signup_subtitle: str = "Create your account to get personalized guidance from expert advisors"
    academic_stages: List[AcademicStage] = []


class ExampleCategory(BaseModel):
    """Chat-page example suggestion category."""

    title: str
    icon: str = "BookOpen"
    avatar: str = ""
    color: str = "#3B82F6"
    bg_color: str = "#EFF6FF"
    suggestions: List[str] = []


class ChatPageConfig(BaseModel):
    """Chat page UI configuration."""

    placeholder: str = "Ask your advisors anything..."
    examples: List[ExampleCategory] = []


class PersonaItemConfig(BaseModel):
    """Single persona entry from ``config.yaml``."""

    id: str
    type: str = "advisor"
    name: str
    role: str = ""
    summary: str = ""
    color: str = "#6B7280"
    bg_color: str = "#F3F4F6"
    dark_color: str = "#9CA3AF"
    dark_bg_color: str = "#374151"
    icon: str = "HelpCircle"
    avatar: str = ""
    temperature: int = 5
    persona_prompt: str = ""
    lemonslice_agent_id: str = ""


class PersonasConfig(BaseModel):
    """Container for the shared base prompt and persona items."""

    base_prompt: str = ""
    items: List[PersonaItemConfig] = []


class OrchestratorConfig(BaseModel):
    """Orchestrator routing configuration."""

    avatar: str = ""
    vague_patterns: List[str] = []
    min_words_without_keywords: int = 6
    specific_keywords: List[str] = []
    clarification_questions: List[str] = []
    clarification_suggestions: List[str] = []


class AuthConfig(BaseModel):
    """JWT authentication settings."""

    jwt_secret: str = ""
    algorithm: str = "HS256"
    token_expiry_minutes: int = 43200  # 30 days

    @validator("jwt_secret", always=True)
    def _fallback_jwt_secret(cls, v: str) -> str:  # noqa: N805
        return v or os.getenv(
            "JWT_SECRET_KEY",
            "your-secret-key-change-this-in-production",
        )


class MongoDBConfig(BaseModel):
    """MongoDB connection settings."""

    connection_string: str = ""
    database_name: str = "undergrad_advisor"

    @validator("connection_string", always=True)
    def _fallback_connection_string(cls, v: str) -> str:  # noqa: N805
        return v or os.getenv("MONGODB_CONNECTION_STRING", "")


class GeminiConfig(BaseModel):
    """Google Gemini LLM settings."""

    api_key: str = ""
    model: str = "gemini-2.0-flash"

    @validator("api_key", always=True)
    def _fallback_api_key(cls, v: str) -> str:  # noqa: N805
        return v or os.getenv("GEMINI_API_KEY", "")

    @validator("model", always=True)
    def _fallback_model(cls, v: str) -> str:  # noqa: N805
        return os.getenv("GEMINI_MODEL", "") or v


class OllamaConfig(BaseModel):
    """Local Ollama LLM settings."""

    model: str = "llama3.2:1b"
    base_url: str = "http://localhost:11434"

    @validator("base_url", always=True)
    def _fallback_base_url(cls, v: str) -> str:  # noqa: N805
        return v or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


class VLLMClientEntry(BaseModel):
    """Single vLLM server endpoint."""

    id: str
    name: str = ""
    api_url: str

    @validator("name", always=True)
    def _name_from_id(cls, v: str, values: Dict[str, Any]) -> str:  # noqa: N805
        return v or values.get("id", "")


class VLLMConfig(BaseModel):
    """Self-hosted vLLM cluster accessed via the OpenAI-compatible API."""

    api_key: str = ""
    clients: List[VLLMClientEntry] = []

    @validator("api_key", always=True)
    def _fallback_api_key(cls, v: str) -> str:  # noqa: N805
        return v or os.getenv("VLLM_API_KEY", "")


class LLMConfig(BaseModel):
    """Aggregated LLM backend configuration."""

    gemini: GeminiConfig = GeminiConfig()
    ollama: OllamaConfig = OllamaConfig()
    vllm: VLLMConfig = VLLMConfig()


class RAGConfig(BaseModel):
    """Retrieval-augmented generation settings."""

    embedding_model: str = "all-MiniLM-L6-v2"
    chroma_collection: str = "undergrad_advisor_documents"


class SemesterConfig(BaseModel):
    """Single semester entry for scheduling."""

    name: str = ""
    end_date: str = ""


class SchedulingConfig(BaseModel):
    """Academic scheduling configuration."""

    cu_semesters: List[SemesterConfig] = []


class LemonSliceConfig(BaseModel):
    """LemonSlice integration settings."""

    enabled: bool = False
    api_key: str = ""
    default_agent_id: str = ""
    widget_url: str = "https://unpkg.com/@lemonsliceai/lemon-slice-widget"

    @validator("api_key", always=True)
    def _fallback_api_key(cls, v: str) -> str:  # noqa: N805
        return v or os.getenv("LEMONSLICE_API_KEY", "")


class AppSettings(BaseModel):
    """Top-level container that mirrors the YAML structure."""

    app: AppConfig = AppConfig()
    homepage: HomepageConfig = HomepageConfig()
    login: LoginConfig = LoginConfig()
    chat_page: ChatPageConfig = ChatPageConfig()
    personas: PersonasConfig = PersonasConfig()
    orchestrator: OrchestratorConfig = OrchestratorConfig()
    auth: AuthConfig = AuthConfig()
    mongodb: MongoDBConfig = MongoDBConfig()
    llm: LLMConfig = LLMConfig()
    rag: RAGConfig = RAGConfig()
    scheduling: SchedulingConfig = SchedulingConfig()
    lemonslice: LemonSliceConfig = LemonSliceConfig()

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def get_public_config(self) -> Dict[str, Any]:
        """Return the subset of configuration safe to expose to the frontend
        via ``GET /api/config``.  Secrets are excluded.

        :returns: Dictionary of public-safe configuration values.
        :rtype:   dict
        """
        return {
            "app": self.app.dict(),
            "homepage": self.homepage.dict(),
            "login": self.login.dict(),
            "chat_page": self.chat_page.dict(),
            "personas": {
                "items": [
                    {
                        "id": p.id,
                        "type": p.type,
                        "name": p.name,
                        "role": p.role,
                        "summary": p.summary,
                        "color": p.color,
                        "bg_color": p.bg_color,
                        "dark_color": p.dark_color,
                        "dark_bg_color": p.dark_bg_color,
                        "icon": p.icon,
                        "avatar": p.avatar,
                        "lemonslice_agent_id": p.lemonslice_agent_id,
                    }
                    for p in self.personas.items
                ],
            },
            "orchestrator": {
                "avatar": self.orchestrator.avatar,
            },
            "lemonslice": {
                "enabled": self.lemonslice.enabled,
                "default_agent_id": self.lemonslice.default_agent_id,
                "widget_url": self.lemonslice.widget_url,
            },
        }


# ---------------------------------------------------------------------------
# Singleton loader
# ---------------------------------------------------------------------------

_settings: Optional[AppSettings] = None


def _find_config_yaml() -> Path:
    """Walk upwards from this file to find ``config.yaml``.

    :returns: Resolved path to ``config.yaml``.
    :rtype:   Path
    """
    current = Path(__file__).resolve().parent  # app/
    for _ in range(5):
        candidate = current / "config.yaml"
        if candidate.exists():
            return candidate
        current = current.parent
    return Path(__file__).resolve().parent.parent.parent / "config.yaml"


def load_settings(config_path: Optional[str] = None) -> AppSettings:
    """Load and validate ``config.yaml``, returning an :class:`AppSettings`.

    The result is cached as a module-level singleton so subsequent calls are
    free.  Pass *config_path* to override the auto-detected location (useful
    for tests).

    :param config_path: Optional explicit path to the YAML file.
    :returns:           Validated application settings.
    :rtype:             AppSettings
    """
    global _settings
    if _settings is not None:
        return _settings

    path = Path(config_path) if config_path else _find_config_yaml()
    if path.exists():
        LOG.info(f"Loading configuration from {path}")
        with open(path, "r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
    else:
        LOG.warning(
            f"config.yaml not found at {path} — using defaults + env vars"
        )
        raw = {}

    _settings = AppSettings(**raw)
    LOG.info(f"Configuration loaded: app.title={_settings.app.title!r}")
    return _settings


def get_settings() -> AppSettings:
    """Return the cached settings singleton (loads on first call).

    :returns: The application settings.
    :rtype:   AppSettings
    """
    return load_settings()
