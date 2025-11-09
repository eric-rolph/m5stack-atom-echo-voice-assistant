/*
 * M5Stack Atom Echo - Voice AI Gateway
 * 
 * This firmware turns the M5Stack Echo into an API gateway for voice AI.
 * Press button to record, sends audio to your server, plays back AI response.
 * 
 * Hardware: M5Stack Atom Echo (ESP32-PICO-D4)
 * Board Setting: M5Stack Atom or M5StickC
 */

#include <HTTPClient.h>
#include <WiFi.h>
#include <driver/i2s.h>
#include <M5Atom.h>
#include <ArduinoJson.h>

// WiFi Configuration - UPDATE THESE!
const char *WIFI_SSID = "Everest";  // Your WiFi name
const char *WIFI_PASSWORD = "hillaryhellscape";  // REPLACE WITH YOUR ACTUAL PASSWORD

// Server Configuration - UPDATE THIS!
const char *SERVER_URL = "http://192.168.1.237:8000/api/voice";  // Your server IP:port

// I2S Audio Configuration
#define CONFIG_I2S_BCK_PIN     19
#define CONFIG_I2S_LRCK_PIN    33
#define CONFIG_I2S_DATA_PIN    22
#define CONFIG_I2S_DATA_IN_PIN 23
#define SPEAKER_I2S_NUMBER     I2S_NUM_0

#define MODE_MIC  0
#define MODE_SPK  1
#define DATA_SIZE 1024
#define MAX_RECORD_TIME_MS 5000  // 5 seconds max recording

// Audio buffer
static uint8_t microphonedata0[1024 * 70];  // ~70KB buffer
size_t byte_read = 0;
uint32_t data_offset = 0;
bool is_recording = false;

// LED Colors
#define LED_IDLE      CRGB(0, 50, 0)     // Green - ready
#define LED_RECORDING CRGB(50, 0, 0)     // Red - recording
#define LED_SENDING   CRGB(50, 50, 0)    // Yellow - sending to server
#define LED_SPEAKING  CRGB(0, 0, 50)     // Blue - playing response
#define LED_ERROR     CRGB(50, 0, 50)    // Purple - error

bool InitI2SSpeakerOrMic(int mode) {
    esp_err_t err = ESP_OK;

    i2s_driver_uninstall(SPEAKER_I2S_NUMBER);
    i2s_config_t i2s_config = {
        .mode        = (i2s_mode_t)(I2S_MODE_MASTER),
        .sample_rate = 16000,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format = I2S_CHANNEL_FMT_ALL_RIGHT,
#if ESP_IDF_VERSION > ESP_IDF_VERSION_VAL(4, 1, 0)
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
#else
        .communication_format = I2S_COMM_FORMAT_I2S,
#endif
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count    = 6,
        .dma_buf_len      = 60,
    };

    if (mode == MODE_MIC) {
        i2s_config.mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX | I2S_MODE_PDM);
    } else {
        i2s_config.mode     = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX);
        i2s_config.use_apll = false;
        i2s_config.tx_desc_auto_clear = true;
    }

    err += i2s_driver_install(SPEAKER_I2S_NUMBER, &i2s_config, 0, NULL);
    i2s_pin_config_t tx_pin_config;

#if (ESP_IDF_VERSION > ESP_IDF_VERSION_VAL(4, 3, 0))
    tx_pin_config.mck_io_num = I2S_PIN_NO_CHANGE;
#endif
    tx_pin_config.bck_io_num   = CONFIG_I2S_BCK_PIN;
    tx_pin_config.ws_io_num    = CONFIG_I2S_LRCK_PIN;
    tx_pin_config.data_out_num = CONFIG_I2S_DATA_PIN;
    tx_pin_config.data_in_num  = CONFIG_I2S_DATA_IN_PIN;

    err += i2s_set_pin(SPEAKER_I2S_NUMBER, &tx_pin_config);
    err += i2s_set_clk(SPEAKER_I2S_NUMBER, 16000, I2S_BITS_PER_SAMPLE_16BIT, I2S_CHANNEL_MONO);

    return (err == ESP_OK);
}

