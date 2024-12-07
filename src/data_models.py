from datetime import date
from typing import Any
from sqlalchemy import ForeignKey
from sqlalchemy import String
from sqlalchemy import Integer
from sqlalchemy import Date
from sqlalchemy import CheckConstraint
from sqlalchemy import Boolean
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
import logging


class Base(DeclarativeBase):
    log: logging.Logger

    def update(self, **data):
        self.log = logging.getLogger(str(self.__class__))
        for key, val in data.items():
            try:
                if getattr(self, key) != val:
                    setattr(self, key, val)
            except AttributeError:
                self.log.debug(f"Tried to add {key} ({val}) to {self}; Not a valid key.")
                continue
        return self
    pass

class WoWCharacter(Base):
    __tablename__ = "wow_character"

    region_contraint: CheckConstraint = CheckConstraint(
        "region in ('us', 'eu', 'kr', 'tw')",
        name="wow_region_constraint"
    )

    id: Mapped[int] = mapped_column(primary_key=True, )
    key: Mapped[str] = mapped_column(unique=True, index=True)
    region: Mapped[str] = mapped_column(String(length=2))
    name: Mapped[str] = mapped_column(String(30))
    realm: Mapped[str] = mapped_column(String(30))
    level: Mapped[int] = mapped_column(Integer(), nullable=True)
    
    def __init__(self, **kw: Any):
        super().__init__(**kw)

    def __repr__(self) -> str:
        return f"WoWCharacter(id={self.id!r}, region={self.region!r}, realm={self.realm!r}, name={self.name!r})"

class GearLog(Base):
    __tablename__ = "gear_log"

    wow_slot_constraint: CheckConstraint = CheckConstraint(
        "slot in ('head', 'neck', 'shoulder', 'chest', 'waist', 'legs', 'feet', 'wrist', 'hands', 'finger_1', 'finger_2', 'trinket_1', 'trinket_2','back', 'main_hand', 'off_hand')",
        name='gear_slot_enum'
    )

    wow_quality_constraint: CheckConstraint = CheckConstraint(
        "quality in ('COMMON', 'UNCOMMON', 'RARE', 'EPIC')",
        name='gear_quality_enum'
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey('wow_character.id'))
    wow_character: Mapped["WoWCharacter"] = relationship(WoWCharacter)
    record_date: Mapped[date] = mapped_column(Date())
    slot: Mapped[str] = mapped_column(String())
    item_id: Mapped[int] = mapped_column(Integer())
    ilevel: Mapped[int] = mapped_column(Integer())
    name: Mapped[str] = mapped_column(String())
    quality: Mapped[str] = mapped_column(String())
    size: Mapped[str] = mapped_column(String(), nullable=True)
    
    def __init__(self, **kw: Any):
        super().__init__(**kw)

    def __repr__(self) -> str:
        return f"GearLog(id={self.id}, character={self.character_id}, date={self.record_date})"
    
class CharacterProgress(Base):
    __tablename__ = "progress_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey('wow_character.id'))
    wow_character: Mapped["WoWCharacter"] = relationship(WoWCharacter)
    character_level: Mapped[int] = mapped_column(Integer(), nullable=True)
    record_date: Mapped[date] = mapped_column(Date())
    average_item_level: Mapped[int] = mapped_column(Integer())
    pinnacle_quest_done: Mapped[bool] = mapped_column(Boolean(), default=False)
    profession_1_quest_done: Mapped[bool] = mapped_column(Boolean(), default=False)
    profession_2_quest_done: Mapped[bool] = mapped_column(Boolean(), default=False)
    delves_completed: Mapped[int] = mapped_column(Integer(), default=0)
    
    def __init__(self, **kw: Any):
        super().__init__(**kw)

    def __repr__(self) -> str:
        return f"CharacterProgress(id={self.id}, character={self.character_id}, date={self.record_date})"
