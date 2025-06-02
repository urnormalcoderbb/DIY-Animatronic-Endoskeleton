import time
import espnow
import network
import machine
import ujson
import random

# Configuration
BROADCAST_PEER = b'\xec\xe34\xdb\x96D'  # Set to broadcast or your receiver's MAC

# ESP-NOW setup
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
e = espnow.ESPNow()
e.active(True)

def add_peer_safe(peer):
    try:
        e.add_peer(peer)
        print("Peer added successfully")
    except OSError as ex:
        print("Peer already exists or OS error:", ex)
    except Exception as ex:
        print("Error adding peer:", ex)

add_peer_safe(BROADCAST_PEER)
print("ESP-NOW Joystick Transmitter FULL ready")

# === Joystick Setup ===
JOYSTICK1_X_PIN = 32  # ADC1_CH4
JOYSTICK1_Y_PIN = 33  # ADC1_CH5
JOYSTICK2_X_PIN = 34  # ADC1_CH6
JOYSTICK2_Y_PIN = 35  # ADC1_CH7
JOYSTICK1_BTN_PIN = 25  # Digital pin for joystick 1 button
JOYSTICK2_BTN_PIN = 26  # Digital pin for joystick 2 button

adc1_x = machine.ADC(machine.Pin(JOYSTICK1_X_PIN))
adc1_y = machine.ADC(machine.Pin(JOYSTICK1_Y_PIN))
adc2_x = machine.ADC(machine.Pin(JOYSTICK2_X_PIN))
adc2_y = machine.ADC(machine.Pin(JOYSTICK2_Y_PIN))

for adc in [adc1_x, adc1_y, adc2_x, adc2_y]:
    adc.atten(machine.ADC.ATTN_11DB)
    adc.width(machine.ADC.WIDTH_12BIT)

