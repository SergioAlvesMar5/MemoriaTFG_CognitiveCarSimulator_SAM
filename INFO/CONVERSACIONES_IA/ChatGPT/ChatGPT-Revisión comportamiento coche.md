# Revisión comportamiento coche

**User:** Anonymous  
**Created:** 6/10/2026 13:49:57  
**Updated:** 6/11/2026 10:20:50  
**Exported:** 6/29/2026 16:54:02  
**Link:** [https://chatgpt.com/g/g-p-69e894c075f08191841adcc5961cd5ef/c/6a294f55-8384-83eb-8499-237953f62f27](https://chatgpt.com/g/g-p-69e894c075f08191841adcc5961cd5ef/c/6a294f55-8384-83eb-8499-237953f62f27)  

## Prompt:
10/6/2026, 13:50:08

este es un corto test de mi modelo, y quiero revisar varias cosas, el orden en el que te las diga, no marca su importancia:

- quiero revisar el comportamiento del coche, cuando en una rotonda, toma a partir de la segunda salida, se acaba chocando, para la primera, o segunda, no tiene problema, pero a partir de ahi si

- quiero revisar en los cedas, cuando llegan a un ceda cuya zona de cruce está ocupada, y deben parar a tope, y esperar, espera muy lejos del punto de parada, casi a la entrada de la zona espera del ceda

- cuando un modelo sin mutar, supere al loaded, no se debe de guardar un backup, ya que sería una duplicación y consume espacio

- hay que revisar los inputs, y su importnacia en la red neuronal, revisar que no haya duplicados, o inputs que no aporten nada

- hay que revisar el fitness, ver cuanto vale cada cosa, su importancia y como influye en el rendimiento del coche

- revisar las penalizaciones y muertes, como de restrictivas son, como de influyentes son y como de importantes son

para todas estas revisiones, quiero que te bases completamente en los datos, si para alguna decisión no tienes información, creamos nuevas variables de debug, las añadimos al Fitness_Debug.csv y hacemos un test rapido

para todas las modificaciones que veas necesarias, describelas paso a paso en blueprint de unreal

[Attachment: Fitness_Debug.csv]

[Attachment: informe.txt]

[Attachment: Test_Summary.csv]

[Attachment: FITNESS 10-06-2026.txt]

[Attachment: EVOLUTIONMANAGER 09-06-2026.txt]

[Attachment: INTERSECTIONS 09-06-2026.txt]

[Attachment: RED NEURONAL 09-06-2026.txt]

## Response:
10/6/2026, 13:49:56

Voy a separar el análisis en dos partes: primero extraigo evidencia numérica del test y de los blueprints actuales; después te dejo cambios concretos, paso a paso, y qué nuevas columnas de debug faltan para decidir lo que aún no se puede demostrar.

Primer hallazgo importante: este test no sirve para comparar familias ni mutaciones porque las 260 filas son LOADED, sin mutaciones. Sí sirve para ver hotspots, muertes, peso del fitness y qué debug falta para rotondas/cedas.

> **Leyendo CSV y analizando archivos de texto**
>
>
> **Normalizando columnas y buscando evidencia de colisión**
>
> Necesito limpiar y normalizar columnas, tal vez agregando un BOM. Estoy pensando en cómo calcular las pruebas de colisiones en los rotondas después de la segunda salida. ¿Tenemos etiquetas? Debo identificar puntos calientes según causas de muerte. Tal vez sea necesario buscar "rot" o "round" en los archivos para encontrar información relevante.
>
> **Limpiando y normalizando columnas BOM**
>
>
> **Buscando información sobre rotondas y rutas**
>
>
> **Aclarando citas y rangos de líneas**
>
> Parece que necesitamos obtener líneas exactas de los archivos con citas. Las búsquedas no incluyen números de línea, solo fragmentos. Las instrucciones requieren rangos de línea, pero los resultados actuales no los proporcionan. Tendré que buscar las partes relevantes usando una búsqueda más detallada, incluyendo líneas exactas de los informes y otros documentos clave.
>
> **Evaluando entradas y redundancias en el modelo**
>
> Parece que los resultados de la búsqueda de archivos no muestran marcadores de línea, pero aún podemos usarlos para las citas. Necesito realizar estadísticas detalladas sobre los 260 test sin mutaciones, ya que no son adecuados para evaluar la importancia de entrada. Debo agregar valores de depuración y realizar pruebas de ablación. También revisaré las 20 entradas y posibles redundancias, como el estado del semáforo y el tipo de control de tráfico que podrían superponerse.
>
> **Ajustes en la entrada y análisis de penalizaciones**
>
> Falto de información clave como la distancia firmada al final de parada/yield y el estado de cruce. También noto que algunas métricas de rotondas no tienen información suficiente. Necesito calcular las correlaciones de componentes sin que el tiempo afecte demasiado los resultados. También debo analizar las penalizaciones por muerte y colisiones, especialmente los valores de "YieldValidationTime" y "NumYieldsCompleted".
>
> **Analizando colisiones y causas de muerte**
>
> Necesito continuar con el análisis en Python. Calcularé tablas detalladas: razón de muerte por "spawn" y colisiones tempranas. Ordenaré las razones de muerte e intentaré identificar si las causas son relacionadas con "rotondas después de la segunda salida". Analizaré las colisiones en función del "spawn" y la muerte, con un enfoque en el tiempo.
>
> **Calculando resumen de razones de muerte y estadísticas**
>
>
> **Analizando problema de Yield**
>
> Necesito calcular estadísticas sobre el problema de Yield. El archivo CSV actual no tiene la distancia hasta la línea ni la ocupación del cruce, pero puedo ver que "YieldValidationTime" es 0, posiblemente porque se reinicia al aceptar. Debo revisar las filas con "yield ticks" altos y conflictos de tiempo o colisiones para generar sospechas.
>
> **Evaluando estadísticas de rendimiento y validación**
>
>
> **Analizando componentes de fitness y correlaciones con tiempo**
>
> Necesito calcular las proporciones de los componentes del fitness, controlando el tiempo, posiblemente por segundo. Usaré regresión para evaluar la importancia y computaré los promedios de los componentes en porcentaje junto con sus correlaciones. También debo analizar la correlación con el tiempo y ajustar las penalizaciones.
>
> **Calculando correlaciones y medias por componente**
>
>
> **Calculando colisiones y mejorando depuración**
>
> Necesito calcular el éxito por generación. Para el problema del rotonda, debo detectar colisiones en el área de "NavModifierVolume" versus "IntersectionBorder". Hay que ajustar la depuración con más datos, como la decisión de intersección y distancias a la línea de parada, entre otros. Esto ayudará a entender mejor los problemas de colisión.
>
> **Analizando colisiones y posibles modificaciones en depuración**
>
> En el código de "EventActorBeginOverlap", solo se produce una muerte si el borde coincide con el "CurrentTrigger" y "DirectionIntent" es igual a la decisión. Para la rotonda después de la segunda salida, podría haber un problema con el "lane corridor border" o los triggers actuales. Necesito agregar más depuración.
>
> **Inspeccionando el blueprint de verificación de cruce de yield**
>
> Necesito revisar el blueprint actual relacionado con la verificación de cruce de "Yield". Parece que es importante entender cómo se está manejando actualmente este proceso antes de seguir adelante. Haré una búsqueda para examinarlo más detalladamente.
>
> **Inspeccionando el plano de Yield CheckCrossing**
>
>
> **Revisando la lógica de validación de parada y yield**
>
> Necesito verificar la lógica de validación de parada. Si la ventana permitida es demasiado amplia, podría permitir paradas excesivas antes de la línea. En cuanto a yield, quiero ajustar las condiciones para que sean más estrictas, limitando la distancia de parada y considerando si hay cruce o no, añadiendo una distinción de signo en la lógica de monitoreo de velocidad.
>
> **Revisando condiciones y duplicaciones en el flujo de parada y respaldo**
>
> Necesito asegurarme de que si el vehículo se detiene demasiado lejos de la línea, se sigan monitoreando los límites de violación, o que haya un error si el tiempo de espera se excede. También debo corregir duplicaciones en la lógica de carga y respaldo del modelo, asegurándome que el modelo cargado no se reemplace innecesariamente si no hay cambios en la mutación o clonación.
>
> **Solucionando problemas de duplicado y respaldo para el modelo cargado**
>
> Mientras reviso la lógica del modelo y la mutación, parece que cuando no hay mutación en el modelo cargado pero la función de rendimiento se supera, no debería hacerse una copia de seguridad. Necesito ajustar la lógica para considerar la diferencia real en los pesos y no solo en el rendimiento para gestionar correctamente el
>
> **Ajustando condiciones de respaldo y comparación de pesos**
>
> Necesito ajustar la lógica de respaldo para que no se realice si no hay cambios entre el coche actual y el cargado, usando tolerancia en la comparación de los pesos. Además, debo excluir el clon cargado y agregar un control adicional para el análisis de entradas, añadiendo depuración para los promedios y la varianza de los tiempos de entrada.
>
> **Evaluando entradas y correlaciones en el modelo**
>
> Estoy considerando si debo agregar un detalle de progreso en la ruta o dirección al modelo, pero eso posiblemente invalidaría los pesos guardados. Primero, quiero depurar las entradas y comparar las correlaciones entre las variables de comportamiento y éxito. Las correlaciones actuales sugieren que el tiempo y la velocidad influyen considerablemente en el rendimiento.
>
> **Analizando penalización y resultados de tráfico**
>
> La penalización por muerte no es significativa en términos absolutos, pero las colisiones interrumpen la acumulación de puntos, lo que representa la verdadera penalización. Las bonificaciones de "Stop/Yield" parecen estar bien correlacionadas, pero el modelo parece estar optimizando más la supervivencia y el tiempo que el cumplimiento del tráfico.
>
> **Revisando fórmula de penalización por muerte**
>
> Creo que necesito revisar la fórmula de la penalización por muerte, tal vez sea demasiado pequeña para las colisiones con navegación debido a obstáculos cercanos, lo que lleva a una terminación temprana. También quiero asegurarme de cómo se calcula la penalización para los obstáculos mediante el NavModifier.
>
> **Calculando correlaciones y análisis de penalizaciones**
>
>
> **Extrayendo sección entre eventos de comienzo y fin**
>
>
> **Revisando penalización y distribución por colisiones**
>
> Tal vez el evento no sea lo suficientemente descriptivo. Para el NavModifier "FueraDeCalle", no hay muerte inmediata, aunque con la superposición del nav se actualiza la aptitud y luego se aplica penalización. Necesito revisar cómo se distribuye la penalización por colisiones e investigar si los objetos de colisión cercanos comparten la misma fórmula.
>
> **Computando distribución de penalizaciones por colisión**
>
>
> **Organizando pasos para la depuración y el informe**
>
> Necesito revisar el informe por líneas como "detección posible atasco ceda" sin candidatos, ya que proviene de la búsqueda en el archivo. También puedo usar citas. Un posible paso será calcular candidatos de parada desde el CSV. Además, debo crear una lista de nuevas variables de depuración y definir instrucciones precisas para el Blueprint.
>
> **Modificaciones y ajustes en el test de penalización y métricas**
>
> No cambiaré las penalizaciones por muerte basadas en este test, excepto para el backup y la condición de yield. Los datos muestran demasiadas muertes, pero la magnitud de la penalización no es la raíz; las colisiones ya terminan el episodio. Puedo agregar "FitnessPerSecond" en el analizador, pero no es necesario en Unreal.
>
> **Ajustes y análisis en penalizaciones y fallos**
>
> La penalización más alta por velocidad es 1996, pero tiene una correlación positiva con la supervivencia; por segundo, es negativa.
> Las variables SteerApproach y Creeping están relacionadas positivamente debido a más contextos de parada en coches exitosos. No es necesario ajustar esto basado en este test.
> 
> El principal modo de fallo es la colisión/ruta, no las violaciones de parada/yield. La muerte por colisión, aunque restrictiva, es adecuada para este test.
>
> **Prueba de importancia de entradas**
>
> Voy a realizar una prueba de ablación, donde ejecuto el mismo modelo configurando una entrada en neutro durante la ejecución mientras mantengo fijos los pesos, y luego registro el éxito. Puedo usar "InputAblationIndex" en el controlador para cambiar ciertas entradas, como TrafficLightState o DistToStopLine,
>
> **Ajustes de exportación y ablation en Blueprint**
>
> El cálculo de Sum, SumSq, Min y Max se realiza en el controlador del coche, exportando la media, desviación estándar, mínimo y máximo. Sin embargo, en Blueprint resulta tedioso. Una opción es escribir una fila en un archivo de debug cada N ticks para la prueba rápida. Agregar también estadísticas de ablation para evaluar la importancia de las entradas.
>
> **Citas finales y ajustes en reportes**
>
> Sólo hay duplicados si un único
>
> **Ajustes en decisiones de intersección y controles de tráfico**
>
> La decisión en las intersecciones depende de varias variables como Control de tráfico, ID de rotonda, número de salida, distancia firmada y dirección. Se recomienda agregar columnas de depuración sin cambiar el comportamiento, pero sí incluir instrumentación de rutas. Además, ajustar la condición de velocidad para evitar resultados incorrectos en zonas de sensor.
>
> **Ajustes para validación y lógica de Yield**
>
> El tiempo de validación
>
> **Ajuste en las condiciones de entrada para cruce y velocidad**
>
> El análisis muestra que usando una relación de distancia (distancia a la línea / distancia de entrada) y una relación de velocidad (velocidad hacia adelante / velocidad máxima) se ajustan bien las condiciones. El cambio de ">= a <=" ajusta la aceptación. Para el cruce ocupado, el ajuste mejora cuando la velocidad es baja, pero si es alta, el margen podría ser más grande.
>
> **Ajustes necesarios en MonitorSpeed y gestión de cruce ocupado**
>
> Cuando la velocidad es alta, la relación de velocidad permite aceptar más distancia, lo cual parece raro, pero el diseño original permitía frenar. Si el cruce está ocupado, también debería requerirse velocidad baja. Se debe ajustar el comparador en MonitorSpeed de >= a <= y agregar una verificación de ocupación del cr
>
> **Ajustando el control de respaldo y análisis de entradas**
>
> Estoy considerando guardar solo un respaldo si hay diferencia entre el "BestCarRef.Debug_MutNumChanged" y el "LoadedBestFitness". Esto evita respaldos innecesarios y optimiza el proceso. Además, para mejorar el análisis de entradas, agregaré variables de depuración y asignaré grupos para pruebas rápidas, neutralizando inputs específicos si es necesario.
>
> **Mejorando las pruebas de colisiones y condiciones de tráfico**
>
> Parece que las muertes por colisión son las más restringidas, pero aún necesarias, lo que confirma que el problema no está en la magnitud de la penalización. Agregaré nuevas pruebas con variables de depuración, incluyendo detalles como la velocidad de colisión, decisiones en intersecciones y condiciones de tráfico, para realizar ajustes. Además, debo asegurarme de que las citas de archivos sean exactas y evitar enlaces directos.
>
> **Generando respuesta final y citaciones apropiadas**
>
> Estoy trabajando en una respuesta final, quizás de
>
> Pensó durante 5m 13s

He revisado el test, el informe y los blueprints actuales. La conclusión principal es esta: **el test demuestra muy bien que el problema dominante ahora son colisiones/localización de rutas, pero no permite todavía demostrar la causa exacta de la rotonda ni la importancia real de cada input**, porque faltan columnas de contexto.

## 1. Diagnóstico del test

Este test son **260 coches**, 5 generaciones × 52 spawns, todo en modo test. La población es **100% LOADED**, con `MutNumChanged = 0`, así que no hay diversidad genética ni comparación real entre mutados/no mutados. El informe también marca diversidad nula y todos los coches como `LOADED`. `informe.txt`

Resultado global:

| Métrica | Valor |
|---|---:|
| Coches evaluados | 260 |
| Éxitos | 85 / 260 = **32.69%** |
| Fallos | 175 / 260 = **67.31%** |
| Muertes por colisión | **175** |
| `TIMEFINISHED` | **85** |
| LAZY / REVERSE / STOP / YIELD / TRAFFIC deaths | **0** |

El fallo dominante no es semáforo, stop, yield, reverse ni lazy. Es **colisión pura**.

Además, las colisiones no parecen aleatorias:

| Evidencia | Valor |
|---|---:|
| Top 8 objetos de colisión | 117 / 175 colisiones = **66.9%** |
| Spawns con 100% colisión | 19 spawns |
| Filas afectadas por esos spawns | 95 / 260 = **36.5%** |
| Colisiones antes de 20 s | 77 / 175 = **44.0%** |
| Colisiones antes de 40 s | 124 / 175 = **70.9%** |

Esto apunta más a **hotspots de ruta / geometría / decisión / sensores en intersección**, no a un problema global del fitness.

---

## 2. Rotondas: no hay datos suficientes para afirmar la causa

Sobre el problema de “a partir de la segunda salida se choca”: **el CSV actual no tiene la información necesaria para demostrarlo**.

Ahora mismo `Fitness_Debug.csv` guarda spawn, muerte, fitness, componentes, stop/yield context, mutación, etc., pero no guarda:

- `IntersectionDecision`
- `CurrentTrigger`
- tipo de intersección
- si estaba en rotonda
- salida elegida: First / Second / Third / Fourth
- ángulo/progreso dentro de la rotonda
- actor exacto de colisión separado por clase/tag
- velocidad/steering/yaw en el momento de colisión
- distancia al borde o al centro de carril

El blueprint sí tiene `IntersectionDecision`, `CurrentTrigger` y `E_DirectionIntent` con `First`, `Second`, `Third`, `Fourth`, pero esos datos no se exportan al CSV. `INTERSECTIONS 09-06-2026.txt`

### Qué hacer ahora

No tocaría todavía la lógica de rotondas a ciegas. Primero añadiría debug.

### Cambios en Blueprint para debug de rotondas

#### En `BP_VehicleAI2`

Crear variables globales:

- `Debug_DeathActorName` string
- `Debug_DeathActorClass` string
- `Debug_DeathActorTags` string
- `Debug_TrafficControlTypeAtDeath` integer
- `Debug_IntersectionDecisionAtDeath` string
- `Debug_CurrentTriggerAtDeath` string
- `Debug_ForwardSpeedAtDeath` float
- `Debug_SteeringAtDeath` float
- `Debug_TargetSteeringAtDeath` float
- `Debug_HorizontalDistDiffAtDeath` float
- `Debug_FrontObstacleAtDeath` float
- `Debug_YawRateAtDeath` float
- `Debug_IsRoundaboutContext` boolean
- `Debug_RoundaboutExitTarget` string/integer, si puedes identificarlo
- `Debug_TimeInCurrentIntersection` float

#### En `EventActorBeginOverlap`

Justo antes de llamar a `KillCar` por colisión:

1. `Set Debug_DeathActorName = GetDisplayName(OtherActor)`
2. `Set Debug_DeathActorClass = GetClass DisplayName(OtherActor)`
3. `Set Debug_TrafficControlTypeAtDeath = TrafficControlType del AiController`
4. `Set Debug_IntersectionDecisionAtDeath = ToString(IntersectionDecision del AiController)`
5. `Set Debug_CurrentTriggerAtDeath = GetDisplayName(CurrentTrigger)`
6. `Set Debug_ForwardSpeedAtDeath = GetForwardSpeed`
7. `Set Debug_SteeringAtDeath = Steering`
8. `Set Debug_TargetSteeringAtDeath = TargetSteering`
9. `Set Debug_HorizontalDistDiffAtDeath = HorizontalDistDiff`
10. `Set Debug_FrontObstacleAtDeath = FrontObstacleDistance`
11. `Set Debug_YawRateAtDeath = AngularVelocityZ`

#### En `KillCar`

Añadir esas columnas al `SaveStringTextToFile`.

Con un test rápido de 5 generaciones podremos separar:

- si las colisiones son solo `Third/Fourth`
- si son siempre el mismo `CurrentTrigger`
- si el coche va demasiado rápido en rotonda
- si gira tarde
- si el sensor no ve el borde correcto
- si el problema es el BP de la rotonda, no la red

---

## 3. Cedas: aquí sí hay una causa clara

Este punto sí tiene una causa muy probable en Blueprint.

En `BP_Sign_Yield -> MonitorSpeed`, la condición actual es:

```text
DistanceRatio >= SpeedRatio
```

donde `DistanceRatio` viene de la distancia al `YieldLine` normalizada por `SensorEntryDistance`, y `SpeedRatio` viene de `ABS(ForwardSpeed) / MaxSpeed`. `INTERSECTIONS 09-06-2026.txt`

Eso significa que si el coche frena mucho y `SpeedRatio` se acerca a 0, la condición puede cumplirse **muy lejos de la línea**, porque `DistanceRatio >= 0` será casi siempre true. Después se marca `StoppedCorrectly = true`, se llama a `CheckCrossing`, y si la zona de cruce está ocupada, el coche queda esperando en el sitio donde fue aceptado. Esa lógica explica exactamente lo que observas: **espera casi en la entrada de la zona del ceda**.

Además, el CSV no puede medirlo bien porque `YieldValidationTime` está siempre a 0; se resetea cuando acepta el ceda. El informe ya indica `YieldValidationTime = 0.00s` de media. `informe.txt`

### Cambio mínimo necesario en `BP_Sign_Yield -> MonitorSpeed`

Busca el Branch que ahora tiene:

```text
Clamp(Abs(Dot(Location - StopTargetLocation, GetForwardVector(YieldLine))) / SensorEntryDistance)
>=
Clamp(Abs(ForwardSpeed) / MaxSpeed)
```

Cámbialo a:

```text
Clamp(Abs(Dot(Location - StopTargetLocation, StopLineForwardVector)) / SensorEntryDistance)
<=
Clamp(Abs(ForwardSpeed) / MaxSpeed)
```

Es decir: **cambiar `>=` por `<=`**.

Esto hace que el coche no pueda validar el ceda lejos de la línea. Cuanto más lento vaya, más cerca de la línea debe estar para validar.

### Cambio robusto recomendado para cedas ocupados

El cambio de comparador es necesario, pero yo añadiría una comprobación extra: **si el cruce está ocupado, no basta con estar cerca; debe estar realmente parado**.

#### Paso 1: crear función `CountYieldCrossingCars`

En `BP_Sign_Yield`, crear una función:

**Nombre:** `CountYieldCrossingCars`

**Input:**

- `TargetCar` BP_VehicleAI2

**Output:**

- `CarsInCrossing` integer

**Flujo:**

1. `Set CarsInCrossing = 0`
2. `ForEachLoop CrossingZones`
3. `GetOverlappingActors` de cada `BP_CrossingZone`
4. Por cada actor:
   - Cast a `BP_VehicleAI2`
   - Branch:
     ```text
     IsDead
     OR ArrayElement == TargetCar
     OR (StoppedCorrectly AND ForceStop)
     ```
   - Si false: `CarsInCrossing++`
5. Return `CarsInCrossing`

Esto reutiliza la misma lógica que ya tienes dentro de `CheckCrossing`. `INTERSECTIONS 09-06-2026.txt`

#### Paso 2: crear función `ComputeYieldValidationData`

En `BP_Sign_Yield`, crear función:

**Inputs:**

- `TargetCar` BP_VehicleAI2

**Outputs:**

- `IsNearYieldLine` boolean
- `IsStoppedEnough` boolean
- `CrossingOccupied` boolean
- `ShouldTimeoutAsBadYield` boolean
- `YieldSignedDistance` float
- `YieldDistanceRatio` float
- `YieldSpeedRatio` float
- `CarsInCrossing` integer

**Cálculos:**

```text
ForwardSpeedAbs = ABS(GetForwardSpeed(TargetCar))

YieldSignedDistance =
Dot(
    GetActorLocation(TargetCar) - StopTargetLocation del AIController,
    StopLineForwardVector del AIController
)

YieldDistanceRatio =
Clamp(
    ABS(YieldSignedDistance) / MAX(SensorEntryDistance, 1.0),
    0.0,
    1.0
)

YieldSpeedRatio =
Clamp(
    ForwardSpeedAbs / MaxSpeed,
    0.0,
    1.0
)

IsNearYieldLine = YieldDistanceRatio <= YieldSpeedRatio

IsStoppedEnough = ForwardSpeedAbs < MaxSpeed * 0.005

CarsInCrossing = CountYieldCrossingCars(TargetCar)

CrossingOccupied = CarsInCrossing > 0
```

Para `ShouldTimeoutAsBadYield`:

```text
ShouldTimeoutAsBadYield =
YieldValidationTime > SafeDivide(MAX(SensorEntryDistance, 1.0), MAX(ABS(AproachSpeed), 1.0))
AND IsStoppedEnough
AND NOT IsNearYieldLine
```

#### Paso 3: modificar `MonitorSpeed`

Dentro de `MonitorSpeed`, después de sumar `YieldValidationTime += 0.1`, llama a `ComputeYieldValidationData`.

Luego cambia la lógica a:

```text
Branch CrossingOccupied
```

Si `CrossingOccupied == true`:

```text
Branch IsNearYieldLine AND IsStoppedEnough
```

Si true:

1. `Set YieldValidationTime = 0.0`
2. `Set StoppedCorrectly = true`
3. `YieldCrossingCheckID++`
4. `CheckCrossing(TargetCar, YieldCrossingCheckID)`

Si false:

1. Branch `ShouldTimeoutAsBadYield`
2. Si true: `ApplyYieldDeathPenalty`
3. Si false: añadir a `PendingMonitorCars` y recheck con timer

Si `CrossingOccupied == false`:

```text
Branch IsNearYieldLine
```

Si true:

1. `Set TrafficControlType = 3`
2. `ApplyYieldCompletionBonus`
3. `Set AproachSpeed = 0.0`
4. `Set ForceStop = false`
5. Remove de `PendingMonitorCars`
6. Remove de `PendingYieldCheckCars`

Si false:

1. Añadir a `PendingMonitorCars`
2. Recheck con timer

Con esto el ceda deja de validar en la entrada y, cuando el cruce está ocupado, obliga a parar cerca del `YieldLine`.

---

## 4. Backups duplicados del modelo cargado

Aquí hay un bug claro.

En `EventBeginPlay` de `BP_EvolutionManager`, cuando existe `SuperCarModel`, cargas pesos, pero seteas:

```text
LoadedBestFitness = 0.0
```

en vez de cargar el `BestFitness` guardado del save. `EVOLUTIONMANAGER 09-06-2026.txt`

Luego, en `EndGeneration`, si `BestFitness > LoadedBestFitness`, se crea:

```text
SuperCarModel_prev_Day-Month_Hour-Minute
```

y después se guarda también `SuperCarModel`. `EVOLUTIONMANAGER 09-06-2026.txt`

Por tanto, un modelo cargado sin mutar puede superar `0.0` y disparar backup aunque los pesos sean idénticos.

### Cambio paso a paso en `BP_EvolutionManager`

#### Paso 1: corregir carga de `LoadedBestFitness`

En `EventBeginPlay`, dentro del branch donde `DoesSaveGameExist(SuperCarModel)` es true:

Ahora tienes:

```text
Set Loaded W IH = W IH del cast
Set Loaded W HO = W HO del cast
Set LoadedBestFitness = 0.0
```

Cámbialo por:

```text
Set Loaded W IH = W IH del cast
Set Loaded W HO = W HO del cast
Set LoadedBestFitness = BestFitness del cast
```

#### Paso 2: crear función `WeightsDifferentFromLoaded`

En `BP_EvolutionManager`:

**Nombre:** `WeightsDifferentFromLoaded`

**Inputs:**

- `CandidateIH` array float
- `CandidateHO` array float

**Output:**

- `Different` boolean

**Variables locales:**

- `Index` integer
- `Epsilon` float = `0.000001`

**Flujo:**

1. Branch:
   ```text
   Length(CandidateIH) != Length(Loaded_W_IH)
   OR Length(CandidateHO) != Length(Loaded_W_HO)
   ```
   Si true: return `Different = true`

2. ForLoop `0 -> Length(CandidateIH)-1`
   - Branch:
     ```text
     ABS(CandidateIH[Index] - Loaded_W_IH[Index]) > Epsilon
     ```
   - Si true: return `Different = true`

3. ForLoop `0 -> Length(CandidateHO)-1`
   - Branch:
     ```text
     ABS(CandidateHO[Index] - Loaded_W_HO[Index]) > Epsilon
     ```
   - Si true: return `Different = true`

4. Return `Different = false`

#### Paso 3: filtrar backup en `EndGeneration`

En `EndGeneration`, justo antes de crear el backup `SuperCarModel_prev_...`, añade:

```text
WeightsDifferentFromLoaded(BestWeightsInputHidden, BestWeightsHiddenOutput)
```

Luego el branch de guardado debe ser:

```text
BestFitness > LoadedBestFitness
AND
WeightsDifferentFromLoaded == true
```

Si false:

- No guardar `SuperCarModel_prev`
- No sobrescribir `SuperCarModel`
- Sí puedes mantener `SessionCarModel` si quieres conservar el mejor de la sesión, porque eso no crea duplicados históricos

Con esto, si el mejor coche es el loaded sin mutar, no hay backup.

---

## 5. Inputs de la red neuronal

La red actual usa 20 inputs:

```text
SensorCount 11
+ velocidad
+ angular velocity
+ TrafficLightState
+ DistToStopLine
+ 4 one-hot TrafficControlType
+ bias
= 20 inputs
```

Eso coincide con el esquema actual: `inputs=20`, `hidden=16`, `outputs=2`, `pesos=352`. `RED NEURONAL 09-06-2026.txt`

### Revisión estructural

No veo duplicados exactos tipo “el mismo valor metido dos veces”, porque `FrontObstacleDistance`, `DistSensorIzda` y `DistSensorDcha` se extraen de `SensorsArray`, pero no se vuelven a añadir como inputs separados.

Pero sí hay una redundancia estructural:

```text
TrafficControlType one-hot 0/1/2/3
+
bias = 1
```

Si siempre hay exactamente un one-hot activo, entonces:

```text
TrafficLight + Stop + Yield + None = 1
```

Eso hace que el one-hot `None` sea parcialmente redundante con el bias. No es un bug grave, pero no aporta mucha información nueva.

### Inputs que faltan para los problemas actuales

Para los fallos que estás viendo, faltan tres señales importantes:

1. **Distancia firmada a línea de stop/yield**, no solo distancia absoluta.
   - Ahora el input de distancia no distingue bien “antes de la línea” vs “después de la línea”.
2. **Cruce ocupado / libre**.
   - El coche no sabe directamente si debe parar en un ceda por tráfico real.
3. **Dirección/salida objetivo en rotonda**.
   - La red recibe sensores filtrados por `IntersectionDecision`, pero no recibe explícitamente “voy a la tercera salida” o “voy a la cuarta salida”.

### No cambiaría inputs todavía en el modelo cargado

Cambiar inputs invalida semánticamente los pesos guardados, aunque mantengas 20 dimensiones. Primero añadiría debug y haría un test de ablación.

### Debug recomendado para importancia de inputs

En `BP_ControllerAI`, crear:

- `Debug_InputSum` array float
- `Debug_InputSqSum` array float
- `Debug_InputMin` array float
- `Debug_InputMax` array float
- `Debug_InputTicks` integer
- `Debug_AblationGroup` integer
- `Debug_AblationInputIndex` integer

Después de `PrepareNetworksInputs`, antes de `ProcessAI`:

1. ForLoop `0 -> Length(ReadyInputs)-1`
2. `Debug_InputSum[Index] += ReadyInputs[Index]`
3. `Debug_InputSqSum[Index] += ReadyInputs[Index] * ReadyInputs[Index]`
4. actualizar min/max
5. `Debug_InputTicks++`

En `KillCar`, exportar al CSV al menos:

```text
I00_Avg, I01_Avg, ..., I19_Avg
I00_Std, I01_Std, ..., I19_Std
Debug_AblationGroup
Debug_AblationInputIndex
```

### Test rápido de ablación

En `StartTesting`, asignar por `CarIndex % 6`:

| Grupo | Ablación |
|---|---|
| 0 | Control, sin tocar inputs |
| 1 | `TrafficLightState = 1.0` |
| 2 | `DistToStopLine = 1.0` |
| 3 | `AngularVelocityZ = 0.0` |
| 4 | one-hot `TrafficControlType` forzado a `None` |
| 5 | sensores extremos izquierda/derecha forzados a `1.0` |

En `PrepareNetworksInputs`, justo antes del return, aplicar la ablación según grupo. Luego comparar `SuccessRate`, colisiones, stop/yield completados y fitness medio por grupo.

---

## 6. Fitness: peso real de cada componente

El fitness está dominado por `Acum_A` / `Acum_NetNormal`.

| Componente | Media | Ratio sobre fitness medio |
|---|---:|---:|
| `Acum_A` | 31,451.83 | **91.1%** |
| `Acum_NetNormal` | 31,473.61 | **91.2%** |
| `StopCompletionBonus` | 4,078.04 | 11.8% |
| `Acum_PenaltyVelocidad` | 1,995.90 | 5.8% |
| `YieldCompletionBonus` | 1,651.30 | 4.8% |
| `Penalty_Muerte` | 627.05 | 1.8% |
| `WaitBonus` | 625.33 | 1.8% |
| `Penalty_SteerApproach` | 431.13 | 1.25% |
| `Penalty_Creeping` | 238.51 | 0.69% |
| `Acum_F` | 21.78 | 0.06% |

El informe también detecta que `A` y `Net normal` tienen correlación altísima con fitness final, mientras que `F` es prácticamente irrelevante en magnitud. `informe.txt`

### Interpretación

El modelo está siendo premiado sobre todo por:

```text
vivir más tiempo + avanzar/centrarse
```

No necesariamente por “resolver bien” cada intersección.

Pero no tocaría todavía los pesos del fitness por una razón: las colisiones ya castigan muchísimo de forma indirecta porque cortan la acumulación de `Acum_A`.

Comparación:

| Familia | Fitness medio | Tiempo medio |
|---|---:|---:|
| `TIMEFINISHED` | 68,108 | 100 s |
| Colisión | 18,212 | 32.6 s |

La muerte por colisión no necesita una penalización mucho mayor: **la muerte ya impide acumular fitness**. El problema es que el coche no está recibiendo o usando suficiente información para evitar esos hotspots.

---

## 7. Penalizaciones y muertes

Con este test no se puede evaluar bien la restrictividad de todas las muertes, porque solo aparecen:

- `TIMEFINISHED`
- `COLLISION_WITH_...`

No aparecen:

- `LAZY`
- `REVERSE`
- `REVERSING_WRONG`
- `TRAFFIC_VIOLATION`
- `STOP_VIOLATION`
- `YIELD_VIOLATION`
- `NAV_VIOLATION`

Así que no cambiaría esas muertes todavía.

Sí se puede concluir esto:

### Colisión

Muy influyente. Causa el **67.31%** de fallos. Es restrictiva, pero debe serlo.

### `Penalty_Muerte`

No es enorme en magnitud media, pero no necesita serlo. El castigo real es terminar el episodio.

### `Penalty_Velocidad`

Es la penalización media más grande, pero en correlación bruta aparece positiva porque los coches que viven más tiempo acumulan más de todo. Por segundo, sí se comporta como penalización: mayor `Penalty_Velocidad/s` se asocia a peor fitness.

### `Penalty_SteerApproach` y `Creeping`

No las subiría todavía. Aparecen más altas en coches que sobreviven más porque pasan por más stops/cedas. El informe ya avisa que `SteerApproach` supera a `SteeringWhileStopped`, pero eso no demuestra que sea demasiado baja o alta. `informe.txt`

---

# Cambios que haría ahora, en orden

## Cambio 1 - Obligatorio: backup duplicado

En `BP_EvolutionManager`:

1. En `EventBeginPlay`, al cargar `SuperCarModel`, cambiar:
   ```text
   LoadedBestFitness = 0.0
   ```
   por:
   ```text
   LoadedBestFitness = BestFitness del save cargado
   ```

2. Crear `WeightsDifferentFromLoaded`.

3. En `EndGeneration`, antes de guardar `SuperCarModel_prev_...`, exigir:
   ```text
   BestFitness > LoadedBestFitness
   AND
   WeightsDifferentFromLoaded == true
   ```

Esto evita backups del loaded sin mutar.

---

## Cambio 2 - Obligatorio: ceda acepta parada demasiado lejos

En `BP_Sign_Yield -> MonitorSpeed`:

1. Cambiar el comparador:
   ```text
   DistanceRatio >= SpeedRatio
   ```
   por:
   ```text
   DistanceRatio <= SpeedRatio
   ```

2. Añadir `ComputeYieldValidationData`.

3. Si el cruce está ocupado:
   ```text
   StoppedCorrectly = true
   ```
   solo cuando:
   ```text
   IsNearYieldLine AND IsStoppedEnough
   ```

4. Si el cruce está libre:
   liberar solo cuando el coche esté cerca de la línea de decisión, no al entrar en la zona.

---

## Cambio 3 - Obligatorio antes de tocar rotondas: debug de rotonda/colisión

Añadir al CSV:

```text
DeathActorName
DeathActorClass
TrafficControlTypeAtDeath
IntersectionDecisionAtDeath
CurrentTriggerAtDeath
ForwardSpeedAtDeath
SteeringAtDeath
TargetSteeringAtDeath
HorizontalDistDiffAtDeath
FrontObstacleAtDeath
YawRateAtDeath
IsRoundaboutContext
RoundaboutExitTarget
TimeInCurrentIntersection
```

Después hacer un test corto igual a este.

---

## Cambio 4 - No inmediato: inputs

No cambiaría la red cargada todavía.

Primero añadiría:

```text
InputAvg_0..19
InputStd_0..19
InputMin_0..19
InputMax_0..19
AblationGroup
```

Luego haría un test de ablación. Si los datos confirman que `DistToStopLine`, `TrafficControlType` o sensores laterales son críticos, entonces sí rediseñamos inputs.

---

## Cambio 5 - No inmediato: fitness

No tocaría aún los pesos del fitness.

El problema actual no parece que el coche “quiera” chocar porque el fitness lo premie. El problema es que:

```text
67% muere por colisión
70.9% de esas colisiones ocurren antes de 40 s
top 8 objetos explican 66.9% de colisiones
```

Eso apunta a problema de ruta/geometría/sensores/contexto, no a escala de penalizaciones.

## Prompt:
10/6/2026, 14:32:22

voy a ir paso a paso y revisa los cambios: primero con lo de los backups duplicados

[Attachment: EVOLUTIONMANAGER 10-06-2026.txt]

## Response:
10/6/2026, 14:32:10

> **Revisando inconsistencias en el código**
>
> Necesito revisar un posible error en la función WeightsDifferentFromLoaded, revisando la condición que dice "Si es false hay ReturnNode(Different=True)", que parece un error de texto; debería decir "si es true return true". También encontré inconsistencias como CandidateOH vs CandidateHO y un error tipográfico en Loaded_W_OH y Loaded_W_HO.
>
> Pensó durante 16s

Sí, vas bien. El cambio principal está aplicado correctamente, pero hay **un fallo importante en `WeightsDifferentFromLoaded`** que debes revisar antes de darlo por cerrado.

## Lo que está bien

### 1. `LoadedBestFitness` ya se carga desde el save

Antes el problema era que al cargar `SuperCarModel` hacías:

```text
LoadedBestFitness = 0.0
```

Ahora lo tienes como:

```text
LoadedBestFitness = BestFitness del cast
```

Eso está correcto. Así ya no comparas contra 0 por error al arrancar con un modelo guardado. `EVOLUTIONMANAGER 10-06-2026.txt`

---

### 2. El backup ahora depende de pesos diferentes

En `EndGeneration` has añadido:

```text
WeightsDifferentFromLoaded(
    CandidateIH = BestWeightsInputHidden,
    CandidateOH = BestWeightsHiddenOutput
)
```

y luego el branch:

```text
BestFitness > LoadedBestFitness
AND
Different output WeightsDifferentFromLoaded
```

Esto es exactamente la idea correcta: solo guardar `SuperCarModel_prev_...` si el modelo mejora al loaded **y además sus pesos son distintos**. `EVOLUTIONMANAGER 10-06-2026.txt`

---

## Lo que tienes que corregir

## Error 1 - Branch inicial de `WeightsDifferentFromLoaded`

En tu descripción aparece esto:

```text
Branch:
Length(CandidateIH) != Length(Loaded_W_IH)
OR
Length(CandidateHO) != Length(Loaded_W_HO)

Si es false hay ReturnNode(Different = True)
```

Eso está al revés.

Debe ser:

```text
Si TRUE  -> Return Different = True
Si FALSE -> continuar a comparar pesos uno por uno
```

Porque si las longitudes son diferentes, obviamente los pesos son diferentes.  
Si las longitudes son iguales, entonces hay que entrar a los bucles.

### Blueprint correcto

En `WeightsDifferentFromLoaded`:

1. Branch condition:

```text
Length(CandidateIH) != Length(Loaded_W_IH)
OR
Length(CandidateHO) != Length(Loaded_W_HO)
```

2. Pin `True`:

```text
ReturnNode Different = True
```

3. Pin `False`:

```text
ForLoop CandidateIH
```

No conectes el `Return True` al pin `False`.

---

## Error 2 - Inconsistencia `HO` / `OH`

Veo nombres mezclados:

```text
CandidateHO
CandidateOH
Loaded_W_HO
Loaded_W_OH
```

Esto debe quedar **todo igual**. Usa siempre `HO`, porque tu variable real es `Loaded_W_HO`.

### Debe quedar así

Inputs de la función:

```text
CandidateIH
CandidateHO
```

Primer branch:

```text
Length(CandidateIH) != Length(Loaded_W_IH)
OR
Length(CandidateHO) != Length(Loaded_W_HO)
```

Segundo bucle:

```text
ForLoop 0 -> Length(CandidateHO) - 1
```

Branch del segundo bucle:

```text
ABS(CandidateHO[Index] - Loaded_W_HO[Index]) > Epsilon
```

No uses `CandidateOH` ni `Loaded_W_OH`.

---

# Versión final correcta de `WeightsDifferentFromLoaded`

Déjala así:

```text
WeightsDifferentFromLoaded

Inputs:
- CandidateIH array float
- CandidateHO array float

Output:
- Different boolean

Local:
- Index integer
- Epsilon float = 0.000001
```

### Flujo

```text
Branch:
Length(CandidateIH) != Length(Loaded_W_IH)
OR
Length(CandidateHO) != Length(Loaded_W_HO)
```

### Si TRUE

```text
Return Different = True
```

### Si FALSE

Primer bucle:

```text
ForLoop
FirstIndex = 0
LastIndex = Length(CandidateIH) - 1
```

Dentro:

```text
Branch:
ABS(CandidateIH[Index] - Loaded_W_IH[Index]) > Epsilon
```

Si true:

```text
Return Different = True
```

Al completar el primer bucle, segundo bucle:

```text
ForLoop
FirstIndex = 0
LastIndex = Length(CandidateHO) - 1
```

Dentro:

```text
Branch:
ABS(CandidateHO[Index] - Loaded_W_HO[Index]) > Epsilon
```

Si true:

```text
Return Different = True
```

Al completar el segundo bucle:

```text
Return Different = False
```

---

# `EndGeneration` queda bien así

La lógica correcta en `EndGeneration` es:

```text
Si CurrentBestFitness > BestFitness:
    guardar SessionCarModel

    llamar WeightsDifferentFromLoaded

    Branch:
    BestFitness > LoadedBestFitness
    AND
    Different == True
```

### Si false

No hacer backup.  
No sobrescribir `SuperCarModel`.

### Si true

Guardar:

```text
SuperCarModel_prev_...
SuperCarModel
```

y actualizar:

```text
LoadedBestFitness = BestFitness
Loaded_W_IH = BestWeightsInputHidden
Loaded_W_HO = BestWeightsHiddenOutput
```

Esto último ya lo tienes bien. `EVOLUTIONMANAGER 10-06-2026.txt`

---

## Conclusión

El cambio está **casi correcto**, pero antes de pasar al siguiente punto corrige estas dos cosas:

1. En `WeightsDifferentFromLoaded`, el branch de longitudes debe devolver `Different=True` por el pin **True**, no por el false.
2. Unifica todos los nombres como `CandidateHO` y `Loaded_W_HO`.

Cuando eso esté corregido, la lógica de backups duplicados queda bien cerrada.

## Prompt:
10/6/2026, 14:34:04

ahora?

[Attachment: EVOLUTIONMANAGER 10-06-2026.txt]

## Response:
10/6/2026, 14:33:53

> **Revisando detalles técnicos y posibles errores**
>
> La función usa todavía CandidateOH / Loaded_W_OH en el segundo ciclo, aunque deberían ser CandidateHO / Loaded_W_HO. También, en la llamada "EndGeneration", el parámetro CandidateOH podría ser un error por un posible desajuste de entrada. También, hay que observar el caso borde de un ciclo donde LastIndex es -1 si las longitudes son cero.
>
> Pensó durante 9s

Casi. **El branch inicial ya está corregido**, pero todavía queda **un error de nombres en la segunda mitad de `WeightsDifferentFromLoaded`**.

## Está bien corregido

Ahora tienes:

```text
Branch:
Length(CandidateIH) != Length(Loaded_W_IH)
OR
Length(CandidateHO) != Length(Loaded_W_HO)

Si true -> Return Different = True
Si false -> comparar pesos
```

Eso ya está correcto. Si las longitudes son distintas, devuelve `Different = True`; si son iguales, compara peso a peso. `EVOLUTIONMANAGER 10-06-2026.txt`

También sigue bien esto:

```text
LoadedBestFitness = BestFitness del cast
```

y en `EndGeneration`:

```text
BestFitness > LoadedBestFitness
AND
Different output WeightsDifferentFromLoaded
```

La lógica general ya está bien.

---

## Lo que falta corregir

En la función declaras los inputs como:

```text
CandidateIH
CandidateHO
```

pero en el segundo bucle todavía aparece:

```text
Length(CandidateOH) - 1
ABS(CandidateOH[Index] - Loaded_W_OH[Index]) > Epsilon
```

Eso está mal. Debe ser **HO**, no **OH**.

### Corrige el segundo bucle así

Donde tienes:

```text
ForLoop:
LastIndex = Length(CandidateOH) - 1
```

cámbialo por:

```text
ForLoop:
LastIndex = Length(CandidateHO) - 1
```

Y donde tienes:

```text
ABS(CandidateOH[Index] - Loaded_W_OH[Index]) > Epsilon
```

cámbialo por:

```text
ABS(CandidateHO[Index] - Loaded_W_HO[Index]) > Epsilon
```

---

## Revisa también la llamada en `EndGeneration`

Ahora aparece:

```text
WeightsDifferentFromLoaded(
    CandidateIH = BestWeightsInputHidden,
    CandidateOH = BestWeightsHiddenOutput
)
```

Pero la función tiene input `CandidateHO`, no `CandidateOH`.

Déjalo así:

```text
WeightsDifferentFromLoaded(
    CandidateIH = BestWeightsInputHidden,
    CandidateHO = BestWeightsHiddenOutput
)
```

---

## Veredicto

La lógica ya está correcta, pero **no lo des por cerrado hasta cambiar todos los `OH` por `HO`**:

```text
CandidateOH  -> CandidateHO
Loaded_W_OH  -> Loaded_W_HO
```

Después de eso, el tema de backups duplicados queda bien cerrado.

## Prompt:
10/6/2026, 14:35:22

AHORA?

[Attachment: EVOLUTIONMANAGER 10-06-2026.txt]

## Response:
10/6/2026, 14:35:11

> **Revisando posible error tipográfico y explicación de variables**
>
> Parece que hay un error tipográfico en el nombre "LoadedBestFitnees", que debería ser "LoadedBestFitness". Este podría ser un error en la descripción o exportación. Si el nodo Blueprint apunta a una variable real, estaría bien, pero si se creó una variable nueva, el error es relevante. Sugiero probar que al cargar un gen no mutado, no se cree un respaldo.
>
> Pensó durante 9s

Ahora sí: **la lógica de backups duplicados queda correcta**.

Has corregido lo importante:

1. En `EventBeginPlay`, al cargar `SuperCarModel`, ahora haces:

```text id="j3qk5n"
LoadedBestFitness = BestFitness del cast
```

Correcto. Ya no comparas contra `0.0`. `EVOLUTIONMANAGER 10-06-2026.txt`

2. En `EndGeneration`, llamas correctamente a:

```text id="4biv0e"
WeightsDifferentFromLoaded(
    CandidateIH = BestWeightsInputHidden,
    CandidateHO = BestWeightsHiddenOutput
)
```

Correcto. Ya no aparece `CandidateOH`. `EVOLUTIONMANAGER 10-06-2026.txt`

3. La condición de guardado de backup queda:

```text id="ld3a08"
BestFitness > LoadedBestFitness
AND
Different == True
```

Correcto. Así, si el modelo sin mutar supera al loaded pero tiene los mismos pesos, **no crea backup duplicado**. `EVOLUTIONMANAGER 10-06-2026.txt`

4. `WeightsDifferentFromLoaded` ya está bien:

```text id="4ey2km"
Si Length distinto -> Different = True
Si algún peso IH distinto -> Different = True
Si algún peso HO distinto -> Different = True
Si todo igual -> Different = False
```

Correcto. `EVOLUTIONMANAGER 10-06-2026.txt`

## Única cosa que revisaría visualmente

En la descripción aparece:

```text id="twdsq6"
LoadedBestFitnees
```

con una `e` de más en `Fitnees`.

Si en Unreal es simplemente una errata del texto exportado, no pasa nada. Pero si por accidente has creado/seleccionado otra variable distinta, debe ser la variable real:

```text id="hni61s"
LoadedBestFitness
```

## Veredicto

Puedes dar este punto por cerrado.  
El comportamiento esperado ahora es:

| Caso | Guarda `SessionCarModel` | Guarda backup `SuperCarModel_prev` | Sobrescribe `SuperCarModel` |
|---|---:|---:|---:|
| Mejor sesión, mismos pesos que loaded | Sí | No | No |
| Mejor sesión, pesos distintos, fitness > loaded | Sí | Sí | Sí |
| No mejora `BestFitness` | No | No | No |

Siguiente paso: podemos pasar al problema del ceda que valida demasiado lejos.

## Prompt:
10/6/2026, 15:15:44

bien, seguimos, vamos con los cedas, comprueba los cambios:

para la funcion de ComputeYieldValidationData, creo que son demasiados outputs, y que lo ideal sería juntar algunos, no simplificarlo, porque imagino que todos los calculos son necesarios

[Attachment: INTERSECTIONS 10-06-2026.txt]

## Response:
10/6/2026, 15:15:32

> **Evaluando el mejor enfoque para outputs y citas**
>
> Parece que no necesito incluir números de línea en la cita final. De todas formas, debería asegurarme de incluir una referencia al archivo. Para las salidas del cálculo, parece mejor agruparlas en tres valores lógicos y algunos flotantes opcionales, sin complicar demasiado para mantener las cosas más claras en los planos.
>
> **Evaluando ajustes para la validación del cruce**
>
> He identificado algunos cambios clave: ahora se configura correctamente el StopLineForwardVector en OnBeginOverlap, y se han realizado ajustes favorables en MonitorSpeed y CountYieldCrossingCars. Sin embargo, MonitorSpeed aún valida el ceda paso antes de comprobar la ocupación del cruce. Si está ocupado, ¿debería requerir una parada completa más cercana al ceda?
>
> Pensó durante 16s

Vas bien, pero **todavía no está cerrado el cambio de los cedas**.

Has corregido una parte importante, pero falta la parte que realmente diferencia:

```text
cruce libre  -> puede continuar si está en punto válido
cruce ocupado -> debe parar de verdad cerca del YieldLine
```

## Lo que ya está bien

### 1. `StopLineForwardVector` ya se setea en el ceda

En `BP_Sign_Yield -> OnComponentBeginOverlap`, ahora haces:

```text id="279atu"
Set StopLineForwardVector = GetForwardVector(YieldLine)
Set StopTargetLocation = GetWorldPosition(YieldLine)
```

Correcto. Así ya no dependes de `GetForwardVector(YieldLine)` suelto dentro de cada cálculo, y mantienes la misma lógica que en STOP. `INTERSECTIONS 10-06-2026.txt`

---

### 2. Has cambiado el comparador principal

Antes el problema era:

```text id="kps1k6"
DistanceRatio >= SpeedRatio
```

Ahora lo tienes como:

```text id="9jxdu5"
DistanceRatio <= SpeedRatio
```

Esto es correcto y arregla gran parte del problema de validar demasiado pronto. `INTERSECTIONS 10-06-2026.txt`

Con el comparador viejo, cuando el coche iba lento, `SpeedRatio` era casi 0, así que `DistanceRatio >= 0` se cumplía muy lejos.  
Con el nuevo, si el coche va lento, necesita estar mucho más cerca del `YieldLine`.

---

### 3. `CountYieldCrossingCars` está bien planteada

La función cuenta coches vivos dentro de las `CrossingZones`, ignorando:

```text id="s1jq8q"
IsDead
TargetCar
StoppedCorrectly AND ForceStop
```

Esto está bien, porque evita contar al propio coche y evita contar coches que están esperando legalmente. `INTERSECTIONS 10-06-2026.txt`

---

# Lo que falta

## Problema principal: `MonitorSpeed` aún valida antes de mirar si el cruce está ocupado

Ahora mismo `MonitorSpeed` hace esto:

```text id="1j7ndg"
Si DistanceRatio <= SpeedRatio:
    YieldValidationTime = 0
    StoppedCorrectly = true
    YieldCrossingCheckID++
    CheckCrossing(...)
```

El problema es que **marca `StoppedCorrectly = true` antes de saber si el cruce está ocupado**. `INTERSECTIONS 10-06-2026.txt`

Eso significa que, si el cruce está ocupado, el coche puede quedar aceptado como “correcto” aunque solo haya llegado a la condición dinámica de aproximación, no necesariamente parado a tope.

Para ceda libre está bien que no siempre pare.  
Para ceda ocupado, no.

---

# Sobre `ComputeYieldValidationData`: sí, tienes razón

Estoy de acuerdo contigo: **demasiados outputs ensucian el Blueprint**.

No hace falta sacar 7 u 8 outputs. Los cálculos sí son necesarios, pero los outputs pueden agruparse.

Yo lo dejaría con **3 outputs**, o como máximo 4.

## Opción recomendada: 3 outputs

Crear función:

```text id="yccjwp"
ComputeYieldValidationData
```

### Inputs

```text id="taxgap"
TargetCar BP_VehicleAI2
```

### Variables locales internas

```text id="bo9vhq"
ForwardSpeedAbs float
SignedDistanceToYieldLine float
YieldDistanceRatio float
YieldSpeedRatio float
CarsInCrossing integer
CrossingOccupied boolean
IsNearYieldLine boolean
IsStoppedEnough boolean
```

### Outputs

```text id="lxb12t"
CanValidateFreeYield boolean
CanValidateBlockedYield boolean
ShouldKeepMonitoring boolean
```

No sacaría `DistanceRatio`, `SpeedRatio`, `CarsInCrossing`, etc. como outputs salvo que los quieras para debug. Para lógica normal, no hacen falta fuera.

---

# Cómo debe calcularse internamente

Dentro de `ComputeYieldValidationData`:

```text id="4k1mfm"
ForwardSpeedAbs = ABS(GetForwardSpeed(TargetCar))
```

```text id="4cj264"
SignedDistanceToYieldLine =
Dot(
    GetActorLocation(TargetCar) - StopTargetLocation del AIController,
    StopLineForwardVector del AIController
)
```

```text id="pzsbyb"
YieldDistanceRatio =
ClampFloat(
    ABS(SignedDistanceToYieldLine) / MAX(SensorEntryDistance, 1.0),
    0.0,
    1.0
)
```

```text id="ex1ns9"
YieldSpeedRatio =
ClampFloat(
    ForwardSpeedAbs / MaxSpeed,
    0.0,
    1.0
)
```

```text id="c8mmgx"
CarsInCrossing = CountYieldCrossingCars(TargetCar)
CrossingOccupied = CarsInCrossing > 0
```

```text id="xgusuy"
IsNearYieldLine = YieldDistanceRatio <= YieldSpeedRatio
```

```text id="rggl00"
IsStoppedEnough = ForwardSpeedAbs < MaxSpeed * 0.005
```

Y los outputs:

```text id="9pomvw"
CanValidateFreeYield =
NOT CrossingOccupied
AND IsNearYieldLine
```

```text id="uoh694"
CanValidateBlockedYield =
CrossingOccupied
AND IsNearYieldLine
AND IsStoppedEnough
```

```text id="uoqr8l"
ShouldKeepMonitoring =
NOT CanValidateFreeYield
AND NOT CanValidateBlockedYield
```

Esto mantiene todos los cálculos importantes, pero la función devuelve solo decisiones útiles.

---

# Cómo modificar `MonitorSpeed`

Ahora mismo tienes el branch grande de:

```text id="tdm0bi"
DistanceRatio <= SpeedRatio
```

Yo lo sustituiría por llamada a `ComputeYieldValidationData`.

## Flujo recomendado

Después del guard inicial:

```text id="7uovsc"
IsDead OR NOT ForceStop OR StoppedCorrectly OR TrafficControlType != 2
```

si false:

```text id="hlavdn"
YieldValidationTime += 0.1
```

Luego:

```text id="twb4rk"
ComputeYieldValidationData(TargetCar)
```

Después:

### Branch 1

```text id="4p2j0t"
CanValidateBlockedYield
```

Si true:

```text id="qvhok7"
Set YieldValidationTime = 0.0
Set StoppedCorrectly = true
YieldCrossingCheckID++
CheckCrossing(TargetCar, YieldCrossingCheckID)
```

### Si false, Branch 2

```text id="99gvww"
CanValidateFreeYield
```

Si true:

```text id="a38g6f"
Set YieldValidationTime = 0.0
Set StoppedCorrectly = true
YieldCrossingCheckID++
CheckCrossing(TargetCar, YieldCrossingCheckID)
```

También podrías liberar directamente aquí, pero yo prefiero mantener `CheckCrossing` porque así confirmas el cruce libre justo antes de liberar.

### Si false

```text id="j1ns8q"
AddUnique PendingMonitorCars(TargetCar)
Branch NOT MonitorTimerActive
    Set MonitorTimerActive = true
    SetTimerByEvent 0.1 -> Recheck_MonitorStop
```

---

# Cambio opcional pero recomendable: usar `CountYieldCrossingCars` dentro de `CheckCrossing`

Ahora `CheckCrossing` vuelve a repetir todo el conteo de crossing zones. No está mal, pero ya que has creado `CountYieldCrossingCars`, puedes simplificar.

En `CheckCrossing`, sustituye:

```text id="fi327f"
Set CarsAlivedInCrossingZone = 0
ForEach CrossingZones
    GetOverlappingActors...
    ++ CarsAlivedInCrossingZones
```

por:

```text id="7qd86b"
CountYieldCrossingCars(TargetCar)
Set CarsAlivedInCrossingZone = CarsInCrossing
```

Luego dejas igual:

```text id="5hhwn0"
Branch CarsAlivedInCrossingZone > 0
```

Esto evita duplicar lógica.

---

# ¿Necesitamos timeout para ceda?

De momento, **no lo metería todavía**.

Primero arreglaría:

1. `ComputeYieldValidationData`
2. `MonitorSpeed` usando `CanValidateBlockedYield` y `CanValidateFreeYield`
3. `CheckCrossing` reutilizando `CountYieldCrossingCars`

Luego hacemos un test corto. Si vemos coches parados eternamente lejos o bloqueados, entonces añadimos:

```text id="j3mfe2"
ShouldTimeoutAsBadYield
```

como cuarto output.

Pero ahora mismo no lo metería para no endurecer de más.

---

# Veredicto

Tu cambio actual mejora el problema, pero **todavía puede validar un ceda ocupado sin exigir parada completa**.

Para cerrarlo, haz esto:

1. Mantén el cambio `<=`.
2. Mantén `CountYieldCrossingCars`.
3. Crea `ComputeYieldValidationData` con solo estos 3 outputs:
   ```text
   CanValidateFreeYield
   CanValidateBlockedYield
   ShouldKeepMonitoring
   ```
4. En `MonitorSpeed`, no marques `StoppedCorrectly = true` solo por `DistanceRatio <= SpeedRatio`; hazlo solo si:
   ```text
   CanValidateFreeYield OR CanValidateBlockedYield
   ```
5. Para ceda ocupado, exige:
   ```text
   IsNearYieldLine AND IsStoppedEnough
   ```

Así queda más limpio y no necesitas sacar 8 outputs de la función.

## Prompt:
10/6/2026, 16:01:24

vale revisa los cambios:

para ShouldKeepMonitoring, creo que lo mejor sería eliminarla, ya que se puede calcular luego si fuese necesario, y solo depende de los otros ouputs

[Attachment: INTERSECTIONS 10-06-2026.txt]

## Response:
10/6/2026, 16:01:12

> **Revisando cuestiones de lógica y validación**
>
> Necesito revisar la lógica y asegurarme de que todo esté correcto. Actualmente, el sistema solo devuelve dos salidas: "Bloqueado" o "Libre". Al ocupar y detener el vehículo, la validación debe ser más flexible, por lo que quiero ajustar el cálculo para permitir una ventana de validación más amplia, sin ser demasiado estricta.
>
> Pensó durante 13s

Sí, estoy de acuerdo: **`ShouldKeepMonitoring` se puede eliminar**. No aporta información nueva, porque siempre sería:

```text id="l239gj"
ShouldKeepMonitoring =
NOT CanValidateBlockedYield
AND NOT CanValidateFreeYield
```

Así que has hecho bien dejando solo:

```text id="l60x6s"
CanValidateBlockedYield
CanValidateFreeYield
```

Eso simplifica el Blueprint sin perder lógica. `INTERSECTIONS 10-06-2026.txt`

## Lo que está bien ahora

### 1. `MonitorSpeed` ya no valida directamente con la comparación antigua

Ahora haces:

```text id="5kzdbj"
ComputeYieldValidationData(TargetCar)
```

y después:

```text id="48lqno"
Branch CanValidateBlockedYield
Branch CanValidateFreeYield
Else -> AddUnique PendingMonitorCars
```

Esto está bien. Ya no marcas `StoppedCorrectly = true` solo por `DistanceRatio <= SpeedRatio`. `INTERSECTIONS 10-06-2026.txt`

---

### 2. `CheckCrossing` ya reutiliza `CountYieldCrossingCars`

También está bien. Antes duplicabas el conteo dentro de `CheckCrossing`; ahora llamas a:

```text id="o4j2fo"
CountYieldCrossingCars(TargetCar)
```

y luego haces:

```text id="zlvjuh"
CarsAlivedInCrossingZone = CarsInCrossing
Branch CarsAlivedInCrossingZones > 0
```

Esto deja la lógica más limpia y evita errores por tener dos conteos distintos. `INTERSECTIONS 10-06-2026.txt`

---

### 3. La separación entre ceda libre y ceda bloqueado está bien planteada

Ahora `ComputeYieldValidationData` devuelve:

```text id="iijhbx"
CanValidateBlockedYield =
CrossingOccupied AND IsNearYieldLine AND IsStoppedEnough
```

y:

```text id="tqvymb"
CanValidateFreeYield =
IsNearYieldLine AND NOT CrossingOccupied
```

Conceptualmente es correcto: si el cruce está libre, no obligas a parar; si está ocupado, sí obligas a estar parado. `INTERSECTIONS 10-06-2026.txt`

---

# El problema que queda

Hay un detalle importante: tu `IsNearYieldLine` actual es demasiado estricto cuando el coche está parado.

Ahora tienes:

```text id="ohk3m9"
IsNearYieldLine = YieldDistanceRatio <= YieldSpeedRatio
```

y:

```text id="t58fwr"
YieldSpeedRatio = ForwardSpeedAbs / MaxSpeed
```

El problema es que, si el coche está parado o casi parado:

```text id="rcx0dq"
ForwardSpeedAbs ≈ 0
YieldSpeedRatio ≈ 0
```

Entonces `IsNearYieldLine` solo será true si:

```text id="6rsr3m"
YieldDistanceRatio <= 0
```

o sea, prácticamente si está **exactamente encima del YieldLine**. Eso en Unreal casi nunca va a pasar.

Resultado probable: cuando el cruce esté ocupado, el coche puede frenar bien cerca del ceda, pero `CanValidateBlockedYield` no se activará porque `IsNearYieldLine` exige distancia casi cero.

---

# Corrección recomendada

Mantén los 2 outputs. No añadas `ShouldKeepMonitoring`.

Lo que cambiaría es el cálculo interno de `IsNearYieldLine`.

## Añade una variable local

En `ComputeYieldValidationData`, añade:

```text id="42o7tk"
StoppedYieldWindowRatio float
```

Y calcula:

```text id="yi9kvp"
StoppedYieldWindowRatio =
ClampFloat(
    SafeDivide(
        GetActorBounds BoxExtent X del TargetCar,
        MAX(SensorEntryDistance, 1.0)
    ),
    0.0,
    1.0
)
```

Si te resulta complicado sacar `BoxExtent X`, puedes usar la longitud aproximada del coche con `GetActorBounds`, pero la idea es que la ventana permitida sea dinámica según el tamaño del coche y la distancia de entrada, no un número mágico.

Después cambia `IsNearYieldLine`.

Ahora:

```text id="n0scei"
IsNearYieldLine = YieldDistanceRatio <= YieldSpeedRatio
```

Cámbialo por:

```text id="50mbgm"
IsNearYieldLine =
YieldDistanceRatio <= MAX(YieldSpeedRatio, StoppedYieldWindowRatio)
```

Así:

- si el coche va rápido, la ventana depende de la velocidad;
- si el coche va muy lento o parado, todavía tiene una ventana física razonable cerca del `YieldLine`;
- no necesita estar exactamente en distancia 0.

---

# Versión final recomendada de `ComputeYieldValidationData`

Déjala con estos outputs:

```text id="ai3ckw"
CanValidateBlockedYield boolean
CanValidateFreeYield boolean
```

Variables locales:

```text id="tet7bn"
ForwardSpeedAbs
SignedDistanceToYieldLine
YieldDistanceRatio
YieldSpeedRatio
StoppedYieldWindowRatio
LocalCarsInCrossing
CrossingOccupied
IsNearYieldLine
IsStoppedEnough
```

Cálculo clave:

```text id="kzhes9"
YieldDistanceRatio =
ClampFloat(
    ABS(SignedDistanceToYieldLine) / MAX(SensorEntryDistance, 1.0),
    0.0,
    1.0
)
```

```text id="gx6kuh"
YieldSpeedRatio =
ClampFloat(
    ForwardSpeedAbs / MaxSpeed,
    0.0,
    1.0
)
```

```text id="13zv2h"
StoppedYieldWindowRatio =
ClampFloat(
    SafeDivide(GetActorBounds_BoxExtentX(TargetCar), MAX(SensorEntryDistance, 1.0)),
    0.0,
    1.0
)
```

```text id="u384ui"
IsNearYieldLine =
YieldDistanceRatio <= MAX(YieldSpeedRatio, StoppedYieldWindowRatio)
```

```text id="hmg2aw"
IsStoppedEnough =
ForwardSpeedAbs < MaxSpeed * 0.005
```

Return:

```text id="5t9jcx"
CanValidateBlockedYield =
CrossingOccupied AND IsNearYieldLine AND IsStoppedEnough
```

```text id="k1959r"
CanValidateFreeYield =
NOT CrossingOccupied AND IsNearYieldLine
```

---

## Veredicto

El cambio está **mucho mejor** y la estructura ya es correcta. Solo falta corregir `IsNearYieldLine`, porque con la fórmula actual el ceda bloqueado puede exigir una parada matemáticamente perfecta sobre la línea.

No recuperes `ShouldKeepMonitoring`; está bien eliminado.

## Prompt:
10/6/2026, 16:10:33

revisa los cambios:

[Attachment: INTERSECTIONS 10-06-2026.txt]

## Response:
10/6/2026, 16:10:20

El cambio está **casi correcto**, pero hay un detalle importante en `StoppedYieldWindowRatio`: ahora mismo lo calculas con `BreakVectorX(GetActorBounds(TargetCar))`, y eso probablemente no es el valor correcto.

## Lo que está bien

### 1. `ComputeYieldValidationData` mantiene solo 2 outputs

Correcto:

```text id="0rjzvd"
CanValidateBlockedYield
CanValidateFreeYield
```

`ShouldKeepMonitoring` sigue eliminado, y está bien porque se deduce de:

```text id="jrqak6"
NOT CanValidateBlockedYield AND NOT CanValidateFreeYield
```

---

### 2. `MonitorSpeed` usa bien los dos outputs

La estructura actual está bien:

```text id="7ny7ra"
ComputeYieldValidationData
Branch CanValidateBlockedYield
    -> YieldValidationTime = 0
    -> StoppedCorrectly = true
    -> YieldCrossingCheckID++
    -> CheckCrossing

Else Branch CanValidateFreeYield
    -> mismo flujo

Else
    -> PendingMonitorCars
    -> Timer 0.1
```

Esto ya separa correctamente ceda libre y ceda bloqueado. `INTERSECTIONS 10-06-2026.txt`

---

### 3. La lógica conceptual del ceda ya está bien

Ahora tienes:

```text id="tuzk61"
CanValidateBlockedYield =
CrossingOccupied AND IsNearYieldLine AND IsStoppedEnough
```

y:

```text id="jzsg0z"
CanValidateFreeYield =
IsNearYieldLine AND NOT CrossingOccupied
```

Eso es lo que buscábamos: si el cruce está ocupado, el coche debe estar cerca del `YieldLine` y parado; si está libre, puede pasar sin parada completa. `INTERSECTIONS 10-06-2026.txt`

---

## Lo que debes corregir

### Problema: `GetActorBounds` no se usa así

Ahora aparece:

```text id="w3d63h"
StoppedYieldWindowRatio =
ClampFloat(
    SafeDivide(
        BreakVectorX(GetActorBounds(TargetCar)),
        MAX(SensorEntryDistance, 1.0)
    ),
    0.0,
    1.0
)
```

El problema es que `GetActorBounds` devuelve normalmente dos vectores:

```text id="ereqgp"
Origin
BoxExtent
```

No debes hacer `BreakVectorX(GetActorBounds(TargetCar))` directamente, porque puedes estar cogiendo el `Origin`, no el `BoxExtent`.

### Corrección

Usa el pin **Box Extent** de `GetActorBounds`.

Debe quedar así:

```text id="kro9y6"
GetActorBounds(TargetCar)
    -> BoxExtent
        -> BreakVector
            -> X
```

Luego:

```text id="fb8s4g"
StoppedYieldWindowRatio =
ClampFloat(
    SafeDivide(
        ABS(BoxExtent.X),
        MAX(SensorEntryDistance, 1.0)
    ),
    0.0,
    1.0
)
```

En Blueprint:

1. `GetActorBounds`
   - Target = `TargetCar`
   - Only Colliding Components = true, si tienes esa opción
2. Coge el output `Box Extent`
3. `Break Vector`
4. Usa `X`
5. `ABS`
6. `SafeDivide` entre `MAX(SensorEntryDistance, 1.0)`
7. `ClampFloat 0.0 - 1.0`

---

## Revisión del cálculo completo

Tu función debe quedar así:

```text id="hvum8c"
ForwardSpeedAbs = ABS(GetForwardSpeed(TargetCar))
```

```text id="5ocgzf"
SignedDistanceToYieldLine =
Dot(
    GetActorLocation(TargetCar) - StopTargetLocation del AIController,
    StopLineForwardVector del AIController
)
```

```text id="mpx53p"
YieldDistanceRatio =
ClampFloat(
    ABS(SignedDistanceToYieldLine) / MAX(SensorEntryDistance, 1.0),
    0.0,
    1.0
)
```

```text id="ynayj6"
YieldSpeedRatio =
ClampFloat(
    ForwardSpeedAbs / MaxSpeed,
    0.0,
    1.0
)
```

```text id="aj98le"
StoppedYieldWindowRatio =
ClampFloat(
    ABS(BoxExtent.X) / MAX(SensorEntryDistance, 1.0),
    0.0,
    1.0
)
```

```text id="qlx091"
IsNearYieldLine =
YieldDistanceRatio <= MAX(YieldSpeedRatio, StoppedYieldWindowRatio)
```

```text id="9rqi4t"
IsStoppedEnough =
ForwardSpeedAbs < MaxSpeed * 0.005
```

```text id="1kv0o7"
CanValidateBlockedYield =
CrossingOccupied AND IsNearYieldLine AND IsStoppedEnough
```

```text id="v096vk"
CanValidateFreeYield =
IsNearYieldLine AND NOT CrossingOccupied
```

---

## Veredicto

La lógica del cambio ya está bien. Solo corrige este detalle:

```text id="3letr1"
BreakVectorX(GetActorBounds(TargetCar))
```

por:

```text id="9e2hrg"
BreakVectorX(BoxExtent output de GetActorBounds(TargetCar))
```

Después de eso, el ceda queda listo para un test corto.

## Prompt:
10/6/2026, 16:11:48

ahora?

[Attachment: INTERSECTIONS 10-06-2026.txt]

## Response:
10/6/2026, 16:11:36

> **Revisando lógica de cálculo de dimensiones del vehículo**
>
> Estoy considerando si el `BoxExtent.X` de `GetActorBounds()` corresponde correctamente a la longitud del vehículo. Como `BoxExtent` se calcula en ejes del mundo, podría no ser exacto si el coche está rotado en el mapa. Tal vez sea mejor usar el valor máximo entre las dimensiones X y Y para obtener la medida más segura.
>
> Pensó durante 10s

Ahora sí, **el cambio de los cedas está prácticamente cerrado**.

Lo principal ya está bien:

1. `MonitorSpeed` ya llama a `ComputeYieldValidationData`.
2. `CanValidateBlockedYield` exige:
   ```text
   CrossingOccupied AND IsNearYieldLine AND IsStoppedEnough
   ```
3. `CanValidateFreeYield` exige:
   ```text
   IsNearYieldLine AND NOT CrossingOccupied
   ```
4. `CheckCrossing` ya reutiliza `CountYieldCrossingCars`.
5. `StoppedYieldWindowRatio` ya usa `GetActorBoundsBoxExtent`, no el `Origin`, así que has corregido el problema anterior. `INTERSECTIONS 10-06-2026.txt`

## Único ajuste que haría antes del test

Ahora tienes:

```text
StoppedYieldWindowRatio =
SafeDivide(
    BreakVectorX(GetActorBoundsBoxExtent(TargetCar)),
    MAX(SensorEntryDistance, 1.0)
)
```

Esto funciona, pero `BoxExtent.X` depende del eje mundo, no necesariamente del largo real del coche según su orientación. Para evitar que en algunos cedas el margen sea demasiado pequeño o raro, yo usaría el mayor eje horizontal del bounding box:

```text
StoppedYieldWindowRatio =
ClampFloat(
    SafeDivide(
        MAX(ABS(BoxExtent.X), ABS(BoxExtent.Y)),
        MAX(SensorEntryDistance, 1.0)
    ),
    0.0,
    1.0
)
```

En Blueprint:

1. `GetActorBounds(TargetCar)`
2. Coger `BoxExtent`
3. `Break Vector`
4. `ABS X`
5. `ABS Y`
6. `MAX(ABS X, ABS Y)`
7. `SafeDivide` entre `MAX(SensorEntryDistance, 1.0)`
8. `ClampFloat 0.0 - 1.0`

Así el margen de parada depende del tamaño físico del coche, pero no queda condicionado por si el coche está orientado más en X o más en Y.

## Veredicto

La lógica ya está bien. Puedes hacer ese pequeño cambio de `BoxExtent.X` a `MAX(BoxExtent.X, BoxExtent.Y)` y después ejecutar un test corto.

En el próximo test deberíamos mirar especialmente:

```text
YieldValidationTime
Ticks_StopContext_Yield
NumYieldsCompleted
Acum_YieldCompletionBonus
TIMEFINISHED con YieldContext alto
YIELD_VIOLATION
```

Si sigue parando lejos, entonces añadimos al CSV `YieldDistanceRatio`, `YieldSpeedRatio`, `StoppedYieldWindowRatio` y `CrossingOccupiedAtYieldValidation`, pero por ahora no hace falta meter más debug.

## Prompt:
10/6/2026, 16:15:41

ahora mejor?

[Attachment: INTERSECTIONS 10-06-2026.txt]

## Response:
10/6/2026, 16:15:29

Sí, **ahora está mejor**. El cambio de `StoppedYieldWindowRatio` ya está en la dirección correcta.

Ahora tienes:

```text
StoppedYieldWindowRatio =
ClampFloat(
    SafeDivide(
        MAX(
            BreakVectorX(GetActorBoundsBoxExtent(TargetCar)),
            BreakVectorY(GetActorBoundsBoxExtent(TargetCar))
        ),
        MAX(SensorEntryDistance, 1.0)
    ),
    0.0,
    1.0
)
```

Esto mejora el cálculo anterior porque ya no dependes solo de `BoxExtent.X`, sino del mayor eje horizontal del coche. Así el margen de parada cerca del `YieldLine` no cambia de forma rara según la orientación del vehículo. `INTERSECTIONS 10-06-2026.txt`

## Veredicto

La lógica del ceda queda bien:

```text
CanValidateBlockedYield =
CrossingOccupied AND IsNearYieldLine AND IsStoppedEnough
```

```text
CanValidateFreeYield =
IsNearYieldLine AND NOT CrossingOccupied
```

Y `MonitorSpeed` usa correctamente primero `CanValidateBlockedYield`, luego `CanValidateFreeYield`, y si ninguno se cumple vuelve a meter el coche en `PendingMonitorCars`. `INTERSECTIONS 10-06-2026.txt`

## Único ajuste menor que haría

Aunque `BoxExtent` normalmente ya viene con valores positivos, yo pondría `ABS` por seguridad:

```text
MAX(
    ABS(BoxExtent.X),
    ABS(BoxExtent.Y)
)
```

Es decir:

```text
StoppedYieldWindowRatio =
ClampFloat(
    SafeDivide(
        MAX(
            ABS(BreakVectorX(BoxExtent)),
            ABS(BreakVectorY(BoxExtent))
        ),
        MAX(SensorEntryDistance, 1.0)
    ),
    0.0,
    1.0
)
```

No es un cambio de lógica, solo robustez.

También intentaría no llamar dos veces a `GetActorBoundsBoxExtent(TargetCar)`. Mejor:

```text
GetActorBounds(TargetCar)
    -> BoxExtent
    -> BreakVector
        X
        Y
```

y de ahí usas `X` e `Y`.

## Conclusión

Sí: **este punto ya se puede dar por cerrado**.  
Solo haría ese microajuste de `ABS` y usaría un único `GetActorBounds`. Después ya toca test corto para ver si los cedas bloqueados paran cerca del `YieldLine` y no al principio de la zona.

## Prompt:
10/6/2026, 16:17:53

ahora?

[Attachment: INTERSECTIONS 10-06-2026.txt]

## Response:
10/6/2026, 16:17:41

Sí, **ahora está bien**. El cambio de los cedas queda correctamente cerrado.

Has dejado `StoppedYieldWindowRatio` así:

```text
StoppedYieldWindowRatio =
ClampFloat(
    SafeDivide(
        MAX(
            ABS(BoxExtent.X),
            ABS(BoxExtent.Y)
        ),
        MAX(SensorEntryDistance, 1.0)
    ),
    0.0,
    1.0
)
```

y eso es lo que buscábamos: margen físico dinámico según el tamaño horizontal del coche, sin depender de un número fijo ni de un solo eje. `INTERSECTIONS 10-06-2026.txt`

La lógica final también queda bien:

```text
IsNearYieldLine =
YieldDistanceRatio <= MAX(YieldSpeedRatio, StoppedYieldWindowRatio)
```

```text
CanValidateBlockedYield =
CrossingOccupied AND IsNearYieldLine AND IsStoppedEnough
```

```text
CanValidateFreeYield =
IsNearYieldLine AND NOT CrossingOccupied
```

Esto significa:

| Situación | Resultado |
|---|---|
| Ceda libre | Puede pasar si está razonablemente cerca del `YieldLine` |
| Ceda ocupado | Solo valida si está cerca del `YieldLine` **y parado** |
| Coche lejos del `YieldLine` | Sigue monitorizando |
| Coche parado muy lejos | No valida como ceda correcto |

## Único detalle menor

Ahora llamas dos veces a:

```text
GetActorBoundsBoxExtent(TargetCar)
```

Una para `X` y otra para `Y`. Funciona, pero es más limpio hacer:

```text
GetActorBounds(TargetCar)
-> BoxExtent
-> BreakVector
-> X
-> Y
```

y reutilizar esos dos valores.

No es obligatorio. Es solo limpieza/rendimiento mínimo.

## Veredicto

**Cedas corregidos.**  
Puedes pasar al siguiente punto o hacer ya un test corto para comprobar que los coches no esperan al principio de la zona del ceda, sino cerca del `YieldLine`.

## Prompt:
10/6/2026, 16:18:57

no se llama dos veces a actorbounds, lo cojo del mismo, pero no se como reflejarlo en el txt

## Response:
10/6/2026, 16:18:45

Perfecto, entonces **no hay problema**. Si en Blueprint sale del mismo `GetActorBounds -> BoxExtent -> BreakVector`, está correcto.

Para reflejarlo mejor en el `.txt`, puedes escribirlo así:

```text
Se llama una única vez a GetActorBounds(TargetCar). Del output BoxExtent se hace BreakVector. 
Con BoxExtent.X y BoxExtent.Y se calcula:

StoppedYieldWindowRatio =
ClampFloat(
    SafeDivide(
        MAX(ABS(BoxExtent.X), ABS(BoxExtent.Y)),
        MAX(SensorEntryDistance del AIController, 1.0)
    ),
    0.0,
    1.0
)
```

O más descriptivo:

```text
Luego se llama una sola vez a GetActorBounds(TargetCar), se usa el output BoxExtent, se rompe el vector con BreakVector y se obtiene el mayor tamaño horizontal del coche con MAX(ABS(BoxExtent.X), ABS(BoxExtent.Y)). 
Después se setea StoppedYieldWindowRatio como ese tamaño dividido entre MAX(SensorEntryDistance, 1.0), limitado entre 0.0 y 1.0.
```

Así queda claro que **no hay dos llamadas**, solo reutilización de los dos componentes del mismo `BoxExtent`.

Entonces, con esa aclaración: **el cambio de cedas está bien cerrado**.

## Prompt:
10/6/2026, 16:19:38

y sin escribir eso? alguna forma de ponerlo en el calculo?

## Response:
10/6/2026, 16:19:26

Sí. Puedes reflejarlo directamente dentro del cálculo usando una variable intermedia, sin explicar todo el nodo.

Lo mejor sería ponerlo así:

```text
BoxExtent = GetActorBounds(TargetCar).BoxExtent

StoppedYieldWindowRatio =
ClampFloat(
    SafeDivide(
        MAX(ABS(BoxExtent.X), ABS(BoxExtent.Y)),
        MAX(SensorEntryDistance del AIController, 1.0)
    ),
    0.0,
    1.0
)
```

Así queda claro que `BoxExtent` sale de **una sola llamada** a `GetActorBounds`.

Otra forma todavía más compacta:

```text
StoppedYieldWindowRatio =
ClampFloat(
    SafeDivide(
        MAX(
            ABS(GetActorBounds(TargetCar).BoxExtent.X),
            ABS(GetActorBounds(TargetCar).BoxExtent.Y)
        ),
        MAX(SensorEntryDistance del AIController, 1.0)
    ),
    0.0,
    1.0
)
```

Pero esta segunda puede dar la impresión de que llamas dos veces a `GetActorBounds`, aunque en Blueprint salga del mismo nodo. Por eso yo usaría la primera, con:

```text
BoxExtent = GetActorBounds(TargetCar).BoxExtent
```

Y luego el cálculo usando `BoxExtent.X` y `BoxExtent.Y`. Esa es la forma más limpia para el `.txt`.

## Prompt:
11/6/2026, 10:04:11

revisa los datos, hay un bug en intersecciones que hace que se estanquen coches en cedas y stops:

[Attachment: INTERSECTIONS 10-06-2026.txt]

[Attachment: EVOLUTIONMANAGER 10-06-2026.txt]

[Attachment: FITNESS 10-06-2026.txt]

[Attachment: RED NEURONAL 09-06-2026.txt]

[Attachment: Fitness_Debug.csv]

[Attachment: informe.txt]

[Attachment: Training_Summary.csv]

## Response:
11/6/2026, 10:04:00

Voy a cruzar dos cosas: los CSV para localizar el patrón real del atasco, y los Blueprints de intersecciones para identificar qué condición deja los coches bloqueados.

Los datos apuntan a dos patrones distintos: el atasco de ceda es masivo y ocurre durante `MonitorSpeed`, no durante `CheckCrossing`; el de STOP es mucho menor y parece más de “no reanuda” o “creep”. Sigo cruzando con las columnas crudas para aislar la condición exacta.

Sí: los datos confirman que hay **un bug de bloqueo lógico**, no simplemente un mal comportamiento aprendido.

## Diagnóstico por datos

El entrenamiento tiene **15.210 registros**, 507 generaciones, todo en modo train, y el CSV está bien alineado con el summary. El dato clave es este: **TIMEFINISHED es el 61.7% de las muertes**, pero los fallos legales explícitos `STOP_VIOLATION + TRAFFIC + YIELD + NAV` son solo **0.28%**. Eso significa que muchos coches no están siendo penalizados/matados por incumplir el stop/ceda, sino que se quedan vivos hasta agotar el tiempo. `informe.txt`

El atasco principal está en **cedas**:

```text
Posible atasco en ceda:
3379 / 9392 TIMEFINISHED = 35.98%
```

Y los hotspots son muy claros:

```text
BP_SpawnPoint12 -> 487/507 TIMEFINISHED candidatos
BP_SpawnPoint40 -> 480/507
BP_SpawnPoint41 -> 478/507
BP_SpawnPoint7  -> 478/507
BP_SpawnPoint44 -> 476/507
BP_SpawnPoint5  -> 460/507
BP_SpawnPoint34 -> 386/505
```

Todos con `StopCtxP50` alrededor del **98-99%** y tiempo mediano **120s**. Es decir, el coche pasa prácticamente toda la vida en contexto de parada/ceda. `informe.txt`

En STOP también existe, pero es mucho menor:

```text
Posible atasco en stop:
109 / 9392 TIMEFINISHED = 1.16%
```

y el informe lo separa en:

```text
CREEP = 55 casos
NO_RESUME = 54 casos
```

Los spawns más afectados son `BP_SpawnPoint51`, `BP_SpawnPoint50`, `BP_SpawnPoint38` y `BP_SpawnPoint28`. `informe.txt`

---

# Bug principal en CEDA

Tu `MonitorSpeed` hace esto:

```text
ComputeYieldValidationData

Branch CanValidateBlockedYield
Branch CanValidateFreeYield
Else -> AddUnique PendingMonitorCars -> Timer -> Recheck_MonitorStop
```

La estructura es correcta, pero falta una salida de emergencia. Si el coche **no cumple nunca** ni `CanValidateBlockedYield` ni `CanValidateFreeYield`, se queda en `PendingMonitorCars` indefinidamente. Eso encaja exactamente con los datos: `YieldValidationTime` medio alto, muchísimo `Ticks_StopContext_Yield`, y muerte por `TIMEFINISHED`, no por `YIELD_VIOLATION`. `INTERSECTIONS 10-06-2026.txt`

## Qué está pasando

Ahora mismo:

```text
CanValidateBlockedYield =
CrossingOccupied AND IsNearYieldLine AND IsStoppedEnough
```

```text
CanValidateFreeYield =
IsNearYieldLine AND NOT CrossingOccupied
```

Si el coche frena demasiado pronto, no está cerca del `YieldLine`.

Entonces:

```text
IsNearYieldLine = false
CanValidateBlockedYield = false
CanValidateFreeYield = false
```

y el flujo cae siempre aquí:

```text
AddUnique PendingMonitorCars
Recheck_MonitorStop
```

Eso se repite hasta `TIMEFINISHED`.

---

# Corrección necesaria en CEDA

Aunque antes intentamos evitar más outputs, aquí **sí hace falta añadir uno**:

```text
ShouldTimeoutAsBadYield boolean
```

No es para simplificar lógica; es para cortar el bucle infinito.

## Modifica `ComputeYieldValidationData`

Añade variables locales:

```text
ExpectedYieldTravelTime float
YieldToleranceTime float
AllowedYieldValidationTime float
```

Y calcula:

```text
ExpectedYieldTravelTime =
SafeDivide(
    SensorEntryDistance del AIController,
    MAX(ABS(AproachSpeed del TargetCar), MaxSpeed del AIController * 0.005)
)
```

Luego reutiliza el tamaño horizontal del coche que ya usas para `StoppedYieldWindowRatio`:

```text
YieldToleranceTime =
SafeDivide(
    MAX(ABS(BoxExtent.X), ABS(BoxExtent.Y)),
    MAX(ABS(AproachSpeed del TargetCar), MaxSpeed del AIController * 0.005)
)
```

Después:

```text
AllowedYieldValidationTime =
ExpectedYieldTravelTime + YieldToleranceTime
```

Y el nuevo output:

```text
ShouldTimeoutAsBadYield =
YieldValidationTime del TargetCar > AllowedYieldValidationTime
AND
NOT CanValidateBlockedYield
AND
NOT CanValidateFreeYield
```

El `ReturnNode` final queda con 3 outputs:

```text
CanValidateBlockedYield =
CrossingOccupied AND IsNearYieldLine AND IsStoppedEnough

CanValidateFreeYield =
IsNearYieldLine AND NOT CrossingOccupied

ShouldTimeoutAsBadYield =
YieldValidationTime > AllowedYieldValidationTime
AND NOT CanValidateBlockedYield
AND NOT CanValidateFreeYield
```

---

## Modifica `MonitorSpeed`

Ahora mismo, cuando `CanValidateBlockedYield` y `CanValidateFreeYield` son false, reencolas directamente el coche.

Cámbialo así:

```text
Branch CanValidateBlockedYield
```

Si true:

```text
YieldValidationTime = 0.0
StoppedCorrectly = true
YieldCrossingCheckID++
CheckCrossing(TargetCar, YieldCrossingCheckID)
```

Si false:

```text
Branch CanValidateFreeYield
```

Si true, igual.

Si false, añade nuevo branch:

```text
Branch ShouldTimeoutAsBadYield
```

Si true:

```text
ApplyYieldDeathPenalty(TargetCar)
```

Si false:

```text
AddUnique PendingMonitorCars(TargetCar)
Branch NOT MonitorTimerActive
    Set MonitorTimerActive = true
    SetTimerByEvent 0.1 -> Recheck_MonitorStop
```

Con esto, un coche que se queda parado lejos del `YieldLine` no puede vivir 120s generando atasco. Morirá como `YIELD_VIOLATION`, que es lo correcto para entrenar.

---

# Bug secundario en STOP

En STOP ya tienes timeout, pero es demasiado estrecho. Ahora `ComputeStopValidationData` devuelve:

```text
ShouldTimeoutAsBadStop =
StopValidationTime > LearnedMinTime + TravelTimeToStopLine
AND ForwardSpeedAbs < LearnedThreshold
AND NOT IsInsideStopWindow
```

El problema está en esta parte:

```text
ForwardSpeedAbs < LearnedThreshold
```

Eso significa que si el coche hace **creep**, es decir, se mueve lentamente pero no llega a estar totalmente parado, el timeout no salta nunca. Justo el informe detecta `CREEP` como causa dominante de los candidatos STOP: 55 casos. `informe.txt`

## Corrección en `ComputeStopValidationData`

Añade una variable local:

```text
ValidStop boolean
```

Calcula:

```text
ValidStop =
IsStoppedEnough
AND IsInsideStopWindow
AND HasWaitedEnough
```

Y cambia `ShouldTimeoutAsBadStop`.

Ahora tienes:

```text
ShouldTimeoutAsBadStop =
StopValidationTime > LearnedMinTime + TravelTimeToStopLine
AND ForwardSpeedAbs < LearnedThreshold
AND NOT IsInsideStopWindow
```

Cámbialo por:

```text
ShouldTimeoutAsBadStop =
StopValidationTime > (LearnedMinTime + TravelTimeToStopLine)
AND NOT ValidStop
```

Así matas tanto:

```text
coche parado demasiado lejos
coche haciendo creep sin validar
coche que no llega a cumplir ventana + espera
```

y no matas el caso correcto, porque si cumple:

```text
IsStoppedEnough AND IsInsideStopWindow AND HasWaitedEnough
```

entonces `ValidStop = true`.

---

# Limpieza recomendable al liberar STOP/CEDA

Cuando liberas un coche en `CheckCrossing` o `CheckCrossingClear`, ahora haces:

```text
TrafficControlType = 3
Apply bonus
AproachSpeed = 0.0
ForceStop = false
Remove pending arrays
```

Yo añadiría también:

```text
StoppedCorrectly = false
```

No porque sea la causa principal, sino para evitar estados residuales. Ahora mismo `StoppedCorrectly` se resetea al entrar en otro stop/ceda, pero es más limpio dejarlo apagado al salir.

Hazlo en:

## `BP_Sign_Yield -> CheckCrossing`, cuando el cruce está libre

Después de:

```text
ForceStop = false
```

añade:

```text
StoppedCorrectly = false
```

## `BP_Sign_Stop -> CheckCrossingClear`, cuando el cruce está libre

Después de:

```text
ForceStop = false
```

añade:

```text
StoppedCorrectly = false
```

## En `OnComponentEndOverlap`

En ceda, si `StoppedCorrectly == true`, ahora quitas `PendingMonitorCars`. Añade también:

```text
RemoveItem PendingYieldCheckCars(TargetCar)
StoppedCorrectly = false
```

En stop, si `StoppedCorrectly == true`, ahora quitas `PendingWaitCars`. Añade también:

```text
RemoveItem PendingCrossCheckCars(TargetCar)
StoppedCorrectly = false
```

---

# Qué NO tocaría todavía

No tocaría de momento:

```text
CountYieldCrossingCars
Count de CrossingZones en STOP
Fitness
Red neuronal
Inputs
```

El problema actual no es que la red no pueda aprender; es que el sistema permite que un coche inválido se quede bloqueado hasta `TIMEFINISHED`. Primero hay que convertir esos bloqueos en `YIELD_VIOLATION` o `STOP_VIOLATION`.

---

# Resumen exacto de cambios

## CEDA

En `ComputeYieldValidationData`:

```text
Añadir output:
ShouldTimeoutAsBadYield
```

Calcular:

```text
ExpectedYieldTravelTime =
SensorEntryDistance / MAX(ABS(AproachSpeed), MaxSpeed * 0.005)

YieldToleranceTime =
MAX(ABS(BoxExtent.X), ABS(BoxExtent.Y)) / MAX(ABS(AproachSpeed), MaxSpeed * 0.005)

AllowedYieldValidationTime =
ExpectedYieldTravelTime + YieldToleranceTime

ShouldTimeoutAsBadYield =
YieldValidationTime > AllowedYieldValidationTime
AND NOT CanValidateBlockedYield
AND NOT CanValidateFreeYield
```

En `MonitorSpeed`:

```text
Si no valida blocked ni free:
    Si ShouldTimeoutAsBadYield:
        ApplyYieldDeathPenalty
    Si no:
        reencolar en PendingMonitorCars
```

## STOP

En `ComputeStopValidationData`:

```text
ValidStop =
IsStoppedEnough AND IsInsideStopWindow AND HasWaitedEnough
```

Cambiar:

```text
ShouldTimeoutAsBadStop =
StopValidationTime > LearnedMinTime + TravelTimeToStopLine
AND ForwardSpeedAbs < LearnedThreshold
AND NOT IsInsideStopWindow
```

por:

```text
ShouldTimeoutAsBadStop =
StopValidationTime > LearnedMinTime + TravelTimeToStopLine
AND NOT ValidStop
```

## Limpieza

Al liberar ceda/stop:

```text
ForceStop = false
StoppedCorrectly = false
Remove pending arrays correspondientes
```

Con esto deberías ver en el próximo CSV una bajada fuerte de `TIMEFINISHED` con `YieldValidationTime` alto, y una subida temporal de `YIELD_VIOLATION`/`STOP_VIOLATION`. Esa subida sería buena señal: significa que el bug de “esperar eternamente” se ha convertido en una señal de aprendizaje.

## Prompt:
11/6/2026, 10:08:10

ten en cuenta que un coche cuyo cruce está ocupado no puede salir, eso es importante

## Response:
11/6/2026, 10:08:02

> **Ajustando lógica de espera en cruces**
>
> Estoy considerando cómo ajustar la recomendación para no detener el coche si está esperando correctamente en un cruce ocupado. Si el coche está bien detenido y cerca de la línea, tiene que pasar a verificar el cruce, pero si no está bien detenido, podría generar un fallo por tiempo de espera. La idea es no activar el proceso repetidamente si está esperando correctamente.
>
> Pensó durante 9s

Sí, totalmente. **Eso cambia cómo hay que interpretar el timeout del ceda**.

Un coche con el cruce ocupado **no debe morir por estar esperando mucho tiempo**, siempre que esté esperando correctamente cerca del `YieldLine` y parado. El timeout solo debe matar casos inválidos: coche parado lejos, creep indefinido, o coche que nunca llega a una posición válida de espera.

La idea correcta sería:

```text id="s54v54"
Cruce ocupado + coche cerca del YieldLine + coche parado
= espera legal indefinida
```

No debe ser `YIELD_VIOLATION`.

## Ajuste sobre mi propuesta anterior

No uses `ShouldTimeoutAsBadYield` como “lleva mucho tiempo en ceda”. Eso sería incorrecto.

Debe ser:

```text id="t5kpm5"
ShouldTimeoutAsBadYield =
YieldValidationTime > AllowedYieldValidationTime
AND NOT CanValidateBlockedYield
AND NOT CanValidateFreeYield
```

Pero con esta interpretación:

```text id="r0zbr8"
CanValidateBlockedYield
```

no significa “puede salir”. Significa:

```text id="8loqrr"
El coche está correctamente colocado para esperar en un ceda bloqueado.
```

Por eso quizá el nombre es confuso. Yo lo renombraría a:

```text id="rw11dj"
HasValidBlockedYieldWait
```

Y dejaría:

```text id="8ew8by"
CanValidateFreeYield
```

o incluso:

```text id="897ebd"
CanEnterFreeYield
```

## Lógica correcta

En `ComputeYieldValidationData`:

```text id="1s98jx"
HasValidBlockedYieldWait =
CrossingOccupied
AND IsNearYieldLine
AND IsStoppedEnough
```

```text id="ma5vap"
CanEnterFreeYield =
NOT CrossingOccupied
AND IsNearYieldLine
```

```text id="60qpxi"
ShouldTimeoutAsBadYield =
YieldValidationTime > AllowedYieldValidationTime
AND NOT HasValidBlockedYieldWait
AND NOT CanEnterFreeYield
```

Así, si el cruce está ocupado y el coche está bien parado:

```text id="ky6ryt"
HasValidBlockedYieldWait = true
ShouldTimeoutAsBadYield = false
```

aunque pasen 120 segundos.

## Flujo recomendado en `MonitorSpeed`

```text id="swoi3h"
ComputeYieldValidationData
```

### Branch 1

```text id="9urwdg"
HasValidBlockedYieldWait
```

Si true:

```text id="xsn6bs"
YieldValidationTime = 0.0
StoppedCorrectly = true
YieldCrossingCheckID++
CheckCrossing(TargetCar, YieldCrossingCheckID)
```

Esto **no lo libera directamente**. Solo lo pasa a `CheckCrossing`, y ahí, si el cruce sigue ocupado, debe quedar en:

```text id="bp4wik"
PendingYieldCheckCars
```

esperando legalmente.

### Branch 2

```text id="z4q68l"
CanEnterFreeYield
```

Si true:

```text id="bjvw5y"
YieldValidationTime = 0.0
StoppedCorrectly = true
YieldCrossingCheckID++
CheckCrossing(TargetCar, YieldCrossingCheckID)
```

Aquí `CheckCrossing` confirmará que no hay coches y entonces liberará.

### Branch 3

```text id="zrnvtf"
ShouldTimeoutAsBadYield
```

Si true:

```text id="zs7f6n"
ApplyYieldDeathPenalty(TargetCar)
```

Si false:

```text id="ta1wy6"
AddUnique PendingMonitorCars
SetTimer 0.1
```

## Punto clave

El coche **solo debe morir por timeout de ceda** si después del tiempo razonable de aproximación:

```text id="qurrs7"
no está correctamente esperando con cruce ocupado
y tampoco puede entrar con cruce libre
```

Pero si está parado cerca del `YieldLine` y el cruce sigue ocupado, debe esperar sin límite hasta que `CheckCrossing` detecte cruce libre.

Así protegemos justo lo importante: **no forzar salida cuando el cruce está ocupado**.

## Prompt:
11/6/2026, 10:10:20

pero matar un coche por parar lejos no tiene sentido, la unica razon es por cuando tiene el cruce libre y no sale, ahí si, pero por parar lejos no

## Response:
11/6/2026, 10:10:08

> **Revisando lógica de penalización por detención**
>
> El usuario requiere una corrección basada en el archivo anterior. Necesito ser preciso al responder en español. En lugar de penalizar por detenerse lejos, no debería castigar si el cruce está ocupado o bloqueado. La penalización ocurre solo si el cruce está libre y no hay salida tras el tiempo o en un estado inválido.
>
> **Resolviendo el bug de detención en "ceda"**
>
> El problema es que los autos en "ceda" se detienen aunque el cruce esté libre y no se mueven. Debo asegurarnos de que si el cruce está libre, se libere el "ForceStop" después del tiempo de validación, incluso si no están cerca de la línea de ceda. Así, "LAZY" podrá intervenir al no tener bloqueos.
>
> Pensó durante 12s

Tienes razón. **Matar por parar lejos en un ceda no es buena señal de aprendizaje**. En un ceda, parar lejos puede ser ineficiente, pero no es una infracción clara. La infracción real es:

```text
El cruce está libre, el coche ya podría salir, pero sigue bloqueado sin avanzar.
```

Así que corrijo la propuesta: **no usaría `ApplyYieldDeathPenalty` por “no estar cerca del YieldLine”**.

## Nueva lógica correcta para CEDA

Hay que separar 3 estados:

```text
1. Cruce ocupado
   -> esperar, no matar nunca por timeout

2. Cruce libre + coche puede entrar
   -> liberar ForceStop

3. Cruce libre + coche sigue sin salir durante demasiado tiempo
   -> ahí sí aplicar YIELD_VIOLATION o dejar que LAZY lo mate
```

El bug actual probablemente viene de que, si `CanValidateFreeYield` no se cumple, el coche se queda en `PendingMonitorCars` con `ForceStop = true`, aunque el cruce esté libre. Mientras `ForceStop = true`, tu `CheckStuck` no lo considera LAZY, porque excluye coches en contexto de stop/semáforo. En `CheckStuck`, la condición de lazy solo se activa si **no** hay `ForceStop` y **no** hay semáforo rojo/ámbar activo. `FITNESS 10-06-2026.txt`

Por eso el coche puede quedar vivo hasta `TIMEFINISHED`.

---

# Cambio que haría

## 1. No crear `ShouldTimeoutAsBadYield`

O, si lo creas, **no debe matar por parar lejos**. Pero lo más limpio: no lo metas todavía.

---

## 2. Cambiar la lógica de `CanValidateFreeYield`

Ahora tienes:

```text
CanValidateFreeYield =
IsNearYieldLine AND NOT CrossingOccupied
```

Yo lo cambiaría a:

```text
CanValidateFreeYield =
NOT CrossingOccupied
```

Sin `IsNearYieldLine`.

¿Por qué? Porque si el cruce está libre, el ceda no debería mantener `ForceStop = true`. Puede que el coche esté lejos, pero entonces simplemente seguirá aproximándose. Si lo obligas a esperar hasta estar cerca del `YieldLine`, puedes crear exactamente el bloqueo que estamos viendo.

El control de velocidad/fitness ya castigará si se comporta mal, pero no debe quedarse forzado a parar.

---

## 3. Mantener `HasValidBlockedYieldWait`

Renombraría mentalmente `CanValidateBlockedYield` a:

```text
HasValidBlockedYieldWait
```

Y dejaría:

```text
HasValidBlockedYieldWait =
CrossingOccupied AND IsNearYieldLine AND IsStoppedEnough
```

Pero ojo: si el cruce está ocupado y el coche aún no está cerca/parado, tampoco lo mates. Solo sigue monitorizando.

---

# Nueva `ComputeYieldValidationData`

Outputs recomendados:

```text
HasValidBlockedYieldWait boolean
CanEnterFreeYield boolean
CrossingOccupied boolean
```

Sí, aquí sí sacaría `CrossingOccupied` porque ayuda a que `MonitorSpeed` sea claro.

Internamente:

```text
HasValidBlockedYieldWait =
CrossingOccupied AND IsNearYieldLine AND IsStoppedEnough
```

```text
CanEnterFreeYield =
NOT CrossingOccupied
```

Nada más.

No hace falta:

```text
ShouldTimeoutAsBadYield
```

---

# Nueva lógica de `MonitorSpeed`

Después de `ComputeYieldValidationData`:

## Branch 1

```text
CanEnterFreeYield
```

Si true:

```text
YieldValidationTime = 0.0
StoppedCorrectly = true
YieldCrossingCheckID++
CheckCrossing(TargetCar, YieldCrossingCheckID)
```

Aquí `CheckCrossing` volverá a contar coches. Si sigue libre, libera:

```text
TrafficControlType = 3
ApplyYieldCompletionBonus
AproachSpeed = 0.0
ForceStop = false
Remove PendingMonitorCars
Remove PendingYieldCheckCars
```

Eso ya lo tienes en `CheckCrossing`. `INTERSECTIONS 10-06-2026.txt`

## Branch 2

Si `CanEnterFreeYield` es false:

```text
Branch HasValidBlockedYieldWait
```

Si true:

```text
YieldValidationTime = 0.0
StoppedCorrectly = true
YieldCrossingCheckID++
CheckCrossing(TargetCar, YieldCrossingCheckID)
```

Si el cruce sigue ocupado, `CheckCrossing` lo mete en `PendingYieldCheckCars`, que es correcto. `INTERSECTIONS 10-06-2026.txt`

## Branch 3

Si tampoco está en espera bloqueada válida:

```text
AddUnique PendingMonitorCars
SetTimer 0.1 -> Recheck_MonitorStop
```

Sin muerte.

---

# Entonces, ¿cuándo se mata si el cruce está libre y no sale?

Una vez `CanEnterFreeYield = true`, `CheckCrossing` debe liberar `ForceStop = false`.

Desde ese momento, si el coche no se mueve, ya no está protegido por contexto de parada, y `CheckStuck` puede matarlo como `LAZY`. Esa es una señal mucho más correcta que `YIELD_VIOLATION`.

Si quieres que sea específicamente `YIELD_VIOLATION`, entonces habría que crear una lógica nueva de “released but did not move”, pero de momento no lo haría. Usaría `LAZY`.

---

# Resumen del cambio exacto

En `ComputeYieldValidationData`, cambia:

```text
CanValidateFreeYield =
IsNearYieldLine AND NOT CrossingOccupied
```

por:

```text
CanValidateFreeYield =
NOT CrossingOccupied
```

Y no añadas muerte por timeout.

Deja:

```text
CanValidateBlockedYield =
CrossingOccupied AND IsNearYieldLine AND IsStoppedEnough
```

En `MonitorSpeed`:

```text
Si CanValidateFreeYield:
    CheckCrossing

Si no, si CanValidateBlockedYield:
    CheckCrossing

Si no:
    PendingMonitorCars
```

Con esto, si el cruce está libre, el coche sale del contexto de ceda y deja de estar bloqueado por `ForceStop`. Si luego no avanza, lo gestionará `CheckStuck` como estancamiento real.

## Prompt:
11/6/2026, 10:15:07

vale, que cambios debo hacer, paso a paso:

[Attachment: INTERSECTIONS 11-06-2026.txt]

## Response:
11/6/2026, 10:14:56

Parto del `INTERSECTIONS 11-06-2026`: ya tienes aplicado el cambio clave de `CanValidateFreeYield = NOT CrossingOccupied`. Ahora te doy los pasos restantes sin meter muerte por parar lejos.

> **Revisando pasos y validaciones necesarias**
>
> Parece que no se necesita una herramienta extra, ya que el archivo está cargado. El archivo actual tiene varias condiciones como CanValidateFreeYield = NOT CrossingOccupied. If bien se ajustan, parece que el sistema valida automáticamente si se está ocupado o libre. Porque puede haber algún error si la intersección permanece bloqueada y si se hace el monitoreo adecuado.
>
> **Revisando posibles problemas de validación de cruce**
>
> Parece que el sistema no verifica ForceStop, pero espera hasta que el cruce esté libre. Un posible problema es que, en MonitorSpeed, el sistema revisa primero la rama bloqueada, y si está ocupado y cerca del detención, se marca como "detenido correctamente". Eso podría olvidar a los autos que están realmente dentro del cruce.
>
> Pensó durante 38s

Sí. Desde tu `INTERSECTIONS 11-06-2026`, haría estos cambios. Lo importante: **no matar por parar lejos en ceda**. Solo liberar el ceda cuando el cruce esté libre; si después no avanza, ya lo gestionará `LAZY`.

---

# 1. CEDA - `ComputeYieldValidationData`

Tu función ya está casi como debe estar. Ahora mismo tienes:

```text id="2pjyyu"
CanValidateBlockedYield =
CrossingOccupied AND IsNearYieldLine AND IsStoppedEnough
```

y:

```text id="gacl8n"
CanValidateFreeYield =
NOT(CrossingOccupied)
```

Eso está bien. No vuelvas a poner:

```text id="gj6mqj"
CanValidateFreeYield =
IsNearYieldLine AND NOT CrossingOccupied
```

Ese era el problema, porque si el cruce estaba libre pero el coche no estaba cerca del `YieldLine`, mantenías `ForceStop = true` y podía quedarse bloqueado. En tu archivo actual ya está corregido. `INTERSECTIONS 11-06-2026.txt`

## Déjalo así

```text id="c7p3su"
CanValidateBlockedYield =
CrossingOccupied AND IsNearYieldLine AND IsStoppedEnough
```

```text id="ef76bn"
CanValidateFreeYield =
NOT CrossingOccupied
```

No añadas `ShouldTimeoutAsBadYield`.

---

# 2. CEDA - cambia el orden en `MonitorSpeed`

Ahora mismo en `MonitorSpeed` haces primero:

```text id="yaafh5"
Branch CanValidateBlockedYield
```

y luego:

```text id="0bhvx6"
Branch CanValidateFreeYield
```

Funcionalmente no está mal, pero para evitar confusión y dejar clara la prioridad, yo lo ordenaría así:

## Nuevo orden recomendado

Después de:

```text id="l6blne"
ComputeYieldValidationData(TargetCar)
```

primero comprueba:

```text id="ef9g1w"
Branch CanValidateFreeYield
```

### Si `CanValidateFreeYield == true`

Haz exactamente este flujo:

```text id="fkhv7i"
Set YieldValidationTime(TargetCar) = 0.0
Set StoppedCorrectly(AIController) = true
YieldCrossingCheckID(TargetCar)++
CheckCrossing(TargetCar, YieldCrossingCheckID)
```

Esto no mata ni fuerza salida manual. Solo permite que `CheckCrossing` confirme que el cruce está libre y quite `ForceStop`.

---

### Si `CanValidateFreeYield == false`

Entonces comprueba:

```text id="nf8i62"
Branch CanValidateBlockedYield
```

### Si `CanValidateBlockedYield == true`

Haz el mismo flujo:

```text id="wsccxu"
Set YieldValidationTime(TargetCar) = 0.0
Set StoppedCorrectly(AIController) = true
YieldCrossingCheckID(TargetCar)++
CheckCrossing(TargetCar, YieldCrossingCheckID)
```

Aquí el cruce está ocupado, así que `CheckCrossing` lo volverá a contar. Si sigue ocupado, lo meterá en `PendingYieldCheckCars`, que es correcto.

---

### Si ambos son false

Deja el flujo actual:

```text id="xoh8xt"
AddUnique PendingMonitorCars(TargetCar)
Branch NOT MonitorTimerActive
    Set MonitorTimerActive = true
    SetTimerByEvent 0.1 -> Recheck_MonitorStop
```

No añadas muerte.

---

# 3. CEDA - `CheckCrossing`

Aquí no cambies la lógica principal. La parte correcta es:

```text id="5qmfp0"
CountYieldCrossingCars(TargetCar)
CarsAlivedInCrossingZone = CarsInCrossing
Branch CarsAlivedInCrossingZones > 0
```

Si hay coches:

```text id="b3oxc6"
AddUnique PendingYieldCheckCars(TargetCar)
SetTimer 0.1 -> Recheck_Crossing
```

Si no hay coches:

```text id="wgaxwc"
TrafficControlType = 3
ApplyYieldCompletionBonus
AproachSpeed = 0.0
ForceStop = false
RemoveItem PendingMonitorCars
RemoveItem PendingYieldCheckCars
```

Eso está bien. `INTERSECTIONS 11-06-2026.txt`

## Importante

**No pongas `StoppedCorrectly = false` dentro de `CheckCrossing`.**

Si lo pones ahí, cuando el coche salga del `SensorZone`, `OnComponentEndOverlap` verá `StoppedCorrectly == false` y puede llamar a:

```text id="m04qh0"
ApplyYieldDeathPenalty
```

Así que `StoppedCorrectly` debe quedarse en `true` hasta que el coche salga físicamente del sensor.

---

# 4. CEDA - modifica `OnComponentEndOverlap`

En `BP_Sign_Yield -> OnComponentEndOverlap`, en la rama donde:

```text id="6321z7"
StoppedCorrectly == true
```

ahora haces:

```text id="2e7ogw"
TrafficControlType = 3
AproachSpeed = 0.0
ForceStop = false
RemoveItem PendingMonitorCars
```

Añade también:

```text id="q7wzvh"
RemoveItem PendingYieldCheckCars(TargetCar)
Set YieldValidationTime(TargetCar) = 0.0
Set StoppedCorrectly(AIController) = false
```

El orden recomendado:

```text id="hym4m1"
TrafficControlType = 3
AproachSpeed = 0.0
ForceStop = false
RemoveItem PendingMonitorCars(TargetCar)
RemoveItem PendingYieldCheckCars(TargetCar)
YieldValidationTime = 0.0
StoppedCorrectly = false
```

La rama false se queda igual:

```text id="2qiz6u"
ApplyYieldDeathPenalty(TargetCar)
```

---

# 5. STOP - cambia `ComputeStopValidationData`

Aquí sí hay un problema real. Ahora mismo tienes:

```text id="i4h52d"
ShouldTimeoutAsBadStop =
StopValidationTime > LearnedMinTime + TravelTimeToStopLine
AND ForwardSpeedAbs < LearnedThreshold
AND NOT IsInsideStopWindow
```

El problema es esta parte:

```text id="u5fcvl"
ForwardSpeedAbs < LearnedThreshold
```

Si el coche está haciendo `creep`, es decir, moviéndose muy lento pero sin llegar a parar legalmente, el timeout puede no activarse bien.

## Añade una variable local

En `ComputeStopValidationData`, añade:

```text id="9j4in8"
ValidStop boolean
```

Calcula:

```text id="4cqe3h"
ValidStop =
(ForwardSpeedAbs < LearnedThreshold)
AND
(SignedDistanceToStopLine <= AllowedStopBeforeLine)
AND
(CurrentStopWaitTime >= LearnedMinTime)
```

## Cambia el return de `ShouldTimeoutAsBadStop`

Sustituye esto:

```text id="yan5hu"
ShouldTimeoutAsBadStop =
(StopValidationTime > LearnedMinTime + TravelTimeToStopLine)
AND
(ForwardSpeedAbs < LearnedThreshold)
AND
NOT(SignedDistanceToStopLine <= AllowedStopBeforeLine)
```

por esto:

```text id="ragpbh"
ShouldTimeoutAsBadStop =
(StopValidationTime > LearnedMinTime + TravelTimeToStopLine)
AND
NOT(ValidStop)
```

O si no quieres crear `ValidStop`, ponlo inline:

```text id="0msz7x"
ShouldTimeoutAsBadStop =
(StopValidationTime > LearnedMinTime + TravelTimeToStopLine)
AND
NOT(
    (ForwardSpeedAbs < LearnedThreshold)
    AND
    (SignedDistanceToStopLine <= AllowedStopBeforeLine)
    AND
    (CurrentStopWaitTime >= LearnedMinTime)
)
```

Esto solo afecta al STOP, no al ceda.

---

# 6. STOP - `CheckCrossingClear`

Igual que en ceda: **no pongas `StoppedCorrectly = false` dentro de `CheckCrossingClear`**.

Ahora, cuando el cruce está libre, haces:

```text id="gp1i59"
TrafficControlType = 3
ApplyStopCompletionBonus
AproachSpeed = 0.0
ForceStop = false
RemoveItem PendingWaitCars
RemoveItem PendingCrossCheckCars
```

Eso está bien. Déjalo así.

Si pones `StoppedCorrectly = false` aquí, luego al salir del `SensorZone`, `OnComponentEndOverlap` podría interpretar que no paró correctamente y aplicar `STOP_VIOLATION`.

---

# 7. STOP - modifica `OnComponentEndOverlap`

En `BP_Sign_Stop -> OnComponentEndOverlap`, en la rama:

```text id="nh8nzw"
StoppedCorrectly == true
```

ahora haces:

```text id="myjzmn"
AproachSpeed = 0.0
ForceStop = false
RemoveItem PendingWaitCars
```

Añade:

```text id="3619hf"
RemoveItem PendingCrossCheckCars(TargetCar)
Set StopValidationTime(TargetCar) = 0.0
Set CurrentStopWaitTime(TargetCar) = 0.0
Set StoppedCorrectly(AIController) = false
```

Orden recomendado:

```text id="hxgfv6"
AproachSpeed = 0.0
ForceStop = false
RemoveItem PendingWaitCars(TargetCar)
RemoveItem PendingCrossCheckCars(TargetCar)
StopValidationTime = 0.0
CurrentStopWaitTime = 0.0
StoppedCorrectly = false
```

La rama false se queda igual:

```text id="zy8yfn"
ApplyStopDeathPenalty(TargetCar)
```

---

# 8. No toques de momento

No tocaría todavía:

```text id="gmrowh"
CountYieldCrossingCars
CrossingZones
Fitness
Red neuronal
Inputs
CheckStuck
```

El problema principal es de estado/lógica de liberación, no de red neuronal.

---

# Resumen rápido de cambios

## CEDA

1. Mantén:

```text id="xklr63"
CanValidateFreeYield = NOT CrossingOccupied
```

2. En `MonitorSpeed`, comprueba primero `CanValidateFreeYield`.

3. Si `CanValidateFreeYield == true`, llama a `CheckCrossing`.

4. Si no, comprueba `CanValidateBlockedYield`.

5. Si ambos son false, reencola en `PendingMonitorCars`.

6. No añadas muerte por timeout.

7. En `OnComponentEndOverlap`, rama correcta, limpia también `PendingYieldCheckCars`, resetea `YieldValidationTime` y al final pon `StoppedCorrectly = false`.

---

## STOP

1. Cambia `ShouldTimeoutAsBadStop`.

2. Nuevo criterio:

```text id="sroqnv"
ShouldTimeoutAsBadStop =
StopValidationTime > LearnedMinTime + TravelTimeToStopLine
AND NOT ValidStop
```

3. En `OnComponentEndOverlap`, rama correcta, limpia también `PendingCrossCheckCars`, resetea tiempos y al final pon `StoppedCorrectly = false`.

Con esto, el ceda libre dejará de bloquear con `ForceStop = true`, y el STOP dejará de permitir creep o esperas inválidas hasta `TIMEFINISHED`.



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)