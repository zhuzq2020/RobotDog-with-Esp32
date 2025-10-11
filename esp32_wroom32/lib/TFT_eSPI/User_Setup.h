// 选择驱动芯片
#define ST7789_DRIVER

// 设置屏幕尺寸（1.54寸IPS通常是240x240）
#define TFT_WIDTH  240
#define TFT_HEIGHT 240

// 配置ESP32引脚
#define TFT_CS   5   // 片选引脚
#define TFT_DC   2   // 数据/命令选择
#define TFT_RST  15  // 复位引脚
#define TFT_BL   4   // 背光控制引脚

// 配置SPI引脚
#define TFT_MOSI 23  // SPI数据线
#define TFT_SCLK 18  // SPI时钟线

// 设置SPI频率
#define SPI_FREQUENCY 27000000  // 27MHz

// 加载所需字体
#define LOAD_GLCD   // 标准字体
#define LOAD_FONT2  // 小字体
#define LOAD_FONT4  // 中等字体[1](@ref)