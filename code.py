import board
import pulseio
import adafruit_irremote

ir_receiver = pulseio.PulseIn(board.GP16, maxlen=120, idle_state=True)
decoder = adafruit_irremote.GenericDecode()

def decode_ir_signals(p):
  codes = decoder.decode_bits(p)
  # El valor hexa: 00FDB001 es el boton on/off  
  return codes

while True:
  
  pulses = decoder.read_pulses(ir_receiver)
  try:
    received_code = decode_ir_signals(pulses)

    if received_code:
        hex_code = ''.join(["%02X" % x for x in received_code])
    print(f"Recibido: {hex_code}")

  except adafruit_irremote.IRNECRepeatException:  # Signal was repeated, ignore
    pass
  
  except adafruit_irremote.IRDecodeException:  # Failed to decode signal
    print("Error decoding")

