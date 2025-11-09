/**
 * ATOM Echo Voice Assistant - ESP-IDF Implementation
 * 
 * Hardware: M5Stack ATOM Echo
 * - ESP32-PICO-D4
 * - SPM1423 PDM Microphone (GPIO 23 DATA, GPIO 33 CLK)
 * - NS4168 I2S Speaker (GPIO 22 DATA, GPIO 19 BCK, GPIO 33 WS)
 * - SK6812 RGB LED (GPIO 27)
 * - Button (GPIO 39)
 */

#include <stdio.h>
#include <string.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "esp_system.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "driver/gpio.h"
#include "driver/i2s_std.h"
#include "driver/i2s_pdm.h"
#include "driver/rmt_tx.h"
#include "esp_http_client.h"
#include "esp_crt_bundle.h"
#include "cJSON.h"
#include "led_strip_encoder.h"
#include "../credentials.h"

static const char *TAG = "ATOM_ECHO";

// Hardware pins
#define BUTTON_PIN      39
#define LED_PIN         27
#define PDM_MIC_CLK     33
#define PDM_MIC_DATA    23
#define I2S_SPK_BCK     19
#define I2S_SPK_WS      33
#define I2S_SPK_DATA    22

// Audio configuration
#define SAMPLE_RATE     24000
#define MIC_BUFFER_SIZE 1024
#define SPK_BUFFER_SIZE 2048

// Voice assistant configuration
#define MAX_RECORDING_DURATION_MS 5000   // 5 seconds max recording (120KB at 24kHz)
#define AUDIO_CHUNK_SIZE 1024            // Samples per chunk for streaming
#define HTTP_RESPONSE_BUFFER_SIZE 16384  // 16KB buffer for API responses

// Recording state
static bool is_recording = false;
static int16_t *recording_buffer = NULL;
static size_t recording_buffer_size = 0;
static size_t recording_position = 0;

// HTTP response buffer
static char *http_response_buffer = NULL;
static size_t http_response_len = 0;

// WiFi credentials (from credentials.h)
#ifndef WIFI_SSID
#error "Please create credentials.h from credentials.h.example"
#endif

// I2S handles
static i2s_chan_handle_t mic_chan = NULL;
static i2s_chan_handle_t spk_chan = NULL;

// WiFi event group
static EventGroupHandle_t wifi_event_group;
#define WIFI_CONNECTED_BIT BIT0
#define WIFI_FAIL_BIT      BIT1

// LED control
static rmt_channel_handle_t led_chan = NULL;
static rmt_encoder_handle_t led_encoder = NULL;

// LED colors (GRB format for SK6812)
typedef struct {
    uint8_t g;
    uint8_t r;
    uint8_t b;
} led_color_t;

static const led_color_t LED_OFF     = {0x00, 0x00, 0x00};
static const led_color_t LED_BLUE    = {0x00, 0x00, 0x20};
static const led_color_t LED_YELLOW  = {0x20, 0x20, 0x00};
static const led_color_t LED_GREEN   = {0x20, 0x00, 0x00};
static const led_color_t LED_CYAN    = {0x20, 0x00, 0x20};
static const led_color_t LED_MAGENTA = {0x00, 0x20, 0x20};
static const led_color_t LED_RED     = {0x00, 0x20, 0x00};

/**
 * Initialize SK6812 RGB LED using RMT peripheral
 */
static esp_err_t init_led(void)
{
    ESP_LOGI(TAG, "Initializing SK6812 LED on GPIO %d", LED_PIN);
    
    // RMT TX channel configuration
    rmt_tx_channel_config_t tx_chan_config = {
        .clk_src = RMT_CLK_SRC_DEFAULT,
        .gpio_num = LED_PIN,
        .mem_block_symbols = 64,
        .resolution_hz = 10000000, // 10MHz resolution, 1 tick = 0.1us
        .trans_queue_depth = 4,
    };
    ESP_ERROR_CHECK(rmt_new_tx_channel(&tx_chan_config, &led_chan));
    
    // LED strip encoder configuration
    led_strip_encoder_config_t encoder_config = {
        .resolution = 10000000, // 10MHz
    };
    ESP_ERROR_CHECK(rmt_new_led_strip_encoder(&encoder_config, &led_encoder));
    
    ESP_ERROR_CHECK(rmt_enable(led_chan));
    
    return ESP_OK;
}

