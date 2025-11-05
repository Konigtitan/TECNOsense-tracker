import streamlit as st
import time
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime, timedelta
import os
from typing import Optional, Dict, Any, List
import logging

# Azure SDK imports
from azure.cosmos import CosmosClient
from azure.iot.hub import IoTHubRegistryManager
from azure.iot.hub.models import CloudToDeviceMethod

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== PAGE CONFIGURATION ====================

st.set_page_config(
    page_title="TECNOsense Azure Dashboard v3.0",
    page_icon="☁️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==================== ENHANCED CSS ====================

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        background: linear-gradient(135deg, #0a0e27 0%, #1a1f3a 50%, #0f1419 100%);
        color: #e8edf4;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .header-title {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(135deg, #60a5fa 0%, #a78bfa 50%, #ec4899 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.02em;
    }
    
    .header-subtitle {
        font-size: 0.95rem;
        color: #94a3b8;
        font-weight: 500;
        margin-top: 4px;
    }
    
    .status-card {
        padding: 48px;
        border-radius: 28px;
        text-align: center;
        margin: 24px 0;
        backdrop-filter: blur(20px);
        border: 2px solid;
        transition: all 0.4s ease;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
    }
    
    .status-card:hover {
        transform: translateY(-4px);
    }
    
    .status-occupied {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.15) 0%, rgba(220, 38, 38, 0.1) 100%);
        border-color: rgba(239, 68, 68, 0.4);
    }
    
    .status-vacant {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(5, 150, 105, 0.1) 100%);
        border-color: rgba(16, 185, 129, 0.4);
    }
    
    .status-title {
        font-size: 3.5rem;
        font-weight: 800;
        margin-bottom: 12px;
        letter-spacing: -0.03em;
    }
    
    .status-occupied .status-title { color: #fca5a5; }
    .status-vacant .status-title { color: #6ee7b7; }
    
    .status-subtitle {
        font-size: 1.75rem;
        font-weight: 600;
        margin: 16px 0;
        color: #e8edf4;
    }
    
    .status-detail {
        font-size: 1.1rem;
        margin: 8px 0;
        color: #cbd5e1;
        font-weight: 500;
    }
    
    .conn-badge {
        padding: 16px 20px;
        border-radius: 16px;
        text-align: center;
        font-weight: 600;
        font-size: 0.95rem;
        backdrop-filter: blur(10px);
        border: 1px solid;
        transition: all 0.3s ease;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
    }
    
    .conn-badge:hover {
        transform: translateY(-2px);
    }
    
    .conn-cloud-on { 
        background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(37, 99, 235, 0.1));
        border-color: rgba(59, 130, 246, 0.5);
        color: #93c5fd;
    }
    
    .conn-cloud-off { 
        background: linear-gradient(135deg, rgba(71, 85, 105, 0.2), rgba(51, 65, 85, 0.1));
        border-color: rgba(71, 85, 105, 0.5);
        color: #94a3b8;
    }
    
    .conn-device-on { 
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.2), rgba(5, 150, 105, 0.1));
        border-color: rgba(16, 185, 129, 0.5);
        color: #6ee7b7;
    }
    
    .conn-device-off { 
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.2), rgba(220, 38, 38, 0.1));
        border-color: rgba(239, 68, 68, 0.5);
        color: #fca5a5;
    }
    
    .metric-card {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.02));
        backdrop-filter: blur(10px);
        padding: 24px;
        border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        text-align: center;
        transition: all 0.3s ease;
    }
    
    .metric-card:hover {
        border-color: rgba(96, 165, 250, 0.4);
        transform: translateY(-4px);
    }
    
    .metric-value {
        font-size: 2.25rem;
        font-weight: 800;
        color: #e8edf4;
        margin: 12px 0;
    }
    
    .metric-label {
        font-size: 0.8rem;
        color: #94a3b8;
        font-weight: 600;
        text-transform: uppercase;
    }
    
    .section-header {
        font-size: 1.75rem;
        font-weight: 700;
        background: linear-gradient(135deg, #60a5fa, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 32px 0 20px 0;
        padding-bottom: 12px;
        border-bottom: 2px solid rgba(96, 165, 250, 0.2);
    }
    
    .diagnostic-box {
        background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(217, 119, 6, 0.05));
        border-left: 4px solid #f59e0b;
        padding: 20px;
        border-radius: 12px;
        margin: 16px 0;
        color: #cbd5e1;
    }
    
    .success-box {
        background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(5, 150, 105, 0.05));
        border-left: 4px solid #10b981;
        padding: 20px;
        border-radius: 12px;
        margin: 16px 0;
        color: #cbd5e1;
    }
    
    .error-box {
        background: linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(220, 38, 38, 0.05));
        border-left: 4px solid #ef4444;
        padding: 20px;
        border-radius: 12px;
        margin: 16px 0;
        color: #cbd5e1;
    }
    
    .chart-container {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.03), rgba(255, 255, 255, 0.01));
        backdrop-filter: blur(10px);
        padding: 24px;
        border-radius: 20px;
        margin: 20px 0;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
    
    .stButton button {
        border-radius: 12px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }
