# UCSD SIPP Robotics Projects

[![Platform](https://img.shields.io/badge/Platform-Adafruit%20Metro%20M0%20Express-red.svg)](https://www.adafruit.com/product/3505)
[![Language](https://img.shields.io/badge/Language-CircuitPython%20%2F%20MicroPython%20Bytecode-yellow.svg)](https://circuitpython.org/)
[![UCSD SIPP](https://img.shields.io/badge/UCSD%20SIPP-Double%20Award%20Winner-gold.svg)](#awards--recognition)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

This repository contains the firmware, hardware integration designs, and engineering documentation for two award-winning embedded systems projects developed during the UC San Diego Summer Internship Preparatory Program (SIPP) (September 2026), hosted by the Department of Electrical and Computer Engineering (ECE).

Both systems were designed and programmed for the Adafruit Metro M0 Express. Techniques include real-time firmware, non-blocking protocol design, sensor drivers, signal filtering, display multiplexing, and aggressive memory optimization (due to limited 32 KB SRAM).

---

## Awards & Recognition

| Project | Distinction(s) | Event | Scope |
| :--- | :--- | :--- | :--- |
| [**Tiny Tanks**](tiny-tanks/) | **Best Project (1st Place)** | SIPP Final Project | 7 teams (in assigned track) |
| [**Egyptian War Machine**](egyptian-war-machine/) | **Best Engineering Design**<br/>**People’s Choice Award** | SIPP Hackathon | 21 teams |

See the program recognition/awards slides [here](https://drive.google.com/file/d/1J1mdxewN5GnLHIc4jr8RVSD7sphNR46r/view?usp=sharing).

---

## Projects Overview

```
sipp/
├── tiny-tanks/            # Final Project: Two-player wireless combat tanks
│   └── README.md          # Technical documentation
├── egyptian-war-machine/  # Hackathon Project: Reflex card game & 2-DOF launcher
│   └── README.md          # Technical documentation
├── compile.sh             # Host-side MicroPython pre-compilation script
└── mpy-cross-windows-*    # Static mpy-cross compiler executable
```

---

### 1. [Tiny Tanks](tiny-tanks/) - Real-Time Wireless Combat Tanks
> **Best Project (Track 3)**, UCSD SIPP Final Project - [Project Documentation](tiny-tanks/README.md)

View the [presentation slides](https://docs.google.com/presentation/d/1WQiBEisVg-VB_Z7gBrMVnCJ5no2UjBza7oZm0h-AR4Y/edit?usp=sharing)!

* **Hardware**: Metro M0 Express, H-Bridge DC motors, 180 degree pan servo, continuous firing servo, MPU6050 6-DOF IMU, RGB status LED.
* **Firmware & Control**: Differential steering, dynamic impact detection via accelerometer thresholding, battle damage/injury degradation, and single-push projectile firing.
* **Low-level Protocol Engineering**: Designed NEC decoder with multi-user address filtering to avoid packet collisions across multiple remotes, as well as NEC repeat message timing windows to differentiate identical, unidentifiable NEC repeat messages.
* **32 KB RAM Optimization**: Mitigated severe 32 KB SRAM ceilings by modifying bloated vendor libraries: zero-allocation buffers, in-place array manipulation, etc. Rewrote Adafruit's `irremote` and `mpu6050` libraries by stripping out and optimizing code to save memory. Pre-compiled entire codebase using maximum optimization level (`-O3`) to save code size.

---

### 2. [Egyptian War Machine](egyptian-war-machine/) - Reflex Card Game & 2-DOF Projectile Launcher
> **Best Engineering Design & People’s Choice**, UCSD SIPP Hackathon - [Project Documentation](egyptian-war-machine/README.md)

View the [video](https://drive.google.com/file/d/1T_9Ks87VnYDBUHqNeeMATJvqaxq6kMD4/view?usp=sharing)!

* **Dual-Feature Mechatronics**: Engineered a multi-function embedded entertainment system combining an interactive reflex card game (Egyptian War / Egyptian Rat Screw) and a high-powered motorized pan-tilt projectile (LEGO) launcher.
* **Signal Conditioning**: Implemented a discrete first-order Exponential Moving Average (EMA) low-pass filter ($\tau = 10\,\text{ms}$, $1000\,\text{Hz}$ tick rate) on dual-axis analog inputs to reduce potentiometer jitter while minimizing control latency.
* **Display Multiplexing**: Built a custom 500 Hz time-division asynchronous multiplexed driver for a 4-digit 7-segment display across 11 raw GPIO pins with anti-ghosting state transitions, maintaining flicker-free persistence, alongside an SSD1306 128x64 OLED display.
* **Disk Bitmap Graphics**: Streamed 52 individual playing card bitmaps directly from SPI Flash to the OLED frame buffer using `displayio.OnDiskBitmap` instead of storing image in RAM.

---

## Engineering Techniques

### 1. Real-Time Embedded Architecture & Asynchronous Event Loops
Microcontrollers operating without a real-time OS (RTOS) require cooperative, non-blocking execution models. In both projects, blocking `delay()` / `sleep()` operations were replaced with timestamp-based monotonic event loops (`monotonic()`). Displays, motor commutations, debouncers, and sensor polling run concurrently without starvation.

### 2. Low-Level Communication Protocols & Register Drivers
* **NEC Infrared Protocol**: Built a custom driver for NEC message decoding that can safely handle multiple remotes as well as configure and use any compatible IR remote.
* **Hardware I2C Register Driver**: Designed compacted bare-metal register drivers for the MPU6050 accelerometer, waking the sensor, setting full-scale $\pm 16\,\text{g}$ sensitivity, and decoding 16-bit big-endian signed 2's-complement integers via `struct.unpack(">hhh", ...)`.
* **I2C DisplayBus**: Interfaced SSD1306 monochrome OLED displays via hardware I2C at address `0x3C`.

### 3. Resource-Constrained Embedded Optimization (32 KB RAM)
The ATSAMD21G18 microcontroller provides only 32 KB of SRAM, the majority of which is reserved for the CircuitPython runtime stack. Standard Python library bundles immediately exhaust the remaining heap.
* **Bytecode Cross-Compilation**: Host-side compilation with `mpy-cross -O3` strips docstrings, removes line numbers, and bypasses on-chip AST generation.
* **Static Allocation & Zero-GC Operation**: Reused static byte buffers (`bytearray(6)`) for cyclic sensor reads, eliminating garbage collection latency spikes.
* **Scope Pruning & In-Place Slicing**: Replaced memory-allocating list concatenations with slice replacements (`[:]`) and explicit `del` invocations.
* **Compile-Time Constant Folding**: Used `micropython.const()` to fold integers and hardware registers directly into bytecode opcodes.
* **Massive Code Compression**: Reduced number of modules and functions, as well as line number count, to save memory used by the loaded program code. Also stripped down, optimized, and re-compiled library modules.

### 4. Analog Signal Conditioning & Noise Suppression
Analog joystick potentiometers exhibit mechanical chatter and electrical ADC noise. Implementing a first-order Exponential Moving Average (EMA) low-pass filter:
$$y[k] = \alpha \cdot x[k] + (1 - \alpha) \cdot y[k-1], \quad \alpha = \frac{\Delta t}{\tau + \Delta t}$$
filtered out high-frequency fluctuations while preserving smooth, lag-free mechanical tracking for high-torque servo linkages.

### 5. Hardware-Software Co-Design & IO Multiplexing
* Direct 11-pin time-division multiplexing for a 4-digit 7-segment display at 500 Hz without dedicated driver ICs (MAX7219/TM1637).
* Dual-action input multiplexing: single tactile buttons distinguish between rapid reflex slaps ($< 200\,\text{ms}$) and intentional card dealing ($\ge 200\,\text{ms}$).
* Idle servo de-energizing (`duty_cycle = 0`) to eliminate gear buzz, reduce heat, and prevent brownouts on the 5V rail.

---

## Compilation

Use [compile.sh](compile.sh), which uses `mpy-cross`:

```bash
# Compile all source files (_*.py) to bytecode (.mpy)
./compile.sh
```

By default, it uses `-O3`, which strips line numbers (from errors).

---

## Repository Structure

```
├── .gitignore                           # Git ignore rules
├── LICENSE                              # MIT License
├── README.md                            # Portfolio overview & engineering highlights
├── compile.sh                           # Pre-compilation script for MicroPython bytecode
├── pyproject.toml                       # Python project definition and dev tooling
├── mpy-cross-windows-10.2.1.static.exe  # MicroPython cross-compiler binary
│
├── tiny-tanks/                          # Tiny Tanks Project
│   ├── README.md                        # System documentation
│   ├── commands.txt                     # Remote ID and IR hex command mappings
│   ├── code.py                          # Hardware boot entry point
│   ├── _main.py                         # Game state machine & motion coordinator
│   ├── _ir.py                           # Non-blocking NEC IR decoder
│   ├── _mpu6xxx.py                      # Bare-metal MPU6050 I2C driver
│   ├── _servo.py                        # Calibrated PWM servo drivers
│   ├── main.mpy                         # Pre-compiled bytecode
│   ├── ir.mpy                           # Pre-compiled bytecode
│   ├── mpu6xxx.mpy                      # Pre-compiled bytecode
│   └── servo.mpy                        # Pre-compiled bytecode
│
└── egyptian-war-machine/                # Egyptian War Machine
    ├── README.md                        # System documentation
    ├── code.py                          # Bootloader and mode selector
    ├── cards-bmp/                       # 52 monochrome card sprites (44x64 BMP)
    ├── _launcher.py                     # 2-DOF EMA joystick & servo aim loop
    ├── _egyptian_war.py                 # Asynchronous card game engine
    ├── _egyptian_war_combos.py          # Reflex slap combination algorithms
    ├── _digit4x1.py                     # 500 Hz time-division 7-segment multiplexer
    ├── _card.py                         # Card rank/suit bitwise packing
    ├── _util.py                         # EMA filter, range mapping, button debounce
    └── *.mpy                            # Pre-compiled bytecode binaries
```

---

## Author & Acknowledgements

* **Author**: Anthony Le
* **Projects Partner**: Duke Coats
* **Institution**: University of California, San Diego
* **Program**: Summer Internship Preparatory Program (SIPP), Department of Electrical & Computer Engineering (ECE)
* **License**: This project is licensed under the [MIT License](LICENSE).
