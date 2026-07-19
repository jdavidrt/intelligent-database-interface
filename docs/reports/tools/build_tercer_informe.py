"""Regenera el cuerpo de IDI_Tercer_Informe.html a partir de IDI_Capitulo3_v2.md.

Conserva del HTML existente todo lo caro y estable — el <head> con las fuentes
Ancizar en base64 y la portada con el escudo — y reemplaza desde el ÍNDICE hasta
</body> con el contenido del capítulo v2 (2026-07-17): §3.10 expandida, rama GGUF
en §3.8, revisión editorial (casos límite por nombre, "query" en vez de "sonda"),
§3.11–3.14 reescritas y las siete Capturas 3.1–3.7 (3.2–3.4: evidencia de
ejecución del Generador SQL, añadidas el 2026-07-17).

Política de imágenes (2026-07-17): las capturas NO van en base64 — se insertan
como referencias relativas a figures/shot_*.png. El base64 infló el HTML a >1 MB
y lo volvió ineditable; el entregable es el HTML junto a su carpeta figures/
(o el PDF impreso desde él). Solo el <head> (fuentes Ancizar) y la portada
(escudo) conservan base64, y este script no los toca.

Reglas (GUIA_GENERACION_INFORMES_HTML.md §5.4):
- Conserva CRLF y UTF-8 (newline="").
- Los [PENDIENTE] del md NO van al HTML: viven en el sidecar _PENDIENTES.txt.
- Assert final: no quedan marcas [PENDIENTE]/[PANTALLAZO] ni class="shot".
"""

import io
import re
from pathlib import Path

REPORTS = Path(__file__).resolve().parent.parent
REPORT = REPORTS / "IDI_Tercer_Informe.html"
FIGS = REPORTS / "figures"

# Capturas del capítulo 3 (serie propia, no renumera las Figuras 2.N).
CAPTURAS = {
    "3.1": (
        "shot_3_3.2.png",
        "El filtro de clarificación detecta una ambigüedad temporal antes de generar SQL",
        "Captura 3.1 — Ejemplo real del filtro de clarificación: ante la pregunta "
        "&quot;who are the most reproduced artists in the last months?&quot;, el agente de "
        "comprensión de consultas detecta la ambigüedad temporal de &quot;the last months&quot; "
        "y pide precisión (&quot;¿los últimos 3 meses o los últimos 6 meses?&quot;) antes de "
        "generar SQL. Fuente: sistema IDI en ejecución local.",
    ),
    "3.2": (
        "shot_3_3.3.1.png",
        "Paneles &quot;What I understood&quot; y &quot;The SQL&quot;",
        "Captura 3.2 — Paneles &quot;What I understood&quot; y &quot;The SQL&quot; de la "
        "respuesta a la pregunta &quot;Who are the most reproduced artists in the last 8 "
        "months?&quot;: el agente reformula la pregunta tal como la entendió y muestra la "
        "consulta SQL generada, con los JOIN entre <code>track_artists</code>, "
        "<code>play_events</code> y <code>artists</code>. Fuente: sistema IDI en ejecución local.",
    ),
    "3.3": (
        "shot_3_3.3.2.png",
        "Panel &quot;Why this query&quot; y cadena de verificación de tres capas",
        "Captura 3.3 — Panel &quot;Why this query&quot;: el Generador SQL explica en lenguaje "
        "natural el razonamiento de la consulta — qué tablas usa y por qué, y los pasos de "
        "unión, filtrado, conteo y ordenamiento — seguido del resultado de la cadena de "
        "verificación de tres capas (sintaxis, semántica y sanidad). "
        "Fuente: sistema IDI en ejecución local.",
    ),
    "3.4": (
        "shot_3_3.3.3.png",
        "Panel &quot;Results&quot; con las filas devueltas por la consulta",
        "Captura 3.4 — Panel &quot;Results&quot;: el conjunto de filas devuelto por la "
        "consulta, con el identificador y el nombre de cada artista junto a su número de "
        "reproducciones. Fuente: sistema IDI en ejecución local.",
    ),
    "3.5": (
        "shot_3_3.6.png",
        "Biblioteca de sesiones (SessionLibrary)",
        "Captura 3.5 — Biblioteca de sesiones (SessionLibrary): lista las conversaciones "
        "anteriores, cada una asociada a su base de datos por el nombre de la carpeta "
        "(&quot;soundwave&quot;) y con su marca de tiempo, y permite reabrirlas. "
        "Fuente: sistema IDI en ejecución local.",
    ),
    "3.6": (
        "shot_3_3.9.1.png",
        "Pantalla de selección de base de datos en la primera vista (DatabaseSelector)",
        "Captura 3.6 — Pantalla de selección de base de datos en la primera vista "
        "(DatabaseSelector): lista las bases de datos disponibles y ofrece el atajo "
        "&quot;usar la última base de datos utilizada&quot; (soundwave), añadida en la "
        "restructuración multi-base de datos. Fuente: sistema IDI en ejecución local.",
    ),
    "3.7": (
        "shot_3_3.9.3.png",
        "Frase didáctica de espera mientras el pipeline procesa la consulta",
        "Captura 3.7 — Frase didáctica de espera (&quot;WHILE YOU WAIT&quot;): mientras el "
        "pipeline procesa la consulta, la interfaz muestra el estado &quot;Thinking…&quot; "
        "junto a una micro-lección relacionada con la pregunta (aquí, qué hace un JOIN). "
        "Fuente: sistema IDI en ejecución local.",
    ),
}


