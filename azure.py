import streamlit as st
import requests
import json
import time
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
import os
from typing import Optional, Dict, Any
import logging
import urllib3
import socket

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="TECNOsense Web v1.0",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS with better device control styling
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

# Enhanced Configuration
class Config:
    # Common ESP32 IPs to test
    POSSIBLE_IPS = [
        "172.30.247.230",  # Your specified IP
        "192.168.4.1",     # Default AP mode
        "192.168.1.100",   # Common router range
        "192.168.0.100",   # Common router range
        "10.0.0.100",      # Some routers
    ]
    ESP32_IP = os.getenv("ESP32_IP", "172.30.247.239") #DEPENDS on board
    REFRESH_INTERVAL = int(os.getenv("REFRESH_INTERVAL", "3"))
    CONNECTION_TIMEOUT = int(os.getenv("CONNECTION_TIMEOUT", "5"))
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))
    HISTORICAL_DATA_LIMIT = int(os.getenv("HISTORICAL_DATA_LIMIT", "200"))
    DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() == "true"
    AUTO_DISCOVER = os.getenv("AUTO_DISCOVER", "true").lower() == "true"

def initialize_session_state():
    defaults = {
        'historical_data': [],
        'last_update': None,
        'connection_status': 'unknown',
        'error_count': 0,
        'total_requests': 0,
        'last_successful_connection': None,
        'device_states': {'light': False, 'fan': False, 'ac': False, 'auto_mode': True},
        'performance_metrics': {'avg_response_time': 0, 'max_response_time': 0, 'min_response_time': float('inf')},
        'discovered_ip': None,
        'ip_test_results': {},
        'auto_discovery_running': False,
        'debug_info': []
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

def add_debug_info(message):
    """Add debug information with timestamp"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    st.session_state.debug_info.append(f"[{timestamp}] {message}")
    if len(st.session_state.debug_info) > 50:
        st.session_state.debug_info.pop(0)
    if Config.DEBUG_MODE:
        logger.info(message)

def test_single_ip(ip_address, timeout=3):
    """Test a single IP address for ESP32 connectivity"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip_address, 80))
        sock.close()
        
        if result != 0:
            return False, "Port 80 not accessible"
        
        url = f"http://{ip_address}/api/test"
        response = requests.get(url, timeout=timeout, verify=False)
        
        if response.status_code == 200:
            try:
                data = response.json()
                if "message" in data and "API is working" in data.get("message", ""):
                    return True, f"ESP32 API v{data.get('version', 'unknown')} found"
                else:
                    return False, "HTTP 200 but not ESP32 API"
            except:
                return False, "HTTP 200 but invalid JSON"
        else:
            return False, f"HTTP {response.status_code}"
            
    except requests.exceptions.Timeout:
        return False, "Timeout"
    except requests.exceptions.ConnectionError:
        return False, "Connection refused"
    except Exception as e:
        return False, f"Error: {str(e)[:30]}"

def discover_esp32_ip():
    """Discover ESP32 IP address by testing common addresses"""
    st.session_state.auto_discovery_running = True
    add_debug_info("Starting IP discovery...")
    
    for ip in Config.POSSIBLE_IPS:
        add_debug_info(f"Testing IP: {ip}")
        success, message = test_single_ip(ip, timeout=2)
        st.session_state.ip_test_results[ip] = {
            'success': success,
            'message': message,
            'tested_at': datetime.now()
        }
        if success:
            st.session_state.discovered_ip = ip
            Config.ESP32_IP = ip
            add_debug_info(f"✅ Found ESP32 at {ip}: {message}")
            st.session_state.auto_discovery_running = False
            return ip
        else:
            add_debug_info(f"❌ {ip}: {message}")
    
    st.session_state.auto_discovery_running = False
    add_debug_info("❌ No ESP32 found on common IP addresses")
    return None

class EnhancedRoomControlAPI:
    def __init__(self, ip_address: str, timeout: int = Config.CONNECTION_TIMEOUT):
        self.base_url = f"http://{ip_address}"
        self.timeout = timeout
        self.max_retries = Config.MAX_RETRIES
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'RoomControl-Dashboard/3.0',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        self.session.verify = False
        
    def _make_request(self, method: str, endpoint: str, **kwargs):
        start_time = time.time()
        st.session_state.total_requests += 1
        
        for attempt in range(self.max_retries):
            try:
                url = f"{self.base_url}{endpoint}"
                add_debug_info(f"Request: {method} {url} (attempt {attempt + 1})")
                
                response = self.session.request(method, url, timeout=self.timeout, **kwargs)
                response_time = (time.time() - start_time) * 1000
                
                metrics = st.session_state.performance_metrics
                if metrics['avg_response_time'] == 0:
                    metrics['avg_response_time'] = response_time
                else:
                    metrics['avg_response_time'] = (metrics['avg_response_time'] + response_time) / 2
                metrics['max_response_time'] = max(metrics['max_response_time'], response_time)
                metrics['min_response_time'] = min(metrics['min_response_time'], response_time)
                
                if response.status_code == 200:
                    st.session_state.connection_status = 'connected'
                    st.session_state.last_successful_connection = datetime.now()
                    st.session_state.error_count = 0
                    add_debug_info(f"✅ Success: {response_time:.1f}ms")
                    return response
                else:
                    add_debug_info(f"❌ HTTP {response.status_code}")
                    if attempt == self.max_retries - 1:
                        st.session_state.connection_status = 'error'
                        st.session_state.error_count += 1
                    time.sleep(0.5)
                    
            except requests.exceptions.Timeout:
                add_debug_info(f"⏱️ Timeout on attempt {attempt + 1}")
                if attempt == self.max_retries - 1:
                    st.session_state.connection_status = 'timeout'
                    st.session_state.error_count += 1
                    
            except requests.exceptions.ConnectionError as e:
                add_debug_info(f"🔌 Connection error: {str(e)[:50]}")
                if attempt == self.max_retries - 1:
                    st.session_state.connection_status = 'disconnected'
                    st.session_state.error_count += 1
                    
            except Exception as e:
                add_debug_info(f"💥 Unexpected error: {str(e)[:50]}")
                if attempt == self.max_retries - 1:
                    st.session_state.connection_status = 'error'
                    st.session_state.error_count += 1
        
        return None
    
    def test_connection(self):
        response = self._make_request('GET', '/api/test')
        return response is not None
    
    def get_status(self):
        response = self._make_request('GET', '/api/status')
        if response:
            try:
                data = response.json()
                add_debug_info(f"📊 Status: occupied={data.get('occupied', False)}, confidence={data.get('confidence', 0)}, auto_mode={data.get('devices', {}).get('auto_mode', True)}")
                return data
            except json.JSONDecodeError as e:
                add_debug_info(f"💥 JSON decode error: {e}")
                return None
        return None
    
    def toggle_device(self, device: str):
        response = self._make_request('POST', f'/api/toggle/{device}')
        if response:
            try:
                return response.status_code == 200
            except:
                return False
        return False

def format_uptime(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        return f"{seconds // 60}m {seconds % 60}s"
    elif seconds < 86400:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"
    else:
        days = seconds // 86400
        hours = (seconds % 86400) // 3600
        return f"{days}d {hours}h"

def create_gauge(value: float, title: str, max_val: float = 100, color: str = "#0078d4", unit: str = ""):
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=value,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': f"<b>{title}</b>", 'font': {'size': 16}},
        number={'suffix': f" {unit}"},
        gauge={
            'axis': {'range': [None, max_val]},
            'bar': {'color': color},
            'steps': [
                {'range': [0, max_val * 0.33], 'color': "#f3f2f1"},
                {'range': [max_val * 0.33, max_val * 0.66], 'color': "#e1dfdd"},
            ],
        }
    ))
    
    fig.update_layout(height=250, margin=dict(l=30, r=30, t=50, b=30))
    return fig

