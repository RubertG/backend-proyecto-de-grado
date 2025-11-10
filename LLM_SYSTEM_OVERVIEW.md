# Subsistema LLM – Descripción Técnica (Resumen Académico)

Este documento presenta la arquitectura y el funcionamiento del subsistema de retroalimentación automática y chat pedagógico apoyado en modelos de lenguaje. El diseño privilegia la calidad didáctica, la robustez operativa y el control de costos, integrando validación estructural previa, construcción de prompts contextualizados, memoria semántica y medición sistemática de calidad.

## Palabras clave (para índice temático)
- Retroalimentación formativa, evaluación continua, aprendizaje activo, scaffolding, metacognición, guía instruccional, ingeniería de prompts, validación estructural, memoria vectorial, similaridad semántica, recency decay, MMR, sanitización, métricas de calidad, latencia, costo-eficiencia, resiliencia operativa, control de tema, off-topic, trazabilidad.

## 1. Modelo y Capa de Abstracción
- Se emplea un modelo conversacional de última generación (variante “2.5 Flash”) con soporte robusto para respuestas en español, configurable en cuanto a temperatura y otros hiperparámetros.
- La integración se realiza mediante una capa de abstracción que encapsula la inicialización, la invocación y la tolerancia a fallos. Esta capa implementa:
  - Inicialización perezosa (lazy) con reintentos espaciados para adoptar credenciales en caliente.
  - Modo de gracia (stub) cuando no existen credenciales, devolviendo respuestas controladas y medibles sin interrumpir el flujo.
- Para funciones de similaridad semántica se emplean embeddings especializados; en ausencia de servicio, se recurre a un embedding determinista de respaldo para mantener reproducibilidad.

### Justificación de selección del modelo “2.5 Flash”
- Equilibrio calidad–precio: ofrece una relación costo/beneficio favorable frente a variantes de mayor tamaño, manteniendo suficiente capacidad de razonamiento y calidad lingüística para retroalimentación pedagógica.
- Latencia y experiencia de usuario: su tiempo de respuesta es competitivo, lo que favorece iteraciones rápidas propias del aprendizaje activo y del chat tutorial.
- Adecuación al dominio educativo: buen desempeño en español neutro, capacidad de seguir directrices de formato (secciones en Markdown) y adaptación a distintos tipos de ejercicio (procedural y conceptual).
- Estabilidad e integración: disponibilidad estable y soporte en librerías de orquestación; reduce fricciones de despliegue y mantenimiento.
- Alternativas consideradas: modelos “pro” o de mayor tamaño elevan el costo marginal por interacción y la latencia; opciones abiertas on‑premise requieren inversión en infraestructura, energía y MLOps que no se justifican en un MVP académico orientado a escalamiento gradual.

## 2. Construcción de Prompts (Ingeniería de Prompt)
- El sistema genera prompts en español con tono pedagógico y estructura fija, incorporando de forma jerárquica:
  - Contexto de la guía (título/tema) y del ejercicio (tipo, dificultad, descripción, respuesta esperada no literal).
  - Historial reciente de intentos, retroalimentación previa y extractos del diálogo.
  - Respuesta actual del estudiante.
- Existen pautas de especialización por tipo de ejercicio (comandos de terminal, construcción de imágenes, definición de servicios, y conceptuales) que orientan el feedback hacia precisión técnica, seguridad, rendimiento y claridad conceptual.
- Se aplica un presupuesto máximo de longitud con truncado progresivo de elementos menos críticos (historial, feedback previo, descripciones extensas), garantizando estabilidad y coste acotado.

## 3. Flujo de Retroalimentación Automática
1. Validación estructural temprana: para entradas de línea de comandos, descripciones de imágenes y definiciones de servicios, se verifica la corrección sintáctica y la presencia de campos mínimos. Los ejercicios conceptuales no requieren esta verificación.
2. Si la validación falla, se retorna un error de datos con detalle pedagógico y no se invoca el modelo (eficiencia y claridad para el estudiante).
3. En caso favorable, se compone el prompt con el contexto disponible y, opcionalmente, se enriquece con fragmentos semánticamente similares extraídos de la memoria vectorial.
4. El modelo genera una respuesta en formato Markdown, con secciones enfocadas en fortalezas, errores y recomendaciones prácticas.
5. Se normaliza la salida (limpieza de encabezados vacíos, eliminación de enlaces/citas) para mejorar legibilidad y reducir riesgos de referencia externa.
6. Se registran métricas clave (latencia, estimación de tokens, densidad, diversidad léxica, longitud media de oración y banderas de calidad) y se persiste el intento con su retroalimentación.
7. Se actualiza la memoria vectorial con las nuevas piezas (entrada y respuesta) para apoyar futuras consultas y contexto de diálogo.

