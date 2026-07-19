# Guía: generación de informes HTML del proyecto IDI

Condensa lo aprendido produciendo `IDI_Segundo_Informe.html` (capítulo 2, julio 2026):
las convenciones del documento, el playbook de capturas de pantalla del sistema en vivo,
y los errores ya cometidos para no repetirlos. Los scripts que funcionaron están en
[`tools/`](tools/).

---

## 1. Piezas y flujo general

```
IDI_CapituloN_vX.md      →  IDI_<Nombre>_Informe.html  →  IDI_<Nombre>_Informe.pdf
(contenido canónico,        (documento entregable,        (impresión del HTML,
 versionado, con marcas      autocontenido, es-CO)         Letter, se regenera
 [PANTALLAZO]/[PENDIENTE])                                 manualmente)
```

- **Fuente de contenido**: los capítulos viven en `docs/reports/IDI_CapituloN_vX.md`.
  Versiones viejas se archivan en `docs/legacydocs/reports/`. El canon editorial
  (identidad didáctica primero, UC-06 silencioso, 62 RF / 20 RNF / 7 UC / 7 métricas)
  está descrito en la memoria del proyecto y en los propios capítulos v3.
- **Marcas en el md**:
  - `[PANTALLAZO: …]` → en el HTML se convierte en un recuadro `<div class="shot">` (ver §5).
  - `[PENDIENTE: …]` → NO va al HTML entregable; se extrae a un sidecar
    `IDI_<Nombre>_Informe_PENDIENTES.txt` con fecha y sección de origen.
- **Regla de economía de contexto (2026-07-17)**: el HTML del informe y los `.md` de
  capítulo contienen **solo prosa y estructura**. Todo bloque grande, estable y no-prosa
  vive en su propio archivo y se referencia por ruta relativa:
  - **Imágenes — NUNCA base64**, ni en el HTML ni en los `.md`: siempre
    `<img src="figures/shot_N_M_<slug>.png">` / `![...](figures/…png)`. El base64 fue
    un error costoso: infló el Tercer Informe a >1 MB, volvió el archivo ineditable a
    mano y cada edición asistida por IA obligaba a arrastrar megabytes de texto inútil.
  - **CSS y fuentes**: el estilo compartido (incluidos los `@font-face` de Ancizar con
    su OTF base64 — el base64 se tolera solo ahí, encapsulado) va en
    `docs/reports/assets/informe.css`, enlazado con
    `<link rel="stylesheet" href="assets/informe.css">`. En el `<head>` del informe
    solo quedan los overrides mínimos propios de ese documento.
  - **Escudo de la portada**: archivo suelto (`assets/escudo_unal.png`), referenciado —
    no incrustado.
  - **SVG de diagramas**: archivos en `figures/fig_N_M_<slug>.svg` referenciados con
    `<img src="figures/fig_N_M_<slug>.svg">`, ya no inline (ver §3).
  Razón: al editar un informe (a mano o con Claude), el archivo que se itera debe
  contener solo el texto que de verdad se está redactando.
- El entregable es el HTML **junto a sus carpetas `figures/` y `assets/`** (misma ruta
  relativa), o el PDF impreso desde él cuando se necesite un archivo único (p. ej. correo).
- Los PNG de capturas y los SVG fuente viven en `docs/reports/figures/`.
- Estado de migración: el Tercer Informe ya referencia sus capturas; aún lleva fuentes y
  escudo embebidos en el `<head>` heredado — extraerlos a `assets/` en la próxima
  regeneración. Los informes nuevos nacen ya con esta estructura.

## 2. Esqueleto del documento HTML

Orden del `<body>`:

1. **Portada** (`div.titlepage`): `tp-h1` "Informe Trabajo de Grado", `tp-h2` con el título
   del informe, escudo UNAL (`img.tp-escudo`, PNG base64, 52mm), bloque `tp-people`
   (Estudiante / Docente). Luego `<div class="pagebreak"></div>`.
