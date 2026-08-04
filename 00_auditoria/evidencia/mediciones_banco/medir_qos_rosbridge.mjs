#!/usr/bin/env node
/**
 * T8 · Mide contra rvr-01 lo que el diseño del cliente marca NO VERIFICADO.
 *
 * ⚠️ ENCIENDE EL BARRIDO DEL LIDAR (el X2 pasa de 2,7 a 11,8 Hz) y LO APAGA
 *    al terminar, pase lo que pase. NO MUEVE EL ROBOT: no publica en
 *    /cmd_vel_raw ni en /emergency_stop.
 *
 * Cada pregunta va en su PROPIA conexion, para que un fallo no contamine a las
 * demas, y cada una lleva su CONTROL:
 *   A  /odom SIN campo qos      (control)
 *   B  /odom CON campo qos      -> ¿existe extract_qos_profile en el 2.7.0?
 *   C  /imu SIN throttle_rate   (control)
 *   D  /imu CON throttle_rate   -> ¿lo respeta?
 *   E  los seis topics de telemetria -> kB/s reales por topic
 */
const HOST = process.argv[2] ?? 'rvr-01.local'
const URL = `ws://${HOST}:9090`
const SEGUNDOS = Number(process.argv[3] ?? 30)

const dormir = (ms) => new Promise((r) => setTimeout(r, ms))

function abrir(nombre) {
  return new Promise((listo, falla) => {
    const ws = new WebSocket(URL)
    const plazo = setTimeout(() => falla(new Error(`${nombre}: no abrio en 10 s`)), 10000)
    ws.addEventListener('open', () => { clearTimeout(plazo); listo(ws) })
    ws.addEventListener('error', (e) => { clearTimeout(plazo); falla(new Error(`${nombre}: ${e.message ?? 'error'}`)) })
  })
}

const contador = (ws) => {
  const c = { n: 0, bytes: 0, porTopic: new Map(), avisos: [] }
  ws.addEventListener('message', (e) => {
    const bruto = String(e.data)
    let m
    try { m = JSON.parse(bruto) } catch { return }
    if (m.op === 'publish') {
      c.n++; c.bytes += bruto.length
      const p = c.porTopic.get(m.topic) ?? { n: 0, bytes: 0 }
      p.n++; p.bytes += bruto.length
      c.porTopic.set(m.topic, p)
    } else if (m.op !== 'service_response') {
      c.avisos.push(bruto.slice(0, 160))
    }
  })
  return c
}

const env = (ws, o) => ws.send(JSON.stringify(o))

