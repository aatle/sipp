from collections import namedtuple
from time import monotonic

import board
import ir
import servo
from digitalio import DigitalInOut
from micropython import const
from mpu6xxx import MPU6xxx
from pulseio import PulseIn
from pwmio import PWMOut

_NEC_REPEAT_WINDOW_START = const(0.102)
"""Time in seconds since last NEC repeat message for it to be considered correct."""
_NEC_REPEAT_WINDOW_END = const(0.116)
"""Time in seconds since last NEC repeat message until repeat is considered to end."""


_COLLISION_THRESHOLD_G = const(6.0)


_TURRET_ROTATION_SPEED = const(20.0)
_TURRET_CORRECTION_TIME = const(0.0)

_TURRET_STARTUP_CORRECTION_TIME = const(0.25)
"""Time in seconds for the turret to start up to its initial angle."""

_FIRING_DURATION = const(0.75)

_FIRING_INVULNERABILITY = const(_FIRING_DURATION + 0.05)

_HIT_INVULNERABILITY = const(1.0)

_INITIALIZATION_INVULNERABILITY = const(1.0)

_TANK_HEALTH = const(3)


_COMMANDS_PATH = const("commands.txt")


Command = int
State = int
Signal = namedtuple("Signal", ("state", "command"))


_PRESS = const(1)
_HOLD = const(2)
_RELEASE = const(3)

_UP = const(1)
_LEFT = const(2)
_DOWN = const(3)
_RIGHT = const(4)
_CENTER = const(5)
_UP_LEFT = const(6)
_UP_RIGHT = const(7)


initial_time = monotonic()


def log(message: object) -> None:
    print(f"t = {monotonic() - initial_time:.3f}s: {message}")


_MAX_VALUE = const(65535)


class RGBLed:
    def __init__(self, r: PWMOut, g: PWMOut, b: PWMOut) -> None:
        self._color = 0.0, 0.0, 0.0
        self.r = r
        self.g = g
        self.b = b
        self.blink_end_time: float | None = None
        self.duty_cycle = 0.0
        self.frequency = 0.0

    @property
    def leds(self) -> tuple[PWMOut, PWMOut, PWMOut]:
        return self.r, self.g, self.b

    @property
    def color(self) -> tuple[float, float, float]:
        return self._color

    @color.setter
    def color(self, value: tuple[float, float, float]) -> None:
        if value == self._color:
            return
        for led, component in zip(self.leds, value):
            led.duty_cycle = round(component * _MAX_VALUE)
        self._color = value

    def blink(
        self,
        duty_cycle: float,
        frequency: float,
        duration: float,
        color: tuple[float, float, float] | None = None,
    ) -> None:
        self.blink_end_time = monotonic() + duration
        self.duty_cycle = duty_cycle
        self.frequency = frequency
        if color is not None:
            self.color = color

    def update(self) -> None:
        if self.blink_end_time is None:
            return
        left = self.blink_end_time - monotonic()
        if left <= 0.0:
            self.blink_end_time = None
            self.color = self.color
            on = True
        else:
            on = (left * self.frequency) % 1.0 < self.duty_cycle
        if on:
            for led, component in zip(self.leds, self.color):
                led.duty_cycle = round(component * _MAX_VALUE)
        else:
            for led in self.leds:
                led.duty_cycle = 0

    def is_blinking(self) -> bool:
        return self.blink_end_time is not None


class IRRemote:
    def __init__(self, ir_receiver: PulseIn, _COMMANDS_PATH: str) -> None:
        (
            self.identity,
            self.up,
            self.left,
            self.down,
            self.right,
            self.center,
            self.up_left,
            self.up_right,
        ) = self.load_commands(_COMMANDS_PATH)
        self.decoder = ir.NonblockingGenericDecode(ir_receiver)
        self.current_command: Command | None = None
        self.last_repeat = monotonic()
        self.repeat_count = 0

    @staticmethod
    def load_commands(_COMMANDS_PATH: str) -> list[Command]:
        with open(_COMMANDS_PATH) as f:
            commands = f.readline().partition("-")[0]
        identity, commands = commands.split(";")
        return [int(code, 16) for code in [identity] + commands.split(",")]

    def update(self) -> Signal | None:
        time = monotonic()
        for message in self.decoder.read():
            # log_ir_message(message)
            if isinstance(message, ir.IRMessage):
                if len(message.code) < 2:
                    continue
                identity = message.code[1]
                if identity != self.identity:
                    continue
                code = message.code[-1]
                if code == self.up:
                    command = _UP
                elif code == self.down:
                    command = _DOWN
                elif code == self.left:
                    command = _LEFT
                elif code == self.right:
                    command = _RIGHT
                elif code == self.center:
                    command = _CENTER
                elif code == self.up_left:
                    command = _UP_LEFT
                elif code == self.up_right:
                    command = _UP_RIGHT
                else:
                    continue
                self.current_command = command
                self.last_repeat = time
                self.repeat_count = 0
                return Signal(_PRESS, command)
            if isinstance(message, ir.NECRepeatIRMessage):
                if self.current_command is None:
                    continue
                duration = time - self.last_repeat
                # log(f"NEC repeat (delay {duration:.3f}s)")
                if _NEC_REPEAT_WINDOW_START <= duration <= _NEC_REPEAT_WINDOW_END:
                    self.last_repeat = time
                    self.repeat_count += 1
            elif isinstance(message, ir.UnparseableIRMessage):
                pass
            else:
                raise TypeError(message)

        current_command = self.current_command
        if current_command is not None:
            if time - self.last_repeat <= _NEC_REPEAT_WINDOW_END:
                return Signal(_HOLD, current_command)
            self.current_command = None
            return Signal(_RELEASE, current_command)
        return None


