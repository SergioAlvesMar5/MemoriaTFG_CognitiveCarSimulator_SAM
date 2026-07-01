# -*- coding: utf-8 -*-
"""Parte interna de analyse_current.py.

Este archivo se carga desde analyse_current.py dentro del mismo namespace global
para mantener compatibilidad con los imports existentes y con la CLI antigua.
No esta pensado para ejecutarse directamente.
"""

# ── Utilidades ──

import csv
import logging
import math
import os
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from functools import lru_cache

import numpy as np


def clean(s):
    return s.replace('\ufeff', '').strip()

def normalize_header_token(s):
    norm = clean(s).lower()
    for bad, good in (
        ('Ã¡', 'a'), ('Ã©', 'e'), ('Ã­', 'i'), ('Ã³', 'o'), ('Ãº', 'u'),
        ('Ã±', 'n'), ('á', 'a'), ('é', 'e'), ('í', 'i'), ('ó', 'o'),
        ('ú', 'u'), ('ñ', 'n'),
    ):
        norm = norm.replace(bad, good)
    norm = ''.join(
        ch for ch in unicodedata.normalize('NFKD', norm)
        if not unicodedata.combining(ch)
    )
    norm = re.sub(r'[^a-z0-9]+', '', norm)
    # Tolera cabeceras fusionadas con la primera fila (p.ej. "Acum_ReversePenalty1").
    norm = re.sub(r'(?<=[a-z])\d+$', '', norm)
    return norm

def alias_lookup(norm_token, aliases):
    key = aliases.get(norm_token)
    if key:
        return key

    # Tolera prefijos "Debug_" en cabeceras de telemetria.
    if norm_token.startswith('debug'):
        key = aliases.get(norm_token[5:])
        if key:
            return key
    return None

def sdiv(a, b):
    return a / b if b else 0.0

def finite_vals(vals):
    out = []
    for v in vals or []:
        try:
            fv = float(v)
        except (TypeError, ValueError):
            continue
        if math.isfinite(fv):
            out.append(fv)
    return out

def mean(vals):
    vals = finite_vals(vals)
    return sdiv(sum(vals), len(vals)) if vals else 0.0

def num(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default

def mean_field(rows, key, default=0.0):
    return mean([num(r.get(key, default), default) for r in rows]) if rows else 0.0

def mean_abs_delta(rows, left_key, right_key):
    return mean([abs(num(r.get(left_key, 0.0)) - num(r.get(right_key, 0.0))) for r in rows]) if rows else 0.0

def debug_available_fields(rows):
    if not rows:
        return set()
    return set(rows[0].get('_available_fields', ()))

def debug_field_available(rows, key):
    return key in debug_available_fields(rows)

def detect_debug_schema(mapped_keys):
    keys = set(mapped_keys or [])
    if {'b', 'c', 'd', 'e'} & keys:
        return 'legacy-components'
    diagnostics_0107 = {
        'car_overlap_penalty',
        'queue_wait_bonus',
    }
    if diagnostics_0107 & keys:
        return '2026-07-01-overlap-penalty-queue-wait'
    diagnostics_3006 = {
        'yield_free_passes',
        'yield_validation_speed',
        'crossing_blocked_t',
        'front_obst_death',
        'steer_app_wrong',
        'steer_app_right',
        'car_overlap_pen_shadow',
        'first_steer_release_ticks',
    }
    if diagnostics_3006 & keys:
        return '2026-06-30-yield-crossing-overlap-diagnostics'
    if 'car_overlaps' in keys and 'pen_align' in keys and {'round_completion_bonus', 'round_entry_penalty', 'round_throttle_penalty'} & keys:
        return '2026-06-car-overlap-alignment-roundabout-bonus-breakdown'
    if 'car_overlaps' in keys and 'pen_align' in keys:
        return '2026-06-car-overlap-alignment'
    if 'car_overlaps' in keys:
        return '2026-06-car-overlap'
    if 'pen_align' in keys and {'round_completion_bonus', 'round_entry_penalty', 'round_throttle_penalty'} & keys:
        return '2026-06-alignment-roundabout-bonus-breakdown'
    if 'pen_align' in keys:
        return '2026-06-alignment-penalty'
    if {'round_completion_bonus', 'round_entry_penalty', 'round_throttle_penalty'} & keys:
        return '2026-06-roundabout-bonus-breakdown'
    if 'round_bonus' in keys and {'round_exit1_count', 'round_exit2_count', 'round_exit3_count'} <= keys:
        return '2026-06-roundabout-bonus'
    if {'round_exit1_count', 'round_exit2_count', 'round_exit3_count'} <= keys:
        return '2026-06-roundabout-exits'
    if {'round_entered_n', 'round_completed_n', 'round_ticks', 'round_collisions'} <= keys:
        return '2026-06-roundabout'
    if {'a', 'f', 'net', 'stop_bonus', 'yield_bonus', 'pen_nav'} <= keys:
        return '2026-06'
    return 'partial'

def env_flag(name, default=True):
    if name not in os.environ:
        return default
    v = clean(str(os.environ.get(name, ''))).lower()
    if v in ('1', 'true', 't', 'yes', 'y', 'on'):
        return True
    if v in ('0', 'false', 'f', 'no', 'n', 'off'):
        return False
    return default

def infer_population_from_debug(rows):
    if not rows:
        return 0
    max_by_gen = {}
    cnt_by_gen = defaultdict(int)
    for r in rows:
        g = int(num(r.get('gen', 0), 0.0))
        if g <= 0:
            continue
        idx = int(num(r.get('car_index', 0), 0.0))
        if idx > 0:
            max_by_gen[g] = max(max_by_gen.get(g, 0), idx)
            cnt_by_gen[g] += 1
    max_vals = [v for v in max_by_gen.values() if v > 0]
    if max_vals:
        return max(1, int(round(pctl(max_vals, 50))))
    cnt_vals = [v for v in cnt_by_gen.values() if v > 0]
    if cnt_vals:
        return max(1, int(round(pctl(cnt_vals, 50))))
    return 0

def infer_carindex_bounds(rows=None, analysis_mode=None, pop_est=None):
    if analysis_mode is None:
        analysis_mode = MODE
    if 'ANALYSE_CARINDEX_DYNAMIC' in os.environ:
        use_dynamic = env_flag('ANALYSE_CARINDEX_DYNAMIC', True)
    else:
        use_dynamic = True
        if any(k in os.environ for k in (
            'ANALYSE_CARINDEX_MUT_LOADED_END',
            'ANALYSE_CARINDEX_MUT_SESSION_END',
            'ANALYSE_CARINDEX_MUT_BEST_END',
        )):
            use_dynamic = False

    bounds = {
        'mut_loaded_end': CARINDEX_MUT_LOADED_END,
        'mut_session_end': CARINDEX_MUT_SESSION_END,
        'mut_each': 0,
        'pop_est': pop_est or 0,
        'source': 'fixed',
    }

    if use_dynamic:
        if pop_est is None and rows:
            pop_est = infer_population_from_debug(rows)
        if pop_est and pop_est > 0:
            mut_each = max(0, int((pop_est - 2) * 0.4))
            mut_loaded_end = 2 + mut_each
            mut_session_end = mut_loaded_end + mut_each
            mut_loaded_end = max(2, min(mut_loaded_end, pop_est))
            mut_session_end = max(mut_loaded_end, min(mut_session_end, pop_est))
            bounds.update({
                'mut_loaded_end': mut_loaded_end,
                'mut_session_end': mut_session_end,
                'mut_each': mut_each,
                'pop_est': pop_est,
                'source': 'dynamic',
            })
        else:
            bounds['source'] = 'fallback'

    return bounds

def car_index_family(value, analysis_mode=None, bounds=None, pop_est=None):
    if analysis_mode is None:
        analysis_mode = MODE
    if analysis_mode == 'test':
        return 'LOADED'
    try:
        idx = int(round(float(value)))
    except (TypeError, ValueError):
        return 'UNKNOWN'
    # Treat non-positive indices as UNKNOWN by default, but when
    # analysing in test-like modes prefer to classify them as LOADED
    # (the test run always uses the loaded model).
    if idx <= 0:
        if isinstance(analysis_mode, str) and 'test' in analysis_mode:
            return 'LOADED'
        return 'UNKNOWN'
    if idx == 1:
        return 'LOADED'
    if idx == 2:
        return 'SESSION'
    if bounds is None:
        bounds = infer_carindex_bounds(None, analysis_mode=analysis_mode, pop_est=pop_est)
    mut_loaded_end = bounds.get('mut_loaded_end', CARINDEX_MUT_LOADED_END)
    mut_session_end = bounds.get('mut_session_end', CARINDEX_MUT_SESSION_END)
    if 3 <= idx <= mut_loaded_end:
        return 'MUT_LOADED'
    if (mut_loaded_end + 1) <= idx <= mut_session_end:
        return 'MUT_SESSION'
    return 'MUT_LOADED_LARGE'

def is_initial_random_brain(row):
    return (
        int(num(row.get('gen', 0), 0.0)) == 1
        and num(row.get('mut_parent_fit', 0.0), 0.0) == 0.0
        and num(row.get('mut_changed', 0.0), 0.0) >= WEIGHTS_TOTAL * 0.95
    )

def car_index_family_for_row(row, analysis_mode=None, bounds=None, pop_est=None):
    """Classify a concrete car, preserving true InitializeRandomBrain rows."""
    if is_initial_random_brain(row):
        return 'RANDOM'
    return car_index_family(
        row.get('car_index', 0),
        analysis_mode=analysis_mode,
        bounds=bounds,
        pop_est=pop_est,
    )

def summarize_car_index_families(rows, analysis_mode=None, bounds=None):
    if analysis_mode is None:
        analysis_mode = MODE
    if bounds is None:
        bounds = infer_carindex_bounds(rows, analysis_mode=analysis_mode)
    by_family = defaultdict(list)
    for r in rows or []:
        by_family[car_index_family_for_row(r, analysis_mode, bounds=bounds)].append(r)

    family_order = [
        'LOADED', 'SESSION', 'MUT_LOADED', 'MUT_SESSION',
        'MUT_LOADED_LARGE', 'RANDOM', 'UNKNOWN',
    ]
    stats = []
    for fam in family_order:
        fam_rows = by_family.get(fam, [])
        if not fam_rows:
            continue
        idx_vals = [num(r.get('car_index', 0), 0.0) for r in fam_rows]
        fit_vals = [r.get('fit', 0.0) for r in fam_rows]
        time_vals = [r.get('time', 0.0) for r in fam_rows]
        yield_vals = [r.get('yield_val_t', 0.0) for r in fam_rows]
        stop_vals = [r.get('stop_val_t', 0.0) for r in fam_rows]
        stats.append({
            'family': fam,
            'n': len(fam_rows),
            'pct': 0.0,
            'car_index_min': min(idx_vals),
            'car_index_max': max(idx_vals),
            'car_index_med': pctl(idx_vals, 50),
            'fit_mean': mean(fit_vals),
            'fit_med': pctl(fit_vals, 50),
            'time_mean': mean(time_vals),
            'time_med': pctl(time_vals, 50),
            'yield_val_med': pctl(yield_vals, 50),
            'stop_val_med': pctl(stop_vals, 50),
        })
    total = len(rows or [])
    for st in stats:
        st['pct'] = sdiv(st['n'] * 100.0, total)
    return stats

def mutation_profile_for_row(row, bounds=None):
    """Classify mutation telemetry according to EvolutionManager 22-06.

    The current Blueprint drives MutationRate from GenerationsWithoutImprovement,
    which is not exported in Fitness_Debug.csv. For mutated families we can only
    report the valid range; exact 0.0 still applies to loaded/session seed cars.
    """
    changed = num(row.get('mut_changed', 0.0), 0.0)
    gen = int(num(row.get('gen', 0), 0.0))
    observed = sdiv(changed, WEIGHTS_TOTAL)

    if is_initial_random_brain(row):
        return {
            'kind': 'INITIAL_RANDOM',
            'is_initialization': True,
            'expected_rate': None,
            'expected_min': None,
            'expected_max': None,
            'observed_rate': observed,
        }

    family = car_index_family_for_row(row, bounds=bounds)
    if gen == 1:
        kind = 'INITIAL_LOADED'
        expected = 0.0
        expected_min = expected_max = 0.0
    elif family in ('LOADED', 'SESSION'):
        kind = family
        expected = 0.0
        expected_min = expected_max = 0.0
    elif family in ('MUT_LOADED', 'MUT_SESSION'):
        kind = family
        expected = None
        expected_min = MUTATION_RATE_DYNAMIC_MIN
        expected_max = MUTATION_RATE_DYNAMIC_MAX
    elif family == 'MUT_LOADED_LARGE':
        kind = 'MUT_LOADED_LARGE'
        expected = None
        expected_min = MUTATION_RATE_LARGE_MIN
        expected_max = MUTATION_RATE_LARGE_MAX
    else:
        kind = family
        expected = None
        expected_min = expected_max = None

    return {
        'kind': kind,
        'is_initialization': False,
        'expected_rate': expected,
        'expected_min': expected_min,
        'expected_max': expected_max,
        'observed_rate': observed,
    }

def stdev(vals):
    vals = finite_vals(vals)
    n = len(vals)
    if n < 2:
        return 0.0
    m = sdiv(sum(vals), n)
    var = sdiv(sum((v - m) ** 2 for v in vals), (n - 1))
    return var ** 0.5

def coef_var(vals):
    m = mean(vals)
    if abs(m) < 1e-12:
        return 0.0
    return sdiv(stdev(vals), abs(m))

def trend_slope(xs, ys):
    """Pendiente de regresion lineal simple y = a + b*x."""
    n = min(len(xs), len(ys))
    if n < 2:
        return 0.0
    x = xs[:n]
    y = ys[:n]
    mx = mean(x)
    my = mean(y)
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    den = sum((xi - mx) ** 2 for xi in x)
    return sdiv(num, den)

def pearson_corr(xs, ys):
    n = min(len(xs), len(ys))
    if n < 2:
        return 0.0
    x = xs[:n]
    y = ys[:n]
    mx = mean(x)
    my = mean(y)
    num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y))
    denx = sum((xi - mx) ** 2 for xi in x)
    deny = sum((yi - my) ** 2 for yi in y)
    den = math.sqrt(max(denx * deny, 0.0))
    return sdiv(num, den)