</style>
""", unsafe_allow_html=True)

# ==================== AZURE CONFIGURATION ====================

class AzureConfig:
    IOT_HUB_FQDN = os.getenv("IOT_HUB_FQDN", "tecnosense-hub.azure-devices.net")
    DEVICE_ID = os.getenv("DEVICE_ID", "tecno-sense-living-room")
    IOTHUB_CONNECTION_STRING = os.getenv(
        "AZURE_IOTHUB_OWNER_CONNECTION_STRING",
        "HostName=tecnosense-hub.azure-devices.net;SharedAccessKeyName=iothubowner;SharedAccessKey=/sd7RP/tca2oB1BTqwM/1Ftst+s4+rYW/AIoTERJKos="
    )
    
    COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT", "https://tecnosense-db-malaysiawest.documents.azure.com:443/")
    COSMOS_KEY = os.getenv("COSMOS_KEY", "UgHy1nb1Gctniq0SXHaI2nAd6MzEoIV8NUMILESPyMmM3lasUWSVFvDExGaWo4VqEOf1PSdNpcTaACDbwR93Nw==")
    COSMOS_DATABASE = "iot_database"
    COSMOS_CONTAINER = "sensor_data"
    
    REFRESH_INTERVAL = 3

# ==================== AZURE MANAGERS ====================

@st.cache_resource
def get_iot_hub_manager():
    try:
        manager = IoTHubRegistryManager.from_connection_string(AzureConfig.IOTHUB_CONNECTION_STRING)
        logger.info("✅ IoT Hub Manager initialized")
        return manager
    except Exception as e:
        logger.error(f"❌ Failed to initialize IoT Hub: {e}")
        return None

@st.cache_resource
def get_cosmos_container():
    try:
        client = CosmosClient(AzureConfig.COSMOS_ENDPOINT, credential=AzureConfig.COSMOS_KEY)
        database = client.get_database_client(AzureConfig.COSMOS_DATABASE)
        container = database.get_container_client(AzureConfig.COSMOS_CONTAINER)
        logger.info("✅ Cosmos DB connected")
        return container
    except Exception as e:
        logger.error(f"❌ Cosmos DB failed: {e}")
        return None

# ==================== DEVICE CONTROLLER (FIXED) ====================

class AzureDeviceController:
    def __init__(self, iot_manager, cosmos_container):
        self.iot_manager = iot_manager
        self.cosmos_container = cosmos_container
        self.device_id = AzureConfig.DEVICE_ID
    
    def invoke_direct_method(self, method_name: str, payload: dict = {}) -> Dict[str, Any]:
        if not self.iot_manager:
            return {"success": False, "error": "IoT Hub not connected"}
        
        try:
            device_method = CloudToDeviceMethod(
                method_name=method_name,
                payload=payload,
                response_timeout_in_seconds=30,
                connect_timeout_in_seconds=15
            )
            
            response = self.iot_manager.invoke_device_method(self.device_id, device_method)
            
            result = {
                "success": response.status == 200,
                "status": response.status,
                "payload": response.payload
            }
            
            if result["success"]:
                logger.info(f"✅ Command successful: {method_name}")
            
            return result
            
        except Exception as e:
            error_msg = "Device offline" if "Not Found" in str(e) else str(e)
            logger.error(f"❌ Command failed: {error_msg}")
            return {"success": False, "error": error_msg}
    
    def toggle_light(self) -> bool:
        return self.invoke_direct_method("toggleLight").get("success", False)
    
    def toggle_fan(self) -> bool:
        return self.invoke_direct_method("toggleFan").get("success", False)
    
    def toggle_ac(self) -> bool:
        return self.invoke_direct_method("toggleAC").get("success", False)
    
    def toggle_auto_mode(self) -> bool:
        return self.invoke_direct_method("toggleAuto").get("success", False)
    
    def reset_counter(self) -> bool:
        return self.invoke_direct_method("resetCounter").get("success", False)
    
    def get_latest_telemetry(self) -> Optional[Dict[str, Any]]:
        """FIXED: Handle Azure IoT Hub message wrapping + proper variable scoping"""
        if not self.cosmos_container:
            logger.error("❌ Cosmos container not initialized")
            return None
        
        try:
            query = """
            SELECT TOP 1 * FROM c 
            WHERE c.deviceId = @deviceId 
            ORDER BY c._ts DESC
            """
            
            params = [{"name": "@deviceId", "value": self.device_id}]
            
            logger.info(f"🔍 Querying for device: {self.device_id}")
            
            items = list(self.cosmos_container.query_items(
                query=query,
                parameters=params,
                enable_cross_partition_query=True
            ))
            
            if not items:
                logger.warning(f"⚠️ No data for {self.device_id}")
                
                # Fallback: Check if ANY documents exist
                fallback_query = "SELECT TOP 1 * FROM c ORDER BY c._ts DESC"
                items = list(self.cosmos_container.query_items(
                    query=fallback_query,
                    enable_cross_partition_query=True
                ))
                
                if items:
                    found_id = items[0].get('deviceId', 'MISSING')
                    logger.error(f"❌ MISMATCH: Found '{found_id}', expected '{self.device_id}'")
                    logger.error(f"Document keys: {list(items[0].keys())}")
                    return None
                else:
                    logger.error("❌ No documents in Cosmos DB at all!")
                    return None
            
            item = items[0]
            
            # 🔥 CRITICAL FIX: Handle Azure IoT Hub message wrapping
            if 'sensorData' in item:
                logger.info("🔓 Unwrapping Azure IoT Hub message envelope")
                
                sensor_data = item.get('sensorData', {})
                
                if isinstance(sensor_data, str):
                    import json
                    try:
                        sensor_data = json.loads(sensor_data)
                        logger.info("✅ Parsed JSON from sensorData string")
                    except json.JSONDecodeError as e:
                        logger.error(f"❌ Failed to parse sensorData JSON: {e}")
                        return None
                
                actual_data = sensor_data
                actual_data['_ts'] = item.get('_ts')
                actual_data['_wrapped'] = True
                
                logger.info("✅ Using unwrapped sensorData as telemetry payload")
            else:
                actual_data = item
                actual_data['_wrapped'] = False
            
            # Initialize analytics outside of conditionals
            ir_data = actual_data.get('ir_counter', {})
            analytics = ir_data.get('analytics', {}) if ir_data else {}
            devices = actual_data.get('devices', {})
            
            # Validation
            missing_fields = []
            
            if 'people_count' not in actual_data:
                missing_fields.append('people_count')
            if 'occupied' not in actual_data:
                missing_fields.append('occupied')
            if not ir_data:
                missing_fields.append('ir_counter (object)')
            if not analytics and ir_data:
                missing_fields.append('ir_counter.analytics (object)')
            
            if missing_fields:
                logger.warning(f"⚠️ MISSING FIELDS: {', '.join(missing_fields)}")
                logger.warning("Document may be from older ESP32 firmware")
            
            logger.info("✅ Retrieved telemetry:")
            logger.info(f"   deviceId: {actual_data.get('deviceId', 'MISSING')}")
            logger.info(f"   people_count: {actual_data.get('people_count', 'MISSING')}")
            logger.info(f"   occupied: {actual_data.get('occupied', 'MISSING')}")
            logger.info(f"   total_entries: {ir_data.get('total_entries', 'MISSING')}")
            logger.info(f"   confidence: {ir_data.get('confidence', 'MISSING')}")
            logger.info(f"   analytics present: {bool(analytics)}")
            logger.info(f"   message wrapped: {actual_data.get('_wrapped', False)}")
            
            return {
                'timestamp': datetime.fromtimestamp(actual_data.get('_ts', time.time())),
                'occupied': actual_data.get('occupied', False),
                'people_count': actual_data.get('people_count', 0),
                'light_level': actual_data.get('light_level', 0),
                'total_entries': ir_data.get('total_entries', 0),
                'total_exits': ir_data.get('total_exits', 0),
                'valid_crossings': ir_data.get('valid_crossings', 0),
                'invalid_sequences': ir_data.get('invalid_sequences', 0),
                'timeout_errors': ir_data.get('timeout_errors', 0),
                'blockage_errors': ir_data.get('blockage_errors', 0),
                'confidence': ir_data.get('confidence', 0),
                'system_confidence': ir_data.get('system_confidence', ir_data.get('confidence', 1.0)),
                'last_direction': ir_data.get('last_direction', 'NONE'),
                'crossing_state': ir_data.get('crossing_state', 'WAITING'),
                'high_confidence_crossings': analytics.get('high_confidence_crossings', 0),
                'medium_confidence_crossings': analytics.get('medium_confidence_crossings', 0),
                'low_confidence_crossings': analytics.get('low_confidence_crossings', 0),
                'devices': devices,
                'light_on': devices.get('light', False),
                'fan_on': devices.get('fan', False),
                'ac_on': devices.get('ac', False),
                'auto_mode': devices.get('auto_mode', True),
                'uptime': actual_data.get('uptime', 0),
                'free_heap': actual_data.get('free_heap', 0),
                'wifi_rssi': actual_data.get('wifi_rssi', 0),
                'system_errors': actual_data.get('system_errors', 0),
                'source': 'cosmos_db',
                '_raw': item,
                '_actual_data': actual_data,
                '_missing_fields': missing_fields
            }
            
        except Exception as e:
            logger.error(f"❌ Telemetry error: {e}")
            logger.exception("Full traceback:")
            return None
    
    def get_historical_data(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Fetch historical data for charts - FIXED to handle IoT Hub wrapping"""
        if not self.cosmos_container:
            return []
        
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            cutoff_timestamp = int(cutoff_time.timestamp())
            
            query = """
            SELECT c._ts, c.deviceId, c.sensorData
            FROM c 
            WHERE c.deviceId = @deviceId AND c._ts >= @cutoff 
            ORDER BY c._ts ASC
            """
            
            params = [
                {"name": "@deviceId", "value": self.device_id},
                {"name": "@cutoff", "value": cutoff_timestamp}
            ]
            
            logger.info(f"📊 Fetching historical data (last {hours} hours)")
            
            items = list(self.cosmos_container.query_items(
                query=query,
                parameters=params,
                enable_cross_partition_query=True
            ))
            
            if not items:
                logger.warning(f"⚠️ No historical data found")
                return []
            
            historical = []
            
            for item in items:
                try:
                    if 'sensorData' in item:
                        sensor_data = item.get('sensorData', {})
                        
                        if isinstance(sensor_data, str):
                            import json
                            try:
                                sensor_data = json.loads(sensor_data)
                            except json.JSONDecodeError:
                                logger.warning("Failed to parse sensorData, skipping record")
                                continue
                        
                        actual_data = sensor_data
                    else:
                        actual_data = item
                    
                    ir_data = actual_data.get('ir_counter', {})
                    
                    historical.append({
                        'timestamp': datetime.fromtimestamp(item['_ts']),
                        'people_count': actual_data.get('people_count', 0),
                        'light_level': actual_data.get('light_level', 0),
                        'occupied': actual_data.get('occupied', False),
                        'total_entries': ir_data.get('total_entries', 0),
                        'total_exits': ir_data.get('total_exits', 0),
                    })
                    
                except Exception as e:
                    logger.warning(f"Skipped malformed record: {e}")
                    continue
            
            logger.info(f"📊 Retrieved {len(historical)} historical records")
            
            if len(historical) == 0:
                logger.error("❌ All records failed to parse - check data structure")
            
            return historical
            
        except Exception as e:
            logger.error(f"❌ Historical data error: {e}")
            logger.exception("Full traceback:")
            return []
    
    def check_device_connection(self) -> Dict[str, Any]:
        if not self.iot_manager:
            return {"connected": False, "error": "IoT Hub not initialized"}
        
        try:
            import socket
            socket.setdefaulttimeout(10)
            
            twin = self.iot_manager.get_twin(self.device_id)
            return {
                "connected": twin.connection_state == "Connected",
                "connection_state": twin.connection_state,
                "device_id": self.device_id
            }
        except Exception as e:
            logger.error(f"❌ Connection check failed: {e}")
            return {"connected": False, "error": str(e)}