/**
 * Set LED color
 */
static void set_led(led_color_t color)
{
    if (!led_chan || !led_encoder) {
        return;  // LED not initialized yet
    }
    
    rmt_transmit_config_t tx_config = {
        .loop_count = 0,
    };
    
    uint8_t led_data[3] = {color.g, color.r, color.b};
    esp_err_t ret = rmt_transmit(led_chan, led_encoder, led_data, sizeof(led_data), &tx_config);
    if (ret == ESP_OK) {
        // Wait for transmission to complete
        rmt_tx_wait_all_done(led_chan, 100);
    }
}

/**
 * WiFi event handler
 */
static void wifi_event_handler(void* arg, esp_event_base_t event_base,
                                int32_t event_id, void* event_data)
{
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        ESP_LOGI(TAG, "WiFi disconnected, retrying...");
        set_led(LED_YELLOW);
        esp_wifi_connect();
        xEventGroupClearBits(wifi_event_group, WIFI_CONNECTED_BIT);
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t* event = (ip_event_got_ip_t*) event_data;
        ESP_LOGI(TAG, "WiFi connected! IP: " IPSTR, IP2STR(&event->ip_info.ip));
        xEventGroupSetBits(wifi_event_group, WIFI_CONNECTED_BIT);
    }
}

/**
 * Initialize WiFi
 */
static void init_wifi(void)
{
    wifi_event_group = xEventGroupCreate();
    
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();
    
    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));
    
    esp_event_handler_instance_t instance_any_id;
    esp_event_handler_instance_t instance_got_ip;
    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT,
                                                        ESP_EVENT_ANY_ID,
                                                        &wifi_event_handler,
                                                        NULL,
                                                        &instance_any_id));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(IP_EVENT,
                                                        IP_EVENT_STA_GOT_IP,
                                                        &wifi_event_handler,
                                                        NULL,
                                                        &instance_got_ip));
    
    wifi_config_t wifi_config = {
        .sta = {
            .ssid = WIFI_SSID,
            .password = WIFI_PASSWORD,
            .threshold.authmode = WIFI_AUTH_WPA2_PSK,
        },
    };
    
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
    ESP_ERROR_CHECK(esp_wifi_start());
    
    ESP_LOGI(TAG, "WiFi init complete, connecting to %s", WIFI_SSID);
    set_led(LED_YELLOW);
}

/**
 * HTTP event handler for API responses
 */
static esp_err_t http_event_handler(esp_http_client_event_t *evt)
{
    switch (evt->event_id) {
        case HTTP_EVENT_ON_DATA:
            if (http_response_buffer && http_response_len + evt->data_len < HTTP_RESPONSE_BUFFER_SIZE) {
                memcpy(http_response_buffer + http_response_len, evt->data, evt->data_len);
                http_response_len += evt->data_len;
                http_response_buffer[http_response_len] = '\0';
            }
            break;
        default:
            break;
    }
    return ESP_OK;
}

/**
 * Get AI response from OpenAI Chat Completions API
 */
