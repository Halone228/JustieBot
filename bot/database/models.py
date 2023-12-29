from .core import Base
from datetime import datetime
from sqlalchemy import func, BigInteger, ForeignKey
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


class Users(Base):
    __tablename__ = "users_table"
    id: Mapped[int] = mapped_column(
        BigInteger(),
        primary_key=True
    )