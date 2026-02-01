import streamlit as st
import time
import plotly.graph_objects as go

def _get_arena_theme():
    """Returns consistent color mapping for the Blood Red Arena theme."""
    return {
        "alive": "#00ffcc",  # Neon Teal
        "dead": "#8a0303",   # Blood Red
        "background": "rgba(0,0,0,0)",
        "font": "white",
        "swatch": ['#8a0303', '#ff4b4b', '#330000', '#5c0000', '#0e1117']
    }

def render_ranked_choice_rounds(round_tallies):
    """Renders donut charts for each round, filtering out 0% entries for clarity."""
    if not round_tallies:
        st.warning("⚠️ No voting data available for runoff visualization.")
        return

    theme = _get_arena_theme()
    st.markdown("### 🗳️ Voting Runoff Analysis")
    
    cols = st.columns(len(round_tallies))
    
    for i, tally in enumerate(round_tallies):
        with cols[i]:
            st.caption(f"Round {i+1}")
            
            # --- THE CLEANUP: Remove candidates with 0 votes ---
            filtered_tally = {k: v for k, v in tally.items() if v > 0}
            
            if not filtered_tally:
                st.info("No votes recorded in this round.")
                continue

            labels = list(filtered_tally.keys())
            values = list(filtered_tally.values())

            fig = go.Figure(data=[go.Pie(
                labels=labels, 
                values=values, 
                hole=.6,
                marker=dict(colors=theme["swatch"]),
                textinfo='percent',
                hoverinfo='label+value'
            )])

            fig.update_layout(
                showlegend=(i == 0), 
                margin=dict(t=10, b=10, l=10, r=10),
                paper_bgcolor=theme["background"],
                plot_bgcolor=theme["background"],
                font=dict(color=theme["font"]),
                height=250
            )
            st.plotly_chart(fig, use_container_width=True, key=f"rc_round_{i}")

def render_battle(candidate_names, logs, winner_name):
    """Renders the animated Battle Royale arena status indicators."""
    theme = _get_arena_theme()
    
    st.markdown("""
        <style>
            .arena-container {
                border: 2px solid #8a0303;
                border-radius: 10px;
                padding: 20px;
                background-color: #0e1117;
                box-shadow: 0 0 20px #8a0303;
            }
        </style>
    """, unsafe_allow_html=True)

    with st.expander(f"⚔️ ARENA STATUS: {len(candidate_names)} COMBATANTS", expanded=True):
        status_placeholder = st.empty()
        agent_status = {name: "🟢 ALIVE" for name in candidate_names}
        
        def _draw_status_chart(status_dict):
            names = list(status_dict.keys())
            health = [1 if "ALIVE" in s else 0.1 for s in status_dict.values()]
            colors = [theme["alive"] if h == 1 else theme["dead"] for h in health]

            fig = go.Figure(go.Bar(
                x=names,
                y=health,
                marker_color=colors,
                text=[s for s in status_dict.values()],
                textposition='auto',
            ))

            fig.update_layout(
                height=250,
                margin=dict(t=20, b=20, l=20, r=20),
                paper_bgcolor=theme["background"],
                plot_bgcolor=theme["background"],
                font=dict(color=theme["font"]),
                yaxis=dict(visible=False),
                xaxis=dict(tickangle=-45)
            )
            
            with status_placeholder.container():
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

        _draw_status_chart(agent_status)
        st.divider()
        st.caption("🩸 *Chronology of Betrayal*")
        
        log_container = st.container(height=300) 
        for log_line in logs:
            time.sleep(1.2) 
            round_victims = [name for name in candidate_names if name in log_line]
            if round_victims:
                for v in round_victims:
                    agent_status[v] = "💀 ELIMINATED"
                _draw_status_chart(agent_status)
            
            with log_container:
                st.markdown(f"> {log_line}")
        
        st.divider()
        if winner_name and "No One" not in winner_name:
            st.success(f"🏆 **VICTORY:** {winner_name} is the last intelligence standing.")
        else:
            st.error("☠️ **TOTAL PARTY KILL:** Mutual destruction confirmed.")