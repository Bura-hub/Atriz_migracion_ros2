---
name: Órbita + Bloques
colors:
  surface: '#12131c'
  surface-dim: '#12131c'
  surface-bright: '#383843'
  surface-container-lowest: '#0c0e17'
  surface-container-low: '#1a1b24'
  surface-container: '#1e1f29'
  surface-container-high: '#282933'
  surface-container-highest: '#33343e'
  on-surface: '#e2e1ef'
  on-surface-variant: '#c4c5d9'
  inverse-surface: '#e2e1ef'
  inverse-on-surface: '#2f303a'
  outline: '#8e8fa2'
  outline-variant: '#444656'
  surface-tint: '#bbc3ff'
  primary: '#bbc3ff'
  on-primary: '#001d93'
  primary-container: '#2b4bf2'
  on-primary-container: '#d7dbff'
  inverse-primary: '#2748ef'
  secondary: '#c5f032'
  on-secondary: '#293500'
  secondary-container: '#aad301'
  on-secondary-container: '#455700'
  tertiary: '#ffb4a4'
  on-tertiary: '#630e00'
  tertiary-container: '#b92a0a'
  on-tertiary-container: '#ffd3ca'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#dee0ff'
  primary-fixed-dim: '#bbc3ff'
  on-primary-fixed: '#000f5d'
  on-primary-fixed-variant: '#002ccd'
  secondary-fixed: '#c7f335'
  secondary-fixed-dim: '#acd609'
  on-secondary-fixed: '#161e00'
  on-secondary-fixed-variant: '#3c4d00'
  tertiary-fixed: '#ffdad3'
  tertiary-fixed-dim: '#ffb4a4'
  on-tertiary-fixed: '#3d0600'
  on-tertiary-fixed-variant: '#8c1800'
  background: '#12131c'
  on-background: '#e2e1ef'
  surface-variant: '#33343e'
  background-well: '#07080D'
  surface-elevated: '#0C0E16'
  text-primary: '#EDEFF5'
  text-muted: '#8B90A3'
  accent-electric: '#5B8CFF'
  accent-cyan: '#22D3EE'
  status-recent: '#4ADE80'
  status-watch: '#FBBF24'
  status-action: '#FB6A5A'
  border-glass: rgba(255, 255, 255, 0.09)
typography:
  display-lg:
    fontFamily: Geist
    fontSize: clamp(2.5rem, 6vw, 4.875rem)
    fontWeight: '650'
    lineHeight: '1.1'
    letterSpacing: -0.045em
  headline-robot:
    fontFamily: Geist
    fontSize: clamp(1.5rem, 3.2vw, 2.4rem)
    fontWeight: '600'
    lineHeight: '1.2'
  data-lg:
    fontFamily: Geist Mono
    fontSize: 40px
    fontWeight: '600'
    lineHeight: '1.0'
    letterSpacing: tabular-nums
  card-title:
    fontFamily: Geist
    fontSize: 19px
    fontWeight: '600'
    lineHeight: '1.4'
  body-md:
    fontFamily: Geist
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.55'
  label-xs:
    fontFamily: Geist Mono
    fontSize: 11.5px
    fontWeight: '500'
    lineHeight: '1.0'
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  step-delay: 60ms
  total-entrance: 720ms
  glass-blur: 20px
---

# Design System: Laboratorio Atriz — Órbita + Bloques

## §2 · El mundo visual

### 2.1 · El registro
- **Fondo de la aplicación (Pozo):** `#07080D`
- **Cabeceras fijas (Pozo elevado):** `#0C0E16`
- **Luz ambiente (Orbes fijos):**
  - Orbe A (arriba izq): 620px, `rgba(91,140,255,0.34)`
  - Orbe B (derecha): 560px, `rgba(34,211,238,0.20)`

### 2.2 · Superficies
- **VIDRIO:**
  - `background: rgba(255,255,255,0.045)`
  - `border: 1px solid rgba(255,255,255,0.09)`
  - `backdrop-filter: blur(20px)`
  - `border-radius: 20px`
- **BLOQUE (Plena saturación):**
  - `border-radius: 20px`
  - Colores: Cobalto `#2B4BF2`, Lima `#B6E01E`, Coral `#FF5C39`
  - Galón (trama diagonal): `repeating-linear-gradient(45deg, rgba(255,255,255,0.55), rgba(255,255,255,0.55) 10px, transparent 10px, transparent 20px)`
  - Paso del galón: 14px (MIRAR), 6px (IR).

### 2.3 · Colores de estado (Texto e Insignias)
- **Texto:** `#EDEFF5`
- **Texto tenue:** `#8B90A3`
- **Filo:** `rgba(255,255,255,0.09)`
- **Neutro:** `#8B90A3` (no se sabe)
- **Vivo:** `#4ADE80` (reciente)
- **Mirar:** `#FBBF24`
- **Ir:** `#FB6A5A`
- **Acento (Eléctrico):** `#5B8CFF`
- **Acento (Cian):** `#22D3EE`

### 2.4 · Tipografía
- **Titulares y Cuerpo:** `Geist` (400, 500, 600, 650)
- **Cifras Medidas:** `Geist Mono` con `font-variant-numeric: tabular-nums`

**Escala:**
- Titular: `clamp(2.5rem, 6vw, 4.875rem)`, peso 650, tracking -0.045em.
- ID Robot Muro: `clamp(1.5rem, 3.2vw, 2.4rem)`, peso 600.
- Cifra grande: 38-42px, peso 600.
- Título tarjeta: 19px, peso 600.
- Cuerpo: 15-16px, peso 400, leading 1.55.

### 2.5 · Componentes y Reglas
- **Tarjeta de Vidrio:** Con filo superior de 1px en degradado del color de estado.
- **Botón Parada de Emergencia:** Ancho completo, 64px alto, coral saturado, versalitas 20px, borde 4px claro, sin sombra. Sticky top-0.
- **Insignia de estado:** Píldora con punto de 5px.
- **Medida:** Microetiqueta arriba, cifra+unidad grande (mono), antigüedad debajo (11.5px).
- **Movimiento:** Entrada escalonada de 60ms entre tarjetas, 720ms total, cubic-bezier(0.23, 1, 0.32, 1). Solo al montar.

### §8 · Restricciones Críticas
- Prohibido: Porcentajes de batería, medidores circulares, animaciones infinitas, negro puro, emojis, latencia inventada.
- "No se sabe" debe verse distinto de cero. Raya `—` en mono.
