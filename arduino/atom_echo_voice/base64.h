// Base64 encoding/decoding for Arduino
// Simplified implementation for audio data

#ifndef BASE64_H
#define BASE64_H

#include <Arduino.h>

namespace base64 {
  
  const char encodingTable[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
  
  String encode(const uint8_t* data, size_t length) {
    size_t encodedLength = 4 * ((length + 2) / 3);
    String encoded;
    encoded.reserve(encodedLength);
    
    for (size_t i = 0; i < length; i += 3) {
      uint32_t triple = (data[i] << 16);
      
      if (i + 1 < length) {
        triple |= (data[i + 1] << 8);
      }
      
      if (i + 2 < length) {
        triple |= data[i + 2];
      }
      
      encoded += encodingTable[(triple >> 18) & 0x3F];
      encoded += encodingTable[(triple >> 12) & 0x3F];
      encoded += (i + 1 < length) ? encodingTable[(triple >> 6) & 0x3F] : '=';
      encoded += (i + 2 < length) ? encodingTable[triple & 0x3F] : '=';
    }
    
    return encoded;
  }
  
  size_t decodeLength(const String& input) {
    size_t len = input.length();
    size_t padding = 0;
    
    if (len > 0 && input[len - 1] == '=') padding++;
    if (len > 1 && input[len - 2] == '=') padding++;
    
    return (len / 4) * 3 - padding;
  }
  
  int decode(const String& input, uint8_t* output, size_t outputSize) {
    size_t len = input.length();
    if (len % 4 != 0) return -1;
    
    size_t outputLength = decodeLength(input);
    if (outputLength > outputSize) return -1;
    
    size_t j = 0;
    for (size_t i = 0; i < len; i += 4) {
      uint32_t sextet_a = input[i] == '=' ? 0 : strchr(encodingTable, input[i]) - encodingTable;
      uint32_t sextet_b = input[i + 1] == '=' ? 0 : strchr(encodingTable, input[i + 1]) - encodingTable;
      uint32_t sextet_c = input[i + 2] == '=' ? 0 : strchr(encodingTable, input[i + 2]) - encodingTable;
      uint32_t sextet_d = input[i + 3] == '=' ? 0 : strchr(encodingTable, input[i + 3]) - encodingTable;
      
      uint32_t triple = (sextet_a << 18) + (sextet_b << 12) + (sextet_c << 6) + sextet_d;
      
      if (j < outputLength) output[j++] = (triple >> 16) & 0xFF;
      if (j < outputLength) output[j++] = (triple >> 8) & 0xFF;
      if (j < outputLength) output[j++] = triple & 0xFF;
    }
    
    return outputLength;
  }
}

#endif // BASE64_H
