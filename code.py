import board
import pulseio
import adafruit_irremote
import adafruit_dht
import time
import pwmio
import digitalio
import math


DHT_PIN = board.GP15
IR_PIN = board.GP16
BUZZER_PIN = board.GP17
RELAY_PIN = board.GP14
LED_PIN = board.GP13

IR_CODE_TURNOFF = '00FD807F00FD40BF00FDC03F'
IR_CODE_RESET = '00FDB04F00FDB04F'
CODE = []


dht_sensor = adafruit_dht.DHT11(DHT_PIN)
ir_sensor = pulseio.PulseIn(IR_PIN, maxlen=120, idle_state=True)
buzzer = pwmio.PWMOut(BUZZER_PIN, duty_cycle=0,
                      frequency=800, variable_frequency=True)

led = digitalio.DigitalInOut(LED_PIN)
led.direction = digitalio.Direction.OUTPUT

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


def activate_alarm_sound():
    beep()
    time.sleep(0.2)
    beep()


last_beep = time.monotonic()
beep_duration = 0.2  # duración del beep en segundos
beep_active = False


def activate_alarm_nonblocking():
    """
    Hace que la alarma suene un beep cada 2 segundos sin bloquear el programa.
    """
    global last_beep, beep_active
    now = time.monotonic()

    if not beep_active and now - last_beep >= 2.0:
        # encender buzzer
        buzzer.duty_cycle = 2**15
        last_beep = now
        beep_active = True

    elif beep_active and now - last_beep >= beep_duration:
        # apagar buzzer
        buzzer.duty_cycle = 0
        beep_active = False


def alarm_turnOnOff_sound():
    # Aca cambio el sonido del beep en frecuencia y velocidad para que indique que la alarma se desactivo
    beep(frequency=800, duration=0.06)
    time.sleep(0.06)
    beep(frequency=800, duration=0.06)


def handle_ir_signal():
    global alarm_on, warning, last_relay_state
    try:
        pulses = decoder.read_pulses(ir_sensor)
        received_code = decoder.decode_bits(pulses)
        if received_code:
            hex_code = ''.join(["%02X" % x for x in received_code])

            if len(CODE) == 0 and hex_code == "00FD807F":
                CODE.append(hex_code)

            elif len(CODE) == 0 and hex_code == "00FDB04F":
                CODE.append(hex_code)

            elif len(CODE) == 1 and hex_code == "00FDB04F" and CODE[0] == "00FDB04F":
                CODE.append(hex_code)

            elif len(CODE) == 1 and hex_code == "00FD40BF" and CODE[0] == "00FD807F":
                CODE.append(hex_code)

            elif len(CODE) == 2 and hex_code == "00FDC03F":
                CODE.append(hex_code)

            else:
                CODE.clear()

            CODE_CONCAT = "".join(CODE)
            if CODE_CONCAT == IR_CODE_TURNOFF and warning:
                print(f"Recibido: {CODE_CONCAT} | Alarma apagada")

                CODE.clear()
                alarm_turnOnOff_sound()
                warning = False
                alarm_on = False

            elif CODE_CONCAT == IR_CODE_RESET and not warning:
                print(f"Recibido: {CODE_CONCAT} | Alarma reseteada")
                CODE.clear()
                led.value = False
                alarm_on = True
                last_relay_state = None

            else:
                if CODE_CONCAT == "" and alarm_on:
                    print(f"Código invalido | alarma activa")
                elif CODE_CONCAT == "" and not alarm_on:
                    print(f"Código invalido | alarma inactiva")

    except adafruit_irremote.IRNECRepeatException:
        pass
    except adafruit_irremote.IRDecodeException:
        print("No se detectó una señal IR válida.")


last_relay_state = None


def check_temp_and_humidity():
    global alarm_on, warning, last_relay_state
    try:

        temperature_c = dht_sensor.temperature
        humidity = dht_sensor.humidity

        # Estado actual del relé según temperatura/humedad
        current_relay_state = temperature_c > 20 or humidity > 100
        relay.value = current_relay_state

        # Detectar cambio de estado o primera lectura
        if current_relay_state != last_relay_state or last_relay_state is None:
            if current_relay_state and alarm_on:
                # Condición de alerta
                if temperature_c > 20 and humidity > 70:
                    print(
                        f"Temperatura mayor a 27 °C y humedad mayor a 80% | T: {temperature_c:.1f}°C | H: {humidity}% | Ventilador ON")
                elif temperature_c > 20:
                    print(
                        f"Temperatura mayor a 27 °C | T: {temperature_c:.1f}°C | H: {humidity}% | Ventilador ON")
                elif humidity > 80:
                    print(
                        f"Humedad mayor a 80% | T: {temperature_c:.1f}°C | H: {humidity}% | Ventilador ON")

                if temperature_c > 20 or humidity > 90:
                    print(
                        f"Temperatura mayor a 30 °C o humedad mayor a 80% | T: {temperature_c:.1f}°C | H: {humidity}% | Alarma ON")
                    warning = True

            elif not current_relay_state and (warning or last_relay_state is None):
                # Condición estable

                if warning:
                    alarm_turnOnOff_sound()
                warning = False
                print(
                    f"Temperatura y humedad estables | T: {temperature_c:.1f}°C | H: {humidity}% | Ventilador OFF")

        # Actualizo el estado anterior
        last_relay_state = current_relay_state

    except RuntimeError as error:
        print(error.args[0])
    except Exception as error:
        dht_sensor.exit()
        raise error


last_toggle = time.monotonic()
led_state = False


def activate_led(interval=1.0):
    global led_state, last_toggle
    now = time.monotonic()
    if now - last_toggle >= interval:
        led_state = not led_state
        led.value = led_state
        last_toggle = now


print("-----------------------------")
print("Sistema de monitoreo iniciado")
print("-----------------------------")
while True:

    if len(ir_sensor) > 0:
        handle_ir_signal()

    check_temp_and_humidity()

    if warning:
        activate_alarm_nonblocking()

    if not alarm_on:
        activate_led(interval=1.0)
