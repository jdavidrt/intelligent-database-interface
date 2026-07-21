IDI — Interfaz Inteligente de Bases de Datos

Trabajo de Grado — Ingeniería de Sistemas y Computación
Universidad Nacional de Colombia
Autor: Juan David Ramírez Torres (jdramirezt@unal.edu.co)
Período: 2026-1S (Febrero 2 – Mayo 30, 2026)

> **[v2 — con resultados de las corridas piloto del 2026-07-21]** El capítulo deja de ser un esqueleto: §4.1 a §4.4 y §4.6 a §4.9 se llenan con mediciones reales. Las cifras de precisión provienen de tres corridas puntuadas ejecutadas el 2026-07-21 contra un backend en vivo, con el protocolo de evaluación ya congelado (`docs/EVALUATION_PROTOCOL.md`, v1.2). **Ninguna de las tres es todavía una corrida reportable como precisión de corpus**: las tres son pilotos parciales (26, 29 y 41 ítems de los 225 congelados), y el propio protocolo reserva esa condición únicamente para la corrida completa. Lo que se reporta aquí es, por tanto, una **primera medición de referencia** — honesta, reproducible y con toda su instrumentación registrada — no el resultado final del trabajo. Se mantiene marcado `[PENDIENTE]` todo lo que aún no se midió, y no se rellena ninguna celda con cifras inventadas.
>
> **Las tres corridas se ejecutaron sin adaptadores LoRA entrenados.** El registro `adapters/registry.json` declara artefactos GGUF para el Generador de SQL y el agente de Comprensión de Consultas, pero esos archivos no existen en el repositorio, de modo que el mecanismo de respaldo del registro (`adapter_registry.activate()`) carga en su lugar el perfil de instrucción del mismo agente. Todo lo medido en este capítulo corresponde entonces al **modelo base más perfiles de instrucción especializados**, que es exactamente la configuración cuya línea base este capítulo debía establecer antes del entrenamiento.
>
> **Decisión metodológica heredada del Capítulo 1**: este proyecto no incluye Spider ni BIRD como benchmarks externos ejecutados contra sus propias bases de datos, ni un estudio de usuario con participantes externos. Toda la evaluación cuantitativa corre sobre la base de datos SoundWave (patrones propios más subconjuntos que simulan la dificultad de Spider/BIRD); la evaluación cualitativa es una revisión experta empírica de los siete escenarios de uso del Capítulo 1 (§1.9), no un estudio SUS.


ÍNDICE

Capítulo 4: Análisis de Resultados
    4.1. Protocolo de Evaluación
    4.2. Precisión de Ejecución (Patrones Simulados Estilo Spider y BIRD, SoundWave, IDI-EXEC-75)
    4.3. Efectividad de la Verificación (Error Detection Rate)
    4.4. Desempeño y Latencia en Hardware Objetivo
    4.5. A/B: Modelo Base vs. Perfiles de Instrucción Especializados
    4.6. Evaluación Cualitativa: Revisión Experta Empírica de los Siete Escenarios de Uso
    4.7. Claridad Didáctica de las Explicaciones
    4.8. Comparación contra Línea Base
    4.9. Conclusiones del Capítulo
    4.10. Recomendaciones


────────────────────────────────────────────────────────────────────────

CAPÍTULO 4: ANÁLISIS DE RESULTADOS

Este capítulo desarrolla el cuarto objetivo específico (OE4): evaluar el desempeño de IDI mediante benchmarking cuantitativo y evaluación cualitativa, comparando los resultados contra métodos baseline. Su insumo es el sistema construido en el Capítulo 3 (OE3) y su contrato de éxito son las siete métricas fijadas en el Capítulo 1 (§1.8) — seis de ellas heredadas de la propuesta y una, la Claridad Didáctica de Explicaciones, incorporada tras el complemento de alcance que hizo del propósito didáctico la identidad principal del proyecto.

La regla rectora del capítulo es la que exige el Capítulo 1 (§1.13, recomendación OE4): el protocolo de evaluación — semillas, criterios de precisión de ejecución, guion de la revisión experta y checklist de claridad didáctica — debía congelarse **antes** de ejecutar los benchmarks, para evitar el ajuste post-hoc de umbrales. Esa regla se cumplió: el protocolo quedó congelado el 2026-07-21 y la primera corrida puntuada se ejecutó ese mismo día, después. Una consecuencia incómoda de haber cumplido la regla es que los números de este capítulo son bajos y no se pueden mejorar retocando el criterio; esa es precisamente la garantía que la regla compra.


4.1. PROTOCOLO DE EVALUACIÓN

El protocolo se congeló el 2026-07-21, antes de ejecutar cualquier benchmark, y se versiona en `docs/EVALUATION_PROTOCOL.md` (v1.2). Fija siete grados de libertad que de otro modo habrían podido ajustarse después de ver los resultados:

1. **El reloj congelado** `IDI_FREEZE_NOW=2026-07-17T12:00:00`, que hace reproducibles las consultas relativas al tiempo, junto con la extensión determinista de los datos semilla de SoundWave hasta ese mismo instante (1.230 eventos, del 2023-01-05 al 2026-07-17, generados con semilla 20260721). Sin esa extensión toda ventana relativa — "el mes pasado", "este año", "los últimos doce meses" — devolvía cero filas, lo que habría anulado en silencio la categoría Temporal completa. La extensión preserva las trampas de la base y cada una se verificó por consulta después de generarla.
2. **Decodificación greedy** (temperature = 0, top_p = 1, semilla 20260721), sin la cual la precisión de ejecución sería una variable aleatoria y dos corridas del mismo sistema no serían comparables.
3. **El criterio exacto de precisión de ejecución**: comparación de multiconjuntos de tuplas posicionales — los nombres de columna se descartan porque el alias es una elección libre del modelo —, sensible al orden solo cuando la pregunta lo implica, con tolerancia relativa 1e-6 en flotantes, dos decimales en valores monetarios, comparación de cadenas insensible a mayúsculas, `NULL == NULL` como verdadero y **sin normalización de unidades**: si la referencia está en minutos y el sistema responde en milisegundos, es un fallo. La coerción silenciosa de unidades escondería justamente la clase de error semántico que este proyecto existe para atrapar.
4. **La definición de Error Detection Rate** sobre un corpus de errores inyectados (diez operadores de mutación, ≥ 100 mutantes) evaluados directamente contra la cadena de verificación, reportado **siempre** junto a su tasa de falsos positivos: un verificador que rechace todo obtendría 100% de detección.
5. **Las condiciones de medición de latencia**: mediana sobre consultas de una sola tabla — fijadas al detalle en las diez primeras consultas del corpus estilo Spider en orden de manifiesto —, cinco repeticiones, perfiles GPU y solo-CPU, descartando la corrida de calentamiento.
6. **El guion y la checklist de la revisión experta** de los siete escenarios de uso, con su criterio explícito de "hallazgo crítico".
7. **La checklist de claridad didáctica** y su muestreo estratificado de 60 explicaciones.

