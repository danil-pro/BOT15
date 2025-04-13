from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class RegisteredUser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role = db.Column(db.String(50), nullable=False)
    name = db.Column(db.String(100))
    city = db.Column(db.String(100))
    language_level = db.Column(db.String(50))
    price = db.Column(db.Float)
    contact = db.Column(db.String(50))
    banned = db.Column(db.Boolean, default=False)


class MuteWord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String(50), nullable=False)
