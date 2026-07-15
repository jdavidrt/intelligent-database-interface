IDI — Interfaz Inteligente de Bases de Datos

Trabajo de Grado — Ingeniería de Sistemas y Computación
Universidad Nacional de Colombia
Autor: Juan David Ramírez Torres (jdramirezt@unal.edu.co)
Período: 2026-1S (Febrero 2 – Mayo 30, 2026)

> **[ESQUELETO / DEMO — v2]** Armazón estructural para el Capítulo 4. La v2 alinea el capítulo con la actualización del Capítulo 1: siete escenarios de uso (UC-01–UC-07, incluido el escenario didáctico), siete métricas de éxito (se añade la Claridad Didáctica de Explicaciones, §4.7), umbral de cobertura heurística ≥ 6/7, y criterio de evaluación de UC-06 bajo la política de auto-corrección silenciosa. Este capítulo depende de ejecuciones reales contra un backend en vivo (`tests/evaluate.py`, `tests/ab_harness.py`, `gate_d1.py`) y de la construcción de los subconjuntos simulados estilo Spider/BIRD (Capítulo 1, §1.3). Casi todo el contenido está marcado `[PENDIENTE]` a propósito: no debe rellenarse con cifras inventadas. Las tablas se dejan con su estructura de columnas ya fijada por las métricas de éxito del Capítulo 1 (§1.8), de modo que ejecutar los benchmarks solo requiera llenar celdas, no rediseñar el capítulo.
>
> **Decisión metodológica heredada del Capítulo 1**: este proyecto no incluye Spider ni BIRD como benchmarks externos ejecutados contra sus propias bases de datos, ni un estudio de usuario con participantes externos. Toda la evaluación cuantitativa corre sobre la base de datos SoundWave (patrones propios más subconjuntos que simulan la dificultad de Spider/BIRD); la evaluación cualitativa es una revisión experta heurística de los siete escenarios de uso del Capítulo 1 (§1.9), no un estudio SUS.


ÍNDICE

Capítulo 4: Análisis de Resultados
    4.1. Protocolo de Evaluación
    4.2. Precisión de Ejecución (Patrones Simulados Estilo Spider y BIRD, SoundWave, IDI-EXEC-75)
    4.3. Efectividad de la Verificación (Error Detection Rate)
    4.4. Desempeño y Latencia en Hardware Objetivo
    4.5. A/B: Modelo Base vs. Perfiles de Instrucción Especializados
    4.6. Evaluación Cualitativa: Revisión Experta Heurística de los Siete Escenarios de Uso
    4.7. Claridad Didáctica de las Explicaciones
    4.8. Comparación contra Línea Base
    4.9. Conclusiones del Capítulo
    4.10. Recomendaciones


────────────────────────────────────────────────────────────────────────

CAPÍTULO 4: ANÁLISIS DE RESULTADOS

Este capítulo desarrolla el cuarto objetivo específico (OE4): evaluar el desempeño de IDI mediante benchmarking cuantitativo y evaluación cualitativa, comparando los resultados contra métodos baseline. Su insumo es el sistema construido en el Capítulo 3 (OE3) y su contrato de éxito son las siete métricas fijadas en el Capítulo 1 (§1.8) — seis de ellas heredadas de la propuesta y una, la Claridad Didáctica de Explicaciones, incorporada tras el complemento de alcance que hizo del propósito didáctico la identidad principal del proyecto. La regla rectora de este capítulo es la que exige el Capítulo 1 (§1.13, recomendación OE4): el protocolo de evaluación (semillas, criterios de EX, guion de la revisión experta heurística y checklist de claridad didáctica) debe congelarse **antes** de ejecutar los benchmarks simulados, para evitar el ajuste post-hoc de umbrales.


4.1. PROTOCOLO DE EVALUACIÓN

[PENDIENTE: fijar y versionar — semilla aleatoria y criterio de muestreo usados para construir los subconjuntos simulados estilo Spider y estilo BIRD sobre SoundWave (Capítulo 1, §1.3; construcción en Capítulo 3), criterio exacto de Execution Accuracy (comparación de conjuntos de resultados, orden, tolerancia numérica), guion de la revisión experta heurística sobre los siete escenarios de uso (UC-01–UC-07), y checklist de claridad didáctica con su criterio de muestreo de explicaciones (§4.7). Este protocolo debe congelarse antes de §4.2. Nota de datos ya conocida (Capítulo 3, §3.4): la sonda EC-08 referencia una artista ("Adele") que no existe en los datos semilla de SoundWave, por lo que su respuesta correcta es 0 filas — el protocolo debe registrar este ground truth para no puntuar como fallo una respuesta vacía correcta.]


4.2. PRECISIÓN DE EJECUCIÓN (PATRONES SIMULADOS ESTILO SPIDER Y BIRD, SOUNDWAVE, IDI-EXEC-75)

