import adafruit_irremote
import board
import pulseio

pulse_in = pulseio.PulseIn(board.D2, maxlen=120, idle_state=False)
decoder = adafruit_irremote.GenericDecode()

print("Ready")

while True:
    pulses = decoder.read_pulses(pulse_in)
    if pulses:
        try:
            bits = decoder.decode_bits(pulses)
            hexes = [f"{b:02X}" for b in bits]
            print(f"HEX: {', '.join(hexes)}")
        except adafruit_irremote.IRNECRepeatException:
            print("REPEAT EXCEPTION")
        except adafruit_irremote.IRDecodeException:
            print("DECODE EXCEPTION")
