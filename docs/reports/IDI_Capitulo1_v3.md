IDI — Interfaz Inteligente de Bases de Datos

Trabajo de Grado — Ingeniería de Sistemas y Computación
Universidad Nacional de Colombia
Autor: Juan David Ramírez Torres (jdramirezt@unal.edu.co)
Período: 2026-1S (Febrero 2 – Mayo 30, 2026)


ÍNDICE

Resumen
Introducción
    Ámbito y Problema
    Pregunta de Investigación
    Objetivos (General y Específicos)
    Enfoque Metodológico
    Descripción del Contenido
Capítulo 1: Análisis de Requerimientos
    1.1. Marco Teórico
        1.1.1. Las Cuatro Eras del NL2SQL
        1.1.2. Trabajos Seminales y Estado del Arte
        1.1.3. Análisis Competitivo
        1.1.4. Brechas Identificadas: Lo que nadie ha resuelto aún
    1.2. Diseño Metodológico
    1.3. Selección y Análisis de Benchmarks
    1.4. Base de Datos de Prueba: SoundWave
    1.5. Conjunto de Prueba Personalizado: IDI-EXEC-75
    1.6. Especificación de Requerimientos Funcionales
    1.7. Requerimientos No Funcionales
    1.8. Métricas de Éxito
    1.9. Escenarios de Casos de Uso
    1.10. Arquitectura de Agentes con LoRA Hot-Swap: Un Solo Modelo, Múltiples Habilidades
    1.11. Avance del Trabajo de Campo: Prototipo Sandbox
    1.12. Conclusiones del Capítulo
    1.13. Recomendaciones
Referencias


────────────────────────────────────────────────────────────────────────

RESUMEN

IDI (Intelligent Database Interface) es un asistente local para el aprendizaje y la exploración de bases de datos. Es un sistema multi-agente de traducción de lenguaje natural a SQL (NL2SQL) concebido como compañero didáctico: cualquier persona que desee aprender sobre bases de datos, SQL y análisis de datos puede hacerlo mediante práctica guiada sobre una base de datos real, formulando preguntas en su propio idioma y recibiendo, junto a cada respuesta, la explicación de cómo se construyó.

Cada consulta se convierte así en una lección concreta: la respuesta viene acompañada del porqué — qué tablas se usaron, qué patrón SQL se aplicó (un JOIN, una agregación, un filtro temporal) y por qué esa era la forma correcta de resolverla. Si la pregunta es ambigua, el sistema pregunta antes de actuar, y esa misma clarificación funciona como una lección breve sobre por qué la ambigüedad importa al construir una consulta. Si el SQL generado tiene errores, el sistema los detecta y corrige antes de que el usuario vea un resultado incorrecto, sin exponer en el proceso qué tipo de error se cometió.

Esta capacidad de responder enseñando tiene una consecuencia directa: el mismo sistema sirve a quien no quiere aprender SQL sino simplemente prescindir de él. Ejecutivos y gerentes no técnicos pueden extraer insights estadísticos de bases de datos relacionales mediante preguntas conversacionales, sin intermediarios técnicos. Un gerente formula una pregunta en español — "¿Cómo van las ventas de este trimestre?" — y el sistema comprende la intención, genera el SQL correcto, verifica su integridad, ejecuta la consulta y presenta los resultados con una visualización automática y una interpretación en lenguaje ejecutivo, reduciendo a segundos lo que hoy tarda días. El artefacto técnico es el mismo en ambos casos: lo que cambia no es el sistema, sino qué hace el usuario con la respuesta que recibe — un estudiante aprende de ella; un ejecutivo actúa sobre ella.

La innovación central reside en que IDI opera completamente en local — sin APIs de pago, sin enviar datos sensibles a la nube — usando un único modelo de lenguaje de 3 mil millones de parámetros (Qwen2.5-Coder-3B-Instruct) que cambia de habilidad en tiempo real mediante adaptadores LoRA (Low-Rank Adaptation, una técnica de fine-tuning ligero que permite especializar un modelo sin modificar sus pesos originales) intercambiados durante la ejecución: según la fase del proceso, el mismo modelo actúa como intérprete de consultas, generador de SQL o verificador de resultados — todo en una GPU de consumidor con 4GB de VRAM, o incluso sin GPU, usando solamente CPU y RAM.

El sistema se evalúa mediante cuatro conjuntos de consultas construidos íntegramente sobre una única base de datos de prueba (SoundWave DB, 19 tablas): dos subconjuntos que simulan los patrones de dificultad publicados por los benchmarks estándar del campo (Spider, BIRD), un conjunto de 30 consultas diseñado para provocar los 18 modos de fallo documentados en la literatura, y un conjunto de 75 consultas en lenguaje ejecutivo real (IDI-EXEC-75). La evaluación cualitativa se realiza mediante revisión experta heurística de escenarios de uso — incluyendo, junto a los seis escenarios de perfil ejecutivo, un escenario dedicado a la claridad didáctica de las explicaciones generadas —, sin estudio con usuarios externos.


────────────────────────────────────────────────────────────────────────

INTRODUCCIÓN

Las bases de datos relacionales son el lugar donde las organizaciones y las instituciones acumulan su conocimiento más valioso. Esos repositorios contienen las respuestas a preguntas urgentes — cómo evoluciona un negocio, qué patrones esconden los datos, qué decisión conviene tomar —, pero esas respuestas están escritas en un idioma que la mayoría de las personas no habla: SQL.

Quien está aprendiendo ese idioma — un estudiante, un analista junior, cualquier persona autodidacta — enfrenta el problema en su forma más directa: no habla todavía el lenguaje de los datos, y los recursos disponibles para aprenderlo (cursos, documentación, foros, ejercicios de práctica) rara vez ofrecen lo que ese aprendizaje realmente exige — práctica guiada sobre una base de datos real, con retroalimentación inmediata sobre los propios errores del estudiante y no sobre un ejercicio de juguete desconectado de un caso de uso genuino.

Esa misma brecha lingüística se observa en el ámbito laboral. Aproximadamente el 85% de los tomadores de decisiones en las empresas carecen de competencia en SQL (Luo et al., 2025), lo que crea una dependencia hacia analistas de datos y departamentos de TI que se traduce en tres consecuencias medibles: latencia decisional (la respuesta llega cuando la decisión ya fue tomada), pérdida de contexto (el intermediario técnico no comprende las sutilezas del análisis deseado) y subutilización de los datos (las bases de datos contienen respuestas que nadie formula porque formularlas requiere un lenguaje que no hablan). El estudiante y el ejecutivo comparten, en el fondo, el mismo obstáculo; lo que los distingue es lo que cada uno haría con una respuesta que hoy no puede obtener.

El campo NL2SQL (Natural Language to SQL) ha experimentado una transformación acelerada. Los Modelos de Lenguaje de Gran Escala (LLMs, por sus siglas en inglés: Large Language Models) han elevado la precisión de ejecución en benchmarks estándar a rangos superiores al 90% en escenarios controlados. Sin embargo, la brecha entre el laboratorio y el uso real permanece abierta: los errores semánticos — sintaxis SQL correcta pero resultados incorrectos — representan hasta el 98.8% de todos los fallos en sistemas NL2SQL de última generación (Liu et al., 2025a). El schema linking, es decir, el mapeo de términos de lenguaje natural a las tablas y columnas correctas de una base de datos, constituye la categoría de error más frecuente, responsable del 27–68% de los fallos.

Es en esa doble brecha — entre lo que un aprendiz necesita entender y lo que los recursos educativos actuales le ofrecen, y entre lo que los LLMs saben hacer y lo que las organizaciones necesitan que hagan — donde IDI encuentra su razón de existir.

La pregunta de investigación que guía este trabajo es:

¿Cómo puede un mismo sistema NL2SQL servir simultáneamente como entorno didáctico para cualquier persona que desee aprender bases de datos, SQL y análisis de datos mediante práctica guiada sobre una base de datos real, y como puente de acceso a datos para ejecutivos y gerentes no técnicos que necesitan extraer insights estadísticos que apoyen la toma de decisiones — en ambos casos sin requerir experticia previa en SQL ni intermediarios técnicos, garantizando la corrección de las consultas y la interpretabilidad y el valor pedagógico de los resultados?

Para responder esta pregunta, el trabajo se articula en torno a los siguientes objetivos, aprobados en la propuesta radicada ante el CADE.

Objetivo General

Diseñar, desarrollar y evaluar IDI (Interfaz Inteligente de Bases de Datos), un sistema NL2SQL modular multi-agente que permita a ejecutivos no técnicos extraer insights estadísticos de bases de datos relacionales mediante consultas conversacionales en lenguaje natural con conciencia contextual, resolución de ambigüedad, verificación automatizada y continuidad investigativa basada en sesiones, alcanzando una corrección de consultas superior al 90% mientras opera en hardware de consumo local (GTX 1650 de 4GB de VRAM y 16GB de RAM) con comunicación transparente de progreso para tiempos de procesamiento extendidos (hasta 30 segundos), con el propósito de democratizar el acceso a datos organizacionales y habilitar una toma de decisiones ágil basada en evidencia.

