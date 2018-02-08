import uuid

import pymongo

from app.config import DB_USER, DB_PASSWORD, DB_URL, DB_NAME

client = pymongo.MongoClient("mongodb://"+DB_USER+":"+DB_PASSWORD+"@"+DB_URL+"/"+DB_NAME)  # defaults to port 27017

db = client.inflex


def create_user():
    user_id = uuid.uuid4().hex

    user_db = db['users']
    user_db.insert_one({
        '_id': user_id
    })

    return user_id


def insert(obj):
    return db['inflex_test'].insert_one(obj)


def get_all():
    inflex = db['inflex_test']

    return inflex.find()