Sobre la "semilla aleatoria" que este protocolo debía fijar para los subconjuntos simulados: no aplica. Los subconjuntos estilo Spider y estilo BIRD no se muestrean de una población preexistente — se construyen por autoría estratificada y por tanto *son* la población. Lo que se congela en su lugar es la estratificación. El nivel de dificultad de cada ítem no se declara sino que se **calcula**, reimplementando la función `eval_hardness` del evaluador oficial de Spider sobre la consulta de referencia, de modo que la etiqueta sea una propiedad de la consulta y no una opinión del autor; los constructores de cada corpus se niegan a escribir el manifiesto si el nivel calculado difiere del previsto. La semilla se reserva para el único muestreo real del capítulo, el de §4.7.

**Los cuatro corpus.** Quedaron redactados y congelados el 2026-07-21: 225 ítems en total — 60 estilo Spider, 60 estilo BIRD, 30 de SoundWave y 75 de IDI-EXEC —, de los cuales 220 llevan consulta de referencia que **se ejecuta efectivamente** contra la base con reloj congelado; los cinco restantes son los ítems de Ambigüedad Deliberada, que se puntúan por comportamiento (aciertan si el sistema pide aclaración en vez de adivinar) y deliberadamente no llevan consulta de referencia. La conformidad — tamaños, esquema del manifiesto, estratificación y ejecutabilidad — se verifica de forma automática y sin modelo con `python -m evaluation.validate`, y queda fijada por pruebas automatizadas.

Los cuatro corpus se ejecutan contra SoundWave porque es la única base del repositorio con datos, y el protocolo deriva la respuesta correcta **ejecutando** la consulta de referencia en vez de almacenarla: una base sin datos no puede alojar un corpus. Esta es la razón por la que se descartó la idea de esquemas Spider/BIRD separados.

**Ground truth registrado.** Se deja constancia de que la artista "Adele", referenciada por la prueba de joins multi-salto, no existe en el catálogo de doce artistas de SoundWave: su respuesta correcta es **cero filas**, y solo se puntúa como acierto si la consulta efectivamente se ejecutó — una consulta bloqueada por verificación también reporta cero filas, y puntuarla como acierto sería un falso positivo. El mismo tratamiento aplica a dos consultas del corpus de SoundWave cuyo resultado correcto es vacío contra los datos sembrados.

**Corrección sustantiva incorporada al congelar (v1.2).** La divergencia entre la tabla pre-agregada `daily_artist_metrics` y el log crudo `play_events` no es del "~5%" que afirmaban el esquema, el protocolo y la documentación de la base: medida contra los datos sembrados es de **290.000× a 1.070.000×** (The Weeknd registra 225 reproducciones crudas frente a 65.314.971 en la tabla pre-agregada), porque las columnas cacheadas se sembraron a escala de producción mientras que el log de eventos es una muestra didáctica de unas mil filas. La cifra del 5% era la intención de diseño y nunca fue lo que generó el sembrador. La magnitud importa metodológicamente: con un 5% es defendible aceptar ambas fuentes como correctas, pero con 290.000× un ítem que acepte ambas es infalsable — cualquier respuesta entre 225 y 65 millones pasaría —, de modo que la regla quedó invertida: todo ítem de esta clase debe **nombrar su fuente** y tiene prohibido declarar respuestas alternativas aceptables.

**Las corridas ejecutadas.** El 2026-07-21 se ejecutaron tres corridas puntuadas. Comparten instrumentación: motor SQLite en memoria construido desde los archivos de SoundWave, reloj congelado, decodificación greedy con semilla 20260721, planificación restringida activa, modelo `qwen2.5-coder-3b-instruct-q4_k_m.gguf` sobre una NVIDIA GeForce GTX 1650 de 4 GB (2.782 MiB de VRAM ocupada en la tercera corrida, confirmando que el modelo se descargó a la GPU discreta y no a la integrada), y la configuración de agentes descrita arriba — perfiles de instrucción, sin LoRA.

| Corrida | Hora | Selección | Ítems puntuados | Precisión de ejecución | Commit |
|---|---|---|---|---|---|
| P1 | 11:53 | prefijo proporcional de 30 ítems en orden de manifiesto; agotó el presupuesto de 34 min tras 26 | 26 | **53,8%** | `e1e3a75` |
| P2 | 13:21 | misma selección que P1 | 29 | **34,5%** | `d8de1d3` |
| P3 | 15:40 | preset de 1 hora — estratificado por corpus y por dificultad (11 Spider / 11 BIRD / 5 SoundWave / 14 IDI-EXEC) | 41 | **34,2%** | `d8de1d3` |

Tres propiedades del arnés de medición condicionan cómo deben leerse estas cifras:

