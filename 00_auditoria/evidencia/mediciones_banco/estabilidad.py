import rospy, time, statistics, subprocess, os
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Imu

DUR = 720           # 12 min
ts_odom, ts_imu = [], []
seqs = []
rospy.init_node('estabilidad', anonymous=True, disable_signals=True)
rospy.Subscriber('/odom', Odometry, lambda m: (ts_odom.append(time.time()), seqs.append(m.header.seq)), queue_size=500)
rospy.Subscriber('/imu',  Imu,      lambda m: ts_imu.append(time.time()),  queue_size=500)

pid = subprocess.run("pgrep -f '[A]triz_rvr_node.py'", shell=True, capture_output=True, text=True).stdout.strip().split('\n')[0]
def temp():
    return int(open('/sys/class/thermal/thermal_zone0/temp').read())/1000
def rss_cpu():
    try:
        o = subprocess.run(f"ps -o rss=,%cpu= -p {pid}", shell=True, capture_output=True, text=True).stdout.split()
        return int(o[0])//1024, float(o[1])
    except Exception:
        return -1, -1.0

t0 = time.time()
print(f"inicio {time.strftime('%H:%M:%S')} | duracion {DUR}s | pid nodo {pid}", flush=True)
muestras = []
while time.time() - t0 < DUR:
    time.sleep(60)
    r, c = rss_cpu()
    n = len(ts_odom)
    muestras.append((int(time.time()-t0), n, temp(), r, c))
    print(f"  t={int(time.time()-t0):4d}s  odom={n:5d}  temp={temp():4.1f}C  rss={r}MB  cpu={c:4.1f}%", flush=True)

print("\n" + "="*66, flush=True)
for nombre, ts in (('odom', ts_odom), ('imu', ts_imu)):
    if len(ts) < 10:
        print(f"{nombre}: SOLO {len(ts)} mensajes -> FALLO"); continue
    gaps = [(ts[i+1]-ts[i])*1000 for i in range(len(ts)-1)]
    med = statistics.median(gaps)
    huecos = [(i, g) for i, g in enumerate(gaps) if g > 3*med]
    print(f"{nombre}: {len(ts)} msgs | {(len(ts)-1)/(ts[-1]-ts[0]):.2f} Hz | mediana {med:.1f} ms | max {max(gaps):.1f} ms | sigma {statistics.pstdev(gaps):.1f} ms")
    print(f"      huecos > 3x mediana ({3*med:.0f} ms): {len(huecos)}")
    for i, g in huecos[:5]:
        print(f"         #{i} -> {g:.0f} ms")

if seqs:
    saltos = sum(1 for i in range(len(seqs)-1) if seqs[i+1] != seqs[i]+1)
    print(f"\nsecuencia: primer={seqs[0]} ultimo={seqs[-1]} recibidos={len(seqs)} discontinuidades={saltos}")
    perdidos = (seqs[-1]-seqs[0]+1) - len(seqs)
    print(f"mensajes perdidos por el suscriptor: {perdidos}")

print(f"\ntemperatura: min {min(m[2] for m in muestras):.1f}C  max {max(m[2] for m in muestras):.1f}C")
print(f"RSS del nodo: inicio {muestras[0][3]}MB  final {muestras[-1][3]}MB  (crecimiento {muestras[-1][3]-muestras[0][3]}MB)")
