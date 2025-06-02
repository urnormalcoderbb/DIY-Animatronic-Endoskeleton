from machine import I2C, Pin
import time

# PCA9685 MicroPython driver
class PCA9685:
    def __init__(self, i2c, address=0x40):
        self.i2c = i2c
        self.address = address
        self.reset()
        self.set_pwm_freq(50)

    def reset(self):
        self.i2c.writeto_mem(self.address, 0x00, b'\x00')

    def set_pwm_freq(self, freq_hz):
        prescale_val = int(round(25000000.0 / (4096 * freq_hz)) - 1)
        old_mode = self.i2c.readfrom_mem(self.address, 0x00, 1)
        self.i2c.writeto_mem(self.address, 0x00, bytes([(old_mode[0] & 0x7F) | 0x10]))  # sleep
        self.i2c.writeto_mem(self.address, 0xFE, bytes([prescale_val]))
        self.i2c.writeto_mem(self.address, 0x00, old_mode)
        time.sleep_ms(5)
        self.i2c.writeto_mem(self.address, 0x00, bytes([old_mode[0] | 0xa1]))  # auto-increment on

    def set_pwm(self, channel, on, off):
        data = bytearray([
            on & 0xFF,
            (on >> 8) & 0xFF,
            off & 0xFF,
            (off >> 8) & 0xFF
        ])
        self.i2c.writeto_mem(self.address, 0x06 + 4 * channel, data)

    def set_servo_angle(self, channel, angle, min_us=500, max_us=2500):
        # Map angle (0-180) to pulse length
        us = min_us + (max_us - min_us) * angle // 180
        pulse_len = int(us * 4096 / 20000)  # 20ms period for 50Hz
        self.set_pwm(channel, 0, pulse_len)

# --- Main setup ---

# ESP32 default I2C pins: sda=21, scl=22
i2c = I2C(0, sda=Pin(21), scl=Pin(22))
pca = PCA9685(i2c)

NUM_SERVOS = 10

while True:
    # Sweep forward
    for angle in range(0, 181, 5):
        for ch in range(NUM_SERVOS):
            pca.set_servo_angle(ch, angle)
        time.sleep_ms(20)
    # Sweep backward
    for angle in range(180, -1, -5):
        for ch in range(NUM_SERVOS):
            pca.set_servo_angle(ch, angle)
        time.sleep_ms(20)