CORRELATION_EXPOSURE_FIELDS = {
    'stop_bonus_per': 'stop_done_n',
    'yield_bonus_per': 'yield_done_n',
    'stop_done_rate': 'stop_zones_n',
    'yield_done_rate': 'stop_zones_n',
    'round_completion_rate': 'round_entered_n',
    'round_collision_rate': 'round_entered_n',
    'round_entry_speed_avg': 'round_entered_n',
    'round_entry_front_avg': 'round_entered_n',
    'round_bonus': 'round_entered_n',
    'round_bonus_per_entry': 'round_entered_n',
    'round_bonus_per_completion': 'round_completed_n',
    'round_bonus_per_tick': 'round_ticks',
    'round_bonus_fit_share': 'round_entered_n',
    'round_completion_bonus_per_completion': 'round_completed_n',
    'round_entry_penalty_per_entry': 'round_entered_n',
    'round_throttle_penalty_per_tick': 'round_ticks',
    'round_tick_ratio': 't_tot',
    'round_steer_avg': 'round_ticks',
    'round_throttle_avg': 'round_ticks',
    'round_exit1_death_rate': 'round_exit1_count',
    'round_exit2_death_rate': 'round_exit2_count',
    'round_exit3_death_rate': 'round_exit3_count',
    'round_exit1_steer_avg': 'round_exit1_ticks',
    'round_exit2_steer_avg': 'round_exit2_ticks',
    'round_exit3_steer_avg': 'round_exit3_ticks',
    'round_exit1_throttle_avg': 'round_exit1_ticks',
    'round_exit2_throttle_avg': 'round_exit2_ticks',
    'round_exit3_throttle_avg': 'round_exit3_ticks',
    'pen_v_per_life_sec': 'pen_v',
    'pen_v_fit_share': 'pen_v',
    'car_overlap_penalty': 'car_overlaps',
    'car_overlap_penalty_per_overlap': 'car_overlaps',
    'car_overlap_per_sec': 'car_overlaps',
    'car_overlap_per_tick': 'car_overlaps',
    'car_overlap_shadow_per_overlap': 'car_overlaps',
    'queue_wait_bonus': 'queue_wait_bonus',
    'queue_wait_bonus_per_life_sec': 'queue_wait_bonus',
    'queue_wait_bonus_fit_share': 'queue_wait_bonus',
    'yield_validation_speed': 'yield_validation_seen',
    'crossing_blocked_per_stop_tick': 'crossing_blocked_t',
    'crossing_blocked_per_life_sec': 'crossing_blocked_t',
    'front_obst_death': 'front_obst_death_seen',
    'steer_app_wrong_share': 'steer_app_total',
    'steer_app_wrong_per_tick': 'steer_app_wrong',
    'steer_app_right_per_tick': 'steer_app_right',
    'first_steer_release_ticks': 'first_steer_release_seen',
}

METRIC_REQUIRED_FIELDS = {
    'round_completion_bonus_per_completion': 'round_completion_bonus',
    'round_entry_penalty_per_entry': 'round_entry_penalty',
    'round_throttle_penalty_per_tick': 'round_throttle_penalty',
    'car_overlap_shadow_per_overlap': 'car_overlap_pen_shadow',
    'car_overlap_penalty_per_overlap': 'car_overlap_penalty',
    'queue_wait_bonus_per_life_sec': 'queue_wait_bonus',
    'queue_wait_bonus_fit_share': 'queue_wait_bonus',
}

def correlation_sample(rows, key):
    """Fitness y metrica solo donde esta ultima tiene exposicion real."""
    xs, ys = [], []
    for row in rows:
        fit = num(row.get('fit', 0.0), 0.0)
        value = metric_value_for_row(row, key)
        if value is not None and math.isfinite(fit) and math.isfinite(value):
            xs.append(fit)
            ys.append(value)
    return xs, ys

def metric_value_for_row(row, key):
    """Valor por fila, devolviendo None cuando la metrica no aplica."""
    required_key = METRIC_REQUIRED_FIELDS.get(key)
    if required_key and required_key not in row.get('_available_fields', ()):
        return None
    exposure_key = CORRELATION_EXPOSURE_FIELDS.get(key)
    if exposure_key and num(row.get(exposure_key, 0.0), 0.0) <= 0.0:
        return None
    if key == 'steer_gap_abs':
        return abs(num(row.get('steer_in', 0.0), 0.0) - num(row.get('steer_target', 0.0), 0.0))
    return num(row.get(key, 0.0), 0.0)

def metric_values(rows, key):
    vals = []
    for row in rows:
        value = metric_value_for_row(row, key)
        if value is not None and math.isfinite(value):
            vals.append(value)
    return vals

def metric_exposure_count(rows, key):
    required_key = METRIC_REQUIRED_FIELDS.get(key)
    if required_key and required_key not in debug_available_fields(rows):
        return 0
    exposure_key = CORRELATION_EXPOSURE_FIELDS.get(key)
    if not exposure_key:
        return len(rows)
    return sum(1 for row in rows if num(row.get(exposure_key, 0.0), 0.0) > 0.0)

def exposed_mean(rows, key):
    vals = metric_values(rows, key)
    return mean(vals), len(vals)

def ratio_or_nan(numer, denom, scale=1.0):
    if denom <= 0:
        return np.nan
    return sdiv(numer * scale, denom)

def longest_streak(values, predicate):
    best = 0
    cur = 0
    for v in values:
        if predicate(v):
            cur += 1
            if cur > best:
                best = cur
        else:
            cur = 0
    return best

def parse_bool_token(v):
    if isinstance(v, bool):
        return v
    s = clean(str(v)).lower()
    if s in ('1', '1.0', 'true', 't', 'yes', 'y', 'si', 'sí', 'train', 'training'):
        return True
    if s in ('0', '0.0', 'false', 'f', 'no', 'n', 'test', 'testing'):
        return False
    return None

def target_training_for_mode(mode):
    if mode == 'train':
        return True
    if mode == 'test':
        return False
    return None

def split_debug_by_phase(rows):
    train_rows, test_rows, unknown_rows = [], [], []
    for r in rows:
        flag = r.get('training')
        if flag is True:
            train_rows.append(r)
        elif flag is False:
            test_rows.append(r)
        else:
            unknown_rows.append(r)
    has_flag = (len(train_rows) + len(test_rows)) > 0
    return train_rows, test_rows, unknown_rows, has_flag

def select_debug_rows_by_mode(rows, mode):
    train_rows, test_rows, unknown_rows, has_flag = split_debug_by_phase(rows)
    if not rows:
        return rows, {
            'has_training_flag': False,
            'raw_total': 0,
            'selected_total': 0,
            'train_total': 0,
            'test_total': 0,
            'unknown_total': 0,
            'mode': mode,
        }

    if not has_flag:
        selected = rows
    elif mode == 'train':
        selected = train_rows + unknown_rows
    elif mode == 'test':
        selected = test_rows + unknown_rows
    else:
        selected = rows

    info = {
        'has_training_flag': has_flag,
        'raw_total': len(rows),
        'selected_total': len(selected),
        'train_total': len(train_rows),
        'test_total': len(test_rows),
        'unknown_total': len(unknown_rows),
        'mode': mode,
    }
    return selected, info

def align_debug_to_completed_summary(summary_rows, debug_rows, mode):
    """Exclude debug rows from generations not yet closed in the summary."""
    if mode not in ('train', 'test') or not summary_rows or not debug_rows:
        return debug_rows, {
            'excluded_rows': 0,
            'excluded_generations': [],
        }

    completed_gens = {int(num(r.get('gen', 0), 0.0)) for r in summary_rows}
    completed_gens.discard(0)
    selected = []
    excluded = []
    for row in debug_rows:
        gen = int(num(row.get('gen', 0), 0.0))
        if gen in completed_gens:
            selected.append(row)
        else:
            excluded.append(row)
    return selected, {
        'excluded_rows': len(excluded),
        'excluded_generations': sorted(set(int(num(r.get('gen', 0), 0.0)) for r in excluded)),
    }

def detect_mode_from_inputs(debug_rows, train_summary, test_summary):
    train_rows, test_rows, unknown_rows, has_flag = split_debug_by_phase(debug_rows)
    train_n = len(train_summary)
    test_n = len(test_summary)
    reason_parts = []

    mode = ''
    if has_flag:
        if train_rows and test_rows:
            mode = 'traintest'
            reason_parts.append('Fitness_Debug contiene filas TRAIN y TEST.')
        elif train_rows:
            mode = 'train'
            reason_parts.append('Fitness_Debug contiene solo filas TRAIN.')
        elif test_rows:
            mode = 'test'
            reason_parts.append('Fitness_Debug contiene solo filas TEST.')
    else:
        reason_parts.append('Fitness_Debug no tiene Training/TrainingMode util.')

    if not mode:
        if train_n and test_n:
            mode = 'traintest'
            reason_parts.append('Ambos summaries tienen datos.')
        elif train_n:
            mode = 'train'
            reason_parts.append('Solo Training_Summary tiene datos.')
        elif test_n:
            mode = 'test'
            reason_parts.append('Solo Test_Summary tiene datos.')
        else:
            mode = 'train'
            reason_parts.append('Sin datos suficientes, fallback=train.')

    info = {
        'mode': mode,
        'reason': ' '.join(reason_parts).strip(),
        'has_training_flag': has_flag,
        'train_debug_rows': len(train_rows),
        'test_debug_rows': len(test_rows),
        'unknown_debug_rows': len(unknown_rows),
        'train_summary_rows': train_n,
        'test_summary_rows': test_n,
    }
    return mode, info

