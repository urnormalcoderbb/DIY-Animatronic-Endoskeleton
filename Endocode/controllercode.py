import time
import ujson
from machine import Pin, ADC
import espnow
import network

# =================== Debounced Button Helper ===================

class DebouncedButton:
    def __init__(self, pin, debounce_ms=40):
        self.pin = pin
        self.debounce_ms = debounce_ms
        self.last_state = self.pin.value()
        self.last_time = time.ticks_ms()
        self._pressed = False

    def update(self):
        now = time.ticks_ms()
        state = self.pin.value()
        if state != self.last_state:
            if time.ticks_diff(now, self.last_time) > self.debounce_ms:
                self.last_state = state
                self.last_time = now
                self._pressed = not state  # Active LOW logic
        else:
            self._pressed = False
        return self._pressed

    def is_pressed(self):
        # Returns True only on rising edge (button press)
        return self.update()

    def raw(self):
        # Returns current (possibly bouncing) hardware value
        return not self.pin.value()

# =================== Communication Setup ===================

def init_wifi_espnow():
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
    try:
        print("Setting up joystick hardware...")
        pin_configs = [
            (34, 35, 27),  # Joy1
            (32, 33, 25)   # Joy2
        ]
        joys = []
        for x_pin, y_pin, btn_pin in pin_configs:
            joys.append((
                ADC(Pin(x_pin, Pin.IN)),
                ADC(Pin(y_pin, Pin.IN)),
                DebouncedButton(Pin(btn_pin, Pin.IN, Pin.PULL_UP))
            ))
        for joy in joys:
            joy[0].atten(ADC.ATTN_11DB)
            joy[1].atten(ADC.ATTN_11DB)
        for idx, (jx, jy, _) in enumerate(joys, 1):
            print(f"    Joy{idx}: X={jx.read()}  Y={jy.read()}")
        return (*joys[0], *joys[1])
    except Exception as e:
        print(f"Joystick hardware setup failed: {e}")
        print("    [Hint] Check GPIO wiring and ADC pin assignments.")
        return (None,) * 6

def read_joy(adc):
    try:
        raw = adc.read()
        center, deadzone = 2048, 50
        if abs(raw - center) < deadzone:
            return 90
        return max(0, min(180, int((raw * 180) / 4095)))
    except Exception as e:
        print(f"Joystick read error: {e}")
        return 90

# =================== State Management ===================

def load_state():
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
    try:
        with open("state.json", "w") as f:
            ujson.dump({"wave_active": wave_active, "jaw_open": jaw_open}, f)
        print("State saved.")
        return True
    except Exception as e:
        print(f"State save error: {e}")
        return False

# =================== ESP-NOW Messaging ===================

class ReliableSender:
    """Resends data on failure; adds sequence numbers for data loss protection."""
    def __init__(self, e, peer):
        self.e = e
        self.peer = peer
        self.seq = 0
        self.last_packet = None
        self.last_type = None
        self.acknowledged = True  # True if last packet was acknowledged/sent

    def send(self, message, msg_type="data"):
        # Attach sequence number for data packets and heartbeats
        if msg_type in ("data", "heartbeat"):
            message["seq"] = self.seq
        try:
            self.e.send(self.peer, ujson.dumps(message))
            self.last_packet = message
            self.last_type = msg_type
            self.acknowledged = True
            if msg_type in {"emergency", "unlock", "error"}:
                print(f"{msg_type.title()} message sent.")
            if msg_type == "data":
                self.seq = (self.seq + 1) % 65536
            return True
        except Exception as ex:
            print(f"Send error ({msg_type}): {ex}")
            print("    [Hint] Check ESP-NOW connection to receiver module.")
            self.acknowledged = False
            return False

    def resend_last(self):
        if self.last_packet is not None:
            print("[WARN] Resending last control packet...")
            return self.send(self.last_packet, self.last_type)
        return False

# =================== Control Logic ===================

def check_emergency_stop(btn1, btn2):
    return btn1.raw() and btn2.raw()

def check_unlock_combo(btn, combo, now):
    if btn.is_pressed():
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
    sender = ReliableSender(e, peer)

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
    last_joy2_btn_press = False
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
                if sender.send({"emergency_stop": True}, "emergency"):
                    unlocked = False
                time.sleep(0.5)
                continue

            # --- Unlock combo ---
            if not unlocked:
                if check_unlock_combo(joy1_btn, unlock_combo, now):
                    if sender.send({"unlock": True}, "unlock"):
                        unlocked = True
                    time.sleep(0.3)
                # Heartbeat to prevent sleep on receiver
                if time.ticks_diff(now, heartbeat_timer) > 1500:
                    sender.send({"heartbeat": True}, "heartbeat")
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
            blink_trigger = joy1_btn.is_pressed()

            # Wave/Jaw toggle (Joy2 button, debounce)
            if joy2_btn.is_pressed():
                joy2_btn_press_time = now
            elif not joy2_btn.raw() and last_joy2_btn_press:
                press_dur = time.ticks_diff(now, joy2_btn_press_time)
                if 50 <= press_dur <= 1000:  # Short press
                    wave_active = not wave_active
                    jaw_open = wave_active
                    save_state(wave_active, jaw_open)
                    print(f"  [INFO] Wave: {'ON' if wave_active else 'OFF'}, Jaw: {'OPEN' if jaw_open else 'CLOSED'}")
            last_joy2_btn_press = joy2_btn.raw()

            # --- Build and send control packet ---
            controls = {
                "eye_h": eye_h, "eye_v": eye_v,
                "neck_lr": neck_lr, "neck_ud": neck_ud,
                "torso_rot": torso_rot,
                "eye_blink": blink_trigger,
                "wave_active": wave_active, "jaw_open": jaw_open
            }
            if sender.send(controls, "data"):
                last_send = now
            elif time.ticks_diff(now, last_send) > 500:
                sender.resend_last()

            # --- Heartbeat ---
            if time.ticks_diff(now, heartbeat_timer) > 1500:
                sender.send({"heartbeat": True}, "heartbeat")
                heartbeat_timer = now

            time.sleep(0.05)  # ~20Hz

        except KeyboardInterrupt:
            print("\n" + "=" * 55)
            print("Controller stopped by user. Sending final emergency stop...")
            sender.send({"emergency_stop": True}, "emergency")
            print("Controller shutdown complete.")
            break
        except Exception as e:
            print(f"Main loop error: {e}")
            try:
                sender.send({"emergency_stop": True}, "error")
            except:
                pass
            time.sleep(1)

    print("=" * 55)
    print("Controller shutting down...")
    print("=" * 55)

if __name__ == "__main__":
    main()