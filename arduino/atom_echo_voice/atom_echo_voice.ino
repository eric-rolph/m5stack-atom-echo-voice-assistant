/*
 * ATOM Echo Voice Assistant with OpenAI Realtime API
 * 
 * Hardware: M5Stack ATOM Echo
 * - ESP32-PICO-D4
 * - SPM1423 PDM Microphone
 * - NS4168 I2S Speaker
 * - SK6812 RGB LED
 * 
 * Features:
 * - PDM microphone input with ESP-IDF I2S driver
 * - I2S speaker output
 * - WebSocket connection to OpenAI Realtime API
 * - Push-to-talk button control
 * - LED status indicators
 */

#include <M5Atom.h>
#include <WiFi.h>
#include <WebSocketsClient.h>
#include <ArduinoJson.h>
#include <driver/i2s.h>
#include "config.h"
#include "base64.h"

// I2S Port Numbers
#define I2S_PORT_MIC I2S_NUM_0
#define I2S_PORT_SPK I2S_NUM_1

// WebSocket client
WebSocketsClient webSocket;

// State management
enum SystemState {
  STATE_INIT,
  STATE_WIFI_CONNECTING,
  STATE_WIFI_CONNECTED,
  STATE_WS_CONNECTING,
  STATE_WS_CONNECTED,
  STATE_READY,
  STATE_RECORDING,
  STATE_SPEAKING,
  STATE_ERROR
};

SystemState currentState = STATE_INIT;
bool buttonPressed = false;
unsigned long lastPingTime = 0;
String sessionId = "";

// Function declarations
void setupWiFi();
void setupI2SMicrophone();
void setupI2SSpeaker();
void setupWebSocket();
void webSocketEvent(WStype_t type, uint8_t * payload, size_t length);
void sendSessionUpdate();
void recordAndSendAudio();
void updateLED();
void handleButton();

void setup() {
  // Initialize M5Atom
  M5.begin(true, false, true);  // Serial, I2C, Display
  Serial.begin(SERIAL_BAUD);
  
  Serial.println("\n\n=== ATOM Echo Voice Assistant ===");
  Serial.println("Build: Arduino/ESP-IDF with PDM support");
  
  // Set initial LED color (blue = initializing)
  M5.dis.drawpix(0, 0x0000FF);
  currentState = STATE_INIT;
  
  // Setup WiFi
  setupWiFi();
  
  // Setup I2S for PDM microphone
  setupI2SMicrophone();
  
  // Setup I2S for speaker
  setupI2SSpeaker();
  
  // Setup WebSocket
  setupWebSocket();
  
  Serial.println("Setup complete - Ready!");
  currentState = STATE_READY;
  M5.dis.drawpix(0, 0x00FF00);  // Green = ready
}

void loop() {
  M5.update();
  webSocket.loop();
  
  // Handle button press
  handleButton();
  
  // Update LED based on state
  updateLED();
  
  // Send WebSocket ping
  if (millis() - lastPingTime > WS_PING_INTERVAL) {
    if (currentState >= STATE_WS_CONNECTED) {
      webSocket.sendPing();
      lastPingTime = millis();
    }
  }
  
  // Small delay to prevent watchdog issues
  delay(10);
}

void setupWiFi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(WIFI_SSID);
  
  currentState = STATE_WIFI_CONNECTING;
  M5.dis.drawpix(0, 0xFFFF00);  // Yellow = connecting
  
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  int retries = 0;
  while (WiFi.status() != WL_CONNECTED && retries < MAX_WIFI_RETRIES) {
    delay(1000);
    Serial.print(".");
    retries++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\nWiFi connected!");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
    currentState = STATE_WIFI_CONNECTED;
  } else {
    Serial.println("\nWiFi connection failed!");
    currentState = STATE_ERROR;
    M5.dis.drawpix(0, 0xFF0000);  // Red = error
    while(1) delay(1000);
  }
}

