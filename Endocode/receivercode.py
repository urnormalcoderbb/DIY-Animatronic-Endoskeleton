import network
import espnow
import ujson
import time
from machine import Pin, I2C

# PCA9685 Registers
MODE1 = 0x00
PRESCALE = 0xFE
LED0_ON_L = 0x06

# Initialize I2C and PCA9685
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
PCA_ADDR = 0x40

def pca_write(addr, value):
    """Write a single byte to PCA9685 register"""
    try:
        i2c.writeto_mem(PCA_ADDR, addr, bytes([value]))
    except OSError as e:
        print(f"PCA write error: {e}")
        raise

def set_pwm(channel, on, off):
    """Set PWM values for a specific channel"""
    if channel < 0 or channel > 15:
        print(f"Invalid channel: {channel}")
        return
    
    try:
        base = LED0_ON_L + 4 * channel
        i2c.writeto_mem(PCA_ADDR, base, bytes([on & 0xFF]))
        i2c.writeto_mem(PCA_ADDR, base + 1, bytes([on >> 8]))
        i2c.writeto_mem(PCA_ADDR, base + 2, bytes([off & 0xFF]))
        i2c.writeto_mem(PCA_ADDR, base + 3, bytes([off >> 8]))
    except OSError as e:
        print(f"PWM set error on channel {channel}: {e}")

