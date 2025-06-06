import network
import espnow
import ujson
import time
from machine import Pin, I2C

# --- PCA9685 Constants ---
MODE1 = 0x00
PRESCALE = 0xFE
LED0_ON_L = 0x06
PCA_ADDR = 0x40

# Servo channel definitions
EYE_H, EYE_V, EYE_BLINK, NECK_LR, NECK_UD = 0, 1, 2, 3, 4
JAW, TORSO, WAVE1, WAVE2, W 5, 6, 7, 8, 9

# --- I2C/PCA9685 Setup ---
i2c = I2C(0, scl=Pin(22), sda=Pin(21))

def pca_write(addr, value):
    try:
        i2c.writeto_mem(PCA_ADDR, addr, bytes([value]))
    except OSError as e:
        print(f"PCA write error: {e}")

def set_pwm(channel, on, off):
    if 0 <= channel <= 15:
        base = LED0_ON_L + 4 * channel
        try:
            i2c.writeto_mem(PCA_ADDR, base, bytes([on & 0xFF]))
            i2c.writeto_mem(PCA_ADDR, base + 1, bytes([on >> 8]))
            i2c.writeto_mem(PCA_ADDR, base + 2, bytes([off & 0xFF]))
            i2c.writeto_mem(PCA_ADDR, base + 3, bytes([off >> 8]))
        except OSError as e:
            print(f"PWM set error on channel {channel}: {e}")
    else:
        print(f"Invalid channel: {channel}")

