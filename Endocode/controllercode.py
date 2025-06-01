import time
import ujson
from machine import Pin, ADC
import espnow
import network

def init_wifi_espnow():
    """Initialize WiFi and ESP-NOW with error handling"""
    try:
        print("Initializing WiFi interface...")
        # Setup WiFi
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        
        # Get MAC address for identification
        mac = wlan.config('mac')
        mac_str = ':'.join(['%02x' % b for b in mac])
        print(f"Controller MAC: {mac_str}")
        
        print("Starting ESP-NOW communication...")
        # Setup ESP-NOW
        e = espnow.ESPNow()
        e.active(True)
        peer = b'\xFF\xFF\xFF\xFF\xFF\xFF'  # Broadcast to all
        e.add_peer(peer)
        
        print("✓ WiFi and ESP-NOW initialized successfully")
        print("✓ Broadcasting to all receivers")
        return e, peer
    except Exception as ex:
        print(f"✗ Communication initialization failed: {ex}")
        print("Check ESP32 WiFi hardware")
        return None, None

def init_hardware():
    """Initialize joystick hardware with error handling"""
    try:
        print("Initializing joystick hardware...")
        print("Joy1: X=GPIO34, Y=GPIO35, BTN=GPIO27")
        print("Joy2: X=GPIO32, Y=GPIO33, BTN=GPIO25")
        
        # Joystick pins
        joy1_x = ADC(Pin(34))
        joy1_y = ADC(Pin(35))
        joy1_btn = Pin(27, Pin.IN, Pin.PULL_UP)
        
        joy2_x = ADC(Pin(32))
        joy2_y = ADC(Pin(33))
        joy2_btn = Pin(25, Pin.IN, Pin.PULL_UP)
        
        # Set ADC attenuation for full range (0-3.3V)
        joy1_x.atten(ADC.ATTN_11DB)
        joy1_y.atten(ADC.ATTN_11DB)
        joy2_x.atten(ADC.ATTN_11DB)
        joy2_y.atten(ADC.ATTN_11DB)
        
        # Test joystick readings
        print("Testing joystick readings...")
        j1x_test = joy1_x.read()
        j1y_test = joy1_y.read()
        j2x_test = joy2_x.read()
        j2y_test = joy2_y.read()
        
        print(f"Joy1 X: {j1x_test}, Y: {j1y_test}")
        print(f"Joy2 X: {j2x_test}, Y: {j2y_test}")
        
        if j1x_test == 0 and j1y_test == 0:
            print("⚠ Warning: Joy1 readings are zero - check connections")
        if j2x_test == 0 and j2y_test == 0:
            print("⚠ Warning: Joy2 readings are zero - check connections")
        
        print("✓ Joystick hardware initialized successfully")
        return joy1_x, joy1_y, joy1_btn, joy2_x, joy2_y, joy2_btn
    except Exception as e:
        print(f"✗ Hardware initialization failed: {e}")
        print("Check GPIO connections and ADC pins")
        return None, None, None, None, None, None

def read_joy(adc):
    """Normalize joystick values to servo range (0-180)"""
    try:
        raw_value = adc.read()
        # Map ADC range (0-4095) to servo range (0-180)
        # Add deadzone in center (±50 around 2048)
        center = 2048
        deadzone = 50
        
        if abs(raw_value - center) < deadzone:
            return 90  # Center position
        
        # Scale to 0-180 range
        normalized = int((raw_value * 180) / 4095)
        return max(0, min(180, normalized))  # Clamp to valid range
    except Exception as e:
        print(f"Joystick read error: {e}")
        return 90  # Return center position on error

def is_pressed(pin):
    """Check if button is pressed with error handling"""
    try:
        return not pin.value()
    except Exception as e:
        print(f"Button read error: {e}")
        return False

def load_state():
    """Load saved state from file with error handling"""
    try:
        with open("state.json", "r") as f:
            state = ujson.load(f)
        print("State loaded successfully")
        return state
    except OSError:
        print("No saved state found, using defaults")
        return {
            "wave_active": False,
            "jaw_open": False
        }
    except Exception as e:
        print(f"State load error: {e}")
        return {
            "wave_active": False,
            "jaw_open": False
        }

def save_state(wave_active, jaw_open):
    """Save current state to file with error handling"""
    try:
        state_data = {
            "wave_active": wave_active,
            "jaw_open": jaw_open
        }
        with open("state.json", "w") as f:
            ujson.dump(state_data, f)
        print("State saved successfully")
        return True
    except Exception as e:
        print(f"State save error: {e}")
        return False

def send_message(e, peer, message, msg_type="data"):
    """Send ESP-NOW message with error handling"""
    try:
        json_msg = ujson.dumps(message)
        e.send(peer, json_msg)
        
        # Only show important messages to avoid spam
        if msg_type in ["emergency", "unlock", "error"]:
            print(f"✓ {msg_type.title()} message sent")
        return True
    except Exception as ex:
        print(f"✗ Send error ({msg_type}): {ex}")
        print("Check ESP-NOW connection to receiver")
        return False

def check_emergency_stop(joy1_btn, joy2_btn):
    """Check for emergency stop condition"""
    return is_pressed(joy1_btn) and is_pressed(joy2_btn)

def check_unlock_combo(joy1_btn, unlock_combo, now):
    """Check unlock button combination"""
    if is_pressed(joy1_btn):
        unlock_combo.append(now)
        # Keep only recent presses (within 2 seconds)
        unlock_combo[:] = [t for t in unlock_combo if time.ticks_diff(now, t) < 2000]
        
        # Need 3 presses within 2 seconds
        if len(unlock_combo) >= 3:
            unlock_combo.clear()
            return True
    return False

