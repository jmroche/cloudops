from datetime import date

import pytest
from _pytest import config
from flask import app

from app.application import db
from app.application import init_app
from app.application.models import BlogPost
from app.application.models import Comment
from app.application.models import User
from app.config import TestConfig


@pytest.fixture(scope="session")
def test_client():
    flask_app = init_app(TestConfig)

    # Create a test client using the Flask application configured for testing
    with flask_app.test_client() as testing_client:
        # Establish an application context
        with flask_app.app_context():
            db.create_all()
            user1 = User(
                email="test_user_1@gmail.com",
                name="Test User 1",
                password="FlaskIsAwesome",
            )
            user2 = User(
                email="test_user_2@gmail.com",
                name="Test User 2",
                password="FlaskIsAwesome",
            )
            db.session.add(user1)
            db.session.add(user2)
            db.session.commit()

            yield testing_client  # this is where the testing happens!\
            db.session.remove()
            db.drop_all()


@pytest.fixture(scope="module")
def new_user():
    user = User(
        email="test_user_1@gmail.com", name="Test User 1", password="FlaskIsAwesome"
    )
    return user


@pytest.fixture(scope="module")
def new_post():
    new_post = BlogPost(
        title="Test Post",
        subtitle="This is a test post",
        body="A body for the the test post.",
        img_url="https://images.unsplash.com/photo-1509869175650-a1d97972541a?ixlib=rb-1.2.1&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=2670&q=80",
        date=date.today().strftime("%B %d, %Y"),
    )
    return new_post


@pytest.fixture(scope="module")
def new_comment():
    new_comment = Comment(
        comment="This is a new comment",
        blog_post_id=1,
        author_id=1,
    )
    return new_comment
