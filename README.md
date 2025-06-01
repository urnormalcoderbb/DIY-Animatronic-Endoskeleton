# DIY Animatronic Endoskeleton

Welcome to the DIY Animatronic Endoskeleton project!  
This project guides you through building your own animatronic endoskeleton using affordable, easy-to-find components—even if you have no prior experience with robotics or electronics.

**Key Features:**
- Wireless control using two ESP32 WROOM microcontrollers.
- Designed for hobbyists, makers, and anyone interested in animatronics.
- 3D-printable files for the endoskeleton (coming soon!).
- Step-by-step instructions and code provided.

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

---

## Getting Started

1. **Clone this repository:**
   ```sh
   git clone https://github.com/urnormalcoderbb/DIY-Animatronic-Endoskeleton.git
   ```
2. **Prepare your hardware:**  
   Gather your ESP32 modules, servos, and other listed materials.

3. **Upload the code:**  
   Flash the provided code to both ESP32s Thonny IDE or any ESP32-Micropython-compatible platform.

4. **Build the endoskeleton:**  
   (3D files and full build guide coming soon! For now, use foam, bamboo skewers, and cardboard as a temporary structure.)
   Use the 3d files in 3d endo plan for reference to build the body.
   Now for the Hinges and Joints:
   You can use simple Hinges and Joints. No need for gears at all!
   Just search for simple hinges AND Movable joints in Robotics on Google, and you will see tons of them!
   

---

## Usage

- Power on both ESP32s.
- Use the controller ESP32 (with joysticks) to send commands wirelessly to the endoskeleton ESP32.
- Please make sure to observe servo movements according to your programmed logic.

---

## Roadmap

- [x] Initial wireless code for ESP32s
- [ ] Provide 3D printable files
- [ ] Full build instructions with images
- [ ] Expand features (sensor integration, more DOF, etc.)

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