# Main initialization
print("=" * 50)
print("  ESP32 Servo Controller Transmitter")
print("=" * 50)

# Initialize communication
print("\n[1/3] Communication Setup:")
e, peer = init_wifi_espnow()
if e is None or peer is None:
    print("✗ CRITICAL: Failed to initialize communication")
    print("Cannot operate without ESP-NOW - check ESP32")
    raise SystemExit

# Initialize hardware
print("\n[2/3] Hardware Setup:")
joy1_x, joy1_y, joy1_btn, joy2_x, joy2_y, joy2_btn = init_hardware()
if joy1_x is None:
    print("✗ CRITICAL: Failed to initialize joystick hardware")
    print("Cannot operate without joysticks - check wiring")
    raise SystemExit

# Load saved state
print("\n[3/3] State Management:")
state = load_state()
wave_active = state["wave_active"]
jaw_open = state["jaw_open"]
print(f"Wave mode: {'ON' if wave_active else 'OFF'}")
print(f"Jaw state: {'OPEN' if jaw_open else 'CLOSED'}")

# Control variables
last_send = 0
heartbeat_timer = 0
unlock_combo = []
unlocked = True
last_joy2_btn_state = False
joy2_btn_press_time = 0
blink_active = False
last_blink_state = False

print("\n" + "=" * 50)
print("✓ CONTROLLER READY")
print("Controls:")
print("  Both buttons = Emergency Stop")
print("  Joy1 triple-click = Unlock")
print("  Joy1 button = Eye blink")
print("  Joy2 button = Toggle wave/jaw")
print("  Joy1 stick = Eye/neck movement")
print("  Joy2 X-axis = Torso rotation")
print("=" * 50)

# Main control loop
while True:
    try:
        now = time.ticks_ms()
        
        # Emergency stop check (both buttons pressed)
        if check_emergency_stop(joy1_btn, joy2_btn):
            if send_message(e, peer, {"emergency_stop": True}, "emergency"):
                unlocked = False
                time.sleep(0.5)  # Prevent multiple triggers
                continue
        
        # Unlock combo check (triple press joy1 button)
        if not unlocked:
            if check_unlock_combo(joy1_btn, unlock_combo, now):
                if send_message(e, peer, {"unlock": True}, "unlock"):
                    unlocked = True
                time.sleep(0.3)
            
            # Send heartbeat even when locked
            if time.ticks_diff(now, heartbeat_timer) > 1500:
                send_message(e, peer, {"heartbeat": True}, "heartbeat")
                heartbeat_timer = now
                if time.ticks_diff(now, last_send) > 10000:  # Every 10s when locked
                    print("⚠ System LOCKED - triple-click Joy1 to unlock")
            
            time.sleep(0.1)
            continue
        
        # Read joystick values
        eye_h = read_joy(joy1_x)
        eye_v = read_joy(joy1_y)
        neck_lr = eye_h  # Mirror eye movement to neck
        neck_ud = eye_v
        torso_rot = read_joy(joy2_x)
        
        # Handle eye blink (joy1 button)
        current_blink_state = is_pressed(joy1_btn)
        blink_trigger = current_blink_state and not last_blink_state
        last_blink_state = current_blink_state
        
        # Handle wave/jaw toggle (joy2 button with debouncing)
        current_joy2_btn_state = is_pressed(joy2_btn)
        if current_joy2_btn_state and not last_joy2_btn_state:
            # Button just pressed
            joy2_btn_press_time = now
        elif not current_joy2_btn_state and last_joy2_btn_state:
            # Button just released - check if it was a valid press
            press_duration = time.ticks_diff(now, joy2_btn_press_time)
            if 50 <= press_duration <= 1000:  # Valid press between 50ms and 1s
                wave_active = not wave_active
                jaw_open = wave_active  # Sync jaw with wave
                save_state(wave_active, jaw_open)
                print(f"Wave: {'ON' if wave_active else 'OFF'}, Jaw: {'OPEN' if jaw_open else 'CLOSED'}")
        
        last_joy2_btn_state = current_joy2_btn_state
        
        # Prepare control message
        controls = {
            "eye_h": eye_h,
            "eye_v": eye_v,
            "neck_lr": neck_lr,
            "neck_ud": neck_ud,
            "torso_rot": torso_rot,
            "eye_blink": blink_trigger,
            "wave_active": wave_active,
            "jaw_open": jaw_open
        }
        
        # Send control packet
        if send_message(e, peer, controls, "control"):
            last_send = now
        else:
            # Connection issue - warn user occasionally
            if time.ticks_diff(now, last_send) > 5000:  # Every 5s
                print("⚠ Communication issues - check receiver")
        
        # Send heartbeat every 1.5 seconds
        if time.ticks_diff(now, heartbeat_timer) > 1500:
            send_message(e, peer, {"heartbeat": True}, "heartbeat")
            heartbeat_timer = now
        
        # Control loop timing
        time.sleep(0.05)  # 20Hz update rate
        
    except KeyboardInterrupt:
        print("\n" + "=" * 50)
        print("Controller stopped by user")
        print("Sending final emergency stop...")
        # Send final emergency stop
        send_message(e, peer, {"emergency_stop": True}, "emergency")
        print("✓ Shutdown complete")
        break
    except Exception as e:
        print(f"✗ Main loop error: {e}")
        # Try to send emergency stop on unexpected errors
        try:
            send_message(e, peer, {"emergency_stop": True}, "error")
        except:
            pass
        time.sleep(1)  # Wait before retrying

print("=" * 50)
print("Controller shutting down...")
print("=" * 50)