import time
import espnow
import network
import ujson

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
e = espnow.ESPNow()
e.active(True)

print("ESP-NOW FULL Receiver ready (with gesture feedback)")

def print_rx(data):
    print("-" * 40)
    if data.get("heartbeat"):
        print(f"[RX] Heartbeat #{data.get('heartbeat_id', '-')}, Uptime: {int(data.get('uptime', 0))/1000:.1f}s")
    if data.get("emergency_stop"):
        print("\033[91m[RX] !!! EMERGENCY STOP RECEIVED !!!\033[0m")  # Red text for emphasis
    if data.get("unlock"):
        print("\033[92m[RX] *** UNLOCK RECEIVED ***\033[0m")  # Green text for emphasis
    if "joystick1_x" in data:
        print(f"[RX] Joystick Data (msg_id={data.get('msg_id', '-')})")
        print(f"  Joy1: X={data['joystick1_x']} Y={data['joystick1_y']}")
        print(f"  Joy2: X={data['joystick2_x']} Y={data['joystick2_y']}")
    if "eye_h" in data:
        print(f"  Eye: H={data['eye_h']} V={data['eye_v']} Blink={data.get('eye_blink', False)}")
        print(f"  Neck: LR={data['neck_lr']} UD={data['neck_ud']}")
        print(f"  Torso: Rot={data['torso_rot']}")
        print(f"  Wave: {data.get('wave_active', False)}  Jaw: {data.get('jaw_open', False)}")

print("Waiting for joystick and state data...")
try:
    last_print = time.ticks_ms()
    while True:
        host, msg = e.recv(timeout=1000)
        if msg:
            try:
                data = ujson.loads(msg.decode())
                print_rx(data)
            except Exception as ex:
                print("Invalid data received:", ex)
        now = time.ticks_ms()
        if time.ticks_diff(now, last_print) > 10000:
            print("...waiting for data...")
            last_print = now
except KeyboardInterrupt:
    print("Receiver stopped by user")
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