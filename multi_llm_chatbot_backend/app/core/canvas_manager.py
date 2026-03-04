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

import asyncio
import hashlib
import logging
import traceback
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from bson import ObjectId

from app.core.bootstrap import llm
from app.core.canvas_analysis import CanvasAnalysisService
from app.models.phd_canvas import CanvasInsight, PhdCanvas, UpdateCanvasRequest

LOG = logging.getLogger(__name__)

_CANVAS_MANAGER_INSTANCE: Optional["CanvasManager"] = None


class CanvasManager:
    """Manages PhD Canvas creation, updates, and incremental processing"""
    
    def __init__(self) -> None:
        self.analysis_service = CanvasAnalysisService(llm_client=llm)
        self._db: Any = None
        self._update_locks: Dict[str, asyncio.Lock] = {}
    
    def get_database(self) -> Any:
        """Lazy database connection to avoid circular imports"""
        if self._db is None:
            from app.core.database import get_database
            self._db = get_database()
        return self._db
    
    async def get_or_create_canvas(self, user_id: str) -> PhdCanvas:
        """Get existing canvas or create new one for user"""
        try:
            db = self.get_database()
            user_object_id = ObjectId(user_id)
            
            canvas_doc = await db.phd_canvases.find_one({"user_id": user_object_id})
            
            if canvas_doc:
                canvas = PhdCanvas(**canvas_doc)
                LOG.info(f"Found existing canvas for user {user_id} with {canvas.total_insights} insights")
                return canvas
            else:
                canvas = PhdCanvas(user_id=user_object_id)
                
                result = await db.phd_canvases.insert_one(canvas.dict(by_alias=True))
                canvas.id = result.inserted_id
                
                LOG.info(f"Created new canvas for user {user_id}")
                return canvas
                
        except Exception as e:
            LOG.error(f"Error getting/creating canvas for user {user_id}: {e}")
            return PhdCanvas(user_id=ObjectId(user_id))
    
    async def update_canvas(self, user_id: str, request: UpdateCanvasRequest) -> PhdCanvas:
        """Update canvas with latest insights from chat sessions"""
        
        if user_id not in self._update_locks:
            self._update_locks[user_id] = asyncio.Lock()
        
        if self._update_locks[user_id].locked():
            LOG.warning(f"Canvas update already in progress for user {user_id}, skipping duplicate request")
            return await self.get_or_create_canvas(user_id)
        
        async with self._update_locks[user_id]:
            try:
                db = self.get_database()
                canvas = await self.get_or_create_canvas(user_id)
                
                LOG.info(f"Updating canvas for user {user_id}, force_full={request.force_full_update}")
                
                is_first_time_update = (
                    canvas.last_chat_processed is None and 
                    canvas.total_insights == 0 and
                    not request.force_full_update
                )
                
                if is_first_time_update:
                    LOG.info(f"Auto-detecting first-time canvas update for user {user_id}. Converting to full update.")
                    request.force_full_update = True
                
                update_started_at = datetime.utcnow()
                
                if request.force_full_update:
                    chat_sessions = await self._get_all_user_chat_sessions(user_id)
                    LOG.info(f"Force full update: processing {len(chat_sessions)} total chat sessions")
                else:
                    chat_sessions = await self._get_new_chat_sessions(user_id, canvas.last_chat_processed)
                    LOG.info(f"Incremental update: processing {len(chat_sessions)} new chat sessions since {canvas.last_chat_processed}")
                
                if not chat_sessions:
                    LOG.info("No new chat sessions to process")
                    return canvas
                
                if request.include_chat_sessions:
                    chat_sessions = [
                        chat for chat in chat_sessions 
                        if str(chat["_id"]) in request.include_chat_sessions
                    ]
                    LOG.info(f"Filtered to {len(chat_sessions)} specifically requested chat sessions")
                
                processed_sources: set = set()
                
                for section in canvas.sections.values():
                    for insight in section.insights:
                        if insight.source_chat_session and insight.source_message_id:
                            processed_sources.add((insight.source_chat_session, insight.source_message_id))
                
                all_new_insights: List[CanvasInsight] = []
                processed_chat_ids: List[str] = []
                
                for chat_session in chat_sessions:
                    try:
                        chat_id = str(chat_session["_id"])
                        messages = chat_session.get("messages", [])
                        
                        if not messages:
                            continue
                        
                        messages_to_process = []
                        for msg in messages:
                            msg_id = msg.get('id', '')
                            if (chat_id, msg_id) not in processed_sources:
                                messages_to_process.append(msg)
                        
                        if not messages_to_process:
                            LOG.info(f"All messages from chat {chat_id} already processed, skipping")
                            continue
                        
                        LOG.info(f"Processing {len(messages_to_process)} new messages from chat {chat_id}")
                        
                        session_insights = await self.analysis_service.extract_insights_from_messages(
                            messages_to_process, chat_id
                        )
                        
                        if session_insights:
                            all_new_insights.extend(session_insights)
                            processed_chat_ids.append(chat_id)
                            LOG.info(f"Extracted {len(session_insights)} insights from chat {chat_id}")
                        
                    except Exception as e:
                        LOG.error(f"Error processing chat session {chat_session.get('_id')}: {e}")
                        continue
                
                if all_new_insights:
                    categorized_insights = self.analysis_service.categorize_insights(all_new_insights)
                    
                    sections_updated = 0
                    for section_key, insights in categorized_insights.items():
                        if request.exclude_sections and section_key in request.exclude_sections:
                            continue
                        
                        prioritized_insights = self.analysis_service.prioritize_insights(insights)
                        
                        MAX_INSIGHTS_PER_SECTION = 10
                        limited_insights = prioritized_insights[:MAX_INSIGHTS_PER_SECTION]
                        
                        if limited_insights:
                            canvas.update_section(section_key, limited_insights)
                            sections_updated += 1
                            LOG.info(f"Updated section '{section_key}' with {len(limited_insights)} insights")
                    
                    canvas.last_chat_processed = update_started_at
                    canvas.last_updated = datetime.utcnow()
                    
                    await self._save_canvas(canvas)
                    
                    LOG.info(f"Canvas update completed: {len(all_new_insights)} new insights, {sections_updated} sections updated")
                else:
                    LOG.info("No insights extracted from chat sessions")
                
                return canvas
                
            except Exception as e:
                LOG.error(f"Error updating canvas for user {user_id}: {e}")
                LOG.error(f"Full traceback: {traceback.format_exc()}")
                raise
            finally:
                if user_id in self._update_locks and not self._update_locks[user_id].locked():
                    pass
    
    async def _get_all_user_chat_sessions(self, user_id: str) -> List[Dict]:
        """Get all chat sessions for a user"""
        try:
            db = self.get_database()
            user_object_id = ObjectId(user_id)
            
            cursor = db.chat_sessions.find({
                "user_id": user_object_id,
                "is_active": {"$ne": False},
                "deleted_at": {"$exists": False}
            }).sort("created_at", -1)
            
            chat_sessions = await cursor.to_list(length=100)
            return chat_sessions
            
        except Exception as e:
            LOG.error(f"Error getting all chat sessions for user {user_id}: {e}")
            return []
    
    async def _get_new_chat_sessions(self, user_id: str, since: Optional[datetime]) -> List[Dict]:
        """Get chat sessions created or updated after a specific time"""
        try:
            db = self.get_database()
            user_object_id = ObjectId(user_id)
            
            query_filter: Dict[str, Any] = {
                "user_id": user_object_id,
                "is_active": {"$ne": False},
                "deleted_at": {"$exists": False}
            }
            
            if since:
                query_filter["$or"] = [
                    {"created_at": {"$gt": since}},
                    {"updated_at": {"$gt": since}}
                ]
            else:
                one_month_ago = datetime.utcnow() - timedelta(days=30)
                query_filter["created_at"] = {"$gte": one_month_ago}
                
                LOG.warning(
                    f"Getting new chat sessions for user {user_id} with no 'since' timestamp. "
                    f"This should only happen for incremental updates. "
                    f"Consider using force_full_update=True for first-time canvas."
                )
            
            limit = 100
            cursor = db.chat_sessions.find(query_filter).sort("created_at", -1)
            chat_sessions = await cursor.to_list(length=limit)
            
            return chat_sessions
            
        except Exception as e:
            LOG.error(f"Error getting new chat sessions for user {user_id}: {e}")
            return []
    
    async def _save_canvas(self, canvas: PhdCanvas) -> None:
        """Save canvas to database"""
        try:
            db = self.get_database()
            
            await db.phd_canvases.replace_one(
                {"_id": canvas.id},
                canvas.dict(by_alias=True),
                upsert=True
            )
            
            LOG.info(f"Saved canvas {canvas.id} to database")
            
        except Exception as e:
            LOG.error(f"Error saving canvas to database: {e}")
            raise
    
    async def delete_canvas(self, user_id: str) -> bool:
        """Delete canvas for a user"""
        try:
            db = self.get_database()
            user_object_id = ObjectId(user_id)
            
            result = await db.phd_canvases.delete_one({"user_id": user_object_id})
            
            if result.deleted_count > 0:
                LOG.info(f"Deleted canvas for user {user_id}")
                return True
            else:
                LOG.info(f"No canvas found to delete for user {user_id}")
                return False
                
        except Exception as e:
            LOG.error(f"Error deleting canvas for user {user_id}: {e}")
            return False
    
    async def get_canvas_stats(self, user_id: str) -> Dict:
        """Get statistics about the user's PhD Canvas"""
        try:
            canvas = await self.get_or_create_canvas(user_id)
            
            sections_breakdown: Dict[str, Dict] = {}
            for section_key, section in canvas.sections.items():
                sections_breakdown[section_key] = {
                    "title": section.title,
                    "insight_count": len(section.insights),
                    "priority": section.priority,
                    "last_updated": section.updated_at
                }
            
            return {
                "total_insights": canvas.total_insights,
                "total_sections": len(canvas.sections),
                "last_updated": canvas.last_updated,
                "last_chat_processed": canvas.last_chat_processed,
                "created_at": canvas.created_at,
                "auto_update": canvas.auto_update,
                "sections_breakdown": sections_breakdown
            }
            
        except Exception as e:
            LOG.error(f"Error getting canvas stats for user {user_id}: {e}")
            return {
                "total_insights": 0,
                "total_sections": 0,
                "sections_breakdown": {}
            }
    
    async def export_canvas_for_printing(self, user_id: str) -> Dict:
        """Export canvas in a format optimized for printing"""
        try:
            canvas = await self.get_or_create_canvas(user_id)
            
            sections: List[Dict] = []
            for section_key, section in canvas.sections.items():
                formatted_section = {
                    "title": section.title,
                    "description": section.description,
                    "insights": [
                        {
                            "content": insight.content,
                            "source": insight.source_persona,
                            "confidence": insight.confidence_score
                        }
                        for insight in section.insights[:5]
                    ]
                }
                sections.append(formatted_section)
            
            return {
                "user_id": str(canvas.user_id),
                "generated_at": datetime.utcnow(),
                "total_insights": canvas.total_insights,
                "last_updated": canvas.last_updated,
                "sections": sections,
                "metadata": {
                    "created_at": canvas.created_at,
                    "last_chat_processed": canvas.last_chat_processed,
                    "print_optimized": True
                }
            }
            
        except Exception as e:
            LOG.error(f"Error exporting canvas for printing for user {user_id}: {e}")
            raise
    
    async def toggle_auto_update(self, user_id: str, enabled: bool) -> bool:
        """Toggle auto-update setting for a canvas"""
        try:
            db = self.get_database()
            user_object_id = ObjectId(user_id)
            
            result = await db.phd_canvases.update_one(
                {"user_id": user_object_id},
                {"$set": {"auto_update": enabled}}
            )
            
            return result.modified_count > 0
            
        except Exception as e:
            LOG.error(f"Error toggling auto-update for user {user_id}: {e}")
            return False


def get_canvas_manager() -> "CanvasManager":
    """Get singleton instance of CanvasManager"""
    global _CANVAS_MANAGER_INSTANCE
    if _CANVAS_MANAGER_INSTANCE is None:
        _CANVAS_MANAGER_INSTANCE = CanvasManager()
    return _CANVAS_MANAGER_INSTANCE
