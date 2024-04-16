from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship

from . import db


class BlogPost(db.Model):
    __tablename__ = "blog_posts"
    id = db.Column(db.Integer, primary_key=True)
    author = db.Column(db.String(250), nullable=False)
    title = db.Column(db.String(250), unique=True, nullable=False)
    subtitle = db.Column(db.String(250), nullable=False)
    date = db.Column(db.String(250), nullable=False)
    body = db.Column(db.Text, nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    # browser firendly blog url. Instead of using id like /post/5
    blog_title_str = db.Column(db.String(250), nullable=False)
    # Create relationship with User table
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    is_draft = db.Column(db.Boolean, default=False)
    post_views = db.Column(db.Integer, default=0)
    post_likes = db.Column(db.Integer, default=0)
    author = relationship("User", back_populates="posts")
    # Create a relationship with Comment table
    comments = relationship("Comment", back_populates="blog_posts")


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(250), unique=True, nullable=False)
    name = db.Column(db.String(250), nullable=False)
    password = db.Column(db.String(250), nullable=False)
    # Create relationship with BlogPost table
    posts = relationship("BlogPost", back_populates="author")
    # Create relationshipb with Comment table
    comments = relationship("Comment", back_populates="comment_author")


class Comment(db.Model):
    __tablename__ = "comments"
    id = db.Column(db.Integer, primary_key=True)
    comment = db.Column(db.Text, nullable=False)
    # Create relationship wirh User table
    author_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    comment_author = relationship("User", back_populates="comments")
    # Create relationship with BlogPost table
    blog_post_id = db.Column(db.Integer, db.ForeignKey("blog_posts.id"))
    blog_posts = relationship("BlogPost", back_populates="comments")
