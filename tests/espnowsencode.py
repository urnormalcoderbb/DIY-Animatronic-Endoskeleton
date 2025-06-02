import network
import espnow
import time

# Enable station mode
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

# Create ESP-NOW object
e = espnow.ESPNow()
e.active(True)

# Replace with the receiver's MAC address
peer = b'\xec\xe34\xdb\x96D'  # <-- Use actual MAC
e.add_peer(peer)

print("Sending messages...")

for i in range(5):
    msg = f"Hello {i} from Sender!"
    e.send(peer, msg)
    print("Sent:", msg)
    time.sleep(1)
