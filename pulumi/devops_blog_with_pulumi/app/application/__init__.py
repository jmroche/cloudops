from flask import Flask
from flask_bootstrap import Bootstrap
from flask_ckeditor import CKEditor
from flask_gravatar import Gravatar
from flask_login import LoginManager
from flask_migrate import Config
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

# Create a CKEditor Object
ckeditor = CKEditor()

# Create SQLAlchemy object
db = SQLAlchemy()

# Create a Flask login manager
login_manager = LoginManager()

# Initialize a Migrate object
migrate = Migrate()

# Create a Grvatar object
gravatar = Gravatar(
    size=100,
    rating="g",
    default="wavatar",
    force_default=False,
    force_lower=False,
    use_ssl=False,
    base_url=None,
)


def init_app(config):
    """Initialize Core Applications."""
    app = Flask(__name__, instance_relative_config=False)
    # Grab the configuration from config.py depending on environment
    app.config.from_object(config)
    login_manager.init_app(app)
    Bootstrap(app)
    db.init_app(app)
    ckeditor.init_app(app)
    # Create a Gravatar Object
    # Doc: https://pythonhosted.org/Flask-Gravatar/
    gravatar.init_app(app)
    migrate.init_app(app, db)

    with app.app_context():
        from . import routes
        from . import models
        from . import forms

        # db.create_all()

        return app
