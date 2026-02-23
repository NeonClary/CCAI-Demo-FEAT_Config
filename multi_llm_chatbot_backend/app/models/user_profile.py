from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from bson import ObjectId
from app.models.user import PyObjectId


class UserProfile(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        arbitrary_types_allowed=True,
        json_encoders={ObjectId: str},
    )

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
