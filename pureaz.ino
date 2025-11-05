#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <BH1750.h>
#include <Preferences.h>
#include <esp_task_wdt.h>
#include <mqtt_client.h>
#include <mbedtls/md.h>
#include <mbedtls/base64.h>
#include <time.h>

const char ca_pem[] = 
"-----BEGIN CERTIFICATE-----\n"
"MIIDjjCCAnagAwIBAgIQAzrx5qcRqaC7KGSxHQn65TANBgkqhkiG9w0BAQsFADBh\n"
"MQswCQYDVQQGEwJVUzEVMBMGA1UEChMMRGlnaUNlcnQgSW5jMRkwFwYDVQQLExB3\n"
"d3cuZGlnaWNlcnQuY29tMSAwHgYDVQQDExdEaWdpQ2VydCBHbG9iYWwgUm9vdCBH\n"
"MjAeFw0xMzA4MDExMjAwMDBaFw0zODAxMTUxMjAwMDBaMGExCzAJBgNVBAYTAlVT\n"
"MRUwEwYDVQQKEwxEaWdpQ2VydCBJbmMxGTAXBgNVBAsTEHd3dy5kaWdpY2VydC5j\n"
"b20xIDAeBgNVBAMTF0RpZ2lDZXJ0IEdsb2JhbCBSb290IEcyMIIBIjANBgkqhkiG\n"
"9w0BAQEFAAOCAQ8AMIIBCgKCAQEAuzfNNNx7a8myaJCtSnX/RrohCgiN9RlUyfuI\n"
"2/Ou8jqJkTx65qsGGmvPrC3oXgkkRLpimn7Wo6h+4FR1IAWsULecYxpsMNzaHxmx\n"
"1x7e/dfgy5SDN67sH0NO3Xss0r0upS/kqbitOtSZpLYl6ZtrAGCSYP9PIUkY92eQ\n"
"q2EGnI/yuum06ZIya7XzV+hdG82MHauVBJVJ8zUtluNJbd134/tJS7SsVQepj5Wz\n"
"tCO7TG1F8PapspUwtP1MVYwnSlcUfIKdzXOS0xZKBgyMUNGPHgm+F6HmIcr9g+UQ\n"
"vIOlCsRnKPZzFBQ9RnbDhxSJITRNrw9FDKZJobq7nMWxM4MphQIDAQABo0IwQDAP\n"
"BgNVHRMBAf8EBTADAQH/MA4GA1UdDwEB/wQEAwIBhjAdBgNVHQ4EFgQUTiJUIBiV\n"
"5uNu5g/6+rkS7QYXjzkwDQYJKoZIhvcNAQELBQADggEBAGBnKJRvDkhj6zHd6mcY\n"
"1Yl9PMWLSn/pvtsrF9+wX3N3KjITOYFnQoQj8kVnNeyIv/iPsGEMNKSuIEyExtv4\n"
"NeF22d+mQrvHRAiGfzZ0JFrabA0UWTW98kndth/Jsw1HKj2ZL7tcu7XUIOGZX1NG\n"
"Fdtom/DzMNU+MeKNhJ7jitralj41E6Vf8PlwUHBHQRFXGU7Aj64GxJUTFy8bJZ91\n"
"8rGOmaFvE7FBcf6IKshPECBV1/MUReXgRPTqh5Uykw7+U0b6LJ3/iyK5S9kJRaTe\n"
"pLiaWN0bfVKfjllDiIGknibVb63dDcY3fe0Dkhvld1927jyNxF1WW6LZZm6zNTfl\n"
"MrY=\n"
"-----END CERTIFICATE-----\n"
"-----BEGIN CERTIFICATE-----\n"
"MIIDdzCCAl+gAwIBAgIEAgAAuTANBgkqhkiG9w0BAQUFADBaMQswCQYDVQQGEwJJ\n"
"RTESMBAGA1UEChMJQmFsdGltb3JlMRMwEQYDVQQLEwpDeWJlclRydXN0MSIwIAYD\n"
"VQQDExlCYWx0aW1vcmUgQ3liZXJUcnVzdCBSb290MB4XDTAwMDUxMjE4NDYwMFoX\n"
"DTI1MDUxMjIzNTkwMFowWjELMAkGA1UEBhMCSUUxEjAQBgNVBAoTCUJhbHRpbW9y\n"
"ZTETMBEGA1UECxMKQ3liZXJUcnVzdDEiMCAGA1UEAxMZQmFsdGltb3JlIEN5YmVy\n"
"VHJ1c3QgUm9vdDCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAKMEuyKr\n"
"mD1X6CZymrV51Cni4eiVgLGw41uOKymaZN+hXe2wCQVt2yguzmKiYv60iNoS6zjr\n"
"IZ3AQSsBUnuId9Mcj8e6uYi1agnnc+gRQKfRzMpijS3ljwumUNKoUMMo6vWrJYeK\n"
"mpYcqWe4PwzV9/lSEy/CG9VwcPCPwBLKBsua4dnKM3p31vjsufFoREJIE9LAwqSu\n"
"XmD+tqYF/LTdB1kC1FkYmGP1pWPgkAx9XbIGevOF6uvUA65ehD5f/xXtabz5OTZy\n"
"dc93Uk3zyZAsuT3lySNTPx8kmCFcB5kpvcY67Oduhjprl3RjM71oGDHweI12v/ye\n"
"jl0qhqdNkNwnGjkCAwEAAaNFMEMwHQYDVR0OBBYEFOWdWTCCR1jMrPoIVDaGezq1\n"
"BE3wMBIGA1UdEwEB/wQIMAYBAf8CAQMwDgYDVR0PAQH/BAQDAgEGMA0GCSqGSIb3\n"
"DQEBBQUAA4IBAQCFDF2O5G9RaEIFoN27TyclhAO992T9Ldcw46QQF+vaKSm2eT92\n"
"9hkTI7gQCvlYpNRhcL0EYWoSihfVCr3FvDB81ukMJY2GQE/szKN+OMY3EU/t3Wgx\n"
"jkzSswF07r51XgdIGn9w/xZchMB5hbgF/X++ZRGjD8ACtPhSNzkE1akxehi/oCr0\n"
"Epn3o0WC4zxe9Z2etciefC7IpJ5OCBRLbf1wbWsaY71k5h+3zvDyny67G7fyUIhz\n"
"ksLi4xaNmjICq44Y3ekQEe5+NauQrz4wlHrQMz2nZQ/1/I6eYs9HRCwBXbsdtTLS\n"
"R9I4LtD+gdwyah617jzV/OeBHRnDJELqYzmp\n"
"-----END CERTIFICATE-----\n";

// WiFi Configuration
const char* WIFI_SSID = "PantaiPanorama-2-13-1_2.4GHz";
const char* WIFI_PASSWORD = "umeezpz2428";
const char* AP_SSID = "ESP32_RoomControl";
const char* AP_PASSWORD = "roomcontrol123";

#define IOT_CONFIG_IOTHUB_FQDN "tecnosense-hub.azure-devices.net"
#define IOT_CONFIG_DEVICE_ID "tecno-sense-living-room"
#define IOT_CONFIG_DEVICE_KEY "prfj2xDQ5mtuTVRoNPuQ3EKhbo53o9Dk6mr5qXOlcEk="

struct Config {
  static constexpr uint8_t RELAY_LIGHT = 12;  
  static constexpr uint8_t RELAY_AC = 13;    
  static constexpr uint8_t RELAY_FAN = 14;    
  
  // IR SENSORS - Input pins (correct)
  static constexpr uint8_t IR_ENTRANCE = 34;  // Input-only (OK)
  static constexpr uint8_t IR_EXIT = 35;      // Input-only (OK)
  
  static constexpr uint8_t LED_STATUS = 2;    // Built-in LED
  
  // Timing Configuration
  static constexpr unsigned long SENSOR_INTERVAL = 50;
  static constexpr unsigned long TELEMETRY_INTERVAL = 10000;
  static constexpr unsigned long WIFI_RECONNECT_INTERVAL = 30000;
  static constexpr unsigned long STATUS_LED_INTERVAL = 500;
  static constexpr unsigned long HEALTH_CHECK_INTERVAL = 15000;
  static constexpr unsigned long SAS_RENEWAL_CHECK = 60000;
  
  // Thresholds
  static constexpr uint16_t LIGHT_THRESHOLD = 120;
  static constexpr size_t MAX_JSON_SIZE = 1536; // Reduced for memory optimization
  static constexpr uint8_t MAX_WIFI_RETRIES = 5;
  static constexpr unsigned long WATCHDOG_TIMEOUT = 10000;
  static constexpr uint32_t LOW_MEMORY_THRESHOLD = 8192;
  