Objetivos Específicos

OE1 — Análisis de requerimientos: conducir un análisis integral de requerimientos para un sistema NL2SQL enfocado en ejecutivos, identificando requerimientos funcionales y no funcionales, criterios de éxito y métricas de evaluación mediante revisión de literatura, análisis competitivo y evaluación de necesidades de stakeholders.

OE2 — Diseño del sistema: diseñar la arquitectura modular de IDI, especificando responsabilidades de componentes, protocolos de comunicación inter-agente, flujos de datos, mecanismos de gestión de sesiones, estrategias de comunicación de progreso y selección de stack tecnológico optimizado para despliegue local en hardware de consumo con timeouts de consulta extendidos (hasta 30 segundos).

OE3 — Desarrollo de la solución: implementar los siete módulos centrales de IDI (Gestor de Contexto, Comprensión de Consultas, Generador SQL, Agente de Verificación, Motor de Visualización, Gestor de Sesiones y Orquestador Multi-Agente) con generación de datos sintéticos de entrenamiento, pipelines de fine-tuning de modelos, gestión de flujo conversacional y componentes de interfaz de usuario, incluyendo indicadores de progreso y controles de sesión.

OE4 — Análisis de resultados: evaluar el desempeño de IDI mediante benchmarking cuantitativo (precisión de ejecución, latencia, efectividad de verificación, patrones de uso de sesiones) y evaluación cualitativa (revisión experta mediante walkthroughs heurísticos sobre los escenarios de uso, efectividad de indicadores de progreso), comparando los resultados contra métodos baseline e identificando oportunidades de mejora.

Complemento de alcance — retroalimentación del director de trabajo de grado: el Objetivo General y los objetivos específicos anteriores son los aprobados en la propuesta radicada ante el CADE y se conservan íntegros. Durante la elaboración de este capítulo, el director del trabajo de grado observó que el proyecto no tenía por qué enfocarse únicamente en su caso de uso ejecutivo, ya que la misma arquitectura — comprensión de intención, generación verificada de SQL, y explicación en lenguaje natural de cada paso del razonamiento — sirve, sin ningún cambio técnico, como entorno de aprendizaje guiado de SQL y bases de datos para cualquier persona interesada en adquirir esa competencia. Esta observación no reemplaza los objetivos aprobados; los complementa, ampliando el público objetivo declarado (de "ejecutivos y gerentes no técnicos" a "cualquier persona interesada en aprender sobre bases de datos y análisis de datos, como ejecutivos y gerentes no técnicos") e incorporando una dimensión didáctica explícita en los requerimientos, escenarios de uso y métricas de evaluación desarrollados en este capítulo (Secciones 1.6 a 1.9). El sistema no cambia; cambia el reconocimiento explícito de a quién más sirve y por qué.

Metodológicamente, estos objetivos se abordan bajo el paradigma de Design Science Research (Hevner et al., 2004), centrado en la construcción y evaluación rigurosa de un artefacto de TI. El desarrollo se organiza en cuatro sprints de cuatro semanas que recorren el ciclo completo — análisis de requerimientos (OE1), diseño arquitectónico (OE2), implementación del pipeline multi-agente (OE3) y evaluación cuantitativa y cualitativa (OE4) — de modo que cada objetivo específico se materializa en un incremento verificable del artefacto. El diseño metodológico detallado, incluyendo el cronograma de sprints y las dimensiones de evaluación, se presenta en la Sección 1.2.

Este documento constituye el Capítulo 1 del trabajo de grado, el cual corresponde al análisis de requerimientos (OE1) y sobre el cual se construirá todo el ciclo de vida del sistema. En él se establece el mapa del problema, se identifican las brechas en el estado del arte, se diseña la estrategia de evaluación, se especifican los requerimientos y se documenta el avance empírico alcanzado hasta la fecha. A partir de este punto, el capítulo desarrolla los requerimientos, escenarios de uso y métricas bajo el propósito ampliado descrito arriba: aprendizaje guiado y acceso ejecutivo como dos expresiones del mismo proyecto.


────────────────────────────────────────────────────────────────────────

CAPÍTULO 1: ANÁLISIS DE REQUERIMIENTOS

Este capítulo desarrolla el primer objetivo específico (OE1): conducir un análisis integral de requerimientos para un sistema NL2SQL enfocado en ejecutivos y, tras el complemento de alcance introducido en la Introducción, también en el aprendizaje de bases de datos y SQL. Su propósito es transformar la pregunta de investigación en un cuerpo de requerimientos verificable y trazable, sustentado en evidencia académica y de mercado. Para ello, el capítulo recorre una secuencia deliberada: primero construye el marco teórico que delimita el estado del arte y las brechas no resueltas (1.1); luego fija el diseño metodológico que gobierna el proyecto (1.2); a continuación define la estrategia de evaluación en cuatro niveles de datos —los benchmarks estándar Spider y BIRD, la base de datos de estrés SoundWave y el conjunto ejecutivo IDI-EXEC-75 (1.3 a 1.5)—; especifica los requerimientos funcionales y no funcionales junto con las métricas de éxito, los escenarios de uso y la arquitectura de agentes con LoRA hot-swap (1.6 a 1.10); y, finalmente, documenta el avance empírico del prototipo sandbox (1.11) antes de consolidar las conclusiones (1.12) y recomendaciones (1.13). El resultado es la especificación de requisitos sobre la cual se erigirán el diseño (OE2), el desarrollo (OE3) y la evaluación (OE4) en los capítulos siguientes.


1.1. MARCO TEÓRICO

1.1.1. Las Cuatro Eras del NL2SQL

El campo NL2SQL ha evolucionado a través de cuatro eras que definen el terreno sobre el cual IDI se construye:

La primera era (1990s–2016) fue la de los modelos estadísticos: sistemas basados en reglas y aproximaciones N-gram que lograban éxito limitado en dominios cerrados con patrones rígidos. Funcionaban, pero solo si el usuario hablaba exactamente como el sistema esperaba.

La segunda era (2017–2018) llegó con las redes neuronales. Las LSTMs y los mecanismos de atención marcaron el punto de inflexión. El benchmark Spider, publicado en la conferencia EMNLP por Yu et al. (2018), estableció la evaluación estandarizada entre dominios y fijó la Execution Accuracy (EX) — el porcentaje de consultas generadas que producen el resultado correcto al ejecutarse — como la métrica canónica del campo.

La tercera era (2018–2023) fue la de los modelos pre-entrenados. Los transformadores (BERT, T5, RoBERTa) elevaron la precisión al rango 70–80% mediante transfer learning. Trabajos como DIN-SQL (Pourreza y Rafiei, 2023) y RESDSQL (Li et al., 2023a) marcaron las líneas base académicas del período.

La cuarta era (2023–Presente) es la de los LLMs. Modelos como GPT-4, Claude y LLaMA demuestran precisiones superiores al 95% cuando se contextualizan apropiadamente. Lo verdaderamente relevante para IDI es que esta era trae consigo una ventaja sin precedentes: grandes empresas — AWS, Google, Microsoft, Salesforce, Databricks — están invirtiendo activamente en soluciones NL2SQL comerciales. Esto significa que el campo no es un ejercicio académico aislado sino un problema de la industria con validación de mercado real, lo que convierte este trabajo de grado en una contribución con relevancia directa para el sector productivo.


1.1.2. Trabajos Seminales y Estado del Arte

El panorama completo del NL2SQL moderno ha sido cartografiado en el tutorial "Natural Language to SQL: State of the Art and Open Problems", presentado en la conferencia VLDB 2025, donde se identifican cinco niveles de dificultad del problema (Luo et al., 2025). Los niveles 1–3 (sintaxis básica, consultas de una tabla, joins) están mayormente resueltos. El nivel 4 — conocimiento de dominio y reconocimiento de entidades — es investigación activa y es exactamente donde IDI se posiciona. El nivel 5 — diálogos multi-turno — es la frontera futura.

Uno de los resultados empíricos más relevantes para el diseño de IDI proviene de una arquitectura NL2SQL desplegada en producción real en la colaboración AWS–Cisco, documentada en el artículo "Enterprise-grade natural language to SQL generation using LLMs: Balancing accuracy, latency, and scale" (Kumar y Matthew, 2025). Su hallazgo central es que la optimización arquitectónica supera la escala del modelo: lograron 95% de precisión con modelos relativamente ligeros (Code Llama 13B, Claude Haiku) usando prompts con alcance de dominio, pre-resolución de identificadores, y verificación tripartita — es decir, validación en tres capas: sintaxis, semántica, y sanidad de los resultados. Lo que no hicieron fue crear mecanismos de clarificación activa ni gestión de sesiones — dos vacíos que IDI llena.

