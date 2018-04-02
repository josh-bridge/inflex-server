import datetime

from celery import Celery

from app.analysis.dominant_colours import analyze
from app.filters.base_filter import Filterable, BaseFilter
from app.web.util import upload_object

app = Celery('app', backend='rpc://', broker='pyamqp://test:testpassword@localhost:5672/testvhost')


# from celery.schedules import crontab
# from celery.task import periodic_task

@app.task
def hello():
    return 'hello world'


# @periodic_task(run_every=(crontab(minute='*/1')), name="test", ignore_result=True)
# def some_task():
#     print("test")


@app.task
def insert(obj):
    from app import db

    db.insert(obj)

# {key: response[key] for key in ['original_url', 'filtered']}


# @app.task
# def do_filter(imid, original_uploaded_url, request_uid, user_id):
#     image = Filterable.from_url(original_uploaded_url)
#     vibrant, dominant = analyze(image)
#     # filtered_images = filter_all(image)
#     response = {
#         'original_url': original_uploaded_url,
#         # 'filtered': filtered_images,
#         # 'properties': {
#         #     'vibrant_colour': vibrant,
#         #     'dominant_colours': dominant
#         # },
#         'user_id': user_id,
#         'timestamp': datetime.datetime.now().timestamp(),
#         '_uuid': str(request_uid),
#         'imid': imid
#     }
#     # from app import db
#     # db.insert(response)
#
#
# def filter_all(image):
#     filters = BaseFilter.__subclasses__()
#     filtered_images = []
#
#     for current_filter in filters:
#         filtered_image = current_filter.apply(image)
#         filtered_images.append({
#             'id': current_filter.id(),
#             'name': current_filter.name(),
#             'thumb_url': upload_object(filtered_image.thumb_bytes())
#         })
#
#     return filtered_images
