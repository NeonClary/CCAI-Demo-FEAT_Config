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

import re
from typing import Dict, List, Optional

from app.llm.llm_client import LLMClient

SENTINEL = "</END>"

COMPACT_MARKDOWN_V1 = (
    "You must format your answer using GitHub-Flavored Markdown and exactly these three sections in this order:\n"
    "### Thought\n"
    "- One sentence only.\n"
    "\n"
    "### What to do\n"
    "- Exactly 3 bullet points, one line each. Use '-' as the bullet. Do not use unicode bullets.\n"
    "- If you would use an ordered list, keep text on the same line as the number (e.g., '1. Do X').\n"
    "\n"
    "### Next step\n"
    "- One imperative sentence only.\n"
    "\n"
    "Rules: Use '###' for headings (never bold-as-heading). Insert a blank line between blocks. "
    "Do not include tables or code blocks unless explicitly requested. "
    "Do not include preambles or conclusions outside the three sections. "
    f"Finish your response with the sentinel token {SENTINEL}."
)

STRUCTURE_HINTS = {
    "short": "Keep it very concise: Thought as one short sentence; bullets \u2264 12 words; next step one short sentence.",
    "medium": "Be concise but clear: Thought one sentence; bullets \u2264 18 words; next step one sentence.",
    "long": "Provide slightly more detail while staying compact: Thought one sentence; bullets \u2264 24 words; next step one sentence.",
}

MAX_TOKENS_MAP = {
    "short": 300,
    "medium": 500,
    "long": 800,
}


def _cut_at_sentinel(text: str) -> str:
    """Remove everything after the sentinel token.

    :param text: Raw LLM output.
    :returns:    Text truncated at the sentinel, or unchanged if absent.
    """
    if not text:
        return ""
    idx = text.find(SENTINEL)
    return text[:idx] if idx != -1 else text


def _normalize_eols(text: str) -> str:
    """Normalise all line endings to ``\\n``.

    :param text: Input text.
    :returns:    Text with uniform line endings.
    """
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _rstrip_lines(text: str) -> str:
    """Strip trailing whitespace from every line.

    :param text: Input text.
    :returns:    Text with each line right-stripped.
    """
    return "\n".join(line.rstrip() for line in text.split("\n"))


def _convert_bold_headers_to_atx(lines: List[str]) -> List[str]:
    """Convert full-line bold markers (``**Heading**``) to ATX headings.

    :param lines: Source lines.
    :returns:     Lines with bold headers replaced by ``### Heading``.
    """
    out: List[str] = []
    for l in lines:
        m = re.match(r"^\s*\*\*(.+?)\*\*\s*:?\s*$", l)
        if m:
            out.append(f"### {m.group(1).strip()}")
        else:
            out.append(l)
    return out


def _convert_unicode_bullets(lines: List[str]) -> List[str]:
    """Replace Unicode bullet characters with standard ``- `` dashes.

    :param lines: Source lines.
    :returns:     Lines with normalised bullets.
    """
    out: List[str] = []
    for l in lines:
        out.append(re.sub(r"^\s*[\u2022\u25cf\u25aa\u25e6]\s+", "- ", l))
    return out


def _merge_orphan_numbered_items(lines: List[str]) -> List[str]:
    """Merge orphan numbered-list markers with the next non-empty line.

    :param lines: Source lines.
    :returns:     Lines with orphan markers merged.
    """
    out: List[str] = []
    i: int = 0
    while i < len(lines):
        cur = lines[i]
        m = re.match(r"^\s*(\d+)\.\s*$", cur)
        if m:
            j = i + 1
            while j < len(lines) and lines[j].strip() == "":
                j += 1
            if j < len(lines):
                out.append(f"{m.group(1)}. {lines[j].strip()}")
                i = j + 1
                continue
        out.append(cur)
        i += 1
    return out


def _collapse_blank_runs(text: str) -> str:
    """Collapse three or more consecutive blank lines into two.

    :param text: Input text.
    :returns:    Text with collapsed blank-line runs.
    """
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _truncate_words(s: str, limit: int) -> str:
    """Truncate *s* to at most *limit* words, appending an ellipsis if trimmed.

    :param s:     Input string.
    :param limit: Maximum word count.
    :returns:     Possibly truncated string.
    """
    words = s.strip().split()
    if len(words) <= limit:
        return s.strip()
    return " ".join(words[:limit]) + "\u2026"


def _first_sentence(text: str, max_words: int) -> str:
    """Extract the first sentence and truncate to *max_words*.

    :param text:      Input text.
    :param max_words: Maximum word count.
    :returns:         First sentence, possibly truncated.
    """
    parts = re.split(r"(?<=[\.!?])\s+", text.strip())
    first = parts[0] if parts else text.strip()
    return _truncate_words(first, max_words)


def _extract_heading_blocks(lines: List[str]) -> Dict[str, List[str]]:
    """Extract content lines under each expected ATX heading.

    :param lines: Source lines.
    :returns:     Mapping of heading name to its content lines.
    """
    sections: Dict[str, List[str]] = {"Thought": [], "What to do": [], "Next step": []}
    current: Optional[str] = None
    for l in lines:
        if l.strip().lower().startswith("### thought"):
            current = "Thought"
            continue
        if l.strip().lower().startswith("### what to do"):
            current = "What to do"
            continue
        if l.strip().lower().startswith("### next step"):
            current = "Next step"
            continue
        if current:
            sections[current].append(l)
    return sections


def _extract_bullets(lines: List[str]) -> List[str]:
    """Extract bullet or numbered-list items from *lines*.

    :param lines: Source lines.
    :returns:     List of extracted bullet text (without markers).
    """
    bullets: List[str] = []
    for l in lines:
        s = l.strip()
        if s.startswith("- "):
            bullets.append(s[2:].strip())
        elif s.startswith("* "):
            bullets.append(s[2:].strip())
        else:
            m = re.match(r"^(\d+)\.\s+(.*)$", s)
            if m and m.group(2).strip():
                bullets.append(m.group(2).strip())
    return bullets


