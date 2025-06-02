import time
import network
import espnow
import ujson

# WiFi Station mode setup
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

# ESP-NOW setup
e = espnow.ESPNow()
e.active(True)

print("ESP-NOW Receiver ready, waiting for data...")

# --- State Variables ---
last_heartbeat = time.ticks_ms()
emergency_stop = False
message_count = 0
error_count = 0
last_status = time.ticks_ms()
status_interval = 30000  # ms

# Control data with defaults
control_data = {
    "eye_h": 0,
    "eye_v": 0,
    "neck_lr": 0,
    "neck_ud": 0,
    "torso_rot": 0,
    "eye_blink": False,
    "wave_active": False,
    "jaw_open": False
}

def log(msg):
    print("[{:.2f}] {}".format(time.ticks_ms()/1000, msg))

def process_heartbeat(data):
    global last_heartbeat
    last_heartbeat = time.ticks_ms()
    hb_id = data.get("heartbeat_id", "?")
    uptime = data.get("uptime", "?")
    log("Heartbeat received (id: {}, uptime: {} ms)".format(hb_id, uptime))

def process_emergency_stop():
    global emergency_stop
    if not emergency_stop:
        log("Emergency STOP triggered!")
    emergency_stop = True

def process_unlock():
    global emergency_stop
    if emergency_stop:
        log("Unlock received! System active.")
    emergency_stop = False

def process_control_data(data):
    global control_data
    if emergency_stop:
        log("EMERGENCY STOP ACTIVE - ignoring control input")
        return
    updated = []
    for key in control_data:
        if key in data:
            old_val = control_data[key]
            new_val = data[key]
            # Type check
            try:
                if isinstance(old_val, bool):
                    new_val = bool(new_val)
                elif isinstance(old_val, (int, float)):
                    new_val = float(new_val)
            except Exception as conv_ex:
                log("Invalid value for {}: {} ({})".format(key, new_val, conv_ex))
                continue
            if new_val != old_val:
                control_data[key] = new_val
                updated.append((key, old_val, new_val))
    if updated:
        log("Control update:")
        for k, old, new in updated:
            print("  {}: {} -> {}".format(k, old, new))
        print("-----")

def check_heartbeat_timeout():
    global emergency_stop
    elapsed = time.ticks_diff(time.ticks_ms(), last_heartbeat)
    if elapsed > 4000:  # ms
        if not emergency_stop:
            log("Lost heartbeat for {:.1f}s! Entering EMERGENCY STOP.".format(elapsed/1000))
            emergency_stop = True
        return True
    return False

def status_report():
    global message_count, error_count, emergency_stop
    status = "YES" if emergency_stop else "NO"
    log("Status: Messages: {}, Errors: {}, Emergency: {}".format(message_count, error_count, status))
    print("Current control data:", control_data)

try:
    while True:
        try:
            msg = e.recv()
            if msg:
                try:
                    data = ujson.loads(msg[1])
                    message_count += 1
                    # Route message
                    if data.get("heartbeat"):
                        process_heartbeat(data)
                    elif data.get("emergency_stop"):
                        process_emergency_stop()
                    elif data.get("unlock"):
                        process_unlock()
                    else:
                        process_control_data(data)
                except Exception as parse_ex:
                    error_count += 1
                    log("Message parse error: {}".format(parse_ex))
        except OSError:
            pass  # No message available

        check_heartbeat_timeout()

        # Status print every 30s
        now = time.ticks_ms()
        if time.ticks_diff(now, last_status) > status_interval:
            status_report()
            last_status = now

        time.sleep_ms(50)

except KeyboardInterrupt:
    log("Receiver stopped by user")
except Exception as main_ex:
    log("Fatal error: {}".format(main_ex))
finally:
    try:
        e.active(False)
    except Exception:
        pass
    wlan.active(False)
    log("Cleanup complete")