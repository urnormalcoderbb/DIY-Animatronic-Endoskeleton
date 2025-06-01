
# transmitter.py (ESP-NOW, Joystick + Emergency + Unlock Combo)
import time
import ujson
from machine import Pin, ADC
import espnow
import network

# Setup Wi-Fi in station mode for ESP-NOW
w0 = network.WLAN(network.STA_IF)
w0.active(True)

e = espnow.ESPNow()
e.active(True)
peer_mac = b'\xff\xff\xff\xff\xff\xff'  # Broadcast
e.add_peer(peer_mac)

# Joysticks and buttons
j1_x = ADC(Pin(34))
j1_y = ADC(Pin(35))
j1_btn = Pin(32, Pin.IN, Pin.PULL_UP)

j2_x = ADC(Pin(33))
j2_y = ADC(Pin(25))
j2_btn = Pin(26, Pin.IN, Pin.PULL_UP)

# State
last_state = {}
last_heartbeat = time.ticks_ms()
wave_jaw_state = False
unlock_press_count = 0
unlock_timer = 0

def map_range(val, in_min, in_max, out_min, out_max):
    return int((val - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)

def read_controls():
    global wave_jaw_state, unlock_press_count, unlock_timer
    controls = {}

    # Read joystick 1 (eye & neck)
    eye_h = map_range(j1_x.read(), 0, 4095, 60, 120)
    eye_v = map_range(j1_y.read(), 0, 4095, 60, 120)
    controls["eye_h"] = eye_h
    controls["eye_v"] = eye_v
    controls["neck_lr"] = eye_h
    controls["neck_ud"] = eye_v

    # Read joystick 2 (torso)
    torso = map_range(j2_x.read(), 0, 4095, 60, 120)
    controls["torso_rot"] = torso

    # Blink button (joystick 1)
    if not j1_btn.value():
        controls["eye_blink"] = True
        if time.ticks_diff(time.ticks_ms(), unlock_timer) > 1200:
            unlock_press_count = 1
            unlock_timer = time.ticks_ms()
        else:
            unlock_press_count += 1
            unlock_timer = time.ticks_ms()

        if unlock_press_count == 3:
            controls["unlock"] = True
            unlock_press_count = 0

    # Wave + Jaw toggle (joystick 2 button)
    if not j2_btn.value():
        wave_jaw_state = not wave_jaw_state
        controls["wave_active"] = wave_jaw_state
        controls["jaw_open"] = wave_jaw_state
        time.sleep(0.3)

    # Emergency stop: both buttons held
    if not j1_btn.value() and not j2_btn.value():
        controls["emergency_stop"] = True

    return controls

while True:
    controls = read_controls()

    # Send heartbeat every 1.5 sec
    if time.ticks_diff(time.ticks_ms(), last_heartbeat) > 1500:
        e.send(peer_mac, ujson.dumps({"heartbeat": True}))
        last_heartbeat = time.ticks_ms()

    if controls != last_state:
        e.send(peer_mac, ujson.dumps(controls))
        last_state = controls

    time.sleep(0.05)