void setupI2SMicrophone() {
  Serial.println("Setting up PDM microphone...");
  
  // I2S configuration for PDM microphone (SPM1423)
  i2s_config_t i2s_config_mic = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX | I2S_MODE_PDM),  // PDM mode!
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_RIGHT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 8,
    .dma_buf_len = 64,
    .use_apll = false,
    .tx_desc_auto_clear = false,
    .fixed_mclk = 0
  };
  
  // Pin configuration for PDM microphone
  i2s_pin_config_t pin_config_mic = {
    .bck_io_num = I2S_PIN_NO_CHANGE,
    .ws_io_num = PDM_MIC_CLK,
    .data_out_num = I2S_PIN_NO_CHANGE,
    .data_in_num = PDM_MIC_DATA
  };
  
  // Install and set pin configuration
  esp_err_t err = i2s_driver_install(I2S_PORT_MIC, &i2s_config_mic, 0, NULL);
  if (err != ESP_OK) {
    Serial.printf("Failed to install I2S driver for mic: %d\n", err);
    currentState = STATE_ERROR;
    return;
  }
  
  err = i2s_set_pin(I2S_PORT_MIC, &pin_config_mic);
  if (err != ESP_OK) {
    Serial.printf("Failed to set I2S pins for mic: %d\n", err);
    currentState = STATE_ERROR;
    return;
  }
  
  // Set clock for PDM mode
  err = i2s_set_clk(I2S_PORT_MIC, SAMPLE_RATE, I2S_BITS_PER_SAMPLE_16BIT, I2S_CHANNEL_MONO);
  if (err != ESP_OK) {
    Serial.printf("Failed to set I2S clock for mic: %d\n", err);
    currentState = STATE_ERROR;
    return;
  }
  
  Serial.println("PDM microphone configured successfully!");
}

void setupI2SSpeaker() {
  Serial.println("Setting up I2S speaker...");
  
  // I2S configuration for speaker (NS4168)
  i2s_config_t i2s_config_spk = {
    .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
    .sample_rate = SAMPLE_RATE,
    .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
    .channel_format = I2S_CHANNEL_FMT_ONLY_RIGHT,
    .communication_format = I2S_COMM_FORMAT_STAND_I2S,
    .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
    .dma_buf_count = 8,
    .dma_buf_len = 64,
    .use_apll = false,
    .tx_desc_auto_clear = true,
    .fixed_mclk = 0
  };
  
  // Pin configuration for speaker
  i2s_pin_config_t pin_config_spk = {
    .bck_io_num = I2S_SPK_BCK,
    .ws_io_num = I2S_SPK_WS,
    .data_out_num = I2S_SPK_DATA,
    .data_in_num = I2S_PIN_NO_CHANGE
  };
  
  // Install and set pin configuration
  esp_err_t err = i2s_driver_install(I2S_PORT_SPK, &i2s_config_spk, 0, NULL);
  if (err != ESP_OK) {
    Serial.printf("Failed to install I2S driver for speaker: %d\n", err);
    currentState = STATE_ERROR;
    return;
  }
  
  err = i2s_set_pin(I2S_PORT_SPK, &pin_config_spk);
  if (err != ESP_OK) {
    Serial.printf("Failed to set I2S pins for speaker: %d\n", err);
    currentState = STATE_ERROR;
    return;
  }
  
  Serial.println("I2S speaker configured successfully!");
}

void setupWebSocket() {
  Serial.println("Setting up WebSocket connection...");
  
  currentState = STATE_WS_CONNECTING;
  
  // Configure WebSocket
  String wsUrl = String("wss://api.openai.com/v1/realtime?model=") + REALTIME_MODEL;
  
  // Parse URL
  webSocket.beginSSL("api.openai.com", 443, "/v1/realtime?model=" + String(REALTIME_MODEL));
  
  // Set authorization header
  String authHeader = "Authorization: Bearer " + String(OPENAI_API_KEY);
  webSocket.setExtraHeaders(authHeader.c_str());
  
  // Set additional headers
  webSocket.setExtraHeaders("OpenAI-Beta: realtime=v1");
  
  // Set event handler
  webSocket.onEvent(webSocketEvent);
  
  // Configure reconnection
  webSocket.setReconnectInterval(WS_RECONNECT_INTERVAL);
  
  Serial.println("WebSocket configured, connecting...");
}

void webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {
  switch(type) {
    case WStype_DISCONNECTED:
      Serial.println("[WS] Disconnected!");
      currentState = STATE_WIFI_CONNECTED;
      M5.dis.drawpix(0, 0xFFFF00);  // Yellow = reconnecting
      break;
      
    case WStype_CONNECTED:
      Serial.println("[WS] Connected to OpenAI Realtime API!");
      currentState = STATE_WS_CONNECTED;
      M5.dis.drawpix(0, 0x00FFFF);  // Cyan = connected
      
      // Send session configuration
      sendSessionUpdate();
      break;
      
    case WStype_TEXT:
      {
        Serial.printf("[WS] Received: %s\n", payload);
        
        // Parse JSON
        DynamicJsonDocument doc(4096);
        DeserializationError error = deserializeJson(doc, payload, length);
        
        if (error) {
          Serial.printf("[WS] JSON parse error: %s\n", error.c_str());
          return;
        }
        
        const char* eventType = doc["type"];
        
        if (strcmp(eventType, "session.created") == 0) {
          sessionId = doc["session"]["id"].as<String>();
          Serial.printf("[WS] Session created: %s\n", sessionId.c_str());
          currentState = STATE_READY;
          M5.dis.drawpix(0, 0x00FF00);  // Green = ready
        }
        else if (strcmp(eventType, "response.audio.delta") == 0) {
          // Audio response from OpenAI
          const char* audioBase64 = doc["delta"];
          if (audioBase64) {
            Serial.println("[WS] Received audio delta");
            // TODO: Decode Base64 and play through speaker
            currentState = STATE_SPEAKING;
          }
        }
        else if (strcmp(eventType, "error") == 0) {
          const char* errorMsg = doc["error"]["message"];
          Serial.printf("[WS] Error: %s\n", errorMsg);
        }
      }
      break;
      
    case WStype_BIN:
      Serial.printf("[WS] Received binary data: %u bytes\n", length);
      break;
      
    case WStype_PING:
      Serial.println("[WS] Received ping");
      break;
      
    case WStype_PONG:
      Serial.println("[WS] Received pong");
      break;
      
    case WStype_ERROR:
      Serial.println("[WS] Error!");
      break;
  }
}

void sendSessionUpdate() {
  Serial.println("[WS] Sending session configuration...");
  
  DynamicJsonDocument doc(2048);
  doc["type"] = "session.update";
  
  JsonObject session = doc.createNestedObject("session");
  session["modalities"][0] = "text";
  session["modalities"][1] = "audio";
  session["instructions"] = "You are a helpful voice assistant.";
  session["voice"] = "alloy";
  session["input_audio_format"] = "pcm16";
  session["output_audio_format"] = "pcm16";
  session["input_audio_transcription"]["model"] = "whisper-1";
  
  JsonObject turnDetection = session.createNestedObject("turn_detection");
  turnDetection["type"] = "server_vad";
  turnDetection["threshold"] = 0.5;
  turnDetection["prefix_padding_ms"] = 300;
  turnDetection["silence_duration_ms"] = 500;
  
  String output;
  serializeJson(doc, output);
  
  webSocket.sendTXT(output);
  Serial.println("[WS] Session configuration sent");
}

void recordAndSendAudio() {
  Serial.println("[MIC] Recording audio...");
  currentState = STATE_RECORDING;
  M5.dis.drawpix(0, 0xFF00FF);  // Magenta = recording
  
  // Buffer for audio samples
  int16_t audioBuffer[MIC_BUFFER_SIZE];
  size_t bytesRead = 0;
  
  // Read from PDM microphone
  esp_err_t result = i2s_read(I2S_PORT_MIC, audioBuffer, sizeof(audioBuffer), &bytesRead, portMAX_DELAY);
  
  if (result == ESP_OK && bytesRead > 0) {
    size_t samplesRead = bytesRead / sizeof(int16_t);
    Serial.printf("[MIC] Read %d samples\n", samplesRead);
    
    // Check if we got real audio data
    int nonZero = 0;
    for (int i = 0; i < samplesRead; i++) {
      if (audioBuffer[i] != 0) nonZero++;
    }
    Serial.printf("[MIC] Non-zero samples: %d / %d (%.1f%%)\n", nonZero, samplesRead, (nonZero * 100.0) / samplesRead);
    
    // Encode to Base64
    String audioBase64 = base64::encode((uint8_t*)audioBuffer, bytesRead);
    
    // Send to OpenAI
    DynamicJsonDocument doc(bytesRead * 2);  // Base64 is larger than binary
    doc["type"] = "input_audio_buffer.append";
    doc["audio"] = audioBase64;
    
    String output;
    serializeJson(doc, output);
    
    webSocket.sendTXT(output);
    Serial.println("[WS] Audio sent to OpenAI");
  } else {
    Serial.printf("[MIC] Read error: %d, bytes: %d\n", result, bytesRead);
  }
  
  currentState = STATE_READY;
  M5.dis.drawpix(0, 0x00FF00);  // Green = ready
}

void handleButton() {
  if (M5.Btn.wasPressed()) {
    Serial.println("[BTN] Button pressed!");
    
    if (currentState == STATE_READY) {
      recordAndSendAudio();
    }
  }
}

void updateLED() {
  // LED colors are already set in state transitions
  // This function can be used for blinking or animations
}
