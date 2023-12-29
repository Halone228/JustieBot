from .core import Base
from datetime import datetime
from sqlalchemy import func, BigInteger, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column


class User(Base):
    __tablename__ = "user_points_table"
    user_id: Mapped[int] = mapped_column(
        ForeignKey('users_table.id'),
        primary_key=True
    )
    points: Mapped[float] = mapped_column(
        default=0
    )


class UserInfo(Base):
    __tablename__ = "user_info_table"
    user_id: Mapped[int] = mapped_column(
        ForeignKey('users_table.id'),
        primary_key=True
    )
    username: Mapped[str] = mapped_column(
        Text(), nullable=True
    )
    first_name: Mapped[str] = mapped_column(
        Text(), nullable=True
    )
    last_name: Mapped[str] = mapped_column(
        Text(), nullable=True
    )


class Users(Base):
    __tablename__ = "users_table"
    id: Mapped[int] = mapped_column(
        BigInteger(),
        primary_key=True
    )