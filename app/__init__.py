from flask import Flask
from pathlib import Path
import config
from .db import init_db

def create_app():
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH
    app.config["SECRET_KEY"] = "change-this-secret-key"

    Path(config.DATABASE_PATH).parent.mkdir(parents=True, exist_ok=True)
    config.PRE_DISTRIBUTION_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    init_db()

    from .routes import bp
    app.register_blueprint(bp)
    return app
