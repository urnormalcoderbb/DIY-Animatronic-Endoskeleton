import time
import ujson
from machine import Pin, ADC
import espnow
import network

# ---------------- Communication ----------------
def init_wifi_espnow():
    """Initialize WiFi and ESP-NOW with error handling."""
    try:
        print("Initializing WiFi interface...")
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        mac = wlan.config('mac')
        mac_str = ':'.join(f'{b:02x}' for b in mac)
        print(f"Controller MAC: {mac_str}")

        print("Starting ESP-NOW communication...")
        e = espnow.ESPNow()
        e.active(True)
        peer = b'\xFF' * 6  # Broadcast to all
        e.add_peer(peer)

        print("✓ WiFi and ESP-NOW initialized successfully")
        print("✓ Broadcasting to all receivers")
        return e, peer
    except Exception as ex:
        print(f"✗ Communication initialization failed: {ex}")
        print("Check ESP32 WiFi hardware")
        return None, None

# ---------------- Hardware ----------------
def init_hardware():
    """Initialize joysticks and their buttons with error handling."""
    try:
        print("Initializing joystick hardware...")
        pins = [
            (34, 35, 27),  # Joy1: X, Y, BTN
            (32, 33, 25)   # Joy2: X, Y, BTN
        ]
        joys = []
        for x_pin, y_pin, btn_pin in pins:
            joys.append((
                ADC(Pin(x_pin, Pin.IN)),
                ADC(Pin(y_pin, Pin.IN)),
                Pin(btn_pin, Pin.IN, Pin.PULL_UP)
            ))
        # Set ADC attenuation for full range (0-3.3V)
        for joy in joys:
            joy[0].atten(ADC.ATTN_11DB)
            joy[1].atten(ADC.ATTN_11DB)
        # Test readings
        for idx, (jx, jy, _) in enumerate(joys, 1):
            print(f"Joy{idx} X: {jx.read()}, Y: {jy.read()}")
        return (*joys[0], *joys[1])
    except Exception as e:
        print(f"✗ Hardware initialization failed: {e}")
        print("Check GPIO connections and ADC pins")
        return (None,) * 6

def read_joy(adc):
    """Normalize joystick ADC value to servo angle (0-180) with deadzone."""
    try:
        raw = adc.read()
        center, deadzone = 2048, 50
        if abs(raw - center) < deadzone:
            return 90
        return max(0, min(180, int((raw * 180) / 4095)))
    except Exception as e:
        print(f"Joystick read error: {e}")
        return 90

def is_pressed(pin):
    """Return True if button is pressed (active low)."""
    try:
        return not pin.value()
    except Exception as e:
        print(f"Button read error: {e}")
        return False

# ---------------- State Management ----------------
def load_state():
    """Load saved state from file or return defaults."""
    try:
        with open("state.json", "r") as f:
            state = ujson.load(f)
        print("State loaded successfully")
        return state
    except OSError:
        print("No saved state found, using defaults")
    except Exception as e:
        print(f"State load error: {e}")
    return {"wave_active": False, "jaw_open": False}

def save_state(wave_active, jaw_open):
    """Save current state to file."""
    try:
        with open("state.json", "w") as f:
            ujson.dump({"wave_active": wave_active, "jaw_open": jaw_open}, f)
        print("State saved successfully")
        return True
    except Exception as e:
        print(f"State save error: {e}")
        return False

# ---------------- Messaging ----------------
def send_message(e, peer, message, msg_type="data"):
    """Send ESP-NOW message, log important types."""
    try:
        e.send(peer, ujson.dumps(message))
        if msg_type in {"emergency", "unlock", "error"}:
            print(f"✓ {msg_type.title()} message sent")
        return True
    except Exception as ex:
        print(f"✗ Send error ({msg_type}): {ex}")
        print("Check ESP-NOW connection to receiver")
        return False

# ---------------- Control Logic ----------------
def check_emergency_stop(btn1, btn2):
    return is_pressed(btn1) and is_pressed(btn2)

def check_unlock_combo(btn, combo, now):
    if is_pressed(btn):
        combo.append(now)
        combo[:] = [t for t in combo if time.ticks_diff(now, t) < 2000]
        if len(combo) >= 3:
            combo.clear()
            return True
    return False

