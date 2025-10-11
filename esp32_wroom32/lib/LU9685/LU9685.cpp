#include "LU9685.h"

LU9685::LU9685(HardwareSerial* ser, uint8_t address) {
    serial = ser;
    addr = address;
}

void LU9685::begin(unsigned long baud) {
    serial->begin(baud, SERIAL_8N1);
}

void LU9685::softReset() {
    uint8_t cmd[] = {0xFA, addr, 0xFB, 0xFB, 0xFE};
    serial->write(cmd, sizeof(cmd));
}

void LU9685::setServoAngle(uint8_t channel, uint8_t angle) {
    if (channel > 19) return;
    uint8_t cmd[] = {0xFA, addr, channel, angle, 0xFE};
    serial->write(cmd, sizeof(cmd));
}

void LU9685::setAllServos(uint8_t angles[]) {
    uint8_t cmd[23] = {0xFD};
    
    for (int i = 0; i < 20; i++) {
        cmd[i + 1] = angles[i];
    }
    cmd[21] = 0xFE;
    
    serial->write(cmd, 22);
}

void LU9685::disableServo(uint8_t channel) {
    setServoAngle(channel, 201); // 大于200表示关闭PWM
}

void LU9685::disableAllServos() {
    uint8_t angles[20];
    for (int i = 0; i < 20; i++) {
        angles[i] = 201;
    }
    setAllServos(angles);
}