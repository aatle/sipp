from time import sleep

from adafruit_motor.servo import Servo
from analogio import AnalogIn
from digitalio import DigitalInOut
from micropython import const
from pwmio import PWMOut
from util import ema_filter, map_range

_MIN_YAW = const(0.0)
_MAX_YAW = const(180.0)

_MIN_PITCH = const(19.0)
_MAX_PITCH = const(79.0)

_RESPONSE_TIME = const(0.01)

_TICK_RATE = const(1000)

_MIN_PULSE = const(575)
_MAX_PULSE = const(2400)


def play_launcher(
    x_meter: AnalogIn,
    y_meter: AnalogIn,
    a_button: DigitalInOut,
    b_button: DigitalInOut,
    yaw_pwm: PWMOut,
    pitch_pwm: PWMOut,
    firing_in: DigitalInOut,
) -> None:
    dt = 1 / _TICK_RATE
    alpha = dt / (_RESPONSE_TIME + dt)
    x = y = None
    yaw_servo = Servo(yaw_pwm, min_pulse=_MIN_PULSE, max_pulse=_MAX_PULSE)
    pitch_servo = Servo(pitch_pwm, min_pulse=_MAX_PULSE, max_pulse=_MIN_PULSE)
    while True:
        sleep(dt)
        x, y = ema_filter(alpha, x_meter.value, x), ema_filter(alpha, y_meter.value, y)
        yaw = map_range(x, 65535, 0, _MIN_YAW, _MAX_YAW)
        pitch = map_range(y, 0, 65535, _MIN_PITCH, _MAX_PITCH)
        yaw_servo.angle = yaw
        pitch_servo.angle = pitch
        firing_in.value = a_button.value