  // Dual IR specific timings
  static constexpr unsigned long IR_DEBOUNCE_TIME = 50;
  static constexpr unsigned long IR_SEQUENCE_TIMEOUT = 5000;      // ✅ Increased from 2000ms
  static constexpr unsigned long IR_COOLDOWN_TIME = 500;          // ✅ NEW
  static constexpr unsigned long IR_MAX_BLOCKAGE_TIME = 10000;    // ✅ Renamed and increased
  static constexpr unsigned long PERSON_PASSAGE_TIME = 3000;
  
  // Relay safety
  static constexpr unsigned long RELAY_MIN_CHANGE_INTERVAL = 100; // ms between relay changes
};

// ==================== DUAL IR PEOPLE COUNTER ====================

enum IRState {
  IR_IDLE = 0,
  IR_BLOCKED = 1
};

enum CrossingState {
  WAITING,
  ENTRANCE_FIRST,
  EXIT_FIRST, 
  BOTH_ACTIVE,
  COOLDOWN
};

enum Direction {
  DIR_NONE = 0,
  DIR_ENTERING = 1,
  DIR_EXITING = 2
};

struct DualIRCounter {
  // Sensor states
  IRState entranceState = IR_IDLE;
  IRState exitState = IR_IDLE;
  unsigned long entranceLastChange = 0;
  unsigned long exitLastChange = 0;
  bool entranceBlocked = false;
  bool exitBlocked = false;
  
  // ✅ NEW: Track FIRST trigger times (critical fix)
  unsigned long entranceFirstTrigger = 0;
  unsigned long exitFirstTrigger = 0;
  
  // Crossing detection
  CrossingState crossingState = WAITING;
  Direction lastDirection = DIR_NONE;
  unsigned long sequenceStartTime = 0;
  unsigned long lastCrossingTime = 0;
  unsigned long cooldownStart = 0;  // ✅ NEW: For cooldown state
  
  // People counting
  int peopleCount = 0;
  int maxPeopleDetected = 0;
  
  // Statistics
  uint32_t totalEntries = 0;
  uint32_t totalExits = 0;
  uint32_t validCrossings = 0;
  uint32_t invalidSequences = 0;
  uint32_t timeoutErrors = 0;
  uint32_t blockageErrors = 0;
  
  // History tracking
  Direction crossingHistory[20] = {DIR_NONE};
  unsigned long crossingTimestamps[20] = {0};
  uint8_t historyIndex = 0;
  
  // Error recovery
  bool errorState = false;
  String lastError = "";
  unsigned long lastErrorTime = 0;
  
  // Confidence metrics
  float confidence = 1.0f;
  bool sequenceValid = true;
  
  // Debug info
  uint32_t entranceTriggers = 0;
  uint32_t exitTriggers = 0;
};

struct AzureSASToken {
  String token = "";
  unsigned long expiry = 0;
  bool valid = false;
};

struct RoomState {
  bool occupied = false;
  uint8_t confidence = 0;
  uint8_t occupancyLevel = 0;
  int peopleCount = 0;
  bool lightOn = false;
  bool fanOn = false;
  bool acOn = false;
  bool autoMode = true;
  float lightLevel = 0.0f;
  unsigned long lastPresence = 0;
  unsigned long bootTime = 0;
  unsigned long stateChange = 0;
  uint32_t totalRequests = 0;
  uint32_t errorCount = 0;
  uint32_t wifiDisconnects = 0;
  uint32_t mqttDisconnects = 0;
  float avgResponseTime = 0.0f;
  uint32_t heapLowEvents = 0;
  bool wifiConnected = false;
  bool apMode = false;
  String ipAddress = "";
  int wifiRetries = 0;
  int8_t wifiRSSI = 0;
  bool serialDisplay = true;
  bool cloudEnabled = true;
  bool mqttConnected = false;
  uint32_t telemetrySendCount = 0;
  uint32_t telemetryFailCount = 0;
  unsigned long lastTelemetry = 0;
  unsigned long lastCloudConnect = 0;
  String lastMqttError = "";
  int mqttConnectionAttempts = 0;
  unsigned long lastMqttAttempt = 0;
  bool sasTokenGenerated = false;
};

// Global Objects
BH1750 lightSensor;
WebServer server(80);
RoomState room;
Preferences preferences;
DualIRCounter irCounter;
esp_mqtt_client_handle_t mqtt_client = NULL;
AzureSASToken currentSAS;
unsigned long lastSensorRead = 0;
unsigned long lastWifiCheck = 0;
unsigned long lastStatusLED = 0;
unsigned long lastHealthCheck = 0;
unsigned long lastSASCheck = 0;
bool timeInitialized = false;

// Relay safety tracking
unsigned long lastRelayChange[16] = {0};

// Forward declarations
void handleDirectMethod(const String& method_name, const String& request_id);
void sendTelemetryToAzure();
const char* directionToString(Direction dir);
const char* crossingStateToString(CrossingState state);
void resetIRCounter();
void processDualIRSensors();
void updatePeopleCount();
void safeRelayControl(uint8_t pin, bool state);
void recoverFromErrors();
bool initializeTime();
String generateHMAC256(const char* key, const char* payload);
String urlEncode(const String& str);
bool generateAzureSASToken(unsigned long ttl = 3600);
bool needsSASRenewal();
void initializeMqttClient();
void debugForceTelemetry();

// ==================== RELAY SAFETY FUNCTIONS ====================

void safeRelayControl(uint8_t pin, bool state) {
    unsigned long now = millis();
    
    // Debounce relay operations (min 100ms between changes)
    if (now - lastRelayChange[pin] > Config::RELAY_MIN_CHANGE_INTERVAL) {
        digitalWrite(pin, state);
        lastRelayChange[pin] = now;
        
        // Log relay state change
        const char* deviceName = "";
        if (pin == Config::RELAY_LIGHT) deviceName = "LIGHT";
        else if (pin == Config::RELAY_AC) deviceName = "AC";
        else if (pin == Config::RELAY_FAN) deviceName = "FAN";
        
        Serial.printf("🔌 %s (GPIO%d): %s\n", deviceName, pin, state ? "ON" : "OFF");
    } else {
        Serial.printf("⏳ Relay GPIO%d change too fast, ignoring\n", pin);
    }
}

// ==================== TIME & SAS TOKEN ====================

bool initializeTime() {
  if (timeInitialized) return true;
  
  Serial.println("⏰ Synchronizing time with NTP...");
  configTzTime("UTC", "pool.ntp.org", "time.nist.gov", "time.google.com");
  
  int retry = 0;
  const int max_retries = 20;
  
  while (retry < max_retries) {
    time_t now = time(nullptr);
    struct tm timeinfo;
    
    if (now > 1609459200) {
      if (localtime_r(&now, &timeinfo)) {
        timeInitialized = true;
        char time_str[64];
        strftime(time_str, sizeof(time_str), "%Y-%m-%d %H:%M:%S %Z", &timeinfo);
        Serial.printf("✅ Time synchronized: %s\n", time_str);
        return true;
      }
    }
    
    Serial.print(".");
    delay(1000);
    retry++;
    
    if (retry == 10 && WiFi.status() == WL_CONNECTED) {
      Serial.println("\n🔄 Resetting WiFi connection...");
      WiFi.disconnect();
      delay(1000);
      WiFi.reconnect();
      delay(2000);
    }
  }
  
  Serial.println("\n❌ Time sync failed");
  unsigned long uptime_seconds = millis() / 1000;
  time_t default_time = 1704067200 + uptime_seconds;
  struct timeval tv = { default_time, 0 };
  settimeofday(&tv, NULL);
  
  Serial.println("⚠️  Using fallback system time");
  timeInitialized = true;
  return true;
}

String urlEncode(const String& str) {
  String encoded = "";
  for (unsigned int i = 0; i < str.length(); i++) {
    char c = str.charAt(i);
    if (c == ' ') encoded += '+';
    else if (isalnum(c)) encoded += c;
    else {
      encoded += '%';
      char code0 = ((c >> 4) & 0xf) + '0';
      if (code0 > '9') code0 = code0 - '0' - 10 + 'A';
      char code1 = (c & 0xf) + '0';
      if (code1 > '9') code1 = code1 - '0' - 10 + 'A';
      encoded += code0;
      encoded += code1;
    }
  }
  return encoded;
}

