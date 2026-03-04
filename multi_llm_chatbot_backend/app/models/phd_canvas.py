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
from datetime import datetime
from typing import Any, Dict, List, Optional

from bson import ObjectId
from pydantic import BaseModel, Field

from app.models.user import PyObjectId

LOG = logging.getLogger(__name__)

class CanvasInsight(BaseModel):
    """Individual insight extracted from chat messages"""
    content: str
    source_persona: str
    source_message_id: Optional[str] = None
    source_chat_session: Optional[str] = None
    confidence_score: float = Field(ge=0.0, le=1.0, default=0.8)
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    keywords: List[str] = Field(default_factory=list)

class CanvasSection(BaseModel):
    """A themed section of the PhD Canvas with related insights"""
    title: str
    description: str
    insights: List[CanvasInsight] = Field(default_factory=list)
    priority: int = Field(default=1, ge=1, le=5)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class PhdCanvas(BaseModel):
    """Main PhD Canvas model storing all user insights organized by sections"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId

    sections: Dict[str, CanvasSection] = Field(default_factory=dict)

    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    last_chat_processed: Optional[datetime] = None
    total_insights: int = Field(default=0)

    auto_update: bool = Field(default=True)
    print_optimized: bool = Field(default=True)

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

    def update_section(self, section_key: str, insights: List[CanvasInsight]) -> None:
        """Update a specific canvas section with new insights"""
        if section_key not in self.sections:
            self.sections[section_key] = CanvasSection(
                title=self._get_section_title(section_key),
                description=self._get_section_description(section_key)
            )

        existing_insights_map = {
            insight.content.strip().lower(): insight
            for insight in self.sections[section_key].insights
        }

        existing_sources = {
            (insight.source_chat_session, insight.source_message_id)
            for insight in self.sections[section_key].insights
            if insight.source_chat_session and insight.source_message_id
        }

        new_insights = []
        for insight in insights:
            normalized_content = insight.content.strip().lower()

            if normalized_content in existing_insights_map:
                LOG.debug(f"Skipping duplicate insight: {insight.content[:50]}...")
                continue

            if insight.source_chat_session and insight.source_message_id:
                source_key = (insight.source_chat_session, insight.source_message_id)
                if source_key in existing_sources:
                    LOG.debug(f"Skipping already processed source: {source_key}")
                    continue

            new_insights.append(insight)

        if new_insights:
            LOG.info(f"Adding {len(new_insights)} new insights to section '{section_key}'")
            self.sections[section_key].insights.extend(new_insights)
            self.sections[section_key].updated_at = datetime.utcnow()
            self.last_updated = datetime.utcnow()
        else:
            LOG.info(f"No new insights to add to section '{section_key}' (all {len(insights)} were duplicates)")

        self.total_insights = sum(len(section.insights) for section in self.sections.values())

    def _get_section_title(self, section_key: str) -> str:
        """Get human-readable title for section"""
        titles = {
            "research_progress": "Research Progress & Milestones",
            "methodology": "Research Methods & Approach",
            "theoretical_framework": "Theoretical Foundations",
            "challenges_obstacles": "Challenges & Solutions",
            "next_steps": "Action Items & Next Steps",
            "writing_communication": "Writing & Communication",
            "career_development": "Academic Career Planning",
            "literature_review": "Literature & Sources",
            "data_analysis": "Data & Analysis",
            "motivation_mindset": "Motivation & Mindset"
        }
        return titles.get(section_key, section_key.replace("_", " ").title())

    def _get_section_description(self, section_key: str) -> str:
        """Get description for each section"""
        descriptions = {
            "research_progress": "Key milestones, accomplishments, and timeline updates",
            "methodology": "Research design decisions and methodological insights",
            "theoretical_framework": "Theoretical perspectives and conceptual foundations",
            "challenges_obstacles": "Challenges faced and strategies for overcoming them",
            "next_steps": "Immediate action items and upcoming priorities",
            "writing_communication": "Writing strategies and communication insights",
            "career_development": "Professional development and career planning",
            "literature_review": "Literature gaps, sources, and review strategies",
            "data_analysis": "Data collection and analysis approaches",
            "motivation_mindset": "Motivational insights and mental health considerations"
        }
        return descriptions.get(section_key, "General insights and guidance")

class CanvasResponse(BaseModel):
    """Response model for canvas API endpoints"""
    id: str
    user_id: str
    sections: Dict[str, CanvasSection]
    created_at: datetime
    last_updated: datetime
    last_chat_processed: Optional[datetime]
    total_insights: int
    auto_update: bool
    print_optimized: bool

class UpdateCanvasRequest(BaseModel):
    """Request model for updating canvas"""
    force_full_update: bool = Field(default=False)
    include_chat_sessions: Optional[List[str]] = None
    exclude_sections: Optional[List[str]] = None
