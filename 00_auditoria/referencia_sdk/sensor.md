# Documentación oficial del protocolo del RVR — sensor

> 🔴 **Copia de rescate.** `sdk.sphero.com` **ya no existe**. Esto viene de
> archive.org (captura de 2021-06-11) y lo encontró el usuario el 2026-08-01.
>
> ⚠️ Documenta el **protocolo del robot**, no el SDK de Python. Hay comandos aquí que la
> librería **no expone** — `get_motor_temperature` y `force_battery_refresh`, por ejemplo.
>
> Análisis de lo relevante en `../evidencia_24_04/43_documentacion_sdk_rescatada.txt`.

---

Sensor
Enable Gyro Max Notify
Enables the Async messages for when the Gyro max is hit.
Parameters:
IsEnabled
- (bool) Boolean set for if you would like a notification when the Gyro max is hit. True for enabled. False for disabled.
Returns:
None
Gyro Max Notify
Occurs when the robot spins faster than the sensor can see in any axis.
Parameters:
None
Returns:
Flags
- (
Gyro Max Flags
- uint8) The values signify things are as such: 0 = Max + X, 1 = Max - X, 2 = Max + Y, 3 = Max - Y, 4 = Max + z, 5 = Max - Z
Reset Locator X And Y
Resets the locator module's current X and Y values to 0.
Parameters:
None
Returns:
None
Set Locator Flags
Sets flags for the locator module.
Parameters:
Flags
- (
Locator Flags
- uint8) Auto calibrate: When set, the robot will maintain the same X - Y axis from initial startup. When cleared, the robot will reset the X - Y axis orientation when a driving yaw reset command is sent.
Returns:
None
Get Bot To Bot Infrared Readings
An 8-bit value is returned for each infrared sensor, assigned by mask.
Mask description on BOLT: 32'h0000_00ff: front left sensor 32'h0000_ff00: front right sensor 32'h00ff_0000: back right sensor 32'hff00_0000: back left sensor
Parameters:
None
Returns:
SensorData
- (
Infrared Sensor Locations
- uint32) If the register reads a value between 0 - 15, then a message of that ID has been received. If the data returned is 255, the register is empty. For RVR, the message is only kept for 1second before it's reset back to 255.
Get Rgbc Sensor Values
Return raw data being read by RGBC sensor on each sensor channel
Parameters:
None
Returns:
RedChannelValue
- (uint16) None
GreenChannelValue
- (uint16) None
BlueChannelValue
- (uint16) None
ClearChannelValue
- (uint16) None
Start Robot To Robot Infrared Broadcasting
For robot following, broadcasting robots emit two codes: one for long distance (3 meters +), and one for short distance (< 1 meter). Following robots use both of these codes to determine direction and distance from the broadcasting robot.
Parameters:
FarCode
- (uint8) Code between 0 and 7 that the robot emits for long distance (3+ meters) communication so that bots receiving it will know that it is further away.
NearCode
- (uint8) Code between 0 and 7 that the robot emits for short distance (<1 meters) communication so that bots receiving it will know that it is closer.
Returns:
None
Start Robot To Robot Infrared Following
Registers a far code and near code for a following robot to follow. Following robots use the far code and near code emitted by a broadcaster bot to determine direction and distance to travel.
Parameters:
FarCode
- (uint8) Code between 0 and 7 that the robot emits for long distance (3+ meters) communication so that bots receiving it will know that it is further away.
NearCode
- (uint8) Code between 0 and 7 that the robot emits for short distance (<1 meters) communication so that bots receiving it will know that it is closer.
Returns:
None
Stop Robot To Robot Infrared Broadcasting
Halts current broadcasting or following. De-registers far code and near code on broadcasting or following robot.
Parameters:
None
Returns:
None
Robot To Robot Infrared Message Received Notify
Async sent when a registered robot to robot infrared message is received. In response returns the infrared code listened for.
Parameters:
None
Returns:
InfraredCode
- (uint8) Infrared code received from within the list of the channels listened for.
Get Ambient Light Sensor Value
Ambient light value is returned; higher = more light!
Parameters:
None
Returns:
AmbientLightValue
- (float) higher = more light
Stop Robot To Robot Infrared Following
Halts current following. De-registers far code and near code on following robot.
Parameters:
None
Returns:
None
Start Robot To Robot Infrared Evading
Registers a far code and near code for a evading robot to evade. Evading robots use the far code and near code emitted by a broadcaster bot to determine direction and distance to travel.
Parameters:
FarCode
- (uint8) Code between 0 and 7 that the robot emits for long distance (3+ meters) communication so that bots receiving it will know that it is further away.
NearCode
- (uint8) Code between 0 and 7 that the robot emits for short distance (<1 meters) communication so that bots receiving it will know that it is closer.
Returns:
None
Stop Robot To Robot Infrared Evading
Halts current evading. De-registers far code and near code on evading robot.
Parameters:
None
Returns:
None
Enable Color Detection Notify
Enable or disable asynchronous color detection notifications. The user must provide an interval and a confidence threshold
Parameters:
IsEnabled
- (bool) True for enable.  False for disable
Interval
- (uint16, milliseconds) Interval, in milliseconds, that color detection asyncs will be sent.
MinimumConfidenceThreshold
- (uint8) The minimum confidence level, from 0 to 255, that must be met before an async is sent.
Returns:
None
Color Detection Notify
Notification sent on the interval set by the user in enable_color_detection_notification with information about the color detected.  The color classification ID 0xFF is a special value indicating that the color could not be identified (e.g., because the reading was too dark).  This is expected behavior when the ring is tapped in the air with the sensor facing out.
Parameters:
None
Returns:
Red
- (uint8) Red value detected.
Green
- (uint8) Green value detected.
Blue
- (uint8) Blue value detected.
Confidence
- (uint8) Level of confidence in color classification ID, from 0 (0% confidence) to 255 (100% confident)
ColorClassificationId
- (uint8) Toy-dependent ID for color classification.
Get Current Detected Color Reading
Note: this does not return anything.  Instead, a color_detection_notify async will be sent after measurement with the answer.
Parameters:
None
Returns:
None
Enable Color Detection
Enables the color detection module.
Parameters:
IsEnabled
- (bool) True for enable.  False for disable
Returns:
None
Configure Streaming Service
Configure streaming services.
Parameters:
Token
- (uint8) None
Configuration
- (
Streaming Data Sizes
- uint8[15]) Array containing the configuration of the client, like the service ID and size.
Returns:
None
Start Streaming Service
Start all streaming services for a client
Parameters:
Period
- (uint16) Interval between sensor streaming packets in milliseconds.
Returns:
None
Stop Streaming Service
Stops all streaming services for a client
Parameters:
None
Returns:
None
Clear Streaming Service
Clears all streaming services for a client
Parameters:
None
Returns:
None
Streaming Service Data Notify
Streaming data notification for a client configuration
Parameters:
None
Returns:
Token
- (uint8) None
SensorData
- (uint8[9999]) Array containing the configuration of the client, like the data.
Enable Robot Infrared Message Notify
Starts listening for infrared messages sent to the robot and will send an async message when received.
Parameters:
IsEnabled
- (bool) True for enable.  False for disable
Returns:
None
Send Infrared Message
Send specified code to any robot in the vicinity. The on/off for each sensor is controlled individually but there can only be one range for all sensors. Therefore, the acceptable combination of emitters strength would be: 5, 5, 0, 0 or 5, 5, 5, 5 or 0, 0, 0, 5, etc.
Parameters:
InfraredCode
- (uint8) The only valid messages to send this way have an ID between 0 and 7.
FrontStrength
- (uint8) The range goes from 0-64, where 0 is no message sent, and 64 is the longest achievable range.
LeftStrength
- (uint8) The range goes from 0-64, where 0 is no message sent, and 64 is the longest achievable range.
RightStrength
- (uint8) The range goes from 0-64, where 0 is no message sent, and 64 is the longest achievable range.
RearStrength
- (uint8) The range goes from 0-64, where 0 is no message sent, and 64 is the longest achievable range.
Returns:
None
Get Motor Temperature
Get the motor temperature (calculated from motor current) for given a motor index.
Parameters:
MotorIndex
- (
Motor Indexes
- uint8) Indicates which motor we would like the metrics.
Returns:
WindingCoilTemperature
- (float) Temperature of the winding coil. Reported in Celsius
CaseTemperature
- (float) Temperature of the case. Reported in Celsius
Get Motor Thermal Protection Status
Get motor thermal protection status.
Parameters:
None
Returns:
LeftMotorTemperature
- (float, celsius) Temperature of the left motor in degrees Celsius
LeftMotorStatus
- (
Thermal Protection Status
- uint8) Thermal protection status.
RightMotorTemperature
- (float, celsius) Temperature of the right motor in degrees Celsius
RightMotorStatus
- (
Thermal Protection Status
- uint8) Thermal protection status.
Enable Motor Thermal Protection Status Notify
Enable motor thermal protection status notifications.
Parameters:
IsEnabled
- (bool) True for enable.  False for disable
Returns:
None
Motor Thermal Protection Status Notify
Motor thermal protection status notification.
Parameters:
None
Returns:
LeftMotorTemperature
- (float, celsius) Temperature of the left motor in degrees Celsius
LeftMotorStatus
- (
Thermal Protection Status
- uint8) Thermal protection status.
RightMotorTemperature
- (float, celsius) Temperature of the right motor in degrees Celsius
RightMotorStatus
- (
Thermal Protection Status
- uint8) Thermal protection status.
Enums:
Streaming Data Sizes
Eight Bit
: 0x00
Sixteen Bit
: 0x01
Thirty Two Bit
: 0x02
Motor Indexes
Left Motor Index
: 0
Right Motor Index
: 1
Bitmasks:
Gyro Max Flags
Max Plus X
: bit 0
Max Minus X
: bit 1
Max Plus Y
: bit 2
Max Minus Y
: bit 3
Max Plus Z
: bit 4
Max Minus Z
: bit 5
Locator Flags
Auto Calibrate
: bit 0
Infrared Sensor Locations
Front Left
: 0x000000FF
Front Right
: 0x0000FF00
Back Right
: 0x00FF0000
Back Left
: 0xFF000000
←
Power
System Info
→
Enable Gyro Max Notify
Gyro Max Notify
Reset Locator X And Y
Set Locator Flags
Get Bot To Bot Infrared Readings
Get Rgbc Sensor Values
Start Robot To Robot Infrared Broadcasting
Start Robot To Robot Infrared Following
Stop Robot To Robot Infrared Broadcasting
Robot To Robot Infrared Message Received Notify
Get Ambient Light Sensor Value
Stop Robot To Robot Infrared Following
Start Robot To Robot Infrared Evading
Stop Robot To Robot Infrared Evading
Enable Color Detection Notify
Color Detection Notify
Get Current Detected Color Reading
Enable Color Detection
Configure Streaming Service
Start Streaming Service
Stop Streaming Service
Clear Streaming Service
Streaming Service Data Notify
Enable Robot Infrared Message Notify
Send Infrared Message
Get Motor Temperature
Get Motor Thermal Protection Status
Enable Motor Thermal Protection Status Notify
Motor Thermal Protection Status Notify
