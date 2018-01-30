from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy(session_options={"autoflush": False, "autocommit": False, "expire_on_commit": False})

def create_app():

    from .app import main
    from .settings import STATIC_ROOT

    app = Flask(__name__, static_url_path=STATIC_ROOT)
    app.register_blueprint(main)

    SQLALCHEMY_DATABASE_URI = 'sqlite:///./db.sqlite'
    app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)

    return app

