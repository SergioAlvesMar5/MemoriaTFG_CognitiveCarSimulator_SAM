# -*- coding: utf-8 -*-
"""Parte interna de analyse_current.py.

Este archivo se carga desde analyse_current.py dentro del mismo namespace global
para mantener compatibilidad con los imports existentes y con la CLI antigua.
No esta pensado para ejecutarse directamente.
"""

# ── Parsers ──

def analyze_fitness_components_correlation(debug_rows):
    """Analyze only fitness components that really exist in the CSV schema."""
    if not debug_rows or len(debug_rows) < 20:
        return None

    available = debug_available_fields(debug_rows)
    labels = {
        'a': 'A (velocidad y centrado)',
        'b': 'B (legacy)',
        'c': 'C (legacy)',
        'd': 'D (legacy)',
        'e': 'E (legacy)',
        'f': 'F (velocidad y obstaculo)',
        'wait_bonus': 'Wait bonus',
        'queue_wait_bonus': 'Queue wait bonus',
        'stop_bonus': 'Stop completion bonus',
        'yield_bonus': 'Yield completion bonus',
        'round_bonus': 'Roundabout bonus neto',
        'net': 'Net normal',
    }
    fit_vals = [r.get('fit', 0.0) for r in debug_rows]
    fit_mean = mean(fit_vals)
    correlations = {}
    contributions = {}
    component_means = {}
    component_counts = {}
    for key in labels:
        if key not in available:
            continue
        corr_fit_vals, vals = correlation_sample(debug_rows, key)
        if len(vals) >= 5 and stdev(corr_fit_vals) > 1e-12 and stdev(vals) > 1e-12:
            correlations[key] = pearson_corr(vals, corr_fit_vals)
        else:
            correlations[key] = 0.0
        component_means[key] = mean(vals)
        component_counts[key] = len(vals)
        contributions[key] = sdiv(component_means[key], fit_mean) if fit_mean != 0 else 0.0

    penalty_keys = ('pen_m', 'pen_v', 'pen_tv', 'pen_nav', 'pen_lazy', 'pen_steer_app', 'pen_align', 'car_overlap_penalty')
    penalty_labels = {
        'pen_m': 'Penalty_Muerte',
        'pen_v': 'Penalty_Velocidad',
        'pen_tv': 'Penalty_TrafficViolation',
        'pen_nav': 'Penalty_NavViolation',
        'pen_lazy': 'Penalty_Lazy',
        'pen_steer_app': 'Penalty_SteerApproach',
        'pen_align': 'Penalty_Alignment',
        'car_overlap_penalty': 'CarOverlapPenalty',
    }
    pen_means = [
        (penalty_labels.get(key, key), mean([r.get(key, 0.0) for r in debug_rows]))
        for key in penalty_keys if key in available
    ]
    pen_means.sort(key=lambda item: item[1], reverse=True)

    return {
        'schema': debug_rows[0].get('_schema', 'unknown'),
        'component_labels': labels,
        'component_fitness_correlations': correlations,
        'component_contributions': contributions,
        'component_means': component_means,
        'component_counts': component_counts,
        'top_penalties': pen_means[:3],
    }

