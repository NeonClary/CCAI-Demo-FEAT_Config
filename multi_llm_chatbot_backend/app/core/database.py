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

import os
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)

class Database:
    client: AsyncIOMotorClient = None
    database = None

db = Database()

async def connect_to_mongo():
    """Create database connection"""
    try:
        settings = get_settings()

        # Connection string: config.yaml → env var fallback (handled by Pydantic validator)
        mongo_url = settings.mongodb.connection_string
        if not mongo_url:
            # Last-resort fallback to raw env var (backwards compat)
            mongo_url = os.getenv("MONGODB_CONNECTION_STRING", "")
        if not mongo_url:
            raise ValueError(
                "MongoDB connection string not set. "
                "Provide it in config.yaml (mongodb.connection_string) "
                "or as the MONGODB_CONNECTION_STRING environment variable."
            )

        db_name = settings.mongodb.database_name
        
        db.client = AsyncIOMotorClient(mongo_url)
        db.database = db.client[db_name]
        
        # Test connection
        await db.client.admin.command('ping')

        logger.info(f"Successfully connected to MongoDB database: {db_name}")
        
        # Create indexes for better performance
        await create_indexes()
        try:
            from app.core.canvas_database import setup_canvas_collections
            await setup_canvas_collections(db.database)  # Pass db directly
            logger.info("Canvas database initialization completed")
        except Exception as canvas_error:
            logger.error(f"Canvas database initialization failed: {canvas_error}")
        
    except ConnectionFailure as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error connecting to MongoDB: {e}")
        raise

async def close_mongo_connection():
    """Close database connection"""
    if db.client:
        db.client.close()
        logger.info("Disconnected from MongoDB")

async def create_indexes():
    """Create database indexes for performance"""
    try:
        # Index for users collection
        await db.database.users.create_index("email", unique=True)
        await db.database.users.create_index("created_at")
        
        # Indexes for chat_sessions collection
        await db.database.chat_sessions.create_index("user_id")
        await db.database.chat_sessions.create_index("created_at")
        await db.database.chat_sessions.create_index([("user_id", 1), ("created_at", -1)])
        
        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.warning(f"Error creating indexes: {e}")

def get_database():
    """Get database instance"""
    return db.database
