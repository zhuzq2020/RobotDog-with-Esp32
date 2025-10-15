#include <WiFi.h>
#include <WiFiClient.h>
#include <WiFiServer.h>
#include <Adafruit_GFX.h>
#include <Adafruit_ST7789.h>
#include <NTPClient.h>
#include <WiFiUdp.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>

// WiFi配置
const char* ssid = "ChinaNet-Wxjp";
const char* password = "Gyxc0927";
WiFiServer server(8080);

WiFiUDP ntpUDP;
NTPClient timeClient(ntpUDP, "pool.ntp.org", 8 * 3600, 60000); // 北京时间，1分钟更新一次

// 天气API配置
const String weatherAPIKey = "5b222384d5c142a39022a2eeb2458784"; // 替换为您的天气API密钥
const String city = "101020100"; // 替换为您的城市
String currentWeather = "Loading...";
String currentTemp = "--";
unsigned long lastWeatherUpdate = 0;
const unsigned long weatherUpdateInterval = 600000; // 10分钟更新一次天气

// 显示模式变量
String currentDisplayMode = "SERVO_STATUS"; // SERVO_STATUS, CLOCK, WEATHER

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
    tft.setCursor(50, 10);
    tft.println("Servo Monitor");
    tft.println("====================");

    // 显示IP地址
    tft.setCursor(10, 60);
    tft.setTextSize(1);
    tft.printf("IP: %s", WiFi.localIP().toString().c_str());
    
    for (int i = 0; i < SERVO_COUNT; i++) {
        tft.setCursor(10, 90 + i * 25);
        tft.printf("  %d    %3d", i, currentAngles[i]);
        
        // 绘制角度条
        int barWidth = map(currentAngles[i], 0, 180, 0, 100);
        tft.fillRect(80, 90 + i * 25, barWidth, 15, ST77XX_BLUE);
        tft.drawRect(80, 90 + i * 25, 100, 15, ST77XX_WHITE);
    }
    
    tft.setTextSize(1);
    tft.setCursor(10, 200);
    tft.println("MADE BY ZHUZQ");
}

// 新增表情显示函数
// 修改后的表情显示函数
void displayExpression(String expressionType) {
    tft.fillScreen(ST77XX_BLACK);
    tft.setTextColor(ST77XX_WHITE);
    tft.setTextSize(3);
    tft.setCursor(70, 100); // 居中显示
    
    if (expressionType == "SMILEY") {
        // 绘制笑脸 - 使用库支持的方法
        tft.fillCircle(120, 120, 50, ST77XX_YELLOW); // 脸
        tft.fillCircle(100, 110, 5, ST77XX_BLACK);   // 左眼
        tft.fillCircle(140, 110, 5, ST77XX_BLACK);   // 右眼
        
        // 替换drawArc: 使用fillCircle和fillRect组合绘制微笑的嘴
        tft.fillCircle(120, 130, 20, ST77XX_YELLOW);  // 用脸的颜色覆盖上半部分
        tft.fillRect(100, 130, 40, 20, ST77XX_YELLOW); // 覆盖上半部分，留下微笑
        tft.fillCircle(120, 130, 15, ST77XX_BLACK);  // 绘制微笑的底部
        
        tft.setCursor(85, 190);
        tft.setTextSize(2);
        tft.println("^_^");
    } 
    else if (expressionType == "CRYING") {
        // 绘制哭泣表情
        tft.fillCircle(120, 120, 50, ST77XX_BLUE);
        tft.fillCircle(100, 110, 5, ST77XX_BLACK);
        tft.fillCircle(140, 110, 5, ST77XX_BLACK);
        
        // 替换drawArc: 使用直线绘制向下的嘴
        for (int i = 0; i < 5; i++) {
            tft.drawLine(110 + i*5, 140, 110 + i*5, 145, ST77XX_BLACK);
        }
        
        // 添加泪滴
        tft.fillTriangle(105, 160, 100, 175, 110, 175, ST77XX_CYAN);
        tft.fillTriangle(135, 160, 130, 175, 140, 175, ST77XX_CYAN);
        tft.setCursor(85, 190);
        tft.setTextSize(2);
        tft.println("T_T");
    }
    else if (expressionType == "SLEEPY") {
        // 绘制发呆/困倦表情
        tft.fillCircle(120, 120, 50, ST77XX_GREEN);
        tft.drawLine(95, 110, 105, 110, ST77XX_BLACK); // 眯着的左眼
        tft.drawLine(135, 110, 145, 110, ST77XX_BLACK); // 眯着的右眼
        
        // 替换drawArc: 使用小矩形绘制小嘴
        tft.fillRect(115, 130, 10, 3, ST77XX_BLACK);
        
        tft.setCursor(85, 190);
        tft.setTextSize(2);
        tft.println("-_-");
    }
    // 可以继续添加其他表情...
    
    // 在屏幕底部显示当前模式
    tft.setTextSize(1);
    tft.setCursor(10, 220);
    tft.print("Mode: ");
    tft.print(expressionType);
}

