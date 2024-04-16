from datetime import date


""" This file contains tests for the models.py"""


def test_new_user_with_fixture(new_user):
    """
    GIVEN a User model
    WHEN a new User is created
    THEN check the email and password_hashed fields are defined correctly
    """
    assert new_user.email == "test_user_1@gmail.com"
    assert new_user.password == "FlaskIsAwesome"
    assert new_user.name == "Test User 1"


def test_new_blog_post_with_fixture(new_post):
    """
    GIVEN a BlogPost model
    WHEN a new Blog Post is created
    THEN check the title, subtitle, body, img_url, author and date fields are defined correctly
    """
    assert new_post.title == "Test Post"
    assert new_post.subtitle == "This is a test post"
    assert new_post.body == "A body for the the test post."
    assert (
        new_post.img_url
        == "https://images.unsplash.com/photo-1509869175650-a1d97972541a?ixlib=rb-1.2.1&ixid=MnwxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8&auto=format&fit=crop&w=2670&q=80"
    )
    assert new_post.date == date.today().strftime("%B %d, %Y")


def test_new_comment_to_post_with_fixture(new_comment):
    """
    GIVEN a Comment model
    WHEN a new Comment is created
    THEN check the comment text, blog post id, and author id fields are defined correctly
    """
    assert new_comment.comment == "This is a new comment"
    assert new_comment.blog_post_id == 1
    assert new_comment.author_id == 1
