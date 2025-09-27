#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <ArduinoJson.h>
#include <Wire.h>
#include <BH1750.h>
#include <Preferences.h>
#include <esp_task_wdt.h>
#include <Update.h>

//wificonfig
const char* WIFI_SSID = "realme 8 5G";
const char* WIFI_PASSWORD = "88888888";
const char* AP_SSID = "ESP32_RoomControl";
const char* AP_PASSWORD = "roomcontrol123";

struct Config {
  static constexpr uint8_t RELAY_LIGHT = 4;
  static constexpr uint8_t RELAY_AC = 34;
  static constexpr uint8_t RELAY_FAN = 35;
  static constexpr uint8_t IR_SENSOR = 18;
  static constexpr int RX_PIN = 16;
  static constexpr int TX_PIN = 17;
  static constexpr uint8_t LED_STATUS = 2;
  // timing
  static constexpr unsigned long SENSOR_INTERVAL = 500;           // More responsive
  static constexpr unsigned long DISPLAY_INTERVAL = 2000;        // Live updates
  static constexpr unsigned long OCCUPANCY_TIMEOUT = 90000;      // 90 seconds
  static constexpr unsigned long IR_DEBOUNCE = 1500;             // Faster response
  static constexpr unsigned long WIFI_RECONNECT_INTERVAL = 30000;
  static constexpr unsigned long STATUS_LED_INTERVAL = 500;      // Faster blink
  // thresholds
  static constexpr uint16_t LIGHT_THRESHOLD = 150;               // More sensitive
  static constexpr uint8_t HIGH_CONFIDENCE_THRESHOLD = 7;
  static constexpr uint8_t LOW_CONFIDENCE_THRESHOLD = 3;
  static constexpr uint16_t RADAR_MIN_DISTANCE = 20;             // Closer detection
  static constexpr uint16_t RADAR_MAX_DISTANCE = 500;
  // System limits
  static constexpr size_t MAX_JSON_SIZE = 1024;
  static constexpr uint8_t MAX_WIFI_RETRIES = 5;
  static constexpr unsigned long WATCHDOG_TIMEOUT = 10000;
};

// tracking stat
struct RoomState {
  // Core occupancy
  bool occupied = false;
  uint8_t confidence = 0;
  uint8_t occupancyLevel = 0;  // 0=vacant, 1=maybe, 2=likely, 3=occupied
  
  // Device states
  bool lightOn = false;
  bool fanOn = false;
  bool acOn = false;
  bool autoMode = true;
  
  // Enhanced sensor data
  float lightLevel = 0;
  uint32_t radarDistance = 0;
  uint16_t irCount = 0;
  uint8_t radarReadings = 0;      // Valid readings counter
  // Smart timing
  unsigned long lastPresence = 0;
  unsigned long lastIR = 0;
  unsigned long lastRadar = 0;
  unsigned long bootTime = 0;
  unsigned long stateChange = 0;  // Last occupancy change
  
  // System health
  uint32_t totalRequests = 0;
  uint32_t errorCount = 0;
  float avgResponseTime = 0;
  // Connection status
  bool wifiConnected = false;
  bool apMode = false;
  String ipAddress = "";
  int wifiRetries = 0;
  // Display control
  bool serialDisplay = true;
  uint8_t displayMode = 1;  // 1=compact, 2=detailed, 3=minimal
};

BH1750 lightSensor;
WebServer server(80);
RoomState room;
Preferences preferences;
unsigned long lastSensorRead = 0;
unsigned long lastWifiCheck = 0;
unsigned long lastStatusLED = 0;
unsigned long lastDisplay = 0;