Instrumentación disponible: `tests/evaluate.py` calcula Execution Accuracy a partir de la data semilla de SoundWave; reutiliza los clientes de streaming de `gate_d1.py`. [PENDIENTE: extender el harness para correr también los subconjuntos simulados estilo Spider/BIRD una vez construidos (Capítulo 3), y ejecutar todo contra un backend en vivo.]

| Métrica | Umbral Mínimo | Objetivo | Resultado Obtenido |
|---|---|---|---|
| EX — subconjunto simulado estilo Spider | 75% | 85% | [PENDIENTE] |
| EX — subconjunto simulado estilo BIRD | 50% | 60% | [PENDIENTE] |
| EX — SoundWave (30 consultas) | — | — | [PENDIENTE] |
| EX — IDI-EXEC-75 (75 consultas) | 80% | 90% | [PENDIENTE] |

[PENDIENTE: desglose de EX por categoría de IDI-EXEC-75 (Ranking, Agregaciones, Temporal, etc., Capítulo 1 §1.5), por patrón de estrés de SoundWave (Capítulo 1 §1.4), y por nivel de dificultad dentro de cada subconjunto simulado (easy/medium/hard/extra-hard para el estilo Spider; simple/moderate/challenging para el estilo BIRD) — para diagnosticar granularmente qué trampa semántica o clase de dificultad resiste el sistema y cuál no, el propósito de diseño original de estos artefactos. Nota de interpretación obligatoria: estos resultados son comparables *en clase de dificultad* con la literatura que reporta sobre los dev sets oficiales de Spider/BIRD, pero no son comparables en puntaje absoluto — ver la nota metodológica del Capítulo 1, §1.3.]


4.3. EFECTIVIDAD DE LA VERIFICACIÓN (ERROR DETECTION RATE)

Precedente disponible: la Puerta D1 ya reportó 6/8 sondas EC correctamente resueltas, con EC-07/EC-08 bloqueadas por la capa sintáctica (fail-safe funcionando). [PENDIENTE: consolidar esta cifra en un Error Detection Rate formal frente al umbral de 90%/95% del Capítulo 1, y extenderla a las 30 consultas de SoundWave, las 75 de IDI-EXEC-75, y los dos subconjuntos simulados.]

| Métrica | Umbral Mínimo | Objetivo | Resultado Obtenido |
|---|---|---|---|
| Error Detection Rate (EDR) | 90% | 95% | [PENDIENTE] |


4.4. DESEMPEÑO Y LATENCIA EN HARDWARE OBJETIVO

[PENDIENTE: medición de P50 latency de extremo a extremo sobre GTX 1650 (4GB VRAM) y en modo CPU-only, sobre consultas de una sola tabla.]

| Métrica | Umbral Mínimo | Objetivo | Resultado Obtenido |
|---|---|---|---|
| P50 Latency (GPU) | < 5s | < 3s | [PENDIENTE] |
| P50 Latency (CPU-only) | — | — | [PENDIENTE] |
| Tokens/s (`chat_with_meta()`) | — | — | [PENDIENTE] |


4.5. A/B: MODELO BASE VS. PERFILES DE INSTRUCCIÓN ESPECIALIZADOS

Instrumentación disponible: `tests/ab_harness.py` compara el modelo base sin perfil contra el modelo con perfil de instrucción especializado activado — el sustituto actual de la comparación "sin adaptador LoRA vs. con adaptador LoRA" que pedía el Capítulo 1. [PENDIENTE: ejecución real; y nota explícita de que esta A/B mide el efecto de los *perfiles de instrucción* (Capítulo 2, §2.9), no de adaptadores LoRA entrenados — la comparación LoRA real queda pendiente hasta que el entrenamiento en curso (Capítulo 3, §3.10) concluya.]


4.6. EVALUACIÓN CUALITATIVA: REVISIÓN EXPERTA HEURÍSTICA DE LOS SIETE ESCENARIOS DE USO

Esta sección reemplaza el estudio de usuario formal (SUS, participantes externos) descartado en el Capítulo 1 (§1.2): el trabajo de grado no incluye reclutamiento de usuarios ni cuestionario estandarizado. En su lugar, los siete escenarios de uso (UC-01–UC-07, Capítulo 1 §1.9) — los seis de perfil ejecutivo más el escenario didáctico UC-07, protagonizado por la persona aprendiz Camilo Vargas — se re-ejecutan sobre el sistema construido en el Capítulo 3 y se califican mediante un walkthrough heurístico: el propio autor, y opcionalmente el asesor, evalúan cada escenario contra una checklist de usabilidad (claridad de la respuesta, ausencia de jerga técnica sin explicar, número de preguntas de clarificación, tiempo de respuesta, y — para UC-07 — utilidad pedagógica del panel didáctico) sin intervención de usuarios externos.

[PENDIENTE: definir y versionar la checklist heurística exacta antes de ejecutar la tabla siguiente, como exige el protocolo de evaluación (§4.1).]