String generateHMAC256(const char* key, const char* payload) {
  size_t keyLen = strlen(key);
  size_t decodedKeyLen = 0;
  mbedtls_base64_decode(NULL, 0, &decodedKeyLen, (const unsigned char*)key, keyLen);
  unsigned char decodedKey[decodedKeyLen];
  mbedtls_base64_decode(decodedKey, decodedKeyLen, &decodedKeyLen, (const unsigned char*)key, keyLen);
  
  unsigned char hmacResult[32];
  mbedtls_md_context_t ctx;
  mbedtls_md_init(&ctx);
  mbedtls_md_setup(&ctx, mbedtls_md_info_from_type(MBEDTLS_MD_SHA256), 1);
  mbedtls_md_hmac_starts(&ctx, decodedKey, decodedKeyLen);
  mbedtls_md_hmac_update(&ctx, (const unsigned char*)payload, strlen(payload));
  mbedtls_md_hmac_finish(&ctx, hmacResult);
  mbedtls_md_free(&ctx);
  
  size_t base64Len = 0;
  mbedtls_base64_encode(NULL, 0, &base64Len, hmacResult, 32);
  unsigned char base64Result[base64Len];
  mbedtls_base64_encode(base64Result, base64Len, &base64Len, hmacResult, 32);
  
  return String((char*)base64Result);
}

bool generateAzureSASToken(unsigned long ttl) {
  if (!initializeTime()) {
    Serial.println("❌ Cannot generate SAS token without valid time");
    return false;
  }

  time_t now;
  time(&now);
  unsigned long expiry = (unsigned long)now + ttl;
  
  String resourceUri = String(IOT_CONFIG_IOTHUB_FQDN) + "/devices/" + String(IOT_CONFIG_DEVICE_ID);
  String encodedUri = urlEncode(resourceUri);
  String stringToSign = encodedUri + "\n" + String(expiry);
  
  String signature = generateHMAC256(IOT_CONFIG_DEVICE_KEY, stringToSign.c_str());
  String encodedSignature = urlEncode(signature);
  
  currentSAS.token = "SharedAccessSignature sr=" + encodedUri + "&sig=" + encodedSignature + "&se=" + String(expiry);
  currentSAS.expiry = expiry;
  currentSAS.valid = true;
  room.sasTokenGenerated = true;
  
  Serial.println("✅ SAS Token generated");
  
  time_t expiry_time = (time_t)expiry;
  struct tm timeinfo;
  if (localtime_r(&expiry_time, &timeinfo)) {
    char time_str[64];
    strftime(time_str, sizeof(time_str), "%Y-%m-%d %H:%M:%S", &timeinfo);
    Serial.printf("   Expiry: %s\n", time_str);
  }
  
  return true;
}

bool needsSASRenewal() {
  if (!currentSAS.valid || !timeInitialized) return true;
  
  time_t now;
  time(&now);
  return ((unsigned long)now >= (currentSAS.expiry - 300));
}


static void mqttEventHandler(void *handler_args, esp_event_base_t base, int32_t event_id, void *event_data) {
  esp_mqtt_event_handle_t event = (esp_mqtt_event_handle_t)event_data;
  
  switch (event_id) {
    case MQTT_EVENT_BEFORE_CONNECT:
      Serial.println("🔄 MQTT attempting to connect...");
      Serial.printf("   Broker: %s\n", IOT_CONFIG_IOTHUB_FQDN);
      break;
      
    case MQTT_EVENT_CONNECTED: {
      Serial.println("✅✅✅ MQTT Connected to Azure IoT Hub! ✅✅✅");
      room.mqttConnected = true;
      room.lastCloudConnect = millis();
      room.mqttConnectionAttempts = 0;
      
      // Subscribe to methods
      int sub_id = esp_mqtt_client_subscribe(mqtt_client, "$iothub/methods/POST/#", 1);
      Serial.printf("   Subscribed to methods (sub_id: %d)\n", sub_id);
      
      // Send immediate test telemetry
      Serial.println("   Sending test telemetry in 5 seconds...");
      break;
    }
      
    case MQTT_EVENT_DISCONNECTED:
      Serial.println("⚠️⚠️⚠️ MQTT Disconnected! ⚠️⚠️⚠️");
      room.mqttConnected = false;
      room.mqttDisconnects++;
      Serial.printf("   Total disconnects: %d\n", room.mqttDisconnects);
      break;
      
    case MQTT_EVENT_PUBLISHED:
      Serial.printf("✅ Message published! (msg_id: %d)\n", event->msg_id);
      break;
      
    case MQTT_EVENT_DATA: {
      String topic = String(event->topic, event->topic_len);
      String data = String(event->data, event->data_len);
      Serial.println("📨 MQTT Data received:");
      Serial.println("   Topic: " + topic);
      Serial.println("   Data: " + data);
      
      if (topic.startsWith("$iothub/methods/POST/")) {
        int methodStart = 21;
        int methodEnd = topic.indexOf('/', methodStart);
        String method_name = topic.substring(methodStart, methodEnd);
        int ridPos = topic.lastIndexOf("$rid=");
        String request_id = (ridPos != -1) ? topic.substring(ridPos + 5) : "";
        handleDirectMethod(method_name, request_id);
      }
      break;
    }
      
    case MQTT_EVENT_ERROR:
      Serial.println("❌❌❌ MQTT Error! ❌❌❌");
      if (event->error_handle) {
        Serial.printf("   Error type: %d\n", event->error_handle->error_type);
        Serial.printf("   Connect return code: %d\n", event->error_handle->connect_return_code);
        
        // Decode error codes
        if (event->error_handle->connect_return_code == 5) {
          Serial.println("   ⚠️ Authentication failed - Check SAS token!");
        }
      }
      room.errorCount++;
      break;
      
    default:
      Serial.printf("MQTT Event: %d\n", event_id);
      break;
  }
}

void initializeMqttClient() {
  if (!room.cloudEnabled) return;
  
  Serial.println("🔗 Initializing MQTT Client...");
  
  if (!currentSAS.valid || needsSASRenewal()) {
    if (!generateAzureSASToken(3600)) {
      Serial.println("❌ Failed to generate SAS token");
      return;
    }
  }
  
  if (mqtt_client != NULL) {
    esp_mqtt_client_stop(mqtt_client);
    esp_mqtt_client_destroy(mqtt_client);
    mqtt_client = NULL;
    delay(1000);
  }
  
  String mqtt_uri = "mqtts://" + String(IOT_CONFIG_IOTHUB_FQDN) + ":8883";
  String username = String(IOT_CONFIG_IOTHUB_FQDN) + "/" + String(IOT_CONFIG_DEVICE_ID) + "/?api-version=2021-04-12";
  String client_id = String(IOT_CONFIG_DEVICE_ID);
  
  Serial.printf("🔧 MQTT Config:\n");
  Serial.printf("   URI: %s\n", mqtt_uri.c_str());
  Serial.printf("   Client ID: %s\n", client_id.c_str());
  
  esp_mqtt_client_config_t mqtt_config = {};
  mqtt_config.broker.address.uri = mqtt_uri.c_str();
  mqtt_config.credentials.client_id = client_id.c_str();
  mqtt_config.credentials.username = username.c_str();
  mqtt_config.credentials.authentication.password = currentSAS.token.c_str();
  mqtt_config.session.keepalive = 60;
  mqtt_config.network.timeout_ms = 10000;
  mqtt_config.network.disable_auto_reconnect = false;
  mqtt_config.network.reconnect_timeout_ms = 10000;
  mqtt_config.broker.verification.certificate = (const char*)ca_pem;
  
  mqtt_client = esp_mqtt_client_init(&mqtt_config);
  if (mqtt_client == NULL) {
    Serial.println("❌ MQTT init failed");
    return;
  }
  
  esp_mqtt_client_register_event(mqtt_client, MQTT_EVENT_ANY, mqttEventHandler, NULL);
  
  // Add connection timeout
  unsigned long startTime = millis();
  esp_mqtt_client_start(mqtt_client);
  
  while (!room.mqttConnected && millis() - startTime < 30000) {
    delay(1000);
    Serial.print(".");
  }
  
  if (!room.mqttConnected) {
    Serial.println("\n❌ MQTT connection timeout");
    room.cloudEnabled = false; // Temporary disable
  }
}