// DETECTION ALGORITHMS
// Smart confidence calculation with multiple factors
void calculateConfidence() {
  unsigned long now = millis();
  room.confidence = 0;
  // Time-based presence scoring (0-4 points)
  unsigned long timeSincePresence = now - room.lastPresence;
  if (timeSincePresence < 10000) room.confidence += 4;      // 10s = very recent
  else if (timeSincePresence < 30000) room.confidence += 3; // 30s = recent
  else if (timeSincePresence < 60000) room.confidence += 2; // 1m = somewhat recent
  else if (timeSincePresence < 90000) room.confidence += 1; // 90s = old but valid
  // Sensor quality scoring (0-3 points)
  if (room.radarReadings > 0) room.confidence += 2;         // Active radar
  if (room.irCount > 0) room.confidence += 2;               // IR detections
  if (room.lightLevel > 0) room.confidence += 1;            // Light sensor working
  // Multi-sensor correlation bonus (0-3 points)
  if (room.radarReadings > 0 && room.irCount > 0) room.confidence += 2; // Both sensors agree
  if (timeSincePresence < 5000 && room.radarReadings > 2) room.confidence += 1; // High activity
  // Cap at maximum
  room.confidence = min(room.confidence, (uint8_t)10);
  // Update occupancy levels
  if (room.confidence >= 8) room.occupancyLevel = 3;      // Definitely occupied
  else if (room.confidence >= 5) room.occupancyLevel = 2;  // Likely occupied
  else if (room.confidence >= 2) room.occupancyLevel = 1;  // Maybe occupied
  else room.occupancyLevel = 0;                            // Vacant
  // Update main occupied state
  bool wasOccupied = room.occupied;
  room.occupied = room.confidence >= Config::LOW_CONFIDENCE_THRESHOLD;
  if (wasOccupied != room.occupied) {
    room.stateChange = now;
  }
}

// Enhanced sensor reading with better filtering
void readSensorsEnhanced() {
  unsigned long now = millis();
  // Light sensor with smoothing
  float rawLight = lightSensor.readLightLevel();
  if (rawLight >= 0 && rawLight <= 65535) {
    room.lightLevel = (room.lightLevel * 0.8) + (rawLight * 0.2); // Moving average
  }
  // IR sensor with smart debounce
  if (digitalRead(Config::IR_SENSOR) == LOW) {
    if (now - room.lastIR > Config::IR_DEBOUNCE) {
      room.lastIR = now;
      room.lastPresence = now;
      room.irCount++;
      if (room.serialDisplay) {
        Serial.printf("🚶 IR Motion [Count: %d]\n", room.irCount);
      }
    }
  }
  
  // Enhanced radar processing
  String radarBuffer = "";
  while (Serial2.available()) {
    char c = Serial2.read();
    if (c == '\n' || c == '\r') {
      if (radarBuffer.length() > 0) {
        processRadarData(radarBuffer);
        radarBuffer = "";
      }
    } else {
      radarBuffer += c;
    }
  }
}

// Improved radar data processing
void processRadarData(String data) {
  data.trim();
  // Multiple parsing patterns for different radar formats
  int distance = -1;
  // Pattern 1: "123cm" or "123 cm"
  int cmPos = data.indexOf("cm");
  if (cmPos > 0) {
    String distStr = data.substring(0, cmPos);
    distStr.trim();
    distance = distStr.toInt();
  }
  // Pattern 2: "Distance: 123"
  else if (data.startsWith("Distance:")) {
    distance = data.substring(9).toInt();
  }
  // Pattern 3: Pure number
  else if (data.length() > 0 && data.length() < 4) {
    distance = data.toInt();
  }
  
  // Validate and update
  if (distance >= Config::RADAR_MIN_DISTANCE && distance <= Config::RADAR_MAX_DISTANCE) {
    room.radarDistance = distance;
    room.lastRadar = millis();
    room.lastPresence = millis();
    room.radarReadings++;
    if (room.serialDisplay && room.displayMode >= 2) {
      Serial.printf("📡 Radar: %dcm\n", distance);
    }
  }
}

