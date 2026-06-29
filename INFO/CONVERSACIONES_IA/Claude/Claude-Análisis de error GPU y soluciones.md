# Análisis de error GPU y soluciones

**Created:** 5/21/2026 11:24:51  
**Updated:** 6/2/2026 12:14:44  
**Exported:** 6/29/2026 16:13:33  
**Link:** [https://claude.ai/chat/a3b8ac5a-f2a5-4e8c-8e1a-5b6671ebb037](https://claude.ai/chat/a3b8ac5a-f2a5-4e8c-8e1a-5b6671ebb037)  

## User:

> 5/21/2026 11:24:51

> File: INTERSECTIONS 20-05-2026.txt

> File: EVOLUTIONMANAGER 20-05-2026.txt

> File: FITNESS 20-05-2026.txt

> File: RED NEURONAL 19-05-2026.txt

> File: clean_run_output.txt

> File: Fitness_Debug.csv

> File: informe.txt

> File: Training_Summary.csv

te adjunto un entrenamiento que he realizado, analiza los datos exhaustivamente y busca que ha ocurrido, y dame mejoras, soluciones o lo que encuentres y calcules. 

Me he encontrado con el programa parado, con el aviso de error:
ErrorGPU Crashed or D3D Device Removed.Check log for GPU state information.A GPU mini dump has been written to"..///../../../Users/SergioULE/Documents/Unreal Projects/cognitive-car/Saved/Logs/D3D12.2026.05.21-00.37.30.nv-gpudmp".

Quiero que compruebes que ha podido ocurrir, y me digas tambien, una solucion para que no vuelva a ocurrir:

## Assistant:

> 5/21/2026 11:27:19

> Reunió información adicional para análisis exhaustivo.
>
> - The user has uploaded several files related to a training run and is asking me to analyze the data exhaustively. They also encountered a GPU crash error (D3D Device Removed) and want to know what happened and how to prevent it.
>   
>   Let me first read the skill for file reading, then read all the uploaded files.
> - Reading file-reading skill
> - Check sizes of all uploaded files
> - Read the main report file
> - Read the clean run output log
> - Read the end of the run output to see the crash context
> - Now I have all the critical information. Let me also quickly check the other txt files for additional context.
> - **Done**

Tengo todos los datos necesarios. Ahora voy a generar el informe completo.

> [Interactive Widget: training_analysis_dashboard]

Aquí tienes el análisis completo. Lo divido en las dos partes que pediste:

---

## 🔴 El crash de GPU — qué pasó exactamente

El dump de NVIDIA Aftermath lo deja bastante claro: la GPU entró en estado **Hung** (`DXGI_ERROR_DEVICE_HUNG`), con un engine reset forzado. El breadcrumb señala que el proceso activo en el momento del crash era `UpdateAllPrimitiveSceneInfos` — la operación que actualiza en GPU la posición y estado de todos los objetos de la escena cada frame.

La clave está en los datos de contexto: **60.7 horas de sesión continua** sin reiniciar el editor (SecondsSinceStart = 218 552 segundos). Con 24 vehículos con física Chaos activa, Nanite, Virtual Shadow Maps y TSR encendidos, la GPU genera frametime spikes periódicos. Windows tiene un watchdog llamado TDR (Timeout Detection & Recovery) que mata el dispositivo si detecta que la GPU no responde en 2 segundos — ese es el mecanismo que disparó el crash. No fue falta de VRAM (solo usaba 5.5 de 11.3 GB), ni un shader buggy, ni corrupción de memoria.

---

## 🟡 El estado del entrenamiento

La sesión fue la **peor de las últimas 9 sesiones comparadas** en MeanFit (puesto 9/9) y BestFit (puesto 8/9). El problema central es la combinación de LAZY masivo (37.7%) + StopTrap en SpawnPoint51 y SpawnPoint28 que arrastra el MeanFit hacia abajo. El BestFit individual de 66 351 en gen 191 es sólido, pero la población general se deteriora a partir de gen 150.

Las soluciones más urgentes están en el widget, ordenadas por prioridad. Lo más impactante a corto plazo sería: aumentar el TDR timeout en el registro de Windows antes de la próxima sesión, y en el entrenamiento, desactivar o penalizar menos los spawns 51 y 28 mientras se investiga la lógica del stop que los bloquea.

## User:

> 5/21/2026 11:48:30

> File: 1779356932447_ConsoleVariables.ini

## Assistant:

> 5/21/2026 11:49:03

> Synthesized configuration modifications for performance optimization.
>
> - The user uploaded their ConsoleVariables.ini file. I need to add the recommended fixes from the previous analysis to this file and provide it back to them.
>   
>   Let me create the modified file with the GPU crash prevention settings and training optimization settings added.
> - Copy the uploaded file to working directory
> - Add GPU crash prevention and training optimization CVars at the end of the [Startup] section
> - Copy to outputs
> - Presenting file(s)...
> - **Done**

He añadido un bloque nuevo al final del `[Startup]` con dos grupos de ajustes:

**Diagnóstico GPU (permanente):**
- `r.D3D12.EnableDRED=1` — activa el Device Removed Extended Data. En tu crash del 20/05 este flag estaba a `false`, por eso el breadcrumb salió vacío. Con esto activado, el próximo crash identificará el comando DX12 exacto que colgó la GPU.

**Reducción de carga en training (los CVars que reducen el riesgo de TDR):**
- `r.Shadow.Virtual.Enable=0` — quita los Virtual Shadow Maps, que son muy intensivos en GPU
- `sg.AntiAliasingQuality=1` — TSR era el paso siguiente al cuelgue según el breadcrumb; bajarlo a low quita esa presión
- `r.SSR.Quality=0` y `r.AmbientOcclusionLevels=0` — reflejos y AO innecesarios en training
- `t.MaxFPS=30` — limita framerate sostenido; reduce temperatura y spikes de frametime que disparan el TDR
- `r.TemporalAA.Method=0` — desactiva TSR completamente

**Importante:** el ajuste de TDR timeout (`TdrDelay=60` en el registro) hay que hacerlo manualmente desde regedit porque no es un CVar de UE, es una configuración de Windows. La ruta es `HKLM\System\CurrentControlSet\Control\GraphicsDrivers`.

> File: [/mnt/user-data/outputs/ConsoleVariables.ini](https://claude.ai/api/organizations/706da224-e70c-4277-af18-892b799d7906/conversations/a3b8ac5a-f2a5-4e8c-8e1a-5b6671ebb037/wiggle/download-file?path=%2Fmnt%2Fuser-data%2Foutputs%2FConsoleVariables.ini)

## User:

> 5/21/2026 11:51:15

quiero solo que modifiques lo del diagnostico, para tener una explicacion más detallada de que ha ocurrido, el resto, no creo que deberiamos de tocarlo porque para el modo test, o cuando un usuario quiera probar el simulador, debe tener la mejor iluminación

## Assistant:

> 5/21/2026 11:51:42

> Identificó solicitud de modificar solo configuración diagnóstica.
>
> - The user wants to keep only the DRED diagnostic setting and remove the graphics quality reduction settings.
> - **Done**

Tiene todo el sentido, tienes razón.

> Edited 2 files, ran command, presented file
>
> - Remove graphics quality settings, keep only DRED diagnostic
> - Remove graphics quality settings, keep only DRED diagnostic
> - Copy updated file to outputs
> - Presenting file(s)...
> - **Done**

Listo. Solo he dejado `r.D3D12.EnableDRED=1` con un comentario detallado que explica exactamente qué hace, por qué se añadió y qué información extra aparecerá en el log si vuelve a ocurrir un crash. El resto del archivo queda intacto.

Recuerda que el ajuste del TDR en el registro de Windows sigue siendo la protección más importante para evitar que el crash se repita — ese no depende de este archivo.

> File: [/mnt/user-data/outputs/ConsoleVariables.ini](https://claude.ai/api/organizations/706da224-e70c-4277-af18-892b799d7906/conversations/a3b8ac5a-f2a5-4e8c-8e1a-5b6671ebb037/wiggle/download-file?path=%2Fmnt%2Fuser-data%2Foutputs%2FConsoleVariables.ini)

Powered by Claude Exporter (https://www.ai-chat-exporter.net)
