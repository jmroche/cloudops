""" This file contains tests for the different routes"""


def test_home_page(test_client):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/' page is requested (GET)
    THEN check that the response is valid
    """

    # Create a test client using the Flask application configured for testing
    response = test_client.get("/")
    assert response.status_code == 200
    assert b"Jose's Blog" in response.data
    assert b"A collection of random Cloudy stuff" in response.data


def test_register_get_page(test_client):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/register' page is requested (GET)
    THEN check that the response is valid
    """

    # Create a test client using the Flask application configured for testing
    response = test_client.get("/register")
    assert response.status_code == 200
    assert b"Register" in response.data
    assert b"Start Contributing to the Blog!" in response.data


def test_login_get_page(test_client):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/login' page is requested (GET)
    THEN check that the response is valid
    """

    # Create a test client using the Flask application configured for testing
    response = test_client.get("/login")
    assert response.status_code == 200
    assert b"Log In" in response.data
    assert b"Welcome Back!" in response.data


def test_about_get_page(test_client):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/about' page is requested (GET)
    THEN check that the response is valid
    """

    # Create a test client using the Flask application configured for testing
    response = test_client.get("/about")
    assert response.status_code == 200
    assert b"About Me" in response.data
    assert b"This is what I do." in response.data


def test_contact_get_page(test_client):
    """
    GIVEN a Flask application configured for testing
    WHEN the '/contact' page is requested (GET)
    THEN check that the response is valid
    """

    # Create a test client using the Flask application configured for testing
    response = test_client.get("/contact")
    assert response.status_code == 200
    assert b"Contact Me" in response.data
    assert b"Have questions? I have answers." in response.data


##################################################################################
# TEST SAVING USERS TO THE DB
##################################################################################
