from datetime import date, timedelta
from textwrap import dedent
from typing import Any, List, Optional, overload
from sqlalchemy import ForeignKey
from sqlalchemy import String as SQL_String
from sqlalchemy import Integer as SQL_Integer
from sqlalchemy import Date as SQL_Date
from sqlalchemy import CheckConstraint
from sqlalchemy import Boolean as SQL_Boolean
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
import logging

logging.addLevelName(5, 'TRACE')

class Base(DeclarativeBase):
    _log: logging.Logger

    def update(self, **data):
        self._log = logging.getLogger('BaseDataModel')
        for key, val in data.items():
            try:
                if getattr(self, key) != val:
                    setattr(self, key, val)
            except AttributeError:
                self._log.log(level=5, msg=f"Tried to add {key} ({val}) to {self}; Not a valid key.")
                continue

        if 'session' in data.keys():
            self._log.debug('Persisting to DB')
            data['session'].add(self)
            data['session'].commit()
        else:
            self._log.debug('No session - not persisting to DB')

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
    region: Mapped[str] = mapped_column(SQL_String(length=2))
    name: Mapped[str] = mapped_column(SQL_String(30))
    realm: Mapped[str] = mapped_column(SQL_String(30))
    level: Mapped[int] = mapped_column(SQL_Integer(), nullable=True)
    
    def get_details(self, db_sess: Session, token: str):
        from wow_api_models import CharacterProfileSummary as cps

        self._log = logging.getLogger('WoWCharacter')

        req = cps(
            region=self.region,
            realm=self.realm,
            character_name=self.name,
            oauth_token=token,
            log_level=logging.INFO
        )

        _ = req.retrieve()

        new = {}

        new['region'] = req.region
        new['name'] = req.character_name
        new['realm'] = req.realm
        new['level'] = req.level

        self.update(session=db_sess, **new)

    @overload
    def __init__(
        self,
        key: Optional[str],
        region: str,
        realm: str,
        name: str,
        level: Optional[int],
        id: Optional[int],
        **kw: Any
    ):
        ...

    @overload
    def __init__(
        self,
        key: str,
        region: Optional[str],
        realm: Optional[str],
        name: Optional[str],
        level: Optional[int],
        id: Optional[int],
        **kw: Any
    ):
        ...

    @overload
    def __init__(
        self,
        key: Optional[str],
        region: Optional[str],
        realm: Optional[str],
        name: Optional[str],
        level: Optional[int],
        id: int,
        **kw: Any
    ):
        ...

    def __init__(
        self,
        key: Optional[str] = None,
        region: Optional[str] = None,
        realm: Optional[str] = None,
        name: Optional[str] = None,
        level: Optional[int] = None,
        id: Optional[int] = None,
        **kw: Any
    ):
        if key is not None:
            k_region, k_realm, k_name = key.split('|')
            if region is not None and region.lower() != k_region.lower():
                msg = f'''
                If `Region` and `Key` are both supplied, `Region` must match region in `Key`.
                Region: {region}
                Key: {key}
                Region in Key: {k_region}
                '''
                raise Exception(dedent(msg))

            
            if realm is not None and realm.lower() != k_realm.lower():
                msg = f'''
                If `Realm` and `Key` are both supplied, Realm must match realm in `Key`.
                realm: {realm}
                Key: {key}
                Realm in Key: {k_realm}
                '''
                raise Exception(dedent(msg))

            
            if name is not None and name.lower() != k_name.lower():
                msg = f'''
                If `Name` and `Key` are both supplied, Name must match name in `Key`.
                Name: {name}
                Key: {key}
                Name in Key: {k_name}
                '''
                raise Exception(dedent(msg))
            
        kwargs = {
            'key': key,
            'region': region,
            'realm': realm,
            'name': name,
            'level': level,
            'id': id
        }

        kwargs.update(kw)

        super().__init__(**kwargs)

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
    record_date: Mapped[date] = mapped_column(SQL_Date)
    slot: Mapped[str] = mapped_column(SQL_String)
    item_id: Mapped[int] = mapped_column(SQL_Integer)
    ilevel: Mapped[int] = mapped_column(SQL_Integer)
    name: Mapped[str] = mapped_column(SQL_String)
    quality: Mapped[str] = mapped_column(SQL_String)
    size: Mapped[str] = mapped_column(SQL_String, nullable=True)
    
    def __init__(self, **kw: Any):
        super().__init__(**kw)

    def __repr__(self) -> str:
        return f"GearLog(id={self.id}, character={self.character_id}, date={self.record_date})"
    