La evidencia empírica de que la especialización de agentes produce mejoras medibles proviene del trabajo "CHASE-SQL: Multi-Path Reasoning and Preference Optimized Candidate Selection in Text-to-SQL" (Pourreza et al., 2024). Mediante el uso de múltiples generadores LLM con estrategias distintas — descomposición divide-and-conquer, razonamiento por cadena de pensamiento, y generación de ejemplos sintéticos — seguidos de un agente selector fine-tuned, la arquitectura multi-agente mejoró la precisión en 8–12% respecto a configuraciones monolíticas equivalentes. Este resultado fundamenta la decisión arquitectónica central de IDI: descomponer el proceso en módulos especializados orquestados dinámicamente.

El enfoque de exploración de múltiples caminos de generación SQL fue llevado a su máxima expresión en "Alpha-SQL: Zero-Shot Text-to-SQL using Monte Carlo Tree Search", publicado en ICML 2025 (Li et al., 2025). Mediante la combinación de LLMs con Monte Carlo Tree Search (MCTS), el sistema demostró que la diversidad de candidatos SQL es una estrategia efectiva para aumentar la robustez. El costo computacional de MCTS es prohibitivo para hardware de consumidor (>30 segundos por consulta), pero el principio subyacente — generar y evaluar múltiples opciones — es adoptable en escenarios de alta incertidumbre.

Quizás el hallazgo más crítico para el diseño de IDI proviene del benchmark "NL2SQL-BUGs: A Benchmark for Detecting Semantic Errors in NL2SQL Translation", presentado en ACM SIGKDD 2025 (Liu et al., 2025a). Al analizar 4,602 consultas SQL incorrectas generadas por sistemas de última generación (DIN-SQL, DAIL-SQL, C3 y E-SQL, usando GPT-3.5 y GPT-4) sobre los benchmarks Spider y BIRD, los autores documentaron que el schema linking — es decir, la selección incorrecta de tabla o columna — representa entre el 27% y el 68% de todos los fallos, seguido de errores de condición (15–20%), errores de JOIN (10–25%), y problemas de agregación (10–15%). Además, los métodos de auto-corrección iterativa solo logran corregir el 10–23% de los errores mientras introducen 5–40% de errores nuevos. La implicación es directa: el sistema NL2SQL debe acertar en el primer intento.

Finalmente, el benchmark diagnóstico "Dr.Spider: A Diagnostic Evaluation Benchmark towards Text-to-SQL Robustness", reconocido como Notable Top-5% en ICLR 2023 (Chang et al., 2023), reveló que perturbaciones menores en la formulación de preguntas o en la nomenclatura del esquema — como abreviar nombres de columnas a formas crípticas (trk_dur_ms en lugar de track_duration_ms) — causan caídas de precisión de hasta 14% en promedio. Este hallazgo informa directamente el diseño de la base de datos de prueba SoundWave (Sección 1.4), donde se embeben deliberadamente convenciones de nombrado mixtas para evaluar la robustez del sistema.


1.1.3. Análisis Competitivo

El mercado de soluciones NL2SQL está dominado por plataformas de grandes empresas tecnológicas que integran esta capacidad dentro de ecosistemas más amplios de analítica de datos. Las tres soluciones comerciales de mayor adopción — Tableau Pulse (Salesforce), Power BI Q&A (Microsoft) y Amazon Q (AWS) — comparten una fortaleza y una limitación estructural: las tres ofrecen interfaces conversacionales maduras orientadas a usuarios de negocio, pero dependen de capas de abstracción propietarias (modelos semánticos, ecosistemas cloud) que reproducen la misma dependencia técnica que supuestamente deberían eliminar. Tableau y Power BI requieren que un analista técnico prepare previamente el modelo de datos; Amazon Q, aunque cuenta con el sistema de contexto de dominio más sofisticado entre las comerciales, opera exclusivamente en la nube de AWS con costos por consulta que hacen inviable el uso exploratorio intensivo. ThoughtSpot se destaca por estar diseñado desde su origen para usuarios no técnicos, con un motor de búsqueda relacional especializado (SpotIQ), pero su licenciamiento de seis cifras anuales lo excluye del alcance de organizaciones medianas y pequeñas — precisamente el segmento más afectado por la brecha de acceso a datos. Google Looker con Gemini ofrece capacidades multimodales prometedoras pero hereda la dependencia del ecosistema Google Cloud. Databricks SQL Assistant se diferencia por la transparencia del SQL generado — el usuario puede ver y entender la consulta — pero su audiencia objetivo son analistas técnicos, no ejecutivos.

En el ámbito académico, los sistemas de referencia como DIN-SQL (Pourreza y Rafiei, 2023), CHASE-SQL (Pourreza et al., 2024) y Alpha-SQL (Li et al., 2025) demuestran alta precisión en benchmarks (82.8%, 74.46% y 69.7% en BIRD respectivamente) pero carecen de las capas de experiencia de usuario que un entorno empresarial real demanda: ninguno ofrece clarificación activa de ambigüedades, visualización automática de resultados, ni gestión de sesiones investigativas. Además, CHASE-SQL requiere modelos de gran escala (Gemini-1.5-Pro) y Alpha-SQL demanda más de 30 segundos por consulta con MCTS, lo que los hace inviables para despliegue local en hardware de consumidor.

En síntesis: cada solución resuelve aspectos parciales del problema, pero ninguna los resuelve todos simultáneamente. Las comerciales tienen la experiencia de usuario pero no la independencia. Las académicas tienen la precisión pero no la interfaz. Ninguna ofrece despliegue completamente local sin APIs de pago, clarificación activa, y gestión de sesiones — todo sobre hardware de consumidor. Y más allá de la brecha ejecutiva, ninguna de las soluciones revisadas — comerciales o académicas — está diseñada para enseñar: todas asumen que el usuario ya sabe qué quiere preguntar y solo necesita el resultado, no la comprensión de cómo se llegó a él.


1.1.4. Brechas Identificadas: Lo que nadie ha resuelto aún

| # | Brecha | Quién la tiene | Solución IDI |
|---|--------|----------------|--------------|
| 1 | Sin adquisición sistemática de conocimiento de dominio antes de la consulta | Todos los sistemas revisados | Context Manager Agent con encuesta estructurada de onboarding |
| 2 | Manejo pasivo de ambigüedades (el usuario debe reformular por su cuenta) | Kumar y Matthew (2025); DIN-SQL; todas las comerciales | Query Understanding Agent con diálogos de clarificación guiados |
| 3 | Sin persistencia de sesiones investigativas entre días | Todos los sistemas revisados | Session Manager con almacenamiento multi-turno |
| 4 | Sin visualización automática integrada al flujo NL2SQL | Todos los sistemas académicos | Visualization Engine con selección inteligente de gráficos |
| 5 | Dependencia de hardware costoso o APIs de pago | CHASE-SQL; Alpha-SQL; todas las comerciales | Despliegue local sobre GTX 1650 (4GB VRAM) o en CPU+RAM |
| 6 | Sin función didáctica: el usuario recibe el resultado pero no aprende a construir la consulta | Todos los sistemas revisados, comerciales y académicos | Explicación en lenguaje natural y anotación didáctica por cláusula de cada SQL generado, en cada agente del pipeline (requerimiento transversal, Sección 1.6) |

IDI será el único sistema que satisface las seis condiciones simultáneamente. Ninguna de ellas es imposible individualmente; lo que no existe es un sistema integrado, de código abierto, que las reúna sobre hardware de consumidor. La sexta brecha no proviene de la literatura revisada — ningún trabajo académico o comercial se propone resolverla — sino del complemento de alcance descrito en la Introducción: se documenta aquí porque, a partir de esa retroalimentación, pasó a ser una condición de diseño tan vinculante como las cinco anteriores.


1.2. DISEÑO METODOLÓGICO

El proyecto sigue una metodología de Design Science Research — DSR — (Hevner et al., 2004), un paradigma centrado en la creación y evaluación rigurosa de artefactos de TI que resuelven problemas organizacionales identificados. A diferencia de la investigación empírica tradicional, DSR produce como resultado principal un artefacto funcional (en este caso, el sistema IDI) evaluado con rigor cuantitativo y cualitativo. La implementación se organiza en cuatro sprints de cuatro semanas:

| Sprint | Semanas | Foco | Lo que produce |
|--------|---------|------|----------------|
| 1 | 1–4 (Feb 2 – Feb 28) | Análisis de requerimientos y diseño | Este documento: SRS, benchmarks, SoundWave DB, IDI-EXEC-75 |
| 2 | 5–8 (Mar 1 – Mar 28) | Infraestructura core y Context Manager | Backend funcional, modelo integrado, adquisición de contexto |
| 3 | 9–12 (Mar 29 – Abr 25) | Generación SQL, verificación, integración | Pipeline completo: pregunta → SQL → resultado → gráfico |
| 4 | 13–16 (Abr 26 – May 23) | Evaluación y documentación | Benchmarks simulados ejecutados, revisión experta heurística, tesis escrita |

