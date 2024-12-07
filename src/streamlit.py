import streamlit as st
import pandas as pd
from sqlalchemy import text, select

from data_models import WoWCharacter, CharacterProgress, GearLog
from sql_commands import *

conn = st.connection('wow_char_db', type='sql')

def get_progress(character: WoWCharacter):
    global conn

    with conn.session as s:
        return s.scalars(
            select(CharacterProgress)
            .where(CharacterProgress.wow_character == character)
            .order_by(CharacterProgress.record_date.desc())
            .limit(30)
        )

def main():
    global conn

    with conn.session as s:
        st.write("Connected!")
        
        characters = [character.__dict__ for character in s.scalars(select(WoWCharacter)).all()]
        characters_df = pd.DataFrame(characters)
        characters_df = characters_df[[col for col in characters_df.columns if not col.startswith('_')]]
        characters_df['display'] = characters_df.apply(lambda row: f"{row['name']} ({row.realm}-{row.region.upper()})", axis=1)
        
        chosen = st.selectbox(
            label='Select a character',
            options=characters_df['display'],
            index=None,
            on_change=
        )

        chosen_key = characters_df[characters_df['display'] == chosen]['key']

    st.write("Disconnected!")

if __name__ == "__main__":
    main()

