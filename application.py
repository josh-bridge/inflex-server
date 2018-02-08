import datetime
import os
import uuid
from io import BytesIO

import cv2 as cv
import numpy
import requests
from PIL import Image, ImageEnhance
from flask import Flask, request, jsonify, redirect
from flask_api import status
from flask_mako import MakoTemplates, render_template

from app import db
from app.helpers import s3

application = Flask(__name__)
mako = MakoTemplates(application)

STATIC = 'static'

application.config.from_object("app.config")


def allowed_file(file):
    return file \
           and file.filename.lower().endswith(".jpg") \
           or file.filename.lower().endswith(".png")


def upload_fileobj_to_s3(file_bytes, filename, content_type, bucket_name, folder="upload", acl="public-read"):
    upload_path = os.path.join(folder, filename)
    try:
        s3.upload_fileobj(
            file_bytes,
            bucket_name,
            upload_path,
            ExtraArgs={
                "ACL": acl,
                "ContentType": content_type
            }
        )

    except Exception as e:
        # This is a catch all exception, edit this part to fit your needs.
        print("Something Happened: ", e)
        return e

    return "{}{}".format(application.config["S3_LOCATION"], upload_path)


def validate_upload(request):
    if "user_file" not in request.files:
        raise Exception("No user_file key in request.files")

    file = request.files["user_file"]

    if file.filename == "":
        raise Exception("No file supplied")

    if not allowed_file(file):
        raise Exception("Invalid file type")

    # if file.content_length == 0:
    #     raise Exception("Empty file")


def random_file_name(extension):
    return str(uuid.uuid4().int) + extension.lower()


def create_uuid():
    return uuid.uuid4()


def upload_object(filtered_image, original_file, folder="filtered"):
    filtered_image.seek(0)  # Without this line it fails
    newfile_name = random_file_name(os.path.splitext(original_file.filename)[1])
    new_url = upload_fileobj_to_s3(
        filtered_image,
        newfile_name,
        original_file.mimetype,
        application.config["S3_BUCKET"],
        folder
    )

    return new_url


def upload_original(uploaded_file):
    new_filename = random_file_name(os.path.splitext(uploaded_file.filename)[1])
    upload_url = upload_fileobj_to_s3(
        uploaded_file,
        new_filename,
        uploaded_file.mimetype,
        application.config["S3_BUCKET"],
        "uploads"
    )

    return upload_url


def filter_image(upload_url):
    response = requests.get(upload_url, stream=True)
    response.raw.decode_content = True
    plain_image = Image.open(response.raw)

    return filter_black_and_white(plain_image, response.headers['Content-Type'])


def dominant_colour(dominant_colours, height=100, width=100):
    # response = requests.get(upload_url, stream=True)
    # response.raw.decode_content = True
    # plain_image = Image.open(response.raw)

    # open_cv_image = numpy.array(plain_image)

    blank_image = numpy.zeros((height, width, 3), numpy.uint8)

    colour = dominant_colours['colors'][0]['color']
    blank_image[:, :] = (colour['blue'], colour['green'], colour['red'])

    # # Convert RGB to BGR
    # open_cv_image = open_cv_image[:, :, ::-1].copy()
    # open_cv_image = cv.rectangle(open_cv_image, (250, 30), (450, 200), (0, 255, 0), 5)
    new_plain = Image.fromarray(blank_image)

    return get_img_object(new_plain, 'image/jpeg')


def filter_black_and_white(plain_image, mime_type):
    filtered = ImageEnhance.Color(plain_image).enhance(0.0)

    return get_img_object(filtered, mime_type)


def get_img_object(image, mime_type):
    file_obj = BytesIO()

    image.save(file_obj, mime_type.split('/')[1])

    return file_obj


def format_response(response):
    response.pop('_id')

    return response


def google_vision_api(image_url):
    img_request = {
        "requests": [
            {
                "image": {
                    "source": {"imageUri": image_url}
                },
                "features": [
                    {"type": "IMAGE_PROPERTIES", "maxResults": 1}
                ]
            }
        ]
    }

    return requests.post(url=application.config["VISION_API"], json=img_request).json()


@application.route('/')
def hello_world():
    return render_template('helloworld.html', text='Welcome to api.inflex.co')


@application.route('/upload', methods=["POST"])
def upload():
    request_uid = create_uuid()

    try:
        validate_upload(request)
    except Exception:
        return jsonify(_uuid=request_uid, error="Invalid file"), status.HTTP_400_BAD_REQUEST

    original_file = request.files["user_file"]

    original_uploaded_url = upload_original(original_file)

    api_response = google_vision_api(original_uploaded_url)['responses'][0]

    dominant_colour_image = dominant_colour(api_response['imagePropertiesAnnotation']['dominantColors'])
    dominant_colour_url = upload_object(dominant_colour_image, original_file, "sample/colour")
    dominant_colour_val = get_dominant_colour(api_response)

    filtered_image = filter_image(original_uploaded_url)
    filtered_uploaded_url = upload_object(filtered_image, original_file)

    response = {
        '_uuid': str(request_uid),
        'timestamp': datetime.datetime.now().timestamp(),
        'original_url': original_uploaded_url,
        'filtered': [
            {
                'black_and_white': {
                    'url': filtered_uploaded_url
                }
            }
        ],
        'dominant_colour': {
            'value': {
                'red': dominant_colour_val['red'],
                'green': dominant_colour_val['green'],
                'blue': dominant_colour_val['blue']
            },
            'sample_url': dominant_colour_url
        }
        # 'properties': api_response
    }

    db.insert(response)

    return jsonify(format_response(response))


def get_dominant_colour(api_response):
    # dominant_colour_val = [0]['color']
    # test = api_response['imagePropertiesAnnotation']['dominantColors']['colors']
    #
    # print(test)
    #
    # sorted_test = sorted(test, key=lambda x: test[x]['score'])
    # print(sorted_test)
    #
    # return sorted_test[len(sorted_test)]

    return api_response['imagePropertiesAnnotation']['dominantColors']['colors'][0]['color']


@application.route('/show', methods=["GET"])
def show_db():
    all = db.get_all()
    posts = []

    for post in all:
        post['_id'] = str(post['_id'])
        posts.append(post)

    return jsonify(posts)


@application.route('/new_id', methods=["GET"])
def user_id():
    random = uuid.uuid4().hex

    return jsonify(user_id=random)


if __name__ == '__main__':
    application.run()
