from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.models.user import User
from app.core.auth import get_current_active_user
from app.core.bootstrap import create_llm_client
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


class SearchRefRequest(BaseModel):
    statement: str


@router.post("/search-references")
async def generate_search_query(
    req: SearchRefRequest,
    current_user: User = Depends(get_current_active_user),
):
    """Generate a concise search query from an advisor statement."""
    llm = create_llm_client()
    try:
        result = await llm.generate(
            system_prompt=(
                "You convert an advisor's statement into a concise web search query "
                "suitable for finding supporting references and citations. "
                "Return ONLY the search query text, nothing else."
            ),
            context=[{"role": "user", "content": req.statement[:500]}],
            temperature=0.2,
            max_tokens=100,
        )
        return {"search_query": result.strip()}
    except Exception as e:
        logger.error(f"Reference search generation failed: {e}")
        return {"search_query": req.statement[:100]}
