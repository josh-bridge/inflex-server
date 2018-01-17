from flask import Flask
from flask_mako import MakoTemplates, render_template

application = Flask(__name__)
mako = MakoTemplates(application)

STATIC = 'static'


@application.route('/')
def hello_world():
    return render_template('helloworld.html', text='Welcome to api.inflex.co')


if __name__ == '__main__':
    application.run()
