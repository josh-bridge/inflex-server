import datetime

from flask import Flask, request, jsonify, Response
from flask_api import status
from flask_mako import MakoTemplates, render_template
from flask_cors import CORS

from app import db
from app.analysis.dominant_colours import analyze
from app.filters.base_filter import Filterable, BaseFilter
from app.recommend.recommender import get_recommendation
from app.tasks import tasks
from app.web.util import create_uuid, validate_upload, upload_original, upload_object

SIZES = ['full', 'preview', 'thumb']

application = Flask(__name__)
CORS(application)
mako = MakoTemplates(application)

STATIC = 'static'

application.config.from_object("app.config.config")


def format_response(response):
    response.pop('_id')

    return response


@application.route('/')
def hello_world():
    return render_template('helloworld.html', text='Welcome to api.inflex.co')


@application.route('/images', methods=["POST"])
def upload():
    request_uid = create_uuid()
    print(str(request_uid))

    try:
        validate_upload(request)
    except Exception:
        return jsonify(_uuid=request_uid, error="Invalid file"), status.HTTP_400_BAD_REQUEST

    original_uploaded_url = upload_original(request.files["user_file"])

    imid = create_uuid().hex[:5]

    do_filter(imid, original_uploaded_url, request_uid)

    return jsonify(im_url="http://localhost:8080/images/" + imid), 201, {'location': "/images/" + imid}


def do_filter(imid, original_uploaded_url, request_uid):
    # api_response = google_vision_api(original_uploaded_url, application.config["VISION_API"])
    # dom_colour, dom_score = get_dominant_colour(api_response)
    image = Filterable.from_url(original_uploaded_url)
    vibrant, dominant = analyze(image)
    filtered_images = filter_all(image)
    response = {
        'original_url': original_uploaded_url,
        'filtered': {
            'recommended': get_recommendation(),
            'all': filtered_images
        },
        'properties': {
            'vibrant_colour': vibrant,
            'dominant_colours': dominant
        },
        'timestamp': datetime.datetime.now().timestamp(),
        '_uuid': str(request_uid),
        'imid': imid
    }

    tasks.insert.delay(response)


def filter_all(image):
    filters = BaseFilter.__subclasses__()
    filtered_images = []

    for current_filter in filters:
        filtered_image = current_filter.apply(image)
        filtered_images.append({
            'id': current_filter.id(),
            'name': current_filter.name(),
            'thumb_url': upload_object(filtered_image.square_thumb_bytes()),
            'preview_url': upload_object(filtered_image.preview_bytes())
        })

    return filtered_images


@application.route('/images/<string:image_id>', methods=["GET"])
def get_image(image_id):
    request_uid = create_uuid()

    if not db.image_exists(image_id):
        return jsonify(_uuid=request_uid, error="Invalid"), status.HTTP_404_NOT_FOUND

    imgs = get_img_from_db(image_id)

    return jsonify(user_response(imgs))


def get_img_from_db(image_id):
    db_image = db.get_image(image_id)
    images = []
    for image in db_image:
        image['_id'] = str(image['_id'])
        images.append(image)

    return images


@application.route('/images/<string:image_id>-<string:filter_id>-<string:size>.jpg')
def get_image_filter_full(image_id, filter_id, size):
    request_uid = create_uuid()

    if not db.image_exists(image_id):
        return jsonify(_uuid=request_uid, error="Invalid"), status.HTTP_404_NOT_FOUND

    img_json = get_img_from_db(image_id)
    filter_obj = get_filter(filter_id)
    if filter_obj is not None and len(img_json) > 0:
        filter_json = get_filter_json(img_json, filter_id)

        if size == "f":
            filtered = do_filter_from_img_json(filter_obj, img_json[0])
            return image_response(filtered.as_bytes())

        if size == "p":
            return image_response(Filterable.from_url(filter_json['preview_url']).as_bytes())

        if size == "t":
            return image_response(Filterable.from_url(filter_json['thumb_url']).as_bytes())

    return jsonify(_uuid=request_uid, error="Invalid filter"), status.HTTP_404_NOT_FOUND


def get_filter_json(img_json, filter_id):
    for filter_json in img_json[0]['filtered']['all']:
        if filter_json['id'] == filter_id:
            return filter_json

    return None


def image_response(image):
    return Response(image.getvalue(), mimetype='image/jpeg')


def do_filter_from_img_json(filter_class, img_json):
    image = Filterable.from_url(img_json['original_url'])
    filtered = filter_class.apply(image)
    return filtered


def get_filter(filter_id):
    filters = BaseFilter.__subclasses__()

    for filter_class in filters:
        if filter_class.id() == filter_id:
            return filter_class

    return None


def user_response(imgs):
    return {key: imgs[0][key] for key in ['original_url', 'filtered']}


@application.route('/show', methods=["GET"])
def show_db():
    all = db.get_all()
    posts = []

    for post in all:
        post['_id'] = str(post['_id'])
        posts.append(post)

    return jsonify(posts)


# @application.route('/celery/test', methods=['GET'])
# def celery_test():
#     return jsonify(task_id=hello.delay().task_id)
#
#
# @application.route('/celery/results/<string:task_id>', methods=['GET'])
# def celery_test_result(task_id):
#     from app.tasks import app
#
#     return jsonify(task_id=task_id, result=AsyncResult(task_id, app=app).get(timeout=2))


if __name__ == '__main__':
    application.run(port=8080)
