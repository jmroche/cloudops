import hashlib
import os
from datetime import date
from functools import wraps

from flask import abort
from flask import current_app as app
from flask import flash
from flask import Flask
from flask import make_response
from flask import redirect
from flask import render_template
from flask import url_for
from flask.globals import request
from flask_login import current_user
from flask_login import login_required
from flask_login import login_user
from flask_login import LoginManager
from flask_login import logout_user
from flask_login import UserMixin
from werkzeug.security import check_password_hash
from werkzeug.security import generate_password_hash

from . import db
from . import login_manager
from .forms import CommentForm
from .forms import CreatePostForm
from .forms import LoginUserForm
from .forms import RegisterForm
from .models import BlogPost
from .models import Comment
from .models import User

# Global varibales for 'url_for' function:

app_env = os.getenv("APP_ENV")
_EXTERNAL = True if app_env == "production" else None
_SCHEME = "https" if app_env == "production" else None


def email_hashing(email: str) -> str:
    """Provide an email address and return and MD5 hashed string.

    Args:
        email (str): Email address to be hashed.

    Returns:
        str: MD5 hashed string.
    """
    # strip blanks, convert to lower case and encode in utf-8
    # encode as md5 and format as hex
    return hashlib.md5(email.strip().lower().encode("utf-8")).hexdigest()


def add_post_view(post_name: str) -> bool:
    """Given a post name, increase its view count by 1 every time is viewed.

    Args:
        post_name (str): The post name to be fetched and updated.

    Returns:
        bool: Returns True or False if the post was succesfully modified.
    """

    try:
        # Fetch the post and increase its view count by 1
        post = BlogPost.query.filter_by(blog_title_str=post_name).first()
        post.post_views += 1
        db.session.commit()
        return True
    except:
        return False


# Admin check decorator function
# This decorator will throw a 403 if the user is not authenticated
# or if authenticated is not the admin user
def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.id != 1:
            abort(403)
        return func(*args, **kwargs)

    return wrapper


# create login user loader, required by Flask
@login_manager.user_loader
def load_user(user):
    return db.session.query(User).get(user)


@app.route("/")
def get_all_posts():
    # Check if the user is logged in to show his/her posts
    # If not logged in don't show draft posts
    if current_user.is_authenticated:
        user_id = current_user.id
        posts = BlogPost.query.filter_by(author_id=user_id).all()
    else:
        posts = BlogPost.query.filter_by(is_draft=False).all()
    return render_template("index.html", all_posts=posts)


@app.route("/register", methods=["GET", "POST"])
def register():
    register_form = RegisterForm()

    if register_form.validate_on_submit():
        email = request.form.get("email")
        name = request.form.get("name")
        hashed_and_salted_password = generate_password_hash(
            password=request.form.get("password"), salt_length=8, method="pbkdf2:sha256"
        )

        # Check if the email already exists in the DB
        check_email_in_db = db.session.query(User).filter_by(email=email).first()
        if check_email_in_db:
            print("email exist in the DB")
            flash("User/Email already exist", category="danger")
            return redirect(url_for("login"))
        else:
            new_user = User(email=email, name=name, password=hashed_and_salted_password)
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            flash(f"User: {new_user.name} registered succesfully!", category="success")
            return redirect(url_for("login", _external=_EXTERNAL, _scheme=_SCHEME))

    return render_template("register.html", form=register_form)


@app.route("/login", methods=["GET", "POST"])
def login():
    login_form = LoginUserForm()

    if login_form.validate_on_submit():
        email = request.form.get("email")
        user = db.session.query(User).filter_by(email=email).first()
        if user:
            password_match = check_password_hash(
                user.password, request.form.get("password")
            )
            if password_match:
                login_user(user)
                return redirect(
                    url_for("get_all_posts", _external=_EXTERNAL, _scheme=_SCHEME)
                )
            else:  # wrong username or password
                flash("Ivalid username or password", category="danger")
                return redirect(url_for("login", _external=_EXTERNAL, _scheme=_SCHEME))
        else:  # user doesn'r exist in DB
            flash("User not found, please register", category="danger")
            return redirect(url_for("register", _external=_EXTERNAL, _scheme=_SCHEME))

    return render_template("login.html", form=login_form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("get_all_posts", _external=_EXTERNAL, _scheme=_SCHEME))


