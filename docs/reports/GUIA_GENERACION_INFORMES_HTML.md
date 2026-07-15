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
- **El HTML es un solo archivo autocontenido**: fuentes, escudo, figuras SVG inline e
  imágenes en base64. Nada referencia archivos externos (se puede enviar por correo tal cual).
- Los diagramas SVG y los PNG de capturas se guardan además como archivos sueltos en
  `docs/reports/figures/` (fuente editable / re-usable), aunque el HTML los lleve embebidos.

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
- **Fuente institucional**: `Ancizar Sans` embebida con un solo `@font-face` múltiple
  (4 variantes: 300/700 × normal/italic) como OTF base64. Cuerpo en peso 300.
- Variables: `--ink:#000; --mauve:#c9ada6; --mauve-line:#b9968c; --code:#274e13; --muted:#666`.
- `@page{ size:Letter; margin:15mm 13mm 15mm 14mm; }` y
  `print-color-adjust:exact` en `*` (los fondos de tabla sobreviven la impresión).
- Cuerpo: 11.7pt, `line-height:1.42`, justificado, `hyphens:auto`.
- Código inline: Consolas verde (`--code`) **sin** chip/fondo/borde.
- Tablas: encabezado malva (`--mauve`), bordes 0.6pt, 10pt.
- Saltos: `.pagebreak` explícito; `h2, table, figure, .shot, .todo { break-inside:avoid }`,
  `h1,h2 { break-after:avoid }`.

## 3. Figuras SVG (serie "Figura N.M")

- Diagramas de diseño: SVG **inline** dentro de `<figure class="fig">`, con la leyenda
  como `<text>` del propio SVG (última línea): `Figura 2.N — Título. Fuente: elaboración
  propia a partir del repositorio (…)`.
- El archivo fuente se guarda en `docs/reports/figures/fig_N_M_<slug>.svg`.
- `figure.fig svg{ max-width:100%; height:auto; }` y en el propio SVG
  `style="max-width:100%;max-height:225mm;height:auto;"` para que quepa en una página Letter.

## 4. Capturas de pantalla (serie aparte "Captura N.M")

**Decisión tomada (2026-07-15, confirmada con el usuario)**: las capturas se numeran como
serie propia `Captura 2.1–2.5`, intercalada con las figuras SVG **sin** renumerarlas.
Así las referencias en el texto a "la Figura 2.N" nunca se rompen.

- Placeholder mientras no existen: `<div class="shot">▣ <span>descripción de lo que debe
  mostrar</span></div>` (recuadro punteado malva; CSS `.shot` ya definido).
- Al materializarlas: cada `.shot` se reemplaza por
  ```html
  <figure class="fig">
    <img src="data:image/png;base64,…" alt="…"
         style="max-width:100%;height:auto;display:block;margin:0 auto 6pt auto;
                border:0.5pt solid #c9ccd4;border-radius:3pt;">
    <figcaption>Captura 2.N — <descripción>. Fuente: sistema IDI en ejecución local.</figcaption>
  </figure>
  ```
  Varias imágenes apiladas en una misma figure están bien (p. ej. selector arriba +
  chat abajo; o las tres rutas de enrutamiento).
- Los PNG fuente quedan en `docs/reports/figures/shot_N_M_<slug>.png`.
- Con las imágenes embebidas el HTML crece (~4 MB con 9 PNG a dsf=2) — aceptable.

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

### 5.4 Incrustación y verificación

- Reemplazar los `.shot` por `figure` con un **script** (`tools/embed_shots.py`), nunca a
  mano: los base64 son enormes. El script debe (a) verificar que encuentra exactamente los
  N placeholders antes de escribir, (b) sustituir en orden de aparición, (c) conservar
  CRLF/UTF-8, (d) assert final de que no queda `class="shot"`.
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
- [ ] HTML autocontenido (buscar `src="http` y `href="http` → solo debe haber URLs citadas como texto).
- [ ] Render verificado en navegador (imágenes cargan, sin overflow horizontal).
- [ ] PNG/SVG fuente en `figures/`; versiones viejas del capítulo en `docs/legacydocs/reports/`.
- [ ] `…_PENDIENTES.txt` al día; PDF regenerado o marcado como desactualizado.