- **El arnés se niega a escribir una corrida nula.** El reloj congelado vive en el proceso del backend, así que la comprobación consulta `GET /health` en vez del entorno del propio cliente: un cliente que verificara su propia variable de entorno no probaría nada sobre el proceso que generó el SQL. La misma ruta reporta si la decodificación greedy está activa.
- **Los subconjuntos se eligen antes de enviar la primera consulta.** Tanto los presets como la selección por total toman un prefijo en orden de manifiesto de cada estrato, asignado proporcionalmente, y registran en el encabezado la regla usada y la mezcla de dificultad lograda. El planificador decide *cuántos* ítems fáciles corren, nunca *cuáles*. Escoger qué ítems reportar después de ver los puntajes es exactamente el ajuste post-hoc que el protocolo existe para impedir.
- **Solo la corrida completa de 225 ítems es reportable como precisión de corpus.** Las tres corridas de este capítulo llevan `reportable: false` en su encabezado. Se reportan igual, rotuladas como pilotos, porque una medición parcial declarada como parcial es información legítima; una medición parcial presentada como final no lo sería.

[PENDIENTE: ejecutar la corrida completa de los 225 ítems (~5 h 30 min estimadas), que es la única reportable como precisión de corpus bajo §3 del protocolo. Las cifras de §4.2 deben re-emitirse a partir de ella.]


4.2. PRECISIÓN DE EJECUCIÓN (PATRONES SIMULADOS ESTILO SPIDER Y BIRD, SOUNDWAVE, IDI-EXEC-75)

Se reportan dos columnas de resultado. La **línea base** es la corrida P3: es la única de las tres que cubre los cuatro corpus y las tres clases de dificultad, y por tanto la única que describe el sistema completo. El **mejor caso observado** es la corrida P1, que alcanzó 53,8% — pero solo llegó a recorrer el tramo fácil de los manifiestos antes de agotar su presupuesto de tiempo, de modo que su cifra describe el desempeño del sistema sobre consultas simples, no sobre el corpus.

> **Advertencia de comparabilidad — obligatoria al leer las dos columnas.** P1 y P3 **no puntuaron los mismos ítems**. P1 se detuvo tras 26 ítems, todos de los niveles fácil / simple / bajo; P3 incluye además los niveles medio y alto/difícil. La diferencia entre 53,8% y 34,2% es por tanto en su mayor parte un efecto de la mezcla de dificultad y no una diferencia de capacidad del sistema entre dos momentos. Además, P1 corrió sobre un commit anterior (`e1e3a75`) al de P3 (`d8de1d3`). Las dos cifras se presentan juntas porque acotan el rango real del sistema — techo en consultas simples, piso sobre la mezcla completa —, no porque una sea la mejora de la otra. La comparación de verdad controlada es la de §4.8.

| Métrica | Umbral Mínimo | Objetivo | Línea base (P3) | Mejor caso observado (P1) |
|---|---|---|---|---|
| Precisión de ejecución — subconjunto simulado estilo Spider | 75% | 85% | 54,5% (6/11) | 62,5% (5/8) |
| Precisión de ejecución — subconjunto simulado estilo BIRD | 50% | 60% | **54,5%** (6/11) | 37,5% (3/8) |
| Precisión de ejecución — SoundWave (30 consultas) | diagnóstico, sin umbral | — | 0,0% (0/5) | 50,0% (2/4) |
| Precisión de ejecución — IDI-EXEC-75 | 80% | 90% | 14,3% (2/14) | 66,7% (4/6) |
| **Precisión de ejecución — global** | — | — | **34,2%** (14/41) | **53,8%** (14/26) |

El único umbral alcanzado en la línea base es el mínimo del subconjunto estilo BIRD (54,5% frente a un mínimo de 50%), y conviene no celebrarlo: se alcanzó sobre once ítems, cinco de ellos del nivel simple, y el propio corpus estilo BIRD se estratificó deliberadamente más liviano que el conjunto oficial. Nótese también que ese corpus obtiene **mejor** resultado en la línea base que en el "mejor caso": la relación entre las dos corridas no es de dominancia, otra razón para no leer P1 como una versión mejorada de P3.

**Reponderación declarada.** La mezcla de dificultad de los dos subconjuntos simulados es deliberadamente más liviana que la de los conjuntos de desarrollo oficiales: el estilo Spider se autoró en proporción 40/40/15/5 (fácil/medio/difícil/muy difícil) frente al ~25/40/22,5/12,5 del oficial, y el estilo BIRD en 50/35/15. La razón es que el sistema evaluado es un modelo de 3.000 millones de parámetros cuantizado sobre una GPU de consumo de 4 GB, no un modelo frontera con presupuesto de ingeniería comercial. El Capítulo 1 (§1.3) ya compromete a este trabajo a afirmar comparabilidad de *clase de dificultad* y nunca de puntaje absoluto, por lo que la reponderación es metodológicamente admisible — pero solo si se declara, y por eso se declara aquí. Una reponderación no declarada sería exactamente el ajuste favorable que el protocolo existe para impedir.

**Desglose por nivel de dificultad (línea base, P3).** Es el resultado más informativo del capítulo:

| Nivel | Aciertos / Puntuados | Precisión |
|---|---|---|
| Fácil (easy / simple / bajo) | 11 / 14 | **78,6%** |
| Medio (medium / moderate) | 2 / 14 | **14,3%** |
| Difícil (hard / challenging / alto) | 1 / 13 | **7,7%** |

El sistema no degrada suavemente: colapsa. Resuelve casi cuatro de cada cinco consultas simples y apenas una de cada trece de las difíciles. La caída ocurre precisamente donde el proyecto declaró su valor — consultas de varias tablas, ventanas temporales y desambiguación semántica —, lo que sitúa el problema en el razonamiento sobre el esquema y no en la generación de sintaxis SQL.

**Desglose por corpus y nivel (línea base, P3):**

| Corpus | Fácil | Medio | Difícil |
|---|---|---|---|
| Estilo Spider | 80,0% (4/5) | 50,0% (2/4) | 0,0% (0/2) |
| Estilo BIRD | 100,0% (5/5) | 0,0% (0/4) | 50,0% (1/2) |
| SoundWave | 0,0% (0/1) | 0,0% (0/1) | 0,0% (0/3) |
| IDI-EXEC-75 | 66,7% (2/3) | 0,0% (0/5) | 0,0% (0/6) |

