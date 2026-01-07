# PROPUESTA DE PROYECTO DE GRADO
## IDI (Interfaz Inteligente de Base de Datos): sistema Contextual NL2SQL para Soporte de Decisiones Ejecutivas

**Programa**: ingeniería de Sistemas y Computación
**Universidad Nacional de Colombia**
**Modalidad**: i (Trabajo de Investigación)

---

## 1. INTRODUCCIÓN

### Información General sobre el Ámbito del Problema

En el panorama empresarial contemporáneo impulsado por datos, las organizaciones acumulan grandes volúmenes de información dentro de sistemas de gestión de bases de datos relacionales (RDBMS). Estos repositorios contienen insights críticos para la toma de decisiones estratégicas, optimización operacional y ventaja competitiva. Sin embargo, persiste una barrera significativa: la experiencia técnica requerida para extraer información significativa mediante el Lenguaje de Consulta Estructurado (SQL) permanece fuera del alcance de la mayoría de ejecutivos y gerentes empresariales.

Estudios indican que aproximadamente el 85% de los tomadores de decisiones organizacionales carecen de competencia en SQL, creando un cuello de botella de dependencia hacia analistas de datos y departamentos de TI para consultas rutinarias de datos. Esta brecha técnica se manifiesta en varias ineficiencias organizacionales: latencia en decisiones (decisiones estratégicas retrasadas horas o días esperando ejecución técnica de consultas), asignación inadecuada de recursos (profesionales altamente calificados ocupados con tareas rutinarias de reportes), y costo de oportunidad (pivotes estratégicos en tiempo real imposibles debido a restricciones de acceso a datos).

La emergencia de Modelos de Lenguaje de Gran Escala (LLMs) y tecnologías de Procesamiento de Lenguaje Natural (NLP) ofrece oportunidades sin precedentes para cerrar esta brecha mediante sistemas de Lenguaje Natural a SQL (NL2SQL). Estos sistemas prometen democratizar el acceso a bases de datos traduciendo consultas conversacionales en sentencias SQL ejecutables, eliminando efectivamente la barrera técnica que separa la intuición empresarial de la validación con datos.

### Problema: situación Actual y Situación Deseada

**Situación Actual**: los ejecutivos y gerentes sin conocimientos técnicos en SQL enfrentan barreras significativas para acceder a bases de datos complejas y extraer insights estadísticos necesarios para la toma de decisiones. Actualmente, deben depender de intermediarios técnicos (analistas de datos, departamentos de TI) para formular y ejecutar consultas, lo que resulta en demoras de horas o días, malinterpretaciones de requerimientos, y pérdida de agilidad estratégica.

**Situación Deseada**: un sistema que permita a usuarios no técnicos interactuar con bases de datos relacionales mediante lenguaje natural conversacional, obteniendo resultados precisos, verificados y visualmente interpretables en segundos, sin necesidad de intermediarios técnicos ni conocimiento de SQL. El sistema debe ser accesible, confiable, y capaz de manejar la ambigüedad inherente al lenguaje natural mientras garantiza la corrección de las consultas generadas.

### Objetivos

Este proyecto propone el diseño, desarrollo y evaluación de IDI (Interfaz Inteligente de Base de Datos), un sistema NL2SQL integral adaptado para soporte de decisiones ejecutivas, con arquitectura modular de múltiples agentes que incluye: adquisición contextual de conocimiento de dominio, resolución de ambigüedad mediante interfaces guiadas, generación de SQL con verificación multi-capa, visualización automática, y gestión de sesiones para continuidad investigativa.

### Metodología

El proyecto seguirá una metodología de Investigación en Ciencias del Diseño (Design Science Research - DSR), enfatizando la creación y evaluación de artefactos a través de cuatro fases de 4 semanas cada una: (1) análisis de requerimientos mediante revisión de literatura, análisis competitivo y selección de benchmarks; (2) diseño del sistema con especificación de arquitectura modular, selección de stack tecnológico y diseño de esquemas; (3) desarrollo de la solución con implementación de siete módulos centrales, fine-tuning de modelos LLM y desarrollo de interfaz web; y (4) análisis de resultados mediante evaluación cuantitativa en benchmarks, estudios de usuario y análisis comparativo.

### Breve Descripción del Contenido del Proyecto

El sistema IDI integra siete módulos especializados orquestados mediante flujos de trabajo agénticos: (1) agente gestor de contexto que adquiere y mantiene conocimiento de dominio específico de la empresa; (2) agente de comprensión de consultas que analiza lenguaje natural y detecta ambigüedades; (3) agente generador de SQL que traduce intención estructurada en SQL ejecutable; (4) agente de verificación que valida corrección mediante verificación de tres capas; (5) motor de visualización que renderiza automáticamente insights estadísticos; (6) agente gestor de sesiones que guarda y administra contextos de consulta para continuidad investigativa; y (7) orquestador multi-agente que coordina enrutamiento dinámico de flujo de trabajo. El proyecto enfatiza consideraciones prácticas de despliegue incluyendo restricciones de recursos (ejecución local en hardware de consumo), eficiencia de costos (dependencia mínima de nube), y extensibilidad (arquitectura modular habilitando evolución de componentes).

---

## 2. JUSTIFICACIÓN

### ¿Por Qué Hay que Hacer el Proyecto?

Este proyecto aborda una necesidad crítica y creciente en el ecosistema empresarial moderno: la democratización del acceso a datos para la toma de decisiones informadas. La brecha existente entre la intuición estratégica de los ejecutivos y su capacidad técnica para validar hipótesis con datos representa un freno significativo a la agilidad organizacional. La implementación de un sistema NL2SQL robusto, verificado y accesible puede transformar fundamentalmente cómo las organizaciones aprovechan sus activos de datos, eliminando intermediarios técnicos y reduciendo ciclos de toma de decisiones de días a segundos.

### Importancia

**Relevancia Práctica**: aproximadamente 2.5 millones de nuevos gerentes ingresan a la fuerza laboral anualmente en América Latina, la mayoría careciendo de habilidades técnicas de bases de datos. IDI habilita a este demográfico para validar independientemente hipótesis estratégicas con datos organizacionales, reduciendo la latencia de decisiones de días a segundos. Las organizaciones gastan en promedio el 30% del tiempo de analistas de datos en consultas rutinarias de reportes que podrían automatizarse, permitiendo reasignar estos recursos a tareas analíticas de alto valor como modelado predictivo e inferencia causal. El acceso a datos en tiempo real habilita adaptación ágil de estrategia, con estudios mostrando que reducir ciclos de toma de decisiones en 50% se correlaciona con crecimiento de ingresos del 15-20% en mercados volátiles.

**Contribución Académica**: el proyecto introduce un marco novedoso de adquisición de contexto mediante encuestas estructuradas, creando repositorios de contexto reutilizables para despliegue empresarial. Combina diseño de interfaces guiadas por palabras clave (reduciendo espacio de entrada) con clarificación conversacional (manejando ambigüedad residual), un enfoque poco estudiado que conecta Interacción Humano-Computadora (HCI) con NLP. Extiende la verificación más allá de chequeo sintáctico hacia pruebas de equivalencia semántica y validación de cordura de resultados, abordando la brecha de confiabilidad identificada en investigaciones recientes. Demuestra la factibilidad de NL2SQL de grado empresarial en hardware de consumo mediante descomposición modular, desafiando la suposición prevalente de que la precisión requiere modelos masivos.

### Interés del Estudiante

Como estudiante de Ingeniería de Sistemas y Computación, este proyecto representa la convergencia de múltiples áreas de interés personal: inteligencia artificial aplicada, arquitecturas de sistemas distribuidos, optimización de recursos computacionales, y diseño de experiencia de usuario. La oportunidad de trabajar en la frontera de tecnologías de LLMs mientras resolviendo un problema práctico tangible que impacta directamente la eficiencia organizacional es altamente motivante. Adicionalmente, el proyecto ofrece exposición profunda a técnicas estado del arte en NLP, fine-tuning de modelos, y diseño de sistemas multi-agente, habilidades altamente demandadas en la industria actual.

### Grado de Novedad

El proyecto presenta múltiples elementos novedosos: (1) marco sistemático de adquisición de conocimiento de dominio mediante encuestas estructuradas, no explorado en profundidad en literatura NL2SQL existente; (2) arquitectura híbrida de resolución de ambigüedad combinando restricción de interfaz con diálogo clarificatorio; (3) pipeline de verificación multi-capa (sintaxis + semántica + cordura de resultados) proporcionando garantías de corrección más robustas que sistemas actuales; (4) gestión de sesiones con preservación completa de contexto investigativo para continuidad analítica; (5) demostración de que modelos especializados ligeros (7-13B parámetros) con fine-tuning pueden rivalizar con modelos monolíticos grandes en tareas NL2SQL específicas de dominio, habilitando despliegue local rentable.

### Necesidad Humana que se Satisface

