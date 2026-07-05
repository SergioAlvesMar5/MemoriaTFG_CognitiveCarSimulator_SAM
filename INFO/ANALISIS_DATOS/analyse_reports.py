# -*- coding: utf-8 -*-
"""Parte interna de analyse_current.py.

Este archivo se carga desde analyse_current.py dentro del mismo namespace global
para mantener compatibilidad con los imports existentes y con la CLI antigua.
No esta pensado para ejecutarse directamente.
"""

# ── Informe de texto ──

class Report:
    def __init__(self):
        self.lines = []
    def p(self, s=''):
        self.lines.append(s)
        logging.info(s)
    def save(self, path):
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.lines))

def report_summary(R, rows):
    n = len(rows)
    if n == 0:
        R.p(f'  No hay datos en {SUMMARY_FILE}')
        return
    freerun = is_freerun_analysis(summary_rows=rows)

    R.p(f'\n{"="*76}')
    if freerun:
        R.p(f'  ANALISIS {LABEL} - FREE RUN (snapshot sin eje generacional)')
    else:
        R.p(f'  ANALISIS {LABEL} - {n} generaciones')
    R.p(f'  Fecha: {datetime.now().strftime("%d/%m/%Y %H:%M")}')
    R.p(f'{"="*76}')

    br = max(rows, key=lambda x: x['best'])
    mr = max(rows, key=lambda x: x['mean'])
    wr = min(rows, key=lambda x: x['mean'])
    neg = sum(1 for r in rows if r['mean'] < 0)
    avg_best   = sdiv(sum(r['best'] for r in rows), n)
    avg_mean   = sdiv(sum(r['mean'] for r in rows), n)
    avg_time   = sdiv(sum(r['time'] for r in rows), n)
    avg_pop    = sdiv(sum(r['pop_count'] for r in rows), n)
    p25_mean   = pctl([r['mean'] for r in rows], 25)
    p50_mean   = pctl([r['mean'] for r in rows], 50)
    p75_mean   = pctl([r['mean'] for r in rows], 75)
    pop_den = estimate_population_size(rows)

    R.p(f'\n-- Estadisticas Generales --')
    if freerun:
        R.p('  Generaciones:     n/a en FreeRun (gen 0/1 constante; snapshot reconstruido)')
        R.p(f'  BestFit terminal: {br["best"]:.6f}')
        R.p(f'  BestFit medio:    {avg_best:.6f}')
        R.p(f'  MeanFit terminal: {avg_mean:.6f}')
        R.p(f'  MeanFit P50:      {p50_mean:.6f}')
    else:
        R.p(f'  Generaciones:     {rows[0]["gen"]} - {rows[-1]["gen"]} ({n} total)')
        R.p(f'  BestFit max:      {br["best"]:.6f}  (gen {br["gen"]})')
        R.p(f'  BestFit medio:    {avg_best:.6f}')
        R.p(f'  MeanFit max:      {mr["mean"]:.6f}  (gen {mr["gen"]})')
        R.p(f'  MeanFit medio:    {avg_mean:.6f}')
        R.p(f'  MeanFit min:      {wr["mean"]:.6f}  (gen {wr["gen"]})')
    R.p(f'  MeanFit P25/P50/P75: {p25_mean:.4f} / {p50_mean:.4f} / {p75_mean:.4f}')
    R.p(f'  MeanFit < 0:      {neg}/{n} ({sdiv(neg*100,n):.1f}%)')
    time_label = 'Tiempo terminal' if freerun else 'TiempoMedio'
    R.p(f'  {time_label}:      {min(r["time"] for r in rows):.2f}s - {max(r["time"] for r in rows):.2f}s (media {avg_time:.2f}s)')
    R.p(f'  PopDeaths medio:  {avg_pop:.1f}/{pop_den}')

    # KPIs de testing (si el CSV trae columnas extendidas)
    has_test_kpi = any('success_rate' in r for r in rows)
    if has_test_kpi:
        kpi_rows = [r for r in rows if 'success_rate' in r]
        nk = len(kpi_rows)
        derived = [binary_metrics_from_row(r) for r in kpi_rows]
        avg_success = sdiv(sum(m['success_rate'] for m in derived), nk)
        avg_fail = sdiv(sum(m['fail_rate'] for m in derived), nk)
        avg_n = sdiv(sum(m['n'] for m in derived), nk)

        # Score teórico recomendado: limite inferior de Wilson por fila (conservador)
        wl_rows = [m['wilson_lo'] for m in derived if m['n'] > 0]
        avg_score_wilson = sdiv(sum(wl_rows), len(wl_rows)) if wl_rows else 0.0

        # Score directo de acierto (referencia simple)
        avg_score_success = avg_success

        # Agregados globales para IC Wilson (sin depender de PopulationSize fija)
        total_eval = sum(m['n'] for m in derived)
        if total_eval == 0:
            total_eval = sum(
                r.get('success_count', 0)
                + r.get('fail_hard_count', 0)
                + r.get('fail_early_count', 0)
                + r.get('fail_collision_count', 0)
                for r in kpi_rows
            )
        total_success = sum(r.get('success_count', 0) for r in kpi_rows)
        total_fail = sum(r.get('fail_count', 0) for r in kpi_rows)
        total_censored = sum(int(num(r.get('censored_count', 0), 0.0)) for r in kpi_rows)
        lo_s, hi_s = wilson_ci(total_success, total_eval)

        # Distribucion entre generaciones para estabilidad
        p10_success = pctl([r['success_rate'] for r in kpi_rows], 10)
        p50_success = pctl([r['success_rate'] for r in kpi_rows], 50)
        p90_success = pctl([r['success_rate'] for r in kpi_rows], 90)
        has_csv_score = any('score' in r for r in kpi_rows)
        if has_csv_score:
            p10_score = pctl([r['score'] for r in kpi_rows if 'score' in r], 10)
            p50_score = pctl([r['score'] for r in kpi_rows if 'score' in r], 50)
            p90_score = pctl([r['score'] for r in kpi_rows if 'score' in r], 90)

        R.p(f'\n-- KPI de Test ({"FreeRun reconstruido" if freerun else "promedio"}) --')
        R.p(f'  N evaluado medio: {avg_n:.1f}')
        R.p(f'  Aciertos (%):     {avg_success:.2f}%')
        R.p(f'  Errores (%):      {avg_fail:.2f}%')
        R.p(f'  Score (Acierto):  {avg_score_success:.2f}')
        R.p(f'  Score (WilsonLB): {avg_score_wilson:.2f}')
        if not freerun:
            R.p(f'  Success P10/P50/P90: {p10_success:.2f}% / {p50_success:.2f}% / {p90_success:.2f}%')
        if total_censored > 0:
            success_upper = sdiv((total_success + total_censored) * 100.0, total_eval)
            observed_rate = sdiv(total_success * 100.0, total_success + total_fail)
            R.p(f'  Censurados vivos: {total_censored}/{total_eval} ({sdiv(total_censored*100.0, total_eval):.2f}%)')
            R.p(f'  Acierto observado terminal: {observed_rate:.2f}%')
            R.p(f'  Rango acierto con censura:  {avg_success:.2f}% - {success_upper:.2f}%')
            if freerun:
                R.p('  Nota FreeRun: los censurados no son exitos cerrados; representan coches vivos al cortar la simulacion.')
        if has_csv_score:
            R.p(f'  ScoreCSV P10/P50/P90:    {p10_score:.2f} / {p50_score:.2f} / {p90_score:.2f}')
        R.p(f'  IC95 Aciertos (global): [{lo_s*100:.2f}%, {hi_s*100:.2f}%]')

    # Primeras vs ultimas
    if n >= 10:
        ln = min(50, n // 3)
        head = rows[:ln]
        tail = rows[-ln:]
        R.p(f'\n-- Comparacion primeras {ln} vs ultimas {ln} gens --')
        hdr = f'  {"":>15s} | {"BestFit":>11s} | {"MeanFit":>11s} | {"Tiempo":>7s} | {"PopC":>5s} | {"%Neg":>5s}'
        R.p(hdr)
        R.p(f'  {"-"*(len(hdr)-2)}')
        for name, blk in [('Primeras', head), ('Ultimas', tail)]:
            nb = len(blk)
            R.p('  {:>15s} | {:>11.4f} | {:>11.4f} | {:>6.2f}s | {:>5.1f} | {:>4.0f}%'.format(
                name,
                sdiv(sum(r['best'] for r in blk), nb),
                sdiv(sum(r['mean'] for r in blk), nb),
                sdiv(sum(r['time'] for r in blk), nb),
                sdiv(sum(r['pop_count'] for r in blk), nb),
                sdiv(sum(1 for r in blk if r['mean']<0)*100, nb)))
        # Mejora
        m_head = sdiv(sum(r['mean'] for r in head), len(head))
        m_tail = sdiv(sum(r['mean'] for r in tail), len(tail))
        if m_head != 0:
            pct = (m_tail - m_head) / abs(m_head) * 100
            direction = 'MEJORA' if m_tail > m_head else 'EMPEORA'
            R.p(f'  >> MeanFit: {direction} {abs(pct):.1f}% (de {m_head:.4f} a {m_tail:.4f})')
        t_head = sdiv(sum(r['time'] for r in head), len(head))
        t_tail = sdiv(sum(r['time'] for r in tail), len(tail))
        if t_head != 0:
            pct_t = (t_tail - t_head) / abs(t_head) * 100
            dir_t = 'MEJORA' if t_tail > t_head else 'EMPEORA'
            R.p(f'  >> TiempoMedio: {dir_t} {abs(pct_t):.1f}% (de {t_head:.2f}s a {t_tail:.2f}s)')

    # Muerte mejor coche
    R.p(f'\n-- Razones de Muerte (Mejor Coche) --')
    bd = Counter(r['best_death'] for r in rows)
    for reason, cnt in bd.most_common():
        R.p(f'  {reason:40s}: {cnt:4d} ({sdiv(cnt*100,n):.1f}%)')

    # Muerte mas popular
    R.p(f'\n-- Razon de Muerte Mas Popular (Poblacion) --')
    pd = Counter(r['pop_death'] for r in rows)
    for reason, cnt in pd.most_common():
        avg_c = sdiv(sum(r['pop_count'] for r in rows if r['pop_death']==reason), cnt)
        R.p(f'  {reason:40s}: {cnt:4d} gens (media {avg_c:.1f}/{pop_den})')

    # Bloques
    if n >= 5:
        if n < 30:     blk = max(1, n // 5)
        elif n < 200:  blk = 20
        elif n < 1000: blk = 100
        else:          blk = 200

        R.p(f'\n-- Bloques de {blk} generaciones --')
        hdr = f'  {"Gens":>12s} | {"BestFit":>10s} | {"MeanFit":>10s} | {"Time":>6s} | {"PopC":>5s} | {"Neg%":>5s}'
        R.p(hdr)
        R.p(f'  {"-"*(len(hdr)-2)}')
        for i in range(0, n, blk):
            b = rows[i:i+blk]
            nb = len(b)
            R.p('  {:>5d}-{:>5d} | {:>10.4f} | {:>10.4f} | {:>5.2f}s | {:>5.1f} | {:>4.0f}%'.format(
                b[0]['gen'], b[-1]['gen'],
                sdiv(sum(r['best'] for r in b), nb),
                sdiv(sum(r['mean'] for r in b), nb),
                sdiv(sum(r['time'] for r in b), nb),
                sdiv(sum(r['pop_count'] for r in b), nb),
                sdiv(sum(1 for r in b if r['mean']<0)*100, nb)))

    # Tendencia bloques de 50
    if n >= 50:
        R.p(f'\n-- Tendencia MeanFit (bloques de 50) --')
        for i in range(0, n, 50):
            b = rows[i:i+50]
            am = sdiv(sum(r['mean'] for r in b), len(b))
            at = sdiv(sum(r['time'] for r in b), len(b))
            bar_len = max(0, int(am * 10)) if am > 0 else 0
            bar = '#' * min(bar_len, 60)
            R.p(f'  {b[0]["gen"]:>5d}-{b[-1]["gen"]:>5d}: MeanFit={am:>10.4f} | t={at:.2f}s {bar}')

    # Top 10
    top_n = min(10, n)
    if freerun:
        R.p(f'\n-- Snapshot FreeRun (BestFit terminal) --')
        for idx, r in enumerate(sorted(rows, key=lambda x:-x['best'])[:top_n], start=1):
            R.p(f'  Snapshot {idx:>2d}: Best={r["best"]:.4f}  Mean={r["mean"]:.4f}  t={r["time"]:.2f}s  {r["best_death"]}')

        R.p(f'\n-- Snapshot FreeRun (MeanFit terminal) --')
        for idx, r in enumerate(sorted(rows, key=lambda x:-x['mean'])[:top_n], start=1):
            R.p(f'  Snapshot {idx:>2d}: Mean={r["mean"]:.4f}  Best={r["best"]:.4f}  t={r["time"]:.2f}s')
    else:
        R.p(f'\n-- Top {top_n} (BestFit) --')
        for r in sorted(rows, key=lambda x:-x['best'])[:top_n]:
            R.p(f'  Gen {r["gen"]:>5d}: Best={r["best"]:.4f}  Mean={r["mean"]:.4f}  t={r["time"]:.2f}s  {r["best_death"]}')

        R.p(f'\n-- Top {top_n} (MeanFit) --')
        for r in sorted(rows, key=lambda x:-x['mean'])[:top_n]:
            R.p(f'  Gen {r["gen"]:>5d}: Mean={r["mean"]:.4f}  Best={r["best"]:.4f}  t={r["time"]:.2f}s')

def report_convergence_analysis(R, summary_rows):
    """Reporte detallado de convergencia y estabilidad."""
    conv_info = analyze_convergence(summary_rows)
    if not conv_info:
        return
    
    R.p(f'\n{"="*76}')
    R.p(f'  ANALISIS DE CONVERGENCIA Y ESTABILIDAD')
    R.p(f'{"="*76}')
    
    R.p(f'\n-- Mejora General --')
    R.p(f'  Fitness máximo alcanzado:  {conv_info["max_best"]:.6f}')
    R.p(f'  Generación del máximo:     Gen {conv_info["gen_at_max"]}')
    R.p(f'  Fitness inicial:           {conv_info["initial_best"]:.6f}')
    R.p(f'  Mejora total:              {conv_info["total_improvement"]:.6f} ({conv_info["improvement_pct"]:.2f}%)')
    
    R.p(f'\n-- Estado de Convergencia --')
    R.p(f'  Generaciones en plateau:   {conv_info["plateau_gens"]} ({conv_info["plateau_pct"]:.1f}%)')
    R.p(f'  Varianza promedio:         {conv_info["avg_variance"]:.6f}')
    R.p(f'  Tendencia reciente (últ 10): {conv_info["recent_trend"]:.8f}')
    R.p(f'  CV (Best):                 {conv_info["cv_best"]:.4f}')
    R.p(f'  CV (Mean):                 {conv_info["cv_mean"]:.4f}')
    
    R.p(f'\n-- Diagnóstico --')
    if conv_info["is_converged"]:
        R.p(f'  [OK] CONVERGENCIA DETECTADA: >30% generaciones en plateau')
    else:
        R.p(f'  [*] Sin convergencia clara (todavía explorando)')
    
    if conv_info["is_improving"]:
        R.p(f'  [OK] MEJORANDO: Tendencia positiva reciente')
    else:
        R.p(f'  [X] Estancado: Sin mejora significativa')

def report_diversity_analysis(R, debug_rows):
    """Reporte de diversidad genética poblacional."""
    div_info = analyze_diversity(debug_rows)
    if not div_info:
        return
    
    R.p(f'\n{"="*76}')
    R.p(f'  ANALISIS DE DIVERSIDAD GENETICA')
    R.p(f'{"="*76}')
    
    R.p(f'\n-- Distribución de Familias --')
    R.p(f'  Total coches evaluados:    {div_info["total_cars"]}')
    R.p(f'  Modelos cargados:          {div_info["loaded_share"]:.1f}%')
    R.p(f'  Modelos aleatorios:        {div_info["random_share"]:.1f}%')
    R.p(f'  Modelos mutados:           {div_info["mutated_share"]:.1f}%')
    
    R.p(f'\n-- Desempeño por Familia --')
    for fam in ['LOADED', 'SESSION', 'MUT_LOADED', 'MUT_SESSION', 'MUT_LOADED_LARGE', 'RANDOM']:
        stats = div_info["family_stats"].get(fam)
        if stats:
            R.p(f'  {fam:15s}: N={stats["count"]:4d} | media={stats["mean_fitness"]:9.2f} | std={stats["std_fitness"]:.2f}')
    
    R.p(f'\n-- Entropía y Diversidad --')
    R.p(f'  Entropía Shannon:          {div_info["entropy"]:.4f}')
    R.p(f'  Entropía normalizada:      {div_info["normalized_entropy"]:.4f}')
    if div_info["is_diverse"]:
        R.p(f'  [OK] DIVERSIDAD ADECUADA: Población heterogénea')
    else:
        R.p(f'  [!] DIVERSIDAD BAJA: Población concentrada en pocas familias')

def report_prediction_analysis(R, summary_rows):
    """Reporte de predicción de trayectoria fitness."""
    pred_info = predict_fitness_trajectory(summary_rows, future_gens=10)
    if not pred_info:
        return
    
    R.p(f'\n{"="*76}')
    R.p(f'  ANALISIS PREDICTIVO')
    R.p(f'{"="*76}')
    
    R.p(f'\n-- Regresión Lineal (últimas 20 gens) --')
    R.p(f'  Pendiente (slope):         {pred_info["slope"]:.8f}')
    R.p(f'  Correlación:               {pred_info["correlation"]:.4f}')
    R.p(f'  Ajuste del modelo:         {"Bueno" if abs(pred_info["correlation"]) > 0.7 else "Moderado" if abs(pred_info["correlation"]) > 0.4 else "Débil"}')
    
    R.p(f'\n-- Predicciones (próximas 10 generaciones) --')
    for pred in pred_info["predictions"][:3]:
        R.p(f'  Gen {pred["gen"]:>5d}: fitness predicho ~= {pred["predicted_fitness"]:.4f}')
    if len(pred_info["predictions"]) > 3:
        R.p(f'  ... ({len(pred_info["predictions"])-3} más predicciones disponibles)')
    
    R.p(f'\n-- Proyección --')
    if pred_info["is_improving"]:
        if pred_info["gens_to_target_10pct"] and pred_info["gens_to_target_10pct"] > 0:
            R.p(f'  Estimado alcanzar +10% en ~= {pred_info["gens_to_target_10pct"]} generaciones')
        else:
            R.p(f'  [OK] Mejorando: pendiente positiva')
    elif pred_info["is_stable"]:
        R.p(f'  [~] Estable: sin cambios significativos (pendiente ~ 0)')
    else:
        R.p(f'  [X] Decayendo: pendiente negativa')

def report_components_correlation(R, debug_rows):
    """Report correlations for fields present in the detected debug schema."""
    comp_info = analyze_fitness_components_correlation(debug_rows)
    if not comp_info:
        return

    R.p(f'\n{"="*76}')
    R.p('  ANALISIS DE COMPONENTES FITNESS')
    R.p(f'{"="*76}')
    R.p(f'  Esquema detectado:         {comp_info.get("schema", "unknown")}')

    labels = comp_info['component_labels']
    corr = comp_info['component_fitness_correlations']
    contrib = comp_info['component_contributions']
    means = comp_info['component_means']
    counts = comp_info.get('component_counts', {})
    R.p('\n-- Correlacion Componentes vs Fitness Final --')
    for key, value in corr.items():
        R.p(f'  {labels.get(key, key):30s}: {value:>7.4f} (N={counts.get(key, 0)})')

    R.p('\n-- Media y proporcion sobre Fitness medio --')
    for key, value in means.items():
        R.p(f'  {labels.get(key, key):30s}: media={value:>11.4f}  ratio={contrib.get(key, 0.0):>8.4f}  N={counts.get(key, 0)}')

    R.p('\n-- Top 3 Penalizaciones --')
    for name, value in comp_info['top_penalties']:
        R.p(f'  {name:20s}: media = {value:.4f}')

def compute_debug_aggregates(dbg):
    """
    Consolidates 20+ iterations over dbg into a SINGLE pass.
    Computes all component sums and special value lists in O(n) time instead of O(n×20).
    Returns: (aggregates_dict, mut_lists_dict)
    """
    if not dbg:
        return {}, {}
    
    agg = {
        'fit': 0.0, 'a': 0.0, 'b': 0.0, 'c': 0.0, 'd': 0.0, 'e': 0.0,
        'f': 0.0, 'wait_bonus': 0.0, 'queue_wait_bonus': 0.0, 'net': 0.0,
        'pen_m': 0.0, 'pen_v': 0.0, 'pen_cw': 0.0, 'pen_tv': 0.0, 'pen_nav': 0.0,
        'pen_creep': 0.0, 'pen_rev': 0.0, 'pen_lazy': 0.0, 'pen_swstop': 0.0,
        'pen_steer_app': 0.0, 'pen_align': 0.0, 't_norm': 0.0, 't_tot': 0.0,
        'thr_pos': 0.0, 'thr_grace': 0.0, 'brake_grace': 0.0, 'brake_in': 0.0,
        'coast_t': 0.0, 'stop_brake': 0.0, 'stop_throttle': 0.0,
        'car_overlaps': 0.0, 'car_overlap_rows': 0.0,
        'yield_free_passes': 0.0, 'yield_free_pass_rows': 0.0,
        'yield_validation_speed': 0.0, 'yield_validation_rows': 0.0,
        'crossing_blocked_t': 0.0, 'crossing_blocked_rows': 0.0,
        'front_obst_death': 0.0, 'front_obst_death_rows': 0.0,
        'steer_app_wrong': 0.0, 'steer_app_right': 0.0, 'steer_app_total': 0.0,
        'car_overlap_pen_shadow': 0.0, 'car_overlap_penalty': 0.0,
        'first_steer_release_ticks': 0.0, 'first_steer_release_rows': 0.0,
        't_stop_ctx': 0.0, 't_stop_ctx_tl': 0.0, 't_stop_ctx_stop': 0.0, 't_stop_ctx_yield': 0.0,
        'yield_val_t': 0.0, 'stop_val_t': 0.0,
        'stop_zones_n': 0.0, 'fit_peak_raw': 0.0, 'fit_peak_gain': 0.0,
        'stop_bonus': 0.0, 'stop_done_n': 0.0, 'yield_bonus': 0.0, 'yield_done_n': 0.0,
        'round_entered_n': 0.0, 'round_completed_n': 0.0,
        'round_entry_speed': 0.0, 'round_entry_front': 0.0, 'round_ticks': 0.0,
        'round_steer': 0.0, 'round_throttle': 0.0, 'round_collisions': 0.0,
        'round_bonus': 0.0,
        'round_completion_bonus': 0.0, 'round_entry_penalty': 0.0, 'round_throttle_penalty': 0.0,
        'round_dir_first': 0.0, 'round_dir_second': 0.0, 'round_dir_third': 0.0,
        'round_exit1_count': 0.0, 'round_exit2_count': 0.0, 'round_exit3_count': 0.0,
        'round_exit1_deaths': 0.0, 'round_exit2_deaths': 0.0, 'round_exit3_deaths': 0.0,
        'round_exit1_steer': 0.0, 'round_exit2_steer': 0.0, 'round_exit3_steer': 0.0,
        'round_exit1_ticks': 0.0, 'round_exit2_ticks': 0.0, 'round_exit3_ticks': 0.0,
        'round_exit1_throttle': 0.0, 'round_exit2_throttle': 0.0, 'round_exit3_throttle': 0.0,
        'steer_in': 0.0, 'steer_target': 0.0, 'steer_abs': 0.0, 'steer_abs_avg': 0.0,
        'steer_gap_avg_abs': 0.0, 'steer_gap_total': 0.0,
        'cmd_total': 0.0, 'grace_cmd_total': 0.0, 'stop_cmd_total': 0.0,
    }
    
    mut_lists = {
        'mut_changed': [], 'mut_avg': [], 'mut_large': [],
        'mut_parent': [], 'mut_rate': [], 'mut_large_rate': [],
        'mut_strength': [], 'fit': [], 'invalid_brain_count': 0
    }
    
    # SINGLE PASS over dbg
    for r in dbg:
        agg['fit'] += r.get('fit', 0.0)
        agg['a'] += r.get('a', 0.0)
        agg['b'] += r.get('b', 0.0)
        agg['c'] += r.get('c', 0.0)
        agg['d'] += r.get('d', 0.0)
        agg['e'] += r.get('e', 0.0)
        agg['f'] += r.get('f', 0.0)
        agg['wait_bonus'] += r.get('wait_bonus', 0.0)
        agg['queue_wait_bonus'] += r.get('queue_wait_bonus', 0.0)
        agg['net'] += r.get('net', 0.0)
        agg['pen_m'] += r.get('pen_m', 0.0)
        agg['pen_v'] += r.get('pen_v', 0.0)
        agg['pen_cw'] += r.get('pen_cw', 0.0)
        agg['pen_tv'] += r.get('pen_tv', 0.0)
        agg['pen_nav'] += r.get('pen_nav', 0.0)
        agg['pen_creep'] += r.get('pen_creep', 0.0)
        agg['pen_rev'] += r.get('pen_rev', 0.0)
        agg['pen_lazy'] += r.get('pen_lazy', 0.0)
        agg['pen_swstop'] += r.get('pen_swstop', 0.0)
        agg['pen_steer_app'] += r.get('pen_steer_app', 0.0)
        agg['pen_align'] += r.get('pen_align', 0.0)
        agg['t_norm'] += r.get('t_norm', 0.0)
        agg['t_tot'] += r.get('t_tot', 0.0)
        agg['thr_pos'] += r.get('thr_pos', 0.0)
        agg['thr_grace'] += r.get('thr_grace', 0.0)
        agg['brake_grace'] += r.get('brake_grace', 0.0)
        agg['brake_in'] += r.get('brake_in', 0.0)
        car_overlaps = r.get('car_overlaps', 0.0)
        agg['car_overlaps'] += car_overlaps
        if car_overlaps > 0.0:
            agg['car_overlap_rows'] += 1.0
        yield_free_passes = r.get('yield_free_passes', 0.0)
        agg['yield_free_passes'] += yield_free_passes
        if yield_free_passes > 0.0:
            agg['yield_free_pass_rows'] += 1.0
        if r.get('yield_validation_seen', 0.0) > 0.0:
            agg['yield_validation_speed'] += r.get('yield_validation_speed', 0.0)
            agg['yield_validation_rows'] += 1.0
        crossing_blocked = r.get('crossing_blocked_t', 0.0)
        agg['crossing_blocked_t'] += crossing_blocked
        if crossing_blocked > 0.0:
            agg['crossing_blocked_rows'] += 1.0
        if r.get('front_obst_death_seen', 0.0) > 0.0:
            agg['front_obst_death'] += r.get('front_obst_death', 0.0)
            agg['front_obst_death_rows'] += 1.0
        agg['steer_app_wrong'] += r.get('steer_app_wrong', 0.0)
        agg['steer_app_right'] += r.get('steer_app_right', 0.0)
        agg['steer_app_total'] += r.get('steer_app_total', 0.0)
        agg['car_overlap_pen_shadow'] += r.get('car_overlap_pen_shadow', 0.0)
        agg['car_overlap_penalty'] += r.get('car_overlap_penalty', 0.0)
        if r.get('first_steer_release_seen', 0.0) > 0.0:
            agg['first_steer_release_ticks'] += r.get('first_steer_release_ticks', 0.0)
            agg['first_steer_release_rows'] += 1.0
        agg['coast_t'] += r.get('coast_t', 0.0)
        agg['stop_brake'] += r.get('stop_brake', 0.0)
        agg['stop_throttle'] += r.get('stop_throttle', 0.0)
        agg['t_stop_ctx'] += r.get('t_stop_ctx', 0.0)
        agg['t_stop_ctx_tl'] += r.get('t_stop_ctx_tl', 0.0)
        agg['t_stop_ctx_stop'] += r.get('t_stop_ctx_stop', 0.0)
        agg['t_stop_ctx_yield'] += r.get('t_stop_ctx_yield', 0.0)
        agg['yield_val_t'] += r.get('yield_val_t', 0.0)
        agg['stop_val_t'] += r.get('stop_val_t', 0.0)
        agg['stop_zones_n'] += r.get('stop_zones_n', 0.0)
        agg['fit_peak_raw'] += r.get('fit_peak_raw', 0.0)
        agg['fit_peak_gain'] += r.get('fit_peak_gain', 0.0)
        agg['stop_bonus'] += r.get('stop_bonus', 0.0)
        agg['stop_done_n'] += r.get('stop_done_n', 0.0)
        agg['yield_bonus'] += r.get('yield_bonus', 0.0)
        agg['yield_done_n'] += r.get('yield_done_n', 0.0)
        agg['round_entered_n'] += r.get('round_entered_n', 0.0)
        agg['round_completed_n'] += r.get('round_completed_n', 0.0)
        agg['round_entry_speed'] += r.get('round_entry_speed', 0.0)
        agg['round_entry_front'] += r.get('round_entry_front', 0.0)
        agg['round_ticks'] += r.get('round_ticks', 0.0)
        agg['round_steer'] += r.get('round_steer', 0.0)
        agg['round_throttle'] += r.get('round_throttle', 0.0)
        agg['round_collisions'] += r.get('round_collisions', 0.0)
        agg['round_bonus'] += r.get('round_bonus', 0.0)
        agg['round_completion_bonus'] += r.get('round_completion_bonus', 0.0)
        agg['round_entry_penalty'] += r.get('round_entry_penalty', 0.0)
        agg['round_throttle_penalty'] += r.get('round_throttle_penalty', 0.0)
        for key in (
            'round_dir_first', 'round_dir_second', 'round_dir_third',
            'round_exit1_count', 'round_exit2_count', 'round_exit3_count',
            'round_exit1_deaths', 'round_exit2_deaths', 'round_exit3_deaths',
            'round_exit1_steer', 'round_exit2_steer', 'round_exit3_steer',
            'round_exit1_ticks', 'round_exit2_ticks', 'round_exit3_ticks',
            'round_exit1_throttle', 'round_exit2_throttle', 'round_exit3_throttle',
        ):
            agg[key] += r.get(key, 0.0)
        agg['steer_in'] += r.get('steer_in', 0.0)
        agg['steer_target'] += r.get('steer_target', 0.0)
        agg['steer_abs'] += r.get('steer_abs', 0.0)
        agg['steer_abs_avg'] += r.get('steer_abs_avg', 0.0)
        agg['steer_gap_avg_abs'] += r.get('steer_gap_avg_abs', 0.0)
        agg['steer_gap_total'] += abs(r.get('steer_in', 0.0) - r.get('steer_target', 0.0))
        agg['cmd_total'] += r.get('thr_pos', 0.0) + r.get('brake_in', 0.0)
        agg['grace_cmd_total'] += r.get('thr_grace', 0.0) + r.get('brake_grace', 0.0)
        agg['stop_cmd_total'] += r.get('stop_brake', 0.0) + r.get('stop_throttle', 0.0)
        
        # InitialRandom reports every weight as changed; it is initialization,
        # not a 100% mutation, so exclude it from mutation distributions.
        if not r.get('is_weight_initialization', False):
            mut_lists['mut_changed'].append(r.get('mut_changed', 0.0))
            mut_lists['mut_avg'].append(r.get('mut_avg_mag', 0.0))
            mut_lists['mut_large'].append(r.get('mut_large', 0.0))
            mut_lists['mut_parent'].append(r.get('mut_parent_fit', 0.0))
            mut_lists['mut_rate'].append(r.get('mut_rate', 0.0))
            mut_lists['mut_large_rate'].append(r.get('mut_large_rate', 0.0))
            mut_lists['mut_strength'].append(r.get('mut_strength', 0.0))
            mut_lists['fit'].append(r.get('fit', 0.0))
        if is_invalid_brain_reason(r.get('death', '')):
            mut_lists['invalid_brain_count'] += 1
    
    return agg, mut_lists

def report_debug(R, dbg):
    if not dbg:
        R.p('\n  (Fitness_Debug.csv vacio o no encontrado)')
        return

    gens = sorted(set(r['gen'] for r in dbg))
    freerun = is_freerun_analysis(debug_rows=dbg)
    R.p(f'\n{"="*76}')
    if freerun:
        R.p(f'  ANALISIS DETALLADO (Fitness_Debug) - FreeRun, {len(dbg)} eventos terminales')
    else:
        R.p(f'  ANALISIS DETALLADO (Fitness_Debug) - {len(dbg)} registros, {len(gens)} gens')
    R.p(f'{"="*76}')

    # Pre-agrupar para evitar escaneos repetidos O(n*G)
    by_gen = defaultdict(list)
    by_death = defaultdict(list)
    by_trigger = defaultdict(list)

    # Por Spawn
    spawns = defaultdict(list)
    for r in dbg:
        by_gen[r['gen']].append(r)
        by_death[r['death']].append(r)
        spawns[r['spawn']].append(r)
        trigger = r.get('current_trigger_short') or short_actor_name(r.get('current_trigger', ''), empty='')
        if trigger:
            by_trigger[trigger].append(r)

    R.p(f'\n-- Fitness por Spawn ({len(spawns)} spawns) --')
    hdr = f'  {"Spawn":>15s} | {"N":>5s} | {"Media":>10s} | {"Mediana":>10s} | {"Max":>10s} | {"P75":>10s} | {"%Neg":>5s} | {"tMed":>5s}'
    R.p(hdr)
    R.p(f'  {"-"*(len(hdr)-2)}')
    spawn_stats = {}
    for sp in sorted(spawns.keys()):
        cars = spawns[sp]
        fits = [r['fit'] for r in cars]
        ns = len(fits)
        stats = {
            'n': ns, 'mean': sdiv(sum(fits), ns), 'med': pctl(fits, 50),
            'max': max(fits), 'p75': pctl(fits, 75),
            'neg_pct': sdiv(sum(1 for f in fits if f<0)*100, ns),
            'time': sdiv(sum(r['time'] for r in cars), ns)
        }
        spawn_stats[sp] = stats
        short = sp.replace('TargetPoint','TP')
        R.p('  {:>15s} | {:>5d} | {:>10.1f} | {:>10.1f} | {:>10.1f} | {:>10.1f} | {:>4.0f}% | {:>4.1f}s'.format(
            short, ns, stats['mean'], stats['med'], stats['max'], stats['p75'], stats['neg_pct'], stats['time']))

    # Ranking dificultad
    R.p(f'\n-- Ranking de Spawns (mas dificil a mas facil, por fitness medio) --')
    for i, (sp, st) in enumerate(sorted(spawn_stats.items(), key=lambda x: x[1]['mean']), 1):
        short = sp.replace('TargetPoint','TP')
        R.p(f'  {i:>2d}. {short:>10s}: media={st["mean"]:>10.1f}  mediana={st["med"]:>10.1f}  %neg={st["neg_pct"]:.0f}%  t={st["time"]:.1f}s')

    # Razones de muerte
    deaths = Counter(r['death'] for r in dbg)
    R.p(f'\n-- Razones de Muerte (todos los coches, {len(dbg)} reg) --')
    for reason, cnt in deaths.most_common():
        grp = by_death[reason]
        mf = sdiv(sum(r['fit'] for r in grp), cnt)
        mt = sdiv(sum(r['time'] for r in grp), cnt)
        collision_note = ''
        if is_collision_reason(reason):
            round_n = sum(1 for r in grp if collision_death_context(r) == 'COLLISION_ROUNDABOUT')
            normal_n = cnt - round_n
            collision_note = f' | rot={round_n}, norm={normal_n}'
        R.p(f'  {reason:45s}: {cnt:5d} ({sdiv(cnt*100,len(dbg)):5.1f}%) fit={mf:>10.1f} t={mt:.1f}s{collision_note}')

    family_counts = Counter(r.get('death_family', death_family(r.get('death', ''))) for r in dbg)
    family_detail_counts = Counter(r.get('death_family_detail', death_family_detail_for_row(r)) for r in dbg)
    collision_stats = summarize_collision_deaths(dbg)
    death_fail_n = sum(1 for r in dbg if r.get('is_test_failure_death', is_test_failure_reason(r.get('death', ''))))
    R.p(f'\n-- Familias y Fallos por DeathReason --')
    for fam, cnt in sorted(family_counts.items(), key=lambda kv: (death_family_order_index(kv[0]), -kv[1], kv[0])):
        R.p(f'  {fam:14s}: {cnt:5d} ({sdiv(cnt*100, len(dbg)):5.1f}%)')
    if collision_stats['total'] > 0:
        R.p(
            f'  Colisiones detalle: rotonda={collision_stats["roundabout"]} '
            f'({sdiv(collision_stats["roundabout"]*100.0, collision_stats["total"]):.1f}% de colisiones), '
            f'normales={collision_stats["normal"]}; eventos_rotonda={collision_stats["roundabout_events"]:.0f}'
        )
    stop_violation_detail = summarize_stop_violation_subtypes(dbg)
    if stop_violation_detail:
        R.p(
            '  STOP_VIOLATION detalle: '
            f'EXIT={stop_violation_detail.get("EXIT", 0)}, '
            f'TIMEOUT={stop_violation_detail.get("TIMEOUT", 0)}, '
            f'GENERIC={stop_violation_detail.get("GENERIC", 0)}'
        )
    detail_text = ', '.join(
        f'{fam}={cnt}'
        for fam, cnt in sorted(
            family_detail_counts.items(),
            key=lambda kv: (death_family_detail_order_index(kv[0]), -kv[1], kv[0]),
        )
    )
    if detail_text:
        R.p(f'  Familias detalle: {detail_text}')
    R.p(
        f'  Fail por muerte*: {death_fail_n:5d}/{len(dbg)} ({sdiv(death_fail_n*100, len(dbg)):5.1f}%) '
        f'(*sin reconstruir TestMinTime/TestMinFitness)'
    )
    if MODE in ('test', 'traintest'):
        reconstructed = reconstruct_test_outcomes(dbg)
        rc = reconstructed['counts']
        R.p('\n-- Reconstruccion de Resultado TEST --')
        R.p(
            f'  Reglas asumidas: tiempo>={reconstructed["min_time"]:.1f}s, '
            f'fitness>={reconstructed["min_fitness"]:.1f} '
            f'(activo={reconstructed["use_fitness"]}), muerte valida'
        )
        R.p(
            f'  Acierto reconstruido: {reconstructed["success"]}/{reconstructed["total"]} '
            f'({reconstructed["success_rate"]:.2f}%)'
        )
        R.p(
            f'  Fallos: muerte={rc.get("fail_death", 0)}, tiempo={rc.get("fail_time", 0)}, '
            f'fitness={rc.get("fail_fitness", 0)}'
        )
        R.p(
            '  Nota: Test_Summary.csv sigue siendo autoritativo; ajusta '
            'ANALYSE_TEST_MIN_TIME/ANALYSE_TEST_MIN_FITNESS/ANALYSE_TEST_USE_FITNESS '
            'si los valores editables de Unreal cambian.'
        )

    if debug_field_available(dbg, 'current_trigger'):
        if by_trigger:
            R.p(f'\n-- CurrentTrigger / Intersecciones al Morir ({len(by_trigger)} triggers) --')
            hdr = (
                f'  {"Trigger":>18s} | {"N":>5s} | {"LAZY":>6s} | {"Legal":>6s} | '
                f'{"Col":>6s} | {"RotCol":>6s} | {"FitMed":>10s} | {"tMed":>7s} | Muerte dominante'
            )
            R.p(hdr)
            R.p(f'  {"-"*(len(hdr)-2)}')
            trigger_rows = []
            for trigger, rows_t in by_trigger.items():
                n_t = len(rows_t)
                legal_n = sum(1 for r in rows_t if death_family(r.get('death', '')) == 'VIOLATION')
                collision_n = sum(1 for r in rows_t if is_collision_reason(r.get('death', '')))
                round_collision_n = sum(1 for r in rows_t if collision_death_context(r) == 'COLLISION_ROUNDABOUT')
                lazy_n = sum(1 for r in rows_t if is_lazy_reason(r.get('death', '')))
                top_death, top_death_n = Counter(r.get('death', '') for r in rows_t).most_common(1)[0]
                risk_score = legal_n + collision_n + lazy_n
                trigger_rows.append((
                    risk_score,
                    n_t,
                    trigger,
                    lazy_n,
                    legal_n,
                    collision_n,
                    round_collision_n,
                    mean([r.get('fit', 0.0) for r in rows_t]),
                    mean([r.get('time', 0.0) for r in rows_t]),
                    top_death,
                    top_death_n,
                ))
            for _, n_t, trigger, lazy_n, legal_n, collision_n, round_collision_n, fit_med, time_med, top_death, top_death_n in sorted(trigger_rows, reverse=True)[:min(TOP_ROWS, 15)]:
                R.p(
                    f'  {trigger:>18s} | {n_t:5d} | {sdiv(lazy_n*100.0, n_t):5.1f}% | '
                    f'{sdiv(legal_n*100.0, n_t):5.1f}% | {sdiv(collision_n*100.0, n_t):5.1f}% | '
                    f'{sdiv(round_collision_n*100.0, max(collision_n, 1)):5.1f}% | '
                    f'{fit_med:10.1f} | {time_med:6.1f}s | '
                    f'{short_death_reason(top_death)} ({top_death_n})'
                )
            R.p('  Nota: CurrentTrigger identifica el trigger/interseccion activo al morir; si falta, el coche no tenia trigger valido exportado.')
        else:
            R.p('\n-- CurrentTrigger / Intersecciones al Morir --')
            R.p('  Columna detectada, pero sin valores validos en este lote.')

    # Componentes globales - usar agregados precomputados (mejora de performance)
    nd = len(dbg)
    if nd == 0:
        return
    
    agg, mut_lists = compute_debug_aggregates(dbg)
    car_bounds = infer_carindex_bounds(dbg)
    
    R.p(f'\n-- Componentes del Fitness (medias globales, {nd} coches) --')
    R.p(f'  Esquema CSV:                     {dbg[0].get("_schema", "unknown")}')
    R.p(
        f'  Red asumida:                     inputs={NETWORK_INPUT_COUNT}, hidden={NETWORK_HIDDEN_COUNT}, '
        f'outputs={NETWORK_OUTPUT_COUNT}, pesos={WEIGHTS_TOTAL}'
    )
    component_lines = (
        ('a', 'Acum_A'),
        ('b', 'Media_B (legacy)'),
        ('c', 'Acum_C (legacy)'),
        ('d', 'Acum_D (legacy)'),
        ('e', 'Acum_E (legacy)'),
        ('f', 'Acum_F'),
        ('wait_bonus', 'Acum_WaitBonus'),
        ('queue_wait_bonus', 'Acum_QueueWaitBonus'),
        ('net', 'Acum_NetNormal'),
        ('stop_bonus', 'StopCompletionBonus'),
        ('yield_bonus', 'YieldCompletionBonus'),
    )
    for key, label in component_lines:
        if debug_field_available(dbg, key):
            R.p(f'  {label:32s}: {sdiv(agg.get(key, 0.0), nd):>10.4f}')
    R.p(f'  Penalty_Muerte:                  {sdiv(agg["pen_m"], nd):>10.4f}')
    R.p(f'  Penalty_Velocidad:               {sdiv(agg["pen_v"], nd):>10.4f}')
    R.p(f'  Penalty_CorrectingWrong:         {sdiv(agg["pen_cw"], nd):>10.4f}')
    R.p(f'  Penalty_TrafficViolation:        {sdiv(agg["pen_tv"], nd):>10.4f}')
    R.p(f'  Penalty_NavViolation:            {sdiv(agg["pen_nav"], nd):>10.4f}')
    R.p(f'  Penalty_Creeping:                {sdiv(agg["pen_creep"], nd):>10.4f}')
    R.p(f'  Penalty_Reverse:                 {sdiv(agg["pen_rev"], nd):>10.4f}')
    R.p(f'  Penalty_Lazy:                    {sdiv(agg["pen_lazy"], nd):>10.4f}')
    R.p(f'  Penalty_SteeringWhileStopped:    {sdiv(agg["pen_swstop"], nd):>10.4f}')
    R.p(f'  Penalty_SteerApproach:           {sdiv(agg["pen_steer_app"], nd):>10.4f}')
    if debug_field_available(dbg, 'pen_align'):
        R.p(f'  Penalty_Alignment:               {sdiv(agg["pen_align"], nd):>10.4f}')
    if debug_field_available(dbg, 'pen_v'):
        R.p(f'  Penalty_Velocidad/s exp.:        {mean(metric_values(dbg, "pen_v_per_life_sec")):>10.4f} (N={metric_exposure_count(dbg, "pen_v_per_life_sec")})')
    R.p(f'  Ticks Normal / Total:            {sdiv(agg["t_norm"], nd):>6.1f} / {sdiv(agg["t_tot"], nd):>6.1f}')
    R.p(f'  Acum_ThrottlePos:                {sdiv(agg["thr_pos"], nd):>10.4f}')
    R.p(f'  Acum_ThrottleDuringGraceTime:    {sdiv(agg["thr_grace"], nd):>10.4f}')
    R.p(f'  Acum_BrakeDuringGraceTime:       {sdiv(agg["brake_grace"], nd):>10.4f}')
    R.p(f'  Acum_BrakeInput:                 {sdiv(agg["brake_in"], nd):>10.4f}')
    if debug_field_available(dbg, 'car_overlaps'):
        R.p(f'  NumCarOverlaps:                  {sdiv(agg["car_overlaps"], nd):>10.4f}')
        R.p(f'  Coches con CarOverlap>0:         {agg["car_overlap_rows"]:>7.0f}/{nd} ({sdiv(agg["car_overlap_rows"]*100.0, nd):.2f}%)')
        if debug_field_available(dbg, 'car_overlap_pen_shadow'):
            R.p(f'  CarOverlapPenaltyShadow:         {sdiv(agg["car_overlap_pen_shadow"], nd):>10.4f}')
            R.p(f'  Shadow/Overlap exp.:             {mean(metric_values(dbg, "car_overlap_shadow_per_overlap")):>10.4f} (N={metric_exposure_count(dbg, "car_overlap_shadow_per_overlap")})')
        if debug_field_available(dbg, 'car_overlap_penalty'):
            R.p(f'  CarOverlapPenalty real:          {sdiv(agg["car_overlap_penalty"], nd):>10.4f}')
            R.p(f'  Penalty/Overlap exp.:            {mean(metric_values(dbg, "car_overlap_penalty_per_overlap")):>10.4f} (N={metric_exposure_count(dbg, "car_overlap_penalty_per_overlap")})')
    if debug_field_available(dbg, 'yield_free_passes'):
        R.p(f'  NumYieldFreePasses:              {sdiv(agg["yield_free_passes"], nd):>10.4f}')
        R.p(f'  Coches con YieldFreePass>0:      {agg["yield_free_pass_rows"]:>7.0f}/{nd} ({sdiv(agg["yield_free_pass_rows"]*100.0, nd):.2f}%)')
    if debug_field_available(dbg, 'yield_validation_speed'):
        R.p(f'  SpeedAtYieldValidation exp.:     {mean(metric_values(dbg, "yield_validation_speed")):>10.4f} (N={metric_exposure_count(dbg, "yield_validation_speed")})')
    if debug_field_available(dbg, 'crossing_blocked_t'):
        R.p(f'  TimeBlockedAtCrossing:           {sdiv(agg["crossing_blocked_t"], nd):>10.4f}')
        R.p(f'  Coches bloqueados en cruce:      {agg["crossing_blocked_rows"]:>7.0f}/{nd} ({sdiv(agg["crossing_blocked_rows"]*100.0, nd):.2f}%)')
    if debug_field_available(dbg, 'front_obst_death'):
        R.p(f'  FrontObstAtDeath exp.:           {mean(metric_values(dbg, "front_obst_death")):>10.4f} (N={metric_exposure_count(dbg, "front_obst_death")})')
    if debug_field_available(dbg, 'steer_app_wrong') or debug_field_available(dbg, 'steer_app_right'):
        R.p(f'  SteerApproach Wrong/Right:       {sdiv(agg["steer_app_wrong"], nd):>10.4f} / {sdiv(agg["steer_app_right"], nd):>10.4f}')
        R.p(f'  SteerApproach wrong share exp.:  {mean(metric_values(dbg, "steer_app_wrong_share"))*100.0:>9.2f}% (N={metric_exposure_count(dbg, "steer_app_wrong_share")})')
    if debug_field_available(dbg, 'first_steer_release_ticks'):
        R.p(f'  FirstSteerAfterRelease exp.:     {mean(metric_values(dbg, "first_steer_release_ticks")):>10.4f} ticks (N={metric_exposure_count(dbg, "first_steer_release_ticks")})')
    R.p(f'  Acum_CoastTime:                  {sdiv(agg["coast_t"], nd):>10.4f}')
    R.p(f'  Acum_StopBrake:                  {sdiv(agg["stop_brake"], nd):>10.4f}')
    R.p(f'  Acum_StopThrottle:               {sdiv(agg["stop_throttle"], nd):>10.4f}')
    R.p(f'  Ticks_StopContext:               {sdiv(agg["t_stop_ctx"], nd):>10.4f}')
    R.p(f'  Ticks_StopContext_TrafficLight:  {sdiv(agg["t_stop_ctx_tl"], nd):>10.4f}')
    R.p(f'  Ticks_StopContext_Stop:          {sdiv(agg["t_stop_ctx_stop"], nd):>10.4f}')
    R.p(f'  Ticks_StopContext_Yield:         {sdiv(agg["t_stop_ctx_yield"], nd):>10.4f}')
    R.p(f'  YieldValidationTime:             {sdiv(agg["yield_val_t"], nd):>10.4f}')
    R.p(f'  StopValidationTime:              {sdiv(agg["stop_val_t"], nd):>10.4f}')
    R.p(f'  StopCompletionBonus:             {sdiv(agg["stop_bonus"], nd):>10.4f}')
    R.p(f'  NumStopsCompleted:               {sdiv(agg["stop_done_n"], nd):>10.4f}')
    R.p(f'  YieldCompletionBonus:            {sdiv(agg["yield_bonus"], nd):>10.4f}')
    R.p(f'  NumYieldsCompleted:              {sdiv(agg["yield_done_n"], nd):>10.4f}')
    R.p(f'  NumStopZonesEntered:             {sdiv(agg["stop_zones_n"], nd):>10.4f}')
    if debug_field_available(dbg, 'round_entered_n'):
        R.p(f'  NumRoundaboutsEntered:           {sdiv(agg["round_entered_n"], nd):>10.4f}')
        R.p(f'  NumRoundaboutsCompleted:         {sdiv(agg["round_completed_n"], nd):>10.4f}')
        R.p(f'  CollisionsInRoundabout:          {sdiv(agg["round_collisions"], nd):>10.4f}')
        R.p(f'  Ticks_InRoundabout:              {sdiv(agg["round_ticks"], nd):>10.4f}')
        if debug_field_available(dbg, 'round_bonus'):
            R.p(f'  Acum_RoundaboutBonus:            {sdiv(agg["round_bonus"], nd):>10.4f}')
        if debug_field_available(dbg, 'round_completion_bonus'):
            R.p(f'  RndCompletionBonus:              {sdiv(agg["round_completion_bonus"], nd):>10.4f}')
            R.p(f'  RndEntryPenalty:                 {sdiv(agg["round_entry_penalty"], nd):>10.4f}')
            R.p(f'  RndThrottlePenalty:              {sdiv(agg["round_throttle_penalty"], nd):>10.4f}')
    R.p(f'  NotNorm_PeakFitness:             {sdiv(agg["fit_peak_raw"], nd):>10.4f}')
    R.p(f'  PeakGain (Peak - Final):         {sdiv(agg["fit_peak_gain"], nd):>10.4f}')
    R.p(f'  Acum_SteeringInput:              {sdiv(agg["steer_in"], nd):>10.4f}')
    R.p(f'  Acum_TargetSteering:             {sdiv(agg["steer_target"], nd):>10.4f}')
    R.p(f'  Acum_ABS_Steering:               {sdiv(agg["steer_abs"], nd):>10.4f}')
    R.p(f'  Avg_ABS_Steering/tick:           {sdiv(agg["steer_abs_avg"], nd):>10.4f}')
    R.p(f'  AvgAbs_TargetVsAppliedGap:       {sdiv(agg["steer_gap_avg_abs"], nd):>10.4f}')
    R.p(f'  SteeringGapAbs (|input-target|): {sdiv(agg["steer_gap_total"], nd):>10.4f}')
    val_total_vals = [r.get('val_total', r.get('yield_val_t', 0.0) + r.get('stop_val_t', 0.0)) for r in dbg]
    val_per_stop_vals = [
        r.get('val_per_stop_tick', sdiv(r.get('yield_val_t', 0.0) + r.get('stop_val_t', 0.0), max(r.get('t_stop_ctx', 0.0), 1.0)))
        for r in dbg if r.get('t_stop_ctx', 0.0) > 0.0
    ]
    stop_zone_vals = [r.get('stop_zones_n', 0.0) for r in dbg]
    stop_done_vals = [r.get('stop_done_n', 0.0) for r in dbg]
    yield_done_vals = [r.get('yield_done_n', 0.0) for r in dbg]
    stop_bonus_vals = [r.get('stop_bonus', 0.0) for r in dbg]
    yield_bonus_vals = [r.get('yield_bonus', 0.0) for r in dbg]
    stop_bonus_per_vals = [r.get('stop_bonus_per', 0.0) for r in dbg if r.get('stop_done_n', 0.0) > 0.0]
    yield_bonus_per_vals = [r.get('yield_bonus_per', 0.0) for r in dbg if r.get('yield_done_n', 0.0) > 0.0]
    peak_gain_vals = [r.get('fit_peak_gain', 0.0) for r in dbg]
    peak_gain_pct_vals = [
        r.get('fit_peak_gain_pct', sdiv(r.get('fit_peak_gain', 0.0) * 100.0, max(abs(r.get('fit_peak_raw', 0.0)), 1.0)))
        for r in dbg
    ]
    peak_gain_pos = [v for v in peak_gain_vals if v > 0.0]
    R.p(f'\n-- Validacion Legal y Stop Zones --')
    R.p(f'  Validacion total P50/P90:        {pctl(val_total_vals, 50):>10.2f} / {pctl(val_total_vals, 90):>10.2f}')
    R.p(f'  Validacion/StopTick P50/P90:     {pctl(val_per_stop_vals, 50):>10.3f} / {pctl(val_per_stop_vals, 90):>10.3f} (N={len(val_per_stop_vals)})')
    R.p(f'  StopZones P50/P90 (media):       {pctl(stop_zone_vals, 50):>6.2f} / {pctl(stop_zone_vals, 90):>6.2f} ({mean(stop_zone_vals):.2f})')
    R.p(f'  StopsCompleted P50/P90:          {pctl(stop_done_vals, 50):>6.2f} / {pctl(stop_done_vals, 90):>6.2f}')
    R.p(f'  YieldsCompleted P50/P90:         {pctl(yield_done_vals, 50):>6.2f} / {pctl(yield_done_vals, 90):>6.2f}')
    R.p(f'  StopBonus P50/P90:               {pctl(stop_bonus_vals, 50):>10.2f} / {pctl(stop_bonus_vals, 90):>10.2f}')
    R.p(f'  YieldBonus P50/P90:              {pctl(yield_bonus_vals, 50):>10.2f} / {pctl(yield_bonus_vals, 90):>10.2f}')
    R.p(f'  StopBonus/Stop P50/P90:          {pctl(stop_bonus_per_vals, 50):>10.2f} / {pctl(stop_bonus_per_vals, 90):>10.2f} (N={len(stop_bonus_per_vals)})')
    R.p(f'  YieldBonus/Yield P50/P90:        {pctl(yield_bonus_per_vals, 50):>10.2f} / {pctl(yield_bonus_per_vals, 90):>10.2f} (N={len(yield_bonus_per_vals)})')
    if debug_field_available(dbg, 'yield_free_passes') or debug_field_available(dbg, 'crossing_blocked_t'):
        yfree_vals = [r.get('yield_free_passes', 0.0) for r in dbg]
        blocked_vals = metric_values(dbg, 'crossing_blocked_per_stop_tick')
        speed_vals = metric_values(dbg, 'yield_validation_speed')
        release_vals = metric_values(dbg, 'first_steer_release_ticks')
        R.p(f'\n-- Diagnostico 30/06: Cedas, Cruce y Release --')
        if debug_field_available(dbg, 'yield_free_passes'):
            R.p(f'  YieldFreePasses total/media:     {sum(yfree_vals):>8.0f} / {mean(yfree_vals):>8.3f}')
        if debug_field_available(dbg, 'yield_validation_speed'):
            R.p(f'  SpeedAtYieldValidation P50/P90:  {pctl(speed_vals, 50):>10.2f} / {pctl(speed_vals, 90):>10.2f} (N={len(speed_vals)})')
        if debug_field_available(dbg, 'crossing_blocked_t'):
            R.p(f'  TimeBlockedAtCrossing total:     {sum(r.get("crossing_blocked_t", 0.0) for r in dbg):>10.2f}s')
            R.p(f'  Blocked/StopTick P50/P90:        {pctl(blocked_vals, 50):>10.4f} / {pctl(blocked_vals, 90):>10.4f} (N={len(blocked_vals)})')
        if debug_field_available(dbg, 'first_steer_release_ticks'):
            R.p(f'  FirstSteerAfterRelease P50/P90:  {pctl(release_vals, 50):>10.2f} / {pctl(release_vals, 90):>10.2f} ticks (N={len(release_vals)})')
        if debug_field_available(dbg, 'front_obst_death'):
            front_vals = metric_values(dbg, 'front_obst_death')
            R.p(f'  FrontObstAtDeath P50/P90:        {pctl(front_vals, 50):>10.4f} / {pctl(front_vals, 90):>10.4f} (N={len(front_vals)})')
        if debug_field_available(dbg, 'steer_app_wrong') or debug_field_available(dbg, 'steer_app_right'):
            wrong_share_vals = [v * 100.0 for v in metric_values(dbg, 'steer_app_wrong_share')]
            R.p(f'  SteerAppWrongShare P50/P90:      {pctl(wrong_share_vals, 50):>9.2f}% / {pctl(wrong_share_vals, 90):>9.2f}% (N={len(wrong_share_vals)})')
    if debug_field_available(dbg, 'round_entered_n'):
        round_rows = [r for r in dbg if r.get('round_entered_n', 0.0) > 0.0]
        round_completion = [r.get('round_completion_rate', 0.0) * 100.0 for r in round_rows]
        round_collision = [r.get('round_collision_rate', 0.0) * 100.0 for r in round_rows]
        round_speed = [r.get('round_entry_speed_avg', 0.0) for r in round_rows]
        round_front = [r.get('round_entry_front_avg', 0.0) for r in round_rows]
        round_steer = [r.get('round_steer_avg', 0.0) for r in round_rows]
        round_throttle = [r.get('round_throttle_avg', 0.0) for r in round_rows]
        round_bonus_entry = metric_values(dbg, 'round_bonus_per_entry')
        round_bonus_tick = metric_values(dbg, 'round_bonus_per_tick')
        round_bonus_rows = [
            r for r in dbg
            if r.get('round_entered_n', 0.0) > 0.0
            or r.get('round_ticks', 0.0) > 0.0
            or abs(r.get('round_bonus', 0.0)) > 1e-12
        ]
        round_bonus_pos = sum(1 for r in round_bonus_rows if r.get('round_bonus', 0.0) > 1e-12)
        round_bonus_neg = sum(1 for r in round_bonus_rows if r.get('round_bonus', 0.0) < -1e-12)
        completion_ci = wilson_ci(agg['round_completed_n'], agg['round_entered_n'])
        collision_ci = wilson_ci(agg['round_collisions'], agg['round_entered_n'])
        R.p(f'\n-- Rotondas --')
        R.p(f'  Coches con entrada:              {len(round_rows):>6d}/{nd} ({sdiv(len(round_rows)*100.0, nd):.2f}%)')
        R.p(f'  Entradas / compl. confirm. / col.: {agg["round_entered_n"]:.0f} / {agg["round_completed_n"]:.0f} / {agg["round_collisions"]:.0f}')
        R.p(
            f'  Compl. confirmada global*:       {sdiv(agg["round_completed_n"]*100.0, agg["round_entered_n"]):>9.2f}% '
            f'(IC95 {completion_ci[0]*100:.2f}-{completion_ci[1]*100:.2f}%)'
        )
        R.p(
            f'  CollisionRate global:            {sdiv(agg["round_collisions"]*100.0, agg["round_entered_n"]):>9.2f}% '
            f'(IC95 {collision_ci[0]*100:.2f}-{collision_ci[1]*100:.2f}%)'
        )
        R.p(f'  Compl. confirmada P50/P90 coche: {pctl(round_completion, 50):>9.2f}% / {pctl(round_completion, 90):>9.2f}%')
        R.p(f'  CollisionRate P50/P90 coche:     {pctl(round_collision, 50):>9.2f}% / {pctl(round_collision, 90):>9.2f}%')
        R.p(f'  Velocidad entrada P50/P90:       {pctl(round_speed, 50):>10.2f} / {pctl(round_speed, 90):>10.2f}')
        R.p(f'  Obstaculo frontal entrada P50:   {pctl(round_front, 50):>10.4f}')
        R.p(f'  Steering/tick P50/P90:           {pctl(round_steer, 50):>10.4f} / {pctl(round_steer, 90):>10.4f}')
        R.p(f'  Throttle/tick P50/P90:           {pctl(round_throttle, 50):>10.4f} / {pctl(round_throttle, 90):>10.4f}')
        R.p(f'  Cobertura ticks rotonda:         {sdiv(agg["round_ticks"]*100.0, agg["t_tot"]):>9.2f}%')
        if debug_field_available(dbg, 'round_bonus'):
            R.p(f'  RoundaboutBonus neto:            {agg["round_bonus"]:>10.2f}')
            if debug_field_available(dbg, 'round_completion_bonus'):
                expected_net = (
                    agg['round_completion_bonus']
                    - agg['round_entry_penalty']
                    - agg['round_throttle_penalty']
                )
                R.p(
                    f'  Desglose bonus C/E/T/neto:      {agg["round_completion_bonus"]:>10.2f} / '
                    f'-{agg["round_entry_penalty"]:>9.2f} / -{agg["round_throttle_penalty"]:>9.2f} / '
                    f'{expected_net:>10.2f}'
                )
            R.p(
                f'  Bonus/entrada P50/P90:           {pctl(round_bonus_entry, 50):>10.2f} / '
                f'{pctl(round_bonus_entry, 90):>10.2f} (N={len(round_bonus_entry)})'
            )
            R.p(
                f'  Bonus/tick rotonda P50/P90:      {pctl(round_bonus_tick, 50):>10.4f} / '
                f'{pctl(round_bonus_tick, 90):>10.4f} (N={len(round_bonus_tick)})'
            )
            R.p(f'  Coches bonus + / - / expuestos:  {round_bonus_pos:d} / {round_bonus_neg:d} / {len(round_bonus_rows):d}')
        R.p('  * NumRoundaboutsCompleted se confirma en la siguiente entrada; es un limite inferior y puede omitir la ultima travesia.')
        if debug_field_available(dbg, 'round_exit1_count'):
            dir_total = agg['round_dir_first'] + agg['round_dir_second'] + agg['round_dir_third']
            R.p(f'\n-- Rotondas por Direccion y Salida --')
            R.p(
                f'  Direccion entrada First/Second/Third: '
                f'{agg["round_dir_first"]:.0f} ({sdiv(agg["round_dir_first"]*100.0, dir_total):.1f}%) / '
                f'{agg["round_dir_second"]:.0f} ({sdiv(agg["round_dir_second"]*100.0, dir_total):.1f}%) / '
                f'{agg["round_dir_third"]:.0f} ({sdiv(agg["round_dir_third"]*100.0, dir_total):.1f}%)'
            )
            hdr_round = f'  {"Tramo":>8s} | {"Expos.":>7s} | {"Muertes":>7s} | {"Death%":>7s} | {"IC95":>15s} | {"Ticks":>9s} | {"Steer/t":>9s} | {"Thr/t":>9s}'
            R.p(hdr_round)
            R.p(f'  {"-"*(len(hdr_round)-2)}')
            for exit_num, label in ((1, 'Exit1'), (2, 'Exit2'), (3, 'Exit3+')):
                count = agg[f'round_exit{exit_num}_count']
                deaths = agg[f'round_exit{exit_num}_deaths']
                ticks = agg[f'round_exit{exit_num}_ticks']
                death_ci = wilson_ci(deaths, count)
                ci_text = f'{death_ci[0]*100:.1f}-{death_ci[1]*100:.1f}%' if count > 0 else 'sin datos'
                if count > 0 and deaths > count:
                    ci_text += ' cap'
                R.p(
                    f'  {label:>8s} | {count:7.0f} | {deaths:7.0f} | '
                    f'{sdiv(deaths*100.0, count):6.2f}% | {ci_text:>15s} | {ticks:9.0f} | '
                    f'{sdiv(agg[f"round_exit{exit_num}_steer"], ticks):9.4f} | '
                    f'{sdiv(agg[f"round_exit{exit_num}_throttle"], ticks):9.4f}'
                )
    R.p(f'\n-- Estabilidad Fitness (Peak vs Final) --')
    R.p(f'  PeakGain P50/P90:                {pctl(peak_gain_vals, 50):>10.2f} / {pctl(peak_gain_vals, 90):>10.2f}')
    R.p(f'  PeakGain% P50/P90:               {pctl(peak_gain_pct_vals, 50):>9.2f}% / {pctl(peak_gain_pct_vals, 90):>9.2f}%')
    R.p(f'  Pico>Final:                      {len(peak_gain_pos):>5d}/{nd} ({sdiv(len(peak_gain_pos)*100.0, nd):.1f}%)')
    car_fams = summarize_car_index_families(dbg, bounds=car_bounds)
    if car_fams:
        fam_line = ', '.join('{}={}'.format(x['family'], x['n']) for x in car_fams)
        car_idx_vals = [num(r.get('car_index', 0), 0.0) for r in dbg if num(r.get('car_index', 0), 0.0) > 0.0]
        if car_idx_vals:
            R.p(f'  CarIndex min/max/uniq:           {min(car_idx_vals):>10.0f} / {max(car_idx_vals):>4.0f} / {len(set(car_idx_vals)):>4d}')
        R.p(f'  CarIndex familias:               {fam_line}')
        if car_bounds:
            ml = car_bounds.get('mut_loaded_end', CARINDEX_MUT_LOADED_END)
            ms = car_bounds.get('mut_session_end', CARINDEX_MUT_SESSION_END)
            pop_est = car_bounds.get('pop_est', 0)
            src = car_bounds.get('source', 'fixed')
            R.p(
                f'  CarIndex esquema ({src}):         LOADED=1, SESSION=2, MUT_LOADED=3..{ml}, '
                f'MUT_SESSION={ml+1}..{ms}, MUT_LOADED_LARGE>{ms}; '
                f'RANDOM=InitializeRandomBrain (pop~{pop_est})'
            )
    invalid_brain_rows = [r for r in dbg if is_invalid_brain_reason(r.get('death', ''))]
    if invalid_brain_rows:
        inv_spawn = Counter(r.get('spawn', '') for r in invalid_brain_rows if r.get('spawn', ''))
        inv_gen = Counter(r.get('gen', 0) for r in invalid_brain_rows)
        R.p(f'  INVALID_BRAIN:                  {len(invalid_brain_rows):>10d} ({sdiv(len(invalid_brain_rows)*100, nd):.2f}%)')
        if inv_spawn:
            top_inv_spawn = ', '.join(f'{sp.replace("TargetPoint", "TP")}:{cnt}' for sp, cnt in inv_spawn.most_common(5))
            R.p(f'  INVALID_BRAIN top spawns:       {top_inv_spawn}')
        if inv_gen:
            top_inv_gen = ', '.join(f'G{g}:{cnt}' for g, cnt in inv_gen.most_common(5))
            R.p(f'  INVALID_BRAIN top gens:         {top_inv_gen}')
    
    # Usar listas de mutación precomputadas
    mut_changed_vals = mut_lists['mut_changed']
    mut_avg_vals = mut_lists['mut_avg']
    mut_large_vals = mut_lists['mut_large']
    mut_parent_vals = mut_lists['mut_parent']
    mut_rate_vals = mut_lists['mut_rate']
    mut_large_rate_vals = mut_lists['mut_large_rate']
    mut_strength_vals = mut_lists['mut_strength']
    fit_vals = mut_lists['fit']
    mutation_n = len(mut_rate_vals)
    if any(mut_changed_vals) or any(mut_avg_vals) or any(mut_large_vals) or any(mut_parent_vals):
        R.p(f'  Weights total (assumed):        {WEIGHTS_TOTAL}')
        init_rows = sum(1 for r in dbg if r.get('is_weight_initialization', False))
        R.p(
            f'  Config EvolutionManager 26/06:  MUT_LOADED/MUT_SESSION={MUTATION_RATE_DYNAMIC_MIN*100:.2f}%..'
            f'{MUTATION_RATE_DYNAMIC_MAX*100:.2f}% | '
            f'MUT_LOADED_LARGE={MUTATION_RATE_LARGE_MIN*100:.2f}%..{MUTATION_RATE_LARGE_MAX*100:.2f}%'
        )
        R.p('  Nota: GenerationsWithoutImprovement no se exporta; el expected exacto es rango, no punto fijo.')
        if init_rows:
            R.p(f'  Inicializaciones excluidas:     {init_rows} (no son mutaciones)')
        R.p(
            f'  MutChanged mean/P50/P90:        {sdiv(sum(mut_changed_vals), mutation_n):>7.2f} / '
            f'{pctl(mut_changed_vals, 50):>7.2f} / {pctl(mut_changed_vals, 90):>7.2f}'
        )
        R.p(
            f'  MutRate mean/P50/P90:           {sdiv(sum(mut_rate_vals), mutation_n)*100:>6.2f}% / '
            f'{pctl(mut_rate_vals, 50)*100:>6.2f}% / {pctl(mut_rate_vals, 90)*100:>6.2f}%'
        )
        R.p(
            f'  MutAvgMag mean/P50/P90:         {sdiv(sum(mut_avg_vals), mutation_n):>7.4f} / '
            f'{pctl(mut_avg_vals, 50):>7.4f} / {pctl(mut_avg_vals, 90):>7.4f}'
        )
        R.p(
            f'  MutStrength mean/P50/P90:       {sdiv(sum(mut_strength_vals), mutation_n):>7.5f} / '
            f'{pctl(mut_strength_vals, 50):>7.5f} / {pctl(mut_strength_vals, 90):>7.5f}'
        )
        R.p(
            f'  MutNumLarge mean/P50/P90:       {sdiv(sum(mut_large_vals), mutation_n):>7.2f} / '
            f'{pctl(mut_large_vals, 50):>7.2f} / {pctl(mut_large_vals, 90):>7.2f}'
        )
        R.p(
            f'  MutLarge share (global):        {sdiv(sum(mut_large_vals), max(sum(mut_changed_vals), 1.0)) * 100.0:>9.2f}%'
        )
        R.p(
            f'  MutLargeRate mean/P50/P90:      {sdiv(sum(mut_large_rate_vals), mutation_n)*100:>6.2f}% / '
            f'{pctl(mut_large_rate_vals, 50)*100:>6.2f}% / {pctl(mut_large_rate_vals, 90)*100:>6.2f}%'
        )
        R.p(f'  Corr MutRate vs Fit:            {pearson_corr(mut_rate_vals, fit_vals):>10.4f}')
        R.p(f'  Corr MutAvgMag vs Fit:          {pearson_corr(mut_avg_vals, fit_vals):>10.4f}')
        R.p(f'  Corr MutStrength vs Fit:        {pearson_corr(mut_strength_vals, fit_vals):>10.4f}')
        R.p(f'  Corr MutChanged vs Fit:         {pearson_corr(mut_changed_vals, fit_vals):>10.4f}')
        parent_deltas = [r.get('mut_parent_delta', 0.0) for r in dbg if r.get('mut_parent_fit', 0.0) != 0.0]
        parent_delta_pct = [r.get('mut_parent_delta_pct', 0.0) for r in dbg if r.get('mut_parent_fit', 0.0) != 0.0]
        if parent_deltas:
            R.p(
                f'  DeltaFit vs Parent P10/P50/P90: {pctl(parent_deltas, 10):>7.2f} / '
                f'{pctl(parent_deltas, 50):>7.2f} / {pctl(parent_deltas, 90):>7.2f}'
            )
        if parent_delta_pct:
            R.p(f'  DeltaFit% vs Parent (P50):      {pctl(parent_delta_pct, 50):>10.2f}%')
        fam_rows = defaultdict(list)
        for r in dbg:
            fam_rows[car_index_family_for_row(r, bounds=car_bounds)].append(r)
        fam_stats = []
        for fam, rows_f in fam_rows.items():
            mutation_rows = [x for x in rows_f if not x.get('is_weight_initialization', False)]
            if len(mutation_rows) < 5:
                continue
            fam_stats.append((
                fam,
                len(mutation_rows),
                mean([x.get('mut_rate', 0.0) for x in mutation_rows]),
                mean([x.get('expected_mut_rate_min', 0.0) or 0.0 for x in mutation_rows]),
                mean([x.get('expected_mut_rate_max', 0.0) or 0.0 for x in mutation_rows]),
                mean([x.get('fit', 0.0) for x in mutation_rows]),
            ))
        if fam_stats:
            R.p('  By family (observed vs expected range):')
            for fam, n, mrate, expected_min, expected_max, mfit in sorted(fam_stats, key=lambda x: x[2], reverse=True):
                if expected_min == expected_max:
                    expected_txt = f'{expected_min*100:>5.2f}%'
                else:
                    expected_txt = f'{expected_min*100:>5.2f}..{expected_max*100:>5.2f}%'
                R.p(
                    f'    {fam:10s}: N={n:4d} observed={mrate*100:>6.2f}% '
                    f'expected={expected_txt} fit_mean={mfit:>9.1f}'
                )
        spawn_mut = []
        for sp, rows_sp in spawns.items():
            if len(rows_sp) < MIN_SPAWN_N:
                continue
            spawn_mut.append((
                sp,
                len(rows_sp),
                mean([x.get('mut_rate', 0.0) for x in rows_sp]),
                mean([x.get('fit', 0.0) for x in rows_sp]),
            ))
        if spawn_mut:
            spawn_mut.sort(key=lambda x: x[2], reverse=True)
            top_tags = ', '.join(
                f"{s.replace('TargetPoint','TP')}:{m*100:.2f}%"
                for s, _, m, _ in spawn_mut[:MUTATION_TOP_SPAWNS]
            )
            R.p(f'  Top spawns by mut_rate (N>={MIN_SPAWN_N}): {top_tags}')

    if not freerun:
        R.p(f'\n-- Mutation por Generacion --')
        hdr_m = f'  {"Gen":>5s} | {"MutRate%":>8s} | {"MutMag":>8s} | {"Large%":>8s} | {"Strength":>9s} | {"FitMed":>9s}'
        R.p(hdr_m)
        R.p(f'  {"-"*(len(hdr_m)-2)}')
        gen_mut = []
        for g in gens:
            gc = by_gen[g]
            ng = len(gc)
            if ng == 0:
                continue
            g_mut_rate = mean([x.get('mut_rate', 0.0) for x in gc]) * 100.0
            g_mut_mag = mean([x.get('mut_avg_mag', 0.0) for x in gc])
            g_mut_large = mean([x.get('mut_large_share', 0.0) for x in gc]) * 100.0
            g_mut_strength = mean([x.get('mut_strength', 0.0) for x in gc])
            g_fit_med = pctl([x.get('fit', 0.0) for x in gc], 50)
            gen_mut.append((g, g_mut_rate, g_mut_mag, g_mut_large, g_mut_strength, g_fit_med))
        for g, r_m, m_m, l_m, s_m, f_m in gen_mut[:MUTATION_TOP_GENS]:
            R.p(f'  {g:5d} | {r_m:8.2f} | {m_m:8.4f} | {l_m:8.2f} | {s_m:9.5f} | {f_m:9.2f}')
    else:
        R.p(f'\n-- Mutation por Generacion --')
        R.p('  Omitido en FreeRun: la generacion del Debug es constante y no representa evolucion.')
    R.p(f'  ShareBrake (Throttle+Brake):     {sdiv(agg["brake_in"], agg["cmd_total"]):>10.4f}')
    R.p(f'  ShareGraceBrake (GraceContext):  {sdiv(agg["brake_grace"], agg["grace_cmd_total"]):>10.4f}')
    R.p(f'  ShareStopBrake (StopContext):    {sdiv(agg["stop_brake"], agg["stop_cmd_total"]):>10.4f}')
    R.p(f'  Cobertura StopContext (ticks):   {sdiv(agg["t_stop_ctx"], agg["t_tot"]):>10.4f}')
    R.p(f'  Fitness_Final medio:             {sdiv(agg["fit"], nd):>10.4f}')

    # Medidas robustas (distribucion completa por coche)
    fits_all = [r['fit'] for r in dbg]
    times_all = [r['time'] for r in dbg]
    R.p(f'  Fitness P10/P50/P90:             {pctl(fits_all,10):>10.2f} / {pctl(fits_all,50):>10.2f} / {pctl(fits_all,90):>10.2f}')
    R.p(f'  Fitness CVaR10 (peor 10%):       {cvar(fits_all,10):>10.2f}')
    R.p(f'  Tiempo P10/P50/P90:              {pctl(times_all,10):>10.2f} / {pctl(times_all,50):>10.2f} / {pctl(times_all,90):>10.2f}')

    if not freerun:
        # Componentes por gen
        show_gens = gens[:20]
        if len(gens) > 25:
            show_gens += ['...'] + gens[-5:]
        elif len(gens) > 20:
            show_gens = gens

        R.p(f'\n-- Componentes por Generacion --')
        hdr2 = f'  {"Gen":>5s} | {"NetNorm":>9s} | {"A":>8s} | {"E":>8s} | {"F":>8s} | {"PenM":>9s} | {"PenV":>8s} | {"PenTV":>8s} | {"PenNav":>8s} | {"PenCr":>8s} | {"PenRv":>8s} | {"PenLz":>8s} | {"PenSS":>8s} | {"FitMed":>9s}'
        R.p(hdr2)
        R.p(f'  {"-"*(len(hdr2)-2)}')
        for g in show_gens:
            if g == '...':
                R.p(f'  {"...":>5s}')
                continue
            gc = by_gen[g]
            ng = len(gc)
            R.p('  {:>5d} | {:>9.4f} | {:>8.4f} | {:>8.4f} | {:>8.4f} | {:>9.2f} | {:>8.4f} | {:>8.4f} | {:>8.4f} | {:>8.4f} | {:>8.4f} | {:>8.4f} | {:>8.4f} | {:>9.2f}'.format(
                g,
                sdiv(sum(r['net'] for r in gc), ng),
                sdiv(sum(r['a'] for r in gc), ng),
                sdiv(sum(r['e'] for r in gc), ng),
                sdiv(sum(r['f'] for r in gc), ng),
                sdiv(sum(r['pen_m'] for r in gc), ng),
                sdiv(sum(r['pen_v'] for r in gc), ng),
                sdiv(sum(r.get('pen_tv', 0.0) for r in gc), ng),
                sdiv(sum(r.get('pen_nav', 0.0) for r in gc), ng),
                sdiv(sum(r.get('pen_creep', 0.0) for r in gc), ng),
                sdiv(sum(r.get('pen_rev', 0.0) for r in gc), ng),
                sdiv(sum(r.get('pen_lazy', 0.0) for r in gc), ng),
                sdiv(sum(r.get('pen_swstop', 0.0) for r in gc), ng),
                sdiv(sum(r['fit'] for r in gc), ng)))

        R.p(f'\n-- Control por Generacion --')
        hdr3 = f'  {"Gen":>5s} | {"Thr+":>8s} | {"GraceThr":>8s} | {"GraceBr":>8s} | {"Brake":>8s} | {"Coast":>8s} | {"StopB":>8s} | {"StopT":>8s} | {"StopTicks":>9s} | {"YldVal":>8s} | {"StopVal":>8s} | {"SteerIn":>8s} | {"SteerTgt":>8s} | {"GapAbs":>8s} | {"StopBrake%":>10s} | {"GraceBr%":>9s}'
        R.p(hdr3)
        R.p(f'  {"-"*(len(hdr3)-2)}')
        for g in show_gens:
            if g == '...':
                R.p(f'  {"...":>5s}')
                continue
            gc = by_gen[g]
            ng = len(gc)
            g_thr = sdiv(sum(r.get('thr_pos', 0.0) for r in gc), ng)
            g_grace = sdiv(sum(r.get('thr_grace', 0.0) for r in gc), ng)
            g_grace_br = sdiv(sum(r.get('brake_grace', 0.0) for r in gc), ng)
            g_brake = sdiv(sum(r.get('brake_in', 0.0) for r in gc), ng)
            g_coast = sdiv(sum(r.get('coast_t', 0.0) for r in gc), ng)
            g_stop_b = sdiv(sum(r.get('stop_brake', 0.0) for r in gc), ng)
            g_stop_t = sdiv(sum(r.get('stop_throttle', 0.0) for r in gc), ng)
            g_stop_ticks = sdiv(sum(r.get('t_stop_ctx', 0.0) for r in gc), ng)
            g_yield_val = sdiv(sum(r.get('yield_val_t', 0.0) for r in gc), ng)
            g_stop_val = sdiv(sum(r.get('stop_val_t', 0.0) for r in gc), ng)
            g_steer_in = sdiv(sum(r.get('steer_in', 0.0) for r in gc), ng)
            g_steer_tgt = sdiv(sum(r.get('steer_target', 0.0) for r in gc), ng)
            g_steer_gap = sdiv(sum(abs(r.get('steer_in', 0.0) - r.get('steer_target', 0.0)) for r in gc), ng)
            g_stop_share = sdiv(g_stop_b, g_stop_b + g_stop_t)
            g_grace_br_share = sdiv(g_grace_br, g_grace + g_grace_br)
            R.p('  {:>5d} | {:>8.4f} | {:>8.4f} | {:>8.4f} | {:>8.4f} | {:>8.4f} | {:>8.4f} | {:>8.4f} | {:>9.3f} | {:>8.4f} | {:>8.4f} | {:>8.4f} | {:>8.4f} | {:>8.4f} | {:>9.2f}% | {:>8.2f}%'.format(
                g, g_thr, g_grace, g_grace_br, g_brake, g_coast, g_stop_b, g_stop_t, g_stop_ticks, g_yield_val, g_stop_val, g_steer_in, g_steer_tgt, g_steer_gap, g_stop_share * 100.0, g_grace_br_share * 100.0))

        # Mejor coche por gen
        show_best = gens[:30]
        if len(gens) > 35:
            show_best += ['...'] + gens[-5:]
        elif len(gens) > 30:
            show_best = gens
        R.p(f'\n-- Mejor Coche por Generacion (raw fitness) --')
        for g in show_best:
            if g == '...':
                R.p('  ...')
                continue
            gc = by_gen[g]
            best = max(gc, key=lambda x: x['fit'])
            R.p(f'  Gen {g:>4d}: fit={best["fit"]:>10.2f} spawn={best["spawn"].replace("TargetPoint","TP"):>8s} t={best["time"]}s death={best["death"]}')
    else:
        R.p(f'\n-- Tablas por Generacion --')
        R.p('  Omitidas en FreeRun: la generacion del Debug es constante; usar rankings por spawn y ciclos censurados.')

# ── Resumen rapido para comparacion ──

def report_quicksummary(R, rows, dbg):
    """Bloque compacto para copiar-pegar y comparar entre dias."""
    n = len(rows)
    if n == 0 and not dbg:
        return
    freerun = is_freerun_analysis(summary_rows=rows, debug_rows=dbg)

    R.p(f'\n{"="*76}')
    R.p(f'  RESUMEN RAPIDO (copiar para comparar)')
    R.p(f'{"="*76}')
    R.p(f'  Modo:             {MODE}')
    R.p(f'  Fecha:            {datetime.now().strftime("%d/%m/%Y")}')
    if n > 0:
        br = max(rows, key=lambda x: x['best'])
        mr = max(rows, key=lambda x: x['mean'])
        avg_best = sdiv(sum(r['best'] for r in rows), n)
        avg_mean = sdiv(sum(r['mean'] for r in rows), n)
        avg_time = sdiv(sum(r['time'] for r in rows), n)
        neg = sum(1 for r in rows if r['mean'] < 0)
        if freerun:
            R.p('  Eje:              FreeRun session/spawn (sin generaciones)')
            R.p(f'  Snapshot summary: {n} fila agregada')
            R.p(f'  BestFit terminal: {br["best"]:.6f}')
        else:
            R.p(f'  Generaciones:     {n}')
            R.p(f'  BestFit max:      {br["best"]:.6f} (gen {br["gen"]})')
        R.p(f'  BestFit medio:    {avg_best:.6f}')
        if not freerun:
            R.p(f'  MeanFit max:      {mr["mean"]:.6f} (gen {mr["gen"]})')
        R.p(f'  MeanFit medio:    {avg_mean:.6f}')
        R.p(f'  MeanFit P50:      {pctl([r["mean"] for r in rows], 50):.6f}')
        R.p(f'  %MeanFit < 0:     {sdiv(neg*100,n):.1f}%')
        R.p(f'  {"Tiempo terminal" if freerun else "TiempoMedio"}:      {avg_time:.2f}s')
    else:
        R.p('  Generaciones:     0 (summary vacio)')
        R.p('  Best/MeanFit:     n/a (se usa bloque Debug para comparacion rapida)')

    if dbg:
        nd = len(dbg)
        deaths = Counter(r['death'] for r in dbg)
        top_death = deaths.most_common(1)[0] if deaths else ('N/A', 0)
        collision_stats = summarize_collision_deaths(dbg)
        yield_stuck = detect_yield_stuck_candidates(dbg)
        stop_stuck = detect_stop_stuck_candidates(dbg)
        cmd_total = sum(r.get('thr_pos', 0.0) + r.get('brake_in', 0.0) for r in dbg)
        grace_cmd_total = sum(r.get('thr_grace', 0.0) + r.get('brake_grace', 0.0) for r in dbg)
        stop_cmd_total = sum(r.get('stop_brake', 0.0) + r.get('stop_throttle', 0.0) for r in dbg)
        death_fail_n = sum(1 for r in dbg if r.get('is_test_failure_death', is_test_failure_reason(r.get('death', ''))))
        death_fail_pct = sdiv(death_fail_n * 100.0, nd)
        R.p(f'  Fitness raw med:  {sdiv(sum(r["fit"] for r in dbg), nd):.2f}')
        R.p(f'  NetNormal med:    {sdiv(sum(r["net"] for r in dbg), nd):.4f}')
        R.p(f'  PenMuerte med:    {sdiv(sum(r["pen_m"] for r in dbg), nd):.2f}')
        R.p(f'  PenTraffic med:   {sdiv(sum(r.get("pen_tv", 0.0) for r in dbg), nd):.2f}')
        R.p(f'  PenNav med:       {sdiv(sum(r.get("pen_nav", 0.0) for r in dbg), nd):.2f}')
        R.p(f'  PenCreeping med:  {sdiv(sum(r.get("pen_creep", 0.0) for r in dbg), nd):.2f}')
        R.p(f'  PenReverse med:   {sdiv(sum(r.get("pen_rev", 0.0) for r in dbg), nd):.2f}')
        R.p(f'  PenLazy med:      {sdiv(sum(r.get("pen_lazy", 0.0) for r in dbg), nd):.2f}')
        R.p(f'  PenSteerStop med: {sdiv(sum(r.get("pen_swstop", 0.0) for r in dbg), nd):.2f}')
        if debug_field_available(dbg, 'pen_align'):
            R.p(f'  PenAlign med:     {sdiv(sum(r.get("pen_align", 0.0) for r in dbg), nd):.2f}')
        R.p(f'  ThrGrace med:     {sdiv(sum(r.get("thr_grace", 0.0) for r in dbg), nd):.2f}')
        R.p(f'  BrGrace med:      {sdiv(sum(r.get("brake_grace", 0.0) for r in dbg), nd):.2f}')
        R.p(f'  YieldVal med:     {sdiv(sum(r.get("yield_val_t", 0.0) for r in dbg), nd):.2f}')
        R.p(f'  StopVal med:      {sdiv(sum(r.get("stop_val_t", 0.0) for r in dbg), nd):.2f}')
        R.p(f'  StopDone med:     {sdiv(sum(r.get("stop_done_n", 0.0) for r in dbg), nd):.2f}')
        R.p(f'  YieldDone med:    {sdiv(sum(r.get("yield_done_n", 0.0) for r in dbg), nd):.2f}')
        R.p(f'  StopBonus med:    {sdiv(sum(r.get("stop_bonus", 0.0) for r in dbg), nd):.2f}')
        R.p(f'  YieldBonus med:   {sdiv(sum(r.get("yield_bonus", 0.0) for r in dbg), nd):.2f}')
        if debug_field_available(dbg, 'yield_free_passes'):
            R.p(f'  YieldFree total:  {sum(r.get("yield_free_passes", 0.0) for r in dbg):.0f}')
        if debug_field_available(dbg, 'crossing_blocked_t'):
            blocked_total = sum(r.get('crossing_blocked_t', 0.0) for r in dbg)
            blocked_rows = sum(1 for r in dbg if r.get('crossing_blocked_t', 0.0) > 0.0)
            R.p(f'  CrossBlocked:     {blocked_total:.2f}s ({blocked_rows}/{nd} coches)')
        if debug_field_available(dbg, 'first_steer_release_ticks'):
            release_vals = metric_values(dbg, 'first_steer_release_ticks')
            R.p(f'  FirstSteerRel P50:{pctl(release_vals, 50):.2f} ticks (N={len(release_vals)})')
        if debug_field_available(dbg, 'steer_app_wrong') or debug_field_available(dbg, 'steer_app_right'):
            wrong_share_vals = [v * 100.0 for v in metric_values(dbg, 'steer_app_wrong_share')]
            R.p(f'  SteerAppWrong P50:{pctl(wrong_share_vals, 50):.2f}% (N={len(wrong_share_vals)})')
        if debug_field_available(dbg, 'round_entered_n'):
            round_entered = sum(r.get('round_entered_n', 0.0) for r in dbg)
            round_completed = sum(r.get('round_completed_n', 0.0) for r in dbg)
            round_collisions = sum(r.get('round_collisions', 0.0) for r in dbg)
            round_ticks = sum(r.get('round_ticks', 0.0) for r in dbg)
            round_bonus = sum(r.get('round_bonus', 0.0) for r in dbg)
            round_completion_bonus = sum(r.get('round_completion_bonus', 0.0) for r in dbg)
            round_entry_penalty = sum(r.get('round_entry_penalty', 0.0) for r in dbg)
            round_throttle_penalty = sum(r.get('round_throttle_penalty', 0.0) for r in dbg)
            total_ticks = sum(r.get('t_tot', 0.0) for r in dbg)
            R.p(f'  Round entered:    {round_entered:.0f}')
            R.p(f'  Round compl. conf.: {round_completed:.0f} ({sdiv(round_completed*100.0, round_entered):.2f}%)*')
            R.p(f'  Round collisions: {round_collisions:.0f} ({sdiv(round_collisions*100.0, round_entered):.2f}%)')
            R.p(f'  Round tick share: {sdiv(round_ticks*100.0, total_ticks):.2f}%')
            if debug_field_available(dbg, 'round_bonus'):
                R.p(f'  Round bonus net:  {round_bonus:.2f} ({sdiv(round_bonus, round_entered):.2f}/entry, {sdiv(round_bonus, round_ticks):.4f}/tick)')
                if debug_field_available(dbg, 'round_completion_bonus'):
                    R.p(
                        f'  Round C/E/T:      +{round_completion_bonus:.2f} / '
                        f'-{round_entry_penalty:.2f} / -{round_throttle_penalty:.2f}'
                    )
            R.p('  * Confirmada al registrar la siguiente entrada; limite inferior.')
            if debug_field_available(dbg, 'round_exit1_count'):
                exit_rates = []
                for exit_num in (1, 2, 3):
                    count = sum(r.get(f'round_exit{exit_num}_count', 0.0) for r in dbg)
                    deaths = sum(r.get(f'round_exit{exit_num}_deaths', 0.0) for r in dbg)
                    exit_rates.append(sdiv(deaths * 100.0, count))
                R.p(f'  Round death E1/E2/E3+: {exit_rates[0]:.2f}% / {exit_rates[1]:.2f}% / {exit_rates[2]:.2f}%')
        R.p(f'  SteerIn med:      {sdiv(sum(r.get("steer_in", 0.0) for r in dbg), nd):.2f}')
        R.p(f'  SteerTgt med:     {sdiv(sum(r.get("steer_target", 0.0) for r in dbg), nd):.2f}')
        R.p(f'  SteerAbs/tick med:{sdiv(sum(r.get("steer_abs_avg", 0.0) for r in dbg), nd):.4f}')
        R.p(f'  SteerGap med:     {sdiv(sum(r.get("steer_gap_avg_abs", abs(r.get("steer_in", 0.0) - r.get("steer_target", 0.0))) for r in dbg), nd):.4f}')
        mut_changed_vals = [r.get('mut_changed', 0.0) for r in dbg]
        mut_avg_vals = [r.get('mut_avg_mag', 0.0) for r in dbg]
        mut_large_vals = [r.get('mut_large', 0.0) for r in dbg]
        if any(mut_changed_vals) or any(mut_avg_vals) or any(mut_large_vals):
            R.p(f'  MutChanged med:  {pctl(mut_changed_vals, 50):.2f}')
            R.p(f'  MutAvgMag med:   {pctl(mut_avg_vals, 50):.4f}')
            R.p(f'  MutLarge med:    {pctl(mut_large_vals, 50):.2f}')
            mut_rate_vals = [r.get('mut_rate', 0.0) for r in dbg]
            if any(mut_rate_vals):
                R.p(f'  MutRate med:    {pctl(mut_rate_vals, 50)*100:.2f}%')
        car_fams = summarize_car_index_families(dbg)
        if car_fams:
            fam_line = ', '.join('{}={}'.format(x['family'], x['n']) for x in car_fams)
            R.p(f'  CarIdx familias:  {fam_line}')
        R.p(f'  Brake share:      {sdiv(sum(r.get("brake_in", 0.0) for r in dbg), cmd_total)*100:.2f}%')
        R.p(f'  Grace brake share:{sdiv(sum(r.get("brake_grace", 0.0) for r in dbg), grace_cmd_total)*100:.2f}%')
        R.p(f'  Stop brake share: {sdiv(sum(r.get("stop_brake", 0.0) for r in dbg), stop_cmd_total)*100:.2f}%')
        R.p(f'  Stop ctx/tot tick:{sdiv(sum(r.get("t_stop_ctx", 0.0) for r in dbg), sum(r.get("t_tot", 0.0) for r in dbg))*100:.2f}%')
        if debug_field_available(dbg, 'car_overlaps'):
            overlap_total = sum(r.get('car_overlaps', 0.0) for r in dbg)
            overlap_rows = sum(1 for r in dbg if r.get('car_overlaps', 0.0) > 0.0)
            R.p(f'  CarOverlaps:      {overlap_total:.0f} ({overlap_rows}/{nd} coches)')
            if debug_field_available(dbg, 'car_overlap_pen_shadow'):
                R.p(f'  OverlapShadow:    {sum(r.get("car_overlap_pen_shadow", 0.0) for r in dbg):.2f}')
            if debug_field_available(dbg, 'car_overlap_penalty'):
                overlap_pen_total = sum(r.get('car_overlap_penalty', 0.0) for r in dbg)
                R.p(f'  OverlapPenalty:   {overlap_pen_total:.2f} ({sdiv(overlap_pen_total, overlap_total):.2f}/overlap)')
        if debug_field_available(dbg, 'queue_wait_bonus'):
            queue_wait_total = sum(r.get('queue_wait_bonus', 0.0) for r in dbg)
            queue_wait_rows = sum(1 for r in dbg if r.get('queue_wait_bonus', 0.0) > 0.0)
            R.p(f'  QueueWaitBonus:   {queue_wait_total:.2f} ({queue_wait_rows}/{nd} coches)')
        R.p(f'  Muerte #1:        {top_death[0]} ({sdiv(top_death[1]*100,nd):.0f}%)')
        if collision_stats['total'] > 0:
            R.p(
                f'  Collisions N/R:   {collision_stats["normal"]}/{collision_stats["roundabout"]} '
                f'(R={sdiv(collision_stats["roundabout"]*100.0, collision_stats["total"]):.1f}%)'
            )
        stop_violation_detail = summarize_stop_violation_subtypes(dbg)
        if stop_violation_detail:
            R.p(
                f'  StopViol E/T/G:   {stop_violation_detail.get("EXIT", 0)}/'
                f'{stop_violation_detail.get("TIMEOUT", 0)}/{stop_violation_detail.get("GENERIC", 0)}'
            )
        R.p(f'  Fail por muerte:  {death_fail_pct:.2f}% ({death_fail_n}/{nd})')
        if yield_stuck.get('timefinished_rows', 0) > 0:
            R.p(
                f'  YieldTrap(TF):    {yield_stuck.get("candidate_count", 0)}/{yield_stuck.get("timefinished_rows", 0)} '
                f'({yield_stuck.get("candidate_pct_timefinished", 0.0):.1f}%) | watch={yield_stuck.get("watch_count", 0)}'
            )
        if stop_stuck.get('timefinished_rows', 0) > 0:
            R.p(
                f'  StopTrap(TF):     {stop_stuck.get("candidate_count", 0)}/{stop_stuck.get("timefinished_rows", 0)} '
                f'({stop_stuck.get("candidate_pct_timefinished", 0.0):.1f}%) | watch={stop_stuck.get("watch_count", 0)}'
            )

    if n >= 10:
        ln = min(50, n // 3)
        tail = rows[-ln:]
        R.p(f'  Ult{ln} MeanFit:    {sdiv(sum(r["mean"] for r in tail), ln):.6f}')
        R.p(f'  Ult{ln} Tiempo:     {sdiv(sum(r["time"] for r in tail), ln):.2f}s')

    # KPI extendido de test (si existe en Summary)
    if n > 0 and any('success_rate' in r for r in rows):
        kpi_rows = [r for r in rows if 'success_rate' in r]
        nk = len(kpi_rows)
        derived = [binary_metrics_from_row(r) for r in kpi_rows]
        avg_success = sdiv(sum(m['success_rate'] for m in derived), nk)
        avg_fail = sdiv(sum(m['fail_rate'] for m in derived), nk)
        total_success = sum(r.get('success_count', 0) for r in kpi_rows)
        total_fail = sum(r.get('fail_count', 0) for r in kpi_rows)
        total_censored = sum(int(num(r.get('censored_count', 0), 0.0)) for r in kpi_rows)
        total_eval = sum(m['n'] for m in derived)
        wl_rows = [m['wilson_lo'] for m in derived if m['n'] > 0]
        score_wilson = sdiv(sum(wl_rows), len(wl_rows)) if wl_rows else 0.0
        if total_censored > 0:
            success_upper = sdiv((total_success + total_censored) * 100.0, total_eval)
            observed_rate = sdiv(total_success * 100.0, total_success + total_fail)
            R.p(f'  Aciertos (%):     {avg_success:.2f}-{success_upper:.2f}% (cens {total_censored})')
            R.p(f'  Aciertos obs.:    {observed_rate:.2f}% terminal')
        else:
            R.p(f'  Aciertos (%):     {avg_success:.2f}%')
        R.p(f'  Errores (%):      {avg_fail:.2f}%')
        R.p(f'  Score (WilsonLB): {score_wilson:.2f}')
        R.p(f'  Aciertos P50:     {pctl([m["success_rate"] for m in derived], 50):.2f}%')
        if dbg:
            death_fail_n = sum(1 for r in dbg if r.get('is_test_failure_death', is_test_failure_reason(r.get('death', ''))))
            death_fail_pct = sdiv(death_fail_n * 100.0, len(dbg))
            R.p(f'  Fail muerte vs SummaryFail: {death_fail_pct:.2f}% vs {avg_fail:.2f}%')

def report_input_quality(R, summary_meta, debug_meta):
    R.p(f'\n{"="*76}')
    R.p('  CALIDAD DE ENTRADA (CSV)')
    R.p(f'{"="*76}')

    for name, meta in [('Summary', summary_meta), ('Debug', debug_meta)]:
        R.p(f'\n-- {name} --')
        if not meta.get('exists'):
            R.p(f'  Estado: NO ENCONTRADO')
            R.p(f'  Ruta:   {meta.get("path", "")}')
            continue

        R.p(f'  Ruta:            {meta.get("path", "")}')
        R.p(f'  Tamano:          {meta.get("size_bytes", 0):,} bytes')
        R.p(f'  Modificado:      {meta.get("mtime", "")}')
        R.p(f'  Filas datos:     {meta.get("data_rows", 0)}')
        R.p(f'  Filas cargadas:  {meta.get("loaded_rows", 0)}')
        if meta.get('synthetic_from_debug'):
            R.p(f'  Reconstruido:    SI, desde {meta.get("synthetic_source", "Fitness_Debug.csv")}')
            R.p(f'  Filas reconstr.: {meta.get("synthetic_rows", meta.get("loaded_rows", 0))}')
            R.p(f'  Debug usado rec.: {meta.get("synthetic_debug_rows", 0)} registros')
            censoring = meta.get('freerun_censoring', {})
            if censoring.get('enabled'):
                R.p(
                    f'  FreeRun cens.:   {censoring.get("censored_alive_count", 0)} vivos estimados; '
                    f'intentos~{censoring.get("total_attempts_with_censored", 0)}'
                )
                R.p(
                    f'  Edad vivos est.: P50={censoring.get("censored_age_p50_s", 0.0):.2f}s, '
                    f'P90={censoring.get("censored_age_p90_s", 0.0):.2f}s, '
                    f'max={censoring.get("censored_age_max_s", 0.0):.2f}s'
                )
                R.p(f'  Sesion FreeRun est.: {censoring.get("session_elapsed_estimate_s", 0.0):.2f}s')
                R.p(
                    f'  Fuente censura:  {censoring.get("source", "-")} '
                    f'(confianza {censoring.get("confidence", "-")})'
                )
        if 'selected_rows' in meta:
            R.p(f'  Filas seleccionadas (modo): {meta.get("selected_rows", 0)}')
        R.p(f'  Filas descart.:  {meta.get("discarded_rows", 0)}')
        R.p(f'  Filas vacias:    {meta.get("empty_rows", 0)}')
        R.p(f'  Filas cortas:    {meta.get("short_rows", 0)}')
        if meta.get('long_rows', 0):
            R.p(f'  Filas largas:    {meta.get("long_rows", 0)} (max cols {meta.get("max_cols", 0)} vs header {meta.get("header_cols", 0)})')
        R.p(f'  Campos mapeados: {len(meta.get("mapped_keys", []))} -> {short_list(meta.get("mapped_keys", []), 14)}')
        R.p(f'  Campos faltan:   {short_list(meta.get("missing_required", []), 14)}')
        R.p(f'  Cabeceras extra: {short_list(meta.get("unknown_headers", []), 14)}')
        if meta.get('duplicate_headers'):
            R.p(f'  Cabeceras duplicadas: {short_list(meta.get("duplicate_headers", []), 14)}')
        if meta.get('duplicate_mapped_keys'):
            R.p(f'  Campos mapeados duplicados: {short_list(meta.get("duplicate_mapped_keys", []), 14)}')


def report_program_updates_0107(R, dbg):
    """Describe semantic changes from the 01/07 program export when present."""
    if not dbg:
        return
    has_overlap_penalty = debug_field_available(dbg, 'car_overlap_penalty')
    has_queue_wait = debug_field_available(dbg, 'queue_wait_bonus')
    has_speed_penalty = debug_field_available(dbg, 'pen_v')
    has_schema_0107 = (
        has_overlap_penalty
        or has_queue_wait
        or (dbg[0].get('_schema') == '2026-07-01-overlap-penalty-queue-wait')
        or str(dbg[0].get('_schema', '')).startswith('2026-07-03')
    )
    if not has_schema_0107:
        return

    nd = len(dbg)
    R.p(f'\n-- Novedades del Programa 01/07 --')
    if has_speed_penalty:
        speed_pen_total = sum(r.get('pen_v', 0.0) for r in dbg)
        speed_pen_rows = sum(1 for r in dbg if r.get('pen_v', 0.0) > 0.0)
        speed_pen_vals = metric_values(dbg, 'pen_v_per_life_sec')
        R.p(
            f'  PenaltyVelocidad: {speed_pen_total:.2f} total, '
            f'exposicion {speed_pen_rows}/{nd} coches.'
        )
        R.p(
            '  Interpretacion 01/07: el calculo usa EffectiveObstacleDistance; '
            'si hay coche vivo cercano, la distancia efectiva depende de ClosestVehicleDistance '
            'y de la velocidad de ese coche.'
        )
        R.p(
            '  Implicacion: Acum_PenaltyVelocidad ya no es solo distancia frontal estatica; '
            'tambien refleja seguimiento de trafico/colas sin exportar una columna propia.'
        )
        if speed_pen_vals:
            R.p(
                f'  PenaltyVelocidad/s exp. P50/P90: {pctl(speed_pen_vals, 50):.4f} / '
                f'{pctl(speed_pen_vals, 90):.4f} (N={len(speed_pen_vals)}).'
            )
    if has_overlap_penalty:
        overlap_total = sum(r.get('car_overlaps', 0.0) for r in dbg)
        overlap_rows = sum(1 for r in dbg if r.get('car_overlaps', 0.0) > 0.0)
        penalty_total = sum(r.get('car_overlap_penalty', 0.0) for r in dbg)
        penalty_vals = metric_values(dbg, 'car_overlap_penalty_per_overlap')
        shadow_total = sum(r.get('car_overlap_pen_shadow', 0.0) for r in dbg)
        R.p(
            f'  CarOverlapPenalty real: {penalty_total:.2f} total, '
            f'{sdiv(penalty_total, overlap_total):.2f}/overlap; '
            f'exposicion {overlap_rows}/{nd} coches.'
        )
        R.p(
            '  Interpretacion: se descuenta fitness por solape entre coches vivos; '
            'la base es velocidad relativa^2 / MaxSpeed.'
        )
        if debug_field_available(dbg, 'car_overlap_pen_shadow'):
            R.p(
                f'  Shadow vs real: shadow={shadow_total:.2f}, real={penalty_total:.2f}; '
                'shadow mide severidad diagnostica, real mide fitness aplicado.'
            )
        if penalty_vals:
            R.p(
                f'  Penalty/overlap exp. P50/P90: {pctl(penalty_vals, 50):.2f} / '
                f'{pctl(penalty_vals, 90):.2f} (N={len(penalty_vals)}).'
            )
    if has_queue_wait:
        queue_total = sum(r.get('queue_wait_bonus', 0.0) for r in dbg)
        queue_rows = sum(1 for r in dbg if r.get('queue_wait_bonus', 0.0) > 0.0)
        queue_life_vals = metric_values(dbg, 'queue_wait_bonus_per_life_sec')
        R.p(
            f'  QueueWaitBonus: {queue_total:.2f} total, '
            f'{sdiv(queue_total, nd):.2f}/coche global; exposicion {queue_rows}/{nd} coches.'
        )
        R.p(
            '  Interpretacion: bonus positivo por esperar en cola detras de otro coche, '
            'solo fuera de ForceStop/semaforo y con obstaculo frontal cercano.'
        )
        if queue_life_vals:
            R.p(
                f'  QueueWaitBonus/s exp. P50/P90: {pctl(queue_life_vals, 50):.4f} / '
                f'{pctl(queue_life_vals, 90):.4f} (N={len(queue_life_vals)}).'
            )
    R.p(
        '  Flujo test 01/07: si MultiTestingMode esta desactivado, el programa puede '
        'lanzar un unico coche con el modelo cargado; en ese caso el Summary puede no '
        'representar una generacion multi-coche completa.'
    )
    R.p(
        '  Limpieza generacional 01/07: al cerrar generacion se vacian colas pendientes '
        'de stop/yield/crossing; Acum_TimeBlockedAtCrossing se debe leer como bloqueo '
        'de la sesion actual, no como arrastre entre generaciones.'
    )


def report_program_updates_0307(R, dbg):
    """Describe semantic changes from the 03/07 program version when present."""
    if not dbg:
        return
    debug_schema = dbg[0].get('_schema', '')
    looks_current = (
        debug_schema == '2026-07-01-overlap-penalty-queue-wait'
        or str(debug_schema).startswith('2026-07-03')
        or debug_field_available(dbg, 'queue_wait_bonus')
        or debug_field_available(dbg, 'crossing_blocked_t')
        or debug_field_available(dbg, 'current_trigger')
    )
    if not looks_current:
        return

    nd = len(dbg)
    tl_ticks = sum(r.get('t_stop_ctx_tl', 0.0) for r in dbg)
    stop_ticks = sum(r.get('t_stop_ctx_stop', 0.0) for r in dbg)
    yield_ticks = sum(r.get('t_stop_ctx_yield', 0.0) for r in dbg)
    wait_bonus_total = sum(r.get('wait_bonus', 0.0) for r in dbg)
    wait_bonus_rows = sum(1 for r in dbg if r.get('wait_bonus', 0.0) > 0.0)
    creep_total = sum(r.get('pen_creep', 0.0) for r in dbg)
    creep_rows = sum(1 for r in dbg if r.get('pen_creep', 0.0) > 0.0)
    correcting_wrong_total = sum(r.get('pen_cw', 0.0) for r in dbg)
    correcting_wrong_rows = sum(1 for r in dbg if r.get('pen_cw', 0.0) > 0.0)
    reverse_total = sum(r.get('pen_rev', 0.0) for r in dbg)
    reverse_rows = sum(1 for r in dbg if r.get('pen_rev', 0.0) > 0.0)
    crossing_blocked_total = sum(r.get('crossing_blocked_t', 0.0) for r in dbg)
    crossing_blocked_rows = sum(1 for r in dbg if r.get('crossing_blocked_t', 0.0) > 0.0)

    R.p(f'\n-- Novedades del Programa 03/07 --')
    R.p(
        '  FreeRun: si IsFreeRunMode esta activo, EvolutionManager crea un coche por '
        'spawn con TrainingMode=false, bBypassLifetimeLimit=true y cerebro cargado. '
        'Leer esas ejecuciones como simulacion libre/debug, no como test estadistico '
        'multi-coche si el Summary no acompana.'
    )
    R.p(
        '  Red neuronal: el input DistToStopLine se mezcla con ReleaseFadeAlpha y '
        'vuelve gradualmente a 1.0 tras liberar ForceStop. FirstSteerAfterRelease '
        'sigue midiendo reaccion, pero ya no implica que la red siga viendo la '
        'distancia real a la linea durante todo el grace.'
    )
    R.p(
        '  Semaforo/stop/yield: las validaciones usan umbrales aprendidos desde '
        'muestras legales cuando existen. STOP anade ventana dinamica antes de linea '
        '(AllowedStopBeforeLine) y tiempo minimo aprendido.'
    )
    R.p(
        '  Fitness stop 03/07: STOP death penalty incluye exceso tras la linea con '
        'SignedDistanceToStopLine; StopCompletionBonus depende del tiempo minimo '
        'aprendido, no de una constante fija.'
    )
    R.p(
        '  Creeping/WaitBonus: CreepingPenalty solo aplica en semaforo/stop antes de '
        'la linea (SignedDistanceToStopLine <= 0) y no en yield; WaitBonus queda '
        'acotado por la ventana temporal de aproximacion.'
    )
    R.p(
        '  Yield 03/07: separa validacion libre, bloqueada y liberacion. '
        'Acum_TimeBlockedAtCrossing mezcla incrementos de stop (0.5s) y yield '
        'crossing/release (0.1/0.3s), asi que conviene interpretarlo como tiempo '
        'bloqueado total por contexto, no como contador homogeneo.'
    )
    R.p(
        '  Reverse 03/07: REVERSING_WRONG exige riesgo de ir marcha atras y steering '
        'en direccion incorrecta; REVERSE queda para el riesgo de marcha atras sin ese '
        'segundo componente; Penalty_CorrectingWrong cubre el caso de steering mal '
        'dirigido sin riesgo de reverse.'
    )
    if tl_ticks + stop_ticks + yield_ticks > 0.0:
        R.p(
            f'  Exposicion stop-context: semaforo={tl_ticks:.0f} ticks, '
            f'stop={stop_ticks:.0f}, yield={yield_ticks:.0f}.'
        )
    if crossing_blocked_total > 0.0:
        R.p(
            f'  TimeBlockedAtCrossing observado: {crossing_blocked_total:.2f}s en '
            f'{crossing_blocked_rows}/{nd} coches.'
        )
    if wait_bonus_total > 0.0 or creep_total > 0.0 or reverse_total > 0.0 or correcting_wrong_total > 0.0:
        R.p(
            f'  Totales clave 03/07: WaitBonus={wait_bonus_total:.2f} '
            f'({wait_bonus_rows}/{nd}), Creeping={creep_total:.2f} '
            f'({creep_rows}/{nd}), Reverse={reverse_total:.2f} '
            f'({reverse_rows}/{nd}), CorrectingWrong={correcting_wrong_total:.2f} '
            f'({correcting_wrong_rows}/{nd}).'
        )
    if debug_field_available(dbg, 'current_trigger'):
        trigger_counts = Counter(
            r.get('current_trigger_short') or short_actor_name(r.get('current_trigger', ''), empty='')
            for r in dbg
        )
        trigger_counts.pop('', None)
        if trigger_counts:
            top_trigger, top_n = trigger_counts.most_common(1)[0]
            R.p(
                f'  CurrentTrigger exportado: {len(trigger_counts)} triggers con datos; '
                f'top={top_trigger} ({top_n}/{nd}).'
            )
        else:
            R.p('  CurrentTrigger exportado, pero sin valores validos en este lote.')


def report_debug_scope(R, info):
    if not info:
        return
    R.p(f'\n-- Alcance del Debug por Fase --')
    R.p(f'  Modo analizado:           {info.get("mode", "")}')
    R.p(f'  Registros debug totales:  {info.get("raw_total", 0)}')
    R.p(f'  Registros seleccionados:  {info.get("selected_total", 0)}')
    if info.get('excluded_incomplete_rows', 0):
        R.p(
            f'  Excluidos sin Summary:    {info.get("excluded_incomplete_rows", 0)} '
            f'(gens {info.get("excluded_incomplete_generations", [])})'
        )

    if not info.get('has_training_flag', False):
        R.p('  Campo Training/TrainingMode: no detectado (se usa debug completo).')
        return

    R.p(f'  Split TRAIN/TEST/UNK:     {info.get("train_total", 0)} / {info.get("test_total", 0)} / {info.get("unknown_total", 0)}')
    if info.get('selected_total', 0) == 0:
        R.p('  AVISO: no hay registros debug para la fase solicitada.')

def analyze_data_coherence(mode, summary_rows, debug_rows, debug_scope=None):
    debug_scope = debug_scope or {}
    freerun = (debug_scope.get('freerun_censoring') or {}).get('enabled')

    def to_int(v, default=0):
        try:
            return int(v)
        except (TypeError, ValueError):
            return default

    summary_gens = sorted(set(g for g in (to_int(r.get('gen', 0)) for r in summary_rows) if g > 0))
    debug_gens = sorted(set(g for g in (to_int(r.get('gen', 0)) for r in debug_rows) if g > 0))
    overlap_gens = sorted(set(summary_gens) & set(debug_gens))

    pop_est = estimate_population_size(summary_rows, default=60) if summary_rows else 60
    eval_ns = [to_int(r.get('eval_n', 0)) for r in summary_rows if to_int(r.get('eval_n', 0)) > 0]
    if eval_ns:
        expected_debug_rows = sum(eval_ns)
        expected_debug_source = 'sum(N)'
    else:
        expected_debug_rows = len(summary_gens) * pop_est if summary_gens else 0
        expected_debug_source = 'gens*pop_est'
    debug_row_coverage = sdiv(len(debug_rows), expected_debug_rows)
    debug_gen_coverage = sdiv(len(debug_gens), len(summary_gens))
    overlap_coverage = sdiv(len(overlap_gens), len(summary_gens))

    sev = 0
    warnings = []

    def add_warning(level, msg):
        nonlocal sev
        warnings.append(msg)
        sev = max(sev, level)

    if summary_rows and not debug_rows:
        add_warning(2, 'Summary tiene datos pero Debug no tiene filas para este modo.')

    if mode in ('train', 'test'):
        if summary_gens and debug_gens and not overlap_gens:
            add_warning(
                2,
                f'No hay solapamiento de generaciones Summary({summary_gens[0]}..{summary_gens[-1]}) '
                f'vs Debug({debug_gens[0]}..{debug_gens[-1]}). Posible reset o mezcla de sesiones.',
            )
        elif summary_gens and overlap_coverage < 0.35:
            add_warning(1, f'Solo solapa el {overlap_coverage*100:.1f}% de generaciones entre Summary y Debug.')

        if len(summary_gens) >= 8 and debug_gen_coverage < 0.35:
            add_warning(1, f'Cobertura de generaciones en Debug baja ({debug_gen_coverage*100:.1f}%).')

        if expected_debug_rows >= (pop_est * 5) and debug_row_coverage < 0.35:
            add_warning(
                1,
                f'Cobertura de filas Debug baja ({debug_row_coverage*100:.1f}% de lo esperado ~{expected_debug_rows}).',
            )

    if debug_scope.get('has_training_flag'):
        raw_total = debug_scope.get('raw_total', 0)
        selected_total = debug_scope.get('selected_total', 0)
        unknown_total = debug_scope.get('unknown_total', 0)

        if raw_total > 0 and mode in ('train', 'test'):
            selected_share = sdiv(selected_total, raw_total)
            if selected_share < 0.20:
                add_warning(
                    1,
                    f'El modo actual usa solo {selected_share*100:.1f}% del Fitness_Debug (split por TrainingMode).',
                )

        if raw_total > 0 and sdiv(unknown_total, raw_total) > 0.50:
            add_warning(1, 'Mas del 50% de filas Debug tienen fase desconocida (TrainingMode ausente/ambiguo).')

        if mode == 'train' and raw_total > 0 and debug_scope.get('train_total', 0) == 0:
            add_warning(2, 'Modo TRAIN sin filas TRAIN en Fitness_Debug.')
        if mode == 'test' and raw_total > 0 and debug_scope.get('test_total', 0) == 0:
            add_warning(2, 'Modo TEST sin filas TEST en Fitness_Debug.')

    status = 'ok'
    if sev == 1:
        status = 'warning'
    elif sev >= 2:
        status = 'critical'

    return {
        'mode': mode,
        'status': status,
        'freerun_analysis': bool(freerun),
        'summary_rows': len(summary_rows),
        'summary_gens': len(summary_gens),
        'summary_gen_min': summary_gens[0] if summary_gens else 0,
        'summary_gen_max': summary_gens[-1] if summary_gens else 0,
        'debug_rows': len(debug_rows),
        'debug_gens': len(debug_gens),
        'debug_gen_min': debug_gens[0] if debug_gens else 0,
        'debug_gen_max': debug_gens[-1] if debug_gens else 0,
        'overlap_gens': len(overlap_gens),
        'expected_debug_rows': expected_debug_rows,
        'expected_debug_source': expected_debug_source,
        'population_estimate': pop_est,
        'debug_row_coverage_pct': debug_row_coverage * 100.0,
        'debug_gen_coverage_pct': debug_gen_coverage * 100.0,
        'overlap_coverage_pct': overlap_coverage * 100.0,
        'warnings': warnings,
    }

def report_data_coherence(R, info):
    if not info:
        return

    R.p(f'\n-- Coherencia Summary vs Debug --')
    R.p(f'  Estado:                  {info.get("status", "ok").upper()}')
    if info.get('freerun_analysis'):
        R.p(f'  Eje generacional:        n/a en FreeRun (gen 0/1 constante)')
        R.p(f'  Summary reconstruido:    {info.get("summary_rows", 0)} snapshot agregado')
        R.p(f'  Debug terminales:        {info.get("debug_rows", 0)} eventos exportados')
    else:
        R.p(
            f'  Summary filas/gens:      {info.get("summary_rows", 0)} / {info.get("summary_gens", 0)} '
            f'({info.get("summary_gen_min", 0)}..{info.get("summary_gen_max", 0)})'
        )
        R.p(
            f'  Debug filas/gens:        {info.get("debug_rows", 0)} / {info.get("debug_gens", 0)} '
            f'({info.get("debug_gen_min", 0)}..{info.get("debug_gen_max", 0)})'
        )
        R.p(f'  Solape de generaciones:  {info.get("overlap_gens", 0)}')
        R.p(f'  Cobertura gens Debug:    {info.get("debug_gen_coverage_pct", 0.0):.1f}%')
    R.p(
        f'  Cobertura filas Debug:   {info.get("debug_row_coverage_pct", 0.0):.1f}% '
        f'(esperado~{info.get("expected_debug_rows", 0)} via {info.get("expected_debug_source", "-")}, '
        f'pop~{info.get("population_estimate", 0)})'
    )

    warnings = info.get('warnings', [])
    if warnings:
        for w in warnings:
            R.p(f'  AVISO: {w}')
    else:
        R.p('  Sin alertas fuertes de desalineacion entre Summary y Debug.')

def report_yield_stuck_detection(R, info, freerun=False):
    if not info:
        return

    R.p(f'\n-- Deteccion de posible atasco en CEDA (TIME_FINISHED) --')
    total_rows = info.get('total_rows', 0)
    tf_rows = info.get('timefinished_rows', 0)
    R.p(f'  TIME_FINISHED:            {tf_rows}/{total_rows} ({info.get("timefinished_pct", 0.0):.2f}%)')

    if tf_rows == 0:
        R.p('  No hay registros TIME_FINISHED en este subconjunto.')
        return

    R.p(
        f'  Umbrales dinamicos: Fit<={info.get("fit_thr", 0.0):.2f}, '
        f'Fit/s<={info.get("fitps_thr", 0.0):.3f}, '
        f'StopCtx>={info.get("stop_ctx_thr", 0.0)*100:.2f}%, '
        f'StopTicks>={info.get("stop_ticks_thr", 0.0):.1f}, '
        f'YCtx>={info.get("stop_ctx_yield_thr", 0.0):.1f}, '
        f'SCtx>={info.get("stop_ctx_stop_thr", 0.0):.1f}, '
        f'TLCtx>={info.get("stop_ctx_tl_thr", 0.0):.1f}, '
        f'YShare>={info.get("min_yield_ctx_share", 0.0)*100:.0f}%'
    )
    R.p(
        f'  Minimos duros: StopCtx>={info.get("min_stop_ratio_total", 0.0)*100:.2f}%, '
        f'StopTicks>={info.get("min_stop_ticks_abs", 0.0):.1f}, '
        f'YieldTot>={info.get("min_yield_ratio_total", 0.0)*100:.2f}%, '
        f'YieldTicks>={info.get("min_yield_ticks_abs", 0.0):.1f}, '
        f'Val>={info.get("min_validation_sec", 0.0):.2f}s, '
        f'Time>={info.get("time_thr", 0.0):.2f}s, '
        f'YieldVal>={info.get("yield_val_thr", 0.0):.2f}s, '
        f'StopVal>={info.get("stop_val_thr", 0.0):.2f}s'
    )
    R.p(
        f'  Scores: candidato>={info.get("score_candidate_thr", 0.0):.2f}, '
        f'vigilancia>={info.get("score_watch_thr", 0.0):.2f}'
    )
    R.p(
        f'  Candidatos fuertes:       {info.get("candidate_count", 0)} '
        f'({info.get("candidate_pct_timefinished", 0.0):.2f}% de TIME_FINISHED)'
    )
    R.p(
        f'  Candidatos vigilancia:    {info.get("watch_count", 0)} '
        f'({info.get("watch_pct_timefinished", 0.0):.2f}% de TIME_FINISHED)'
    )

    candidates = info.get('candidates', [])
    if candidates:
        R.p(f'  Top candidatos (score compuesto):')
        first_col = 'Evento' if freerun else 'Gen'
        hdr = (
            f'  {first_col:>6s} | {"Car":>16s} | {"Spawn":>15s} | {"Fit":>10s} | {"t":>6s} | '
            f'{"Fit/s":>9s} | {"StopCtx%":>9s} | {"YShare%":>8s} | {"SShare%":>8s} | {"TShare%":>8s} | {"StopTk":>7s} | {"YVal":>6s} | {"SVal":>6s} | {"GBr":>6s} | {"Score":>6s} | {"Sev":>5s}'
        )
        R.p(hdr)
        R.p(f'  {"-"*(len(hdr)-2)}')
        for idx, c in enumerate(candidates[:TOP_ROWS], start=1):
            first_value = idx if freerun else c.get("gen", 0)
            R.p(
                f'  {first_value:>6d} | {c.get("car", "")[:16]:>16s} | {c.get("spawn", "").replace("TargetPoint", "TP"):>15s} | '
                f'{c.get("fit", 0.0):>10.2f} | {c.get("time", 0.0):>5.1f}s | {c.get("fit_per_sec", 0.0):>9.3f} | '
                f'{c.get("stop_ctx_pct", 0.0):>8.2f}% | {c.get("stop_ctx_yield_share", 0.0)*100.0:>7.2f}% | {c.get("stop_ctx_stop_share", 0.0)*100.0:>7.2f}% | {c.get("stop_ctx_tl_share", 0.0)*100.0:>7.2f}% | {c.get("stop_ctx_ticks", 0.0):>7.1f} | '
                f'{c.get("yield_val_t", 0.0):>6.1f} | {c.get("stop_val_t", 0.0):>6.1f} | {c.get("brake_grace", 0.0):>6.2f} | '
                f'{c.get("score", 0.0):>6.2f} | {c.get("severity", ""):>5s}'
            )

    spawns = info.get('spawns', [])
    if spawns:
        R.p(f'\n  Spawns con mas sospecha de atasco en ceda (candidatos fuertes):')
        hdr_sp = f'  {"Spawn":>15s} | {"TF":>5s} | {"Cand":>5s} | {"Watch":>6s} | {"Cand/TF%":>8s} | {"FitMed":>10s} | {"StopCtxP50":>11s} | {"tP50":>7s} | {"ScoreP50":>9s}'
        R.p(hdr_sp)
        R.p(f'  {"-"*(len(hdr_sp)-2)}')
        for s in spawns[:TOP_ROWS]:
            R.p(
                f'  {s.get("spawn", "").replace("TargetPoint", "TP"):>15s} | {s.get("tf_n", 0):>5d} | {s.get("n", 0):>5d} | {s.get("watch_n", 0):>6d} | '
                f'{s.get("cand_pct_tf", 0.0):>7.1f}% | {s.get("fit_med", 0.0):>10.2f} | {s.get("stop_ctx_p50", 0.0):>10.2f}% | '
                f'{s.get("time_p50", 0.0):>6.1f}s | {s.get("score_med", 0.0):>9.2f}'
            )

    gens = [] if freerun else info.get('gens', [])
    if gens:
        R.p(f'\n  Generaciones con mas sospecha de atasco en ceda:')
        hdr_g = f'  {"Gen":>5s} | {"TF":>5s} | {"Cand":>5s} | {"Watch":>6s} | {"Cand/TF%":>8s} | {"ScoreP50":>9s}'
        R.p(hdr_g)
        R.p(f'  {"-"*(len(hdr_g)-2)}')
        for g in gens[:min(TOP_ROWS, len(gens))]:
            R.p(
                f'  {g.get("gen", 0):>5d} | {g.get("tf_n", 0):>5d} | {g.get("n", 0):>5d} | {g.get("watch_n", 0):>6d} | '
                f'{g.get("cand_pct_tf", 0.0):>7.1f}% | {g.get("score_med", 0.0):>9.2f}'
            )
    elif freerun and info.get('gens', []):
        R.p('  Eje generacional omitido: en FreeRun gen 0/1 no representa evolucion.')

def report_stop_stuck_detection(R, info, freerun=False):
    if not info:
        return

    R.p(f'\n-- Deteccion de posible atasco en STOP (TIME_FINISHED) --')
    total_rows = info.get('total_rows', 0)
    tf_rows = info.get('timefinished_rows', 0)
    R.p(f'  TIME_FINISHED:            {tf_rows}/{total_rows} ({info.get("timefinished_pct", 0.0):.2f}%)')

    if tf_rows == 0:
        R.p('  No hay registros TIME_FINISHED en este subconjunto.')
        return

    R.p(
        f'  Umbrales dinamicos: Fit<={info.get("fit_thr", 0.0):.2f}, '
        f'Fit/s<={info.get("fitps_thr", 0.0):.3f}, '
        f'StopCtx>={info.get("stop_ctx_thr", 0.0)*100:.2f}%, '
        f'StopTicks>={info.get("stop_ticks_thr", 0.0):.1f}, '
        f'StopOnlyTk>={info.get("stop_ctx_stop_thr", 0.0):.1f}, '
        f'StopOnly>={info.get("stop_ctx_stop_ratio_thr", 0.0)*100:.2f}%, '
        f'SShare>={info.get("min_stop_ctx_share", 0.0)*100:.0f}%, '
        f'Lazy>={info.get("lazy_thr", 0.0):.2f}'
    )
    R.p(
        f'  Reanudacion minima: OutCtx>={info.get("min_resume_ratio", 0.0)*100:.1f}%, '
        f'CmdOut>={info.get("min_resume_cmd_ratio", 0.0)*100:.1f}%'
    )
    R.p(
        f'  Minimos duros: StopCtx>={info.get("min_stop_ctx_ratio_total", 0.0)*100:.2f}%, '
        f'StopTicks>={info.get("min_stop_ctx_ticks_abs", 0.0):.1f}, '
        f'StopOnly>={info.get("min_stop_ratio_total", 0.0)*100:.2f}%, '
        f'StopOnlyTicks>={info.get("min_stop_ticks_abs", 0.0):.1f}, '
        f'Val>={info.get("min_validation_sec", 0.0):.2f}s, '
        f'Time>={info.get("time_thr", 0.0):.2f}s, '
        f'StopVal>={info.get("stop_val_thr", 0.0):.2f}s'
    )
    R.p(
        f'  Scores: candidato>={info.get("score_candidate_thr", 0.0):.2f}, '
        f'vigilancia>={info.get("score_watch_thr", 0.0):.2f}'
    )
    R.p(
        f'  Candidatos fuertes:       {info.get("candidate_count", 0)} '
        f'({info.get("candidate_pct_timefinished", 0.0):.2f}% de TIME_FINISHED)'
    )
    R.p(
        f'  Candidatos vigilancia:    {info.get("watch_count", 0)} '
        f'({info.get("watch_pct_timefinished", 0.0):.2f}% de TIME_FINISHED)'
    )

    cause_counts = info.get('cause_counts', {})
    if cause_counts:
        total_tf = info.get('timefinished_rows', 0)
        parts = []
        for name, cnt in sorted(cause_counts.items(), key=lambda kv: kv[1], reverse=True):
            parts.append(f'{name}={cnt} ({sdiv(cnt*100.0, total_tf):.1f}%)')
        R.p(f'  Causas estimadas (TF):     {", ".join(parts)}')
    cand_cause_counts = info.get('candidate_cause_counts', {})
    if cand_cause_counts:
        total_c = max(info.get('candidate_count', 0), 1)
        parts = []
        for name, cnt in sorted(cand_cause_counts.items(), key=lambda kv: kv[1], reverse=True):
            parts.append(f'{name}={cnt} ({sdiv(cnt*100.0, total_c):.1f}%)')
        R.p(f'  Causas estimadas (Cand):   {", ".join(parts)}')

    candidates = info.get('candidates', [])
    if candidates:
        R.p(f'  Top candidatos (score compuesto):')
        first_col = 'Evento' if freerun else 'Gen'
        hdr = (
            f'  {first_col:>6s} | {"Car":>16s} | {"Spawn":>15s} | {"Fit":>10s} | {"t":>6s} | '
            f'{"Fit/s":>9s} | {"StopCtx%":>9s} | {"SShare%":>8s} | {"YShare%":>8s} | {"TShare%":>8s} | '
            f'{"StopTk":>7s} | {"Out%":>6s} | {"CmdOut%":>7s} | {"SVal":>6s} | {"Score":>6s} | {"Cause":>9s} | {"Sev":>5s}'
        )
        R.p(hdr)
        R.p(f'  {"-"*(len(hdr)-2)}')
        for idx, c in enumerate(candidates[:TOP_ROWS], start=1):
            first_value = idx if freerun else c.get("gen", 0)
            R.p(
                f'  {first_value:>6d} | {c.get("car", "")[:16]:>16s} | {c.get("spawn", "").replace("TargetPoint", "TP"):>15s} | '
                f'{c.get("fit", 0.0):>10.2f} | {c.get("time", 0.0):>5.1f}s | {c.get("fit_per_sec", 0.0):>9.3f} | '
                f'{c.get("stop_ctx_pct", 0.0):>8.2f}% | {c.get("stop_ctx_stop_share", 0.0)*100.0:>7.2f}% | {c.get("stop_ctx_yield_share", 0.0)*100.0:>7.2f}% | '
                f'{c.get("stop_ctx_tl_share", 0.0)*100.0:>7.2f}% | {c.get("stop_ctx_stop_ticks", 0.0):>7.1f} | '
                f'{c.get("out_ctx_ratio", 0.0)*100.0:>6.1f}% | {c.get("out_cmd_ratio", 0.0)*100.0:>7.1f}% | {c.get("stop_val_t", 0.0):>6.1f} | '
                f'{c.get("score", 0.0):>6.2f} | {c.get("cause_primary", ""):>9s} | {c.get("severity", ""):>5s}'
            )

    spawns = info.get('spawns', [])
    if spawns:
        R.p(f'\n  Spawns con mas sospecha de atasco en stop (candidatos fuertes):')
        hdr_sp = f'  {"Spawn":>15s} | {"TF":>5s} | {"Cand":>5s} | {"Watch":>6s} | {"Cand/TF%":>8s} | {"FitMed":>10s} | {"StopCtxP50":>11s} | {"tP50":>7s} | {"ScoreP50":>9s}'
        R.p(hdr_sp)
        R.p(f'  {"-"*(len(hdr_sp)-2)}')
        for s in spawns[:TOP_ROWS]:
            R.p(
                f'  {s.get("spawn", "").replace("TargetPoint", "TP"):>15s} | {s.get("tf_n", 0):>5d} | {s.get("n", 0):>5d} | {s.get("watch_n", 0):>6d} | '
                f'{s.get("cand_pct_tf", 0.0):>7.1f}% | {s.get("fit_med", 0.0):>10.2f} | {s.get("stop_ctx_p50", 0.0):>10.2f}% | '
                f'{s.get("time_p50", 0.0):>6.1f}s | {s.get("score_med", 0.0):>9.2f}'
            )

    gens = [] if freerun else info.get('gens', [])
    if gens:
        R.p(f'\n  Generaciones con mas sospecha de atasco en stop:')
        hdr_g = f'  {"Gen":>5s} | {"TF":>5s} | {"Cand":>5s} | {"Watch":>6s} | {"Cand/TF%":>8s} | {"ScoreP50":>9s}'
        R.p(hdr_g)
        R.p(f'  {"-"*(len(hdr_g)-2)}')
        for g in gens[:min(TOP_ROWS, len(gens))]:
            R.p(
                f'  {g.get("gen", 0):>5d} | {g.get("tf_n", 0):>5d} | {g.get("n", 0):>5d} | {g.get("watch_n", 0):>6d} | '
                f'{g.get("cand_pct_tf", 0.0):>7.1f}% | {g.get("score_med", 0.0):>9.2f}'
            )
    elif freerun and info.get('gens', []):
        R.p('  Eje generacional omitido: en FreeRun gen 0/1 no representa evolucion.')

def report_summary_deep(R, rows):
    if not rows:
        return
    if is_freerun_analysis(summary_rows=rows):
        R.p(f'\n-- Summary Profundo --')
        R.p('  Omitido en FreeRun: el Summary reconstruido es un snapshot, no una serie generacional.')
        return

    gens = [r['gen'] for r in rows]
    bests = [r['best'] for r in rows]
    means = [r['mean'] for r in rows]
    times = [r['time'] for r in rows]

    R.p(f'\n-- Diagnostico de Tendencia y Volatilidad --')
    R.p(f'  BestFit std/cv:   {stdev(bests):.4f} / {coef_var(bests)*100:.2f}%')
    R.p(f'  MeanFit std/cv:   {stdev(means):.4f} / {coef_var(means)*100:.2f}%')
    R.p(f'  Tiempo std/cv:    {stdev(times):.4f} / {coef_var(times)*100:.2f}%')
    slope_best = trend_slope(gens, bests)
    slope_mean = trend_slope(gens, means)
    slope_time = trend_slope(gens, times)
    R.p(f'  Pendiente BestFit: {slope_best:+.6f}/gen ({slope_best*100:+.4f}/100gens)')
    R.p(f'  Pendiente MeanFit: {slope_mean:+.6f}/gen ({slope_mean*100:+.4f}/100gens)')
    R.p(f'  Pendiente Tiempo:  {slope_time:+.6f}/gen ({slope_time*100:+.4f}/100gens)')

    # Rachas
    no_imp = 0
    cur_no_imp = 0
    running_best = -1e30
    for v in bests:
        if v > running_best:
            running_best = v
            cur_no_imp = 0
        else:
            cur_no_imp += 1
            if cur_no_imp > no_imp:
                no_imp = cur_no_imp

    neg_streak = longest_streak(means, lambda x: x < 0)
    pos_streak = longest_streak(means, lambda x: x >= 0)
    R.p(f'  Racha sin nuevo BestFit: {no_imp} gens')
    R.p(f'  Racha MeanFit negativo:  {neg_streak} gens')
    R.p(f'  Racha MeanFit no-neg:    {pos_streak} gens')

    # Saltos entre generaciones
    if len(rows) >= 2:
        jumps = []
        for i in range(1, len(rows)):
            prev = rows[i - 1]
            cur = rows[i]
            d_mean = cur['mean'] - prev['mean']
            d_best = cur['best'] - prev['best']
            d_time = cur['time'] - prev['time']
            jumps.append((abs(d_mean), prev['gen'], cur['gen'], d_mean, d_best, d_time))
        jumps.sort(key=lambda t: t[0], reverse=True)

        R.p(f'\n-- Saltos Mas Grandes Entre Gens (por |delta MeanFit|) --')
        hdr = f'  {"GenA->GenB":>14s} | {"dMean":>11s} | {"dBest":>11s} | {"dTime":>9s}'
        R.p(hdr)
        R.p(f'  {"-"*(len(hdr)-2)}')
        for _, ga, gb, dm, db, dt in jumps[:TOP_ROWS]:
            R.p(f'  {ga:>5d}->{gb:<5d} | {dm:>+11.4f} | {db:>+11.4f} | {dt:>+8.3f}s')

    # Top / Bottom generaciones
    top_n = min(TOP_ROWS, len(rows))
    R.p(f'\n-- Bottom {top_n} Generaciones por MeanFit --')
    for r in sorted(rows, key=lambda x: x['mean'])[:top_n]:
        R.p(
            f'  Gen {r["gen"]:>5d}: Mean={r["mean"]:>10.4f} '
            f'Best={r["best"]:>10.4f} t={r["time"]:>6.2f}s '
            f'BestDeath={r.get("best_death","")} PopDeath={r.get("pop_death","")}'
        )

    R.p(f'\n-- Top {top_n} Generaciones por MeanFit --')
    for r in sorted(rows, key=lambda x: -x['mean'])[:top_n]:
        R.p(
            f'  Gen {r["gen"]:>5d}: Mean={r["mean"]:>10.4f} '
            f'Best={r["best"]:>10.4f} t={r["time"]:>6.2f}s '
            f'BestDeath={r.get("best_death","")} PopDeath={r.get("pop_death","")}'
        )

    # KPI test extendido
    kpi_rows = [r for r in rows if 'success_rate' in r]
    if kpi_rows:
        succ = [r.get('success_rate', 0.0) for r in kpi_rows]
        fail = [r.get('fail_rate', 0.0) for r in kpi_rows]
        hard = [r.get('fail_hard_count', 0) for r in kpi_rows]
        early = [r.get('fail_early_count', 0) for r in kpi_rows]
        coll = [r.get('fail_collision_count', 0) for r in kpi_rows]

        best_s = max(kpi_rows, key=lambda r: r.get('success_rate', 0.0))
        worst_s = min(kpi_rows, key=lambda r: r.get('success_rate', 0.0))

        R.p(f'\n-- KPI Test: Diagnostico Detallado --')
        R.p(f'  SuccessRate std/cv: {stdev(succ):.4f} / {coef_var(succ)*100:.2f}%')
        R.p(f'  FailRate std/cv:    {stdev(fail):.4f} / {coef_var(fail)*100:.2f}%')
        R.p(f'  Mejor SuccessRate:  Gen {best_s["gen"]} -> {best_s.get("success_rate",0.0):.2f}%')
        R.p(f'  Peor SuccessRate:   Gen {worst_s["gen"]} -> {worst_s.get("success_rate",0.0):.2f}%')
        R.p(f'  Fallo duro medio:   {mean(hard):.2f} coches/gen')
        R.p(f'  Fallo temprano med: {mean(early):.2f} coches/gen')
        R.p(f'  Fallo colision med: {mean(coll):.2f} coches/gen')

def report_debug_deep(R, dbg, yield_stuck_info=None, stop_stuck_info=None):
    if not dbg:
        return

    nd = len(dbg)
    freerun = is_freerun_analysis(debug_rows=dbg)
    by_spawn = defaultdict(list)
    by_gen = defaultdict(list)
    by_death = defaultdict(list)
    by_family = defaultdict(list)
    by_family_detail = defaultdict(list)

    missing_spawn = 0
    missing_death = 0
    bad_ticks = 0
    neg_time = 0

    for r in dbg:
        by_spawn[r['spawn']].append(r)
        by_gen[r['gen']].append(r)
        by_death[r['death']].append(r)
        by_family[r.get('death_family', death_family(r['death']))].append(r)
        by_family_detail[r.get('death_family_detail', death_family_detail_for_row(r))].append(r)
        if not r['spawn']:
            missing_spawn += 1
        if not r['death']:
            missing_death += 1
        if r.get('t_norm', 0) > r.get('t_tot', 0):
            bad_ticks += 1
        if r.get('time', 0) < 0:
            neg_time += 1

    R.p(f'\n-- Calidad de Registros Debug --')
    R.p(f'  Registros totales:         {nd}')
    R.p(f'  Spawn vacio:               {missing_spawn} ({sdiv(missing_spawn*100, nd):.2f}%)')
    R.p(f'  DeathReason vacio:         {missing_death} ({sdiv(missing_death*100, nd):.2f}%)')
    R.p(f'  TicksNormal > TicksTotal:  {bad_ticks} ({sdiv(bad_ticks*100, nd):.2f}%)')
    R.p(f'  Tiempo negativo:           {neg_time} ({sdiv(neg_time*100, nd):.2f}%)')

    train_rows, test_rows, unknown_rows, has_flag = split_debug_by_phase(dbg)
    if has_flag:
        R.p(f'  Fase TRAIN/TEST/UNK:       {len(train_rows)} / {len(test_rows)} / {len(unknown_rows)}')

    yield_stuck = yield_stuck_info or detect_yield_stuck_candidates(dbg)
    stop_stuck = stop_stuck_info or detect_stop_stuck_candidates(dbg)
    report_yield_stuck_detection(R, yield_stuck, freerun=freerun)
    report_stop_stuck_detection(R, stop_stuck, freerun=freerun)

    # Analisis LAZY
    lazy_rows = [r for r in dbg if is_lazy_reason(r.get('death', ''))]
    non_lazy = [r for r in dbg if not is_lazy_reason(r.get('death', ''))]
    R.p(f'\n-- Diagnostico Especifico LAZY --')
    R.p(f'  LAZY total: {len(lazy_rows)}/{nd} ({sdiv(len(lazy_rows)*100, nd):.2f}%)')

    if lazy_rows:
        lazy_stop0_n = sum(1 for r in lazy_rows if r.get('t_stop_ctx', 0.0) <= 0.0)
        lazy_stop_low_n = sum(
            1 for r in lazy_rows
            if sdiv(r.get('t_stop_ctx', 0.0), max(r.get('t_tot', 0.0), 1.0)) < 0.01
        )
        lazy_stop_mid_n = sum(
            1 for r in lazy_rows
            if 0.01 <= sdiv(r.get('t_stop_ctx', 0.0), max(r.get('t_tot', 0.0), 1.0)) < 0.10
        )
        lazy_stop_hi_n = sum(
            1 for r in lazy_rows
            if sdiv(r.get('t_stop_ctx', 0.0), max(r.get('t_tot', 0.0), 1.0)) >= 0.10
        )
        R.p(f'  Contexto stop/semaforo dentro de LAZY:')
        R.p(
            f'    StopTicks==0: {lazy_stop0_n}/{len(lazy_rows)} '
            f'({sdiv(lazy_stop0_n*100.0, len(lazy_rows)):.1f}%)'
        )
        R.p(
            f'    StopCtx <1% / 1-10% / >=10%: '
            f'{lazy_stop_low_n}/{lazy_stop_mid_n}/{lazy_stop_hi_n}'
        )

        lazy_by_spawn = Counter(r['spawn'] for r in lazy_rows)
        R.p(f'  Top spawns con LAZY (count y ratio interno):')
        hdr = f'  {"Spawn":>15s} | {"LazyN":>6s} | {"SpawnN":>7s} | {"Lazy%Spawn":>10s} | {"Stop0%":>7s} | {"Stop>=10%":>9s} | {"FitMedLazy":>11s} | {"tMedLazy":>8s}'
        R.p(hdr)
        R.p(f'  {"-"*(len(hdr)-2)}')
        for sp, cnt in lazy_by_spawn.most_common(TOP_ROWS):
            all_sp = by_spawn.get(sp, [])
            lazy_sp = [r for r in all_sp if is_lazy_reason(r.get('death', ''))]
            fits_lazy = [r['fit'] for r in lazy_sp]
            time_lazy = [r['time'] for r in lazy_sp]
            stop0_n = sum(1 for r in lazy_sp if r.get('t_stop_ctx', 0.0) <= 0.0)
            stop_hi_n = sum(
                1 for r in lazy_sp
                if sdiv(r.get('t_stop_ctx', 0.0), max(r.get('t_tot', 0.0), 1.0)) >= 0.10
            )
            R.p(
                f'  {sp.replace("TargetPoint","TP"):>15s} | {cnt:>6d} | {len(all_sp):>7d} | '
                f'{sdiv(cnt*100, len(all_sp)):>9.1f}% | {sdiv(stop0_n*100.0, len(lazy_sp)):>6.1f}% | '
                f'{sdiv(stop_hi_n*100.0, len(lazy_sp)):>8.1f}% | {pctl(fits_lazy, 50):>11.2f} | {pctl(time_lazy, 50):>7.2f}s'
            )

        if not freerun:
            lazy_by_gen = Counter(r['gen'] for r in lazy_rows)
            R.p(f'\n  Gens con mas LAZY:')
            for g, cnt in lazy_by_gen.most_common(min(TOP_ROWS, len(lazy_by_gen))):
                gn = len(by_gen[g])
                R.p(f'    Gen {g:>5d}: {cnt:>3d}/{gn} ({sdiv(cnt*100, gn):.1f}%)')

        if non_lazy:
            R.p(f'\n  Comparativa LAZY vs no-LAZY:')
            R.p(f'    Fit medio:       {mean([r["fit"] for r in lazy_rows]):.2f} vs {mean([r["fit"] for r in non_lazy]):.2f}')
            R.p(f'    Tiempo medio:    {mean([r["time"] for r in lazy_rows]):.2f}s vs {mean([r["time"] for r in non_lazy]):.2f}s')
            R.p(f'    PenMuerte media: {mean([r["pen_m"] for r in lazy_rows]):.2f} vs {mean([r["pen_m"] for r in non_lazy]):.2f}')
            R.p(f'    PenVel media:    {mean([r["pen_v"] for r in lazy_rows]):.2f} vs {mean([r["pen_v"] for r in non_lazy]):.2f}')
            R.p(f'    PenLazy media:   {mean([r.get("pen_lazy", 0.0) for r in lazy_rows]):.2f} vs {mean([r.get("pen_lazy", 0.0) for r in non_lazy]):.2f}')
            R.p(f'    PenSteerApp med: {mean([r.get("pen_steer_app", 0.0) for r in lazy_rows]):.2f} vs {mean([r.get("pen_steer_app", 0.0) for r in non_lazy]):.2f}')
            R.p(f'    PenRev media:    {mean([r.get("pen_rev", 0.0) for r in lazy_rows]):.2f} vs {mean([r.get("pen_rev", 0.0) for r in non_lazy]):.2f}')
            R.p(f'    ThrGrace media:  {mean([r.get("thr_grace", 0.0) for r in lazy_rows]):.2f} vs {mean([r.get("thr_grace", 0.0) for r in non_lazy]):.2f}')
            R.p(f'    BrGrace media:   {mean([r.get("brake_grace", 0.0) for r in lazy_rows]):.2f} vs {mean([r.get("brake_grace", 0.0) for r in non_lazy]):.2f}')
            R.p(f'    NetNormal medio: {mean([r["net"] for r in lazy_rows]):.2f} vs {mean([r["net"] for r in non_lazy]):.2f}')

        total_lazy_pen = sum(r.get('pen_lazy', 0.0) for r in dbg)
        spawn_lazy_stats = []
        for sp, rows_sp in by_spawn.items():
            if not sp:
                continue
            nsp = len(rows_sp)
            lazy_n = sum(1 for r in rows_sp if is_lazy_reason(r.get('death', '')))
            pen_lazy_vals = [r.get('pen_lazy', 0.0) for r in rows_sp]
            pen_lazy_sum = sum(pen_lazy_vals)
            spawn_lazy_stats.append({
                'spawn': sp,
                'n': nsp,
                'lazy_n': lazy_n,
                'lazy_pct': sdiv(lazy_n * 100.0, nsp),
                'pen_lazy_med': mean(pen_lazy_vals),
                'pen_lazy_p90': pctl(pen_lazy_vals, 90),
                'pen_lazy_share': sdiv(pen_lazy_sum * 100.0, total_lazy_pen),
            })

        if spawn_lazy_stats:
            R.p(f'\n-- Penalty_Lazy por Spawn (top dinamico) --')
            hdr_lz_sp = f'  {"Spawn":>15s} | {"N":>6s} | {"LazyN":>6s} | {"Lazy%":>7s} | {"PenLzMed":>9s} | {"PenLzP90":>9s} | {"Contrib%":>9s}'
            R.p(hdr_lz_sp)
            R.p(f'  {"-"*(len(hdr_lz_sp)-2)}')
            for st in sorted(spawn_lazy_stats, key=lambda x: (x['pen_lazy_med'], x['lazy_pct']), reverse=True)[:TOP_ROWS]:
                R.p(
                    f'  {st["spawn"].replace("TargetPoint","TP"):>15s} | {st["n"]:>6d} | {st["lazy_n"]:>6d} | {st["lazy_pct"]:>6.1f}% | '
                    f'{st["pen_lazy_med"]:>9.2f} | {st["pen_lazy_p90"]:>9.2f} | {st["pen_lazy_share"]:>8.2f}%'
                )

        death_lazy_stats = []
        for dr, rows_dr in by_death.items():
            if not dr:
                continue
            pen_lazy_vals = [r.get('pen_lazy', 0.0) for r in rows_dr]
            pen_lazy_sum = sum(pen_lazy_vals)
            death_lazy_stats.append({
                'death': dr,
                'n': len(rows_dr),
                'pen_lazy_med': mean(pen_lazy_vals),
                'pen_lazy_p90': pctl(pen_lazy_vals, 90),
                'pen_lazy_share': sdiv(pen_lazy_sum * 100.0, total_lazy_pen),
            })

        if death_lazy_stats:
            R.p(f'\n-- Penalty_Lazy por Razon de Muerte --')
            hdr_lz_dr = f'  {"DeathReason":>35s} | {"N":>6s} | {"PenLzMed":>9s} | {"PenLzP90":>9s} | {"Contrib%":>9s}'
            R.p(hdr_lz_dr)
            R.p(f'  {"-"*(len(hdr_lz_dr)-2)}')
            for st in sorted(death_lazy_stats, key=lambda x: (x['pen_lazy_med'], x['n']), reverse=True)[:TOP_ROWS]:
                R.p(
                    f'  {st["death"]:>35s} | {st["n"]:>6d} | {st["pen_lazy_med"]:>9.2f} | '
                    f'{st["pen_lazy_p90"]:>9.2f} | {st["pen_lazy_share"]:>8.2f}%'
                )

    if (
        debug_field_available(dbg, 'yield_free_passes')
        or debug_field_available(dbg, 'crossing_blocked_t')
        or debug_field_available(dbg, 'first_steer_release_ticks')
        or debug_field_available(dbg, 'steer_app_wrong')
        or debug_field_available(dbg, 'front_obst_death')
    ):
        R.p(f'\n-- Diagnostico 30/06: Cedas, Cruce, Release y SteerApproach --')
        yield_free_total = sum(r.get('yield_free_passes', 0.0) for r in dbg)
        yield_done_total = sum(r.get('yield_done_n', 0.0) for r in dbg)
        crossing_total = sum(r.get('crossing_blocked_t', 0.0) for r in dbg)
        crossing_rows = [r for r in dbg if r.get('crossing_blocked_t', 0.0) > 0.0]
        release_vals = metric_values(dbg, 'first_steer_release_ticks')
        speed_vals = metric_values(dbg, 'yield_validation_speed')
        front_vals = metric_values(dbg, 'front_obst_death')
        wrong_share_vals = [v * 100.0 for v in metric_values(dbg, 'steer_app_wrong_share')]
        R.p(f'  YieldFreePasses / YieldsCompleted: {yield_free_total:.0f} / {yield_done_total:.0f}')
        if debug_field_available(dbg, 'yield_validation_speed'):
            R.p(f'  SpeedAtYieldValidation exp.:      media={mean(speed_vals):.2f}, P50={pctl(speed_vals, 50):.2f}, P90={pctl(speed_vals, 90):.2f}, N={len(speed_vals)}')
        if debug_field_available(dbg, 'crossing_blocked_t'):
            R.p(f'  TimeBlockedAtCrossing:            total={crossing_total:.2f}s, coches={len(crossing_rows)}/{nd} ({sdiv(len(crossing_rows)*100.0, nd):.2f}%)')
            R.p(
                f'  Blocked/life-sec exp.:            media={mean(metric_values(dbg, "crossing_blocked_per_life_sec")):.5f}, '
                f'Blocked/stop-tick exp.={mean(metric_values(dbg, "crossing_blocked_per_stop_tick")):.5f}'
            )
        if debug_field_available(dbg, 'first_steer_release_ticks'):
            R.p(f'  FirstSteerAfterReleaseTicks exp.: media={mean(release_vals):.2f}, P50={pctl(release_vals, 50):.2f}, P90={pctl(release_vals, 90):.2f}, N={len(release_vals)}')
        if debug_field_available(dbg, 'front_obst_death'):
            R.p(f'  FrontObstAtDeath exp.:            media={mean(front_vals):.4f}, P50={pctl(front_vals, 50):.4f}, N={len(front_vals)}')
        if debug_field_available(dbg, 'steer_app_wrong') or debug_field_available(dbg, 'steer_app_right'):
            wrong_total = sum(r.get('steer_app_wrong', 0.0) for r in dbg)
            right_total = sum(r.get('steer_app_right', 0.0) for r in dbg)
            R.p(f'  SteerApproach wrong/right:        {wrong_total:.2f} / {right_total:.2f} (wrong share={sdiv(wrong_total*100.0, wrong_total+right_total):.2f}%)')
            R.p(f'  WrongShare exp. P50/P90:          {pctl(wrong_share_vals, 50):.2f}% / {pctl(wrong_share_vals, 90):.2f}% (N={len(wrong_share_vals)})')

        stop_violation_detail = summarize_stop_violation_subtypes(dbg)
        if stop_violation_detail:
            R.p(
                '  StopViolation subtipos:           '
                f'EXIT={stop_violation_detail.get("EXIT", 0)}, '
                f'TIMEOUT={stop_violation_detail.get("TIMEOUT", 0)}, '
                f'GENERIC={stop_violation_detail.get("GENERIC", 0)}'
            )

        if crossing_rows:
            blocked_by_gen = []
            if not freerun:
                for g, rows_gen in by_gen.items():
                    total_gen = sum(r.get('crossing_blocked_t', 0.0) for r in rows_gen)
                    if total_gen > 0.0:
                        blocked_by_gen.append((total_gen, g, len(rows_gen), mean([r.get('fit', 0.0) for r in rows_gen])))
            if blocked_by_gen:
                R.p('  Top generaciones por bloqueo de cruce:')
                for total_gen, g, ngen, fit_med in sorted(blocked_by_gen, reverse=True)[:min(TOP_ROWS, 10)]:
                    R.p(f'    Gen {g:>5d}: blocked={total_gen:.2f}s, coches={ngen}, fitMed={fit_med:.1f}')
            blocked_by_spawn = []
            for sp, rows_sp in by_spawn.items():
                total_sp = sum(r.get('crossing_blocked_t', 0.0) for r in rows_sp)
                if total_sp > 0.0:
                    affected_sp = sum(1 for r in rows_sp if r.get('crossing_blocked_t', 0.0) > 0.0)
                    blocked_by_spawn.append((total_sp, affected_sp, sp, len(rows_sp), mean([r.get('fit', 0.0) for r in rows_sp])))
            if blocked_by_spawn:
                R.p('  Top spawns por bloqueo de cruce:')
                for total_sp, affected_sp, sp, nsp, fit_med in sorted(blocked_by_spawn, reverse=True)[:min(TOP_ROWS, 10)]:
                    R.p(
                        f'    {sp.replace("TargetPoint","TP"):>15s}: blocked={total_sp:.2f}s, '
                        f'coches={affected_sp}/{nsp}, fitMed={fit_med:.1f}'
                    )

    if debug_field_available(dbg, 'car_overlaps'):
        overlap_total = sum(r.get('car_overlaps', 0.0) for r in dbg)
        overlap_rows = [r for r in dbg if r.get('car_overlaps', 0.0) > 0.0]
        R.p(f'\n-- Interaccion entre Coches (NumCarOverlaps, 26/06+) --')
        R.p(f'  Eventos totales:           {overlap_total:.0f}')
        R.p(f'  Coches afectados:          {len(overlap_rows)}/{nd} ({sdiv(len(overlap_rows)*100.0, nd):.2f}%)')
        R.p(f'  Overlaps/coche medio:      {sdiv(overlap_total, nd):.4f}')
        if debug_field_available(dbg, 'car_overlap_pen_shadow'):
            shadow_total = sum(r.get('car_overlap_pen_shadow', 0.0) for r in dbg)
            shadow_vals = metric_values(dbg, 'car_overlap_shadow_per_overlap')
            R.p(f'  Shadow penalty total:      {shadow_total:.2f}')
            R.p(f'  Shadow/overlap exp.:       {mean(shadow_vals):.4f} (N={len(shadow_vals)})')
        if debug_field_available(dbg, 'car_overlap_penalty'):
            overlap_pen_total = sum(r.get('car_overlap_penalty', 0.0) for r in dbg)
            overlap_pen_vals = metric_values(dbg, 'car_overlap_penalty_per_overlap')
            R.p(f'  Penalty real total:        {overlap_pen_total:.2f}')
            R.p(f'  Penalty real/overlap exp.: {mean(overlap_pen_vals):.4f} (N={len(overlap_pen_vals)})')
        collision_rows = [r for r in dbg if is_collision_reason(r.get('death', ''))]
        overlap_collision_rows = [r for r in collision_rows if r.get('car_overlaps', 0.0) > 0.0]
        overlap_noncollision_rows = [
            r for r in dbg
            if not is_collision_reason(r.get('death', '')) and r.get('car_overlaps', 0.0) > 0.0
        ]
        if collision_rows:
            R.p(
                f'  Solapes en muerte COLLISION: {len(overlap_collision_rows)}/{len(collision_rows)} coches, '
                f'eventos={sum(r.get("car_overlaps", 0.0) for r in overlap_collision_rows):.0f}'
            )
        if overlap_noncollision_rows:
            R.p(
                f'  Solapes sin muerte COLLISION: {len(overlap_noncollision_rows)} coches, '
                f'eventos={sum(r.get("car_overlaps", 0.0) for r in overlap_noncollision_rows):.0f}'
            )
            if debug_field_available(dbg, 'car_overlap_penalty'):
                R.p(
                    f'  Penalty solape sin COLLISION: '
                    f'{sum(r.get("car_overlap_penalty", 0.0) for r in overlap_noncollision_rows):.2f}'
                )
        if overlap_rows:
            R.p(f'  Overlaps/coche afectado:   {sdiv(overlap_total, len(overlap_rows)):.4f}')
            R.p(f'  Overlaps/s medio afectado: {mean([r.get("car_overlap_per_sec", 0.0) for r in overlap_rows]):.4f}')
            overlap_by_gen = []
            if not freerun:
                for g, rows_gen in by_gen.items():
                    total_gen = sum(r.get('car_overlaps', 0.0) for r in rows_gen)
                    if total_gen <= 0.0:
                        continue
                    affected_gen = sum(1 for r in rows_gen if r.get('car_overlaps', 0.0) > 0.0)
                    overlap_by_gen.append((total_gen, affected_gen, g, len(rows_gen), mean([r.get('fit', 0.0) for r in rows_gen])))
            if overlap_by_gen:
                R.p('  Top generaciones por solapes:')
                for total_gen, affected_gen, g, ngen, fit_med in sorted(overlap_by_gen, reverse=True)[:min(TOP_ROWS, 10)]:
                    R.p(
                        f'    Gen {g:>5d}: overlaps={total_gen:.0f}, coches={affected_gen}/{ngen} '
                        f'({sdiv(affected_gen*100.0, ngen):.1f}%), fitMed={fit_med:.1f}'
                    )
            overlap_by_spawn = []
            for sp, rows_sp in by_spawn.items():
                total_sp = sum(r.get('car_overlaps', 0.0) for r in rows_sp)
                if total_sp <= 0.0:
                    continue
                affected_sp = sum(1 for r in rows_sp if r.get('car_overlaps', 0.0) > 0.0)
                overlap_by_spawn.append((total_sp, affected_sp, sp, len(rows_sp), mean([r.get('fit', 0.0) for r in rows_sp])))
            if overlap_by_spawn:
                R.p('  Top spawns por solapes:')
                for total_sp, affected_sp, sp, nsp, fit_med in sorted(overlap_by_spawn, reverse=True)[:min(TOP_ROWS, 10)]:
                    R.p(
                        f'    {sp.replace("TargetPoint","TP"):>15s}: overlaps={total_sp:.0f}, '
                        f'coches={affected_sp}/{nsp}, fitMed={fit_med:.1f}'
                    )
            overlap_by_death = []
            for death, rows_dr in by_death.items():
                total_dr = sum(r.get('car_overlaps', 0.0) for r in rows_dr)
                if total_dr > 0.0:
                    overlap_by_death.append((total_dr, death, len(rows_dr)))
            if overlap_by_death:
                R.p('  Top razones de muerte con solapes:')
                for total_dr, death, ndr in sorted(overlap_by_death, reverse=True)[:min(TOP_ROWS, 10)]:
                    R.p(f'    {death:45s}: overlaps={total_dr:.0f}, coches={ndr}')
            car_bounds_overlap = infer_carindex_bounds(dbg)
            overlap_by_car_family = defaultdict(lambda: {'overlaps': 0.0, 'rows': 0, 'affected': 0})
            for r in dbg:
                fam = car_index_family_for_row(r, bounds=car_bounds_overlap)
                item = overlap_by_car_family[fam]
                item['rows'] += 1
                item['overlaps'] += r.get('car_overlaps', 0.0)
                if r.get('car_overlaps', 0.0) > 0.0:
                    item['affected'] += 1
            family_rows = [
                (v['overlaps'], v['affected'], fam, v['rows'])
                for fam, v in overlap_by_car_family.items()
                if v['overlaps'] > 0.0
            ]
            if family_rows:
                R.p('  Familias CarIndex con solapes:')
                for total_fam, affected_fam, fam, nfam in sorted(family_rows, reverse=True):
                    R.p(
                        f'    {fam:>16s}: overlaps={total_fam:.0f}, coches={affected_fam}/{nfam} '
                        f'({sdiv(affected_fam*100.0, nfam):.1f}%)'
                    )

    if debug_field_available(dbg, 'queue_wait_bonus'):
        queue_total = sum(r.get('queue_wait_bonus', 0.0) for r in dbg)
        queue_rows = [r for r in dbg if r.get('queue_wait_bonus', 0.0) > 0.0]
        R.p(f'\n-- Espera en Cola (QueueWaitBonus, 01/07+) --')
        R.p(f'  Bonus total:              {queue_total:.2f}')
        R.p(f'  Coches con bonus:         {len(queue_rows)}/{nd} ({sdiv(len(queue_rows)*100.0, nd):.2f}%)')
        R.p(f'  Bonus/coche global:       {sdiv(queue_total, nd):.4f}')
        if queue_rows:
            R.p(f'  Bonus/coche expuesto:     {sdiv(queue_total, len(queue_rows)):.4f}')
            R.p(f'  Bonus/s expuesto:         {mean(metric_values(dbg, "queue_wait_bonus_per_life_sec")):.4f}')
            queue_by_gen = []
            if not freerun:
                for g, rows_gen in by_gen.items():
                    total_gen = sum(r.get('queue_wait_bonus', 0.0) for r in rows_gen)
                    if total_gen > 0.0:
                        affected_gen = sum(1 for r in rows_gen if r.get('queue_wait_bonus', 0.0) > 0.0)
                        queue_by_gen.append((total_gen, affected_gen, g, len(rows_gen), mean([r.get('fit', 0.0) for r in rows_gen])))
            if queue_by_gen:
                R.p('  Top generaciones por QueueWaitBonus:')
                for total_gen, affected_gen, g, ngen, fit_med in sorted(queue_by_gen, reverse=True)[:min(TOP_ROWS, 10)]:
                    R.p(
                        f'    Gen {g:>5d}: bonus={total_gen:.2f}, coches={affected_gen}/{ngen} '
                        f'({sdiv(affected_gen*100.0, ngen):.1f}%), fitMed={fit_med:.1f}'
                    )
            queue_by_spawn = []
            for sp, rows_sp in by_spawn.items():
                total_sp = sum(r.get('queue_wait_bonus', 0.0) for r in rows_sp)
                if total_sp > 0.0:
                    affected_sp = sum(1 for r in rows_sp if r.get('queue_wait_bonus', 0.0) > 0.0)
                    queue_by_spawn.append((total_sp, affected_sp, sp, len(rows_sp), mean([r.get('fit', 0.0) for r in rows_sp])))
            if queue_by_spawn:
                R.p('  Top spawns por QueueWaitBonus:')
                for total_sp, affected_sp, sp, nsp, fit_med in sorted(queue_by_spawn, reverse=True)[:min(TOP_ROWS, 10)]:
                    R.p(
                        f'    {sp.replace("TargetPoint","TP"):>15s}: bonus={total_sp:.2f}, '
                        f'coches={affected_sp}/{nsp}, fitMed={fit_med:.1f}'
                    )
            queue_by_death = []
            for death, rows_dr in by_death.items():
                total_dr = sum(r.get('queue_wait_bonus', 0.0) for r in rows_dr)
                if total_dr > 0.0:
                    queue_by_death.append((total_dr, death, len(rows_dr)))
            if queue_by_death:
                R.p('  Top razones de muerte con QueueWaitBonus:')
                for total_dr, death, ndr in sorted(queue_by_death, reverse=True)[:min(TOP_ROWS, 10)]:
                    R.p(f'    {death:45s}: bonus={total_dr:.2f}, coches={ndr}')
        else:
            R.p('  Sin activaciones: la condicion de cola no aparecio en este lote.')

    # Familias de muerte
    R.p(f'\n-- Muertes por Familia (colisiones separadas) --')
    hdr = f'  {"Familia":>22s} | {"N":>7s} | {"Pct":>7s} | {"FitMed":>10s} | {"tMed":>7s} | {"PenM":>9s} | {"PenV":>9s} | {"PenSS":>9s}'
    R.p(hdr)
    R.p(f'  {"-"*(len(hdr)-2)}')
    for fam, rows_f in sorted(by_family_detail.items(), key=lambda kv: len(kv[1]), reverse=True):
        nf = len(rows_f)
        R.p(
            f'  {fam:>22s} | {nf:>7d} | {sdiv(nf*100, nd):>6.2f}% | {mean([r["fit"] for r in rows_f]):>10.2f} | '
            f'{mean([r["time"] for r in rows_f]):>6.2f}s | {mean([r["pen_m"] for r in rows_f]):>9.2f} | {mean([r["pen_v"] for r in rows_f]):>9.2f} | {mean([r.get("pen_swstop", 0.0) for r in rows_f]):>9.2f}'
        )

    car_fams = summarize_car_index_families(dbg)
    if car_fams:
        R.p(f'\n-- CarIndex / Genealogia --')
        hdr = f'  {"Familia":>12s} | {"N":>7s} | {"Pct":>7s} | {"IdxMed":>7s} | {"FitMed":>10s} | {"FitMean":>10s} | {"tMed":>7s} | {"YldV":>7s} | {"StpV":>7s}'
        R.p(hdr)
        R.p(f'  {"-"*(len(hdr)-2)}')
        for st in car_fams:
            R.p(
                f'  {st["family"]:>12s} | {st["n"]:>7d} | {st["pct"]:>6.2f}% | {st["car_index_med"]:>7.1f} | {st["fit_med"]:>10.2f} | {st["fit_mean"]:>10.2f} | '
                f'{st["time_med"]:>6.2f}s | {st["yield_val_med"]:>6.2f}s | {st["stop_val_med"]:>6.2f}s'
            )

    situational_items = [
        ('stop_bonus_per', 'StopBonus/Stop', 'stop_done_n'),
        ('yield_bonus_per', 'YieldBonus/Yield', 'yield_done_n'),
        ('stop_done_rate', 'StopDone/StopZone', 'stop_zones_n'),
        ('yield_done_rate', 'YieldDone/StopZone', 'stop_zones_n'),
        ('round_completion_rate', 'RoundCompletionRate', 'round_entered_n'),
        ('round_collision_rate', 'RoundCollisionRate', 'round_entered_n'),
        ('round_entry_speed_avg', 'RoundEntrySpeedAvg', 'round_entered_n'),
        ('round_entry_front_avg', 'RoundEntryFrontObstAvg', 'round_entered_n'),
        ('round_bonus_per_entry', 'RoundBonus/Entry', 'round_entered_n'),
        ('round_bonus_per_tick', 'RoundBonus/RoundTick', 'round_ticks'),
        ('round_completion_bonus_per_completion', 'RndCompletionBonus/Completion', 'round_completed_n'),
        ('round_entry_penalty_per_entry', 'RndEntryPenalty/Entry', 'round_entered_n'),
        ('round_throttle_penalty_per_tick', 'RndThrottlePenalty/RoundTick', 'round_ticks'),
        ('round_steer_avg', 'RoundSteeringAvg', 'round_ticks'),
        ('round_throttle_avg', 'RoundThrottleAvg', 'round_ticks'),
        ('round_exit1_death_rate', 'RoundExit1DeathRate', 'round_exit1_count'),
        ('round_exit2_death_rate', 'RoundExit2DeathRate', 'round_exit2_count'),
        ('round_exit3_death_rate', 'RoundExit3PlusDeathRate', 'round_exit3_count'),
        ('pen_v_per_life_sec', 'PenaltyVelocidad/LifeSec', 'pen_v'),
        ('pen_v_fit_share', 'PenaltyVelocidad/FitShare', 'pen_v'),
        ('car_overlap_per_sec', 'CarOverlaps/s', 'car_overlaps'),
        ('car_overlap_per_tick', 'CarOverlaps/tick', 'car_overlaps'),
        ('car_overlap_shadow_per_overlap', 'CarOverlapShadow/Overlap', 'car_overlaps'),
        ('car_overlap_penalty_per_overlap', 'CarOverlapPenalty/Overlap', 'car_overlaps'),
        ('queue_wait_bonus_per_life_sec', 'QueueWaitBonus/LifeSec', 'queue_wait_bonus'),
        ('queue_wait_bonus_fit_share', 'QueueWaitBonus/FitShare', 'queue_wait_bonus'),
        ('yield_validation_speed', 'SpeedAtYieldValidation', 'yield_validation_seen'),
        ('crossing_blocked_per_stop_tick', 'BlockedCrossing/StopTick', 'crossing_blocked_t'),
        ('crossing_blocked_per_life_sec', 'BlockedCrossing/LifeSec', 'crossing_blocked_t'),
        ('front_obst_death', 'FrontObstAtDeath', 'front_obst_death_seen'),
        ('steer_app_wrong_share', 'SteerApproachWrongShare', 'steer_app_total'),
        ('first_steer_release_ticks', 'FirstSteerAfterReleaseTicks', 'first_steer_release_seen'),
    ]
    available_fields = debug_available_fields(dbg)
    coverage_rows = []
    for key, label, exposure_key in situational_items:
        required_key = METRIC_REQUIRED_FIELDS.get(key)
        if required_key and required_key not in available_fields:
            continue
        if (
            key not in available_fields
            and exposure_key not in available_fields
            and not any(num(r.get(exposure_key, 0.0), 0.0) > 0.0 for r in dbg)
        ):
            continue
        n_exp = metric_exposure_count(dbg, key)
        if n_exp > 0:
            coverage_rows.append((label, exposure_key, n_exp))
    if coverage_rows:
        R.p(f'\n-- Cobertura de Metricas Situacionales --')
        hdr_cov = f'  {"Metrica":>26s} | {"Denominador":>18s} | {"N":>7s} | {"Pct":>7s}'
        R.p(hdr_cov)
        R.p(f'  {"-"*(len(hdr_cov)-2)}')
        for label, exposure_key, n_exp in coverage_rows:
            R.p(f'  {label:>26s} | {exposure_key:>18s} | {n_exp:>7d} | {sdiv(n_exp*100.0, nd):>6.2f}%')

    # Correlaciones de componentes con fitness
    corr_items = [
        ('time', 'Tiempo'),
        ('a', 'Acum_A'),
        ('b', 'Media_B'),
        ('e', 'Acum_E'),
        ('f', 'Acum_F'),
        ('net', 'Acum_NetNormal'),
        ('pen_m', 'Penalty_Muerte'),
        ('pen_v', 'Penalty_Velocidad'),
        ('pen_v_per_life_sec', 'PenaltyVelocidadPerLifeSec'),
        ('pen_v_fit_share', 'PenaltyVelocidadFitShare'),
        ('pen_tv', 'Penalty_TrafficViolation'),
        ('pen_nav', 'Penalty_NavViolation'),
        ('pen_creep', 'Penalty_Creeping'),
        ('pen_rev', 'Penalty_Reverse'),
        ('pen_lazy', 'Penalty_Lazy'),
        ('pen_swstop', 'Penalty_SteeringWhileStopped'),
        ('pen_steer_app', 'Penalty_SteerApproach'),
        ('pen_align', 'Penalty_Alignment'),
        ('pen_cw', 'Penalty_CorrectingWrong'),
        ('thr_pos', 'Acum_ThrottlePos'),
        ('thr_grace', 'Acum_ThrottleDuringGraceTime'),
        ('brake_grace', 'Acum_BrakeDuringGraceTime'),
        ('yield_val_t', 'YieldValidationTime'),
        ('stop_val_t', 'StopValidationTime'),
        ('stop_bonus', 'StopCompletionBonus'),
        ('stop_done_n', 'NumStopsCompleted'),
        ('yield_bonus', 'YieldCompletionBonus'),
        ('yield_done_n', 'NumYieldsCompleted'),
        ('stop_bonus_per', 'StopBonus/Stop'),
        ('yield_bonus_per', 'YieldBonus/Yield'),
        ('stop_done_rate', 'StopDone/StopZone'),
        ('yield_done_rate', 'YieldDone/StopZone'),
        ('round_entered_n', 'NumRoundaboutsEntered'),
        ('round_completed_n', 'NumRoundaboutsCompleted'),
        ('round_completion_rate', 'RoundaboutCompletionRate'),
        ('round_collision_rate', 'RoundaboutCollisionRate'),
        ('round_entry_speed_avg', 'RoundaboutEntrySpeedAvg'),
        ('round_entry_front_avg', 'RoundaboutEntryFrontObstAvg'),
        ('round_bonus', 'RoundaboutBonusNet'),
        ('round_bonus_per_entry', 'RoundaboutBonusPerEntry'),
        ('round_bonus_per_completion', 'RoundaboutBonusPerCompletion'),
        ('round_bonus_per_tick', 'RoundaboutBonusPerTick'),
        ('round_bonus_fit_share', 'RoundaboutBonusFitShare'),
        ('round_completion_bonus', 'RoundCompletionBonus'),
        ('round_entry_penalty', 'RoundEntryPenalty'),
        ('round_throttle_penalty', 'RoundThrottlePenalty'),
        ('round_completion_bonus_per_completion', 'RoundCompletionBonusPerCompletion'),
        ('round_entry_penalty_per_entry', 'RoundEntryPenaltyPerEntry'),
        ('round_throttle_penalty_per_tick', 'RoundThrottlePenaltyPerTick'),
        ('round_tick_ratio', 'RoundaboutTickRatio'),
        ('round_steer_avg', 'RoundaboutSteeringAvg'),
        ('round_throttle_avg', 'RoundaboutThrottleAvg'),
        ('round_collisions', 'CollisionsInRoundabout'),
        ('round_exit1_death_rate', 'RoundExit1DeathRate'),
        ('round_exit2_death_rate', 'RoundExit2DeathRate'),
        ('round_exit3_death_rate', 'RoundExit3PlusDeathRate'),
        ('round_exit1_steer_avg', 'RoundExit1SteeringAvg'),
        ('round_exit2_steer_avg', 'RoundExit2SteeringAvg'),
        ('round_exit3_steer_avg', 'RoundExit3PlusSteeringAvg'),
        ('round_exit1_throttle_avg', 'RoundExit1ThrottleAvg'),
        ('round_exit2_throttle_avg', 'RoundExit2ThrottleAvg'),
        ('round_exit3_throttle_avg', 'RoundExit3PlusThrottleAvg'),
        ('car_overlaps', 'NumCarOverlaps'),
        ('car_overlap_per_sec', 'CarOverlapsPerSec'),
        ('car_overlap_per_tick', 'CarOverlapsPerTick'),
        ('car_overlap_pen_shadow', 'CarOverlapPenaltyShadow'),
        ('car_overlap_shadow_per_overlap', 'CarOverlapShadowPerOverlap'),
        ('car_overlap_penalty', 'CarOverlapPenaltyReal'),
        ('car_overlap_penalty_per_overlap', 'CarOverlapPenaltyPerOverlap'),
        ('queue_wait_bonus', 'QueueWaitBonus'),
        ('queue_wait_bonus_per_life_sec', 'QueueWaitBonusPerLifeSec'),
        ('queue_wait_bonus_fit_share', 'QueueWaitBonusFitShare'),
        ('yield_free_passes', 'NumYieldFreePasses'),
        ('yield_validation_speed', 'SpeedAtYieldValidation'),
        ('crossing_blocked_t', 'TimeBlockedAtCrossing'),
        ('crossing_blocked_per_stop_tick', 'BlockedCrossingPerStopTick'),
        ('crossing_blocked_per_life_sec', 'BlockedCrossingPerLifeSec'),
        ('front_obst_death', 'FrontObstAtDeath'),
        ('steer_app_wrong', 'SteerApproachWrongDir'),
        ('steer_app_right', 'SteerApproachRightDir'),
        ('steer_app_wrong_share', 'SteerApproachWrongShare'),
        ('first_steer_release_ticks', 'FirstSteerAfterReleaseTicks'),
        ('stop_zones_n', 'NumStopZonesEntered'),
        ('fit_peak_raw', 'NotNorm_PeakFitness'),
        ('fit_peak_gain', 'PeakGain(Peak-Final)'),
        ('steer_in', 'Acum_SteeringInput'),
        ('steer_target', 'Acum_TargetSteering'),
        ('steer_gap_abs', 'SteeringGapAbs'),
        ('steer_abs', 'Acum_ABS_Steering'),
        ('steer_in_avg', 'Avg_SteeringInput'),
        ('steer_abs_avg', 'Avg_ABS_Steering'),
        ('steer_gap_avg_abs', 'AvgAbs_TargetVsAppliedGap'),
        ('car_index', 'CarIndex'),
        ('brake_in', 'Acum_BrakeInput'),
        ('coast_t', 'Acum_CoastTime'),
        ('stop_brake', 'Acum_StopBrake'),
        ('stop_throttle', 'Acum_StopThrottle'),
        ('t_stop_ctx', 'Ticks_StopContext'),
        ('t_stop_ctx_tl', 'Ticks_StopContext_TrafficLight'),
        ('t_stop_ctx_stop', 'Ticks_StopContext_Stop'),
        ('t_stop_ctx_yield', 'Ticks_StopContext_Yield'),
        ('t_norm', 'Ticks_Normal'),
        ('t_tot', 'Ticks_Total'),
    ]
    corrs = []
    derived_corr_fields = {
        'time', 'steer_gap_abs', 'steer_in_avg', 'steer_abs_avg',
        'steer_gap_avg_abs', 'stop_bonus_per', 'yield_bonus_per',
        'stop_done_rate', 'yield_done_rate', 'fit_peak_gain',
        'pen_v_per_life_sec', 'pen_v_fit_share',
        'round_completion_rate', 'round_collision_rate', 'round_entry_speed_avg',
        'round_entry_front_avg', 'round_bonus', 'round_bonus_per_entry',
        'round_bonus_per_completion', 'round_bonus_per_tick', 'round_bonus_fit_share',
        'round_completion_bonus_per_completion', 'round_entry_penalty_per_entry',
        'round_throttle_penalty_per_tick',
        'round_tick_ratio', 'round_steer_avg', 'round_throttle_avg',
        'round_exit1_death_rate', 'round_exit2_death_rate', 'round_exit3_death_rate',
        'round_exit1_steer_avg', 'round_exit2_steer_avg', 'round_exit3_steer_avg',
        'round_exit1_throttle_avg', 'round_exit2_throttle_avg', 'round_exit3_throttle_avg',
        'car_overlap_shadow_per_overlap', 'car_overlap_penalty_per_overlap',
        'queue_wait_bonus_per_life_sec', 'queue_wait_bonus_fit_share',
        'yield_validation_speed',
        'crossing_blocked_per_stop_tick', 'crossing_blocked_per_life_sec',
        'front_obst_death', 'steer_app_wrong_share', 'steer_app_wrong_per_tick',
        'steer_app_right_per_tick', 'first_steer_release_ticks',
    }
    for key, label in corr_items:
        required_key = METRIC_REQUIRED_FIELDS.get(key)
        if required_key and required_key not in available_fields:
            continue
        if key not in available_fields and key not in derived_corr_fields:
            continue
        fit_vals, vals = correlation_sample(dbg, key)
        if len(vals) < 5 or stdev(fit_vals) <= 1e-12 or stdev(vals) <= 1e-12:
            continue
        c = pearson_corr(fit_vals, vals)
        corrs.append((abs(c), c, label, len(vals)))
    corrs.sort(reverse=True)

    R.p(f'\n-- Correlaciones con Fitness (Pearson) --')
    R.p('  Solo se muestran metricas variables con N>=5 y exposicion real cuando requieren denominador.')
    for _, c, label, sample_n in corrs:
        R.p(f'  {label:28s}: {c:+.4f} (N={sample_n})')

    R.p(f'\n-- Conduccion en Contexto Stop/Semaforo por Familia --')
    hdr_stop = f'  {"Familia":>10s} | {"N":>7s} | {"StopTicks":>10s} | {"StopTL":>8s} | {"StopSt":>8s} | {"StopYld":>8s} | {"StopBrake":>10s} | {"StopThr":>10s} | {"StopBrake%":>10s} | {"Brake%":>8s} | {"GraceThr":>9s} | {"GraceBr":>9s} | {"YldVal":>8s} | {"StopVal":>8s} | {"StIn":>7s} | {"StTgt":>7s} | {"GapAbs":>8s} | {"SteerStop":>10s}'
    R.p(hdr_stop)
    R.p(f'  {"-"*(len(hdr_stop)-2)}')
    global_stop_brake_sum = sum(r.get('stop_brake', 0.0) for r in dbg)
    global_stop_throttle_sum = sum(r.get('stop_throttle', 0.0) for r in dbg)
    global_stop_brake_share = sdiv(global_stop_brake_sum, global_stop_brake_sum + global_stop_throttle_sum)
    for fam, rows_f in sorted(by_family.items(), key=lambda kv: len(kv[1]), reverse=True):
        nf = len(rows_f)
        stop_ticks = mean([r.get('t_stop_ctx', 0.0) for r in rows_f])
        stop_ticks_tl = mean([r.get('t_stop_ctx_tl', 0.0) for r in rows_f])
        stop_ticks_stop = mean([r.get('t_stop_ctx_stop', 0.0) for r in rows_f])
        stop_ticks_yield = mean([r.get('t_stop_ctx_yield', 0.0) for r in rows_f])
        stop_brake = mean([r.get('stop_brake', 0.0) for r in rows_f])
        stop_thr = mean([r.get('stop_throttle', 0.0) for r in rows_f])
        stop_share = sdiv(stop_brake, stop_brake + stop_thr)
        cmd_brake = mean([r.get('brake_in', 0.0) for r in rows_f])
        cmd_thr = mean([r.get('thr_pos', 0.0) for r in rows_f])
        cmd_share = sdiv(cmd_brake, cmd_brake + cmd_thr)
        grace_thr = mean([r.get('thr_grace', 0.0) for r in rows_f])
        grace_br = mean([r.get('brake_grace', 0.0) for r in rows_f])
        yield_val = mean([r.get('yield_val_t', 0.0) for r in rows_f])
        stop_val = mean([r.get('stop_val_t', 0.0) for r in rows_f])
        steer_in = mean([r.get('steer_in', 0.0) for r in rows_f])
        steer_tgt = mean([r.get('steer_target', 0.0) for r in rows_f])
        steer_gap = mean([abs(r.get('steer_in', 0.0) - r.get('steer_target', 0.0)) for r in rows_f])
        steer_stop_pen = mean([r.get('pen_swstop', 0.0) for r in rows_f])
        R.p(
            f'  {fam:>10s} | {nf:>7d} | {stop_ticks:>10.3f} | {stop_ticks_tl:>8.3f} | {stop_ticks_stop:>8.3f} | {stop_ticks_yield:>8.3f} | '
            f'{stop_brake:>10.4f} | {stop_thr:>10.4f} | {stop_share*100:>9.2f}% | {cmd_share*100:>7.2f}% | {grace_thr:>9.4f} | {grace_br:>9.4f} | {yield_val:>8.3f} | {stop_val:>8.3f} | {steer_in:>7.3f} | {steer_tgt:>7.3f} | {steer_gap:>8.3f} | {steer_stop_pen:>10.4f}'
        )

    stop_spawn_rows = []
    for sp, rows_sp in by_spawn.items():
        nsp = len(rows_sp)
        legal_fail_n = sum(1 for r in rows_sp if death_family(r.get('death', '')) == 'VIOLATION')

        stop_cov_vals = [sdiv(r.get('t_stop_ctx', 0.0), max(r.get('t_tot', 0.0), 1.0)) for r in rows_sp]
        stop_share_vals = []
        brake_share_vals = []
        for r in rows_sp:
            sb = r.get('stop_brake', 0.0)
            st = r.get('stop_throttle', 0.0)
            if (sb + st) > 0.0:
                stop_share_vals.append(sdiv(sb, sb + st))
            b = r.get('brake_in', 0.0)
            t = r.get('thr_pos', 0.0)
            if (b + t) > 0.0:
                brake_share_vals.append(sdiv(b, b + t))

        stop_spawn_rows.append({
            'spawn': sp,
            'n': nsp,
            'legal_fail_pct': sdiv(legal_fail_n * 100.0, nsp),
            'stop_ctx_p10': pctl(stop_cov_vals, 10) * 100.0,
            'stop_ctx_p50': pctl(stop_cov_vals, 50) * 100.0,
            'stop_ctx_p90': pctl(stop_cov_vals, 90) * 100.0,
            'stop_brake_p50': pctl(stop_share_vals, 50) * 100.0,
            'stop_brake_p90': pctl(stop_share_vals, 90) * 100.0,
            'brake_p50': pctl(brake_share_vals, 50) * 100.0,
            'stop_brake_gap': (pctl(stop_share_vals, 50) - global_stop_brake_share) * 100.0,
        })

    if stop_spawn_rows:
        R.p(f'\n-- Stop/Semaforo por Spawn (percentiles dinamicos) --')
        hdr_ss = f'  {"Spawn":>15s} | {"N":>5s} | {"Legal%":>8s} | {"StopCtx P10/P50/P90":>24s} | {"StopBrake P50/P90":>19s} | {"Brake P50":>9s} | {"GapStop%":>9s}'
        R.p(hdr_ss)
        R.p(f'  {"-"*(len(hdr_ss)-2)}')
        for st in sorted(stop_spawn_rows, key=lambda x: (x['legal_fail_pct'], x['stop_ctx_p50']), reverse=True)[:TOP_ROWS]:
            R.p(
                f'  {st["spawn"].replace("TargetPoint","TP"):>15s} | {st["n"]:>5d} | {st["legal_fail_pct"]:>7.2f}% | '
                f'{st["stop_ctx_p10"]:>6.2f}/{st["stop_ctx_p50"]:>6.2f}/{st["stop_ctx_p90"]:>6.2f}% | '
                f'{st["stop_brake_p50"]:>7.2f}/{st["stop_brake_p90"]:>7.2f}% | {st["brake_p50"]:>8.2f}% | {st["stop_brake_gap"]:>+8.2f}pp'
            )

        legal_vals = [x['legal_fail_pct'] for x in stop_spawn_rows if x['n'] >= MIN_SPAWN_N]
        legal_vals_pos = [v for v in legal_vals if v > 0.0]
        q3_legal = pctl(legal_vals_pos, 75) if legal_vals_pos else 0.0
        high_legal = [x for x in stop_spawn_rows if x['legal_fail_pct'] >= q3_legal and x['legal_fail_pct'] > 0.0 and x['n'] >= MIN_SPAWN_N]
        low_n_legal = [x for x in stop_spawn_rows if x['legal_fail_pct'] > 0.0 and x['n'] < MIN_SPAWN_N]
        if high_legal:
            top_show = sorted(high_legal, key=lambda x: x['legal_fail_pct'], reverse=True)[:TOP_ROWS]
            R.p(f'\n  Spawns con fallo legal alto (>= P75={q3_legal:.2f}%):')
            for st in top_show:
                R.p(f'    {st["spawn"].replace("TargetPoint","TP")}: legal={st["legal_fail_pct"]:.2f}% stopCtxP50={st["stop_ctx_p50"]:.2f}% stopBrakeP50={st["stop_brake_p50"]:.2f}%')
        if low_n_legal:
            R.p(f'  ({len(low_n_legal)} spawns con violaciones omitidos por N<{MIN_SPAWN_N} — necesitan más datos)')

    peak_spawn_rows = []
    for sp, rows_sp in by_spawn.items():
        if not sp:
            continue
        gains = [r.get('fit_peak_gain', 0.0) for r in rows_sp]
        stop_vals = [r.get('stop_zones_n', 0.0) for r in rows_sp]
        val_totals = [r.get('val_total', r.get('yield_val_t', 0.0) + r.get('stop_val_t', 0.0)) for r in rows_sp]
        peak_pos = sum(1 for v in gains if v > 0.0)
        peak_spawn_rows.append({
            'spawn': sp,
            'n': len(rows_sp),
            'peak_gain_p50': pctl(gains, 50),
            'peak_gain_p90': pctl(gains, 90),
            'peak_pos_pct': sdiv(peak_pos * 100.0, len(rows_sp)),
            'stop_zones_p50': pctl(stop_vals, 50),
            'val_total_p50': pctl(val_totals, 50),
        })

    if peak_spawn_rows:
        R.p(f'\n-- PeakGain/StopZones por Spawn (P50) --')
        hdr_peak = f'  {"Spawn":>15s} | {"N":>5s} | {"PeakP50":>9s} | {"PeakP90":>9s} | {"Peak>Final%":>11s} | {"StopZ P50":>9s} | {"ValTot P50":>10s}'
        R.p(hdr_peak)
        R.p(f'  {"-"*(len(hdr_peak)-2)}')
        for st in sorted(peak_spawn_rows, key=lambda x: (x['peak_gain_p50'], x['peak_gain_p90']), reverse=True)[:TOP_ROWS]:
            R.p(
                f'  {st["spawn"].replace("TargetPoint","TP"):>15s} | {st["n"]:>5d} | {st["peak_gain_p50"]:>9.2f} | {st["peak_gain_p90"]:>9.2f} | '
                f'{st["peak_pos_pct"]:>10.1f}% | {st["stop_zones_p50"]:>9.2f} | {st["val_total_p50"]:>10.2f}'
            )

    # Spawns inestables
    spawn_rows = []
    for sp, rows_sp in by_spawn.items():
        fits = [r['fit'] for r in rows_sp]
        lazy_n = sum(1 for r in rows_sp if is_lazy_reason(r.get('death', '')))
        spawn_rows.append({
            'spawn': sp,
            'n': len(rows_sp),
            'mean_fit': mean(fits),
            'std_fit': stdev(fits),
            'cv_fit': coef_var(fits) * 100.0,
            'p10': pctl(fits, 10),
            'p50': pctl(fits, 50),
            'p90': pctl(fits, 90),
            'lazy_pct': sdiv(lazy_n * 100.0, len(rows_sp)),
        })

    R.p(f'\n-- Spawns Mas Inestables (por desv. fitness) --')
    hdr = f'  {"Spawn":>15s} | {"N":>5s} | {"FitMed":>10s} | {"Std":>10s} | {"CV%":>8s} | {"P10":>9s} | {"P50":>9s} | {"P90":>9s} | {"Lazy%":>7s}'
    R.p(hdr)
    R.p(f'  {"-"*(len(hdr)-2)}')
    for st in sorted(spawn_rows, key=lambda x: x['std_fit'], reverse=True)[:TOP_ROWS]:
        R.p(
            f'  {st["spawn"].replace("TargetPoint","TP"):>15s} | {st["n"]:>5d} | {st["mean_fit"]:>10.2f} | '
            f'{st["std_fit"]:>10.2f} | {st["cv_fit"]:>7.1f}% | {st["p10"]:>9.2f} | {st["p50"]:>9.2f} | {st["p90"]:>9.2f} | {st["lazy_pct"]:>6.1f}%'
        )

    # Top razones y sus spawns dominantes
    reason_counts = Counter(r['death'] for r in dbg)
    R.p(f'\n-- Top Razones y Spawns Dominantes --')
    for reason, cnt in reason_counts.most_common(min(10, len(reason_counts))):
        spc = Counter(r['spawn'] for r in by_death[reason])
        top_sp = ', '.join(f'{sp.replace("TargetPoint","TP")}:{c}' for sp, c in spc.most_common(5))
        R.p(f'  {reason:40s} -> {cnt:>6d} | {top_sp}')

    # Peores/mejores muestras individuales
    top_n = min(TOP_ROWS, nd)
    R.p(f'\n-- Peores {top_n} Coches (raw fitness) --')
    for i, r in enumerate(sorted(dbg, key=lambda x: x['fit'])[:top_n], 1):
        prefix = f'  Terminal {i:>3d}' if freerun else f'  Gen {r["gen"]:>5d}'
        R.p(
            f'{prefix} | {r["spawn"].replace("TargetPoint","TP"):>15s} | '
            f'fit={r["fit"]:>10.2f} | t={r["time"]:>5.1f}s | death={r["death"]}'
        )

    R.p(f'\n-- Mejores {top_n} Coches (raw fitness) --')
    for i, r in enumerate(sorted(dbg, key=lambda x: -x['fit'])[:top_n], 1):
        prefix = f'  Terminal {i:>3d}' if freerun else f'  Gen {r["gen"]:>5d}'
        R.p(
            f'{prefix} | {r["spawn"].replace("TargetPoint","TP"):>15s} | '
            f'fit={r["fit"]:>10.2f} | t={r["time"]:>5.1f}s | death={r["death"]}'
        )

def report_session_comparison(R, summary_rows, dbg_rows, previous_sessions):
    if not previous_sessions:
        R.p(f'\n-- Comparativa entre sesiones --')
        R.p('  No hay sesiones previas para comparar en la carpeta Analisis.')
        return

    cur_deaths = Counter(r.get('death', '') for r in dbg_rows)
    cur_top_death = cur_deaths.most_common(1)[0][0] if cur_deaths else ''
    cur_lazy = sum(1 for r in dbg_rows if is_lazy_reason(r.get('death', '')))
    current = summarize_session(
        summary_rows,
        dbg_rows_count=len(dbg_rows),
        lazy_rows=cur_lazy,
        top_death=cur_top_death,
        debug_rows=dbg_rows,
    )
    current['session'] = f'ACTUAL_{NOW}'

    all_sessions = previous_sessions + [current]
    R.p(f'\n{"="*76}')
    R.p(f'  COMPARATIVA ENTRE SESIONES (modo={MODE}, ultimas {len(all_sessions)})')
    R.p(f'{"="*76}')

    hdr = f'  {"Sesion":>22s} | {"Gens":>5s} | {"BestMax":>11s} | {"MeanMed":>11s} | {"TimeMed":>8s} | {"Neg%":>6s} | {"Succ%":>7s} | {"DbgN":>7s} | {"Lazy%":>7s}'
    R.p(hdr)
    R.p(f'  {"-"*(len(hdr)-2)}')
    for s in all_sessions[-(COMPARE_LIMIT+1):]:
        session_name = s.get('session', '')[:22]
        R.p(
            f'  {session_name:>22s} | {s.get("gens", 0):>5d} | {s.get("best_max", 0.0):>11.2f} | '
            f'{s.get("mean_mean", 0.0):>11.2f} | {s.get("time_mean", 0.0):>7.2f}s | {s.get("neg_pct", 0.0):>5.1f}% | '
            f'{s.get("success_mean", 0.0):>6.2f}% | {s.get("debug_rows", 0):>7d} | {s.get("lazy_pct", 0.0):>6.2f}%'
        )

    prev = previous_sessions[-1]
    R.p(f'\n-- Delta vs sesion inmediatamente anterior --')
    R.p(f'  Sesion previa: {prev.get("session", "")}, Sesion actual: {current.get("session", "")}')
    R.p(f'  dBestMax: {current.get("best_max",0.0)-prev.get("best_max",0.0):+.2f}')
    R.p(f'  dMeanMed: {current.get("mean_mean",0.0)-prev.get("mean_mean",0.0):+.2f}')
    R.p(f'  dTimeMed: {current.get("time_mean",0.0)-prev.get("time_mean",0.0):+.2f}s')
    R.p(f'  dNegPct:  {current.get("neg_pct",0.0)-prev.get("neg_pct",0.0):+.2f}pp')
    R.p(f'  dSuccPct: {current.get("success_mean",0.0)-prev.get("success_mean",0.0):+.2f}pp')
    R.p(f'  dLazyPct: {current.get("lazy_pct",0.0)-prev.get("lazy_pct",0.0):+.2f}pp')

    # Ranking de la sesion actual
    with_summary = [s for s in all_sessions if s.get('gens', 0) > 0]
    if current.get('gens', 0) <= 0:
        R.p('\n  Ranking no disponible para la sesion actual (summary vacio).')
    elif len(with_summary) >= 2:
        rank_best = sorted(with_summary, key=lambda x: x.get('best_max', 0.0), reverse=True)
        rank_mean = sorted(with_summary, key=lambda x: x.get('mean_mean', 0.0), reverse=True)
        rank_neg = sorted(with_summary, key=lambda x: x.get('neg_pct', 9999.0))

        rb = next((i + 1 for i, s in enumerate(rank_best) if s.get('session') == current.get('session')), 0)
        rm = next((i + 1 for i, s in enumerate(rank_mean) if s.get('session') == current.get('session')), 0)
        rn = next((i + 1 for i, s in enumerate(rank_neg) if s.get('session') == current.get('session')), 0)
        total = len(with_summary)
        R.p(f'\n  Ranking actual entre {total} sesiones con summary:')
        R.p(f'    BestMax : #{rb}')
        R.p(f'    MeanMed : #{rm}')
        R.p(f'    Neg%    : #{rn} (menor es mejor)')

def save_json_snapshot(
    path,
    summary_rows,
    dbg_rows,
    summary_meta,
    debug_meta,
    previous_sessions,
    debug_scope=None,
    train_summary_rows=0,
    test_summary_rows=0,
    generation_normalization=None,
    auto_insights=None,
    data_coherence=None,
    yield_stuck=None,
    stop_stuck=None,
):
    deaths = Counter(r.get('death', '') for r in dbg_rows)
    car_bounds = infer_carindex_bounds(dbg_rows)
    families = Counter(death_family(r.get('death', '')) for r in dbg_rows)
    families_detail = Counter(death_family_detail_for_row(r) for r in dbg_rows)
    lazy_rows = families.get('LAZY', 0)
    invalid_brain_rows = families.get('INVALID_BRAIN', 0)
    death_failure_rows = sum(
        1 for r in dbg_rows
        if r.get('is_test_failure_death', is_test_failure_reason(r.get('death', '')))
    )
    cmd_total = sum(r.get('thr_pos', 0.0) + r.get('brake_in', 0.0) for r in dbg_rows)
    grace_cmd_total = sum(r.get('thr_grace', 0.0) + r.get('brake_grace', 0.0) for r in dbg_rows)
    stop_cmd_total = sum(r.get('stop_brake', 0.0) + r.get('stop_throttle', 0.0) for r in dbg_rows)
    stop_ticks_total = sum(r.get('t_stop_ctx', 0.0) for r in dbg_rows)
    ticks_total = sum(r.get('t_tot', 0.0) for r in dbg_rows)
    creep_total = sum(r.get('pen_creep', 0.0) for r in dbg_rows)
    rev_total = sum(r.get('pen_rev', 0.0) for r in dbg_rows)
    lazy_total = sum(r.get('pen_lazy', 0.0) for r in dbg_rows)
    steer_stop_total = sum(r.get('pen_swstop', 0.0) for r in dbg_rows)
    steer_approach_total = sum(r.get('pen_steer_app', 0.0) for r in dbg_rows)
    alignment_total = sum(r.get('pen_align', 0.0) for r in dbg_rows)
    yield_val_total = sum(r.get('yield_val_t', 0.0) for r in dbg_rows)
    stop_val_total = sum(r.get('stop_val_t', 0.0) for r in dbg_rows)
    stop_bonus_total = sum(r.get('stop_bonus', 0.0) for r in dbg_rows)
    yield_bonus_total = sum(r.get('yield_bonus', 0.0) for r in dbg_rows)
    stop_done_total = sum(r.get('stop_done_n', 0.0) for r in dbg_rows)
    yield_done_total = sum(r.get('yield_done_n', 0.0) for r in dbg_rows)
    speed_penalty_life_avg, speed_penalty_life_n = exposed_mean(dbg_rows, 'pen_v_per_life_sec')
    car_overlap_total = sum(r.get('car_overlaps', 0.0) for r in dbg_rows)
    car_overlap_rows = sum(1 for r in dbg_rows if r.get('car_overlaps', 0.0) > 0.0)
    car_overlap_per_sec_avg, car_overlap_per_sec_n = exposed_mean(dbg_rows, 'car_overlap_per_sec')
    car_overlap_per_tick_avg, car_overlap_per_tick_n = exposed_mean(dbg_rows, 'car_overlap_per_tick')
    car_overlap_shadow_total = sum(r.get('car_overlap_pen_shadow', 0.0) for r in dbg_rows)
    car_overlap_shadow_avg, car_overlap_shadow_n = exposed_mean(dbg_rows, 'car_overlap_shadow_per_overlap')
    car_overlap_penalty_total = sum(r.get('car_overlap_penalty', 0.0) for r in dbg_rows)
    car_overlap_penalty_avg, car_overlap_penalty_n = exposed_mean(dbg_rows, 'car_overlap_penalty_per_overlap')
    queue_wait_bonus_total = sum(r.get('queue_wait_bonus', 0.0) for r in dbg_rows)
    queue_wait_bonus_rows = sum(1 for r in dbg_rows if r.get('queue_wait_bonus', 0.0) > 0.0)
    queue_wait_bonus_life_avg, queue_wait_bonus_life_n = exposed_mean(dbg_rows, 'queue_wait_bonus_per_life_sec')
    queue_wait_bonus_fit_share_avg, queue_wait_bonus_fit_share_n = exposed_mean(dbg_rows, 'queue_wait_bonus_fit_share')
    yield_free_passes_total = sum(r.get('yield_free_passes', 0.0) for r in dbg_rows)
    yield_validation_speed_avg, yield_validation_speed_n = exposed_mean(dbg_rows, 'yield_validation_speed')
    crossing_blocked_total = sum(r.get('crossing_blocked_t', 0.0) for r in dbg_rows)
    crossing_blocked_rows = sum(1 for r in dbg_rows if r.get('crossing_blocked_t', 0.0) > 0.0)
    crossing_blocked_stop_avg, crossing_blocked_stop_n = exposed_mean(dbg_rows, 'crossing_blocked_per_stop_tick')
    crossing_blocked_life_avg, crossing_blocked_life_n = exposed_mean(dbg_rows, 'crossing_blocked_per_life_sec')
    front_obst_death_avg, front_obst_death_n = exposed_mean(dbg_rows, 'front_obst_death')
    steer_app_wrong_total = sum(r.get('steer_app_wrong', 0.0) for r in dbg_rows)
    steer_app_right_total = sum(r.get('steer_app_right', 0.0) for r in dbg_rows)
    steer_app_wrong_share_avg, steer_app_wrong_share_n = exposed_mean(dbg_rows, 'steer_app_wrong_share')
    first_steer_release_avg, first_steer_release_n = exposed_mean(dbg_rows, 'first_steer_release_ticks')
    stop_bonus_per_avg, stop_bonus_per_n = exposed_mean(dbg_rows, 'stop_bonus_per')
    yield_bonus_per_avg, yield_bonus_per_n = exposed_mean(dbg_rows, 'yield_bonus_per')
    stop_done_rate_avg, stop_done_rate_n = exposed_mean(dbg_rows, 'stop_done_rate')
    yield_done_rate_avg, yield_done_rate_n = exposed_mean(dbg_rows, 'yield_done_rate')
    round_entry_speed_avg, round_entry_speed_n = exposed_mean(dbg_rows, 'round_entry_speed_avg')
    round_entry_front_avg, round_entry_front_n = exposed_mean(dbg_rows, 'round_entry_front_avg')
    round_steer_avg, round_steer_n = exposed_mean(dbg_rows, 'round_steer_avg')
    round_throttle_avg, round_throttle_n = exposed_mean(dbg_rows, 'round_throttle_avg')
    round_bonus_total = sum(r.get('round_bonus', 0.0) for r in dbg_rows)
    round_completion_bonus_total = sum(r.get('round_completion_bonus', 0.0) for r in dbg_rows)
    round_entry_penalty_total = sum(r.get('round_entry_penalty', 0.0) for r in dbg_rows)
    round_throttle_penalty_total = sum(r.get('round_throttle_penalty', 0.0) for r in dbg_rows)
    round_bonus_breakdown_available = debug_field_available(dbg_rows, 'round_completion_bonus')
    round_bonus_entry_avg, round_bonus_entry_n = exposed_mean(dbg_rows, 'round_bonus_per_entry')
    round_bonus_completion_avg, round_bonus_completion_n = exposed_mean(dbg_rows, 'round_bonus_per_completion')
    round_bonus_tick_avg, round_bonus_tick_n = exposed_mean(dbg_rows, 'round_bonus_per_tick')
    round_completion_bonus_avg, round_completion_bonus_n = exposed_mean(dbg_rows, 'round_completion_bonus_per_completion')
    round_entry_penalty_avg, round_entry_penalty_n = exposed_mean(dbg_rows, 'round_entry_penalty_per_entry')
    round_throttle_penalty_avg, round_throttle_penalty_n = exposed_mean(dbg_rows, 'round_throttle_penalty_per_tick')
    if not round_bonus_breakdown_available:
        round_completion_bonus_avg = round_entry_penalty_avg = round_throttle_penalty_avg = 0.0
        round_completion_bonus_n = round_entry_penalty_n = round_throttle_penalty_n = 0
    steer_in_total = sum(r.get('steer_in', 0.0) for r in dbg_rows)
    steer_target_total = sum(r.get('steer_target', 0.0) for r in dbg_rows)
    steer_gap_total = sum(abs(r.get('steer_in', 0.0) - r.get('steer_target', 0.0)) for r in dbg_rows)
    round_entered_total = sum(r.get('round_entered_n', 0.0) for r in dbg_rows)
    round_completed_total = sum(r.get('round_completed_n', 0.0) for r in dbg_rows)
    round_collisions_total = sum(r.get('round_collisions', 0.0) for r in dbg_rows)
    round_ticks_total = sum(r.get('round_ticks', 0.0) for r in dbg_rows)
    collision_stats = summarize_collision_deaths(dbg_rows)
    debug_schema = dbg_rows[0].get('_schema', '') if dbg_rows else ''
    debug_schema_0107 = (
        debug_schema == '2026-07-01-overlap-penalty-queue-wait'
        or str(debug_schema).startswith('2026-07-03')
        or debug_field_available(dbg_rows, 'queue_wait_bonus')
        or debug_field_available(dbg_rows, 'current_trigger')
    )
    freerun_censored_rows = [r for r in summary_rows if int(num(r.get('censored_count', 0), 0.0)) > 0]
    freerun_censoring = {
        'enabled': bool(freerun_censored_rows),
        'censored_alive_count': sum(int(num(r.get('censored_count', 0), 0.0)) for r in freerun_censored_rows),
        'observed_terminal_rows': sum(int(num(r.get('observed_terminal_count', 0), 0.0)) for r in freerun_censored_rows),
        'total_attempts_with_censored': sum(int(num(r.get('eval_n', 0), 0.0)) for r in freerun_censored_rows),
        'success_rate_lower': sdiv(
            sum(r.get('success_count', 0) for r in freerun_censored_rows) * 100.0,
            sum(int(num(r.get('eval_n', 0), 0.0)) for r in freerun_censored_rows),
        ),
        'success_rate_upper_if_censored_alive_success': sdiv(
            sum((r.get('success_count', 0) + int(num(r.get('censored_count', 0), 0.0))) for r in freerun_censored_rows) * 100.0,
            sum(int(num(r.get('eval_n', 0), 0.0)) for r in freerun_censored_rows),
        ),
        'session_elapsed_estimate_s': max([r.get('session_elapsed_estimate_s', 0.0) for r in freerun_censored_rows] or [0.0]),
        'censored_age_mean_s': pctl([r.get('censored_age_mean_s', 0.0) for r in freerun_censored_rows], 50),
        'censored_age_p50_s': pctl([r.get('censored_age_p50_s', 0.0) for r in freerun_censored_rows], 50),
        'censored_age_p90_s': pctl([r.get('censored_age_p90_s', 0.0) for r in freerun_censored_rows], 50),
        'censored_age_max_s': max([r.get('censored_age_max_s', 0.0) for r in freerun_censored_rows] or [0.0]),
        'note': 'FreeRun Debug is terminal-row only; alive cars are censored and have no exact final lifetime.',
    }

    by_spawn = defaultdict(list)
    for r in dbg_rows:
        by_spawn[r.get('spawn', '')].append(r)
    spawn_stop_stats = []
    for sp, rows_sp in by_spawn.items():
        if not sp:
            continue
        nsp = len(rows_sp)
        legal_fail_n = sum(1 for r in rows_sp if death_family(r.get('death', '')) == 'VIOLATION')
        stop_cov_vals = [sdiv(r.get('t_stop_ctx', 0.0), max(r.get('t_tot', 0.0), 1.0)) * 100.0 for r in rows_sp]
        stop_share_vals = [
            sdiv(r.get('stop_brake', 0.0), r.get('stop_brake', 0.0) + r.get('stop_throttle', 0.0)) * 100.0
            for r in rows_sp if (r.get('stop_brake', 0.0) + r.get('stop_throttle', 0.0)) > 0.0
        ]
        yield_vals = [r.get('yield_val_t', 0.0) for r in rows_sp]
        stop_vals = [r.get('stop_val_t', 0.0) for r in rows_sp]
        steer_gap_vals = [abs(r.get('steer_in', 0.0) - r.get('steer_target', 0.0)) for r in rows_sp]
        steer_abs_vals = [r.get('steer_abs_avg', 0.0) for r in rows_sp]
        spawn_stop_stats.append({
            'spawn': sp,
            'n': nsp,
            'legal_fail_pct': sdiv(legal_fail_n * 100.0, nsp),
            'stop_ctx_p50': pctl(stop_cov_vals, 50),
            'stop_ctx_p90': pctl(stop_cov_vals, 90),
            'stop_brake_p50': pctl(stop_share_vals, 50),
            'stop_brake_p90': pctl(stop_share_vals, 90),
            'yield_val_p50': pctl(yield_vals, 50),
            'stop_val_p50': pctl(stop_vals, 50),
            'steer_abs_avg_p50': pctl(steer_abs_vals, 50),
            'steer_gap_p50': pctl(steer_gap_vals, 50),
            'steer_gap_avg_abs_p50': pctl([r.get('steer_gap_avg_abs', 0.0) for r in rows_sp], 50),
        })
    current_trigger_stats = []
    if debug_field_available(dbg_rows, 'current_trigger'):
        by_trigger = defaultdict(list)
        for row in dbg_rows:
            trigger = row.get('current_trigger_short') or short_actor_name(row.get('current_trigger', ''), empty='')
            if trigger:
                by_trigger[trigger].append(row)
        for trigger, rows_tr in by_trigger.items():
            ntr = len(rows_tr)
            legal_n = sum(1 for r in rows_tr if death_family(r.get('death', '')) == 'VIOLATION')
            collision_n = sum(1 for r in rows_tr if is_collision_reason(r.get('death', '')))
            lazy_n = sum(1 for r in rows_tr if is_lazy_reason(r.get('death', '')))
            top_death = Counter(r.get('death', '') for r in rows_tr).most_common(1)[0]
            current_trigger_stats.append({
                'trigger': trigger,
                'kind': trigger_kind(rows_tr[0].get('current_trigger', '')),
                'n': ntr,
                'lazy_pct': sdiv(lazy_n * 100.0, ntr),
                'legal_fail_pct': sdiv(legal_n * 100.0, ntr),
                'collision_pct': sdiv(collision_n * 100.0, ntr),
                'problem_pct': sdiv((lazy_n + legal_n + collision_n) * 100.0, ntr),
                'fit_median': pctl([r.get('fit', 0.0) for r in rows_tr], 50),
                'time_median': pctl([r.get('time', 0.0) for r in rows_tr], 50),
                'top_death': top_death[0],
                'top_death_count': top_death[1],
            })
        current_trigger_stats.sort(key=lambda x: (x['problem_pct'], x['n']), reverse=True)
    data = {
        'mode': MODE,
        'label': LABEL,
        'timestamp': NOW,
        'output_dir': OUT_DIR,
        'phase_split_summary': {
            'train_rows': train_summary_rows,
            'test_rows': test_summary_rows,
        },
        'summary_rows': len(summary_rows),
        'debug_rows': len(dbg_rows),
        'summary_file': summary_meta,
        'debug_file': debug_meta,
        'debug_scope': debug_scope or {},
        'generation_normalization': generation_normalization or {},
        'car_index_bounds': car_bounds,
        'data_coherence': data_coherence or {},
        'freerun_censoring': freerun_censoring,
        'yield_stuck_detection': yield_stuck or {},
        'stop_stuck_detection': stop_stuck or {},
        'auto_insights': auto_insights or [],
        'current_trigger_stats': current_trigger_stats,
        'program_updates_0107': {
            'schema_detected': debug_schema,
            'single_car_test_mode_note': (
                'When MultiTestingMode is false, EvolutionManager can spawn one loaded-brain car; '
                'Summary may be empty or not represent a full multi-car generation.'
            ) if debug_schema_0107 else '',
            'pending_signal_queues_cleared_on_generation_end': debug_schema_0107,
            'crossing_blocked_time_semantics': (
                'EndGeneration clears pending stop/yield/crossing queues; Acum_TimeBlockedAtCrossing '
                'should be read as current-session waiting, not cross-generation carryover.'
            ) if debug_schema_0107 else '',
            'speed_penalty_effective_obstacle_distance': debug_schema_0107 and debug_field_available(dbg_rows, 'pen_v'),
            'speed_penalty_semantics': (
                'Acum_PenaltyVelocidad uses EffectiveObstacleDistance; when a live closest vehicle exists, '
                'the effective distance is ClosestVehicleDistance scaled by that vehicle speed.'
            ) if debug_schema_0107 else '',
            'speed_penalty_total': sum(r.get('pen_v', 0.0) for r in dbg_rows),
            'speed_penalty_rows': sum(1 for r in dbg_rows if r.get('pen_v', 0.0) > 0.0),
            'speed_penalty_per_life_sec_exposed_avg': speed_penalty_life_avg,
            'speed_penalty_per_life_sec_exposed_n': speed_penalty_life_n,
            'car_overlap_penalty_available': debug_field_available(dbg_rows, 'car_overlap_penalty'),
            'car_overlap_penalty_formula': 'relative_speed^2 / MaxSpeed; subtracts real fitness',
            'car_overlap_events': car_overlap_total,
            'car_overlap_penalty_real': car_overlap_penalty_total,
            'car_overlap_penalty_per_overlap_exposed_avg': car_overlap_penalty_avg,
            'car_overlap_penalty_per_overlap_exposed_n': car_overlap_penalty_n,
            'car_overlap_shadow_is_diagnostic_only': True,
            'queue_wait_bonus_available': debug_field_available(dbg_rows, 'queue_wait_bonus'),
            'queue_wait_bonus_condition': 'not ForceStop, not traffic light, front obstacle < 0.3, low speed behind car',
            'queue_wait_bonus_total': queue_wait_bonus_total,
            'queue_wait_bonus_rows': queue_wait_bonus_rows,
            'queue_wait_bonus_rows_pct': sdiv(queue_wait_bonus_rows * 100.0, len(dbg_rows)),
            'queue_wait_bonus_per_life_sec_exposed_avg': queue_wait_bonus_life_avg,
            'queue_wait_bonus_per_life_sec_exposed_n': queue_wait_bonus_life_n,
        },
        'program_updates_0307': {
            'schema_detected': debug_schema,
            'notes_are_semantic_not_new_csv_columns': debug_schema_0107,
            'free_run_mode_note': (
                'If IsFreeRunMode is enabled, EvolutionManager spawns one loaded-brain car per spawn '
                'with TrainingMode=false and bBypassLifetimeLimit=true. Interpret as free simulation/debug '
                'unless Summary confirms a regular train/test batch.'
            ) if debug_schema_0107 else '',
            'release_fade_distance_input': (
                'DistToStopLine network input fades back to neutral 1.0 through ReleaseFadeAlpha after ForceStop '
                'release; FirstSteerAfterRelease remains a reaction metric, not persistent stop-line visibility.'
            ) if debug_schema_0107 else '',
            'learned_legal_thresholds': (
                'Traffic light, stop and yield validation can use thresholds learned from legal samples; '
                'fallbacks still exist when there are not enough samples.'
            ) if debug_schema_0107 else '',
            'dynamic_stop_window': (
                'STOP validation uses a dynamic allowed distance before the line and a learned minimum wait time.'
            ) if debug_schema_0107 else '',
            'stop_death_penalty_signed_distance': (
                'STOP death penalty includes excess after the stop line through SignedDistanceToStopLine.'
            ) if debug_schema_0107 else '',
            'creeping_condition': (
                'CreepingPenalty applies only for traffic-light/stop contexts before the line '
                '(SignedDistanceToStopLine <= 0), not for yield.'
            ) if debug_schema_0107 else '',
            'wait_bonus_condition': (
                'WaitBonus is bounded by the approach-time window; it should not be read as unlimited waiting reward.'
            ) if debug_schema_0107 else '',
            'crossing_blocked_time_semantics': (
                'Acum_TimeBlockedAtCrossing aggregates stop and yield waiting increments with different step sizes '
                '(stop 0.5s, yield crossing/release 0.1/0.3s).'
            ) if debug_schema_0107 else '',
            'reverse_wrong_semantics': (
                'REVERSING_WRONG combines reverse risk and wrong steering direction; REVERSE alone is only reverse risk; '
                'Penalty_CorrectingWrong covers wrong steering without reverse risk.'
            ) if debug_schema_0107 else '',
            'stop_context_ticks_traffic_light': sum(r.get('t_stop_ctx_tl', 0.0) for r in dbg_rows),
            'stop_context_ticks_stop': sum(r.get('t_stop_ctx_stop', 0.0) for r in dbg_rows),
            'stop_context_ticks_yield': sum(r.get('t_stop_ctx_yield', 0.0) for r in dbg_rows),
            'wait_bonus_total': sum(r.get('wait_bonus', 0.0) for r in dbg_rows),
            'wait_bonus_rows': sum(1 for r in dbg_rows if r.get('wait_bonus', 0.0) > 0.0),
            'creeping_penalty_total': creep_total,
            'creeping_penalty_rows': sum(1 for r in dbg_rows if r.get('pen_creep', 0.0) > 0.0),
            'reverse_penalty_total': rev_total,
            'reverse_penalty_rows': sum(1 for r in dbg_rows if r.get('pen_rev', 0.0) > 0.0),
            'correcting_wrong_penalty_total': sum(r.get('pen_cw', 0.0) for r in dbg_rows),
            'correcting_wrong_penalty_rows': sum(1 for r in dbg_rows if r.get('pen_cw', 0.0) > 0.0),
            'crossing_blocked_time': crossing_blocked_total,
            'crossing_blocked_rows': crossing_blocked_rows,
        },
        'summary_metrics': summarize_session(
            summary_rows,
            dbg_rows_count=len(dbg_rows),
            lazy_rows=lazy_rows,
            top_death=deaths.most_common(1)[0][0] if deaths else '',
            debug_rows=dbg_rows,
        ),
        'debug_metrics': {
            'lazy_rows': lazy_rows,
            'lazy_pct': sdiv(lazy_rows * 100.0, len(dbg_rows)),
            'invalid_brain_rows': invalid_brain_rows,
            'invalid_brain_pct': sdiv(invalid_brain_rows * 100.0, len(dbg_rows)),
            'top_death': deaths.most_common(1)[0][0] if deaths else '',
            'top_death_count': deaths.most_common(1)[0][1] if deaths else 0,
            'unique_spawns': len(set(r.get('spawn', '') for r in dbg_rows if r.get('spawn', ''))),
            'unique_deaths': len(set(r.get('death', '') for r in dbg_rows if r.get('death', ''))),
            'avg_thr_pos': sdiv(sum(r.get('thr_pos', 0.0) for r in dbg_rows), len(dbg_rows)),
            'avg_thr_grace': sdiv(sum(r.get('thr_grace', 0.0) for r in dbg_rows), len(dbg_rows)),
            'avg_brake_grace': sdiv(sum(r.get('brake_grace', 0.0) for r in dbg_rows), len(dbg_rows)),
            'avg_brake_in': sdiv(sum(r.get('brake_in', 0.0) for r in dbg_rows), len(dbg_rows)),
            'car_overlap_events': car_overlap_total,
            'car_overlap_rows': car_overlap_rows,
            'car_overlap_rows_pct': sdiv(car_overlap_rows * 100.0, len(dbg_rows)),
            'avg_car_overlaps': sdiv(car_overlap_total, len(dbg_rows)),
            'avg_car_overlap_per_sec_exposed': car_overlap_per_sec_avg,
            'avg_car_overlap_per_sec_exposed_n': car_overlap_per_sec_n,
            'avg_car_overlap_per_tick_exposed': car_overlap_per_tick_avg,
            'avg_car_overlap_per_tick_exposed_n': car_overlap_per_tick_n,
            'car_overlap_penalty_shadow': car_overlap_shadow_total,
            'avg_car_overlap_shadow_per_overlap': car_overlap_shadow_avg,
            'avg_car_overlap_shadow_per_overlap_n': car_overlap_shadow_n,
            'car_overlap_penalty_real': car_overlap_penalty_total,
            'avg_car_overlap_penalty_per_overlap': car_overlap_penalty_avg,
            'avg_car_overlap_penalty_per_overlap_n': car_overlap_penalty_n,
            'queue_wait_bonus': queue_wait_bonus_total,
            'queue_wait_bonus_rows': queue_wait_bonus_rows,
            'queue_wait_bonus_rows_pct': sdiv(queue_wait_bonus_rows * 100.0, len(dbg_rows)),
            'avg_queue_wait_bonus': sdiv(queue_wait_bonus_total, len(dbg_rows)),
            'avg_queue_wait_bonus_per_life_sec_exposed': queue_wait_bonus_life_avg,
            'avg_queue_wait_bonus_per_life_sec_exposed_n': queue_wait_bonus_life_n,
            'avg_queue_wait_bonus_fit_share_exposed': queue_wait_bonus_fit_share_avg,
            'avg_queue_wait_bonus_fit_share_exposed_n': queue_wait_bonus_fit_share_n,
            'yield_free_passes': yield_free_passes_total,
            'avg_yield_free_passes': sdiv(yield_free_passes_total, len(dbg_rows)),
            'avg_yield_validation_speed_exposed': yield_validation_speed_avg,
            'avg_yield_validation_speed_exposed_n': yield_validation_speed_n,
            'crossing_blocked_time': crossing_blocked_total,
            'crossing_blocked_rows': crossing_blocked_rows,
            'crossing_blocked_rows_pct': sdiv(crossing_blocked_rows * 100.0, len(dbg_rows)),
            'avg_crossing_blocked_per_stop_tick': crossing_blocked_stop_avg,
            'avg_crossing_blocked_per_stop_tick_n': crossing_blocked_stop_n,
            'avg_crossing_blocked_per_life_sec': crossing_blocked_life_avg,
            'avg_crossing_blocked_per_life_sec_n': crossing_blocked_life_n,
            'avg_front_obst_at_death_exposed': front_obst_death_avg,
            'avg_front_obst_at_death_exposed_n': front_obst_death_n,
            'steer_approach_wrong_dir': steer_app_wrong_total,
            'steer_approach_right_dir': steer_app_right_total,
            'steer_approach_wrong_share': sdiv(steer_app_wrong_total, steer_app_wrong_total + steer_app_right_total),
            'avg_steer_approach_wrong_share_exposed': steer_app_wrong_share_avg,
            'avg_steer_approach_wrong_share_exposed_n': steer_app_wrong_share_n,
            'avg_first_steer_after_release_ticks_exposed': first_steer_release_avg,
            'avg_first_steer_after_release_ticks_exposed_n': first_steer_release_n,
            'avg_coast_t': sdiv(sum(r.get('coast_t', 0.0) for r in dbg_rows), len(dbg_rows)),
            'avg_stop_brake': sdiv(sum(r.get('stop_brake', 0.0) for r in dbg_rows), len(dbg_rows)),
            'avg_stop_throttle': sdiv(sum(r.get('stop_throttle', 0.0) for r in dbg_rows), len(dbg_rows)),
            'avg_pen_creep': sdiv(creep_total, len(dbg_rows)),
            'avg_pen_rev': sdiv(rev_total, len(dbg_rows)),
            'avg_pen_lazy': sdiv(lazy_total, len(dbg_rows)),
            'avg_pen_swstop': sdiv(steer_stop_total, len(dbg_rows)),
            'avg_pen_speed_per_life_sec_exposed': speed_penalty_life_avg,
            'avg_pen_speed_per_life_sec_exposed_n': speed_penalty_life_n,
            'avg_pen_nav': sdiv(sum(r.get('pen_nav', 0.0) for r in dbg_rows), len(dbg_rows)),
            'avg_pen_steer_app': sdiv(steer_approach_total, len(dbg_rows)),
            'avg_pen_alignment': sdiv(alignment_total, len(dbg_rows)),
            'avg_yield_val_t': sdiv(yield_val_total, len(dbg_rows)),
            'avg_stop_val_t': sdiv(stop_val_total, len(dbg_rows)),
            'avg_stop_bonus': sdiv(stop_bonus_total, len(dbg_rows)),
            'avg_yield_bonus': sdiv(yield_bonus_total, len(dbg_rows)),
            'avg_stop_done_n': sdiv(stop_done_total, len(dbg_rows)),
            'avg_yield_done_n': sdiv(yield_done_total, len(dbg_rows)),
            'avg_stop_bonus_per': stop_bonus_per_avg,
            'avg_stop_bonus_per_n': stop_bonus_per_n,
            'avg_yield_bonus_per': yield_bonus_per_avg,
            'avg_yield_bonus_per_n': yield_bonus_per_n,
            'avg_stop_done_rate': stop_done_rate_avg,
            'avg_stop_done_rate_n': stop_done_rate_n,
            'avg_yield_done_rate': yield_done_rate_avg,
            'avg_yield_done_rate_n': yield_done_rate_n,
            'avg_stop_zones_n': sdiv(sum(r.get('stop_zones_n', 0.0) for r in dbg_rows), len(dbg_rows)),
            'avg_fit_peak_raw': sdiv(sum(r.get('fit_peak_raw', 0.0) for r in dbg_rows), len(dbg_rows)),
            'avg_fit_peak_gain': sdiv(sum(r.get('fit_peak_gain', 0.0) for r in dbg_rows), len(dbg_rows)),
            'avg_steer_in': sdiv(steer_in_total, len(dbg_rows)),
            'avg_steer_target': sdiv(steer_target_total, len(dbg_rows)),
            'avg_steer_gap_abs': sdiv(steer_gap_total, len(dbg_rows)),
            'avg_steer_abs': sdiv(sum(r.get('steer_abs', 0.0) for r in dbg_rows), len(dbg_rows)),
            'avg_steer_abs_avg': sdiv(sum(r.get('steer_abs_avg', 0.0) for r in dbg_rows), len(dbg_rows)),
            'avg_steer_gap_avg_abs': sdiv(sum(r.get('steer_gap_avg_abs', 0.0) for r in dbg_rows), len(dbg_rows)),
            'avg_stop_ticks': sdiv(stop_ticks_total, len(dbg_rows)),
            'roundabout_entries': round_entered_total,
            'roundabout_completed': round_completed_total,
            'roundabout_collisions': round_collisions_total,
            'collision_deaths_total': collision_stats['total'],
            'roundabout_collision_deaths': collision_stats['roundabout'],
            'normal_collision_deaths': collision_stats['normal'],
            'roundabout_collision_death_share': sdiv(collision_stats['roundabout'], collision_stats['total']),
            'roundabout_collision_events': collision_stats['roundabout_events'],
            'roundabout_collision_signal_non_collision_rows': collision_stats['round_signal_non_collision'],
            'roundabout_bonus_breakdown_available': round_bonus_breakdown_available,
            'roundabout_bonus_net': round_bonus_total,
            'roundabout_completion_bonus': round_completion_bonus_total,
            'roundabout_entry_penalty': round_entry_penalty_total,
            'roundabout_throttle_penalty': round_throttle_penalty_total,
            'roundabout_completion_rate': sdiv(round_completed_total, round_entered_total),
            'roundabout_collision_rate': sdiv(round_collisions_total, round_entered_total),
            'roundabout_tick_share': sdiv(round_ticks_total, ticks_total),
            'avg_roundabout_entry_speed': round_entry_speed_avg,
            'avg_roundabout_entry_speed_n': round_entry_speed_n,
            'avg_roundabout_entry_front_obstacle': round_entry_front_avg,
            'avg_roundabout_entry_front_obstacle_n': round_entry_front_n,
            'avg_roundabout_steering': round_steer_avg,
            'avg_roundabout_steering_n': round_steer_n,
            'avg_roundabout_throttle': round_throttle_avg,
            'avg_roundabout_throttle_n': round_throttle_n,
            'avg_roundabout_bonus_per_entry': round_bonus_entry_avg,
            'avg_roundabout_bonus_per_entry_n': round_bonus_entry_n,
            'avg_roundabout_bonus_per_completion': round_bonus_completion_avg,
            'avg_roundabout_bonus_per_completion_n': round_bonus_completion_n,
            'avg_roundabout_bonus_per_tick': round_bonus_tick_avg,
            'avg_roundabout_bonus_per_tick_n': round_bonus_tick_n,
            'avg_roundabout_completion_bonus_per_completion': round_completion_bonus_avg,
            'avg_roundabout_completion_bonus_per_completion_n': round_completion_bonus_n,
            'avg_roundabout_entry_penalty_per_entry': round_entry_penalty_avg,
            'avg_roundabout_entry_penalty_per_entry_n': round_entry_penalty_n,
            'avg_roundabout_throttle_penalty_per_tick': round_throttle_penalty_avg,
            'avg_roundabout_throttle_penalty_per_tick_n': round_throttle_penalty_n,
            'roundabout_entry_directions': {
                'first': sum(r.get('round_dir_first', 0.0) for r in dbg_rows),
                'second': sum(r.get('round_dir_second', 0.0) for r in dbg_rows),
                'third': sum(r.get('round_dir_third', 0.0) for r in dbg_rows),
            },
            'roundabout_exit_metrics': {
                str(exit_num): {
                    'exposures': sum(r.get(f'round_exit{exit_num}_count', 0.0) for r in dbg_rows),
                    'deaths': sum(r.get(f'round_exit{exit_num}_deaths', 0.0) for r in dbg_rows),
                    'ticks': sum(r.get(f'round_exit{exit_num}_ticks', 0.0) for r in dbg_rows),
                    'death_rate': sdiv(
                        sum(r.get(f'round_exit{exit_num}_deaths', 0.0) for r in dbg_rows),
                        sum(r.get(f'round_exit{exit_num}_count', 0.0) for r in dbg_rows),
                    ),
                    'avg_steering': sdiv(
                        sum(r.get(f'round_exit{exit_num}_steer', 0.0) for r in dbg_rows),
                        sum(r.get(f'round_exit{exit_num}_ticks', 0.0) for r in dbg_rows),
                    ),
                    'avg_throttle': sdiv(
                        sum(r.get(f'round_exit{exit_num}_throttle', 0.0) for r in dbg_rows),
                        sum(r.get(f'round_exit{exit_num}_ticks', 0.0) for r in dbg_rows),
                    ),
                }
                for exit_num in (1, 2, 3)
            },
            'car_index_families': summarize_car_index_families(dbg_rows),
            'brake_share': sdiv(sum(r.get('brake_in', 0.0) for r in dbg_rows), cmd_total),
            'grace_brake_share': sdiv(sum(r.get('brake_grace', 0.0) for r in dbg_rows), grace_cmd_total),
            'stop_brake_share': sdiv(sum(r.get('stop_brake', 0.0) for r in dbg_rows), stop_cmd_total),
            'stop_ctx_tick_coverage': sdiv(stop_ticks_total, ticks_total),
            'death_families': dict(families),
            'death_families_detail': dict(families_detail),
            'stop_violation_subtypes': dict(summarize_stop_violation_subtypes(dbg_rows)),
            'death_failure_rows': death_failure_rows,
            'death_failure_pct': sdiv(death_failure_rows * 100.0, len(dbg_rows)),
        },
        'spawn_stop_percentiles': sorted(spawn_stop_stats, key=lambda x: x.get('legal_fail_pct', 0.0), reverse=True)[:20],
        'previous_sessions': previous_sessions,
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