### Diagrama de Flujo (retroalimentación)
```
Entrada estudiante → Validación estructural
  ├─ Falla → Error con detalle (fin)
  └─ Pasa → Recolección de contexto → Construcción de prompt → (Similaridad opcional)
           → Generación LLM/stub → Post-proceso → Métricas → Persistencia → Respuesta
```

## 4. Flujo de Conversación (Chat)
- Se construye un prompt controlado que obliga a mantener el foco en la guía y el ejercicio; ante desvíos temáticos, el sistema redirige amable y brevemente.
- El historial reciente y, en su caso, fragmentos semánticamente similares se integran para reforzar coherencia y evitar repeticiones.
- La respuesta resultante se normaliza, se miden métricas y se almacena la interacción en la memoria vectorial para continuidad del diálogo.

### Diagrama de Flujo (chat)
```
Mensaje estudiante → Contexto (ejercicio + historial) → Prompt controlado → (Similaridad opcional)
                   → Generación LLM/stub → Post-proceso → Métricas → Persistencia → Respuesta
```

## 5. Memoria Semántica y Recuperación por Similaridad
- El sistema mantiene una memoria vectorial de interacciones (intentos, respuestas, preguntas, contestaciones) que habilita:
  - Recuperación de fragmentos relevantes mediante similitud coseno.
  - Atenuación por recencia con decaimiento exponencial, priorizando material reciente.
  - Re-selección basada en relevancia-diversidad (MMR) para evitar redundancia y mejorar cobertura.
- Este mecanismo incrementa la pertinencia del contexto inyectado en prompts sin aumentar el costo de forma descontrolada.

### Diagrama de Flujo (similaridad)
```
Recuperar candidatos → Embedding de la consulta → Similaridad coseno × recencia
→ Orden inicial → Preselección → MMR (diversidad) → K fragmentos finales
```

## 6. Medición de Calidad y Observabilidad
- Se instrumenta cada interacción con métricas cuantitativas: latencia, estimaciones de tokens, densidad caracteres/token, diversidad léxica y longitud media de oración.
- Se registran banderas de calidad (uso de similaridad, truncamiento, especialización aplicada, modo stub) que permiten auditoría y mejora continua.
- La persistencia estructurada de estos datos habilita análisis longitudinales para ajustar prompts, umbrales de truncado y estrategias de recuperación.

## 7. Justificación pedagógica
- Enfoque formativo: la retroalimentación se estructura para promover reflexión y mejora incremental (fortalezas, errores, recomendaciones operativas), favoreciendo la autorregulación del aprendizaje.
- Scaffolding y gradualidad: el sistema introduce apoyos específicos según el tipo de tarea (procedimental/constructiva o conceptual), reduciendo la carga cognitiva extrínseca y guiando al estudiante hacia prácticas correctas y seguras.
- Brevedad con claridad: el formato compacto y seccionado facilita la asimilación y evita sobrecarga informativa, alineándose con principios de micro‑aprendizaje.
- Control de tema: la conversación restringida al ámbito de la guía/ejercicio minimiza distracciones y asegura pertinencia pedagógica.
- Evaluación auténtica: la validación estructural temprana ofrece señales diagnósticas objetivas (sintaxis, campos mínimos), complementando el juicio cualitativo del LLM.

## 8. Robustez Operativa
- Modo de operación sin credenciales que devuelve respuestas controladas, garantizando continuidad en entornos de desarrollo o contingencia.
- Inicialización perezosa para adoptar cambios de configuración sin reinicios agresivos.
- Validación estructural previa que evita consumo innecesario del modelo ante entradas inválidas, contribuyendo a la eficiencia y a la experiencia de usuario.

## 9. Parámetros de Configuración Relevantes
- Selección de modelo y temperatura.
- Activación y parámetros de similaridad (tamaño de recuperación, decaimiento temporal, equilibrio relevancia-diversidad, límites de presupuesto).
- Variables de entorno para acceso a servicios externos y a la capa de persistencia.

## 10. Líneas de Evolución Propuestas
- Sustituir el embedding de respaldo por un modelo local abierto para mayor consistencia y control de privacidad.
- Migración a índices vectoriales nativos para ejecutar ranking en la base de datos y reducir latencia.
- Incorporación de clasificadores ligeros para detección de desvíos temáticos con mayor precisión.
- Baterías de pruebas específicas para truncado, especialización y post-procesamiento.
- Políticas de uso y límites de coste por usuario/guía en escenarios de producción.

---
Este documento sintetiza el diseño del subsistema desde una perspectiva académica, destacando sus mecanismos de control, su orientación pedagógica y su capacidad de ampliación.
