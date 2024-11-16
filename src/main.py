import os
import logging
from typing import Dict, List, Literal
import requests
import requests.auth

log = logging.getLogger(__name__)
logging.basicConfig(encoding="utf-8", level=logging.DEBUG)

OAUTH_TOKEN = ""

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
    region: Literal["us", "eu", "kr", "tw", "cn"],
    realm: str,
    character: str,
    locale: str = "en_US",
):
    global OAUTH_TOKEN
    if region == "cn":
        API_HOST = "gateway.battlenet.com.cn"
    else:
        API_HOST = f"{region}.api.blizzard.com"

    auth = {"Authorization": f"Bearer {OAUTH_TOKEN}"}
    realmSlug = realm.lower().strip()
    characterName = character.lower().strip()

    endpoint = f"/profile/wow/character/{realmSlug}/{characterName}/equipment"

    params = {":region": region, "namespace": f"profile-{region}", "locale": locale}

    resp = requests.get(
        url=f"https://{API_HOST}/{endpoint}", params=params, headers=auth
    )
    return resp.json()

def persist_gear_to_db(gear: Dict[str, Dict[str, str | int]]):
    pass


def main():
    global OAUTH_TOKEN
    OAUTH_TOKEN = get_oauth_token(client_id, client_secret)["access_token"]

    equipment = get_equipment_for_character("us", "icecrown", "littlegizmo")
    slots = [item["slot"]["type"] for item in equipment["equipped_items"]]

    structured_gear = {}

    for slot in slots:
        try:
            obj = [
                item
                for item in equipment["equipped_items"]
                if item["slot"]["type"] == slot
            ][0]
            log.info("-" * 50)
            log.info(obj)
            log.info("-" * 50)
            structured_gear[slot] = {
                "name": obj["name"],
                "item_number": obj["item"]["id"],
                "ilevel": obj["level"]["value"],
                "quality": obj["quality"]["type"],
            }
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
    
    persist_gear_to_db(structured_gear)
