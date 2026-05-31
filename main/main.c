#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/event_groups.h"
#include "esp_system.h"
#include "esp_wifi.h"
#include "esp_event.h"
#include "esp_log.h"
#include "nvs_flash.h"
#include "driver/i2s_pdm.h"
#include "driver/i2s_std.h"
#include "driver/gpio.h"
#include "esp_websocket_client.h"
#include "esp_crt_bundle.h"
#include "mbedtls/base64.h"

static const char *TAG = "atom_echo";

// Pin Configuration
#define BUTTON_PIN      39
#define LED_PIN         27
#define PDM_MIC_CLK     33
#define PDM_MIC_DATA    23
#define I2S_SPK_BCK     19
#define I2S_SPK_WS      33
#define I2S_SPK_DATA    22

// FreeRTOS event group to signal when we are connected
static EventGroupHandle_t s_wifi_event_group;
#define WIFI_CONNECTED_BIT BIT0
#define WIFI_FAIL_BIT      BIT1

static int s_retry_num = 0;

static volatile bool ws_connected = false;
static volatile bool is_speaking = false;
static volatile bool i2s_busy = false;
static esp_websocket_client_handle_t ws_client = NULL;
static i2s_chan_handle_t rx_chan = NULL;
static i2s_chan_handle_t tx_chan = NULL;

// Buffers
#define AUDIO_CHUNK_SIZE 2048
static uint8_t mic_buf[AUDIO_CHUNK_SIZE];
static uint8_t spk_buf[16384];
static unsigned char base64_buf[AUDIO_CHUNK_SIZE * 2];
static char json_buf[AUDIO_CHUNK_SIZE * 2 + 256];

// Pre-declare
void audio_init_mic(void);
void audio_init_spk(void);

static void event_handler(void* arg, esp_event_base_t event_base,
                                int32_t event_id, void* event_data)
{
    if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_DISCONNECTED) {
        if (s_retry_num < 10) {
            esp_wifi_connect();
            s_retry_num++;
            ESP_LOGI(TAG, "retry to connect to the AP");
        } else {
            xEventGroupSetBits(s_wifi_event_group, WIFI_FAIL_BIT);
        }
        ESP_LOGI(TAG,"connect to the AP fail");
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t* event = (ip_event_got_ip_t*) event_data;
        ESP_LOGI(TAG, "got ip:" IPSTR, IP2STR(&event->ip_info.ip));
        s_retry_num = 0;
        xEventGroupSetBits(s_wifi_event_group, WIFI_CONNECTED_BIT);
    }
}

void wifi_init_sta(void)
{
    s_wifi_event_group = xEventGroupCreate();

    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();

    wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&cfg));

    esp_event_handler_instance_t instance_any_id;
    esp_event_handler_instance_t instance_got_ip;
    ESP_ERROR_CHECK(esp_event_handler_instance_register(WIFI_EVENT,
                                                        ESP_EVENT_ANY_ID,
                                                        &event_handler,
                                                        NULL,
                                                        &instance_any_id));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(IP_EVENT,
                                                        IP_EVENT_STA_GOT_IP,
                                                        &event_handler,
                                                        NULL,
                                                        &instance_got_ip));

    wifi_config_t wifi_config = {
        .sta = {
            .ssid = CONFIG_WIFI_SSID,
            .password = CONFIG_WIFI_PASSWORD,
            .threshold.authmode = WIFI_AUTH_WPA2_PSK,
        },
    };
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA) );
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config) );
    ESP_ERROR_CHECK(esp_wifi_start() );

    ESP_LOGI(TAG, "wifi_init_sta finished.");

    EventBits_t bits = xEventGroupWaitBits(s_wifi_event_group,
            WIFI_CONNECTED_BIT | WIFI_FAIL_BIT,
            pdFALSE,
            pdFALSE,
            portMAX_DELAY);

    if (bits & WIFI_CONNECTED_BIT) {
        ESP_LOGI(TAG, "connected to ap SSID:%s", CONFIG_WIFI_SSID);
    } else if (bits & WIFI_FAIL_BIT) {
        ESP_LOGI(TAG, "Failed to connect to SSID:%s", CONFIG_WIFI_SSID);
    }
}