La evaluación se estructura en tres dimensiones: precisión (Execution Accuracy sobre los cuatro niveles de la Sección 1.3, los cuatro construidos o simulados sobre SoundWave), rendimiento (latencia y uso de recursos en hardware de consumidor), y usabilidad — evaluada mediante revisión experta heurística de los siete escenarios de uso de la Sección 1.9, incluyendo el escenario didáctico (UC-07) incorporado tras el complemento de alcance descrito en la Introducción. Se consideró y se descartó el uso de un cuestionario estandarizado como el System Usability Scale o SUS (Brooke, 1996), que exige reclutar una muestra externa de usuarios ejecutivos: el alcance de un trabajo de grado de un semestre, sin acceso institucional a ese perfil de usuario, no permite un estudio de usuario formal con la validez estadística que el instrumento requiere.


1.3. SELECCIÓN Y ANÁLISIS DE BENCHMARKS

La evaluación de IDI se apoya en cuatro niveles de datos, cada uno diseñado para responder una pregunta distinta. Los cuatro niveles se ejecutan sobre una única base de datos — SoundWave — por una decisión metodológica explícita que esta sección justifica antes de presentar la tabla.

Nota metodológica — de benchmarks externos a patrones simulados: Spider (Yu et al., 2018) y BIRD (Li et al., 2023b) se distribuyen como conjuntos de bases de datos independientes (~20 esquemas en el dev set de Spider, ~95 en el de BIRD), cada uno con su propio archivo SQLite y su propio script oficial de evaluación. Ejecutarlos tal como se distribuyen exigiría: (a) construir un adaptador de ingesta que traduzca decenas de esquemas ajenos a la convención `databases/<nombre>/` que ya usa el descubrimiento dinámico de IDI; (b) generar o suplir, para cada uno de esos esquemas desconocidos, el glosario de negocio por base de datos que hoy el Context Manager Agent obtiene de un archivo curado a mano (como `04_soundwave_survey.json`); y (c) correr cientos de consultas adicionales a través de un pipeline multi-agente sobre un modelo local de 3B parámetros, con el consiguiente costo de tiempo. Nada de esta infraestructura existe hoy ni está dentro del alcance de un trabajo de grado de un semestre.

En su lugar, IDI adopta una estrategia de simulación de patrones: en vez de ejecutar los benchmarks originales, se construyen subconjuntos de consultas escritos íntegramente contra el esquema de SoundWave, calibrados para replicar la distribución de dificultad y los tipos de error que Spider y BIRD documentan en su propia literatura (los niveles de dificultad easy/medium/hard/extra-hard de Spider; las categorías simple/moderate/challenging y el uso de conocimiento externo — "evidence" — de BIRD). Esto permite comparar la clase de dificultad que IDI resiste, no el puntaje absoluto frente a los leaderboards oficiales de Spider o BIRD — una limitación que se declara explícitamente para no sobre-interpretar los resultados del Capítulo 4. El tamaño exacto de cada subconjunto simulado se fija durante su construcción (Capítulo 3) y se reporta en el Capítulo 4.

| Nivel | Fuente de patrones | Tamaño | Pregunta que responde |
|-------|-----------|--------|----------------------|
| Primario | Patrones estilo Spider (Yu et al., 2018), simulados sobre SoundWave | A definir en el Capítulo 3 | ¿IDI generaliza sobre patrones de complejidad cross-domain, dentro de un único esquema? |
| Secundario | Patrones estilo BIRD (Li et al., 2023b), simulados sobre SoundWave | A definir en el Capítulo 3 | ¿IDI resiste patrones de datos sucios/reales y de conocimiento externo, dentro de SoundWave? |
| Terciario | SoundWave DB (este trabajo) | 30 consultas | ¿IDI resiste las 18 trampas semánticas documentadas? |
| Cuaternario | IDI-EXEC-75 (este trabajo) | 75 consultas | ¿IDI entiende el lenguaje real de los ejecutivos? |

El benchmark Spider (Yu et al., 2018) es el estándar universal del campo: 10,181 pares pregunta-SQL en 200 bases de datos y 138 dominios, con una precisión humana de referencia de ~92% que fija un techo teórico. Sus consultas son relativamente limpias y formales — no reflejan cómo habla un gerente real —, pero su taxonomía de dificultad es la que IDI replica en el subconjunto simulado.

El benchmark BIRD, publicado en NeurIPS 2023 bajo el título "Can LLM Already Serve as a Database Interface?" (Li et al., 2023b), complementa a Spider con el patrón de datos empresariales reales: valores nulos, duplicados, anomalías, y consultas que requieren conocimiento de dominio externo al esquema. IDI replica este patrón, no el esquema físico de BIRD.

SoundWave y IDI-EXEC-75 cubren lo que ningún benchmark estándar provee — y se describen en las dos secciones siguientes.


1.4. BASE DE DATOS DE PRUEBA: SOUNDWAVE

SoundWave es una base de datos de 19 tablas en el dominio de streaming musical, diseñada como artefacto de evaluación original de este trabajo de grado. Su premisa de diseño parte del hallazgo central de la literatura: los LLMs modernos producen SQL sintácticamente válido el 95–99% del tiempo; el problema no resuelto es semántico. Por lo tanto, el esquema está ingeniado para provocar fallos de resultado incorrecto, no fallos de parsing.

El dominio musical fue seleccionado porque requiere naturalmente todos los patrones SQL complejos que quiebran sistemas NL2SQL (agregaciones anidadas, joins multi-hop, razonamiento temporal, operaciones de conjunto), y porque cualquier evaluador comprende intuitivamente los conceptos del dominio (artistas, canciones, playlists, suscripciones).

La base de datos se organiza en cuatro capas:

| Capa | Tablas | Lo que provoca |
|------|--------|----------------|
| Entidades core | users, artists, albums, tracks, genres, subscription_plans | Colisión deliberada de nombres de columna (name en 4 tablas, title en 2, status en 2); valores codificados como enteros (plan_type: 1=free, 2=student, 3=individual, 4=family) |
| Junction / bridge | playlist_tracks, user_follows_artists, user_liked_tracks, artist_genres, track_artists, track_genres | Cadenas de join multi-hop de hasta 5 tablas que el usuario jamás nombra (playlists → playlist_tracks → tracks → track_artists → artists) |
| Eventos / transaccional | play_events, subscriptions, subscription_periods, payments, playlists | Tabla polimórfica de eventos (event_type: play/skip/save/share); FK nullables (tracks.album_id NULL = single); lógica de rangos temporales (end_date IS NULL = activo) |
| Analítica / derivada | pricing_history, daily_artist_metrics | Ambigüedad pre-agregado vs. raw: daily_artist_metrics tiene valores intencionalmente ~5% superiores a lo que COUNT(play_events) retorna, simulando pipelines ETL reales |

En total, SoundWave embebe deliberadamente 8 patrones de estrés NL2SQL derivados de la literatura académica (Bhaskar et al., 2023; Lei et al., 2024; Li et al., 2023b; Chang et al., 2023; Lee et al., 2021; Eckmann et al., 2025; Liu et al., 2025a). Incluye 30 consultas SQL de referencia pre-verificadas, cada una anotada con los patrones de estrés que ejercita, y datos semilla realistas para ejecución inmediata.

Lo que SoundWave aporta que los benchmarks estándar no proveen es control deliberado sobre los modos de fallo: permite diagnosticar con granularidad qué tipo de trampa semántica quiebra al sistema y cuál resiste.


1.5. CONJUNTO DE PRUEBA PERSONALIZADO: IDI-EXEC-75

IDI-EXEC-75 es un conjunto de 75 consultas en lenguaje natural ejecutivo — informal, ambiguo, cargado de jerga empresarial — diseñado para evaluar la dimensión que ni Spider ni BIRD cubren: cómo hablan realmente los tomadores de decisiones cuando quieren datos.

Las consultas se organizan en 8 categorías que reflejan los patrones cognitivos reales de los ejecutivos:

| Categoría | Consultas | Ejemplo representativo | Lo que evalúa |
|-----------|-----------|----------------------|---------------|
| Ranking / Top-N | 10 | "¿Cuáles son los 5 productos que más se vendieron el mes pasado?" | ORDER BY + LIMIT + agregación temporal |
| Agregaciones / KPIs | 15 | "¿Cuánto vendimos en total el mes pasado?" | Funciones de agregación básicas a complejas |
| Temporal / Tendencias | 15 | "¿Estamos creciendo o decreciendo en comparación con el año pasado?" | Comparaciones período-sobre-período, self-joins temporales |
| Comparaciones | 10 | "Compara las ventas de los últimos tres meses entre nuestros dos mejores vendedores" | Subconsultas, joins cruzados, cálculos derivados |
| Filtrado / Segmentación | 10 | "¿Qué departamentos están por encima del 80% de su presupuesto anual?" | WHERE + HAVING + cálculos de porcentaje |
| Relacional / Multi-tabla | 5 | "¿Qué vendedores tienen clientes asignados que no han hecho ninguna compra?" | Anti-joins, LEFT JOIN + IS NULL |
| Análisis Complejo | 5 | "¿Cuál es la tasa de retención de clientes mes a mes?" | CTEs, subconsultas correlacionadas, funciones de ventana |
| Ambigüedad Deliberada | 5 | "¿Cómo vamos?" / "¿Estamos en rojo?" | Diseñadas para activar el módulo de clarificación |