2. **Índice**: `h1.center.toc-title` "ÍNDICE" + `div.toc` con `toc-top` (capítulo) y
   `toc-sub` (secciones N.M). Sin números de página (el PDF los pone el lector).
3. **Cuerpo**: `h1.center.chap-title` "CAPÍTULO N: …" y secciones `h2` "N.M. TÍTULO EN MAYÚSCULAS".
4. **Referencias**: `h1.center.chap-title.refs` "REFERENCIAS", párrafos estilo APA 7
   (autores, año, título, venue en `<em>`). Solo se citan fuentes realmente usadas en el capítulo.
5. **Cierre**: dos `<p>` — "Universidad Nacional de Colombia — Facultad de Ingeniería —
   Departamento de Sistemas e Industrial" y "Período 2026-1S".

### CSS y tipografía (copiar del informe anterior, no reinventar)

- `<html lang="es">`, `<meta charset="utf-8">`, CRLF y UTF-8 (así lo dejó Word/Windows — conservarlo al editar por script: `read_text(..., newline="")`).
- **Todo el CSS compartido va en `assets/informe.css`** (regla de economía de contexto,
  §1): ahí viven las reglas siguientes y los `@font-face`. El informe lo enlaza con
  `<link rel="stylesheet" href="assets/informe.css">` y solo define overrides propios.
- **Fuente institucional**: `Ancizar Sans` con un solo `@font-face` múltiple
  (4 variantes: 300/700 × normal/italic), OTF base64 **dentro de `informe.css`** —
  único lugar donde se tolera base64. Cuerpo en peso 300.
- Variables: `--ink:#000; --mauve:#c9ada6; --mauve-line:#b9968c; --code:#274e13; --muted:#666`.
- `@page{ size:Letter; margin:15mm 13mm 15mm 14mm; }` y
  `print-color-adjust:exact` en `*` (los fondos de tabla sobreviven la impresión).
- Cuerpo: 11.7pt, `line-height:1.42`, justificado, `hyphens:auto`.
- Código inline: Consolas verde (`--code`) **sin** chip/fondo/borde.
- Tablas: encabezado malva (`--mauve`), bordes 0.6pt, 10pt.
- Saltos: `.pagebreak` explícito; `h2, table, figure, .shot, .todo { break-inside:avoid }`,
  `h1,h2 { break-after:avoid }`.

## 3. Figuras SVG (serie "Figura N.M")

- Diagramas de diseño: archivo `docs/reports/figures/fig_N_M_<slug>.svg`, referenciado
  desde el informe como
  `<figure class="fig"><img src="figures/fig_N_M_<slug>.svg" alt="…"></figure>` —
  **ya no inline** (regla de economía de contexto, §1: cientos de líneas de markup SVG
  no deben estorbar la edición de la prosa). La leyenda sigue viviendo como `<text>`
  dentro del propio SVG (última línea): `Figura 2.N — Título. Fuente: elaboración
  propia a partir del repositorio (…)`, así el archivo es autoexplicativo también suelto.
- `figure.fig img{ max-width:100%; height:auto; }` y en el propio SVG
  `style="max-width:100%;max-height:225mm;height:auto;"` para que quepa en una página Letter.
- Nota: referenciado vía `<img>`, el SVG no hereda el CSS del documento — todo su estilo
  (incluida la tipografía de sus textos) debe ser autocontenido en el archivo SVG.

## 4. Capturas de pantalla (serie aparte "Captura N.M")

**Decisión tomada (2026-07-15, confirmada con el usuario)**: las capturas se numeran como
serie propia `Captura 2.1–2.5`, intercalada con las figuras SVG **sin** renumerarlas.
Así las referencias en el texto a "la Figura 2.N" nunca se rompen.

- Placeholder mientras no existen: `<div class="shot">▣ <span>descripción de lo que debe
  mostrar</span></div>` (recuadro punteado malva; CSS `.shot` ya definido).
