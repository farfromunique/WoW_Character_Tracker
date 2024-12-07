from pathlib import Path
import os
import logging
from typing import Dict
import requests
import json
from datetime import date
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from tqdm.auto import tqdm
from data_models import WoWCharacter, GearLog, CharacterProgress, Base

log = logging.getLogger(__name__)
logging.basicConfig(encoding="utf-8", level=logging.INFO)
logging.getLogger("urllib3.connectionpool").level = logging.WARNING
logging.getLogger("sqlalchemy.engine.Engine").level = logging.WARNING


OAUTH_TOKEN = ""

list_of_characters = [
    "us|icecrown|littlegizmo",
    "us|icecrown|evilgizmo",
    "us|icecrown|tidalgizmo",
    "us|icecrown|stockygizmo",
    "us|icecrown|scaledgizmo",
    "us|icecrown|naturalgizmo",
    "us|icecrown|voidedgizmo",
    "us|icecrown|fuzzygizmo",
    "us|icecrown|felgizmo",
    "us|icecrown|tallgizmo"
]

client_id = os.getenv("WOW_CLIENT_ID", "NeedAKey")
client_secret = os.getenv("WOW_CLIENT_SECRET", "OrThisWillNotWork")


def get_oauth_token(id: str, secret: str) -> Dict:
    base_url = "https://oauth.battle.net/token"
    data = {
        "grant_type": "client_credentials",
    }

    response = requests.post(base_url, data=data, auth=(id, secret))
    return response.json()


def get_equipment_for_character(
    region: str,
    realm: str,
    character: str,
    locale: str = "en_US",
):
    global OAUTH_TOKEN, log
    if region == "cn":
        API_HOST = "gateway.battlenet.com.cn"
    elif region in ["us", "eu", "kr", "tw"]:
        API_HOST = f"{region}.api.blizzard.com"
    else:
        raise Exception("Invalid region specified.", region)

    auth = {"Authorization": f"Bearer {OAUTH_TOKEN}"}
    realmSlug = realm.lower().strip()
    characterName = character.lower().strip()

    endpoint = f"/profile/wow/character/{realmSlug}/{characterName}/equipment"

    params = {":region": region, "namespace": f"profile-{region}", "locale": locale}

    resp = requests.get(
        url=f"https://{API_HOST}/{endpoint}",
        params=params,
        headers=auth
    )
    return resp.json()


def get_engine():

    db_host = os.getenv("DB_HOST")
    db_user = os.getenv("DB_USER")
    db_port = os.getenv("DB_PORT")
    db_pass = os.getenv("DB_PASS")
    db_name = os.getenv("DB_NAME")

    return create_engine(f"postgresql+psycopg://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}")
    

def main():

    global OAUTH_TOKEN, list_of_characters, log
    OAUTH_TOKEN = get_oauth_token(client_id, client_secret)["access_token"]

    output_dir = Path('.', 'storage', 'equipment')

    engine = get_engine()
    Base.metadata.create_all(engine)

    for character in tqdm(list_of_characters):
        log.debug(character)
        with Session(engine) as db_sess:
            this_character = db_sess.scalar(select(WoWCharacter).where(WoWCharacter.key == character))

            if not this_character:
                region, realm, character_name = character.split('|')
                this_character = WoWCharacter(
                    key = character,
                    region = region,
                    name = character_name,
                    realm = realm
                )
                db_sess.add(this_character)
                db_sess.commit()
            else:
                region = this_character.region
                realm = this_character.realm
                character_name = this_character.name

            output_file = Path(output_dir, date.today().isoformat(), region, realm, character_name, 'equipment.json')
            
            equipment = get_equipment_for_character(region, realm, character_name)
            slots = [item["slot"]["type"] for item in equipment["equipped_items"]]

            structured_gear = {}
            gear_logs: Dict[str, GearLog] = {}
            
            stored_gear = db_sess.scalars(
                select(GearLog)
                .where(GearLog.wow_character == this_character)
                .where(GearLog.record_date == date.today())
                .order_by(GearLog.slot)
            )
            if stored_gear:
                for gear in stored_gear:
                    slot = gear.slot
                    gear_logs[slot] = gear

            for slot in tqdm(slots):
                try:
                    obj = [
                        item
                        for item in equipment["equipped_items"]
                        if item["slot"]["type"] == slot
                    ][0]
                    structured_gear[slot] = {
                        "name": obj["name"],
                        "item_id": obj["item"]["id"],
                        "ilevel": obj["level"]["value"],
                        "quality": obj["quality"]["type"],
                    }
                    if slot == 'MAIN_HAND':
                        size = obj['inventory_type']['type']
                    else:
                        size = None
                    
                    structured_gear[slot]['size'] = size
                        
                    if slot in gear_logs:
                        gear_logs[slot].update(**structured_gear[slot])
                    else:
                        gear_logs[slot] = GearLog(
                            wow_character = this_character,
                            record_date = date.today(),
                            slot = slot,
                            **structured_gear[slot]
                        )
                        db_sess.add(gear_logs[slot])
                        db_sess.commit()
                except KeyError:
                    log.debug(
                        f"Tried to get gear for slot {slot}, but that slot isn't in the data."
                    )
                    log.debug("Returned slots: ")
                    log.debug(
                        ", ".join(
                            [item["slot"]["type"] for item in equipment["equipped_items"]]
                        )
                    )
                    continue
            
            
                try:
                    for slot, gear_log in gear_logs.items():
                        db_sess.add(gear_log)
                        db_sess.commit()
                except Exception as e:
                    log.error(e)
                    db_sess.rollback()
                    continue

            if not output_file.exists():
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.open(mode='w+').close()
            output_file.write_text(json.dumps(structured_gear))

            total_ilvl = sum([structured_gear[slot]["ilevel"] for slot in structured_gear])
            if structured_gear['MAIN_HAND']['size'] == "TWOHWEAPON":
                total_ilvl += structured_gear['MAIN_HAND']['ilevel']
            average_ilvl = int(total_ilvl / 16)

            progress = db_sess.scalar(
                select(CharacterProgress)
                .where(CharacterProgress.wow_character == this_character)
                .where(CharacterProgress.record_date == date.today())
            )
            if not progress:
                progress = CharacterProgress(
                    wow_character=this_character,
                    record_date=date.today(),
                    average_item_level=average_ilvl
                )
                db_sess.add(progress)
                db_sess.commit()
            else:
                progress.update(average_item_level = average_ilvl)


if __name__ == "__main__":
    main()
