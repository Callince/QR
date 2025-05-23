from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, UTC
from flask_login import UserMixin
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship


# Initialize SQLAlchemy without binding to app yet
db = SQLAlchemy()