def _synthesize_bullets_from_text(text: str, max_items: int, per_bullet_words: int) -> List[str]:
    """Create bullet items from free-form text by splitting on sentences.

    :param text:             Source text.
    :param max_items:        Maximum number of bullets to produce.
    :param per_bullet_words: Word limit per bullet.
    :returns:                List of synthesised bullet strings.
    """
    sentences = re.split(r"(?<=[\.!?])\s+", text.strip())
    items: List[str] = []
    for s in sentences:
        s_clean = s.strip("-\u2022* ").strip()
        if not s_clean:
            continue
        items.append(_truncate_words(s_clean, per_bullet_words))
        if len(items) >= max_items:
            break
    if not items:
        return []
    return items[:max_items]


def _ensure_compact_shape(text: str, response_length: str) -> str:
    """Normalise raw LLM output into the canonical three-section compact shape.

    :param text:            Raw response text.
    :param response_length: One of ``"short"``, ``"medium"``, ``"long"``.
    :returns:               Compact Markdown with Thought / What to do / Next step.
    """
    per_bullet_words = 12 if response_length == "short" else 18 if response_length == "medium" else 24
    sentence_words = 18 if response_length == "short" else 26 if response_length == "medium" else 34

    t = _cut_at_sentinel(_rstrip_lines(_normalize_eols(text)))
    lines = t.split("\n")
    lines = _convert_bold_headers_to_atx(lines)
    lines = _convert_unicode_bullets(lines)
    lines = _merge_orphan_numbered_items(lines)
    t = _collapse_blank_runs("\n".join(lines))
    lines = t.split("\n")

    sections = _extract_heading_blocks(lines)
    have_all = all(sections[k] for k in sections.keys())

    if not have_all:
        raw_plain = " ".join([l for l in lines if not l.strip().startswith("#")]).strip()
        tldr = _first_sentence(raw_plain, sentence_words) if raw_plain else ""
        bullets = _extract_bullets(lines)
        if not bullets:
            bullets = _synthesize_bullets_from_text(raw_plain, 3, per_bullet_words)
        bullets = [_truncate_words(b, per_bullet_words) for b in bullets[:3]]
        next_step = ""
        for cand in bullets:
            if cand:
                next_step = cand
                break
        if not next_step:
            next_step = tldr or "Proceed with the most actionable item."
        next_step = _truncate_words(next_step, sentence_words)

        parts: List[str] = []
        parts.append("### Thought")
        parts.append(tldr or "Concise summary unavailable.")
        parts.append("")
        parts.append("### What to do")
        if bullets:
            for b in bullets:
                parts.append(f"- {b}")
        else:
            parts.append("- Identify the key task.")
            parts.append("- Decide the immediate next action.")
            parts.append("- Verify prerequisites and proceed.")
        parts.append("")
        parts.append("### Next step")
        parts.append(next_step)
        return "\n".join(parts).strip()

    tldr_body = " ".join([l.strip() for l in sections["Thought"] if l.strip()])
    tldr_final = _first_sentence(tldr_body, sentence_words) if tldr_body else "Concise summary unavailable."

    bullets = _extract_bullets(sections["What to do"])
    bullets = [_truncate_words(b, per_bullet_words) for b in bullets[:3]]
    if len(bullets) < 3:
        raw_plain = " ".join([l for l in lines if not l.strip().startswith("#")]).strip()
        filler = _synthesize_bullets_from_text(raw_plain, 3 - len(bullets), per_bullet_words)
        bullets.extend(filler)
    bullets = bullets[:3]

    next_body = " ".join([l.strip() for l in sections["Next step"] if l.strip()])
    if not next_body:
        next_body = bullets[0] if bullets else tldr_final
    next_final = _truncate_words(_first_sentence(next_body, sentence_words), sentence_words)

    parts = []
    parts.append("### Thought")
    parts.append(tldr_final)
    parts.append("")
    parts.append("### What to do")
    for b in bullets[:3]:
        parts.append(f"- {b}")
    parts.append("")
    parts.append("### Next step")
    parts.append(next_final)

    return "\n".join(parts).strip()


class Persona:
    """Wraps a single persona identity and its LLM backend for response generation."""

    def __init__(self, id: str, name: str, system_prompt: str, llm: LLMClient, temperature: int = 5) -> None:
        self.id = id
        self.name = name
        self.system_prompt = system_prompt
        self.llm = llm
        self.temperature = temperature

    async def respond(self, context: List[Dict], response_length: str = "medium") -> str:
        """Generate a compact, well-formed Markdown response suitable for the UI.

        :param context:         Conversation history.
        :param response_length: One of ``"short"``, ``"medium"``, ``"long"``.
        :returns:               Compact Markdown string.
        """
        max_tokens = MAX_TOKENS_MAP.get(response_length, 500)
        structure_hint = STRUCTURE_HINTS.get(response_length, STRUCTURE_HINTS["medium"])
        temp_scaled = round(self.temperature / 10, 2)

        full_prompt = (
            f"{self.system_prompt}\n\n"
            f"{COMPACT_MARKDOWN_V1}\n\n"
            f"{structure_hint}"
        )

        raw_text = await self.llm.generate(
            system_prompt=full_prompt,
            context=context,
            temperature=temp_scaled,
            max_tokens=max_tokens,
        )

        compact = _ensure_compact_shape(raw_text or "", response_length)

        if len(compact) > 4000:
            compact = _ensure_compact_shape(compact, "short")

        return compact
