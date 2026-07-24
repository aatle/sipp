from digitalio import DigitalInOut
from micropython import const

_PATTERNS = const((  # for digits 0-9
    0b1111110,
    0b0110000,
    0b1101101,
    0b1111001,
    0b0110011,
    0b1011011,
    0b1011111,
    0b1110000,
    0b1111111,
    0b1111011,
))


UPDATE_RATE = const(500)


class Digit4x1:
    BLANK_TEXT = "    "

    def __init__(
        self,
        segments: tuple[
            DigitalInOut,
            DigitalInOut,
            DigitalInOut,
            DigitalInOut,
            DigitalInOut,
            DigitalInOut,
            DigitalInOut,
        ],
        digits: tuple[DigitalInOut, DigitalInOut, DigitalInOut, DigitalInOut],
        *,
        common_anode: bool = True,
    ) -> None:
        self.segments = segments
        self.digits = digits
        self._text = self.BLANK_TEXT
        self.current_digit = 0
        self.common_anode = common_anode
        self._patterns = [0] * 4

    def update(self) -> None:
        common_anode = self.common_anode
        self.digits[self.current_digit].value = not common_anode
        self.current_digit = digit = (self.current_digit + 1) % 4
        pattern = self._patterns[digit]
        bit = 1
        for segment in reversed(self.segments):
            segment.value = (pattern & bit != 0) ^ common_anode
            bit <<= 1
        self.digits[digit].value = common_anode

    @property
    def text(self) -> str:
        return self._text

    @text.setter
    def text(self, value: str) -> None:
        if len(value) != 4:
            raise ValueError("value must be 4 characters")
        self._text = value
        self._patterns[:] = [
            _PATTERNS[int(char)] if char != " " else 0 for char in value
        ]