static char* get_ai_response(const char *transcription)
{
    ESP_LOGI(TAG, "Getting AI response for: %s", transcription);
    
    // Allocate response buffer
    http_response_buffer = malloc(HTTP_RESPONSE_BUFFER_SIZE);
    if (!http_response_buffer) {
        ESP_LOGE(TAG, "Failed to allocate response buffer");
        return NULL;
    }
    http_response_len = 0;
    
    // Prepare authorization header
    char auth_header[256];
    snprintf(auth_header, sizeof(auth_header), "Bearer %s", OPENAI_API_KEY);
    
    // Build request body
    cJSON *root = cJSON_CreateObject();
    cJSON_AddStringToObject(root, "model", "gpt-4o-mini");
    
    cJSON *messages = cJSON_CreateArray();
    cJSON *system_msg = cJSON_CreateObject();
    cJSON_AddStringToObject(system_msg, "role", "system");
    cJSON_AddStringToObject(system_msg, "content", 
        "You are a helpful voice assistant. Keep responses concise and conversational.");
    cJSON_AddItemToArray(messages, system_msg);
    
    cJSON *user_msg = cJSON_CreateObject();
    cJSON_AddStringToObject(user_msg, "role", "user");
    cJSON_AddStringToObject(user_msg, "content", transcription);
    cJSON_AddItemToArray(messages, user_msg);
    
    cJSON_AddItemToObject(root, "messages", messages);
    cJSON_AddNumberToObject(root, "temperature", 0.7);
    cJSON_AddNumberToObject(root, "max_tokens", 150);
    
    char *request_body = cJSON_PrintUnformatted(root);
    cJSON_Delete(root);
    
    // Configure HTTP client
    esp_http_client_config_t config = {
        .url = "https://api.openai.com/v1/chat/completions",
        .method = HTTP_METHOD_POST,
        .event_handler = http_event_handler,
        .crt_bundle_attach = esp_crt_bundle_attach,
        .timeout_ms = 30000,
    };
    
    esp_http_client_handle_t client = esp_http_client_init(&config);
    
    esp_http_client_set_header(client, "Content-Type", "application/json");
    esp_http_client_set_header(client, "Authorization", auth_header);
    esp_http_client_set_post_field(client, request_body, strlen(request_body));
    
    // Perform request
    esp_err_t err = esp_http_client_perform(client);
    char *ai_response = NULL;
    
    if (err == ESP_OK) {
        int status = esp_http_client_get_status_code(client);
        ESP_LOGI(TAG, "Chat API Status = %d", status);
        
        if (status == 200 && http_response_len > 0) {
            // Parse JSON response
            cJSON *json = cJSON_Parse(http_response_buffer);
            if (json) {
                cJSON *choices = cJSON_GetObjectItem(json, "choices");
                if (choices && cJSON_GetArraySize(choices) > 0) {
                    cJSON *choice = cJSON_GetArrayItem(choices, 0);
                    cJSON *message = cJSON_GetObjectItem(choice, "message");
                    cJSON *content = cJSON_GetObjectItem(message, "content");
                    if (content && content->valuestring) {
                        ai_response = strdup(content->valuestring);
                        ESP_LOGI(TAG, "AI Response: %s", ai_response);
                    }
                }
                cJSON_Delete(json);
            }
        }
    } else {
        ESP_LOGE(TAG, "Chat API request failed: %s", esp_err_to_name(err));
    }
    
    free(request_body);
    free(http_response_buffer);
    esp_http_client_cleanup(client);
    
    return ai_response;
}

// Context for TTS audio capture
typedef struct {
    uint8_t *buffer;
    size_t len;
    size_t max_size;
} tts_audio_ctx_t;

/**
 * HTTP event handler for TTS binary audio data
 */
static esp_err_t tts_event_handler(esp_http_client_event_t *evt)
{
    if (evt->event_id == HTTP_EVENT_ON_DATA) {
        tts_audio_ctx_t *ctx = (tts_audio_ctx_t*)evt->user_data;
        if (ctx->buffer && ctx->len + evt->data_len < ctx->max_size) {
            memcpy(ctx->buffer + ctx->len, evt->data, evt->data_len);
            ctx->len += evt->data_len;
        }
    }
    return ESP_OK;
}

/**
 * Convert text to speech using OpenAI TTS API and play it
 */
