# Sistema de control de temperatura en data center con Raspberry Pico 2W y CircuitPython

<img width="711" height="403" alt="image" src="https://github.com/user-attachments/assets/9acb3b90-174e-49bc-b7fd-d786f033543f" />

## Escenario

Una empresa quiere armar un data center para sus servidores, necesita controlar las condiciones del ambiente a través de un microcontrolador.

- Si la temperatura sube demasiado, los servidores pueden apagarse por sobrecalentamiento.
- Si la humedad es demasiado alta, existe riesgo de cortocircuitos por que se podrían generar gotas de agua dentro de los equipos.

Por ello se comunica con la Startup **Relay** para que implemente el sistema de control.

En primer lugar, el sensor KY-015, encargado de medir tanto la temperatura como la humedad, es el dispositivo central de monitoreo. Este sensor mantiene un registro constante de las condiciones de la sala, verificando que la temperatura sea menor a 25 °C y que la humedad se mantenga menor a 80 %. (aclaración: tanto la humedad como la temperatura dependerá de las condiciones climáticas del día mismo, por lo que estos valores podrían variar, el punto está en tener un umbral)

Para accionar la refrigeración, el sistema cuenta con un relé KY-019, que simula el encendido de un ventilador industrial. Su activación ocurre tanto cuando la temperatura supera los 25 °C como cuando la humedad se encuentra fuera de los límites seguros, superior al 80%.

El buzzer pasivo KY-006 tiene la función de actuar como alarma sonora. Su activación ocurre cuando la temperatura supera los 30 °C o cuando la humedad alcanza valores superiores al 90%. En estas situaciones, la alarma suena cada 2 segundos de manera indefinida, hasta que las condiciones de la sala se estabilicen en intervalos normales de temperatura y humedad o se desactive manualmente.

Para la desactivación manual, el receptor infrarrojo KY-022 permite al operador autorizado silenciar la alarma utilizando un control remoto preconfigurado. El sistema solo reconoce un código IR específico evitando desactivaciones accidentales por señales externas. El código consiste en la concatenación de las señales 00FD807F + 00FD40BF + 00FDC03F , que equivale a presionar los botones “1”, ”2” y “3”; en ese orden. Esta acción se considera parte de un protocolo de seguridad, de manera que la alarma puede silenciarse únicamente mientras se aplican medidas correctivas.  

En caso de que se efectúe una desactivación manual se encenderá un led el cual representa el estado desactivado de la alarma. Este led modulará senoidalmente su intensidad de 0% a 100% y de 100% a 0% cada 1 segundo. El operador, al finalizar sus tareas, debe restablecer la alarma enviando al sistema un código concatenando las señales 00FDB04F + 00FDB04F, que equivale a presionar dos veces consecutivas el botón “on/off” del control. La acción de reseteo apagará el led y activará la alarma.

Finalmente, el microcontrolador cumple también la tarea de documentar todos los eventos relevantes a través de la consola serial. Cada cambio de estado del sistema queda registrado con la hora a la que ocurren junto a los siguientes mensajes: 

- “Temperatura y humedad estables | Ventilador OFF”.
- “Temperatura mayor a 25 °C o humedad mayor 80% | Ventilador ON”. 
- “Temperatura mayor a 30 °C o humedad mayor 90% | Ventilador y Alarma ON”. 
- “Alarma desactivada”.  
- “Alarma reseteada”.

# Red de Microcontroladores con MQTT y Node-RED

## MQTT

MQTT (Message Queuing Telemetry Transport) es un protocolo de mensajería ligero, orientado a eventos, diseñado para dispositivos con recursos limitados y redes inestables. Usa el modelo publicador–suscriptor sobre TCP/IP.

En qué consiste:

- Broker: servidor central que recibe y distribuye mensajes.
- Clientes: publican o se suscriben a "temas" (topics).
- QoS (Quality of Service): mecanismo que ofrece tres niveles distintos (0, 1, 2) para garantizar diferentes grados de entrega de mensajes.
    - El nivel 0 proporciona entrega "fire and forget" sin confirmación
    - El nivel 1 garantiza que el mensaje llegue al menos una vez con confirmación
    - El nivel 2 asegura que el mensaje se entregue exactamente una vez mediante handshake

Cómo funciona:

1. Un cliente se conecta al broker.
2. Publica mensajes en un topic, por ejemplo sensores/temperatura.
3. Otros clientes se suscriben a ese topic y reciben los mensajes en tiempo real.

## Implementación

### Arquitectura

