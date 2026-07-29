import random
from math import sqrt
from time import sleep

import board
import digitalio

TICK_RATE: float = 30.0

# Increase to make velocity higher and duration slower
DECELERATION: float = 4.0

# Increase limits to make duration longer. Expand bounds for more variation.
CYCLE_RANGE: tuple[int, int] = 6, 8


LEDS = 6


leds = tuple(
    map(
        digitalio.DigitalInOut,
        (board.D2, board.D3, board.D4, board.D5, board.D6, board.D7),
    )
)
assert len(leds) == LEDS
for led in leds:
    led.direction = digitalio.Direction.OUTPUT


def set_led(index: int, *, on: bool) -> None:
    leds[index].value = on


def led_on(index: int) -> None:
    set_led(index, on=True)


def led_off(index: int) -> None:
    set_led(index, on=False)


def calculate_velocity(distance: float, acceleration: float = -DECELERATION) -> float:
    return sqrt(-2.0 * acceleration * distance)


def calculate_velocity_range(
    index: int, cycles: int = 0, start: float = 0.0, acceleration: float = -DECELERATION
) -> tuple[float, float]:
    velocity_min = calculate_velocity((index - start) % LEDS + LEDS * cycles)
    velocity_max = calculate_velocity(((index + 1 - start) % LEDS + LEDS * cycles))
    EPSILON = 0.001
    return (velocity_min + EPSILON, velocity_max - EPSILON)


def main() -> None:
    index = random.randrange(LEDS)
    cycles = random.randint(*CYCLE_RANGE)
    position = random.uniform(0.0, LEDS)
    velocity_range = calculate_velocity_range(index, cycles, position)
    velocity = random.uniform(*velocity_range)
    dt = 1.0 / TICK_RATE
    active = int(position) % LEDS
    led_on(active)

    while velocity > 0.0:
        sleep(dt)
        velocity -= 0.5 * DECELERATION * dt
        position += velocity * dt
        velocity -= 0.5 * DECELERATION * dt
        new_active = int(position) % LEDS
        if new_active != active:
            led_off(active)
            active = new_active
            led_on(active)

    sleep(0.5)
    led_off(active)
    sleep(0.1)
    led_on(active)
    sleep(1.0)
    led_off(active)
    if active != index:
        print("Error: simulation did not match calculation")


if __name__ == "__main__":
    main()