static esp_err_t speak_text(const char *text)
{
    ESP_LOGI(TAG, "Converting text to speech...");
    set_led(LED_CYAN);
    
    // Prepare authorization header
    char auth_header[256];
    snprintf(auth_header, sizeof(auth_header), "Bearer %s", OPENAI_API_KEY);
    
    // Build request body
    cJSON *root = cJSON_CreateObject();
    cJSON_AddStringToObject(root, "model", "tts-1");
    cJSON_AddStringToObject(root, "input", text);
    cJSON_AddStringToObject(root, "voice", "alloy");
    cJSON_AddStringToObject(root, "response_format", "pcm");
    
    char *request_body = cJSON_PrintUnformatted(root);
    cJSON_Delete(root);
    
    // Allocate buffer for audio response
    size_t audio_buffer_size = 512 * 1024;  // 512KB should be enough
    uint8_t *audio_buffer = malloc(audio_buffer_size);
    if (!audio_buffer) {
        ESP_LOGE(TAG, "Failed to allocate audio buffer");
        free(request_body);
        return ESP_ERR_NO_MEM;
    }
    
    tts_audio_ctx_t audio_ctx = {
        .buffer = audio_buffer,
        .len = 0,
        .max_size = audio_buffer_size
    };
    
    // Configure HTTP client
    esp_http_client_config_t config = {
        .url = "https://api.openai.com/v1/audio/speech",
        .method = HTTP_METHOD_POST,
        .event_handler = tts_event_handler,
        .user_data = &audio_ctx,
        .crt_bundle_attach = esp_crt_bundle_attach,
        .timeout_ms = 60000,
        .buffer_size = 4096,
    };
    
    esp_http_client_handle_t client = esp_http_client_init(&config);
    
    esp_http_client_set_header(client, "Content-Type", "application/json");
    esp_http_client_set_header(client, "Authorization", auth_header);
    esp_http_client_set_post_field(client, request_body, strlen(request_body));
    
    // Perform request
    esp_err_t err = esp_http_client_perform(client);
    
    if (err == ESP_OK) {
        int status = esp_http_client_get_status_code(client);
        ESP_LOGI(TAG, "TTS API Status = %d, received %d bytes", status, audio_ctx.len);
        
        if (status == 200 && audio_ctx.len > 0) {
            // Play audio through speaker
            // TTS returns mono PCM, convert to stereo
            size_t sample_count = audio_ctx.len / 2;
            int16_t *stereo_buffer = (int16_t*)malloc(sample_count * 4);
            if (stereo_buffer) {
                int16_t *mono = (int16_t*)audio_buffer;
                for (size_t i = 0; i < sample_count; i++) {
                    stereo_buffer[i * 2] = mono[i];
                    stereo_buffer[i * 2 + 1] = mono[i];
                }
                
                size_t bytes_written;
                i2s_channel_write(spk_chan, stereo_buffer, sample_count * 4, &bytes_written, portMAX_DELAY);
                ESP_LOGI(TAG, "✓ Played %d samples", sample_count);
                
                free(stereo_buffer);
            }
        }
    } else {
        ESP_LOGE(TAG, "TTS API request failed: %s", esp_err_to_name(err));
    }
    
    free(request_body);
    free(audio_buffer);
    esp_http_client_cleanup(client);
    
    set_led(LED_GREEN);
    return err;
}

/**
 * Send audio to OpenAI Whisper API for transcription
 */
