# -*- coding: utf-8 -*-
"""Parte interna de analyse_current.py.

Este archivo se carga desde analyse_current.py dentro del mismo namespace global
para mantener compatibilidad con los imports existentes y con la CLI antigua.
No esta pensado para ejecutarse directamente.
"""

def build_combined_summary(train_summary, test_summary):
    rows = []
    for phase, src in (('train', train_summary), ('test', test_summary)):
        ordered = sorted(src, key=lambda r: r.get('gen', 0))
        for r in ordered:
            rr = dict(r)
            rr['source_phase'] = phase
            rr['gen_phase'] = rr.get('gen', 0)
            rows.append(rr)

    # Reindexar para evitar colisiones de generacion entre train y test.
    for i, r in enumerate(rows, 1):
        r['gen'] = i
    return rows

def reindex_generations_for_analysis(summary_rows, debug_rows):
    def to_int(v, default=0):
        try:
            return int(v)
        except (TypeError, ValueError):
            return default

    def is_contiguous_one_based(vals):
        return vals == list(range(1, len(vals) + 1))

    summary_copy = [dict(r) for r in summary_rows]
    summary_copy.sort(key=lambda r: to_int(r.get('gen', 0)))
    summary_gens = sorted(set(to_int(r.get('gen', 0)) for r in summary_copy))
    summary_map = {g: i + 1 for i, g in enumerate(summary_gens)}
    for r in summary_copy:
        raw = to_int(r.get('gen', 0))
        r['gen_raw'] = raw
        r['gen'] = summary_map.get(raw, raw)

    debug_copy = [dict(r) for r in debug_rows]
    debug_gens = sorted(set(to_int(r.get('gen', 0)) for r in debug_copy))
    debug_map = {g: i + 1 for i, g in enumerate(debug_gens)}
    for r in debug_copy:
        raw = to_int(r.get('gen', 0))
        r['gen_raw'] = raw
        r['gen'] = debug_map.get(raw, raw)
    debug_copy.sort(key=lambda r: (to_int(r.get('gen', 0)), str(r.get('car', ''))))

    info = {
        'summary_raw_min': summary_gens[0] if summary_gens else 0,
        'summary_raw_max': summary_gens[-1] if summary_gens else 0,
        'summary_count': len(summary_gens),
        'summary_idx_max': len(summary_gens),
        'summary_reindexed': not is_contiguous_one_based(summary_gens) if summary_gens else False,
        'summary_mapping': [{'raw': g, 'norm': summary_map[g]} for g in summary_gens],
        'debug_raw_min': debug_gens[0] if debug_gens else 0,
        'debug_raw_max': debug_gens[-1] if debug_gens else 0,
        'debug_count': len(debug_gens),
        'debug_idx_max': len(debug_gens),
        'debug_reindexed': not is_contiguous_one_based(debug_gens) if debug_gens else False,
        'debug_mapping': [{'raw': g, 'norm': debug_map[g]} for g in debug_gens],
    }
    return summary_copy, debug_copy, info

def report_generation_normalization(R, info):
    R.p(f'\n-- Normalizacion de Generaciones (1..N) --')

    if info.get('summary_count', 0) > 0:
        state = 'aplicada' if info.get('summary_reindexed') else 'sin cambios'
        R.p(
            f'  Summary original: {info.get("summary_raw_min", 0)}..{info.get("summary_raw_max", 0)} '
            f'({info.get("summary_count", 0)} gens) -> analisis: 1..{info.get("summary_idx_max", 0)} [{state}]'
        )
    else:
        R.p('  Summary original: sin datos')

    if info.get('debug_count', 0) > 0:
        state = 'aplicada' if info.get('debug_reindexed') else 'sin cambios'
        R.p(
            f'  Debug original:   {info.get("debug_raw_min", 0)}..{info.get("debug_raw_max", 0)} '
            f'({info.get("debug_count", 0)} gens) -> analisis: 1..{info.get("debug_idx_max", 0)} [{state}]'
        )
    else:
        R.p('  Debug original:   sin datos')