// 获取天气信息函数
void updateWeather() {
    if (WiFi.status() == WL_CONNECTED) {
        HTTPClient http;
        String url = "https://devapi.qweather.com/v7/weather/now?key=" + weatherAPIKey + "&location=" + city;
        
        http.begin(url);
        int httpCode = http.GET();
        
        if (httpCode == 200) {
            String payload = http.getString();
            DynamicJsonDocument doc(1024);
            deserializeJson(doc, payload);
            
            String weather = doc["now"]["text"].as<String>();
            String tempStr = doc["now"]["temp"].as<String>();
            
            currentWeather = "Weather: " + weather;
            currentTemp = "Tempearture: " + tempStr; // 和风天气返回的是整数温度
            lastWeatherUpdate = millis();
        }
        http.end();
    }
}

// 时钟显示函数
void displayClock() {
    tft.fillScreen(ST77XX_BLACK);
    tft.setTextColor(ST77XX_WHITE);
    
    // 显示时间
    tft.setTextSize(4);
    tft.setCursor(30, 80);
    tft.println(timeClient.getFormattedTime().substring(0, 5));
    
    // 显示日期
    tft.setTextSize(2);
    tft.setCursor(40, 140);
    
    // 获取并格式化日期
    time_t epochTime = timeClient.getEpochTime();
    struct tm *ptm = gmtime((time_t *)&epochTime);
    String date = String(ptm->tm_year+1900) + "/" + String(ptm->tm_mon+1) + "/" + String(ptm->tm_mday);
    tft.println(date);
    
    // 显示星期
    String weekDays[] = {"Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"};
    String weekDay = weekDays[timeClient.getDay()];
    tft.setCursor(50, 170);
    tft.println(weekDay);
}

// 天气显示函数
void displayWeather() {
    tft.fillScreen(ST77XX_BLACK);
    tft.setTextColor(ST77XX_WHITE);
    
    // 显示城市
    tft.setTextSize(2);
    tft.setCursor(60, 50);
    tft.println("Shanghai");
    
    // 显示温度
    tft.setTextSize(2);
    tft.setCursor(20, 90);
    tft.println(currentTemp);
    
    // 显示天气状况
    tft.setTextSize(2);
    tft.setCursor(40, 140);
    tft.println(currentWeather);
    
    // 显示更新时间
    tft.setTextSize(1);
    tft.setCursor(10, 220);
    tft.println("Last update: " + String((millis() - lastWeatherUpdate) / 60000) + " min ago");
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
    tft.setCursor(10, 30);
    tft.println("Connecting to WiFi");
    
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

    // 初始化NTP客户端
    timeClient.begin();
    timeClient.update();
    
    // 首次获取天气
    updateWeather();
}

void processCommand(String command) {
    if (command == "MODE_CLOCK") {
        currentDisplayMode = "CLOCK";
        displayClock();
        return;
    }
    
    if (command == "MODE_WEATHER") {
        currentDisplayMode = "WEATHER";
        updateWeather(); // 立即更新天气
        displayWeather();
        return;
    }
    
    if (command == "MODE_STATUS") {
        currentDisplayMode = "SERVO_STATUS";
        updateDisplay();
        return;
    }
    
    if (command == "RESET") {
        softReset();
        updateDisplay();
        return;
    }

    if (command.startsWith("EXPRESSION,")) {
        String expressionType = command.substring(11); // 提取"EXPRESSION,"后面的部分
        displayExpression(expressionType);
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
        // updateDisplay();
    } else {
        int commaPos = command.indexOf(',');
        if (commaPos != -1) {
            uint8_t channel = command.substring(0, commaPos).toInt();
            uint8_t angle = command.substring(commaPos + 1).toInt();
            
            if (channel < SERVO_COUNT) {
                sendToLU9685(channel, angle);
                // updateDisplay();
            }
        }
    }
}

void loop() {
    // 更新时间客户端
    timeClient.update();
    
    // 定期更新天气（每10分钟）
    if (millis() - lastWeatherUpdate > weatherUpdateInterval) {
        updateWeather();
    }
    
    // 根据当前显示模式自动更新显示
    if (currentDisplayMode == "CLOCK") {
        static unsigned long lastClockUpdate = 0;
        if (millis() - lastClockUpdate > 1000) { // 每秒更新一次时钟
            displayClock();
            lastClockUpdate = millis();
        }
    }

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