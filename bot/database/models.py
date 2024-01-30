from .core import Base
from datetime import datetime
from sqlalchemy import func, BigInteger, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship


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
    referrer: Mapped[int] = mapped_column(
        ForeignKey('users_table.id'),
        nullable=True
    )


class Users(Base):
    __tablename__ = "users_table"
    id: Mapped[int] = mapped_column(
        BigInteger(),
        primary_key=True
    )


class Referrers(Base):
    __tablename__ = "referrers_table"
    referrer_id: Mapped[int] = mapped_column(
        ForeignKey('users_table.id'),
        primary_key=True
    )
    referral_id: Mapped[int] = mapped_column(
        ForeignKey('users_table.id')
    )


class Matches(Base):
    __tablename__ = "matches_table"
    id: Mapped[int] = mapped_column(
        autoincrement=True,
        primary_key=True
    )
    first_opponent: Mapped[str]
    second_opponent: Mapped[str]
    match_name: Mapped[str]
    ended: Mapped[bool] = mapped_column(
        default=False
    )
    first_coff: Mapped[float]
    second_coff: Mapped[float]
    first_win: Mapped[bool] = mapped_column(
        nullable=True
    )
    end_time: Mapped[datetime]
    bids: Mapped['Bids'] = relationship(
        back_populates='match'
    )

    def __repr__(self):
        return f'{self.id} | {self.match_name} | {self.first_coff:.2f}:{self.second_coff:.2f}'


class Bids(Base):
    __tablename__ = 'bids_table'
    match_id: Mapped[int] = mapped_column(
        ForeignKey(f'{Matches.__tablename__}.id'),
        primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey(f'{Users.__tablename__}.id'),
        primary_key=True
    )
    bid: Mapped[float]
    match: Mapped[Matches] = relationship(
        back_populates='bids',
        lazy='selectin'
    )

    def get_info(self):
        return f'{self.match.match_name} | {self.bid}'
