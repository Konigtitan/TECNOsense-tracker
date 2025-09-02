import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter, And
from sklearn.linear_model import LinearRegression
import plotly.express as px
import numpy as np
from datetime import datetime, timedelta

# Page Configuration
st.set_page_config(page_title="TECNOsense Dashboard", page_icon="⚙️", layout="wide")

# Firebase Connection (Runs only once)
@st.cache_resource
def initialize_firebase():
    try:
        cred = credentials.Certificate("firebase_credentials.json")
        if not firebase_admin._apps: firebase_admin.initialize_app(cred)
        return firestore.client()
    except Exception as e:
        st.error(f"Failed to connect to Firebase: {e}."); return None

db = initialize_firebase()

# App State Management
if 'selected_room' not in st.session_state: st.session_state.selected_room = None
if 'hours_to_show' not in st.session_state: st.session_state.hours_to_show = 24
if 'latest_data' not in st.session_state: st.session_state.latest_data = None
if 'historical_data' not in st.session_state: st.session_state.historical_data = pd.DataFrame()

# Data Fetching from Firestore
@st.cache_data(ttl=10)
def fetch_firestore_data(_db, query_info):
    collection_ref = _db.collection('room_data_aggregated')
    query = collection_ref
    filters = []
    if 'room_id' in query_info: filters.append(FieldFilter('room_id', '==', query_info['room_id']))
    if 'start_time' in query_info: filters.append(FieldFilter('timestamp', '>=', query_info['start_time']))
    if len(filters) > 1: query = query.where(filter=And(filters))
    elif len(filters) == 1: query = query.where(filter=filters[0])
    query = query.order_by("timestamp", direction=firestore.Query.DESCENDING)
    if 'limit' in query_info: query = query.limit(query_info['limit'])
    try:
        docs = query.stream()
        records = [doc.to_dict() for doc in docs]
        if not records: return pd.DataFrame()
        df = pd.DataFrame(records)
        if 'timestamp' in df.columns: df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    except Exception as e:
        st.error(f"Firestore Query Error: {e}"); return pd.DataFrame()

# AI/ML Model
def analyze_occupancy_pattern(df):
    if df.shape[0] < 2: return None, "Not enough data."
    df_copy = df.copy(); df_copy['hour'] = df_copy['timestamp'].dt.hour
    hourly_avg = df_copy.groupby('hour')['avg_person_count'].mean().reset_index()
    
    # Handle missing data (NaN) by filling it with 0.
    # This prevents the machine learning model from crashing.
    hourly_avg['avg_person_count'] = hourly_avg['avg_person_count'].fillna(0)
    
    if hourly_avg.shape[0] < 2: return None, "Not enough hourly variation."
    model = LinearRegression(); X = hourly_avg[['hour']]; y = hourly_avg['avg_person_count']
    model.fit(X, y); hourly_avg['predicted_occupancy'] = model.predict(X)
    return hourly_avg, "Analysis complete."

# UI Rendering
if not db: st.stop()

st.title("TECNOSense: Enhanced Privacy-First Campus Occupancy Platform")

# Room Selection
room_list = ["Clasroom 1", "Classroom 2", "Lab"]
if st.session_state.selected_room is None: st.session_state.selected_room = room_list[0]
st.radio("Select a Room", options=room_list, key='selected_room', horizontal=True)

st.markdown("---")

# Real-Time Status
col1, col2, _ = st.columns([1.3, 2, 5])
with col1: st.header(f"Real-Time Status")
with col2:
    st.write("")
    if st.button("Refresh Now"):
        st.cache_data.clear(); st.toast("Data refreshed!", icon="✅")

latest_data_query = {"room_id": st.session_state.selected_room, "limit": 1}
latest_data_df = fetch_firestore_data(db, latest_data_query)
if not latest_data_df.empty: st.session_state.latest_data = latest_data_df.iloc[0]

col1, col2, col3, col4 = st.columns(4)
if st.session_state.latest_data is not None:
    data = st.session_state.latest_data
    col1.metric("Occupancy Status", "Occupied" if data.get('is_occupied') else "Empty")
    col2.metric("Person Count (Avg)", f"{data.get('avg_person_count', 0)}")
    col3.metric("Light Intensity (Avg)", f"{data.get('avg_light_intensity', 0):.1f} Lux")
    col4.metric("Air Quality (Avg)", f"{data.get('avg_air_quality_ppm', 0):.1f} PPM")
    if data.get('is_smoke_detected'): st.error("🚨 SMOKE DETECTED!", icon="🔥")
    else: st.success("Safety Status: Normal", icon="✅")
else:
    col1.metric("Occupancy Status", "Loading..."); col2.metric("Person Count", "--")
    col3.metric("Light Intensity", "-- Lux"); col4.metric("Air Quality", "-- PPM")

st.markdown("---")

# Historical Data Visualization
st.header(f"Historical Analysis")
st.write("##### Select a Time Range")
cols = st.columns(4)
if cols[0].button("Last 12 Hours", use_container_width=True): st.session_state.hours_to_show = 12
if cols[1].button("Last 24 Hours", use_container_width=True): st.session_state.hours_to_show = 24
if cols[2].button("Last 7 Days", use_container_width=True): st.session_state.hours_to_show = 168
if cols[3].button("Last 30 Days", use_container_width=True): st.session_state.hours_to_show = 720

start_time_dt = datetime.now() - timedelta(hours=st.session_state.hours_to_show)
historical_query = {"room_id": st.session_state.selected_room, "start_time": start_time_dt}
historical_df = fetch_firestore_data(db, historical_query)

if not historical_df.empty:
    st.session_state.historical_data = historical_df.iloc[::-1].reset_index(drop=True)

if not st.session_state.historical_data.empty:
    df_to_display = st.session_state.historical_data
    start_time_actual = df_to_display['timestamp'].min().strftime('%Y-%m-%d %H:%M:%S')
    end_time_actual = df_to_display['timestamp'].max().strftime('%Y-%m-%d %H:%M:%S')
    st.info(f"Displaying data from **{start_time_actual}** to **{end_time_actual}**.")

    st.subheader("Occupancy and Sensor Readings")
    fig_count = px.line(df_to_display, x='timestamp', y='avg_person_count', title='Average Person Count Over Time')
    st.plotly_chart(fig_count, use_container_width=True)
    fig_sensors = px.line(df_to_display, x='timestamp', y=['avg_light_intensity', 'avg_air_quality_ppm'], title='Average Sensor Readings')
    st.plotly_chart(fig_sensors, use_container_width=True)

    st.markdown("---")
    st.header(f"AI-Powered Occupancy Pattern")
    pattern_df, message = analyze_occupancy_pattern(df_to_display)
    if pattern_df is not None:
        peak_hour = pattern_df.loc[pattern_df['avg_person_count'].idxmax()]
        st.write(f"**Insight:** Occupancy peaks around **{int(peak_hour['hour'])}:00**.")
        fig_pattern = px.scatter(pattern_df, x='hour', y='avg_person_count', title='Average Occupancy by Hour')
        fig_pattern.add_traces(px.line(pattern_df, x='hour', y='predicted_occupancy').data)
        fig_pattern.data[1].name = 'Usage Trend'; fig_pattern.data[1].line.color = 'red'
        st.plotly_chart(fig_pattern, use_container_width=True)
    else:
        st.warning(message)
else:
    st.warning(f"No historical data found in the selected time range.")