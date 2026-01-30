"""
Announcements endpoints for the High School Management System API
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List, Optional
from datetime import datetime
from bson import ObjectId
from ..database import announcements_collection

router = APIRouter(
    prefix="/announcements",
    tags=["announcements"]
)


@router.get("")
def get_announcements(include_expired: bool = Query(False)) -> List[Dict[str, Any]]:
    """Get all active announcements, optionally including expired ones"""
    now = datetime.now().isoformat()
    
    if include_expired:
        announcements = list(announcements_collection.find({}))
    else:
        announcements = list(announcements_collection.find({
            "expiration_date": {"$gt": now}
        }))
    
    # Convert ObjectId to string for JSON serialization
    for announcement in announcements:
        if "_id" in announcement:
            announcement["_id"] = str(announcement["_id"])
    
    return announcements


@router.get("/active")
def get_active_announcements() -> List[Dict[str, Any]]:
    """Get all active announcements (started and not expired)"""
    now = datetime.now().isoformat()
    
    announcements = list(announcements_collection.find({
        "$and": [
            {
                "$or": [
                    {"start_date": {"$lte": now}},
                    {"start_date": {"$exists": False}},
                    {"start_date": None},
                ]
            },
            {"expiration_date": {"$gt": now}}
        ]
    }))
    
    # Convert ObjectId to string for JSON serialization
    for announcement in announcements:
        if "_id" in announcement:
            announcement["_id"] = str(announcement["_id"])
    
    return announcements


@router.post("")
def create_announcement(
    title: str,
    message: str,
    expiration_date: str,
    start_date: Optional[str] = None
) -> Dict[str, Any]:
    """Create a new announcement (admin only)"""
    
    if not start_date:
        start_date = datetime.now().isoformat()
    
    # Validate dates
    try:
        start_dt = datetime.fromisoformat(start_date)
        expiry_dt = datetime.fromisoformat(expiration_date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format")
    
    if expiry_dt <= start_dt:
        raise HTTPException(
            status_code=400,
            detail="Expiration date must be after start date"
        )
    
    new_announcement = {
        "title": title,
        "message": message,
        "start_date": start_date,
        "expiration_date": expiration_date,
        "created_at": datetime.now().isoformat()
    }
    
    result = announcements_collection.insert_one(new_announcement)
    new_announcement["_id"] = str(result.inserted_id)
    
    return new_announcement


@router.put("/{announcement_id}")
def update_announcement(
    announcement_id: str,
    title: Optional[str] = None,
    message: Optional[str] = None,
    expiration_date: Optional[str] = None,
    start_date: Optional[str] = None
) -> Dict[str, Any]:
    """Update an announcement (admin only)"""
    
    try:
        obj_id = ObjectId(announcement_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    # Build update dictionary
    update_data = {}
    if title is not None:
        update_data["title"] = title
    if message is not None:
        update_data["message"] = message
    if expiration_date is not None:
        update_data["expiration_date"] = expiration_date
    if start_date is not None:
        update_data["start_date"] = start_date
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    # Validate dates if provided
    if "start_date" in update_data or "expiration_date" in update_data:
        announcement = announcements_collection.find_one({"_id": obj_id})
        if not announcement:
            raise HTTPException(status_code=404, detail="Announcement not found")
        
        start_dt_str = update_data.get("start_date", announcement.get("start_date"))
        expiry_dt_str = update_data.get("expiration_date", announcement.get("expiration_date"))
        
        try:
            start_dt = datetime.fromisoformat(start_dt_str)
            expiry_dt = datetime.fromisoformat(expiry_dt_str)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
        
        if expiry_dt <= start_dt:
            raise HTTPException(
                status_code=400,
                detail="Expiration date must be after start date"
            )
    
    result = announcements_collection.update_one(
        {"_id": obj_id},
        {"$set": update_data}
    )
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    # Return updated announcement
    updated_announcement = announcements_collection.find_one({"_id": obj_id})
    updated_announcement["_id"] = str(updated_announcement["_id"])
    
    return updated_announcement


@router.delete("/{announcement_id}")
def delete_announcement(announcement_id: str) -> Dict[str, str]:
    """Delete an announcement (admin only)"""
    
    try:
        obj_id = ObjectId(announcement_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid announcement ID")
    
    result = announcements_collection.delete_one({"_id": obj_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    return {"message": "Announcement deleted successfully"}