- Al materializarlas: cada `.shot` se reemplaza por
  ```html
  <figure class="fig">
    <img src="figures/shot_N_M_<slug>.png" alt="…"
         style="max-width:100%;height:auto;display:block;margin:0 auto 6pt auto;
                border:0.5pt solid #c9ccd4;border-radius:3pt;">
    <figcaption>Captura 2.N — <descripción>. Fuente: sistema IDI en ejecución local.</figcaption>
  </figure>
  ```
  Varias imágenes apiladas en una misma figure están bien (p. ej. selector arriba +
  chat abajo; o las tres rutas de enrutamiento).
- Los PNG quedan en `docs/reports/figures/shot_N_M_<slug>.png` y el HTML **los referencia
  por esa ruta relativa — nunca en base64** (ver la política de imágenes de §1; el
  Segundo Informe de 4 MB es el contraejemplo que no se repite). El script generador debe
  incluir un assert de que el cuerpo no contiene `data:image`.

## 5. Playbook de captura (sistema en vivo)

### 5.1 Levantar el stack

**No usar `start.py`** para esto: usa `uvicorn --reload`, que es poco fiable en esta
máquina. Lanzar los tres procesos a mano, en background:

```bash
llama-server --model models/qwen2.5-coder-3b-instruct-q4_k_m.gguf --port 7860 -ngl 99
.venv/Scripts/python -m uvicorn backend.app.main:app --port 5000     # cwd = raíz, SIN --reload
npm run dev                                                          # cwd = frontend/
```

Salud: `:7860/health`, `:5000/docs`, `:5173/`. Al terminar, matar por puerto
(`Get-NetTCPConnection -LocalPort 7860,5000,5173 -State Listen | … Stop-Process`).

### 5.2 Automatización del navegador

- `playwright-core` (npm, sin descarga de navegadores) + `chromium.launch({ channel: 'msedge' })`
  usa el Edge del sistema. Instalarlo en un directorio temporal, no en el repo.
- Contexto: `viewport 1360×850`, `deviceScaleFactor: 2` (nítido en impresión).
- Selectores estables de la UI: `.chat-input`, `.send-btn`, `.message.user-message`,
  `.message.bot-message` (¡excluir `.agent-progress`, que también es bot-message!),
  `.agent-progress`, `.agent-step-adapter`, botón `button:has-text("DB Profile")`,
  drawer `text=Database Map`, selector de BD `text=Select the database`.
- "Turno terminado" = apareció un `bot-message` nuevo **y** `.send-btn:not([disabled])`.
  Timeout LLM: 240 s (modelo local 3B, GTX 1650).

### 5.3 Gotchas descubiertos (no repetir)

1. **Animación de entrada del selector**: capturar recién cargado sale semitransparente
   y desplazado. Esperar ~3 s tras `waitForSelector` antes del screenshot.
2. **El drawer intercepta el header**: con el drawer abierto, clicar la pestaña del header
   falla (`subtree intercepts pointer events`). Cerrarlo con su botón ✕
   (`aria-label="Close panel"`), no con la pestaña.
3. **El stream NDJSON de `/query` llega bufferizado**: todas las líneas (eventos de agente
   + resultado) llegan el mismo segundo, al final. La barra de progreso **nunca se pinta**,
   ni en headless ni en uso normal. Para capturarla: envolver `window.fetch` vía
   `addInitScript` y re-emitir las líneas reales con pausas (~700 ms entre eventos,
   reteniendo la línea final `type:'result'` ~12 s). Son los eventos auténticos del
   pipeline, solo re-temporizados. (Defecto de fondo pendiente de arreglar en el backend.)
4. **El LLM 3B es no determinista y falible**: EC-01 alucinó `country_code` una vez y otra
   metió un `JOIN users` espurio que triplicaba filas. **Validar cada respuesta antes de
   capturar** (texto del último bot-message debe contener `RESULTS`, no contener
   `Verification failed`, y para la captura estrella tampoco `JOIN` espurio) y reintentar
   la misma pregunta hasta 3–4 veces.
