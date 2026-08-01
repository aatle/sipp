from math import sqrt
from struct import unpack
from time import sleep

from busio import I2C
from micropython import const

# MPU6xxx I2C Configuration
_MPU6xxx_ADDR = const(0x68)
_PWR_MGMT_1 = const(0x6B)
_ACCEL_CONFIG = const(0x1C)
_ACCEL_XOUT_H = const(0x3B)
_WHO_AM_I = const(0x75)

# 1G is ~9.81 m/s^2. At 16G full scale, raw value 2048 = 1G.
_ACCEL_SCALE_16G = const(2048.0)  # LSB/g at +/-16g range


class MPU6xxx:
    def __init__(self, i2c: I2C) -> None:
        self.i2c = i2c
        chip_id = self.read_register(_MPU6xxx_ADDR, _WHO_AM_I, bytearray(1))[0]
        if chip_id not in (0x68, 0x70):
            raise RuntimeError(f"MPU6xxx not detected; device ID: {hex(chip_id)}")
        self.buffer = bytearray(6)
        # Wake up MPU6xxx (clear sleep mode bit)
        self.write_register(_MPU6xxx_ADDR, _PWR_MGMT_1, 0x00)
        # Wait at least 30ms to wake up
        sleep(0.050)
        # Set full scale range to max, +/-16g (bits [4:3] = 1:1)
        self.write_register(_MPU6xxx_ADDR, _ACCEL_CONFIG, 0x18)

    def write_register(self, addr: int, reg: int, value: int) -> None:
        while not self.i2c.try_lock():
            pass
        try:
            self.i2c.writeto(addr, bytes((reg, value)))
        finally:
            self.i2c.unlock()

    def read_register(self, addr: int, reg: int, buffer: bytearray) -> bytearray:
        while not self.i2c.try_lock():
            pass
        try:
            self.i2c.writeto_then_readfrom(addr, bytes((reg,)), buffer)
        finally:
            self.i2c.unlock()
        return buffer

    def read_acceleration_g(self) -> float:
        buffer = self.read_register(_MPU6xxx_ADDR, _ACCEL_XOUT_H, self.buffer)
        # Unpack big-endian signed 16-bit integers
        ax, ay, az = unpack(">hhh", buffer)
        return sqrt(ax * ax + ay * ay + az * az) / _ACCEL_SCALE_16G