async function main() {
  console.log(`objetivo: ${URL}   ventana: ${SEGUNDOS} s\n`)

  // ── conexion de control: enciende y apaga el barrido ──────────────────────
  const ctl = await abrir('ctl')
  const respuestas = []
  ctl.addEventListener('message', (e) => {
    const m = JSON.parse(String(e.data))
    if (m.op === 'service_response') respuestas.push(m)
  })

  let apagado = false
  const apagarBarrido = () => {
    if (apagado) return
    apagado = true
    try { env(ctl, { op: 'call_service', service: '/stop_scan', args: {}, id: 'off' }) } catch {}
  }
  // El barrido se apaga PASE LO QUE PASE: es la regla del proyecto.
  process.on('exit', apagarBarrido)
  process.on('SIGINT', () => { apagarBarrido(); process.exit(130) })

  console.log('→ /start_scan …')
  env(ctl, { op: 'call_service', service: '/start_scan', args: {}, id: 'on' })
  await dormir(3000)
  console.log('   respuesta:', JSON.stringify(respuestas.find((r) => r.id === 'on') ?? '(ninguna)'), '\n')

  // ── A/B: ¿acepta el campo qos? ────────────────────────────────────────────
  const A = await abrir('A'); const cA = contador(A)
  const B = await abrir('B'); const cB = contador(B)
  env(A, { op: 'subscribe', topic: '/odom', type: 'nav_msgs/msg/Odometry' })
  env(B, { op: 'subscribe', topic: '/odom', type: 'nav_msgs/msg/Odometry',
           qos: { reliability: 'best_effort', durability: 'volatile', history: 'keep_last', depth: 10 } })

  // ── C/D: ¿respeta throttle_rate? ──────────────────────────────────────────
  const C = await abrir('C'); const cC = contador(C)
  const D = await abrir('D'); const cD = contador(D)
  env(C, { op: 'subscribe', topic: '/imu', type: 'sensor_msgs/msg/Imu' })
  env(D, { op: 'subscribe', topic: '/imu', type: 'sensor_msgs/msg/Imu', throttle_rate: 500 })

  // ── E: caudal real por topic ──────────────────────────────────────────────
  const E = await abrir('E'); const cE = contador(E)
  const TEL = [
    ['/odom', 'nav_msgs/msg/Odometry'], ['/scan', 'sensor_msgs/msg/LaserScan'],
    ['/imu', 'sensor_msgs/msg/Imu'], ['/battery_state', 'sensor_msgs/msg/BatteryState'],
    ['/motor_status', 'atriz_rvr_msgs/msg/MotorStatus'], ['/encoders', 'atriz_rvr_msgs/msg/Encoder'],
  ]
  for (const [t, tipo] of TEL) env(E, { op: 'subscribe', topic: t, type: tipo })

  const t0 = Date.now()
  console.log(`midiendo ${SEGUNDOS} s …`)
  await dormir(SEGUNDOS * 1000)
  const s = (Date.now() - t0) / 1000

  console.log('\n══════════ 1 · ¿ACEPTA EL CAMPO qos? ══════════')
  console.log(`  A  /odom SIN qos (control) : ${cA.n} msg  ${(cA.n / s).toFixed(2)} Hz`)
  console.log(`  B  /odom CON qos           : ${cB.n} msg  ${(cB.n / s).toFixed(2)} Hz`)
  console.log(cB.n === 0 && cA.n > 0
    ? '  → 🔴 CON qos NO LLEGA NADA: el campo ROMPE la suscripcion en esta version.'
    : cB.n > 0 ? '  → ✅ el campo se acepta (o se ignora) sin romper la suscripcion.' : '  → ⚠️ tampoco llega el control: mira si el driver publica.')

  console.log('\n══════════ 2 · ¿RESPETA throttle_rate? ══════════')
  console.log(`  C  /imu SIN throttle (control) : ${cC.n} msg  ${(cC.n / s).toFixed(2)} Hz`)
  console.log(`  D  /imu CON throttle_rate 500  : ${cD.n} msg  ${(cD.n / s).toFixed(2)} Hz  (esperado ~2 Hz)`)
  const r = cC.n > 0 ? cD.n / cC.n : NaN
  console.log(`  → ${r < 0.35 ? '✅ LO RESPETA' : '🔴 NO lo respeta'} (D/C = ${r.toFixed(2)})`)

  console.log('\n══════════ 3 · CAUDAL REAL POR TOPIC ══════════')
  let total = 0
  for (const [t] of TEL) {
    const p = cE.porTopic.get(t) ?? { n: 0, bytes: 0 }
    total += p.bytes
    console.log(`  ${t.padEnd(16)} ${(p.bytes / s / 1024).toFixed(2).padStart(7)} kB/s   ${(p.n / s).toFixed(2).padStart(6)} Hz   ${p.n} msg`)
  }
  console.log(`  ${'TOTAL'.padEnd(16)} ${(total / s / 1024).toFixed(2).padStart(7)} kB/s        (referencia navegando: 80,7)`)
  for (const [t] of TEL) {
    const p = cE.porTopic.get(t) ?? { bytes: 0 }
    if (total > 0 && p.bytes / total > 0.5) console.log(`  → ${t} es el ${(100 * p.bytes / total).toFixed(0)} % del trafico`)
  }

  const avisos = [...cA.avisos, ...cB.avisos, ...cC.avisos, ...cD.avisos, ...cE.avisos]
  console.log('\n══════════ 4 · MENSAJES NO-publish RECIBIDOS ══════════')
  console.log(avisos.length ? avisos.slice(0, 8).join('\n') : '  ninguno — coherente con que rosbridge 2.7.0 no manda `status`')

  console.log('\n→ /stop_scan …')
  apagarBarrido()
  await dormir(1500)
  console.log('   respuesta:', JSON.stringify(respuestas.find((x) => x.id === 'off') ?? '(ninguna)'))
  for (const w of [ctl, A, B, C, D, E]) { try { w.close() } catch {} }
  await dormir(300)
}

main().catch(async (e) => { console.error('FALLO:', e.message); process.exitCode = 1 })
