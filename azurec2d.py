import streamlit as st
import time
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
import os
import logging
from dotenv import load_dotenv

# --- AZURE + C2D IMPORTS ---
from azure.cosmos import CosmosClient, exceptions
from azure.iot.hub import IoTHubRegistryManager
from msrest.exceptions import HttpOperationError

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- PAGE CONFIGURATION (Unchanged) ---
st.set_page_config(
    page_title="TECNOsense Web v1.0 (Azure)",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS STYLES (Unchanged) ---
st.markdown("""
<style>
.metric-card {
    background: linear-gradient(135deg, #0078d4 0%, #5a67d8 100%);
    padding: 20px;
    border-radius: 10px;
    color: white;
    text-align: center;
    margin: 10px 0;
    box-shadow: 0 4px 12px rgba(0, 120, 212, 0.15);
}

.status-occupied {
    background: linear-gradient(135deg, #d13438 0%, #ff6b6b 100%);
    color: white;
    padding: 20px;
    border-radius: 12px;
    text-align: center;
    font-weight: bold;
}

.status-vacant {
    background: linear-gradient(135deg, #107c10 0%, #51cf66 100%);
    color: white;
    padding: 20px;
    border-radius: 12px;
    text-align: center;
    font-weight: bold;
}

.connection-error {
    background: linear-gradient(135deg, #ffaa44 0%, #ffd43b 100%);
    color: #495057;
    padding: 20px;
    border-radius: 12px;
    text-align: center;
    border-left: 6px solid #d13438;
}

.connection-status {
    padding: 10px 15px;
    border-radius: 8px;
    margin: 10px 0;
    font-weight: 600;
    text-align: center;
}

.connection-connected {
    background-color: #d4edda;
    color: #155724;
    border: 1px solid #c3e6cb;
}

.connection-disconnected {
    background-color: #f8d7da;
    color: #721c24;
    border: 1px solid #f5c6cb;
}

.device-button {
    width: 100%;
    margin: 5px 0;
    border-radius: 6px;
    font-weight: 600;
}

.device-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
}

.auto-mode-active {
    background: linear-gradient(135deg, #28a745 0%, #20c997 100%);
    color: white;
    padding: 10px;
    border-radius: 8px;
    text-align: center;
    font-weight: bold;
}

.manual-mode-active {
    background: linear-gradient(135deg, #dc3545 0%, #fd7e14 100%);
    color: white;
    padding: 10px;
    border-radius: 8px;
    text-align: center;
    font-weight: bold;
}

.debug-panel {
    background-color: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 8px;
    padding: 15px;
    margin: 10px 0;
    font-family: monospace;
    font-size: 12px;
}

.ip-test-result {
    padding: 8px 12px;
    margin: 4px 0;
    border-radius: 6px;
    font-family: monospace;
}

.ip-success {
    background-color: #d1e7dd;
    color: #0f5132;
    border-left: 4px solid #198754;
}

.ip-failed {
    background-color: #f8d7da;
    color: #721c24;
    border-left: 4px solid #dc3545;
}

.ip-testing {
    background-color: #fff3cd;
    color: #664d03;
    border-left: 4px solid #ffc107;
}
</style>
""", unsafe_allow_html=True)

# --- AZURE + C2D CONFIGURATION ---
class Config:
    # Azure Cosmos DB Configuration
    COSMOS_ENDPOINT = os.getenv("AZURE_COSMOS_ENDPOINT")
    COSMOS_KEY = os.getenv("AZURE_COSMOS_KEY")
    COSMOS_DATABASE = "iot_database"
    COSMOS_CONTAINER = "sensor_data"
    
    # Azure IoT Hub Configuration for C2D
    IOTHUB_OWNER_CONNECTION_STRING = os.getenv("AZURE_IOTHUB_OWNER_CONNECTION_STRING")
    TARGET_DEVICE_ID = "tecno-sense-living-room"
    
    # App Settings
    REFRESH_INTERVAL = int(os.getenv("REFRESH_INTERVAL", "5"))
    HISTORICAL_DATA_LIMIT = int(os.getenv("HISTORICAL_DATA_LIMIT", "200"))

def initialize_session_state():
    defaults = {
        'historical_data': [],
        'connection_status': 'unknown',
        'last_successful_connection': None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# --- AZURE + C2D DEVICE CONTROL ---
class DeviceControlManager:
    """Manages sending commands to the device via Azure IoT Hub Direct Methods."""
    def __init__(self, connection_string, device_id):
        self.connection_string = connection_string
        self.device_id = device_id
        if not self.connection_string:
            logger.error("IoT Hub Owner Connection String is not configured.")
        
    def _invoke_method(self, method_name: str, payload: dict = {}):
        if not self.connection_string:
            st.error("Cannot send command: IoT Hub connection string is not set in .env file.")
            return False
            
        try:
            registry_manager = IoTHubRegistryManager.from_connection_string(self.connection_string)
            device_method = {
                "method_name": method_name,
                "payload": payload,
                "response_timeout_in_seconds": 20,
                "connect_timeout_in_seconds": 20
            }
            response = registry_manager.invoke_device_method(self.device_id, device_method)
            
            if response.status == 200:
                st.toast(f"Device says: {response.payload.get('message', 'OK')}", icon="✅")
                return True
            else:
                st.error(f"Device returned error {response.status}: {response.payload}")
                return False

        except HttpOperationError as ex:
            st.error(f"Failed to send command. IoT Hub Error: {ex.response.text}")
            return False
        except Exception as e:
            st.error(f"An unexpected error occurred while sending command: {str(e)}")
            return False

    def toggle_device(self, device_name: str):
        # Map the device name from the UI to the direct method name on the ESP32
        method_map = {
            'light': 'toggleLight',
            'fan': 'toggleFan',
            'ac': 'toggleAC',
            'auto': 'toggleAuto'
        }
        method_name = method_map.get(device_name)
        if method_name:
            return self._invoke_method(method_name)
        else:
            st.error(f"Unknown device '{device_name}' for C2D command.")
            return False

# --- AZURE DATA FETCHING FUNCTIONS ---
@st.cache_resource
def get_cosmos_container():
    """Create and cache the Cosmos DB container client."""
    if not all([Config.COSMOS_ENDPOINT, Config.COSMOS_KEY]):
        st.error("Cosmos DB credentials (ENDPOINT, KEY) are not set in the .env file.")
        return None
    try:
        client = CosmosClient(Config.COSMOS_ENDPOINT, credential=Config.COSMOS_KEY)
        database = client.get_database_client(Config.COSMOS_DATABASE)
        container = database.get_container_client(Config.COSMOS_CONTAINER)
        return container
    except Exception as e:
        st.error(f"Failed to connect to Cosmos DB: {e}")
        return None

def get_latest_sensor_data(container, device_id):
    """Fetches the most recent document for a specific device."""
    try:
        query = "SELECT TOP 1 * FROM c WHERE c.deviceId = @deviceId ORDER BY c._ts DESC"
        params = [{"name": "@deviceId", "value": device_id}]
        items = list(container.query_items(query=query, parameters=params, enable_cross_partition_query=False))
        if items:
            st.session_state.connection_status = 'connected'
            st.session_state.last_successful_connection = datetime.now()
            return items[0]
        else:
            st.session_state.connection_status = 'disconnected'
            return None
    except Exception as e:
        logger.error(f"Error querying Cosmos DB: {e}")
        st.session_state.connection_status = 'error'
        return None

def get_historical_data(container, device_id):
    """Fetches historical data for charting."""
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=4)
        cutoff_timestamp = int(cutoff_time.timestamp())
        query = "SELECT * FROM c WHERE c.deviceId = @deviceId AND c._ts >= @cutoff ORDER BY c._ts DESC"
        params = [{"name": "@deviceId", "value": device_id}, {"name": "@cutoff", "value": cutoff_timestamp}]
        items = list(container.query_items(query=query, parameters=params))
        for item in items:
            item['timestamp'] = datetime.fromtimestamp(item['_ts'])
        return items
    except Exception as e:
        logger.error(f"Error fetching historical data: {e}")
        return []

# --- HELPER & DISPLAY FUNCTIONS (Unchanged UI Logic) ---
def format_uptime(seconds: int) -> str:
    if not isinstance(seconds, (int, float)): return "0s"
    seconds = int(seconds)
    if seconds < 60: return f"{seconds}s"
    if seconds < 3600: return f"{seconds // 60}m {seconds % 60}s"
    if seconds < 86400: return f"{seconds // 3600}h {(seconds % 3600) // 60}m"
    return f"{seconds // 86400}d {(seconds % 86400) // 3600}h"

def create_gauge(value: float, title: str, max_val: float = 100, color: str = "#0078d4", unit: str = ""):
    fig = go.Figure(go.Indicator(mode="gauge+number+delta", value=value, domain={'x': [0, 1], 'y': [0, 1]}, title={'text': f"<b>{title}</b>", 'font': {'size': 16}}, number={'suffix': f" {unit}"}, gauge={'axis': {'range': [None, max_val]}, 'bar': {'color': color}, 'steps': [{'range': [0, max_val * 0.33], 'color': "#f3f2f1"}, {'range': [max_val * 0.33, max_val * 0.66], 'color': "#e1dfdd"}]}))
    fig.update_layout(height=250, margin=dict(l=30, r=30, t=50, b=30))
    return fig

def display_device_controls(api, devices):
    st.subheader("🎛️ Device Control Panel")
    auto_mode = devices.get('auto_mode', True)
    light_state = devices.get('light', False)
    fan_state = devices.get('fan', False) 
    ac_state = devices.get('ac', False)
    
    mode_class = "auto-mode-active" if auto_mode else "manual-mode-active"
    mode_text = "AUTO MODE ACTIVE 🤖" if auto_mode else "MANUAL MODE ACTIVE 👤"
    st.markdown(f'<div class="{mode_class}">{mode_text}</div>', unsafe_allow_html=True)
    
    if auto_mode:
        st.info("🔒 Devices are automatically controlled. Switch to Manual mode to enable manual control.")
    
    device_config = [
        {'key': 'light', 'icon': '💡', 'name': 'Light', 'endpoint': 'light', 'state': light_state},
        {'key': 'fan', 'icon': '🌪️', 'name': 'Fan', 'endpoint': 'fan', 'state': fan_state},
        {'key': 'ac', 'icon': '❄️', 'name': 'AC', 'endpoint': 'ac', 'state': ac_state},
        {'key': 'auto_mode', 'icon': '🤖', 'name': 'Auto Mode', 'endpoint': 'auto', 'state': auto_mode}
    ]
    
    cols = st.columns(2)
    for i, device in enumerate(device_config):
        with cols[i % 2]:
            device_state = device['state']
            if device['key'] == 'auto_mode':
                button_text = f"{'👤 Switch to MANUAL' if device_state else '🤖 Switch to AUTO'}"
                button_type = "primary"
                disabled = False
            else:
                status_text = "ON" if device_state else "OFF"
                button_text = f"{device['icon']} {device['name']} ({status_text})"
                button_type = "primary" if device_state else "secondary"
                disabled = auto_mode
            
            if disabled: button_text += " 🔒"
            
            if st.button(button_text, key=f"{device['key']}_btn", use_container_width=True, type=button_type, disabled=disabled and device['key'] != 'auto_mode'):
                with st.spinner(f'Sending command to {device["name"]}...'):
                    if api.toggle_device(device['endpoint']):
                        st.success(f"Command for '{device['name']}' sent successfully!")
                        time.sleep(2) # Give time for device state to update in telemetry
                        st.rerun()
                    else:
                        st.error(f"Failed to send command for '{device['name']}'")

def display_main_dashboard(status_data, api):
    # --- FIX: Extract the nested sensorData object first ---
    sensor_data = status_data.get('sensorData', status_data) # Fallback to top-level for safety

    devices = sensor_data.get('devices', {})
    auto_mode = devices.get('auto_mode', True)
    light_state = devices.get('light', False)
    
    col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
    with col1:
        # --- FIX: Get data from the sensor_data object ---
        confidence = sensor_data.get('confidence', 0)
        occupancy_level = sensor_data.get('occupancy_level', 0)
        if occupancy_level == 3: status_text, status_class = "OCCUPIED", "status-occupied"
        elif occupancy_level == 2: status_text, status_class = "LIKELY OCCUPIED", "status-occupied"
        elif occupancy_level == 1: status_text, status_class = "MAYBE OCCUPIED", "status-vacant"
        else: status_text, status_class = "VACANT", "status-vacant"
        st.markdown(f'<div class="{status_class}"><h2>{status_text}</h2><p>Confidence: {confidence}/10</p><p>Level: {occupancy_level}/3</p></div>', unsafe_allow_html=True)
    
    # --- FIX: Get data from the sensor_data object ---
    with col2: st.metric("💡 Light", f"{sensor_data.get('light_level', 0):.0f} lux", "ON" if light_state else "OFF")
    with col3: st.metric("📡 Radar", f"{sensor_data.get('radar_distance', 0)} cm")
    with col4: st.metric("🚶 IR Events", f"{sensor_data.get('ir_count', 0)}")
    with col5: st.metric(f"{'🤖' if auto_mode else '👤'} Mode", "AUTO" if auto_mode else "MANUAL")
    
    display_device_controls(api, devices)
    
    st.subheader("📊 Real-time Metrics")
    g_col1, g_col2, g_col3, g_col4 = st.columns(4)
    # --- FIX: Get data from the sensor_data object ---
    with g_col1: st.plotly_chart(create_gauge(confidence, "Confidence", 10, "#66bb6a", "/10"), use_container_width=True)
    with g_col2: st.plotly_chart(create_gauge(min(sensor_data.get('light_level', 0), 1000), "Light Level", 1000, "#ffa726", "lux"), use_container_width=True)
    with g_col3: st.plotly_chart(create_gauge(min(sensor_data.get('radar_distance', 0), 600), "Radar Distance", 600, "#42a5f5", "cm"), use_container_width=True)
    with g_col4: st.plotly_chart(create_gauge(min(sensor_data.get('ir_count', 0), 50), "IR Count", 50, "#ab47bc", "events"), use_container_width=True)

def display_charts():
    if len(st.session_state.historical_data) <= 2:
        st.info("📊 Collecting data for charts...")
        return
    st.subheader("📈 Historical Data")
    df = pd.DataFrame(st.session_state.historical_data)
    if 'timestamp' not in df.columns: return

    # --- FIX: Extract the nested fields into new columns for charting ---
    # This handles cases where the nested object might be missing
    df['occupied'] = df['sensorData'].apply(lambda x: x.get('occupied', False) if isinstance(x, dict) else False)
    df['light_level'] = df['sensorData'].apply(lambda x: x.get('light_level', 0) if isinstance(x, dict) else 0)
    df['confidence'] = df['sensorData'].apply(lambda x: x.get('confidence', 0) if isinstance(x, dict) else 0)
    df['radar_distance'] = df['sensorData'].apply(lambda x: x.get('radar_distance', 0) if isinstance(x, dict) else 0)

    fig = make_subplots(rows=2, cols=2, subplot_titles=('Occupancy Status', 'Light Level (lux)', 'Detection Confidence', 'Radar Distance (cm)'))
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['occupied'].astype(int), mode='lines+markers', name='Occupied', line=dict(color='#ff6b6b', width=2), fill='tonexty'), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['light_level'], mode='lines', name='Light', line=dict(color='#ffa726', width=2)), row=1, col=2)
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['confidence'], mode='lines+markers', name='Confidence', line=dict(color='#66bb6a', width=2)), row=2, col=1)
    fig.add_trace(go.Scatter(x=df['timestamp'], y=df['radar_distance'], mode='lines', name='Radar', line=dict(color='#42a5f5', width=2)), row=2, col=2)
    fig.update_layout(height=500, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

def display_system_health(status_data):
    st.subheader("⚡ System Health")
    # --- FIX: Extract the nested sensorData object first ---
    sensor_data = status_data.get('sensorData', status_data)

    col1, col2, col3, col4 = st.columns(4)
    # --- FIX: Get data from the sensor_data object ---
    with col1: st.metric("Free Memory", f"{sensor_data.get('free_heap', 0) / 1024:.1f} KB")
    with col2: st.metric("Uptime", format_uptime(sensor_data.get('uptime', 0)))
    with col3: st.metric("WiFi Signal", f"{sensor_data.get('health', {}).get('wifi_rssi', 0)} dBm")
    with col4: st.metric("API Calls", f"{sensor_data.get('health', {}).get('total_requests', 0)}")

def display_connection_status():
    status_info = {
        'connected': {'icon': '🟢', 'text': 'Connected to Azure', 'class': 'connection-connected'},
        'disconnected': {'icon': '🔴', 'text': 'No Data from Azure', 'class': 'connection-disconnected'},
        'error': {'icon': '🟠', 'text': 'Connection Error', 'class': 'connection-disconnected'},
        'unknown': {'icon': '⚪', 'text': 'Unknown', 'class': 'connection-disconnected'}
    }
    status = st.session_state.connection_status
    info = status_info.get(status, status_info['unknown'])
    st.sidebar.markdown(f'<div class="connection-status {info["class"]}"> {info["icon"]} <strong>{info["text"]}</strong> </div>', unsafe_allow_html=True)
    st.sidebar.info(f"Device ID: {Config.TARGET_DEVICE_ID}")
    if st.session_state.last_successful_connection:
        st.sidebar.success(f"Last success: {st.session_state.last_successful_connection.strftime('%H:%M:%S')}")

# --- MAIN APPLICATION LOGIC ---
def main():
    st.markdown("""
    <div style="text-align: center; padding: 20px 0;">
        <h1>🏠 TECNOsense Control Dashboard (Azure + C2D)</h1>
        <p><em>Real-time occupancy monitoring and cloud control</em></p>
    </div>
    """, unsafe_allow_html=True)
    
    initialize_session_state()
    
    with st.sidebar:
        st.header("Configuration")
        Config.REFRESH_INTERVAL = st.slider("Refresh Interval (seconds)", 1, 30, Config.REFRESH_INTERVAL)
        st.divider()
        display_connection_status()

    # Initialize the C2D control manager
    api = DeviceControlManager(Config.IOTHUB_OWNER_CONNECTION_STRING, Config.TARGET_DEVICE_ID)
    
    # Get the Cosmos DB container client
    container = get_cosmos_container()
    if not container: return

    with st.spinner('Loading data from Azure Cosmos DB...'):
        status_data = get_latest_sensor_data(container, Config.TARGET_DEVICE_ID)
    
    if status_data:
        st.session_state.historical_data = get_historical_data(container, Config.TARGET_DEVICE_ID)
        
        # Display dashboard sections
        display_main_dashboard(status_data, api)
        display_system_health(status_data)
        display_charts()
        
        timestamp = datetime.fromtimestamp(status_data.get('_ts', time.time()))
        st.caption(f"Last update: {timestamp.strftime('%H:%M:%S')}")
        
    else:
        st.error("Cannot fetch data from Azure Cosmos DB.")
        st.markdown('<div class="connection-error"><h3>No Data Received</h3><p>Waiting for the ESP32 to send data to the cloud.</p></div>', unsafe_allow_html=True)
    
    time.sleep(Config.REFRESH_INTERVAL)
    st.rerun()

if __name__ == "__main__":
    main()