# def log_ir_message(message) -> None:
#     log("IR message received")
#     print(f"Pulses ({len(message.pulses)}): {message.pulses}")
#     if isinstance(message, ir.IRMessage):
#         hexes = [f"{bit:02X}" for bit in message.code]
#         print(f"IR Message, code: {' '.join(hexes)}")
#     elif isinstance(message, ir.NECRepeatIRMessage):
#         print("NEC Repeat Message")
#     elif isinstance(message, ir.UnparseableIRMessage):
#         print(f"Unparseable Message, reason: {message.reason}")
#     else:
#         raise TypeError(message)
#     print("---")


_TURRET_ACTUATION_RANGE = const(180)
_TURRET_MIN_PULSE = const(575)
_TURRET_MAX_PULSE = const(2400)

_FORWARD = const(0b01)
_BACKWARD = const(0b10)
_COAST = const(0b00)
_BRAKE = const(0b11)


class Tank:
    def __init__(
        self,
        left_forward: DigitalInOut,
        left_backward: DigitalInOut,
        right_forward: DigitalInOut,
        right_backward: DigitalInOut,
        firing_pwm_out: PWMOut,
        turret_pwm_out: PWMOut,
        mpu: MPU6xxx,
        rgb_led: RGBLed,
    ) -> None:
        self.left_forward = left_forward
        self.left_backward = left_backward
        self.right_forward = right_forward
        self.right_backward = right_backward
        self._left_drive = _COAST
        self._right_drive = _COAST
        self.firing_servo = servo.ContinuousServo(firing_pwm_out)
        self.turret_servo = servo.Servo(
            turret_pwm_out,
            actuation_range=_TURRET_ACTUATION_RANGE,
            min_pulse=_TURRET_MIN_PULSE,
            max_pulse=_TURRET_MAX_PULSE,
        )
        self.turret_angle = 90.0
        self.turret_rotation_speed = _TURRET_ROTATION_SPEED
        self.turret_correction_end_time: float | None = (
            monotonic() + _TURRET_STARTUP_CORRECTION_TIME
        )
        self.fire_start_time: float | None = None
        self.mpu = mpu
        self.invulnerability_end_time: float | None = None
        self.rgb_led = rgb_led
        self.health = _TANK_HEALTH
        self.set_invulnerability(_INITIALIZATION_INVULNERABILITY)

    @property
    def left_drive(self) -> None:
        return self._left_drive

    @left_drive.setter
    def left_drive(self, value: int) -> None:
        if self.health <= 0:
            value = _COAST
        self.left_forward.value = bool(value & 0b01)
        self.left_backward.value = bool(value & 0b10)
        self._left_drive = value

    @property
    def right_drive(self) -> None:
        return self._right_drive

    @right_drive.setter
    def right_drive(self, value: int) -> None:
        if self.health <= 0:
            value = _COAST
        self.right_forward.value = bool(value & 0b01)
        self.right_backward.value = bool(value & 0b10)
        self._right_drive = value

    def drive(self, left_drive: int, right_drive: int) -> None:
        self.left_drive = left_drive
        self.right_drive = right_drive

    def forward(self) -> None:
        log("FORWARD")
        self.drive(_FORWARD, _FORWARD)

    def left(self) -> None:
        self.drive(_BACKWARD, _FORWARD)

    def backward(self) -> None:
        self.drive(_BACKWARD, _BACKWARD)

    def right(self) -> None:
        self.drive(_FORWARD, _BACKWARD)

    def coast(self) -> None:
        self.drive(_COAST, _COAST)

    def brake(self) -> None:
        self.drive(_BRAKE, _BRAKE)

    def fire(self) -> None:
        if self.fire_start_time is not None:
            return
        log("FIRE")
        DIRECTION = -1.0
        self.firing_servo.throttle = DIRECTION
        time = monotonic()
        self.fire_start_time = time
        self.set_invulnerability(_FIRING_INVULNERABILITY)

    @property
    def turret_angle(self) -> float:
        return self._turret_angle

    @turret_angle.setter
    def turret_angle(self, value: float) -> None:
        value = min(max(value, 0.0), 180.0)
        self._turret_angle = value
        self.turret_servo.angle = round(value)
        self.turret_correction_end_time = monotonic() + _TURRET_CORRECTION_TIME

    def rotate_turret_ccw(self, dt: float) -> None:
        self.turret_angle += self.turret_rotation_speed * dt

    def rotate_turret_cw(self, dt: float) -> None:
        self.turret_angle -= self.turret_rotation_speed * dt

    def hit(self) -> None:
        log(f"HIT, health {self.health} -> {self.health - 1}")
        self.health -= 1
        self.set_invulnerability(_HIT_INVULNERABILITY)
        self.rgb_led.blink(0.5, 3, 1.0, (1.0, 0.0, 0.0))

        self.turret_rotation_speed -= _TURRET_ROTATION_SPEED / _TANK_HEALTH

    def set_invulnerability(self, duration: float) -> None:
        end_time = monotonic() + duration
        if self.invulnerability_end_time is None:
            self.invulnerability_end_time = end_time
        else:
            self.invulnerability_end_time = max(self.invulnerability_end_time, end_time)

    def get_health_color(self) -> tuple[float, float, float]:
        health = self.health
        if health > 3:
            return (1.0, 1.0, 1.0)
        if health == 3:
            return (0.0, 0.0, 1.0)
        if health == 2:
            return (0.0, 1.0, 0.0)
        if health == 1:
            return (1.0, 0.5, 0.0)
        return (1.0, 0.0, 0.0)

    def update(self) -> None:
        time = monotonic()
        self.rgb_led.update()
        if not self.rgb_led.is_blinking():
            self.rgb_led.color = self.get_health_color()
        if (
            self.turret_correction_end_time is not None
            and time > self.turret_correction_end_time
        ):
            self.turret_servo.angle = None
            self.turret_correction_end_time = None
        if (
            self.fire_start_time is not None
            and time - self.fire_start_time >= _FIRING_DURATION
        ):
            self.firing_servo.throttle = 0.0
            self.fire_start_time = None
        if (
            self.invulnerability_end_time is not None
            and time > self.invulnerability_end_time
        ):
            self.invulnerability_end_time = None
        if self.mpu.read_acceleration_g() >= _COLLISION_THRESHOLD_G:
            if self.invulnerability_end_time is None:
                self.hit()


