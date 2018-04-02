import datetime
import uuid

import pymongo

from app.config.config import DB_USER, DB_PASSWORD, DB_URL, DB_NAME

client = pymongo.MongoClient("mongodb://"+DB_USER+":"+DB_PASSWORD+"@"+DB_URL+"/"+DB_NAME)  # defaults to port 27017

db = client.inflex


def insert(obj):
    return db['inflex_test'].insert_one(obj)


def get_all():
    inflex = db['inflex_test']

    return inflex.find().sort("timestamp", pymongo.DESCENDING)


def get_image(image_id):
    inflex = db['inflex_test']

    return inflex.find({"imid": image_id}).sort("timestamp", pymongo.DESCENDING)


def image_exists(image_id):
    inflex = db['inflex_test']

    return bool(inflex.find_one({"imid": image_id}))