// Smart automation with hysteresis
void runSmartAutomation() {
  if (!room.autoMode) return;
  unsigned long now = millis();
  bool changed = false;
  // Enhanced light control with ambient consideration
  bool lightNeeded = room.occupied && 
                     room.lightLevel < Config::LIGHT_THRESHOLD &&
                     room.confidence >= Config::LOW_CONFIDENCE_THRESHOLD;
  if (room.lightOn != lightNeeded) {
    room.lightOn = lightNeeded;
    digitalWrite(Config::RELAY_LIGHT, room.lightOn);
    if (room.serialDisplay) {
      Serial.printf("💡 Light %s [Lux: %.0f, Conf: %d]\n", 
                    room.lightOn ? "ON" : "OFF", room.lightLevel, room.confidence);
    }
    changed = true;
  }
  
  // Smart fan control based on confidence and activity
  bool fanNeeded = room.occupied && room.confidence >= Config::HIGH_CONFIDENCE_THRESHOLD;
  if (room.fanOn != fanNeeded) {
    room.fanOn = fanNeeded;
    digitalWrite(Config::RELAY_FAN, room.fanOn);
    if (room.serialDisplay) {
      Serial.printf("🌀 Fan %s [Confidence: %d]\n", 
                    room.fanOn ? "ON" : "OFF", room.confidence);
    }
    changed = true;
  }
  
  // AC control with sustained presence requirement
  bool acNeeded = room.occupied && 
                  room.confidence >= 8 && 
                  (now - room.stateChange) > 30000; // 30s sustained presence
  
  if (room.acOn != acNeeded) {
    room.acOn = acNeeded;
    digitalWrite(Config::RELAY_AC, room.acOn);
    if (room.serialDisplay) {
      Serial.printf("❄️  AC %s [Sustained presence: %s]\n", 
                    room.acOn ? "ON" : "OFF", 
                    (now - room.stateChange) > 30000 ? "Yes" : "No");
    }
    changed = true;
  }
  
  if (changed) {
    saveState();
  }
}
// ENHANCED SERIAL INTERFACE
// Live status display with multiple modes
void updateSerialDisplay() {
  if (!room.serialDisplay) return;
  
  unsigned long now = millis();
  if (now - lastDisplay < Config::DISPLAY_INTERVAL) return;
  
  static uint8_t displayCounter = 0;
  
  // Clear previous line and move cursor up
  if (room.displayMode == 3) { // Minimal mode - single line update
    Serial.print("\r");
    for (int i = 0; i < 80; i++) Serial.print(" ");
    Serial.print("\r");
  } else {
    Serial.println(); // New line for other modes
  }
  
  switch (room.displayMode) {
    case 1: // Compact mode
      displayCompactStatus();
      break;
    case 2: // Detailed mode
      displayDetailedStatus();
      break;
    case 3: // Minimal single-line mode
      displayMinimalStatus();
      break;
  }
  
  lastDisplay = now;
  displayCounter++;
}

void displayCompactStatus() {
  char statusIcon = room.occupied ? '*' : 'o';
  char autoIcon = room.autoMode ? 'A' : 'M';
  
  Serial.printf("%c %s [%d/10] | Lux:%.0f Light:%s Fan:%s AC:%s | %c | %lus\n",
                statusIcon,
                getOccupancyText(),
                room.confidence,
                room.lightLevel,
                room.lightOn ? "ON" : "off",
                room.fanOn ? "ON" : "off", 
                room.acOn ? "ON" : "off",
                autoIcon,
                (millis() - room.bootTime) / 1000);
}

void displayDetailedStatus() {
  Serial.println("+-----------------------------------------+");
  Serial.printf("| Status: %-8s  Confidence: %2d/10    |\n", 
                getOccupancyText(), room.confidence);
  Serial.printf("| Light: %4.0f lux    Radar: %3dcm       |\n", 
                room.lightLevel, room.radarDistance);
  Serial.printf("| Devices: L:%s F:%s AC:%s  Mode:%s   |\n",
                room.lightOn ? "ON " : "OFF",
                room.fanOn ? "ON " : "OFF",
                room.acOn ? "ON " : "OFF",
                room.autoMode ? "AUTO" : "MANUAL");
  Serial.printf("| IR Count: %3d   Radar Reads: %3d     |\n",
                room.irCount, room.radarReadings);
  Serial.println("+-----------------------------------------+");
}

void displayMinimalStatus() {
  Serial.printf("Room: %s(%d) | Light:%.0f | Devices: L:%s F:%s AC:%s",
                room.occupied ? "OCCUPIED" : "vacant",
                room.confidence,
                room.lightLevel,
                room.lightOn ? "●" : "○",
                room.fanOn ? "●" : "○",
                room.acOn ? "●" : "○");
}