def set_servo_angle(channel, angle):
    """Set servo angle (0-180 degrees)"""
    if angle < 0 or angle > 180:
        print(f"Invalid angle: {angle}. Must be 0-180")
        angle = max(0, min(180, angle))  # Clamp to valid range
    
    # Convert angle to microseconds (500-2500us for 0-180 degrees)
    us = 500 + (angle * 2000) // 180
    # Convert to duty cycle value (0-4095 for 20ms period)
    duty = int(us * 4096 // 20000)
    set_pwm(channel, 0, duty)

def init_pca9685():
    """Initialize PCA9685 with proper error handling"""
    try:
        # Check if PCA9685 is connected by reading a register
        print("Checking for PCA9685 servo controller...")
        test_read = i2c.readfrom_mem(PCA_ADDR, MODE1, 1)
        print(f"PCA9685 found at address 0x{PCA_ADDR:02X}")
        
        # Reset
        pca_write(MODE1, 0x10)  # Sleep mode
        time.sleep_ms(10)  # Wait for oscillator
        
        # Set prescaler for 50Hz (servo frequency)
        pca_write(PRESCALE, 0x79)  # 50Hz prescaler value
        
        # Wake up and enable auto-increment
        pca_write(MODE1, 0x00)  # Normal mode
        time.sleep_ms(5)
        pca_write(MODE1, 0xA1)  # Auto-increment enabled
        
        print("PCA9685 servo controller initialized successfully")
        print("10 servo channels ready")
        return True
    except OSError as e:
        if e.errno == 19:  # ENODEV - No such device
            print("ERROR: PCA9685 servo controller not found!")
            print("Check I2C connections (SDA=21, SCL=22)")
            print("Verify PCA9685 power supply")
        else:
            print(f"I2C communication error: {e}")
        return False
    except Exception as e:
        print(f"PCA9685 initialization failed: {e}")
        return False

# Servo channel definitions
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

def init_wifi_espnow():
    """Initialize Wi-Fi and ESP-NOW with error handling"""
    try:
        w0 = network.WLAN(network.STA_IF)
        w0.active(True)
        
        e = espnow.ESPNow()
        e.active(True)
        e.add_peer(b'\xFF\xFF\xFF\xFF\xFF\xFF')  # Accept broadcast
        
        print("ESP-NOW initialized successfully")
        return e
    except Exception as ex:
        print(f"ESP-NOW initialization failed: {ex}")
        return None

def stop_all_servos():
    """Stop all servos by setting them to neutral position"""
    try:
        print("Setting all servos to neutral position...")
        for ch in range(10):
            set_servo_angle(ch, 90)
        print("✓ All 10 servos stopped successfully")
    except Exception as e:
        print(f"✗ Error stopping servos: {e}")
        print("Some servos may still be active!")

def perform_wave_sequence():
    """Perform waving animation sequence"""
    try:
        for _ in range(3):
            set_servo_angle(WAVE1, 60)
            set_servo_angle(WAVE2, 120)
            set_servo_angle(WAVE3, 90)
            time.sleep(0.2)
            set_servo_angle(WAVE1, 120)
            set_servo_angle(WAVE2, 60)
            set_servo_angle(WAVE3, 90)
            time.sleep(0.2)
        
        # Return to neutral
        set_servo_angle(WAVE1, 90)
        set_servo_angle(WAVE2, 90)
        set_servo_angle(WAVE3, 90)
    except Exception as e:
        print(f"Wave sequence error: {e}")

def perform_blink():
    """Perform eye blink animation"""
    try:
        set_servo_angle(EYE_BLINK, 0)
        time.sleep(0.15)
        set_servo_angle(EYE_BLINK, 90)
    except Exception as e:
        print(f"Blink error: {e}")

# Main initialization
print("Starting servo controller...")
print("Scanning I2C bus for devices...")

if not init_pca9685():
    print("CRITICAL: Failed to initialize PCA9685 servo controller")
    print("System cannot operate without servo controller")
    print("Please check hardware connections and restart")
    # Could implement retry mechanism here
    while True:
        time.sleep(5)
        print("Retrying PCA9685 initialization...")
        if init_pca9685():
            break

e = init_wifi_espnow()
if e is None:
    print("Failed to initialize ESP-NOW - exiting")
    # You might want to implement a retry mechanism here

# Control state variables
wave_active = False
jaw_open = False
emergency_stop = False
last_heartbeat = time.ticks_ms()

# Set all servos to neutral position
stop_all_servos()

print("Servo controller ready - waiting for commands...")

# Main control loop
while True:
    try:
        # Check for incoming ESP-NOW messages
        host, msg = e.recv()
        if not msg:
            # Check heartbeat timeout even when no message received
            if time.ticks_diff(time.ticks_ms(), last_heartbeat) > 4000:
                if not emergency_stop:
                    print("Lost heartbeat — stopping servos")
                    stop_all_servos()
                    emergency_stop = True
            time.sleep_ms(10)  # Small delay to prevent tight loop
            continue

        # Parse the received message
        try:
            controls = ujson.loads(msg)
        except ValueError as e:
            print(f"JSON decode error: {e}")
            continue

        # Handle heartbeat
        if controls.get("heartbeat"):
            last_heartbeat = time.ticks_ms()
            if emergency_stop:
                print("Heartbeat received - system still in emergency stop")
            continue

        # Handle emergency stop
        if controls.get("emergency_stop"):
            print("EMERGENCY STOP ACTIVATED")
            emergency_stop = True
            stop_all_servos()
            continue

        # Handle unlock
        if controls.get("unlock"):
            print("UNLOCK RECEIVED - System ready")
            emergency_stop = False
            continue

        # Skip servo commands if in emergency stop
        if emergency_stop:
            continue

        # Basic servo control with bounds checking
        if "eye_h" in controls:
            set_servo_angle(EYE_H, controls["eye_h"])
        if "eye_v" in controls:
            set_servo_angle(EYE_V, controls["eye_v"])
        if "neck_lr" in controls:
            set_servo_angle(NECK_LR, controls["neck_lr"])
        if "neck_ud" in controls:
            set_servo_angle(NECK_UD, controls["neck_ud"])
        if "torso_rot" in controls:
            set_servo_angle(TORSO, controls["torso_rot"])

        # Handle eye blink
        if controls.get("eye_blink"):
            perform_blink()

        # Handle wave animation
        if "wave_active" in controls:
            wave_active = controls["wave_active"]
            if wave_active:
                perform_wave_sequence()

        # Handle jaw control
        if "jaw_open" in controls:
            jaw_open = controls["jaw_open"]
            set_servo_angle(JAW, 30 if jaw_open else 90)

    except OSError as e:
        print(f"Communication error: {e}")
        # Don't stop servos for communication errors, just continue
        time.sleep(0.1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        stop_all_servos()
        emergency_stop = True
        time.sleep(1)