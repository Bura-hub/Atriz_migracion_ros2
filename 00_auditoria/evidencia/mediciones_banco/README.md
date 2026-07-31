# Herramientas de medición en banco

Con el RVR encendido y conectado por UART. Son las que producen los números del informe, del
manual y del CHANGELOG: **en este proyecto nada se documenta sin haberse ejecutado.**

> ⚠️ **Las marcadas 🚗 MUEVEN EL ROBOT.** No hay evitación de obstáculos: solo existe el
> watchdog de `cmd_vel`, que para los motores si dejan de llegar órdenes, **no si hay algo
> delante**. Lee «Cuánto espacio hace falta» antes de lanzarlas.

## Sin ROS — aíslan el robot del software

Sirven para responder «¿es culpa del robot o de mi código?», que es la primera pregunta.

| Script | Qué mide | Referencia medida |
|---|---|---|
| `raw_uart.py` | ¿contesta el RVR **a nivel de bytes**? Es el test de más bajo nivel: distingue «robot apagado» de «enlace roto» | 46 bytes de respuesta |
| `test_rvr.py` | Construye `SpheroRvrAsync` y pide batería y firmware. ⚠️ el check de firmware **traga excepciones**: «construido» no implica que el robot responda | firmware 9.1.462 |
| `sdk_rate.py <ms>` | Frecuencia real de 3 sensores **a nivel del SDK** | — |
| `sdk_full.py <ms>` | Igual con los 8 sensores del driver. Mide el ancho de banda real | 16.67 Hz a 60 ms |
| `estabilidad.py` | 12 min: huecos, pérdidas y fugas de memoria | 0 huecos, RSS plano |
| `x2_parse.py` | ¿funciona el LIDAR? Decodifica el protocolo X2 **sin driver ROS** | 100 % checksums, 11.48 Hz |
| `verificar_leds_sensores.py` | 37 comprobaciones: los LEDs uno a uno y los 17 sensores | — |

## Sobre ROS 2 — miden el sistema entero

| Script | Qué mide | Referencia medida |
|---|---|---|
| `medir.py` | Frecuencia, mediana y jitter de `/odom` e `/imu` en 30 s | 16.7 Hz, σ 0.47 ms |
| `medir_keepalive_ros2.py` | ¿se duerme el RVR? Vigila el **ritmo** de `/odom` 12 min sin tocar nada | 0 huecos con keepalive, 2 sin él |
| 🚗 `medir_watchdog_ros2.py` | ¿frena el watchdog al cortar `cmd_vel`? Mide **desplazamiento**, no velocidad | 527 ms, 7.9 cm |
| 🚗 `medir_slam_ros2.py` | ¿crece el mapa al moverse? | 2367 → 3299 celdas |
| 🚗 `verificar_inverted_lidar.py` | ¿coinciden `/scan` y `/odom` en el sentido de giro? | ±48°, opuestos, calidad 0.93 |
| 🚗 `caracterizar_deriva_slam.py` | Repite la prueba de SLAM N veces y da la **distribución** de la deriva | mediana 1.0 / 2.7 cm, n=6 |

Y sin ROS, pero moviendo el robot:

| Script | Qué mide | Referencia medida |
|---|---|---|
| 🚗 `medir_velocidad_rvr.py --calibrar` | Avanza 1 m y para, para medirlo **con cinta métrica** | locator 101.1 vs 101.0 reales |
| 🚗 `medir_velocidad_rvr.py --marco` | ¿`Velocity` viene en marco mundo o robot? | **mundo**, 0.1° de coincidencia |
| 🚗 `medir_velocidad_rvr.py` | Las 4 fuentes de velocidad a la vez contra el desplazamiento | `Velocity` y `Speed`: 1 % de error |

## Cuánto espacio hace falta

`medir_slam_ros2.py` es la más exigente: gira 360° y luego avanza y retrocede en tramos.

```
            ↑ 1 m por delante (hacia donde mira)
    ┌───────────────────────┐
40cm│      ┌─────┐          │40cm     el robot NO se desplaza
←───┤      │ RVR │ →        ├───→     lateralmente: a los lados
    │      └──┬──┘          │         solo hace falta el hueco
    └───────────────────────┘         del giro (radio 14 cm)
            ↓ 1 m por detrás
```

**Nada a menos de 60 cm.** Y el LIDAR va a **15.5 cm** ✅ medido barriendo en horizontal: pasa por
encima de zócalos y cajas bajas, y por debajo de mesas. «Despejado a ras de suelo» no basta.

`verificar_inverted_lidar.py` solo gira: le basta un círculo de 50 cm.

## Tres reglas que estas herramientas aprendieron a base de fallar

