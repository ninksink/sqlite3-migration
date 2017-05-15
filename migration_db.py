from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from config import CONFIG

db = SQLAlchemy()

class Migrate_Version(db.Model):
    __tablename__ = 'migrate_version'
    id = db.Column(db.Integer, primary_key=True)
    git_version = db.Column(db.String(20))
    migration_filename = db.Column(db.Text)
    migration_direction = db.Column(db.String(20))
    migration_timestamp = db.Column(db.String(20))