La distribución por dificultad es 20% baja, 40% media, 40% alta — reflejando que el perfil ejecutivo real tiende hacia preguntas de análisis que involucran múltiples tablas y períodos de tiempo.


1.6. ESPECIFICACIÓN DE REQUERIMIENTOS FUNCIONALES

IDI se descompone en siete módulos especializados, cada uno con una responsabilidad clara. El valor de esta modularidad no está en la separación misma sino en lo que logra: cada módulo puede evolucionar independientemente, fallar sin derribar al sistema completo, y ser evaluado en aislamiento. Tras el complemento de alcance descrito en la Introducción, cada módulo incorpora además un requerimiento didáctico transversal: no solo ejecuta su función, sino que expone al usuario — ejecutivo o aprendiz — el razonamiento detrás de lo que hizo.

Context Manager Agent (CMA) — 9 requerimientos. Lo que logra: el sistema aprende el vocabulario de negocio, sinónimos, convenciones temporales y estructura del esquema antes de la primera consulta. Esto ataca directamente la categoría de error dominante (schema linking, 27–68% de fallos según Liu et al., 2025a). Acepta archivos DDL, genera embeddings vectoriales del glosario, y retorna el paquete de contexto en menos de 200ms. Requerimiento didáctico: expone bajo demanda un mini-glosario navegable del dominio, con ejemplos de consulta por término.

Query Understanding Agent (QUA) — 8 requerimientos. Lo que logra: la consulta del usuario se descompone en intención, entidades, período temporal y filtros antes de generar SQL. Detecta tres tipos de ambigüedad (temporal, de entidad, de métrica) y formula máximo 2 preguntas de clarificación en lenguaje no técnico. Esto elimina la frustración de obtener respuestas incorrectas por preguntas mal interpretadas. Requerimiento didáctico: explica, en cada clarificación solicitada, por qué la ambigüedad detectada importa para construir una consulta SQL correcta — convirtiendo la pregunta de clarificación en una lección breve sobre diseño de consultas.

SQL Generator Agent (SGA) — 9 requerimientos. Lo que logra: produce SQL ejecutable en cuatro dialectos (PostgreSQL, MySQL, SQLite, SQL Server), con explicación en lenguaje natural de cada consulta generada y reporte de los supuestos realizados. Soporta hasta 5 tablas con JOIN, subconsultas, CTEs y funciones de ventana. Nunca ejecuta directamente — siempre pasa por verificación. Requerimiento didáctico: anota cada cláusula del SQL generado (SELECT, JOIN, WHERE, GROUP BY, etc.) con una explicación de una línea sobre su propósito, dirigida a alguien que está aprendiendo a leer SQL.

Verification Agent (VA) — 9 requerimientos. Lo que logra: actúa como el guardián del sistema en tres capas. Capa 1 (sintaxis) valida que el SQL sea parseable. Capa 2 (semántica) verifica que las tablas y columnas referenciadas existen en el esquema real. Capa 3 (sanidad) verifica que los resultados son plausibles y bloquea operaciones destructivas (DELETE, DROP). La verificación completa toma menos de 2 segundos. Requerimiento didáctico: cuando un fallo debe llegar al usuario — una consulta bloqueada por seguridad o una verificación que no puede resolverse automáticamente —, lo traduce a una explicación conceptual (por ejemplo, por qué una columna referenciada no existe en el esquema, o por qué un JOIN produce filas duplicadas), en lugar de un mensaje de error técnico; los errores que la auto-corrección resuelve no interrumpen al usuario ni se le exponen (UC-06).

Visualization Engine (VE) — 9 requerimientos. Lo que logra: selecciona automáticamente el tipo de gráfico más apropiado (barra, línea, dispersión, pastel, tabla interactiva, entre 8 opciones), agrega líneas de tendencia para series temporales, genera una descripción en lenguaje ejecutivo del insight principal, y permite drill-down interactivo. El ejecutivo recibe una visualización lista para presentar sin tocar ningún eje ni configurar nada. Requerimiento didáctico: justifica en una frase por qué se eligió ese tipo de gráfico y no otro, ayudando a que el usuario aprenda a elegir visualizaciones apropiadas.

Session Manager Agent (SMA) — 9 requerimientos. Lo que logra: las investigaciones no se pierden al cerrar el navegador. El usuario puede guardar, retomar, buscar y exportar sesiones completas — incluyendo consultas, SQL, resultados, visualizaciones e historial de clarificación. Permite retomar un análisis el lunes que se empezó el viernes, o exportar una investigación como PDF para una reunión. Requerimiento didáctico: permite marcar una sesión como "ruta de aprendizaje" y exportarla junto con sus explicaciones didácticas como material de estudio.

Multi-Agent Orchestrator (MAO) — 9 requerimientos. Lo que logra: coordina el flujo canónico (CMA → QUA → SGA → VA → VE) con bifurcaciones para clarificación y reintentos automáticos (máximo 2). Informa al usuario del progreso en tiempo real vía WebSocket, estima el tiempo restante, y propaga cancelaciones en menos de 500ms. Requerimiento didáctico: comunica, junto con el progreso, en qué fase del pipeline se encuentra la consulta y qué agente está actuando — trazabilidad que un ejecutivo no necesita pero que un aprendiz usa para entender la arquitectura completa del sistema.

En total: 62 requerimientos funcionales distribuidos en 7 módulos (55 orientados a la función central de cada agente, más 7 requerimientos didácticos transversales — uno por módulo — añadidos tras el complemento de alcance descrito en la Introducción).


1.7. REQUERIMIENTOS NO FUNCIONALES

Los requerimientos no funcionales definen las restricciones dentro de las cuales IDI debe operar — y cada una existe por una razón práctica:

Desempeño: consultas simples en menos de 5 segundos (porque un ejecutivo no espera más), consultas complejas en menos de 30 segundos (con progreso informado), visualizaciones en menos de 1 segundo.

Hardware: el sistema completo debe operar en una GTX 1650 con 4GB de VRAM y 16GB de RAM. Esta restricción existe porque la democratización del acceso a datos pierde sentido si requiere hardware de datacenter. En modo GPU, la VRAM máxima durante inferencia es 3.5GB; el sistema también debe ser capaz de operar sin GPU usando solamente CPU y RAM del sistema, con latencia degradada pero funcional.

Usabilidad: cobertura heurística de al menos 6 de los 7 escenarios de uso sin hallazgos críticos (evaluada por revisión experta, sin estudio con usuarios externos), máximo 2 preguntas de clarificación por consulta, cero jerga técnica sin explicar — el sistema puede usar términos técnicos, pero cuando lo hace los define en el mismo turno.

Claridad didáctica (requerimiento añadido tras el complemento de alcance): toda explicación generada por el sistema — anotación de SQL, glosario de dominio, justificación de una visualización — debe ser comprensible para alguien sin conocimiento previo de SQL, validado mediante revisión heurística sobre una muestra de respuestas.

Seguridad: el sistema jamás ejecuta SQL destructivo sin autorización explícita, no expone datos en logs, y funciona completamente offline sin dependencia de servicios externos.

Extensibilidad: adaptadores LoRA intercambiables sin reinicio del servidor, arquitectura que permite reemplazar el LLM base sin cambios en capas superiores, soporte de múltiples perfiles de dominio sin reinstalación.

En total: 20 requerimientos no funcionales en 5 categorías (19 originales más el requerimiento de claridad didáctica).


1.8. MÉTRICAS DE ÉXITO

Las métricas de éxito son el contrato cuantitativo que vincula el diseño con la evaluación. Se seleccionaron las seis métricas más relevantes y ampliamente utilizadas en la evaluación de sistemas NL2SQL, alineadas con la taxonomía de dificultad de los benchmarks Spider y BIRD (véase la nota metodológica de la Sección 1.3):

