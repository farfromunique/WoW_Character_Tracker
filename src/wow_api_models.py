from typing import Any, Collection, Dict, List, Literal, Optional, Type, overload
import logging
import requests


# Error Classes
class DoNotUseBaseClassError(Exception):
    pass


class UnknownRegionError(Exception):
    pass


class UnknownRealmError(Exception):
    pass


class AmbiguousRealmError(Exception):
    pass


class AmbiguousFieldError(Exception):
    pass


# Return Type Placeholders
class WoWDataApiReturnPlaceholder:
    locale: str = "en_US"
    href: str
    default_field: str

    def __init__(self, **kwargs) -> None:
        if "local" in kwargs.keys():
            self.locale = kwargs.pop("locale")

        if "href" in kwargs.keys():
            self.href = kwargs.pop("href")

        if "default_field" in kwargs.keys():
            self.default_field = kwargs.pop("default_field")

    def __str__(self) -> str:
        if self.__class__ != "WoWDataApiReturnPlaceholder":
            if self.default_field is not None:
                return getattr(self, self.default_field)
            else:
                raise AmbiguousFieldError(
                    f"Default Field not set for class {str(self.__class__)}"
                )
        else:
            raise DoNotUseBaseClassError(
                "The base class doesn't have a string to return"
            )

    @overload
    def assert_key_in_obj(
        self, key: str, obj: Dict[str, Any], type: Type[str]
    ) -> str: ...

    @overload
    def assert_key_in_obj(
        self, key: str, obj: Dict[str, Any], type: Type[int]
    ) -> int: ...

    @overload
    def assert_key_in_obj(
        self, key: str, obj: Dict[str, Any], type: Type[List[Any]]
    ) -> List[Any]: ...

    @overload
    def assert_key_in_obj(
        self, key: str, obj: Dict[str, Any], type: Type[Dict[Any, Any]]
    ) -> Dict[Any, Any]: ...

    def assert_key_in_obj(self, key: str, obj: Dict[str, Any], type: Type) -> Any:
        if key not in obj.keys():
            raise KeyError(
                f"The key '{key}' is not present in the passed 'obj': {obj}."
            )
        
        assert key in obj.keys()
        assert isinstance(obj[key], type)

        return obj[key]

    def _retrieve_from_href_get(self, auth: Dict[str, str]):
        response = requests.get(url=self.href, headers=auth)
        resp = response.json()
        for key in resp:
            try:
                setattr(self, key, resp[key])
            except Exception:
                continue

    def _retrieve_from_href_post(self, auth: Dict[str, str]):
        response = requests.post(url=self.href, headers=auth)
        resp = response.json()
        for key in resp:
            try:
                setattr(self, key, resp[key])
            except Exception:
                continue

    def retrieve_from_href(self, auth) -> bool:
        self._retrieve_from_href_get(auth)
        return True


class WoWCharacterGender(WoWDataApiReturnPlaceholder):
    type: None
    name: str
    default_field: str = "name"

    def __init__(self, obj, **kwargs):
        if self.default_field not in obj.keys():
            raise KeyError(f'Key "{self.default_field}" not in object.keys ({", ".join(obj.keys())})')
        super().__init__(**kwargs)
        if isinstance(obj[self.default_field], Dict):
            if self.locale in obj[self.default_field].keys():
                self.name = obj[self.default_field][self.locale]
            else:
                raise KeyError(f"The passed object's `{self.default_field}` key (a Dict) does not have the desired locale ({self.locale}). Provided locales were: {"', '".join(obj[self.default_field].keys())}")
        elif isinstance(obj[self.default_field], str):
            self.name = obj[self.default_field]
        else:
            raise AttributeError(f"The passed object's {obj[self.default_field]} key is of type `{type(obj[self.default_field])}`. Expected either Dict or str.")


class WoWCharacterGenderName(WoWDataApiReturnPlaceholder):
    default_field: None
    male: WoWCharacterGender
    female: WoWCharacterGender

    def __init__(self, obj, **kwargs):
        super().__init__(**kwargs)
        male_name = self.assert_key_in_obj("male", obj, Dict)
        self.male = WoWCharacterGender(male_name)
        female_name = self.assert_key_in_obj("female", obj, Dict)
        self.female = WoWCharacterGender(female_name)


class WoWCharacterPowerType(WoWDataApiReturnPlaceholder):
    type: None
    name: str
    id: int

    def __init__(self, obj: Dict[str, Dict[str, str]]):
        self.assert_key_in_obj("name", obj, Dict)
        self.name = self.assert_key_in_obj(self.locale, obj["name"], str)
        self.id = self.assert_key_in_obj("id", obj, int)