const char* getOccupancyText() {
  switch (room.occupancyLevel) {
    case 3: return "OCCUPIED";
    case 2: return "LIKELY";
    case 1: return "MAYBE";
    default: return "VACANT";
  }
}

// Enhanced command processing
void handleSerialInputEnhanced() {
  if (!Serial.available()) return;
  
  String command = Serial.readStringUntil('\n');
  command.trim();
  command.toLowerCase();
  
  if (command == "status" || command == "s") {
    printDetailedStatus();
  }
  else if (command == "display" || command == "d") {
    room.serialDisplay = !room.serialDisplay;
    Serial.printf("Serial display: %s\n", room.serialDisplay ? "ON" : "OFF");
  }
  else if (command.startsWith("mode ")) {
    uint8_t mode = command.substring(5).toInt();
    if (mode >= 1 && mode <= 3) {
      room.displayMode = mode;
      Serial.printf("Display mode: %d (%s)\n", mode, 
                    mode == 1 ? "Compact" : mode == 2 ? "Detailed" : "Minimal");
    }
  }
  else if (command == "reset sensors" || command == "rs") {
    resetSensorCounters();
  }
  else if (command == "light" || command == "l") {
    toggleLight();
  }
  else if (command == "fan" || command == "f") {
    toggleFan();
  }
  else if (command == "ac" || command == "a") {
    toggleAC();
  }
  else if (command == "auto") {
    toggleAutoMode();
  }
  else if (command == "help" || command == "h") {
    printEnhancedHelp();
  }
  else if (command == "wifi") {
    printWiFiStatus();
  }
  else if (command == "restart") {
    Serial.println("Restarting ESP32...");
    ESP.restart();
  }
  else {
    Serial.println("Unknown command. Type 'help' for available commands.");
  }
}

void printEnhancedHelp() {
  Serial.println(F("\n╔════════════════════════════════════════╗"));
  Serial.println(F("║         ESP32 Room Control v1.0        ║"));
  Serial.println(F("╠════════════════════════════════════════╣"));
  Serial.println(F("║ CONTROLS:                              ║"));
  Serial.println(F("║  status, s      - Show detailed status ║"));
  Serial.println(F("║  light, l       - Toggle light         ║"));
  Serial.println(F("║  fan, f         - Toggle fan           ║"));
  Serial.println(F("║  ac, a          - Toggle AC            ║"));
  Serial.println(F("║  auto           - Toggle auto mode     ║"));
  Serial.println(F("║                                        ║"));
  Serial.println(F("║ DISPLAY:                               ║"));
  Serial.println(F("║  display, d     - Toggle live display  ║"));
  Serial.println(F("║  mode 1         - Compact display      ║"));
  Serial.println(F("║  mode 2         - Detailed display     ║"));
  Serial.println(F("║  mode 3         - Minimal display      ║"));
  Serial.println(F("║                                        ║"));
  Serial.println(F("║ SYSTEM:                                ║"));
  Serial.println(F("║  reset sensors  - Reset sensor counts  ║"));
  Serial.println(F("║  wifi           - Show WiFi status     ║"));
  Serial.println(F("║  restart        - Restart ESP32       ║"));
  Serial.println(F("╚════════════════════════════════════════╝\n"));
}

