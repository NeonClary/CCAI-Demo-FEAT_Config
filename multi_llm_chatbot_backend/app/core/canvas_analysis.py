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
import re
import traceback
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from app.config import get_settings
from app.llm.improved_gemini_client import ImprovedGeminiClient
from app.llm.improved_ollama_client import ImprovedOllamaClient
from app.models.phd_canvas import CanvasInsight, CanvasSection

LOG = logging.getLogger(__name__)

class CanvasAnalysisService:
    """Service for extracting and categorizing insights from chat messages"""
    
    def __init__(self, llm_client: Optional[Any] = None) -> None:
        self.llm_client = llm_client
        
        # Predefined section mappings for semantic analysis
        self.section_keywords: Dict[str, List[str]] = {
            "research_progress": [
                "progress", "milestone", "completed", "finished", "accomplished", 
                "achieved", "timeline", "deadline", "chapter", "draft", "version"
            ],
            "methodology": [
                "method", "methodology", "approach", "design", "data collection",
                "survey", "interview", "experiment", "analysis", "statistical", 
                "qualitative", "quantitative", "mixed methods"
            ],
            "theoretical_framework": [
                "theory", "theoretical", "framework", "concept", "model",
                "literature", "author", "philosophy", "paradigm", "assumption"
            ],
            "challenges_obstacles": [
                "challenge", "problem", "difficulty", "obstacle", "stuck",
                "confused", "frustrated", "struggle", "barrier", "issue"
            ],
            "next_steps": [
                "next", "plan", "should", "will", "going to", "need to",
                "action", "step", "priority", "focus", "goal", "objective"
            ],
            "writing_communication": [
                "write", "writing", "paper", "thesis", "dissertation", "publication",
                "communication", "presentation", "defense", "draft", "revision"
            ],
            "career_development": [
                "career", "job", "position", "networking", "conference",
                "skills", "CV", "resume", "application", "fellowship", "grant"
            ],
            "literature_review": [
                "literature", "sources", "papers", "articles", "bibliography",
                "citation", "author", "study", "research", "gap", "review"
            ],
            "data_analysis": [
                "data", "analysis", "results", "findings", "statistics",
                "coding", "software", "tool", "visualization", "pattern"
            ],
            "motivation_mindset": [
                "motivation", "confidence", "stress", "anxiety", "balance",
                "mental health", "mindset", "support", "overwhelmed", "burnout"
            ]
        }
    
    async def extract_insights_from_messages(self, messages: List[Dict], chat_session_id: str) -> List[CanvasInsight]:
        """Extract actionable insights from chat messages using semantic analysis"""
        try:
            insights = []
            
            for message in messages:
                msg_type = message.get("type", "")
                
                if msg_type == "advisor":
                    content = message.get("content", "")
                    persona_id = message.get("advisorName", message.get("persona", "advisor"))
                    message_id = message.get("id", str(message.get("_id", "")))
                    
                    if content and len(content.strip()) > 20:
                        persona_insights = await self._extract_insights_from_content(
                            content, persona_id, message_id, chat_session_id
                        )
                        insights.extend(persona_insights)
                        LOG.debug(f"Extracted {len(persona_insights)} insights from {persona_id} message")
                        
                elif msg_type == "assistant" and "responses" in message:
                    for response in message.get("responses", []):
                        persona_insights = await self._extract_insights_from_persona_response(
                            response, message.get("id"), chat_session_id
                        )
                        insights.extend(persona_insights)
                        
                elif message.get("role") == "assistant" and message.get("content"):
                    persona_insights = await self._extract_insights_from_content(
                        message.get("content", ""), "assistant", 
                        message.get("id"), chat_session_id
                    )
                    insights.extend(persona_insights)
            
            # Remove duplicates and low-confidence insights
            unique_insights = self._deduplicate_insights(insights)
            high_confidence_insights = [i for i in unique_insights if i.confidence_score >= 0.5]
            
            LOG.info(f"Extracted {len(high_confidence_insights)} insights from {len(messages)} messages")
            return high_confidence_insights
            
        except Exception as e:
            LOG.error(f"Error extracting insights from messages: {e}")
            LOG.error(f"Full traceback: {traceback.format_exc()}")
            return []
    
    async def _extract_insights_from_persona_response(self, response: Dict, message_id: str, chat_session_id: str) -> List[CanvasInsight]:
        """Extract insights from a single persona response"""
        persona_id = response.get("persona_id", "unknown")
        content = response.get("content", "")
        
        return await self._extract_insights_from_content(content, persona_id, message_id, chat_session_id)
    
    async def _extract_insights_from_content(self, content: str, persona_id: str, message_id: str, chat_session_id: str) -> List[CanvasInsight]:
        """Extract actionable insights from content using LLM analysis"""
        if not content or len(content.strip()) < 30:
            return []
        
        try:
            app_title = get_settings().app.title
            extraction_prompt = (
                f"Extract actionable insights from this {app_title} advisor response "
                f"that would be valuable for a user's progress summary.\n\n"
                f"PERSONA: {persona_id}\n"
                f"CONTENT: {content}\n\n"
                f"Return ONLY a numbered list (1. 2. 3.) of insights. Each insight should be:\n"
                f"- Actionable and specific to the user's progress\n"
                f"- 1-2 sentences long\n"
                f"- Valuable for advisor meetings\n"
                f"- Not generic advice\n\n"
                f"Return ONLY the numbered list, no other text."
            )
            
            if self.llm_client:
                try:
                    llm_response = await self.llm_client.generate(
                        system_prompt=f"You are an expert at extracting actionable guidance from {app_title} advisor responses.",
                        context=[{"role": "user", "content": extraction_prompt}],
                        temperature=0.3,
                        max_tokens=500
                    )
                    
                    lines = [
                        re.sub(r"^\d+[\.\)]\s*", "", line).strip()
                        for line in llm_response.strip().splitlines()
                        if re.match(r"^\d+[\.\)]", line.strip())
                    ]
                    
                    insights: List[CanvasInsight] = []
                    for line in lines:
                        if len(line) < 15:
                            continue
                        length_bonus = min(len(line) / 500, 1.0) * 0.15
                        insight = CanvasInsight(
                            content=line,
                            source_persona=persona_id,
                            source_message_id=message_id,
                            source_chat_session=chat_session_id,
                            confidence_score=round(0.75 + length_bonus, 2),
                            keywords=self._extract_keywords_from_sentence(line)
                        )
                        insights.append(insight)
                    
                    if insights:
                        LOG.debug(f"LLM extracted {len(insights)} insights from {persona_id}")
                        return insights
                    
                    LOG.warning(f"LLM returned no parseable insights for {persona_id}, falling back to rule-based")
                    
                except Exception as llm_error:
                    LOG.warning(f"LLM extraction failed for {persona_id}: {llm_error}")
            
            # Fallback: rule-based extraction
            return self._extract_insights_rule_based(content, persona_id, message_id, chat_session_id)
            
        except Exception as e:
            LOG.error(f"Error extracting insights from {persona_id} content: {e}")
            return []
    
    def _extract_insights_rule_based(self, content: str, persona_id: str, message_id: str, chat_session_id: str) -> List[CanvasInsight]:
        """Fallback rule-based insight extraction"""
        insights: List[CanvasInsight] = []
        
        sentences = re.split(r'[.!?]+', content)
        actionable_patterns = [
            r"(?:you should|consider|try|focus on|prioritize|next step|recommended?|suggest)",
            r"(?:action item|goal|objective|plan|strategy)",
            r"(?:deadline|timeline|schedule|by \w+)",
            r"(?:complete|finish|work on|tackle|address)"
        ]
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 15:
                continue
                
            match_count = sum(1 for pattern in actionable_patterns if re.search(pattern, sentence, re.IGNORECASE))
            
            if match_count > 0:
                keywords = self._extract_keywords_from_sentence(sentence)
                confidence = round(0.55 + min(match_count * 0.05, 0.15), 2)
                
                insight = CanvasInsight(
                    content=sentence,
                    source_persona=persona_id,
                    source_message_id=message_id,
                    source_chat_session=chat_session_id,
                    confidence_score=confidence,
                    keywords=keywords
                )
                insights.append(insight)
        
        LOG.debug(f"Rule-based extracted {len(insights)} insights from {persona_id}")
        return insights[:3]
    
    def _extract_keywords_from_sentence(self, sentence: str) -> List[str]:
        """Extract relevant keywords from a sentence"""
        words = re.findall(r'\b\w{4,}\b', sentence.lower())
        
        stop_words = {
            "should", "could", "would", "your", "research", "work", "study", 
            "consider", "think", "important", "also", "really", "maybe",
            "probably", "definitely", "certainly", "particular", "specific"
        }
        
        keywords = [word for word in words if word not in stop_words]
        return keywords[:5]
    
    def categorize_insights(self, insights: List[CanvasInsight]) -> Dict[str, List[CanvasInsight]]:
        """Categorize insights into canvas sections using semantic analysis"""
        categorized: Dict[str, List[CanvasInsight]] = defaultdict(list)
        
        for insight in insights:
            section = self._determine_section(insight)
            categorized[section].append(insight)
        
        return dict(categorized)
    
    def _determine_section(self, insight: CanvasInsight) -> str:
        """Determine which section an insight belongs to"""
        content_lower = insight.content.lower()
        keywords_lower = [k.lower() for k in insight.keywords]
        all_text = content_lower + " " + " ".join(keywords_lower)
        
        section_scores: Dict[str, int] = {}
        for section, keywords in self.section_keywords.items():
            score = sum(1 for keyword in keywords if keyword in all_text)
            if score > 0:
                section_scores[section] = score
        
        if section_scores:
            return max(section_scores, key=section_scores.get)
        else:
            return "general_notes"
    
    def prioritize_insights(self, insights: List[CanvasInsight]) -> List[CanvasInsight]:
        """Sort insights by priority (confidence score and recency)"""
        return sorted(insights, key=lambda x: (x.confidence_score, x.extracted_at), reverse=True)
    
    def _deduplicate_insights(self, insights: List[CanvasInsight]) -> List[CanvasInsight]:
        """Remove duplicate or very similar insights"""
        if not insights:
            return insights
        
        unique_insights: List[CanvasInsight] = []
        seen_content: Set[str] = set()
        
        for insight in insights:
            content_key = insight.content.lower().strip()[:100]
            
            if content_key not in seen_content:
                seen_content.add(content_key)
                unique_insights.append(insight)
        
        return unique_insights