def captura(num: str) -> str:
    fname, alt, caption = CAPTURAS[num]
    png = FIGS / fname
    if not png.is_file():
        raise SystemExit(f"MISSING IMAGE: {png}")
    return (
        '<figure class="fig">'
        f'<img src="figures/{fname}" alt="{alt}" '
        'style="max-width:100%;height:auto;display:block;margin:0 auto 6pt auto;'
        'border:0.5pt solid #c9ccd4;border-radius:3pt;">'
        f"<figcaption>{caption}</figcaption></figure>"
    )


TOC = """<h1 class="center toc-title">ÍNDICE</h1>
<div class="toc">
<div class="toc-top">Capítulo 3: Desarrollo de la Solución</div>
<div class="toc-sub">3.1. Adquisición de Contexto: Context Manager Agent y FileConnector</div>
<div class="toc-sub">3.2. Comprensión de Consultas, Clarificación y Salvaguarda de Filtrado</div>
<div class="toc-sub">3.3. Generador SQL</div>
<div class="toc-sub">3.4. Agente de Verificación</div>
<div class="toc-sub">3.5. Motor de Visualización</div>
<div class="toc-sub">3.6. Gestor de Sesiones</div>
<div class="toc-sub">3.7. Orquestador Multi-Agente</div>
<div class="toc-sub">3.8. Registro de Instrucciones y Disciplina de Hot-Swap</div>
<div class="toc-sub">3.9. Reconstrucción del Frontend</div>
<div class="toc-sub">3.10. Datos Sintéticos y Fine-Tuning LoRA</div>
<div class="toc-sub">3.11. Estado del Requerimiento Didáctico Transversal por Módulo</div>
<div class="toc-sub">3.12. Estado de Avance y Problemas Conocidos</div>
<div class="toc-sub">3.13. Conclusiones del Capítulo</div>
<div class="toc-sub">3.14. Recomendaciones</div>
</div>
<div class="pagebreak"></div>"""


