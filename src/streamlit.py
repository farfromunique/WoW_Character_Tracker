from typing import List, Optional, Sequence, Tuple
from csv import reader as csv_reader
import streamlit as st
import pandas as pd
from sqlalchemy import text, select
from sqlalchemy.orm import Session
from matplotlib.axes import Axes
from matplotlib.dates import DateFormatter, WeekdayLocator
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from datetime import date, timedelta
from calendar import TUESDAY

from data_models import WoWCharacter, CharacterProgress, GearLog

conn = st.connection('wow_char_db', type='sql')
conn.engine.echo = True

VALID_SLOTS = [
    'HEAD',
    'NECK',
    'SHOULDER',
    'BACK',
    'CHEST',
    'WAIST',
    'HANDS',
    'WRIST',
    'LEGS',
    'FEET',
    'FINGER_1',
    'FINGER_2',
    'TRINKET_1',
    'TRINKET_2',
    'MAIN_HAND',
    'OFF_HAND'
]


def get_todays_progress(s: Session, character: WoWCharacter) -> CharacterProgress:
    global conn

    today = date.today()
    offset = (today.weekday() - TUESDAY) % 7
    last_tuesday = today - timedelta(days=offset)
    if last_tuesday == today:
        last_tuesday -= timedelta(days=7)

    
    stmt = text("""
        SELECT
            c.id,
            max(l.average_item_level) as ilvl,
            bool_or(l.pinnacle_quest_done) as pinnacle,
            bool_or(profession_1_quest_done) as prof_1,
            bool_or(profession_2_quest_done) as prof_2,
            sum(delves_completed) as delves_completed,
            string_agg(to_char(l.record_date, 'yyyy-mm-dd'), '|' order by l.record_date ASC)
        FROM progress_log as l
        LEFT JOIN wow_character as c
            ON l.character_id = c.id
        WHERE 1=1
        AND (false
            OR c.level = 80
            OR c.level is NULL
        )
        AND l.record_date >= CASE
            WHEN EXTRACT(DOW FROM CURRENT_DATE) = 2 THEN CURRENT_DATE - INTERVAL '7 days'
            ELSE CURRENT_DATE - INTERVAL '1 day' * ((EXTRACT(DOW FROM CURRENT_DATE) + 5) % 7)
        END
        AND c.key = :character_key
        GROUP BY c.id
    """).bindparams(character_key=character.key)

    result = s.execute(
        statement=stmt
    ).first()

    if result is None:
        raise Exception("No rows returned")
    
    char_prog = CharacterProgress(
        character_id=result[0],
        record_date=result[6].split('|')[-1],
        average_item_level=result[1],
        pinnacle_quest_done=result[2],
        profession_1_quest_done=result[3],
        profession_2_quest_done=result[4],
        delves_completed=result[5]
    )

    s.add(char_prog)
    s.commit()

    f"out: {char_prog.id}"
    return char_prog

def get_gear_chart(character: WoWCharacter) -> Tuple[Figure, Axes]:
    global VALID_SLOTS
    gear_logs = get_logs(character)

    logs_df = pd.DataFrame(
        [gl.__dict__ for gl in gear_logs]
    )
    
    logs_df['_record_date'] = logs_df.apply(lambda x: x['record_date'].isoformat(), axis=1)
    logs_df['d_record_date'] = logs_df.apply(lambda x: x['record_date'], axis=1)
    logs_df['_slot'] = logs_df['slot']
    logs_df.set_index(['_slot', 'd_record_date'], inplace=True)
    logs_df.sort_index(inplace=True)

    logs_df.drop(columns=['_sa_instance_state'], inplace=True)

    for slot in VALID_SLOTS:
        try:
            test = logs_df.loc[slot]  # noqa: F841
        except KeyError:
            VALID_SLOTS.remove(slot)
            pass
    
    filtered_df = logs_df.loc[VALID_SLOTS]

    filtered_df = filtered_df[['ilevel']]

    grouped_df = filtered_df.groupby('d_record_date').sum()

    grouped_df['average_ilevel'] = grouped_df.apply(lambda x: int(x['ilevel'] / 16), axis=1)

    final_df = grouped_df.reset_index().sort_index()

    final_df.drop('ilevel', axis=1, inplace=True)
    
    min_ilevel = final_df['average_ilevel'].min()
    max_ilevel = final_df['average_ilevel'].max()

    early = final_df['d_record_date'].min()
    late = final_df['d_record_date'].max()

    
    fig, ax = plt.subplots()

    # Plot the line chart
    ax.plot(
        'd_record_date',
        'average_ilevel',
        data=final_df,
        marker='o'
    )

    annotations = get_annotations()
    for a in annotations:
        _year, _month, _day = a[0].split('-')
        x_coord = date(int(_year), int(_month), int(_day))
        ax.axvline(x=x_coord, color="black", linestyle="--")  # type: ignore
        ax.annotate(a[1], xy=(x_coord, max_ilevel+8))  # type: ignore

    ax.xaxis.set_major_locator(WeekdayLocator(byweekday=1, interval=1))
    ax.xaxis.set_major_formatter(DateFormatter('%d %b'))


    # Set x-axis limits
    start_value = min_ilevel - 10  # Replace with your desired starting value
    end_value = max_ilevel + 10
    ax.set_ylim(start_value, end_value)
    ax.set_xlim(early, late)

    return fig, ax

