# Los repositorios del proyecto — cuál es cuál

Existe porque **la confusión entre repositorios ya costó tiempo real**: el 2026-08-03 se auditó «el
repositorio de la web» sin decir cuál de los tres era ni sobre qué rama, y dos auditorías correctas
llegaron a conclusiones opuestas.

**Inventario del 2026-08-04.** Son **nueve**, repartidos entre dos dueños.

---

## Vivos — aquí se trabaja

| Repositorio | Dueño | Vis. | Qué es |
|---|---|---|---|
| **`Atriz_migracion_ros2`** | Bura-hub | privado | **El cerebro.** Auditoría, plan, manual, RUNBOOK, `FLOTA.md`, prueba de aceptación, scripts de aprovisionamiento y las evidencias numeradas |
| **`atriz-lab`** | Bura-hub | privado | **La plataforma web.** Next.js + React + TypeScript. Contiene el cliente de rosbridge, en `frontend/src/lib/rosbridge/` |
| **`Atriz_rvr`** | Bura-hub | **PÚBLICO** | **El robot.** Driver, LIDAR, capa de seguridad, navegación y la biblioteca de prácticas. Rama de trabajo y por defecto: **`ros2`** |

🔴 **`Atriz_rvr` rama `main` es ROS 1 y no compila con `colcon`.** La rama viva es `ros2`.
🔐 **`Atriz_rvr` es público y su historial contiene la PSK del WiFi y la contraseña de `sphero`.**
Rotar las dos es lo único que cierra esa exposición; borrar ramas **no la cerró** (medido).

---

## Paraguas público

| | |
|---|---|
| **`ATRIZ`** (Bura-hub, público, ⭐1) | Repositorio paraguas y **única puerta pública del proyecto**. Contiene los dos PDF institucionales —desarrollo de software, y pruebas e implementación— y un submódulo al robot |

⚠️ **Los dos PDF describen la arquitectura ANTERIOR a la migración**, con funcionalidades después
descartadas (entre ellas la transmisión de vídeo: **los robots no llevan cámara**). Valen como
registro; **no describen el sistema actual**, y el README lo dice.

📝 **Hasta el 2026-08-04 sus dos submódulos apuntaban al sistema muerto** —`Atriz_rvr` rama `main`
(ROS 1) y `Atriz_web_server`—, así que un `git clone --recursive` repartía el stack antiguo entero.
Corregido: ahora apunta solo al driver, rama `ros2`, y se verificó **clonando como lo haría un
tercero**.

---

## Superados

| Repositorio | Dueño | Estado | Por qué |
|---|---|---|---|
| **`Atriz_web_server`** | Bura-hub | ✅ **ARCHIVADO** | La web anterior. **65 MB de los que el 98 % son artefactos** (`swarm_lab_env/`, `build/`, `devel/`). **Tres ramas SIN ancestro común** —`master`, `develop`, `pruebas`—; manda `pruebas`, que es la que tiene Monaco integrado de verdad. Superado por `atriz-lab` |
| **`ros_sphero_rvr`** | atriz-udenar | ✅ **ARCHIVADO** | Driver de ROS 1 (`catkin`, `rospy`). Superado por `Atriz_rvr` rama `ros2` |

🔐 **Los dos se archivaron el 2026-08-04, y `Atriz_web_server` solo DESPUÉS de rotar.** Contenía la
credencial de PostgreSQL en un `.env` **commiteado** (solo en `master`) y la **`SECRET_KEY` de los
JWT** en `core/security.py`, que estaba en **las tres ramas**. **Archivar no habría cerrado nada:**
deja el repositorio en solo lectura y los secretos siguen en el historial. **Rotar es lo único que
lo cierra**, y por eso se hizo en ese orden. Sigue siendo público, ahora en solo lectura.

⚠️ **Consecuencia de haberlo archivado, por si algún día se quiere purgar el historial:** un
repositorio archivado **no admite escrituras**, así que habría que **desarchivarlo primero**. Con
`forks = 0` la purga sería efectiva, pero es higiene — la exposición ya está cerrada por la
rotación.

---

## De la organización `atriz-udenar` — no son nuestros para tocar

Permisos comprobados: **solo lectura** (`admin: false`, `push: false`).

| Repositorio | Vis. | Qué es |
|---|---|---|
| `atriz-web` | PÚBLICO | Sitio informativo del laboratorio (HTML). **No confundir con `atriz-lab`**, que es la aplicación |
| `Practicas__SpheroRVR` | PÚBLICO | Prácticas iniciales, incluida Open Roberta |
| `atriz-server` | privado | **Vacío desde que se creó** (dic 2024). Candidato a borrar, pero es decisión de quien administre la organización |

---

## 📝 Propuesta de nombres, registrada y NO aplicada (2026-08-04)

Decisión del usuario: **no se renombra nada por ahora**. Queda escrito para no volver a razonarlo.

| Actual | Propuesta | Motivo |
|---|---|---|
| `Atriz_migracion_ros2` | `atriz-ingenieria` | 🔴 **Nombra un evento temporal, no un propósito.** La migración acaba; el manual, el RUNBOOK, la prueba de aceptación y las evidencias siguen. El día que acabe, el nombre miente |
| `Atriz_rvr` | `atriz-robot` | Ya no es solo «el RVR»: incluye LIDAR, navegación, seguridad y las prácticas |
| `atriz-lab` | `atriz-plataforma` | Distingue la aplicación del sitio informativo `atriz-udenar/atriz-web` |
| `ATRIZ` | *sin cambio* | Es el nombre del proyecto y la puerta pública con la estrella |

**El coste no es técnico** —GitHub redirige las URLs viejas, y clones y submódulos siguen
funcionando—: es que `Atriz_rvr` y `Atriz_migracion_ros2` están citados **decenas de veces** en la
documentación y en los clones de la Pi. Renombrar sin actualizar esas referencias **crea justo la
deriva que el nombre nuevo venía a evitar**.

→ El momento natural para retomarlo es **cuando la migración se dé por cerrada**.