BODY = """<div class="rule"></div>
<h1 class="center chap-title">CAPÍTULO 3: DESARROLLO DE LA SOLUCIÓN</h1>
<p>Este capítulo desarrolla el tercer objetivo específico (OE3): implementar los siete módulos centrales de IDI con generación de datos sintéticos de entrenamiento, pipelines de fine-tuning, gestión de flujo conversacional y componentes de interfaz de usuario. A diferencia del Capítulo 2 (diseño), este capítulo documenta lo efectivamente construido — código en ejecución, verificado mediante pruebas y demostraciones — y es explícito sobre lo que quedó pendiente o en curso. Bajo el propósito actualizado del Capítulo 1 — IDI como compañero didáctico que responde enseñando —, la implementación de cada módulo se reporta en dos planos: su función central y el estado de su requerimiento didáctico transversal (consolidado en la Sección 3.11). El resultado alimenta el análisis de resultados (OE4, Capítulo 4).</p>

<h2>3.1. ADQUISICIÓN DE CONTEXTO: CONTEXT MANAGER AGENT Y FileConnector</h2>
<p>Implementado. El agente se alimenta de una base de datos SQLite en memoria construida a partir de archivos fuente por base de datos (<code>databases/&lt;db_name&gt;/*.sql</code>), a través de <code>FileConnector</code> (generalizado desde <code>SoundwaveFileConnector</code>) y <code>backend/app/services/db/discovery.py</code>. El glosario de negocio se extrajo del código a un archivo <code>NN_&lt;db&gt;_survey.json</code> por base de datos — un aporte directo al propósito didáctico: el contexto que el sistema usa para entender el dominio es el mismo que el aprendiz puede consultar como material de estudio.</p>
<p>La Captura 2.3 del Capítulo 2 (§2.2, drawer &quot;DB Info&quot;) documenta el paquete de contexto generado — esquema de SoundWave con columnas, tipos y claves, y el glosario de términos crípticos del dominio con su significado.</p>

<h2>3.2. COMPRENSIÓN DE CONSULTAS, CLARIFICACIÓN Y SALVAGUARDA DE FILTRADO</h2>
<p>Implementado en la fase temprana de implementación, con perfil de instrucción especializado (<code>backend/app/prompts/clarification.md</code>) ajustado contra las pruebas de ejecución de casos límite 1 a 8.</p>
<p>Durante la fase de endurecimiento se añadió una salvaguarda de enrutamiento de consultas (2026-07-06), cuyo diseño se documenta en el Capítulo 2 (§2.5): antes de que una pregunta llegue al parseo de intención y a la generación de SQL, un filtro basado en lista de permitidos (allowlist) determina si la pregunta se relaciona con la base de datos activa (vocabulario del dominio derivado del <code>DBProfile</code>) o si constituye una pregunta de conocimiento SQL. Las preguntas sobre el sistema o la base de datos seleccionada se responden por una ruta separada — las respuestas de la base de datos seleccionada —, siempre fundamentada en hechos actuales del <code>DBProfile</code>; las preguntas no relevantes para bases de datos quedan fuera del propósito de IDI y reciben una redirección cortés sin invocar el pipeline NL2SQL. La salvaguarda está cubierta por pruebas offline (<code>tests/test_meta_question_filter.py</code>, <code>tests/test_query_understanding.py</code>).</p>
{CAP_3_1}

<h2>3.3. GENERADOR SQL</h2>
<p>Implementado en la fase temprana de implementación. El Generador SQL es el traductor del sistema: recibe la intención estructurada que produce el agente de comprensión de consultas y la convierte en una única consulta SQL de solo lectura. Para hacerlo no trabaja a ciegas: su prompt se construye con la capa de contexto de la base de datos activa — el resumen del esquema (tablas, columnas, tipos y claves), el glosario de términos del dominio y los pasajes de contexto recuperados para la pregunta —, de modo que la traducción queda anclada a la base de datos real y no a suposiciones del modelo. Junto con el SQL, el agente reporta su razonamiento y los supuestos que asumió, insumo directo del panel didáctico de la respuesta. Su salida nunca se ejecuta directamente: pasa primero por el Agente de Verificación (§3.4), y si la verificación la rechaza, el generador recibe el error real del motor y produce una versión corregida (§3.7).</p>
<p>La instrucción especializada del agente fue ajustada en la fase temprana y reforzada durante el endurecimiento (ajustes en <code>sql_generator.py</code> y su perfil de instrucción). Ese perfil es, además, la línea base que el adaptador LoRA entrenado para este agente busca superar: el conjunto de entrenamiento sobre-muestra deliberadamente los modos de fallo que el perfil no cerró — los casos límite 2 y 4 —, como se detalla en la §3.10.</p>
<p>Las Capturas 3.2 a 3.4 recorren, sobre una misma pregunta, los paneles con que la respuesta expone el trabajo del Generador SQL: la pregunta tal como el sistema la entendió junto al SQL que produjo, el razonamiento en lenguaje natural seguido del resultado de la cadena de verificación, y las filas devueltas.</p>
{CAP_3_2}
{CAP_3_3}
{CAP_3_4}

<h2>3.4. AGENTE DE VERIFICACIÓN</h2>
<p>Implementado en la fase temprana de implementación como cadena de tres capas (sintaxis → semántica → sanidad). Validado en la Puerta D1 (Gate D1): seis de las ocho queries de prueba pasaron; las dos restantes — las de las pruebas de ejecución de casos límite 7 y 8 — fueron correctamente bloqueadas por la capa de verificación sintáctica, comportamiento fail-safe funcionando según diseño. Un hallazgo de datos de esa fase es relevante para la evaluación (Capítulo 4): la artista referenciada en la query de la prueba de ejecución de casos límite 8 (&quot;Adele&quot;) no existe en los datos semilla de SoundWave, por lo que la respuesta correcta de esa query es 0 filas.</p>
<p>La implementación sigue la política de auto-corrección silenciosa fijada en la actualización del Capítulo 1 (UC-06): los fallos que el reintento automático resuelve se consumen como contexto interno y no se exponen al usuario; solo los fallos no corregibles (o los bloqueos de seguridad) llegan a la interfaz, y deben llegar como explicación conceptual, no como error técnico.</p>
<p>La medición real del tiempo de verificación de extremo a extremo frente a su umbral de &lt;2s es evidencia de evaluación y se traslada como pendiente al Capítulo 4 (§4.4).</p>

<h2>3.5. MOTOR DE VISUALIZACIÓN</h2>
<p>Implementado: selección automática de gráfico vía Recharts, integrada en la respuesta didáctica de 4 paneles. La Captura 2.2 del Capítulo 2 (§2.2) muestra el panel de visualización dentro de la respuesta de 4 paneles en el chat en vivo.</p>

<h2>3.6. GESTOR DE SESIONES</h2>
<p>Implementado. El gestor de sesiones guarda las conversaciones para poder retomarlas después: una biblioteca de sesiones (<code>SessionLibrary</code>) lista las conversaciones anteriores y permite reabrirlas, y un panel lateral muestra la información de la base de datos con la que se está trabajando. Desde la restructuración multi-base de datos (2026-07-03), cada sesión queda asociada a su base de datos por el nombre de la carpeta que la contiene; el historial guardado hasta ese momento se reinició, y el archivo de sesiones se vuelve a crear vacío, de forma automática, la próxima vez que arranca el backend.</p>
{CAP_3_5}

<h2>3.7. ORQUESTADOR MULTI-AGENTE</h2>
<p>Implementado. El orquestador dirige el flujo completo de cada consulta: decide qué agente interviene en cada fase y, justo antes de ejecutarlo, activa el perfil de instrucción de ese agente. Cuando un agente arranca, el evento de progreso que se envía al frontend incluye la etiqueta del perfil que quedó activo, de modo que la interfaz puede mostrar en todo momento qué agente está trabajando y con qué especialización — sin que el frontend necesitara cambios, pues ya leía esa etiqueta de los eventos de estado. Esta trazabilidad de fase y agente activo es, además, el requerimiento didáctico del módulo, ya implementado (Sección 3.11).</p>
<p>El orquestador también implementa la recuperación automática ante SQL rechazado, con un máximo de dos intentos. Primero, si la cadena de verificación propone una reparación de la consulta, el orquestador la aplica y la vuelve a verificar. Si aún falla, realiza un único reintento de regeneración: devuelve al Generador SQL el error real reportado por el motor (por ejemplo, una columna que no existe) para que produzca una consulta corregida, que se verifica de nuevo. Ambos intentos siguen la política de auto-corrección silenciosa (Sección 3.4): el usuario no ve el detalle de la recuperación, solo el resultado final; y si tras ambos intentos el SQL sigue sin pasar la verificación, no se ejecuta nunca y el fallo llega a la interfaz como explicación conceptual. La cancelación, por su parte, aprovecha el diseño de streaming de la respuesta: los eventos del pipeline viajan como un flujo continuo hacia el frontend, y si el usuario cancela, la conexión se cierra y el pipeline se detiene en la siguiente frontera entre agentes (objetivo de propagación &lt;500ms, UC-05).</p>

<h2>3.8. REGISTRO DE INSTRUCCIONES Y DISCIPLINA DE HOT-SWAP</h2>
<p>Implementado. La orquestación de agentes permite cambiar de habilidad sobre la marcha, según el orquestador dictamine para cada fase de la ejecución: cada agente tiene asociada una especialización, y el sistema activa la que corresponde justo antes de que ese agente trabaje. El mapeo de qué especialización usa cada agente vive fuera del código, en un registro (<code>adapters/registry.json</code>, gestionado por <code>backend/app/services/adapter_registry.py</code>), de modo que cambiar la habilidad de un agente no exige tocar el pipeline. Los cuatro perfiles de instrucción (<code>backend/app/prompts/*.md</code>) fueron expandidos a especializaciones reales, ajustadas contra las pruebas de ejecución de casos límite 1 a 8. El servicio LLM expone además <code>chat_with_meta()</code> para reportar tokens por segundo, insumo de la evaluación de desempeño (Capítulo 4, §4.4).</p>
<p>El mecanismo acepta dos tipos de especialización por la misma interfaz: perfiles de instrucción (archivos de texto que se anteponen al prompt del agente) y adaptadores LoRA entrenados (archivos GGUF que modifican los pesos del modelo). Con el entrenamiento en marcha (§3.10), la rama de adaptadores quedó cableada (2026-07-16): el registro ya declara adaptadores GGUF para el Generador SQL y el agente de comprensión de consultas, el servidor de inferencia arranca con cada adaptador disponible precargado, y el orquestador enciende el del agente en turno. El diseño es fail-safe: si el archivo de un adaptador no existe, el sistema vuelve de forma transparente al perfil de instrucción del mismo nombre — un adaptador faltante nunca bloquea el pipeline. El comportamiento está cubierto por pruebas offline (<code>tests/test_adapter_registry.py</code>).</p>

<h2>3.9. RECONSTRUCCIÓN DEL FRONTEND</h2>
<p>Implementado. Durante la reconstrucción se pasó de Tailwind a CSS puro para mejorar el mantenimiento y la modularidad de los estilos. La interfaz ofrece respuestas didácticas de 4 paneles, etiquetas del perfil activo de cada agente, autocompletado inline, la biblioteca de sesiones y el panel de información de la base de datos. En la primera vista podemos seleccionar una base de datos, funcionalidad añadida en la restructuración multi-base de datos. La respuesta de 4 paneles es el vehículo principal del propósito didáctico en la interfaz: la misma respuesta que el ejecutivo lee como insight, el aprendiz la lee como lección (qué se entendió, qué SQL se construyó, qué resultado produjo y cómo se visualiza).</p>
{CAP_3_6}
<p>La respuesta didáctica de 4 paneles se documenta en la Captura 2.2 del Capítulo 2 (§2.2).</p>
{CAP_3_7}

<h2>3.10. DATOS SINTÉTICOS Y FINE-TUNING LoRA</h2>
<p>Esta sección documenta dos desviaciones frente al plan original del Capítulo 1 (§1.10), que especificó el entrenamiento de cuatro adaptadores LoRA vía QLoRA/Unsloth sobre datasets de 15,000–20,000 ejemplos. Ambas responden a decisiones de ingeniería tomadas para acelerar etapas del desarrollo general del proyecto — como lo fue también realizar las pruebas y el primer entrenamiento únicamente sobre SoundWave —: toda la lógica del backend se levantó, y sus pruebas se ejecutan, usando perfiles de instrucción sobre el mismo mecanismo de hot-swap (§3.8), lo que permitió posponer el entrenamiento hasta contar con resultados reales del sistema en operación. El entrenamiento, tal como lo definimos luego, tuvo más sentido según los resultados que hemos tenido del sistema sin entrenar: los datos se concentran en los modos de fallo que el sistema aún no cierra. Las dos desviaciones — número de adaptadores y tamaño del dataset — se justifican a continuación; el entrenamiento <strong>se está llevando a cabo</strong> sobre el pipeline que esta sección documenta.</p>

<h3>3.10.1. El corpus fuente y la escasez de datos apropiados para el entrenamiento</h3>
<p>Una auditoría del repositorio (2026-07-16) estableció que la única fuente de pares pregunta→SQL verificados a mano para SoundWave es el catálogo de casos límite (<code>databases/soundwave/03_soundwave_edge_cases.md</code>): 30 consultas (Q01–Q30), cada una con su SQL correcto, su versión típicamente errónea y el modo de fallo NL2SQL que ejercita (casos límite 1 a 18). Ninguna otra fuente sirve como verdad de referencia: las 8 queries de <code>gate_d1.py</code> no traen SQL objetivo, <code>tests/evaluate.py</code> valida conjuntos de resultados (no SQL), y los turnos registrados en <code>data/sessions.db</code> son salida no verificada del propio modelo. Treinta ejemplos con tres épocas producirían memorización, no aprendizaje; el pipeline de datos existe precisamente para convertir esas 30 semillas en un conjunto de entrenamiento de precisión sin diluir su calidad.</p>

<h3>3.10.2. Construcción del dataset (<code>training/build_dataset.py</code>)</h3>
<p>El generador produce cuatro archivos JSONL en <code>data/synthetic/</code> — train/eval para el SQL Generator (334 ejemplos) y para el Query Understanding (349 ejemplos) — bajo cuatro principios verificables:</p>
<p class="numli"><span class="n">•</span> <strong>Fidelidad de prompt:</strong> el entrenamiento se lleva a cabo teniendo en cuenta que IDI cuenta con una capa de contexto por base de datos: cada ejemplo de entrenamiento incluye la misma información de contexto que el agente recibe cuando opera — el resumen del esquema, el glosario de términos del dominio y los pasajes recuperados para la pregunta —, de modo que el adaptador aprende en las mismas condiciones en las que luego trabaja. Esta decisión es la que hace coherente el fine-tuning con la arquitectura orientada al contexto por base de datos descrita en el Capítulo 2.</p>
<p class="numli"><span class="n">•</span> <strong>Validación por ejecución:</strong> todo el SQL del dataset es válido, porque se comprobó ejecutándolo: cada consulta se corre contra la base de datos y, si falla o no devuelve el resultado esperado, se descarta. Un dataset NL2SQL sin esta garantía arrastra SQL sintácticamente válido pero semánticamente incorrecto — exactamente el modo de fallo que IDI combate.</p>
<p class="numli"><span class="n">•</span> <strong>Aumentación dirigida a las brechas:</strong> sobre cada semilla se generan paráfrasis y sustituciones de valores (otros países, géneros, planes) tomadas del propio <code>02_soundwave_data.sql</code>. La aumentación sobre-muestrea deliberadamente los dos modos de fallo donde el prompt engineering tocó techo (Capítulo 2, §2.9): el caso límite 2 — término de negocio hacia columna booleana o codificada, p. ej. &quot;audio de alta fidelidad&quot; → <code>has_hifi = 1</code> — y el caso límite 4 — dirección del auto-join, p. ej. <code>genres.parent_genre_id</code> —, con decenas de ejemplos por familia en ambos sentidos del auto-join.</p>
<p class="numli"><span class="n">•</span> <strong>Separación entre entrenamiento y evaluación:</strong> el modelo nunca ve durante el entrenamiento las preguntas con las que después será evaluado: las 30 preguntas originales y las 8 queries de prueba se reservan exclusivamente para la evaluación, y el entrenamiento usa solo versiones reformuladas de ellas (paráfrasis y cambios de valores); no hay ninguna pregunta repetida entre ambos conjuntos. Es la misma lógica de un examen justo: se estudia con ejercicios parecidos, pero las preguntas del examen no se conocen de antemano. Gracias a esto, la evaluación del Capítulo 4 mide si el modelo aprendió a traducir, no si memorizó respuestas.</p>

<h3>3.10.3. La receta de entrenamiento (<code>training/lora_config.py</code>, <code>training/colab_train_adapter.ipynb</code>)</h3>
<p>El entrenamiento se ejecuta en Google Colab (GPU T4) con Unsloth sobre <code>Qwen2.5-Coder-3B-Instruct</code> en cuantización de 4 bits (QLoRA), replicando los hiperparámetros del Capítulo 1: rango r = 16, α = 32, dropout 0.05, módulos objetivo de atención y MLP, 3 épocas, tasa de aprendizaje 2e-4. Un detalle metodológico crítico: la pérdida se computa <strong>solo sobre la respuesta del asistente</strong> (<code>train_on_responses_only</code>), nunca sobre el prompt cargado de esquema — de otro modo el adaptador aprendería a regenerar el esquema en lugar de la habilidad de traducir. Cada adaptador se exporta a formato GGUF (<code>convert_lora_to_gguf.py</code>) para ser servido por llama.cpp junto al modelo base Q4_K_M, dentro del presupuesto de restricción dura de &lt; 3.5 GB de VRAM (Capítulo 1).</p>

<h3>3.10.4. Decisión de alcance: dos adaptadores, calidad sobre cantidad</h3>
<p>Se entrenan dos adaptadores — SQL Generator y Query Understanding —, no los cuatro del plan. La razón es honesta: los agentes de Verificación y Clarificación no cuentan con un solo ejemplo etiquetado, y entrenarlos sería fabricar datos; además, la evidencia de los benchmarks sitúa las brechas más importantes en la generación de SQL y en su comprensión previa.</p>
<p>El entrenamiento también se preparó de manera óptima para casos generales de SQL, no solo para SoundWave. Una parte del conjunto del Generador SQL (~350 ejemplos filtrados de <code>gretelai/synthetic_text_to_sql</code>) proviene de bases de datos distintas, y cada uno de esos ejemplos lleva en su bloque de contexto el esquema de su propia base. Con esto el adaptador no puede limitarse a memorizar SoundWave: se ve obligado a aprender la habilidad general de leer el esquema que se le entrega y traducir sobre él — la misma habilidad que necesitará frente a cualquier base de datos nueva que se agregue al sistema. El agente de comprensión de consultas permanece centrado en SoundWave, pues su salida (el intent estructurado) no tiene equivalente externo directo.</p>
<p>El tamaño resultante — cientos, no decenas de miles, de ejemplos — es una consecuencia deliberada de anteponer la precisión verificada por ejecución a la escala: para un modelo de 3B sobre hardware de consumo y un objetivo estrecho (los casos límite 2 y 4), un conjunto pequeño y correcto supera a uno grande y ruidoso.</p>

<h3>3.10.5. Integración en tiempo de ejecución</h3>
<p>El seam de hot-swap quedó cerrado en su rama GGUF (§3.8): <code>adapters/registry.json</code> declara <code>kind: &quot;gguf&quot;</code> para los dos agentes entrenados; <code>start.py</code> arranca llama.cpp con un flag <code>--lora</code> por cada adaptador presente (<code>--lora-init-without-apply</code>, escala 0 al inicio); y el orquestador activa el adaptador del agente en turno fijando su escala a 1.0 vía <code>POST /lora-adapters</code> (<code>llm_service.load_gguf_adapter</code>). Mientras un adaptador GGUF está activo, el perfil de instrucción <code>.md</code> <strong>no</strong> se antepone — el conocimiento quedó destilado en los pesos, y el adaptador se entrenó sobre el <code>SYSTEM_PROMPT</code> desnudo del agente —. La ausencia de un archivo GGUF revierte de forma segura al perfil de instrucción, de modo que el sistema nunca se bloquea por un adaptador faltante.</p>

<h2>3.11. ESTADO DEL REQUERIMIENTO DIDÁCTICO TRANSVERSAL POR MÓDULO</h2>
<p>El Capítulo 1 (§1.6) asignó un requerimiento didáctico a cada uno de los siete módulos. Durante la implementación, dos de ellos (Verificación y Orquestador) se reclasificaron: son mecanismos internos del sistema, sin un objetivo didáctico de cara al usuario. El estado de los demás, insumo de la evaluación de Claridad Didáctica del Capítulo 4 (§4.7), es el siguiente:</p>
<table><thead><tr><th>Módulo</th><th>Requerimiento didáctico (Capítulo 1, §1.6)</th><th>Estado</th></tr></thead><tbody>
<tr><td>Context Manager</td><td>Mini-glosario navegable del dominio, con ejemplos por término</td><td>Completo — ya existe y se encuentra correctamente integrado (panel de información de la base de datos, con esquema y glosario)</td></tr>
<tr><td>Query Understanding</td><td>Cada clarificación explica por qué la ambigüedad importa</td><td>Completo — el sistema ya incorpora estas desambiguaciones y aclaraciones dentro de su funcionamiento</td></tr>
<tr><td>SQL Generator</td><td>Anotación por cláusula del SQL generado</td><td>Completo — cada respuesta explica por qué se usaron esas tablas y esas columnas</td></tr>
<tr><td>Verification</td><td>Explicación conceptual de los fallos que llegan al usuario</td><td>No aplica — es un mecanismo interno del sistema; no es relevante enseñar al usuario por qué falló un intento, y los fallos corregibles se resuelven en silencio (UC-06)</td></tr>
<tr><td>Visualization Engine</td><td>Justificación de la elección del tipo de gráfico</td><td>Implementación básica, para casos muy generales</td></tr>
<tr><td>Session Manager</td><td>Sesiones marcables como &quot;ruta de aprendizaje&quot; exportable</td><td>Cumplido — las sesiones permiten al usuario repasar sus preguntas y su aprendizaje</td></tr>
<tr><td>Orchestrator</td><td>Trazabilidad de fase y agente activo</td><td>No aplica como objetivo didáctico — es solo el orquestador; su trazabilidad de fase y agente activo está implementada y visible en la interfaz</td></tr>
</tbody></table>

<h2>3.12. ESTADO DE AVANCE Y PROBLEMAS CONOCIDOS</h2>
<table><thead><tr><th>Artefacto</th><th>Estado</th></tr></thead><tbody>
<tr><td>Pipeline de 7 agentes end-to-end sobre <code>/query</code></td><td>Completado (fase temprana de implementación)</td></tr>
<tr><td>Frontend didáctico de 4 paneles</td><td>Completado (fase temprana de implementación)</td></tr>
<tr><td>Registro de adaptadores/instrucciones + hot-swap</td><td>Completado (fase temprana de implementación)</td></tr>
<tr><td>Suite de pruebas offline (<code>pytest</code>)</td><td>Completado (fase temprana de implementación), extendida con las pruebas de filtrado de consultas</td></tr>
<tr><td><code>ruff</code>/<code>black</code>, <code>eslint</code>/<code>prettier</code></td><td>Completado (fase temprana de implementación)</td></tr>
<tr><td>Salvaguarda de filtrado de consultas (allowlist)</td><td>Completado (2026-07-06)</td></tr>
<tr><td>Documentación visual del frontend (capturas del sistema en ejecución)</td><td>Completado — hay capturas a lo largo de este capítulo y del Capítulo 2</td></tr>
<tr><td>Requerimientos didácticos transversales (7)</td><td>Completado donde aplica — ver Sección 3.11</td></tr>
<tr><td>Conexión a base de datos real (MySQL)</td><td>Descartada del alcance — las bases de datos se simulan desde sus archivos de contexto (ver nota al final de esta sección)</td></tr>
<tr><td>Pipeline de datos sintéticos + datasets LoRA (train/eval, validados por ejecución)</td><td>Completado (2026-07-16)</td></tr>
<tr><td>Cableado de hot-swap de adaptadores GGUF (rama <code>kind: gguf</code>)</td><td>Completado (2026-07-16), con pruebas offline</td></tr>
<tr><td>Entrenamiento LoRA (2 adaptadores: SQL Generator, Query Understanding)</td><td><strong>En ejecución (Colab); métricas A/B → Capítulo 4</strong></td></tr>
</tbody></table>
<p>Nota sobre la conexión a bases de datos reales: la conexión directa a un motor MySQL se descartó del alcance del proyecto, y en su lugar las bases de datos se simulan por medio de sus archivos de contexto (<code>databases/&lt;db&gt;/</code>). Implementar la conexión real habría implicado una complejidad mucho mayor del proyecto — credenciales, seguridad, latencias y esquemas fuera de nuestro control — sin aportar a los objetivos específicos, pues la simulación reproduce fielmente el comportamiento de consulta. La decisión, sin embargo, dejó rutas preparadas para que esa conexión ocurra sin mayor problema más adelante: los agentes consumen una interfaz de conector genérica, de la cual el conector de archivos es la implementación actual, de modo que un conector MySQL puede añadirse sin tocar el pipeline. El autor planea continuar el proyecto por su cuenta como código abierto, y esta es una de las primeras extensiones previstas para versiones posteriores.</p>

<h2>3.13. CONCLUSIONES DEL CAPÍTULO</h2>
<p class="numli"><span class="n">1.</span> (aporta a OE3) Los siete módulos centrales de IDI quedaron implementados y operando de extremo a extremo. Las decisiones de diseño tomadas en el Capítulo 2 — la cadena de verificación de tres capas, la capa de contexto por base de datos, el mecanismo de hot-swap de especializaciones y la respuesta didáctica de 4 paneles — se implementaron satisfactoriamente y fueron las que permitieron que el proyecto funcionara: cada una está validada en el sistema en ejecución (Puerta D1, suite de pruebas offline y las capturas de este capítulo y del Capítulo 2).</p>
<p class="numli"><span class="n">2.</span> (aporta a OE3) Completar el desarrollo exigió tomar decisiones ingenieriles que se desvían del plan original, y tomarlas fue lo correcto: invertir el orden de los sprints (agentes primero, base de datos física al final), levantar el backend sobre perfiles de instrucción antes de entrenar, realizar las pruebas y el primer entrenamiento únicamente sobre SoundWave, y descartar la conexión MySQL real en favor de la simulación por archivos de contexto. Desviarse del plan es parte normal de un proceso de desarrollo cuando la evidencia lo respalda; lo importante es que cada desviación quedó documentada con su justificación.</p>
<p class="numli"><span class="n">3.</span> Ser honestos frente al alcance del proyecto — y muy selectivos sobre qué implementar y qué no — resultó tan valioso como la implementación misma. El ejemplo central es el fine-tuning: se entrenaron solo los dos adaptadores LoRA más relevantes según lo investigado (el Generador SQL y la comprensión de consultas), con cientos de ejemplos verificados por ejecución en lugar de decenas de miles sin verificar, anteponiendo la calidad demostrable a la escala aparente.</p>
<p class="numli"><span class="n">4.</span> El requerimiento didáctico transversal se implementó sin módulos adicionales: donde aplica, viaja dentro de los contratos existentes (respuesta de 4 paneles, etiquetas de perfil activo, sesiones repasables, panel de información de la base de datos), lo que valida la decisión de diseño del Capítulo 2 (§2.2).</p>

<h2>3.14. RECOMENDACIONES</h2>
<p class="numli"><span class="n">1.</span> (OE3) Tratar las desviaciones del plan como decisiones de ingeniería de primera clase: registrarlas con su evidencia y su justificación en el momento en que se toman — como se hizo con el número de adaptadores, el tamaño del dataset y la conexión a bases de datos reales —, de modo que la evaluación (OE4) mida el sistema que efectivamente se decidió construir, y no un plan que la evidencia recomendó ajustar.</p>
<p class="numli"><span class="n">2.</span> (OE3) Mantener esa misma selectividad de alcance en la fase de evaluación: congelar el protocolo antes de medir, evaluar sobre lo efectivamente implementado y reportar de forma explícita lo que se descartó y por qué.</p>
<p class="numli"><span class="n">3.</span> Para versiones posteriores del proyecto — que el autor planea continuar como código abierto —: retomar la conexión a bases de datos reales por las rutas ya preparadas en el diseño (la interfaz de conector genérica) y ampliar el motor de visualización más allá de su implementación básica actual.</p>

<div class="rule"></div>
<h1 class="center chap-title refs">REFERENCIAS</h1>
<p>Se heredan del Capítulo 2 las cuatro fuentes de diseño que este capítulo también usa — entrenamiento LoRA (§3.10), cadena de verificación y auto-corrección (§3.4):</p>
<p>Hu, E. J., Shen, Y., Wallis, P., Allen-Zhu, Z., Li, Y., Wang, S., Wang, L., y Chen, W. (2022). LoRA: Low-rank adaptation of large language models. En <em>Proceedings of the International Conference on Learning Representations (ICLR)</em>.</p>
<p>Liu, X., Shen, S., Li, B., Ma, P., Jiang, R., Zhang, Y., Fan, J., Li, G., Tang, N., y Luo, Y. (2025a). NL2SQL-BUGs: A benchmark for detecting semantic errors in NL2SQL translation. En <em>Proceedings of the 31st ACM SIGKDD Conference on Knowledge Discovery and Data Mining (KDD)</em>. arXiv:2503.11984.</p>
<p>Liu, X., Shen, S., Li, B., Tang, N., y Luo, Y. (2025b). A survey of NL2SQL with large language models: Where are we, and where are we going? <em>IEEE Transactions on Knowledge and Data Engineering</em>. arXiv:2408.05109.</p>
<p>Pourreza, M., y Rafiei, D. (2023). DIN-SQL: Decomposed in-context learning of text-to-SQL with self-correction. En <em>Advances in Neural Information Processing Systems (NeurIPS)</em>, 36.</p>
<p>Fuentes específicas de este capítulo, correspondientes al modelo base y las fuentes de datos del fine-tuning (§3.10):</p>
<p>Hui, B., Yang, J., Cui, Z., et al. (2024). Qwen2.5-Coder technical report. <em>arXiv preprint</em> arXiv:2409.12186.</p>
<p>Gretel.ai (2024). Synthetic Text-to-SQL [conjunto de datos]. Hugging Face. Identificador: <code>gretelai/synthetic_text_to_sql</code>.</p>
<div class="rule"></div>
<p>Universidad Nacional de Colombia — Facultad de Ingeniería — Departamento de Sistemas e Industrial</p>
<p>Período 2026-1S</p>
</body>
</html>"""