def compute_auto_insights(summary_rows, dbg_rows, data_coherence=None, yield_stuck_info=None, stop_stuck_info=None):
    insights = []

    if summary_rows:
        gens = [r.get('gen', 0) for r in summary_rows]
        means = [r.get('mean', 0.0) for r in summary_rows]
        times = [r.get('time', 0.0) for r in summary_rows]

        slope_mean = trend_slope(gens, means)
        if slope_mean > 0:
            insights.append(f'Tendencia MeanFit positiva ({slope_mean:+.4f}/gen normalizada).')
        elif slope_mean < 0:
            insights.append(f'Tendencia MeanFit negativa ({slope_mean:+.4f}/gen normalizada).')
        else:
            insights.append('Tendencia MeanFit plana.')

        slope_time = trend_slope(gens, times)
        if slope_time > 0:
            insights.append(f'Tiempo medio de vida en aumento ({slope_time:+.3f}s/gen).')
        elif slope_time < 0:
            insights.append(f'Tiempo medio de vida en descenso ({slope_time:+.3f}s/gen).')

        neg_pct = sdiv(sum(1 for v in means if v < 0) * 100.0, len(means))
        if neg_pct >= 20.0:
            insights.append(f'Porcentaje alto de generaciones con MeanFit negativo ({neg_pct:.1f}%).')

        mean_cv = coef_var(means) * 100.0
        if mean_cv >= 60.0:
            insights.append(f'Volatilidad alta en MeanFit (CV={mean_cv:.1f}%).')

        kpi_rows = [r for r in summary_rows if 'success_rate' in r]
        if kpi_rows:
            avg_success = mean([r.get('success_rate', 0.0) for r in kpi_rows])
            if avg_success < 5.0:
                insights.append(f'Acierto medio bajo en test ({avg_success:.2f}%). Prioridad: robustecer politica.')
            elif avg_success >= 20.0:
                insights.append(f'Acierto medio solido en test ({avg_success:.2f}%).')

    if dbg_rows:
        n_dbg = len(dbg_rows)
        lazy_rows = sum(1 for r in dbg_rows if is_lazy_reason(r.get('death', '')))
        lazy_list = [r for r in dbg_rows if is_lazy_reason(r.get('death', ''))]
        non_lazy_list = [r for r in dbg_rows if not is_lazy_reason(r.get('death', ''))]
        lazy_pct = sdiv(lazy_rows * 100.0, n_dbg)
        if lazy_pct >= 10.0:
            insights.append(f'LAZY elevado ({lazy_pct:.2f}%). Revisar reward de avance o criterios de estancamiento.')
        elif lazy_pct > 0.0:
            insights.append(f'LAZY contenido ({lazy_pct:.2f}%).')

        if lazy_list:
            lazy_stop0_n = sum(1 for r in lazy_list if r.get('t_stop_ctx', 0.0) <= 0.0)
            lazy_stop_low_n = sum(
                1 for r in lazy_list
                if sdiv(r.get('t_stop_ctx', 0.0), max(r.get('t_tot', 0.0), 1.0)) < 0.01
            )
            lazy_stop_hi_n = sum(
                1 for r in lazy_list
                if sdiv(r.get('t_stop_ctx', 0.0), max(r.get('t_tot', 0.0), 1.0)) >= 0.10
            )
            lazy_stop_low_pct = sdiv(lazy_stop_low_n * 100.0, len(lazy_list))
            lazy_stop_hi_pct = sdiv(lazy_stop_hi_n * 100.0, len(lazy_list))

            if lazy_stop_low_pct >= 70.0:
                insights.append(
                    f'La mayoria de LAZY ocurre fuera de stop/semaforo (<1% stop-context en {lazy_stop_low_pct:.1f}%; '
                    f'StopTicks==0 en {sdiv(lazy_stop0_n*100.0, len(lazy_list)):.1f}%). '
                    f'Revisar spawn cercano a control no detectado y ventana anti-LAZY inicial.'
                )
            elif lazy_stop_hi_pct >= 50.0:
                insights.append(
                    f'Gran parte de LAZY ocurre dentro de stop/semaforo (>=10% stop-context en {lazy_stop_hi_pct:.1f}%). '
                    f'Revisar logica de liberacion en ceda/stop y colas de cruce.'
                )

        deaths = Counter(r.get('death', '') for r in dbg_rows if r.get('death', ''))
        if deaths:
            top_death, top_n = deaths.most_common(1)[0]
            insights.append(f'Razon de muerte dominante: {top_death} ({sdiv(top_n*100.0, n_dbg):.1f}%).')

            family_counts = Counter(death_family(r.get('death', '')) for r in dbg_rows if r.get('death', ''))
            invalid_brain = family_counts.get('INVALID_BRAIN', 0)
            if invalid_brain > 0:
                insights.append(f'INVALID_BRAIN detectado en {invalid_brain} coches; revisar guardas de ProcessAI y longitud de entradas/pesos.')

            legal_fail_pct = sdiv(family_counts.get('VIOLATION', 0) * 100.0, n_dbg)
            if legal_fail_pct > 0.0:
                insights.append(f'Fallo legal (stop+traffic+yield+nav): {legal_fail_pct:.2f}% de coches.')
                stop_violation_detail = summarize_stop_violation_subtypes(dbg_rows)
                if stop_violation_detail:
                    insights.append(
                        'STOP_VIOLATION 30/06 desglosado: '
                        f'EXIT={stop_violation_detail.get("EXIT", 0)}, '
                        f'TIMEOUT={stop_violation_detail.get("TIMEOUT", 0)}, '
                        f'GENERIC={stop_violation_detail.get("GENERIC", 0)}.'
                    )

            collision_stats = summarize_collision_deaths(dbg_rows)
            if collision_stats['total'] > 0:
                insights.append(
                    f'Colisiones: {collision_stats["roundabout"]} en rotonda '
                    f'({sdiv(collision_stats["roundabout"]*100.0, collision_stats["total"]):.1f}% de colisiones) '
                    f'y {collision_stats["normal"]} normales.'
                )

        mutation_rows = [
            r for r in dbg_rows
            if not r.get('is_weight_initialization', False)
            and str(r.get('mutation_kind', '')).startswith('MUT_')
        ]
        if mutation_rows:
            mut_rate_med = pctl([r.get('mut_rate', 0.0) for r in mutation_rows], 50) * 100.0
            insights.append(
                f'Mutacion dinamica 26/06: MutRate mediano {mut_rate_med:.2f}% '
                f'(rango normal {MUTATION_RATE_DYNAMIC_MIN*100:.2f}%..{MUTATION_RATE_DYNAMIC_MAX*100:.2f}%, '
                f'familia grande {MUTATION_RATE_LARGE_MIN*100:.2f}%..{MUTATION_RATE_LARGE_MAX*100:.2f}%).'
            )

        cmd_thr = sum(r.get('thr_pos', 0.0) for r in dbg_rows)
        thr_grace = sum(r.get('thr_grace', 0.0) for r in dbg_rows)
        brake_grace = sum(r.get('brake_grace', 0.0) for r in dbg_rows)
        cmd_brk = sum(r.get('brake_in', 0.0) for r in dbg_rows)
        stop_brk = sum(r.get('stop_brake', 0.0) for r in dbg_rows)
        stop_thr = sum(r.get('stop_throttle', 0.0) for r in dbg_rows)
        total_ticks = sum(r.get('t_tot', 0.0) for r in dbg_rows)
        stop_ticks = sum(r.get('t_stop_ctx', 0.0) for r in dbg_rows)
        yield_val_total = sum(r.get('yield_val_t', 0.0) for r in dbg_rows)
        stop_val_total = sum(r.get('stop_val_t', 0.0) for r in dbg_rows)
        stop_bonus_total = sum(r.get('stop_bonus', 0.0) for r in dbg_rows)
        yield_bonus_total = sum(r.get('yield_bonus', 0.0) for r in dbg_rows)
        stop_done_total = sum(r.get('stop_done_n', 0.0) for r in dbg_rows)
        yield_done_total = sum(r.get('yield_done_n', 0.0) for r in dbg_rows)
        stop_zones_total = sum(r.get('stop_zones_n', 0.0) for r in dbg_rows)
        round_entered_total = sum(r.get('round_entered_n', 0.0) for r in dbg_rows)
        round_completed_total = sum(r.get('round_completed_n', 0.0) for r in dbg_rows)
        round_collisions_total = sum(r.get('round_collisions', 0.0) for r in dbg_rows)
        round_ticks_total = sum(r.get('round_ticks', 0.0) for r in dbg_rows)
        round_bonus_total = sum(r.get('round_bonus', 0.0) for r in dbg_rows)
        round_completion_bonus_total = sum(r.get('round_completion_bonus', 0.0) for r in dbg_rows)
        round_entry_penalty_total = sum(r.get('round_entry_penalty', 0.0) for r in dbg_rows)
        round_throttle_penalty_total = sum(r.get('round_throttle_penalty', 0.0) for r in dbg_rows)
        steer_in_total = sum(r.get('steer_in', 0.0) for r in dbg_rows)
        steer_target_total = sum(r.get('steer_target', 0.0) for r in dbg_rows)
        steer_gap_total = sum(abs(r.get('steer_in', 0.0) - r.get('steer_target', 0.0)) for r in dbg_rows)
        creep_pen = sum(r.get('pen_creep', 0.0) for r in dbg_rows)
        rev_pen = sum(r.get('pen_rev', 0.0) for r in dbg_rows)
        lazy_pen = sum(r.get('pen_lazy', 0.0) for r in dbg_rows)
        steer_stop_pen = sum(r.get('pen_swstop', 0.0) for r in dbg_rows)
        align_pen = sum(r.get('pen_align', 0.0) for r in dbg_rows)
        nav_pen = sum(r.get('pen_nav', 0.0) for r in dbg_rows)
        car_overlap_total = sum(r.get('car_overlaps', 0.0) for r in dbg_rows)
        car_overlap_rows = sum(1 for r in dbg_rows if r.get('car_overlaps', 0.0) > 0.0)
        car_overlap_penalty_total = sum(r.get('car_overlap_penalty', 0.0) for r in dbg_rows)
        queue_wait_bonus_total = sum(r.get('queue_wait_bonus', 0.0) for r in dbg_rows)
        queue_wait_bonus_rows = sum(1 for r in dbg_rows if r.get('queue_wait_bonus', 0.0) > 0.0)
        yield_free_passes_total = sum(r.get('yield_free_passes', 0.0) for r in dbg_rows)
        crossing_blocked_total = sum(r.get('crossing_blocked_t', 0.0) for r in dbg_rows)
        crossing_blocked_rows = sum(1 for r in dbg_rows if r.get('crossing_blocked_t', 0.0) > 0.0)
        car_overlap_shadow_total = sum(r.get('car_overlap_pen_shadow', 0.0) for r in dbg_rows)
        steer_app_wrong_total = sum(r.get('steer_app_wrong', 0.0) for r in dbg_rows)
        steer_app_right_total = sum(r.get('steer_app_right', 0.0) for r in dbg_rows)
        first_steer_release_vals = metric_values(dbg_rows, 'first_steer_release_ticks')

        brake_share_global = sdiv(cmd_brk, cmd_brk + cmd_thr)
        stop_brake_share = sdiv(stop_brk, stop_brk + stop_thr)
        stop_ctx_coverage = sdiv(stop_ticks, total_ticks)

        if stop_ctx_coverage > 0.0:
            insights.append(f'Cobertura de contexto stop/semaforo: {stop_ctx_coverage*100:.2f}% de ticks.')

        if debug_field_available(dbg_rows, 'car_overlaps') and car_overlap_total > 0.0:
            insights.append(
                f'Solapes entre coches 26/06: {car_overlap_total:.0f} eventos en '
                f'{car_overlap_rows}/{n_dbg} coches ({sdiv(car_overlap_rows*100.0, n_dbg):.2f}%).'
            )
            if debug_field_available(dbg_rows, 'car_overlap_pen_shadow') and car_overlap_shadow_total > 0.0:
                insights.append(
                    f'Sombra de penalty por solape 30/06: {car_overlap_shadow_total:.2f} '
                    f'({sdiv(car_overlap_shadow_total, car_overlap_total):.2f}/overlap).'
                )
            if debug_field_available(dbg_rows, 'car_overlap_penalty') and car_overlap_penalty_total > 0.0:
                insights.append(
                    f'Penalty real por solape 01/07: {car_overlap_penalty_total:.2f} '
                    f'({sdiv(car_overlap_penalty_total, car_overlap_total):.2f}/overlap).'
                )

        if debug_field_available(dbg_rows, 'queue_wait_bonus') and queue_wait_bonus_total > 0.0:
            insights.append(
                f'QueueWaitBonus 01/07: {queue_wait_bonus_total:.2f} acumulado en '
                f'{queue_wait_bonus_rows}/{n_dbg} coches ({sdiv(queue_wait_bonus_rows*100.0, n_dbg):.2f}%).'
            )

        if debug_field_available(dbg_rows, 'yield_free_passes') and yield_free_passes_total > 0.0:
            insights.append(
                f'Cedas libres 30/06: {yield_free_passes_total:.0f} validaciones sin coche bloqueando '
                f'({sdiv(yield_free_passes_total, n_dbg):.2f}/coche).'
            )

        if debug_field_available(dbg_rows, 'crossing_blocked_t') and crossing_blocked_total > 0.0:
            insights.append(
                f'Tiempo bloqueado en cruce 30/06: {crossing_blocked_total:.2f}s en '
                f'{crossing_blocked_rows}/{n_dbg} coches ({sdiv(crossing_blocked_rows*100.0, n_dbg):.2f}%).'
            )

        if debug_field_available(dbg_rows, 'first_steer_release_ticks') and first_steer_release_vals:
            insights.append(
                f'Reaccion tras release 30/06: FirstSteerAfterRelease P50={pctl(first_steer_release_vals, 50):.1f} '
                f'ticks, P90={pctl(first_steer_release_vals, 90):.1f}.'
            )

        if (debug_field_available(dbg_rows, 'steer_app_wrong') or debug_field_available(dbg_rows, 'steer_app_right')) and (steer_app_wrong_total + steer_app_right_total) > 0.0:
            wrong_share = sdiv(steer_app_wrong_total, steer_app_wrong_total + steer_app_right_total)
            insights.append(
                f'SteerApproach 30/06: wrong={steer_app_wrong_total:.2f}, right={steer_app_right_total:.2f} '
                f'(wrong share={wrong_share*100:.1f}%).'
            )
            if wrong_share >= 0.60:
                insights.append('La mayor parte de SteerApproachPenalty viene de direccion incorrecta; revisar signo/target de aproximacion.')

        if (yield_val_total + stop_val_total) > 0.0:
            insights.append(
                f'Ventanas de validacion acumuladas: Yield={sdiv(yield_val_total, n_dbg):.2f}s y '
                f'Stop={sdiv(stop_val_total, n_dbg):.2f}s por coche.'
            )

        if (stop_done_total + yield_done_total) > 0:
            insights.append(
                f'Completados: Stop={sdiv(stop_done_total, n_dbg):.2f}/coche (bonus {sdiv(stop_bonus_total, n_dbg):.2f}), '
                f'Yield={sdiv(yield_done_total, n_dbg):.2f}/coche (bonus {sdiv(yield_bonus_total, n_dbg):.2f}).'
            )
            if debug_field_available(dbg_rows, 'queue_wait_bonus') and queue_wait_bonus_total > 0.0:
                insights.append(f'Bonus de espera en cola: {sdiv(queue_wait_bonus_total, n_dbg):.2f}/coche de media global.')

        if stop_zones_total > 0:
            stop_done_rate = sdiv(stop_done_total, stop_zones_total)
            yield_done_rate = sdiv(yield_done_total, stop_zones_total)
            if stop_done_total == 0:
                insights.append('No hay stops completados pese a entradas en zonas de stop; revisar ApplyStopCompletionBonus y la logica de cruce.')
            elif stop_done_rate < 0.15:
                insights.append(f'Baja finalizacion de stop (StopDone/StopZones={stop_done_rate*100:.1f}%).')
            if yield_done_total == 0 and yield_val_total > 0.0:
                insights.append('No hay yields completados pese a validacion de ceda; revisar ApplyYieldCompletionBonus y liberacion de cruce.')
            elif yield_done_rate < 0.10 and yield_done_total > 0:
                insights.append(f'Baja finalizacion de yield (YieldDone/StopZones={yield_done_rate*100:.1f}%).')

        if round_entered_total > 0:
            round_completion_rate = sdiv(round_completed_total, round_entered_total)
            round_collision_rate = sdiv(round_collisions_total, round_entered_total)
            insights.append(
                f'Rotondas: {round_entered_total:.0f} entradas, {round_completed_total:.0f} completaciones '
                f'confirmadas por reentrada ({round_completion_rate*100:.1f}%, limite inferior), '
                f'{round_collisions_total:.0f} colisiones '
                f'({round_collision_rate*100:.1f}% por entrada).'
            )
            if total_ticks > 0:
                insights.append(f'Cobertura en rotonda: {sdiv(round_ticks_total*100.0, total_ticks):.2f}% de ticks.')
            if debug_field_available(dbg_rows, 'round_bonus'):
                bonus_per_entry = sdiv(round_bonus_total, round_entered_total)
                bonus_per_tick = sdiv(round_bonus_total, round_ticks_total)
                insights.append(
                    f'RoundaboutBonus neto: {round_bonus_total:.2f} '
                    f'({bonus_per_entry:.2f}/entrada, {bonus_per_tick:.4f}/tick en rotonda).'
                )
                if debug_field_available(dbg_rows, 'round_completion_bonus'):
                    insights.append(
                        f'Desglose RoundaboutBonus: +{round_completion_bonus_total:.2f} completado, '
                        f'-{round_entry_penalty_total:.2f} entrada, -{round_throttle_penalty_total:.2f} throttle.'
                    )
                    if round_throttle_penalty_total > round_completion_bonus_total * 0.5:
                        insights.append('El penalty de throttle en rotonda pesa mucho frente al bonus de completado; revisar aceleracion dentro de rotonda.')
                    if round_entry_penalty_total > round_completion_bonus_total * 0.5:
                        insights.append('El penalty de entrada a rotonda pesa mucho frente al bonus de completado; revisar velocidad/distancia al entrar.')
                if round_bonus_total < 0.0:
                    insights.append('RoundaboutBonus neto negativo; el castigo de throttle en rotonda esta superando los bonus de entrada/completado.')
            if round_collision_rate >= 0.20:
                insights.append('Tasa alta de colision en rotonda (>=20% por entrada); revisar velocidad de entrada y steering dentro de la rotonda.')
            if round_completed_total == 0:
                insights.append(
                    'No hay completaciones de rotonda confirmadas por una entrada posterior; '
                    'puede faltar una segunda entrada o existir un problema en el registro.'
                )
            if debug_field_available(dbg_rows, 'round_exit1_count'):
                exit_stats = []
                for exit_num, label in ((1, 'Exit1'), (2, 'Exit2'), (3, 'Exit3+')):
                    count = sum(r.get(f'round_exit{exit_num}_count', 0.0) for r in dbg_rows)
                    deaths = sum(r.get(f'round_exit{exit_num}_deaths', 0.0) for r in dbg_rows)
                    ticks = sum(r.get(f'round_exit{exit_num}_ticks', 0.0) for r in dbg_rows)
                    exit_stats.append({
                        'label': label,
                        'count': count,
                        'deaths': deaths,
                        'death_rate': sdiv(deaths, count),
                        'steer': sdiv(sum(r.get(f'round_exit{exit_num}_steer', 0.0) for r in dbg_rows), ticks),
                        'throttle': sdiv(sum(r.get(f'round_exit{exit_num}_throttle', 0.0) for r in dbg_rows), ticks),
                    })
                exposed = [x for x in exit_stats if x['count'] > 0]
                if exposed:
                    worst = max(exposed, key=lambda x: x['death_rate'])
                    insights.append(
                        f'Tramo de rotonda mas critico: {worst["label"]} con '
                        f'{worst["deaths"]:.0f}/{worst["count"]:.0f} muertes '
                        f'({worst["death_rate"]*100:.1f}%), steering/tick={worst["steer"]:.3f}, '
                        f'throttle/tick={worst["throttle"]:.3f}.'
                    )
                if len(exposed) < 2:
                    insights.append(
                        'Solo hay exposicion registrada en un tramo de salida de rotonda; '
                        'todavia no se pueden comparar Exit1, Exit2 y Exit3+.'
                    )

        if (steer_in_total + steer_target_total) > 0.0:
            avg_steer_gap = sdiv(steer_gap_total, n_dbg)
            steer_gap_ratio = sdiv(steer_gap_total, max(abs(steer_target_total), 1e-6))
            insights.append(
                f'Seguimiento steering: Input={sdiv(steer_in_total, n_dbg):.2f}, '
                f'Target={sdiv(steer_target_total, n_dbg):.2f}, GapAbs={avg_steer_gap:.2f} por coche.'
            )
            if steer_gap_ratio >= 0.25:
                insights.append(
                    f'Desacople alto entre steering input y target (Gap/Target={steer_gap_ratio*100:.1f}%); '
                    f'revisar limites de suavizado en control.'
                )
            elif steer_gap_ratio <= 0.08:
                insights.append(
                    f'Seguimiento de steering estable (Gap/Target={steer_gap_ratio*100:.1f}%).'
                )

        car_fams = summarize_car_index_families(dbg_rows)
        if car_fams:
            top_family = max(car_fams, key=lambda x: (x['fit_mean'], x['n']))
            if top_family['family'] in ('MUT_LOADED', 'MUT_SESSION', 'MUT_LOADED_LARGE'):
                insights.append(
                    f'La familia CarIndex con mejor fitness medio es {top_family["family"]} '
                    f'({top_family["fit_mean"]:.2f}).'
                )
            elif top_family['family'] == 'RANDOM':
                insights.append(
                    f'Los cerebros InitializeRandomBrain lideran el fitness medio ({top_family["fit_mean"]:.2f}); '
                    f'puede indicar que las semillas actuales limitan la exploracion.'
                )
            elif top_family['family'] == 'SESSION':
                insights.append(
                    f'La semilla SESSION lidera el fitness medio ({top_family["fit_mean"]:.2f}); '
                    f'conviene revisar si la mutacion añade mejora real.'
                )

        if creep_pen > 0.0:
            insights.append(f'Penalty de creeping acumulado: media {sdiv(creep_pen, n_dbg):.2f} por coche.')
        if nav_pen > 0.0:
            insights.append(f'Penalty de navegacion acumulado: media {sdiv(nav_pen, n_dbg):.2f} por coche.')
        if rev_pen > 0.0:
            insights.append(f'Penalty de marcha atras acumulado: media {sdiv(rev_pen, n_dbg):.2f} por coche.')
        if lazy_pen > 0.0:
            insights.append(f'Penalty de estancamiento (lazy) acumulado: media {sdiv(lazy_pen, n_dbg):.2f} por coche.')
        if steer_stop_pen > 0.0:
            insights.append(f'Penalty por giro en parado acumulado: media {sdiv(steer_stop_pen, n_dbg):.2f} por coche.')
        steer_approach_pen = sum(r.get('pen_steer_app', 0.0) for r in dbg_rows)
        if steer_approach_pen > 0.0:
            insights.append(f'Penalty por aproximacion con steering acumulado: media {sdiv(steer_approach_pen, n_dbg):.2f} por coche.')
            if steer_stop_pen > 0.0 and steer_approach_pen > steer_stop_pen:
                insights.append('La penalizacion por aproximacion de steering supera la de giro en parado; revisar suavizado antes de la fase stop.')
        if align_pen > 0.0:
            insights.append(f'Penalty de alineacion acumulado: media {sdiv(align_pen, n_dbg):.2f} por coche.')
            if align_pen > steer_approach_pen and steer_approach_pen > 0.0:
                insights.append('La penalizacion de alineacion supera a SteerApproach; revisar orientacion respecto a la linea de stop/ceda/semaforo.')
        if abs(thr_grace) > 0.0:
            insights.append(f'Acum_ThrottleDuringGraceTime medio: {sdiv(thr_grace, n_dbg):.2f} por coche.')
        if abs(brake_grace) > 0.0:
            insights.append(f'Acum_BrakeDuringGraceTime medio: {sdiv(brake_grace, n_dbg):.2f} por coche.')
        if abs(brake_grace) > (abs(thr_grace) + 0.1):
            insights.append('Predomina el frenado durante ventana de gracia frente al throttle; revisar salida de resume-grace y umbral anti-LAZY.')

        if lazy_list and non_lazy_list:
            lazy_grace = mean([r.get('thr_grace', 0.0) for r in lazy_list])
            non_lazy_grace = mean([r.get('thr_grace', 0.0) for r in non_lazy_list])
            lazy_brake_grace = mean([r.get('brake_grace', 0.0) for r in lazy_list])
            non_lazy_brake_grace = mean([r.get('brake_grace', 0.0) for r in non_lazy_list])
            lazy_yield_val = mean([r.get('yield_val_t', 0.0) for r in lazy_list])
            non_lazy_yield_val = mean([r.get('yield_val_t', 0.0) for r in non_lazy_list])
            lazy_stop_val = mean([r.get('stop_val_t', 0.0) for r in lazy_list])
            non_lazy_stop_val = mean([r.get('stop_val_t', 0.0) for r in non_lazy_list])
            lazy_steer_gap = mean_abs_delta(lazy_list, 'steer_in', 'steer_target') if lazy_list else 0.0
            non_lazy_steer_gap = mean_abs_delta(non_lazy_list, 'steer_in', 'steer_target') if non_lazy_list else 0.0
            if lazy_grace > (non_lazy_grace + 0.1):
                insights.append(
                    f'En LAZY se acumula mas throttle durante ventana de gracia '
                    f'({lazy_grace:.2f} vs {non_lazy_grace:.2f}); revisar salida de resume-grace y umbral de estancamiento.'
                )
            if lazy_brake_grace > (non_lazy_brake_grace + 0.1):
                insights.append(
                    f'En LAZY se acumula mas brake durante ventana de gracia '
                    f'({lazy_brake_grace:.2f} vs {non_lazy_brake_grace:.2f}); revisar comportamiento de reanudacion tras stop/semaforo.'
                )
            if lazy_yield_val > (non_lazy_yield_val + 0.1):
                insights.append(
                    f'En LAZY hay mayor tiempo de validacion de ceda '
                    f'({lazy_yield_val:.2f}s vs {non_lazy_yield_val:.2f}s); revisar liberacion y logica de cruce.'
                )
            if lazy_stop_val > (non_lazy_stop_val + 0.1):
                insights.append(
                    f'En LAZY hay mayor tiempo de validacion de stop '
                    f'({lazy_stop_val:.2f}s vs {non_lazy_stop_val:.2f}s); revisar umbral/condicion de salida de stop.'
                )
            if lazy_steer_gap > (non_lazy_steer_gap + 0.05):
                insights.append(
                    f'En LAZY hay mayor desacople de steering input/target '
                    f'({lazy_steer_gap:.2f} vs {non_lazy_steer_gap:.2f}); revisar suavizado y control de direccion en baja velocidad.'
                )

        if lazy_pen > 0.0:
            by_spawn_lazy = defaultdict(list)
            for r in dbg_rows:
                sp = r.get('spawn', '')
                if sp:
                    by_spawn_lazy[sp].append(r)
            if by_spawn_lazy:
                top_spawn, top_rows = max(
                    by_spawn_lazy.items(),
                    key=lambda kv: mean([x.get('pen_lazy', 0.0) for x in kv[1]]),
                )
                top_lazy_vals = [x.get('pen_lazy', 0.0) for x in top_rows]
                top_lazy_n = sum(1 for x in top_rows if is_lazy_reason(x.get('death', '')))
                insights.append(
                    f'Hotspot Penalty_Lazy por spawn: {top_spawn.replace("TargetPoint", "TP")} '
                    f'(media {mean(top_lazy_vals):.2f}, P90 {pctl(top_lazy_vals, 90):.2f}, '
                    f'LAZY {top_lazy_n}/{len(top_rows)}={sdiv(top_lazy_n*100.0, len(top_rows)):.1f}%).'
                )

            by_death_lazy = defaultdict(list)
            for r in dbg_rows:
                dr = r.get('death', '')
                if dr:
                    by_death_lazy[dr].append(r)
            min_rows = max(5, int(n_dbg * 0.01))
            death_candidates = [(dr, rows_dr) for dr, rows_dr in by_death_lazy.items() if len(rows_dr) >= min_rows]
            if death_candidates:
                top_death_lazy, top_rows = max(
                    death_candidates,
                    key=lambda kv: mean([x.get('pen_lazy', 0.0) for x in kv[1]]),
                )
                top_lazy_vals = [x.get('pen_lazy', 0.0) for x in top_rows]
                insights.append(
                    f'Hotspot Penalty_Lazy por muerte: {top_death_lazy} '
                    f'(N={len(top_rows)}, media {mean(top_lazy_vals):.2f}, P90 {pctl(top_lazy_vals, 90):.2f}).'
                )

        reverse_rows = sum(1 for r in dbg_rows if is_reverse_reason(r.get('death', '')))
        if reverse_rows > 0 and rev_pen > 0.0:
            insights.append(
                f'Hay señal de marcha atras en {reverse_rows} muertes etiquetadas como REVERSE/REVERSING_WRONG '
                f'y penalty medio de reverse {sdiv(rev_pen, n_dbg):.2f}.'
            )

        if (stop_brk + stop_thr) > 0.0 and (cmd_brk + cmd_thr) > 0.0:
            if stop_brake_share < brake_share_global:
                insights.append(
                    'En contexto stop/semaforo se frena proporcionalmente menos que en global '
                    f'({stop_brake_share*100:.2f}% vs {brake_share_global*100:.2f}%).'
                )
            elif stop_brake_share > brake_share_global:
                insights.append(
                    'En contexto stop/semaforo se frena proporcionalmente mas que en global '
                    f'({stop_brake_share*100:.2f}% vs {brake_share_global*100:.2f}%).'
                )

        by_spawn = defaultdict(list)
        for r in dbg_rows:
            by_spawn[r.get('spawn', '')].append(r)
        spawn_stats = []
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
            spawn_stats.append({
                'spawn': sp,
                'n': nsp,
                'legal_fail_pct': sdiv(legal_fail_n * 100.0, nsp),
                'stop_ctx_p50': pctl(stop_cov_vals, 50),
                'stop_brake_p50': pctl(stop_share_vals, 50),
            })

        if spawn_stats:
            legal_ref = [x['legal_fail_pct'] for x in spawn_stats if x['legal_fail_pct'] > 0.0 and x['n'] >= MIN_SPAWN_N]
            q3_legal = pctl(legal_ref, 75) if legal_ref else 0.0
            stop_ctx_ref = [x['stop_ctx_p50'] for x in spawn_stats if x['stop_ctx_p50'] > 0.0]
            q3_stop_ctx = pctl(stop_ctx_ref, 75) if stop_ctx_ref else 0.0
            hot_legal = sorted(
                [x for x in spawn_stats if x['legal_fail_pct'] >= q3_legal and x['legal_fail_pct'] > 0.0 and x['n'] >= MIN_SPAWN_N],
                key=lambda x: x['legal_fail_pct'],
                reverse=True,
            )
            if hot_legal:
                top_tags = ', '.join(f"{x['spawn'].replace('TargetPoint','TP')}:{x['legal_fail_pct']:.1f}%" for x in hot_legal[:5])
                insights.append(f'Spawns con fallo legal alto (>=P75={q3_legal:.2f}%): {top_tags}.')
            low_n_legal = [x for x in spawn_stats if x['legal_fail_pct'] > 0.0 and x['n'] < MIN_SPAWN_N]
            if low_n_legal:
                insights.append(f'Se omitieron {len(low_n_legal)} spawns con violaciones por N<{MIN_SPAWN_N}; faltan mas datos.')

            hot_stop_ctx = sorted(
                [x for x in spawn_stats if x['stop_ctx_p50'] >= q3_stop_ctx and x['stop_ctx_p50'] > 0.0],
                key=lambda x: x['stop_ctx_p50'],
                reverse=True,
            )
            if hot_stop_ctx:
                top_tags = ', '.join(f"{x['spawn'].replace('TargetPoint','TP')}:{x['stop_ctx_p50']:.1f}%" for x in hot_stop_ctx[:5])
                insights.append(f'Spawns con mayor exposicion stop-context (>=P75={q3_stop_ctx:.2f}%): {top_tags}.')

        if yield_stuck_info is None:
            yield_stuck_info = detect_yield_stuck_candidates(dbg_rows)
        tf_rows = yield_stuck_info.get('timefinished_rows', 0)
        cand_rows = yield_stuck_info.get('candidate_count', 0)
        watch_rows = yield_stuck_info.get('watch_count', 0)
        cand_thr = yield_stuck_info.get('score_candidate_thr', 0.0)
        watch_thr = yield_stuck_info.get('score_watch_thr', 0.0)
        if tf_rows > 0:
            if cand_rows > 0:
                insights.append(
                    f'Posible atasco en ceda: {cand_rows}/{tf_rows} TIME_FINISHED '
                    f'({yield_stuck_info.get("candidate_pct_timefinished", 0.0):.2f}%) con bajo fitness y alto stop-context '
                    f'(score>={cand_thr:.2f}).'
                )
                top_spawn = (yield_stuck_info.get('spawns') or [{}])[0]
                if top_spawn.get('spawn'):
                    insights.append(
                        f'Hotspot atasco-ceda por spawn: {top_spawn.get("spawn", "").replace("TargetPoint", "TP")} '
                        f'(Cand={top_spawn.get("n", 0)}, TF={top_spawn.get("tf_n", 0)}, '
                        f'StopCtxP50={top_spawn.get("stop_ctx_p50", 0.0):.1f}%, FitMed={top_spawn.get("fit_med", 0.0):.1f}).'
                    )
                top_gen = (yield_stuck_info.get('gens') or [{}])[0]
                if top_gen.get('gen', 0) > 0:
                    insights.append(
                        f'Generacion mas afectada por atasco-ceda: G{top_gen.get("gen", 0)} '
                        f'(Cand={top_gen.get("n", 0)}, TF={top_gen.get("tf_n", 0)}, '
                        f'Cand/TF={top_gen.get("cand_pct_tf", 0.0):.1f}%).'
                    )
            elif watch_rows > 0:
                insights.append(
                    f'Se detectan {watch_rows}/{tf_rows} TIME_FINISHED en vigilancia de posible atasco en ceda '
                    f'(score>={watch_thr:.2f}, sin suficiente evidencia fuerte todavia).'
                )

        if stop_stuck_info is None:
            stop_stuck_info = detect_stop_stuck_candidates(dbg_rows)
        tf_rows_stop = stop_stuck_info.get('timefinished_rows', 0)
        cand_rows_stop = stop_stuck_info.get('candidate_count', 0)
        watch_rows_stop = stop_stuck_info.get('watch_count', 0)
        cand_thr_stop = stop_stuck_info.get('score_candidate_thr', 0.0)
        watch_thr_stop = stop_stuck_info.get('score_watch_thr', 0.0)
        if tf_rows_stop > 0:
            if cand_rows_stop > 0:
                insights.append(
                    f'Posible atasco en stop: {cand_rows_stop}/{tf_rows_stop} TIME_FINISHED '
                    f'({stop_stuck_info.get("candidate_pct_timefinished", 0.0):.2f}%) con alto stop-context '
                    f'y validacion de stop (score>={cand_thr_stop:.2f}).'
                )
                cause_counts = stop_stuck_info.get('candidate_cause_counts', {})
                if cause_counts:
                    top_cause = max(cause_counts.items(), key=lambda kv: kv[1])
                    insights.append(
                        f'Causa dominante en StopTrap (candidatos): {top_cause[0]} ({top_cause[1]} casos).'
                    )
                top_spawn = (stop_stuck_info.get('spawns') or [{}])[0]
                if top_spawn.get('spawn'):
                    insights.append(
                        f'Hotspot atasco-stop por spawn: {top_spawn.get("spawn", "").replace("TargetPoint", "TP")} '
                        f'(Cand={top_spawn.get("n", 0)}, TF={top_spawn.get("tf_n", 0)}, '
                        f'StopCtxP50={top_spawn.get("stop_ctx_p50", 0.0):.1f}%, FitMed={top_spawn.get("fit_med", 0.0):.1f}).'
                    )
                top_gen = (stop_stuck_info.get('gens') or [{}])[0]
                if top_gen.get('gen', 0) > 0:
                    insights.append(
                        f'Generacion mas afectada por atasco-stop: G{top_gen.get("gen", 0)} '
                        f'(Cand={top_gen.get("n", 0)}, TF={top_gen.get("tf_n", 0)}, '
                        f'Cand/TF={top_gen.get("cand_pct_tf", 0.0):.1f}%).'
                    )
            elif watch_rows_stop > 0:
                insights.append(
                    f'Se detectan {watch_rows_stop}/{tf_rows_stop} TIME_FINISHED en vigilancia de posible atasco en stop '
                    f'(score>={watch_thr_stop:.2f}, sin suficiente evidencia fuerte todavia).'
                )

    if data_coherence:
        status = data_coherence.get('status', 'ok')
        if status == 'critical':
            insights.append('ALERTA de coherencia entre Summary y Debug: alto riesgo de mezclar sesiones o usar Debug parcial.')
        elif status == 'warning':
            insights.append('Advertencia de coherencia entre Summary y Debug: revisar cobertura antes de concluir.')

        for w in data_coherence.get('warnings', [])[:3]:
            insights.append(f'Coherencia: {w}')

    if not insights:
        insights.append('Sin alertas automaticas relevantes con los datos actuales.')
    return insights