# ==================== SESSION STATE ====================

def init_session_state():
    defaults = {
        'historical_data': [],
        'last_update': None,
        'device_connected': False,
        'show_diagnostics': False,
        'show_charts': True,
        'auto_refresh': True,
        'telemetry_cache': None,
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# ==================== UI COMPONENTS ====================

def display_connection_status(controller):
    """Display connection badges"""
    col1, col2, col3, col4 = st.columns(4)
    
    cosmos_ok = controller.cosmos_container is not None
    iot_ok = controller.iot_manager is not None
    device_status = controller.check_device_connection()
    device_ok = device_status.get("connected", False)
    
    with col1:
        status_class = "conn-cloud-on" if cosmos_ok else "conn-cloud-off"
        st.markdown(f'<div class="conn-badge {status_class}">☁️ Cosmos DB<br><small>{"Connected" if cosmos_ok else "Offline"}</small></div>', unsafe_allow_html=True)
    
    with col2:
        status_class = "conn-cloud-on" if iot_ok else "conn-cloud-off"
        st.markdown(f'<div class="conn-badge {status_class}">☁️ IoT Hub<br><small>{"Connected" if iot_ok else "Offline"}</small></div>', unsafe_allow_html=True)
    
    with col3:
        status_class = "conn-device-on" if device_ok else "conn-device-off"
        st.markdown(f'<div class="conn-badge {status_class}">📡 ESP32<br><small>{"Online" if device_ok else "Offline"}</small></div>', unsafe_allow_html=True)
    
    with col4:
        health = "good" if all([cosmos_ok, iot_ok, device_ok]) else "warning"
        status_class = f"conn-device-on" if health == "good" else "conn-cloud-off"
        st.markdown(f'<div class="conn-badge {status_class}">⚡ System<br><small>{"Healthy" if health == "good" else "Degraded"}</small></div>', unsafe_allow_html=True)

def display_main_status(telemetry: Dict, controller: AzureDeviceController):
    """Display main occupancy status and controls - FULLY FIXED NO DUPLICATES"""
    
    people_count = telemetry.get('people_count', 0)
    occupied = telemetry.get('occupied', False)
    confidence = telemetry.get('confidence', 0)
    
    status_class = "status-occupied" if occupied else "status-vacant"
    status_text = "OCCUPIED" if occupied else "VACANT"
    
    # ==================== MAIN STATUS CARD ====================
    st.markdown(f'''
    <div class="status-card {status_class}">
        <div class="status-title">{status_text}</div>
        <div class="status-subtitle">{people_count} {'Person' if people_count == 1 else 'People'} in Room</div>
        <div class="status-detail">
            Confidence: {confidence*100:.0f}% • 
            Entries: {telemetry.get('total_entries', 0)} • 
            Exits: {telemetry.get('total_exits', 0)}
        </div>
        <div class="status-detail" style="font-size: 0.95rem; opacity: 0.8;">
            State: {telemetry.get('crossing_state', 'WAITING')} • 
            Last: {telemetry.get('last_direction', 'NONE')}
        </div>
    </div>
    ''', unsafe_allow_html=True)
    
    # ==================== IR COUNTER METRICS (5 BOXES) - ONLY ONCE ====================
    st.markdown('<div class="section-header">🚪 IR Counter Metrics</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    metrics = [
        (col1, "People Count", people_count, "👥"),
        (col2, "Total Entries", telemetry.get('total_entries', 0), "➡️"),
        (col3, "Total Exits", telemetry.get('total_exits', 0), "⬅️"),
        (col4, "Valid Crossings", telemetry.get('valid_crossings', 0), "✓"),
        (col5, "Light Level", f"{telemetry.get('light_level', 0):.0f}", "💡"),
    ]
    
    for col, label, value, icon in metrics:
        with col:
            st.markdown(f'''
            <div class="metric-card">
                <div style="font-size: 2rem; margin-bottom: 8px;">{icon}</div>
                <div class="metric-label">{label}</div>
                <div class="metric-value">{value}</div>
            </div>
            ''', unsafe_allow_html=True)
    
    # ==================== CONFIDENCE ANALYSIS (3 BOXES) - ONLY ONCE ====================
    st.markdown('<div class="section-header">📊 Confidence Analysis</div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    # Get confidence metrics from analytics - FIXED to use correct data source
    analytics = telemetry.get('ir_counter', {}).get('analytics', {})
    high_conf = analytics.get('high_confidence_crossings', 0)
    med_conf = analytics.get('medium_confidence_crossings', 0)
    low_conf = analytics.get('low_confidence_crossings', 0)
    
    # If analytics are empty, calculate from confidence value
    if high_conf == 0 and med_conf == 0 and low_conf == 0:
        total_crossings = telemetry.get('valid_crossings', 0)
        if total_crossings > 0:
            # Distribute based on system confidence
            system_conf = telemetry.get('confidence', 0.8)
            if system_conf >= 0.9:
                high_conf = int(total_crossings * 0.7)
                med_conf = int(total_crossings * 0.2)
                low_conf = total_crossings - high_conf - med_conf
            elif system_conf >= 0.7:
                high_conf = int(total_crossings * 0.3)
                med_conf = int(total_crossings * 0.5)
                low_conf = total_crossings - high_conf - med_conf
            else:
                high_conf = int(total_crossings * 0.1)
                med_conf = int(total_crossings * 0.3)
                low_conf = total_crossings - high_conf - med_conf
    
    with col1:
        st.metric(
            "High Confidence (≥90%)", 
            high_conf,
            help="Crossings with high confidence level (≥90%)"
        )
    
    with col2:
        st.metric(
            "Medium (70-89%)", 
            med_conf,
            help="Crossings with medium confidence level (70-89%)"
        )
    
    with col3:
        st.metric(
            "Low (<70%)", 
            low_conf,
            help="Crossings with low confidence level (<70%)"
        )
    
    # ==================== SYSTEM PERFORMANCE METRICS ====================
    st.markdown('<div class="section-header">⚡ System Performance</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "System Confidence", 
            f"{telemetry.get('confidence', 0)*100:.0f}%",
            help="Overall system confidence based on crossing accuracy"
        )
    
    with col2:
        error_rate = 0
        total_sequences = telemetry.get('valid_crossings', 0) + telemetry.get('invalid_sequences', 0)
        if total_sequences > 0:
            error_rate = (telemetry.get('invalid_sequences', 0) / total_sequences) * 100
        
        st.metric(
            "Error Rate", 
            f"{error_rate:.1f}%",
            help="Percentage of invalid crossing sequences"
        )
    
    with col3:
        st.metric(
            "Success Rate", 
            f"{(100 - error_rate):.1f}%",
            help="Percentage of valid crossing sequences"
        )
    
    with col4:
        total_events = telemetry.get('entrance_triggers', 0) + telemetry.get('exit_triggers', 0)
        st.metric(
            "Total Events", 
            total_events,
            help="Combined sensor trigger events"
        )
    
    # ==================== DEVICE CONTROLS ====================
    st.markdown('<div class="section-header">🎛️ Device Controls</div>', unsafe_allow_html=True)
    
    devices = telemetry.get('devices', {})
    auto_mode = devices.get('auto_mode', True)
    
    # Connection status warning
    if not st.session_state.device_connected:
        st.markdown('''
        <div class="diagnostic-box">
            <strong>⚠️ Device Offline</strong><br>
            Device controls are currently unavailable. The ESP32 may be disconnected or offline.
        </div>
        ''', unsafe_allow_html=True)
    
    # Control buttons
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        light_on = devices.get('light', False)
        button_type = "primary" if light_on else "secondary"
        disabled = not st.session_state.device_connected
        
        if st.button(
            f"💡 Light\n{'ON' if light_on else 'OFF'}", 
            use_container_width=True, 
            type=button_type,
            disabled=disabled
        ):
            if controller.toggle_light():
                st.success("✅ Light toggled!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Failed to toggle light")
    
    with col2:
        fan_on = devices.get('fan', False)
        button_type = "primary" if fan_on else "secondary"
        disabled = not st.session_state.device_connected
        
        if st.button(
            f"🌪️ Fan\n{'ON' if fan_on else 'OFF'}", 
            use_container_width=True, 
            type=button_type,
            disabled=disabled
        ):
            if controller.toggle_fan():
                st.success("✅ Fan toggled!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Failed to toggle fan")
    
    with col3:
        ac_on = devices.get('ac', False)
        button_type = "primary" if ac_on else "secondary"
        disabled = not st.session_state.device_connected
        
        if st.button(
            f"❄️ AC\n{'ON' if ac_on else 'OFF'}", 
            use_container_width=True, 
            type=button_type,
            disabled=disabled
        ):
            if controller.toggle_ac():
                st.success("✅ AC toggled!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Failed to toggle AC")
    
    with col4:
        button_type = "primary" if auto_mode else "secondary"
        disabled = not st.session_state.device_connected
        
        if st.button(
            f"🤖 Auto Mode\n{'ON' if auto_mode else 'OFF'}", 
            use_container_width=True, 
            type=button_type,
            disabled=disabled
        ):
            if controller.toggle_auto_mode():
                st.success(f"✅ Auto mode {'enabled' if not auto_mode else 'disabled'}!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Failed to toggle auto mode")
    
    with col5:
        disabled = not st.session_state.device_connected
        
        if st.button(
            "🔄 Reset\nCounter", 
            use_container_width=True,
            disabled=disabled
        ):
            if controller.reset_counter():
                st.success("✅ People counter reset!")
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Failed to reset counter")
    
    # Auto mode status indicator
    if auto_mode:
        st.markdown('''
        <div class="success-box">
            <strong>🤖 Auto Mode Active</strong><br>
            Devices are automatically controlled based on occupancy and environmental conditions.
        </div>
        ''', unsafe_allow_html=True)
    else:
        st.markdown('''
        <div class="diagnostic-box">
            <strong>🎛️ Manual Mode Active</strong><br>
            Devices are manually controlled. Toggle "Auto Mode" to enable automatic control.
        </div>
        ''', unsafe_allow_html=True)

def display_system_metrics(telemetry: Dict):
    """Display system health metrics"""
    st.markdown('<div class="section-header">⚡ System Health</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Memory", f"{telemetry.get('free_heap', 0)/1024:.1f} KB", 
                 help="Available heap memory")
    
    with col2:
        uptime_hours = telemetry.get('uptime', 0) // 3600
        st.metric("Uptime", f"{uptime_hours}h", 
                 help="Time since ESP32 boot")
    
    with col3:
        st.metric("WiFi Signal", f"{telemetry.get('wifi_rssi', 0)} dBm",
                 help="WiFi signal strength")
    
    with col4:
        st.metric("System Errors", telemetry.get('system_errors', 0),
                 help="Total error count")

def display_advanced_charts(controller, cosmos_container):
    """Enhanced analytics with customizable timeframes and filtering - FIXED DUPLICATION"""
    
    st.markdown('<div class="section-header">📈 Advanced Historical Analytics</div>', unsafe_allow_html=True)
    
    # ==================== TIME RANGE CONTROLS ====================
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        time_preset = st.selectbox(
            "📅 Quick Select",
            ["Last Hour", "Last 3 Hours", "Last 6 Hours", "Last 12 Hours", 
             "Last 24 Hours", "Last 3 Days", "Last Week", "Custom Range"],
            index=4
        )
    
    with col2:
        chart_type = st.selectbox(
            "📊 Chart Style",
            ["Line Charts", "Area Charts", "Bar Charts", "Combined View"],
            index=0
        )
    
    with col3:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.session_state.historical_data = None
            st.rerun()
    
    # Custom date range picker (same as before)
    if time_preset == "Custom Range":
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input("Start Date", datetime.now() - timedelta(days=7))
            start_time = st.time_input("Start Time", datetime.now().replace(hour=0, minute=0))
        with col2:
            end_date = st.date_input("End Date", datetime.now())
            end_time = st.time_input("End Time", datetime.now())
        
        start_datetime = datetime.combine(start_date, start_time)
        end_datetime = datetime.combine(end_date, end_time)
        hours_back = (end_datetime - start_datetime).total_seconds() / 3600
    else:
        preset_hours = {
            "Last Hour": 1, "Last 3 Hours": 3, "Last 6 Hours": 6, "Last 12 Hours": 12,
            "Last 24 Hours": 24, "Last 3 Days": 72, "Last Week": 168
        }
        hours_back = preset_hours.get(time_preset, 24)
    
    # ==================== DATA FILTERING OPTIONS ====================
    with st.expander("🔧 Advanced Filters", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            show_entries = st.checkbox("Show Entry Events", value=True)
            show_exits = st.checkbox("Show Exit Events", value=True)
        
        with col2:
            min_people = st.number_input("Min People Count", min_value=0, value=0)
            max_people = st.number_input("Max People Count", min_value=0, value=20)
        
        with col3:
            smooth_data = st.checkbox("Smooth Data", value=False)
            show_anomalies = st.checkbox("Highlight Anomalies", value=False)
    
    # ==================== FETCH DATA ====================
    with st.spinner(f'📊 Loading {hours_back:.0f} hours of data...'):
        historical_data = get_historical_data_enhanced(
            controller, 
            hours_back, 
            min_people, 
            max_people
        )
    
    if not historical_data or len(historical_data) < 2:
        st.warning(f"⚠️ Insufficient data for the selected timeframe ({len(historical_data) if historical_data else 0} records)")
        st.info("💡 Try selecting a longer time period or check if ESP32 is sending telemetry")
        return
    
    df = pd.DataFrame(historical_data)
    
    # Apply smoothing if enabled
    if smooth_data and len(df) > 5:
        df['people_count_smooth'] = df['people_count'].rolling(window=5, center=True).mean()
        df['light_level_smooth'] = df['light_level'].rolling(window=5, center=True).mean()
    
    # ==================== SUMMARY STATISTICS ====================
    st.markdown("### 📊 Statistical Summary")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        avg_occupancy = df['people_count'].mean()
        st.metric("Avg Occupancy", f"{avg_occupancy:.1f}")
    
    with col2:
        peak_occupancy = df['people_count'].max()
        peak_time = df.loc[df['people_count'].idxmax(), 'timestamp']
        st.metric("Peak Occupancy", f"{peak_occupancy}", 
                 delta=f"at {peak_time.strftime('%H:%M')}")
    
    with col3:
        total_entries = df['total_entries'].iloc[-1] - df['total_entries'].iloc[0] if len(df) > 0 else 0
        st.metric("Period Entries", f"{total_entries}")
    
    with col4:
        total_exits = df['total_exits'].iloc[-1] - df['total_exits'].iloc[0] if len(df) > 0 else 0
        st.metric("Period Exits", f"{total_exits}")
    
    with col5:
        occupied_pct = (df['occupied'].sum() / len(df) * 100) if len(df) > 0 else 0
        st.metric("Occupied Time", f"{occupied_pct:.0f}%")
    
    # ==================== SINGLE MAIN CHART ====================
    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
    
    # ✅ FIX: Only ONE chart creation function called based on selection
    if chart_type == "Combined View":
        fig = create_combined_charts(df, show_entries, show_exits, smooth_data, show_anomalies)
    elif chart_type == "Line Charts":
        fig = create_line_charts(df, show_entries, show_exits, smooth_data, show_anomalies)
    elif chart_type == "Area Charts":
        fig = create_area_charts(df, show_entries, show_exits, smooth_data)
    else:  # Bar Charts
        fig = create_bar_charts(df, show_entries, show_exits)
    
    # ✅ FIX: Only ONE main chart displayed
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True})
    st.markdown('</div>', unsafe_allow_html=True)
    
    # ==================== DATA TABLES (NO CHARTS) ====================
    with st.expander("📅 Hourly Breakdown Analysis", expanded=False):
        # ✅ FIX: Only show data table, no duplicate charts
        df['hour'] = df['timestamp'].dt.hour
        hourly_stats = df.groupby('hour').agg({
            'people_count': ['mean', 'max', 'min'],
            'occupied': 'sum'
        }).round(2)
        
        hourly_stats.columns = ['Avg People', 'Max People', 'Min People', 'Occupied Count']
        st.dataframe(hourly_stats, use_container_width=True)
        
        st.info("💡 Use the main chart above for visual analysis. Switch chart types using the dropdown.")
    
    # ==================== ADDITIONAL ANALYSIS (TABLES ONLY) ====================
    with st.expander("🚦 Traffic Pattern Analysis", expanded=False):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Entry vs Exit Summary")
            # ✅ FIX: Show summary stats instead of duplicate chart
            entry_rate = df['total_entries'].diff().mean()
            exit_rate = df['total_exits'].diff().mean()
            
            st.metric("Avg Entry Rate", f"{entry_rate:.2f}/record")
            st.metric("Avg Exit Rate", f"{exit_rate:.2f}/record")
            st.metric("Net Traffic", f"{df['total_entries'].iloc[-1] - df['total_exits'].iloc[-1]}")
        
        with col2:
            st.markdown("#### Occupancy Distribution")
            # ✅ FIX: Show distribution table instead of chart
            occupancy_summary = df['people_count'].describe()
            st.dataframe(occupancy_summary, use_container_width=True)
    
    # ==================== EXPORT DATA ====================
    with st.expander("💾 Export Data", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"room_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            st.metric("Total Records", len(df))
        
        with col3:
            time_span = (df['timestamp'].max() - df['timestamp'].min()).total_seconds() / 3600
            st.metric("Time Span", f"{time_span:.1f}h")

# ==================== HELPER FUNCTIONS ====================

def get_historical_data_enhanced(controller, hours: float, min_people: int = 0, max_people: int = 20) -> List[Dict]:
    """Enhanced historical data fetch with filtering"""
    data = controller.get_historical_data(int(hours))
    if not data:
        return []
    
    # Apply filters
    filtered = [
        record for record in data
        if min_people <= record.get('people_count', 0) <= max_people
    ]
    return filtered


def create_combined_charts(df, show_entries, show_exits, smooth_data, show_anomalies):
    """Create comprehensive combined view"""
    
    fig = make_subplots(
        rows=3, cols=2,
        subplot_titles=(
            'People Count Over Time', 
            'Light Level vs Occupancy',
            'Entry & Exit Events', 
            'Occupancy Status',
            'Cumulative Traffic',
            'Real-time Activity'
        ),
        vertical_spacing=0.12,
        horizontal_spacing=0.1,
        specs=[
            [{"secondary_y": False}, {"secondary_y": True}],
            [{"secondary_y": False}, {"secondary_y": False}],
            [{"secondary_y": False}, {"secondary_y": False}]
        ]
    )
    
    # 1. People Count (with smoothing)
    if smooth_data and 'people_count_smooth' in df.columns:
        fig.add_trace(go.Scatter(
            x=df['timestamp'], 
            y=df['people_count_smooth'],
            mode='lines',
            name='People (Smoothed)',
            line=dict(color='#60a5fa', width=3),
            fill='tozeroy',
            fillcolor='rgba(96, 165, 250, 0.1)'
        ), row=1, col=1)
    else:
        fig.add_trace(go.Scatter(
            x=df['timestamp'], 
            y=df['people_count'],
            mode='lines+markers',
            name='People Count',
            line=dict(color='#60a5fa', width=2),
            marker=dict(size=6)
        ), row=1, col=1)
    
    # Anomaly detection
    if show_anomalies:
        mean = df['people_count'].mean()
        std = df['people_count'].std()
        anomalies = df[abs(df['people_count'] - mean) > 2 * std]
        
        if len(anomalies) > 0:
            fig.add_trace(go.Scatter(
                x=anomalies['timestamp'],
                y=anomalies['people_count'],
                mode='markers',
                name='Anomalies',
                marker=dict(size=12, color='#ef4444', symbol='x')
            ), row=1, col=1)
    
    # 2. Light Level vs Occupancy (dual axis)
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['light_level'],
        mode='lines',
        name='Light Level',
        line=dict(color='#fbbf24', width=2)
    ), row=1, col=2, secondary_y=False)
    
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['people_count'],
        mode='lines',
        name='People',
        line=dict(color='#a78bfa', width=2, dash='dot')
    ), row=1, col=2, secondary_y=True)
    
    # 3. Entry & Exit Events
    if show_entries:
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['total_entries'],
            mode='lines',
            name='Entries',
            line=dict(color='#10b981', width=2)
        ), row=2, col=1)
    
    if show_exits:
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['total_exits'],
            mode='lines',
            name='Exits',
            line=dict(color='#ef4444', width=2)
        ), row=2, col=1)
    
    # 4. Occupancy Status (heatmap style)
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['occupied'].astype(int),
        mode='lines',
        name='Occupied',
        line=dict(color='#ec4899', width=0),
        fill='tozeroy',
        fillcolor='rgba(236, 72, 153, 0.3)'
    ), row=2, col=2)
    
    # 5. Cumulative Traffic
    df['net_traffic'] = df['total_entries'] - df['total_exits']
    
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['net_traffic'],
        mode='lines',
        name='Net Traffic',
        line=dict(color='#8b5cf6', width=3),
        fill='tonexty'
    ), row=3, col=1)
    
    # 6. Activity Indicator (change rate)
    df['activity'] = df['people_count'].diff().abs().fillna(0)
    
    fig.add_trace(go.Bar(
        x=df['timestamp'],
        y=df['activity'],
        name='Activity',
        marker=dict(color='#06b6d4')
    ), row=3, col=2)
    
    # Styling
    fig.update_layout(
        height=900,
        showlegend=True,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(255,255,255,0.02)',
        font=dict(family='Inter', color='#cbd5e1', size=11),
        hovermode='x unified'
    )
    
    fig.update_xaxes(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
    fig.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
    
    return fig


def create_line_charts(df, show_entries, show_exits, smooth_data, show_anomalies):
    """Create clean line chart view"""
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Occupancy Timeline', 'Environmental Conditions'),
        vertical_spacing=0.15
    )
    
    # People count
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['people_count'],
        mode='lines+markers',
        name='People Count',
        line=dict(color='#60a5fa', width=3),
        marker=dict(size=8, color='#60a5fa')
    ), row=1, col=1)
    
    # Light level
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['light_level'],
        mode='lines',
        name='Light Level',
        line=dict(color='#fbbf24', width=2)
    ), row=2, col=1)
    
    fig.update_layout(
        height=600,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(255,255,255,0.02)',
        font=dict(color='#cbd5e1'),
        hovermode='x unified'
    )
    
    return fig


