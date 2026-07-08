# Preguntas prioritarias para defensa oral

## Resultados y protocolo experimental

1. ¿Por qué se mantiene el 18 de junio como referencia histórica si el 7 de julio obtiene una tasa mayor?
2. ¿Qué diferencia hay entre la referencia histórica del 18 de junio y la validación final instrumentada del 7 de julio?
3. ¿Por qué no se agregan directamente el 57.50 % y el 84.64 %?
4. ¿Qué significa exactamente “acierto operativo” y qué no garantiza?
5. ¿Cómo se interpreta el descuadre entre `Test_Summary.csv` y `Fitness_Debug.csv` en el bloque del 7 de julio?
6. ¿Por qué `OVERLAP_TIMEOUT` queda como diagnóstico de convivencia en ese bloque y no como fallo añadido a la tasa?
7. ¿Qué papel tiene `SuperCarModel` en los tests y por qué `SessionCarModel` no se usa para identificar el modelo evaluado?
8. ¿Qué limitaciones introduce no disponer de semillas aleatorias documentadas ni réplicas completas independientes?
9. ¿Por qué el bloque alto del 26 de junio no se usa como referencia principal?
10. ¿Por qué `FreeRun` se considera diagnóstico y no test generacional comparable?

## Entrenamiento, fitness y modelo

11. ¿Por qué se eligió el entrenamiento del 18 de junio como sesión representativa si el máximo aparece pronto y luego hay meseta?
12. ¿Qué indica que el tiempo medio de vida aumente mientras el `MeanFit` no mejora de forma sostenida?
13. ¿Qué componentes principales suma y penaliza la función de fitness?
14. ¿Cómo se justifica la penalización por corrección lateral incorrecta?
15. ¿Qué papel tiene la mutación dinámica y por qué no se usó un enfoque de aprendizaje por refuerzo clásico?
16. ¿Por qué se eligió una red 20-16-2 y qué limitaciones tiene esa arquitectura?
17. ¿Qué implicaría añadir una línea base reglada para comparar los resultados?

## Simulador, tráfico y normativa

18. ¿Por qué se descartó `NavMesh`/`Path Finding` como solución principal para coches físicos?
19. ¿Qué fallos normativos siguen pendientes tras el 84.64 % del bloque final?
20. ¿Por qué las rotondas siguen siendo una zona crítica del sistema?
21. ¿Qué cambios serían prioritarios antes de aumentar la densidad de tráfico o añadir peatones y bicicletas?
22. ¿Qué parte del proyecto podría ser útil en un contexto clínico y qué faltaría para hablar de validación clínica real?
23. ¿Cómo se ha tratado el RGPD, la LOPDGDD, el AI Act y la accesibilidad en el alcance actual?
24. ¿Qué papel tuvieron las herramientas de IA en la memoria y cómo se controló que no sustituyeran las fuentes primarias?