void printDetailedStatus() {
  Serial.println(F("\n╔══════════════════════════════════════════════╗"));
  Serial.println(F("║              DETAILED STATUS                 ║"));
  Serial.println(F("╠══════════════════════════════════════════════╣"));
  Serial.printf("║ Room Status: %-10s Confidence: %2d/10   ║\n", 
                getOccupancyText(), room.confidence);
  Serial.printf("║ Occupancy Level: %d/3  Last Change: %4lus  ║\n",
                room.occupancyLevel, (millis() - room.stateChange) / 1000);
  Serial.println(F("╠══════════════════════════════════════════════╣"));
  Serial.printf("║ Light Level: %6.1f lux  Threshold: %3d     ║\n", 
                room.lightLevel, Config::LIGHT_THRESHOLD);
  Serial.printf("║ Radar Distance: %3d cm   IR Count: %3d      ║\n", 
                room.radarDistance, room.irCount);
  Serial.printf("║ Radar Readings: %3d       Valid Data: %s   ║\n",
                room.radarReadings, room.radarReadings > 0 ? "Yes" : "No");
  Serial.println(F("╠══════════════════════════════════════════════╣"));
  Serial.printf("║ Light: %-3s  Fan: %-3s  AC: %-3s  Auto: %-6s ║\n",
                room.lightOn ? "ON" : "OFF", room.fanOn ? "ON" : "OFF", 
                room.acOn ? "ON" : "OFF", room.autoMode ? "ACTIVE" : "MANUAL");
  Serial.println(F("╠══════════════════════════════════════════════╣"));
  Serial.printf("║ Uptime: %6lu min    Free RAM: %5d KB    ║\n", 
                (millis() - room.bootTime) / 60000, ESP.getFreeHeap() / 1024);
  Serial.printf("║ WiFi: %-11s  IP: %-15s ║\n",
                room.wifiConnected ? "Connected" : "Disconnected", 
                room.ipAddress.c_str());
  Serial.println(F("╚══════════════════════════════════════════════╝\n"));
}

void resetSensorCounters() {
  room.irCount = 0;
  room.radarReadings = 0;
  room.confidence = 0;
  room.lastPresence = 0;
  room.lastIR = 0;
  room.lastRadar = 0;
  Serial.println(F("🔄 Sensor counters reset"));
}

// OPTIMIZED SYSTEM FUNCTIONS
void initPreferences() {
  preferences.begin("roomcontrol", false);
  room.autoMode = preferences.getBool("autoMode", true);
  room.lightOn = preferences.getBool("lightOn", false);
  room.fanOn = preferences.getBool("fanOn", false);
  room.acOn = preferences.getBool("acOn", false);
  room.displayMode = preferences.getUChar("displayMode", 2);
  Serial.println(F("✓ Preferences loaded"));
}

void saveState() {
  preferences.putBool("autoMode", room.autoMode);
  preferences.putBool("lightOn", room.lightOn);
  preferences.putBool("fanOn", room.fanOn);
  preferences.putBool("acOn", room.acOn);
  preferences.putUChar("displayMode", room.displayMode);
}

void updateSystemHealth() {
  static unsigned long lastHeapCheck = 0;
  unsigned long now = millis();
  
  if (now - lastHeapCheck > 15000) { // Every 15 seconds
    uint32_t freeHeap = ESP.getFreeHeap();
    if (freeHeap < 8192) { // Less than 8KB free
      Serial.printf("⚠️  Low memory: %d bytes\n", freeHeap);
      delay(50); // Brief pause for cleanup
    }
    lastHeapCheck = now;
  }
  
  // Decay sensor readings over time
  if (now - room.lastRadar > 10000) { // 10s without radar
    room.radarReadings = max(0, (int)room.radarReadings - 1);
  }
  
  // Reset IR count periodically to prevent overflow
  if (room.irCount > 100) {
    room.irCount = room.irCount / 2; // Halve instead of reset
  }
}

void handleStatusLED() {
  static bool ledState = false;
  unsigned long now = millis();
  
  if (now - lastStatusLED >= Config::STATUS_LED_INTERVAL) {
    if (room.wifiConnected) {
      // Brightness indicates confidence level
      if (room.occupied) {
        digitalWrite(Config::LED_STATUS, HIGH);
      } else {
        // Dim flash for vacant
        ledState = !ledState;
        digitalWrite(Config::LED_STATUS, ledState && (room.confidence > 0));
      }
    } else {
      // Fast blink when disconnected
      ledState = !ledState;
      digitalWrite(Config::LED_STATUS, ledState);
    }
    lastStatusLED = now;
  }
}