joy1_btn = machine.Pin(JOYSTICK1_BTN_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
joy2_btn = machine.Pin(JOYSTICK2_BTN_PIN, machine.Pin.IN, machine.Pin.PULL_UP)

def read_joysticks():
    j1x = adc1_x.read() / 4095.0
    j1y = adc1_y.read() / 4095.0
    j2x = adc2_x.read() / 4095.0
    j2y = adc2_y.read() / 4095.0
    return {
        "joystick1_x": round(j1x, 3),
        "joystick1_y": round(j1y, 3),
        "joystick2_x": round(j2x, 3),
        "joystick2_y": round(j2y, 3)
    }

def send_message(data_dict):
    try:
        json_str = ujson.dumps(data_dict)
        e.send(BROADCAST_PEER, json_str.encode())
        return True
    except Exception as ex:
        print("Send error:", ex)
        return False

# Blinker class for eyes
class Blinker:
    def __init__(self):
        self.blinking = False
        self.next_blink = self._next_interval()
        self.blink_timer = 0

    def _next_interval(self):
        return random.randint(1200, 3500)  # ms

    def step(self, now):
        if not self.blinking:
            if now > self.next_blink:
                self.blinking = True
                self.blink_timer = now + random.randint(120, 200)
        else:
            if now > self.blink_timer:
                self.blinking = False
                self.next_blink = now + self._next_interval()
        return self.blinking

blinker = Blinker()

# State variables
wave_state = False
jaw_state = False
emergency_sent = False
unlock_sent = False

# Control ranges/initial positions for simulated movements
eye_h, eye_v = 90.0, 90.0
neck_lr, neck_ud = 90.0, 90.0
torso_rot = 90.0
eye_h_dir, eye_v_dir, torso_dir = 1.0, 1.0, 1.0

# Timing
last_heartbeat = time.ticks_ms()
last_toggle = time.ticks_ms()
last_status = time.ticks_ms()
start_time = time.ticks_ms()
heartbeat_count = 0

# For unlock gesture
joy1_btn_history = []
UNLOCK_WINDOW_MS = 2000  # 2 seconds
JOYBTN_DEBOUNCE_MS = 100

def check_emergency_gesture():
    # If both joystick buttons are pressed at the same time (active low)
    return not joy1_btn.value() and not joy2_btn.value()

def check_unlock_gesture(current_time):
    # If 3 presses within 2 seconds on joystick 1 button
    global joy1_btn_history
    # Remove old entries
    joy1_btn_history = [t for t in joy1_btn_history if current_time - t <= UNLOCK_WINDOW_MS]
    return len(joy1_btn_history) >= 3

print("Starting FULL transmitter loop with gesture emergency/unlock...")
try:
    count = 0
    last_joy1_btn = 1
    last_joy2_btn = 1
    joy1_btn_last_time = 0
    while True:
        current_time = time.ticks_ms()
        uptime = time.ticks_diff(current_time, start_time)

        # Heartbeat every 1.5s
        if time.ticks_diff(current_time, last_heartbeat) > 1500:
            heartbeat_count += 1
            if send_message({
                "heartbeat": True,
                "heartbeat_id": heartbeat_count,
                "uptime": uptime
            }):
                print(f"Heartbeat sent #{heartbeat_count}")
            last_heartbeat = current_time

        # Toggle states every 8s
        if time.ticks_diff(current_time, last_toggle) > 8000:
            wave_state = not wave_state
            jaw_state = random.choice([True, False])
            last_toggle = current_time
            print(f"State change - Wave: {wave_state}, Jaw: {jaw_state}")

        # --- Emergency Stop Gesture ---
        if not emergency_sent and check_emergency_gesture():
            if send_message({"emergency_stop": True}):
                print("Emergency stop sent (gesture)!")
                emergency_sent = True
            time.sleep_ms(500)  # Prevent auto-retrigger

        # --- Unlock Gesture ---
        current_joy1_btn = joy1_btn.value()
        if last_joy1_btn == 1 and current_joy1_btn == 0:  # Button press (active low)
            # Debounce
            if current_time - joy1_btn_last_time > JOYBTN_DEBOUNCE_MS:
                joy1_btn_history.append(current_time)
                joy1_btn_last_time = current_time
                print(f"Joystick 1 button press recorded at {current_time//1000}s")
        last_joy1_btn = current_joy1_btn

        if emergency_sent and not unlock_sent and check_unlock_gesture(current_time):
            if send_message({"unlock": True}):
                print("Unlock sent! (gesture: 3x joy1)")
                unlock_sent = True
            joy1_btn_history = []  # Reset after unlock

        # Simulate movement
        eye_h += eye_h_dir * 0.8
        if eye_h <= 70 or eye_h >= 110:
            eye_h_dir *= -1
            eye_h = min(110, max(70, eye_h))
        eye_v += eye_v_dir * 0.6
        if eye_v <= 75 or eye_v >= 105:
            eye_v_dir *= -1
            eye_v = min(105, max(75, eye_v))
        torso_rot += torso_dir * 0.4
        if torso_rot <= 85 or torso_rot >= 95:
            torso_dir *= -1
            torso_rot = min(95, max(85, torso_rot))

        # Blinking
        blink = blinker.step(current_time)

        # Read joysticks
        js = read_joysticks()
        # Form message
        control_data = {
            "msg_id": count,
            "joystick1_x": js["joystick1_x"],
            "joystick1_y": js["joystick1_y"],
            "joystick2_x": js["joystick2_x"],
            "joystick2_y": js["joystick2_y"],
            "eye_h": round(eye_h, 1),
            "eye_v": round(eye_v, 1),
            "neck_lr": round(eye_h, 1),
            "neck_ud": round(eye_v, 1),
            "torso_rot": round(torso_rot, 1),
            "eye_blink": blink,
            "wave_active": wave_state,
            "jaw_open": jaw_state
        }
        send_message(control_data)
        count += 1

        # Status print every 10s
        if time.ticks_diff(current_time, last_status) > 10000:
            uptime_sec = uptime // 1000
            print(f"Status - Uptime: {uptime_sec}s")
            print(f"  Eye: {round(eye_h, 1)},{round(eye_v, 1)} Torso: {round(torso_rot, 1)}")
            print(f"  Joysticks: {js}")
            last_status = current_time

        time.sleep_ms(100)
except KeyboardInterrupt:
    print("Transmitter stopped by user")
except Exception as ex:
    print("Fatal error in main loop:", ex)
finally:
    print("Cleaning up...")
    try:
        if hasattr(e, "deinit"):
            e.deinit()
        wlan.active(False)
    except Exception as cleanup_ex:
        print("Cleanup failed:", cleanup_ex)