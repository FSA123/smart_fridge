#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include "secrets.h"

// ==========================================
// 1. YOUR NETWORK & SERVER SETTINGS
// ==========================================
// Credentials and API key are now in secrets.h

// ==========================================
// 2. HARDWARE PINOUT (AI-Thinker)
// ==========================================
#define FLASH_GPIO_NUM    4
#define PWDN_GPIO_NUM    32
#define RESET_GPIO_NUM   -1
#define XCLK_GPIO_NUM     0
#define SIOD_GPIO_NUM    26
#define SIOC_GPIO_NUM    27
#define Y9_GPIO_NUM      35
#define Y8_GPIO_NUM      34
#define Y7_GPIO_NUM      39
#define Y6_GPIO_NUM      36
#define Y5_GPIO_NUM      21
#define Y4_GPIO_NUM      19
#define Y3_GPIO_NUM      18
#define Y2_GPIO_NUM       5
#define VSYNC_GPIO_NUM   25
#define HREF_GPIO_NUM    23
#define PCLK_GPIO_NUM    22

void setup() {
  Serial.begin(115200);
  Serial.println();

  // Initialize Flash LED
  pinMode(FLASH_GPIO_NUM, OUTPUT);
  digitalWrite(FLASH_GPIO_NUM, LOW);

  // Camera Configuration
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;

  // Use PSRAM for better resolution
  if(psramFound()){
    config.frame_size = FRAMESIZE_VGA; // 640x480
    config.jpeg_quality = 10;
    config.fb_count = 2;
  } else {
    config.frame_size = FRAMESIZE_SVGA;
    config.jpeg_quality = 12;
    config.fb_count = 1;
  }

  // Init Camera
  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed: 0x%x", err);
    return;
  }

  // Sensor fine-tuning for Auto-Exposure
  sensor_t * s = esp_camera_sensor_get();
  s->set_brightness(s, 0);     
  s->set_contrast(s, 0);       
  s->set_whitebal(s, 1);       
  s->set_exposure_ctrl(s, 1);  
  s->set_gain_ctrl(s, 1);      

  // Connect WiFi
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi Connected!");
}

void loop() {
  takeAndSendPhoto();
  
  // Every 10 minutes (600,000 milliseconds)
  Serial.println("System entering standby for 10 minutes...");
  delay(30000); 
}

void takeAndSendPhoto() {
  // 1. ENSURE WIFI IS READY BUT IDLE
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi lost. Reconnecting...");
    return;
  }

  // 2. TURN ON FLASH
  digitalWrite(FLASH_GPIO_NUM, HIGH);
  Serial.println("Flash ON. Stabilizing...");
  
  // 3. AGGRESSIVE STABILIZATION
  // We wait 2 seconds for the light to be steady
  delay(2000); 

  // 4. SENSOR TUNING (Force high gain for dark environments)
  sensor_t * s = esp_camera_sensor_get();
  s->set_agc_gain(s, 30);      // Max gain boost
  s->set_aec_value(s, 1200);   // Force longer exposure time

  // 5. TRIPLE BUFFER FLUSH
  for (int i = 0; i < 3; i++) {
    camera_fb_t * fb_trash = esp_camera_fb_get();
    if (fb_trash) esp_camera_fb_return(fb_trash);
    delay(100);
  }

  // 6. THE ACTUAL CAPTURE
  Serial.println("Capturing now...");
  camera_fb_t * fb = esp_camera_fb_get();
  
  // 7. FLASH OFF IMMEDIATELY
  // We do this BEFORE the network starts working again
  digitalWrite(FLASH_GPIO_NUM, LOW);
  Serial.println("Flash OFF.");

  if (!fb) {
    Serial.println("Capture failed");
    return;
  }

  // 8. DATA TRANSMISSION (Now WiFi can use all the power)
  Serial.println("Starting network transmission...");
  HTTPClient http;
  
  // Increase timeout for your poor WiFi
  http.setTimeout(15000); // 15 seconds
  
  http.begin(serverUrl);
  http.addHeader("Content-Type", "image/jpeg");
  http.addHeader("X-API-Key", apiKey);
  
  int httpResponseCode = http.POST(fb->buf, fb->len);
  
  if (httpResponseCode > 0) {
    Serial.printf("Server Response: %d\n", httpResponseCode);
  } else {
    Serial.printf("Network Error: %s\n", http.errorToString(httpResponseCode).c_str());
  }

  http.end();
  esp_camera_fb_return(fb);
}
