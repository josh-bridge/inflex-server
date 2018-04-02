import datetime
import uuid

import pymongo

from app.config.config import DB_USER, DB_PASSWORD, DB_URL, DB_NAME

client = pymongo.MongoClient("mongodb://"+DB_USER+":"+DB_PASSWORD+"@"+DB_URL+"/"+DB_NAME)  # defaults to port 27017

db = client.inflex


def create_user():
    user_id = uuid.uuid4().hex[:10]

    user_db = db['users']
    user_db.insert_one({
        '_id': user_id,
        'created_date': datetime.datetime.now().timestamp()
    })

    return user_id


def get_all_users():
    inflex = db['users']

    return inflex.find()


def insert(obj):
    return db['inflex_test'].insert_one(obj)


def get_all():
    inflex = db['inflex_test']

    return inflex.find().sort("timestamp", pymongo.DESCENDING)


def get_all_by_user(user_id):
    inflex = db['inflex_test']

    return inflex.find({"user_id": user_id}).sort("timestamp", pymongo.DESCENDING)


def get_image(user_id, image_id):
    inflex = db['inflex_test']

    return inflex.find({"user_id": user_id, "imid": image_id}).sort("timestamp", pymongo.DESCENDING)


def user_exists(user_id):
    inflex = db['users']

    return bool(inflex.find_one({'_id': user_id}))


def image_exists(user_id, image_id):
    inflex = db['inflex_test']

    return bool(inflex.find_one({"user_id": user_id, "imid": image_id}))
