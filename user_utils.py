from pymongo import MongoClient

def get_user_tier(user_id):
    # get user tier from database
    db = MongoClient.db
    user = db.users.find_one({"user_id": user_id})
    return user["tier"]

def get_user_subscription_status(user_id):
    # get user subscription status from database
    db = MongoClient.db
    user = db.users.find_one({"user_id": user_id})
    return user["subscription_status"]

def get_user_voice_path(user_id):
    # Get user voice from database
    # Return file path
    db = MongoClient.db
    user = db.users.find_one({"user_id": user_id})
    voice_path = user["voice_path"]
    return voice_path
