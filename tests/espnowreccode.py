import network
import espnow

# Enable station mode (required for ESP-NOW)
wlan = network.WLAN(network.STA_IF)
wlan.active(True)

# Create ESP-NOW object (initializes automatically)
e = espnow.ESPNow()
e.active(True)

print("Receiver ready. Waiting for messages...")

while True:
    peer, msg = e.recv()
    if msg:
        print("From:", peer)
        print("Message:", msg.decode())
