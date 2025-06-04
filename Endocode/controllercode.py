import time
import ujson
from machine import Pin, ADC
import espnow
import network

# =================== Communication Setup ===================

def init_wifi_espnow():
    """Initialize WiFi and ESP-NOW for controller. Handles errors gracefully."""
    try:
        print("Setting up WiFi interface...")
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        mac = wlan.config('mac')
        mac_str = ':'.join(f'{b:02x}' for b in mac)
        print(f"  [INFO] Controller MAC Address: {mac_str}")

        print("Initializing ESP-NOW protocol...")
        e = espnow.ESPNow()
        e.active(True)
        peer = b'\xFF' * 6  # Broadcast to all receivers
        e.add_peer(peer)

        print("ESP-NOW ready. Broadcasting enabled.")
        return e, peer
    except Exception as ex:
        print(f"Failed to initialize communication: {ex}")
        print("    [Hint] Verify ESP32 WiFi hardware and firmware.")
        return None, None

# =================== Hardware Initialization ===================

def init_hardware():
    """Initialize joystick ADCs and button pins. Returns joystick ADCs and pins."""
    try:
        print("Setting up joystick hardware...")
        # Format: (X ADC pin, Y ADC pin, Button Pin)
        pin_configs = [
            (34, 35, 27),  # Joy1
            (32, 33, 25)   # Joy2
        ]
        joys = []
        for x_pin, y_pin, btn_pin in pin_configs:
            joys.append((
                ADC(Pin(x_pin, Pin.IN)),
                ADC(Pin(y_pin, Pin.IN)),
                Pin(btn_pin, Pin.IN, Pin.PULL_UP)
            ))
        # Set ADC range to 0-3.3V
        for joy in joys:
            joy[0].atten(ADC.ATTN_11DB)
            joy[1].atten(ADC.ATTN_11DB)
        # Display initial readings
        for idx, (jx, jy, _) in enumerate(joys, 1):
            print(f"    Joy{idx}: X={jx.read()}  Y={jy.read()}")
        return (*joys[0], *joys[1])
    except Exception as e:
        print(f"Joystick hardware setup failed: {e}")
        print("    [Hint] Check GPIO wiring and ADC pin assignments.")
        return (None,) * 6

def read_joy(adc):
    """Convert ADC value to a servo angle (0-180) with deadzone for neutral."""
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

# =================== State Management ===================

def load_state():
    """Load previously saved controller state from file, if it exists."""
    try:
        with open("state.json", "r") as f:
            state = ujson.load(f)
        print("Controller state restored from file.")
        return state
    except OSError:
        print("No previous state found. Using default states.")
    except Exception as e:
        print(f"State load error: {e}")
    return {"wave_active": False, "jaw_open": False}

def save_state(wave_active, jaw_open):
    """Save current controller state to file."""
    try:
        with open("state.json", "w") as f:
            ujson.dump({"wave_active": wave_active, "jaw_open": jaw_open}, f)
        print("State saved.")
        return True
    except Exception as e:
        print(f"State save error: {e}")
        return False

# =================== ESP-NOW Messaging ===================

def send_message(e, peer, message, msg_type="data"):
    """Send ESP-NOW message. Log important message types."""
    try:
        e.send(peer, ujson.dumps(message))
        if msg_type in {"emergency", "unlock", "error"}:
            print(f"{msg_type.title()} message sent.")
        return True
    except Exception as ex:
        print(f"Send error ({msg_type}): {ex}")
        print("    [Hint] Check ESP-NOW connection to receiver module.")
        return False

# =================== Control Logic ===================

def check_emergency_stop(btn1, btn2):
    """Both buttons pressed = emergency stop."""
    return is_pressed(btn1) and is_pressed(btn2)

def check_unlock_combo(btn, combo, now):
    """Check if button triple-clicked for unlock (within 2 seconds)."""
    if is_pressed(btn):
        combo.append(now)
        # Keep only clicks within last 2 seconds
        combo[:] = [t for t in combo if time.ticks_diff(now, t) < 2000]
        if len(combo) >= 3:
            combo.clear()
            return True
    return False

# =================== Main Loop ===================

def main():
    print("=" * 55)
    print("      ESP32 Animatronic Controller - Transmitter")
    print("=" * 55)

    # 1. Communication
    print("\n[1/3] Communication Setup:")
    e, peer = init_wifi_espnow()
    if e is None:
        print("CRITICAL: Communication not initialized. Exiting.")
        raise SystemExit

    # 2. Hardware
    print("\n[2/3] Hardware Setup:")
    joy1_x, joy1_y, joy1_btn, joy2_x, joy2_y, joy2_btn = init_hardware()
    if joy1_x is None:
        print("CRITICAL: Joystick hardware not initialized. Exiting.")
        raise SystemExit

    # 3. State
    print("\n[3/3] State Management:")
    state = load_state()
    wave_active, jaw_open = state["wave_active"], state["jaw_open"]
    print(f"  [State] Wave mode: {'ON' if wave_active else 'OFF'} | Jaw: {'OPEN' if jaw_open else 'CLOSED'}")

    # ====== Control Variables ======
    last_send = heartbeat_timer = 0
    unlock_combo, unlocked = [], True
    last_joy2_btn_state = last_blink_state = False
    joy2_btn_press_time = 0

    print("\n" + "=" * 55)
    print("CONTROLLER READY! Controls:")
    print("  - Both buttons = Emergency Stop")
    print("  - Joy1 triple-click = Unlock")
    print("  - Joy1 button = Eye blink")
    print("  - Joy2 button = Toggle wave/jaw")
    print("  - Joy1 stick = Eye/neck movement")
    print("  - Joy2 X-axis = Torso rotation")
    print("=" * 55)

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
                # Heartbeat to prevent sleep on receiver
                if time.ticks_diff(now, heartbeat_timer) > 1500:
                    send_message(e, peer, {"heartbeat": True}, "heartbeat")
                    heartbeat_timer = now
                if time.ticks_diff(now, last_send) > 10000:
                    print("System LOCKED - triple-click Joy1 to unlock")
                time.sleep(0.1)
                continue

            # --- Read controls ---
            eye_h, eye_v = read_joy(joy1_x), read_joy(joy1_y)
            neck_lr, neck_ud = eye_h, eye_v  # For now, same as eye
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
                if 50 <= press_dur <= 1000:  # Short press
                    wave_active = not wave_active
                    jaw_open = wave_active
                    save_state(wave_active, jaw_open)
                    print(f"  [INFO] Wave: {'ON' if wave_active else 'OFF'}, Jaw: {'OPEN' if jaw_open else 'CLOSED'}")
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
                print("Communication issues - check receiver module.")

            # --- Heartbeat ---
            if time.ticks_diff(now, heartbeat_timer) > 1500:
                send_message(e, peer, {"heartbeat": True}, "heartbeat")
                heartbeat_timer = now

            time.sleep(0.05)  # ~20Hz

        except KeyboardInterrupt:
            print("\n" + "=" * 55)
            print("Controller stopped by user. Sending final emergency stop...")
            send_message(e, peer, {"emergency_stop": True}, "emergency")
            print("Controller shutdown complete.")
            break
        except Exception as e:
            print(f"Main loop error: {e}")
            try:
                send_message(e, peer, {"emergency_stop": True}, "error")
            except:
                pass
            time.sleep(1)

    print("=" * 55)
    print("Controller shutting down...")
    print("=" * 55)

if __name__ == "__main__":
    main()
