import board
import pulseio
import adafruit_irremote
import adafruit_dht
import time
import pwmio
import digitalio
import math
# import wifi


# SSID = "Familiastegmayer"
# PASSWORD = "Canela2024"

# wifi.radio.connect(SSID, PASSWORD)
# print("Conectado a Wi-Fi:", wifi.radio.ipv4_address)

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
                      frequency=1000, variable_frequency=True)
led = pwmio.PWMOut(LED_PIN, duty_cycle=0, frequency=1000)

relay = digitalio.DigitalInOut(RELAY_PIN)
relay.direction = digitalio.Direction.OUTPUT
decoder = adafruit_irremote.GenericDecode()

warning = False
alarm_on = True

led_start_time = None
led_duration = 2.0
led_flashes = 4
led_active = False


def start_led(duration=2.0, flashes=4):
    global led_start_time, led_duration, led_flashes, led_active
    led_start_time = time.monotonic()
    led_duration = duration
    led_flashes = flashes
    led_active = True


def update_led():
    global led_active
    if not led_active:
        return
    t = time.monotonic() - led_start_time
    if t >= led_duration:
        led.duty_cycle = 0
        led_active = False
    else:
        frequency = led_flashes / led_duration
        valor = (math.sin(2 * math.pi * frequency * t) + 1) / 2 * 0.5
        led.duty_cycle = int(valor * 65535)


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


def turnOn_led():
    led.duty_cycle = int(0.5 * 65535)


def turnOff_led():

    led.duty_cycle = 0


def handle_ir_signal():
    global alarm_on, warning
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
            if CODE_CONCAT == IR_CODE_TURNOFF:
                print(f"Recibido: {CODE_CONCAT} | Alarma apagada")
                if warning:
                    alarm_turnOnOff_sound()
                    warning = False
                    alarm_on = False
                    CODE.clear()
            elif CODE_CONCAT == IR_CODE_RESET:
                print(f"Recibido: {CODE_CONCAT} | Alarma reseteada")
                alarm_on = True

            else:
                print(f"Recibido: {CODE_CONCAT} ")
                # print(
                #     f"Boton desconocido. Presione OFF para apagar o RESET para reiniciar la alarma.")

    except adafruit_irremote.IRNECRepeatException:
        pass
    except adafruit_irremote.IRDecodeException:
        print("No se detectó una señal IR válida.")


def check_temp_and_humidity():
    global alarm_on, warning
    try:
        temperature_c = dht_sensor.temperature
        humidity = dht_sensor.humidity

        relay.value = temperature_c > 27 or humidity > 80

        if relay.value and alarm_on:
            warning = True
        elif not relay.value and warning:
            warning = False
            alarm_turnOnOff_sound()

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
        start_led(duration=2.0, flashes=4)

    update_led()  # actualiza el LED cada it

    if len(ir_sensor) > 0:
        handle_ir_signal()

    time.sleep(2.0)
eracion