def main() -> None:
    ir_receiver = PulseIn(board.D7, maxlen=120, idle_state=True)
    in1 = DigitalInOut(board.D3)
    in2 = DigitalInOut(board.D4)
    in3 = DigitalInOut(board.D5)
    in4 = DigitalInOut(board.D6)
    for in_pin in (in1, in2, in3, in4):
        in_pin.switch_to_output()
    firing_pwm_out = PWMOut(board.D11, frequency=50)
    turret_pwm_out = PWMOut(board.D9, frequency=50)
    rgb_led = RGBLed(
        PWMOut(board.D13),
        PWMOut(board.A2),
        PWMOut(board.D12),
    )
    i2c = board.I2C()
    mpu = MPU6xxx(i2c)

    tank = Tank(in2, in1, in4, in3, firing_pwm_out, turret_pwm_out, mpu, rgb_led)
    ir_remote = IRRemote(ir_receiver, _COMMANDS_PATH)
    loop(tank, ir_remote)


def loop(tank: Tank, ir_remote: IRRemote) -> None:
    previous_time = monotonic()
    while True:
        current_time = monotonic()
        dt = current_time - previous_time
        previous_time = current_time

        tank.update()
        signal = ir_remote.update()
        if signal is None:
            continue
        if signal.state != _HOLD:
            log(signal)
        command = signal.command
        if signal.state == _PRESS:
            if command == _UP:
                tank.forward()
            elif command == _LEFT:
                tank.left()
            elif command == _DOWN:
                tank.backward()
            elif command == _RIGHT:
                tank.right()
            elif command == _CENTER:
                tank.fire()
        elif signal.state == _HOLD:
            if command == _UP_LEFT:
                tank.rotate_turret_ccw(dt)
            elif command == _UP_RIGHT:
                tank.rotate_turret_cw(dt)
        elif signal.state == _RELEASE:
            tank.coast()
        else:
            raise ValueError(signal.state)
