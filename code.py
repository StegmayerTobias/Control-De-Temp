import board
import pulseio
import adafruit_irremote
import adafruit_dht
import time
import pwmio
import digitalio
import math
import json
import wifi
import socketpool
import adafruit_minimqtt.adafruit_minimqtt as MQTT


# Configuración
SSID = ""
PASSWORD = ""
BROKER = ""
NOMBRE_EQUIPO = "relay"
DESCOVERY_TOPIC = "descubrir"
TOPIC = f"sensores/{NOMBRE_EQUIPO}"

print(f"Intentando conectar a {SSID}...")
try:
    wifi.radio.connect(SSID, PASSWORD)
    print(f"Conectado a {SSID}")
    print(f"Dirección IP: {wifi.radio.ipv4_address}")
except Exception as e:
    print(f"Error al conectar a WiFi: {e}")
    while True:
        pass

# Configuración MQTT
pool = socketpool.SocketPool(wifi.radio)


def connect(client, userdata, flags, rc):
    print("Conectado al broker MQTT")
    client.publish(DESCOVERY_TOPIC, json.dumps(
        {"equipo": NOMBRE_EQUIPO, "magnitudes": ["temperatura", "humedad","IR"]}))


mqtt_client = MQTT.MQTT(
    broker=BROKER,
    port=1883,
    socket_pool=pool
)

mqtt_client.on_connect = connect

mqtt_client.connect()


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

led = pwmio.PWMOut(LED_PIN, frequency=5000, duty_cycle=0)

relay = digitalio.DigitalInOut(RELAY_PIN)
relay.direction = digitalio.Direction.OUTPUT
decoder = adafruit_irremote.GenericDecode()

warning = False
alarm_on = True
last_relay_state = None

temperature_c = 0.0
humidity = 0

last_beep = time.monotonic()
beep_duration = 0.2
beep_active = False

last_pub = 0
PUB_INTERVAL = 5

def publish_temp_hum():
    global last_pub
    now = time.monotonic()

    if now - last_pub >= PUB_INTERVAL:
        try:
            temp_topic = f"{TOPIC}/temperatura"
            mqtt_client.publish(temp_topic, str(temperature_c))

            hum_topic = f"{TOPIC}/humedad"
            mqtt_client.publish(hum_topic, str(humidity))

            last_pub = now

        except Exception as e:
            print(f"Error publicando MQTT: {e}")

def publish_IR(estado):
    try:
        ir_topic = f"{TOPIC}/IR"
        mqtt_client.publish(ir_topic, str(estado).lower())


    except Exception as e:
        print(f"Error publicando MQTT: {e}")

def activate_alarm():
    """
    Hace sonar la alarma con un beep cada 2 segundos.
    """
    global last_beep, beep_active
    now = time.monotonic()

    if not beep_active and now - last_beep >= 2.0:
        buzzer.duty_cycle = 2**15
        last_beep = now
        beep_active = True

    elif beep_active and now - last_beep >= beep_duration:
        buzzer.duty_cycle = 0
        beep_active = False


def beep(frequency=880, duration=0.2):
    buzzer.duty_cycle = 2**15
    buzzer.frequency = frequency
    time.sleep(duration)
    buzzer.duty_cycle = 0


def alarm_turnOnOff_sound():
    """
    Dos beeps consecutivos que representan la desactivación de la alarma.
    """
    beep(frequency=800, duration=0.06)
    time.sleep(0.06)
    beep(frequency=800, duration=0.06)


def handle_ir_signal():
    """
    Espera en cada iteración señales IR. 
    Los codigos que espera son: 

    * 1 + 2 + 3: para desactivar la alarma;
    * on/off + on/off: para resetearla. 
    """

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

            print(CODE)

            CODE_CONCAT = "".join(CODE)
            if CODE_CONCAT == IR_CODE_TURNOFF and warning:
                print(f"Recibido: {CODE_CONCAT} | Alarma desactivada")
                publish_IR(False)
                CODE.clear()
                alarm_turnOnOff_sound()
                warning = False
                alarm_on = False

            elif CODE_CONCAT == IR_CODE_RESET and not alarm_on:
                print(f"Recibido: {CODE_CONCAT} | Alarma reseteada")
                publish_IR(True)
                CODE.clear()
                led.duty_cycle = 0
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
        pass


def check_temp_and_humidity():
    """
    Verifica en cada iteración la temperatura y la humedad.

    * Temperatura > 25°C o Humedad > 80% => Ventilador activado (se activa relé);
    * Temperatura > 30°C o Humedad > 90% => Se activa alarma.
    """

    global alarm_on, warning, last_relay_state, temperature_c, humidity
    try:
        temperature_c = dht_sensor.temperature
        humidity = dht_sensor.humidity

        current_relay_state = temperature_c > 25 or humidity > 80
        relay.value = current_relay_state

        if temperature_c > 30 or humidity > 90 and alarm_on:
            if not warning:
                print(
                    f"Alarma ON (T>30 o H>90) | T: {temperature_c:.1f}°C | H: {humidity}%")
                warning = True
        else:
            if warning and (temperature_c < 30 and humidity < 90):
                print(
                    f"Alarma OFF | T: {temperature_c:.1f}°C | H: {humidity}%")
                warning = False
                alarm_on = False
                alarm_turnOnOff_sound()

        if current_relay_state != last_relay_state or last_relay_state is None:
            if current_relay_state:
                if not alarm_on:
                    print(
                        f"Ventilador ON (T>25 o H>80) | T: {temperature_c:.1f}°C | H: {humidity}%")
            else:
                print(
                    f"Ventilador OFF | T: {temperature_c:.1f}°C | H: {humidity}%")

        last_relay_state = current_relay_state

    except RuntimeError as error:
        print(error.args[0])
    except Exception as error:
        dht_sensor.exit()
        raise error


def activate_led(speed=1.0):
    """
    Activa el led cuando la alarma esta desactivada. El led modula su intensidad senoidalmente.
    """

    now = time.monotonic()
    # seno va de -1 a 1, lo normalizamos a 0..1
    value = (math.sin(now * speed) + 1) / 2
    # convertir 0..1 a 0..65535 (rango de duty_cycle)
    led.duty_cycle = int(value * 65535)

publish_IR(True)
print("-----------------------------")
print("Sistema de monitoreo iniciado")
print("-----------------------------")
while True:
    if len(ir_sensor) > 0:
        handle_ir_signal()

    check_temp_and_humidity()

    if warning and alarm_on:
        activate_alarm()

    if not alarm_on:
        activate_led(speed=1.5)

    publish_temp_hum()
