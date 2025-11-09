/**
 * LED Strip Encoder for RMT peripheral
 * Based on ESP-IDF examples
 */

#pragma once

#include <stdint.h>
#include "driver/rmt_encoder.h"

#ifdef __cplusplus
extern "C" {
#endif

/**
 * @brief Type of LED strip encoder configuration
 */
typedef struct {
    uint32_t resolution; /*!< Encoder resolution, in Hz */
} led_strip_encoder_config_t;

/**
 * @brief Create RMT encoder for encoding LED strip pixels into RMT symbols
 *
 * @param[in] config Encoder configuration
 * @param[out] ret_encoder Returned encoder handle
 * @return
 *      - ESP_OK: Create RMT encoder successfully
 *      - ESP_ERR_INVALID_ARG: Create RMT encoder failed because of invalid argument
 *      - ESP_ERR_NO_MEM: Create RMT encoder failed because out of memory
 *      - ESP_FAIL: Create RMT encoder failed because of other error
 */
esp_err_t rmt_new_led_strip_encoder(const led_strip_encoder_config_t *config, rmt_encoder_handle_t *ret_encoder);

#ifdef __cplusplus
}
#endif