| Métrica | Definición | Umbral Mínimo | Objetivo | Fuente |
|---------|-----------|--------------|----------|--------|
| Execution Accuracy (EX) — Estilo Spider | Porcentaje de consultas cuyo SQL generado produce el resultado correcto al ejecutarse sobre SoundWave | 75% | 85% | Subconjunto simulado estilo Spider (Sección 1.3) |
| Execution Accuracy (EX) — Estilo BIRD | Misma definición, sobre el subconjunto que replica patrones de datos empresariales reales | 50% | 60% | Subconjunto simulado estilo BIRD (Sección 1.3) |
| Execution Accuracy (EX) — IDI-EXEC-75 | Misma definición, aplicada a consultas en lenguaje ejecutivo informal | 80% | 90% | IDI-EXEC-75 (75 consultas) |
| Error Detection Rate (EDR) | Porcentaje de consultas SQL erróneas correctamente detectadas por el Verification Agent antes de ejecutarse | 90% | 95% | Todas las fuentes |
| P50 Latency | Latencia mediana para consultas de una sola tabla, medida de extremo a extremo (pregunta del usuario → resultado en pantalla) | < 5s | < 3s | Medición en hardware objetivo |
| Cobertura Heurística de Escenarios de Uso | Porcentaje de los siete escenarios UC-01–UC-07 (Sección 1.9) que superan una revisión experta heurística sin hallazgos críticos | ≥ 6/7 (86%) | 7/7 (100%) | Revisión experta (walkthrough heurístico, sin usuarios externos) |
| Claridad Didáctica de Explicaciones (métrica añadida tras el complemento de alcance) | Porcentaje de explicaciones generadas (anotación de SQL, glosario de dominio, justificación de gráfico) juzgadas comprensibles para un principiante en una revisión heurística por muestreo | 75% | 90% | Revisión experta sobre muestra de las cuatro fuentes de evaluación |


1.9. ESCENARIOS DE CASOS DE USO

Cinco personas de usuario definen los arquetipos de interacción con IDI: Claudia Herrera (Directora de Operaciones, 47 años, MBA — no sabe SQL y no quiere aprenderlo), Andrés Castellanos (Gerente de Ventas, 38 años — "sé que existe el SELECT, pero no más"), Patricia Molina (Directora Financiera, 52 años — experta en Excel, baja tolerancia a errores numéricos), Sebastián Ríos (Analista BI, 28 años — super-user técnico y validador del sistema), y Camilo Vargas (estudiante de últimos semestres de Ingeniería / analista junior, 24 años — está aprendiendo SQL y bases de datos, y usa IDI tanto para resolver tareas concretas como para entender el razonamiento detrás de cada consulta que el sistema genera). Camilo es la persona incorporada tras el complemento de alcance descrito en la Introducción.

UC-01 — Consulta simple con visualización: Claudia escribe: "Muéstrame cuánto vendimos en cada región el mes pasado." El sistema comprende la intención, genera el SQL con GROUP BY region y filtro de fecha, lo verifica, lo ejecuta, y presenta un gráfico de barras con un insight: "La región Andina lidera con 42% del total." Claudia lo guarda como "Reunión Junta - Ventas Marzo." Todo ocurre en menos de 8 segundos.

UC-02 — Consulta ambigua con clarificación: Andrés escribe: "¿Cómo están los vendedores?" El sistema detecta tres ambigüedades (¿qué métrica?, ¿qué período?, ¿todos o una región?) y presenta dos preguntas con opciones seleccionables. Andrés elige "cumplimiento de meta" y "este mes." El sistema genera un gráfico de barras horizontales con línea de referencia en 100%.

UC-03 — Investigación multi-turno persistente: Patricia retoma una sesión guardada ("Análisis Presupuestal Q3"), el sistema restaura el historial de 3 consultas previas, y cuando ella escribe "De esos departamentos que mencionaste ayer, ¿cuál tiene la mayor variación respecto al año pasado?", el sistema resuelve la referencia contextual y genera la comparación interanual correcta.

UC-04 — Bloqueo de consulta peligrosa: Claudia escribe: "Elimina los clientes que no han comprado en 2024." El sistema detecta la intención destructiva, rechaza la operación, y ofrece una alternativa constructiva: "IDI está configurado para consultas de solo lectura. ¿Quieres que te muestre la lista de esos clientes para exportarla?"

UC-05 — Timeout con progreso informado: Andrés lanza una consulta extremadamente compleja. El sistema muestra progreso por fases con estimación de tiempo. Andrés decide cancelar; el sistema responde en menos de 500ms y procesa una consulta simplificada.

UC-06 — Auto-corrección transparente: el SQL generado referencia una columna inexistente (stock_actual en lugar de stock_disponible). El Verification Agent detecta el error, el Orchestrator activa un reintento automático con el error como contexto adicional, y el SQL corregido se ejecuta exitosamente — todo transparente para el usuario.

UC-07 — Consulta con propósito de aprendizaje (escenario añadido tras el complemento de alcance): Camilo, que está aprendiendo SQL, escribe: "¿Cuántas canciones tiene cada playlist creada este año?" El sistema genera el SQL, lo ejecuta, y junto con la respuesta despliega un panel didáctico: qué tablas participaron (playlists, playlist_tracks), qué tipo de join se usó y por qué, y una nota conceptual sobre la diferencia entre COUNT(*) y COUNT(columna) aplicada a este caso concreto. Camilo guarda la sesión como "Ruta de aprendizaje — JOINs y agregación" para repasarla después.

Estos siete escenarios constituyen, además, el instrumento de evaluación cualitativa del proyecto — con UC-07 evaluando específicamente la dimensión didáctica introducida por el complemento de alcance —: en el Capítulo 4 (OE4) se re-ejecutan como walkthroughs heurísticos de usabilidad conducidos por revisión experta, sin recurrir a un estudio con usuarios externos ni a un cuestionario estandarizado como el SUS.


1.10. ARQUITECTURA DE AGENTES CON LoRA HOT-SWAP: UN SOLO MODELO, MÚLTIPLES HABILIDADES

Esta es la decisión arquitectónica que hace viable todo el sistema sobre hardware de consumidor. IDI no usa múltiples modelos de IA. Usa un solo modelo base (Qwen2.5-Coder-3B-Instruct, cuantizado a Q4_K_M, ~2GB de VRAM) al que se le intercambian adaptadores LoRA en tiempo real según la fase del proceso.

LoRA (Low-Rank Adaptation) es una técnica de fine-tuning introducida por Hu et al. (2022) que permite entrenar adaptadores ligeros — del orden del 1–5% de los parámetros del modelo base — para especializar el comportamiento de un LLM en tareas específicas sin modificar los pesos originales. En la práctica, esto significa que un solo modelo en memoria puede adquirir habilidades diferentes según el adaptador que se le aplique. Es como un profesional que cambia la habilidad que está usando según la tarea: el mismo cerebro, pero con especialización instantánea para cada tarea.

La arquitectura funciona así:

```
┌──────────────────────────────────────────────────────────┐
│                  Multi-Agent Orchestrator                  │
│          (enruta la consulta según la fase)                │
└──────┬──────────┬──────────────┬──────────────┬───────────┘
       │          │              │              │
  ┌────▼───┐ ┌───▼────────┐ ┌──▼──────────┐ ┌─▼──────────┐
  │Context │ │   Query    │ │    SQL      │ │ Verification│
  │Manager │ │Understanding│ │  Generator  │ │   Agent    │
  │ Agent  │ │   Agent    │ │   Agent     │ │            │
  └────┬───┘ └───┬────────┘ └──┬──────────┘ └─┬──────────┘
       │         │             │               │
  ┌────▼─────────▼─────────────▼───────────────▼──────────┐
  │          LLM Service (Adapter Controller)              │
  │  • Gestiona la conexión con llama.cpp                  │
  │  • Hot-swap de LoRA vía API /lora-adapters (<100ms)    │
  │  • Enruta cada solicitud al adaptador apropiado        │
  └───────────────────────┬────────────────────────────────┘
                          │ HTTP API (localhost:8080)
  ┌───────────────────────▼────────────────────────────────┐
  │                   llama.cpp Server                      │
  │                                                         │
  │  Modelo base: Qwen2.5-Coder-3B-Instruct (Q4_K_M)      │
  │  ~2GB VRAM (GPU) ó ~3GB RAM (modo CPU)                 │
  │                                                         │
  │  Adaptadores LoRA (precargados, intercambiados en       │
  │  tiempo de ejecución):                                  │
  │  ├── query_understanding.gguf  (~30MB)                  │
  │  ├── clarification.gguf        (~30MB)                  │
  │  ├── sql_generator.gguf        (~30MB)                  │
  │  └── verification.gguf         (~30MB)                  │
  └─────────────────────────────────────────────────────────┘
```

Lo que esta arquitectura logra:

Un solo modelo en memoria. En lugar de cargar 4 modelos separados (que requerirían 4× la VRAM), IDI mantiene un único modelo base y le aplica adaptadores ligeros (~30MB cada uno) que modifican su comportamiento sin recargar los pesos principales. El intercambio ocurre en menos de 100ms — imperceptible para el usuario.

Especialización real sin costo. Cada adaptador LoRA se entrena con datos específicos de su tarea: el adaptador de SQL Generator se entrena con miles de pares pregunta→SQL; el de Verification se entrena con pares SQL_correcto/SQL_incorrecto; el de Query Understanding se entrena con pares pregunta→intención_estructurada. Esto produce una mejora medible en cada tarea respecto al modelo base sin adaptador.