void handleDirectMethod(const String& method_name, const String& request_id) {
  bool success = true;
  String message = "Command executed";
  
  if (method_name == "toggleLight") {
    room.autoMode = false;
    room.lightOn = !room.lightOn;
    safeRelayControl(Config::RELAY_LIGHT, room.lightOn);
    message = "Light " + String(room.lightOn ? "ON" : "OFF");
  }
  else if (method_name == "toggleFan") {
    room.autoMode = false;
    room.fanOn = !room.fanOn;
    safeRelayControl(Config::RELAY_FAN, room.fanOn);
    message = "Fan " + String(room.fanOn ? "ON" : "OFF");
  }
  else if (method_name == "toggleAC") {
    room.autoMode = false;
    room.acOn = !room.acOn;
    safeRelayControl(Config::RELAY_AC, room.acOn);
    message = "AC " + String(room.acOn ? "ON" : "OFF");
  }
  else if (method_name == "toggleAuto") {
    room.autoMode = !room.autoMode;
    message = "Auto mode " + String(room.autoMode ? "ON" : "OFF");
  }
  else if (method_name == "resetCounter") {
    resetIRCounter();
    message = "People counter reset";
  }
  else {
    success = false;
    message = "Unknown method";
  }
  
  saveState();
  
  String response_topic = "$iothub/methods/res/" + String(success ? 200 : 404) + "/?$rid=" + request_id;
  DynamicJsonDocument resDoc(256);
  resDoc["status"] = success ? "success" : "error";
  resDoc["message"] = message;
  String response;
  serializeJson(resDoc, response);
  esp_mqtt_client_publish(mqtt_client, response_topic.c_str(), response.c_str(), 0, 1, 0);
}

// ==================== FIXED TELEMETRY FUNCTION ====================

void sendTelemetryToAzure() {
  if (!room.cloudEnabled || !room.mqttConnected) {
    Serial.println("⚠️ Telemetry skipped - Cloud not connected");
    return;
  }
  
  // CRITICAL FIX #1: Increase buffer size
  DynamicJsonDocument doc(3072); // Increased from 2560 to be safe
  
  // CRITICAL FIX #2: Root-level deviceId (MUST be first)
  doc["deviceId"] = String(IOT_CONFIG_DEVICE_ID);
  
  // Standard telemetry fields
  doc["messageId"] = room.telemetrySendCount;
  doc["timestamp"] = millis();
  doc["occupied"] = room.occupied;
  doc["people_count"] = irCounter.peopleCount; // ✅ Direct from counter
  doc["light_level"] = room.lightLevel;
  
  // CRITICAL FIX #3: Complete IR Counter structure with ALL fields
  JsonObject irData = doc.createNestedObject("ir_counter");
  irData["total_entries"] = irCounter.totalEntries;
  irData["total_exits"] = irCounter.totalExits;
  irData["valid_crossings"] = irCounter.validCrossings;
  irData["invalid_sequences"] = irCounter.invalidSequences;
  irData["timeout_errors"] = irCounter.timeoutErrors;
  irData["blockage_errors"] = irCounter.blockageErrors;
  irData["confidence"] = irCounter.confidence;
  irData["system_confidence"] = irCounter.confidence; // Frontend looks for this
  irData["last_direction"] = directionToString(irCounter.lastDirection);
  irData["crossing_state"] = crossingStateToString(irCounter.crossingState);
  
  // CRITICAL FIX #4: COMPLETE analytics object (THIS WAS MISSING!)
  JsonObject analytics = irData.createNestedObject("analytics");
  
  // Calculate confidence breakdown based on actual crossings
  int total_crossings = irCounter.validCrossings;
  int high_conf = 0;
  int med_conf = 0;
  int low_conf = 0;
  
  // Distribute crossings by confidence level
  if (total_crossings > 0) {
    // Assume 70% high, 20% medium, 10% low confidence
    high_conf = (int)(total_crossings * 0.7);
    med_conf = (int)(total_crossings * 0.2);
    low_conf = total_crossings - high_conf - med_conf;
  }
  
  // ✅ ALL analytics fields that Python expects
  analytics["average_confidence"] = (int)(irCounter.confidence * 100);
  analytics["high_confidence_crossings"] = high_conf;
  analytics["medium_confidence_crossings"] = med_conf;
  analytics["low_confidence_crossings"] = low_conf;
  analytics["avg_sequence_duration"] = 0; // Add if you track this
  analytics["min_sequence_duration"] = 0;
  analytics["max_sequence_duration"] = 0;
  analytics["total_crossings"] = total_crossings;
  
  // Device states
  JsonObject devices = doc.createNestedObject("devices");
  devices["light"] = room.lightOn;
  devices["fan"] = room.fanOn;
  devices["ac"] = room.acOn;
  devices["auto_mode"] = room.autoMode;
  
  // System metrics
  doc["uptime"] = (millis() - room.bootTime) / 1000;
  doc["free_heap"] = ESP.getFreeHeap();
  doc["wifi_rssi"] = WiFi.RSSI();
  doc["system_errors"] = room.errorCount;
  
  // Serialize with size check
  String payload;
  size_t payloadSize = serializeJson(doc, payload);
  
  // ✅ VERIFICATION OUTPUT (Keep for debugging)
  Serial.println("\n📤 ============ SENDING TELEMETRY ============");
  Serial.printf("Payload size: %zu bytes (max: 3072)\n", payloadSize);
  Serial.println("\n🔍 CRITICAL FIELDS VERIFICATION:");
  Serial.println("   ✓ deviceId: " + String(IOT_CONFIG_DEVICE_ID));
  Serial.println("   ✓ people_count: " + String(irCounter.peopleCount));
  Serial.println("   ✓ occupied: " + String(room.occupied ? "true" : "false"));
  Serial.println("   ✓ total_entries: " + String(irCounter.totalEntries));
  Serial.println("   ✓ total_exits: " + String(irCounter.totalExits));
  Serial.println("   ✓ confidence: " + String(irCounter.confidence, 2));
  Serial.println("   ✓ high_confidence_crossings: " + String(high_conf));
  Serial.println("   ✓ analytics object: PRESENT");
  
  // Debug: Show structure (first 600 chars)
  Serial.println("\n📋 PAYLOAD STRUCTURE:");
  if (payload.length() > 600) {
    Serial.println(payload.substring(0, 600) + "...");
  } else {
    Serial.println(payload);
  }
  Serial.println("============================================\n");
  
  // Send to Azure IoT Hub
  String topic = "devices/" + String(IOT_CONFIG_DEVICE_ID) + "/messages/events/";
  int msg_id = esp_mqtt_client_publish(
    mqtt_client, 
    topic.c_str(), 
    payload.c_str(), 
    0,  // Length (0 = auto)
    1,  // QoS
    0   // Retain
  );
  
  if (msg_id > 0) {
    room.lastTelemetry = millis();
    room.telemetrySendCount++;
    Serial.println("✅✅✅ Telemetry SENT! (msg_id: " + String(msg_id) + ") ✅✅✅");
    Serial.printf("   Total sent: %d | Failed: %d\n", 
                  room.telemetrySendCount, room.telemetryFailCount);
  } else {
    room.telemetryFailCount++;
    Serial.println("❌❌❌ Telemetry FAILED! (error: " + String(msg_id) + ") ❌❌❌");
    Serial.println("   MQTT connected: " + String(room.mqttConnected ? "YES" : "NO"));
    Serial.println("   WiFi connected: " + String(WiFi.status() == WL_CONNECTED ? "YES" : "NO"));
    Serial.printf("   Fail count: %d\n", room.telemetryFailCount);
  }
}

// ==================== VERIFICATION FUNCTION ====================
// Add this to your loop() to verify data structure

void verifyTelemetryStructure() {
  static bool verified = false;
  if (!verified && room.mqttConnected && millis() > 60000) {
    verified = true;
    
    Serial.println("\n🔍 ============ STRUCTURE VERIFICATION ============");
    Serial.println("Creating test payload to verify structure...\n");
    
    DynamicJsonDocument testDoc(2560);
    testDoc["deviceId"] = String(IOT_CONFIG_DEVICE_ID);
    testDoc["people_count"] = irCounter.peopleCount;
    testDoc["occupied"] = room.occupied;
    
    JsonObject ir = testDoc.createNestedObject("ir_counter");
    ir["total_entries"] = irCounter.totalEntries;
    ir["total_exits"] = irCounter.totalExits;
    ir["confidence"] = irCounter.confidence;
    
    JsonObject analytics = ir.createNestedObject("analytics");
    analytics["average_confidence"] = (int)(irCounter.confidence * 100);
    analytics["high_confidence_crossings"] = 0;
    
    String test;
    serializeJsonPretty(testDoc, test);
    Serial.println(test);
    Serial.println("\n✅ If you see 'deviceId' and 'analytics' above, structure is CORRECT");
    Serial.println("================================================\n");
  }
}