def display_device_controls(api, devices):
    st.subheader("🎛️ Device Control Panel")
    
    # Get current states from the API response
    auto_mode = devices.get('auto_mode', True)
    light_state = devices.get('light', False)
    fan_state = devices.get('fan', False) 
    ac_state = devices.get('ac', False)
    
    # Display current mode with clear visual indication
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
                # Auto mode toggle button
                button_text = f"{'👤 Switch to MANUAL' if device_state else '🤖 Switch to AUTO'}"
                button_type = "primary"
                disabled = False
            else:
                # Device toggle buttons
                status_text = "ON" if device_state else "OFF"
                button_text = f"{device['icon']} {device['name']} ({status_text})"
                button_type = "primary" if device_state else "secondary"
                # Disable device buttons when in auto mode
                disabled = auto_mode
            
            if disabled:
                button_text += " 🔒"
            
            if st.button(button_text, 
                        key=f"{device['key']}_btn", 
                        use_container_width=True,
                        type=button_type,
                        disabled=disabled and device['key'] != 'auto_mode'):
                with st.spinner(f'Toggling {device["name"]}...'):
                    add_debug_info(f"User toggling {device['name']}")
                    if api.toggle_device(device['endpoint']):
                        st.success(f"{device['name']} toggled successfully!")
                        # Update session state
                        st.session_state.device_states[device['key']] = not device_state
                        add_debug_info(f"✅ {device['name']} toggled successfully")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Failed to toggle {device['name']}")
                        add_debug_info(f"❌ Failed to toggle {device['name']}")

