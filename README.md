# DIY Animatronic Endoskeleton

Welcome to the DIY Animatronic Endoskeleton project!  
This project guides you through building your own animatronic endoskeleton, which can wave hi to people using affordable, easy-to-find components—even if you have no prior experience with robotics.

**Key Features:**
- Wireless control using two ESP32 WROOM microcontrollers.
- Designed for hobbyists, makers, and anyone interested in animatronics.
- Can wave hi to people.
- A Jaw which can move. You can configure how it moves in the receiver code.
- 3D-printable files for the endoskeleton (coming soon!).
- Step-by-step instructions (Coming very soon!) and the code provided.

---

## Project Overview

This animatronic endoskeleton is designed to be both accessible and expandable.  
You’ll use two ESP32 WROOM modules to enable wireless communication—perfect for remote-controlled or semi-autonomous animatronics.

In future updates, I’ll provide STL/3D files so you can print the mechanical parts yourself.

---

## Required Materials

- 2 × ESP32 WROOM microcontrollers
- About 6 × SG90 servo motors
- 4 × MG90S servo motors
- 1 × PCA9685 servo driver
- 2 × Analog joysticks
- A lot of jumper wires (F-F, M-F, M-M)
- 1 × 5V 5A power source (available on eBay/Amazon)
- Foam (for now, as a body material)
- Bamboo skewers (for now, for structure/support)
- Cardboard (for now, to help build the frame or for prototyping)
- 1 × Multimeter (**compulsory for safety!**)
- A few paper clips as servo linkages

---

## Getting Started

1. **Clone this repository:**
   ```sh
   git clone https://github.com/urnormalcoderbb/DIY-Animatronic-Endoskeleton.git
   ```
2. **Prepare your hardware:**  
   Gather your ESP32 modules, servos, and other listed materials.

3. **Upload the code:**  
   Flash the provided code to both ESP32s using Thonny IDE or any ESP32-Micropython-compatible platform.

4. **Build the endoskeleton:**  
   (3D files and full build guide coming soon! For now, use foam, bamboo skewers, and cardboard as a temporary structure.)  
   Use the 3d files in 3d endo plan for reference to build the body.  
   Now for the Hinges and Joints:  
   You can use simple Hinges and Joints. No need for gears at all!  
   Just search for simple hinges AND Movable joints in Robotics on Google, and you will see tons of them!

---

## Usage

- Power on both ESP32s.
- Note: Don't forget to give power to the Servo Driver, and don't forget to use the multimeter to measure voltage!
- Use the controller ESP32 (with joysticks) to send commands wirelessly to the endoskeleton ESP32.
- Please make sure to observe servo movements according to your programmed logic.

---

## Test Codes

This section contains test codes to help you verify your hardware and connections before assembling the full project.

<!--
Paste your test code samples and usage instructions here.
Example:
```
# Example: Servo Test Code
import machine
import time
# ...rest of your test code
```
-->

*Test codes for servos, wireless communication, and other modules will be provided here. Please check back soon or contribute your own!*

---

## Roadmap

- [x] Initial wireless code for ESP32s
- [ ] Provide 3D printable files
- [ ] Full build instructions with images
- [ ] Expand features (sensor integration, more DOF, etc.)
- [ ] Add comprehensive test codes and documentation

---

## License

This project is licensed under the [MIT License](LICENSE).

---

## Contributing

Feel free to open issues or pull requests! Suggestions and improvements are welcome.

---

## Contact

Questions? Ideas?  
Open an issue or reach out via [my GitHub profile](https://github.com/urnormalcoderbb).