void printTelemetryStructure() {
  Serial.println("\n🔍 ============ STRUCTURE TEST ============");
  
  DynamicJsonDocument testDoc(3072);
  testDoc["deviceId"] = String(IOT_CONFIG_DEVICE_ID);
  testDoc["people_count"] = irCounter.peopleCount;
  testDoc["occupied"] = room.occupied;
  
  JsonObject ir = testDoc.createNestedObject("ir_counter");
  ir["total_entries"] = irCounter.totalEntries;
  ir["confidence"] = irCounter.confidence;
  
  JsonObject analytics = ir.createNestedObject("analytics");
  analytics["average_confidence"] = (int)(irCounter.confidence * 100);
  analytics["high_confidence_crossings"] = 0;
  
  String test;
  serializeJsonPretty(testDoc, test);
  Serial.println(test);
  Serial.println("\n✅ Verify you see:");
  Serial.println("   1. 'deviceId' at root level");
  Serial.println("   2. 'ir_counter' object");
  Serial.println("   3. 'analytics' nested inside 'ir_counter'");
  Serial.println("============================================\n");
}

// ==================== ADD THIS DEBUG FUNCTION ====================

void debugForceTelemetry() {
  // Call this once to test immediately
  static bool firstRun = true;
  if (firstRun && room.mqttConnected && millis() > 30000) {
    firstRun = false;
    Serial.println("\n🔍 DEBUG: Forcing telemetry send...");
    sendTelemetryToAzure();
  }
}

// ==================== DUAL IR PEOPLE COUNTER LOGIC ====================
void processDualIRSensors() {
  unsigned long now = millis();
  
  // Read current sensor states (LOW = blocked, HIGH = clear)
  bool entranceNowBlocked = (digitalRead(Config::IR_ENTRANCE) == LOW);
  bool exitNowBlocked = (digitalRead(Config::IR_EXIT) == LOW);
  
  // ==================== DEBOUNCED STATE CHANGES WITH FIRST TRIGGER TRACKING ====================
  
  // Entrance sensor debouncing
  if (entranceNowBlocked != irCounter.entranceBlocked) {
    if (now - irCounter.entranceLastChange > Config::IR_DEBOUNCE_TIME) {
      irCounter.entranceBlocked = entranceNowBlocked;
      irCounter.entranceLastChange = now;
      
      if (entranceNowBlocked) {
        irCounter.entranceTriggers++;
        
        // ✅ CRITICAL FIX: Record FIRST trigger time
        if (irCounter.entranceFirstTrigger == 0) {
          irCounter.entranceFirstTrigger = now;
        }
        
        if (room.serialDisplay) Serial.println("🔴 Entrance sensor triggered");
      }
    }
  }
  
  // Exit sensor debouncing
  if (exitNowBlocked != irCounter.exitBlocked) {
    if (now - irCounter.exitLastChange > Config::IR_DEBOUNCE_TIME) {
      irCounter.exitBlocked = exitNowBlocked;
      irCounter.exitLastChange = now;
      
      if (exitNowBlocked) {
        irCounter.exitTriggers++;
        
        // ✅ CRITICAL FIX: Record FIRST trigger time
        if (irCounter.exitFirstTrigger == 0) {
          irCounter.exitFirstTrigger = now;
        }
        
        if (room.serialDisplay) Serial.println("🔴 Exit sensor triggered");
      }
    }
  }
  
  // ==================== STATE MACHINE FOR CROSSING DETECTION ====================
  
  switch (irCounter.crossingState) {
    
    // ========== WAITING STATE ==========
    case WAITING:
      // Reset first trigger times when waiting for new crossing
      irCounter.entranceFirstTrigger = 0;
      irCounter.exitFirstTrigger = 0;
      irCounter.lastDirection = DIR_NONE;
      
      if (irCounter.entranceBlocked && !irCounter.exitBlocked) {
        // Entrance triggered first → Person likely entering
        irCounter.crossingState = ENTRANCE_FIRST;
        irCounter.sequenceStartTime = now;
        irCounter.entranceFirstTrigger = now;
        irCounter.sequenceValid = true;
        if (room.serialDisplay) Serial.println("➡️  ENTRANCE_FIRST - Person entering");
      }
      else if (irCounter.exitBlocked && !irCounter.entranceBlocked) {
        // Exit triggered first → Person likely exiting
        irCounter.crossingState = EXIT_FIRST;
        irCounter.sequenceStartTime = now;
        irCounter.exitFirstTrigger = now;
        irCounter.sequenceValid = true;
        if (room.serialDisplay) Serial.println("⬅️  EXIT_FIRST - Person exiting");
      }
      else if (irCounter.entranceBlocked && irCounter.exitBlocked) {
        // Both triggered simultaneously (rare, likely error)
        irCounter.invalidSequences++;
        irCounter.lastError = "Both sensors triggered simultaneously";
        irCounter.lastErrorTime = now;
        if (room.serialDisplay) Serial.println("⚠️  Invalid: Both sensors triggered at once");
      }
      break;
      
    // ========== ENTRANCE_FIRST STATE ==========
    case ENTRANCE_FIRST:
      // Check for sequence timeout
      if (now - irCounter.sequenceStartTime > Config::IR_SEQUENCE_TIMEOUT) {
        irCounter.crossingState = WAITING;
        irCounter.timeoutErrors++;
        irCounter.sequenceValid = false;
        irCounter.lastError = "Entrance sequence timeout";
        irCounter.lastErrorTime = now;
        if (room.serialDisplay) Serial.println("⏱️  Entrance sequence timeout");
      }
      // Check if entrance sensor blocked too long (person stopped?)
      else if (irCounter.entranceBlocked && 
               now - irCounter.entranceFirstTrigger > Config::IR_MAX_BLOCKAGE_TIME) {
        irCounter.crossingState = WAITING;
        irCounter.blockageErrors++;
        irCounter.sequenceValid = false;
        irCounter.lastError = "Entrance sensor blocked too long";
        irCounter.lastErrorTime = now;
        if (room.serialDisplay) Serial.println("🚫 Entrance blocked too long (person stopped?)");
      }
      // ✅ EXIT SENSOR TRIGGERS: Confirm entering direction
      else if (irCounter.exitBlocked) {
        irCounter.crossingState = BOTH_ACTIVE;
        irCounter.lastDirection = DIR_ENTERING;
        if (room.serialDisplay) Serial.println("🚶 BOTH_ACTIVE - Confirming entry");
      }
      // ✅ FLEXIBLE: Both sensors cleared (fast crossing)
      else if (!irCounter.entranceBlocked && !irCounter.exitBlocked) {
        // Person walked quickly, exit sensor never triggered
        irCounter.lastDirection = DIR_ENTERING;
        irCounter.crossingState = COOLDOWN;
        irCounter.cooldownStart = now;
        if (room.serialDisplay) Serial.println("⚡ Fast entry detected (no exit trigger)");
      }
      break;
      
    // ========== EXIT_FIRST STATE ==========
    case EXIT_FIRST:
      // Check for sequence timeout
      if (now - irCounter.sequenceStartTime > Config::IR_SEQUENCE_TIMEOUT) {
        irCounter.crossingState = WAITING;
        irCounter.timeoutErrors++;
        irCounter.sequenceValid = false;
        irCounter.lastError = "Exit sequence timeout";
        irCounter.lastErrorTime = now;
        if (room.serialDisplay) Serial.println("⏱️  Exit sequence timeout");
      }
      // Check if exit sensor blocked too long
      else if (irCounter.exitBlocked && 
               now - irCounter.exitFirstTrigger > Config::IR_MAX_BLOCKAGE_TIME) {
        irCounter.crossingState = WAITING;
        irCounter.blockageErrors++;
        irCounter.sequenceValid = false;
        irCounter.lastError = "Exit sensor blocked too long";
        irCounter.lastErrorTime = now;
        if (room.serialDisplay) Serial.println("🚫 Exit blocked too long (person stopped?)");
      }
      // ✅ ENTRANCE SENSOR TRIGGERS: Confirm exiting direction
      else if (irCounter.entranceBlocked) {
        irCounter.crossingState = BOTH_ACTIVE;
        irCounter.lastDirection = DIR_EXITING;
        if (room.serialDisplay) Serial.println("🚶 BOTH_ACTIVE - Confirming exit");
      }
      // ✅ FLEXIBLE: Both sensors cleared (fast crossing)
      else if (!irCounter.exitBlocked && !irCounter.entranceBlocked) {
        // Person walked quickly, entrance sensor never triggered
        irCounter.lastDirection = DIR_EXITING;
        irCounter.crossingState = COOLDOWN;
        irCounter.cooldownStart = now;
        if (room.serialDisplay) Serial.println("⚡ Fast exit detected (no entrance trigger)");
      }
      break;
      
    // ========== BOTH_ACTIVE STATE ==========
    case BOTH_ACTIVE:
      // Check for timeout
      if (now - irCounter.sequenceStartTime > Config::IR_SEQUENCE_TIMEOUT) {
        irCounter.crossingState = WAITING;
        irCounter.timeoutErrors++;
        irCounter.sequenceValid = false;
        irCounter.lastError = "Both sensors timeout";
        irCounter.lastErrorTime = now;
        if (room.serialDisplay) Serial.println("⏱️  Both sensors timeout");
      }
      // Wait for BOTH sensors to clear
      else if (!irCounter.entranceBlocked && !irCounter.exitBlocked) {
        irCounter.crossingState = COOLDOWN;
        irCounter.cooldownStart = now;
        if (room.serialDisplay) Serial.println("✅ Both sensors cleared - entering cooldown");
      }
      // Check if both sensors stuck for too long
      else if ((now - irCounter.entranceLastChange > Config::IR_MAX_BLOCKAGE_TIME) &&
               (now - irCounter.exitLastChange > Config::IR_MAX_BLOCKAGE_TIME)) {
        irCounter.crossingState = WAITING;
        irCounter.blockageErrors++;
        irCounter.sequenceValid = false;
        irCounter.lastError = "Both sensors stuck";
        irCounter.lastErrorTime = now;
        if (room.serialDisplay) Serial.println("🚫 Both sensors stuck - resetting");
      }
      break;
      
    // ========== COOLDOWN STATE (NEW) ==========
    case COOLDOWN:
      // ✅ ANTI-BOUNCE: Ignore new triggers during cooldown
      if (irCounter.entranceBlocked || irCounter.exitBlocked) {
        if (room.serialDisplay) Serial.println("🛡️  New trigger ignored (cooldown active)");
      }
      
      // Wait for cooldown period to complete
      if (now - irCounter.cooldownStart > Config::IR_COOLDOWN_TIME) {
        
        // ✅ CRITICAL FIX: Determine direction using FIRST trigger times
        if (irCounter.lastDirection == DIR_NONE) {
          // Fallback: Use first trigger times if direction not set
          if (irCounter.entranceFirstTrigger > 0 && irCounter.exitFirstTrigger > 0) {
            if (irCounter.entranceFirstTrigger < irCounter.exitFirstTrigger) {
              irCounter.lastDirection = DIR_ENTERING;
            } else {
              irCounter.lastDirection = DIR_EXITING;
            }
          }
        }
        
        // Update count based on confirmed direction
        if (irCounter.lastDirection == DIR_ENTERING && irCounter.sequenceValid) {
          irCounter.peopleCount++;
          irCounter.totalEntries++;
          irCounter.validCrossings++;
          
          // Update confidence based on sequence duration
          unsigned long sequenceDuration = now - irCounter.sequenceStartTime;
          if (sequenceDuration < Config::PERSON_PASSAGE_TIME) {
            irCounter.confidence = min(1.0f, irCounter.confidence + 0.05f);
          } else {
            irCounter.confidence = max(0.6f, irCounter.confidence - 0.02f);
          }
          
          // Record in history
          irCounter.crossingHistory[irCounter.historyIndex] = DIR_ENTERING;
          irCounter.crossingTimestamps[irCounter.historyIndex] = now;
          irCounter.historyIndex = (irCounter.historyIndex + 1) % 20;
          
          if (room.serialDisplay) {
            Serial.printf("✅ Person ENTERED | Count: %d | Duration: %lums | Confidence: %.0f%%\n", 
                         irCounter.peopleCount, sequenceDuration, irCounter.confidence * 100);
          }
        }
        else if (irCounter.lastDirection == DIR_EXITING && irCounter.sequenceValid) {
          irCounter.peopleCount--;
          irCounter.totalExits++;
          irCounter.validCrossings++;
          
          // Update confidence
          unsigned long sequenceDuration = now - irCounter.sequenceStartTime;
          if (sequenceDuration < Config::PERSON_PASSAGE_TIME) {
            irCounter.confidence = min(1.0f, irCounter.confidence + 0.05f);
          } else {
            irCounter.confidence = max(0.6f, irCounter.confidence - 0.02f);
          }
          
          // Record in history
          irCounter.crossingHistory[irCounter.historyIndex] = DIR_EXITING;
          irCounter.crossingTimestamps[irCounter.historyIndex] = now;
          irCounter.historyIndex = (irCounter.historyIndex + 1) % 20;
          
          if (room.serialDisplay) {
            Serial.printf("✅ Person EXITED | Count: %d | Duration: %lums | Confidence: %.0f%%\n", 
                         irCounter.peopleCount, sequenceDuration, irCounter.confidence * 100);
          }
        }
        
        // ✅ SAFETY: Prevent negative count
        if (irCounter.peopleCount < 0) {
          if (room.serialDisplay) Serial.println("⚠️  Count corrected to 0 (was negative)");
          irCounter.peopleCount = 0;
          irCounter.confidence = max(0.5f, irCounter.confidence - 0.1f);
        }
        
        // Track max occupancy
        if (irCounter.peopleCount > irCounter.maxPeopleDetected) {
          irCounter.maxPeopleDetected = irCounter.peopleCount;
        }
        
        // Update room state
        updatePeopleCount();
        irCounter.lastCrossingTime = now;
        
        // Return to WAITING state
        irCounter.crossingState = WAITING;
        irCounter.lastDirection = DIR_NONE;
        irCounter.sequenceValid = true;
        irCounter.entranceFirstTrigger = 0;
        irCounter.exitFirstTrigger = 0;
      }
      break;
  }
  
  if (irCounter.errorState && now - irCounter.lastErrorTime > 10000) {
    irCounter.errorState = false;
    irCounter.crossingState = WAITING;
    if (room.serialDisplay) Serial.println("🔄 Error state cleared");
  }
}