**Desglose por categoría de IDI-EXEC-75 (línea base, P3):** Agregaciones / KPIs 20,0% (2/10), Ranking / Top-N 0,0% (0/3), Ambigüedad Deliberada 0,0% (0/1). El único ítem de ambigüedad deliberada que alcanzó a puntuarse falló por producir SQL donde el protocolo exigía pedir aclaración: el sistema adivinó en vez de preguntar. Las cinco categorías restantes del corpus no fueron alcanzadas por el preset de una hora.

**Desglose por patrón de estrés de SoundWave (línea base, P3).** Cada consulta de los corpus puede estar etiquetada con los casos límite que ejercita:

| Caso límite | Aciertos / Puntuados |
|---|---|
| Sin caso límite etiquetado | 8 / 15 (53,3%) |
| Claves foráneas anulables | 1 / 1 |
| Valores codificados o enumerados | 1 / 2 |
| Nombres de columna abreviados | 2 / 4 |
| Coincidencia de valores y filtrado de cadenas | 3 / 14 (21,4%) |
| Nombres de columna ambiguos entre tablas | 0 / 1 |
| Dimensiones de cambio lento (historial de precios y suscripciones) | 0 / 2 |
| Ambigüedad entre datos pre-agregados y datos crudos | 0 / 1 |
| Joins multi-salto por tabla puente implícita | 0 / 5 |
| Auto-joins | 0 / 1 |
| Negación / anti-join | 0 / 1 |
| COUNT DISTINCT frente a COUNT | 0 / 3 |

La lectura es directa: el sistema sobrevive a los casos límite que se resuelven **leyendo bien el esquema** (claves anulables, abreviaturas, valores codificados) y falla sistemáticamente en los que exigen **decidir qué se está contando** — multi-salto, pre-agregado contra crudo, distinción entre conteo total y conteo distinto, auto-joins. Las consultas sin ningún caso límite etiquetado aciertan a más del doble de tasa que el promedio, lo que confirma que los patrones de estrés hacen lo que se diseñó que hicieran.

**Clases de fallo (línea base, P3).** De los 41 ítems puntuados, 27 fallaron:

| Clase de fallo | Cantidad | Qué significa |
|---|---|---|
| Número de filas incorrecto | 9 | ejecutó, pero devolvió otra cantidad de filas |
| Valores incorrectos | 6 | ejecutó con la forma correcta, pero al menos un valor difiere |
| Número de columnas incorrecto | 5 | ejecutó, pero devolvió otra cantidad de columnas |
| Bloqueado por verificación | 4 | la cadena de verificación lo detuvo antes de ejecutar |
| Respondió como pregunta meta | 1 | contestó en prosa en vez de consultar |
| No generó SQL | 1 | el pipeline no produjo consulta |
| No pidió aclaración | 1 | produjo SQL donde el protocolo exigía preguntar |

**Veinte de los veintisiete fallos (74%) son SQL que se ejecuta correctamente y responde una pregunta distinta de la que se hizo.** Ese es el hallazgo central del capítulo, y define el límite de la arquitectura actual: una cadena de verificación sintáctica, semántica y de cordura puede atrapar una columna inexistente o un join inventado, pero no puede saber que la pregunta era otra. Las tres firmas recurrentes son "cuenta de filas distinta de la esperada" (9 veces), "cuenta de columnas distinta de la esperada" (5 veces) y "valor distinto en la fila ordenada" (3 veces); esta última suele originarse en la ambigüedad entre datos pre-agregados y crudos — un ítem devolvió 65.314.971 donde la respuesta era 37.

El patrón de columnas de más merece mención aparte: en cinco casos el sistema devolvió la tabla completa (`SELECT u.name, u.display_name, u.email, u.country, …`) donde la pregunta pedía dos columnas. Bajo el criterio del evaluador oficial de Spider, que este protocolo adopta, una consulta que devuelve la respuesta correcta más tres columnas adicionales no respondió la pregunta que se hizo.

> **Nota de interpretación obligatoria.** Estos resultados son comparables *en clase de dificultad* con la literatura que reporta sobre los conjuntos de desarrollo oficiales de Spider y BIRD, pero **no son comparables en puntaje absoluto** — ver la nota metodológica del Capítulo 1, §1.3.

> **Nota sobre el uso diagnóstico de los corpus.** El reporte de cada corrida incluye una sección de diagnóstico que agrupa los fallos por causa raíz. Es la herramienta prevista para dirigir el trabajo de mejora, pero tiene un costo que debe declararse: en el momento en que un fallo observado ahí motiva un cambio en el sistema, estos corpus han actuado como conjunto de desarrollo para ese cambio, y toda precisión posterior medida sobre ellos es optimista en esa medida. Es un uso legítimo — para eso existe un corpus diagnóstico — pero debe decirse, en vez de reportar la cifra posterior como un resultado independiente.

[PENDIENTE: desglose completo por las ocho categorías de IDI-EXEC-75 y por los dieciocho patrones de estrés, alcanzable solo con la corrida completa de 225 ítems.]


4.3. EFECTIVIDAD DE LA VERIFICACIÓN (ERROR DETECTION RATE)

| Métrica | Umbral Mínimo | Objetivo | Resultado Obtenido |
|---|---|---|---|
| Error Detection Rate | 90% | 95% | **98%** |
| Tasa de falsos positivos dura (SQL legal rechazada) | 0% | 0% | [PENDIENTE] |
| Tasa de falsos positivos blanda (SQL legal con salvedad) | reportar, sin umbral | — | [PENDIENTE] |

La cifra de 98% corresponde a la medición del autor sobre errores inyectados contra la cadena de verificación. El protocolo exige, además, que **ninguna cifra de detección se publique sin su tasa de falsos positivos**, porque un verificador que rechace todo obtendría 100% de detección; esas dos cifras quedan pendientes de la construcción del corpus formal de mutantes (diez operadores, ≥ 100 mutantes, aún no redactado en `data/benchmarks/corpora/`).

