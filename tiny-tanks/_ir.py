from collections import namedtuple

IRMessage = namedtuple("IRMessage", ("pulses", "code"))
"Pulses and the code they were parsed into"

UnparseableIRMessage = namedtuple("UnparseableIRMessage", ("pulses", "reason"))
"Pulses and the reason that they could not be parsed into a code"

NECRepeatIRMessage = namedtuple("NECRepeatIRMessage", ("pulses",))
"Pulses interpreted as an NEC repeat code"


def bin_data(pulses: list[int]) -> list[list[int]]:
    """Compute bins of pulse lengths where pulses are +-25% of the average.

    :param list pulses: Input pulse lengths
    """
    bins = [[pulses[0], 0]]

    for pulse in pulses:
        for b, pulse_bin in enumerate(bins):
            if pulse_bin[0] * 0.75 <= pulse <= pulse_bin[0] * 1.25:
                bins[b][0] = (pulse_bin[0] + pulse) // 2  # avg em
                bins[b][1] += 1  # track it
                break
        else:
            bins.append([pulse, 1])
    return bins


def decode_bits(pulses: list[int]) -> tuple:
    """Decode the pulses into bits."""
    length = len(pulses)
    if (
        length == 3
        and 8000 <= pulses[0] <= 10000
        and 2000 <= pulses[1] <= 3000
        and 450 <= pulses[2] <= 700
    ):
        return NECRepeatIRMessage(length)

    if length < 10:
        return UnparseableIRMessage(length, "1")

    # Ignore any header (evens start at 1), and any trailer.
    pulses_end = -1 if length % 2 == 0 else None

    evens = pulses[1:pulses_end:2]
    odds = pulses[2:pulses_end:2]

    pulses.clear()

    # bin both halves
    even_bins = bin_data(evens)
    odd_bins = bin_data(odds)

    outliers = [b[0] for b in (even_bins + odd_bins) if b[1] == 1]
    even_bins[:] = [b for b in even_bins if b[1] > 1]
    odd_bins[:] = [b for b in odd_bins if b[1] > 1]

    if not even_bins or not odd_bins:
        return UnparseableIRMessage(length, "2")

    if len(even_bins) == 1:
        parity_pulses = odds
        pulse_bins = odd_bins
        del evens, even_bins
    elif len(odd_bins) == 1:
        parity_pulses = evens
        pulse_bins = even_bins
        del odds, odd_bins
    else:
        return UnparseableIRMessage(length, "3")

    if len(pulse_bins) == 1:
        return UnparseableIRMessage(length, "4")
    if len(pulse_bins) > 2:
        return UnparseableIRMessage(length, "5")

    mark = min(pulse_bins[0][0], pulse_bins[1][0])
    space = max(pulse_bins[0][0], pulse_bins[1][0])
    del pulse_bins

    if outliers:
        # skip outliers
        parity_pulses[:] = [
            p
            for p in parity_pulses
            if not (outliers[0] * 0.75) <= p <= (outliers[0] * 1.25)
        ]
    del outliers
    # convert marks/spaces to 0 and 1
    for i, pulse_length in enumerate(parity_pulses):
        if space * 0.75 <= pulse_length <= space * 1.25:
            parity_pulses[i] = True
        elif mark * 0.75 <= pulse_length <= mark * 1.25:
            parity_pulses[i] = False
        else:
            return UnparseableIRMessage(length, "6")

    # convert bits to bytes!
    output = [0] * ((len(parity_pulses) + 7) // 8)
    for i, pulse_length in enumerate(parity_pulses):
        output[i // 8] <<= 1
        if pulse_length != 0:
            output[i // 8] |= 1
    del parity_pulses
    return IRMessage(length, output)


class NonblockingGenericDecode:
    """
    Decode pulses into bytes in a non-blocking fashion.

    :param ~pulseio.PulseIn input_pulses: Object to read pulses from
    :param int max_pulse: Pulse duration to end a burst.  Units are microseconds.

    >>> pulses = PulseIn(...)
    >>> decoder = NonblockingGenericDecoder(pulses)
    >>> for message in decoder.read():
    ...     if isinstance(message, IRMessage):
    ...         message.code  # TA-DA! Do something with this in your application.
    ...     else:
    ...         # message is either NECRepeatIRMessage or
    ...         # UnparseableIRMessage. You may decide to ignore it, raise
    ...         # an error, or log the issue to a file. If you raise or log,
    ...         # it may be helpful to include message.pulses in the error message.
    ...         ...
    """

    def __init__(self, pulses, max_pulse: int = 10_000) -> None:
        self.pulses = pulses  # PulseIn
        self.max_pulse = max_pulse
        self._unparsed_pulses: list[int] = []  # internal buffer of partial messages

    def read(self):
        """
        Consume all pulses from PulseIn. Yield decoded messages, if any.

        If a partial message is received, this does not block to wait for the
        rest. It stashes the partial message, to be continued the next time it
        is called.
        """
        # Consume from PulseIn.
        while self.pulses:
            pulse = self.pulses.popleft()
            if pulse <= self.max_pulse:
                self._unparsed_pulses.append(pulse)
            else:
                # End of message! Decode it and yield a BaseIRMessage.
                result = decode_bits(self._unparsed_pulses)
                self._unparsed_pulses.clear()
                yield result