5. **Redirect off-topic frágil**: "What is the capital of France?" toma la ruta correcta
   pero el modelo responde "Paris" en vez de redirigir. "What is the weather today?" sí
   produce la redirección cortés de forma confiable — usar esa.
6. **La barra de input es fija** y tapa el final del último mensaje. Para capturar un par
   pregunta+respuesta completo: agrandar el viewport a `alto_del_mensaje + 500`,
   `scrollIntoView({block:'center'})`, y recortar (`clip`) topando el borde inferior en
   `input.y - 6`. No usar `locator.screenshot()` directo en elementos más altos que el
   viewport (recorta mal con el header sticky).
7. **Preguntas conocidas-buenas** (probes de `tests/gate_d1.py`, en inglés como la UI):
   - 4 paneles: `Show me all artists from Colombia.` (reintentar hasta SQL sin JOIN)
   - Ruta datos corta: `How many artists are from Colombia?`
   - Ruta meta: `What tables does this database have?`
   - Off-topic: `What is the weather today?`
   - Progreso: `What is the average track duration in minutes?` (EC-05)
8. **Inconsistencia conocida**: la respuesta meta dice "18 tables" y el drawer "TABLES (19)".
   Si ambas capturas van al informe, que no queden en la misma página, o arreglar el origen.

### 5.4 Inserción y verificación

- Reemplazar los `.shot` por `figure` con un **script** (p. ej. `tools/build_tercer_informe.py`),
  nunca a mano. El script debe (a) verificar que encuentra exactamente los
  N placeholders antes de escribir, (b) sustituir en orden de aparición, (c) conservar
  CRLF/UTF-8, (d) assert final de que no queda `class="shot"`, (e) verificar que cada
  PNG referenciado existe en `figures/` y (f) assert de que el cuerpo generado no
  contiene `base64,` — las capturas van por referencia relativa, no incrustadas.
- Verificación final con Playwright sobre `file:///…/IDI_…_Informe.html`: 0 divs `.shot`,
  todos los `<img>` con `naturalWidth > 0`, las figuras SVG intactas. Revisar visualmente
  1–2 PNG (verificar que muestran lo que la leyenda promete).
- Actualizar el sidecar `…_PENDIENTES.txt` (fecha, qué se resolvió, si el PDF quedó
  desactualizado a propósito).

## 6. PDF

El PDF se regenera imprimiendo el HTML final (Edge/Chrome → Guardar como PDF, tamaño
carta, márgenes por defecto — el `@page` del documento manda), o con Playwright:
`page.pdf({ preferCSSPageSize: true, printBackground: true })`. Hacerlo **solo cuando el
usuario lo pida** — el 2026-07-15 se dejó desactualizado a propósito.

## 7. Checklist de entrega

- [ ] Portada, índice, secciones, referencias APA y cierre institucional presentes.
- [ ] 0 marcas `[PENDIENTE]`/`[PANTALLAZO]` en el HTML (movidas al sidecar o resueltas).
- [ ] Figuras SVG numeradas `Figura N.M` en serie continua; capturas `Captura N.M` en serie propia.
- [ ] Sin dependencias remotas (buscar `src="http` y `href="http` → solo URLs citadas como texto).
- [ ] 0 base64 en el HTML del informe y en los `.md` de capítulo (el único base64 tolerado
      son los `@font-face` dentro de `assets/informe.css`). Capturas y SVG por referencia
      relativa a `figures/`; CSS compartido enlazado desde `assets/informe.css`.
- [ ] El HTML se entrega junto a `figures/` y `assets/` (o como PDF impreso para archivo único).
- [ ] Render verificado en navegador (imágenes cargan, sin overflow horizontal).
- [ ] PNG/SVG fuente en `figures/`; versiones viejas del capítulo en `docs/legacydocs/reports/`.
- [ ] `…_PENDIENTES.txt` al día; PDF regenerado o marcado como desactualizado.
