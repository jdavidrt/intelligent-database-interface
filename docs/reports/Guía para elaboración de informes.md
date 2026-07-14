# Guía para la Elaboración de Informes — Trabajo de Grado IDI

Universidad Nacional de Colombia — Facultad de Ingeniería
Autor: Juan David Ramírez Torres (jdramirezt@unal.edu.co)
Proyecto: IDI (Intelligent Database Interface)

Esta guía sintetiza las directrices institucionales y las observaciones editoriales recibidas en la asesoría, de modo que cada informe del proyecto nazca ya alineado con el estándar de rigor exigido. Sirve como lista de verificación antes de entregar y como plantilla de estructura al empezar a redactar. La regla rectora es simple: todo lo que se promete en los objetivos debe poder rastrearse hasta una conclusión y una recomendación.

---

## 1. Estructura obligatoria del documento

Todo informe debe contener, en este orden, los siguientes componentes. La columna "Verificación" indica la pregunta que debe responderse con un "sí" antes de entregar.

| # | Componente | Qué debe contener | Verificación |
|---|------------|-------------------|--------------|
| 1 | Portada | Título completo, universidad, facultad, autor, correo, período | ¿El título coincide exactamente con el aprobado por el CADE? |
| 2 | Índice | Todas las secciones y subsecciones con su numeración | ¿El índice refleja el contenido real y su numeración? |
| 3 | Resumen | Síntesis del problema, propuesta, método y alcance del avance | ¿Se entiende el trabajo leyendo solo esto? |
| 4 | Introducción general | Ámbito, problema, pregunta, objetivos, método, descripción del contenido | ¿Están los seis sub-elementos? (ver Sección 2) |
| 5 | Capítulos | Un capítulo por cada objetivo específico | ¿Cada capítulo abre con su párrafo introductorio? |
| 6 | Conclusiones | Al menos una conclusión por cada objetivo | ¿Cada conclusión cita el objetivo al que aporta? |
| 7 | Recomendaciones | Al menos una recomendación por cada objetivo | ¿Cada recomendación cita el objetivo al que se vincula? |
| 8 | Bibliografía | Referencias en formato de citación consistente | ¿Toda cita en el texto aparece aquí y viceversa? |
| 9 | Anexos | Documentos de soporte (ver Sección 6) | ¿Se anexó la propuesta CADE en el documento final? |

---

## 2. La introducción general: sus seis elementos

La introducción no es un texto libre; es una estructura de seis piezas. Faltó una sola de ellas y el informe se considera incompleto. Cada pieza responde una pregunta concreta:

| Elemento | Pregunta que responde | Regla |
|----------|----------------------|-------|
| Ámbito y problema | ¿Cuál es el panorama y qué está roto en él? | Sustentar la brecha con evidencia citada (cifras, fuentes) |
| Pregunta de investigación | ¿Qué se quiere responder? | Una sola pregunta, clara y delimitada |
| Objetivos | ¿Qué se va a lograr? | Listar **textualmente** el General y los Específicos (ver Sección 3) |
| Enfoque metodológico | ¿Cómo se cumplirán los objetivos? | Un párrafo macro que anticipe el método (el detalle va en su capítulo) |
| Descripción del contenido | ¿Qué entrega este informe? | Indicar qué capítulo/avance se presenta y por qué |

> Nota de fondo recurrente: los objetivos suelen estar implícitos en una buena pregunta de investigación, pero eso no basta. Deben aparecer **listados de forma explícita**, ya sea dentro de la introducción o en una sección independiente. La metodología puede tener su propio capítulo, pero la introducción debe contener igualmente un párrafo que la anticipe a nivel macroscópico.

---

## 3. Objetivos: el eje de trazabilidad

Los objetivos son la columna vertebral del documento. Todo lo demás —capítulos, conclusiones, recomendaciones— se ancla a ellos.

Reglas:

1. Transcribir el Objetivo General y los Objetivos Específicos **literalmente** como fueron aprobados ante el CADE. Cualquier ajuste de redacción debe conservar el alcance pactado.
2. Asignar a cada objetivo específico un identificador estable (OE1, OE2, OE3, OE4). Ese identificador se reutiliza en capítulos, conclusiones y recomendaciones para hacer visible la trazabilidad.
3. Verificar la coherencia interna: si el cuerpo del documento dice "4GB de VRAM", el objetivo no puede decir "8GB". Las cifras y restricciones deben ser idénticas en toda la obra.

La regla de oro de la trazabilidad:

> Cada objetivo específico (OEn) → debe tener su propio capítulo → que cierra con al menos una conclusión rotulada (OEn) → y al menos una recomendación rotulada (OEn).

---

## 4. Estructura de cada capítulo

| Regla | Descripción |
|-------|-------------|
| Un capítulo por objetivo | El documento final tendrá tantos capítulos formales como objetivos específicos. En un avance temprano es válido entregar solo el capítulo del objetivo en curso. |
| Párrafo introductorio propio | Cada capítulo debe abrir con un párrafo que aclare y contextualice el objetivo específico que desarrolla. **Nunca** pasar directamente del título del capítulo al primer numeral. |
| Numeración jerárquica | Usar numeración consistente (1, 1.1, 1.1.1) y que el índice la refleje sin saltos ni cortes. |
| Cierre trazable | El capítulo debe poder mapearse, al final, contra una conclusión y una recomendación. |

Plantilla mínima de apertura de capítulo:

```
CAPÍTULO N: [TÍTULO]

[Párrafo introductorio: este capítulo desarrolla el objetivo específico OEn,
cuyo propósito es [...]. Para ello recorre [...]. El resultado alimenta [...].]

N.1. [Primer subtema]
```