def parse_summary(path):
    rows = []
    if not os.path.exists(path):
        return rows
    header_map = {}

    def to_num(p, idx, cast=float, default=0):
        if idx is None or idx >= len(p):
            return default
        try:
            return cast(float(p[idx]))
        except (TypeError, ValueError):
            return default

    with open(path, encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            p = [clean(x) for x in row]
            if i == 0:
                if p:
                    raw = [normalize_header_token(x) for x in p]
                    for idx, h in enumerate(raw):
                        key = alias_lookup(h, SUMMARY_ALIASES)
                        if key:
                            header_map[key] = idx
                continue

            if not p:
                continue
            if len(p) < 7:
                continue
            try:
                rec = {
                    'gen': to_num(p, header_map.get('gen', 0), int),
                    'best': to_num(p, header_map.get('best', 1), float),
                    'mean': to_num(p, header_map.get('mean', 2), float),
                    'time': to_num(p, header_map.get('time', 3), float),
                    'best_death': p[header_map.get('best_death', 4)].strip() if len(p) > header_map.get('best_death', 4) else '',
                    'pop_death': p[header_map.get('pop_death', 5)].strip() if len(p) > header_map.get('pop_death', 5) else '',
                    'pop_count': to_num(p, header_map.get('pop_count', 6), int)
                }
                if 'eval_n' in header_map:
                    rec['eval_n'] = to_num(p, header_map.get('eval_n'), int)

                # KPIs de test (binario nuevo)
                if 'success_count' in header_map:
                    success_count = to_num(p, header_map.get('success_count'), int)
                    fail_count = to_num(p, header_map.get('fail_count'), int)
                    eval_n = to_num(p, header_map.get('eval_n'), int)
                    if not eval_n:
                        eval_n = success_count + fail_count
                    success_rate = to_num(p, header_map.get('success_rate'), float)
                    fail_rate = to_num(p, header_map.get('fail_rate'), float)
                    if eval_n > 0:
                        if 'success_rate' not in header_map or (success_rate == 0.0 and success_count > 0):
                            success_rate = sdiv(success_count * 100.0, eval_n)
                        if 'fail_rate' not in header_map or (fail_rate == 0.0 and fail_count > 0):
                            fail_rate = sdiv(fail_count * 100.0, eval_n)
                    rec.update({
                        'success_count': success_count,
                        'fail_count': fail_count,
                        'eval_n': eval_n,
                        'fail_hard_count': to_num(p, header_map.get('fail_hard_count'), int),
                        'fail_early_count': to_num(p, header_map.get('fail_early_count'), int),
                        'fail_collision_count': to_num(p, header_map.get('fail_collision_count'), int),
                        'success_rate': success_rate,
                        'fail_rate': fail_rate,
                        'hard_fail_rate': to_num(p, header_map.get('hard_fail_rate'), float),
                    })
                    if 'score' in header_map:
                        rec['score'] = to_num(p, header_map.get('score'), float)

                # Compatibilidad con esquema anterior (fuerte/debil)
                elif 'success_total' in header_map:
                    success_strong_count = to_num(p, header_map.get('success_strong_count'), int)
                    success_weak_count = to_num(p, header_map.get('success_weak_count'), int)
                    fail_hard_count = to_num(p, header_map.get('fail_hard_count'), int)
                    fail_early_count = to_num(p, header_map.get('fail_early_count'), int)
                    fail_collision_count = to_num(p, header_map.get('fail_collision_count'), int)
                    success_total = to_num(p, header_map.get('success_total'), float)
                    rec.update({
                        'success_strong_count': success_strong_count,
                        'success_weak_count': success_weak_count,
                        'success_count': success_strong_count + success_weak_count,
                        'eval_n': to_num(p, header_map.get('eval_n'), int),
                        'fail_hard_count': fail_hard_count,
                        'fail_early_count': fail_early_count,
                        'fail_collision_count': fail_collision_count,
                        'fail_count': fail_hard_count + fail_early_count + fail_collision_count,
                        'success_total': success_total,
                        'success_strong': to_num(p, header_map.get('success_strong'), float),
                        'success_rate': success_total,
                        'fail_rate': max(0.0, 100.0 - success_total),
                        'hard_fail_rate': to_num(p, header_map.get('hard_fail_rate'), float),
                    })
                    if 'score' in header_map:
                        rec['score'] = to_num(p, header_map.get('score'), float)

                rows.append(rec)
            except (TypeError, ValueError, IndexError) as e:
                logging.warning(f'[parse_summary] Row {i} skipped: {type(e).__name__}: {e}')
    rows.sort(key=lambda r: r.get('gen', 0))
    logging.info(f'[parse_summary] Loaded {len(rows)} rows from {os.path.basename(path)}')
    return rows

def parse_debug(path):
    rows = []
    if not os.path.exists(path):
        return rows

    def to_num(parts, idx, cast=float, default=0):
        if idx is None or idx >= len(parts):
            return default
        try:
            return cast(float(parts[idx]))
        except (TypeError, ValueError):
            return default

    header_map = {}

    def build_row(parts):
        t_idx = header_map.get('training')
        death_raw = parts[header_map.get('death', 5)].strip() if len(parts) > header_map.get('death', 5) else ''
        row = {
            '_schema': schema_name,
            '_available_fields': available_fields,
            'gen': to_num(parts, header_map.get('gen', 0), int),
            'car': parts[header_map.get('car', 1)].strip() if len(parts) > header_map.get('car', 1) else '',
            'fit': to_num(parts, header_map.get('fit', 2), float),
            'time': to_num(parts, header_map.get('time', 3), float),
            'spawn': parts[header_map.get('spawn', 4)].strip() if len(parts) > header_map.get('spawn', 4) else '',
            'death': death_raw,
            'death_norm': normalize_reason(death_raw),
            'death_canon': canonical_death_reason(death_raw),
            'death_family': death_family(death_raw),
            'is_test_failure_death': is_test_failure_reason(death_raw),
            'pen_m': to_num(parts, header_map.get('pen_m'), float),
            'pen_v': to_num(parts, header_map.get('pen_v'), float),
            'a': to_num(parts, header_map.get('a'), float),
            'b': to_num(parts, header_map.get('b'), float),
            'c': to_num(parts, header_map.get('c'), float),
            'd': to_num(parts, header_map.get('d'), float),
            'e': to_num(parts, header_map.get('e'), float),
            'f': to_num(parts, header_map.get('f'), float),
            'wait_bonus': to_num(parts, header_map.get('wait_bonus'), float),
            'net': to_num(parts, header_map.get('net'), float),
            'pen_cw': to_num(parts, header_map.get('pen_cw'), float),
            'pen_tv': to_num(parts, header_map.get('pen_tv'), float),
            'pen_creep': to_num(parts, header_map.get('pen_creep'), float),
            'pen_rev': to_num(parts, header_map.get('pen_rev'), float),
            'pen_lazy': to_num(parts, header_map.get('pen_lazy'), float),
            'pen_swstop': to_num(parts, header_map.get('pen_swstop'), float),
            'pen_steer_app': to_num(parts, header_map.get('pen_steer_app'), float),
            'pen_align': to_num(parts, header_map.get('pen_align'), float),
            't_norm': to_num(parts, header_map.get('t_norm'), int),
            't_tot': to_num(parts, header_map.get('t_tot'), int),
            'thr_pos': to_num(parts, header_map.get('thr_pos'), float),
            'thr_grace': to_num(parts, header_map.get('thr_grace'), float),
            'brake_grace': to_num(parts, header_map.get('brake_grace'), float),
            'brake_in': to_num(parts, header_map.get('brake_in'), float),
            'coast_t': to_num(parts, header_map.get('coast_t'), float),
            'stop_brake': to_num(parts, header_map.get('stop_brake'), float),
            'stop_throttle': to_num(parts, header_map.get('stop_throttle'), float),
            't_stop_ctx': to_num(parts, header_map.get('t_stop_ctx'), float),
            't_stop_ctx_tl': to_num(parts, header_map.get('t_stop_ctx_tl'), float),
            't_stop_ctx_stop': to_num(parts, header_map.get('t_stop_ctx_stop'), float),
            't_stop_ctx_yield': to_num(parts, header_map.get('t_stop_ctx_yield'), float),
            'yield_val_t': to_num(parts, header_map.get('yield_val_t'), float),
            'stop_val_t': to_num(parts, header_map.get('stop_val_t'), float),
            'steer_in': to_num(parts, header_map.get('steer_in'), float),
            'steer_target': to_num(parts, header_map.get('steer_target'), float),
            'car_index': to_num(parts, header_map.get('car_index'), int),
            'steer_abs': to_num(parts, header_map.get('steer_abs'), float),
            'mut_changed': to_num(parts, header_map.get('mut_changed'), int),
            'mut_avg_mag': to_num(parts, header_map.get('mut_avg_mag'), float),
            'mut_large': to_num(parts, header_map.get('mut_large'), int),
            'mut_parent_fit': to_num(parts, header_map.get('mut_parent_fit'), float),
            'stop_zones_n': to_num(parts, header_map.get('stop_zones_n'), int),
            'fit_peak_raw': to_num(parts, header_map.get('fit_peak_raw'), float),
            'pen_nav': to_num(parts, header_map.get('pen_nav'), float),
            'stop_bonus': to_num(parts, header_map.get('stop_bonus'), float),
            'stop_done_n': to_num(parts, header_map.get('stop_done_n'), int),
            'yield_bonus': to_num(parts, header_map.get('yield_bonus'), float),
            'yield_done_n': to_num(parts, header_map.get('yield_done_n'), int),
            'round_entered_n': to_num(parts, header_map.get('round_entered_n'), int),
            'round_completed_n': to_num(parts, header_map.get('round_completed_n'), int),
            'round_entry_speed': to_num(parts, header_map.get('round_entry_speed'), float),
            'round_entry_front': to_num(parts, header_map.get('round_entry_front'), float),
            'round_ticks': to_num(parts, header_map.get('round_ticks'), int),
            'round_steer': to_num(parts, header_map.get('round_steer'), float),
            'round_throttle': to_num(parts, header_map.get('round_throttle'), float),
            'round_collisions': to_num(parts, header_map.get('round_collisions'), int),
            'round_bonus': to_num(parts, header_map.get('round_bonus'), float),
            'round_completion_bonus': to_num(parts, header_map.get('round_completion_bonus'), float),
            'round_entry_penalty': to_num(parts, header_map.get('round_entry_penalty'), float),
            'round_throttle_penalty': to_num(parts, header_map.get('round_throttle_penalty'), float),
            'round_current_exit': to_num(parts, header_map.get('round_current_exit'), int),
            'round_dir_first': to_num(parts, header_map.get('round_dir_first'), int),
            'round_dir_second': to_num(parts, header_map.get('round_dir_second'), int),
            'round_dir_third': to_num(parts, header_map.get('round_dir_third'), int),
            'round_exit1_count': to_num(parts, header_map.get('round_exit1_count'), int),
            'round_exit2_count': to_num(parts, header_map.get('round_exit2_count'), int),
            'round_exit3_count': to_num(parts, header_map.get('round_exit3_count'), int),
            'round_exit1_deaths': to_num(parts, header_map.get('round_exit1_deaths'), int),
            'round_exit2_deaths': to_num(parts, header_map.get('round_exit2_deaths'), int),
            'round_exit3_deaths': to_num(parts, header_map.get('round_exit3_deaths'), int),
            'round_exit1_steer': to_num(parts, header_map.get('round_exit1_steer'), float),
            'round_exit2_steer': to_num(parts, header_map.get('round_exit2_steer'), float),
            'round_exit3_steer': to_num(parts, header_map.get('round_exit3_steer'), float),
            'round_exit1_ticks': to_num(parts, header_map.get('round_exit1_ticks'), float),
            'round_exit2_ticks': to_num(parts, header_map.get('round_exit2_ticks'), float),
            'round_exit3_ticks': to_num(parts, header_map.get('round_exit3_ticks'), float),
            'round_exit1_throttle': to_num(parts, header_map.get('round_exit1_throttle'), float),
            'round_exit2_throttle': to_num(parts, header_map.get('round_exit2_throttle'), float),
            'round_exit3_throttle': to_num(parts, header_map.get('round_exit3_throttle'), float),
            'car_overlaps': to_num(parts, header_map.get('car_overlaps'), int),
            'yield_free_passes': to_num(parts, header_map.get('yield_free_passes'), int),
            'yield_validation_speed': to_num(parts, header_map.get('yield_validation_speed'), float),
            'crossing_blocked_t': to_num(parts, header_map.get('crossing_blocked_t'), float),
            'front_obst_death': to_num(parts, header_map.get('front_obst_death'), float),
            'steer_app_wrong': to_num(parts, header_map.get('steer_app_wrong'), float),
            'steer_app_right': to_num(parts, header_map.get('steer_app_right'), float),
            'car_overlap_pen_shadow': to_num(parts, header_map.get('car_overlap_pen_shadow'), float),
            'car_overlap_penalty': to_num(parts, header_map.get('car_overlap_penalty'), float),
            'queue_wait_bonus': to_num(parts, header_map.get('queue_wait_bonus'), float),
            'first_steer_release_ticks': to_num(parts, header_map.get('first_steer_release_ticks'), int),
            'training': parse_bool_token(parts[t_idx]) if t_idx is not None and t_idx < len(parts) else None,
        }
        row['stop_violation_subtype'] = stop_violation_subtype(death_raw)
        row['collision_context'] = collision_death_context(row)
        row['death_family_detail'] = death_family_detail_for_row(row)
        return row

    with open(path, encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            p = [clean(x) for x in row]
            if i == 0:
                if p:
                    raw = [normalize_header_token(x) for x in p]
                    for idx, h in enumerate(raw):
                        key = alias_lookup(h, DEBUG_ALIASES)
                        if key and key not in header_map:
                            header_map[key] = idx
                    available_fields = tuple(sorted(header_map.keys()))
                    schema_name = detect_debug_schema(available_fields)

                    # Si la cabecera viene fusionada con la primera fila, recuperarla.
                    if header_map:
                        header_end = max(header_map.values())
                        if len(p) > (header_end + 1):
                            tail = p[header_end + 1:]
                            gen_suffix = ''
                            m = re.search(r'(\d+)$', clean(p[header_end]))
                            if m:
                                gen_suffix = m.group(1)
                            if gen_suffix and len(tail) >= 6:
                                merged_first_row = [gen_suffix] + tail
                                try:
                                    rows.append(build_row(merged_first_row))
                                except (TypeError, ValueError, IndexError):
                                    pass
                continue

            if not p:
                continue
            if len(p) < 6:
                continue
            try:
                rows.append(build_row(p))
            except (TypeError, ValueError, IndexError) as e:
                logging.warning(f'[parse_debug] Row {i} skipped: {type(e).__name__}: {e}')
    logging.info(f'[parse_debug] Loaded {len(rows)} rows from {os.path.basename(path)}')
    # Derivadas compatibles con logs 27-04-2026 y posteriores.
    mutation_bounds = infer_carindex_bounds(rows)
    for r in rows:
        t_norm = max(float(r.get('t_norm', 0.0)), 1.0)
        t_tot = max(float(r.get('t_tot', 0.0)), 1.0)
        r['steer_in_avg'] = sdiv(r.get('steer_in', 0.0), t_norm)
        r['steer_target_avg'] = sdiv(r.get('steer_target', 0.0), t_norm)
        r['steer_abs_avg'] = sdiv(r.get('steer_abs', 0.0), t_norm)
        r['steer_gap_abs'] = abs(r.get('steer_in', 0.0) - r.get('steer_target', 0.0))
        r['steer_gap_avg_abs'] = abs(r.get('steer_in_avg', 0.0) - r.get('steer_target_avg', 0.0))
        r['stop_ctx_ratio'] = sdiv(r.get('t_stop_ctx', 0.0), t_tot)
        r['stop_ctx_tl_ratio'] = sdiv(r.get('t_stop_ctx_tl', 0.0), t_tot)
        r['stop_ctx_stop_ratio'] = sdiv(r.get('t_stop_ctx_stop', 0.0), t_tot)
        r['stop_ctx_yield_ratio'] = sdiv(r.get('t_stop_ctx_yield', 0.0), t_tot)
        r['brake_share'] = sdiv(r.get('brake_in', 0.0), r.get('brake_in', 0.0) + r.get('thr_pos', 0.0))
        r['grace_brake_share'] = sdiv(r.get('brake_grace', 0.0), r.get('brake_grace', 0.0) + r.get('thr_grace', 0.0))
        r['stop_brake_share'] = sdiv(r.get('stop_brake', 0.0), r.get('stop_brake', 0.0) + r.get('stop_throttle', 0.0))
        r['pen_v_per_life_sec'] = sdiv(r.get('pen_v', 0.0), max(r.get('time', 0.0), 1.0))
        r['pen_v_fit_share'] = sdiv(r.get('pen_v', 0.0) * 100.0, max(abs(r.get('fit', 0.0)), 1.0))
        r['car_overlap_per_sec'] = sdiv(r.get('car_overlaps', 0.0), max(r.get('time', 0.0), 1.0))
        r['car_overlap_per_tick'] = sdiv(r.get('car_overlaps', 0.0), t_tot)
        r['car_overlap_shadow_per_overlap'] = sdiv(
            r.get('car_overlap_pen_shadow', 0.0),
            max(r.get('car_overlaps', 0.0), 1.0),
        )
        r['car_overlap_penalty_per_overlap'] = sdiv(
            r.get('car_overlap_penalty', 0.0),
            max(r.get('car_overlaps', 0.0), 1.0),
        )
        r['queue_wait_bonus_per_life_sec'] = sdiv(r.get('queue_wait_bonus', 0.0), max(r.get('time', 0.0), 1.0))
        r['queue_wait_bonus_fit_share'] = sdiv(
            r.get('queue_wait_bonus', 0.0) * 100.0,
            max(abs(r.get('fit', 0.0)), 1.0),
        )
        r['yield_validation_seen'] = 1.0 if (
            r.get('yield_validation_speed', 0.0) > 0.0
            or r.get('yield_free_passes', 0.0) > 0.0
            or r.get('yield_done_n', 0.0) > 0.0
        ) else 0.0
        r['crossing_blocked_per_stop_tick'] = sdiv(r.get('crossing_blocked_t', 0.0), max(r.get('t_stop_ctx', 0.0), 1.0))
        r['crossing_blocked_per_life_sec'] = sdiv(r.get('crossing_blocked_t', 0.0), max(r.get('time', 0.0), 1.0))
        r['front_obst_death_seen'] = 1.0 if (
            r.get('front_obst_death', 0.0) > 0.0
            or is_collision_reason(r.get('death', ''))
        ) else 0.0
        r['first_steer_release_seen'] = 1.0 if r.get('first_steer_release_ticks', 0.0) > 0.0 else 0.0
        r['steer_app_total'] = r.get('steer_app_wrong', 0.0) + r.get('steer_app_right', 0.0)
        r['steer_app_wrong_share'] = sdiv(r.get('steer_app_wrong', 0.0), r.get('steer_app_total', 0.0))
        r['steer_app_wrong_per_tick'] = sdiv(r.get('steer_app_wrong', 0.0), t_tot)
        r['steer_app_right_per_tick'] = sdiv(r.get('steer_app_right', 0.0), t_tot)
        val_total = r.get('yield_val_t', 0.0) + r.get('stop_val_t', 0.0)
        r['val_total'] = val_total
        r['val_per_stop_tick'] = sdiv(val_total, max(r.get('t_stop_ctx', 0.0), 1.0))
        r['stop_zones_rate'] = sdiv(r.get('stop_zones_n', 0.0), max(r.get('time', 0.0), 1.0))
        peak_raw = r.get('fit_peak_raw', 0.0)
        fit_peak_gain = peak_raw - r.get('fit', 0.0)
        r['fit_peak_gain'] = fit_peak_gain
        r['fit_peak_gain_pct'] = sdiv(fit_peak_gain * 100.0, max(abs(peak_raw), 1.0))
        mut_changed = r.get('mut_changed', 0.0)
        r['mut_rate'] = sdiv(mut_changed, WEIGHTS_TOTAL)
        r['mut_large_rate'] = sdiv(r.get('mut_large', 0.0), WEIGHTS_TOTAL)
        r['mut_large_share'] = sdiv(r.get('mut_large', 0.0), max(mut_changed, 1.0))
        r['mut_strength'] = r.get('mut_avg_mag', 0.0) * mut_changed
        mutation_profile = mutation_profile_for_row(r, bounds=mutation_bounds)
        r['mutation_kind'] = mutation_profile['kind']
        r['is_weight_initialization'] = mutation_profile['is_initialization']
        r['expected_mut_rate'] = mutation_profile['expected_rate']
        r['expected_mut_rate_min'] = mutation_profile.get('expected_min')
        r['expected_mut_rate_max'] = mutation_profile.get('expected_max')
        if mutation_profile['expected_rate'] is not None:
            r['mut_rate_error'] = r['mut_rate'] - mutation_profile['expected_rate']
        else:
            # MutationRate is a probability; an individual car can legitimately
            # realize 0 changes even when the expected range is non-zero.
            r['mut_rate_error'] = 0.0
        if r.get('mut_parent_fit', 0.0) != 0.0:
            r['mut_parent_delta'] = r.get('fit', 0.0) - r.get('mut_parent_fit', 0.0)
            r['mut_parent_delta_pct'] = sdiv(r['mut_parent_delta'] * 100.0, abs(r.get('mut_parent_fit', 0.0)))
        else:
            r['mut_parent_delta'] = 0.0
            r['mut_parent_delta_pct'] = 0.0
        stop_done_n = r.get('stop_done_n', 0.0)
        yield_done_n = r.get('yield_done_n', 0.0)
        r['stop_bonus_per'] = sdiv(r.get('stop_bonus', 0.0), max(stop_done_n, 1.0))
        r['yield_bonus_per'] = sdiv(r.get('yield_bonus', 0.0), max(yield_done_n, 1.0))
        stop_zone_den = max(r.get('stop_zones_n', 0.0), 1.0)
        r['stop_done_rate'] = sdiv(stop_done_n, stop_zone_den)
        r['yield_done_rate'] = sdiv(yield_done_n, stop_zone_den)
        round_entered = r.get('round_entered_n', 0.0)
        round_ticks = r.get('round_ticks', 0.0)
        r['round_completion_rate'] = sdiv(r.get('round_completed_n', 0.0), max(round_entered, 1.0))
        r['round_collision_rate'] = sdiv(r.get('round_collisions', 0.0), max(round_entered, 1.0))
        r['round_entry_speed_avg'] = sdiv(r.get('round_entry_speed', 0.0), max(round_entered, 1.0))
        r['round_entry_front_avg'] = sdiv(r.get('round_entry_front', 0.0), max(round_entered, 1.0))
        r['round_steer_avg'] = sdiv(r.get('round_steer', 0.0), max(round_ticks, 1.0))
        r['round_throttle_avg'] = sdiv(r.get('round_throttle', 0.0), max(round_ticks, 1.0))
        r['round_bonus_per_entry'] = sdiv(r.get('round_bonus', 0.0), max(round_entered, 1.0))
        r['round_bonus_per_completion'] = sdiv(r.get('round_bonus', 0.0), max(r.get('round_completed_n', 0.0), 1.0))
        r['round_bonus_per_tick'] = sdiv(r.get('round_bonus', 0.0), max(round_ticks, 1.0))
        r['round_bonus_fit_share'] = sdiv(r.get('round_bonus', 0.0) * 100.0, max(abs(r.get('fit', 0.0)), 1.0))
        r['round_completion_bonus_per_completion'] = sdiv(
            r.get('round_completion_bonus', 0.0),
            max(r.get('round_completed_n', 0.0), 1.0),
        )
        r['round_entry_penalty_per_entry'] = sdiv(r.get('round_entry_penalty', 0.0), max(round_entered, 1.0))
        r['round_throttle_penalty_per_tick'] = sdiv(r.get('round_throttle_penalty', 0.0), max(round_ticks, 1.0))
        r['round_tick_ratio'] = sdiv(round_ticks, t_tot)
        round_dir_total = (
            r.get('round_dir_first', 0.0)
            + r.get('round_dir_second', 0.0)
            + r.get('round_dir_third', 0.0)
        )
        r['round_dir_first_share'] = sdiv(r.get('round_dir_first', 0.0), round_dir_total)
        r['round_dir_second_share'] = sdiv(r.get('round_dir_second', 0.0), round_dir_total)
        r['round_dir_third_share'] = sdiv(r.get('round_dir_third', 0.0), round_dir_total)
        for exit_num in (1, 2, 3):
            count = r.get(f'round_exit{exit_num}_count', 0.0)
            ticks = r.get(f'round_exit{exit_num}_ticks', 0.0)
            r[f'round_exit{exit_num}_death_rate'] = sdiv(
                r.get(f'round_exit{exit_num}_deaths', 0.0),
                max(count, 1.0),
            )
            r[f'round_exit{exit_num}_steer_avg'] = sdiv(
                r.get(f'round_exit{exit_num}_steer', 0.0),
                max(ticks, 1.0),
            )
            r[f'round_exit{exit_num}_throttle_avg'] = sdiv(
                r.get(f'round_exit{exit_num}_throttle', 0.0),
                max(ticks, 1.0),
            )
    rows.sort(key=lambda r: (r.get('gen', 0), r.get('car_index', 0), r.get('car', '')))
    return rows