El proyecto satisface la necesidad fundamental de acceso democrático al conocimiento contenido en bases de datos organizacionales. Actualmente, la información valiosa está efectivamente bloqueada para la mayoría de trabajadores del conocimiento debido a barreras técnicas. IDI elimina esta barrera, permitiendo que gerentes, ejecutivos, analistas de negocio y otros profesionales no técnicos formulen preguntas en su lenguaje natural y obtengan respuestas verificadas inmediatamente. Esto no solo mejora la eficiencia operacional sino que empodera a individuos para tomar decisiones informadas, fomenta la alfabetización en datos, y promueve una cultura organizacional más analítica y basada en evidencia.

### Beneficios y Beneficiados

**Beneficiarios Directos**:
- **Ejecutivos y Gerentes**: acceso inmediato a insights de datos sin dependencia de TI, habilitando decisiones estratégicas más rápidas y basadas en datos
- **Analistas de Datos**: liberación de tareas rutinarias de generación de reportes, permitiendo enfoque en análisis complejo de alto valor
- **Organizaciones**: reducción de costos operacionales, mejora en agilidad de toma de decisiones, y ventaja competitiva mediante aprovechamiento más efectivo de activos de datos

**Beneficiarios Indirectos**:
- **Estudiantes e Investigadores**: plataforma de código abierto para experimentación en NL2SQL y arquitecturas multi-agente
- **Comunidad Académica**: contribuciones metodológicas y empíricas avanzando el estado del arte en interfaces de lenguaje natural para bases de datos
- **Sector Tecnológico Colombiano**: demostración de capacidad local para desarrollar soluciones de IA aplicada competitivas internacionalmente

### Mercado

El mercado global de herramientas de inteligencia de negocios (BI) y analítica alcanzó $27.11 mil millones en 2022 y se proyecta crecer a $54.27 mil millones para 2030 (CAGR del 9.1%). Dentro de este mercado, las interfaces de lenguaje natural representan un segmento de rápido crecimiento, con el 78% de proveedores de bases de datos empresariales planeando integración NL2SQL para 2026. Sin embargo, soluciones actuales son predominantemente propietarias, basadas en nube, y costosas, creando oportunidad para alternativas de código abierto, desplegables localmente. El mercado objetivo inicial incluye: (1) PYMEs en América Latina buscando capacidades analíticas sin inversión en infraestructura costosa; (2) Departamentos gubernamentales requiriendo soberanía de datos y despliegue on-premise; (3) Instituciones educativas buscando herramientas pedagógicas para enseñanza de bases de datos e IA. El potencial de escalamiento incluye adaptación a dominios especializados (salud, finanzas, logística) mediante personalización del marco de adquisición de contexto.

---

## 3. OBJETIVO GENERAL

**Diseñar, desarrollar y evaluar IDI (Interfaz Inteligente de Base de Datos), un sistema NL2SQL modular multi-agente que permite a ejecutivos no técnicos extraer insights estadísticos de bases de datos relacionales mediante consultas conversacionales en lenguaje natural con conciencia contextual, resolución de ambigüedad, verificación automatizada y continuidad investigativa basada en sesiones, alcanzando >90% de corrección de consultas mientras opera en hardware de consumo local con comunicación transparente de progreso para tiempos de procesamiento extendidos (hasta 30 segundos), con el propósito de democratizar el acceso a datos organizacionales y habilitar toma de decisiones ágil basada en evidencia.**

---

## 4. OBJETIVOS ESPECÍFICOS

### Objetivo Específico 1: análisis de Requerimientos

**Conducir análisis integral de requerimientos para un sistema NL2SQL enfocado en ejecutivos, identificando requerimientos funcionales y no funcionales, criterios de éxito y métricas de evaluación mediante revisión de literatura, análisis competitivo y evaluación de necesidades de stakeholders.**

### Objetivo Específico 2: diseño del Sistema

**Diseñar la arquitectura modular de IDI, especificando responsabilidades de componentes, protocolos de comunicación inter-agente, flujos de datos, mecanismos de gestión de sesiones, estrategias de comunicación de progreso, y selección de stack tecnológico optimizado para despliegue local en hardware de consumo (16GB RAM, 8GB VRAM) con timeouts de consulta extendidos (hasta 30 segundos).**

### Objetivo Específico 3: desarrollo de la Solución

**Implementar los siete módulos centrales de IDI (Gestor de Contexto, Comprensión de Consultas, Generador SQL, Agente de Verificación, Motor de Visualización, Gestor de Sesiones, Orquestador Multi-Agente) con generación de datos sintéticos de entrenamiento, pipelines de fine-tuning de modelos, gestión de flujo conversacional y componentes de interfaz de usuario incluyendo indicadores de progreso y controles de sesión.**

### Objetivo Específico 4: análisis de Resultados

**Evaluar el desempeño de IDI mediante benchmarking cuantitativo (precisión de ejecución, latencia, efectividad de verificación, patrones de uso de sesiones) y evaluación cualitativa (estudio de usuario con tareas multi-turno, revisión experta, efectividad de indicadores de progreso), comparando resultados contra métodos baseline e identificando oportunidades de mejora.**

---

## 5. ANTECEDENTES

### Antecedentes Locales

En Colombia, la adopción de sistemas de análisis de datos ha crecido significativamente en la última década, particularmente en sectores financiero, salud y retail. Sin embargo, la mayoría de organizaciones colombianas todavía dependen de soluciones propietarias internacionales (Tableau, Power BI) con costos de licenciamiento significativos y dependencia de conectividad a nube. La Universidad Nacional de Colombia ha desarrollado investigación en procesamiento de lenguaje natural para español, particularmente en el grupo de investigación MindLab, pero aplicaciones específicas a interfaces de bases de datos permanecen limitadas. Este proyecto representa una oportunidad para desarrollar capacidad local en esta área emergente, adaptada a necesidades y restricciones del contexto latinoamericano.

### Antecedentes Regionales

En América Latina, iniciativas de transformación digital gubernamental y empresarial han identificado el acceso democrático a datos como prioridad estratégica. Países como Brasil y México han invertido en plataformas de datos abiertos con interfaces de consulta, pero predominantemente mediante formularios estructurados en lugar de lenguaje natural. La brecha de habilidades técnicas es particularmente pronunciada en la región, con estudios mostrando que solo el 12% de gerentes en PYMEs latinoamericanas tienen capacitación formal en análisis de datos. Esto crea tanto necesidad urgente como oportunidad de mercado significativa para soluciones que reduzcan barreras técnicas de acceso a datos.

### Antecedentes Nacionales

El Plan Nacional de Desarrollo 2022-2026 de Colombia prioriza transformación digital y gobernanza basada en datos. IDI se alinea directamente con estos objetivos mediante: (1) transformación Productiva: habilitando PYMEs para aprovechar analítica de datos sin contratar personal especializado; (2) desarrollo de Capital Humano: entrenando ingenieros de próxima generación en intersección estado del arte de IA/bases de datos; (3) soberanía Tecnológica: desarrollando soluciones localmente adaptables reduciendo dependencia de plataformas SaaS extranjeras. Adicionalmente, instituciones como el Ministerio de Tecnologías de la Información y las Comunicaciones (MinTIC) han promovido iniciativas de alfabetización digital y datos abiertos que se beneficiarían de herramientas de acceso más intuitivas.

### Antecedentes Internacionales

Internacionalmente, el campo NL2SQL ha evolucionado a través de cuatro eras paradigmáticas: (1) era de Modelos de Lenguaje Estadístico (1990s-2016) con sistemas basados en reglas y aproximaciones N-gram; (2) era de Modelos de Lenguaje Neural (2017-2018) con introducción de LSTMs y mecanismos de atención, culminando en el benchmark seminal Spider; (3) era de Modelos de Lenguaje Pre-entrenados (2018-2023) con modelos basados en Transformers (BERT, T5) elevando precisión a 70-80% en benchmarks complejos; y (4) era de Modelos de Lenguaje de Gran Escala (2023-Presente) con modelos como GPT-4, Claude y LLaMA demostrando >95% de precisión en tareas específicas de dominio cuando apropiadamente contextualizados.

Trabajos recientes particularmente relevantes incluyen: (1) Luo et al. (2025) proporcionando la taxonomía más comprensiva de técnicas NL2SQL contemporáneas; (2) Kumar et al. (2025) presentando arquitectura probada en producción para NL2SQL empresarial a escala AWS-Cisco con enfoque en promptos con alcance de dominio, pre-resolución de identificadores y abstracciones de datos; (3) Li et al. (2025) con Alpha-SQL demostrando frameworks zero-shot combinando LLMs con Monte Carlo Tree Search para planificación autónoma de flujo de trabajo; y (4) Pourreza et al. (2024) con CHASE-SQL explorando descomposición basada en agentes con agentes especializados para poda de esquema, generación de candidatos y ranking basado en ejecución.

A pesar de estos avances, el despliegue empresarial permanece desafiante debido a brechas de conocimiento de dominio, complejidad de esquemas, manejo de ambigüedad y preocupaciones de confiabilidad, desafíos que IDI específicamente aborda mediante arquitectura modular y conciencia contextual.

---

## 6. METODOLOGÍA

### Objetivo Específico 1: análisis de Requerimientos

