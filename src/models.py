import uuid
from datetime import datetime

from sqlalchemy import MetaData
from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import relationship


metadata_obj = MetaData(schema="webtronics")

class Base(DeclarativeBase):
    metadata = metadata_obj


class User(Base):
    __tablename__ = 'user'

    id = Column(
        UUID(as_uuid=True), primary_key=True,
        default=uuid.uuid4, unique=True, nullable=False
    )
    login = Column(String(255), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(50))
    last_name = Column(String(50))
    email = Column(String(50), unique=True, nullable=False)
    
    def __init__(
            self, login: str, hashed_password: str, first_name: str | None,
            last_name: str | None, email: str
        ) -> None:
        self.login = login
        self.hashed_password = hashed_password
        self.first_name = first_name
        self.last_name = last_name
        self.email = email

    def __repr__(self) -> str:
        return f'<User {self.login}>'
    

class Post(Base):
    __tablename__ = 'post'

    id = Column(
        UUID(as_uuid=True), primary_key=True,
        default=uuid.uuid4, unique=True, nullable=False
    )
    title = Column(String(120), nullable=False)
    content = Column(Text())
    author_id = Column(ForeignKey('user.id'), nullable=False)
    author = relationship('User')
    creation_dt = Column(DateTime, default=datetime.now)

    def __init__(self, title: str, content: str, author: User) -> None:
        self.title = title
        self.content = content
        self.author = author

    def __repr__(self) -> str:
        return f'<Post {self.title}>'
