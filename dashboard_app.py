"""Interactive Streamlit dashboard for visualizing multi-agent test results."""
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from PIL import Image


st.set_page_config(
    page_title="Multi-Agent Beta Testing Dashboard",
    page_icon="🤖",
    layout="wide",
)


def load_csv_data(uploaded_file):
    """Load and parse CSV data."""
    df = pd.read_csv(uploaded_file)
    
    # Parse JSON columns
    if 'agent_proposals' in df.columns:
        df['agent_proposals_parsed'] = df['agent_proposals'].apply(
            lambda x: json.loads(x) if pd.notna(x) else []
        )
    if 'confidence_scores' in df.columns:
        df['confidence_scores_parsed'] = df['confidence_scores'].apply(
            lambda x: json.loads(x) if pd.notna(x) else {}
        )
    
    return df


def display_metrics(df):
    """Display key metrics in cards."""
    st.header("📊 Session Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_turns = len(df)
        st.metric("Total Turns", total_turns)
    
    with col2:
        success_rate = (df['success'].sum() / len(df) * 100) if len(df) > 0 else 0
        st.metric("Success Rate", f"{success_rate:.1f}%")
    
    with col3:
        safety_rate = (df['safety_pass'].sum() / len(df) * 100) if len(df) > 0 else 0
        st.metric("Safety Pass Rate", f"{safety_rate:.1f}%")
    
    with col4:
        avg_latency = df['latency'].mean() if len(df) > 0 else 0
        st.metric("Avg Latency", f"{avg_latency:.3f}s")


def display_agent_agreement(df):
    """Show agent agreement rates."""
    st.header("🤝 Agent Agreement Analysis")
    
    if 'agent_proposals_parsed' not in df.columns:
        st.warning("No agent proposal data available")
        return
    
    agreement_data = []
    
    for idx, row in df.iterrows():
        proposals = row['agent_proposals_parsed']
        if not proposals:
            continue
        
        # Count unique action types
        action_types = [p['action']['type'] for p in proposals if 'action' in p]
        unique_actions = len(set(action_types))
        total_agents = len(action_types)
        
        agreement_rate = (total_agents - unique_actions + 1) / total_agents if total_agents > 0 else 0
        
        agreement_data.append({
            'turn': row['turn'],
            'agreement_rate': agreement_rate * 100,
            'unique_proposals': unique_actions,
        })
    
    if agreement_data:
        agreement_df = pd.DataFrame(agreement_data)
        
        fig = px.line(
            agreement_df,
            x='turn',
            y='agreement_rate',
            title='Agent Agreement Rate Over Time',
            labels={'agreement_rate': 'Agreement %', 'turn': 'Turn'},
        )
        fig.update_traces(mode='lines+markers')
        st.plotly_chart(fig, use_container_width=True)
        
        avg_agreement = agreement_df['agreement_rate'].mean()
        st.info(f"📈 Average agent agreement: {avg_agreement:.1f}%")


def display_turn_details(df):
    """Interactive turn-by-turn viewer."""
    st.header("🔍 Turn-by-Turn Analysis")
    
    for idx, row in df.iterrows():
        turn_num = row['turn']
        
        with st.expander(f"Turn {turn_num}: {row['action_type']} → {row['action_target']}", expanded=(idx == 0)):
            col1, col2 = st.columns([1, 1])
            
            with col1:
                st.subheader("📸 Screenshot")
                screenshot_path = Path(row['screenshot_path'])
                
                if screenshot_path.exists():
                    try:
                        image = Image.open(screenshot_path)
                        st.image(image, use_column_width=True)
                    except Exception as e:
                        st.error(f"Could not load screenshot: {e}")
                else:
                    st.warning(f"Screenshot not found: {screenshot_path}")
            
            with col2:
                st.subheader("🤖 Agent Proposals")
                
                proposals = row.get('agent_proposals_parsed', [])
                if proposals:
                    for proposal in proposals:
                        agent_id = proposal.get('agent_id', 'Unknown')
                        action = proposal.get('action', {})
                        confidence = proposal.get('confidence', 0)
                        reasoning = proposal.get('reasoning', 'N/A')
                        
                        with st.container():
                            st.markdown(f"**Agent {agent_id}** (confidence: {confidence:.2f})")
                            st.code(f"Type: {action.get('type', 'N/A')}\nTarget: {action.get('target', 'N/A')}", language="json")
                            st.caption(reasoning)
                            st.divider()
                else:
                    st.info("No proposal data available")
                
                st.subheader("✅ Validation")
                st.write(f"**Success:** {row['success']}")
                st.write(f"**Safety Pass:** {row['safety_pass']}")
                st.write(f"**Latency:** {row['latency']:.3f}s")
                
                if row['validators']:
                    st.write(f"**Validators:** {row['validators']}")


def display_action_distribution(df):
    """Show distribution of action types."""
    st.header("📈 Action Distribution")
    
    action_counts = df['action_type'].value_counts()
    
    fig = px.pie(
        values=action_counts.values,
        names=action_counts.index,
        title='Action Types Distribution',
    )
    st.plotly_chart(fig, use_container_width=True)


def display_latency_chart(df):
    """Show latency over time."""
    st.header("⏱️ Latency Analysis")
    
    fig = px.bar(
        df,
        x='turn',
        y='latency',
        title='Latency per Turn',
        labels={'latency': 'Latency (seconds)', 'turn': 'Turn'},
        color='latency',
        color_continuous_scale='Viridis',
    )
    st.plotly_chart(fig, use_container_width=True)


def main():
    st.markdown("<h1 style='text-align: center;'>🤖 Multi-Agent Beta Testing Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Centered file upload
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        uploaded_file = st.file_uploader(
            "Upload Test Results CSV",
            type=['csv'],
            help="Upload the CSV file generated by your test session",
        )
    
    if uploaded_file is None:
        return
    
    # Load data
    try:
        df = load_csv_data(uploaded_file)
        
        session_id = df['session_id'].iloc[0] if len(df) > 0 else "Unknown"
        st.success(f"✅ Loaded {len(df)} turns from session: {session_id}")
        
    except Exception as e:
        st.error(f"Error loading CSV: {e}")
        return
    
    # Display sections
    st.markdown("---")
    display_metrics(df)
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    with col1:
        display_action_distribution(df)
    with col2:
        display_latency_chart(df)
    
    st.markdown("---")
    display_agent_agreement(df)
    st.markdown("---")
    display_turn_details(df)


if __name__ == "__main__":
    main()