def display_main_dashboard(status_data, api):
    # Get device states
    devices = status_data.get('devices', {})
    auto_mode = devices.get('auto_mode', True)
    light_state = devices.get('light', False)
    fan_state = devices.get('fan', False)
    ac_state = devices.get('ac', False)
    
    # Main status with enhanced display
    col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
    
    with col1:
        is_occupied = status_data.get('occupied', False)
        confidence = status_data.get('confidence', 0)
        occupancy_level = status_data.get('occupancy_level', 0)
        
        # Enhanced status display with occupancy level
        if occupancy_level == 3:
            status_text = "OCCUPIED"
            status_class = "status-occupied"
        elif occupancy_level == 2:
            status_text = "LIKELY OCCUPIED"
            status_class = "status-occupied"
        elif occupancy_level == 1:
            status_text = "MAYBE OCCUPIED"
            status_class = "status-vacant"
        else:
            status_text = "VACANT"
            status_class = "status-vacant"
            
        st.markdown(f'''
        <div class="{status_class}">
            <h2>{status_text}</h2>
            <p>Confidence: {confidence}/10</p>
            <p>Level: {occupancy_level}/3</p>
            <p>Mode: {'AUTO' if auto_mode else 'MANUAL'}</p>
        </div>
        ''', unsafe_allow_html=True)
    
    with col2:
        light_level = status_data.get('light_level', 0)
        status_icon = "💡" if light_state else "⚫"
        status_color = "🟢" if light_state else "⚫"
        st.metric(f"{status_icon} Light", f"{light_level:.0f} lux", status_color)

    with col3:
        radar_distance = status_data.get('radar_distance', 0)
        st.metric("📡 Radar", f"{radar_distance} cm")
    
    with col4:
        ir_count = status_data.get('ir_count', 0)
        st.metric("🚶 IR Events", ir_count)
    
    with col5:
        mode_icon = "🤖" if auto_mode else "👤"
        mode_status = "AUTO" if auto_mode else "MANUAL"
        st.metric(f"{mode_icon} Mode", mode_status)
    
    # Device controls with proper state
    display_device_controls(api, devices)
    
    # Gauges with better layout
    st.subheader("📊 Real-time Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        fig = create_gauge(confidence, "Confidence", 10, "#66bb6a", "/10")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        light_level = min(status_data.get('light_level', 0), 1000)
        fig = create_gauge(light_level, "Light Level", 1000, "#ffa726", "lux")
        st.plotly_chart(fig, use_container_width=True)
    
    with col3:
        radar_dist = min(status_data.get('radar_distance', 0), 600)
        fig = create_gauge(radar_dist, "Radar Distance", 600, "#42a5f5", "cm")
        st.plotly_chart(fig, use_container_width=True)
    
    with col4:
        ir_count = min(status_data.get('ir_count', 0), 50)
        fig = create_gauge(ir_count, "IR Count", 50, "#ab47bc", "events")
        st.plotly_chart(fig, use_container_width=True)

def display_charts():
    if len(st.session_state.historical_data) <= 2:
        st.info("📊 Collecting data for charts...")
        return
    
    st.subheader("📈 Historical Data")
    df = pd.DataFrame(st.session_state.historical_data)
    
    col1, col2 = st.columns([3, 1])
    with col1:
        time_range = st.selectbox("Time Range", ["Last 30 minutes", "Last 1 Hour", "Last 4 Hours", "All Data"], index=1)
    with col2:
        st.metric("Data Points", len(df))
    
    now = datetime.now()
    if time_range == "Last 30 minutes":
        cutoff = now - timedelta(minutes=30)
    elif time_range == "Last 1 Hour":
        cutoff = now - timedelta(hours=1)
    elif time_range == "Last 4 Hours":
        cutoff = now - timedelta(hours=4)
    else:
        cutoff = df['timestamp'].min()
    
    filtered_df = df[df['timestamp'] >= cutoff]
    
    if len(filtered_df) == 0:
        st.warning("No data for selected range")
        return
    
    fig = make_subplots(
        rows=2, cols=2, 
        subplot_titles=('Occupancy Status', 'Light Level (lux)', 'Detection Confidence', 'Radar Distance (cm)')
    )
    
    occupancy_y = filtered_df['occupied'].astype(int)
    fig.add_trace(go.Scatter(
        x=filtered_df['timestamp'], 
        y=occupancy_y, 
        mode='lines+markers', 
        name='Occupied', 
        line=dict(color='#ff6b6b', width=2),
        fill='tonexty'
    ), row=1, col=1)
    
    fig.add_trace(go.Scatter(
        x=filtered_df['timestamp'], 
        y=filtered_df['light_level'], 
        mode='lines', 
        name='Light', 
        line=dict(color='#ffa726', width=2)
    ), row=1, col=2)
    
    fig.add_trace(go.Scatter(
        x=filtered_df['timestamp'], 
        y=filtered_df['confidence'], 
        mode='lines+markers', 
        name='Confidence', 
        line=dict(color='#66bb6a', width=2)
    ), row=2, col=1)
    
    fig.add_trace(go.Scatter(
        x=filtered_df['timestamp'], 
        y=filtered_df['radar_distance'], 
        mode='lines', 
        name='Radar', 
        line=dict(color='#42a5f5', width=2)
    ), row=2, col=2)
    
    fig.update_layout(height=500, showlegend=False)
    fig.update_xaxes(showgrid=True)
    fig.update_yaxes(showgrid=True)
    
    st.plotly_chart(fig, use_container_width=True)

def display_system_health(health_data, status_data):
    st.subheader("⚡ System Health")
    
    if not health_data and not status_data:
        st.warning("Health data unavailable")
        return
    
    combined_data = {}
    if health_data: combined_data.update(health_data)
    if status_data: combined_data.update(status_data)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        free_heap = combined_data.get('free_heap', 0) / 1024
        st.metric("Free Memory", f"{free_heap:.1f} KB")
    
    with col2:
        uptime = combined_data.get('uptime', 0)
        st.metric("Uptime", format_uptime(uptime))
    
    with col3:
        wifi_rssi = combined_data.get('wifi_rssi', 0)
        st.metric("WiFi Signal", f"{wifi_rssi} dBm")
    
    with col4:
        requests = combined_data.get('total_requests', 0)
        st.metric("API Calls", f"{requests}")

def display_connection_status():
    status_info = {
        'connected': {'icon': '🟢', 'text': 'Connected', 'class': 'connection-connected'},
        'disconnected': {'icon': '🔴', 'text': 'Disconnected', 'class': 'connection-disconnected'},
        'timeout': {'icon': '🟡', 'text': 'Timeout', 'class': 'connection-disconnected'},
        'error': {'icon': '🟠', 'text': 'Error', 'class': 'connection-disconnected'},
        'unknown': {'icon': '⚪', 'text': 'Unknown', 'class': 'connection-disconnected'}
    }
    
    status = st.session_state.connection_status
    info = status_info.get(status, status_info['unknown'])
    
    st.sidebar.markdown(f'''
    <div class="connection-status {info['class']}">
        {info['icon']} <strong>{info['text']}</strong>
    </div>
    ''', unsafe_allow_html=True)
    
    current_ip = st.session_state.discovered_ip or Config.ESP32_IP
    st.sidebar.info(f"Current IP: {current_ip}")
    
    if st.session_state.error_count > 0:
        st.sidebar.error(f"Errors: {st.session_state.error_count}")
    
    if st.session_state.last_successful_connection:
        last_conn = st.session_state.last_successful_connection
        st.sidebar.success(f"Last success: {last_conn.strftime('%H:%M:%S')}")
    
    metrics = st.session_state.performance_metrics
    if metrics['avg_response_time'] > 0:
        st.sidebar.metric("Avg Response", f"{metrics['avg_response_time']:.0f}ms")

def display_debug_panel():
    with st.expander("🔧 Debug Information", expanded=Config.DEBUG_MODE):
        st.subheader("IP Discovery Results")
        
        if st.session_state.ip_test_results:
            for ip, result in st.session_state.ip_test_results.items():
                status_class = "ip-success" if result['success'] else "ip-failed"
                status_icon = "✅" if result['success'] else "❌"
                
                st.markdown(f'''
                <div class="ip-test-result {status_class}">
                    {status_icon} <strong>{ip}</strong> - {result['message']}
                    <small style="float: right;">{result['tested_at'].strftime('%H:%M:%S')}</small>
                </div>
                ''', unsafe_allow_html=True)
        
        st.subheader("Recent Activity Log")
        if st.session_state.debug_info:
            debug_text = "\n".join(st.session_state.debug_info[-20:])
            st.markdown(f'''
            <div class="debug-panel">
{debug_text}
            </div>
            ''', unsafe_allow_html=True)
        
        st.subheader("Network Diagnostics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔍 Rediscover IPs"):
                with st.spinner("Scanning for ESP32..."):
                    discovered = discover_esp32_ip()
                    if discovered:
                        st.success(f"Found ESP32 at {discovered}")
                        st.rerun()
                    else:
                        st.error("No ESP32 found")
        
        with col2:
            if st.button("🧪 Test Current IP"):
                ip = Config.ESP32_IP
                with st.spinner(f"Testing {ip}..."):
                    success, message = test_single_ip(ip)
                    if success:
                        st.success(f"✅ {ip}: {message}")
                    else:
                        st.error(f"❌ {ip}: {message}")
        
        with col3:
            if st.button("🗑️ Clear Debug Log"):
                st.session_state.debug_info = []
                st.session_state.ip_test_results = {}
                st.success("Debug log cleared")

def main():
    st.markdown("""
    <div style="text-align: center; padding: 20px 0;">
        <h1>🏠 TECNOsense Control Dashboard</h1>
        <p><em>Real-time occupancy monitoring and control</em></p>
    </div>
    """, unsafe_allow_html=True)
    
    initialize_session_state()
    
    # Sidebar
    with st.sidebar:
        st.header("Configuration")
        
        esp32_ip = st.text_input("ESP32 IP Address", value=Config.ESP32_IP)
        Config.ESP32_IP = esp32_ip
        
        refresh_interval = st.slider("Refresh Interval (seconds)", 1, 30, Config.REFRESH_INTERVAL)
        Config.REFRESH_INTERVAL = refresh_interval
        
        st.divider()
        display_connection_status()
        
        if st.button("Test Connection"):
            api = EnhancedRoomControlAPI(Config.ESP32_IP)
            if api.test_connection():
                st.success("✅ Connected to ESP32!")
            else:
                st.error("❌ Connection failed")
        
        if st.button("Clear History"):
            st.session_state.historical_data = []
            st.success("History cleared!")
        
        if Config.DEBUG_MODE:
            display_debug_panel()
    
    # Main content
    api = EnhancedRoomControlAPI(Config.ESP32_IP)
    
    with st.spinner('Loading data...'):
        status_data = api.get_status()
    
    if status_data:
        # Store historical data
        timestamp = datetime.now()
        historical_entry = {
            'timestamp': timestamp,
            'occupied': status_data.get('occupied', False),
            'confidence': status_data.get('confidence', 0),
            'light_level': status_data.get('light_level', 0),
            'ir_count': status_data.get('ir_count', 0),
            'radar_distance': status_data.get('radar_distance', 0)
        }
        
        st.session_state.historical_data.append(historical_entry)
        if len(st.session_state.historical_data) > Config.HISTORICAL_DATA_LIMIT:
            st.session_state.historical_data.pop(0)
        
        st.session_state.last_update = timestamp
        
        # Display dashboard
        display_main_dashboard(status_data, api)
        
        # Display system health and charts
        health_data = status_data.get('health', {})
        display_system_health(health_data, status_data)
        display_charts()
        
        st.caption(f"Last update: {timestamp.strftime('%H:%M:%S')}")
        
    else:
        st.error("Cannot connect to ESP32")
        st.markdown(f'''
        <div class="connection-error">
            <h3>Connection Issues</h3>
            <p>Cannot reach ESP32 at <strong>{Config.ESP32_IP}</strong></p>
            <p>Check: IP address, WiFi connection, and power</p>
        </div>
        ''', unsafe_allow_html=True)
        
        if st.button("Try Auto-Discovery"):
            with st.spinner("Discovering ESP32..."):
                discovered_ip = discover_esp32_ip()
                if discovered_ip:
                    st.success(f"Found ESP32 at {discovered_ip}! Updating configuration...")
                    Config.ESP32_IP = discovered_ip
                    st.rerun()
                else:
                    st.error("No ESP32 found on network")
    
    # Auto-refresh
    if st.session_state.connection_status == 'connected':
        time.sleep(Config.REFRESH_INTERVAL)
        st.rerun()

if __name__ == "__main__":
    main()