bool sendAudioToServer(uint8_t* audio_data, size_t audio_len, uint8_t** response_audio, size_t* response_len) {
    HTTPClient http;
    
    Serial.println("Connecting to server...");
    http.begin(SERVER_URL);
    http.addHeader("Content-Type", "application/octet-stream");
    http.setTimeout(30000);  // 30 second timeout for AI processing
    
    Serial.printf("Sending %d bytes of audio data...\n", audio_len);
    int httpCode = http.POST(audio_data, audio_len);
    
    if (httpCode == HTTP_CODE_OK) {
        int len = http.getSize();
        if (len > 0) {
            Serial.printf("Received %d bytes of audio response\n", len);
            *response_audio = (uint8_t*)malloc(len);
            if (*response_audio) {
                WiFiClient* stream = http.getStreamPtr();
                size_t received = 0;
                while (received < len && stream->available()) {
                    int chunk = stream->readBytes(*response_audio + received, len - received);
                    if (chunk > 0) {
                        received += chunk;
                    }
                    delay(1);
                }
                *response_len = received;
                http.end();
                return true;
            }
        }
    } else {
        Serial.printf("HTTP POST failed: %d - %s\n", httpCode, http.errorToString(httpCode).c_str());
    }
    
    http.end();
    return false;
}

void playAudio(uint8_t* audio_data, size_t audio_len) {
    if (!audio_data || audio_len == 0) return;
    
    Serial.println("Playing audio response...");
    InitI2SSpeakerOrMic(MODE_SPK);
    M5.dis.drawpix(0, LED_SPEAKING);
    
    size_t bytes_written;
    i2s_write(SPEAKER_I2S_NUMBER, audio_data, audio_len, &bytes_written, portMAX_DELAY);
    
    delay(100);  // Small delay to ensure playback completes
}

void setup() {
    M5.begin(true, false, true);
    M5.dis.clear();
    
    Serial.begin(115200);
    Serial.println("\n\nM5Stack Echo - Voice AI Gateway");
    Serial.println("================================");
    
    // Initialize speaker mode first
    InitI2SSpeakerOrMic(MODE_SPK);
    delay(100);
    
    // Connect to WiFi
    Serial.printf("Connecting to WiFi: %s\n", WIFI_SSID);
    M5.dis.drawpix(0, LED_SENDING);
    
    WiFi.mode(WIFI_STA);
    WiFi.setSleep(false);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    
    int wifi_attempts = 0;
    while (WiFi.status() != WL_CONNECTED && wifi_attempts < 30) {
        delay(500);
        Serial.print(".");
        wifi_attempts++;
    }
    Serial.println();
    
    if (WiFi.status() == WL_CONNECTED) {
        Serial.println("WiFi Connected!");
        Serial.printf("IP Address: %s\n", WiFi.localIP().toString().c_str());
        Serial.printf("Server URL: %s\n", SERVER_URL);
        Serial.println("\nReady! Press button to record voice.");
        M5.dis.drawpix(0, LED_IDLE);
    } else {
        Serial.println("WiFi connection failed!");
        M5.dis.drawpix(0, LED_ERROR);
    }
}

void loop() {
    M5.update();
    
    // Button pressed - start recording
    if (M5.Btn.isPressed() && !is_recording) {
        is_recording = true;
        data_offset = 0;
        
        Serial.println("\n=== Recording Started ===");
        InitI2SSpeakerOrMic(MODE_MIC);
        M5.dis.drawpix(0, LED_RECORDING);
        
        unsigned long start_time = millis();
        
        // Record while button held (up to max time)
        while (M5.Btn.isPressed() && (millis() - start_time) < MAX_RECORD_TIME_MS) {
            i2s_read(SPEAKER_I2S_NUMBER, 
                     (char *)(microphonedata0 + data_offset),
                     DATA_SIZE, 
                     &byte_read, 
                     (100 / portTICK_RATE_MS));
            data_offset += byte_read;
            
            // Check if buffer is full
            if (data_offset >= sizeof(microphonedata0) - DATA_SIZE) {
                Serial.println("Buffer full!");
                break;
            }
            M5.update();
        }
        
        unsigned long record_duration = millis() - start_time;
        Serial.printf("=== Recording Stopped ===\n");
        Serial.printf("Recorded: %d bytes (%.1f seconds)\n", 
                     data_offset, record_duration / 1000.0);
        
        if (data_offset > 0) {
            // Send to server
            M5.dis.drawpix(0, LED_SENDING);
            Serial.println("Sending to AI server...");
            
            uint8_t* response_audio = NULL;
            size_t response_len = 0;
            
            if (sendAudioToServer(microphonedata0, data_offset, &response_audio, &response_len)) {
                Serial.println("AI response received!");
                
                if (response_audio && response_len > 0) {
                    playAudio(response_audio, response_len);
                    free(response_audio);
                }
                
                M5.dis.drawpix(0, LED_IDLE);
                Serial.println("Ready for next recording.\n");
            } else {
                Serial.println("Failed to get AI response");
                M5.dis.drawpix(0, LED_ERROR);
                delay(1000);
                M5.dis.drawpix(0, LED_IDLE);
            }
        }
        
        is_recording = false;
    }
    
    delay(10);
}
