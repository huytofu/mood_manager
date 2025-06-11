"""
MongoDB Mood Manager
===================
Manages mood-related collections for mental health tracking:
1. mood_records - Daily mood tracking with crisis/depression flags
2. date_records - Daily summary records with mood information (shared with habit manager)

This module was created to separate mood recording concerns from habit tracking.
Mood manager owns mood record creation while habit manager can read for correlation analysis.
"""

from pymongo import MongoClient
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import os

# Import Pydantic validation schemas from mood manager schemas
try:
    from .schemas import (
        MoodRecordDocument,
        DateRecordDocument,
        validate_mood_data
    )
    VALIDATION_AVAILABLE = True
except ImportError:
    VALIDATION_AVAILABLE = False
    print("⚠️ Pydantic validation schemas not available - using basic validation only")
    def validate_mood_data(data: Dict) -> Dict:
        return data

class MongoMoodManager:
    def __init__(self, connection_string: str = "mongodb://localhost:27017/"):
        self.connection_string = connection_string
        self.client = None
        self.db = None
        self.mood_records = None
        self.dates = None  # Shared with habit manager
        self.connected = False
        
        self._connect()
    
    def _connect(self):
        """Establish MongoDB connection and initialize collections."""
        try:
            self.client = MongoClient(
                host=self.connection_string,
                username=os.getenv("MONGO_USERNAME"),
                password=os.getenv("MONGO_PASSWORD"),
                database=os.getenv("MONGO_DATABASE")
            )
            self.db = self.client[os.getenv("MONGO_DATABASE")]
            
            # Test connection
            self.client.admin.command('ismaster')
            
            # Initialize mood-related collections
            self.mood_records = self.db["mood_records"]
            self.dates = self.db["dates"]  # Shared collection with habit manager
            
            # Create indexes for better performance
            self._create_indexes()
            
            # Create schema validation for mood collections
            self._create_schema_validation()
            
            self.connected = True
            print("✅ Connected to MongoDB Mood Manager successfully")
        except Exception as e:
            print(f"❌ Failed to connect to MongoDB Mood Manager: {e}")
            self.connected = False
    
    def is_connected(self) -> bool:
        return self.connected and self.client is not None
    
    def _create_indexes(self):
        """Create indexes for efficient mood querying if they don't already exist."""
        try:
            def safe_create_index(collection, index_spec, index_name=None):
                try:
                    existing_indexes = collection.list_indexes()
                    existing_names = [idx["name"] for idx in existing_indexes]
                    
                    if index_name and index_name in existing_names:
                        return
                    
                    if isinstance(index_spec, list):
                        collection.create_index(index_spec)
                    else:
                        collection.create_index(index_spec)
                except Exception as e:
                    print(f"Warning: Could not create index {index_spec}: {e}")
            
            # Mood records indexes
            safe_create_index(self.mood_records, [("user_id", 1), ("date", 1)])
            safe_create_index(self.mood_records, [("is_crisis", 1), ("is_depressed", 1)])
            safe_create_index(self.mood_records, "recorded_at")
            safe_create_index(self.mood_records, "mood_score")
            
            # Dates indexes (shared collection)
            safe_create_index(self.dates, [("user_id", 1), ("date", 1)])
            safe_create_index(self.dates, [("is_crisis", 1), ("is_depressed", 1)])
            safe_create_index(self.dates, "date")
            
        except Exception as e:
            print(f"Warning: Error during mood manager index creation: {e}")
    
    def _create_schema_validation(self):
        """Create schema validation for mood-related MongoDB collections."""
        try:
            # MOOD RECORDS Schema Validation
            mood_records_schema = {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["user_id", "date", "mood_score"],
                    "properties": {
                        "user_id": {"bsonType": "string", "minLength": 1},
                        "date": {"bsonType": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"},
                        "mood_score": {"bsonType": "int", "minimum": 1, "maximum": 10},
                        "is_crisis": {"bsonType": "bool"},
                        "is_depressed": {"bsonType": "bool"},
                        "notes": {"bsonType": ["string", "null"], "maxLength": 1000},
                        "recorded_at": {"bsonType": "string"}
                    }
                }
            }
            
            # DATE RECORDS Schema Validation (shared with habit manager)
            date_records_schema = {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["user_id", "date"],
                    "properties": {
                        "user_id": {"bsonType": "string", "minLength": 1},
                        "date": {"bsonType": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"},
                        "habits_scheduled": {"bsonType": "array", "items": {"bsonType": "string"}},
                        "habits_completed": {"bsonType": "array", "items": {"bsonType": "string"}},
                        "mood_score": {"bsonType": ["int", "null"], "minimum": 1, "maximum": 10},
                        "is_crisis": {"bsonType": "bool"},
                        "is_depressed": {"bsonType": "bool"},
                        "mood_notes": {"bsonType": ["string", "null"]},
                        "created_at": {"bsonType": "string"}
                    }
                }
            }
            
            # Apply validation to collections
            try:
                self.db.command("collMod", "mood_records", validator=mood_records_schema)
                print("✅ Mood records schema validation created")
            except Exception as e:
                print(f"⚠️ Could not create mood_records schema validation: {e}")
            
            try:
                self.db.command("collMod", "dates", validator=date_records_schema)
                print("✅ Date records schema validation updated for mood manager")
            except Exception as e:
                print(f"⚠️ Could not update dates schema validation: {e}")
                
        except Exception as e:
            print(f"Warning: Error during mood manager schema validation setup: {e}")
    
    # MOOD RECORDS COLLECTION
    def record_mood(self, mood_data: Dict) -> bool:
        """Record daily mood with crisis/depression flags and validation."""
        if not self.is_connected():
            return False
        
        try:
            # Apply Pydantic validation if available
            if VALIDATION_AVAILABLE:
                try:
                    # Validate using MoodRecordDocument schema
                    mood_record = MoodRecordDocument(**mood_data)
                    validated_data = mood_record.dict()
                    print(f"✅ MoodRecordDocument validation passed for mood record: {mood_data.get('date', 'unknown')}")
                except ValueError as e:
                    print(f"❌ MoodRecordDocument validation failed: {e}")
                    return False
            else:
                # Fallback: Add basic timestamp
                validated_data = mood_data.copy()
                validated_data["recorded_at"] = datetime.now().isoformat()
            
            # Use upsert for daily mood (one per day per user)
            self.mood_records.update_one(
                {"user_id": validated_data["user_id"], "date": validated_data["date"]},
                {"$set": validated_data},
                upsert=True
            )
            
            # Also update the shared date record
            self.update_date_record(validated_data["user_id"], validated_data["date"], {
                "mood_score": validated_data["mood_score"],
                "is_crisis": validated_data.get("is_crisis", False),
                "is_depressed": validated_data.get("is_depressed", False),
                "mood_notes": validated_data.get("notes", "")
            })
            
            return True
        except Exception as e:
            print(f"Error recording mood: {e}")
            return False
    
    def get_mood_records(self, user_id: str, time_period: str = "monthly", start_date: str = None, end_date: str = None) -> List[Dict]:
        """Get mood records for user within time period."""
        if not self.is_connected():
            return []
        
        try:
            # Handle time period calculation
            if time_period == "weekly" and not (start_date and end_date):
                end_date = datetime.now().strftime("%Y-%m-%d")
                start_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            elif time_period == "monthly" and not (start_date and end_date):
                end_date = datetime.now().strftime("%Y-%m-%d")
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            
            query = {"user_id": user_id}
            if start_date and end_date:
                query["date"] = {"$gte": start_date, "$lte": end_date}
            elif start_date:
                query["date"] = {"$gte": start_date}
            elif end_date:
                query["date"] = {"$lte": end_date}
            
            return list(self.mood_records.find(query).sort("date", 1))
        except Exception as e:
            print(f"Error getting mood records: {e}")
            return []
    
    def get_recent_mood_trend(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """Get recent mood trend analysis."""
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        mood_records = self.get_mood_records(user_id, "custom", start_date, end_date)
        
        if not mood_records:
            return {"trend": "no_data", "average": 5, "crisis_days": 0}
        
        mood_scores = [r.get("mood_score", 5) for r in mood_records]
        avg_mood = sum(mood_scores) / len(mood_scores)
        crisis_days = len([r for r in mood_records if r.get("is_crisis", False)])
        
        # Calculate trend
        if len(mood_scores) >= 3:
            recent = sum(mood_scores[-3:]) / 3
            earlier = sum(mood_scores[:-3]) / len(mood_scores[:-3]) if len(mood_scores) > 3 else avg_mood
            if recent > earlier + 0.5:
                trend = "improving"
            elif recent < earlier - 0.5:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "insufficient_data"
        
        return {
            "trend": trend,
            "average": round(avg_mood, 2),
            "crisis_days": crisis_days,
            "total_days": len(mood_records)
        }
    
    # DATE RECORDS COLLECTION (Shared with habit manager)
    def update_date_record(self, user_id: str, date: str, mood_data: Dict) -> bool:
        """Update date record with mood information."""
        if not self.is_connected():
            return False
        
        try:
            # Update existing date record or create new one
            update_data = {
                "mood_score": mood_data.get("mood_score"),
                "is_crisis": mood_data.get("is_crisis", False),
                "is_depressed": mood_data.get("is_depressed", False),
                "mood_notes": mood_data.get("mood_notes", "")
            }
            
            # Prepare full record for potential creation with DateRecordDocument validation
            full_record_data = {
                "user_id": user_id,
                "date": date,
                "habits_scheduled": [],
                "habits_completed": [],
                "created_at": datetime.now().isoformat(),
                **update_data
            }
            
            # Validate using DateRecordDocument schema if available
            if VALIDATION_AVAILABLE:
                try:
                    date_record = DateRecordDocument(**full_record_data)
                    validated_insert_data = date_record.dict()
                    print(f"✅ DateRecordDocument validation passed for date record: {date}")
                except ValueError as e:
                    print(f"❌ DateRecordDocument validation failed: {e}")
                    # Fall back to basic validation
                    validated_insert_data = full_record_data
            else:
                validated_insert_data = full_record_data
            
            # Use upsert to create record if it doesn't exist
            self.dates.update_one(
                {"user_id": user_id, "date": date},
                {
                    "$set": update_data,
                    "$setOnInsert": {k: v for k, v in validated_insert_data.items() if k not in update_data}
                },
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error updating date record: {e}")
            return False
    
    def get_date_record(self, user_id: str, date: str) -> Optional[Dict]:
        """Get date record for specific date."""
        if not self.is_connected():
            return None
        
        return self.dates.find_one({"user_id": user_id, "date": date})
    
    # ANALYTICS AND UTILITIES
    def get_mood_stats(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive mood statistics."""
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        mood_records = self.get_mood_records(user_id, "custom", start_date, end_date)
        
        if not mood_records:
            return {"error": "No mood data found"}
        
        mood_scores = [r.get("mood_score", 5) for r in mood_records]
        
        return {
            "total_records": len(mood_records),
            "average_mood": round(sum(mood_scores) / len(mood_scores), 2),
            "min_mood": min(mood_scores),
            "max_mood": max(mood_scores),
            "crisis_days": len([r for r in mood_records if r.get("is_crisis", False)]),
            "depressed_days": len([r for r in mood_records if r.get("is_depressed", False)]),
            "low_mood_days": len([s for s in mood_scores if s <= 3]),
            "high_mood_days": len([s for s in mood_scores if s >= 8]),
            "analysis_period": f"{start_date} to {end_date}"
        }
    
    def cleanup_old_mood_records(self, days_old: int = 90):
        """Clean up old mood records while preserving important data."""
        cutoff_date = (datetime.now() - timedelta(days=days_old)).isoformat()[:10]
        
        try:
            # Only clean up mood records older than cutoff (keep crisis records longer)
            result = self.mood_records.delete_many({
                "date": {"$lt": cutoff_date},
                "is_crisis": {"$ne": True}  # Keep crisis records
            })
            
            print(f"Cleaned up {result.deleted_count} old mood records (kept crisis records)")
        except Exception as e:
            print(f"Error during mood cleanup: {e}")
    
    def get_collection_stats(self) -> Dict:
        """Get statistics for mood-related collections."""
        if not self.is_connected():
            return {}
        
        return {
            "mood_records": self.mood_records.count_documents({}),
            "dates_with_mood": self.dates.count_documents({"mood_score": {"$exists": True}}),
            "crisis_records": self.mood_records.count_documents({"is_crisis": True}),
            "depression_records": self.mood_records.count_documents({"is_depressed": True})
        }

# Global instance
mongo_mood_manager = MongoMoodManager() 