1. **Mide POSICIÓN, nunca velocidad — y sobre todo, mira EN QUÉ MARCO viene lo que lees.**
   Una herramienta concluyó «el robot NUNCA se movió» mientras cruzaba la habitación, porque
   leía `Velocity.X` y el robot iba encarado a ~90° del eje X del locator. De ahí salió el
   hallazgo «el stream `Velocity` es basura», que estuvo un día en la documentación y
   **se retractó el 2026-07-31**: el stream es exacto (0 % de error), viene en el marco del
   MUNDO, y quien estaba mal era el driver.
2. **Suscríbete a `/scan` y `/odom` con BEST_EFFORT.** `rclpy` pide RELIABLE por defecto, DDS
   no empareja, y **no llega nada, sin error**. Sería un falso positivo perfecto.
3. **Pregúntate si lo que mides PUEDE cambiar.** `medir_slam_ros2.py` comprobaba si el mapa
   crecía **girando en el sitio**, que es imposible por construcción — el X2 barre los 360°.
   Su falso negativo costó bisecar una configuración que estaba bien.

## Reproducir

```bash
# Sin ROS (necesitan el puerto libre: para el driver antes)
python3 raw_uart.py                 # ¿robot despierto?
python3 sdk_full.py 60              # ritmo del SDK con 8 sensores
python3 x2_parse.py                 # ¿funciona el LIDAR?

# Sobre ROS 2
source /opt/ros/jazzy/setup.bash && source ~/atriz_ws/install/setup.bash
ros2 launch atriz_rvr_bringup robot.launch.py    # terminal aparte
python3 medir.py
python3 medir_keepalive_ros2.py --minutos 12

# Con SLAM también arrancado
python3 medir_slam_ros2.py          # 🚗 mueve el robot
```

> **Para el sistema viejo (Noetic):** `source /opt/ros/noetic/setup.bash && source
> ~/atriz_git/devel/setup.bash`, y el nodo era `rosrun atriz_rvr_driver Atriz_rvr_node.py`.

## Resultado resumido

- Barrido del intervalo: 250→3.85 Hz · 200→5.00 · 150→6.25 · 100→9.94 · 60→16.5 · 50→no arranca
- El firmware cuantiza a múltiplos de 20 ms
- SDK y ROS dan el mismo número → el nodo no es el cuello de botella
- 125 paquetes/s a 60 ms, holgado para 115200 baud

---

## Prueba de estabilidad de 12 min — 2026-07-29

Salida completa en `estabilidad_12min_2026-07-29.txt`. Resumen:

| Métrica | Resultado |
|---|---|
| `/odom` | 11 962 msgs en 721 s = **16.59 Hz** |
| Intervalo | mediana **60.1 ms**, máx 82.7 ms, σ **2.5 ms** |
| Huecos > 3× mediana (180 ms) | **0** |
| Discontinuidades de `header.seq` | **0** |
| Mensajes perdidos | **0** de 11 965 |
| Temperatura | 55.5 – 57.9 °C (bajó durante la prueba) |
| RSS del nodo | 53 MB → 53 MB, **crecimiento 0** |
| CPU del nodo | 29.4 % → 29.6 % de un núcleo |

Cadencia por minuto: 997 mensajes, constante en los 12 intervalos. Ni una sola
reconexión del UART.

## Añadidas el 2026-07-31

| Herramienta | Qué mide | Mueve el robot |
|---|---|---|
| `medir_ritmo_ros2.py` | ritmo y jitter de `/odom`, `/imu` y `/scan`. **Sustituye a `medir.py`**, que es de ROS 1 y ya no arranca | no |
| `medir_parada_nav2.py` | si el robot **arranca solo** al liberar la parada de emergencia con Nav2 navegando | ⚠️ ~2 m |
| `medir_sensor_color.py` | si el sensor de color sirve sin encender su luz (no sirve: 4 contra 741) | no |
| `medir_collision_monitor.py` | dónde para de verdad la capa de seguridad | ⚠️ sí |
| `comparar_deriva_roll.py` | deriva de SLAM con y sin el roll de la IMU | ⚠️ sí |
| `referenciar_posicion.py` | devuelve el robot a su punto de partida entre corridas | ⚠️ sí |

🔴 **`medir_ritmo_ros2.py` documenta tres formas distintas de medir mal un ritmo**, las tres
descubiertas el mismo día y las tres dando números bajos sobre un robot sano: `ros2 topic hz`
(QoS incompatible), `rclpy.spin_once` en bucle (pierde mensajes) y `mensajes/duración` (mete el
descubrimiento de DDS en el denominador). Merece leerse la cabecera antes de escribir cualquier
medida de frecuencia en este proyecto.
