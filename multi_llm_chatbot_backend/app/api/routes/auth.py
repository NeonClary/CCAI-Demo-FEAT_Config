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
from datetime import datetime, timedelta

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.core.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    authenticate_user,
    create_access_token,
    create_user_response,
    get_current_active_user,
    get_password_hash,
    get_user_by_email,
    verify_password,
)
from app.core.database import get_database
from app.models.user import ChatSession, Token, User, UserCreate, UserLogin, UserResponse, UserUpdate

LOG = logging.getLogger(__name__)

router = APIRouter()

@router.post("/signup", response_model=Token)
async def signup(user_data: UserCreate) -> Token:
    """Create a new user account"""
    try:
        db = get_database()
        
        existing_user = await get_user_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        hashed_password = get_password_hash(user_data.password)
        user = User(
            firstName=user_data.firstName,
            lastName=user_data.lastName,
            email=user_data.email,
            hashed_password=hashed_password,
            academicStage=user_data.academicStage,
            researchArea=user_data.researchArea,
            created_at=datetime.utcnow(),
            is_active=True
        )
        
        result = await db.users.insert_one(user.dict(by_alias=True))
        user.id = result.inserted_id
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id)}, 
            expires_delta=access_token_expires
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=create_user_response(user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        LOG.error(f"Error during signup: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create user account"
        )

@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin) -> Token:
    """Login with email and password"""
    try:
        user = await authenticate_user(user_credentials.email, user_credentials.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        db = get_database()
        await db.users.update_one(
            {"_id": user.id},
            {"$set": {"last_login": datetime.utcnow()}}
        )
        user.last_login = datetime.utcnow()
        
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user.id)}, 
            expires_delta=access_token_expires
        )
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=create_user_response(user)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        LOG.error(f"Error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_active_user)) -> UserResponse:
    """Get current user profile"""
    return create_user_response(current_user)

@router.patch("/me", response_model=UserResponse)
async def update_current_user(
    updates: UserUpdate,
    current_user: User = Depends(get_current_active_user)
) -> UserResponse:
    """Update current user profile fields"""
    try:
        db = get_database()
        update_data = {k: v for k, v in updates.dict().items() if v is not None}
        if not update_data:
            return create_user_response(current_user)

        if "email" in update_data and update_data["email"] != current_user.email:
            existing = await get_user_by_email(update_data["email"])
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already in use by another account",
                )

        await db.users.update_one(
            {"_id": current_user.id},
            {"$set": update_data}
        )
        updated = await db.users.find_one({"_id": current_user.id})
        updated_user = User(**updated)
        return create_user_response(updated_user)
    except HTTPException:
        raise
    except Exception as e:
        LOG.error(f"Error updating user: {e}")
        raise HTTPException(status_code=500, detail="Failed to update user")


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/me/password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
) -> dict:
    """Change the current user's password."""
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    if len(body.new_password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 6 characters",
        )
    try:
        db = get_database()
        new_hash = get_password_hash(body.new_password)
        await db.users.update_one(
            {"_id": current_user.id},
            {"$set": {"hashed_password": new_hash}},
        )
        return {"message": "Password updated"}
    except Exception as e:
        LOG.error(f"Error changing password for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to change password")


@router.delete("/me")
async def delete_account(current_user: User = Depends(get_current_active_user)) -> dict:
    """Permanently delete the current user's account and all associated data."""
    try:
        db = get_database()
        uid = current_user.id
        uid_str = str(uid)

        await db.user_profiles.delete_many({"user_id": uid})
        await db.onboarding_conversations.delete_many({"user_id": uid})
        await db.chat_sessions.delete_many({"user_id": uid})
        await db.phd_canvases.delete_many({"user_id": uid_str})
        await db.users.delete_one({"_id": uid})

        LOG.info(f"Deleted account and all data for user {uid}")
        return {"message": "Account deleted"}
    except Exception as e:
        LOG.error(f"Error deleting account for user {current_user.id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete account")

@router.post("/logout")
async def logout() -> dict:
    """Logout (client should discard token)"""
    return {"message": "Successfully logged out"}

@router.post("/verify-token", response_model=UserResponse)
async def verify_token(current_user: User = Depends(get_current_active_user)) -> UserResponse:
    """Verify token and return user info"""
    return create_user_response(current_user)
