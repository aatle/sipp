from digitalio import DigitalInOut
from micropython import const


def map_range(
    x: float, in_min: float, in_max: float, out_min: float, out_max: float
) -> float:
    """
    Maps a number from one range to another.
    Note: This implementation handles values < in_min differently than arduino's map function does.

    :return: Returns value mapped to new range
    :rtype: float
    """
    in_range = in_max - in_min
    in_delta = x - in_min
    if in_range != 0:
        mapped = in_delta / in_range
    elif in_delta != 0:
        mapped = in_delta
    else:
        mapped = 0.5
    mapped *= out_max - out_min
    mapped += out_min
    if out_min <= out_max:
        return max(min(mapped, out_max), out_min)
    return min(max(mapped, out_max), out_min)


def ema_filter(
    alpha: float, current_value: float, previous_filtered_value: float | None = None
) -> float:
    if previous_filtered_value is None:
        return current_value
    return alpha * current_value + (1 - alpha) * previous_filtered_value


class Button:
    SHORT_PRESS_DURATION = const(0.2)

    NO_PRESS = const(0)
    SHORT_PRESS = const(1)
    LONG_PRESS = const(2)

    def __init__(self, pin: DigitalInOut) -> None:
        self.pin = pin
        self.last_value = pin.value
        self.last_press = 0.0

    def update(self, time: float) -> int:
        value = self.pin.value
        if value != self.last_value:
            self.last_value = value
            if not value:
                return (
                    self.SHORT_PRESS
                    if time - self.last_press < self.SHORT_PRESS_DURATION
                    else self.LONG_PRESS
                )
            self.last_press = time
        return self.NO_PRESS
