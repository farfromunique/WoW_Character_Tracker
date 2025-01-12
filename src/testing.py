from main import get_oauth_token
from main import get_engine
import data_models as dm
import wow_api_models as wow
import os
client_id = os.getenv("WOW_CLIENT_ID", "NeedAKey")
client_secret = os.getenv("WOW_CLIENT_SECRET", "OrThisWillNotWork")
token = get_oauth_token(client_id, client_secret)['access_token']
little = "us|icecrown|littlegizmo"
region, realm, name = little.split('|')
l_profile = wow.CharacterProfileSummary(region, realm, name, token)
l_profile.retrieve()