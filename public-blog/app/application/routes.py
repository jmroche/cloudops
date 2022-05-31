import hashlib
from datetime import date
from functools import wraps

from flask import abort
from flask import current_app as app
from flask import flash
from flask import Flask
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
    posts = BlogPost.query.all()
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
            return redirect(url_for("login", _external=True, _scheme="https"))

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
                    url_for("get_all_posts", _external=True, _scheme="https")
                )
            else:  # wrong username or password
                flash("Ivalid username or password", category="danger")
                return redirect(url_for("login", _external=True, _scheme="https"))
        else:  # user doesn'r exist in DB
            flash("User not found, please register", category="danger")
            return redirect(url_for("register", _external=True, _scheme="https"))

    return render_template("login.html", form=login_form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("get_all_posts", _external=True, _scheme="https"))


@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def show_post(post_id):
    comment_form = CommentForm()
    requested_post = BlogPost.query.get(post_id)
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
                blog_post_id=post_id,
                author_id=current_user.id,
            )
            db.session.add(new_comment)
            db.session.commit()
            return render_template(
                "post.html",
                post=requested_post,
                form=comment_form,
                comments=Comment.query.filter_by(blog_post_id=post_id).all(),
                email=hashed_user_email,
            )
        else:
            flash("You need to login or register to comment", category="danger")
            return redirect(url_for("login", _external=True, _scheme="https"))

    return render_template(
        "post.html",
        post=requested_post,
        form=comment_form,
        comments=Comment.query.filter_by(blog_post_id=post_id).all(),
        email=hashed_user_email,
    )


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
        new_post = BlogPost(
            title=form.title.data,
            subtitle=form.subtitle.data,
            body=form.body.data,
            img_url=form.img_url.data,
            # use the current logged in user_id as the author id
            author_id=current_user.id,
            date=date.today().strftime("%B %d, %Y"),
        )
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for("get_all_posts", _external=True, _scheme="https"))
    return render_template("make-post.html", form=form)


@app.route("/edit-post/<int:post_id>", methods=["GET", "POST"])
@admin_required
def edit_post(post_id):
    post = BlogPost.query.get(post_id)
    edit_form = CreatePostForm(
        title=post.title,
        subtitle=post.subtitle,
        img_url=post.img_url,
        # author=post.author,
        body=post.body,
    )
    if edit_form.validate_on_submit():
        post.title = edit_form.title.data
        post.subtitle = edit_form.subtitle.data
        post.img_url = edit_form.img_url.data
        post.author_id = current_user.id
        post.body = edit_form.body.data
        db.session.commit()
        return redirect(
            url_for("show_post", post_id=post.id, _external=True, _scheme="https")
        )

    return render_template("make-post.html", form=edit_form)


@app.route("/delete/<int:post_id>")
def delete_post(post_id):
    post_to_delete = BlogPost.query.get(post_id)
    db.session.delete(post_to_delete)
    db.session.commit()
    return redirect(url_for("get_all_posts", _external=True, _scheme="https"))