**Tarea A: revisión de Literatura y Análisis Competitivo**
- Realizar inmersión profunda en papers recientes de NL2SQL (Luo et al., Li et al., Kumar et al.)
- Analizar soluciones comerciales (Tableau Ask Data, Power BI Q&A, AWS Athena NL)
- Documentar fortalezas, debilidades y brechas identificadas
- Crear matriz de características competitivas comparando 5+ soluciones existentes

**Tarea B: selección y Análisis de Conjuntos de Datos Benchmark**
- Descargar y analizar benchmarks Spider, BIRD y específicos de dominio
- Evaluar características de datasets (tamaño, complejidad, diversidad de dominio)
- Seleccionar benchmarks primarios y secundarios para evaluación
- Crear conjunto de prueba personalizado de consultas específicas para ejecutivos (50-100 consultas)

**Tarea C: especificación de Requerimientos y Definición de Métricas**
- Definir requerimientos funcionales por módulo
- Definir requerimientos no funcionales (desempeño, usabilidad, escalabilidad)
- Especificar métricas de éxito con umbrales cuantitativos
- Crear personas de usuario y escenarios de casos de uso detallados

### Objetivo Específico 2: diseño del Sistema

**Tarea A: diseño de Arquitectura y Especificación de Módulos**
- Diseñar arquitectura del sistema de alto nivel (diagrama de componentes)
- Especificar interfaces de módulos (contratos API)
- Diseñar flujos de datos entre componentes (diagramas de secuencia)
- Documentar patrones de diseño y decisiones arquitectónicas

**Tarea B: selección y Justificación de Stack Tecnológico**
- Evaluar candidatos LLM (benchmark en consultas de muestra)
- Comparar opciones de frameworks (LangChain vs. LangGraph vs. personalizado)
- Probar impacto de cuantización en precisión (4-bit vs. 8-bit vs. FP16)
- Prototipar inferencia en hardware objetivo (medir uso de VRAM, latencia)

**Tarea C: diseño de Encuesta de Adquisición de Contexto y Esquema de Base de Datos**
- Diseñar encuesta de onboarding (estructura de preguntas, lógica de ramificación)
- Crear esquema para almacenamiento de contexto (BD vectorial + registro de metadatos)
- Diseñar plantilla de ejemplos few-shot y formato de almacenamiento
- Planificar pipeline de generación de datos sintéticos

### Objetivo Específico 3: desarrollo de la Solución

**Tarea A: infraestructura Central y Gestor de Contexto**
- Configurar estructura de repositorio de proyecto
- Implementar conexiones de base de datos (PostgreSQL/SQLite)
- Desarrollar agente gestor de contexto (integración BD vectorial, pipeline de generación de embeddings, recuperación de contexto con búsqueda de similitud)
- Implementar lógica de procesamiento de encuestas

**Tarea B: agentes de Comprensión de Consultas y Generación SQL**
- Implementar agente de comprensión de consultas (NER para extracción de entidades, clasificación de intención, reglas de detección de ambigüedad, generación de preguntas clarificatorias)
- Implementar agente generador de SQL (diseño de plantilla de prompt, pipeline de inferencia LLM, decodificación restringida)
- Generar datos sintéticos de entrenamiento (500-1000 ejemplos)
- Realizar fine-tuning de modelos usando QLoRA

**Tarea C: verificación, Visualización, Gestor de Sesiones y Orquestación**
- Implementar agente de verificación (tres capas: validador sintáctico, verificador de equivalencia semántica, verificador de cordura de resultados)
- Implementar motor de visualización (lógica de selección de tipo de gráfico, integración con Recharts)
- Implementar agente gestor de sesiones (almacenamiento PostgreSQL con JSONB, operaciones guardar/cargar/listar/eliminar/exportar)
- Implementar orquestador multi-agente (definición de flujo de trabajo LangGraph, gestión de estado con soporte multi-turno, rastreo de progreso y actualizaciones WebSocket)
- Desarrollar interfaz web (constructor de consultas guiado por palabras clave, panel de visualización, indicadores de progreso, controles de sesión)

### Objetivo Específico 4: análisis de Resultados

**Tarea A: evaluación Cuantitativa y Benchmarking**
- Ejecutar evaluación de benchmarks (Spider, BIRD, conjunto de prueba personalizado)
- Medir métricas cuantitativas (Precisión de Ejecución, Precisión de Coincidencia Exacta, Latencia, Utilización de recursos)
- Realizar estudios de ablación (remover módulos, medir impacto)
- Comparar contra métodos baseline (herramientas comerciales, benchmarks académicos)

**Tarea B: estudio de Usuario y Evaluación Cualitativa**
- Diseñar protocolo de estudio de usuario (tareas, cuestionarios)
- Reclutar 10-15 participantes (profesores, gerentes de negocios locales si es factible)
- Conducir sesiones de evaluación basadas en tareas
- Administrar cuestionario System Usability Scale (SUS)
- Recolectar retroalimentación cualitativa (entrevistas, respuestas abiertas)
- Revisión experta: administradores de bases de datos evalúan calidad SQL

**Tarea C: documentación de Tesis y Presentación Final**
- Escribir capítulos de tesis (Introducción, Antecedentes, Metodología, Resultados, Discusión, Conclusiones)
- Finalizar todos los diagramas y figuras
- Revisar y pulir basándose en retroalimentación del asesor
- Preparar diapositivas de presentación final
- Crear video de demostración mostrando capacidades del sistema

---

## 7. RECURSOS

Para el desarrollo de este proyecto, se requieren los siguientes recursos:

### Recursos Humanos
- **Estudiante**: dedicación de 20-25 horas semanales durante 16 semanas para investigación, desarrollo e implementación del sistema
- **Computador personal**: equipo con especificaciones mínimas de 16GB RAM, 8GB VRAM (GPU NVIDIA RTX 3060/3070 o equivalente), CPU moderno multi-núcleo

### Recursos Tecnológicos
- **Acceso a Internet**: conexión estable para descarga de modelos pre-entrenados, datasets de benchmark, consulta de documentación y búsqueda bibliográfica
- **Software de código abierto**: python 3.11+, librerías ML/NLP (Transformers, LangChain, ChromaDB, SQLAlchemy), frameworks web (FastAPI, React), herramientas de desarrollo (VS Code, Git)

### Recursos Académicos
- **Literatura científica**: acceso a bases de datos académicas (IEEE Xplore, ACM Digital Library, arXiv) mediante suscripciones institucionales de la Universidad Nacional
- **Datasets de benchmark**: conjuntos públicos de datos NL2SQL (Spider, BIRD) disponibles gratuitamente

**Nota**: el proyecto se ha diseñado específicamente para ser desarrollable con recursos mínimos, priorizando software de código abierto, modelos localmente desplegables y hardware de consumo accesible, eliminando dependencias de infraestructura costosa o servicios de nube de pago.

---

## 8. CRONOGRAMA DE ACTIVIDADES

### Fase 1: Análisis de Requerimientos (Semanas 1-4)

| Actividad | Semanas | Entregable |
|-----------|---------|------------|
| Revisión de literatura y análisis competitivo | 1-2 | Documento resumen estado del arte (10-15 páginas) |
| Selección y análisis de datasets benchmark | 2-3 | Documento justificación selección de benchmarks |
| Especificación de requerimientos y definición de métricas | 3-4 | Especificación de Requerimientos de Software (15-20 páginas) |

### Fase 2: Diseño del Sistema (Semanas 5-8)

| Actividad | Semanas | Entregable |
|-----------|---------|------------|
| Diseño de arquitectura y especificación de módulos | 5-6 | Documento arquitectura con diagramas UML |
| Selección y justificación de stack tecnológico | 6-7 | Documento justificación tecnológica con benchmarks preliminares |
| Diseño de encuesta de contexto y esquema de BD | 7-8 | Encuesta final + diseño de esquema de base de datos |

### Fase 3: Desarrollo de la Solución (Semanas 9-12)

| Actividad | Semanas | Entregable |
|-----------|---------|------------|
| Infraestructura central y Gestor de Contexto | 9 | Módulo Gestor de Contexto funcional con pruebas |
| Agentes de Comprensión de Consultas y Generación SQL | 10-11 | Agentes funcionales + dataset sintético + modelos fine-tuned |
| Verificación, Visualización, Sesiones y Orquestación | 11-12 | Sistema prototipo completo funcional con interfaz web |

### Fase 4: Análisis de Resultados (Semanas 13-16)

| Actividad | Semanas | Entregable |
|-----------|---------|------------|
| Evaluación cuantitativa y benchmarking | 13-14 | Reporte de evaluación de desempeño (10-15 páginas) |
| Estudio de usuario y evaluación cualitativa | 14-15 | Resultados de estudio de usuario + reporte SUS |
| Documentación de tesis y presentación final | 15-16 | Documento de tesis completo (100-120 páginas) + presentación |

---

## 9. RESULTADOS ESPERADOS

### Resultado Esperado 1 (Objetivo Específico 1: análisis de Requerimientos)