def set_servo_angle(channel, angle):
    angle = max(0, min(180, angle))
    us = 500 + (angle * 2000) // 180
    duty = int(us * 4096 // 20000)
    set_pwm(channel, 0, duty)

def init_pca9685():
    try:
        print("Checking for PCA9685 servo controller...")
        i2c.readfrom_mem(PCA_ADDR, MODE1, 1)
        print(f"PCA9685 found at address 0x{PCA_ADDR:02X}")
        pca_write(MODE1, 0x10)
        time.sleep_ms(10)
        pca_write(PRESCALE, 0x79)
        pca_write(MODE1, 0x00)
        time.sleep_ms(5)
        pca_write(MODE1, 0xA1)
        print("PCA9685 initialized (10 channels ready)")
        return True
    except OSError as e:
        print("ERROR: PCA9685 not found!" if getattr(e, "errno", None) == 19
              else f"I2C communication error: {e}")
        print("Check I2C connections (SDA=21, SCL=22) and power supply")
        return False
    except Exception as e:
        print(f"PCA9685 initialization failed: {e}")
        return False

def stop_all_servos():
    print("Setting all servos to neutral position...")
    for ch in range(10):
        set_servo_angle(ch, 90)
    print("All 10 servos stopped successfully")

# --- Non-blocking Wave Animation State ---
wave_active = False
wave_step = 0
wave_last_time = time.ticks_ms()
wave_in_progress = False

def wave_animate():
    # 0: Reset to neutral, 1: wave pose A, 2: wave pose B, repeat
    global wave_step, wave_last_time, wave_active, wave_in_progress
    interval = 200  # ms
    if not wave_active:
        if wave_in_progress:
            # Ensure always return to neutral at end
            set_servo_angle(WAVE1, 90)
            set_servo_angle(WAVE2, 90)
            set_servo_angle(WAVE3, 90)
            wave_in_progress = False
        return
    now = time.ticks_ms()
    if time.ticks_diff(now, wave_last_time) >= interval:
        if wave_step == 0:
            set_servo_angle(WAVE1, 60)
            set_servo_angle(WAVE2, 120)
            set_servo_angle(WAVE3, 90)
        elif wave_step == 1:
            set_servo_angle(WAVE1, 120)
            set_servo_angle(WAVE2, 60)
            set_servo_angle(WAVE3, 90)
        wave_last_time = now
        wave_step = (wave_step + 1) % 2
        wave_in_progress = True

# --- Non-repeating blink ---
blink_active = False
blink_last_time = 0

def blink_animate():
    global blink_active, blink_last_time
    now = time.ticks_ms()
    if blink_active:
        # After 150ms, open eyelid
        if time.ticks_diff(now, blink_last_time) > 150:
            set_servo_angle(EYE_BLINK, 90)
            blink_active = False

def perform_blink():
    global blink_active, blink_last_time
    if not blink_active:
        set_servo_angle(EYE_BLINK, 0)
        blink_last_time = time.ticks_ms()
        blink_active = True

def init_wifi_espnow():
    try:
        w0 = network.WLAN(network.STA_IF)
        w0.active(True)
        e = espnow.ESPNow()
        e.active(True)
        e.add_peer(b'\xFF\xFF\xFF\xFF\xFF\xFF')
        print("ESP-NOW initialized successfully")
        return e
    except Exception as ex:
        print(f"ESP-NOW initialization failed: {ex}")
        return None

# --- Initialization ---
print("Starting servo controller...")
print("Scanning I2C bus for devices...")

# --- Emergency stop fallback ---
def hardware_emergency_fallback():
    print("HARDWARE EMERGENCY STOP ACTIVATED! Attempting forced neutral pose.")
    for _ in range(5):
        stop_all_servos()
        time.sleep_ms(100)
    print("Hardware fallback attempted.")

# Try PCA9685 repeatedly but not forever
pca_attempts = 0
while not init_pca9685():
    pca_attempts += 1
    print("CRITICAL: Failed to initialize PCA9685 servo controller")
    print("System cannot operate without servo controller")
    for _ in range(5):
        time.sleep(1)
        print("Retrying PCA9685 initialization...")
    if pca_attempts >= 5:
        hardware_emergency_fallback()
        raise SystemExit

# Startup pose: set all servos to neutral
stop_all_servos()

e = init_wifi_espnow()
if e is None:
    print("Failed to initialize ESP-NOW - exiting")
    hardware_emergency_fallback()
    raise SystemExit

jaw_open = emergency_stop = False
last_heartbeat = time.ticks_ms()

print("Servo controller ready - waiting for commands...")

# --- Main control loop ---
while True:
    try:
        # Non-blocking animation steps
        wave_animate()
        blink_animate()

        host, msg = e.recv()
        now = time.ticks_ms()

        # Heartbeat timeout
        if not msg:
            if time.ticks_diff(now, last_heartbeat) > 4000 and not emergency_stop:
                print("Lost heartbeat — stopping servos")
                stop_all_servos()
                emergency_stop = True
                hardware_emergency_fallback()
            time.sleep_ms(10)
            continue

        try:
            controls = ujson.loads(msg)
        except Exception as e:
            print(f"JSON decode error: {e}")
            continue

        if controls.get("heartbeat"):
            last_heartbeat = now
            if emergency_stop:
                print("Heartbeat received - system still in emergency stop")
            continue

        if controls.get("emergency_stop"):
            print("EMERGENCY STOP ACTIVATED")
            emergency_stop = True
            stop_all_servos()
            hardware_emergency_fallback()
            continue

        if controls.get("unlock"):
            print("UNLOCK RECEIVED - System ready")
            emergency_stop = False
            continue

        if emergency_stop:
            continue

        # Servo controls
        for field, channel in [
            ("eye_h", EYE_H), ("eye_v", EYE_V),
            ("neck_lr", NECK_LR), ("neck_ud", NECK_UD),
            ("torso_rot", TORSO)
        ]:
            if field in controls:
                set_servo_angle(channel, controls[field])

        # Blinking (prevent repeated triggers)
        if controls.get("eye_blink"):
            perform_blink()

        # Non-blocking wave: set flag only
        if "wave_active" in controls:
            wave_active = controls["wave_active"]

        if "jaw_open" in controls:
            jaw_open = controls["jaw_open"]
            set_servo_angle(JAW, 30 if jaw_open else 90)

    except OSError as e:
        print(f"Communication error: {e}")
        time.sleep(0.1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        stop_all_servos()
        hardware_emergency_fallback()
        emergency_stop = True
        time.sleep(1)