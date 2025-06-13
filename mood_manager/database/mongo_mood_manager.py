"""
MongoDB Mood Manager
===================
Manages mood-related collections for mental health tracking:
1. dates - Daily summary records with mood information (shared with habit manager)
2. emotion_records - Specific emotion tracking with granular detail

This module provides a clean architecture for mood data storage using only two collections:
- DateRecordDocument for daily mood scores and diary notes
- EmotionRecordDocument for specific emotion tracking with context
"""

from pymongo import MongoClient
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
import os

# Import Pydantic validation schemas from mood manager schemas
try:
    from .schemas import (
        DateRecordDocument,
        EmotionRecordDocument,
        validate_date_record_data,
        validate_emotion_record_data
    )
    VALIDATION_AVAILABLE = True
except ImportError:
    VALIDATION_AVAILABLE = False
    print("⚠️ Pydantic validation schemas not available - using basic validation only")
    def validate_date_record_data(data: Dict) -> Dict:
        return data
    def validate_emotion_record_data(data: Dict) -> Dict:
        return data

class MongoMoodManager:
    def __init__(self, connection_string: str = "mongodb://localhost:27017/"):
        self.connection_string = connection_string
        self.client = None
        self.db = None
        self.dates = None  # Shared with habit manager
        self.emotion_records = None  # New collection for specific emotion tracking
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
            self.dates = self.db["dates"]  # Shared collection with habit manager
            self.emotion_records = self.db["emotion_records"]  # New collection for specific emotion tracking
            
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
            
            # Dates indexes (shared collection)
            safe_create_index(self.dates, [("user_id", 1), ("date", 1)])
            safe_create_index(self.dates, [("is_crisis", 1), ("is_depressed", 1)])
            safe_create_index(self.dates, "date")
            
            # Emotion records indexes
            safe_create_index(self.emotion_records, [("user_id", 1), ("date", 1)])
            safe_create_index(self.emotion_records, [("user_id", 1), ("emotion_type", 1)])
            safe_create_index(self.emotion_records, [("emotion_type", 1), ("emotion_score", 1)])
            safe_create_index(self.emotion_records, "created_at")
            
        except Exception as e:
            print(f"Warning: Error during mood manager index creation: {e}")
    
    def _create_schema_validation(self):
        """Create schema validation for mood-related MongoDB collections."""
        try:
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
            
            # EMOTION RECORDS Schema Validation
            emotion_records_schema = {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["user_id", "date", "emotion_type", "emotion_score"],
                    "properties": {
                        "user_id": {"bsonType": "string", "minLength": 1},
                        "date": {"bsonType": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"},
                        "emotion_type": {"bsonType": "string", "minLength": 1, "maxLength": 50},
                        "emotion_score": {"bsonType": "int", "minimum": 1, "maximum": 10},
                        "emotion_notes": {"bsonType": ["string", "null"], "maxLength": 1500},
                        "triggers": {"bsonType": "array", "items": {"bsonType": "string"}},
                        "context": {"bsonType": ["object", "null"]},
                        "created_at": {"bsonType": "string"},
                        "updated_at": {"bsonType": ["string", "null"]}
                    }
                }
            }
            
            # Apply validation to collections
            try:
                self.db.command("collMod", "dates", validator=date_records_schema)
                print("✅ Date records schema validation updated for mood manager")
            except Exception as e:
                print(f"⚠️ Could not update dates schema validation: {e}")
                
            try:
                self.db.command("collMod", "emotion_records", validator=emotion_records_schema)
                print("✅ Emotion records schema validation created")
            except Exception as e:
                print(f"⚠️ Could not create emotion_records schema validation: {e}")
                
        except Exception as e:
            print(f"Warning: Error during mood manager schema validation setup: {e}")

    # =============================================================================
    # DATE RECORDS COLLECTION (Primary mood recording method)
    # =============================================================================
    
    def update_date_record(self, user_id: str, date: str, mood_data: Dict) -> bool:
        """Update date record with mood data."""
        if not self.is_connected():
            return False
        
        try:
            # Prepare update data
            update_data = {
                "user_id": user_id,
                "date": date,
                "updated_at": datetime.now().isoformat()
            }
            
            # Add mood-specific fields
            if "mood_score" in mood_data:
                update_data["mood_score"] = mood_data["mood_score"]
            if "is_crisis" in mood_data:
                update_data["is_crisis"] = mood_data["is_crisis"]
            if "is_depressed" in mood_data:
                update_data["is_depressed"] = mood_data["is_depressed"]
            if "mood_notes" in mood_data:
                update_data["mood_notes"] = mood_data["mood_notes"]
            
            # Use upsert to create or update
            result = self.dates.update_one(
                {"user_id": user_id, "date": date},
                {
                    "$set": update_data,
                    "$setOnInsert": {
                        "created_at": datetime.now().isoformat(),
                        "habits_scheduled": [],
                        "habits_completed": []
                    }
                },
                upsert=True
            )
            
            return True
        except Exception as e:
            print(f"Error updating date record: {e}")
            return False
    
    def get_date_record(self, user_id: str, date: str) -> Optional[Dict]:
        """Get single date record."""
        if not self.is_connected():
            return None
        return self.dates.find_one({"user_id": user_id, "date": date})
    
    def get_mood_stats(self, user_id: str, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """Get mood statistics from date records within a date range."""
        if not self.is_connected():
            return {}
        
        try:
            # If no dates provided, default to last 30 days
            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
            if not start_date:
                start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
            
            date_records = self.get_date_records_range(user_id, start_date, end_date)
            
            # Filter records with mood data
            mood_records = [r for r in date_records if r.get("mood_score") is not None]
            
            if not mood_records:
                return {"error": "No mood data found"}
            
            mood_scores = [r["mood_score"] for r in mood_records]
            
            return {
                "total_records": len(mood_records),
                "average_mood": sum(mood_scores) / len(mood_scores),
                "min_mood": min(mood_scores),
                "max_mood": max(mood_scores),
                "crisis_days": len([r for r in mood_records if r.get("is_crisis", False)]),
                "depressed_days": len([r for r in mood_records if r.get("is_depressed", False)]),
                "mood_records": mood_records,  # Include the actual records
                "start_date": start_date,
                "end_date": end_date,
            }
        except Exception as e:
            print(f"Error getting mood stats: {e}")
            return {}

    def get_collection_stats(self) -> Dict:
        """Get statistics about all collections."""
        if not self.is_connected():
            return {}
        
        try:
            return {
                "dates": self.dates.count_documents({}),
                "emotion_records": self.emotion_records.count_documents({}),
                "crisis_records": self.dates.count_documents({"is_crisis": True}),
                "depression_records": self.dates.count_documents({"is_depressed": True}),
            }
        except Exception as e:
            print(f"Error getting collection stats: {e}")
            return {}

    def record_daily_mood_with_notes(self, user_id: str, date: str, mood_score: int = None, 
                                   mood_notes: str = None, is_crisis: bool = False, 
                                   is_depressed: bool = False) -> bool:
        """
        Record daily mood with notes using the enhanced DateRecordDocument structure.
        This replaces the old mood_records pattern.
        """
        if not self.is_connected():
            return False
        
        try:
            # Prepare record data
            record_data = {
                "user_id": user_id,
                "date": date,
                "is_crisis": is_crisis,
                "is_depressed": is_depressed,
                "updated_at": datetime.now().isoformat()
            }
            
            # Add optional fields
            if mood_score is not None:
                record_data["mood_score"] = mood_score
            if mood_notes:
                record_data["mood_notes"] = mood_notes
            
            # Apply validation if available
            if VALIDATION_AVAILABLE:
                try:
                    validated_data = validate_date_record_data(record_data)
                    record_data.update(validated_data)
                except Exception as e:
                    print(f"Validation warning: {e}")
            
            # Use upsert to update existing or create new
            result = self.dates.update_one(
                {"user_id": user_id, "date": date},
                {
                    "$set": record_data,
                    "$setOnInsert": {
                        "created_at": datetime.now().isoformat(),
                        "habits_scheduled": [],
                        "habits_completed": []
                    }
                },
                upsert=True
            )
            
            return True
            
        except Exception as e:
            print(f"Error recording daily mood with notes: {e}")
            return False

    def get_date_records_range(self, user_id: str, start_date: str = None, end_date: str = None, limit: int = 50) -> List[Dict]:
        """Get date records within a range."""
        if not self.is_connected():
            return []
        
        try:
            query = {"user_id": user_id}
            
            if start_date and end_date:
                query["date"] = {"$gte": start_date, "$lte": end_date}
            elif start_date:
                query["date"] = {"$gte": start_date}
            elif end_date:
                query["date"] = {"$lte": end_date}
            
            return list(self.dates.find(query).sort("date", -1).limit(limit))
        except Exception as e:
            print(f"Error getting date records range: {e}")
            return []

    # =============================================================================
    # EMOTION RECORDS COLLECTION
    # =============================================================================

    def record_daily_emotion_with_notes(self, user_id: str, date: str, emotion_type: str, 
                                       emotion_score: int, emotion_notes: str = None,
                                       triggers: List[str] = None, context: Dict[str, Any] = None) -> bool:
        """
        Record daily emotion with score and optional notes/context.
        Consolidated function that handles both emotion recording and note updates.
        
        Args:
            user_id: User identifier
            date: Date in YYYY-MM-DD format
            emotion_type: Type of emotion (e.g., 'anxiety', 'joy', 'anger')
            emotion_score: Emotion intensity score 1-10
            emotion_notes: Optional emotion-specific notes/context
            triggers: Optional list of triggers that caused this emotion
            context: Optional additional context data
            
        Returns:
            bool: Success status
        """
        if not self.is_connected():
            return False
        
        try:
            # Prepare emotion record data
            emotion_data = {
                "user_id": user_id,
                "date": date,
                "emotion_type": emotion_type.lower().strip(),
                "emotion_score": emotion_score,
                "updated_at": datetime.now().isoformat()
            }
            
            # Add optional fields
            if emotion_notes:
                emotion_data["emotion_notes"] = emotion_notes
            if triggers:
                emotion_data["triggers"] = triggers if isinstance(triggers, list) else [triggers]
            if context:
                emotion_data["context"] = context
            
            # Apply validation if available
            if VALIDATION_AVAILABLE:
                try:
                    validated_data = validate_emotion_record_data(emotion_data)
                    emotion_data.update(validated_data)
                except Exception as e:
                    print(f"Emotion validation warning: {e}")
            
            # Use upsert to create or update emotion record
            result = self.emotion_records.update_one(
                {
                    "user_id": user_id,
                    "date": date,
                    "emotion_type": emotion_type.lower().strip()
                },
                {
                    "$set": emotion_data,
                    "$setOnInsert": {
                        "created_at": datetime.now().isoformat()
                    }
                },
                upsert=True
            )
            
            return True
            
        except Exception as e:
            print(f"Error recording daily emotion with notes: {e}")
            return False

    def get_emotion_records(self, user_id: str, emotion_types: List[str] = None, 
                          start_date: str = None, end_date: str = None, limit: int = 100) -> List[Dict]:
        """Get emotion records with optional filtering."""
        if not self.is_connected():
            return []
        
        try:
            query = {"user_id": user_id}
            
            if emotion_types:
                query["emotion_type"] = {"$in": [e.lower().strip() for e in emotion_types]}
            
            if start_date and end_date:
                query["date"] = {"$gte": start_date, "$lte": end_date}
            elif start_date:
                query["date"] = {"$gte": start_date}
            elif end_date:
                query["date"] = {"$lte": end_date}
            
            return list(self.emotion_records.find(query).sort("date", -1).limit(limit))
        except Exception as e:
            print(f"Error getting emotion records: {e}")
            return []

    def get_emotion_stats(self, user_id: str, emotion_type: str = None, days: int = 30) -> Dict[str, Any]:
        """Get emotion statistics."""
        if not self.is_connected():
            return {}
        
        try:
            end_date = datetime.now().strftime("%Y-%m-%d")
            start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            
            emotion_types = [emotion_type] if emotion_type else None
            emotion_records = self.get_emotion_records(user_id, emotion_types, start_date, end_date)
            
            if not emotion_records:
                return {"error": "No emotion data found"}
            
            # Calculate statistics
            emotion_scores = [r.get("emotion_score", 5) for r in emotion_records]
            emotion_breakdown = {}
            
            for record in emotion_records:
                emotion = record.get("emotion_type", "unknown")
                if emotion not in emotion_breakdown:
                    emotion_breakdown[emotion] = {"count": 0, "total_score": 0, "avg_score": 0}
                
                emotion_breakdown[emotion]["count"] += 1
                emotion_breakdown[emotion]["total_score"] += record.get("emotion_score", 5)
            
            # Calculate averages
            for emotion, data in emotion_breakdown.items():
                data["avg_score"] = data["total_score"] / data["count"]
            
            return {
                "total_records": len(emotion_records),
                "average_intensity": sum(emotion_scores) / len(emotion_scores),
                "min_intensity": min(emotion_scores),
                "max_intensity": max(emotion_scores),
                "emotion_breakdown": emotion_breakdown,
                "date_range": f"{start_date} to {end_date}",
                "common_triggers": self._get_common_triggers(emotion_records)
            }
        except Exception as e:
            print(f"Error getting emotion stats: {e}")
            return {}

    def _get_common_triggers(self, emotion_records: List[Dict]) -> List[str]:
        """Extract common triggers from emotion records."""
        trigger_counts = {}
        
        for record in emotion_records:
            triggers = record.get("triggers", [])
            for trigger in triggers:
                if trigger:
                    trigger_counts[trigger] = trigger_counts.get(trigger, 0) + 1
        
        # Return top 5 triggers
        return sorted(trigger_counts.keys(), key=trigger_counts.get, reverse=True)[:5]

# Global instance
mongo_mood_manager = MongoMoodManager() 