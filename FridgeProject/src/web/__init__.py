from flask import Flask
from src.database import db_session

def create_app():
    app = Flask(__name__)

    from src.web.routes import main
    app.register_blueprint(main)

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db_session.remove()

    return app
