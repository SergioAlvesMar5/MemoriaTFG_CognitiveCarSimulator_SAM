# Duplicados de modelos y selección

**User:** Anonymous  
**Created:** 6/10/2026 12:12:25  
**Updated:** 6/10/2026 12:21:39  
**Exported:** 6/29/2026 16:54:13  
**Link:** [https://chatgpt.com/g/g-p-69e894c075f08191841adcc5961cd5ef/c/6a29385d-04ec-83ed-a331-7e02eb591fc2](https://chatgpt.com/g/g-p-69e894c075f08191841adcc5961cd5ef/c/6a29385d-04ec-83ed-a331-7e02eb591fc2)  

## Prompt:
10/6/2026, 12:12:36

quiero encontrar el mejor modelo para reentrenar, pero son muchos backups, y algunos pueden ser del mismo modelo, quiero que deshashes los pesos, y busques que modelos están duplicados, para no hacer test de más, confirma que entiendes la propuesta y te paso los modelos

[Attachment: EVOLUTIONMANAGER 09-06-2026.txt]

[Attachment: INTERSECTIONS 09-06-2026.txt]

[Attachment: FITNESS 09-06-2026.txt]

[Attachment: RED NEURONAL 09-06-2026.txt]

[Attachment: clean_run_output.txt]

[Attachment: SuperCarModel_prev_09_06_15_36.sav]

[Attachment: SuperCarModel_prev_09_06_15_41.sav]

[Attachment: SuperCarModel_prev_09_06_15_42.sav]

[Attachment: SuperCarModel_prev_09_06_15_44.sav]

[Attachment: SuperCarModel_prev_09_06_15_45.sav]

[Attachment: SuperCarModel_prev_09_06_15_46.sav]

[Attachment: SuperCarModel_prev_09_06_15_51.sav]

[Attachment: SuperCarModel_prev_09_06_16_11.sav]

[Attachment: SuperCarModel_prev_09_06_16_17.sav]

[Attachment: SuperCarModel_prev_09_06_16_31.sav]

[Attachment: SuperCarModel_prev_09_06_16_43.sav]

[Attachment: SuperCarModel_prev_09_06_17_45.sav]

[Attachment: SuperCarModel_prev_09_06_18_19.sav]

[Attachment: SuperCarModel_prev_09_06_18_21.sav]

[Attachment: SuperCarModel_prev_09_06_19_27.sav]

## Response:
10/6/2026, 12:12:24

Entiendo la propuesta: quieres comparar los backups por **pesos reales del modelo**, no solo por nombre o fecha, para agrupar duplicados y reducir tests repetidos. Voy a distinguir entre duplicados binarios exactos y duplicados de pesos si el `.sav` permite extraerlos limpiamente.

Ya he podido leer los `.sav`: todos tienen el mismo tamaño y estructura compatible con el modelo actual. Estoy comparando dos niveles: SHA del archivo completo y SHA solo de `W_IH + W_HO`, que es el criterio importante para detectar el mismo cerebro aunque cambie el `BestFitness`.

> **Acknowledge user’s files and plan next steps**
>
> El usuario ha solicitado confirmación sobre la propuesta y ha adjuntado los modelos. Parece que ya están listos, así que probablemente deba proceder, reconociendo que los archivos están presentes. Como piden confirmación, puedo proceder al hashing de los pesos de los modelos, calculando hashes de las matrices serializadas.
>
> **Analizando cómo manejar archivos SAV de Unreal para encontrar duplicados**
>
> Los archivos SAV de Unreal podrían ser binarios no fácilmente legibles, pero aplicar un hash exacto puede ayudar a identificar duplicados byte por byte. Debo extraer los valores flotantes de estos archivos, ya que pueden contener arrays y propiedades en formato little-endian. Extraeremos solo los pesos y lo que es relevante, ignorando metadatos como el fitness o las marcas de tiempo, para identificar duplicados exactos de los modelos.
>
> **Preparando para procesar archivos con Python**
>
> Necesito usar Python para leer los archivos. Puedo calcular los hashes, pero también debo inspeccionar detalles como el tamaño, los primeros bytes, las cadenas y los valores flotantes. Así puedo asegurarme de cubrir todas las posibles variaciones de los archivos y encontrar lo que necesito de manera eficiente.
>
> **Leyendo archivos y calculando hashes**
>
>
> **Leyendo archivos y obteniendo información**
>
>
> **Leyendo archivos y extrayendo cadenas y hashes**
>
>
> **Analizando formato SaveGame de Unreal**
>
> Necesito analizar el formato de "SaveGame" de Unreal, que incluye GVAS, encabezado, ruta del recurso y etiquetas de propiedad. Debo identificar los offsets de los arrays W_IH y W_HO, así como los valores flotantes/dobles. El nombre de las propiedades en la serialización binaria está en formato FString. Vamos a inspeccionar los detalles.
>
> **Examinando formato de guardado de Unreal Engine**
>
>
> **Inspeccionando la propiedad BestFitness en el archivo**
>
> Necesito analizar la propiedad BestFitness. Después de ella, veo un posible valor `\x00\x00\x00\x00\x00`. Al parecer, podría ser una cadena que empieza con un entero de 32 bits indicando longitud, seguido de "BestFitness" y luego "DoubleProperty". Voy a revisar el volcado en hexadecimal para confirmar.
>
> **Mostrando volcado hexadecimal y analizando propiedades**
>
>
> **Analizando etiquetas de propiedades en el archivo**
>
> Necesito entender las etiquetas de propiedades. Después del tipo, hay 4 bytes (00 00 00 00), que podrían indicar el tamaño como int64. UE5 usa int64, así que el tamaño sería 8. Entonces, ¿esto podría ser un GUID o un valor booleano? También estoy viendo lo que podría ser el valor de BestFitness en 06e8, tal vez como un doble. Vamos a analizar más.
>
> **Desentrañando la estructura de bytes en el archivo**
>
> Necesito analizar con precisión los bytes. Después de encontrar una cadena en 06ca, veo bytes adicionales que podrían ser el tamaño y el índice del arreglo. En cuanto al tamaño, parece que podría estar utilizando int64. Sin embargo, no está claro si el tamaño de la propiedad está precedido por un valor booleano, o si es un FName con un puntero "None".
>
> **Calculando las dimensiones del array y el tamaño de los datos**
>
> Parece que la longitud de los datos del array es 320, basado en el número de entradas y neuronas ocultas. Con este cálculo, tengo 320 pesos para W_IH y 32 para W_HO. Al multiplicar por 8 para doubles, esos arrays suman 2816 bytes. Después, la metadata completa el tamaño del archivo.
>
> **Imprimiendo índices de datos estructurados**
>
>
> **Desentrañando el parámetro de tamaño y las secuencias de datos**
>
> Parece que después de "ArrayProperty", el valor de `ArrayIndex` podría estar entre los bytes 1808-1811. Posteriormente, localizo un tipo interno de 15 bytes, seguido de "DoubleProperty", con un tamaño asociado de 2564. También observo posibles GUIDs y un conteo en 1857. Necesito confirmar esto extra...
>
> **Localizando secuencia de bytes y longitud de arreglo**
>
>
> **Interpretando secuencias de datos y arreglos**
>
> Parece que el tamaño es 2564 (bytes 1835-1838), y el GUID podría estar presente entre los bytes 1840-1855. El índice del arreglo podría ser 0, pero es confuso. lo de "hasPropertyGuid" también parece un valor de sentencia. De todos modos, puedo extraer los arreglos de datos con las secuencias conocidas de conteos e índices.
>
> **Implementando heurística y parsing de datos**
>
> Puedo usar un enfoque donde encuentro el nombre de propiedad W_IH, seguido del entero 320, luego extraigo los 320 valores de tipo double después de eso. También debería considerar el parseo de BestFitness, probablemente ubicado en el offset 1775, con 8 bytes en 1773. De todos modos, ajustaré el código para decodificar correctamente.
>
> **Evaluando propiedades y extrayendo valores de arrays**
>
>
> **Gestionando archivos y duplicados con hash**
>
> Tengo que procesar el archivo 15_36 con BestFitness de 415.3025587. Parece que hay una diferencia de zona horaria con el log. Debo extraer todos los archivos .sav con BestFitness, calcular el hash SHA y los pesos (doubles exactos). También debo manejar duplicados si los pesos son iguales dentro de la tolerancia y generar un hash canonico de los pesos como SHA-256.
>
> **Extrayendo y comparando pesos y hashes**
>
>
> **Corregir extracción para BestFitness**
>
> Parece que mi extracción de BestFitness falló porque usé un rango demasiado amplio. Necesito encontrar el valor más cercano al log, entre los candidatos, que sea mayor a 100. Buscaré el valor más cercano al valor real antes de W_IH, ajustando y limitando el rango.
>
> **Ajustando selección de mejores valores de fitness**
>
>
> **Analizando duplicados de pesos**
>
> Encontré duplicados de pesos (16_43 y 17_45) con diferentes valores de BestFitness y hashes de archivos. Podría ser que solo el BestFitness haya cambiado. Necesito verificar si los archivos son realmente duplicados solo con la diferencia en el BestFitness. También investigaré si las HOs cambian o si las arrays exactas muestran algo más.
>
> **Analizando cambios en la fitness y registros de archivo**
>
> Los pesos no cambiaron, pero el modelo alcanzó una mayor fitness en otra generación debido a una variación de inicio, probablemente por la carga de un “elite car”. Los registros de log a las 14:43 y 15:45 (hora local) coinciden con los archivos 16_43 y 17_45. Necesito considerar esto al inspeccionar los resultados.
>
> **Generando reporte de duplicados y mejor modelo**
>
> Necesito continuar generando un reporte en formato CSV usando Python. Puedo agrupar duplicados y calcular distancias Hamming para clasificar similitudes. También puedo analizar la distancia entre vectores de pesos de modelos consecutivos para entender la progresión. El mejor modelo para reentrenar podría ser el 19_27, basado en la mejor fitness histórica.
>
> **Verificando registros posteriores en el log**
>
> El log muestra registros posteriores a las 19:27 con una mejor fitness, hasta 1495.28, pero esos archivos .sav no se subieron. Si tienes backups más recientes, deberían priorizarse. El log probablemente usa UTC mientras los nombres de archivo están en hora local. Puedo extraer esa información y destacarla.
>
> **Generando informe con duplicados y distancias Hamming**
>
>
> **Analizando registros de fitness y modelos históricos**
>
>
> **Verificando archivos .sav y mapeo de registros**
>
> Parece que los archivos .sav subidos tienen una diferencia de 2 horas con los registros del log, lo que sugiere que se usan horarios locales en lugar de UTC. Es probable que el usuario esté en España (horario UTC+2 en verano). Puedo generar un reporte en formato CSV con los hashes completos y grupos, excluyendo la necesidad de una hoja de cálculo.
>
> **Creando archivo visible para el usuario**
>
> Puedo generar un archivo en formato CSV para el usuario, ya que no se requiere una hoja de cálculo compleja. No es necesario usar herramientas específicas para hojas de cálculo como XLSX, y un archivo CSV es lo suficientemente simple para la tarea. Confirmaré el enlace al archivo generado sin complicaciones.
>
> **Verificando duplicados y distancias**
>
> Voy a calcular las distancias L2 entre los modelos para verificar si son duplicados o simplemente similares. Compararé los pesos y verificaré las diferencias. Es importante asegurarme de que no haya duplicados cercanos y que los modelos sean efectivamente únicos, utilizando numpy para facilitar el cálculo.
>
> **Calculando distancias L2 entre vectores de archivo**
>
>
> **Evaluando modelos redundantes y su impacto en pruebas**
>
> Puedo mencionar que no hay duplicados cercanos más allá de los duplicados exactos. De hecho, mantener solo 17_45 si usamos BestFitness podría ser lo ideal, pero ambos modelos tienen los mismos pesos. El cambio de LoadedBestFitness podría no afectar tanto, ya que la información de metadata podría no ser relevante aquí.
>
> **Preparando código para detectar duplicados y explicar el proceso**
>
> Puedo crear un código para detectar duplicados en el futuro, posiblemente usando funciones de análisis y hash para los modelos subidos. Es importante aclarar que no "deshashé" sino que extraí los pesos y calculé un hash canónico. También podría mencionar la arquitectura del modelo, como los 320 IH y 32 HO.
>
> **Organizando prioridades y análisis para reentrenar modelos**
>
> Voy a probar los modelos únicos, sin incluir los duplicados. Mi prioridad para reentrenar sería: 19_27 > 18_21 > 18_19 > 17_45/16_43. Importante mencionar que la "fitness histórica" no es lo mismo que la generalización del modelo. También, analizaré los puntos de aparición desde los logs para cada archivo .sav y sus mejores valores.
>
> **Asignando mejor valor a punto de aparición**
>
>
> **Creando informe de modelos con CSV**
>
> Voy a crear un informe con los modelos que el usuario ya proporcionó. Puede que no sea necesario, pero incluiré el análisis en un archivo CSV en "/mnt/data/hash_report_supercarmodels.csv". Finalmente, reflejaré en el resultado: "Con los modelos que ya has pasado...", ya que el usuario puede estar esperando solo confirmación.
>
> **Generando reporte CSV de modelos y análisis**
>
>
> Pensó durante 3m 42s

Sí, entendida la propuesta. Con los modelos que ya has pasado, he extraído los pesos `W_IH + W_HO` de cada `.sav` y he calculado un hash solo de pesos, ignorando diferencias de metadatos como `BestFitness`.

Resultado:

- **Modelos analizados:** 15
- **Tamaño de cada modelo:** 4768 bytes
- **Arquitectura detectada:** `W_IH = 320` pesos, `W_HO = 32` pesos
- **Duplicados exactos de archivo completo:** 0
- **Duplicados exactos de pesos:** 1 grupo
- **Modelos únicos por pesos:** 14

### Duplicado encontrado

Estos dos backups tienen **exactamente los mismos pesos**, aunque el `.sav` completo no sea idéntico porque cambia el `BestFitness` guardado:

| Modelo | BestFitness guardado | Hash pesos |
|---|---:|---|
| `SuperCarModel_prev_09_06_16_43.sav` | 672.687896 | `b7151c8d9b26...` |
| `SuperCarModel_prev_09_06_17_45.sav` | 672.735726 | `b7151c8d9b26...` |

**Conclusión:** no hace falta testear ambos. Para quedarte con uno, conservaría `SuperCarModel_prev_09_06_17_45.sav`, porque tiene el mismo cerebro pero mejor `BestFitness` asociado.

### Mejor candidato de los backups subidos

Entre los modelos que has pasado, el mejor por `BestFitness` guardado y además único por pesos es:

| Prioridad | Modelo | BestFitness | Hash pesos |
|---:|---|---:|---|
| 1 | `SuperCarModel_prev_09_06_19_27.sav` | 692.921810 | `e1299caa99d5...` |
| 2 | `SuperCarModel_prev_09_06_18_21.sav` | 688.530163 | `754646b6e66a...` |
| 3 | `SuperCarModel_prev_09_06_18_19.sav` | 677.530578 | `af1fc30ff3c9...` |
| 4 | `SuperCarModel_prev_09_06_17_45.sav` | 672.735726 | `b7151c8d9b26...` |

Mi recomendación práctica: para no hacer tests de más, elimina de la tanda de test `SuperCarModel_prev_09_06_16_43.sav` y quédate con `17_45`. Si quieres hacer una selección corta para reentrenar, probaría primero `19_27`, `18_21`, `18_19` y `17_45`.

Ojo: en el `clean_run_output.txt` aparecen récords posteriores bastante más altos, llegando a valores sobre **1496**, pero esos `.sav` posteriores no están en el lote que has subido. Si tienes esos backups, probablemente son más interesantes que todos estos.

Te dejo también el CSV con el informe completo de hashes:

[Descargar informe de hashes](sandbox:/mnt/data/model_weights_hash_report_09_06.csv)

## Prompt:
10/6/2026, 12:18:58

te paso los restantes:

[Attachment: SuperCarModel_prev_09_06_23_32.sav]

[Attachment: SuperCarModel_prev_09_06_23_36.sav]

[Attachment: SuperCarModel_prev_09_06_23_48.sav]

[Attachment: SuperCarModel_prev_09_06_23_54.sav]

[Attachment: SuperCarModel_prev_09_06_23_58.sav]

[Attachment: SuperCarModel_prev_10_06_00_01.sav]

[Attachment: SuperCarModel_prev_10_06_00_13.sav]

[Attachment: SuperCarModel_prev_10_06_00_16.sav]

[Attachment: SuperCarModel_prev_10_06_00_20.sav]

[Attachment: SuperCarModel_prev_10_06_00_39.sav]

[Attachment: SuperCarModel_prev_10_06_00_50.sav]

[Attachment: SuperCarModel_prev_10_06_00_56.sav]

[Attachment: SuperCarModel_prev_10_06_01_02.sav]

[Attachment: SuperCarModel_prev_10_06_06_47.sav]

[Attachment: SuperCarModel_prev_10_06_07_56.sav]

[Attachment: SuperCarModel_prev_10_06_09_53.sav]

[Attachment: SuperCarModel_prev_10_06_11_33.sav]

## Response:
10/6/2026, 12:18:46

Perfecto. Voy a integrar estos backups con los anteriores, recalcular hashes de pesos para todo el lote y sacar una lista final de modelos únicos recomendados para test/retrain.

> **Inspeccionando archivos y procesando datos**
>
>
> **Inspección binaria de archivo con hexdump y cadenas**
>
>
> **Mostrando hexadecimales y cadenas**
>
>
> **Buscando cadenas en archivo de guardado Unreal**
>
>
> **Parsing datos alrededor de BestFitness**
>
>
> **Localizando valores tipo double válidos**
>
>
> **Analizando el formato de propiedades en Unreal SaveGame**
>
> Parece que necesito analizar un encabezado específico y luego interpretar los nombres de clase y propiedades usando un formato de cadena. Al encontrar el tipo de propiedad, como "DoubleProperty", y su tamaño, deberé implementar funciones específicas, como `read_fstring` y un analizador de propiedades para obtener los desplazamientos adecuados.
>
> **Escribiendo el analizador de propiedades**
>
> Voy a empezar en la posición prop_start, justo antes de "BestFitness", para leer la cadena Fstring. Luego, leeré el tipo Fstring y posiblemente un tamaño int64. Hay que considerar la estructura de los datos, como el nombre, tipo, tamaño y valores específicos. Necesito asegurarme de que los desplazamientos sean correctos y de verificar cualquier posible desalineación al analizar los bytes.
>
> **Parseando encabezado GVAS y propiedades Unreal**
>
>
> **Inspeccionando el formato de propiedades en el archivo UE5**
>
> Parece que el valor de "BestFitness" en el archivo podría estar desalineado. Necesito considerar si el tamaño es int64 o más bien un int32. Además, el índice del array y un posible GUID de la propiedad podrían jugar un papel al lado de los valores tipo "FName". También debo verificar si hay alguna coincidencia con un valor de "BestFitness" conocido, como 1496.502.
>
> **Analizando el valor y los GUID en la ubicación correcta**
>
> Parece que el valor de "BestFitness" está exactamente en la posición 1773, después de un posible GUID de 16 bytes. A partir de ahí, el tamaño del array podría ser int32, seguido del índice y un posible token que indica la presencia de un GUID. Necesito confirmar la correspondencia entre estos valores y el valor esperado para el cálculo.
>
> **Inspeccionando archivos de juego y propiedades binarias**
>
>
> **Necesito parsear W y luego imprimir**
>
> Parece que debo procesar un valor o conjunto de datos denominado "W". Después de hacerlo, será necesario imprimir los resultados para confirmar si todo está correcto. Lo siguiente sería asegurarme de que la salida sea un formato legible o utilizable según lo que se espera.
>
> **Analizando y extrayendo datos de archivo**
>
>
> **Analizando propiedad de array y extracción de pesos**
>
> Parece que estoy lidiando con un array de propiedades, posiblemente con un tipo interno de `FName` o `FString`. Necesito extraer los pesos de manera confiable, observando el tamaño y los desplazamientos conocidos. Para obtener los elementos de `W_IH` y `W_HO`, voy a verificar las posiciones especificadas y analizar los valores alrededor de las ubicaciones clave encontradas.
>
> **Analizando propiedades de array y pesos**
>
> Parece que estoy tratando de analizar un array que tiene una estructura compleja: 4 bytes desconocidos, 4 bytes para el tamaño, un byte para banderas o GUID, y luego un GUID de 16 bytes. Después de esto, los pesos deben comenzar después del contador, pero necesito verificar el detalle final de la alineación de los datos para asegurarme de su precisión.
>
> **Buscando patrones en archivo de datos**
>
>
> **Confirmando el inicio de pesos y propiedades**
>
> Parece que los pesos comienzan en 1860 y, al sumar 2560, llegamos a 4420, que es el inicio de la propiedad W_HO. Ahora, necesitaré revisar el valor de 32 para W_HO y asegurarnos de que todo esté alineado según lo previsto.
>
> **Contando patrones en archivo de datos**
>
>
> **Finalizando procesamiento y considerando archivo final**
>
> Parece que el propósito es analizar todos los archivos, posiblemente generar un CSV con los datos más relevantes y agregar informes antiguos. Para compartirlo, puedo usar un análisis en Python y vincularlo adecuadamente utilizando herramientas disponibles. Es importante asegurarse de que el archivo visible para el usuario tenga la fuente correcta.
>
> **Asegurando la estructura de los datos y el cálculo de hashes**
>
> Parece que debo usar un contenedor para crear el archivo sin mostrar el código; es una mejor opción que usar python_user_visible. Además, para procesar todos los archivos .sav, necesito encontrar el valor de BestFitness. Para hash de los datos, podría usar sha256 o aplicar un hash directamente a los arreglos de pesos. Todo debe coincidir con la arquitectura vieja.
>
> **Determinando duplicados exactos y aproximados**
>
> Parece que debería comparar y verificar si las diferencias en los pesos son mínimas a través de un hash de los bytes crudos. Para los duplicados exactos, podría comparar los archivos y buscar grupos duplicados. También tendría que considerar cómo manejar posibles duplicados aproximados, dado que algunos modelos pueden diferir ligeramente.
>
> **Analizando modelos y detectando duplicados**
>
>
> **Verificando valores y ajustes de extracción**
>
> Necesito volver a ejecutar el proceso, esta vez ignorando la extracción extra. Además, debo verificar los valores de "bestfitness" comparándolos con los registros de logs para asegurarme de que todo esté correcto y alineado con los datos esperados.
>
> **Verificando valores de bestfitness y duplicados de pesos**
>
>
> **Verificando archivos y eliminando duplicados**
>
> Necesito verificar si se han analizado todos los archivos más recientes, combinando viejos y nuevos. Creo que deberíamos identificar los duplicados y hacer recomendaciones. Al parecer, hay 17 archivos nuevos, de los cuales 2 son duplicados. Finalmente, agregaré un resumen de los archivos restantes y crearé un CSV con los que se mantuvieron.
>
> Pensó durante 2m 40s

He integrado los **17 backups nuevos** con los **15 anteriores** y he recalculado todo por hash de pesos `W_IH + W_HO`.

## Resultado global

- **Modelos totales analizados:** 32
- **Modelos únicos por pesos:** 28
- **Duplicados exactos de archivo completo:** 0
- **Duplicados exactos de pesos:** 4 grupos
- **Arquitectura detectada en todos:** `W_IH = 320`, `W_HO = 32`

## Duplicados encontrados

Estos modelos tienen **exactamente los mismos pesos**, así que no merece la pena testear todos:

| Grupo | Modelos duplicados por pesos | Qué conservaría |
|---|---|---|
| 1 | `09_06_16_43` / `09_06_17_45` | `SuperCarModel_prev_09_06_17_45.sav` |
| 2 | `09_06_19_27` / `09_06_23_32` | `SuperCarModel_prev_09_06_23_32.sav` |
| 3 | `10_06_01_02` / `10_06_06_47` | `SuperCarModel_prev_10_06_06_47.sav` |
| 4 | `10_06_07_56` / `10_06_09_53` | `SuperCarModel_prev_10_06_09_53.sav` |

El criterio para conservar uno dentro de cada grupo ha sido: **mismos pesos → quedarse con el que tiene mayor `BestFitness` guardado**.

## Mejor modelo candidato para reentrenar

El mejor backup de todos los analizados es:

| Prioridad | Modelo | BestFitness | Estado |
|---:|---|---:|---|
| 1 | `SuperCarModel_prev_10_06_11_33.sav` | **1496.502346** | único |
| 2 | `SuperCarModel_prev_10_06_09_53.sav` | 1495.280513 | duplicado con `07_56`, conservar este |
| 3 | `SuperCarModel_prev_10_06_06_47.sav` | 1494.552258 | duplicado con `01_02`, conservar este |
| 4 | `SuperCarModel_prev_10_06_00_56.sav` | 1487.934091 | único |
| 5 | `SuperCarModel_prev_10_06_00_50.sav` | 1470.938468 | único |

Mi recomendación: **reentrena primero desde `SuperCarModel_prev_10_06_11_33.sav`**. Si quieres hacer test comparativo sin gastar demasiado, prueba solo los **top 5 únicos** de la tabla anterior.

## Modelos que puedes saltarte

No testearía estos porque tienen los mismos pesos que otro backup mejor del grupo:

- `SuperCarModel_prev_09_06_16_43.sav`
- `SuperCarModel_prev_09_06_19_27.sav`
- `SuperCarModel_prev_10_06_01_02.sav`
- `SuperCarModel_prev_10_06_07_56.sav`

Te dejo los dos CSV:

- [Informe completo de todos los backups](sandbox:/mnt/data/model_weights_hash_report_all_backups_09_10_06.csv)
- [Modelos únicos recomendados para test](sandbox:/mnt/data/unique_models_recommended_for_test_09_10_06.csv)



---
Powered by [ChatGPT Exporter](https://www.chatgptexporter.com)