static char* transcribe_audio(const int16_t *audio_data, size_t sample_count)
{
    ESP_LOGI(TAG, "→ Transcribing %d samples (%.2f seconds) to Whisper API...", 
             sample_count, (float)sample_count / SAMPLE_RATE);
    set_led(LED_YELLOW);
    
    // Allocate response buffer
    http_response_buffer = malloc(HTTP_RESPONSE_BUFFER_SIZE);
    if (!http_response_buffer) {
        ESP_LOGE(TAG, "Failed to allocate response buffer");
        return NULL;
    }
    http_response_len = 0;
    
    ESP_LOGI(TAG, "  Building WAV file and multipart form data...");
    
    // Prepare authorization header
    char auth_header[256];
    snprintf(auth_header, sizeof(auth_header), "Bearer %s", OPENAI_API_KEY);
    
    // Configure HTTP client for multipart form data
    esp_http_client_config_t config = {
        .url = "https://api.openai.com/v1/audio/transcriptions",
        .method = HTTP_METHOD_POST,
        .event_handler = http_event_handler,
        .crt_bundle_attach = esp_crt_bundle_attach,
        .timeout_ms = 30000,
    };
    
    esp_http_client_handle_t client = esp_http_client_init(&config);
    
    // Create multipart boundary
    const char *boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW";
    char content_type[128];
    snprintf(content_type, sizeof(content_type), "multipart/form-data; boundary=%s", boundary);
    
    esp_http_client_set_header(client, "Authorization", auth_header);
    esp_http_client_set_header(client, "Content-Type", content_type);
    
    // Build multipart form data
    // Note: Sending raw PCM as WAV file with header
    size_t wav_data_size = sample_count * 2;  // 16-bit samples
    size_t wav_file_size = wav_data_size + 44;  // WAV header is 44 bytes
    
    // Allocate buffer for complete request body
    size_t body_size = 512 + wav_file_size;
    char *body = malloc(body_size);
    if (!body) {
        ESP_LOGE(TAG, "Failed to allocate request body");
        free(http_response_buffer);
        esp_http_client_cleanup(client);
        return NULL;
    }
    
    // Build multipart body with WAV file
    int offset = 0;
    offset += snprintf(body + offset, body_size - offset,
        "--%s\r\n"
        "Content-Disposition: form-data; name=\"file\"; filename=\"audio.wav\"\r\n"
        "Content-Type: audio/wav\r\n\r\n", boundary);
    
    // Write WAV header
    memcpy(body + offset, "RIFF", 4); offset += 4;
    uint32_t chunk_size = wav_file_size - 8;
    memcpy(body + offset, &chunk_size, 4); offset += 4;
    memcpy(body + offset, "WAVE", 4); offset += 4;
    memcpy(body + offset, "fmt ", 4); offset += 4;
    uint32_t subchunk1_size = 16;
    memcpy(body + offset, &subchunk1_size, 4); offset += 4;
    uint16_t audio_format = 1;  // PCM
    memcpy(body + offset, &audio_format, 2); offset += 2;
    uint16_t num_channels = 1;
    memcpy(body + offset, &num_channels, 2); offset += 2;
    uint32_t sample_rate = SAMPLE_RATE;
    memcpy(body + offset, &sample_rate, 4); offset += 4;
    uint32_t byte_rate = SAMPLE_RATE * 2;
    memcpy(body + offset, &byte_rate, 4); offset += 4;
    uint16_t block_align = 2;
    memcpy(body + offset, &block_align, 2); offset += 2;
    uint16_t bits_per_sample = 16;
    memcpy(body + offset, &bits_per_sample, 2); offset += 2;
    memcpy(body + offset, "data", 4); offset += 4;
    uint32_t subchunk2_size = wav_data_size;
    memcpy(body + offset, &subchunk2_size, 4); offset += 4;
    
    // Copy audio data
    memcpy(body + offset, audio_data, wav_data_size); offset += wav_data_size;
    
    // Add form fields
    offset += snprintf(body + offset, body_size - offset,
        "\r\n--%s\r\n"
        "Content-Disposition: form-data; name=\"model\"\r\n\r\n"
        "whisper-1\r\n"
        "--%s--\r\n", boundary, boundary);
    
    esp_http_client_set_post_field(client, body, offset);
    
    ESP_LOGI(TAG, "  Sending %d bytes to Whisper API...", offset);
    
    // Perform request
    esp_err_t err = esp_http_client_perform(client);
    char *transcription = NULL;
    
    if (err == ESP_OK) {
        int status = esp_http_client_get_status_code(client);
        ESP_LOGI(TAG, "  Whisper API Status = %d, response length = %d", status, http_response_len);
        
        if (status == 200 && http_response_len > 0) {
            ESP_LOGI(TAG, "  Response: %.*s", http_response_len, http_response_buffer);
            // Parse JSON response
            cJSON *json = cJSON_Parse(http_response_buffer);
            if (json) {
                cJSON *text = cJSON_GetObjectItem(json, "text");
                if (text && text->valuestring) {
                    transcription = strdup(text->valuestring);
                    ESP_LOGI(TAG, "  ✓ Transcription successful");
                } else {
                    ESP_LOGE(TAG, "  ✗ No 'text' field in response");
                }
                cJSON_Delete(json);
            } else {
                ESP_LOGE(TAG, "  ✗ Failed to parse JSON response");
            }
        } else {
            ESP_LOGE(TAG, "  ✗ HTTP error: status=%d, response: %.*s", 
                     status, http_response_len, http_response_buffer);
        }
    } else {
        ESP_LOGE(TAG, "  ✗ Whisper API request failed: %s", esp_err_to_name(err));
    }
    
    free(body);
    free(http_response_buffer);
    esp_http_client_cleanup(client);
    
    return transcription;
}

