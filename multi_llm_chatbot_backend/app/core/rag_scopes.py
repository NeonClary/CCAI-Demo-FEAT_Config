"""Reserved session IDs and RAG scope labels for Chroma metadata."""

RAG_SCOPE_SESSION = "session"
RAG_SCOPE_GENERAL = "general_background"
RAG_SCOPE_PERSONA = "persona"

# Seeded general-reference publications (available to all personas).
SESSION_GENERAL_BACKGROUND = "__general_background__"

# Legacy global seed (e.g. data/*.txt) uses this session id.
SESSION_GLOBAL_LEGACY = "__global__"

# Admin-uploaded persona-specific documents (one persona_id per chunk).
SESSION_ADMIN_PERSONA = "__admin_persona__"
