
# receiver.py (ESP-NOW + PCA9685 direct control)
import time
import ujson
from machine import Pin, I2C, PWM
import espnow
import network

# Servo control
class PCA9685:
    def __init__(self, i2c, address=0x40):
        self.i2c = i2c
        self.address = address
        self.i2c.writeto_mem(address, 0x00, b'\x00')
        self.set_pwm_freq(50)

    def set_pwm_freq(self, freq):
        prescale_val = int(25000000.0 / (4096 * freq) - 1)
        self.i2c.writeto_mem(self.address, 0x00, b'\x10')
        self.i2c.writeto_mem(self.address, 0xFE, bytes([prescale_val]))
        self.i2c.writeto_mem(self.address, 0x00, b'\xA1')

    def set_pwm(self, channel, on, off):
        reg = 0x06 + 4 * channel
        data = bytes([on & 0xFF, on >> 8, off & 0xFF, off >> 8])
        self.i2c.writeto_mem(self.address, reg, data)

    def set_servo_angle(self, channel, angle):
        pulse = int(4096 * ((angle * 11 + 500) / 20000))
        self.set_pwm(channel, 0, pulse)

# Setup I2C
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
pca = PCA9685(i2c)

# Servo channels
EYE_H = 0
EYE_V = 1
EYE_BLINK = 2
NECK_LR = 3
NECK_UD = 4
JAW = 5
TORSO = 6
WAVE1 = 7
WAVE2 = 8
WAVE3 = 9

# ESP-NOW setup
w0 = network.WLAN(network.STA_IF)
w0.active(True)
e = espnow.ESPNow()
e.active(True)
e.recv_cb(None)

# State
wave_active = False
jaw_open = False
emergency_stop = False
last_heartbeat = time.ticks_ms()

def stop_all_servos():
    for ch in range(10):
        pca.set_servo_angle(ch, 90)

stop_all_servos()

# Main loop
while True:
    host, msg = e.irecv()
    if msg:
        try:
            controls = ujson.loads(msg)

            if controls.get("heartbeat"):
                last_heartbeat = time.ticks_ms()
                continue

            if controls.get("unlock"):
                emergency_stop = False
                continue

            if controls.get("emergency_stop"):
                emergency_stop = True
                stop_all_servos()
                continue

            if emergency_stop:
                continue

            # Eyes and neck
            pca.set_servo_angle(EYE_H, controls.get("eye_h", 90))
            pca.set_servo_angle(EYE_V, controls.get("eye_v", 90))
            pca.set_servo_angle(NECK_LR, controls.get("neck_lr", 90))
            pca.set_servo_angle(NECK_UD, controls.get("neck_ud", 90))
            pca.set_servo_angle(TORSO, controls.get("torso_rot", 90))

            if controls.get("eye_blink"):
                pca.set_servo_angle(EYE_BLINK, 0)
                time.sleep(0.15)
                pca.set_servo_angle(EYE_BLINK, 90)

            if controls.get("wave_active") is not None:
                wave_active = controls["wave_active"]
                if wave_active:
                    for _ in range(3):
                        pca.set_servo_angle(WAVE1, 60)
                        pca.set_servo_angle(WAVE2, 120)
                        pca.set_servo_angle(WAVE3, 90)
                        time.sleep(0.2)
                        pca.set_servo_angle(WAVE1, 120)
                        pca.set_servo_angle(WAVE2, 60)
                        pca.set_servo_angle(WAVE3, 90)
                        time.sleep(0.2)
                    pca.set_servo_angle(WAVE1, 90)
                    pca.set_servo_angle(WAVE2, 90)
                    pca.set_servo_angle(WAVE3, 90)

            if controls.get("jaw_open") is not None:
                jaw_open = controls["jaw_open"]
                pca.set_servo_angle(JAW, 30 if jaw_open else 90)

            # Heartbeat timeout
            if time.ticks_diff(time.ticks_ms(), last_heartbeat) > 4000:
                stop_all_servos()
                emergency_stop = True

        except Exception as e:
            print("Error:", e)
            stop_all_servos()
            emergency_stop = True
