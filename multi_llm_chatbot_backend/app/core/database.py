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
import logging

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure

from app.config import get_settings

LOG = logging.getLogger(__name__)


class Database:
    """Thin wrapper around an async MongoDB connection."""

    client: AsyncIOMotorClient = None
    database = None


db = Database()


async def connect_to_mongo() -> None:
    """
    Create the database connection and initialise indexes.
    """
    try:
        settings = get_settings()

        mongo_url: str = settings.mongodb.connection_string
        if not mongo_url:
            mongo_url = os.getenv("MONGODB_CONNECTION_STRING", "")
        if not mongo_url:
            raise ValueError(
                "MongoDB connection string not set. "
                "Provide it in config.yaml (mongodb.connection_string) "
                "or as the MONGODB_CONNECTION_STRING environment variable."
            )

        db_name: str = settings.mongodb.database_name

        db.client = AsyncIOMotorClient(mongo_url)
        db.database = db.client[db_name]

        await db.client.admin.command("ping")

        LOG.info(f"Successfully connected to MongoDB database: {db_name}")

        await create_indexes()
        try:
            from app.core.canvas_database import setup_canvas_collections

            await setup_canvas_collections(db.database)
            LOG.info("Canvas database initialization completed")
        except Exception as canvas_error:
            LOG.error(f"Canvas database initialization failed: {canvas_error}")

    except ConnectionFailure as e:
        LOG.error(f"Failed to connect to MongoDB: {e}")
        raise
    except Exception as e:
        LOG.error(f"Unexpected error connecting to MongoDB: {e}")
        raise


async def close_mongo_connection() -> None:
    """
    Close the database connection.
    """
    if db.client:
        db.client.close()
        LOG.info("Disconnected from MongoDB")


async def create_indexes() -> None:
    """
    Create database indexes for performance.
    """
    try:
        await db.database.users.create_index("email", unique=True)
        await db.database.users.create_index("created_at")

        await db.database.chat_sessions.create_index("user_id")
        await db.database.chat_sessions.create_index("created_at")
        await db.database.chat_sessions.create_index(
            [("user_id", 1), ("created_at", -1)]
        )

        await db.database.user_profiles.create_index("user_id", unique=True)

        await db.database.professor_ratings.create_index("name")
        await db.database.professor_ratings.create_index("department")
        await db.database.professor_ratings.create_index(
            [("name", 1), ("department", 1)]
        )

        await db.database.courses.create_index("course_code")
        await db.database.courses.create_index("instructor")
        await db.database.courses.create_index("semester")
        await db.database.courses.create_index(
            [("course_code", 1), ("semester", 1)]
        )

        LOG.info("Database indexes created successfully")
    except Exception as e:
        LOG.warning(f"Error creating indexes: {e}")


def get_database():
    """
    Get the database instance.

    :returns: The active MongoDB database object.
    """
    return db.database
