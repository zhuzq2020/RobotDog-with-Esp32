#include <WiFi.h>
#include <WiFiClient.h>
#include <WiFiServer.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>

// WiFi配置
const char* ssid = "ChinaNet-Wxjp";
const char* password = "Gyxc0927";
WiFiServer server(8080);

// TFT显示屏配置
#define TFT_CS   5
#define TFT_DC   2
#define TFT_RST  15
#define TFT_BL   4
Adafruit_ST7789 tft = Adafruit_ST7789(TFT_CS, TFT_DC, TFT_RST);

// LU9685配置
#define SERVO_COUNT 4  // 只使用4路舵机
uint8_t currentAngles[SERVO_COUNT] = {90, 90, 90, 90}; // 存储当前角度

// 简化的LU9685控制函数
void sendToLU9685(uint8_t channel, uint8_t angle) {
    if (channel >= SERVO_COUNT) return;
    
    uint8_t cmd[] = {0xFA, 0x00, channel, angle, 0xFE};
    Serial2.write(cmd, sizeof(cmd));
    currentAngles[channel] = angle;
}

void sendAllToLU9685(uint8_t angles[]) {
    uint8_t cmd[24] = {0xFA, 0x00, 0xFD};  // 正确的命令头：0xFA + 地址0x00 + 0xFD
    
    for (int i = 0; i < 20; i++) {
        if (i < SERVO_COUNT) {
            cmd[i + 3] = angles[i];  // 从第4个字节开始是角度数据
            currentAngles[i] = angles[i];
        } else {
            cmd[i + 3] = 201; // 未使用的通道设为关闭
        }
    }
    cmd[23] = 0xFE;  // 命令尾
    
    Serial2.write(cmd, 24);  // 总共24字节
}

void softReset() {
    uint8_t cmd[] = {0xFA, 0x00, 0xFB, 0xFB, 0xFE};
    Serial2.write(cmd, sizeof(cmd));
    
    // 重置角度记录
    for (int i = 0; i < SERVO_COUNT; i++) {
        currentAngles[i] = 90;
    }
}

// 显示函数
void updateDisplay() {
    tft.fillScreen(ST77XX_BLACK);
    tft.setTextColor(ST77XX_WHITE);
    tft.setTextSize(2);
    
    tft.setCursor(10, 10);
    tft.println("ServoStatusMonitor");
    tft.println("==================");
    
    tft.setTextSize(1);
    tft.setCursor(10, 60);
    tft.println("Channel Angle");
    tft.println("-------  -----");
    
    for (int i = 0; i < SERVO_COUNT; i++) {
        tft.setCursor(10, 90 + i * 25);
        tft.printf("  %d    %3d", i, currentAngles[i]);
        
        // 绘制角度条
        int barWidth = map(currentAngles[i], 0, 180, 0, 100);
        tft.fillRect(80, 90 + i * 25, barWidth, 15, ST77XX_BLUE);
        tft.drawRect(80, 90 + i * 25, 100, 15, ST77XX_WHITE);
    }
    
    // 显示IP地址
    tft.setCursor(10, 200);
    tft.setTextSize(1);
    tft.printf("IP: %s", WiFi.localIP().toString().c_str());
}

void setup() {
    Serial.begin(115200);
    Serial2.begin(9600, SERIAL_8N1, 16, 17); // RX=16, TX=17
    
    // 初始化TFT显示屏
    pinMode(TFT_BL, OUTPUT);
    digitalWrite(TFT_BL, HIGH);
    tft.init(240, 240);
    tft.setRotation(2);
    
    // 连接WiFi
    WiFi.begin(ssid, password);
    tft.fillScreen(ST77XX_BLACK);
    tft.setTextColor(ST77XX_WHITE);
    tft.setTextSize(2);
    tft.setCursor(10, 10);
    tft.println("Connect to WiFi...");
    
    while (WiFi.status() != WL_CONNECTED) {
        delay(1000);
        Serial.println("Connecting to WiFi...");
    }
    
    // 启动TCP服务器
    server.begin();
    
    // 初始化舵机控制器
    softReset();
    
    // 更新显示
    updateDisplay();
    
    Serial.println("Server started on port 8080");
}

void processCommand(String command) {
    if (command == "RESET") {
        softReset();
        updateDisplay();
        return;
    }
    
    if (command.startsWith("ALL,")) {
        uint8_t angles[20] = {201}; // 默认关闭所有通道
        
        int startPos = 4;
        for (int i = 0; i < SERVO_COUNT; i++) {
            int commaPos = command.indexOf(',', startPos);
            if (commaPos == -1) commaPos = command.length();
            
            String angleStr = command.substring(startPos, commaPos);
            angles[i] = angleStr.toInt();
            startPos = commaPos + 1;
        }
        
        sendAllToLU9685(angles);
        updateDisplay();
    } else {
        int commaPos = command.indexOf(',');
        if (commaPos != -1) {
            uint8_t channel = command.substring(0, commaPos).toInt();
            uint8_t angle = command.substring(commaPos + 1).toInt();
            
            if (channel < SERVO_COUNT) {
                sendToLU9685(channel, angle);
                updateDisplay();
            }
        }
    }
}

void loop() {
    WiFiClient client = server.available();
    
    if (client) {
        Serial.println("Client connected");
        
        while (client.connected()) {
            if (client.available()) {
                String command = client.readStringUntil('\n');
                command.trim();
                
                Serial.print("Received: ");
                Serial.println(command);
                
                processCommand(command);
                
                // 发送响应
                client.println("OK");
            }
        }
        
        client.stop();
        Serial.println("Client disconnected");
    }
}