void audio_init_mic(void) {
    if (tx_chan) {
        i2s_channel_disable(tx_chan);
        i2s_del_channel(tx_chan);
        tx_chan = NULL;
    }
    
    i2s_chan_config_t rx_chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_AUTO, I2S_ROLE_MASTER);
    esp_err_t err = i2s_new_channel(&rx_chan_cfg, NULL, &rx_chan);
    if (err != ESP_OK) return;

    i2s_pdm_rx_config_t pdm_rx_cfg = {
        .clk_cfg = I2S_PDM_RX_CLK_DEFAULT_CONFIG(24000),
        .slot_cfg = I2S_PDM_RX_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO),
        .gpio_cfg = {
            .clk = PDM_MIC_CLK,
            .din = PDM_MIC_DATA,
            .invert_flags = {
                .clk_inv = false,
            },
        },
    };
    i2s_channel_init_pdm_rx_mode(rx_chan, &pdm_rx_cfg);
    i2s_channel_enable(rx_chan);
    ESP_LOGI(TAG, "Initialized PDM Microphone at 24kHz");
}

void audio_init_spk(void) {
    if (rx_chan) {
        i2s_channel_disable(rx_chan);
        i2s_del_channel(rx_chan);
        rx_chan = NULL;
    }

    i2s_chan_config_t tx_chan_cfg = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_AUTO, I2S_ROLE_MASTER);
    esp_err_t err = i2s_new_channel(&tx_chan_cfg, &tx_chan, NULL);
    if (err != ESP_OK) return;

    i2s_std_config_t std_cfg = {
        .clk_cfg  = I2S_STD_CLK_DEFAULT_CONFIG(24000),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_STEREO),
        .gpio_cfg = {
            .mclk = I2S_GPIO_UNUSED,
            .bclk = I2S_SPK_BCK,
            .ws   = I2S_SPK_WS,
            .dout = I2S_SPK_DATA,
            .din  = I2S_GPIO_UNUSED,
            .invert_flags = {
                .mclk_inv = false,
                .bclk_inv = false,
                .ws_inv   = false,
            },
        },
    };

    err = i2s_channel_init_std_mode(tx_chan, &std_cfg);
    i2s_channel_enable(tx_chan);
    ESP_LOGI(TAG, "Initialized I2S Speaker at 24kHz");
}

#define MAX_WS_RX_BUF 65536
static char ws_rx_buf[MAX_WS_RX_BUF];
static size_t ws_rx_len = 0;
static uint8_t decode_buf[49152];

static void websocket_event_handler(void *handler_args, esp_event_base_t base, int32_t event_id, void *event_data)
{
    esp_websocket_event_data_t *data = (esp_websocket_event_data_t *)event_data;
    switch (event_id) {
        case WEBSOCKET_EVENT_CONNECTED:
            ESP_LOGI(TAG, "WEBSOCKET_EVENT_CONNECTED");
            ws_connected = true;
            
            const char* initial_greeting = "{\"type\":\"response.create\",\"response\":{\"instructions\":\"Greet the user warmly and introduce yourself as their ATOM Echo Voice Assistant. Say you are ready to help.\"}}";
            esp_websocket_client_send_text(ws_client, initial_greeting, strlen(initial_greeting), portMAX_DELAY);
            break;
            
        case WEBSOCKET_EVENT_DISCONNECTED:
            ESP_LOGI(TAG, "WEBSOCKET_EVENT_DISCONNECTED");
            ws_connected = false;
            if (is_speaking) {
                is_speaking = false;
                while (i2s_busy) vTaskDelay(pdMS_TO_TICKS(10));
                audio_init_mic();
            }
            break;
            
        case WEBSOCKET_EVENT_DATA:
            if (data->op_code == 1 || data->op_code == 0) { // Text frame or continuation
                if (data->payload_offset == 0) ws_rx_len = 0;
                
                if (ws_rx_len + data->data_len < MAX_WS_RX_BUF) {
                    memcpy(ws_rx_buf + ws_rx_len, data->data_ptr, data->data_len);
                    ws_rx_len += data->data_len;
                }
                
                if (data->payload_offset + data->data_len == data->payload_len) {
                    ws_rx_buf[ws_rx_len] = '\0';
                    char *payload = ws_rx_buf;
                    
                    if (strstr(payload, "response.audio.delta")) {
                        if (!is_speaking) {
                            is_speaking = true;
                            while (i2s_busy) vTaskDelay(pdMS_TO_TICKS(10));
                            audio_init_spk();
                        }
                        
                        char *delta_key = strstr(payload, "\"delta\"");
                        if (delta_key) {
                            char *delta_start = strchr(delta_key + 7, '"');
                            if (delta_start) {
                                delta_start++;
                                char *delta_end = strchr(delta_start, '"');
                                if (delta_end) {
                                    *delta_end = '\0';
                                    size_t decoded_len = 0;
                                    mbedtls_base64_decode(decode_buf, sizeof(decode_buf), &decoded_len, (const unsigned char*)delta_start, strlen(delta_start));
                                    
                                    if (tx_chan && decoded_len > 0) {
                                        i2s_busy = true;
                                        int16_t* in_samples = (int16_t*)decode_buf;
                                        int num_samples = decoded_len / 2;
                                        int chunk_samples = 4096; // 4096 mono samples -> 16384 bytes stereo
                                        int16_t *spk_buf_16 = (int16_t*)spk_buf;
                                        
                                        for (int i = 0; i < num_samples; i += chunk_samples) {
                                            int samples_to_process = (num_samples - i > chunk_samples) ? chunk_samples : (num_samples - i);
                                            for (int j = 0; j < samples_to_process; j++) {
                                                int32_t val = in_samples[i + j] * 2; // Reduced gain from 8 to 2 to prevent hard clipping distortion
                                                if (val > 32767) val = 32767;
                                                if (val < -32768) val = -32768;
                                                spk_buf_16[j * 2] = (int16_t)val;
                                                spk_buf_16[j * 2 + 1] = (int16_t)val;
                                            }
                                            size_t written = 0;
                                            i2s_channel_write(tx_chan, spk_buf, samples_to_process * 4, &written, portMAX_DELAY);
                                        }
                                        i2s_busy = false;
                                    }
                                }
                            }
                        }
                    } else if (strstr(payload, "response.audio.done") != NULL ||
                               strstr(payload, "response.done") != NULL) {
                        if (is_speaking) {
                            vTaskDelay(pdMS_TO_TICKS(400));
                            is_speaking = false;
                            while (i2s_busy) vTaskDelay(pdMS_TO_TICKS(10));
                            audio_init_mic();
                        }
                    }
                }
            }
            break;
            
        case WEBSOCKET_EVENT_ERROR:
            ESP_LOGE(TAG, "WEBSOCKET_EVENT_ERROR");
            break;
    }
}