**Documento integral de especificación de requerimientos** que identifique clara y completamente los requerimientos funcionales y no funcionales del sistema IDI, incluyendo: (1) especificación detallada de responsabilidades, entradas y salidas de cada uno de los siete módulos del sistema; (2) definición cuantitativa de métricas de éxito con umbrales específicos (>90% precisión de ejecución, <30s latencia para consultas complejas, SUS >70); (3) selección justificada de datasets de benchmark primarios y secundarios; (4) conjunto de prueba personalizado de 50-100 consultas representativas de necesidades ejecutivas; y (5) personas de usuario y escenarios de casos de uso detallados. Este documento proporcionará la base sólida para todas las fases subsecuentes del proyecto, asegurando alineación entre diseño, implementación y evaluación.

### Resultado Esperado 2 (Objetivo Específico 2: diseño del Sistema)

**Diseño arquitectónico completo y validado del sistema IDI** que especifique: (1) arquitectura modular de siete componentes con diagramas UML de componentes, despliegue y secuencia mostrando separación clara de responsabilidades y flujos de datos; (2) especificaciones de interfaces de módulos con contratos API tipo-seguros para cada agente; (3) stack tecnológico seleccionado y justificado mediante benchmarks empíricos comparando alternativas de modelos LLM, frameworks de orquestación, y técnicas de cuantización; (4) diseño de encuesta de adquisición de contexto con estructura de preguntas validada; (5) esquemas de almacenamiento para base de datos vectorial, registro de metadatos y gestión de sesiones; (6) estrategias de comunicación de progreso y manejo de timeouts extendidos. Este diseño garantizará factibilidad técnica antes de iniciar implementación, minimizando riesgos de integración.

### Resultado Esperado 3 (Objetivo Específico 3: desarrollo de la Solución)

**Sistema prototipo IDI completamente funcional** que integre los siete módulos centrales con las siguientes características demostrables: (1) capacidad de procesar consultas en lenguaje natural end-to-end, desde entrada de usuario hasta visualización de resultados; (2) gestión de conversaciones multi-turno con preservación de contexto, permitiendo consultas de seguimiento y refinamiento basado en retroalimentación; (3) generación de SQL sintácticamente válido y semánticamente correcto para >85% de consultas de prueba; (4) verificación automática multi-capa detectando >90% de errores con <10% falsos positivos; (5) selección automática de visualizaciones apropiadas (gráficos de línea, barras, pie, etc.) basada en características de resultados; (6) funcionalidad completa de gestión de sesiones (guardar, cargar, buscar, exportar investigaciones); (7) indicadores de progreso en tiempo real con capacidad de cancelación para consultas de procesamiento extendido; y (8) interfaz web intuitiva accesible para usuarios no técnicos. El sistema incluirá suite de pruebas unitarias e integración con >80% cobertura de código.

### Resultado Esperado 4 (Objetivo Específico 4: análisis de Resultados)

**Evaluación exhaustiva del sistema IDI con evidencia cuantitativa y cualitativa** que demuestre: (1) reporte de desempeño cuantitativo mostrando precisión de ejecución >85% en conjunto de prueba de dominio específico, latencia promedio <5 segundos para consultas simples y <30 segundos para consultas complejas, y efectividad de verificación >95% detección de errores; (2) resultados de estudios de usuario mostrando tasa de éxito de tareas >75%, puntaje SUS >70 (usabilidad "buena"), y confianza de usuario promedio >4/5; (3) análisis comparativo contra soluciones baseline (herramientas comerciales, métodos académicos) demostrando competitividad en precisión con ventajas en eficiencia de costos, resolución de ambigüedad y robustez de verificación; (4) estudios de ablación cuantificando contribución individual de cada módulo al desempeño general; (5) análisis de patrones de uso de sesiones y efectividad de indicadores de progreso; y (6) identificación de limitaciones actuales y recomendaciones concretas para trabajo futuro. Estos resultados proporcionarán validación rigurosa de hipótesis de investigación y contribuciones del proyecto.

---

## 10. BIBLIOGRAFÍA

### Libros

1. Hevner, A. R., March, S. T., Park, J., & Ram, S. (2004). *Design Science in Information Systems Research*. MIS Quarterly, 28(1), 75-105.

2. Zelle, M., & Mooney, R. J. (1996). *Learning to Parse Database Queries Using Inductive Logic Programming*. In Proceedings of the Thirteenth National Conference on Artificial Intelligence (pp. 1050-1055).

### Artículos Científicos

1. **Luo, Y., Li, G., Fan, J., Chai, C., & Tang, N. (2025).** Natural Language to SQL: State of the Art and Open Problems. *Proceedings of the VLDB Endowment*, 18(12), 5466-5471. https://doi.org/10.14778/3750601.3750696
   *[Taxonomía comprehensiva de técnicas NL2SQL contemporáneas, identificando cinco niveles de dificultad y situando investigación actual]*

2. **Kumar, R., Fotherby, T., Keshavanarayana, S., Matthew, T., Vaquero, D., Varshneya, A., & Wu, J. (2025).** Enterprise-grade Natural Language to SQL Generation Using LLMs: Balancing Accuracy, Latency, and Scale. *AWS Machine Learning Blog*. Retrieved from https://aws.amazon.com/blogs/machine-learning/
   *[Arquitectura probada en producción AWS-Cisco con promptos con alcance de dominio, pre-resolución de identificadores y abstracciones de datos]*

3. **Li, B., Zhang, J., Fan, J., Xu, Y., Chen, C., Tang, N., & Luo, Y. (2025).** Alpha-SQL: Zero-shot Text-to-SQL Using Monte Carlo Tree Search. *arXiv preprint arXiv:2502.17248*.
   *[Framework zero-shot combinando LLMs con MCTS para planificación autónoma de flujo de trabajo]*

4. **Pourreza, M., Li, H., Sun, R., Chung, Y., Talaei, S., Kakkar, G. T., ... & Arik, S. O. (2024).** CHASE-SQL: Multi-path Reasoning and Preference Optimized Candidate Selection in Text-to-SQL. *arXiv preprint arXiv:2410.01943*.
   *[Descomposición basada en agentes con agentes especializados para poda de esquema, generación de candidatos y ranking basado en ejecución]*

5. **Brown, T. B., Mann, B., Ryder, N., Subbiah, M., Kaplan, J., Dhariwal, P., ... & Amodei, D. (2020).** Language Models are Few-shot Learners. *Advances in Neural Information Processing Systems*, 33, 1877-1901.
   *[Introducción de capacidades de in-context learning de LLMs habilitando NL2SQL few-shot]*

6. **Yu, T., Zhang, R., Yang, K., Yasunaga, M., Wang, D., Li, Z., ... & Radev, D. (2018).** Spider: A Large-scale Human-labeled Dataset for Complex and Cross-domain Semantic Parsing and Text-to-SQL Task. In *Proceedings of the 2018 Conference on Empirical Methods in Natural Language Processing* (pp. 3911-3921).
   *[Benchmark seminal estableciendo evaluación estandarizada cross-domain para NL2SQL]*

7. **Wei, J., Wang, X., Schuurmans, D., Bosma, M., Ichter, B., Xia, F., ... & Zhou, D. (2022).** Chain-of-thought Prompting Elicits Reasoning in Large Language Models. *Advances in Neural Information Processing Systems*, 35, 24824-24837.
   *[Generación de pasos de razonamiento intermedios mejorando manejo de consultas complejas en NL2SQL]*

8. **Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., ... & Polosukhin, I. (2017).** Attention is All You Need. *Advances in Neural Information Processing Systems*, 30, 5998-6008.
   *[Arquitectura Transformer fundamental para modelos NL2SQL basados en atención]*

### Referencias Adicionales

9. **Li, J., Hui, B., Cheng, R., Qin, B., Ma, C., Huo, N., ... & Li, Y. (2023).** Can LLM Already Serve as a Database Interface? A BIg Bench for Large-scale Database Grounded Text-to-SQLs. *arXiv preprint arXiv:2305.03111*.
   *[Benchmark BIRD para evaluación de NL2SQL a escala empresarial con esquemas complejos]*

10. **Gartner Research (2023).** Market Trends: Business Intelligence and Analytics. *Gartner Inc.*
    *[Análisis de mercado mostrando 30% de tiempo de analistas en consultas rutinarias automatizables]*

11. **McKinsey & Company (2024).** The Data-Driven Enterprise. *McKinsey Global Institute*.
    *[Correlación entre reducción de ciclos de decisión (50%) y crecimiento de ingresos (15-20%)]*

12. **International Labour Organization - ILO (2024).** Labour Market Statistics for Latin America. *ILO Regional Office*.
    *[Estadísticas sobre 2.5 millones de nuevos gerentes anuales en América Latina]*

---

**Fecha**: noviembre 2024
**Estudiante**: [Tu Nombre]
**Asesor Propuesto**: [Nombre del Asesor]
**Programa**: ingeniería de Sistemas y Computación
**Universidad Nacional de Colombia**
# PROPUESTA DE PROYECTO DE GRADO
## IDI (Interfaz Inteligente de Base de Datos): Sistema Contextual NL2SQL para Soporte de Decisiones Ejecutivas

