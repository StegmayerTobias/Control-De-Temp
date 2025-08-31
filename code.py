import board
import pulseio
import adafruit_irremote
import adafruit_dht
import time

dhtDevice = adafruit_dht.DHT11(board.GP15)
ir_receiver = pulseio.PulseIn(board.GP16, maxlen=120, idle_state=True)
decoder = adafruit_irremote.GenericDecode()

def decode_ir_signals(p):
  codes = decoder.decode_bits(p)
  return codes

while True:
  try:
    # Print the values to the serial port
    temperature_c = dhtDevice.temperature
    temperature_f = temperature_c * (9 / 5) + 32
    humidity = dhtDevice.humidity
    print(f"Temp: {temperature_f:.1f} F / {temperature_c:.1f} C    Humidity: {humidity}% ")

  except RuntimeError as error:
    # Errors happen fairly often, DHT's are hard to read, just keep going
    print(error.args[0])
    
  except Exception as error:
    dhtDevice.exit()
    raise error
  
  print()
  print("Waiting for IR signal (5s)...")
  pulses = decoder.read_pulses(ir_receiver)
  time.sleep(5.0)
  
  
  if pulses:
    try:
      received_code = decode_ir_signals(pulses)
      if received_code:
     
        hex_code = ''.join(["%02X" % x for x in received_code])
        print(f"Recibido: {hex_code}")
    except adafruit_irremote.IRNECRepeatException:
      pass
    except adafruit_irremote.IRDecodeException:
      print("No IR signal detected")

  print()
    

  

