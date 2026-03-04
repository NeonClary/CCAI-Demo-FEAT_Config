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

from motor.motor_asyncio import AsyncIOMotorDatabase

LOG = logging.getLogger(__name__)

async def setup_canvas_collections(db: AsyncIOMotorDatabase) -> None:
    """Setup MongoDB collections and indexes for PhD Canvas"""
    try:
        collection = db.phd_canvases

        await collection.create_index("user_id")
        LOG.info("Created index on user_id")

        await collection.create_index("last_updated", background=True)
        LOG.info("Created index on last_updated")

        await collection.create_index([("user_id", 1), ("last_updated", -1)])
        LOG.info("Created compound index on user_id and last_updated")

        await collection.create_index([("user_id", 1), ("created_at", -1)])
        LOG.info("Created compound index on user_id and created_at")

        await collection.create_index(
            "created_at",
            expireAfterSeconds=63072000
        )
        LOG.info("Created TTL index for canvas cleanup")

        LOG.info("PhD Canvas database setup completed successfully")

    except Exception as e:
        LOG.error(f"Error setting up canvas collections: {e}")
        raise

async def cleanup_old_canvas_data(db: AsyncIOMotorDatabase) -> None:
    """Cleanup old or orphaned canvas data (maintenance function)"""
    try:
        pipeline = [
            {
                "$lookup": {
                    "from": "users",
                    "localField": "user_id",
                    "foreignField": "_id",
                    "as": "user_data"
                }
            },
            {
                "$match": {
                    "user_data": {"$size": 0}
                }
            }
        ]

        orphaned_canvases = await db.phd_canvases.aggregate(pipeline).to_list(length=100)

        if orphaned_canvases:
            orphaned_ids = [canvas["_id"] for canvas in orphaned_canvases]
            result = await db.phd_canvases.delete_many({"_id": {"$in": orphaned_ids}})
            LOG.info(f"Cleaned up {result.deleted_count} orphaned canvas records")
        else:
            LOG.info("No orphaned canvas records found")

    except Exception as e:
        LOG.error(f"Error during canvas cleanup: {e}")