/**
 * Encode audio to Base64 (demo function) - runs in separate task
 */
/**
 * Initialize PDM microphone on I2S0
 */
static esp_err_t init_pdm_microphone(void)
{
    ESP_LOGI(TAG, "Initializing PDM microphone...");
    
    // I2S channel configuration for PDM RX
    i2s_chan_config_t chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0, I2S_ROLE_MASTER);
    ESP_ERROR_CHECK(i2s_new_channel(&chan_cfg, NULL, &mic_chan));
    
    // PDM RX configuration
    i2s_pdm_rx_config_t pdm_rx_cfg = {
        .clk_cfg = I2S_PDM_RX_CLK_DEFAULT_CONFIG(SAMPLE_RATE),
        .slot_cfg = I2S_PDM_RX_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO),
        .gpio_cfg = {
            .clk = PDM_MIC_CLK,
            .din = PDM_MIC_DATA,
            .invert_flags = {
                .clk_inv = false,
            },
        },
    };
    
    ESP_ERROR_CHECK(i2s_channel_init_pdm_rx_mode(mic_chan, &pdm_rx_cfg));
    ESP_ERROR_CHECK(i2s_channel_enable(mic_chan));
    
    ESP_LOGI(TAG, "PDM microphone initialized successfully!");
    return ESP_OK;
}

/**
 * Initialize I2S speaker on I2S1
 */
static esp_err_t init_i2s_speaker(void)
{
    ESP_LOGI(TAG, "Initializing I2S speaker...");
    
    // I2S channel configuration for standard TX
    i2s_chan_config_t chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_1, I2S_ROLE_MASTER);
    ESP_ERROR_CHECK(i2s_new_channel(&chan_cfg, &spk_chan, NULL));
    
    // Standard mode configuration for NS4168
    i2s_std_config_t std_cfg = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(SAMPLE_RATE),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_STEREO),
        .gpio_cfg = {
            .mclk = I2S_GPIO_UNUSED,
            .bclk = I2S_SPK_BCK,
            .ws = I2S_SPK_WS,
            .dout = I2S_SPK_DATA,
            .din = I2S_GPIO_UNUSED,
            .invert_flags = {
                .mclk_inv = false,
                .bclk_inv = false,
                .ws_inv = false,
            },
        },
    };
    
    ESP_ERROR_CHECK(i2s_channel_init_std_mode(spk_chan, &std_cfg));
    ESP_ERROR_CHECK(i2s_channel_enable(spk_chan));
    
    ESP_LOGI(TAG, "I2S speaker initialized successfully!");
    return ESP_OK;
}

/**
 * Start recording audio from microphone
 */