Escalabilidad modular. Agregar un nuevo agente (por ejemplo, un generador de reportes) solo requiere entrenar un nuevo adaptador LoRA (~2-4 horas en Google Colab con GPU T4 gratuita) y registrarlo en el controlador. No hay que reentrenar el modelo base ni modificar la infraestructura.

Los adaptadores se entrenan usando la técnica QLoRA — Quantized LoRA — (Dettmers et al., 2023) con la librería Unsloth en Google Colab, sobre datasets de 15,000–20,000 ejemplos en 2-4 horas con la GPU T4 gratuita. Los datasets de entrenamiento incluyen gretelai/synthetic_text_to_sql para el generador SQL, y corpus auto-generados a partir de las consultas de SoundWave e IDI-EXEC-75 para los demás adaptadores.

Esta arquitectura es la razón por la que IDI puede ofrecer capacidades multi-agente reales sobre una GTX 1650 de 4GB de VRAM — un requisito que ningún otro sistema multi-agente NL2SQL en la literatura satisface.


1.11. AVANCE DEL TRABAJO DE CAMPO: PROTOTIPO SANDBOX

Antes de comprometer el diseño completo, se construyó un prototipo funcional mínimo (sandbox) para validar empíricamente las hipótesis tecnológicas más críticas, siguiendo los principios de evaluación temprana del Design Science Research (Hevner et al., 2004). El sandbox es un sistema de un único agente con la siguiente arquitectura:

```
start.py
  ├── llama.cpp server   → puerto 7860  (motor de inferencia)
  ├── backend/main.py    → puerto 5000  (proxy FastAPI)
  └── frontend/          → puerto 5173  (Vite + React + TypeScript)
```

Componentes implementados: motor de inferencia llama.cpp con Qwen2.5-Coder-3B-Instruct (Q4_K_M); backend FastAPI; interfaz React con chat conversacional, resaltado sintáctico de SQL, 5 temas visuales, animación typewriter, y métricas de generación (tokens, tiempo, tokens/s).


[ESPACIO PARA CAPTURA DE PANTALLA: Interfaz del Sandbox — Vista general del chat]


[ESPACIO PARA CAPTURA DE PANTALLA: Sandbox — Ejemplo de consulta SQL generada con resaltado sintáctico]


[ESPACIO PARA CAPTURA DE PANTALLA: Sandbox — Métricas de generación y temas visuales]


Hallazgos de validación:

| Hipótesis | Resultado | Evidencia |
|-----------|-----------|-----------|
| Qwen2.5-Coder-3B opera en GTX 1650 (4GB VRAM) | Confirmada | 25–35 tokens/s, ~2GB VRAM en uso |
| El sistema opera en modo CPU-only (sin GPU) | Confirmada | llama.cpp soporta inferencia por CPU; ~3-5 tokens/s con 16GB RAM, funcional para consultas simples |
| llama.cpp soporta hot-swap de adaptadores LoRA | Confirmada | API /lora-adapters disponible en compilación CUDA |
| El modelo base genera SQL plausible sin fine-tuning | Confirmada con limitaciones | Simples: ~75% correctas; complejas: ~40% |
| FastAPI + llama.cpp tienen latencia aceptable | Confirmada | < 2s para consultas simples (modo GPU) |
| La arquitectura de prompt puede guiar el razonamiento | Confirmada | El ciclo de 6 fases reduce errores de sintaxis |

Un hallazgo particularmente relevante para la democratización del sistema es que llama.cpp permite inferencia no solo en GPU sino también en CPU y RAM. Si bien el rendimiento se degrada significativamente (de 25–35 tokens/s en GPU a ~3–5 tokens/s en CPU-only), el sistema permanece funcional para consultas simples. Esto significa que IDI podría ejecutarse en cualquier PC moderno con 16GB de RAM, incluso sin GPU dedicada — ampliando considerablemente la base de hardware compatible y haciendo viable el despliegue en organizaciones con infraestructura limitada.

Lo que el sandbox cubre (~15–20% del sistema final) y lo que falta:

| Lo que el sandbox ya probó | Lo que falta construir |
|---|---|
| Modelo base corriendo localmente en GPU y CPU | Arquitectura multi-agente con 7 módulos especializados |
| Generación de SQL desde un prompt monolítico | Adquisición de contexto con encuesta + embeddings + ChromaDB |
| Interfaz conversacional funcional | Verificación tripartita (sintaxis → semántica → sanidad) |
| Latencia aceptable (< 2s simples en GPU) | Fine-tuning LoRA de los 4 adaptadores especializados |
| Hot-swap de LoRA validado como viable | Gestión de sesiones persistentes |
| Compatibilidad CPU-only confirmada | Visualización automática con Recharts |

La implicación más relevante del sandbox es que los umbrales de desempeño especificados son alcanzables: si el modelo base sin ningún fine-tuning ya logra < 2s de latencia y ~75% de precisión en consultas simples, el sistema completo con adaptadores LoRA especializados y verificación tripartita tiene un camino claro hacia los objetivos de > 85% de precisión y < 5s de latencia.


Resumen del estado de avance:

| Artefacto | Estado | Qué demuestra |
|-----------|--------|---------------|
| Prototipo sandbox | Completado | Viabilidad tecnológica en hardware de consumidor (GPU y CPU) |
| Base de datos SoundWave (19 tablas, 30 consultas) | Completado | Artefacto de evaluación original con 18 categorías de fallo |
| Conjunto IDI-EXEC-75 (75 consultas ejecutivas) | Completado | Representatividad del perfil de usuario real |
| Síntesis de investigación sobre fallos NL2SQL | Completado | Fundamentación académica de 15 fuentes |
| Documento SRS completo | Completado | 62 RF, 20 RNF, 7 métricas de éxito |
| Revisión de literatura y análisis competitivo | Completado | 6 soluciones comerciales, 5 académicas |


1.12. CONCLUSIONES DEL CAPÍTULO

Este capítulo ha construido la fundación sobre la que se erige el sistema IDI y materializa el primer objetivo específico (OE1). De lo hecho emergen seis conclusiones que orientan el camino hacia adelante; cada una se rotula con el objetivo del proyecto al que aporta evidencia, de modo que la trazabilidad objetivo–conclusión quede explícita:

Primera (aporta a OE1) — El problema es real y el momento es oportuno. La brecha de acceso a datos para tomadores de decisiones no técnicos está documentada (85% sin competencia SQL según Luo et al., 2025) y las grandes empresas tecnológicas están invirtiendo activamente en solucionarla. Este trabajo no navega aguas inexploradas: navega aguas que la industria ya validó como valiosas, pero con una ruta que nadie ha completado aún (las seis brechas identificadas, la sexta añadida tras el complemento de alcance).

Segunda (aporta a OE1 y fundamenta OE2) — Los errores semánticos, no los sintácticos, son el enemigo. La literatura es inequívoca: los LLMs generan SQL sintácticamente válido el 95–99% del tiempo (Liu et al., 2025a). Lo que falla es el significado. El diseño de IDI — con adquisición de contexto pre-consulta, clarificación activa de ambigüedades, y verificación tripartita — ataca directamente esta realidad.

Tercera (fundamenta OE2 y OE3) — Un solo modelo con múltiples habilidades es viable. La validación del sandbox demuestra que Qwen2.5-Coder-3B opera en una GTX 1650 de 4GB con 25–35 tokens/s y ~2GB de VRAM, e incluso en modo CPU-only con latencia funcional. La arquitectura LoRA hot-swap (Hu et al., 2022) permite convertir ese único modelo en un sistema multi-agente real sin multiplicar los recursos de hardware — una solución que no existe en la literatura revisada.

Cuarta (aporta a OE1 y habilita OE4) — Los artefactos de evaluación están listos para usar. SoundWave (19 tablas, 30 consultas, 18 categorías de fallo embebidas) e IDI-EXEC-75 (75 consultas ejecutivas en 8 categorías) son contribuciones empíricas originales que están completamente construidas y operacionales, complementando los benchmarks estándar con las dimensiones que estos no cubren.

Quinta (proyecta OE3) — El sistema es alcanzable en el cronograma del semestre. El sandbox ya cubre el 15–20% del sistema final, los benchmarks están seleccionados, los requerimientos están especificados con umbrales cuantitativos, y la arquitectura está validada. Los tres sprints restantes tienen un camino claro: infraestructura (Sprint 2), pipeline completo (Sprint 3), evaluación (Sprint 4).

Sexta (proyecta OE2) — Lo que queda por hacer está bien definido. El Capítulo 2 tomará esta base para construir el diseño detallado: los diagramas UML, los contratos de API entre módulos, la selección y justificación final del stack tecnológico, y el diseño de los datasets de entrenamiento para cada adaptador LoRA.

