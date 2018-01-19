import os
from flask import Flask, request, redirect
from flask_mako import MakoTemplates, render_template
from werkzeug.utils import secure_filename

from app.helpers import s3

application = Flask(__name__)
mako = MakoTemplates(application)

STATIC = 'static'

application.config.from_object("app.config")


@application.route('/')
def hello_world():
    return render_template('helloworld.html', text='Welcome to api.inflex.co')


def allowed_file(filename):
    return filename.endswith(".jpg") or filename.endswith(".png") or filename.endswith(".gif")


def upload_file_to_s3(file, bucket_name, folder="upload", acl="public-read"):
    upload_path = os.path.join(folder, file.filename)
    try:
        s3.upload_fileobj(
            file,
            bucket_name,
            upload_path,
            ExtraArgs={
                "ACL": acl,
                "ContentType": file.content_type
            }
        )

    except Exception as e:
        # This is a catch all exception, edit this part to fit your needs.
        print("Something Happened: ", e)
        return e

    return "{}{}".format(application.config["S3_LOCATION"], upload_path)


@application.route('/upload', methods=["POST"])
def upload():
    if "user_file" not in request.files:
        return "No user_file key in request.files"

    file = request.files["user_file"]

    """
        These attributes are also available

        file.filename               # The actual name of the file
        file.content_type
        file.content_length
        file.mimetype

    """

    if file.filename == "":
        return "Please select a file"

    if file and allowed_file(file.filename):
        file.filename = secure_filename(file.filename)
        upload_url = upload_file_to_s3(file, application.config["S3_BUCKET"])
        bucket_files = s3.list_objects_v2(Bucket=application.config["S3_BUCKET"])
        files = ["{}{}".format(application.config["S3_LOCATION"], file['Key']) for file in bucket_files['Contents']]
        return render_template("done.html", url=upload_url, files=files)

    else:
        return redirect("/")


if __name__ == '__main__':
    application.run()
