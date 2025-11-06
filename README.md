# DIY Animatronic Endoskeleton

[![MIT License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Welcome to the DIY Animatronic Endoskeleton project! This project guides you through building your own animatronic endoskeleton that can wave and interact with people using affordable, easy-to-find components—perfect for beginners with no prior robotics experience.

## 🌟 Key Features

- **Wireless Control**: Powered by two ESP32 WROOM microcontrollers for reliable remote operation
- **Beginner-Friendly**: Designed for hobbyists, makers, and anyone interested in animatronics
- **Interactive**: Can wave and greet people with programmable movements
- **Articulated Design**: Features a movable jaw with configurable motion patterns
- **Open Source**: Complete with documentation, code, and upcoming 3D-printable files
- **Expandable**: Basic foundation that can be enhanced with additional features

## 🛠️ Required Materials

### Electronics
- 2× ESP32 WROOM microcontrollers
- 6× SG90 servo motors
- 4× MG90S servo motors
- 1× PCA9685 servo driver
- 2× Analog joysticks
- 1× 5V 5A power supply (readily available on eBay/Amazon)
- Assorted jumper wires (F-F, M-F, M-M)
- 1× Multimeter (mandatory for safety)

### Structure Materials
- Foam (temporary body material)
- Bamboo skewers (temporary structure/support)
- Cardboard (prototyping and frame construction)
- Paper clips (servo linkages)

## 🚀 Getting Started

### 1. Setup
```sh
git clone https://github.com/urnormalcoderbb/DIY-Animatronic-Endoskeleton.git
cd DIY-Animatronic-Endoskeleton
```

### 2. Hardware Preparation
1. Gather all required materials listed above
2. Test all servo motors before assembly
3. Verify power supply output with multimeter
4. Set up both ESP32 modules for programming

### 3. Software Installation
1. Use Thonny IDE or any ESP32-MicroPython compatible platform
2. Get the receiver ESP32's MAC address using `getmac.py` from the test codes directory
3. Flash the controller code to the first ESP32
4. Flash the receiver code to the second ESP32

### 4. Assembly Instructions
1. Refer to the [build plans](https://github.com/urnormalcoderbb/DIY-Animatronic-Endoskeleton/tree/main/Endo%20build%20plan%20PDFS) for detailed guidance
2. Follow the schematics diagram in the main file
3. Use the 3D files in the `3d endo plan` directory as reference
4. For hinges and joints:
   - Simple mechanical joints work well (no gears required)
   - Reference the Ultimate Animatronic Endoskeleton Project Plan P3 PDF for joint designs
   - Search online for basic robotics joints and hinges for inspiration

## 🔧 Testing & Usage

1. **Power Up**
   - Turn on both ESP32 modules
   - Supply power to the Servo Driver (verify voltage with multimeter)
   - Allow system to initialize

2. **Operation**
   - Use the controller ESP32 with joysticks to send wireless commands
   - Monitor servo responses and movement patterns
   - Make adjustments to programming as needed

3. **Test Codes**
   Visit our [test codes directory](https://github.com/urnormalcoderbb/DIY-Animatronic-Endoskeleton/tree/main/tests) for:
   - Component verification scripts
   - Connection testers
   - Wireless communication tests

## 📑 Project Status

### Completed
- ✅ ESP32 wireless communication implementation
- ✅ Comprehensive build instructions
- ✅ Test code suite and documentation

### In Progress
- 🔄 3D printable files creation
- 🔄 Feature expansion (sensors, degrees of freedom)

## 🤝 Contributing

We welcome contributions! Feel free to:
- Open issues for bugs or suggestions
- Submit pull requests for improvements
- Share your builds and modifications

## 📬 Contact & Support

- Open an [issue](https://github.com/urnormalcoderbb/DIY-Animatronic-Endoskeleton/issues) for questions
- Visit [my GitHub profile](https://github.com/urnormalcoderbb) for direct contact

## 📜 License

This project is licensed under the [MIT License](LICENSE).