# Configuración de semáforos en Unreal Engine

**Exported:** 6/29/2026 16:57:02  
**Link:** [https://gemini.google.com/app/97a50f001e874740?pli=1](https://gemini.google.com/app/97a50f001e874740?pli=1)

## Prompt:
quiero hacer un semaforo para vehiculos en unreal 5.5.4, pero no encuentro la documentación oficial de los tiempos establecidos e intervalos en los cambios de luces, cuanto duran esos intervalos, oficialmente en españa

## Response:
Para lograr un comportamiento realista y **legalmente coherente con España** en tu simulación de Unreal Engine 5.5.4, debes distinguir entre lo que es "normativa de tráfico" (lo que el conductor debe hacer) y la "ingeniería de tráfico" (cómo se programan los autómatas).

No existe una "ley" única que diga que el verde dura X segundos en todo el país, ya que depende del flujo de tráfico de cada cruce. Sin embargo, sí existen **estándares técnicos muy estrictos** (especialmente para el ámbar) que usan ayuntamientos como el de Madrid o Barcelona y la DGT para evitar accidentes y multas.

Aquí tienes los valores técnicos estándar para configurar tus variables (`float`) en el Blueprint/C++:

### 1\. La Tabla de Tiempos (Estándar Urbano Español)

Para una vía urbana estándar (límite 30-50 km/h), esta es la configuración más realista:

| Fase del Semáforo | Duración (Segundos) | Notas Técnicas |
| --- | --- | --- |
| **Verde** | **30.0s - 60.0s** | Variable. En Unreal, hazlo editable (`Exposed variable`) para ajustarlo según la "importancia" de la calle. |
| **Ámbar (Fijo)** | **3.0s** | **Crítico.** En España, el estándar técnico para zonas de 50km/h es de **3 segundos clavados**. Si pones menos es peligroso; si pones más, el conductor español tiende a acelerar. |
| **Rojo** | **Variable** | Depende del ciclo total. _Fórmula: Ciclo Total - (Verde + Ámbar)._ |
| **Rojo de Despeje** | **2.0s** | (Explicado abajo) Es vital para que tus coches (AI) no choquen en la simulación. |

### 2\. Detalles Técnicos para tu Lógica en Unreal

Para que el semáforo "se sienta" español, debes implementar estas dos lógicas que a menudo se olvidan en los videojuegos:

#### A. La "Fase de Despeje" (Inter-green / All-Red)

En España, cuando un semáforo se pone en rojo, el semáforo de la calle transversal **no se pone verde inmediatamente**. Existe un tiempo muerto donde **ambos** están en rojo.

*   **Duración:** 2 segundos.
*   **Por qué:** Para permitir que los vehículos que cruzaron en el último segundo de ámbar terminen de liberar la intersección antes de soltar el tráfico transversal.
*   **En Unreal:** Si no programas este `Delay`, tus vehículos AI chocarán en el centro del cruce frecuentemente.

#### B. El Ámbar Intermitente (Opcional)

Si quieres añadir un extra de realismo, puedes incluir la fase de "Ámbar Intermitente".

*   **Uso:** Se usa cuando el semáforo de peatones está en verde para cruzar, pero se permite el giro de vehículos cediendo el paso.
*   **Duración:** Coincide con el tiempo de verde de los peatones.

### 3\. Ejemplo de Lógica (Pseudocódigo para Blueprint)

Puedes estructurar tu `Enum` de estados así: `Green`, `Amber`, `Red`, `AllRed_Transition`.

```
// Configuración de variables (Editables)
float Time_Green = 45.0f; // Estándar medio
float Time_Amber = 3.0f;  // Estándar fijo DGT/Ayuntamientos
float Time_AllRed = 2.0f; // Seguridad (Despeje)

// Lógica del ciclo
Function RunCycle() {
    // 1. Calle Principal VERDE
    SetLightState(MainStreet, Green);
    SetLightState(CrossStreet, Red);
    Wait(Time_Green);

    // 2. Calle Principal ÁMBAR
    SetLightState(MainStreet, Amber);
    Wait(Time_Amber);

    // 3. TODO ROJO (Fase de Despeje - Muy importante)
    SetLightState(MainStreet, Red);
    SetLightState(CrossStreet, Red);
    Wait(Time_AllRed); 

    // 4. Calle Transversal VERDE
    SetLightState(CrossStreet, Green);
    // ... repetir lógica inversa
}
```

### Resumen para tu proyecto:

Si quieres ir a lo seguro y realista, usa **3 segundos para el ámbar**. Es el estándar de oro en ingeniería de tráfico en España para ciudad. Si tu carretera es de alta velocidad (tipo autovía de acceso a 80km/h), súbelo a **4 o 5 segundos**.

¿Te gustaría que te ayude a plantear la lógica de los materiales emisivos en Unreal para que el cambio de luz se vea realista (con ese pequeño "fade" de las bombillas incandescentes antiguas vs el cambio instantáneo de los LED modernos)?



---
Powered by [Gemini Exporter](https://www.ai-chat-exporter.com)