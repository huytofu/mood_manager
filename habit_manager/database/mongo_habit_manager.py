"""
MongoDB Habit Manager
====================
Manages 5 collections for habit tracking:
1. micro_habits - Individual atomic habits with scheduling and scoring
2. epic_habits - Overarching goals containing micro habits
3. dates - Daily tracking records with mood and crisis flags
4. habit_completions - Individual habit completion records
5. mood_records - Daily mood tracking with correlation data
"""

from pymongo import MongoClient
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import os

class MongoHabitManager:
    def __init__(self, connection_string: str = "mongodb://localhost:27017/"):
        self.connection_string = connection_string
        self.client = None
        self.db = None
        self.micro_habits = None
        self.epic_habits = None
        self.dates = None
        self.habit_completions = None
        self.mood_records = None
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
            
            # Initialize collections
            self.micro_habits = self.db["micro_habits"]
            self.epic_habits = self.db["epic_habits"]
            self.dates = self.db["dates"]
            self.habit_completions = self.db["habit_completions"]
            self.mood_records = self.db["mood_records"]
            
            # Create indexes for better performance
            self._create_indexes()
            
            # Create schema validation for collections
            self._create_schema_validation()
            
            self.connected = True
            print("✅ Connected to MongoDB Habit Manager successfully")
        except Exception as e:
            print(f"❌ Failed to connect to MongoDB Habit Manager: {e}")
            self.connected = False
    
    def is_connected(self) -> bool:
        return self.connected and self.client is not None
    
    def _create_indexes(self):
        """Create indexes for efficient querying if they don't already exist."""
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
            
            # Micro habits indexes
            safe_create_index(self.micro_habits, [("user_id", 1), ("status", 1)])
            safe_create_index(self.micro_habits, [("category", 1), ("habit_type", 1)])
            safe_create_index(self.micro_habits, "created_date")
            safe_create_index(self.micro_habits, "epic_habit_id")
            
            # Epic habits indexes
            safe_create_index(self.epic_habits, [("user_id", 1), ("priority", 1)])
            safe_create_index(self.epic_habits, "target_completion_date")
            safe_create_index(self.epic_habits, "created_date")
            
            # Dates indexes
            safe_create_index(self.dates, [("user_id", 1), ("date", 1)])
            safe_create_index(self.dates, [("is_crisis", 1), ("is_depressed", 1)])
            safe_create_index(self.dates, "date")
            
            # Habit completions indexes
            safe_create_index(self.habit_completions, [("user_id", 1), ("habit_id", 1), ("date", 1)])
            safe_create_index(self.habit_completions, [("habit_id", 1), ("date", 1)])
            safe_create_index(self.habit_completions, "recorded_at")
            
            # Mood records indexes
            safe_create_index(self.mood_records, [("user_id", 1), ("date", 1)])
            safe_create_index(self.mood_records, [("is_crisis", 1), ("is_depressed", 1)])
            safe_create_index(self.mood_records, "recorded_at")
            
        except Exception as e:
            print(f"Warning: Error during index creation: {e}")
    
    def _create_schema_validation(self):
        """Create schema validation for MongoDB collections to ensure data integrity."""
        try:
            # MICRO HABITS Schema Validation
            micro_habits_schema = {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["habit_id", "user_id", "name", "category", "period", "intrinsic_score", "habit_type", "status"],
                    "properties": {
                        "habit_id": {"bsonType": "string", "minLength": 1},
                        "user_id": {"bsonType": "string", "minLength": 1},
                        "name": {"bsonType": "string", "minLength": 1, "maxLength": 200},
                        "description": {"bsonType": "string", "maxLength": 1000},
                        "category": {"bsonType": "string", "enum": ["health", "productivity", "social", "financial", "mental_health", "spiritual", "creative", "other"]},
                        "period": {"bsonType": "string", "enum": ["daily", "weekly", "specific_dates"]},
                        "intrinsic_score": {"bsonType": "int", "minimum": 1, "maximum": 4},
                        "habit_type": {"bsonType": "string", "enum": ["formation", "breaking"]},
                        "status": {"bsonType": "string", "enum": ["active", "paused", "completed", "archived"]},
                        "current_streak": {"bsonType": "int", "minimum": 0},
                        "best_streak": {"bsonType": "int", "minimum": 0},
                        "total_completions": {"bsonType": "int", "minimum": 0},
                        "weekly_days": {"bsonType": "array", "items": {"bsonType": "string"}},
                        "specific_dates": {"bsonType": "array", "items": {"bsonType": "string"}},
                        "daily_timing": {"bsonType": ["string", "null"]},
                        "is_meditation": {"bsonType": "bool"},
                        "epic_habit_id": {"bsonType": ["string", "null"]},
                        "priority_within_epic": {"bsonType": ["string", "null"], "enum": ["high", "low", None]}
                    }
                }
            }
            
            # EPIC HABITS Schema Validation
            epic_habits_schema = {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["epic_id", "user_id", "name", "category", "priority", "target_completion_date"],
                    "properties": {
                        "epic_id": {"bsonType": "string", "minLength": 1},
                        "user_id": {"bsonType": "string", "minLength": 1},
                        "name": {"bsonType": "string", "minLength": 1, "maxLength": 200},
                        "description": {"bsonType": "string", "maxLength": 1000},
                        "category": {"bsonType": "string", "enum": ["health", "productivity", "social", "financial", "mental_health", "spiritual", "creative", "other"]},
                        "priority": {"bsonType": "int", "minimum": 1, "maximum": 10},
                        "target_completion_date": {"bsonType": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"},
                        "success_criteria": {"bsonType": "array", "items": {"bsonType": "string"}},
                        "current_progress": {"bsonType": "number", "minimum": 0, "maximum": 100},
                        "high_priority_micro_habits": {"bsonType": "array", "items": {"bsonType": "string"}},
                        "low_priority_micro_habits": {"bsonType": "array", "items": {"bsonType": "string"}}
                    }
                }
            }
            
            # HABIT COMPLETIONS Schema Validation
            completions_schema = {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["user_id", "habit_id", "date", "completion_score"],
                    "properties": {
                        "user_id": {"bsonType": "string", "minLength": 1},
                        "habit_id": {"bsonType": "string", "minLength": 1},
                        "date": {"bsonType": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"},
                        "completion_score": {"bsonType": "int", "minimum": 0, "maximum": 4},
                        "actual_timing": {"bsonType": ["string", "null"]},
                        "notes": {"bsonType": ["string", "null"], "maxLength": 500}
                    }
                }
            }
            
            # MOOD RECORDS Schema Validation
            mood_schema = {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["user_id", "date", "mood_score"],
                    "properties": {
                        "user_id": {"bsonType": "string", "minLength": 1},
                        "date": {"bsonType": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"},
                        "mood_score": {"bsonType": "int", "minimum": 1, "maximum": 10},
                        "is_crisis": {"bsonType": "bool"},
                        "is_depressed": {"bsonType": "bool"},
                        "notes": {"bsonType": ["string", "null"], "maxLength": 1000}
                    }
                }
            }
            
            # DATES Schema Validation
            dates_schema = {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["user_id", "date"],
                    "properties": {
                        "user_id": {"bsonType": "string", "minLength": 1},
                        "date": {"bsonType": "string", "pattern": "^[0-9]{4}-[0-9]{2}-[0-9]{2}$"},
                        "habits_scheduled": {"bsonType": "array", "items": {"bsonType": "string"}},
                        "habits_completed": {"bsonType": "array", "items": {"bsonType": "string"}},
                        "mood_score": {"bsonType": ["int", "null"], "minimum": 1, "maximum": 10},
                        "is_crisis": {"bsonType": ["bool", "null"]},
                        "is_depressed": {"bsonType": ["bool", "null"]},
                        "mood_notes": {"bsonType": ["string", "null"]}
                    }
                }
            }
            
            # Apply validation to collections
            validation_configs = [
                ("micro_habits", micro_habits_schema),
                ("epic_habits", epic_habits_schema),
                ("habit_completions", completions_schema),
                ("mood_records", mood_schema),
                ("dates", dates_schema)
            ]
            
            for collection_name, schema in validation_configs:
                try:
                    # Check if collection exists and has validation
                    collection_info = self.db.list_collections(filter={"name": collection_name})
                    collection_exists = len(list(collection_info)) > 0
                    
                    if collection_exists:
                        # Modify existing collection validation
                        self.db.command("collMod", collection_name, validator=schema, validationLevel="moderate")
                        print(f"✅ Updated schema validation for {collection_name}")
                    else:
                        # Create collection with validation
                        self.db.create_collection(collection_name, validator=schema, validationLevel="moderate")
                        print(f"✅ Created {collection_name} with schema validation")
                        
                except Exception as e:
                    print(f"⚠️ Could not set validation for {collection_name}: {e}")
            
        except Exception as e:
            print(f"Warning: Error during schema validation setup: {e}")
    
    # MICRO HABITS COLLECTION
    def create_micro_habit(self, habit_data: Dict) -> bool:
        """Create a new micro habit record."""
        if not self.is_connected():
            return False
        
        # Add creation timestamp and default status
        habit_data.update({
            "created_date": datetime.now().isoformat(),
            "status": "active",
            "current_streak": 0,
            "best_streak": 0,
            "total_completions": 0
        })
        
        try:
            self.micro_habits.insert_one(habit_data)
            return True
        except Exception as e:
            print(f"Error creating micro habit: {e}")
            return False
    
    def get_micro_habit(self, habit_id: str) -> Optional[Dict]:
        """Get micro habit by ID."""
        if not self.is_connected():
            return None
        
        return self.micro_habits.find_one({"habit_id": habit_id})
    
    def get_user_micro_habits(self, user_id: str, status: str = "active") -> List[Dict]:
        """Get all micro habits for a user."""
        if not self.is_connected():
            return []
        
        return list(self.micro_habits.find(
            {"user_id": user_id, "status": status}
        ).sort("created_date", -1))
    
    def update_micro_habit(self, habit_id: str, updates: Dict) -> bool:
        """Update micro habit data."""
        if not self.is_connected():
            return False
        
        try:
            result = self.micro_habits.update_one(
                {"habit_id": habit_id},
                {"$set": updates}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error updating micro habit: {e}")
            return False
    
    def assign_micro_to_epic(self, micro_habit_id: str, epic_habit_id: str, priority: str) -> bool:
        """Assign micro habit to epic habit."""
        if not self.is_connected():
            return False
        
        try:
            # Update micro habit with epic assignment
            micro_result = self.micro_habits.update_one(
                {"habit_id": micro_habit_id},
                {"$set": {
                    "epic_habit_id": epic_habit_id,
                    "priority_within_epic": priority,
                    "assignment_date": datetime.now().isoformat()
                }}
            )
            
            # Update epic habit with micro habit reference
            list_field = "high_priority_micro_habits" if priority == "high" else "low_priority_micro_habits"
            epic_result = self.epic_habits.update_one(
                {"epic_id": epic_habit_id},
                {"$addToSet": {list_field: micro_habit_id}}
            )
            
            return micro_result.modified_count > 0 and epic_result.modified_count > 0
        except Exception as e:
            print(f"Error assigning micro to epic: {e}")
            return False
    
    # EPIC HABITS COLLECTION
    def create_epic_habit(self, epic_data: Dict) -> bool:
        """Create a new epic habit record."""
        if not self.is_connected():
            return False
        
        # Add creation timestamp and default values
        epic_data.update({
            "created_date": datetime.now().isoformat(),
            "current_progress": 0.0,
            "high_priority_micro_habits": [],
            "low_priority_micro_habits": []
        })
        
        try:
            self.epic_habits.insert_one(epic_data)
            return True
        except Exception as e:
            print(f"Error creating epic habit: {e}")
            return False
    
    def get_epic_habit(self, epic_id: str) -> Optional[Dict]:
        """Get epic habit by ID."""
        if not self.is_connected():
            return None
        
        return self.epic_habits.find_one({"epic_id": epic_id})
    
    def get_user_epic_habits(self, user_id: str) -> List[Dict]:
        """Get all epic habits for a user, sorted by priority."""
        if not self.is_connected():
            return []
        
        return list(self.epic_habits.find(
            {"user_id": user_id}
        ).sort("priority", 1))
    
    def update_epic_progress(self, epic_id: str, progress: float) -> bool:
        """Update epic habit progress."""
        if not self.is_connected():
            return False
        
        try:
            result = self.epic_habits.update_one(
                {"epic_id": epic_id},
                {"$set": {
                    "current_progress": progress,
                    "last_progress_update": datetime.now().isoformat()
                }}
            )
            return result.modified_count > 0
        except Exception as e:
            print(f"Error updating epic progress: {e}")
            return False
    
    # DATES COLLECTION (Daily tracking)
    def create_date_record(self, user_id: str, date: str, mood_data: Dict = None) -> bool:
        """Create or update date record with mood and crisis flags."""
        if not self.is_connected():
            return False
        
        date_record = {
            "user_id": user_id,
            "date": date,
            "created_at": datetime.now().isoformat(),
            "habits_completed": [],
            "habits_scheduled": []
        }
        
        if mood_data:
            date_record.update(mood_data)
        
        try:
            # Use upsert to create or update
            self.dates.update_one(
                {"user_id": user_id, "date": date},
                {"$set": date_record},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Error creating/updating date record: {e}")
            return False
    
    def get_date_record(self, user_id: str, date: str) -> Optional[Dict]:
        """Get date record for user and date."""
        if not self.is_connected():
            return None
        
        return self.dates.find_one({"user_id": user_id, "date": date})
    
    def get_user_date_range(self, user_id: str, start_date: str, end_date: str) -> List[Dict]:
        """Get date records for user within date range."""
        if not self.is_connected():
            return []
        
        return list(self.dates.find({
            "user_id": user_id,
            "date": {"$gte": start_date, "$lte": end_date}
        }).sort("date", 1))
    
    # HABIT COMPLETIONS COLLECTION
    def record_habit_completion(self, completion_data: Dict) -> bool:
        """Record a habit completion."""
        if not self.is_connected():
            return False
        
        completion_data["recorded_at"] = datetime.now().isoformat()
        
        try:
            # Insert completion record
            self.habit_completions.insert_one(completion_data)
            
            # Update habit streak data
            self._update_habit_streak(completion_data["habit_id"], completion_data["completion_score"] > 0)
            
            return True
        except Exception as e:
            print(f"Error recording habit completion: {e}")
            return False
    
    def get_habit_completions(self, habit_id: str, start_date: str = None, end_date: str = None) -> List[Dict]:
        """Get completion records for a habit within date range."""
        if not self.is_connected():
            return []
        
        query = {"habit_id": habit_id}
        if start_date and end_date:
            query["date"] = {"$gte": start_date, "$lte": end_date}
        elif start_date:
            query["date"] = {"$gte": start_date}
        elif end_date:
            query["date"] = {"$lte": end_date}
        
        return list(self.habit_completions.find(query).sort("date", 1))
    
    def get_user_completions(self, user_id: str, start_date: str = None, end_date: str = None) -> List[Dict]:
        """Get all completion records for a user within date range."""
        if not self.is_connected():
            return []
        
        query = {"user_id": user_id}
        if start_date and end_date:
            query["date"] = {"$gte": start_date, "$lte": end_date}
        
        return list(self.habit_completions.find(query).sort("date", 1))
    
    def _update_habit_streak(self, habit_id: str, completed: bool) -> bool:
        """Update habit streak information."""
        if not completed:
            # Reset current streak
            self.micro_habits.update_one(
                {"habit_id": habit_id},
                {"$set": {"current_streak": 0}}
            )
            return True
        
        # Increment streak and total completions
        habit = self.get_micro_habit(habit_id)
        if not habit:
            return False
        
        new_streak = habit.get("current_streak", 0) + 1
        best_streak = max(new_streak, habit.get("best_streak", 0))
        total_completions = habit.get("total_completions", 0) + 1
        
        self.micro_habits.update_one(
            {"habit_id": habit_id},
            {"$set": {
                "current_streak": new_streak,
                "best_streak": best_streak,
                "total_completions": total_completions
            }}
        )
        return True
    
    # MOOD RECORDS COLLECTION
    def record_mood(self, mood_data: Dict) -> bool:
        """Record daily mood with correlation flags."""
        if not self.is_connected():
            return False
        
        mood_data["recorded_at"] = datetime.now().isoformat()
        
        try:
            # Use upsert for daily mood (one per day per user)
            self.mood_records.update_one(
                {"user_id": mood_data["user_id"], "date": mood_data["date"]},
                {"$set": mood_data},
                upsert=True
            )
            
            # Also update the date record
            self.create_date_record(mood_data["user_id"], mood_data["date"], {
                "mood_score": mood_data["mood_score"],
                "is_crisis": mood_data.get("is_crisis", False),
                "is_depressed": mood_data.get("is_depressed", False),
                "mood_notes": mood_data.get("notes", "")
            })
            
            return True
        except Exception as e:
            print(f"Error recording mood: {e}")
            return False
    
    def get_mood_records(self, user_id: str, start_date: str = None, end_date: str = None) -> List[Dict]:
        """Get mood records for user within date range."""
        if not self.is_connected():
            return []
        
        query = {"user_id": user_id}
        if start_date and end_date:
            query["date"] = {"$gte": start_date, "$lte": end_date}
        
        return list(self.mood_records.find(query).sort("date", 1))
    
    # ANALYTICS AND UTILITIES
    def get_habits_by_category(self, user_id: str, category: str) -> List[Dict]:
        """Get habits by category."""
        if not self.is_connected():
            return []
        
        return list(self.micro_habits.find({
            "user_id": user_id,
            "category": category,
            "status": "active"
        }))
    
    def get_habits_for_date(self, user_id: str, date: str) -> List[Dict]:
        """Get habits scheduled for a specific date."""
        if not self.is_connected():
            return []
        
        # This would need scheduling logic based on period/frequency
        # For now, return all active habits
        return self.get_user_micro_habits(user_id, "active")
    
    def cleanup_old_records(self, days_old: int = 90):
        """Clean up old records while preserving important data."""
        cutoff_date = (datetime.now() - timedelta(days=days_old)).isoformat()[:10]
        
        try:
            # Only clean up completion records older than cutoff
            self.habit_completions.delete_many({"date": {"$lt": cutoff_date}})
            
            # Clean up mood records older than cutoff
            self.mood_records.delete_many({"date": {"$lt": cutoff_date}})
            
            # Clean up date records older than cutoff
            self.dates.delete_many({"date": {"$lt": cutoff_date}})
            
            print(f"Cleaned up records older than {cutoff_date}")
        except Exception as e:
            print(f"Error during cleanup: {e}")
    
    def get_collection_stats(self) -> Dict:
        """Get statistics for all collections."""
        if not self.is_connected():
            return {}
        
        return {
            "micro_habits": self.micro_habits.count_documents({}),
            "epic_habits": self.epic_habits.count_documents({}),
            "dates": self.dates.count_documents({}),
            "habit_completions": self.habit_completions.count_documents({}),
            "mood_records": self.mood_records.count_documents({})
        }

# Global instance
mongo_habit_manager = MongoHabitManager() 