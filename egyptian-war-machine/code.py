import board
import displayio
from adafruit_displayio_ssd1306 import SSD1306
from analogio import AnalogIn
from digit4x1 import Digit4x1
from digitalio import DigitalInOut
from i2cdisplaybus import I2CDisplayBus
from pwmio import PWMOut


def main() -> None:
    x_meter = AnalogIn(board.A1)
    y_meter = AnalogIn(board.A0)

    yaw_pwm = PWMOut(board.A4, frequency=50)
    pitch_pwm = PWMOut(board.A3, frequency=50)

    firing_in = DigitalInOut(board.A2)
    firing_in.switch_to_output()

    a_button = DigitalInOut(board.A5)
    b_button = DigitalInOut(board.D12)

    displayio.release_displays()

    i2c = board.I2C()
    display_bus = I2CDisplayBus(i2c, device_address=0x3C)
    display = SSD1306(display_bus, width=128, height=64)

    splash = displayio.Group()
    display.root_group = splash

    led_r = DigitalInOut(board.D13)
    led_r.switch_to_output()
    led_b = DigitalInOut(board.D0)
    led_b.switch_to_output()

    segments = tuple(  # abcdefg
        DigitalInOut(pin)
        for pin in (
            board.D1,
            board.D6,
            board.D10,
            board.D9,
            board.D7,
            board.D2,
            board.D8,
        )
    )
    digits = tuple(  # 1234
        DigitalInOut(pin) for pin in (board.D3, board.D4, board.D5, board.D11)
    )
    for pin in segments + digits:
        pin.switch_to_output()
    digit4x1 = Digit4x1(segments, digits)

    if False:
        from launcher import play_launcher

        play_launcher(
            x_meter, y_meter, a_button, b_button, yaw_pwm, pitch_pwm, firing_in
        )
    else:
        from egyptian_war import play_egyptian_war

        play_egyptian_war(a_button, b_button, splash, digit4x1, led_r, led_b)


main()
