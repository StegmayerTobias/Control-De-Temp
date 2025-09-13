# Sistema de control de temperatura en data center con Raspberry Pico 2W y CircuitPython

## Escenario

Una empresa quiere armar un data center para sus servidores, necesita controlar las condiciones del ambiente a través de un microcontrolador.

- Si la temperatura sube demasiado, los servidores pueden apagarse por sobrecalentamiento.
- Si la humedad es demasiado alta, existe riesgo de cortocircuitos por que se podrían generar gotas de agua dentro de los equipos.

Por ello se comunica con la Startup **Relay** para que implemente el sistema de control.

En primer lugar, el sensor KY-015, encargado de medir tanto la temperatura como la humedad, es el dispositivo central de monitoreo. Este sensor mantiene un registro constante de las condiciones de la sala, verificando que la temperatura sea menor a 25 °C y que la humedad se mantenga menor a 80 %. (aclaración: tanto la humedad como la temperatura dependerá de las condiciones climáticas del día mismo, por lo que estos valores podrían variar, el punto está en tener un umbral)

Para accionar la refrigeración, el sistema cuenta con un relé KY-019, que simula el encendido de un ventilador industrial. Su activación ocurre tanto cuando la temperatura supera los 25 °C como cuando la humedad se encuentra fuera de los límites seguros, superior al 80%.

El buzzer pasivo KY-006 tiene la función de actuar como alarma sonora. Su activación ocurre cuando la temperatura supera los 30 °C o cuando la humedad alcanza valores superiores al 90%. En estas situaciones, la alarma emite dos pitidos consecutivos cada 2 segundos de manera indefinida, hasta que las condiciones de la sala se estabilicen en intervalos normales de temperatura y humedad o se desactive manualmente.

Para la desactivación manual, el receptor infrarrojo KY-022 permite al operador autorizado silenciar la alarma utilizando un control remoto preconfigurado. El sistema solo reconoce un código IR específico evitando desactivaciones accidentales por señales externas. El código consiste en la concatenación de las señales 00FD807F + 00FD40BF + 00FDC03F , que equivale a presionar los botones “1”, ”2” y “3”; en ese orden. Esta acción se considera parte de un protocolo de seguridad, de manera que la alarma puede silenciarse únicamente mientras se aplican medidas correctivas.  

En caso de que se efectúe una desactivación manual se encenderá un led el cual representa el estado desactivado de la alarma. Este led modulará senoidalmente su intensidad de 0% a 100% y de 100% a 0% cada 1 segundo. El operador, al finalizar sus tareas, debe restablecer la alarma enviando al sistema un código concatenando las señales 00FDB04F + 00FDB04F, que equivale a presionar dos veces consecutivas el botón “on/off” del control. La acción de reseteo apagará el led y activará la alarma.

Finalmente, el microcontrolador cumple también la tarea de documentar todos los eventos relevantes a través de la consola serial. Cada cambio de estado del sistema queda registrado con la hora a la que ocurren junto a los siguientes mensajes: 

- “Temperatura y humedad estables | Ventilador OFF”.
- “Temperatura mayor a 25 °C o humedad mayor 80% | Ventilador ON”. 
- “Temperatura mayor a 30 °C o humedad mayor 90% | Ventilador y Alarma ON”. 
- “Alarma desactivada”.  
- “Alarma reseteada”.
