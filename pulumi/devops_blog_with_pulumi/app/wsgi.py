import os

import config
from application import init_app

# Check in what environment we are running on
# This is passed as env variable
# If no ENV set, then assume we are in development mode.

app_env = os.environ.get("APP_ENV", "dev")

if app_env == "production" or app_env == "prod":
    app_config = config.ProdConfig

elif app_env == "test":
    app_config = config.TestConfig

else:
    app_config = config.DevConfig


app = init_app(app_config)

if __name__ == "__main__":
    app.run(host="0.0.0.0")