**Programa**: Ingeniería de Sistemas y Computación
**Universidad Nacional de Colombia**
**Modalidad**: I (Trabajo de Investigación)

---

## 1. INTRODUCCIÓN

### Información General sobre el Ámbito del Problema

En el panorama empresarial contemporáneo impulsado por datos, las organizaciones acumulan grandes volúmenes de información dentro de sistemas de gestión de bases de datos relacionales (RDBMS). Estos repositorios contienen insights críticos para la toma de decisiones estratégicas, optimización operacional y ventaja competitiva. Sin embargo, persiste una barrera significativa: la experiencia técnica requerida para extraer información significativa mediante el Lenguaje de Consulta Estructurado (SQL) permanece fuera del alcance de la mayoría de ejecutivos y gerentes empresariales.

Estudios indican que aproximadamente el 85% de los tomadores de decisiones organizacionales carecen de competencia en SQL, creando un cuello de botella de dependencia hacia analistas de datos y departamentos de TI para consultas rutinarias de datos. Esta brecha técnica se manifiesta en varias ineficiencias organizacionales: latencia en decisiones (decisiones estratégicas retrasadas horas o días esperando ejecución técnica de consultas), asignación inadecuada de recursos (profesionales altamente calificados ocupados con tareas rutinarias de reportes), y costo de oportunidad (pivotes estratégicos en tiempo real imposibles debido a restricciones de acceso a datos).

La emergencia de Modelos de Lenguaje de Gran Escala (LLMs) y tecnologías de Procesamiento de Lenguaje Natural (NLP) ofrece oportunidades sin precedentes para cerrar esta brecha mediante sistemas de Lenguaje Natural a SQL (NL2SQL). Estos sistemas prometen democratizar el acceso a bases de datos traduciendo consultas conversacionales en sentencias SQL ejecutables, eliminando efectivamente la barrera técnica que separa la intuición empresarial de la validación con datos.

### Problema: Situación Actual y Situación Deseada

**Situación Actual**: Los ejecutivos y gerentes sin conocimientos técnicos en SQL enfrentan barreras significativas para acceder a bases de datos complejas y extraer insights estadísticos necesarios para la toma de decisiones. Actualmente, deben depender de intermediarios técnicos (analistas de datos, departamentos de TI) para formular y ejecutar consultas, lo que resulta en demoras de horas o días, malinterpretaciones de requerimientos, y pérdida de agilidad estratégica.

**Situación Deseada**: Un sistema que permita a usuarios no técnicos interactuar con bases de datos relacionales mediante lenguaje natural conversacional, obteniendo resultados precisos, verificados y visualmente interpretables en segundos, sin necesidad de intermediarios técnicos ni conocimiento de SQL. El sistema debe ser accesible, confiable, y capaz de manejar la ambigüedad inherente al lenguaje natural mientras garantiza la corrección de las consultas generadas.

### Objetivos

Este proyecto propone el diseño, desarrollo y evaluación de IDI (Interfaz Inteligente de Base de Datos), un sistema NL2SQL integral adaptado para soporte de decisiones ejecutivas, con arquitectura modular de múltiples agentes que incluye: adquisición contextual de conocimiento de dominio, resolución de ambigüedad mediante interfaces guiadas, generación de SQL con verificación multi-capa, visualización automática, y gestión de sesiones para continuidad investigativa.

### Metodología

El proyecto seguirá una metodología de Investigación en Ciencias del Diseño (Design Science Research - DSR), enfatizando la creación y evaluación de artefactos a través de cuatro fases de 4 semanas cada una: (1) Análisis de Requerimientos mediante revisión de literatura, análisis competitivo y selección de benchmarks; (2) Diseño del Sistema con especificación de arquitectura modular, selección de stack tecnológico y diseño de esquemas; (3) Desarrollo de la Solución con implementación de siete módulos centrales, fine-tuning de modelos LLM y desarrollo de interfaz web; y (4) Análisis de Resultados mediante evaluación cuantitativa en benchmarks, estudios de usuario y análisis comparativo.

### Breve Descripción del Contenido del Proyecto

El sistema IDI integra siete módulos especializados orquestados mediante flujos de trabajo agénticos: (1) Agente Gestor de Contexto que adquiere y mantiene conocimiento de dominio específico de la empresa; (2) Agente de Comprensión de Consultas que analiza lenguaje natural y detecta ambigüedades; (3) Agente Generador de SQL que traduce intención estructurada en SQL ejecutable; (4) Agente de Verificación que valida corrección mediante verificación de tres capas; (5) Motor de Visualización que renderiza automáticamente insights estadísticos; (6) Agente Gestor de Sesiones que guarda y administra contextos de consulta para continuidad investigativa; y (7) Orquestador Multi-Agente que coordina enrutamiento dinámico de flujo de trabajo. El proyecto enfatiza consideraciones prácticas de despliegue incluyendo restricciones de recursos (ejecución local en hardware de consumo), eficiencia de costos (dependencia mínima de nube), y extensibilidad (arquitectura modular habilitando evolución de componentes).

---

## 2. JUSTIFICACIÓN

### ¿Por Qué Hay que Hacer el Proyecto?

Este proyecto aborda una necesidad crítica y creciente en el ecosistema empresarial moderno: la democratización del acceso a datos para la toma de decisiones informadas. La brecha existente entre la intuición estratégica de los ejecutivos y su capacidad técnica para validar hipótesis con datos representa un freno significativo a la agilidad organizacional. La implementación de un sistema NL2SQL robusto, verificado y accesible puede transformar fundamentalmente cómo las organizaciones aprovechan sus activos de datos, eliminando intermediarios técnicos y reduciendo ciclos de toma de decisiones de días a segundos.

### Importancia

**Relevancia Práctica**: Aproximadamente 2.5 millones de nuevos gerentes ingresan a la fuerza laboral anualmente en América Latina, la mayoría careciendo de habilidades técnicas de bases de datos. IDI habilita a este demográfico para validar independientemente hipótesis estratégicas con datos organizacionales, reduciendo la latencia de decisiones de días a segundos. Las organizaciones gastan en promedio el 30% del tiempo de analistas de datos en consultas rutinarias de reportes que podrían automatizarse, permitiendo reasignar estos recursos a tareas analíticas de alto valor como modelado predictivo e inferencia causal. El acceso a datos en tiempo real habilita adaptación ágil de estrategia, con estudios mostrando que reducir ciclos de toma de decisiones en 50% se correlaciona con crecimiento de ingresos del 15-20% en mercados volátiles.

**Contribución Académica**: El proyecto introduce un marco novedoso de adquisición de contexto mediante encuestas estructuradas, creando repositorios de contexto reutilizables para despliegue empresarial. Combina diseño de interfaces guiadas por palabras clave (reduciendo espacio de entrada) con clarificación conversacional (manejando ambigüedad residual), un enfoque poco estudiado que conecta Interacción Humano-Computadora (HCI) con NLP. Extiende la verificación más allá de chequeo sintáctico hacia pruebas de equivalencia semántica y validación de cordura de resultados, abordando la brecha de confiabilidad identificada en investigaciones recientes. Demuestra la factibilidad de NL2SQL de grado empresarial en hardware de consumo mediante descomposición modular, desafiando la suposición prevalente de que la precisión requiere modelos masivos.

### Interés del Estudiante

Como estudiante de Ingeniería de Sistemas y Computación, este proyecto representa la convergencia de múltiples áreas de interés personal: inteligencia artificial aplicada, arquitecturas de sistemas distribuidos, optimización de recursos computacionales, y diseño de experiencia de usuario. La oportunidad de trabajar en la frontera de tecnologías de LLMs mientras resolviendo un problema práctico tangible que impacta directamente la eficiencia organizacional es altamente motivante. Adicionalmente, el proyecto ofrece exposición profunda a técnicas estado del arte en NLP, fine-tuning de modelos, y diseño de sistemas multi-agente, habilidades altamente demandadas en la industria actual.

### Grado de Novedad

El proyecto presenta múltiples elementos novedosos: (1) Marco sistemático de adquisición de conocimiento de dominio mediante encuestas estructuradas, no explorado en profundidad en literatura NL2SQL existente; (2) Arquitectura híbrida de resolución de ambigüedad combinando restricción de interfaz con diálogo clarificatorio; (3) Pipeline de verificación multi-capa (sintaxis + semántica + cordura de resultados) proporcionando garantías de corrección más robustas que sistemas actuales; (4) Gestión de sesiones con preservación completa de contexto investigativo para continuidad analítica; (5) Demostración de que modelos especializados ligeros (7-13B parámetros) con fine-tuning pueden rivalizar con modelos monolíticos grandes en tareas NL2SQL específicas de dominio, habilitando despliegue local rentable.

### Necesidad Humana que se Satisface