| Escenario | Descripción | Resultado (walkthrough heurístico) |
|---|---|---|
| UC-01 | Consulta simple con visualización | [PENDIENTE] |
| UC-02 | Consulta ambigua con clarificación | [PENDIENTE] |
| UC-03 | Investigación multi-turno persistente | [PENDIENTE — bloqueado por KI-1, Capítulo 3 §3.6] |
| UC-04 | Bloqueo de consulta peligrosa | [PENDIENTE] |
| UC-05 | Timeout con progreso informado | [PENDIENTE] |
| UC-06 | Auto-corrección silenciosa | [PENDIENTE] |
| UC-07 | Consulta con propósito de aprendizaje (panel didáctico) | [PENDIENTE] |

| Métrica | Umbral Mínimo | Objetivo | Resultado Obtenido |
|---|---|---|---|
| Cobertura Heurística de Escenarios de Uso | ≥ 6/7 (86%) | 7/7 (100%) | [PENDIENTE] |
| Preguntas de clarificación por consulta | ≤ 2 | — | [PENDIENTE] |

Nota sobre el criterio de UC-06: bajo la política de auto-corrección silenciosa fijada en la actualización del Capítulo 1, el criterio de éxito del walkthrough es que el usuario nunca vea un resultado erróneo ni el detalle del reintento; la evidencia de que la auto-corrección efectivamente ocurrió se busca en los `AgentEvent`s y logs del backend, no en la interfaz.

Nota de alcance: el defecto conocido KI-1 (restauración de sesión, Capítulo 3 §3.6) afecta directamente UC-03. [PENDIENTE: decidir si UC-03 se pospone hasta resolver KI-1, o si se documenta como hallazgo crítico dentro de este mismo walkthrough — bajo esta metodología, a diferencia de un estudio SUS con calendario de participantes, no hay una razón logística para posponer: puede simplemente reportarse como falla conocida.]


4.7. CLARIDAD DIDÁCTICA DE LAS EXPLICACIONES

Métrica incorporada tras el complemento de alcance del Capítulo 1 (§1.8): mide el porcentaje de explicaciones generadas por el sistema — anotación de SQL, glosario de dominio, justificación de la elección de gráfico — juzgadas comprensibles para un principiante sin conocimiento previo de SQL, mediante revisión heurística sobre una muestra tomada de las cuatro fuentes de evaluación (subconjuntos simulados estilo Spider y BIRD, SoundWave-30, IDI-EXEC-75).

[PENDIENTE: definir en §4.1 el tamaño y criterio de la muestra y la checklist de comprensibilidad, y ejecutar la revisión. Prerrequisito honesto registrado en el Capítulo 3 (§3.11): varios requerimientos didácticos por módulo (clarificación como lección, justificación de gráfico, explicación conceptual de fallos) aún no tienen evidencia de implementación — la medición debe hacerse después de cerrar esas brechas, o reportar explícitamente qué fuentes de explicación quedaron fuera y por qué.]

| Métrica | Umbral Mínimo | Objetivo | Resultado Obtenido |
|---|---|---|---|
| Claridad Didáctica de Explicaciones | 75% | 90% | [PENDIENTE] |


4.8. COMPARACIÓN CONTRA LÍNEA BASE

[PENDIENTE: reportar todos los resultados anteriores frente a una línea base del modelo sin perfiles/adaptadores, tal como exige la recomendación OE4 del Capítulo 1, de modo que la contribución de cada perfil de instrucción (y, más adelante, de cada LoRA) sea cuantificable.]


4.9. CONCLUSIONES DEL CAPÍTULO

[PENDIENTE — redactar solo después de ejecutar §4.1–4.8; al menos una conclusión rotulada "(aporta a OE4)". La conclusión sobre la pregunta de investigación debe responder sus dos mitades en el orden actualizado del Capítulo 1: primero el valor didáctico (UC-07, Claridad Didáctica), luego el acceso ejecutivo (EX, latencia, escenarios UC-01–UC-06).]


4.10. RECOMENDACIONES

[PENDIENTE — al menos una recomendación rotulada "(OE4)". Candidatas evidentes a partir de este esqueleto: (i) si el entrenamiento LoRA (en curso, Capítulo 3 §3.10) no se completa a tiempo, recomendar explícitamente el alcance con el que se cerrará el documento final — evaluación solo sobre perfiles de instrucción, con el entrenamiento LoRA documentado como trabajo futuro; (ii) si se decide en el futuro correr Spider/BIRD reales, documentar como ADR separado el costo de ingesta identificado en el Capítulo 1 (§1.3) antes de comprometer tiempo de sprint a esa extensión; (iii) heredada del Capítulo 1 (recomendación OE1): contrastar el escenario UC-07 y la métrica de Claridad Didáctica con al menos un usuario real en fase de aprendizaje de SQL, como validación externa mínima de la dimensión didáctica.]


────────────────────────────────────────────────────────────────────────

REFERENCIAS

[PENDIENTE: heredar y extender la bibliografía de capítulos previos.]


────────────────────────────────────────────────────────────────────────

Universidad Nacional de Colombia — Facultad de Ingeniería — Departamento de Sistemas e Industrial
Período 2026-1S
