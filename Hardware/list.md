# Hardware list
ESP32-WROOM32主控板
LU9685控制板
ST7789显示屏
SG90舵机*4
5V恒压锂电池

# Connect
# ESP32,ST7789
ST7789    ESP32
-----------------
VCC       3.3V
GND       GND
SCL       GPIO18
SDA       GPIO23
RES       GPIO15
DC        GPIO2
CS        GPIO5 (如果使用)
BLK       GPIO4 (背光控制，可选)
# ESP32,LU9685
TX,RX