void audio_record_task(void *pvParameters)
{
    size_t bytes_read = 0;
    size_t base64_len = 0;
    
    while (1) {
        if (ws_connected && !is_speaking && rx_chan != NULL) {
            i2s_busy = true;
            esp_err_t err = i2s_channel_read(rx_chan, mic_buf, AUDIO_CHUNK_SIZE, &bytes_read, pdMS_TO_TICKS(50));
            i2s_busy = false;
            
            if (err == ESP_OK && bytes_read > 0 && !is_speaking) {
                mbedtls_base64_encode(base64_buf, sizeof(base64_buf), &base64_len, mic_buf, bytes_read);
                base64_buf[base64_len] = '\0';
                
                int len = snprintf(json_buf, sizeof(json_buf), "{\"type\":\"input_audio_buffer.append\",\"audio\":\"%s\"}", base64_buf);
                if (len > 0) {
                    esp_websocket_client_send_text(ws_client, json_buf, len, portMAX_DELAY);
                }
            }
        } else {
            vTaskDelay(pdMS_TO_TICKS(10));
        }
    }
}

void app_main(void)
{
    ESP_LOGI(TAG, "M5Stack ATOM Echo Voice Assistant starting...");
    
    // Initialize NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
      ESP_ERROR_CHECK(nvs_flash_erase());
      ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);
    
    wifi_init_sta();

    // Init Audio in Mic Mode
    audio_init_mic();
    
    // Configure WebSocket to OpenAI
    esp_websocket_client_config_t ws_cfg = {
        .uri = "wss://api.openai.com/v1/realtime?model=gpt-realtime-mini",
        .crt_bundle_attach = esp_crt_bundle_attach,
        .buffer_size = 8192,
    };
    
    ws_client = esp_websocket_client_init(&ws_cfg);
    
    char auth_header[256];
    snprintf(auth_header, sizeof(auth_header), "Bearer %s", CONFIG_OPENAI_API_KEY);
    esp_websocket_client_append_header(ws_client, "Authorization", auth_header);
    
    esp_websocket_register_events(ws_client, WEBSOCKET_EVENT_ANY, websocket_event_handler, (void *)ws_client);
    esp_websocket_client_start(ws_client);
    
    xTaskCreate(audio_record_task, "audio_record_task", 4096, NULL, 5, NULL);

    while(1) {
        vTaskDelay(1000 / portTICK_PERIOD_MS);
    }
}