// Hardware initialization
void initHardware() {
  pinMode(Config::RELAY_LIGHT, OUTPUT);
  pinMode(Config::RELAY_AC, OUTPUT);
  pinMode(Config::RELAY_FAN, OUTPUT);
  pinMode(Config::IR_SENSOR, INPUT_PULLUP);
  pinMode(Config::LED_STATUS, OUTPUT);
  
  digitalWrite(Config::RELAY_LIGHT, room.lightOn);
  digitalWrite(Config::RELAY_AC, room.acOn);
  digitalWrite(Config::RELAY_FAN, room.fanOn);
  
  Serial.println(F("✓ Hardware initialized"));
}

void initSensors() {
  Wire.begin(21, 22);
  Wire.setClock(100000);
  
  if (lightSensor.begin(BH1750::CONTINUOUS_HIGH_RES_MODE)) {
    Serial.println(F("✓ Light sensor ready"));
  } else {
    Serial.println(F("⚠️  Light sensor not found"));
    room.errorCount++;
  }
  
  Serial2.begin(115200, SERIAL_8N1, Config::RX_PIN, Config::TX_PIN);
  Serial2.setTimeout(50);
  delay(300);
  Serial.println(F("✓ Radar sensor initialized"));
}

void initWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.persistent(true);
  
  room.wifiRetries = 0;
  connectWiFi();
  room.bootTime = millis();
}

void connectWiFi() {
  if (room.wifiRetries >= Config::MAX_WIFI_RETRIES) {
    startAPMode();
    return;
  }
  
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print(F("Connecting to WiFi"));
  
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 15000) {
    delay(500);
    Serial.print(".");
    esp_task_wdt_reset();
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    room.wifiConnected = true;
    room.ipAddress = WiFi.localIP().toString();
    room.wifiRetries = 0;
    Serial.printf("\n✓ WiFi Connected! IP: %s\n", room.ipAddress.c_str());
  } else {
    room.wifiRetries++;
    Serial.printf("\n⚠️  WiFi failed (attempt %d/%d)\n", 
                  room.wifiRetries, Config::MAX_WIFI_RETRIES);
    if (room.wifiRetries >= Config::MAX_WIFI_RETRIES) {
      startAPMode();
    }
  }
}

void startAPMode() {
  WiFi.mode(WIFI_AP_STA);
  WiFi.softAP(AP_SSID, AP_PASSWORD);
  room.apMode = true;
  room.ipAddress = WiFi.softAPIP().toString();
  Serial.printf("✓ AP Mode started: %s | IP: %s\n", AP_SSID, room.ipAddress.c_str());
}

void checkWiFiConnection() {
  unsigned long now = millis();
  
  if (now - lastWifiCheck >= Config::WIFI_RECONNECT_INTERVAL) {
    if (!room.wifiConnected && WiFi.status() != WL_CONNECTED && !room.apMode) {
      connectWiFi();
    } else if (WiFi.status() == WL_CONNECTED && !room.wifiConnected) {
      room.wifiConnected = true;
      room.ipAddress = WiFi.localIP().toString();
      Serial.printf("✓ WiFi reconnected: %s\n", room.ipAddress.c_str());
    } else if (WiFi.status() != WL_CONNECTED && room.wifiConnected) {
      room.wifiConnected = false;
      Serial.println(F("⚠️  WiFi disconnected"));
    }
    lastWifiCheck = now;
  }
}

void sendCORSHeaders() {
  server.sendHeader(F("Access-Control-Allow-Origin"), "*");
  server.sendHeader(F("Access-Control-Allow-Methods"), "GET, POST, OPTIONS");
  server.sendHeader(F("Access-Control-Allow-Headers"), "Content-Type");
  server.sendHeader(F("Cache-Control"), "no-cache, no-store, must-revalidate");
}

void handleOptions() {
  sendCORSHeaders();
  server.send(200, F("text/plain"), "");
}

void handleNotFound() {
  room.errorCount++;
  sendCORSHeaders();
  
  DynamicJsonDocument doc(256);
  doc["error"] = "Not found";
  doc["available_endpoints"] = JsonArray();
  doc["available_endpoints"].add("/api/status");
  doc["available_endpoints"].add("/api/toggle/light");
  doc["available_endpoints"].add("/api/toggle/fan");
  doc["available_endpoints"].add("/api/toggle/ac");
  doc["available_endpoints"].add("/api/toggle/auto");
  
  String response;
  serializeJson(doc, response);
  server.send(404, F("application/json"), response);
}

