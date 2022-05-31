"""Flask configuration."""
from os import environ
from os import listdir
from os import path

# from dotenv import load_dotenv

# Get the DB details from ENV VARS passed to the container

db_user = environ.get("DB_USERNAME")
db_password = environ.get("DB_PASSWORD")
db_hostname = environ.get("DB_HOSTNAME")
db_name = environ.get("DB_NAME")
db_port = 3306

# if environ.get("ON_CLOUD"):

#     basedir = path.abspath("/mnt/secrets")
#     files = listdir(basedir)

#     for file in files:
#         if file == "dbhostname":
#             with open(path.abspath(path.join(basedir, file)), "r") as fr:
#                 db_hostname = fr.read().strip()

#     db_uri = f"mysql+pymysql://{db_user}:{db_password}@infrastacktestrdsstackf4d892f-auroramysqld0c29ccd-89gj83tnfyky.cluster-c0zjezn9agfn.us-east-1.rds.amazonaws.com/flaskblogtest"
#     print(f"DB_URI: {db_uri}")

# Construct the db conenction string to be used by flask-migrate
db_uri = f"mysql+pymysql://{db_user}:{db_password}@{db_hostname}/{db_name}"
# print(f"DB_URI: {db_uri}")


class Config:
    """Base config."""

    SECRET_KEY = environ.get("SECRET_KEY")
    # SESSION_COOKIE_NAME = environ.get('SESSION_COOKIE_NAME')
    STATIC_FOLDER = "static"
    TEMPLATES_FOLDER = "templates"
    SQLALCHEMY_TRACK_MODIFICATIONS = "FALSE"
    CKEDITOR_PKG_TYPE = "standard"


class ProdConfig(Config):
    FLASK_ENV = "production"
    DEBUG = False
    TESTING = False
    SQLALCHEMY_DATABASE_URI = environ.get("PROD_DATABASE_URI", db_uri)
    # SQLALCHEMY_DATABASE_URI = db_uri


class DevConfig(Config):
    FLASK_ENV = "development"
    DEBUG = True
    TESTING = True
    # SQLALCHEMY_DATABASE_URI = environ.get("DEV_DATABASE_URI")
    SQLALCHEMY_DATABASE_URI = "sqlite:///blog.db"


class TestConfig(Config):
    FLASK_ENV = "testing"
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = environ.get("TEST_DATABASE_URI", db_uri)
    # SQLALCHEMY_DATABASE_URI = db_uri