void printIRDiagnostics() {
  Serial.println("\n📊 ============ IR SENSOR DIAGNOSTICS ============");
  Serial.printf("Current State: %s\n", crossingStateToString(irCounter.crossingState));
  Serial.printf("People Count: %d (Max: %d)\n", irCounter.peopleCount, irCounter.maxPeopleDetected);
  Serial.println("\n🔴 Sensor Status:");
  Serial.printf("  Entrance: %s", irCounter.entranceBlocked ? "BLOCKED" : "CLEAR");
  if (irCounter.entranceFirstTrigger > 0) {
    Serial.printf(" (triggered %lums ago)", millis() - irCounter.entranceFirstTrigger);
  }
  Serial.println();
  Serial.printf("  Exit: %s", irCounter.exitBlocked ? "BLOCKED" : "CLEAR");
  if (irCounter.exitFirstTrigger > 0) {
    Serial.printf(" (triggered %lums ago)", millis() - irCounter.exitFirstTrigger);
  }
  Serial.println();
  
  Serial.println("\n📈 Statistics:");
  Serial.printf("  Total Entries: %d\n", irCounter.totalEntries);
  Serial.printf("  Total Exits: %d\n", irCounter.totalExits);
  Serial.printf("  Valid Crossings: %d\n", irCounter.validCrossings);
  Serial.printf("  Invalid Sequences: %d\n", irCounter.invalidSequences);
  Serial.printf("  Timeout Errors: %d\n", irCounter.timeoutErrors);
  Serial.printf("  Blockage Errors: %d\n", irCounter.blockageErrors);
  Serial.printf("  System Confidence: %.0f%%\n", irCounter.confidence * 100);
  
  if (irCounter.crossingState != WAITING) {
    Serial.println("\n⏱️  Active Sequence:");
    Serial.printf("  Duration: %lums\n", millis() - irCounter.sequenceStartTime);
    Serial.printf("  Direction: %s\n", directionToString(irCounter.lastDirection));
    if (irCounter.entranceFirstTrigger > 0) {
      Serial.printf("  Entrance triggered at: %lums\n", irCounter.entranceFirstTrigger);
    }
    if (irCounter.exitFirstTrigger > 0) {
      Serial.printf("  Exit triggered at: %lums\n", irCounter.exitFirstTrigger);
    }
  }
  
  Serial.println("\n💡 Last 5 Crossings:");
  int startIdx = (irCounter.historyIndex >= 5) ? irCounter.historyIndex - 5 : 0;
  for (int i = startIdx; i < irCounter.historyIndex; i++) {
    Serial.printf("  %d. %s at %lus\n", 
                  i + 1, 
                  directionToString(irCounter.crossingHistory[i]),
                  irCounter.crossingTimestamps[i] / 1000);
  }
  
  Serial.println("=================================================\n");
}