def report_auto_insights(R, insights):
    R.p(f'\n-- Insights Automaticos --')
    for line in insights:
        R.p(f'  - {line}')

def fmt_num(value, digits=2):
    try:
        fv = float(value)
    except (TypeError, ValueError):
        return '-'
    if not math.isfinite(fv):
        return '-'
    return f'{fv:.{digits}f}'

def fmt_pct_value(value, digits=2):
    return f'{fmt_num(value, digits)}%'

def fmt_pct_ratio(num_value, den_value, digits=2):
    return fmt_pct_value(sdiv(float(num_value) * 100.0, float(den_value or 0.0)), digits)

def fmt_int(value):
    try:
        return f'{int(round(float(value))):,}'
    except (TypeError, ValueError):
        return '-'

def add_kv(R, label, value):
    R.p(f'  {label:<32s}: {value}')

def report_external_ai_brief(
    R,
    summary_rows,
    debug_rows,
    summary_meta,
    debug_meta,
    debug_scope,
    data_coherence,
    detected_info,
    gen_norm_info,
    auto_insights,
    yield_stuck_info=None,
    stop_stuck_info=None,
    train_summary_rows=0,
    test_summary_rows=0,
):
    """Top-level report brief for readers that do not inspect the CSV files."""
    R.p(f'{"="*76}')
    R.p('  RESUMEN EJECUTIVO PARA IA EXTERNA')
    R.p(f'{"="*76}')
    R.p('  Objetivo: este bloque resume lo imprescindible para analizar el train/test')
    R.p('  sin abrir Fitness_Debug.csv ni los Summary. El detalle completo queda debajo.')

    add_kv(R, 'Modo de este informe', f'{MODE} ({LABEL})')
    add_kv(R, 'Fecha de analisis', datetime.now().strftime('%d/%m/%Y %H:%M'))
    add_kv(R, 'Modo global detectado', detected_info.get('mode', '-'))
    add_kv(R, 'Motivo de deteccion', detected_info.get('reason', '-'))
    add_kv(R, 'Summary usado', os.path.basename(SUMMARY_FILE) if SUMMARY_FILE else '-')
    add_kv(R, 'Debug usado', os.path.basename(DEBUG_FILE))
    add_kv(R, 'Training/Test Summary filas', f'{train_summary_rows}/{test_summary_rows}')

    schema = debug_rows[0].get('_schema', 'unknown') if debug_rows else detect_debug_schema(debug_meta.get('mapped_keys', []))
    mapped_summary = len(summary_meta.get('mapped_keys', []))
    mapped_debug = len(debug_meta.get('mapped_keys', []))
    add_kv(R, 'Esquema Debug detectado', schema)
    add_kv(R, 'Campos mapeados Summary/Debug', f'{mapped_summary}/{mapped_debug}')
    add_kv(R, 'Cabeceras extra Summary', short_list(summary_meta.get('unknown_headers', []), 8))
    add_kv(R, 'Cabeceras extra Debug', short_list(debug_meta.get('unknown_headers', []), 8))
    add_kv(R, 'Cabeceras duplicadas Debug', short_list(debug_meta.get('duplicate_headers', []), 8))
    add_kv(R, 'Campos duplicados Debug', short_list(debug_meta.get('duplicate_mapped_keys', []), 8))
    if any(str(x).startswith('pen_steer_app:') for x in debug_meta.get('duplicate_mapped_keys', [])) and 'pen_align' not in debug_meta.get('mapped_keys', []):
        add_kv(R, 'Aviso export 23/06', 'SteerApproach aparece duplicado y AlignmentPenalty no aparece como columna.')

    R.p(f'\n-- Cobertura y Validez de Datos --')
    status = data_coherence.get('status', 'ok').upper() if data_coherence else 'UNKNOWN'
    add_kv(R, 'Estado coherencia', status)
    add_kv(
        R,
        'Summary filas/gens',
        f'{data_coherence.get("summary_rows", 0)}/{data_coherence.get("summary_gens", 0)} '
        f'({data_coherence.get("summary_gen_min", 0)}..{data_coherence.get("summary_gen_max", 0)})'
        if data_coherence else '-',
    )
    add_kv(
        R,
        'Debug filas/gens',
        f'{data_coherence.get("debug_rows", 0)}/{data_coherence.get("debug_gens", 0)} '
        f'({data_coherence.get("debug_gen_min", 0)}..{data_coherence.get("debug_gen_max", 0)})'
        if data_coherence else '-',
    )
    if data_coherence:
        if data_coherence.get('summary_gens', 0) > 0:
            add_kv(R, 'Cobertura gens Debug', fmt_pct_value(data_coherence.get('debug_gen_coverage_pct', 0.0), 1))
        else:
            add_kv(R, 'Cobertura gens Debug', 'n/a (Summary sin generaciones)')
        if data_coherence.get('expected_debug_rows', 0) > 0:
            add_kv(
                R,
                'Cobertura filas Debug',
                f'{fmt_pct_value(data_coherence.get("debug_row_coverage_pct", 0.0), 1)} '
                f'(esperado~{fmt_int(data_coherence.get("expected_debug_rows", 0))}, '
                f'{data_coherence.get("expected_debug_source", "-")})',
            )
        else:
            add_kv(R, 'Cobertura filas Debug', 'n/a (sin esperado porque Summary esta vacio)')
    add_kv(R, 'Registros Debug totales', fmt_int(debug_scope.get('raw_total', 0)))
    add_kv(R, 'Registros seleccionados', fmt_int(debug_scope.get('selected_total', len(debug_rows))))
    if debug_scope.get('has_training_flag'):
        add_kv(
            R,
            'Split TRAIN/TEST/UNK',
            f'{fmt_int(debug_scope.get("train_total", 0))}/'
            f'{fmt_int(debug_scope.get("test_total", 0))}/'
            f'{fmt_int(debug_scope.get("unknown_total", 0))}',
        )
    if debug_scope.get('excluded_incomplete_rows', 0):
        add_kv(
            R,
            'Debug excluido sin Summary',
            f'{fmt_int(debug_scope.get("excluded_incomplete_rows", 0))} filas; '
            f'gens {short_list(debug_scope.get("excluded_incomplete_generations", []), 12)}',
    )
    if gen_norm_info:
        if gen_norm_info.get('summary_count', 0) > 0:
            add_kv(
                R,
                'Generaciones Summary',
                f'{gen_norm_info.get("summary_raw_min", 0)}..{gen_norm_info.get("summary_raw_max", 0)} '
                f'-> 1..{gen_norm_info.get("summary_idx_max", 0)}',
            )
        else:
            add_kv(R, 'Generaciones Summary', 'sin datos')
        if gen_norm_info.get('debug_count', 0) > 0:
            add_kv(
                R,
                'Generaciones Debug',
                f'{gen_norm_info.get("debug_raw_min", 0)}..{gen_norm_info.get("debug_raw_max", 0)} '
                f'-> 1..{gen_norm_info.get("debug_idx_max", 0)}',
            )
        else:
            add_kv(R, 'Generaciones Debug', 'sin datos')

    warnings = list(data_coherence.get('warnings', [])) if data_coherence else []
    R.p(f'\n-- Alertas de Lectura --')
    if warnings:
        for w in warnings:
            R.p(f'  - {w}')
    else:
        R.p('  - No hay alertas fuertes de alineacion entre Summary y Debug.')
    if not debug_rows:
        R.p('  - No hay registros Debug seleccionados; las metricas por coche no son concluyentes.')
    if not summary_rows:
        R.p('  - No hay Summary seleccionado; la lectura de generacion/convergencia queda limitada.')
        if MODE == 'test':
            R.p('  - En test 01/07 puede ser normal si se ejecuto el flujo de coche unico con MultiTestingMode desactivado.')

    report_program_updates_0107(R, debug_rows)

    R.p(f'\n-- KPIs Principales --')
    if summary_rows:
        n = len(summary_rows)
        br = max(summary_rows, key=lambda x: x.get('best', 0.0))
        mr = max(summary_rows, key=lambda x: x.get('mean', 0.0))
        wr = min(summary_rows, key=lambda x: x.get('mean', 0.0))
        means = [r.get('mean', 0.0) for r in summary_rows]
        times = [r.get('time', 0.0) for r in summary_rows]
        slope_mean = trend_slope([r.get('gen', i + 1) for i, r in enumerate(summary_rows)], means)
        tail_n = min(50, max(1, n // 3)) if n >= 3 else n
        tail = summary_rows[-tail_n:] if tail_n else []
        add_kv(R, 'Generaciones analizadas', fmt_int(n))
        add_kv(R, 'BestFit max', f'{br.get("best", 0.0):.2f} (gen {br.get("gen", 0)})')
        add_kv(R, 'MeanFit max/min', f'{mr.get("mean", 0.0):.2f} / {wr.get("mean", 0.0):.2f}')
        add_kv(R, 'MeanFit medio/P50', f'{mean(means):.2f} / {pctl(means, 50):.2f}')
        add_kv(R, 'MeanFit tendencia', f'{slope_mean:+.4f} por gen normalizada')
        add_kv(R, 'Tiempo medio/P50', f'{mean(times):.2f}s / {pctl(times, 50):.2f}s')
        if tail:
            add_kv(R, f'Ultimas {tail_n} gens', f'MeanFit {mean([r.get("mean", 0.0) for r in tail]):.2f}; Tiempo {mean([r.get("time", 0.0) for r in tail]):.2f}s')
        test_stats = summarize_test_results(summary_rows)
        if test_stats:
            add_kv(
                R,
                'Test acierto global',
                f'{test_stats["success_rate"]:.2f}% '
                f'({test_stats["total_success"]}/{test_stats["total_n"]}, '
                f'IC95 {test_stats["wilson_lo"]:.2f}-{test_stats["wilson_hi"]:.2f}%)',
            )
            add_kv(R, 'Test acierto P50/desv', f'{test_stats["success_median"]:.2f}% / {test_stats["success_std"]:.2f} pp')
    else:
        R.p('  Summary: sin datos.')

    if debug_rows:
        nd = len(debug_rows)
        fits = [r.get('fit', 0.0) for r in debug_rows]
        times_dbg = [r.get('time', 0.0) for r in debug_rows]
        deaths = Counter(r.get('death', '') for r in debug_rows if r.get('death', ''))
        family_counts = Counter(death_family(r.get('death', '')) for r in debug_rows if r.get('death', ''))
        collision_stats = summarize_collision_deaths(debug_rows)
        top_death = deaths.most_common(1)[0] if deaths else ('-', 0)
        lazy_n = sum(1 for r in debug_rows if is_lazy_reason(r.get('death', '')))
        death_fail_n = sum(1 for r in debug_rows if r.get('is_test_failure_death', is_test_failure_reason(r.get('death', ''))))
        total_ticks = sum(r.get('t_tot', 0.0) for r in debug_rows)
        stop_ticks = sum(r.get('t_stop_ctx', 0.0) for r in debug_rows)
        legal_fail_n = family_counts.get('VIOLATION', 0)
        add_kv(R, 'Debug registros', fmt_int(nd))
        add_kv(R, 'Fitness raw medio/P50/P90', f'{mean(fits):.2f} / {pctl(fits, 50):.2f} / {pctl(fits, 90):.2f}')
        add_kv(R, 'Tiempo vivo medio/P50', f'{mean(times_dbg):.2f}s / {pctl(times_dbg, 50):.2f}s')
        add_kv(R, 'Muerte dominante', f'{top_death[0]} ({fmt_pct_ratio(top_death[1], nd, 1)})')
        add_kv(R, 'Familias de muerte top', ', '.join(f'{k}={fmt_pct_ratio(v, nd, 1)}' for k, v in family_counts.most_common(4)) or '-')
        if collision_stats['total'] > 0:
            add_kv(
                R,
                'Colisiones normal/rotonda',
                f'{collision_stats["normal"]}/{collision_stats["roundabout"]} '
                f'(rotonda {fmt_pct_ratio(collision_stats["roundabout"], collision_stats["total"], 1)} de colisiones)',
            )
        add_kv(R, 'Fallo legal', f'{fmt_pct_ratio(legal_fail_n, nd, 2)} ({fmt_int(legal_fail_n)}/{fmt_int(nd)})')
        add_kv(R, 'LAZY', f'{fmt_pct_ratio(lazy_n, nd, 2)} ({fmt_int(lazy_n)}/{fmt_int(nd)})')
        fail_label = 'Fail por muerte' if MODE == 'test' else 'Muertes no exitosas segun TEST'
        add_kv(R, fail_label, f'{fmt_pct_ratio(death_fail_n, nd, 2)} ({fmt_int(death_fail_n)}/{fmt_int(nd)})')
        stop_violation_detail = summarize_stop_violation_subtypes(debug_rows)
        if stop_violation_detail:
            add_kv(
                R,
                'STOP_VIOLATION EXIT/TIMEOUT',
                f'{stop_violation_detail.get("EXIT", 0)}/{stop_violation_detail.get("TIMEOUT", 0)} '
                f'(generico {stop_violation_detail.get("GENERIC", 0)})',
            )
        if debug_field_available(debug_rows, 'car_overlaps'):
            overlap_total = sum(r.get('car_overlaps', 0.0) for r in debug_rows)
            overlap_rows = sum(1 for r in debug_rows if r.get('car_overlaps', 0.0) > 0.0)
            add_kv(
                R,
                'Solapes entre coches',
                f'{overlap_total:.0f} eventos; {fmt_pct_ratio(overlap_rows, nd, 2)} '
                f'({fmt_int(overlap_rows)}/{fmt_int(nd)} coches)',
            )
            if debug_field_available(debug_rows, 'car_overlap_pen_shadow'):
                shadow_total = sum(r.get('car_overlap_pen_shadow', 0.0) for r in debug_rows)
                add_kv(R, 'Sombra penalty solapes', f'{shadow_total:.2f}; {sdiv(shadow_total, overlap_total):.2f}/overlap')
            if debug_field_available(debug_rows, 'car_overlap_penalty'):
                overlap_penalty = sum(r.get('car_overlap_penalty', 0.0) for r in debug_rows)
                add_kv(R, 'Penalty real solapes', f'{overlap_penalty:.2f}; {sdiv(overlap_penalty, overlap_total):.2f}/overlap')
        if debug_field_available(debug_rows, 'queue_wait_bonus'):
            queue_wait_bonus = sum(r.get('queue_wait_bonus', 0.0) for r in debug_rows)
            queue_wait_rows = sum(1 for r in debug_rows if r.get('queue_wait_bonus', 0.0) > 0.0)
            add_kv(
                R,
                'QueueWaitBonus',
                f'{queue_wait_bonus:.2f} total; {fmt_pct_ratio(queue_wait_rows, nd, 2)} '
                f'({fmt_int(queue_wait_rows)}/{fmt_int(nd)} coches)',
            )
        add_kv(R, 'Stop-context/ticks', fmt_pct_ratio(stop_ticks, total_ticks, 2))
        add_kv(R, 'Stop/Yield completados', f'{sum(r.get("stop_done_n", 0.0) for r in debug_rows):.0f} / {sum(r.get("yield_done_n", 0.0) for r in debug_rows):.0f}')
        add_kv(R, 'Stop/Yield bonus total', f'{sum(r.get("stop_bonus", 0.0) for r in debug_rows):.2f} / {sum(r.get("yield_bonus", 0.0) for r in debug_rows):.2f}')
        if debug_field_available(debug_rows, 'yield_free_passes'):
            add_kv(
                R,
                'Yield free/completed',
                f'{sum(r.get("yield_free_passes", 0.0) for r in debug_rows):.0f} / '
                f'{sum(r.get("yield_done_n", 0.0) for r in debug_rows):.0f}',
            )
        if debug_field_available(debug_rows, 'yield_validation_speed'):
            speed_vals = metric_values(debug_rows, 'yield_validation_speed')
            add_kv(R, 'SpeedAtYieldValidation', f'media exp. {mean(speed_vals):.2f}; P50 {pctl(speed_vals, 50):.2f}; N={len(speed_vals)}')
        if debug_field_available(debug_rows, 'crossing_blocked_t'):
            crossing_total = sum(r.get('crossing_blocked_t', 0.0) for r in debug_rows)
            crossing_rows = sum(1 for r in debug_rows if r.get('crossing_blocked_t', 0.0) > 0.0)
            add_kv(
                R,
                'Bloqueo en cruce',
                f'{crossing_total:.2f}s; {fmt_pct_ratio(crossing_rows, nd, 2)} ({fmt_int(crossing_rows)}/{fmt_int(nd)} coches)',
            )
        if debug_field_available(debug_rows, 'first_steer_release_ticks'):
            release_vals = metric_values(debug_rows, 'first_steer_release_ticks')
            add_kv(R, 'FirstSteerAfterRelease', f'P50 {pctl(release_vals, 50):.2f} ticks; P90 {pctl(release_vals, 90):.2f}; N={len(release_vals)}')
        if debug_field_available(debug_rows, 'front_obst_death'):
            front_vals = metric_values(debug_rows, 'front_obst_death')
            add_kv(R, 'FrontObstAtDeath', f'media exp. {mean(front_vals):.4f}; P50 {pctl(front_vals, 50):.4f}; N={len(front_vals)}')
        if debug_field_available(debug_rows, 'steer_app_wrong') or debug_field_available(debug_rows, 'steer_app_right'):
            wrong_total = sum(r.get('steer_app_wrong', 0.0) for r in debug_rows)
            right_total = sum(r.get('steer_app_right', 0.0) for r in debug_rows)
            add_kv(R, 'SteerApproach wrong/right', f'{wrong_total:.2f} / {right_total:.2f}; wrong {sdiv(wrong_total*100.0, wrong_total+right_total):.2f}%')
        if yield_stuck_info and yield_stuck_info.get('timefinished_rows', 0) > 0:
            add_kv(
                R,
                'YieldTrap en TIME_FINISHED',
                f'{yield_stuck_info.get("candidate_count", 0)}/{yield_stuck_info.get("timefinished_rows", 0)} '
                f'candidatos; watch={yield_stuck_info.get("watch_count", 0)}',
            )
        if stop_stuck_info and stop_stuck_info.get('timefinished_rows', 0) > 0:
            add_kv(
                R,
                'StopTrap en TIME_FINISHED',
                f'{stop_stuck_info.get("candidate_count", 0)}/{stop_stuck_info.get("timefinished_rows", 0)} '
                f'candidatos; watch={stop_stuck_info.get("watch_count", 0)}',
            )
        penalty_parts = [
            f'Muerte={mean([r.get("pen_m", 0.0) for r in debug_rows]):.2f}',
            f'Nav={mean([r.get("pen_nav", 0.0) for r in debug_rows]):.2f}',
            f'Creep={mean([r.get("pen_creep", 0.0) for r in debug_rows]):.2f}',
            f'SteerApp={mean([r.get("pen_steer_app", 0.0) for r in debug_rows]):.2f}',
        ]
        if debug_field_available(debug_rows, 'pen_align'):
            penalty_parts.append(f'Align={mean([r.get("pen_align", 0.0) for r in debug_rows]):.2f}')
        penalty_parts.append(f'Lazy={mean([r.get("pen_lazy", 0.0) for r in debug_rows]):.2f}')
        add_kv(
            R,
            'Penalties medios clave',
            '; '.join(penalty_parts),
        )
        mutation_rows = [
            r for r in debug_rows
            if not r.get('is_weight_initialization', False)
            and str(r.get('mutation_kind', '')).startswith('MUT_')
        ]
        if mutation_rows:
            add_kv(
                R,
                'Mutacion observada',
                f'MutRate P50={pctl([r.get("mut_rate", 0.0) for r in mutation_rows], 50)*100.0:.2f}%; '
                f'MutChanged P50={pctl([r.get("mut_changed", 0.0) for r in mutation_rows], 50):.0f}',
            )
        car_fams = summarize_car_index_families(debug_rows)
        if car_fams:
            add_kv(R, 'Familias CarIndex', ', '.join(f'{x["family"]}={x["n"]}' for x in car_fams))
    else:
        R.p('  Debug: sin datos.')

    if debug_rows and debug_field_available(debug_rows, 'round_entered_n'):
        R.p(f'\n-- Rotondas y Metricas Situacionales --')
        nd = len(debug_rows)
        round_entered = sum(r.get('round_entered_n', 0.0) for r in debug_rows)
        round_completed = sum(r.get('round_completed_n', 0.0) for r in debug_rows)
        round_collisions = sum(r.get('round_collisions', 0.0) for r in debug_rows)
        round_ticks = sum(r.get('round_ticks', 0.0) for r in debug_rows)
        total_ticks = sum(r.get('t_tot', 0.0) for r in debug_rows)
        add_kv(R, 'Entradas/completadas', f'{round_entered:.0f} / {round_completed:.0f} ({fmt_pct_ratio(round_completed, round_entered, 2)})')
        add_kv(R, 'Colisiones en rotonda', f'{round_collisions:.0f} ({fmt_pct_ratio(round_collisions, round_entered, 2)} por entrada)')
        add_kv(R, 'Ticks en rotonda', f'{round_ticks:.0f} ({fmt_pct_ratio(round_ticks, total_ticks, 2)} del total)')
        entry_speed_n = metric_exposure_count(debug_rows, 'round_entry_speed_avg')
        entry_front_n = metric_exposure_count(debug_rows, 'round_entry_front_avg')
        steer_n = metric_exposure_count(debug_rows, 'round_steer_avg')
        throttle_n = metric_exposure_count(debug_rows, 'round_throttle_avg')
        add_kv(R, 'EntrySpeed avg (N exp.)', f'{mean(metric_values(debug_rows, "round_entry_speed_avg")):.2f} (N={entry_speed_n}/{nd})')
        add_kv(R, 'FrontObst entry avg (N exp.)', f'{mean(metric_values(debug_rows, "round_entry_front_avg")):.4f} (N={entry_front_n}/{nd})')
        add_kv(R, 'Steering/Throttle in round', f'{mean(metric_values(debug_rows, "round_steer_avg")):.4f} (N={steer_n}) / {mean(metric_values(debug_rows, "round_throttle_avg")):.4f} (N={throttle_n})')
        if debug_field_available(debug_rows, 'round_bonus'):
            round_bonus = sum(r.get('round_bonus', 0.0) for r in debug_rows)
            add_kv(R, 'RoundaboutBonus neto', f'{round_bonus:.2f}; {sdiv(round_bonus, round_entered):.2f}/entrada; {sdiv(round_bonus, round_ticks):.4f}/tick')
            if debug_field_available(debug_rows, 'round_completion_bonus'):
                add_kv(
                    R,
                    'Bonus C/E/T',
                    f'+{sum(r.get("round_completion_bonus", 0.0) for r in debug_rows):.2f} / '
                    f'-{sum(r.get("round_entry_penalty", 0.0) for r in debug_rows):.2f} / '
                    f'-{sum(r.get("round_throttle_penalty", 0.0) for r in debug_rows):.2f}',
                )
        if debug_field_available(debug_rows, 'round_exit1_count'):
            exit_parts = []
            for exit_num, label in ((1, 'E1'), (2, 'E2'), (3, 'E3+')):
                count = sum(r.get(f'round_exit{exit_num}_count', 0.0) for r in debug_rows)
                deaths = sum(r.get(f'round_exit{exit_num}_deaths', 0.0) for r in debug_rows)
                if count > 0:
                    exit_parts.append(f'{label} {deaths:.0f}/{count:.0f}={fmt_pct_ratio(deaths, count, 1)}')
                else:
                    exit_parts.append(f'{label} sin exposicion')
            add_kv(R, 'Muertes por salida', '; '.join(exit_parts))
        R.p('  Nota: las medias de entrada/steering/throttle usan solo filas con exposicion real;')
        R.p('  los ceros de coches que no entraron en rotonda no se mezclan como si fueran medidas reales.')

    R.p(f'\n-- Diagnosticos Prioritarios --')
    priority_lines = []
    if data_coherence and data_coherence.get('status') in ('warning', 'critical'):
        priority_lines.append('Primero validar coherencia: hay avisos de alineacion/cobertura.')
    if summary_rows:
        means = [r.get('mean', 0.0) for r in summary_rows]
        slope_mean = trend_slope([r.get('gen', i + 1) for i, r in enumerate(summary_rows)], means)
        if slope_mean < 0:
            priority_lines.append(f'MeanFit cae ({slope_mean:+.4f}/gen): posible regresion o recompensa dominante negativa.')
    if debug_rows:
        family_counts = Counter(death_family(r.get('death', '')) for r in debug_rows if r.get('death', ''))
        collision_stats = summarize_collision_deaths(debug_rows)
        violation_pct = sdiv(family_counts.get('VIOLATION', 0) * 100.0, len(debug_rows))
        collision_pct = sdiv(family_counts.get('COLLISION', 0) * 100.0, len(debug_rows))
        if violation_pct >= 20.0:
            priority_lines.append(f'Fallo legal alto ({violation_pct:.2f}%): revisar stop/yield/traffic/nav antes que microajustes de fitness.')
        if collision_pct >= 20.0:
            priority_lines.append(
                f'Colisiones altas ({collision_pct:.2f}%): '
                f'rotonda={collision_stats["roundabout"]}, normales={collision_stats["normal"]}; '
                'revisar velocidad/steering/spawns problematicos.'
            )
    if yield_stuck_info and yield_stuck_info.get('candidate_count', 0) > 0:
        priority_lines.append(
            f'YieldTrap: {yield_stuck_info.get("candidate_count", 0)}/'
            f'{yield_stuck_info.get("timefinished_rows", 0)} TIME_FINISHED candidatos.'
        )
    if stop_stuck_info and stop_stuck_info.get('candidate_count', 0) > 0:
        priority_lines.append(
            f'StopTrap: {stop_stuck_info.get("candidate_count", 0)}/'
            f'{stop_stuck_info.get("timefinished_rows", 0)} TIME_FINISHED candidatos.'
        )
    if debug_rows and debug_field_available(debug_rows, 'round_entered_n'):
        round_entered = sum(r.get('round_entered_n', 0.0) for r in debug_rows)
        round_collisions = sum(r.get('round_collisions', 0.0) for r in debug_rows)
        if round_entered > 0 and sdiv(round_collisions, round_entered) >= 0.20:
            priority_lines.append(f'Rotondas: colision por entrada {sdiv(round_collisions*100.0, round_entered):.2f}%, probablemente un foco de regresion.')
    if debug_rows and debug_field_available(debug_rows, 'crossing_blocked_t'):
        crossing_total = sum(r.get('crossing_blocked_t', 0.0) for r in debug_rows)
        crossing_rows = sum(1 for r in debug_rows if r.get('crossing_blocked_t', 0.0) > 0.0)
        if crossing_total > 0.0:
            priority_lines.append(f'Bloqueo en cruce 30/06: {crossing_total:.2f}s concentrados en {crossing_rows}/{len(debug_rows)} coches.')
    if debug_rows and debug_field_available(debug_rows, 'car_overlap_penalty'):
        overlap_total = sum(r.get('car_overlaps', 0.0) for r in debug_rows)
        overlap_penalty = sum(r.get('car_overlap_penalty', 0.0) for r in debug_rows)
        if overlap_penalty > 0.0:
            priority_lines.append(
                f'Penalty real por solapes 01/07: {overlap_penalty:.2f} '
                f'({sdiv(overlap_penalty, overlap_total):.2f}/overlap).'
            )
    if debug_rows and debug_field_available(debug_rows, 'queue_wait_bonus'):
        queue_wait_bonus = sum(r.get('queue_wait_bonus', 0.0) for r in debug_rows)
        queue_wait_rows = sum(1 for r in debug_rows if r.get('queue_wait_bonus', 0.0) > 0.0)
        if queue_wait_bonus > 0.0:
            priority_lines.append(f'QueueWaitBonus 01/07 activo: {queue_wait_bonus:.2f} en {queue_wait_rows}/{len(debug_rows)} coches.')
    if debug_rows and (debug_field_available(debug_rows, 'steer_app_wrong') or debug_field_available(debug_rows, 'steer_app_right')):
        wrong_total = sum(r.get('steer_app_wrong', 0.0) for r in debug_rows)
        right_total = sum(r.get('steer_app_right', 0.0) for r in debug_rows)
        if wrong_total + right_total > 0.0 and sdiv(wrong_total, wrong_total + right_total) >= 0.60:
            priority_lines.append(f'SteerApproach wrong-dir alto ({sdiv(wrong_total*100.0, wrong_total + right_total):.1f}% del desglose).')
    for line in priority_lines[:8] or ['Sin diagnosticos prioritarios adicionales fuera de los insights automaticos.']:
        R.p(f'  - {line}')
    for line in auto_insights[:8]:
        R.p(f'  - Insight: {line}')

    R.p(f'\n-- Guia de Interpretacion para Otra IA --')
    R.p('  - Tratar este bloque como indice y el resto del informe como evidencia detallada.')
    R.p('  - No inferir causalidad desde Pearson/correlaciones; usarlas solo para priorizar hipotesis.')
    R.p('  - Las metricas situacionales solo valen con denominador real: entradas, ticks o completaciones.')
    R.p('  - NumRoundaboutsCompleted es limite inferior: se confirma al registrar una entrada posterior.')
    R.p('  - RoundaboutBonus neto = bonus completado - penalty entrada - penalty throttle cuando el desglose existe.')
    R.p('  - NumCarOverlaps 26/06 mide solapes entre coches vivos; no equivale automaticamente a DeathReason COLLISION.')
    R.p('  - CarOverlapPenaltyShadow 30/06 es diagnostico sombra de solape; interpretarlo como severidad, no necesariamente como fitness aplicado.')
    R.p('  - CarOverlapPenalty 01/07 si es penalty real aplicado al fitness; compararlo con NumCarOverlaps y no con muertes por colision.')
    R.p('  - QueueWaitBonus 01/07 premia espera detras de coche/cola; es situacional y debe leerse solo donde hay exposicion real.')
    R.p('  - Penalty_Velocidad 01/07 usa EffectiveObstacleDistance cuando hay coche cercano; no es solo sensor frontal estatico.')
    R.p('  - Test single-car 01/07: con MultiTestingMode desactivado puede existir Debug sin Summary multi-coche completo.')
    R.p('  - EndGeneration 01/07 limpia colas pendientes de stop/yield/crossing; no asumir bloqueo heredado entre generaciones.')
    R.p('  - SpeedAtYieldValidation 30/06 es la velocidad puntual al validar ceda, no un acumulado por coche.')
    R.p('  - STOP_VIOLATION_EXIT/TIMEOUT se agrupan como VIOLATION, pero el subtipo indica salida indebida vs espera agotada.')
    R.p('  - Mutacion 26/06: GenerationsWithoutImprovement no se exporta; el informe valida rangos esperados, no el valor exacto por individuo.')
    R.p('  - En TEST, Summary es la fuente principal de acierto/fallo; Debug reconstruye causas y contexto.')
    R.p('  - Si hay filas Debug excluidas sin Summary cerrado, evitar conclusiones sobre generaciones incompletas.')

def save_generation_mapping(out_dir, info):
    path = os.path.join(out_dir, 'mapeo_generaciones.csv')
    rows = []

    for m in info.get('summary_mapping', []):
        rows.append(['summary', m.get('raw', 0), m.get('norm', 0)])
    for m in info.get('debug_mapping', []):
        rows.append(['debug', m.get('raw', 0), m.get('norm', 0)])

    with open(path, 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f)
        w.writerow(['scope', 'gen_raw', 'gen_norm'])
        w.writerows(rows)
    return path

def save_master_summary(base_dir, now_ts, detected_info, results):
    analisis_dir = os.path.join(base_dir, 'Analisis')
    txt_path = os.path.join(analisis_dir, f'resumen_global_{now_ts}.txt')
    json_path = os.path.join(analisis_dir, f'resumen_global_{now_ts}.json')

    lines = []
    lines.append('=' * 84)
    lines.append('RESUMEN GLOBAL DE EJECUCION')
    lines.append('=' * 84)
    lines.append(f'Timestamp: {now_ts}')
    lines.append(f'Modo detectado global: {detected_info.get("mode", "")}')
    lines.append(f'Motivo deteccion: {detected_info.get("reason", "-")}')
    lines.append('')
    lines.append('Modo       | Gens | Debug | BestMax    | MeanMed    | TimeMed | Neg%  | Succ% | Lazy%')
    lines.append('-' * 84)

    for r in results:
        m = r.get('metrics', {})
        lines.append(
            f'{r.get("mode", ""):10s} | '
            f'{m.get("gens", 0):4d} | '
            f'{m.get("debug_rows", 0):5d} | '
            f'{m.get("best_max", 0.0):10.2f} | '
            f'{m.get("mean_mean", 0.0):10.2f} | '
            f'{m.get("time_mean", 0.0):7.2f} | '
            f'{m.get("neg_pct", 0.0):5.1f}% | '
            f'{m.get("success_mean", 0.0):5.2f}% | '
            f'{m.get("lazy_pct", 0.0):5.2f}%'
        )
        lines.append(f'  carpeta: {r.get("out_dir", "")}')

    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    payload = {
        'timestamp': now_ts,
        'detected_info': detected_info,
        'results': results,
    }
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return txt_path, json_path

def build_combined_summary_meta(train_meta, test_meta):
    return {
        'path': f'{TRAIN_SUMMARY_FILE} + {TEST_SUMMARY_FILE}',
        'exists': train_meta.get('exists', False) or test_meta.get('exists', False),
        'size_bytes': train_meta.get('size_bytes', 0) + test_meta.get('size_bytes', 0),
        'mtime': max(train_meta.get('mtime', ''), test_meta.get('mtime', '')),
        'header': [],
        'mapped_keys': sorted(set(train_meta.get('mapped_keys', []) + test_meta.get('mapped_keys', []))),
        'unknown_headers': sorted(set(train_meta.get('unknown_headers', []) + test_meta.get('unknown_headers', []))),
        'duplicate_headers': sorted(set(train_meta.get('duplicate_headers', []) + test_meta.get('duplicate_headers', []))),
        'duplicate_mapped_keys': sorted(set(train_meta.get('duplicate_mapped_keys', []) + test_meta.get('duplicate_mapped_keys', []))),
        'missing_required': sorted(set(train_meta.get('missing_required', [])) & set(test_meta.get('missing_required', []))),
        'data_rows': train_meta.get('data_rows', 0) + test_meta.get('data_rows', 0),
        'empty_rows': train_meta.get('empty_rows', 0) + test_meta.get('empty_rows', 0),
        'short_rows': train_meta.get('short_rows', 0) + test_meta.get('short_rows', 0),
        'long_rows': train_meta.get('long_rows', 0) + test_meta.get('long_rows', 0),
        'header_cols': max(train_meta.get('header_cols', 0), test_meta.get('header_cols', 0)),
        'max_cols': max(train_meta.get('max_cols', 0), test_meta.get('max_cols', 0)),
        'loaded_rows': 0,
        'discarded_rows': 0,
    }

def copy_savegame_models(out_dir):
    copied = []
    model_dates = {}  # {nombre: fecha de modificación}
    missing = []
    target_dir = os.path.join(out_dir, 'SaveGames')
    try:
        os.makedirs(target_dir, exist_ok=True)
    except Exception:
        logging.warning('No se pudo crear carpeta SaveGames en: %s', target_dir)
    os.makedirs(target_dir, exist_ok=True)

    for name in ('SuperCarModel.sav', 'SessionCarModel.sav'):
        src = os.path.join(SAVEGAMES_DIR, name)
        dst = os.path.join(target_dir, name)
        if os.path.exists(src):
            # Capturar fecha de modificación del modelo
            try:
                mtime = os.path.getmtime(src)
                from datetime import datetime
                mod_date = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
                model_dates[name] = mod_date
            except Exception:
                model_dates[name] = 'desconocida'
            shutil.copy2(src, dst)
            copied.append(name)
        else:
            missing.append(name)

    return copied, missing, model_dates

def run_analysis_variant(
    mode,
    summary_rows,
    debug_rows,
    summary_meta_template,
    debug_meta_template,
    debug_scope,
    detected_info,
    train_summary_rows,
    test_summary_rows,
    csvs,
):
    global MODE, LABEL, SUMMARY_FILE, OUT_DIR
    MODE = mode
    LABEL = mode_label(mode)
    if mode == 'train':
        SUMMARY_FILE = TRAIN_SUMMARY_FILE
    elif mode == 'test':
        SUMMARY_FILE = TEST_SUMMARY_FILE
    else:
        SUMMARY_FILE = f'{os.path.basename(TRAIN_SUMMARY_FILE)} + {os.path.basename(TEST_SUMMARY_FILE)}'

    debug_rows, completion_alignment = align_debug_to_completed_summary(summary_rows, debug_rows, mode)
    debug_scope = dict(debug_scope)
    debug_scope['selected_total'] = len(debug_rows)
    debug_scope['excluded_incomplete_rows'] = completion_alignment['excluded_rows']
    debug_scope['excluded_incomplete_generations'] = completion_alignment['excluded_generations']
    if completion_alignment['excluded_rows']:
        logging.warning(
            'Se excluyen %d filas debug de generaciones sin Summary cerrado: %s',
            completion_alignment['excluded_rows'],
            completion_alignment['excluded_generations'],
        )

    data_coherence = analyze_data_coherence(mode, summary_rows, debug_rows, debug_scope)
    summary_rows_idx, debug_rows_idx, gen_norm_info = reindex_generations_for_analysis(summary_rows, debug_rows)
    yield_stuck_info = detect_yield_stuck_candidates(debug_rows_idx)
    stop_stuck_info = detect_stop_stuck_candidates(debug_rows_idx)
    auto_insights = compute_auto_insights(
        summary_rows_idx,
        debug_rows_idx,
        data_coherence=data_coherence,
        yield_stuck_info=yield_stuck_info,
        stop_stuck_info=stop_stuck_info,
    )

    OUT_DIR = os.path.join(BASE_DIR, 'Analisis', f'{MODE}_{NOW}')
    # Crear OUT_DIR solo si hay algo que guardar (evitar carpetas vacías)
    # Decidiremos crearla más abajo solo si existen archivos a copiar, se requieren mapas,
    # se copiarán SaveGames, o se van a generar gráficas.
    mapping_path = ''
    if SAVE_GENERATION_MAPPING:
        mapping_path = save_generation_mapping(OUT_DIR, gen_norm_info)

    # Copiar solo los CSV relevantes por modo de analisis.
    files_to_copy = {DEBUG_FILE}
    if mode in ('train', 'traintest'):
        files_to_copy.add(TRAIN_SUMMARY_FILE)
    if mode in ('test', 'traintest'):
        files_to_copy.add(TEST_SUMMARY_FILE)

    # Copiar CSVs existentes solo si hay archivos que copiar -> crear carpeta en ese caso
    existing_csvs = [src for src in csvs if src in files_to_copy and os.path.exists(src)]

    need_savegames = False
    if mode in ('test', 'traintest'):
        for name in ('SuperCarModel.sav', 'SessionCarModel.sav'):
            if os.path.exists(os.path.join(SAVEGAMES_DIR, name)):
                need_savegames = True
                break

    should_create_out = bool(existing_csvs) or SAVE_GENERATION_MAPPING or need_savegames or ENABLE_PLOTS
    if should_create_out:
        try:
            os.makedirs(OUT_DIR, exist_ok=True)
        except Exception:
            logging.warning('No se pudo crear OUT_DIR: %s', OUT_DIR)

    for src in existing_csvs:
        shutil.copy2(src, os.path.join(OUT_DIR, os.path.basename(src)))

    savegame_info = {'copied': [], 'missing': [], 'model_dates': {}}
    if mode in ('test', 'traintest'):
        copied, missing, model_dates = copy_savegame_models(OUT_DIR)
        savegame_info = {'copied': copied, 'missing': missing, 'model_dates': model_dates}
        if copied:
            logging.info('[SaveGames] copiados en %s: %s', os.path.join(OUT_DIR, 'SaveGames'), ', '.join(copied))
        if missing:
            logging.warning('[SaveGames] no encontrados en %s: %s', SAVEGAMES_DIR, ', '.join(missing))

    summary_meta = copy.deepcopy(summary_meta_template)
    debug_meta = copy.deepcopy(debug_meta_template)

    summary_meta['loaded_rows'] = len(summary_rows_idx)
    summary_meta['discarded_rows'] = max(0, summary_meta.get('data_rows', 0) - len(summary_rows_idx))
    debug_meta['selected_rows'] = len(debug_rows_idx)
    debug_meta['discarded_rows'] = max(0, debug_meta.get('data_rows', 0) - debug_meta.get('loaded_rows', 0))

    previous_sessions = collect_previous_sessions(MODE, SUMMARY_FILE, OUT_DIR, COMPARE_LIMIT)

    if debug_scope.get('has_training_flag') and debug_scope.get('selected_total', 0) == 0 and debug_scope.get('raw_total', 0) > 0:
        logging.warning('No hay filas debug compatibles con el modo analizado=%s.', MODE)
    if data_coherence.get('status') in ('warning', 'critical'):
        logging.warning('Coherencia %s: %d alerta(s).', MODE, len(data_coherence.get('warnings', [])))
    if yield_stuck_info.get('candidate_count', 0) > 0:
        logging.warning(
            'YieldTrap %s: %d candidatos fuertes sobre %d TIME_FINISHED.',
            MODE,
            yield_stuck_info.get('candidate_count', 0),
            yield_stuck_info.get('timefinished_rows', 0),
        )
    elif yield_stuck_info.get('watch_count', 0) > 0:
        logging.info(
            'YieldTrap %s: %d casos en vigilancia (TIME_FINISHED=%d).',
            MODE,
            yield_stuck_info.get('watch_count', 0),
            yield_stuck_info.get('timefinished_rows', 0),
        )
    if stop_stuck_info.get('candidate_count', 0) > 0:
        logging.warning(
            'StopTrap %s: %d candidatos fuertes sobre %d TIME_FINISHED.',
            MODE,
            stop_stuck_info.get('candidate_count', 0),
            stop_stuck_info.get('timefinished_rows', 0),
        )
    elif stop_stuck_info.get('watch_count', 0) > 0:
        logging.info(
            'StopTrap %s: %d casos en vigilancia (TIME_FINISHED=%d).',
            MODE,
            stop_stuck_info.get('watch_count', 0),
            stop_stuck_info.get('timefinished_rows', 0),
        )

    R = Report()
    report_external_ai_brief(
        R,
        summary_rows_idx,
        debug_rows_idx,
        summary_meta,
        debug_meta,
        debug_scope,
        data_coherence,
        detected_info,
        gen_norm_info,
        auto_insights,
        yield_stuck_info=yield_stuck_info,
        stop_stuck_info=stop_stuck_info,
        train_summary_rows=train_summary_rows,
        test_summary_rows=test_summary_rows,
    )
    report_input_quality(R, summary_meta, debug_meta)
    report_debug_scope(R, debug_scope)
    report_data_coherence(R, data_coherence)

    R.p(f'\n-- Deteccion automatica de fase --')
    R.p(f'  Modo global detectado: {detected_info.get("mode", "")}')
    R.p(f'  Modo de este informe:  {MODE}')
    R.p(f'  Motivo global:         {detected_info.get("reason", "-")}')
    report_generation_normalization(R, gen_norm_info)
    report_auto_insights(R, auto_insights)

    R.p(f'\n-- Resumen de Fases (Summary CSV) --')
    R.p(f'  Training_Summary filas: {train_summary_rows}')
    R.p(f'  Test_Summary filas:     {test_summary_rows}')

    report_summary(R, summary_rows_idx)
    
    # NUEVOS ANÁLISIS AVANZADOS
    if summary_rows_idx:
        report_convergence_analysis(R, summary_rows_idx)
        report_prediction_analysis(R, summary_rows_idx)
    
    report_summary_deep(R, summary_rows_idx)
    report_debug(R, debug_rows_idx)
    
    # NUEVO: Análisis de Diversidad y Componentes
    if debug_rows_idx:
        report_diversity_analysis(R, debug_rows_idx)
        report_components_correlation(R, debug_rows_idx)
    
    report_debug_deep(R, debug_rows_idx, yield_stuck_info=yield_stuck_info, stop_stuck_info=stop_stuck_info)
    report_quicksummary(R, summary_rows_idx, debug_rows_idx)
    report_session_comparison(R, summary_rows_idx, debug_rows_idx, previous_sessions)

    R.p(f'\n{"="*76}')
    R.p(f'  Analisis completado: {LABEL}')
    R.p(f'  Summary: {len(summary_rows_idx)} gens | Debug: {len(debug_rows_idx)} registros')
    if mapping_path:
        R.p(f'  Mapeo generaciones: {mapping_path}')
    else:
        R.p('  Mapeo generaciones: deshabilitado (no se guarda archivo).')
    
    # Mostrar información de modelos cargados con sus fechas de modificación
    if mode in ('test', 'traintest'):
        R.p(f'\n-- Modelos cargados --')
        if savegame_info.get('model_dates'):
            for model_name, mod_date in savegame_info['model_dates'].items():
                R.p(f'  {model_name}: {mod_date}')
        if savegame_info.get('missing'):
            R.p(f'  Modelos no encontrados: {savegame_info["missing"]}')
    
    R.p(f'  Carpeta: {os.path.abspath(OUT_DIR)}')
    R.p(f'{"="*76}\n')

    # Guardar informe de texto
    report_path = os.path.join(OUT_DIR, 'informe.txt')
    R.save(report_path)

    # Guardar snapshot estructurado para comparaciones automáticas (opcional)
    if SAVE_DETAILED_JSON:
        json_path = os.path.join(OUT_DIR, 'resumen_detallado.json')
        save_json_snapshot(
            json_path,
            summary_rows_idx,
            debug_rows_idx,
            summary_meta,
            debug_meta,
            previous_sessions,
            debug_scope=debug_scope,
            train_summary_rows=train_summary_rows,
            test_summary_rows=test_summary_rows,
            generation_normalization=gen_norm_info,
            auto_insights=auto_insights,
            data_coherence=data_coherence,
            yield_stuck=yield_stuck_info,
            stop_stuck=stop_stuck_info,
        )

    figs = []
    if ENABLE_PLOTS:
        logging.info('\n-- Generando graficas (%s) --', MODE)
        if mode in ('test', 'traintest'):
            figs += plot_test_model_dashboard(
                summary_rows_idx,
                previous_sessions=previous_sessions,
                model_dates=savegame_info.get('model_dates', {}),
            )
        figs += plot_all(summary_rows_idx, debug_rows_idx)
        logging.info('  Total graficas (%s): %d', MODE, len(figs))
    else:
        logging.info('\n-- Graficas deshabilitadas (%s) --', MODE)

    if os.path.exists(OUT_DIR):
        logging.info('\n-- Archivos generados en %s/ --', OUT_DIR)
        for f in sorted(os.listdir(OUT_DIR)):
            logging.info('  %s', f)
    else:
        logging.info('No se generaron archivos en %s (carpeta no creada)', OUT_DIR)

    deaths = Counter(r.get('death', '') for r in debug_rows_idx)
    lazy_rows = sum(1 for r in debug_rows_idx if is_lazy_reason(r.get('death', '')))
    metrics = summarize_session(
        summary_rows_idx,
        dbg_rows_count=len(debug_rows_idx),
        lazy_rows=lazy_rows,
        top_death=deaths.most_common(1)[0][0] if deaths else '',
        debug_rows=debug_rows_idx,
    )

    return {
        'mode': MODE,
        'label': LABEL,
        'out_dir': OUT_DIR,
        'summary_rows': len(summary_rows_idx),
        'debug_rows': len(debug_rows_idx),
        'figures': len(figs),
        'mapping_file': mapping_path,
        'auto_insights': auto_insights,
        'data_coherence': data_coherence,
        'yield_stuck': yield_stuck_info,
        'stop_stuck': stop_stuck_info,
        'metrics': metrics,
        'savegame_models': savegame_info,
    }