<img width="1052" height="581" alt="arq red de microcontroladores" src="https://github.com/user-attachments/assets/646a09d6-f5be-4168-982a-3d606d9dbfac" />

- **Sensores (12 microcontroladores Pico 2W)**: Cada uno publica sus datos (temperatura, humedad, movimiento, etc.) en un topic MQTT único.
- **Controlador Maestro (1 microcontrolador Pico 2W extra)**: Se suscribe a todos los sensores y centraliza la información en un solo topic (datos).
- **Broker MQTT**: Usamos un broker local, por lo que [instalamos mosquitto](https://mosquitto.org/download/) en nuestra PC. Este es el puerto estándar para el protocolo MQTT.
    - Una vez instalado mosquitto se ejecutara automaticamente como servicio, sin embargo, hay que hacer una pequeña modificación en el archivo mosquitto.config. Colocamos al principio las siguientes lineas:
        
        ```markdown
        listener 1883
        allow_anonymous true
        ```
        
    - 1883 es el puerto estándar para el protocolo MQTT.
- **Node-RED (en la PC)**: Se conecta al broker MQTT, escucha los datos (`datos/#`) y muestra cada valor en gráficos, indicadores, contadores, etc. según corresponda.
    - Lo instalamos https://nodered.org/docs/getting-started/windows, y ejecutamos el comando `node-red` , luego podremos abrir el servidor donde esta corriendo.
    - Debemos instalar la extensión (`@flowfuse/node-red-dashboard`) para tener acceso a distintos tipos de graficos.

### Librerías

Vamos a necesitar incorporar librerías que no vienen por defecto. En https://circuitpython.org/libraries se puede descargar un zip con todas las librerías. Luego las copias en la carpeta `/lib` en el microcontrolador.

Las librerías son:

- `/lib/adafruit_minimqtt`: Copiar la carpeta completa.
- `/lib/adafruit_ticks.mpy`: Módulo que necesita minimqtt.
- `/lib/adafruit_connection_manager.mpy`: Módulo que necesita minimqtt.
- `/lib/adafruit_esp32spi_socketpool.mpy`: Módulo para conectarnos a la red.

### Descubrimiento automático de sensores

Cuando un sensor se conecta a la red, además de comenzar a publicar sus datos periódicamente, envía un mensaje de anuncio al tema especial `descubrir/sensores`.

El mensaje contiene la información mínima necesaria para que el maestro lo identifique, por ejemplo en formato JSON:

```json
{
  "id": "temp_y_humedad",
  "topic": "/sensores/temp_y_humedad"
}

```

El maestro está suscripto al tema `descubrir/sensores`. Cada vez que se publica en el, lo interpreta como un sensor recientemente conectado y lo agrega a una lista de sensores conocidos (un diccionario con `id → topic`). Luego, se suscribe dinámicamente al `topic` de ese sensor para empezar a recibir sus datos en tiempo real.

### Node-red

El maestro centraliza toda la información que recibe y la publica en el tema `/datos/.`

Por ejemplo:

- `/datos/temp_y_humedad` → contiene `{ "temperatura": 22.5, "humedad": 70 }`
- `/datos/movimiento` → contiene `{ "movimiento": 1 }`

De esta forma, Node-RED solo necesita escuchar `datos/#` para recibir en tiempo real toda la información de la red de sensores.
### Configuración de los microcontroladores

```python
import time
import wifi
import socketpool
import adafruit_minimqtt.adafruit_minimqtt as MQTT

# Configuración de RED
SSID = "Tu wifi"
PASSWORD = "Contraseña de tu wifi"
BROKER = "La IPv4 de la pc donde corre mosquitto. Win: ipconfig o Linux: ip addr"  
TOPIC = "sensores/[la magnitud que mide ej sensores/temperatura]"

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

mqtt_client = MQTT.MQTT(
    broker=BROKER,
    port=1883,
    socket_pool=pool
)

# Usamos las estas varaibles globales para controlar cada cuanto publicamos
LAST_PUB = 0
PUB_INTERVAL = 5  

def mqtt_connected(client, userdata, flags, rc):
    print("Conectado al broker MQTT")
    
mqtt_client.on_connect = mqtt_connected

mqtt_client.connect()

def publish_data():
    global LAST_PUB
    now = time.monotonic()
    if now - last_pub >= PUB_INTERVAL:
        try:
            mqtt_client.publish(TOPIC, str(El parametro que quieras publicar))
            LAST_PUB = now
            print(f"Publicando")
        except Exception as e:
            print(f"Error publicando MQTT: {e}")

```
