# Documentación oficial del protocolo del RVR — connection

> 🔴 **Copia de rescate.** `sdk.sphero.com` **ya no existe**. Esto viene de
> archive.org (captura de 2021-06-11) y lo encontró el usuario el 2026-08-01.
>
> ⚠️ Documenta el **protocolo del robot**, no el SDK de Python. Hay comandos aquí que la
> librería **no expone** — `get_motor_temperature` y `force_battery_refresh`, por ejemplo.
>
> Análisis de lo relevante en `../evidencia_24_04/43_documentacion_sdk_rescatada.txt`.

---

Connection
Get Bluetooth Advertising Name
Returns null-terminated string with the BLE advertising name (e.g., "BL-ABCD").
Parameters:
None
Returns:
Name
- (string) BLE advertising name
Drive
→
Get Bluetooth Advertising Name
