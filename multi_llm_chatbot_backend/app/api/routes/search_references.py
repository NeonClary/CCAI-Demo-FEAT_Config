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

import logging
from typing import Dict

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.auth import get_current_active_user
from app.core.bootstrap import create_llm_client
from app.models.user import User

LOG = logging.getLogger(__name__)

router = APIRouter()


class SearchRefRequest(BaseModel):
    statement: str


@router.post("/search-references")
async def generate_search_query(
    req: SearchRefRequest,
    current_user: User = Depends(get_current_active_user),
) -> Dict[str, str]:
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
        LOG.error(f"Reference search generation failed: {e}")
        return {"search_query": req.statement[:100]}
