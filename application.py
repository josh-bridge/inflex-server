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


@application.route('/users/<string:user_id>/images', methods=["GET"])
def get_history(user_id):
    request_uid = create_uuid()

    if not db.user_exists(user_id):
        return jsonify(_uuid=request_uid, error="Invalid user"), status.HTTP_404_NOT_FOUND

    all = db.get_all_by_user(user_id)

    posts = []

    for post in all:
        post['_id'] = str(post['_id'])
        posts.append(post)

    return jsonify(posts)


@application.route('/users/<string:user_id>/images', methods=["POST"])
def upload(user_id):
    request_uid = create_uuid()
    print(str(request_uid))

    if not db.user_exists(user_id):
        return jsonify(_uuid=request_uid, error="Invalid user"), status.HTTP_404_NOT_FOUND

    try:
        validate_upload(request)
    except Exception:
        return jsonify(_uuid=request_uid, error="Invalid file"), status.HTTP_400_BAD_REQUEST

    original_uploaded_url = upload_original(request.files["user_file"])

    imid = create_uuid().hex[:5]

    do_filter(imid, original_uploaded_url, request_uid, user_id)

    return jsonify(im_url="http://localhost:8080/users/" + user_id + "/images/" + imid)


def do_filter(imid, original_uploaded_url, request_uid, user_id):
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
        'user_id': user_id,
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


@application.route('/users/<string:user_id>/images/<string:image_id>', methods=["GET"])
def get_image(user_id, image_id):
    request_uid = create_uuid()

    if not db.user_exists(user_id) \
            or not db.image_exists(user_id, image_id):
        return jsonify(_uuid=request_uid, error="Invalid"), status.HTTP_404_NOT_FOUND

    imgs = get_img_from_db(user_id, image_id)

    return jsonify(user_response(imgs))


def get_img_from_db(user_id, image_id):
    db_image = db.get_image(user_id, image_id)
    images = []
    for image in db_image:
        image['_id'] = str(image['_id'])
        images.append(image)

    return images


@application.route('/users/<string:user_id>/images/<string:image_id>/<string:filter_id>')
def get_image_filter(user_id, image_id, filter_id):
    request_uid = create_uuid()

    if not db.user_exists(user_id) \
            or not db.image_exists(user_id, image_id):
        return jsonify(_uuid=request_uid, error="Invalid"), status.HTTP_404_NOT_FOUND

    imgs = get_img_from_db(user_id, image_id)

    for filt in imgs[0]['filtered']['all']:
        if filt['id'] == filter_id:
            return filt

    return jsonify(_uuid=request_uid, error="Invalid filter"), status.HTTP_404_NOT_FOUND


@application.route('/users/<string:user_id>/images/<string:image_id>_<string:filter_id>_<string:size>.jpg')
def get_image_filter_full(user_id, image_id, filter_id, size):
    request_uid = create_uuid()

    if not db.user_exists(user_id) \
            or not db.image_exists(user_id, image_id):
        return jsonify(_uuid=request_uid, error="Invalid"), status.HTTP_404_NOT_FOUND

    img_json = get_img_from_db(user_id, image_id)
    filter_obj = get_filter(filter_id)
    if filter_obj is not None and len(img_json) > 0:
        filtered = do_filter_from_img_json(filter_obj, img_json[0])

        img = get_img_for_response(filtered, size)
        if img is not None:
            return image_response(img)

    return jsonify(_uuid=request_uid, error="Invalid filter"), status.HTTP_404_NOT_FOUND


def get_img_for_response(filtered, size):
    if size == "f":
        return filtered.as_bytes()
    if size == "p":
        return filtered.preview_bytes()
    if size == "t":
        return filtered.thumb_bytes()

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


@application.route('/users/', methods=["POST"])
def user_id():
    return jsonify(user_id=db.create_user())


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