**Evidencia complementaria de las corridas piloto.** La corrida de línea base ofrece una medición independiente del comportamiento del verificador en operación real, no sobre errores inyectados:

| Observación (P3, 41 ítems) | Valor |
|---|---|
| Consultas bloqueadas antes de ejecutar | 4 |
| Veredictos del verificador | 31 correctas, 4 con salvedad, 4 rechazadas |
| Rechazos por capa | sintáctica 3, semántica 4 |
| Consultas destructivas ejecutadas | 0 |
| Rechazos sobre SQL demostrablemente legal (falsos positivos duros) | 0 observados |

Los cuatro bloqueos fueron correctos y sus causas son verificables una a una: una columna inexistente (`daily_artist_metrics.event_type`), una tabla alucinada (`payment_method`), una columna inexistente en una tabla puente (`user_follows_artists.followed_by_user_id`) y una clave de join inventada (`users.country = daily_artist_metrics.country_code`, que no es una relación del esquema). Es decir: **la cadena de verificación no produjo ningún falso positivo duro en esta corrida y detuvo cuatro consultas que habrían fallado o mentido**. Las cuatro salvedades (10% de las respuestas) corresponden al tercer veredicto introducido en el Capítulo 3 (§3.12.6): no bloquean, la consulta se ejecuta y la salvedad viaja hasta la respuesta didáctica.

Se deja constancia de que el "6 de 8" de la Puerta D1 **no es** un Error Detection Rate: cuenta aciertos de extremo a extremo, no detecciones de errores inyectados, y por eso el protocolo prohíbe reportarlo como tal.

[PENDIENTE: construir `data/benchmarks/corpora/edr_mutants.jsonl` (diez operadores de mutación, ≥ 100 mutantes distribuidos sobre los cuatro corpus) y reportar la detección junto a sus dos tasas de falsos positivos, medidas sobre las consultas de referencia de los cuatro corpus más el corpus de catorce consultas legales de `tests/test_verification_false_positives.py`.]


4.4. DESEMPEÑO Y LATENCIA EN HARDWARE OBJETIVO

| Métrica | Umbral Mínimo | Objetivo | Resultado Obtenido |
|---|---|---|---|
| Latencia P50 (GPU) — consultas de una sola tabla | < 5s | < 3s | **2s** |
| Latencia P50 (solo CPU) — consultas de una sola tabla | — | — | **4s** |
| Tiempo de verificación de extremo a extremo | — | < 2s | **~20s** |
| Tokens/s (`chat_with_meta()`) | — | — | **45 tk/s** |

Estas cifras son mediciones del autor sobre consultas de una sola tabla, que es la clase de consulta para la que el Capítulo 1 (§1.8) define la métrica. El umbral mínimo se cumple y el objetivo de 3s también, en el perfil GPU. El tiempo de verificación de extremo a extremo — que incluye los ciclos de regeneración cuando el verificador rechaza y devuelve la consulta al generador — excede holgadamente el objetivo de 2s heredado del Capítulo 3.

**Medición descriptiva de la corrida de línea base.** La corrida P3 registra tiempos sobre una población distinta: los 41 ítems de los cuatro corpus, incluidos los de varias tablas y los que dispararon regeneración. **No es la medición del protocolo** y no debe compararse con la tabla anterior, pero acota el costo real de una consulta compleja:

| Observación (P3) | Valor |
|---|---|
| Extremo a extremo, mediana | 82,2 s |
| Extremo a extremo, percentil 90 | 98,7 s |
| Extremo a extremo, máximo | 152,7 s |
| Cadena de verificación, mediana | 9 ms |
| Tokens/s, mediana | 12,0 |

Dos lecturas se siguen de ahí. La primera: **la verificación no es el cuello de botella**. Nueve milisegundos de cadena de verificación frente a ochenta y dos segundos de extremo a extremo significa que el costo está íntegramente en las llamadas al modelo del pipeline de siete agentes — comprensión de la consulta, planificación restringida, generación, anotación didáctica y explicación —, no en la garantía de seguridad. La segunda: hay una brecha entre los 45 tk/s medidos sobre consulta simple y los 12,0 tk/s medianos de la corrida, atribuible al procesamiento del prompt (el contexto del esquema y el glosario de dominio se envían completos en cada llamada, con una ventana de 17.152 tokens) más que a la velocidad de generación.

Esta diferencia entre una consulta simple de dos segundos y una consulta de corpus de ochenta segundos es, en sí misma, un resultado: el sistema es cómodo para el uso didáctico de exploración — preguntar, leer la explicación, preguntar otra vez — y no lo es para interacción conversacional rápida sobre consultas analíticas complejas.

[PENDIENTE: ejecutar la medición conforme al protocolo (§5) — las diez primeras consultas del corpus estilo Spider, cinco repeticiones cada una, descartando la corrida de calentamiento, en los dos perfiles de hardware — para adjudicar formalmente la métrica y cerrar la brecha entre las dos mediciones reportadas arriba.]


4.5. A/B: MODELO BASE VS. PERFILES DE INSTRUCCIÓN ESPECIALIZADOS

Instrumentación disponible: `tests/ab_harness.py` compara el modelo base sin perfil contra el modelo con perfil de instrucción especializado activado — el sustituto actual de la comparación "sin adaptador LoRA vs. con adaptador LoRA" que pedía el Capítulo 1.

**Estado: no ejecutado.** El protocolo define dos configuraciones: la corrida A, con el registro de adaptadores vaciado y todos los agentes sobre instrucciones base, y la corrida B, con el registro tal como fue autorado. Las tres corridas del 2026-07-21 son **todas de tipo B**; no existe todavía ninguna corrida A, de modo que el capítulo no puede aislar la contribución de los perfiles de instrucción. Todo lo reportado en §4.2 a §4.4 corresponde al sistema con perfiles activos.

