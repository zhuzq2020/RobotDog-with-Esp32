#ifndef LU9685_H
#define LU9685_H

#include <Arduino.h>

class LU9685 {
private:
    HardwareSerial* serial;
    uint8_t addr;
    
public:
    LU9685(HardwareSerial* ser, uint8_t address = 0x00);
    
    void begin(unsigned long baud = 9600);
    void softReset();
    void setServoAngle(uint8_t channel, uint8_t angle);
    void setAllServos(uint8_t angles[]);
    void disableServo(uint8_t channel);
    void disableAllServos();
};

#endif