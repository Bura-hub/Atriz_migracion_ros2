"""Decodifica el protocolo YDLIDAR X2 (canal unico) sobre /dev/ttyUSB0.
Verifica cabeceras, checksums, frecuencia de giro y rango de distancias."""
import serial, time, struct, statistics, sys

PORT, BAUD, DUR = '/dev/ttyUSB0', 115200, 12
p = serial.Serial(PORT, BAUD, timeout=1)
p.reset_input_buffer()
buf = bytearray()
t0 = time.time()
paquetes = ok_chk = bad_chk = zero_pkts = 0
muestras_total = 0
dists = []
t_zero = []

while time.time() - t0 < DUR:
    buf += p.read(2048)
    while True:
        i = buf.find(b'\xaa\x55')
        if i < 0 or len(buf) - i < 10:
            if i > 0: del buf[:i]
            break
        ct, lsn = buf[i+2], buf[i+3]
        need = 10 + 2*lsn
        if len(buf) - i < need: break
        pkt = bytes(buf[i:i+need]); del buf[:i+need]
        paquetes += 1
        muestras_total += lsn
        fsa, lsa, cs = struct.unpack('<HHH', pkt[4:10])
        # checksum: XOR de todas las palabras de 16 bits excepto CS
        words = [struct.unpack('<H', pkt[0:2])[0], fsa,
                 struct.unpack('<H', pkt[2:4])[0], lsa]
        for k in range(lsn):
            words.append(struct.unpack('<H', pkt[10+2*k:12+2*k])[0])
        x = 0
        for w in words: x ^= w
        if x == cs: ok_chk += 1
        else:        bad_chk += 1
        if ct & 0x01:                        # paquete de inicio de vuelta
            zero_pkts += 1; t_zero.append(time.time())
        for k in range(lsn):
            d = struct.unpack('<H', pkt[10+2*k:12+2*k])[0] / 4.0   # mm
            if d > 0: dists.append(d)

p.close()
dur = time.time() - t0
print(f"duracion            : {dur:.1f} s")
print(f"paquetes decodificados: {paquetes}   ({paquetes/dur:.0f}/s)")
print(f"checksum OK / KO    : {ok_chk} / {bad_chk}   ({100*ok_chk/max(paquetes,1):.1f}% validos)")
print(f"muestras totales    : {muestras_total}   ({muestras_total/dur:.0f} muestras/s)")
print(f"paquetes de inicio de vuelta: {zero_pkts}")
if len(t_zero) > 2:
    per = [(t_zero[i+1]-t_zero[i]) for i in range(len(t_zero)-1)]
    print(f"frecuencia de giro  : {1/statistics.median(per):.2f} Hz   (mediana {statistics.median(per)*1000:.1f} ms)")
    print(f"muestras por vuelta : {muestras_total/max(zero_pkts,1):.0f}")
if dists:
    dists.sort()
    print(f"distancias validas  : {len(dists)}  ({100*len(dists)/max(muestras_total,1):.0f}% de las muestras)")
    print(f"  min {min(dists)/1000:.3f} m | p50 {dists[len(dists)//2]/1000:.3f} m | max {max(dists)/1000:.3f} m")
print()
if paquetes > 100 and ok_chk/paquetes > 0.9:
    print("VEREDICTO: el YDLIDAR X2 FUNCIONA. Protocolo valido, checksums correctos.")
else:
    print("VEREDICTO: datos presentes pero el protocolo no cuadra. Revisar baudrate o modelo.")