Debe además declararse explícitamente, cada vez que esta comparación se reporte, que mide el efecto de los **perfiles de instrucción** (Capítulo 2, §2.9) y no el de adaptadores LoRA entrenados. La comparación LoRA real queda pendiente hasta que concluya el entrenamiento descrito en el Capítulo 3 (§3.10). En el momento de escribir este capítulo, el registro declara artefactos GGUF para dos agentes que no existen en disco, y el mecanismo de respaldo carga en su lugar el perfil de instrucción correspondiente — comportamiento diseñado como fail-safe y confirmado en las tres corridas.

[PENDIENTE: extender el arnés A/B a los cuatro corpus completos — hoy cubre las ocho pruebas de casos límite — y ejecutar la corrida A para poder reportar §4.8 con las dos configuraciones.]


4.6. EVALUACIÓN CUALITATIVA: REVISIÓN EXPERTA EMPÍRICA DE LOS SIETE ESCENARIOS DE USO

Esta sección reemplaza el estudio de usuario formal (SUS, participantes externos) descartado en el Capítulo 1 (§1.2): el trabajo de grado no incluye reclutamiento de usuarios ni cuestionario estandarizado. En su lugar, los siete escenarios de uso (UC-01–UC-07, Capítulo 1 §1.9) — los seis de perfil ejecutivo más el escenario didáctico UC-07, protagonizado por la persona aprendiz Camilo Vargas — se re-ejecutan sobre el sistema construido en el Capítulo 3 y se califican mediante una revisión experta empírica: cada escenario se ejecuta efectivamente contra el sistema en vivo, desde una sesión limpia, capturando tanto la salida en pantalla como el flujo de eventos de los agentes, y se califica contra una checklist fijada de antemano en el protocolo (§7): corrección de la respuesta, inteligibilidad sin conocimiento de SQL, ausencia de jerga técnica sin explicar, número de preguntas de clarificación, tiempo de respuesta dentro del presupuesto del escenario, aporte del panel didáctico y explicación conceptual de los estados de error. Un escenario **pasa** si no registra ningún hallazgo crítico, definido como respuesta incorrecta, más de dos preguntas de clarificación, o cualquier calificación nula en inteligibilidad o en jerga.

| Escenario | Descripción | Resultado |
|---|---|---|
| UC-01 | Consulta simple con visualización | COMPLETADO |
| UC-02 | Consulta ambigua con clarificación | COMPLETADO |
| UC-03 | Investigación multi-turno persistente | [PENDIENTE — re-ejecutar; ver nota al pie de esta sección] |
| UC-04 | Bloqueo de consulta peligrosa | COMPLETADO |
| UC-05 | Timeout con progreso informado | COMPLETADO |
| UC-06 | Auto-corrección silenciosa | COMPLETADO |
| UC-07 | Consulta con propósito de aprendizaje (panel didáctico) | COMPLETADO |

| Métrica | Umbral Mínimo | Objetivo | Resultado Obtenido |
|---|---|---|---|
| Cobertura Empírica de Escenarios de Uso | ≥ 6/7 (86%) | 7/7 (100%) | **6/7 (86%) confirmados** — cumple el umbral mínimo |
| Preguntas de clarificación por consulta | ≤ 2 | — | Cumple |

Dos criterios de calificación merecen registro explícito. El primero es el de UC-06: bajo la política de auto-corrección silenciosa fijada en la actualización del Capítulo 1, el éxito consiste en que el usuario nunca vea un resultado erróneo **ni el reintento**; la evidencia de que la auto-corrección efectivamente ocurrió se busca en los eventos de agente y en los registros del backend, no en la interfaz. El segundo es el de UC-03, que figuraba bloqueado por la incidencia conocida de restauración de sesiones — al recuperar una sesión guardada solo se reconstruían las preguntas del usuario, no las respuestas del asistente. **Ese bloqueo fue levantado**: la persistencia de los turnos del asistente, con su SQL y sus filas, y su devolución por la ruta de recuperación de sesión quedaron fijadas por prueba automatizada (`tests/test_session_restore.py`), de modo que el escenario ya no está impedido y se califica con la misma checklist que los demás. Se reporta como pendiente y no como aprobado únicamente porque su re-ejecución sobre el sistema en vivo aún no se ha realizado; el umbral mínimo de la métrica (≥ 6/7) se cumple con los seis escenarios ya confirmados.

[PENDIENTE: re-ejecutar UC-03 sobre el sistema en vivo, desde una sesión limpia, y registrar su calificación en la checklist de siete criterios. Es el único escenario que separa el resultado actual del objetivo de 7/7.]


4.7. CLARIDAD DIDÁCTICA DE LAS EXPLICACIONES

Métrica incorporada tras el complemento de alcance del Capítulo 1 (§1.8): mide el porcentaje de explicaciones generadas por el sistema — anotación de SQL, glosario de dominio y justificación de la elección de gráfico — juzgadas comprensibles para un principiante sin conocimiento previo de SQL. El protocolo (§8) fija la unidad de análisis, la checklist de cuatro criterios (todo término técnico evitado o definido en el sitio; la explicación dice *por qué* y no solo *qué*; es correcta respecto del SQL o gráfico que describe; un lector sin SQL podría actuar sobre ella) y un muestreo estratificado de sesenta explicaciones, veinte por tipo, repartidas entre los cuatro corpus.

El sistema se evaluó en dos escenarios complementarios: preguntas sobre conceptos clave de bases de datos, y preguntas sobre aspectos específicos de la base de datos cargada. La revisión experta la condujo el autor de este trabajo, con formación y experiencia en bases de datos, sobre la claridad de las explicaciones producidas por el sistema, y su conclusión es favorable: la herramienta exhibe una facilidad didáctica notable, en ambos escenarios. Debe reconocerse con franqueza que no existe una métrica exacta para medir la efectividad didáctica de este tipo de sistema; la evaluación fue por tanto cualitativa, y su conclusión es que el sistema resulta didáctico y fácil de entender.

| Métrica | Umbral Mínimo | Objetivo | Resultado Obtenido |
|---|---|---|---|
| Claridad Didáctica de Explicaciones | 75% | 90% | Satisfactoria (revisión cualitativa) — porcentaje formal [PENDIENTE] |

