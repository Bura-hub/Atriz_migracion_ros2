# Documentación oficial del protocolo del RVR — io

> 🔴 **Copia de rescate.** `sdk.sphero.com` **ya no existe**. Esto viene de
> archive.org (captura de 2021-06-11) y lo encontró el usuario el 2026-08-01.
>
> ⚠️ Documenta el **protocolo del robot**, no el SDK de Python. Hay comandos aquí que la
> librería **no expone** — `get_motor_temperature` y `force_battery_refresh`, por ejemplo.
>
> Análisis de lo relevante en `../evidencia_24_04/43_documentacion_sdk_rescatada.txt`.

---

Io
Set All Leds
LED affected mask can affect up to 32 LEDs simultaneously. 0 = not affected. 1 = affected (update this LED). If mask value is set to 1, you must provide a value in the LED data array.
Parameters:
LedGroup
- (
Led Groups
- uint32) Bitmask selecting which LEDs to change (32-bit).
LedBrightnessValues
- (uint8[32]) Array of RGB values for each of the selected LEDs (1 to 32 bytes; length depends on robot).
Returns:
None
Get Active Color Palette
The response data will list all assigned color palette slots in the system.
Parameters:
None
Returns:
RgbIndexBytes
- (uint8[48]) struct array -- index, red, green, blue -- that stores the contents of the active color palette.
Set Active Color Palette
Each entry in the array corresponds to one color slot in the system.  Any unmentioned slot indices will be marked unassigned.
Parameters:
RgbIndexBytes
- (uint8[48]) struct array -- index, red, green, blue -- that stores the contents of the color palette to be set as the active color palette.
Returns:
None
Get Color Identification Report
The response to this command will provide an array of color palette entries that would match on the provided color with higher confidence than the given threshold.
Parameters:
Red
- (uint8) Red ('R') value of the color to be matched.
Green
- (uint8) Green ('G') value of the color to be matched.
Blue
- (uint8) Blue ('B') value of the color to be matched.
ConfidenceThreshold
- (uint8) How closely the palette should match the provided color. The confidence threshold is in [0, 255].
Returns:
IndexConfidenceByte
- (uint8[24]) struct array -- index, confidence -- that contains the index of the palette that best matches the provided color and a confidence level for how closely the palette matches the provided color.
Load Color Palette
Loads the specified color palette into the active palette.
Parameters:
PaletteIndex
- (
Specdrums Color Palette Indicies
- uint8) The index of (number that identifies) the color palette to be loaded.
Returns:
None
Save Color Palette
Stores the active palette into the palette at palette index (see table above).
Parameters:
PaletteIndex
- (
Specdrums Color Palette Indicies
- uint8) The index of (number that identifies) the color palette to be stored.
Returns:
None
Release Led Requests
Releases LED requests to show the idle indication.
Parameters:
None
Returns:
None
Enums:
Specdrums Color Palette Indicies
Default
: 0
Midi
: 1
Specdrums Color Palette Indicies
Default
: 0
Midi
: 1
Bitmasks:
Led Groups
←
Drive
Power
→
Set All Leds
Get Active Color Palette
Set Active Color Palette
Get Color Identification Report
Load Color Palette
Save Color Palette
Release Led Requests
