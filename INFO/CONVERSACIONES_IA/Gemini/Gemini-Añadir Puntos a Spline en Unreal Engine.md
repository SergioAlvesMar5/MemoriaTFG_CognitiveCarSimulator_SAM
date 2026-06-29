# Añadir Puntos a Spline en Unreal Engine

**Exported:** 6/29/2026 16:56:55  
**Link:** [https://gemini.google.com/app/5802f4537f4bfd88?pli=1](https://gemini.google.com/app/5802f4537f4bfd88?pli=1)

## Prompt:
en unreal engine 5.5, si tengo una spline, como añado un punto

## Response:
En Unreal Engine 5.5, existen dos formas principales de añadir un punto a una **Spline**: manualmente en el editor (mientras diseñas el nivel) o programáticamente mediante Blueprints (durante el juego o en el Construction Script).

Aquí tienes los pasos detallados para ambos casos:

### 1\. En el Editor (Viewport)

Esta es la forma más común si estás construyendo un nivel o una carretera manualmente.

**Método A: La tecla ALT (El más rápido)** Este es el método estándar para extender una spline.

1.  Selecciona el **Actor** que contiene la Spline en tu nivel.
2.  Haz clic en el **último punto** (o cualquier punto existente) de la línea de la spline para seleccionarlo. Verás el gizmo de transformación (las flechas de movimiento).
3.  Mantén presionada la tecla **`Alt`** en tu teclado.
4.  Mientras mantienes `Alt`, **arrastra** una de las flechas del gizmo hacia afuera.
5.  Se creará un nuevo punto conectado al anterior.

**Método B: Clic Derecho (Para insertar en medio)** Si necesitas añadir un punto entre dos puntos existentes:

1.  Selecciona el segmento de la línea (la curva blanca) entre dos puntos.
2.  Haz clic derecho sobre la línea.
3.  En el menú contextual, selecciona **"Add Spline Point Here"** (Añadir punto de spline aquí).

### 2\. En Blueprints (Programación)

Si necesitas que la spline crezca dinámicamente mientras juegas (por ejemplo, un rastro detrás de un personaje), usarás nodos.

1.  Abre tu **Blueprint**.
2.  Arrastra la referencia de tu **Spline Component** al gráfico de eventos.
3.  Desde el pin del componente, busca el nodo **`Add Spline Point`**.

**Configuración del nodo:**

*   **Position:** Las coordenadas X, Y, Z donde quieres el nuevo punto.
*   **Coordinate Space:**
    *   _Local:_ El punto se añade relativo al centro del actor.
    *   _World:_ El punto se añade en una coordenada global del mapa.
*   **Update Spline:** Mantenlo marcado para que la forma se recalcule visualmente al instante.

> **Nota:** Si quieres insertar un punto en un índice específico (en medio de la spline y no al final), usa el nodo **`Add Spline Point at Index`**.

### Resumen de Atajos de Teclado

| Acción | Atajo | Descripción |
| --- | --- | --- |
| **Extender Spline** | `Alt` + Arrastrar | Crea un nuevo punto al final. |
| **Borrar Punto** | `Supr` (Delete) | Elimina el punto seleccionado. |
| **Duplicar Punto** | `Ctrl` + `W` | Duplica el punto en la misma ubicación (útil para esquinas cerradas). |

**¿Te gustaría que te explique cómo hacer que un objeto siga esa spline automáticamente?**

## Prompt:
vale, en un mapa como subo y bajo? en el editor vaya

## Response:
Para moverte verticalmente (subir y bajar) con la cámara en el editor de Unreal Engine 5, tienes dos formas principales dependiendo de tu estilo de trabajo:

### 1\. Estilo "Videojuego" (El más común)

Este método es ideal para moverte libremente por el nivel.

1.  Mantén presionado el **Clic Derecho** del ratón (para entrar en modo vuelo).
2.  Usa estas teclas:
    *   **`Q`**: Para **Bajar** (descender).
    *   **`E`**: Para **Subir** (ascender).

_(Nota: Esto funciona combinado con WASD para moverte horizontalmente)._

### 2\. Estilo "Software 3D" (Panning)

Si prefieres usar solo el ratón (útil para encuadres precisos):

*   Haz **Clic Central** (la rueda del ratón) y manténlo presionado.
*   Mueve el ratón hacia adelante (arriba) o atrás (abajo).

> **Truco Pro:** Si sientes que la cámara se mueve muy lento o muy rápido, mientras mantienes el **Clic Derecho**, gira la **Rueda del Ratón** para ajustar la velocidad de vuelo al instante.

¿Quieres que te explique cómo enfocar rápidamente un objeto que has perdido de vista?



---
Powered by [Gemini Exporter](https://www.ai-chat-exporter.com)