// Device control functions
void toggleLight() {
  room.lightOn = !room.lightOn;
  digitalWrite(Config::RELAY_LIGHT, room.lightOn);
  room.autoMode = false;
  saveState();
  Serial.printf("💡 Light: %s (Manual Mode)\n", room.lightOn ? "ON" : "OFF");
}

void toggleFan() {
  room.fanOn = !room.fanOn;
  digitalWrite(Config::RELAY_FAN, room.fanOn);
  room.autoMode = false;
  saveState();
  Serial.printf("🌀 Fan: %s (Manual Mode)\n", room.fanOn ? "ON" : "OFF");
}

void toggleAC() {
  room.acOn = !room.acOn;
  digitalWrite(Config::RELAY_AC, room.acOn);
  room.autoMode = false;
  saveState();
  Serial.printf("❄️  AC: %s (Manual Mode)\n", room.acOn ? "ON" : "OFF");
}

void toggleAutoMode() {
  room.autoMode = !room.autoMode;
  saveState();
  Serial.printf("🤖 Mode: %s\n", room.autoMode ? "AUTO" : "MANUAL");
}

void printWiFiStatus() {
  Serial.printf("📶 WiFi: %s", room.wifiConnected ? "Connected" : "Disconnected");
  if (room.wifiConnected) {
    Serial.printf(" | IP: %s | RSSI: %d dBm", 
                  room.ipAddress.c_str(), WiFi.RSSI());
  }
  if (room.apMode) {
    Serial.printf(" | AP Mode: %s", WiFi.softAPIP().toString().c_str());
  }
  Serial.println();
}

void setupWebServer() {
  // Add this before your endpoints:
  server.enableCORS(true);
  server.enableCrossOrigin(true);
  // Add a root endpoint for testing
  server.on("/", HTTP_GET, []() {
    sendCORSHeaders();
    server.send(200, "text/plain", "ESP32 Room Control API v3.1 - Server is running");
  });
  // Add API test endpoint
  server.on("/api/test", HTTP_GET, []() {
    sendCORSHeaders();
    DynamicJsonDocument doc(200);
    doc["message"] = "API is working";
    doc["timestamp"] = millis();
    doc["version"] = "3.1";
    String response;
    serializeJson(doc, response);
    server.send(200, "application/json", response);
  });
  server.on("/api/status", HTTP_OPTIONS, handleOptions);
  server.on("/api/toggle/light", HTTP_OPTIONS, handleOptions);
  server.on("/api/toggle/fan", HTTP_OPTIONS, handleOptions);
  server.on("/api/toggle/ac", HTTP_OPTIONS, handleOptions);
  server.on("/api/toggle/auto", HTTP_OPTIONS, handleOptions);
  server.on("/api/status", HTTP_GET, []() {
    unsigned long startTime = millis();
    room.totalRequests++;
    DynamicJsonDocument doc(Config::MAX_JSON_SIZE);
    doc["occupied"] = room.occupied;
    doc["confidence"] = room.confidence;
    doc["occupancy_level"] = room.occupancyLevel;
    doc["ir_count"] = room.irCount;
    doc["light_level"] = round(room.lightLevel * 10) / 10.0;
    doc["radar_distance"] = room.radarDistance;
    doc["radar_readings"] = room.radarReadings;
    JsonObject devices = doc.createNestedObject("devices");
    devices["light"] = room.lightOn;
    devices["fan"] = room.fanOn;
    devices["ac"] = room.acOn;
    devices["auto_mode"] = room.autoMode;
    doc["uptime"] = (millis() - room.bootTime) / 1000;
    doc["free_heap"] = ESP.getFreeHeap();
    doc["ip"] = room.ipAddress;
    doc["wifi_connected"] = room.wifiConnected;
    doc["ap_mode"] = room.apMode;
    JsonObject health = doc.createNestedObject("health");
    health["total_requests"] = room.totalRequests;
    health["error_count"] = room.errorCount;
    health["avg_response_ms"] = round(room.avgResponseTime * 10) / 10.0;
    health["wifi_rssi"] = room.wifiConnected ? WiFi.RSSI() : 0;
    String response;
    serializeJson(doc, response);
    sendCORSHeaders();
    server.send(200, F("application/json"), response);
    // Update response time
    unsigned long responseTime = millis() - startTime;
    room.avgResponseTime = (room.avgResponseTime + responseTime) / 2.0;
  });
  server.on("/api/toggle/light", HTTP_POST, []() {
    toggleLight();
    sendCORSHeaders();
    server.send(200, F("application/json"), 
                String("{\"status\":\"ok\",\"device\":\"light\",\"state\":") + 
                (room.lightOn ? "true" : "false") + "}");
  });
  server.on("/api/toggle/fan", HTTP_POST, []() {
    toggleFan();
    sendCORSHeaders();
    server.send(200, F("application/json"), 
                String("{\"status\":\"ok\",\"device\":\"fan\",\"state\":") + 
                (room.fanOn ? "true" : "false") + "}");
  });
  server.on("/api/toggle/ac", HTTP_POST, []() {
    toggleAC();
    sendCORSHeaders();
    server.send(200, F("application/json"), 
                String("{\"status\":\"ok\",\"device\":\"ac\",\"state\":") + 
                (room.acOn ? "true" : "false") + "}");
  });
  server.on("/api/toggle/auto", HTTP_POST, []() {
    toggleAutoMode();
    sendCORSHeaders();
    server.send(200, F("application/json"), 
                String("{\"status\":\"ok\",\"mode\":\"") + 
                (room.autoMode ? "auto" : "manual") + "\"}");
  });
  server.onNotFound(handleNotFound);
  server.begin();
  Serial.printf("🌐 Web server started on port 80 | IP: %s\n", room.ipAddress.c_str());
}

