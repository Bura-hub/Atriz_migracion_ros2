import serial, time
SOP, EOP, ESC = 0x8D, 0xD8, 0xAB
ESC_MAP = {SOP: 0x05, EOP: 0x50, ESC: 0x23}

def build(did, cid, seq=0x01, target=0x01, source=0x01):
    flags = 0x02 | 0x08 | 0x10 | 0x20      # requests_response|reset_inactivity|has_target|has_source
    body = [flags, target, source, did, cid, seq]
    chk = (~(sum(body) & 0xFF)) & 0xFF
    out = bytearray([SOP])
    for b in body + [chk]:
        if b in ESC_MAP: out += bytes([ESC, ESC_MAP[b]])
        else:            out.append(b)
    out.append(EOP)
    return bytes(out)

p = serial.Serial('/dev/rvr', 115200, timeout=0.5)
print(f"puerto abierto: {p.name} @ {p.baudrate}  (CTS={p.cts if p.rtscts else 'n/a'})")
p.reset_input_buffer()

# 1) escuchar sin enviar nada
time.sleep(1.0)
n = p.in_waiting
print(f"[1] bytes espontaneos en 1s: {n}")

# 2) enviar wake (Power=0x13, wake=0x0D) tres veces y escuchar
total = b''
for i in range(3):
    pkt = build(0x13, 0x0D, seq=i+1)
    p.write(pkt); p.flush()
    print(f"[2] enviado wake #{i+1}: {pkt.hex(' ')}")
    time.sleep(0.7)
    r = p.read(p.in_waiting or 1)
    if r: print(f"    <- RECIBIDO {len(r)} bytes: {r.hex(' ')}")
    total += r

# 3) echo test: get_main_app_version (System=0x11, cid=0x00)
pkt = build(0x11, 0x00, seq=9)
p.write(pkt); p.flush()
print(f"[3] enviado get_version: {pkt.hex(' ')}")
time.sleep(1.0)
r = p.read(p.in_waiting or 1); total += r
if r: print(f"    <- RECIBIDO {len(r)} bytes: {r.hex(' ')}")

p.close()
print()
print("="*60)
if total:
    print(f"RESULTADO: el RVR CONTESTA ({len(total)} bytes). El enlace UART funciona.")
else:
    print("RESULTADO: CERO bytes de respuesta.")
    print("  -> El transmisor de la Pi funciona (no hay error de escritura),")
    print("     pero nada vuelve por RX. Causas por orden de probabilidad:")
    print("       1. El Sphero RVR esta APAGADO o sin bateria")
    print("       2. TX/RX cruzados o GND suelto")
    print("       3. El RVR esta en sueño profundo")
