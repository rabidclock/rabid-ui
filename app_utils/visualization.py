import streamlit as st
import pandas as pd
import altair as alt
import ast
import re

def parse_voting_logs(logs):
    """
    Converts text logs into a structured DataFrame for graphing.
    """
    data = []
    for entry in logs:
        # We only care about lines starting with "Round"
        if entry.startswith("Round"):
            # Extract Round Number
            round_match = re.search(r"Round (\d+):", entry)
            if round_match:
                round_num = int(round_match.group(1))
                
                # Extract the dictionary part
                try:
                    dict_str = entry.split(":", 1)[1].strip()
                    # Safely evaluate the string representation of the dict
                    counts = ast.literal_eval(dict_str)
                    
                    for candidate, votes in counts.items():
                        data.append({
                            "Round": f"Round {round_num}", 
                            "Candidate": candidate, 
                            "Votes": votes
                        })
                except Exception as e:
                    print(f"Error parsing log line: {e}")
                    continue
                    
    return pd.DataFrame(data)

def render_voting_chart(logs):
    """
    Renders an interactive Donut Chart of the voting rounds.
    Includes a slider to scrub through the history of the vote.
    """
    df = parse_voting_logs(logs)
    
    if df.empty:
        st.warning("No voting data available to visualize.")
        return

    # 1. Round Selector (Interactive)
    # We define the order explicitly so 'Round 10' doesn't come before 'Round 2'
    unique_rounds = sorted(df['Round'].unique().tolist(), key=lambda x: int(x.split(' ')[1]))
    
    # --- FIX: HANDLE SINGLE ROUND (LANDSLIDE) ---
    # Prevents RangeError: min (0) is equal/bigger than max (0)
    if len(unique_rounds) > 1:
        selected_round = st.select_slider(
            "Round History", 
            options=unique_rounds, 
            value=unique_rounds[-1],
            help="Slide to see how votes shifted as candidates were eliminated."
        )
    else:
        # If only 1 round, auto-select it and skip the slider
        selected_round = unique_rounds[0]

    # 2. Filter Data for the selected round
    round_data = df[df['Round'] == selected_round]
    
    if round_data.empty:
        st.info(f"No votes recorded for {selected_round}.")
        return

    # 3. Define the Chart
    base = alt.Chart(round_data).encode(
        theta=alt.Theta("Votes", stack=True)
    )

    # The Donut Ring
    pie = base.mark_arc(outerRadius=100, innerRadius=60).encode(
        color=alt.Color("Candidate", legend=alt.Legend(orient="right")),
        order=alt.Order("Votes", sort="descending"),
        tooltip=["Candidate", "Votes", alt.Tooltip("Votes", format=".0f")]
    )

    # Labels (Only show if votes > 0)
    text = base.mark_text(radius=120).encode(
        text=alt.Text("Votes", format=".0f"),
        order=alt.Order("Votes", sort="descending"),
        color=alt.value("#e0e0e0")  # Light text for dark mode
    ).transform_filter(
        alt.datum.Votes > 0
    )

    # Combine
    chart = (pie + text).properties(
        title=f"Vote Distribution - {selected_round}",
        height=300
    )

    # --- FIX: Updated syntax for newer Streamlit versions ---
    try:
        st.altair_chart(chart, width="stretch")
    except TypeError:
        # Fallback for older Streamlit versions just in case
        st.altair_chart(chart, use_container_width=True)