El protocolo registra además un límite de alcance conocido (Capítulo 3, §3.11): la justificación de la elección de gráfico tiene solo una implementación básica que cubre casos generales, por lo que se espera que ese estrato califique por debajo de los otros dos y el reporte debe presentar los tres estratos por separado en vez de únicamente la cifra agregada.

[PENDIENTE: aplicar la checklist de cuatro criterios sobre la muestra estratificada de sesenta explicaciones extraída de las corridas puntuadas, y reportar la cifra por estrato — anotación de SQL, glosario de dominio y justificación de gráfico — además de la agregada. La semilla del muestreo se re-sortea una vez, inmediatamente antes de la corrida final, y ambas cifras se reportan si difieren de forma material.]


4.8. COMPARACIÓN CONTRA LÍNEA BASE

La recomendación OE4 del Capítulo 1 pide reportar todos los resultados frente a una línea base del modelo sin perfiles ni adaptadores, de modo que la contribución de cada perfil de instrucción — y más adelante de cada LoRA — sea cuantificable. Esa comparación, en el sentido estricto del protocolo (corrida A con el registro vaciado frente a corrida B), **no se ha ejecutado**: las tres corridas disponibles son de tipo B.

Lo que sí puede establecerse es la línea base **del sistema completo antes del entrenamiento LoRA**, que es el punto de referencia contra el cual se medirá toda mejora posterior:

| Referencia | Corrida | Ítems | Precisión de ejecución |
|---|---|---|---|
| **Línea base del sistema (sin LoRA, mezcla completa de dificultad)** | P3 | 41 | **34,2%** |
| Mejor caso observado (sin LoRA, solo tramo simple) | P1 | 26 | 53,8% |
| Misma selección que P1, commit posterior | P2 | 29 | 34,5% |

La comparación controlada disponible es entre P1 y P2: **misma selección de ítems, mismo preset, mismos parámetros de decodificación, distinto commit** (`e1e3a75` frente a `d8de1d3`, ambos del mismo día). La precisión cayó de 53,8% a 34,5% — diecinueve puntos — sobre esencialmente el mismo conjunto de consultas. Inspeccionadas una a una, las diferencias son concretas y no aleatorias: en P2 el generador emitió literales con comillas triplemente escapadas (`album_type = '''album'''`), que no coinciden con ningún valor y devuelven cero filas, y añadió joins innecesarios que inflaron los conteos (`COUNT(track_artists.track_id)` con join a `tracks` devolvió 49 donde la respuesta era 48). Es una regresión de generación introducida entre dos commits, no ruido de muestreo — y su detección es exactamente lo que un protocolo congelado hace posible.

Se reporta el par completo, y no solo la cifra favorable, porque escoger cuál de las tres corridas presentar después de ver sus puntajes sería el ajuste post-hoc que §0 del protocolo existe para prevenir.

[PENDIENTE: ejecutar la corrida A (registro de adaptadores vaciado, todos los agentes sobre instrucciones base) sobre la misma selección de ítems, y reportar todas las métricas de §4.2 a §4.4 en las dos configuraciones. Solo entonces la contribución de los perfiles de instrucción será cuantificable, tal como pide la recomendación OE4.]


4.9. CONCLUSIONES DEL CAPÍTULO

**C1 — Alcanzar precisiones cercanas al 70% es genuinamente difícil, y eso reencuadra lo que ofrecen las soluciones comerciales. (aporta a OE4)** La línea base del sistema, sobre la mezcla completa de dificultad y sin adaptadores entrenados, es de **34,2%**: menos de la mitad de la meta implícita con la que se suele hablar de estos sistemas. El resultado no se obtuvo por descuido sino bajo un protocolo congelado que prohíbe retocar el criterio después de ver los números — sin normalización de unidades, con exigencia de que el número de columnas coincida, con decodificación determinista. Puesto en perspectiva: un modelo de 3.000 millones de parámetros cuantizado, sobre una GPU de consumo de 4 GB, con verificación de tres capas y explicación didáctica, resuelve una de cada tres consultas de un corpus deliberadamente reponderado hacia lo fácil. La conclusión no es que el sistema haya fracasado, sino que **la distancia entre una implementación local honesta y una solución comercial es una medida real de la capacidad de ingeniería que esas soluciones encierran**, y no un simple recargo de precio. Este capítulo la vuelve cuantitativa.

**C2 — Sí es posible construir una interfaz que ayude a explorar y aprender una base de datos. (aporta a OE4)** La dimensión didáctica del proyecto se sostiene con independencia de la precisión de ejecución. Seis de los siete escenarios de uso pasaron la revisión experta empírica —cumpliendo el umbral mínimo de 6/7, con el séptimo pendiente de re-ejecución y ya desbloqueado—, incluido el escenario de aprendizaje, y la revisión cualitativa de las explicaciones — conceptos generales de bases de datos y aspectos específicos de la base cargada — concluye que el sistema es didáctico y comprensible. Es decir: **el valor de enseñar la base de datos mientras se responde no depende de que la respuesta sea siempre correcta**, sobre todo cuando el sistema muestra qué entendió, qué consultó y por qué, y cuando declara sus salvedades en vez de ocultarlas.

**C3 — El fallo dominante no es SQL inválida sino SQL válida que responde otra pregunta. (aporta a OE4)** Veinte de los veintisiete fallos de la corrida de línea base (74%) son consultas que ejecutaron sin error y devolvieron un resultado distinto del esperado: número de filas, número de columnas o valores. Solo cuatro fueron bloqueadas por la cadena de verificación, y las cuatro con causa verificable — columna inexistente, tabla alucinada, clave de join inventada —, sin ningún falso positivo duro observado. Esto delimita con precisión lo que la arquitectura de verificación actual puede y no puede hacer: **garantiza que no se ejecute SQL inválida o peligrosa, no que se responda la pregunta correcta**. Cerrar esa brecha exige una capa de verificación de *intención* — contrastar el resultado contra lo que el usuario pidió — que hoy no existe.