# ---------------- Main ----------------
def main():
    print("=" * 50)
    print("  ESP32 Servo Controller Transmitter")
    print("=" * 50)

    # 1. Communication
    print("\n[1/3] Communication Setup:")
    e, peer = init_wifi_espnow()
    if e is None:
        print("✗ CRITICAL: Failed to initialize communication")
        raise SystemExit

    # 2. Hardware
    print("\n[2/3] Hardware Setup:")
    joy1_x, joy1_y, joy1_btn, joy2_x, joy2_y, joy2_btn = init_hardware()
    if joy1_x is None:
        print("✗ CRITICAL: Failed to initialize joystick hardware")
        raise SystemExit

    # 3. State
    print("\n[3/3] State Management:")
    state = load_state()
    wave_active, jaw_open = state["wave_active"], state["jaw_open"]
    print(f"Wave mode: {'ON' if wave_active else 'OFF'}")
    print(f"Jaw state: {'OPEN' if jaw_open else 'CLOSED'}")

    # Control variables
    last_send = heartbeat_timer = 0
    unlock_combo, unlocked = [], True
    last_joy2_btn_state = last_blink_state = False
    joy2_btn_press_time = 0

    print("\n" + "=" * 50)
    print("✓ CONTROLLER READY\nControls:")
    print("  Both buttons = Emergency Stop")
    print("  Joy1 triple-click = Unlock")
    print("  Joy1 button = Eye blink")
    print("  Joy2 button = Toggle wave/jaw")
    print("  Joy1 stick = Eye/neck movement")
    print("  Joy2 X-axis = Torso rotation")
    print("=" * 50)

    while True:
        try:
            now = time.ticks_ms()

            # --- Emergency stop ---
            if check_emergency_stop(joy1_btn, joy2_btn):
                if send_message(e, peer, {"emergency_stop": True}, "emergency"):
                    unlocked = False
                time.sleep(0.5)
                continue

            # --- Unlock combo ---
            if not unlocked:
                if check_unlock_combo(joy1_btn, unlock_combo, now):
                    if send_message(e, peer, {"unlock": True}, "unlock"):
                        unlocked = True
                    time.sleep(0.3)
                if time.ticks_diff(now, heartbeat_timer) > 1500:
                    send_message(e, peer, {"heartbeat": True}, "heartbeat")
                    heartbeat_timer = now
                    if time.ticks_diff(now, last_send) > 10000:
                        print("⚠ System LOCKED - triple-click Joy1 to unlock")
                time.sleep(0.1)
                continue

            # --- Read controls ---
            eye_h, eye_v = read_joy(joy1_x), read_joy(joy1_y)
            neck_lr, neck_ud = eye_h, eye_v
            torso_rot = read_joy(joy2_x)

            # Eye blink (Joy1 button)
            current_blink = is_pressed(joy1_btn)
            blink_trigger = current_blink and not last_blink_state
            last_blink_state = current_blink

            # Wave/Jaw toggle (Joy2 button, debounce)
            current_joy2_btn = is_pressed(joy2_btn)
            if current_joy2_btn and not last_joy2_btn_state:
                joy2_btn_press_time = now
            elif not current_joy2_btn and last_joy2_btn_state:
                press_dur = time.ticks_diff(now, joy2_btn_press_time)
                if 50 <= press_dur <= 1000:
                    wave_active = not wave_active
                    jaw_open = wave_active
                    save_state(wave_active, jaw_open)
                    print(f"Wave: {'ON' if wave_active else 'OFF'}, Jaw: {'OPEN' if jaw_open else 'CLOSED'}")
            last_joy2_btn_state = current_joy2_btn

            # --- Build and send control packet ---
            controls = {
                "eye_h": eye_h, "eye_v": eye_v,
                "neck_lr": neck_lr, "neck_ud": neck_ud,
                "torso_rot": torso_rot,
                "eye_blink": blink_trigger,
                "wave_active": wave_active, "jaw_open": jaw_open
            }
            if send_message(e, peer, controls, "control"):
                last_send = now
            elif time.ticks_diff(now, last_send) > 5000:
                print("⚠ Communication issues - check receiver")

            # --- Heartbeat ---
            if time.ticks_diff(now, heartbeat_timer) > 1500:
                send_message(e, peer, {"heartbeat": True}, "heartbeat")
                heartbeat_timer = now

            time.sleep(0.05)  # 20Hz

        except KeyboardInterrupt:
            print("\n" + "=" * 50)
            print("Controller stopped by user\nSending final emergency stop...")
            send_message(e, peer, {"emergency_stop": True}, "emergency")
            print("✓ Shutdown complete")
            break
        except Exception as e:
            print(f"✗ Main loop error: {e}")
            try:
                send_message(e, peer, {"emergency_stop": True}, "error")
            except:
                pass
            time.sleep(1)

    print("=" * 50)
    print("Controller shutting down...")
    print("=" * 50)

if __name__ == "__main__":
    main()