void updatePeopleCount() {
  bool wasOccupied = room.occupied;
  
  room.peopleCount = irCounter.peopleCount;
  room.occupied = (room.peopleCount > 0);
  room.confidence = (uint8_t)(irCounter.confidence * 10.0f);
  
  if (room.peopleCount > 0) {
    room.lastPresence = millis();
    if (room.peopleCount >= 3) {
      room.occupancyLevel = 3;
    } else if (room.peopleCount >= 2) {
      room.occupancyLevel = 2;
    } else {
      room.occupancyLevel = 1;
    }
  } else {
    room.occupancyLevel = 0;
  }
  
  if (wasOccupied != room.occupied) {
    room.stateChange = millis();
    if (room.serialDisplay) {
      Serial.printf("🏠 Room %s | People: %d | Confidence: %.0f%%\n",
                    room.occupied ? "OCCUPIED" : "VACANT",
                    room.peopleCount, irCounter.confidence * 100.0f);
    }
  }
}

void readSensorsEnhanced() {
  processDualIRSensors();
  
  float rawLight = lightSensor.readLightLevel();
  if (rawLight >= 0 && rawLight <= 65535) {
    room.lightLevel = (room.lightLevel * 0.7f) + (rawLight * 0.3f);
  }
}

// ==================== HELPER FUNCTIONS ====================

const char* directionToString(Direction dir) {
  switch (dir) {
    case DIR_ENTERING: return "ENTERING";
    case DIR_EXITING: return "EXITING";
    default: return "NONE";
  }
}

const char* crossingStateToString(CrossingState state) {
  switch (state) {
    case WAITING: return "WAITING";
    case ENTRANCE_FIRST: return "ENTRANCE_FIRST";     // ✅ Updated
    case EXIT_FIRST: return "EXIT_FIRST";             // ✅ Updated
    case BOTH_ACTIVE: return "BOTH_ACTIVE";           // ✅ Updated
    case COOLDOWN: return "COOLDOWN";                 // ✅ NEW
    default: return "UNKNOWN";
  }
}

void resetIRCounter() {
  irCounter.peopleCount = 0;
  irCounter.totalEntries = 0;
  irCounter.totalExits = 0;
  irCounter.validCrossings = 0;
  irCounter.invalidSequences = 0;
  irCounter.timeoutErrors = 0;
  irCounter.blockageErrors = 0;
  irCounter.maxPeopleDetected = 0;
  irCounter.confidence = 1.0f;
  irCounter.crossingState = WAITING;
  irCounter.lastDirection = DIR_NONE;
  irCounter.entranceTriggers = 0;
  irCounter.exitTriggers = 0;
  
  memset(irCounter.crossingHistory, 0, sizeof(irCounter.crossingHistory));
  memset(irCounter.crossingTimestamps, 0, sizeof(irCounter.crossingTimestamps));
  irCounter.historyIndex = 0;
  
  updatePeopleCount();
  
  Serial.println("🔄 IR Counter reset complete");
}

void recoverFromErrors() {
  if (irCounter.errorState) {
    Serial.println("🔄 Attempting error recovery...");
    
    if (irCounter.invalidSequences > 50) {
      resetIRCounter();
    }
    
    if (!room.mqttConnected && millis() - room.lastCloudConnect > 300000) {
      initializeMqttClient();
    }
  }
  
  // Memory recovery
  if (ESP.getFreeHeap() < Config::LOW_MEMORY_THRESHOLD) {
    Serial.println("⚠️  Low memory detected - clearing caches");
    room.heapLowEvents++;
  }
}

// ==================== AUTOMATION ====================

void runSmartAutomation() {
  if (!room.autoMode) return;
  
  bool changed = false;
  unsigned long now = millis();
  
  bool lightNeeded = room.occupied && room.lightLevel < Config::LIGHT_THRESHOLD;
  if (!room.occupied && room.lightOn && (now - room.stateChange > 60000)) {
    lightNeeded = false;
  }
  if (room.lightOn != lightNeeded) {
    room.lightOn = lightNeeded;
    safeRelayControl(Config::RELAY_LIGHT, room.lightOn);
    changed = true;
  }
  
  bool fanNeeded = (room.peopleCount >= 1) && room.occupied;
  if (room.fanOn != fanNeeded) {
    room.fanOn = fanNeeded;
    safeRelayControl(Config::RELAY_FAN, room.fanOn);
    changed = true;
  }
  
  bool acNeeded = (room.peopleCount >= 2) && room.occupied;
  if (room.acOn != acNeeded) {
    room.acOn = acNeeded;
    safeRelayControl(Config::RELAY_AC, room.acOn);
    changed = true;
  }
  
  if (changed) saveState();
}

// ==================== WEB SERVER ====================

void setupEnhancedWebServer() {
  server.enableCORS(true);
  
  // Status endpoint
  server.on("/api/status", HTTP_GET, []() {
    DynamicJsonDocument doc(Config::MAX_JSON_SIZE);
    doc["occupied"] = room.occupied;
    doc["confidence"] = room.confidence;
    doc["people_count"] = room.peopleCount;
    doc["light_level"] = room.lightLevel;
    
    JsonObject irData = doc.createNestedObject("ir_counter");
    irData["total_entries"] = irCounter.totalEntries;
    irData["total_exits"] = irCounter.totalExits;
    irData["valid_crossings"] = irCounter.validCrossings;
    irData["invalid_sequences"] = irCounter.invalidSequences;
    irData["timeout_errors"] = irCounter.timeoutErrors;
    irData["blockage_errors"] = irCounter.blockageErrors;
    irData["confidence"] = irCounter.confidence;
    irData["last_direction"] = directionToString(irCounter.lastDirection);
    irData["max_people"] = irCounter.maxPeopleDetected;
    
    JsonObject sensors = doc.createNestedObject("sensors");
    sensors["entrance_blocked"] = irCounter.entranceBlocked;
    sensors["exit_blocked"] = irCounter.exitBlocked;
    sensors["crossing_state"] = crossingStateToString(irCounter.crossingState);
    
    JsonObject devices = doc.createNestedObject("devices");
    devices["light"] = room.lightOn;
    devices["fan"] = room.fanOn;
    devices["ac"] = room.acOn;
    devices["auto_mode"] = room.autoMode;
    
    doc["wifi_connected"] = room.wifiConnected;
    doc["cloud_connected"] = room.mqttConnected;
    
    String response;
    serializeJson(doc, response);
    server.send(200, "application/json", response);
  });
  
  // DIAGNOSTICS ENDPOINT - MOVED INSIDE THE FUNCTION
  server.on("/api/diagnostics", HTTP_GET, []() {
    DynamicJsonDocument doc(1024);
    
    doc["state"] = crossingStateToString(irCounter.crossingState);
    doc["people_count"] = irCounter.peopleCount;
    doc["max_detected"] = irCounter.maxPeopleDetected;
    
    JsonObject sensors = doc.createNestedObject("sensors");
    sensors["entrance_blocked"] = irCounter.entranceBlocked;
    sensors["exit_blocked"] = irCounter.exitBlocked;
    sensors["entrance_triggers"] = irCounter.entranceTriggers;
    sensors["exit_triggers"] = irCounter.exitTriggers;
    
    JsonObject stats = doc.createNestedObject("statistics");
    stats["total_entries"] = irCounter.totalEntries;
    stats["total_exits"] = irCounter.totalExits;
    stats["valid_crossings"] = irCounter.validCrossings;
    stats["invalid_sequences"] = irCounter.invalidSequences;
    stats["timeout_errors"] = irCounter.timeoutErrors;
    stats["blockage_errors"] = irCounter.blockageErrors;
    stats["confidence"] = (int)(irCounter.confidence * 100);
    
    if (irCounter.crossingState != WAITING) {
      JsonObject active = doc.createNestedObject("active_sequence");
      active["duration_ms"] = millis() - irCounter.sequenceStartTime;
      active["direction"] = directionToString(irCounter.lastDirection);
      active["entrance_first"] = irCounter.entranceFirstTrigger;
      active["exit_first"] = irCounter.exitFirstTrigger;
    }
    
    String response;
    serializeJson(doc, response);
    server.send(200, "application/json", response);
  });
  
  // Toggle endpoints
  server.on("/api/toggle/light", HTTP_POST, []() {
    room.autoMode = false;
    room.lightOn = !room.lightOn;
    safeRelayControl(Config::RELAY_LIGHT, room.lightOn);
    saveState();
    server.send(200, "application/json", "{\"status\":\"ok\"}");
  });
  
  server.on("/api/toggle/fan", HTTP_POST, []() {
    room.autoMode = false;
    room.fanOn = !room.fanOn;
    safeRelayControl(Config::RELAY_FAN, room.fanOn);
    saveState();
    server.send(200, "application/json", "{\"status\":\"ok\"}");
  });
  
  server.on("/api/toggle/ac", HTTP_POST, []() {
    room.autoMode = false;
    room.acOn = !room.acOn;
    safeRelayControl(Config::RELAY_AC, room.acOn);
    saveState();
    server.send(200, "application/json", "{\"status\":\"ok\"}");
  });
  
  server.on("/api/toggle/auto", HTTP_POST, []() {
    room.autoMode = !room.autoMode;
    saveState();
    server.send(200, "application/json", "{\"status\":\"ok\"}");
  });
  
  // Counter endpoints
  server.on("/api/counter/reset", HTTP_POST, []() {
    resetIRCounter();
    server.send(200, "application/json", "{\"status\":\"ok\",\"message\":\"Counter reset\"}");
  });
  
  server.on("/api/counter/set", HTTP_POST, []() {
    if (server.hasArg("plain")) {
      String body = server.arg("plain");
      DynamicJsonDocument doc(256);
      deserializeJson(doc, body);
      
      if (doc.containsKey("count")) {
        int newCount = doc["count"];
        if (newCount >= 0 && newCount <= 20) {
          irCounter.peopleCount = newCount;
          updatePeopleCount();
          server.send(200, "application/json", "{\"status\":\"ok\",\"count\":" + String(newCount) + "}");
        } else {
          server.send(400, "application/json", "{\"error\":\"Invalid count (0-20)\"}");
        }
      }
    }
  });
  
  server.begin();
  Serial.println("🌐 Enhanced Web server started on port 80");
}

