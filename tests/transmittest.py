import time
import espnow
import network
import random
import ujson

# Configuration
BROADCAST_PEER = b'\xec\xe34\xdb\x96D'  # Use broadcast; set to a specific MAC if needed

# ESP-NOW setup
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
e = espnow.ESPNow()
e.active(True)  # Proper initialization for MicroPython 2025

# Add peer – can be broadcast or unicast
def add_peer_safe(peer):
    try:
        e.add_peer(peer)
        print("Peer added successfully")
    except OSError as ex:
        print("Peer already exists or OS error:", ex)
    except Exception as ex:
        print("Error adding peer:", ex)

add_peer_safe(BROADCAST_PEER)
print("ESP-NOW Transmitter ready")

# State variables
wave_state = False
jaw_state = False
emergency_sent = False
unlock_sent = False

# Control ranges/initial positions
eye_h, eye_v = 90.0, 90.0
neck_lr, neck_ud = 90.0, 90.0
torso_rot = 90.0

# Movement directions
eye_h_dir, eye_v_dir, torso_dir = 1.0, 1.0, 1.0

# Timing
last_heartbeat = time.ticks_ms()
last_toggle = time.ticks_ms()
last_status = time.ticks_ms()
start_time = time.ticks_ms()
heartbeat_count = 0

def send_message(data_dict):
    try:
        json_str = ujson.dumps(data_dict)
        e.send(BROADCAST_PEER, json_str.encode())
        return True
    except Exception as ex:
        print("Send error:", ex)
        return False

def update_movement():
    global eye_h, eye_v, torso_rot, eye_h_dir, eye_v_dir, torso_dir
    # Eye horizontal
    eye_h += eye_h_dir * 0.8
    if eye_h <= 70 or eye_h >= 110:
        eye_h_dir *= -1
        eye_h = min(110, max(70, eye_h))
    # Eye vertical
    eye_v += eye_v_dir * 0.6
    if eye_v <= 75 or eye_v >= 105:
        eye_v_dir *= -1
        eye_v = min(105, max(75, eye_v))
    # Torso
    torso_rot += torso_dir * 0.4
    if torso_rot <= 85 or torso_rot >= 95:
        torso_dir *= -1
        torso_rot = min(95, max(85, torso_rot))

# Blink logic: blink for a few frames at random intervals
class Blinker:
    def __init__(self):
        self.blinking = False
        self.next_blink = self._next_interval()
        self.blink_timer = 0

    def _next_interval(self):
        return random.randint(1200, 3500)  # ms to next blink

    def step(self, now):
        if not self.blinking:
            if now > self.next_blink:
                self.blinking = True
                self.blink_timer = now + random.randint(120, 200)  # blink duration
        else:
            if now > self.blink_timer:
                self.blinking = False
                self.next_blink = now + self._next_interval()
        return self.blinking

blinker = Blinker()

print("Starting transmitter loop...")
try:
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

        # Emergency/Unlock sequence
        if not emergency_sent and uptime > 20000:
            if send_message({"emergency_stop": True}):
                print("Emergency stop sent!")
                emergency_sent = True
            # Don't send other data this cycle
            continue

        if emergency_sent and not unlock_sent and uptime > 25000:
            if send_message({"unlock": True}):
                print("Unlock sent!")
                unlock_sent = True
            continue

        # Update movements
        update_movement()

        # Blinking
        blink = blinker.step(current_time)

        # Control data
        control_data = {
            "eye_h": round(eye_h, 1),
            "eye_v": round(eye_v, 1),
            "neck_lr": round(eye_h, 1),  # Sync with eyes, or set independently
            "neck_ud": round(eye_v, 1),
            "torso_rot": round(torso_rot, 1),
            "eye_blink": blink,
            "wave_active": wave_state,
            "jaw_open": jaw_state
        }
        send_message(control_data)

        # Status print every 10s
        if time.ticks_diff(current_time, last_status) > 10000:
            uptime_sec = uptime // 1000
            print(f"Status - Uptime: {uptime_sec}s")
            print(f"  Eye: {round(eye_h, 1)},{round(eye_v, 1)} Torso: {round(torso_rot, 1)}")
            last_status = current_time

        time.sleep_ms(100)
except KeyboardInterrupt:
    print("Transmitter stopped")
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