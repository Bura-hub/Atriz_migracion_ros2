# Scripts de medición en banco (2026-07-29)

Con el RVR encendido y conectado por UART. Producen los números de la sección
"Correcciones tras verificar en banco" del informe.

| Script | Qué hace |
|---|---|
| `raw_uart.py` | Envía paquetes `wake` y `get_version` crudos por `/dev/rvr` y muestra la respuesta en hex. Es el test de más bajo nivel: distingue "robot apagado" de "enlace roto" |
| `test_rvr.py` | Construye `SpheroRvrAsync` y pide batería y firmware. **Cuidado:** el check de firmware traga excepciones, así que "construido" no implica que el robot responda |
| `sdk_rate.py <ms>` | Mide la frecuencia real de 3 sensores a nivel del SDK, **sin ROS**. Aísla el robot de la estructura del nodo |
| `sdk_full.py <ms>` | Igual pero con los 8 sensores que registra el driver. Mide el ancho de banda real |
| `medir.py` | Se suscribe a `/odom` e `/imu` en ROS y reporta frecuencia, mediana y jitter en 30 s |

## Reproducir

```bash
source /opt/ros/noetic/setup.bash && source ~/atriz_git/devel/setup.bash
python3 raw_uart.py                 # robot despierto?
python3 sdk_full.py 60              # ritmo del SDK con 8 sensores
rosrun atriz_rvr_driver Atriz_rvr_node.py &
python3 medir.py                    # ritmo a traves de ROS
```

`sdk_rate.py` y `sdk_full.py` necesitan el puerto libre: para el nodo antes.

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