El proyecto satisface la necesidad fundamental de acceso democrático al conocimiento contenido en bases de datos organizacionales. Actualmente, la información valiosa está efectivamente bloqueada para la mayoría de trabajadores del conocimiento debido a barreras técnicas. IDI elimina esta barrera, permitiendo que gerentes, ejecutivos, analistas de negocio y otros profesionales no técnicos formulen preguntas en su lenguaje natural y obtengan respuestas verificadas inmediatamente. Esto no solo mejora la eficiencia operacional sino que empodera a individuos para tomar decisiones informadas, fomenta la alfabetización en datos, y promueve una cultura organizacional más analítica y basada en evidencia.

### Beneficios y Beneficiados

**Beneficiarios Directos**:
- **Ejecutivos y Gerentes**: Acceso inmediato a insights de datos sin dependencia de TI, habilitando decisiones estratégicas más rápidas y basadas en datos
- **Analistas de Datos**: Liberación de tareas rutinarias de generación de reportes, permitiendo enfoque en análisis complejo de alto valor
- **Organizaciones**: Reducción de costos operacionales, mejora en agilidad de toma de decisiones, y ventaja competitiva mediante aprovechamiento más efectivo de activos de datos

**Beneficiarios Indirectos**:
- **Estudiantes e Investigadores**: Plataforma de código abierto para experimentación en NL2SQL y arquitecturas multi-agente
- **Comunidad Académica**: Contribuciones metodológicas y empíricas avanzando el estado del arte en interfaces de lenguaje natural para bases de datos
- **Sector Tecnológico Colombiano**: Demostración de capacidad local para desarrollar soluciones de IA aplicada competitivas internacionalmente

### Mercado

El mercado global de herramientas de inteligencia de negocios (BI) y analítica alcanzó $27.11 mil millones en 2022 y se proyecta crecer a $54.27 mil millones para 2030 (CAGR del 9.1%). Dentro de este mercado, las interfaces de lenguaje natural representan un segmento de rápido crecimiento, con el 78% de proveedores de bases de datos empresariales planeando integración NL2SQL para 2026. Sin embargo, soluciones actuales son predominantemente propietarias, basadas en nube, y costosas, creando oportunidad para alternativas de código abierto, desplegables localmente. El mercado objetivo inicial incluye: (1) PYMEs en América Latina buscando capacidades analíticas sin inversión en infraestructura costosa; (2) Departamentos gubernamentales requiriendo soberanía de datos y despliegue on-premise; (3) Instituciones educativas buscando herramientas pedagógicas para enseñanza de bases de datos e IA. El potencial de escalamiento incluye adaptación a dominios especializados (salud, finanzas, logística) mediante personalización del marco de adquisición de contexto.

---

## 3. OBJETIVO GENERAL

**Diseñar, desarrollar y evaluar IDI (Interfaz Inteligente de Base de Datos), un sistema NL2SQL modular multi-agente que permite a ejecutivos no técnicos extraer insights estadísticos de bases de datos relacionales mediante consultas conversacionales en lenguaje natural con conciencia contextual, resolución de ambigüedad, verificación automatizada y continuidad investigativa basada en sesiones, alcanzando >90% de corrección de consultas mientras opera en hardware de consumo local con comunicación transparente de progreso para tiempos de procesamiento extendidos (hasta 30 segundos), con el propósito de democratizar el acceso a datos organizacionales y habilitar toma de decisiones ágil basada en evidencia.**

---

## 4. OBJETIVOS ESPECÍFICOS

### Objetivo Específico 1: Análisis de Requerimientos

**Conducir análisis integral de requerimientos para un sistema NL2SQL enfocado en ejecutivos, identificando requerimientos funcionales y no funcionales, criterios de éxito y métricas de evaluación mediante revisión de literatura, análisis competitivo y evaluación de necesidades de stakeholders.**

### Objetivo Específico 2: Diseño del Sistema

**Diseñar la arquitectura modular de IDI, especificando responsabilidades de componentes, protocolos de comunicación inter-agente, flujos de datos, mecanismos de gestión de sesiones, estrategias de comunicación de progreso, y selección de stack tecnológico optimizado para despliegue local en hardware de consumo (16GB RAM, 8GB VRAM) con timeouts de consulta extendidos (hasta 30 segundos).**

### Objetivo Específico 3: Desarrollo de la Solución

**Implementar los siete módulos centrales de IDI (Gestor de Contexto, Comprensión de Consultas, Generador SQL, Agente de Verificación, Motor de Visualización, Gestor de Sesiones, Orquestador Multi-Agente) con generación de datos sintéticos de entrenamiento, pipelines de fine-tuning de modelos, gestión de flujo conversacional y componentes de interfaz de usuario incluyendo indicadores de progreso y controles de sesión.**

### Objetivo Específico 4: Análisis de Resultados

**Evaluar el desempeño de IDI mediante benchmarking cuantitativo (precisión de ejecución, latencia, efectividad de verificación, patrones de uso de sesiones) y evaluación cualitativa (estudio de usuario con tareas multi-turno, revisión experta, efectividad de indicadores de progreso), comparando resultados contra métodos baseline e identificando oportunidades de mejora.**

---

## 5. ANTECEDENTES

### Antecedentes Locales

En Colombia, la adopción de sistemas de análisis de datos ha crecido significativamente en la última década, particularmente en sectores financiero, salud y retail. Sin embargo, la mayoría de organizaciones colombianas todavía dependen de soluciones propietarias internacionales (Tableau, Power BI) con costos de licenciamiento significativos y dependencia de conectividad a nube. La Universidad Nacional de Colombia ha desarrollado investigación en procesamiento de lenguaje natural para español, particularmente en el grupo de investigación MindLab, pero aplicaciones específicas a interfaces de bases de datos permanecen limitadas. Este proyecto representa una oportunidad para desarrollar capacidad local en esta área emergente, adaptada a necesidades y restricciones del contexto latinoamericano.

### Antecedentes Regionales

En América Latina, iniciativas de transformación digital gubernamental y empresarial han identificado el acceso democrático a datos como prioridad estratégica. Países como Brasil y México han invertido en plataformas de datos abiertos con interfaces de consulta, pero predominantemente mediante formularios estructurados en lugar de lenguaje natural. La brecha de habilidades técnicas es particularmente pronunciada en la región, con estudios mostrando que solo el 12% de gerentes en PYMEs latinoamericanas tienen capacitación formal en análisis de datos. Esto crea tanto necesidad urgente como oportunidad de mercado significativa para soluciones que reduzcan barreras técnicas de acceso a datos.

### Antecedentes Nacionales

El Plan Nacional de Desarrollo 2022-2026 de Colombia prioriza transformación digital y gobernanza basada en datos. IDI se alinea directamente con estos objetivos mediante: (1) Transformación Productiva: habilitando PYMEs para aprovechar analítica de datos sin contratar personal especializado; (2) Desarrollo de Capital Humano: entrenando ingenieros de próxima generación en intersección estado del arte de IA/bases de datos; (3) Soberanía Tecnológica: desarrollando soluciones localmente adaptables reduciendo dependencia de plataformas SaaS extranjeras. Adicionalmente, instituciones como el Ministerio de Tecnologías de la Información y las Comunicaciones (MinTIC) han promovido iniciativas de alfabetización digital y datos abiertos que se beneficiarían de herramientas de acceso más intuitivas.

### Antecedentes Internacionales

Internacionalmente, el campo NL2SQL ha evolucionado a través de cuatro eras paradigmáticas: (1) Era de Modelos de Lenguaje Estadístico (1990s-2016) con sistemas basados en reglas y aproximaciones N-gram; (2) Era de Modelos de Lenguaje Neural (2017-2018) con introducción de LSTMs y mecanismos de atención, culminando en el benchmark seminal Spider; (3) Era de Modelos de Lenguaje Pre-entrenados (2018-2023) con modelos basados en Transformers (BERT, T5) elevando precisión a 70-80% en benchmarks complejos; y (4) Era de Modelos de Lenguaje de Gran Escala (2023-Presente) con modelos como GPT-4, Claude y LLaMA demostrando >95% de precisión en tareas específicas de dominio cuando apropiadamente contextualizados.

Trabajos recientes particularmente relevantes incluyen: (1) Luo et al. (2025) proporcionando la taxonomía más comprensiva de técnicas NL2SQL contemporáneas; (2) Kumar et al. (2025) presentando arquitectura probada en producción para NL2SQL empresarial a escala AWS-Cisco con enfoque en promptos con alcance de dominio, pre-resolución de identificadores y abstracciones de datos; (3) Li et al. (2025) con Alpha-SQL demostrando frameworks zero-shot combinando LLMs con Monte Carlo Tree Search para planificación autónoma de flujo de trabajo; y (4) Pourreza et al. (2024) con CHASE-SQL explorando descomposición basada en agentes con agentes especializados para poda de esquema, generación de candidatos y ranking basado en ejecución.

A pesar de estos avances, el despliegue empresarial permanece desafiante debido a brechas de conocimiento de dominio, complejidad de esquemas, manejo de ambigüedad y preocupaciones de confiabilidad, desafíos que IDI específicamente aborda mediante arquitectura modular y conciencia contextual.

---

## 6. METODOLOGÍA

### Objetivo Específico 1: Análisis de Requerimientos