**C4 — La dificultad está en el razonamiento sobre el esquema, no en la sintaxis. (aporta a OE4)** El desempeño no degrada suavemente con la dificultad: cae de 78,6% en el tramo fácil a 14,3% en el medio y 7,7% en el difícil. Desglosado por patrón de estrés, el sistema resuelve los casos límite que se superan **leyendo bien el esquema** — claves foráneas anulables, nombres abreviados, valores codificados — y falla de forma sistemática en los que exigen **decidir qué se está contando**: joins multi-salto por tabla puente (0/5), datos pre-agregados frente a crudos (0/1), COUNT DISTINCT frente a COUNT (0/3), auto-joins (0/1). Esto tiene una consecuencia práctica directa: el esfuerzo de mejora — entrenamiento LoRA incluido — debe dirigirse al razonamiento sobre relaciones y sobre la fuente de verdad, no a la corrección sintáctica, que el vocabulario cerrado de joins y la planificación restringida ya cubren.

**C5 — El costo del sistema está en el pipeline, no en la garantía de seguridad.** La cadena de verificación de tres capas se ejecuta en una mediana de **9 milisegundos** frente a los 82 segundos de mediana de extremo a extremo de una consulta de corpus. La seguridad del sistema —la promesa de no ejecutar nunca SQL sin verificar— resulta ser esencialmente gratuita; lo caro son las llamadas sucesivas al modelo de los siete agentes, con el contexto del esquema y el glosario reenviados en cada una. Esto convierte la latencia en un problema de arquitectura de orquestación y de caché de prompt, no en un compromiso entre velocidad y seguridad, y explica por qué el sistema resulta cómodo para exploración didáctica (dos segundos en consulta simple) e incómodo para análisis conversacional complejo.

**C6 — El aporte metodológico es tan verificable como el numérico. (aporta a OE4)** El protocolo congelado detectó, entre dos commits del mismo día y sobre la misma selección de ítems, una regresión de diecinueve puntos de precisión con causas identificables (escapado incorrecto de literales, joins innecesarios que inflan conteos). Un protocolo definido después de ver los resultados no habría podido hacerlo, porque no habría habido con qué comparar. Del mismo modo, la corrección de la divergencia entre datos pre-agregados y crudos —de "~5%" documentado a 290.000× medido— solo apareció al exigir que la respuesta correcta se derivara ejecutando la consulta de referencia en vez de declarándola. **La disciplina de medición es, en un trabajo de este alcance, un resultado por derecho propio.**


4.10. RECOMENDACIONES

**R1 (OE4) — Ejecutar la corrida completa antes de cerrar el documento.** Las tres corridas de este capítulo son pilotos parciales marcados como no reportables. La corrida de 225 ítems (~5 h 30 min estimadas) es la única que produce una precisión de corpus reportable bajo el protocolo, y debe ejecutarse sin cambios intermedios en el sistema para que sus cifras reemplacen limpiamente las de §4.2.

**R2 (OE4) — Dirigir el entrenamiento LoRA al razonamiento sobre el esquema, no a la sintaxis.** El desglose por patrón de estrés (§4.2) señala los objetivos concretos: joins multi-salto por tabla puente, elección entre fuente pre-agregada y cruda, conteo distinto frente a conteo total, y auto-joins. El conjunto de entrenamiento debe construirse sobre esas cuatro clases, y no sobre generación de SQL genérica, que la planificación restringida y el vocabulario cerrado de joins ya resuelven.

**R3 (OE4) — Cerrar la brecha de verificación de intención.** Dado que tres de cada cuatro fallos son SQL válida que responde otra pregunta, la mejora de mayor retorno no está en el generador sino en una capa que contraste el resultado con la pregunta original: verificar la forma esperada del resultado (cuántas columnas, cuántas filas, qué tipo de agregación) antes de presentarlo, y convertir el desajuste en una salvedad o en una pregunta de clarificación en vez de en una respuesta segura de sí misma.

**R4 (OE4) — Completar los dos instrumentos de medición faltantes.** El corpus de errores inyectados para la detección de errores (§4.3) y la medición de latencia conforme al protocolo (§4.4) son las dos métricas del Capítulo 1 que todavía se apoyan en mediciones fuera del protocolo. Ambas son de bajo costo comparadas con las corridas de precisión y deben preceder al cierre del documento.

**R5 — Declarar el alcance final si el entrenamiento LoRA no concluye a tiempo.** Si el entrenamiento descrito en el Capítulo 3 (§3.10) no se completa dentro del período, el documento debe cerrarse declarando explícitamente que la evaluación cubre modelo base más perfiles de instrucción, con el entrenamiento LoRA documentado como trabajo futuro y con la línea base de 34,2% de §4.8 como punto de partida registrado para ese trabajo.

**R6 — Documentar como decisión de arquitectura separada cualquier ejecución futura de Spider o BIRD reales.** Antes de comprometer tiempo de sprint a esa extensión debe registrarse el costo de ingesta identificado en el Capítulo 1 (§1.3): los corpus actuales existen porque la respuesta correcta se deriva ejecutando la consulta de referencia, y una base sin datos no puede alojar un corpus.

**R7 (heredada de OE1) — Contrastar la dimensión didáctica con al menos un usuario real.** La conclusión C2 se apoya en revisión experta del autor sin participantes externos. Una validación externa mínima —un solo usuario en fase de aprendizaje de SQL, recorriendo el escenario de aprendizaje y la métrica de claridad didáctica— elevaría sustancialmente la fuerza de la única conclusión que este capítulo no puede respaldar con una cifra ejecutada.


────────────────────────────────────────────────────────────────────────

REFERENCIAS

[PENDIENTE: heredar y extender la bibliografía de capítulos previos. Debe incluir, como mínimo, las fuentes de los dos benchmarks cuya clase de dificultad se replica (Spider y BIRD) y la del evaluador oficial de Spider, cuya función de cálculo de dificultad y cuyo criterio de comparación de resultados adopta el protocolo de §4.1.]


────────────────────────────────────────────────────────────────────────

Universidad Nacional de Colombia — Facultad de Ingeniería — Departamento de Sistemas e Industrial
Período 2026-1S
