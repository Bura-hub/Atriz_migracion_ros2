# Documentación oficial del protocolo del RVR — system_info

> 🔴 **Copia de rescate.** `sdk.sphero.com` **ya no existe**. Esto viene de
> archive.org (captura de 2021-06-11) y lo encontró el usuario el 2026-08-01.
>
> ⚠️ Documenta el **protocolo del robot**, no el SDK de Python. Hay comandos aquí que la
> librería **no expone** — `get_motor_temperature` y `force_battery_refresh`, por ejemplo.
>
> Análisis de lo relevante en `../evidencia_24_04/43_documentacion_sdk_rescatada.txt`.

---

System Info
Get Main Application Version
Gets the version of the main application.
Parameters:
None
Returns:
Major
- (uint16) The x value for version x.y.z
Minor
- (uint16) The y value for version x.y.z
Revision
- (uint16) The z value for version x.y.z
Get Bootloader Version
Gets the version of the bootloader.
Parameters:
None
Returns:
Major
- (uint16) The x value for version x.y.z
Minor
- (uint16) The y value for version x.y.z
Revision
- (uint16) The z value for version x.y.z
Get Board Revision
Gets the board revision number.
Parameters:
None
Returns:
Revision
- (uint8) The hardware version for the board.
Get Mac Address
Gets the robot's MAC address.
Parameters:
None
Returns:
MacAddress
- (string) A 12-byte string representing the robot's MAC address.
Get Stats Id
Gets the id number assigned by the company for activation tracking.
Parameters:
None
Returns:
StatsId
- (uint16) The ID number assigned by the company (for activation tracking).
Get Processor Name
Returns the processor name string (as specified to the System Info module). If no name is specified, returns an empty string or no string.
Parameters:
None
Returns:
Name
- (string) The processor name (string up to 16 characters, including optional null terminator).
Get Sku
Returns the SKU of the bot.
Parameters:
None
Returns:
Sku
- (string) SKU (null-terminated string).
Get Core Up Time In Milliseconds
Returns the time (in milliseconds) that has passed since the latest power cycle started.
Parameters:
None
Returns:
UpTime
- (uint64, milliseconds) Time (in milliseconds) since last application start up.
←
Sensor
Get Main Application Version
Get Bootloader Version
Get Board Revision
Get Mac Address
Get Stats Id
Get Processor Name
Get Sku
Get Core Up Time In Milliseconds