**Tarea A: Revisión de Literatura y Análisis Competitivo**
- Realizar inmersión profunda en papers recientes de NL2SQL (Luo et al., Li et al., Kumar et al.)
- Analizar soluciones comerciales (Tableau Ask Data, Power BI Q&A, AWS Athena NL)
- Documentar fortalezas, debilidades y brechas identificadas
- Crear matriz de características competitivas comparando 5+ soluciones existentes

**Tarea B: Selección y Análisis de Conjuntos de Datos Benchmark**
- Descargar y analizar benchmarks Spider, BIRD y específicos de dominio
- Evaluar características de datasets (tamaño, complejidad, diversidad de dominio)
- Seleccionar benchmarks primarios y secundarios para evaluación
- Crear conjunto de prueba personalizado de consultas específicas para ejecutivos (50-100 consultas)

**Tarea C: Especificación de Requerimientos y Definición de Métricas**
- Definir requerimientos funcionales por módulo
- Definir requerimientos no funcionales (desempeño, usabilidad, escalabilidad)
- Especificar métricas de éxito con umbrales cuantitativos
- Crear personas de usuario y escenarios de casos de uso detallados

### Objetivo Específico 2: Diseño del Sistema

**Tarea A: Diseño de Arquitectura y Especificación de Módulos**
- Diseñar arquitectura del sistema de alto nivel (diagrama de componentes)
- Especificar interfaces de módulos (contratos API)
- Diseñar flujos de datos entre componentes (diagramas de secuencia)
- Documentar patrones de diseño y decisiones arquitectónicas

**Tarea B: Selección y Justificación de Stack Tecnológico**
- Evaluar candidatos LLM (benchmark en consultas de muestra)
- Comparar opciones de frameworks (LangChain vs. LangGraph vs. personalizado)
- Probar impacto de cuantización en precisión (4-bit vs. 8-bit vs. FP16)
- Prototipar inferencia en hardware objetivo (medir uso de VRAM, latencia)

**Tarea C: Diseño de Encuesta de Adquisición de Contexto y Esquema de Base de Datos**
- Diseñar encuesta de onboarding (estructura de preguntas, lógica de ramificación)
- Crear esquema para almacenamiento de contexto (BD vectorial + registro de metadatos)
- Diseñar plantilla de ejemplos few-shot y formato de almacenamiento
- Planificar pipeline de generación de datos sintéticos

### Objetivo Específico 3: Desarrollo de la Solución

**Tarea A: Infraestructura Central y Gestor de Contexto**
- Configurar estructura de repositorio de proyecto
- Implementar conexiones de base de datos (PostgreSQL/SQLite)
- Desarrollar Agente Gestor de Contexto (integración BD vectorial, pipeline de generación de embeddings, recuperación de contexto con búsqueda de similitud)
- Implementar lógica de procesamiento de encuestas

**Tarea B: Agentes de Comprensión de Consultas y Generación SQL**
- Implementar Agente de Comprensión de Consultas (NER para extracción de entidades, clasificación de intención, reglas de detección de ambigüedad, generación de preguntas clarificatorias)
- Implementar Agente Generador SQL (diseño de plantilla de prompt, pipeline de inferencia LLM, decodificación restringida)
- Generar datos sintéticos de entrenamiento (500-1000 ejemplos)
- Realizar fine-tuning de modelos usando QLoRA

**Tarea C: Verificación, Visualización, Gestor de Sesiones y Orquestación**
- Implementar Agente de Verificación (tres capas: validador sintáctico, verificador de equivalencia semántica, verificador de cordura de resultados)
- Implementar Motor de Visualización (lógica de selección de tipo de gráfico, integración con Recharts)
- Implementar Agente Gestor de Sesiones (almacenamiento PostgreSQL con JSONB, operaciones guardar/cargar/listar/eliminar/exportar)
- Implementar Orquestador Multi-Agente (definición de flujo de trabajo LangGraph, gestión de estado con soporte multi-turno, rastreo de progreso y actualizaciones WebSocket)
- Desarrollar interfaz web (constructor de consultas guiado por palabras clave, panel de visualización, indicadores de progreso, controles de sesión)

### Objetivo Específico 4: Análisis de Resultados

**Tarea A: Evaluación Cuantitativa y Benchmarking**
- Ejecutar evaluación de benchmarks (Spider, BIRD, conjunto de prueba personalizado)
- Medir métricas cuantitativas (Precisión de Ejecución, Precisión de Coincidencia Exacta, Latencia, Utilización de recursos)
- Realizar estudios de ablación (remover módulos, medir impacto)
- Comparar contra métodos baseline (herramientas comerciales, benchmarks académicos)

**Tarea B: Estudio de Usuario y Evaluación Cualitativa**
- Diseñar protocolo de estudio de usuario (tareas, cuestionarios)
- Reclutar 10-15 participantes (profesores, gerentes de negocios locales si es factible)
- Conducir sesiones de evaluación basadas en tareas
- Administrar cuestionario System Usability Scale (SUS)
- Recolectar retroalimentación cualitativa (entrevistas, respuestas abiertas)
- Revisión experta: administradores de bases de datos evalúan calidad SQL

**Tarea C: Documentación de Tesis y Presentación Final**
- Escribir capítulos de tesis (Introducción, Antecedentes, Metodología, Resultados, Discusión, Conclusiones)
- Finalizar todos los diagramas y figuras
- Revisar y pulir basándose en retroalimentación del asesor
- Preparar diapositivas de presentación final
- Crear video de demostración mostrando capacidades del sistema

---

## 7. RECURSOS

Para el desarrollo de este proyecto, se requieren los siguientes recursos:

### Recursos Humanos
- **Estudiante**: Dedicación de 20-25 horas semanales durante 16 semanas para investigación, desarrollo e implementación del sistema
- **Computador personal**: Equipo con especificaciones mínimas de 16GB RAM, 8GB VRAM (GPU NVIDIA RTX 3060/3070 o equivalente), CPU moderno multi-núcleo

### Recursos Tecnológicos
- **Acceso a Internet**: Conexión estable para descarga de modelos pre-entrenados, datasets de benchmark, consulta de documentación y búsqueda bibliográfica
- **Software de código abierto**: Python 3.11+, librerías ML/NLP (Transformers, LangChain, ChromaDB, SQLAlchemy), frameworks web (FastAPI, React), herramientas de desarrollo (VS Code, Git)

### Recursos Académicos
- **Literatura científica**: Acceso a bases de datos académicas (IEEE Xplore, ACM Digital Library, arXiv) mediante suscripciones institucionales de la Universidad Nacional
- **Datasets de benchmark**: Conjuntos públicos de datos NL2SQL (Spider, BIRD) disponibles gratuitamente

**Nota**: El proyecto se ha diseñado específicamente para ser desarrollable con recursos mínimos, priorizando software de código abierto, modelos localmente desplegables y hardware de consumo accesible, eliminando dependencias de infraestructura costosa o servicios de nube de pago.

---

## 8. CRONOGRAMA DE ACTIVIDADES

### Fase 1: Análisis de Requerimientos (Semanas 1-4)

| Actividad | Semanas | Entregable |
|-----------|---------|------------|
| Revisión de literatura y análisis competitivo | 1-2 | Documento resumen estado del arte (10-15 páginas) |
| Selección y análisis de datasets benchmark | 2-3 | Documento justificación selección de benchmarks |
| Especificación de requerimientos y definición de métricas | 3-4 | Especificación de Requerimientos de Software (15-20 páginas) |

### Fase 2: Diseño del Sistema (Semanas 5-8)

| Actividad | Semanas | Entregable |
|-----------|---------|------------|
| Diseño de arquitectura y especificación de módulos | 5-6 | Documento arquitectura con diagramas UML |
| Selección y justificación de stack tecnológico | 6-7 | Documento justificación tecnológica con benchmarks preliminares |
| Diseño de encuesta de contexto y esquema de BD | 7-8 | Encuesta final + diseño de esquema de base de datos |

### Fase 3: Desarrollo de la Solución (Semanas 9-12)

| Actividad | Semanas | Entregable |
|-----------|---------|------------|
| Infraestructura central y Gestor de Contexto | 9 | Módulo Gestor de Contexto funcional con pruebas |
| Agentes de Comprensión de Consultas y Generación SQL | 10-11 | Agentes funcionales + dataset sintético + modelos fine-tuned |
| Verificación, Visualización, Sesiones y Orquestación | 11-12 | Sistema prototipo completo funcional con interfaz web |

### Fase 4: Análisis de Resultados (Semanas 13-16)

| Actividad | Semanas | Entregable |
|-----------|---------|------------|
| Evaluación cuantitativa y benchmarking | 13-14 | Reporte de evaluación de desempeño (10-15 páginas) |
| Estudio de usuario y evaluación cualitativa | 14-15 | Resultados de estudio de usuario + reporte SUS |
| Documentación de tesis y presentación final | 15-16 | Documento de tesis completo (100-120 páginas) + presentación |

---

## 9. RESULTADOS ESPERADOS

### Resultado Esperado 1 (Objetivo Específico 1: Análisis de Requerimientos)

