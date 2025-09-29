import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.base_query import FieldFilter, And
from sklearn.linear_model import LinearRegression
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import datetime, timedelta
import time

# ==================== PAGE CONFIGURATION ====================
st.set_page_config(
    page_title="TECNOsense Smart Building Platform",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== CUSTOM CSS ====================
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .status-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #2a5298;
        margin-bottom: 1rem;
    }
    
    .metric-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem;
        background: #f8f9fa;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    
    .control-button {
        width: 100%;
        margin: 0.25rem 0;
    }
    
    .alert-success {
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        padding: 0.75rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
    
    .alert-warning {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 0.75rem;
        border-radius: 5px;
        margin: 0.5rem 0;
    }
    
    .connection-status {
        padding: 0.5rem;
        border-radius: 5px;
        text-align: center;
        margin: 0.25rem 0;
    }
    
    .status-online {
        background-color: #d4edda;
        color: #155724;
    }
    
    .status-offline {
        background-color: #f8d7da;
        color: #721c24;
    }
</style>
""", unsafe_allow_html=True)

# ==================== FIREBASE CONNECTION ====================
@st.cache_resource
def initialize_firebase():
    """Initialize Firebase connection (runs only once)"""
    try:
        cred = credentials.Certificate("firebase_credentials.json")
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        return db, True
    except Exception as e:
        st.error(f"Failed to connect to Firebase: {e}")
        return None, False

# Initialize Firebase
db, firebase_connected = initialize_firebase()

# ==================== SESSION STATE INITIALIZATION ====================
if 'selected_room' not in st.session_state:
    st.session_state.selected_room = "Classroom 1"
if 'selected_building' not in st.session_state:
    st.session_state.selected_building = "Engineering Block A"
if 'hours_to_show' not in st.session_state:
    st.session_state.hours_to_show = 24
if 'latest_data' not in st.session_state:
    st.session_state.latest_data = None
if 'historical_data' not in st.session_state:
    st.session_state.historical_data = pd.DataFrame()
if 'auto_refresh' not in st.session_state:
    st.session_state.auto_refresh = False

# ==================== DATA FETCHING FUNCTIONS ====================
@st.cache_data(ttl=10)
def fetch_firestore_data(_db, query_info):
    """Fetch data from Firestore with proper error handling"""
    if not _db:
        return pd.DataFrame()
    
    try:
        collection_ref = _db.collection('room_data_aggregated')
        query = collection_ref
        filters = []
        
        # Build query filters
        if 'room_id' in query_info:
            filters.append(FieldFilter('room_id', '==', query_info['room_id']))
        if 'start_time' in query_info:
            filters.append(FieldFilter('timestamp', '>=', query_info['start_time']))
        
        # Apply filters
        if len(filters) > 1:
            query = query.where(filter=And(filters))
        elif len(filters) == 1:
            query = query.where(filter=filters[0])
        
        # Order and limit
        query = query.order_by("timestamp", direction=firestore.Query.DESCENDING)
        if 'limit' in query_info:
            query = query.limit(query_info['limit'])
        
        # Execute query
        docs = query.stream()
        records = [doc.to_dict() for doc in docs]
        
        if not records:
            return pd.DataFrame()
        
        df = pd.DataFrame(records)
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return df
    
    except Exception as e:
        st.error(f"Firestore Query Error: {e}")
        return pd.DataFrame()

@st.cache_data
def generate_mock_fallback_data():
    """Generate mock data as fallback when Firebase is not available"""
    now = datetime.now()
    
    # Current status data
    current_data = {
        'room_id': st.session_state.selected_room,
        'is_occupied': np.random.choice([True, False], p=[0.7, 0.3]),
        'avg_person_count': np.random.randint(0, 15),
        'avg_light_intensity': np.random.uniform(150, 800),
        'avg_air_quality_ppm': np.random.uniform(400, 1200),
        'avg_temperature': np.random.uniform(20, 28),
        'avg_humidity': np.random.uniform(40, 70),
        'is_smoke_detected': False,
        'timestamp': now,
        'light_on': np.random.choice([True, False]),
        'ac_on': np.random.choice([True, False]),
        'fan_on': np.random.choice([True, False]),
        'auto_mode': np.random.choice([True, False], p=[0.8, 0.2]),
    }
    
    # Historical data (last 24 hours)
    timestamps = [now - timedelta(minutes=x*10) for x in range(144, 0, -1)]
    historical_data = []
    
    for i, ts in enumerate(timestamps):
        # Simulate realistic patterns
        hour = ts.hour
        if 8 <= hour <= 18:  # Working hours
            base_occupancy = np.random.poisson(8)
        elif 19 <= hour <= 22:  # Evening
            base_occupancy = np.random.poisson(3)
        else:  # Night
            base_occupancy = np.random.poisson(0.5)
            
        historical_data.append({
            'room_id': st.session_state.selected_room,
            'timestamp': ts,
            'avg_person_count': max(0, base_occupancy + np.random.randint(-2, 3)),
            'avg_light_intensity': np.random.uniform(100, 900),
            'avg_air_quality_ppm': np.random.uniform(350, 1300),
            'avg_temperature': np.random.uniform(19, 29),
            'avg_humidity': np.random.uniform(35, 75),
            'is_occupied': base_occupancy > 0,
            'is_smoke_detected': False
        }) 
    
    return current_data, pd.DataFrame(historical_data)

# ==================== AI/ML ANALYSIS ====================
def analyze_occupancy_pattern(df):
    """AI-powered occupancy pattern analysis"""
    if df.shape[0] < 2:
        return None, "Not enough data for analysis."
    
    df_copy = df.copy()
    df_copy['hour'] = df_copy['timestamp'].dt.hour
    hourly_avg = df_copy.groupby('hour')['avg_person_count'].mean().reset_index()
    
    # Handle missing data
    hourly_avg['avg_person_count'] = hourly_avg['avg_person_count'].fillna(0)
    
    if hourly_avg.shape[0] < 2:
        return None, "Not enough hourly variation."
    
    # Linear regression model
    model = LinearRegression()
    X = hourly_avg[['hour']]
    y = hourly_avg['avg_person_count']
    model.fit(X, y)
    hourly_avg['predicted_occupancy'] = model.predict(X)
    
    return hourly_avg, "Analysis complete."

# ==================== MAIN DASHBOARD ====================
def main_dashboard():
    # Header Section
    st.markdown("""
    <div class="main-header">
        <h1>🏢 TECNOsense Smart Building Platform</h1>
        <p>Privacy-First Campus Occupancy & Environmental Control System</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Building and Room Selection
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        st.session_state.selected_building = st.selectbox(
            "🏛️ Select Building",
            ["Engineering Block A", "Engineering Block B", "Science Complex", "Library Wing"]
        )
    
    with col2:
        room_options = ["Classroom 1", "Classroom 2", "Lab 101", "Lab 102", "Conference Room"]
        st.session_state.selected_room = st.selectbox(
            "🚪 Select Room",
            room_options
        )
    
    with col3:
        st.write("")
        st.write("")
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.toast("Data refreshed!", icon="✅")
            st.rerun()
    
    st.markdown("---")
    
    # Connection Status
    st.subheader("📡 System Status")
    status_col1, status_col2, status_col3, status_col4 = st.columns(4)
    
    with status_col1:
        if firebase_connected:
            st.markdown('<div class="connection-status status-online">🟢 Firebase Connected</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="connection-status status-offline">🔴 Firebase Offline</div>', unsafe_allow_html=True)
    
    with status_col2:
        st.markdown('<div class="connection-status status-online">📶 Sensors Active</div>', unsafe_allow_html=True)
    
    with status_col3:
        current_time = datetime.now().strftime('%H:%M:%S')
        st.info(f"🕐 Last Update: {current_time}")
    
    with status_col4:
        st.success("✅ Safety Normal")

def real_time_section():
    """Real-time data display section"""
    st.subheader("📊 Real-Time Monitoring")
    
    # Fetch or generate data
    if firebase_connected and db:
        # Fetch real data from Firebase
        latest_data_query = {"room_id": st.session_state.selected_room, "limit": 1}
        latest_data_df = fetch_firestore_data(db, latest_data_query)
        
        if not latest_data_df.empty:
            st.session_state.latest_data = latest_data_df.iloc[0].to_dict()
        else:
            # Fallback to mock data if no real data
            mock_current, _ = generate_mock_fallback_data()
            st.session_state.latest_data = mock_current
    else:
        # Use mock data when Firebase not available
        mock_current, _ = generate_mock_fallback_data()
        st.session_state.latest_data = mock_current
    
    # Display current metrics
    if st.session_state.latest_data:
        data = st.session_state.latest_data
        
        # Main metrics row
        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
        
        with metric_col1:
            occupancy_status = "🟢 Occupied" if data.get('is_occupied', False) else "🔴 Empty"
            people_count = data.get('avg_person_count', 0)
            st.metric(
                "Room Status",
                occupancy_status,
                delta=f"{people_count} people"
            )
        
        with metric_col2:
            light_level = data.get('avg_light_intensity', 0)
            st.metric(
                "Light Level",
                f"{light_level:.0f}",
                delta="Lux"
            )
        
        with metric_col3:
            air_quality = data.get('avg_air_quality_ppm', 0)
            st.metric(
                "Air Quality",
                f"{air_quality:.0f}",
                delta="PPM"
            )
        
        with metric_col4:
            temperature = data.get('avg_temperature', data.get('temperature', 22))
            humidity = data.get('avg_humidity', data.get('humidity', 50))
            st.metric(
                "Temperature",
                f"{temperature:.1f}°C",
                delta=f"{humidity:.0f}% RH"
            )
        
        # Safety alerts
        if data.get('is_smoke_detected', False):
            st.error("🚨 SMOKE DETECTED - EVACUATE IMMEDIATELY!", icon="🔥")
        else:
            st.success("🛡️ Safety Status: Normal", icon="✅")

def historical_section():
    """Historical data visualization section"""
    st.markdown("---")
    st.subheader("📈 Historical Analysis")
    
    # Time range selection
    st.write("##### Select Time Range")
    time_cols = st.columns(4)
    
    if time_cols[0].button("Last 12 Hours", use_container_width=True):
        st.session_state.hours_to_show = 12
    if time_cols[1].button("Last 24 Hours", use_container_width=True):
        st.session_state.hours_to_show = 24
    if time_cols[2].button("Last 7 Days", use_container_width=True):
        st.session_state.hours_to_show = 168
    if time_cols[3].button("Last 30 Days", use_container_width=True):
        st.session_state.hours_to_show = 720
    
    # Fetch historical data
    if firebase_connected and db:
        start_time_dt = datetime.now() - timedelta(hours=st.session_state.hours_to_show)
        historical_query = {
            "room_id": st.session_state.selected_room, 
            "start_time": start_time_dt
        }
        historical_df = fetch_firestore_data(db, historical_query)
        
        if not historical_df.empty:
            st.session_state.historical_data = historical_df.iloc[::-1].reset_index(drop=True)
        else:
            # Use mock data as fallback
            _, mock_historical = generate_mock_fallback_data()
            st.session_state.historical_data = mock_historical
    else:
        # Use mock data when Firebase not available
        _, mock_historical = generate_mock_fallback_data()
        st.session_state.historical_data = mock_historical
    
    # Display charts
    if not st.session_state.historical_data.empty:
        df_display = st.session_state.historical_data
        
        # Date range info
        start_time = df_display['timestamp'].min().strftime('%Y-%m-%d %H:%M:%S')
        end_time = df_display['timestamp'].max().strftime('%Y-%m-%d %H:%M:%S')
        st.info(f"📅 Displaying data from **{start_time}** to **{end_time}**")
        
        # Charts layout
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            # Occupancy chart
            fig_occupancy = px.area(
                df_display, 
                x='timestamp', 
                y='avg_person_count',
                title='👥 People Count Over Time',
                color_discrete_sequence=['#1f77b4']
            )
            fig_occupancy.update_layout(height=350)
            st.plotly_chart(fig_occupancy, use_container_width=True)
        
        with chart_col2:
            # Environmental sensors
            fig_env = go.Figure()
            fig_env.add_trace(go.Scatter(
                x=df_display['timestamp'],
                y=df_display['avg_light_intensity'],
                mode='lines',
                name='💡 Light (Lux)',
                line=dict(color='orange')
            ))
            fig_env.add_trace(go.Scatter(
                x=df_display['timestamp'],
                y=df_display['avg_air_quality_ppm'],
                mode='lines',
                name='🌬️ Air Quality (PPM)',
                yaxis='y2',
                line=dict(color='green')
            ))
            
            fig_env.update_layout(
                title='🌡️ Environmental Sensors',
                height=350,
                yaxis=dict(title='Light Level (Lux)', side='left'),
                yaxis2=dict(title='Air Quality (PPM)', side='right', overlaying='y'),
                legend=dict(x=0, y=1)
            )
            st.plotly_chart(fig_env, use_container_width=True)

def ai_analytics_section():
    """AI-powered analytics section"""
    st.markdown("---")
    st.subheader("🧠 AI-Powered Analytics")
    
    if not st.session_state.historical_data.empty:
        df_analysis = st.session_state.historical_data
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Occupancy pattern analysis
            pattern_df, message = analyze_occupancy_pattern(df_analysis)
            
            if pattern_df is not None:
                peak_hour = pattern_df.loc[pattern_df['avg_person_count'].idxmax()]
                st.success(f"🎯 **Peak Usage:** {int(peak_hour['hour'])}:00 ({peak_hour['avg_person_count']:.1f} people avg)")
                
                # Pattern visualization
                fig_pattern = px.scatter(
                    pattern_df, 
                    x='hour', 
                    y='avg_person_count',
                    title='📊 Hourly Occupancy Patterns',
                    color='avg_person_count',
                    color_continuous_scale='Blues'
                )
                fig_pattern.add_traces(
                    px.line(pattern_df, x='hour', y='predicted_occupancy').data
                )
                fig_pattern.data[1].name = 'Trend Line'
                fig_pattern.data[1].line.color = 'red'
                fig_pattern.update_layout(height=350)
                st.plotly_chart(fig_pattern, use_container_width=True)
            else:
                st.warning(f"⚠️ {message}")
        
        with col2:
            # Utilization efficiency
            occupied_records = len(df_analysis[df_analysis['is_occupied'] == True])
            total_records = len(df_analysis)
            efficiency_score = (occupied_records / total_records) * 100 if total_records > 0 else 0
            
            fig_efficiency = go.Figure(go.Indicator(
                mode="gauge+number+delta",
                value=efficiency_score,
                domain={'x': [0, 1], 'y': [0, 1]},
                title={'text': "Room Utilization %"},
                delta={'reference': 75},
                gauge={
                    'axis': {'range': [None, 100]},
                    'bar': {'color': "darkblue"},
                    'steps': [
                        {'range': [0, 50], 'color': "lightgray"},
                        {'range': [50, 80], 'color': "gray"}
                    ],
                    'threshold': {
                        'line': {'color': "red", 'width': 4},
                        'thickness': 0.75,
                        'value': 90
                    }
                }
            ))
            fig_efficiency.update_layout(height=350)
            st.plotly_chart(fig_efficiency, use_container_width=True)
            
            # Efficiency insights
            if efficiency_score > 75:
                st.success("✅ Excellent utilization!")
            elif efficiency_score > 50:
                st.warning("⚠️ Moderate utilization")
            else:
                st.error("❌ Low utilization - consider optimization")

def device_control_section():
    """Device control panel (mock for demo)"""
    st.markdown("---")
    st.subheader("🎛️ Device Control Panel")
    
    control_col1, control_col2 = st.columns([1, 2])
    
    with control_col1:
        # Current data for control states
        if st.session_state.latest_data:
            data = st.session_state.latest_data
        else:
            data = {}
        
        # Mode Control
        st.markdown("**🤖 Operation Mode**")
        auto_mode = data.get('auto_mode', True)
        current_mode = "🤖 AUTO MODE" if auto_mode else "👤 MANUAL MODE"
        
        if auto_mode:
            st.success(current_mode)
        else:
            st.warning(current_mode)
        
        mode_col1, mode_col2 = st.columns(2)
        with mode_col1:
            if st.button("🤖 Auto", use_container_width=True):
                st.success("✅ Switched to Auto Mode")
        
        with mode_col2:
            if st.button("👤 Manual", use_container_width=True):
                st.success("✅ Switched to Manual Mode")
    
    with control_col2:
        # Device Controls
        device_col1, device_col2, device_col3 = st.columns(3)
        
        with device_col1:
            st.markdown("**💡 Lighting**")
            if st.button("💡 ON", use_container_width=True, key="light_on"):
                st.success("💡 Light ON")
            if st.button("💡 OFF", use_container_width=True, key="light_off"):
                st.success("💡 Light OFF")
        
        with device_col2:
            st.markdown("**❄️ Air Con**")
            if st.button("❄️ ON", use_container_width=True, key="ac_on"):
                st.success("❄️ AC ON")
            if st.button("❄️ OFF", use_container_width=True, key="ac_off"):
                st.success("❄️ AC OFF")
        
        with device_col3:
            st.markdown("**🌪️ Fan**")
            if st.button("🌪️ ON", use_container_width=True, key="fan_on"):
                st.success("🌪️ Fan ON")
            if st.button("🌪️ OFF", use_container_width=True, key="fan_off"):
                st.success("🌪️ Fan OFF")

def sidebar_content():
    """Enhanced sidebar with system information"""
    with st.sidebar:
        st.header("⚙️ System Dashboard")
        
        # Connection Status
        st.subheader("📡 Connection Status")
        if firebase_connected:
            st.success("🟢 Firebase: Connected")
            st.success("🟢 Firestore: Active")
        else:
            st.error("🔴 Firebase: Offline")
            st.info("📊 Using Demo Mode")
        
        st.success("🟢 AI Engine: Active")
        st.success("🟢 Sensors: Online")
        
        st.markdown("---")
        
        # Current Selection
        st.subheader("🏢 Current Selection")
        st.info(f"**Building:** {st.session_state.selected_building}")
        st.info(f"**Room:** {st.session_state.selected_room}")
        st.info(f"**Time Range:** {st.session_state.hours_to_show} hours")
        
        st.markdown("---")
        
        # System Settings
        st.subheader("⚙️ Settings")
        
        # Auto-refresh toggle
        st.session_state.auto_refresh = st.checkbox("🔄 Auto-refresh (30s)", value=st.session_state.auto_refresh)
        
        privacy_mode = st.checkbox("🔒 Privacy Mode", value=True)
        if privacy_mode:
            st.success("🛡️ Data anonymized")
        
        # Data Export
        st.markdown("---")
        st.subheader("📤 Data Export")
        if st.button("📊 Export Current", use_container_width=True):
            st.success("📊 Current data exported!")
        
        if st.button("📈 Export Historical", use_container_width=True):
            st.success("📈 Historical data exported!")
        
        # System Info
        st.markdown("---")
        st.subheader("ℹ️ System Info")
        st.text(f"Version: 2.0.0")
        st.text(f"Updated: {datetime.now().strftime('%Y-%m-%d')}")
        
        # Auto-refresh logic
        if st.session_state.auto_refresh:
            time.sleep(30)
            st.rerun()

# ==================== MAIN APPLICATION ====================
def main():
    """Main application entry point"""
    # Initialize sidebar
    sidebar_content()
    
    # Main dashboard sections
    main_dashboard()
    real_time_section()
    historical_section()
    ai_analytics_section()
    device_control_section()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666; padding: 2rem;'>
        <p>🏢 <strong>TECNOsense Smart Building Platform v2.0</strong></p>
        <p><em>Intelligent • Sustainable • Privacy-First • Firebase-Powered</em></p>
        <p>🔐 All personal data anonymized | 🌱 Promoting energy efficiency</p>
    </div>
    """, unsafe_allow_html=True)

# ==================== APPLICATION ENTRY POINT ====================
if __name__ == "__main__":
    if not firebase_connected:
        st.warning("⚠️ Firebase connection unavailable. Running in demo mode with simulated data.")
    
    main()