Nota sobre el complemento de alcance — La retroalimentación del director de trabajo de grado, recibida durante la elaboración de este capítulo, amplió el público objetivo declarado sin alterar el artefacto técnico: el mismo pipeline que sirve a un ejecutivo sirve, sin modificación alguna, a quien aprende. Esta ampliación se incorporó de forma trazable en las Secciones 1.1, 1.6 a 1.9 (la sexta brecha competitiva, los siete requerimientos didácticos transversales, la persona Camilo Vargas, el escenario UC-07 y la métrica de Claridad Didáctica), y no afecta el Objetivo General ni los objetivos específicos aprobados ante el CADE, que se conservan íntegros en la Introducción.


1.13. RECOMENDACIONES

Del análisis realizado se derivan recomendaciones que orientan las fases siguientes del proyecto. Para preservar la trazabilidad exigida, se formula al menos una recomendación vinculada a cada objetivo específico:

Sobre el análisis de requerimientos (OE1) — Mantener el catálogo de requerimientos (62 funcionales y 20 no funcionales) bajo control de versiones y revisarlo al cierre de cada sprint, de modo que todo cambio quede trazado frente a la pregunta de investigación. Se recomienda, además, validar una muestra de los requerimientos con al menos un usuario ejecutivo real antes de congelar el alcance, para reducir el riesgo de sesgo derivado de requerimientos elicitados únicamente desde la literatura. Dado que el complemento de alcance didáctico surgió como retroalimentación del director y aún no ha sido validado con estudiantes reales, se recomienda además contrastar el escenario UC-07 y el requerimiento de Claridad Didáctica con al menos un usuario en fase de aprendizaje de SQL antes de congelar su diseño definitivo en el Capítulo 2.

Sobre el diseño del sistema (OE2) — Formalizar tempranamente los contratos de API entre los siete módulos mediante esquemas explícitos (por ejemplo, modelos Pydantic y especificación OpenAPI), de manera que la verificación tripartita y la orquestación puedan probarse de forma aislada. Se recomienda documentar cada decisión arquitectónica significativa como un Architecture Decision Record (ADR), comenzando por la elección del LoRA hot-swap frente a alternativas multi-modelo.

Sobre el desarrollo de la solución (OE3) — Priorizar el fine-tuning del adaptador de Generación SQL y del Agente de Verificación, pues atacan la categoría de error dominante (schema linking, 27–68% de fallos según Liu et al., 2025a) y constituyen la ruta crítica del pipeline. Dada la restricción de 4GB de VRAM, se recomienda instrumentar el consumo de memoria desde la primera integración y fijar un presupuesto de VRAM por componente, para evitar regresiones que solo se detectarían en evaluación.

Sobre el análisis de resultados (OE4) — Establecer desde ya el protocolo de evaluación (semillas, criterios de Execution Accuracy, y el guion de la revisión experta heurística sobre los siete escenarios de uso) y congelarlo antes de ejecutar los benchmarks simulados, para garantizar la reproducibilidad y evitar el ajuste post-hoc de umbrales. Se recomienda reportar siempre los resultados frente a una línea base del modelo sin adaptadores, de modo que la contribución de cada LoRA sea cuantificable.

Recomendación estratégica para el documento final — Anexar como apéndice la propuesta original aprobada ante el CADE, con el fin de que el comité evaluador y los jurados puedan contrastar de forma transparente las metas inicialmente pactadas frente a la evolución y el cumplimiento alcanzados a lo largo del trabajo.


────────────────────────────────────────────────────────────────────────

REFERENCIAS

Bhaskar, A., Talaei, S., y Saberi, A. (2023). Benchmarking and analyzing text-to-SQL on ambiguous questions. En Proceedings of the 2023 Conference on Empirical Methods in Natural Language Processing (EMNLP) (pp. 1524–1536). Association for Computational Linguistics.

Brooke, J. (1996). SUS: A "quick and dirty" usability scale. En P. W. Jordan, B. Thomas, B. A. Weerdmeester, e I. L. McClelland (Eds.), Usability evaluation in industry (pp. 189–194). Taylor & Francis.

Brown, T. B., Mann, B., Ryder, N., Subbiah, M., Kaplan, J., Dhariwal, P., ... y Amodei, D. (2020). Language models are few-shot learners. En Advances in Neural Information Processing Systems (NeurIPS), 33, 1877–1901.

Chang, S., Fosler-Lussier, E., y otros. (2023). Dr.Spider: A diagnostic evaluation benchmark towards text-to-SQL robustness. En Proceedings of the International Conference on Learning Representations (ICLR). [Notable Top-5%].

Dettmers, T., Pagnoni, A., Holtzman, A., y Zettlemoyer, L. (2023). QLoRA: Efficient finetuning of quantized language models. En Advances in Neural Information Processing Systems (NeurIPS), 36.

Eckmann, P., Rai, A., y otros. (2025). Spider-HJ: Human-like reasoning for text-to-SQL. OpenReview. https://openreview.net/pdf?id=NZLm4vzXfm

Hevner, A. R., March, S. T., Park, J., y Ram, S. (2004). Design science in information systems research. MIS Quarterly, 28(1), 75–105.

Hu, E. J., Shen, Y., Wallis, P., Allen-Zhu, Z., Li, Y., Wang, S., Wang, L., y Chen, W. (2022). LoRA: Low-rank adaptation of large language models. En Proceedings of the International Conference on Learning Representations (ICLR).

Kumar, R., y Matthew, T. (2025). Enterprise-grade natural language to SQL generation using LLMs: Balancing accuracy, latency, and scale. AWS Machine Learning Blog. https://aws.amazon.com/blogs/machine-learning/enterprise-grade-natural-language-to-sql-generation-using-llms-balancing-accuracy-latency-and-scale/

Lee, C., Shi, T., Jeon, J., Uppal, A., y otros. (2021). KaggleDBQA: Realistic evaluation of text-to-SQL parsers. En Proceedings of the 59th Annual Meeting of the Association for Computational Linguistics (ACL) (pp. 2261–2273).

Lei, F., y otros. (2024). Spider 2.0: Evaluating language models on real-world enterprise text-to-SQL workflows. En Proceedings of the International Conference on Learning Representations (ICLR). https://spider2-sql.github.io/

Li, B., Zhang, J., Fan, J., Xu, Y., Chen, C., Tang, N., y Luo, Y. (2025). Alpha-SQL: Zero-shot text-to-SQL using Monte Carlo Tree Search. En Proceedings of the 42nd International Conference on Machine Learning (ICML 2025), PMLR 267, 36810–36830.

Li, H., Zhang, J., Li, C., y Chen, H. (2023a). RESDSQL: Decoupling schema linking and skeleton parsing for text-to-SQL. arXiv preprint arXiv:2302.05965.

Li, J., Li, B., Chen, N., Tang, N., y Luo, Y. (2023b). Can LLM already serve as a database interface? A big bench for large-scale database grounded text-to-SQLs. En Advances in Neural Information Processing Systems (NeurIPS), 36.

Liu, X., Shen, S., Li, B., Ma, P., Jiang, R., Zhang, Y., Fan, J., Li, G., Tang, N., y Luo, Y. (2025a). NL2SQL-BUGs: A benchmark for detecting semantic errors in NL2SQL translation. En Proceedings of the 31st ACM SIGKDD Conference on Knowledge Discovery and Data Mining (KDD). arXiv:2503.11984.

Liu, X., Shen, S., Li, B., Tang, N., y Luo, Y. (2025b). A survey of NL2SQL with large language models: Where are we, and where are we going? IEEE Transactions on Knowledge and Data Engineering. arXiv:2408.05109.

Luo, Y., Li, G., Fan, J., Chai, C., y Tang, N. (2025). Natural language to SQL: State of the art and open problems. Proceedings of the VLDB Endowment, 18(12), 5466–5471. https://doi.org/10.14778/3750601.3750696

Pourreza, M., y Rafiei, D. (2023). DIN-SQL: Decomposed in-context learning of text-to-SQL with self-correction. En Advances in Neural Information Processing Systems (NeurIPS), 36.

Pourreza, M., Li, H., Sun, R., Chung, Y., Talaei, S., Kakkar, G. T., Gan, Y., Saberi, A., Ozcan, F., y Arik, S. O. (2024). CHASE-SQL: Multi-path reasoning and preference optimized candidate selection in text-to-SQL. arXiv preprint arXiv:2410.01943.

Yu, T., Zhang, R., Yang, K., Yasunaga, M., Wang, D., Li, Z., ... y Radev, D. (2018). Spider: A large-scale human-labeled dataset for complex and cross-domain semantic parsing and text-to-SQL task. En Proceedings of the 2018 Conference on Empirical Methods in Natural Language Processing (EMNLP) (pp. 3911–3921).


────────────────────────────────────────────────────────────────────────

Universidad Nacional de Colombia — Facultad de Ingeniería — Departamento de Sistemas e Industrial
Período 2026-1S