class WoWCharacterClass(WoWDataApiReturnPlaceholder):
    type: None
    name: str
    id: int
    default_field: str = "name"

    gender_name: WoWCharacterGender
    power_type: WoWCharacterPowerType

    def __init__(self, obj: Dict[str, Dict[str, str]]):
        self.href = self.assert_key_in_obj("href", obj, str)
        self.assert_key_in_obj("name", obj, Dict)

        self.name = self.assert_key_in_obj(self.locale, obj["name"], str)

        self.id = self.assert_key_in_obj("id", obj, int)

    def retrieve_from_href(self, auth) -> bool:
        return True


class WoWCharacterRace(WoWDataApiReturnPlaceholder):
    type: str
    name: str
    id: int
    default_field: str = "name"

    gender_name: Dict[str, str]
    # faction: WoWCharacterFaction
    is_selectable: bool
    is_allied_race: bool
    playable_classes: List[WoWCharacterClass]

    def __init__(self, obj, **kwargs):
        if self.default_field not in obj.keys():
            raise KeyError(f'Key "{self.default_field}" not in object.keys ({", ".join(obj.keys())})')
        super().__init__(**kwargs)
        if isinstance(obj[self.default_field], Dict):
            if self.locale in obj[self.default_field].keys():
                self.name = obj[self.default_field][self.locale]
            else:
                raise KeyError(f"The passed object's `{self.default_field}` key (a Dict) does not have the desired locale ({self.locale}). Provided locales were: {"', '".join(obj[self.default_field].keys())}")
        elif isinstance(obj[self.default_field], str):
            self.name = obj[self.default_field]
        else:
            raise AttributeError(f"The passed object's {obj[self.default_field]} key is of type `{type(obj[self.default_field])}`. Expected either Dict or str.")

    def retrieve_from_href(self, auth) -> bool:
        return True


class WoWCharacterFaction(WoWDataApiReturnPlaceholder):
    type: str
    name: str
    default_field: str = "name"

    def __init__(self, obj, **kwargs):
        if self.default_field not in obj.keys():
            raise KeyError(f'Key "{self.default_field}" not in object.keys ({", ".join(obj.keys())})')
        super().__init__(**kwargs)
        if isinstance(obj[self.default_field], Dict):
            if self.locale in obj[self.default_field].keys():
                self.name = obj[self.default_field][self.locale]
            else:
                raise KeyError(f"The passed object's `{self.default_field}` key (a Dict) does not have the desired locale ({self.locale}). Provided locales were: {"', '".join(obj[self.default_field].keys())}")
        elif isinstance(obj[self.default_field], str):
            self.name = obj[self.default_field]
        else:
            raise AttributeError(f"The passed object's {obj[self.default_field]} key is of type `{type(obj[self.default_field])}`. Expected either Dict or str.")



# Endpoints
class WoWRetailApiEndpoint:
    _log: logging.Logger

    known_regions: List[str] = ["us", "eu", "kr", "tw", "cn"]
    row_base_url: str = "https://{region}.api.blizzard.com"
    china_base_url: str = "https://gateway.battlenet.com.cn"
    region: str
    base_url: str
    method: Literal["GET", "POST"]
    realm: str
    realm_slug: str
    character_name: str
    locale: str
    _oauth_token: str
    _realm_validated: bool = False

    def __init__(
        self,
        region: str,
        realm: str,
        character_name: str,
        oauth_token: Optional[str] = None,
        **kwargs
    ) -> None:
        self._log = logging.getLogger('WoW_Retail_API_Endpoint')
        if 'log_level' in kwargs.keys():
            self._log.setLevel(kwargs["log_level"])
        
        if region not in self.known_regions:
            raise UnknownRegionError(
                f"Region {region} is not recognized.",
                f"Known regions are: {', '.join(self.known_regions)}",
            )
        elif region == "cn":
            self.base_url = self.china_base_url
        else:
            self.base_url = self.row_base_url.format(region=region)

        self.region = region
        self.realm = realm
        self.character_name = character_name

        if 'locale' in kwargs.keys():
            self.locale = kwargs['locale']
        else:
            self.locale = 'en_US'

        if oauth_token:
            self._oauth_token = oauth_token

            self.validate_realm()
            

    # TODO: Implement return typr checking for 404, 401, etc.

    def validate_realm(self):
        if self._realm_validated:
            return True

        endpoint = "/data/wow/search/realm"
        auth = {"Authorization": f"Bearer {self._oauth_token}"}
        self.realm_slug = self.realm.lower().strip()
        params = {
            "namespace": "dynamic-us",
            "_page": 1,
            "_pageSize": 10,
            "orderby": "name",
            "slug": self.realm_slug,
        }

        response = requests.get(
            url=f"{self.base_url}{endpoint}", params=params, headers=auth
        )

        if len(response.json()["results"]) == 1:
            self._log.debug(f"Realm slug {self.realm_slug} appears valid!")
            self.realm = response.json()["results"][0]["data"]["name"]["en_US"]
            self._log.debug(self.realm)
        elif len(response.json()["results"]) > 1:
            msg = f"Realm slug {self.realm_slug} returned multiple results:"
            msg += "\n\t"
            msg += ",\n".join(
                [
                    f"\t{realm['data']['name']['en_US']}"
                    for realm in response.json()["results"]
                ]
            )
            raise AmbiguousRealmError(msg)
        else:
            msg = (
                f"Realm slug {self.realm_slug} (from {self.realm}) returned no results."
            )
            raise UnknownRealmError(msg)
        self._realm_validated = True
        return True

    def retrieve(self):
        self._log.warning(
            "Calling `retrieve` on the base class for endpoints? Not useful."
        )
        pass


