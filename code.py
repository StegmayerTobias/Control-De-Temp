import board
import pulseio
import adafruit_irremote
import adafruit_dht
import time
import pwmio
import digitalio

DHT_PIN = board.GP15
IR_PIN = board.GP16
BUZZER_PIN = board.GP17
RELAY_PIN = board.GP14

IR_CODE_TURNOFF = '00FDB04F'
IR_CODE_RESET = '00FD48B7'

dht_sensor = adafruit_dht.DHT11(DHT_PIN)
ir_sensor = pulseio.PulseIn(IR_PIN, maxlen=120, idle_state=True)
buzzer = pwmio.PWMOut(BUZZER_PIN, duty_cycle=0, frequency=1000, variable_frequency=True)
relay = digitalio.DigitalInOut(RELAY_PIN)
relay.direction = digitalio.Direction.OUTPUT
decoder = adafruit_irremote.GenericDecode()

warning = False
alarm_on = True

def beep(frequency=880, duration=0.2):
    buzzer.duty_cycle = 2**15
    buzzer.frequency = frequency
    time.sleep(duration)
    buzzer.duty_cycle = 0

def decode_ir_signals(p):
  codes = decoder.decode_bits(p)
  return codes

def activate_alarm_sound():
  beep()         
  time.sleep(0.2)             
  beep()

def alarm_turnOnOff_sound():
  # Aca cambio el sonido del beep en frecuencia y velocidad para que indique que la alarma se desactivo
  beep(frequency=800, duration=0.06)
  time.sleep(0.06)
  beep(frequency=800, duration=0.06)

def handle_ir_signal():
  global alarm_on, warning
  try:
    pulses = decoder.read_pulses(ir_sensor)
    received_code = decoder.decode_bits(pulses)
    if received_code:
      hex_code = ''.join(["%02X" % x for x in received_code])
      
      if hex_code == IR_CODE_TURNOFF:
        print(f"Recibido: {hex_code} | Botón OFF | Alarma apagada")
        if warning:
          alarm_turnOnOff_sound()
          warning = False
          alarm_on = False
      elif hex_code == IR_CODE_RESET:
        print(f"Recibido: {hex_code} | Botón RESET | Alarma reseteada")
        alarm_on = True
      else:
        print(f"Boton desconocido. Presione OFF para apagar o RESET para reiniciar la alarma.")
                
  except adafruit_irremote.IRNECRepeatException:
    pass
  except adafruit_irremote.IRDecodeException:
    print("No se detectó una señal IR válida.")

def check_temp_and_humidity():
  global alarm_on, warning
  try:
    temperature_c = dht_sensor.temperature
    humidity = dht_sensor.humidity

    relay.value = temperature_c > 27

    if temperature_c > 30 and alarm_on:
      warning = True
  
    print(f"Temp: {temperature_c:.1f} C  |  Humidity: {humidity}% ")

  except RuntimeError as error:
    print(error.args[0])
    
  except Exception as error:
    dht_sensor.exit()
    raise error

print("-----------------------------")
print("Sistema de monitoreo iniciado")
print("-----------------------------")
while True:

  check_temp_and_humidity()

  if warning:
    activate_alarm_sound()
  
  time.sleep(1.0)

  if len(ir_sensor) > 0:
    handle_ir_signal()

  time.sleep(1.0)
 
    

  