**Documento integral de especificación de requerimientos** que identifique clara y completamente los requerimientos funcionales y no funcionales del sistema IDI, incluyendo: (1) Especificación detallada de responsabilidades, entradas y salidas de cada uno de los siete módulos del sistema; (2) Definición cuantitativa de métricas de éxito con umbrales específicos (>90% precisión de ejecución, <30s latencia para consultas complejas, SUS >70); (3) Selección justificada de datasets de benchmark primarios y secundarios; (4) Conjunto de prueba personalizado de 50-100 consultas representativas de necesidades ejecutivas; y (5) Personas de usuario y escenarios de casos de uso detallados. Este documento proporcionará la base sólida para todas las fases subsecuentes del proyecto, asegurando alineación entre diseño, implementación y evaluación.

### Resultado Esperado 2 (Objetivo Específico 2: Diseño del Sistema)

**Diseño arquitectónico completo y validado del sistema IDI** que especifique: (1) Arquitectura modular de siete componentes con diagramas UML de componentes, despliegue y secuencia mostrando separación clara de responsabilidades y flujos de datos; (2) Especificaciones de interfaces de módulos con contratos API tipo-seguros para cada agente; (3) Stack tecnológico seleccionado y justificado mediante benchmarks empíricos comparando alternativas de modelos LLM, frameworks de orquestación, y técnicas de cuantización; (4) Diseño de encuesta de adquisición de contexto con estructura de preguntas validada; (5) Esquemas de almacenamiento para base de datos vectorial, registro de metadatos y gestión de sesiones; (6) Estrategias de comunicación de progreso y manejo de timeouts extendidos. Este diseño garantizará factibilidad técnica antes de iniciar implementación, minimizando riesgos de integración.

### Resultado Esperado 3 (Objetivo Específico 3: Desarrollo de la Solución)

**Sistema prototipo IDI completamente funcional** que integre los siete módulos centrales con las siguientes características demostrables: (1) Capacidad de procesar consultas en lenguaje natural end-to-end, desde entrada de usuario hasta visualización de resultados; (2) Gestión de conversaciones multi-turno con preservación de contexto, permitiendo consultas de seguimiento y refinamiento basado en retroalimentación; (3) Generación de SQL sintácticamente válido y semánticamente correcto para >85% de consultas de prueba; (4) Verificación automática multi-capa detectando >90% de errores con <10% falsos positivos; (5) Selección automática de visualizaciones apropiadas (gráficos de línea, barras, pie, etc.) basada en características de resultados; (6) Funcionalidad completa de gestión de sesiones (guardar, cargar, buscar, exportar investigaciones); (7) Indicadores de progreso en tiempo real con capacidad de cancelación para consultas de procesamiento extendido; y (8) Interfaz web intuitiva accesible para usuarios no técnicos. El sistema incluirá suite de pruebas unitarias e integración con >80% cobertura de código.

### Resultado Esperado 4 (Objetivo Específico 4: Análisis de Resultados)

**Evaluación exhaustiva del sistema IDI con evidencia cuantitativa y cualitativa** que demuestre: (1) Reporte de desempeño cuantitativo mostrando precisión de ejecución >85% en conjunto de prueba de dominio específico, latencia promedio <5 segundos para consultas simples y <30 segundos para consultas complejas, y efectividad de verificación >95% detección de errores; (2) Resultados de estudios de usuario mostrando tasa de éxito de tareas >75%, puntaje SUS >70 (usabilidad "buena"), y confianza de usuario promedio >4/5; (3) Análisis comparativo contra soluciones baseline (herramientas comerciales, métodos académicos) demostrando competitividad en precisión con ventajas en eficiencia de costos, resolución de ambigüedad y robustez de verificación; (4) Estudios de ablación cuantificando contribución individual de cada módulo al desempeño general; (5) Análisis de patrones de uso de sesiones y efectividad de indicadores de progreso; y (6) Identificación de limitaciones actuales y recomendaciones concretas para trabajo futuro. Estos resultados proporcionarán validación rigurosa de hipótesis de investigación y contribuciones del proyecto.

---

## 10. BIBLIOGRAFÍA

### Libros

1. Hevner, A. R., March, S. T., Park, J., & Ram, S. (2004). *Design Science in Information Systems Research*. MIS Quarterly, 28(1), 75-105.

2. Zelle, M., & Mooney, R. J. (1996). *Learning to Parse Database Queries Using Inductive Logic Programming*. In Proceedings of the Thirteenth National Conference on Artificial Intelligence (pp. 1050-1055).

### Artículos Científicos

1. **Luo, Y., Li, G., Fan, J., Chai, C., & Tang, N. (2025).** Natural Language to SQL: State of the Art and Open Problems. *Proceedings of the VLDB Endowment*, 18(12), 5466-5471. https://doi.org/10.14778/3750601.3750696
   *[Taxonomía comprehensiva de técnicas NL2SQL contemporáneas, identificando cinco niveles de dificultad y situando investigación actual]*

2. **Kumar, R., Fotherby, T., Keshavanarayana, S., Matthew, T., Vaquero, D., Varshneya, A., & Wu, J. (2025).** Enterprise-grade Natural Language to SQL Generation Using LLMs: Balancing Accuracy, Latency, and Scale. *AWS Machine Learning Blog*. Retrieved from https://aws.amazon.com/blogs/machine-learning/
   *[Arquitectura probada en producción AWS-Cisco con promptos con alcance de dominio, pre-resolución de identificadores y abstracciones de datos]*

3. **Li, B., Zhang, J., Fan, J., Xu, Y., Chen, C., Tang, N., & Luo, Y. (2025).** Alpha-SQL: Zero-shot Text-to-SQL Using Monte Carlo Tree Search. *arXiv preprint arXiv:2502.17248*.
   *[Framework zero-shot combinando LLMs con MCTS para planificación autónoma de flujo de trabajo]*

4. **Pourreza, M., Li, H., Sun, R., Chung, Y., Talaei, S., Kakkar, G. T., ... & Arik, S. O. (2024).** CHASE-SQL: Multi-path Reasoning and Preference Optimized Candidate Selection in Text-to-SQL. *arXiv preprint arXiv:2410.01943*.
   *[Descomposición basada en agentes con agentes especializados para poda de esquema, generación de candidatos y ranking basado en ejecución]*

5. **Brown, T. B., Mann, B., Ryder, N., Subbiah, M., Kaplan, J., Dhariwal, P., ... & Amodei, D. (2020).** Language Models are Few-shot Learners. *Advances in Neural Information Processing Systems*, 33, 1877-1901.
   *[Introducción de capacidades de in-context learning de LLMs habilitando NL2SQL few-shot]*

6. **Yu, T., Zhang, R., Yang, K., Yasunaga, M., Wang, D., Li, Z., ... & Radev, D. (2018).** Spider: A Large-scale Human-labeled Dataset for Complex and Cross-domain Semantic Parsing and Text-to-SQL Task. In *Proceedings of the 2018 Conference on Empirical Methods in Natural Language Processing* (pp. 3911-3921).
   *[Benchmark seminal estableciendo evaluación estandarizada cross-domain para NL2SQL]*

7. **Wei, J., Wang, X., Schuurmans, D., Bosma, M., Ichter, B., Xia, F., ... & Zhou, D. (2022).** Chain-of-thought Prompting Elicits Reasoning in Large Language Models. *Advances in Neural Information Processing Systems*, 35, 24824-24837.
   *[Generación de pasos de razonamiento intermedios mejorando manejo de consultas complejas en NL2SQL]*

8. **Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., ... & Polosukhin, I. (2017).** Attention is All You Need. *Advances in Neural Information Processing Systems*, 30, 5998-6008.
   *[Arquitectura Transformer fundamental para modelos NL2SQL basados en atención]*

### Referencias Adicionales

9. **Li, J., Hui, B., Cheng, R., Qin, B., Ma, C., Huo, N., ... & Li, Y. (2023).** Can LLM Already Serve as a Database Interface? A BIg Bench for Large-scale Database Grounded Text-to-SQLs. *arXiv preprint arXiv:2305.03111*.
   *[Benchmark BIRD para evaluación de NL2SQL a escala empresarial con esquemas complejos]*

10. **Gartner Research (2023).** Market Trends: Business Intelligence and Analytics. *Gartner Inc.*
    *[Análisis de mercado mostrando 30% de tiempo de analistas en consultas rutinarias automatizables]*

11. **McKinsey & Company (2024).** The Data-Driven Enterprise. *McKinsey Global Institute*.
    *[Correlación entre reducción de ciclos de decisión (50%) y crecimiento de ingresos (15-20%)]*

12. **International Labour Organization - ILO (2024).** Labour Market Statistics for Latin America. *ILO Regional Office*.
    *[Estadísticas sobre 2.5 millones de nuevos gerentes anuales en América Latina]*

---

**Fecha**: Noviembre 2024
**Estudiante**: [Tu Nombre]
**Asesor Propuesto**: [Nombre del Asesor]
**Programa**: Ingeniería de Sistemas y Computación
**Universidad Nacional de Colombia**