class CharacterProgress(Base):
    __tablename__ = "progress_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(ForeignKey('wow_character.id'))
    wow_character: Mapped["WoWCharacter"] = relationship(WoWCharacter)
    character_level: Mapped[int] = mapped_column(SQL_Integer(), nullable=True)
    record_date: Mapped[date] = mapped_column(SQL_Date())
    average_item_level: Mapped[int] = mapped_column(SQL_Integer())
    pinnacle_quest_done: Mapped[bool] = mapped_column(SQL_Boolean(), default=False)
    profession_1_quest_done: Mapped[bool] = mapped_column(SQL_Boolean(), default=False)
    profession_2_quest_done: Mapped[bool] = mapped_column(SQL_Boolean(), default=False)
    delves_completed: Mapped[int] = mapped_column(SQL_Integer(), default=0)

    def __init__(
        self,
        character_id: Optional[int] = None,
        wow_character: Optional[WoWCharacter] = None,
        character_level: int = 0,
        record_date: Optional[date] = None,
        average_item_level: int = 0,
        pinnacle_quest_done: bool = False,
        profession_1_quest_done: bool = False,
        profession_2_quest_done: bool = False,
        delves_completed: int = 0,
        **kw: Any
    ):
        if character_id is not None:
            self.character_id = character_id
        elif wow_character is not None:
            self.wow_character = wow_character
            self.character_id = wow_character.id

        if character_level is not None:
            self.character_level = character_level

        if record_date is not None:
            self.record_date = record_date

        if average_item_level is not None:
            self.average_item_level = average_item_level

        if pinnacle_quest_done is not None:
            self.pinnacle_quest_done = pinnacle_quest_done

        if profession_1_quest_done is not None:
            self.profession_1_quest_done = profession_1_quest_done

        if profession_2_quest_done is not None:
            self.profession_2_quest_done = profession_2_quest_done

        if delves_completed is not None:
            self.delves_completed = delves_completed

        super().__init__(**kw)

    @staticmethod
    def new(character: WoWCharacter, session: Session) -> "CharacterProgress":
        this = CharacterProgress
        this_wow_week: List[date] = []
        this_wow_week.append(date.today())
        
        character_level = character.level
        record_date = date.today()
        pinnacle_quest_done = False
        profession_1_quest_done = False
        profession_2_quest_done = False
        delves_completed = 0
        
        for d in range(1,7):
            target_date = date.today() - timedelta(days=d)
            if target_date.weekday() != 1:
                this_wow_week.append(target_date)

        with session as s:
            latest_gear_logs = s.scalars(
                select(GearLog)
                .where(GearLog.character_id == character.id)
                .where(GearLog.record_date == date.today())
            )
            average_item_level = int(sum([glog.ilevel for glog in latest_gear_logs]) / 16)

            for day in sorted(this_wow_week):
                prog = s.scalar(
                    select(this)
                    .where(this.character_id == character.id)
                    .where(this.record_date == day)
                )
                if prog is not None:
                    pinnacle_quest_done = pinnacle_quest_done or prog.pinnacle_quest_done
                    profession_1_quest_done = profession_1_quest_done or prog.profession_1_quest_done
                    profession_2_quest_done = profession_2_quest_done or prog.profession_2_quest_done
                    delves_completed += prog.delves_completed

            current_progress = this(
                character_id = character.id,
                wow_character=character,
                record_date = record_date,
                character_level = character_level,
                average_item_level=average_item_level,
                pinnacle_quest_done = pinnacle_quest_done,
                profession_1_quest_done = profession_1_quest_done,
                profession_2_quest_done = profession_2_quest_done,
                delves_completed=delves_completed
            )

            with session as s:
                s.add(current_progress)
                s.commit()

            return current_progress

    def __repr__(self) -> str:
        return f"CharacterProgress(id={self.id}, character={self.character_id}, date={self.record_date})"