---

## 5. Conclusiones y recomendaciones

Ambas secciones son obligatorias y ambas se rigen por la misma ley de trazabilidad.

| Sección | Regla mínima | Buena práctica |
|---------|--------------|----------------|
| Conclusiones | Al menos una por cada objetivo específico | Rotular cada conclusión con el objetivo al que aporta evidencia, p. ej. "Primera (aporta a OE1) — ..." |
| Recomendaciones | Al menos una por cada objetivo específico | Conectar cada recomendación con un objetivo y orientarla a la fase siguiente del proyecto |

La sección de recomendaciones es de carácter **obligatorio**; su ausencia es una falta de fondo, no un detalle menor. No debe confundirse con las conclusiones: la conclusión afirma lo que se halló; la recomendación propone lo que conviene hacer a partir de ese hallazgo.

---

## 6. Anexos y soportes (documento final)

| Anexo | Cuándo | Para qué |
|-------|--------|----------|
| Propuesta aprobada ante el CADE | Documento final de grado | Permite al comité y a los jurados contrastar las metas pactadas inicialmente frente a la evolución y el cumplimiento alcanzados |

Aunque en los avances intermedios este anexo no es exigible, conviene tenerlo listo desde temprano para no improvisarlo al cierre.

---

## 7. Reglas de forma (control de calidad editorial)

Los defectos de forma erosionan la credibilidad de un contenido técnico sólido. Antes de entregar, revisar:

| Defecto a evitar | Regla |
|------------------|-------|
| Encabezados corruptos | El nombre institucional debe leerse siempre completo y correcto: "UNIVERSIDAD NACIONAL DE COLOMBIA". Verificar **todas** las páginas; los errores de plantilla o de conversión a PDF suelen degradar el encabezado (p. ej. "VACIONAL", "LACIONAL"). |
| Texto truncado en tablas | Ninguna celda debe cortar la idea. Verificar que cada frase de cada tabla quepa y se lea completa en el PDF final. |
| Bucles de copiar y pegar | Ningún bloque debe repetirse ni mezclar el contenido de dos secciones. Cada módulo, sección o ítem debe tener su descripción única y sin colisiones. |
| Incoherencia sintáctica | Releer en voz alta las frases de cierre. Evitar oraciones rotas como "El es la frontera futura"; redactar "Este último representa la frontera futura". |
| Falta de conectores | Encadenar las ideas con puntuación y conectores adecuados ("[...] del trabajo de grado, **el cual corresponde al** análisis de requerimientos"). |
| Tildes diacríticas | Distinguir "el/él", "si/sí", "mas/más", "solo/sólo" según corresponda. |
| Inconsistencia de cifras | Las restricciones numéricas (VRAM, RAM, latencias, umbrales) deben ser idénticas en todo el documento y respecto a la propuesta. |
| Puntuación tras el enunciado en listas y subtítulos | En todo ítem de lista o subtítulo que presente un enunciado seguido de su desarrollo, separar ambos con dos puntos (`:`) y continuar en minúscula, nunca con punto (`.`) y mayúscula. Ejemplo correcto: "OE4 — Análisis de resultados: evaluar el desempeño de IDI [...]". Ejemplo incorrecto: "OE4 — Análisis de resultados. Evaluar el desempeño de IDI [...]". |

> Advertencia sobre el PDF: muchos defectos de encabezado y de tablas no viven en el archivo fuente (Markdown), sino que aparecen al **generar el PDF**. Tras cualquier corrección, regenerar el PDF y revisarlo página por página, no solo el fuente.

---

## 8. Reglas de formato Markdown

Para garantizar compatibilidad universal del archivo fuente:

1. Las tablas deben usar el formato Markdown estándar, con barras `|` y guiones `-`. No usar HTML ni formatos propietarios.
2. Dejar una línea en blanco antes de toda lista o tabla, y entre un encabezado y el contenido que le sigue, para asegurar el renderizado correcto.
3. El texto se redacta en prosa; las listas y tablas se reservan para enumeraciones, comparaciones o datos estructurados.
4. Todo el código y sus comentarios se escriben en inglés. El cuerpo del informe va en español.
5. Para las horas usar siempre el formato AM / PM.

---

## 9. Lista de verificación final (pre-entrega)

Marcar cada casilla antes de enviar el informe:

- [ ] Portada, índice y resumen presentes y correctos.
- [ ] Introducción con sus seis elementos (ámbito/problema, pregunta, objetivos, método, descripción del contenido).
- [ ] Objetivo General y Específicos listados textualmente y con identificador (OEn).
- [ ] Párrafo de anticipación metodológica en la introducción general.
- [ ] Cada capítulo abre con su párrafo introductorio propio.
- [ ] Al menos una conclusión por cada objetivo, rotulada con su OEn.
- [ ] Al menos una recomendación por cada objetivo, rotulada con su OEn.
- [ ] Bibliografía completa y consistente; toda cita del texto está referenciada.
- [ ] Cifras y restricciones coherentes en todo el documento y con la propuesta CADE.
- [ ] Encabezados institucionales correctos en todas las páginas del PDF.
- [ ] Sin tablas truncadas, sin bucles de texto, sin frases rotas.
- [ ] Listas y subtítulos usan dos puntos y minúscula tras el enunciado (no punto y mayúscula).
- [ ] PDF regenerado desde el fuente y revisado página por página.
- [ ] (Documento final) Propuesta CADE anexada como apéndice.

---

Documento de referencia interna — Trabajo de Grado IDI (Intelligent Database Interface)
Universidad Nacional de Colombia — Facultad de Ingeniería — Departamento de Sistemas e Industrial
