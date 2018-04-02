import os
import uuid
from io import BytesIO

import numpy as np
import requests
from PIL import Image

from app.config import config
from app.helpers import s3


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

    return "{}{}".format(config.S3_LOCATION, upload_path)


def upload_original(uploaded_file):
    upload_url = upload_fileobj_to_s3(
        uploaded_file,
        random_file_name(os.path.splitext(uploaded_file.filename)[1]),
        uploaded_file.mimetype,
        config.S3_BUCKET,
        "originals"
    )

    return upload_url


def upload_object(filtered_image, folder="filtered"):
    filtered_image.seek(0)  # Without this line it fails
    new_url = upload_fileobj_to_s3(
        filtered_image,
        random_file_name(),
        'image/jpeg',
        config.S3_BUCKET,
        folder
    )

    return new_url


def validate_upload(request):
    # data = request.form["user_file"]
    # bytes64 = re.sub('^data:image/.+;base64,', '', data)
    # io = BytesIO(base64.b64decode(bytes64))
    # file = FileStorage(stream=io, filename="test.jpg", content_type="image/jpeg", name="test2.jpg")

    if "user_file" not in request.files:
        raise Exception("No user_file key in request.files")

    file = request.files["user_file"]

    if file.filename == "":
        raise Exception("No file supplied")

    if not allowed_file(file):
        raise Exception("Invalid file type")

    # return file

    # if file.content_length == 0:
    #     raise Exception("Empty file")


def allowed_file(file):
    return file \
           and file.filename.lower().endswith(".jpg") \
           or file.filename.lower().endswith(".png")


def create_uuid():
    return uuid.uuid4()


def get_dominant_colour(api_response):
    colour = api_response['imagePropertiesAnnotation']['dominantColors']['colors'][0]

    return colour['color'], colour['score']


def upload_colour_sample(dom_colour):
    return upload_object(colour_sample(dom_colour), "sample/colour")


def colour_sample(colour, height=100, width=100):
    blank_image = blank_array(height, width)

    blank_image[:, :] = (colour['red'], colour['green'], colour['blue'])

    return get_img_object(Image.fromarray(blank_image), 'image/jpeg')


def get_img_object(image, mime_type):
    file_obj = BytesIO()

    image.save(file_obj, mime_type.split('/')[1])

    return file_obj


def random_file_name(ext='.jpg'):
    return str(uuid.uuid4().hex[:10]) + ext


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

    return requests.post(url=config.VISION_API, json=img_request).json()['responses'][0]


def blank_array(height, width):
    return np.zeros((height, width, 3), np.uint8)