static esp_err_t start_recording(void)
{
    if (is_recording) {
        ESP_LOGW(TAG, "Already recording!");
        return ESP_ERR_INVALID_STATE;
    }
    
    // Calculate max buffer size (at 24kHz, 16-bit mono)
    recording_buffer_size = (SAMPLE_RATE * MAX_RECORDING_DURATION_MS) / 1000;  // in samples
    size_t buffer_bytes = recording_buffer_size * sizeof(int16_t);
    
    ESP_LOGI(TAG, "Allocating %d bytes for recording buffer (free heap: %lu bytes)", 
             buffer_bytes, esp_get_free_heap_size());
    
    recording_buffer = (int16_t *)malloc(buffer_bytes);
    if (!recording_buffer) {
        ESP_LOGE(TAG, "Failed to allocate recording buffer! Need %d bytes, have %lu free", 
                 buffer_bytes, esp_get_free_heap_size());
        return ESP_ERR_NO_MEM;
    }
    
    recording_position = 0;  // in samples
    is_recording = true;
    
    ESP_LOGI(TAG, "Started recording (max %d seconds, %d samples buffer)", 
             MAX_RECORDING_DURATION_MS / 1000, recording_buffer_size);
    set_led(LED_MAGENTA);  // Recording
    
    return ESP_OK;
}

/**
 * Stop recording and prepare to send
 */
static esp_err_t stop_recording(void)
{
    if (!is_recording) {
        ESP_LOGW(TAG, "Not recording!");
        return ESP_ERR_INVALID_STATE;
    }
    
    is_recording = false;
    
    float duration_sec = (float)recording_position / SAMPLE_RATE;
    ESP_LOGI(TAG, "Stopped recording: %.2f seconds, %d samples", duration_sec, recording_position);
    
    set_led(LED_YELLOW);  // Processing
    
    return ESP_OK;
}

/**
 * Recording task - captures audio while button is pressed
 */
static void recording_task(void *arg)
{
    int16_t audio_chunk[AUDIO_CHUNK_SIZE];
    size_t bytes_read = 0;
    
    while (1) {
        if (is_recording) {
            // Read audio from microphone
            esp_err_t ret = i2s_channel_read(mic_chan, audio_chunk, sizeof(audio_chunk), &bytes_read, 100);
            
            if (ret == ESP_OK && bytes_read > 0) {
                size_t samples_read = bytes_read / sizeof(int16_t);
                
                // Check if we have space in buffer
                if (recording_position + samples_read <= recording_buffer_size) {
                    memcpy(&recording_buffer[recording_position], audio_chunk, bytes_read);
                    recording_position += samples_read;
                } else {
                    // Buffer full - stop recording
                    ESP_LOGW(TAG, "Recording buffer full!");
                    is_recording = false;
                    set_led(LED_RED);
                }
            }
        } else {
            vTaskDelay(pdMS_TO_TICKS(100));  // Sleep when not recording
        }
    }
}

/**
 * Send recorded audio to OpenAI
 */
/**
 * Button task - Push-to-Talk interface
 */
