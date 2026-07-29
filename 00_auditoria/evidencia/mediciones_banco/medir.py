import rospy, time, statistics
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Imu

T = {}
def mk(name):
    T[name] = []
    def cb(msg, name=name): T[name].append(time.time())
    return cb

rospy.init_node('medidor', anonymous=True, disable_signals=True)
rospy.Subscriber('/odom', Odometry, mk('odom'), queue_size=200)
rospy.Subscriber('/imu',  Imu,      mk('imu'),  queue_size=200)
print("midiendo 30 s...", flush=True)
time.sleep(30)

print()
for n, ts in T.items():
    if len(ts) < 3:
        print(f"{n:6}: solo {len(ts)} mensajes"); continue
    dur = ts[-1] - ts[0]
    hz  = (len(ts)-1)/dur
    gaps = [ (ts[i+1]-ts[i])*1000 for i in range(len(ts)-1) ]
    print(f"{n:6}: {len(ts):4d} msgs en {dur:.1f}s -> {hz:5.2f} Hz")
    print(f"        intervalo  min {min(gaps):6.1f} ms | mediana {statistics.median(gaps):6.1f} ms | max {max(gaps):6.1f} ms")
    print(f"        jitter (desv. tipica) {statistics.pstdev(gaps):.1f} ms")
