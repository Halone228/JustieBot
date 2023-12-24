from .core import Base
from datetime import datetime
from sqlalchemy import func, BigInteger
from sqlalchemy.orm import Mapped, mapped_column


class User(Base):
    __tablename__ = "user_table"
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True
    )
    expire_date: Mapped[datetime] = mapped_column(
        server_default=func.now()
    )
    notified: Mapped[bool] = mapped_column(
        default=True
    )
    in_group: Mapped[bool] = mapped_column(
        default=False
    )
    points: Mapped[float] = mapped_column(
        default=0
    )
    messages: Mapped[int] = mapped_column(
        default=0
    )