def get_logs(character: WoWCharacter, count: int = 30) -> Sequence[GearLog]:
    global conn

    with conn.session as s:
        return s.scalars(
            select(GearLog)
            .where(GearLog.wow_character == character)
            .where(GearLog.record_date >= (date.today() - timedelta(days=count)))
            .order_by(GearLog.record_date.desc())
        ).all()

def get_annotations() -> List[List[str]]:
    output = []
    with open('ANNOTATIONS.csv', mode='r', newline='\n') as f:
        ann = csv_reader(f, delimiter='|', quotechar='"')

        for line in ann:
            output.append(line)
    
    return output[1:]

def prev_char(choices: List):
    selected = st.session_state['this_char']
    if selected in choices:
        idx = choices.index(selected)
        try:
            st.session_state['this_char'] = choices[idx-1]
        except KeyError:
            pass
    
    return

def next_char(choices: List):
    selected = st.session_state['this_char']
    if selected in choices:
        idx = choices.index(selected)
        try:
            st.session_state['this_char'] = choices[idx+1]
        except KeyError:
            pass
    
    return
    

def main():
    global conn
    global VALID_SLOTS

    with conn.session as s:
        characters = []
        #characters = [character.__dict__ for character in s.scalars(select(WoWCharacter)).all()]
        for c in s.scalars(select(WoWCharacter)).all():
            char_key = c.key
            characters.append({
                'key': char_key,
                'obj': c,
                'display': f"{c.name} ({c.realm}-{c.region.upper()})",
                'region': c.region,
                'name': c.name,
                'realm': c.realm,
                'level': c.level
            })
        
        characters_df = pd.DataFrame(characters)
        characters_df = characters_df[[col for col in characters_df.columns if not col.startswith('_')]]        
        
        st.title("Character Progress Tracker")

        # Select character
        st.session_state["this_char"] = characters_df['display'][0]
        col1, col2, col3 = st.columns([1,8,1])

        col1.button(
            label="<",
            on_click=prev_char,
            kwargs={"choices": characters_df['display']}
        )
        col2.subheader(body=st.session_state["this_char"])
        col3.button(
            label="\>",
            on_click=next_char,
            kwargs={"choices": characters_df['display']}
        )

        this_char = [c['obj'] for c in characters if c['display'] == st.session_state["this_char"]][0]
        assert(isinstance(this_char, WoWCharacter))
        # Filter progress records for the selected character
        char_data = get_todays_progress(s, this_char)
        st.session_state['progress_id'] = char_data.id
        st.session_state['previous_delves'] = char_data.delves_completed
        char_data: CharacterProgress = s.scalar(
            select(CharacterProgress)
            .where(CharacterProgress.id == st.session_state['progress_id'])) # type: ignore

        st.toggle(
            label='Pinnacle Quest Completed?',
            value=char_data.pinnacle_quest_done,
            key='pinnacle_done'
        )
        st.toggle(
            label='Profession Quest 1 Completed?',
            value=char_data.profession_1_quest_done,
            key='prof_1_done'
        )
        st.toggle(
            label='Profession Quest 2 Completed?',
            value=char_data.profession_2_quest_done,
            key='prof_2_done'
        )
        st.number_input(
            label="Delves completed (today)",
            value=0,
            key='todays_delves'
        )
        st.number_input(
            label="Delves completed (This week)",
            value=st.session_state['previous_delves']+st.session_state['todays_delves'],
            disabled=True
        )

        char_data.pinnacle_quest_done = st.session_state['pinnacle_done']
        char_data.profession_1_quest_done = st.session_state['prof_1_done']
        char_data.profession_2_quest_done = st.session_state['prof_2_done']
        s.commit()
        
        fig, ax = get_gear_chart(this_char)

        # Display the plot in Streamlit
        st.pyplot(fig)

    st.write("Disconnected!")

if __name__ == "__main__":
    main()