# Regla h3 para las subsecciones 3.10.1–3.10.5 (el capítulo 3 es el primero que
# las necesita; el CSS heredado del Segundo Informe solo llegaba hasta h2).
H3_CSS = (
    "h3{ font-size:12.5pt; font-weight:700; text-align:left; "
    "margin:12pt 0 5pt 0; line-height:1.3; }\r\n"
)


def main() -> None:
    # newline="" conserva los CRLF tal cual (Path.read_text solo acepta
    # newline desde Python 3.13; aquí corre 3.10).
    with io.open(REPORT, "r", encoding="utf-8", newline="") as fh:
        html = fh.read()

    body = BODY
    for num, token in [
        ("3.1", "{CAP_3_1}"),
        ("3.2", "{CAP_3_2}"),
        ("3.3", "{CAP_3_3}"),
        ("3.4", "{CAP_3_4}"),
        ("3.5", "{CAP_3_5}"),
        ("3.6", "{CAP_3_6}"),
        ("3.7", "{CAP_3_7}"),
    ]:
        if token not in body:
            raise SystemExit(f"falta el token {token} en BODY")
        body = body.replace(token, captura(num))

    # El documento es CRLF de punta a punta (así lo dejó Word/Windows); los
    # literales de este script son LF, de modo que hay que convertirlos.
    new_tail = (TOC + "\n" + body).replace("\r\n", "\n").replace("\n", "\r\n")

    # 1) CSS: añadir la regla h3 y sumar h3 a los break-after:avoid.
    if "h3{ font-size" not in html:
        html = html.replace(
            "h2{ font-size:15pt;", H3_CSS + "h2{ font-size:15pt;", 1
        )
        html = html.replace("h1,h2{ break-after:avoid; }", "h1,h2,h3{ break-after:avoid; }", 1)
        html = html.replace(
            "h2, table, figure, .shot, .todo{ break-inside:avoid; }",
            "h2, h3, table, figure, .shot, .todo{ break-inside:avoid; }",
            1,
        )

    # 2) Cuerpo: reemplazar desde el ÍNDICE hasta el final, conservando
    #    <head> (fuentes) y portada (escudo).
    anchor = '<h1 class="center toc-title">'
    i = html.find(anchor)
    if i == -1:
        raise SystemExit("no se encontró el ancla del ÍNDICE — no se escribió nada")
    html = html[:i] + new_tail

    for marca in ("[PENDIENTE", "[PANTALLAZO", 'class="shot"'):
        assert marca not in html, f"sobrevivió una marca: {marca}"
    assert html.count("<figure") == 7, f"se esperaban 7 figuras, hay {html.count('<figure')}"
    # Las capturas van como referencia a archivo, nunca en base64 (política
    # 2026-07-17): el único base64 permitido vive antes del ÍNDICE (fuentes,
    # escudo). new_tail es todo lo que este script escribe.
    assert "base64," not in new_tail, "una captura quedó incrustada en base64"
    assert html.count('src="figures/') == 7, "capturas sin referencia a figures/"
    for n in range(1, 8):
        marca = f"<figcaption>Captura 3.{n} —"
        assert html.count(marca) == 1, f"numeración de capturas rota en 3.{n}"
    assert html.rstrip().endswith("</html>"), "el documento no cierra en </html>"
    assert not re.search(r"(?<!\r)\n", html), "quedaron saltos de línea LF sueltos"

    with io.open(REPORT, "w", encoding="utf-8", newline="") as fh:
        fh.write(html)
    print(f"escrito: {REPORT} ({REPORT.stat().st_size / 1e6:.1f} MB)")
    print(f"figuras: {html.count('<figure')} | h3: {html.count('<h3')} | tablas: {html.count('<table')}")


if __name__ == "__main__":
    main()