// MAIN 
void setup() {
  Serial.begin(115200);
  delay(1000);
  
  // Initialize watchdog timer
  esp_task_wdt_config_t config = {
    .timeout_ms = Config::WATCHDOG_TIMEOUT,
    .idle_core_mask = (1 << portNUM_PROCESSORS) - 1,
    .trigger_panic = true
  };
  esp_task_wdt_init(&config);
  esp_task_wdt_add(NULL);
  
  Serial.println(F("\n🚀 ESP32 Room Control v1.0 - Enhanced"));
  Serial.println(F("📊 Smart occupancy detection with multi-sensor fusion"));
  Serial.println(F("💡 Advanced automation with confidence-based control"));
  Serial.println(F("Type 'help' for enhanced commands\n"));
  
  initPreferences();
  initHardware();
  initSensors();
  initWiFi();
  setupWebServer();

  Serial.printf("📡 Network Information:\n");
  Serial.printf("   WiFi SSID: %s\n", WiFi.SSID().c_str());
  Serial.printf("   IP Address: %s\n", WiFi.localIP().toString().c_str());
  Serial.printf("   AP IP: %s\n", WiFi.softAPIP().toString().c_str());
  Serial.printf("   Use this IP in Streamlit: %s\n", room.ipAddress.c_str());
  Serial.printf("✅ Ready! | Light threshold: %d lux | Free RAM: %d KB\n", 
                Config::LIGHT_THRESHOLD, ESP.getFreeHeap() / 1024);
  printEnhancedHelp();
}

void loop() {
  unsigned long now = millis();
  // Reset watchdog
  esp_task_wdt_reset();
  // Handle serial commands
  handleSerialInputEnhanced();
  // Handle web server requests
  server.handleClient();
  // Check WiFi connection
  checkWiFiConnection();
  // Update status LED
  handleStatusLED();
  // Read sensors and update automation
  if (now - lastSensorRead >= Config::SENSOR_INTERVAL) {
    readSensorsEnhanced();
    calculateConfidence();
    runSmartAutomation();
    updateSystemHealth();
    lastSensorRead = now;
  }
  updateSerialDisplay();
  // Small delay for stability
  delay(10);
}