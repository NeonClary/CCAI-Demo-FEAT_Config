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

from datetime import datetime
from typing import List, Optional

from bson import ObjectId
from pydantic import BaseModel, Field

from app.models.user import PyObjectId


class UserProfile(BaseModel):
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}

    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    user_id: PyObjectId
    major: Optional[str] = None
    minor: Optional[str] = None
    year: Optional[str] = None
    gpa_range: Optional[str] = None
    career_goals: Optional[str] = None
    courses_completed: List[str] = []
    courses_planned: List[str] = []
    schedule_preferences: Optional[str] = None
    learning_style: Optional[str] = None
    extracurriculars: Optional[str] = None
    advisor_notes: Optional[str] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class UserProfileUpdate(BaseModel):
    major: Optional[str] = None
    minor: Optional[str] = None
    year: Optional[str] = None
    gpa_range: Optional[str] = None
    career_goals: Optional[str] = None
    courses_completed: Optional[List[str]] = None
    courses_planned: Optional[List[str]] = None
    schedule_preferences: Optional[str] = None
    learning_style: Optional[str] = None
    extracurriculars: Optional[str] = None
    advisor_notes: Optional[str] = None


class UserProfileResponse(BaseModel):
    user_id: str
    major: Optional[str] = None
    minor: Optional[str] = None
    year: Optional[str] = None
    gpa_range: Optional[str] = None
    career_goals: Optional[str] = None
    courses_completed: List[str] = []
    courses_planned: List[str] = []
    schedule_preferences: Optional[str] = None
    learning_style: Optional[str] = None
    extracurriculars: Optional[str] = None
    advisor_notes: Optional[str] = None
    updated_at: Optional[datetime] = None
    completion_pct: int = 0
