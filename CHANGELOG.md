# Changelog

## [2.0.0] — 2025-02-28
### Added
- Centralised YAML-driven configuration (`config.yaml`)
- Multi-persona advisor panel with intelligent routing
- Parallel LLM response generation across personas
- SSE streaming endpoint (`/chat-stream`)
- Course database sub-agent with follow-up resolution
- RAG document upload, chunking, and retrieval via ChromaDB
- User profile memory for personalised advice
- LLM-powered clarification for vague queries
- Synthesised single-answer mode across advisors
- CU Boulder course & professor scraper with scheduling
- Global RAG seed from scraped university pages
- Pydantic-validated configuration with env-var fallbacks
- LemonSlice animated avatar integration (optional)

### Changed
- Project restructured to follow BSD-3 Neon AI coding conventions
- Requirements moved to `requirements/requirements.txt` with pinned versions
- Added `setup.py`, `version.py`, and `__main__.py` entry point
- Consistent `LOG` naming for all module loggers
- RST-style docstrings and full type annotations on public APIs
- Database queries centralised in `app/core/queries.py`
- License headers added to all Python source files