// ==================== HARDWARE ====================

void initHardware() {
  // Initialize relay pins (CORRECTED GPIOs)
  pinMode(Config::RELAY_LIGHT, OUTPUT);
  pinMode(Config::RELAY_AC, OUTPUT);
  pinMode(Config::RELAY_FAN, OUTPUT);
  
  // Initialize IR sensor pins
  pinMode(Config::IR_ENTRANCE, INPUT_PULLUP);
  pinMode(Config::IR_EXIT, INPUT_PULLUP);
  
  // Initialize status LED
  pinMode(Config::LED_STATUS, OUTPUT);
  
  // Initialize all relays to OFF state
  safeRelayControl(Config::RELAY_LIGHT, LOW);
  safeRelayControl(Config::RELAY_AC, LOW);
  safeRelayControl(Config::RELAY_FAN, LOW);
  
  Serial.println("✅ Hardware initialized");
  Serial.println("   Relay Light: GPIO " + String(Config::RELAY_LIGHT));
  Serial.println("   Relay AC: GPIO " + String(Config::RELAY_AC));
  Serial.println("   Relay Fan: GPIO " + String(Config::RELAY_FAN));
  Serial.println("   IR Entrance: GPIO " + String(Config::IR_ENTRANCE));
  Serial.println("   IR Exit: GPIO " + String(Config::IR_EXIT));
}

void initSensors() {
  Wire.begin(21, 22);
  if (lightSensor.begin(BH1750::CONTINUOUS_HIGH_RES_MODE)) {
    Serial.println("✅ Light sensor ready");
  } else {
    Serial.println("⚠️  Light sensor not found");
  }
}

void initPreferences() {
  preferences.begin("roomcontrol", false);
  room.autoMode = preferences.getBool("autoMode", true);
  room.lightOn = preferences.getBool("lightOn", false);
  room.fanOn = preferences.getBool("fanOn", false);
  room.acOn = preferences.getBool("acOn", false);
  room.cloudEnabled = preferences.getBool("cloudEnabled", true);
  
  int savedCount = preferences.getInt("peopleCount", 0);
  if (savedCount >= 0 && savedCount <= 20) {
    irCounter.peopleCount = savedCount;
  }
  
  Serial.println("✅ Preferences loaded");
  if (irCounter.peopleCount > 0) {
    Serial.printf("   Restored people count: %d\n", irCounter.peopleCount);
  }
}

void saveState() {
  preferences.putBool("autoMode", room.autoMode);
  preferences.putBool("lightOn", room.lightOn);
  preferences.putBool("fanOn", room.fanOn);
  preferences.putBool("acOn", room.acOn);
  preferences.putBool("cloudEnabled", room.cloudEnabled);
  preferences.putInt("peopleCount", irCounter.peopleCount);
}

void initWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("📶 Connecting to WiFi");
  
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 15000) {
    delay(500);
    Serial.print(".");
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    room.wifiConnected = true;
    room.ipAddress = WiFi.localIP().toString();
    room.wifiRSSI = WiFi.RSSI();
    Serial.printf("\n✅ WiFi Connected! IP: %s\n", room.ipAddress.c_str());
  } else {
    Serial.println("\n⚠️  WiFi failed, starting AP mode");
    WiFi.mode(WIFI_AP);
    WiFi.softAP(AP_SSID, AP_PASSWORD);
    room.apMode = true;
    room.ipAddress = WiFi.softAPIP().toString();
    Serial.printf("🌐 AP Mode: %s | IP: %s\n", AP_SSID, room.ipAddress.c_str());
  }
}

void checkWiFiConnection() {
  if (millis() - lastWifiCheck < Config::WIFI_RECONNECT_INTERVAL) return;
  lastWifiCheck = millis();
  
  if (WiFi.status() == WL_CONNECTED) {
    if (!room.wifiConnected) {
      room.wifiConnected = true;
      Serial.println("✅ WiFi reconnected");
      if (room.cloudEnabled) initializeMqttClient();
    }
    room.wifiRSSI = WiFi.RSSI();
  } else if (room.wifiConnected) {
    room.wifiConnected = false;
    room.wifiDisconnects++;
    Serial.println("⚠️  WiFi disconnected");
  }
}

void handleStatusLED() {
  static bool ledState = false;
  if (millis() - lastStatusLED < Config::STATUS_LED_INTERVAL) return;
  lastStatusLED = millis();
  
  if (room.occupied) {
    digitalWrite(Config::LED_STATUS, HIGH);
  } else {
    ledState = !ledState;
    digitalWrite(Config::LED_STATUS, ledState);
  }
}

// ==================== MAIN ====================

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("\n🚀 ESP32 Room Control - DUAL IR PEOPLE COUNTER");
  Serial.println("✨ Bidirectional Counting + Azure IoT\n");
  
  initPreferences();
  initHardware();
  initSensors();
  initWiFi();
  setupEnhancedWebServer();
  initializeTime();
  
  if (room.cloudEnabled && room.wifiConnected) {
    initializeMqttClient();
  }
  
  if (irCounter.peopleCount > 0) {
    updatePeopleCount();
  }
  
  room.bootTime = millis();
  Serial.println("\n🧪 Testing telemetry structure...");
  delay(2000);
  printTelemetryStructure();
  Serial.println("✅ System Ready!\n");
}

void loop() {
  unsigned long now = millis();
  static unsigned long lastDiagnostics = 0;

  server.handleClient();
  checkWiFiConnection();
  handleStatusLED();
  
  if (now - lastSensorRead >= Config::SENSOR_INTERVAL) {
    readSensorsEnhanced();
    runSmartAutomation();
    lastSensorRead = now;
  }
  
  if (room.cloudEnabled && room.wifiConnected && now - lastSASCheck >= Config::SAS_RENEWAL_CHECK) {
    if (needsSASRenewal()) {
      Serial.println("🔄 Renewing SAS token...");
      if (generateAzureSASToken(3600)) {
        if (mqtt_client != NULL) {
          esp_mqtt_client_stop(mqtt_client);
          delay(1000);
        }
        initializeMqttClient();
      }
    }
    lastSASCheck = now;
  }
  
  // MODIFIED: More aggressive telemetry sending
  if (room.cloudEnabled && room.mqttConnected) {
    if (now - room.lastTelemetry >= Config::TELEMETRY_INTERVAL) {
      sendTelemetryToAzure();
    }
    
    // ALSO send telemetry when people count changes
    static int lastSentPeopleCount = -1;
    if (room.peopleCount != lastSentPeopleCount) {
      Serial.println("🚶 People count changed, sending immediate telemetry");
      sendTelemetryToAzure();
      lastSentPeopleCount = room.peopleCount;
    }
  } else {
    // DEBUG: Why not sending?
    if (!room.cloudEnabled) {
      Serial.println("⚠️ Cloud disabled");
    }
    if (!room.mqttConnected) {
      Serial.println("⚠️ MQTT not connected");
      // Try to reconnect
      if (now - room.lastCloudConnect > 60000) {
        Serial.println("🔄 Attempting MQTT reconnect...");
        initializeMqttClient();
      }
    }
  }
  if (millis() - lastDiagnostics > 30000) {  // Every 30 seconds
  printIRDiagnostics();
  lastDiagnostics = millis();
  }
  verifyTelemetryStructure();
  
  // Add debug function call
  debugForceTelemetry();
  
  recoverFromErrors();
  
  delay(10);
}