static void button_task(void *arg)
{
    // GPIO 39 is input-only and has external pull-up, so don't enable internal pull-up
    gpio_config_t io_conf = {
        .pin_bit_mask = (1ULL << BUTTON_PIN),
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_DISABLE,  // External pull-up on GPIO 39
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&io_conf);
    
    bool last_state = true;
    
    while (1) {
        bool current_state = gpio_get_level(BUTTON_PIN);
        
        // Button pressed (active low)
        if (last_state == true && current_state == false) {
            vTaskDelay(pdMS_TO_TICKS(50)); // Debounce
            if (gpio_get_level(BUTTON_PIN) == false) {
                ESP_LOGI(TAG, "Button pressed - starting recording...");
                start_recording();
            }
        }
        // Button released
        else if (last_state == false && current_state == true) {
            vTaskDelay(pdMS_TO_TICKS(50)); // Debounce
            if (gpio_get_level(BUTTON_PIN) == true) {
                ESP_LOGI(TAG, "Button released - processing...");
                stop_recording();
                
                // Check if we have audio
                if (recording_position == 0) {
                    ESP_LOGW(TAG, "No audio recorded!");
                    set_led(LED_RED);
                    vTaskDelay(pdMS_TO_TICKS(1000));
                    set_led(LED_GREEN);
                    continue;
                }
                
                ESP_LOGI(TAG, "Processing %d samples...", recording_position);
                set_led(LED_YELLOW);  // Processing
                
                // Step 1: Transcribe audio
                ESP_LOGI(TAG, "Step 1: Calling Whisper API...");
                char *transcription = transcribe_audio(recording_buffer, recording_position);
                if (transcription) {
                    ESP_LOGI(TAG, "✓ Transcription: %s", transcription);
                    
                    // Step 2: Get AI response
                    ESP_LOGI(TAG, "Step 2: Calling Chat API...");
                    char *response = get_ai_response(transcription);
                    if (response) {
                        ESP_LOGI(TAG, "✓ AI Response: %s", response);
                        
                        // Step 3: Convert to speech and play
                        ESP_LOGI(TAG, "Step 3: Calling TTS API...");
                        speak_text(response);
                        
                        free(response);
                    } else {
                        ESP_LOGE(TAG, "✗ Failed to get AI response");
                        set_led(LED_RED);
                        vTaskDelay(pdMS_TO_TICKS(2000));
                        set_led(LED_GREEN);
                    }
                    
                    free(transcription);
                } else {
                    ESP_LOGE(TAG, "✗ Failed to transcribe audio");
                    set_led(LED_RED);
                    vTaskDelay(pdMS_TO_TICKS(2000));
                    set_led(LED_GREEN);
                }
            }
        }
        
        last_state = current_state;
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

/**
 * Main application entry point
 */
void app_main(void)
{
    ESP_LOGI(TAG, "\n\n=== ATOM Echo Voice Assistant ===");
    ESP_LOGI(TAG, "Build: PlatformIO + ESP-IDF");
    ESP_LOGI(TAG, "ESP-IDF Version: %s", esp_get_idf_version());
    
    // Initialize NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);
    
    // Initialize LED
    set_led(LED_BLUE);
    ESP_ERROR_CHECK(init_led());
    
    // Initialize WiFi
    init_wifi();
    
    // Wait for WiFi connection
    EventBits_t bits = xEventGroupWaitBits(wifi_event_group,
                                           WIFI_CONNECTED_BIT | WIFI_FAIL_BIT,
                                           pdFALSE,
                                           pdFALSE,
                                           portMAX_DELAY);
    
    if (bits & WIFI_CONNECTED_BIT) {
        ESP_LOGI(TAG, "WiFi connected!");
        set_led(LED_CYAN);
    } else {
        ESP_LOGE(TAG, "WiFi connection failed!");
        set_led(LED_RED);
        return;
    }
    
    // Initialize PDM microphone (NEW ESP-IDF I2S driver with PDM support!)
    ESP_ERROR_CHECK(init_pdm_microphone());
    
    // Initialize I2S speaker
    ESP_ERROR_CHECK(init_i2s_speaker());
    
    // Ready!
    ESP_LOGI(TAG, "Setup complete - Ready!");
    ESP_LOGI(TAG, "Free heap: %lu bytes", esp_get_free_heap_size());
    set_led(LED_GREEN);
    
    // Start recording task
    xTaskCreate(recording_task, "recording_task", 4096, NULL, 10, NULL);
    
    // Start button task (reduced stack for REST API sequential processing)
    xTaskCreate(button_task, "button_task", 8192, NULL, 5, NULL);
    
    ESP_LOGI(TAG, "Voice assistant ready! Press and hold button to speak.");
    ESP_LOGI(TAG, "Max recording: %d seconds (%d samples = %d bytes)",
             MAX_RECORDING_DURATION_MS / 1000,
             (SAMPLE_RATE * MAX_RECORDING_DURATION_MS) / 1000,
             (SAMPLE_RATE * MAX_RECORDING_DURATION_MS * 2) / 1000);
}
