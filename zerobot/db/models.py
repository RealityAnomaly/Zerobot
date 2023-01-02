from email.policy import default
from sqlalchemy import Column, BigInteger, Text, DateTime, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class UserMessage(Base):
    __tablename__ = "user_messages"

    id = Column(BigInteger, primary_key=True)
    author = Column(BigInteger)
    content = Column(Text)
    channel = Column(BigInteger)
    guild = Column(BigInteger)
    edited = Column(DateTime, nullable=True)
    deleted = Column(Boolean)

class Guild(Base):
    __tablename__ = "guilds"

    id = Column(BigInteger, primary_key=True)
    last_backfill = Column(DateTime, nullable=True)

class MimicFrontendResponse(Base):
    __tablename__ = "mimic_frontend_responses"

    # just the message id of the response
    id = Column(BigInteger, primary_key=True)
    content = Column(Text)
    deleted = Column(Boolean)