class CharacterProfileSummary(WoWRetailApiEndpoint):
    endpoint = "profile/wow/character/{realm_slug}/{character_name}"

    id: str
    name: str
    gender: WoWCharacterGender
    faction: WoWCharacterFaction
    race: WoWCharacterRace
    character_class: str
    active_spec: str
    guild: str
    level: int
    experience: int
    achievement_points: int
    achievements: Dict[str, str]
    titles: Dict[str, str]
    pvp_summary: Dict[str, str]
    encounters: Dict[str, str]
    media: Dict[str, str]
    last_login_timestamp: Dict[str, str]
    average_item_level: int
    equipped_item_level: int
    specializations: Dict[str, str]
    statistics: Dict[str, str]
    mythic_keystone_profile: Dict[str, str]
    equipment: Dict[str, str]
    appearance: Dict[str, str]
    collections: Dict[str, str]
    reputations: Dict[str, str]
    quests: Dict[str, str]
    achievements_statistics: Dict[str, str]
    professions: Dict[str, str]
    covenant_progress: Dict[str, str]

    def __init__(self, **kwargs):
        super_params = {}
        
        if 'region' in kwargs.keys():
            super_params['region'] = kwargs['region']
        if 'realm' in kwargs.keys():
            super_params['realm'] = kwargs['realm']
        if 'character_name' in kwargs.keys():
            super_params['character_name'] = kwargs['character_name']
        if 'token' in kwargs.keys():
            super_params['oauth_token'] = kwargs['token']
        if 'log_level' in kwargs.keys():
            super_params['log_level'] = kwargs['log_level']
        
        super().__init__(
            **super_params
        )

        my_log = self._log.getChild('CharacterProfileSummary')
        self._log = my_log


    def retrieve(self) -> Dict[str, str | int | Any]:
        if not self._oauth_token or self._oauth_token == '':
            raise Exception("Can't retrieve data without a token.")
        
        self._log.info(f'Retrieving data for {self.character_name}...')

        params = {":region": self.region, "namespace": f"profile-{self.region}", "locale": self.locale}

        resp = requests.get(
            url=f"{self.base_url}/{self.endpoint.format_map({
                "realm_slug":self.realm_slug,
                "character_name":self.character_name
            })}",
            params=params,
            headers={"Authorization": f"Bearer {self._oauth_token}"}
        )

        # resp.raise_for_status()
        
        resp = resp.json()

        processed_keys = []
        for key in resp.keys():
            self._log.debug(f'Processing key `{key}`')

            for sub in WoWDataApiReturnPlaceholder.__subclasses__():
                if f'wowcharacter{key}' == sub.__name__.lower():
                    self._log.debug(f'Found class {sub.__name__}')
                    self._log.debug(f'Passing object with keys: {', '.join(resp[key].keys())}')
                    out = sub(obj=resp[key])
                    setattr(self, key, out)
                    self._log.debug(f'self.{key} = {getattr(self, key)}')
                    processed_keys.append(key)
        
        remaining_keys = resp.keys() - processed_keys

        for key in remaining_keys:
            if not isinstance(resp[key], Collection):
                setattr(self, key, resp[key])

        return resp