@app.route("/post/<string:post_name>", methods=["GET", "POST"])
def show_post(post_name):
    comment_form = CommentForm()
    try:
        get_post = BlogPost.query.filter_by(blog_title_str=post_name).first()

        if get_post.is_draft:
            if not current_user.is_authenticated:
                abort(404)
            elif current_user.id != get_post.author_id:
                abort(404)
            requested_post = get_post
        else:
            requested_post = get_post
            add_post_view(post_name)

        # Check if user is authenticated to setup the gravatar
        # if not use a sample email to show a default gravatar
        if current_user.is_authenticated:
            hashed_user_email = email_hashing(
                db.session.query(User).get(current_user.id).email
            )

        else:
            hashed_user_email = "sample@email.com"

        if comment_form.is_submitted():
            if current_user.is_authenticated:
                new_comment = Comment(
                    comment=comment_form.body.data,
                    blog_post_id=requested_post.id,
                    author_id=current_user.id,
                )
                db.session.add(new_comment)
                db.session.commit()
                comment_form.body.data = ""  # reset the body form
                return render_template(
                    "post.html",
                    post=requested_post,
                    form=comment_form,
                    comments=Comment.query.filter_by(
                        blog_post_id=requested_post.id
                    ).all(),
                    email=hashed_user_email,
                )
            else:
                flash("You need to login or register to comment", category="danger")
                return redirect(url_for("login", _external=_EXTERNAL, _scheme=_SCHEME))

        return render_template(
            "post.html",
            post=requested_post,
            form=comment_form,
            comments=Comment.query.filter_by(blog_post_id=requested_post.id).all(),
            email=hashed_user_email,
        )
    except:
        abort(404)


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact")
def contact():
    return render_template("contact.html")


@app.route("/new-post", methods=["GET", "POST"])
@admin_required
def add_new_post():
    form = CreatePostForm()
    if form.validate_on_submit():
        # Check if either save draft or publish button is pressed
        # then set the is_draft flag appropriately in the DB
        is_draft_value = True if form.save_draft.data else False
        is_draft_value = False if form.publish.data else True
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            # use the current logged in user_id as the author id
            author_id=current_user.id,
            date=date.today().strftime("%B %d, %Y"),
            blog_title_str=form.title.data.replace(" ", "-").lower(),
            is_draft=is_draft_value,
        )
        is_draft_value = ""
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts", _external=_EXTERNAL, _scheme=_SCHEME))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<string:post_name>", methods=["GET", "POST"])
@admin_required
def edit_post(post_name):
    post = BlogPost.query.filter_by(blog_title_str=post_name).first()
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        # author=post.author,
        body=post.body,
    )
    if edit_form.validate_on_submit():
        # Check if either save draft or publish button is pressed
        # then set the is_draft flag appropriately in the DB
        is_draft_value = True if edit_form.save_draft.data else False
        is_draft_value = False if edit_form.publish.data else True
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author_id = current_user.id
        post.body = edit_form.body.data
        post.blog_title_str = edit_form.title.data.replace(" ", "-").lower()
        post.is_draft = is_draft_value
        db.session.commit()
        return redirect(
            url_for(
                "show_post",
                post_name=post.blog_title_str,
                _external=_EXTERNAL,
                _scheme=_SCHEME,
            )
        )

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for("get_all_posts", _external=_EXTERNAL, _scheme=_SCHEME))


@app.route("/like-post/<string:post_name>", methods=["GET", "POST"])
def like_post(post_name):
    post = BlogPost.query.filter_by(blog_title_str=post_name).first()

    # Add 1 to the likes of the post and save back to the DB
    current_likes = post.post_likes
    new_likes = current_likes + 1
    post.post_likes = new_likes
    db.session.commit()
    # Get the new the new value from DB
    post = BlogPost.query.filter_by(blog_title_str=post_name).first()
    response = make_response(str(post.post_likes), 200)
    response.mimetype = "text/plain"
    return response