def mode_label(mode):
    if mode == 'train':
        return 'ENTRENAMIENTO'
    if mode == 'test':
        return 'TEST'
    if mode == 'traintest':
        return 'TRAIN+TEST'
    return 'AUTO'

def infer_label_from_debug_rows(rows, fallback=None):
    if fallback is None:
        fallback = LABEL
    train_rows, test_rows, _, has_flag = split_debug_by_phase(rows or [])
    if not has_flag:
        return fallback
    if train_rows and test_rows:
        return mode_label('traintest')
    if train_rows:
        return mode_label('train')
    if test_rows:
        return mode_label('test')
    return fallback

def inspect_csv_layout(path, aliases, required_keys, min_cols=0):
    meta = {
        'path': path,
        'exists': os.path.exists(path),
        'size_bytes': 0,
        'mtime': '',
        'header': [],
        'mapped_keys': [],
        'unknown_headers': [],
        'duplicate_headers': [],
        'duplicate_mapped_keys': [],
        'missing_required': list(required_keys),
        'data_rows': 0,
        'empty_rows': 0,
        'short_rows': 0,
        'long_rows': 0,
        'header_cols': 0,
        'max_cols': 0,
        'loaded_rows': 0,
        'discarded_rows': 0,
    }
    if not meta['exists']:
        return meta

    meta['size_bytes'] = os.path.getsize(path)
    try:
        meta['mtime'] = datetime.fromtimestamp(os.path.getmtime(path)).strftime('%Y-%m-%d %H:%M:%S')
    except OSError:
        meta['mtime'] = ''

    header_map = {}
    schema_name = 'partial'
    available_fields = ()
    with open(path, encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            p = [clean(x) for x in row]
            if i == 0:
                meta['header'] = p
                meta['header_cols'] = len(p)
                meta['max_cols'] = len(p)
                norm = [normalize_header_token(x) for x in p]
                unknown = []
                seen_headers = defaultdict(list)
                seen_mapped = defaultdict(list)
                for idx, h in enumerate(norm):
                    if h:
                        seen_headers[h].append(p[idx])
                    key = alias_lookup(h, aliases)
                    if key:
                        seen_mapped[key].append(p[idx])
                        if key not in header_map:
                            header_map[key] = idx
                    else:
                        unknown.append(p[idx])
                meta['mapped_keys'] = sorted(header_map.keys())
                meta['unknown_headers'] = [u for u in unknown if u]
                meta['duplicate_headers'] = [
                    f'{vals[0]} x{len(vals)}'
                    for vals in seen_headers.values()
                    if len(vals) > 1 and vals[0]
                ]
                meta['duplicate_mapped_keys'] = [
                    f'{key}: {short_list(vals, 4)}'
                    for key, vals in sorted(seen_mapped.items())
                    if len(vals) > 1
                ]
                meta['missing_required'] = [k for k in required_keys if k not in header_map]
                continue

            if not p or not any(p):
                meta['empty_rows'] += 1
                continue
            meta['data_rows'] += 1
            meta['max_cols'] = max(meta.get('max_cols', 0), len(p))
            if min_cols and len(p) < min_cols:
                meta['short_rows'] += 1
            if meta.get('header_cols', 0) and len(p) > meta.get('header_cols', 0):
                meta['long_rows'] += 1
    
    if meta['exists']:
        logging.debug(f"[inspect_csv_layout] {os.path.basename(path)}: {meta['data_rows']} data rows, {meta['empty_rows']} empty, {meta['short_rows']} short, missing: {meta['missing_required']}")
    return meta

def quick_debug_snapshot(path, target_training=None):
    out = {
        'rows': 0,
        'lazy_rows': 0,
        'top_death': '',
        'top_death_count': 0,
        'top_death_pct': 0.0,
    }
    if not os.path.exists(path):
        return out

    death_idx = None
    training_idx = None
    deaths = Counter()
    with open(path, encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if i == 0:
                p = [clean(x) for x in row]
                norm = [normalize_header_token(x) for x in p]
                for idx, h in enumerate(norm):
                    mapped = alias_lookup(h, DEBUG_ALIASES)
                    if mapped == 'death':
                        death_idx = idx
                    elif mapped == 'training':
                        training_idx = idx
                continue
            if not row or not any(row):
                continue

            if target_training is not None and training_idx is not None and training_idx < len(row):
                row_training = parse_bool_token(row[training_idx])
                if row_training is not None and row_training != target_training:
                    continue

            out['rows'] += 1
            if death_idx is None or death_idx >= len(row):
                continue
            reason = row[death_idx].strip()
            if not reason:
                continue
            deaths[reason] += 1
            if is_lazy_reason(reason):
                out['lazy_rows'] += 1

    if deaths:
        top, cnt = deaths.most_common(1)[0]
        out['top_death'] = top
        out['top_death_count'] = cnt
        out['top_death_pct'] = sdiv(cnt * 100.0, out['rows'])
    return out

def summarize_session(summary_rows, dbg_rows_count=0, lazy_rows=0, top_death='', debug_rows=None):
    metrics = {
        'gens': len(summary_rows),
        'best_max': 0.0,
        'best_mean': 0.0,
        'mean_mean': 0.0,
        'time_mean': 0.0,
        'neg_pct': 0.0,
        'success_mean': 0.0,
        'debug_rows': dbg_rows_count,
        'lazy_pct': sdiv(lazy_rows * 100.0, dbg_rows_count),
        'top_death': top_death,
    }
    if not summary_rows:
        # Fallback para sesiones con Summary vacio pero Debug disponible.
        if debug_rows:
            fits = [r.get('fit', 0.0) for r in debug_rows]
            times = [r.get('time', 0.0) for r in debug_rows]
            if fits:
                metrics.update({
                    'best_max': max(fits),
                    'best_mean': mean(fits),
                    'mean_mean': mean(fits),
                    'time_mean': mean(times),
                    'neg_pct': sdiv(sum(1 for v in fits if v < 0) * 100.0, len(fits)),
                })
        return metrics

    bests = [r['best'] for r in summary_rows]
    means = [r['mean'] for r in summary_rows]
    times = [r['time'] for r in summary_rows]
    metrics.update({
        'best_max': max(bests),
        'best_mean': mean(bests),
        'mean_mean': mean(means),
        'time_mean': mean(times),
        'neg_pct': sdiv(sum(1 for v in means if v < 0) * 100.0, len(means)),
    })

    kpis = [r for r in summary_rows if 'success_rate' in r]
    if kpis:
        test_metrics = summarize_test_results(summary_rows)
        metrics['success_mean'] = test_metrics['success_rate']
        metrics['success_median'] = test_metrics['success_median']
        metrics['success_std'] = test_metrics['success_std']
        metrics['test_evaluations'] = test_metrics['total_n']
    return metrics

def collect_previous_sessions(mode, summary_file, out_dir, limit=8):
    root = os.path.join(BASE_DIR, 'Analisis')
    if not os.path.isdir(root):
        return []

    pref = f'{mode}_'
    names = []
    for name in os.listdir(root):
        full = os.path.join(root, name)
        if name.startswith(pref) and os.path.isdir(full):
            names.append(name)
    names.sort()
    current_out = os.path.abspath(out_dir)
    names = [
        name for name in names
        if os.path.abspath(os.path.join(root, name)) != current_out
    ][-max(1, limit):]

    sessions = []
    summary_names = []
    if mode == 'traintest':
        summary_names = [os.path.basename(TRAIN_SUMMARY_FILE), os.path.basename(TEST_SUMMARY_FILE)]
    elif summary_file:
        summary_names = [os.path.basename(summary_file)]

    target_training = target_training_for_mode(mode)
    for name in names:
        full = os.path.join(root, name)

        s_rows = []
        for summary_name in summary_names:
            s_path = os.path.join(full, summary_name)
            if os.path.exists(s_path):
                s_rows.extend(parse_summary(s_path))
        if s_rows:
            s_rows.sort(key=lambda r: r.get('gen', 0))

        d_path = os.path.join(full, 'Fitness_Debug.csv')
        dbg_snap = quick_debug_snapshot(d_path, target_training=target_training)
        dbg_rows_fallback = None
        if (not s_rows) and os.path.exists(d_path):
            try:
                dbg_rows_full = parse_debug(d_path)
                dbg_rows_fallback, _ = select_debug_rows_by_mode(dbg_rows_full, mode)
            except Exception:
                dbg_rows_fallback = None
        m = summarize_session(
            s_rows,
            dbg_rows_count=dbg_snap['rows'],
            lazy_rows=dbg_snap['lazy_rows'],
            top_death=dbg_snap['top_death'],
            debug_rows=dbg_rows_fallback,
        )
        m['session'] = name
        sessions.append(m)

    return sessions

def short_list(items, max_items=10):
    if not items:
        return '-'
    if len(items) <= max_items:
        return ', '.join(str(x) for x in items)
    shown = ', '.join(str(x) for x in items[:max_items])
    return f'{shown} ... (+{len(items)-max_items})'

def estimate_population_size(summary_rows, default=60):
    ns = [int(r.get('eval_n', 0)) for r in summary_rows if r.get('eval_n', 0)]
    ns = [n for n in ns if n > 0]
    if not ns:
        return default
    # Mediana para robustez ante filas sueltas con N anomalo.
    return max(1, int(round(pctl(ns, 50))))

@lru_cache(maxsize=4096)
def normalize_reason(reason):
    return clean(str(reason or '')).upper()

@lru_cache(maxsize=4096)
def compact_reason(reason):
    return re.sub(r'[^A-Z0-9]+', '', normalize_reason(reason))

@lru_cache(maxsize=4096)
def canonical_death_reason(reason):
    r = normalize_reason(reason)
    r_compact = compact_reason(r)
    if not r_compact:
        return 'UNKNOWN'
    if 'COLLISION' in r_compact:
        return 'COLLISION'
    if 'TRAFFICVIOLATION' in r_compact:
        return 'TRAFFIC_VIOLATION'
    if 'STOPVIOLATION' in r_compact:
        return 'STOP_VIOLATION'
    if 'YIELDVIOLATION' in r_compact:
        return 'YIELD_VIOLATION'
    if 'NAVVIOLATION' in r_compact:
        return 'NAV_VIOLATION'
    if 'INVALIDBRAIN' in r_compact:
        return 'INVALID_BRAIN'
    if 'TIMEFINISHED' in r_compact:
        return 'TIMEFINISHED'
    if 'CORRECTINGWRONG' in r_compact:
        return 'CORRECTING_WRONG'
    if 'REVERSINGWRONG' in r_compact:
        return 'REVERSING_WRONG'
    if 'REVERSE' in r_compact or 'REVERS' in r_compact:
        return 'REVERSE'
    if 'FLIPPED' in r_compact:
        return 'FLIPPED'
    if 'LAZY' in r_compact:
        return 'LAZY'
    return r or 'UNKNOWN'

def is_reverse_reason(reason):
    return 'REVERS' in compact_reason(reason)

@lru_cache(maxsize=4096)
def death_family(reason):
    r = normalize_reason(reason)
    r_compact = compact_reason(reason)
    if not r_compact:
        return 'UNKNOWN'
    if 'COLLISION' in r_compact:
        return 'COLLISION'
    if 'VIOLATION' in r_compact:
        return 'VIOLATION'
    if 'INVALIDBRAIN' in r_compact:
        return 'INVALID_BRAIN'
    if 'TIMEFINISHED' in r_compact:
        return 'TIMEOUT'
    if 'LAZY' in r:
        return 'LAZY'
    if 'CORRECTING' in r:
        return 'CORRECTING'
    if is_reverse_reason(reason):
        return 'REVERSE'
    if 'FLIPPED' in r_compact:
        return 'FLIPPED'
    return 'OTHER'

def is_collision_reason(reason):
    return canonical_death_reason(reason) == 'COLLISION'

@lru_cache(maxsize=4096)
def stop_violation_subtype(reason):
    if canonical_death_reason(reason) != 'STOP_VIOLATION':
        return ''
    r_compact = compact_reason(reason)
    if r_compact.endswith('EXIT') or 'STOPVIOLATIONEXIT' in r_compact:
        return 'EXIT'
    if r_compact.endswith('TIMEOUT') or 'STOPVIOLATIONTIMEOUT' in r_compact:
        return 'TIMEOUT'
    return 'GENERIC'

DEATH_FAMILY_ORDER = (
    'COLLISION',
    'VIOLATION',
    'TIMEOUT',
    'LAZY',
    'CORRECTING',
    'REVERSE',
    'INVALID_BRAIN',
    'FLIPPED',
    'UNKNOWN',
    'OTHER',
)

def death_family_order_index(family):
    try:
        return DEATH_FAMILY_ORDER.index(family)
    except ValueError:
        return len(DEATH_FAMILY_ORDER)

DEATH_FAMILY_DETAIL_ORDER = (
    'COLLISION_ROUNDABOUT',
    'COLLISION_NORMAL',
    'STOP_VIOLATION_EXIT',
    'STOP_VIOLATION_TIMEOUT',
) + DEATH_FAMILY_ORDER

def death_family_detail_order_index(family):
    try:
        return DEATH_FAMILY_DETAIL_ORDER.index(family)
    except ValueError:
        return len(DEATH_FAMILY_DETAIL_ORDER)

def collision_death_context(row):
    if not is_collision_reason(row.get('death', '')):
        return 'NO_COLLISION'
    return 'COLLISION_ROUNDABOUT' if num(row.get('round_collisions', 0.0), 0.0) > 0.0 else 'COLLISION_NORMAL'

def death_family_detail_for_row(row):
    collision_context = collision_death_context(row)
    if collision_context != 'NO_COLLISION':
        return collision_context
    stop_subtype = stop_violation_subtype(row.get('death', ''))
    if stop_subtype in ('EXIT', 'TIMEOUT'):
        return f'STOP_VIOLATION_{stop_subtype}'
    return row.get('death_family') or death_family(row.get('death', ''))

def death_group_color(group):
    if group == 'COLLISION_ROUNDABOUT':
        return 'crimson'
    if group == 'COLLISION_NORMAL':
        return 'tomato'
    if group.startswith('STOP_VIOLATION_'):
        return 'saddlebrown'
    return death_reason_color(group)

def group_debug_death_families(rows, split_roundabout_collisions=True):
    counts = Counter()
    for row in rows:
        if split_roundabout_collisions:
            counts[death_family_detail_for_row(row)] += 1
        else:
            counts[death_family(row.get('death', ''))] += 1
    grouped = [(family, cnt, family) for family, cnt in counts.items()]
    grouped.sort(key=lambda x: (death_family_detail_order_index(x[2]), -x[1], x[0]))
    return grouped

def summarize_collision_deaths(rows):
    total = 0
    roundabout = 0
    normal = 0
    roundabout_events = 0.0
    round_signal_non_collision = 0
    for r in rows:
        round_events = num(r.get('round_collisions', 0.0), 0.0)
        roundabout_events += round_events
        if is_collision_reason(r.get('death', '')):
            total += 1
            if round_events > 0.0:
                roundabout += 1
            else:
                normal += 1
        elif round_events > 0.0:
            round_signal_non_collision += 1
    return {
        'total': total,
        'roundabout': roundabout,
        'normal': normal,
        'roundabout_events': roundabout_events,
        'round_signal_non_collision': round_signal_non_collision,
    }

def summarize_stop_violation_subtypes(rows):
    counts = Counter()
    for row in rows or []:
        subtype = stop_violation_subtype(row.get('death', ''))
        if subtype:
            counts[subtype] += 1
    return counts

def group_death_reasons(deaths):
    family_counts = Counter()
    for reason, cnt in deaths.items():
        family_counts[death_family(reason)] += cnt
    grouped = [(family, cnt, family) for family, cnt in family_counts.items()]
    grouped.sort(key=lambda x: (death_family_order_index(x[2]), -x[1], x[0]))
    return grouped

def death_reason_color(reason):
    fam = death_family(reason)
    if fam == 'LAZY':
        return 'gold'
    if fam == 'COLLISION':
        return 'tomato'
    if fam == 'REVERSE':
        return 'mediumpurple'
    if fam == 'CORRECTING':
        return 'orange'
    if fam == 'VIOLATION':
        return 'brown'
    if fam == 'TIMEOUT':
        return 'seagreen'
    if fam == 'INVALID_BRAIN':
        return 'black'
    if fam == 'FLIPPED':
        return 'darkred'
    return 'gray'

def short_death_reason(reason):
    r = normalize_reason(reason)
    if r in DEATH_FAMILY_DETAIL_ORDER:
        return r
    return (reason or '').replace('COLLISION_WITH_', 'COL_') or 'UNKNOWN'

def is_lazy_reason(reason):
    return canonical_death_reason(reason) == 'LAZY'

def is_invalid_brain_reason(reason):
    return canonical_death_reason(reason) == 'INVALID_BRAIN'

def is_test_failure_reason(reason):
    # Mirrors BP_EvolutionManager CalculateAndExport death-based fail rules
    # from the latest local description (30-06-2026). Fitness/time thresholds
    # are handled in Unreal and are not inferable from DeathReason alone.
    canon = canonical_death_reason(reason)
    if canon in {
        'LAZY',
        'REVERSE',
        'REVERSING_WRONG',
        'CORRECTING_WRONG',
        'TRAFFIC_VIOLATION',
        'STOP_VIOLATION',
        'YIELD_VIOLATION',
        'NAV_VIOLATION',
        'INVALID_BRAIN',
        'FLIPPED',
        'COLLISION',
    }:
        return True
    return False

def classify_test_outcome(row, min_time=None, min_fitness=None, use_fitness=None):
    """Mirror EvolutionManager test rules using configurable runtime assumptions."""
    if min_time is None:
        min_time = TEST_MIN_TIME
    if min_fitness is None:
        min_fitness = TEST_MIN_FITNESS
    if use_fitness is None:
        use_fitness = TEST_USE_FITNESS

    if is_test_failure_reason(row.get('death', '')):
        return 'fail_death'
    if use_fitness and num(row.get('fit', 0.0), 0.0) < min_fitness:
        return 'fail_fitness'
    if num(row.get('time', 0.0), 0.0) < min_time:
        return 'fail_time'
    return 'success'

def reconstruct_test_outcomes(rows):
    counts = Counter(classify_test_outcome(row) for row in rows or [])
    total = sum(counts.values())
    success = counts.get('success', 0)
    fail = total - success
    return {
        'total': total,
        'success': success,
        'fail': fail,
        'success_rate': sdiv(success * 100.0, total),
        'fail_rate': sdiv(fail * 100.0, total),
        'counts': dict(counts),
        'min_time': TEST_MIN_TIME,
        'min_fitness': TEST_MIN_FITNESS,
        'use_fitness': TEST_USE_FITNESS,
    }

def add_family_separators(ax, grouped):
    last_fam = None
    for idx, (_, _, fam) in enumerate(grouped):
        if last_fam is None:
            last_fam = fam
            continue
        if fam != last_fam:
            ax.axhline(idx - 0.5, color='k', linewidth=0.6, alpha=0.2)
            last_fam = fam

def is_time_finished_reason(reason):
    return 'TIMEFINISHED' in compact_reason(reason)

def detect_yield_stuck_candidates(dbg_rows):
    info = {
        'total_rows': len(dbg_rows),
        'timefinished_rows': 0,
        'timefinished_pct': 0.0,
        'candidate_count': 0,
        'candidate_pct_timefinished': 0.0,
        'watch_count': 0,
        'watch_pct_timefinished': 0.0,
        'fit_thr': 0.0,
        'fitps_thr': 0.0,
        'stop_ctx_thr': 0.0,
        'stop_ticks_thr': 0.0,
        'time_thr': 0.0,
        'creep_thr': 0.0,
        'score_candidate_thr': 0.0,
        'score_watch_thr': 0.0,
        'candidates': [],
        'watchlist': [],
        'spawns': [],
        'gens': [],
        'tf_by_gen': [],
        'candidate_by_gen': [],
        'watch_by_gen': [],
        'tf_by_spawn': [],
        'candidate_by_spawn': [],
        'watch_by_spawn': [],
    }
    if not dbg_rows:
        return info

    def envf(name, default, lo=None, hi=None):
        try:
            v = float(os.environ.get(name, default))
        except (TypeError, ValueError):
            v = float(default)
        if lo is not None:
            v = max(float(lo), v)
        if hi is not None:
            v = min(float(hi), v)
        return v

    def envi(name, default, lo=None, hi=None):
        try:
            v = int(float(os.environ.get(name, default)))
        except (TypeError, ValueError):
            v = int(default)
        if lo is not None:
            v = max(int(lo), v)
        if hi is not None:
            v = min(int(hi), v)
        return v

    fit_pctl = envf('ANALYSE_YIELD_TRAP_FIT_PCTL', 50.0, 5.0, 95.0)
    fitps_pctl = envf('ANALYSE_YIELD_TRAP_FITPS_PCTL', 50.0, 5.0, 95.0)
    stop_pctl = envf('ANALYSE_YIELD_TRAP_STOP_CTX_PCTL', 75.0, 5.0, 95.0)
    stop_ticks_pctl = envf('ANALYSE_YIELD_TRAP_STOP_TICKS_PCTL', 75.0, 5.0, 95.0)
    time_pctl = envf('ANALYSE_YIELD_TRAP_TIME_PCTL', 65.0, 5.0, 95.0)
    creep_pctl = envf('ANALYSE_YIELD_TRAP_CREEP_PCTL', 80.0, 5.0, 95.0)

    min_stop_ratio = envf('ANALYSE_YIELD_TRAP_MIN_STOP_CTX_RATIO', 0.25, 0.0, 1.0)
    min_stop_ratio_small = envf('ANALYSE_YIELD_TRAP_MIN_STOP_CTX_RATIO_SMALL', 0.20, 0.0, 1.0)
    min_time_sec = envf('ANALYSE_YIELD_TRAP_MIN_TIME_SEC', 0.0, 0.0, None)
    min_stop_ticks_abs = envf('ANALYSE_YIELD_TRAP_MIN_STOP_TICKS', 10.0, 0.0, None)
    min_yield_ctx_share = envf('ANALYSE_YIELD_TRAP_MIN_YIELD_CTX_SHARE', 0.34, 0.0, 1.0)
    min_yield_ctx_share_watch = envf('ANALYSE_YIELD_TRAP_MIN_YIELD_CTX_SHARE_WATCH', 0.22, 0.0, 1.0)
    min_stop_ratio_total = envf('ANALYSE_YIELD_TRAP_MIN_STOP_CTX_RATIO_TOTAL', 0.05, 0.0, 1.0)
    min_yield_ratio_total = envf('ANALYSE_YIELD_TRAP_MIN_YIELD_RATIO_TOTAL', 0.02, 0.0, 1.0)
    min_yield_ticks_abs = envf('ANALYSE_YIELD_TRAP_MIN_YIELD_TICKS_ABS', 5.0, 0.0, None)
    min_validation_sec = envf('ANALYSE_YIELD_TRAP_MIN_VALIDATION_SEC', 0.5, 0.0, None)

    small_n = envi('ANALYSE_YIELD_TRAP_SMALL_SAMPLE_N', 6, 1, 9999)
    score_candidate_thr = envf('ANALYSE_YIELD_TRAP_SCORE_CANDIDATE', 3.2, 0.1, 20.0)
    score_watch_thr = envf('ANALYSE_YIELD_TRAP_SCORE_WATCH', 2.5, 0.1, 20.0)

    tf_rows = [r for r in dbg_rows if is_time_finished_reason(r.get('death', ''))]
    info['timefinished_rows'] = len(tf_rows)
    info['timefinished_pct'] = sdiv(len(tf_rows) * 100.0, len(dbg_rows))
    if not tf_rows:
        return info

    tf_by_gen = Counter(int(r.get('gen', 0)) for r in tf_rows)
    tf_by_spawn = Counter(str(r.get('spawn', '')) for r in tf_rows if str(r.get('spawn', '')))

    enriched = []
    for r in tf_rows:
        t_tot = max(float(r.get('t_tot', 0.0)), 1.0)
        stop_ticks = float(r.get('t_stop_ctx', 0.0))
        stop_ratio = sdiv(float(r.get('t_stop_ctx', 0.0)), t_tot)
        fit = float(r.get('fit', 0.0))
        t_alive = max(float(r.get('time', 0.0)), 0.0)
        fit_per_sec = sdiv(fit, max(t_alive, 1.0))
        stop_b = float(r.get('stop_brake', 0.0))
        stop_t = float(r.get('stop_throttle', 0.0))
        stop_brake_share = sdiv(stop_b, stop_b + stop_t)
        stop_ctx_yield_share = sdiv(float(r.get('t_stop_ctx_yield', 0.0)), max(stop_ticks, 1.0))
        stop_ctx_yield_ratio_total = sdiv(float(r.get('t_stop_ctx_yield', 0.0)), t_tot)
        stop_ctx_stop_share = sdiv(float(r.get('t_stop_ctx_stop', 0.0)), max(stop_ticks, 1.0))
        stop_ctx_tl_share = sdiv(float(r.get('t_stop_ctx_tl', 0.0)), max(stop_ticks, 1.0))
        enriched.append({
            'gen': int(r.get('gen', 0)),
            'car': str(r.get('car', '')),
            'spawn': str(r.get('spawn', '')),
            'fit': fit,
            'time': t_alive,
            'fit_per_sec': fit_per_sec,
            'stop_ctx_ticks': stop_ticks,
            'stop_ctx_ratio': stop_ratio,
            'stop_ctx_pct': stop_ratio * 100.0,
            'stop_ctx_tl_ticks': float(r.get('t_stop_ctx_tl', 0.0)),
            'stop_ctx_stop_ticks': float(r.get('t_stop_ctx_stop', 0.0)),
            'stop_ctx_yield_ticks': float(r.get('t_stop_ctx_yield', 0.0)),
            'stop_ctx_tl_ratio': float(r.get('stop_ctx_tl_ratio', 0.0)),
            'stop_ctx_stop_ratio': float(r.get('stop_ctx_stop_ratio', 0.0)),
            'stop_ctx_yield_ratio': float(r.get('stop_ctx_yield_ratio', 0.0)),
            'stop_ctx_yield_share': stop_ctx_yield_share,
            'stop_ctx_yield_ratio_total': stop_ctx_yield_ratio_total,
            'stop_ctx_stop_share': stop_ctx_stop_share,
            'stop_ctx_tl_share': stop_ctx_tl_share,
            'stop_brake_share': stop_brake_share,
            'pen_creep': float(r.get('pen_creep', 0.0)),
            'pen_lazy': float(r.get('pen_lazy', 0.0)),
            'pen_swstop': float(r.get('pen_swstop', 0.0)),
            'yield_val_t': float(r.get('yield_val_t', 0.0)),
            'stop_val_t': float(r.get('stop_val_t', 0.0)),
            'thr_grace': float(r.get('thr_grace', 0.0)),
            'brake_grace': float(r.get('brake_grace', 0.0)),
            'steer_abs_avg': float(r.get('steer_abs_avg', 0.0)),
            'steer_gap_avg_abs': float(r.get('steer_gap_avg_abs', 0.0)),
        })

    fits = [x['fit'] for x in enriched]
    fitps = [x['fit_per_sec'] for x in enriched]
    stop_ratios = [x['stop_ctx_ratio'] for x in enriched]
    stop_ticks_vals = [x['stop_ctx_ticks'] for x in enriched]
    stop_ctx_yield_vals = [x['stop_ctx_yield_ticks'] for x in enriched]
    stop_ctx_stop_vals = [x['stop_ctx_stop_ticks'] for x in enriched]
    stop_ctx_tl_vals = [x['stop_ctx_tl_ticks'] for x in enriched]
    times = [x['time'] for x in enriched]
    creeps = [x['pen_creep'] for x in enriched]
    yield_vals = [x.get('yield_val_t', 0.0) for x in enriched]
    stop_vals = [x.get('stop_val_t', 0.0) for x in enriched]
    grace_brakes = [x.get('brake_grace', 0.0) for x in enriched]
    steer_gaps = [x.get('steer_gap_avg_abs', 0.0) for x in enriched]

    # Baseline thresholds from configured percentiles
    fit_thr = pctl(fits, fit_pctl)
    fitps_thr = pctl(fitps, fitps_pctl)
    stop_thr = max(min_stop_ratio, pctl(stop_ratios, stop_pctl))
    stop_ticks_thr = max(min_stop_ticks_abs, pctl(stop_ticks_vals, stop_ticks_pctl))
    stop_ctx_yield_thr = pctl(stop_ctx_yield_vals, 75)
    stop_ctx_stop_thr = pctl(stop_ctx_stop_vals, 75)
    stop_ctx_tl_thr = pctl(stop_ctx_tl_vals, 75)
    time_thr = max(min_time_sec, pctl(times, time_pctl))
    creep_thr = pctl(creeps, creep_pctl)
    yield_val_thr = pctl(yield_vals, 70)
    stop_val_thr = pctl(stop_vals, 70)
    grace_brake_thr = pctl(grace_brakes, 70)
    steer_gap_thr = pctl(steer_gaps, 70)

    # Con pocas muestras TIME_FINISHED, usar criterios algo mas robustos.
    if len(enriched) < small_n:
        fit_thr = pctl(fits, 60)
        fitps_thr = pctl(fitps, 60)
        stop_thr = max(min_stop_ratio_small, pctl(stop_ratios, 70))
        stop_ticks_thr = max(min_stop_ticks_abs, pctl(stop_ticks_vals, 70))
        stop_ctx_yield_thr = pctl(stop_ctx_yield_vals, 70)
        stop_ctx_stop_thr = pctl(stop_ctx_stop_vals, 70)
        stop_ctx_tl_thr = pctl(stop_ctx_tl_vals, 70)
        time_thr = max(min_time_sec, pctl(times, 60))
        creep_thr = pctl(creeps, 75)
        yield_val_thr = pctl(yield_vals, 70)
        stop_val_thr = pctl(stop_vals, 70)
        grace_brake_thr = pctl(grace_brakes, 70)
        steer_gap_thr = pctl(steer_gaps, 70)

    candidates = []
    watchlist = []

    # --- Dynamic adjustment: blend percentile-based thresholds with median+IQR
    # to adapt to data spread and avoid hard-fixed heuristics.
    def blend_high(baseline, vals):
        # for thresholds where higher is more significant (e.g., stop ratio)
        if not vals:
            return baseline
        med = pctl(vals, 50)
        iqr = pctl(vals, 75) - pctl(vals, 25)
        adaptive = med + 0.5 * iqr
        return max(baseline, 0.6 * baseline + 0.4 * adaptive)

    def blend_low(baseline, vals):
        # for thresholds where lower is more significant (e.g., fit)
        if not vals:
            return baseline
        med = pctl(vals, 50)
        iqr = pctl(vals, 75) - pctl(vals, 25)
        adaptive = med - 0.5 * iqr
        return min(baseline, 0.6 * baseline + 0.4 * adaptive)

    # Apply blending
    fit_thr = blend_low(fit_thr, fits)
    fitps_thr = blend_low(fitps_thr, fitps)
    stop_thr = blend_high(stop_thr, stop_ratios)
    stop_ticks_thr = blend_high(stop_ticks_thr, stop_ticks_vals)
    stop_ctx_yield_thr = blend_high(stop_ctx_yield_thr, stop_ctx_yield_vals)
    stop_ctx_stop_thr = blend_high(stop_ctx_stop_thr, stop_ctx_stop_vals)
    stop_ctx_tl_thr = blend_high(stop_ctx_tl_thr, stop_ctx_tl_vals)
    time_thr = blend_high(time_thr, times)
    creep_thr = blend_high(creep_thr, creeps)
    for x in enriched:
        low_fit = x['fit'] <= fit_thr
        low_fitps = x['fit_per_sec'] <= fitps_thr
        high_stop = x['stop_ctx_ratio'] >= stop_thr
        high_stop_ticks = x['stop_ctx_ticks'] >= stop_ticks_thr
        high_stop_ctx_yield = x['stop_ctx_yield_ticks'] >= stop_ctx_yield_thr
        high_stop_ctx_stop = x['stop_ctx_stop_ticks'] >= stop_ctx_stop_thr
        high_stop_ctx_tl = x['stop_ctx_tl_ticks'] >= stop_ctx_tl_thr
        yield_ctx_dominant = x['stop_ctx_yield_share'] >= min_yield_ctx_share
        yield_ctx_watch = x['stop_ctx_yield_share'] >= min_yield_ctx_share_watch
        yield_ctx_clear = x['stop_ctx_yield_share'] >= max(x['stop_ctx_stop_share'], x['stop_ctx_tl_share'])
        long_time = x['time'] >= time_thr
        high_creep = x['pen_creep'] >= creep_thr and creep_thr > 0.0
        high_yield_validation = x.get('yield_val_t', 0.0) >= yield_val_thr and yield_val_thr > 0.0
        high_stop_validation = x.get('stop_val_t', 0.0) >= stop_val_thr and stop_val_thr > 0.0
        high_grace_brake = x.get('brake_grace', 0.0) >= grace_brake_thr and grace_brake_thr > 0.0
        high_steer_gap = x.get('steer_gap_avg_abs', 0.0) >= steer_gap_thr and steer_gap_thr > 0.0

        score = 0.0
        if low_fit:
            score += 1.1
        if low_fitps:
            score += 1.0
        if high_stop:
            score += 1.4
        if high_stop_ticks:
            score += 0.8
        if high_stop_ctx_yield:
            score += 0.8
        if high_stop_ctx_stop:
            score += 0.2
        if high_stop_ctx_tl:
            score += 0.1
        if yield_ctx_dominant:
            score += 0.9
        elif yield_ctx_clear:
            score += 0.4
        if long_time:
            score += 0.4
        if high_creep:
            score += 0.5
        if high_stop and x['stop_brake_share'] >= 0.60:
            score += 0.2
        if x.get('pen_swstop', 0.0) > 0.0:
            score += 0.2
        if high_yield_validation:
            score += 0.6
        if high_stop_validation:
            score += 0.4
        if high_grace_brake:
            score += 0.5
        if high_steer_gap:
            score += 0.4

        y = dict(x)
        y['score'] = score
        y['severity'] = 'alta' if score >= (score_candidate_thr + 0.7) else 'media'

        # Requerer evidencia minima de validacion para evitar falsos positivos
        has_validation = x.get('yield_val_t', 0.0) >= min_validation_sec or x.get('stop_val_t', 0.0) >= min_validation_sec
        stop_ctx_ok = (x['stop_ctx_ratio'] >= min_stop_ratio_total) or (x['stop_ctx_ticks'] >= min_stop_ticks_abs)
        yield_ctx_ok = (
            x.get('stop_ctx_yield_ratio_total', 0.0) >= min_yield_ratio_total
            and x.get('stop_ctx_yield_ticks', 0.0) >= min_yield_ticks_abs
        )
        context_ok = stop_ctx_ok and yield_ctx_ok

        # Candidatos: criterios estrictos + validación de parada y sesgo claro a contexto YIELD,
        # O score extremadamente alto si además el contexto de yield domina.
        is_candidate = context_ok and (
            (
                high_stop
                and (low_fit or low_fitps)
                and (long_time or high_stop_ticks)
                and has_validation
                and (yield_ctx_dominant or (yield_ctx_clear and high_yield_validation))
            ) or (
                score >= score_candidate_thr + 1.0
                and (high_stop_ticks or long_time)
                and (yield_ctx_dominant or yield_ctx_clear)
                and has_validation
            )
        )
        
        # Watchlist: menos restrictivo, pero el contexto YIELD debe ser visible.
        is_watch = context_ok and (
            (
                high_stop
                and (low_fit or low_fitps)
                and has_validation
                and (yield_ctx_watch or yield_ctx_clear)
            ) or (
                score >= score_watch_thr
                and (yield_ctx_watch or yield_ctx_clear)
                and (high_stop_ticks or long_time)
                and has_validation
            )
        )

        if is_watch:
            watchlist.append(y)
        if is_candidate:
            candidates.append(y)

    candidates.sort(key=lambda t: (t['score'], -t['stop_ctx_ratio'], -t['time'], -t['fit']), reverse=True)
    watchlist.sort(key=lambda t: (t['score'], -t['stop_ctx_ratio'], -t['time'], -t['fit']), reverse=True)

    by_spawn = defaultdict(list)
    by_gen = defaultdict(list)
    watch_by_spawn = Counter(c['spawn'] for c in watchlist if c.get('spawn'))
    watch_by_gen = Counter(int(c['gen']) for c in watchlist)
    cand_by_spawn = Counter(c['spawn'] for c in candidates if c.get('spawn'))
    cand_by_gen = Counter(int(c['gen']) for c in candidates)
    for c in candidates:
        by_spawn[c['spawn']].append(c)
        by_gen[c['gen']].append(c)

    spawn_rows = []
    all_spawns = sorted(set(tf_by_spawn.keys()) | set(cand_by_spawn.keys()) | set(watch_by_spawn.keys()))
    for sp in all_spawns:
        rows = by_spawn.get(sp, [])
        spawn_rows.append({
            'spawn': sp,
            'tf_n': int(tf_by_spawn.get(sp, 0)),
            'n': int(cand_by_spawn.get(sp, 0)),
            'watch_n': int(watch_by_spawn.get(sp, 0)),
            'cand_pct_tf': sdiv(cand_by_spawn.get(sp, 0) * 100.0, tf_by_spawn.get(sp, 0)),
            'fit_med': pctl([r['fit'] for r in rows], 50) if rows else 0.0,
            'stop_ctx_p50': pctl([r['stop_ctx_pct'] for r in rows], 50) if rows else 0.0,
            'time_p50': pctl([r['time'] for r in rows], 50) if rows else 0.0,
            'score_med': pctl([r['score'] for r in rows], 50) if rows else 0.0,
        })
    spawn_rows = [r for r in spawn_rows if r.get('n', 0) > 0 or r.get('watch_n', 0) > 0]
    spawn_rows.sort(key=lambda x: (x['n'], x['watch_n'], x['cand_pct_tf'], x['score_med']), reverse=True)

    gen_rows = []
    all_gens = sorted(set(tf_by_gen.keys()) | set(cand_by_gen.keys()) | set(watch_by_gen.keys()))
    for g in all_gens:
        rows = by_gen.get(g, [])
        gen_rows.append({
            'gen': g,
            'tf_n': int(tf_by_gen.get(g, 0)),
            'n': int(cand_by_gen.get(g, 0)),
            'watch_n': int(watch_by_gen.get(g, 0)),
            'cand_pct_tf': sdiv(cand_by_gen.get(g, 0) * 100.0, tf_by_gen.get(g, 0)),
            'score_med': pctl([r['score'] for r in rows], 50) if rows else 0.0,
        })
    gen_rows = [r for r in gen_rows if r.get('n', 0) > 0 or r.get('watch_n', 0) > 0]
    gen_rows.sort(key=lambda x: (x['n'], x['watch_n'], x['cand_pct_tf'], x['score_med']), reverse=True)

    info.update({
        'fit_thr': fit_thr,
        'fitps_thr': fitps_thr,
        'stop_ctx_thr': stop_thr,
        'stop_ticks_thr': stop_ticks_thr,
        'stop_ctx_yield_thr': stop_ctx_yield_thr,
        'stop_ctx_stop_thr': stop_ctx_stop_thr,
        'stop_ctx_tl_thr': stop_ctx_tl_thr,
        'min_yield_ctx_share': min_yield_ctx_share,
        'min_yield_ctx_share_watch': min_yield_ctx_share_watch,
        'min_stop_ratio_total': min_stop_ratio_total,
        'min_stop_ticks_abs': min_stop_ticks_abs,
        'min_yield_ratio_total': min_yield_ratio_total,
        'min_yield_ticks_abs': min_yield_ticks_abs,
        'min_validation_sec': min_validation_sec,
        'time_thr': time_thr,
        'creep_thr': creep_thr,
        'score_candidate_thr': score_candidate_thr,
        'score_watch_thr': score_watch_thr,
        'yield_val_thr': yield_val_thr,
        'stop_val_thr': stop_val_thr,
        'grace_brake_thr': grace_brake_thr,
        'steer_gap_thr': steer_gap_thr,
        'candidate_count': len(candidates),
        'candidate_pct_timefinished': sdiv(len(candidates) * 100.0, len(enriched)),
        'watch_count': len(watchlist),
        'watch_pct_timefinished': sdiv(len(watchlist) * 100.0, len(enriched)),
        'candidates': candidates,
        'watchlist': watchlist,
        'spawns': spawn_rows,
        'gens': gen_rows,
        'tf_by_gen': [{'gen': g, 'n': int(tf_by_gen[g])} for g in sorted(tf_by_gen.keys())],
        'candidate_by_gen': [{'gen': g, 'n': int(cand_by_gen[g])} for g in sorted(cand_by_gen.keys())],
        'watch_by_gen': [{'gen': g, 'n': int(watch_by_gen[g])} for g in sorted(watch_by_gen.keys())],
        'tf_by_spawn': [{'spawn': s, 'n': int(tf_by_spawn[s])} for s in sorted(tf_by_spawn.keys())],
        'candidate_by_spawn': [{'spawn': s, 'n': int(cand_by_spawn[s])} for s in sorted(cand_by_spawn.keys())],
        'watch_by_spawn': [{'spawn': s, 'n': int(watch_by_spawn[s])} for s in sorted(watch_by_spawn.keys())],
    })
    return info

def detect_stop_stuck_candidates(dbg_rows):
    info = {
        'total_rows': len(dbg_rows),
        'timefinished_rows': 0,
        'timefinished_pct': 0.0,
        'candidate_count': 0,
        'candidate_pct_timefinished': 0.0,
        'watch_count': 0,
        'watch_pct_timefinished': 0.0,
        'fit_thr': 0.0,
        'fitps_thr': 0.0,
        'stop_ctx_thr': 0.0,
        'stop_ticks_thr': 0.0,
        'stop_ctx_stop_thr': 0.0,
        'stop_ctx_stop_ratio_thr': 0.0,
        'time_thr': 0.0,
        'creep_thr': 0.0,
        'score_candidate_thr': 0.0,
        'score_watch_thr': 0.0,
        'candidates': [],
        'watchlist': [],
        'spawns': [],
        'gens': [],
        'tf_by_gen': [],
        'candidate_by_gen': [],
        'watch_by_gen': [],
        'tf_by_spawn': [],
        'candidate_by_spawn': [],
        'watch_by_spawn': [],
    }
    if not dbg_rows:
        return info

    def envf(name, default, lo=None, hi=None):
        try:
            v = float(os.environ.get(name, default))
        except (TypeError, ValueError):
            v = float(default)
        if lo is not None:
            v = max(float(lo), v)
        if hi is not None:
            v = min(float(hi), v)
        return v

    def envi(name, default, lo=None, hi=None):
        try:
            v = int(float(os.environ.get(name, default)))
        except (TypeError, ValueError):
            v = int(default)
        if lo is not None:
            v = max(int(lo), v)
        if hi is not None:
            v = min(int(hi), v)
        return v

    fit_pctl = envf('ANALYSE_STOP_TRAP_FIT_PCTL', 50.0, 5.0, 95.0)
    fitps_pctl = envf('ANALYSE_STOP_TRAP_FITPS_PCTL', 50.0, 5.0, 95.0)
    stop_pctl = envf('ANALYSE_STOP_TRAP_STOP_CTX_PCTL', 75.0, 5.0, 95.0)
    stop_ticks_pctl = envf('ANALYSE_STOP_TRAP_STOP_TICKS_PCTL', 75.0, 5.0, 95.0)
    stop_only_pctl = envf('ANALYSE_STOP_TRAP_STOP_ONLY_PCTL', 75.0, 5.0, 95.0)
    stop_only_ticks_pctl = envf('ANALYSE_STOP_TRAP_STOP_ONLY_TICKS_PCTL', 75.0, 5.0, 95.0)
    time_pctl = envf('ANALYSE_STOP_TRAP_TIME_PCTL', 65.0, 5.0, 95.0)
    creep_pctl = envf('ANALYSE_STOP_TRAP_CREEP_PCTL', 80.0, 5.0, 95.0)
    lazy_pctl = envf('ANALYSE_STOP_TRAP_LAZY_PCTL', 80.0, 5.0, 95.0)

    min_stop_ratio = envf('ANALYSE_STOP_TRAP_MIN_STOP_CTX_RATIO', 0.25, 0.0, 1.0)
    min_stop_ratio_small = envf('ANALYSE_STOP_TRAP_MIN_STOP_CTX_RATIO_SMALL', 0.20, 0.0, 1.0)
    min_time_sec = envf('ANALYSE_STOP_TRAP_MIN_TIME_SEC', 0.0, 0.0, None)
    min_stop_ticks_abs = envf('ANALYSE_STOP_TRAP_MIN_STOP_TICKS', 10.0, 0.0, None)
    min_stop_ctx_share = envf('ANALYSE_STOP_TRAP_MIN_STOP_CTX_SHARE', 0.45, 0.0, 1.0)
    min_stop_ctx_share_watch = envf('ANALYSE_STOP_TRAP_MIN_STOP_CTX_SHARE_WATCH', 0.30, 0.0, 1.0)
    min_stop_ctx_ratio_total = envf('ANALYSE_STOP_TRAP_MIN_STOP_CTX_RATIO_TOTAL', 0.05, 0.0, 1.0)
    min_stop_ctx_ticks_abs = envf('ANALYSE_STOP_TRAP_MIN_STOP_CTX_TICKS_ABS', 5.0, 0.0, None)
    min_stop_ratio_total = envf('ANALYSE_STOP_TRAP_MIN_STOP_RATIO_TOTAL', 0.02, 0.0, 1.0)
    min_stop_ticks_abs_only = envf('ANALYSE_STOP_TRAP_MIN_STOP_TICKS_ABS', 5.0, 0.0, None)
    min_validation_sec = envf('ANALYSE_STOP_TRAP_MIN_VALIDATION_SEC', 0.5, 0.0, None)
    min_resume_ratio = envf('ANALYSE_STOP_TRAP_MIN_RESUME_RATIO', 0.12, 0.0, 1.0)
    min_resume_cmd_ratio = envf('ANALYSE_STOP_TRAP_MIN_RESUME_CMD_RATIO', 0.08, 0.0, 1.0)

    small_n = envi('ANALYSE_STOP_TRAP_SMALL_SAMPLE_N', 6, 1, 9999)
    score_candidate_thr = envf('ANALYSE_STOP_TRAP_SCORE_CANDIDATE', 3.0, 0.1, 20.0)
    score_watch_thr = envf('ANALYSE_STOP_TRAP_SCORE_WATCH', 2.3, 0.1, 20.0)

    tf_rows = [r for r in dbg_rows if is_time_finished_reason(r.get('death', ''))]
    info['timefinished_rows'] = len(tf_rows)
    info['timefinished_pct'] = sdiv(len(tf_rows) * 100.0, len(dbg_rows))
    if not tf_rows:
        return info

    tf_by_gen = Counter(int(r.get('gen', 0)) for r in tf_rows)
    tf_by_spawn = Counter(str(r.get('spawn', '')) for r in tf_rows if str(r.get('spawn', '')))

    enriched = []
    for r in tf_rows:
        t_tot = max(float(r.get('t_tot', 0.0)), 1.0)
        stop_ticks = float(r.get('t_stop_ctx', 0.0))
        stop_ratio = sdiv(float(r.get('t_stop_ctx', 0.0)), t_tot)
        fit = float(r.get('fit', 0.0))
        t_alive = max(float(r.get('time', 0.0)), 0.0)
        fit_per_sec = sdiv(fit, max(t_alive, 1.0))
        stop_b = float(r.get('stop_brake', 0.0))
        stop_t = float(r.get('stop_throttle', 0.0))
        stop_brake_share = sdiv(stop_b, stop_b + stop_t)
        thr_pos = float(r.get('thr_pos', 0.0))
        brake_in = float(r.get('brake_in', 0.0))
        thr_grace = float(r.get('thr_grace', 0.0))
        brake_grace = float(r.get('brake_grace', 0.0))
        cmd_total = thr_pos + brake_in
        stop_cmd_total = stop_b + stop_t
        grace_cmd_total = thr_grace + brake_grace
        out_cmd_total = max(cmd_total - stop_cmd_total - grace_cmd_total, 0.0)
        out_cmd_ratio = sdiv(out_cmd_total, max(cmd_total, 1.0))
        t_out_ctx = max(t_tot - stop_ticks, 0.0)
        out_ctx_ratio = sdiv(t_out_ctx, t_tot)
        grace_brake_share = sdiv(brake_grace, max(grace_cmd_total, 1.0))
        stop_ctx_stop_ticks = float(r.get('t_stop_ctx_stop', 0.0))
        stop_ctx_stop_share = sdiv(stop_ctx_stop_ticks, max(stop_ticks, 1.0))
        stop_ctx_stop_ratio_total = sdiv(stop_ctx_stop_ticks, t_tot)
        stop_ctx_yield_share = sdiv(float(r.get('t_stop_ctx_yield', 0.0)), max(stop_ticks, 1.0))
        stop_ctx_tl_share = sdiv(float(r.get('t_stop_ctx_tl', 0.0)), max(stop_ticks, 1.0))
        enriched.append({
            'gen': int(r.get('gen', 0)),
            'car': str(r.get('car', '')),
            'spawn': str(r.get('spawn', '')),
            'fit': fit,
            'time': t_alive,
            'fit_per_sec': fit_per_sec,
            'stop_ctx_ticks': stop_ticks,
            'stop_ctx_ratio': stop_ratio,
            'stop_ctx_pct': stop_ratio * 100.0,
            't_out_ctx': t_out_ctx,
            'out_ctx_ratio': out_ctx_ratio,
            'cmd_total': cmd_total,
            'out_cmd_total': out_cmd_total,
            'out_cmd_ratio': out_cmd_ratio,
            'grace_brake_share': grace_brake_share,
            'stop_ctx_tl_ticks': float(r.get('t_stop_ctx_tl', 0.0)),
            'stop_ctx_stop_ticks': stop_ctx_stop_ticks,
            'stop_ctx_yield_ticks': float(r.get('t_stop_ctx_yield', 0.0)),
            'stop_ctx_tl_ratio': float(r.get('stop_ctx_tl_ratio', 0.0)),
            'stop_ctx_stop_ratio': float(r.get('stop_ctx_stop_ratio', 0.0)),
            'stop_ctx_yield_ratio': float(r.get('stop_ctx_yield_ratio', 0.0)),
            'stop_ctx_stop_share': stop_ctx_stop_share,
            'stop_ctx_stop_ratio_total': stop_ctx_stop_ratio_total,
            'stop_ctx_yield_share': stop_ctx_yield_share,
            'stop_ctx_tl_share': stop_ctx_tl_share,
            'stop_brake_share': stop_brake_share,
            'pen_creep': float(r.get('pen_creep', 0.0)),
            'pen_lazy': float(r.get('pen_lazy', 0.0)),
            'pen_swstop': float(r.get('pen_swstop', 0.0)),
            'yield_val_t': float(r.get('yield_val_t', 0.0)),
            'stop_val_t': float(r.get('stop_val_t', 0.0)),
            'thr_grace': thr_grace,
            'brake_grace': brake_grace,
            'steer_abs_avg': float(r.get('steer_abs_avg', 0.0)),
            'steer_gap_avg_abs': float(r.get('steer_gap_avg_abs', 0.0)),
        })

    fits = [x['fit'] for x in enriched]
    fitps = [x['fit_per_sec'] for x in enriched]
    stop_ratios = [x['stop_ctx_ratio'] for x in enriched]
    stop_ticks_vals = [x['stop_ctx_ticks'] for x in enriched]
    stop_ctx_stop_vals = [x['stop_ctx_stop_ticks'] for x in enriched]
    stop_ctx_stop_ratio_vals = [x['stop_ctx_stop_ratio_total'] for x in enriched]
    times = [x['time'] for x in enriched]
    creeps = [x['pen_creep'] for x in enriched]
    lazy_vals = [x.get('pen_lazy', 0.0) for x in enriched]
    out_ctx_ratios = [x.get('out_ctx_ratio', 0.0) for x in enriched]
    out_cmd_ratios = [x.get('out_cmd_ratio', 0.0) for x in enriched]
    stop_vals = [x.get('stop_val_t', 0.0) for x in enriched]
    grace_brakes = [x.get('brake_grace', 0.0) for x in enriched]
    steer_gaps = [x.get('steer_gap_avg_abs', 0.0) for x in enriched]

    # Baseline thresholds from configured percentiles
    fit_thr = pctl(fits, fit_pctl)
    fitps_thr = pctl(fitps, fitps_pctl)
    stop_thr = max(min_stop_ratio, pctl(stop_ratios, stop_pctl))
    stop_ticks_thr = max(min_stop_ticks_abs, pctl(stop_ticks_vals, stop_ticks_pctl))
    stop_ctx_stop_thr = pctl(stop_ctx_stop_vals, stop_only_ticks_pctl)
    stop_ctx_stop_ratio_thr = max(min_stop_ratio_total, pctl(stop_ctx_stop_ratio_vals, stop_only_pctl))
    time_thr = max(min_time_sec, pctl(times, time_pctl))
    creep_thr = pctl(creeps, creep_pctl)
    lazy_thr = pctl(lazy_vals, lazy_pctl)
    stop_val_thr = pctl(stop_vals, 70)
    grace_brake_thr = pctl(grace_brakes, 70)
    steer_gap_thr = pctl(steer_gaps, 70)

    # Con pocas muestras TIME_FINISHED, usar criterios algo mas robustos.
    if len(enriched) < small_n:
        fit_thr = pctl(fits, 60)
        fitps_thr = pctl(fitps, 60)
        stop_thr = max(min_stop_ratio_small, pctl(stop_ratios, 70))
        stop_ticks_thr = max(min_stop_ticks_abs, pctl(stop_ticks_vals, 70))
        stop_ctx_stop_thr = pctl(stop_ctx_stop_vals, 70)
        stop_ctx_stop_ratio_thr = max(min_stop_ratio_total, pctl(stop_ctx_stop_ratio_vals, 70))
        time_thr = max(min_time_sec, pctl(times, 60))
        creep_thr = pctl(creeps, 75)
        lazy_thr = pctl(lazy_vals, 75)
        stop_val_thr = pctl(stop_vals, 70)
        grace_brake_thr = pctl(grace_brakes, 70)
        steer_gap_thr = pctl(steer_gaps, 70)

    candidates = []
    watchlist = []

    # --- Dynamic adjustment: blend percentile-based thresholds with median+IQR
    # to adapt to data spread and avoid hard-fixed heuristics.
    def blend_high(baseline, vals):
        if not vals:
            return baseline
        med = pctl(vals, 50)
        iqr = pctl(vals, 75) - pctl(vals, 25)
        adaptive = med + 0.5 * iqr
        return max(baseline, 0.6 * baseline + 0.4 * adaptive)

    def blend_low(baseline, vals):
        if not vals:
            return baseline
        med = pctl(vals, 50)
        iqr = pctl(vals, 75) - pctl(vals, 25)
        adaptive = med - 0.5 * iqr
        return min(baseline, 0.6 * baseline + 0.4 * adaptive)

    # Apply blending
    fit_thr = blend_low(fit_thr, fits)
    fitps_thr = blend_low(fitps_thr, fitps)
    stop_thr = blend_high(stop_thr, stop_ratios)
    stop_ticks_thr = blend_high(stop_ticks_thr, stop_ticks_vals)
    stop_ctx_stop_thr = blend_high(stop_ctx_stop_thr, stop_ctx_stop_vals)
    stop_ctx_stop_ratio_thr = blend_high(stop_ctx_stop_ratio_thr, stop_ctx_stop_ratio_vals)
    time_thr = blend_high(time_thr, times)
    creep_thr = blend_high(creep_thr, creeps)
    lazy_thr = blend_high(lazy_thr, lazy_vals)

    for x in enriched:
        low_fit = x['fit'] <= fit_thr
        low_fitps = x['fit_per_sec'] <= fitps_thr
        high_stop = x['stop_ctx_ratio'] >= stop_thr
        high_stop_ticks = x['stop_ctx_ticks'] >= stop_ticks_thr
        high_stop_ctx_stop = x['stop_ctx_stop_ticks'] >= stop_ctx_stop_thr
        high_stop_ctx_stop_ratio = x['stop_ctx_stop_ratio_total'] >= stop_ctx_stop_ratio_thr
        stop_ctx_dominant = x['stop_ctx_stop_share'] >= min_stop_ctx_share
        stop_ctx_watch = x['stop_ctx_stop_share'] >= min_stop_ctx_share_watch
        stop_ctx_clear = x['stop_ctx_stop_share'] >= max(x['stop_ctx_yield_share'], x['stop_ctx_tl_share'])
        long_time = x['time'] >= time_thr
        high_creep = x['pen_creep'] >= creep_thr and creep_thr > 0.0
        high_lazy = x.get('pen_lazy', 0.0) >= lazy_thr and lazy_thr > 0.0
        resume_ok = (x.get('out_ctx_ratio', 0.0) >= min_resume_ratio) or (x.get('out_cmd_ratio', 0.0) >= min_resume_cmd_ratio)
        high_stop_validation = x.get('stop_val_t', 0.0) >= stop_val_thr and stop_val_thr > 0.0
        high_grace_brake = x.get('brake_grace', 0.0) >= grace_brake_thr and grace_brake_thr > 0.0
        high_steer_gap = x.get('steer_gap_avg_abs', 0.0) >= steer_gap_thr and steer_gap_thr > 0.0

        score = 0.0
        if low_fit:
            score += 1.1
        if low_fitps:
            score += 1.0
        if high_stop:
            score += 1.4
        if high_stop_ticks:
            score += 0.8
        if high_stop_ctx_stop:
            score += 0.8
        if high_stop_ctx_stop_ratio:
            score += 0.6
        if stop_ctx_dominant:
            score += 0.9
        elif stop_ctx_clear:
            score += 0.4
        if long_time:
            score += 0.4
        if high_creep:
            score += 0.4
        if high_lazy:
            score += 0.3
        if not resume_ok:
            score += 0.4
        if high_stop and x['stop_brake_share'] >= 0.60:
            score += 0.2
        if x.get('pen_swstop', 0.0) > 0.0:
            score += 0.2
        if high_stop_validation:
            score += 0.7
        if high_grace_brake:
            score += 0.4
        if high_steer_gap:
            score += 0.3

        y = dict(x)
        y['score'] = score
        y['severity'] = 'alta' if score >= (score_candidate_thr + 0.7) else 'media'

        # Requerer evidencia minima de validacion para evitar falsos positivos
        has_validation = x.get('stop_val_t', 0.0) >= min_validation_sec
        stop_ctx_ok = (x['stop_ctx_ratio'] >= min_stop_ctx_ratio_total) or (x['stop_ctx_ticks'] >= min_stop_ctx_ticks_abs)
        stop_only_ok = (
            x.get('stop_ctx_stop_ratio_total', 0.0) >= min_stop_ratio_total
            and x.get('stop_ctx_stop_ticks', 0.0) >= min_stop_ticks_abs_only
        )
        context_ok = stop_ctx_ok and stop_only_ok

        stop_focus = stop_only_ok and (stop_ctx_dominant or stop_ctx_watch or stop_ctx_clear)
        stop_fail = stop_focus and high_stop_validation and (high_stop or high_stop_ticks or long_time)
        no_validation = stop_focus and (x.get('stop_val_t', 0.0) < min_validation_sec)
        no_resume = stop_focus and (not resume_ok)

        if stop_fail:
            cause_primary = 'STOP_FAIL'
        elif no_resume:
            cause_primary = 'NO_RESUME'
        elif high_lazy and stop_ctx_ok:
            cause_primary = 'LAZY_SUSPECT'
        elif high_creep and stop_ctx_ok:
            cause_primary = 'CREEP'
        elif no_validation:
            cause_primary = 'NO_VALID'
        else:
            cause_primary = 'OTHER'

        y['cause_primary'] = cause_primary

        # Candidatos: criterios estrictos + validacion de parada y sesgo claro a contexto STOP,
        # O score extremadamente alto si ademas el contexto de stop domina.
        is_candidate = context_ok and (
            (
                high_stop
                and (low_fit or low_fitps)
                and (long_time or high_stop_ticks)
                and has_validation
                and (stop_ctx_dominant or (stop_ctx_clear and high_stop_validation))
            ) or (
                score >= score_candidate_thr + 1.0
                and (high_stop_ticks or long_time)
                and (stop_ctx_dominant or stop_ctx_clear)
                and has_validation
            )
        )

        # Watchlist: menos restrictivo, pero el contexto STOP debe ser visible.
        is_watch = context_ok and (
            (
                high_stop
                and (low_fit or low_fitps)
                and has_validation
                and (stop_ctx_watch or stop_ctx_clear)
            ) or (
                score >= score_watch_thr
                and (stop_ctx_watch or stop_ctx_clear)
                and (high_stop_ticks or long_time)
                and has_validation
            )
        )

        if is_watch:
            watchlist.append(y)
        if is_candidate:
            candidates.append(y)

    candidates.sort(key=lambda t: (t['score'], -t['stop_ctx_ratio'], -t['time'], -t['fit']), reverse=True)
    watchlist.sort(key=lambda t: (t['score'], -t['stop_ctx_ratio'], -t['time'], -t['fit']), reverse=True)

    by_spawn = defaultdict(list)
    by_gen = defaultdict(list)
    watch_by_spawn = Counter(c['spawn'] for c in watchlist if c.get('spawn'))
    watch_by_gen = Counter(int(c['gen']) for c in watchlist)
    cand_by_spawn = Counter(c['spawn'] for c in candidates if c.get('spawn'))
    cand_by_gen = Counter(int(c['gen']) for c in candidates)
    for c in candidates:
        by_spawn[c['spawn']].append(c)
        by_gen[c['gen']].append(c)

    spawn_rows = []
    all_spawns = sorted(set(tf_by_spawn.keys()) | set(cand_by_spawn.keys()) | set(watch_by_spawn.keys()))
    for sp in all_spawns:
        rows = by_spawn.get(sp, [])
        spawn_rows.append({
            'spawn': sp,
            'tf_n': int(tf_by_spawn.get(sp, 0)),
            'n': int(cand_by_spawn.get(sp, 0)),
            'watch_n': int(watch_by_spawn.get(sp, 0)),
            'cand_pct_tf': sdiv(cand_by_spawn.get(sp, 0) * 100.0, tf_by_spawn.get(sp, 0)),
            'fit_med': pctl([r['fit'] for r in rows], 50) if rows else 0.0,
            'stop_ctx_p50': pctl([r['stop_ctx_pct'] for r in rows], 50) if rows else 0.0,
            'time_p50': pctl([r['time'] for r in rows], 50) if rows else 0.0,
            'score_med': pctl([r['score'] for r in rows], 50) if rows else 0.0,
        })
    spawn_rows = [r for r in spawn_rows if r.get('n', 0) > 0 or r.get('watch_n', 0) > 0]
    spawn_rows.sort(key=lambda x: (x['n'], x['watch_n'], x['cand_pct_tf'], x['score_med']), reverse=True)

    gen_rows = []
    all_gens = sorted(set(tf_by_gen.keys()) | set(cand_by_gen.keys()) | set(watch_by_gen.keys()))
    for g in all_gens:
        rows = by_gen.get(g, [])
        gen_rows.append({
            'gen': g,
            'tf_n': int(tf_by_gen.get(g, 0)),
            'n': int(cand_by_gen.get(g, 0)),
            'watch_n': int(watch_by_gen.get(g, 0)),
            'cand_pct_tf': sdiv(cand_by_gen.get(g, 0) * 100.0, tf_by_gen.get(g, 0)),
            'score_med': pctl([r['score'] for r in rows], 50) if rows else 0.0,
        })
    gen_rows = [r for r in gen_rows if r.get('n', 0) > 0 or r.get('watch_n', 0) > 0]
    gen_rows.sort(key=lambda x: (x['n'], x['watch_n'], x['cand_pct_tf'], x['score_med']), reverse=True)

    info.update({
        'fit_thr': fit_thr,
        'fitps_thr': fitps_thr,
        'stop_ctx_thr': stop_thr,
        'stop_ticks_thr': stop_ticks_thr,
        'stop_ctx_stop_thr': stop_ctx_stop_thr,
        'stop_ctx_stop_ratio_thr': stop_ctx_stop_ratio_thr,
        'lazy_thr': lazy_thr,
        'min_resume_ratio': min_resume_ratio,
        'min_resume_cmd_ratio': min_resume_cmd_ratio,
        'min_stop_ctx_share': min_stop_ctx_share,
        'min_stop_ctx_share_watch': min_stop_ctx_share_watch,
        'min_stop_ctx_ratio_total': min_stop_ctx_ratio_total,
        'min_stop_ctx_ticks_abs': min_stop_ctx_ticks_abs,
        'min_stop_ratio_total': min_stop_ratio_total,
        'min_stop_ticks_abs': min_stop_ticks_abs_only,
        'min_validation_sec': min_validation_sec,
        'time_thr': time_thr,
        'creep_thr': creep_thr,
        'score_candidate_thr': score_candidate_thr,
        'score_watch_thr': score_watch_thr,
        'stop_val_thr': stop_val_thr,
        'grace_brake_thr': grace_brake_thr,
        'steer_gap_thr': steer_gap_thr,
        'candidate_count': len(candidates),
        'candidate_pct_timefinished': sdiv(len(candidates) * 100.0, len(enriched)),
        'watch_count': len(watchlist),
        'watch_pct_timefinished': sdiv(len(watchlist) * 100.0, len(enriched)),
        'candidates': candidates,
        'watchlist': watchlist,
        'spawns': spawn_rows,
        'gens': gen_rows,
        'cause_counts': dict(Counter(x.get('cause_primary', 'OTHER') for x in enriched)),
        'candidate_cause_counts': dict(Counter(x.get('cause_primary', 'OTHER') for x in candidates)),
        'tf_by_gen': [{'gen': g, 'n': int(tf_by_gen[g])} for g in sorted(tf_by_gen.keys())],
        'candidate_by_gen': [{'gen': g, 'n': int(cand_by_gen[g])} for g in sorted(cand_by_gen.keys())],
        'watch_by_gen': [{'gen': g, 'n': int(watch_by_gen[g])} for g in sorted(watch_by_gen.keys())],
        'tf_by_spawn': [{'spawn': s, 'n': int(tf_by_spawn[s])} for s in sorted(tf_by_spawn.keys())],
        'candidate_by_spawn': [{'spawn': s, 'n': int(cand_by_spawn[s])} for s in sorted(cand_by_spawn.keys())],
        'watch_by_spawn': [{'spawn': s, 'n': int(watch_by_spawn[s])} for s in sorted(watch_by_spawn.keys())],
    })
    return info

def rolling(data, w):
    if not data:
        return []
    w = max(1, int(w))
    out = []
    window_sum = 0.0
    for i, value in enumerate(data):
        window_sum += value
        if i >= w:
            window_sum -= data[i - w]
        out.append(window_sum / min(i + 1, w))
    return out

def pctl(vals, p):
    vals = finite_vals(vals)
    if not vals:
        return 0.0
    try:
        p = float(p)
    except (TypeError, ValueError):
        return 0.0
    if p < 0.0:
        p = 0.0
    elif p > 100.0:
        p = 100.0
    # Preferir numpy para rendimiento y manejo de NaNs
    try:
        arr = np.array(vals, dtype=float)
        return float(np.nanpercentile(arr, p))
    except Exception:
        # Fallback a implementación pura de Python
        s = sorted(vals)
        if not s:
            return 0.0
        k = (len(s) - 1) * p / 100.0
        f = int(k)
        c = min(f + 1, len(s) - 1)
        return s[f] + (s[c] - s[f]) * (k - f)

def cvar(vals, alpha=10):
    """CVaR: media del peor alpha% (cola inferior)."""
    if not vals:
        return 0.0
    cutoff = pctl(vals, alpha)
    tail = [v for v in vals if v <= cutoff]
    return sdiv(sum(tail), len(tail)) if tail else 0.0

def wilson_ci(k, n, z=1.96):
    """Intervalo de confianza Wilson para una proporcion binomial."""
    if n <= 0:
        return (0.0, 0.0)
    phat = k / n
    den = 1.0 + (z*z)/n
    center = (phat + (z*z)/(2*n)) / den
    margin = (z / den) * ((phat*(1-phat)/n + (z*z)/(4*n*n)) ** 0.5)
    lo = max(0.0, center - margin)
    hi = min(1.0, center + margin)
    return (lo, hi)

def binary_metrics_from_row(r):
    """Devuelve metricas binarias derivadas por fila de summary."""
    succ = r.get('success_count', 0)
    fail = r.get('fail_count', 0)
    n_counts = succ + fail
    n_row = r.get('eval_n', 0)
    n = n_counts if n_counts > 0 else n_row
    if n > 0:
        success_rate = sdiv(succ * 100.0, n)
        fail_rate = sdiv(fail * 100.0, n)
        lo, hi = wilson_ci(succ, n)
        return {
            'n': n,
            'n_counts': n_counts,
            'success_rate': success_rate,
            'fail_rate': fail_rate,
            'wilson_lo': lo * 100.0,
            'wilson_hi': hi * 100.0,
        }

    # Fallback cuando no llegan los conteos, pero si porcentajes
    success_rate = r.get('success_rate', 0.0)
    fail_rate = r.get('fail_rate', max(0.0, 100.0 - success_rate))
    return {
        'n': 0,
        'n_counts': 0,
        'success_rate': success_rate,
        'fail_rate': fail_rate,
        'wilson_lo': 0.0,
        'wilson_hi': 0.0,
    }

# ═══════════════════════════════════════════════════════════════════════
# ║ ANÁLISIS AVANZADOS: Convergencia, Predicción y Diversidad