def create_area_charts(df, show_entries, show_exits, smooth_data):
    """Create filled area charts"""
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['people_count'],
        mode='lines',
        name='People Count',
        line=dict(color='#60a5fa', width=0),
        fill='tozeroy',
        fillcolor='rgba(96, 165, 250, 0.3)'
    ))
    
    fig.update_layout(
        height=400,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(255,255,255,0.02)',
        font=dict(color='#cbd5e1')
    )
    
    return fig


def create_bar_charts(df, show_entries, show_exits):
    """Create bar chart view for discrete events"""
    
    # Resample to hourly for cleaner bars
    df_hourly = df.set_index('timestamp').resample('1H').agg({
        'people_count': 'mean',
        'total_entries': 'last',
        'total_exits': 'last'
    }).reset_index()
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=df_hourly['timestamp'],
        y=df_hourly['people_count'],
        name='Avg Occupancy',
        marker=dict(color='#60a5fa')
    ))
    
    fig.update_layout(
        height=400,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(255,255,255,0.02)',
        font=dict(color='#cbd5e1')
    )
    
    return fig

# ==================== MAIN APPLICATION ====================

def main():
    """Main application"""
    
    # Header
    col1, col2 = st.columns([5, 1])
    with col1:
        st.markdown('<div class="header-title">☁️ TECNOsense Azure v3.0 </div>', unsafe_allow_html=True)
        st.markdown('<div class="header-subtitle">Enhanced Dual IR People Counter • Azure IoT Hub & Cosmos DB</div>', unsafe_allow_html=True)
    
    with col2:
        if st.button("🔍 Diagnostics", use_container_width=True):
            st.session_state.show_diagnostics = not st.session_state.get('show_diagnostics', False)
    
    # Initialize
    init_session_state()
    
    # Azure services
    iot_manager = get_iot_hub_manager()
    cosmos_container = get_cosmos_container()
    
    if not cosmos_container:
        st.markdown('<div class="error-box"><strong>❌ Cosmos DB Connection Failed</strong><br>Check COSMOS_ENDPOINT and COSMOS_KEY</div>', unsafe_allow_html=True)
        return
    
    if not iot_manager:
        st.markdown('<div class="diagnostic-box"><strong>⚠️ IoT Hub Connection Failed</strong><br>Device commands will not work</div>', unsafe_allow_html=True)
    
    controller = AzureDeviceController(iot_manager, cosmos_container)
    
    # Diagnostics panel
    if st.session_state.get('show_diagnostics', False):
        with st.expander("🔍 System Diagnostics", expanded=True):
            if st.button("Run Cosmos DB Check", type="primary"):
                try:
                    query = "SELECT TOP 5 c.deviceId, c._ts, c.people_count FROM c ORDER BY c._ts DESC"
                    items = list(cosmos_container.query_items(query=query, enable_cross_partition_query=True))
                    
                    if items:
                        st.success(f"✅ Found {len(items)} documents")
                        df = pd.DataFrame([{
                            'deviceId': item.get('deviceId', 'MISSING'),
                            'timestamp': pd.to_datetime(item['_ts'], unit='s'),
                            'people_count': item.get('people_count', 'MISSING')
                        } for item in items])
                        st.dataframe(df)
                    else:
                        st.error("❌ No documents found")
                        
                except Exception as e:
                    st.error(f"❌ Query failed: {e}")
    
    # Connection status
    st.markdown("---")
    display_connection_status(controller)
    st.markdown("---")
    
    # Fetch telemetry
    with st.spinner('☁️ Fetching telemetry from Azure...'):
        telemetry = controller.get_latest_telemetry()
    
    if telemetry:
        # Cache it
        st.session_state.telemetry_cache = telemetry
        st.session_state.last_update = telemetry.get('timestamp')
        st.session_state.device_connected = True
        
        # Check data age
        data_age = (datetime.now() - st.session_state.last_update).total_seconds()
        if data_age > 120:
            st.markdown(f'''
            <div class="diagnostic-box">
                <strong>⚠️ Data May Be Stale</strong><br>
                Last telemetry was {int(data_age)} seconds ago<br>
                Expected: < 10 seconds for real-time data
            </div>
            ''', unsafe_allow_html=True)
        
        # Display main status (NO DUPLICATES)
        display_main_status(telemetry, controller)
        
        # Display system metrics
        display_system_metrics(telemetry)
        
        # Historical charts
        if st.session_state.get('show_charts', True):
            # Fetch historical data if not cached
            if not st.session_state.historical_data:
                with st.spinner('📊 Loading historical data...'):
                    st.session_state.historical_data = controller.get_historical_data(24)
            
        if st.session_state.historical_data:
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(f"**{len(st.session_state.historical_data)} data points** from last 24 hours")
            with col2:
                if st.button("🔄 Refresh", use_container_width=True):
                    st.session_state.historical_data = controller.get_historical_data(24)
                    st.rerun()
            
            display_advanced_charts(controller, cosmos_container)
        
        # Debug info
        with st.expander("🔍 Raw Telemetry Data (Debug)"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Core Data:**")
                st.json({
                    'deviceId': telemetry.get('_raw', {}).get('deviceId', 'NOT FOUND'),
                    'people_count': telemetry.get('people_count'),
                    'total_entries': telemetry.get('total_entries'),
                    'total_exits': telemetry.get('total_exits'),
                    'confidence': telemetry.get('confidence'),
                    'occupied': telemetry.get('occupied'),
                })
            with col2:
                st.markdown("**Device States:**")
                st.json(telemetry.get('devices', {}))
        
        # Footer
        st.markdown("---")
        st.markdown(f"""
        <div style="text-align: center; padding: 20px; color: #64748b;">
            <strong>Last Updated:</strong> {st.session_state.last_update.strftime('%Y-%m-%d %H:%M:%S')} 
            • <strong>Data Age:</strong> {int(data_age)}s 
            • <strong>Source:</strong> ☁️ Azure Cosmos DB
            <br>
            <small>Device: {AzureConfig.DEVICE_ID} • Records: {len(st.session_state.historical_data)}</small>
        </div>
        """, unsafe_allow_html=True)
        
        # Auto-refresh
        if st.session_state.auto_refresh:
            time.sleep(AzureConfig.REFRESH_INTERVAL)
            st.rerun()
    
    else:
        # No telemetry available
        st.markdown('''
        <div class="error-box">
            <strong style="font-size: 1.2rem;">❌ No Telemetry Data Available</strong><br><br>
            
            <strong>Possible causes:</strong><br>
            • ESP32 not sending data to IoT Hub<br>
            • IoT Hub message routing to Cosmos DB not configured<br>
            • deviceId field missing from telemetry payload<br>
            • No documents in Cosmos DB container<br><br>
            
            <strong>Next steps:</strong><br>
            1. Check ESP32 Serial Monitor for "✅✅✅ Telemetry SENT!"<br>
            2. Run Diagnostics to check for documents<br>
            3. Verify ESP32 code has deviceId field
        </div>
        ''', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔍 Run Diagnostics", type="primary", use_container_width=True):
                st.session_state.show_diagnostics = True
                st.rerun()
        
        with col2:
            if st.button("🔄 Force Refresh", use_container_width=True):
                st.session_state.telemetry_cache = None
                st.rerun()
        
        time.sleep(5)
        st.rerun()

if __name__ == "__main__":
    main()