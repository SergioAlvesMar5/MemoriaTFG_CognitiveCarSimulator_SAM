#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Analisis completo de entrenamiento/testing para cognitive-car.
Genera informe de texto + graficas en una carpeta con fecha.
"""
import os, shutil, csv
import json, math, copy, re
from datetime import datetime
from collections import defaultdict, Counter

import numpy as np
import argparse
import logging
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
try:
    import seaborn as sns  # pyright: ignore[reportMissingModuleSource]
    _HAVE_SEABORN = True
except Exception:
    sns = None
    _HAVE_SEABORN = False

if _HAVE_SEABORN:
    sns.set_theme(style='whitegrid')

# ╔══════════════════════════════════════════════════════════════════════╗
# ║  CONFIGURACION AUTOMATICA                                           ║
# ║  El modo se detecta desde Fitness_Debug.csv (train/test/traintest).║
# ╚══════════════════════════════════════════════════════════════════════╝

MODE = 'auto'

# ═══════════════════════════════════════════════════════════════════════

BASE_DIR     = os.path.dirname(os.path.abspath(__file__))
SAVED_DIR    = os.path.dirname(BASE_DIR)
SAVEGAMES_DIR = os.path.join(SAVED_DIR, 'SaveGames')
TRAIN_SUMMARY_FILE = os.path.join(BASE_DIR, 'Training_Summary.csv')
TEST_SUMMARY_FILE  = os.path.join(BASE_DIR, 'Test_Summary.csv')
SUMMARY_FILE = ''
DEBUG_FILE   = os.path.join(BASE_DIR, 'Fitness_Debug.csv')
LABEL        = 'AUTO'
NOW          = datetime.now().strftime('%Y-%m-%d_%H-%M')
OUT_DIR      = os.path.join(BASE_DIR, 'Analisis', f'auto_{NOW}')
COMPARE_LIMIT = max(1, int(os.environ.get('ANALYSE_COMPARE_SESSIONS', '8')))
TOP_ROWS = max(5, int(os.environ.get('ANALYSE_TOP_ROWS', '15')))
GEN_XLABEL = 'Generacion normalizada (1..N)'
SAVE_DETAILED_JSON = False
SAVE_GENERATION_MAPPING = False
SAVE_GLOBAL_SUMMARY = False
MIN_SPAWN_N = 10
NETWORK_SENSOR_COUNT = max(1, int(os.environ.get('ANALYSE_SENSOR_COUNT', '11')))
NETWORK_HIDDEN_COUNT = max(1, int(os.environ.get('ANALYSE_HIDDEN_COUNT', '16')))
NETWORK_OUTPUT_COUNT = max(1, int(os.environ.get('ANALYSE_OUTPUT_COUNT', '2')))
NETWORK_INPUT_COUNT = NETWORK_SENSOR_COUNT + 2 + 2 + 4 + 1
NETWORK_WEIGHTS_TOTAL = (
    NETWORK_INPUT_COUNT * NETWORK_HIDDEN_COUNT
    + NETWORK_HIDDEN_COUNT * NETWORK_OUTPUT_COUNT
)
WEIGHTS_TOTAL = max(1, int(os.environ.get('ANALYSE_WEIGHTS_TOTAL', str(NETWORK_WEIGHTS_TOTAL))))
TEST_MIN_TIME = float(os.environ.get('ANALYSE_TEST_MIN_TIME', '60'))
TEST_MIN_FITNESS = float(os.environ.get('ANALYSE_TEST_MIN_FITNESS', '25000'))
TEST_USE_FITNESS = str(
    os.environ.get('ANALYSE_TEST_USE_FITNESS', 'false')
).strip().lower() in ('1', 'true', 'yes', 'on')
MUTATION_RATE_EVOLVED = float(os.environ.get('ANALYSE_MUTATION_RATE', '0.03'))
MUTATION_RATE_RANDOM_FAMILY = float(os.environ.get('ANALYSE_RANDOM_MUTATION_RATE', '0.06'))
MUTATION_TOP_SPAWNS = max(5, int(os.environ.get('ANALYSE_MUTATION_TOP_SPAWNS', '15')))
MUTATION_TOP_GENS = max(10, int(os.environ.get('ANALYSE_MUTATION_TOP_GENS', '20')))
CARINDEX_MUT_LOADED_END = max(3, int(os.environ.get('ANALYSE_CARINDEX_MUT_LOADED_END', '20')))
CARINDEX_MUT_SESSION_END = max(
    CARINDEX_MUT_LOADED_END + 1,
    int(os.environ.get('ANALYSE_CARINDEX_MUT_SESSION_END', os.environ.get('ANALYSE_CARINDEX_MUT_BEST_END', '38')))
)

# Control de graficas (permitir deshabilitar desde CLI)
ENABLE_PLOTS = True

SUMMARY_ALIASES = {
    # esquema base
    'generacion': 'gen',
    'mejorfitnessnorm': 'best',
    'fitnessmedio': 'mean',
    'tiempomedio': 'time',
    'razonmuertemejorcoche': 'best_death',
    'razonmuertemaspopular': 'pop_death',
    'muertosporrazonmaspopular': 'pop_count',
    # esquema binario nuevo
    'exitos': 'success_count',
    'exito': 'success_count',
    'aciertos': 'success_count',
    'fracasos': 'fail_count',
    'fracaso': 'fail_count',
    'errores': 'fail_count',
    'fracasoduro': 'fail_hard_count',
    'fracasotemprano': 'fail_early_count',
    'fracasocolision': 'fail_collision_count',
    'successrate': 'success_rate',
    'failrate': 'fail_rate',
    'lengthcarsarray': 'eval_n',
    'totalcars': 'eval_n',
    'n': 'eval_n',
    'hardfailrate': 'hard_fail_rate',
    'score': 'score',
    # esquema anterior (fuerte/debil), mantenido por compatibilidad
    'exitofuerte': 'success_strong_count',
    'exitodebil': 'success_weak_count',
    'successratetotal': 'success_total',
    'successratefuerte': 'success_strong',
}

SUMMARY_REQUIRED_KEYS = ['gen', 'best', 'mean', 'time', 'best_death', 'pop_death', 'pop_count']

DEBUG_ALIASES = {
    'generacion': 'gen',
    'carid': 'car',
    'cocheid': 'car',
    'fitnessfinal': 'fit',
    'tiempovivo': 'time',
    'spawnid': 'spawn',
    'spawnpoint': 'spawn',
    'razonmuerte': 'death',
    'penaltymuerte': 'pen_m',
    'acumpenaltyvelocidad': 'pen_v',
    'acuma': 'a',
    'mediab': 'b',
    'acumc': 'c',
    'acumd': 'd',
    'acume': 'e',
    'acumf': 'f',
    'acumwaitbonus': 'wait_bonus',
    'acumnetnormal': 'net',
    'acumpenaltycorrectingwrong': 'pen_cw',
    'acumpenaltytrafficviolation': 'pen_tv',
    'acumcreepingpenalty': 'pen_creep',
    'acumpenaltycreeping': 'pen_creep',
    'acumreversepenalty': 'pen_rev',
    'acumpenaltyreverse': 'pen_rev',
    'acumlazypenalty': 'pen_lazy',
    'acumpenaltylazy': 'pen_lazy',
    'acumsteeringwhilestopped': 'pen_swstop',
    'acumpenaltysteeringwhilestopped': 'pen_swstop',
    'steeringwhilestopped': 'pen_swstop',
    'acumsteerapproachpenalty': 'pen_steer_app',
    'acumpenaltysteerapproach': 'pen_steer_app',
    'ticksnormal': 't_norm',
    'tickstotal': 't_tot',
    # nuevas metricas de control (07-04-2026+)
    'acumthrottlepos': 'thr_pos',
    'acumthrottlepositive': 'thr_pos',
    'acumthrottleduringgracetime': 'thr_grace',
    'throttleduringgracetime': 'thr_grace',
    'acumbrakeduringgracetime': 'brake_grace',
    'brakeduringgracetime': 'brake_grace',
    'acumbrakeinput': 'brake_in',
    'coasttime': 'coast_t',
    'acumstopbrake': 'stop_brake',
    'acumstopcontextbrake': 'stop_brake',
    'acumstopthrottle': 'stop_throttle',
    'acumstopcontextthrottle': 'stop_throttle',
    'ticksstopcontext': 't_stop_ctx',
    'ticksstopcontexttrafficlight': 't_stop_ctx_tl',
    'ticksstopcontextstop': 't_stop_ctx_stop',
    'ticksstopcontextyield': 't_stop_ctx_yield',
    # mutation metrics (06-05-2026+)
    'mutnumchanged': 'mut_changed',
    'mutavgmagnitude': 'mut_avg_mag',
    'mutavgmag': 'mut_avg_mag',
    'mutnumlarge': 'mut_large',
    'mutparentfitness': 'mut_parent_fit',
    'numstopzonesentered': 'stop_zones_n',
    'debugnumstopzonesentered': 'stop_zones_n',
    'notnormpeakfitness': 'fit_peak_raw',
    'debugnotnormpeakfitness': 'fit_peak_raw',
    'acumstopcompletionbonus': 'stop_bonus',
    'stopcompletionbonus': 'stop_bonus',
    'numstopscompleted': 'stop_done_n',
    'acumyieldcompletionbonus': 'yield_bonus',
    'yieldcompletionbonus': 'yield_bonus',
    'numyieldscompleted': 'yield_done_n',
    'acumnavpenalty': 'pen_nav',
    'navpenalty': 'pen_nav',
    # metricas nuevas 24-04-2026: validacion legal y reanudacion tras parada
    'yieldvalidationtime': 'yield_val_t',
    'yieldvalidation': 'yield_val_t',
    'acumyieldvalidationtime': 'yield_val_t',
    'stopvalidationtime': 'stop_val_t',
    'stopvalidation': 'stop_val_t',
    'acumstopvalidationtime': 'stop_val_t',
    'acumsteeringinput': 'steer_in',
    'steeringinput': 'steer_in',
    'debugacumsteeringinput': 'steer_in',
    'acumtargetsteering': 'steer_target',
    'targetsteering': 'steer_target',
    'debugacumtargetsteering': 'steer_target',
    'carindex': 'car_index',
    'debugcarindex': 'car_index',
    'acumabssteering': 'steer_abs',
    'abssteering': 'steer_abs',
    'debugacumabssteering': 'steer_abs',
    'trainingmode': 'training',
    'training': 'training',
    'istraining': 'training',
    'train': 'training',
}

DEBUG_REQUIRED_KEYS = ['gen', 'car', 'fit', 'time', 'spawn', 'death']

# ── Utilidades ──

def clean(s):
    return s.replace('\ufeff', '').strip()

def normalize_header_token(s):
    norm = (
        clean(s)
        .lower()
        .replace('ó', 'o')
        .replace('á', 'a')
        .replace('é', 'e')
        .replace('í', 'i')
        .replace('ú', 'u')
        .replace('_', '')
        .replace(' ', '')
    )
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
    """Classify mutation telemetry according to the latest EvolutionManager."""
    changed = num(row.get('mut_changed', 0.0), 0.0)
    gen = int(num(row.get('gen', 0), 0.0))
    parent_fit = num(row.get('mut_parent_fit', 0.0), 0.0)
    observed = sdiv(changed, WEIGHTS_TOTAL)

    if is_initial_random_brain(row):
        return {
            'kind': 'INITIAL_RANDOM',
            'is_initialization': True,
            'expected_rate': None,
            'observed_rate': observed,
        }

    family = car_index_family_for_row(row, bounds=bounds)
    if gen == 1:
        kind = 'INITIAL_LOADED'
        expected = 0.0
    elif family in ('LOADED', 'SESSION'):
        kind = family
        expected = 0.0
    elif family in ('MUT_LOADED', 'MUT_SESSION'):
        kind = family
        expected = MUTATION_RATE_EVOLVED
    elif family == 'MUT_LOADED_LARGE':
        kind = 'MUT_LOADED_LARGE'
        expected = MUTATION_RATE_RANDOM_FAMILY
    else:
        kind = family
        expected = None

    return {
        'kind': kind,
        'is_initialization': False,
        'expected_rate': expected,
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

def inspect_csv_layout(path, aliases, required_keys, min_cols=0):
    meta = {
        'path': path,
        'exists': os.path.exists(path),
        'size_bytes': 0,
        'mtime': '',
        'header': [],
        'mapped_keys': [],
        'unknown_headers': [],
        'missing_required': list(required_keys),
        'data_rows': 0,
        'empty_rows': 0,
        'short_rows': 0,
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
    with open(path, encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            p = [clean(x) for x in row]
            if i == 0:
                meta['header'] = p
                norm = [normalize_header_token(x) for x in p]
                unknown = []
                for idx, h in enumerate(norm):
                    key = alias_lookup(h, aliases)
                    if key:
                        header_map[key] = idx
                    else:
                        unknown.append(p[idx])
                meta['mapped_keys'] = sorted(header_map.keys())
                meta['unknown_headers'] = [u for u in unknown if u]
                meta['missing_required'] = [k for k in required_keys if k not in header_map]
                continue

            if not p or not any(p):
                meta['empty_rows'] += 1
                continue
            meta['data_rows'] += 1
            if min_cols and len(p) < min_cols:
                meta['short_rows'] += 1
    
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
            p = [clean(x) for x in row]
            if i == 0:
                norm = [normalize_header_token(x) for x in p]
                for idx, h in enumerate(norm):
                    mapped = alias_lookup(h, DEBUG_ALIASES)
                    if mapped == 'death':
                        death_idx = idx
                    elif mapped == 'training':
                        training_idx = idx
                continue
            if not p or not any(p):
                continue

            if target_training is not None and training_idx is not None and training_idx < len(p):
                row_training = parse_bool_token(p[training_idx])
                if row_training is not None and row_training != target_training:
                    continue

            out['rows'] += 1
            if death_idx is None or death_idx >= len(p):
                continue
            reason = p[death_idx].strip()
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

def normalize_reason(reason):
    return clean(str(reason or '')).upper()

def compact_reason(reason):
    return re.sub(r'[^A-Z0-9]+', '', normalize_reason(reason))

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
    if r in DEATH_FAMILY_ORDER:
        return r
    return (reason or '').replace('COLLISION_WITH_', 'COL_') or 'UNKNOWN'

def is_death_family(reason, family):
    return death_family(reason) == family

def is_lazy_reason(reason):
    return canonical_death_reason(reason) == 'LAZY'

def is_invalid_brain_reason(reason):
    return canonical_death_reason(reason) == 'INVALID_BRAIN'

def is_test_failure_reason(reason):
    # Mirrors BP_EvolutionManager CalculateAndExport death-based fail rules
    # from the latest local description (01-06-2026). Fitness/time thresholds
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
# ═══════════════════════════════════════════════════════════════════════

def select_test_summary_rows(summary_rows):
    """Return only rows that represent test generations."""
    rows = [r for r in summary_rows or [] if 'success_rate' in r]
    phased = [r for r in rows if r.get('source_phase') == 'test']
    return phased if phased else rows

def summarize_test_results(summary_rows):
    """Aggregate binary test KPIs, weighting rates by evaluated cars."""
    rows = select_test_summary_rows(summary_rows)
    if not rows:
        return None

    derived = [binary_metrics_from_row(r) for r in rows]
    total_n = sum(m['n'] for m in derived)
    total_success = sum(int(num(r.get('success_count', 0), 0.0)) for r in rows)
    total_fail = sum(int(num(r.get('fail_count', 0), 0.0)) for r in rows)
    rates = [m['success_rate'] for m in derived]
    weighted_rate = (
        sdiv(total_success * 100.0, total_n)
        if total_n > 0 and (total_success + total_fail) > 0
        else mean(rates)
    )
    lo, hi = wilson_ci(total_success, total_n) if total_n > 0 else (0.0, 0.0)
    best_idx = max(range(len(rows)), key=lambda i: rates[i])
    worst_idx = min(range(len(rows)), key=lambda i: rates[i])

    return {
        'rows': rows,
        'derived': derived,
        'gens': len(rows),
        'total_n': total_n,
        'total_success': total_success,
        'total_fail': total_fail,
        'success_rate': weighted_rate,
        'success_mean': mean(rates),
        'success_median': pctl(rates, 50),
        'success_std': stdev(rates),
        'success_min': min(rates),
        'success_max': max(rates),
        'best_gen': rows[best_idx].get('gen_phase', rows[best_idx].get('gen', 0)),
        'worst_gen': rows[worst_idx].get('gen_phase', rows[worst_idx].get('gen', 0)),
        'wilson_lo': lo * 100.0,
        'wilson_hi': hi * 100.0,
        'fitness_mean': mean([r.get('mean', 0.0) for r in rows]),
        'fitness_best': max(r.get('best', 0.0) for r in rows),
        'time_mean': mean([r.get('time', 0.0) for r in rows]),
    }

def analyze_convergence(summary_rows):
    """Analiza convergencia, plateaus y estabilidad de fitness."""
    if not summary_rows or len(summary_rows) < 3:
        return None
    
    gens = [r['gen'] for r in summary_rows]
    best_vals = [r['best'] for r in summary_rows]
    mean_vals = [r['mean'] for r in summary_rows]
    
    # Mejora máxima y en qué generación
    max_best = max(best_vals)
    gen_max_best = gens[best_vals.index(max_best)]
    
    # Mejora desde inicio
    initial_best = best_vals[0]
    total_improvement = max_best - initial_best
    improvement_pct = sdiv(total_improvement * 100.0, abs(initial_best)) if initial_best != 0 else (100.0 if total_improvement > 0 else 0.0)
    
    # Detectar plateau: últimas N gens sin mejora >threshold
    plateau_threshold = max_best * 0.01  # 1% del mejor
    plateau_gens = 0
    for i in range(len(best_vals)-1, -1, -1):
        if best_vals[i] < max_best - plateau_threshold:
            break
        plateau_gens += 1
    
    # Varianza intra-generacional (de mean vs best)
    avg_variance = mean([abs(best - mean_val) for best, mean_val in zip(best_vals, mean_vals)])
    
    # Tendencia reciente (últimas 10 gens)
    recent_n = min(10, len(best_vals))
    recent_trend = trend_slope(list(range(recent_n)), best_vals[-recent_n:])
    
    # Coeficiente de variación (estabilidad)
    cv_best = coef_var(best_vals)
    cv_mean = coef_var(mean_vals)
    
    return {
        'max_best': max_best,
        'gen_at_max': gen_max_best,
        'initial_best': initial_best,
        'total_improvement': total_improvement,
        'improvement_pct': improvement_pct,
        'plateau_gens': plateau_gens,
        'plateau_pct': sdiv(plateau_gens * 100.0, len(gens)),
        'avg_variance': avg_variance,
        'recent_trend': recent_trend,
        'cv_best': cv_best,
        'cv_mean': cv_mean,
        'is_converged': plateau_gens > len(gens) * 0.3,  # >30% en plateau
        'is_improving': recent_trend > max_best * 0.001,  # trend positivo >0.1%
    }

def analyze_diversity(debug_rows):
    """Analiza diversidad genética y heterogeneidad poblacional."""
    if not debug_rows or len(debug_rows) < 10:
        return None

    bounds = infer_carindex_bounds(debug_rows)
    
    # Familia de índices de coche
    families = defaultdict(int)
    for r in debug_rows:
        fam = car_index_family_for_row(r, bounds=bounds)
        families[fam] += 1
    
    total = len(debug_rows)
    loaded_share = sdiv(families.get('LOADED', 0) * 100.0, total)
    random_share = sdiv(families.get('RANDOM', 0) * 100.0, total)
    mutated_share = sdiv((
        families.get('MUT_LOADED', 0)
        + families.get('MUT_SESSION', 0)
        + families.get('MUT_LOADED_LARGE', 0)
    ) * 100.0, total)
    
    # Fitness por familia
    fitness_by_family = defaultdict(list)
    for r in debug_rows:
        fam = car_index_family_for_row(r, bounds=bounds)
        fitness_by_family[fam].append(r.get('fit', 0.0))
    
    family_stats = {}
    for fam, fits in fitness_by_family.items():
        if fits:
            family_stats[fam] = {
                'count': len(fits),
                'mean_fitness': mean(fits),
                'max_fitness': max(fits),
                'std_fitness': stdev(fits),
            }
    
    # Muertes por familia
    deaths_by_family = defaultdict(lambda: defaultdict(int))
    for r in debug_rows:
        fam = car_index_family_for_row(r, bounds=bounds)
        death = r.get('death', 'UNKNOWN')
        deaths_by_family[fam][death] += 1
    
    # Shannon entropy para diversidad
    entropy = -sum(sdiv(families[k], total) * math.log(sdiv(families[k], total)) 
                   for k in families.keys() if families[k] > 0)
    max_entropy = math.log(len(families)) if len(families) > 0 else 1.0
    normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0.0
    
    return {
        'total_cars': total,
        'families': dict(families),
        'loaded_share': loaded_share,
        'random_share': random_share,
        'mutated_share': mutated_share,
        'family_stats': family_stats,
        'entropy': entropy,
        'normalized_entropy': normalized_entropy,
        'is_diverse': normalized_entropy > 0.6,
        'deaths_by_family': dict(deaths_by_family),
    }

def predict_fitness_trajectory(summary_rows, future_gens=10):
    """Predice trayectoria de fitness basada en regresión lineal."""
    if not summary_rows or len(summary_rows) < 3:
        return None
    
    gens = [r['gen'] for r in summary_rows]
    best_vals = [r['best'] for r in summary_rows]
    
    # Usar últimas N gens (hasta 20) para predicción más relevante
    use_n = min(20, len(gens))
    # Construir historial relativo (0..use_n-1) y calcular pendiente/ordenada
    y_hist = best_vals[-use_n:]
    x_hist = list(range(use_n))

    # Calcular pendiente usando los indices relativos y extrapolar a futuro
    slope = trend_slope(x_hist, y_hist)
    intercept = y_hist[0] - slope * x_hist[0]

    # Predicción: el siguiente punto corresponde a x = use_n (continuando la secuencia)
    current_gen = gens[-1]
    predictions = []
    for i in range(1, future_gens + 1):
        pred_gen = current_gen + i
        x_pred = (use_n - 1) + i
        pred_val = intercept + slope * x_pred
        predictions.append({
            'gen': pred_gen,
            'predicted_fitness': pred_val,
        })
    
    # Correlación de la predicción
    correlation = pearson_corr(x_hist, y_hist)
    
    # Tiempo para alcanzar threshold (si existe mejora)
    target_fitness = max(best_vals) * 1.1  # 10% mejor que actual
    gens_to_target = None
    if slope > 0:
        gens_needed = (target_fitness - best_vals[-1]) / slope
        if gens_needed > 0:
            gens_to_target = int(round(gens_needed))
    
    return {
        'slope': slope,
        'intercept': intercept,
        'correlation': correlation,
        'predictions': predictions,
        'gens_to_target_10pct': gens_to_target,
        'is_improving': slope > 0,
        'is_stable': abs(slope) < max(best_vals) * 0.0001,
    }

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
        'stop_bonus': 'Stop completion bonus',
        'yield_bonus': 'Yield completion bonus',
        'net': 'Net normal',
    }
    fit_vals = [r.get('fit', 0.0) for r in debug_rows]
    fit_mean = mean(fit_vals)
    correlations = {}
    contributions = {}
    component_means = {}
    for key in labels:
        if key not in available:
            continue
        vals = [r.get(key, 0.0) for r in debug_rows]
        correlations[key] = pearson_corr(vals, fit_vals)
        component_means[key] = mean(vals)
        contributions[key] = sdiv(component_means[key], fit_mean) if fit_mean != 0 else 0.0

    penalty_keys = ('pen_m', 'pen_v', 'pen_tv', 'pen_nav', 'pen_lazy', 'pen_steer_app')
    pen_means = [
        (key, mean([r.get(key, 0.0) for r in debug_rows]))
        for key in penalty_keys if key in available
    ]
    pen_means.sort(key=lambda item: item[1], reverse=True)

    return {
        'schema': debug_rows[0].get('_schema', 'unknown'),
        'component_labels': labels,
        'component_fitness_correlations': correlations,
        'component_contributions': contributions,
        'component_means': component_means,
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
            '_schema': detect_debug_schema(header_map.keys()),
            '_available_fields': tuple(sorted(header_map.keys())),
            'gen': to_num(parts, header_map.get('gen', 0), int),
            'car': parts[header_map.get('car', 1)].strip() if len(parts) > header_map.get('car', 1) else '',
            'fit': to_num(parts, header_map.get('fit', 2), float),
            'time': to_num(parts, header_map.get('time', 3), int),
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
            'training': parse_bool_token(parts[t_idx]) if t_idx is not None and t_idx < len(parts) else None,
        }
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
        r['mut_rate_error'] = (
            r['mut_rate'] - mutation_profile['expected_rate']
            if mutation_profile['expected_rate'] is not None else 0.0
        )
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
    rows.sort(key=lambda r: (r.get('gen', 0), r.get('car_index', 0), r.get('car', '')))
    return rows

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

    R.p(f'\n{"="*76}')
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
    R.p(f'  Generaciones:     {rows[0]["gen"]} - {rows[-1]["gen"]} ({n} total)')
    R.p(f'  BestFit max:      {br["best"]:.6f}  (gen {br["gen"]})')
    R.p(f'  BestFit medio:    {avg_best:.6f}')
    R.p(f'  MeanFit max:      {mr["mean"]:.6f}  (gen {mr["gen"]})')
    R.p(f'  MeanFit medio:    {avg_mean:.6f}')
    R.p(f'  MeanFit min:      {wr["mean"]:.6f}  (gen {wr["gen"]})')
    R.p(f'  MeanFit P25/P50/P75: {p25_mean:.4f} / {p50_mean:.4f} / {p75_mean:.4f}')
    R.p(f'  MeanFit < 0:      {neg}/{n} ({sdiv(neg*100,n):.1f}%)')
    R.p(f'  TiempoMedio:      {min(r["time"] for r in rows):.2f}s - {max(r["time"] for r in rows):.2f}s (media {avg_time:.2f}s)')
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

        R.p(f'\n-- KPI de Test (promedio) --')
        R.p(f'  N evaluado medio: {avg_n:.1f}')
        R.p(f'  Aciertos (%):     {avg_success:.2f}%')
        R.p(f'  Errores (%):      {avg_fail:.2f}%')
        R.p(f'  Score (Acierto):  {avg_score_success:.2f}')
        R.p(f'  Score (WilsonLB): {avg_score_wilson:.2f}')
        R.p(f'  Success P10/P50/P90: {p10_success:.2f}% / {p50_success:.2f}% / {p90_success:.2f}%')
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
    R.p('\n-- Correlacion Componentes vs Fitness Final --')
    for key, value in corr.items():
        R.p(f'  {labels.get(key, key):30s}: {value:>7.4f}')

    R.p('\n-- Media y proporcion sobre Fitness medio --')
    for key, value in means.items():
        R.p(f'  {labels.get(key, key):30s}: media={value:>11.4f}  ratio={contrib.get(key, 0.0):>8.4f}')

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
        'f': 0.0, 'wait_bonus': 0.0, 'net': 0.0,
        'pen_m': 0.0, 'pen_v': 0.0, 'pen_cw': 0.0, 'pen_tv': 0.0, 'pen_nav': 0.0,
        'pen_creep': 0.0, 'pen_rev': 0.0, 'pen_lazy': 0.0, 'pen_swstop': 0.0,
        'pen_steer_app': 0.0, 't_norm': 0.0, 't_tot': 0.0,
        'thr_pos': 0.0, 'thr_grace': 0.0, 'brake_grace': 0.0, 'brake_in': 0.0,
        'coast_t': 0.0, 'stop_brake': 0.0, 'stop_throttle': 0.0,
        't_stop_ctx': 0.0, 't_stop_ctx_tl': 0.0, 't_stop_ctx_stop': 0.0, 't_stop_ctx_yield': 0.0,
        'yield_val_t': 0.0, 'stop_val_t': 0.0,
        'stop_zones_n': 0.0, 'fit_peak_raw': 0.0, 'fit_peak_gain': 0.0,
        'stop_bonus': 0.0, 'stop_done_n': 0.0, 'yield_bonus': 0.0, 'yield_done_n': 0.0,
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
        agg['t_norm'] += r.get('t_norm', 0.0)
        agg['t_tot'] += r.get('t_tot', 0.0)
        agg['thr_pos'] += r.get('thr_pos', 0.0)
        agg['thr_grace'] += r.get('thr_grace', 0.0)
        agg['brake_grace'] += r.get('brake_grace', 0.0)
        agg['brake_in'] += r.get('brake_in', 0.0)
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
    R.p(f'\n{"="*76}')
    R.p(f'  ANALISIS DETALLADO (Fitness_Debug) - {len(dbg)} registros, {len(gens)} gens')
    R.p(f'{"="*76}')

    # Pre-agrupar para evitar escaneos repetidos O(n*G)
    by_gen = defaultdict(list)
    by_death = defaultdict(list)

    # Por Spawn
    spawns = defaultdict(list)
    for r in dbg:
        by_gen[r['gen']].append(r)
        by_death[r['death']].append(r)
        spawns[r['spawn']].append(r)

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
        R.p(f'  {reason:45s}: {cnt:5d} ({sdiv(cnt*100,len(dbg)):5.1f}%) fit={mf:>10.1f} t={mt:.1f}s')

    family_counts = Counter(r.get('death_family', death_family(r.get('death', ''))) for r in dbg)
    death_fail_n = sum(1 for r in dbg if r.get('is_test_failure_death', is_test_failure_reason(r.get('death', ''))))
    R.p(f'\n-- Familias y Fallos por DeathReason --')
    for fam, cnt in sorted(family_counts.items(), key=lambda kv: (death_family_order_index(kv[0]), -kv[1], kv[0])):
        R.p(f'  {fam:14s}: {cnt:5d} ({sdiv(cnt*100, len(dbg)):5.1f}%)')
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
    R.p(f'  Ticks Normal / Total:            {sdiv(agg["t_norm"], nd):>6.1f} / {sdiv(agg["t_tot"], nd):>6.1f}')
    R.p(f'  Acum_ThrottlePos:                {sdiv(agg["thr_pos"], nd):>10.4f}')
    R.p(f'  Acum_ThrottleDuringGraceTime:    {sdiv(agg["thr_grace"], nd):>10.4f}')
    R.p(f'  Acum_BrakeDuringGraceTime:       {sdiv(agg["brake_grace"], nd):>10.4f}')
    R.p(f'  Acum_BrakeInput:                 {sdiv(agg["brake_in"], nd):>10.4f}')
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
            f'  Config EvolutionManager:        mutados={MUTATION_RATE_EVOLVED*100:.1f}% | '
            f'MUT_LOADED_LARGE={MUTATION_RATE_RANDOM_FAMILY*100:.1f}%'
        )
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
                mean([x.get('expected_mut_rate', 0.0) or 0.0 for x in mutation_rows]),
                mean([x.get('fit', 0.0) for x in mutation_rows]),
            ))
        if fam_stats:
            R.p('  By family (observed vs expected):')
            for fam, n, mrate, expected, mfit in sorted(fam_stats, key=lambda x: x[2], reverse=True):
                R.p(
                    f'    {fam:10s}: N={n:4d} observed={mrate*100:>6.2f}% '
                    f'expected={expected*100:>5.2f}% fit_mean={mfit:>9.1f}'
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

# ── Resumen rapido para comparacion ──

def report_quicksummary(R, rows, dbg):
    """Bloque compacto para copiar-pegar y comparar entre dias."""
    n = len(rows)
    if n == 0 and not dbg:
        return

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
        R.p(f'  Generaciones:     {n}')
        R.p(f'  BestFit max:      {br["best"]:.6f} (gen {br["gen"]})')
        R.p(f'  BestFit medio:    {avg_best:.6f}')
        R.p(f'  MeanFit max:      {mr["mean"]:.6f} (gen {mr["gen"]})')
        R.p(f'  MeanFit medio:    {avg_mean:.6f}')
        R.p(f'  MeanFit P50:      {pctl([r["mean"] for r in rows], 50):.6f}')
        R.p(f'  %MeanFit < 0:     {sdiv(neg*100,n):.1f}%')
        R.p(f'  TiempoMedio:      {avg_time:.2f}s')
    else:
        R.p('  Generaciones:     0 (summary vacio)')
        R.p('  Best/MeanFit:     n/a (se usa bloque Debug para comparacion rapida)')

    if dbg:
        nd = len(dbg)
        deaths = Counter(r['death'] for r in dbg)
        top_death = deaths.most_common(1)[0] if deaths else ('N/A', 0)
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
        R.p(f'  ThrGrace med:     {sdiv(sum(r.get("thr_grace", 0.0) for r in dbg), nd):.2f}')
        R.p(f'  BrGrace med:      {sdiv(sum(r.get("brake_grace", 0.0) for r in dbg), nd):.2f}')
        R.p(f'  YieldVal med:     {sdiv(sum(r.get("yield_val_t", 0.0) for r in dbg), nd):.2f}')
        R.p(f'  StopVal med:      {sdiv(sum(r.get("stop_val_t", 0.0) for r in dbg), nd):.2f}')
        R.p(f'  StopDone med:     {sdiv(sum(r.get("stop_done_n", 0.0) for r in dbg), nd):.2f}')
        R.p(f'  YieldDone med:    {sdiv(sum(r.get("yield_done_n", 0.0) for r in dbg), nd):.2f}')
        R.p(f'  StopBonus med:    {sdiv(sum(r.get("stop_bonus", 0.0) for r in dbg), nd):.2f}')
        R.p(f'  YieldBonus med:   {sdiv(sum(r.get("yield_bonus", 0.0) for r in dbg), nd):.2f}')
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
        R.p(f'  Muerte #1:        {top_death[0]} ({sdiv(top_death[1]*100,nd):.0f}%)')
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
        wl_rows = [m['wilson_lo'] for m in derived if m['n'] > 0]
        score_wilson = sdiv(sum(wl_rows), len(wl_rows)) if wl_rows else 0.0
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
        if 'selected_rows' in meta:
            R.p(f'  Filas seleccionadas (modo): {meta.get("selected_rows", 0)}')
        R.p(f'  Filas descart.:  {meta.get("discarded_rows", 0)}')
        R.p(f'  Filas vacias:    {meta.get("empty_rows", 0)}')
        R.p(f'  Filas cortas:    {meta.get("short_rows", 0)}')
        R.p(f'  Campos mapeados: {len(meta.get("mapped_keys", []))} -> {short_list(meta.get("mapped_keys", []), 14)}')
        R.p(f'  Campos faltan:   {short_list(meta.get("missing_required", []), 14)}')
        R.p(f'  Cabeceras extra: {short_list(meta.get("unknown_headers", []), 14)}')

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

def report_yield_stuck_detection(R, info):
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
        hdr = (
            f'  {"Gen":>5s} | {"Car":>16s} | {"Spawn":>15s} | {"Fit":>10s} | {"t":>6s} | '
            f'{"Fit/s":>9s} | {"StopCtx%":>9s} | {"YShare%":>8s} | {"SShare%":>8s} | {"TShare%":>8s} | {"StopTk":>7s} | {"YVal":>6s} | {"SVal":>6s} | {"GBr":>6s} | {"Score":>6s} | {"Sev":>5s}'
        )
        R.p(hdr)
        R.p(f'  {"-"*(len(hdr)-2)}')
        for c in candidates[:TOP_ROWS]:
            R.p(
                f'  {c.get("gen", 0):>5d} | {c.get("car", "")[:16]:>16s} | {c.get("spawn", "").replace("TargetPoint", "TP"):>15s} | '
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

    gens = info.get('gens', [])
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

def report_stop_stuck_detection(R, info):
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
        hdr = (
            f'  {"Gen":>5s} | {"Car":>16s} | {"Spawn":>15s} | {"Fit":>10s} | {"t":>6s} | '
            f'{"Fit/s":>9s} | {"StopCtx%":>9s} | {"SShare%":>8s} | {"YShare%":>8s} | {"TShare%":>8s} | '
            f'{"StopTk":>7s} | {"Out%":>6s} | {"CmdOut%":>7s} | {"SVal":>6s} | {"Score":>6s} | {"Cause":>9s} | {"Sev":>5s}'
        )
        R.p(hdr)
        R.p(f'  {"-"*(len(hdr)-2)}')
        for c in candidates[:TOP_ROWS]:
            R.p(
                f'  {c.get("gen", 0):>5d} | {c.get("car", "")[:16]:>16s} | {c.get("spawn", "").replace("TargetPoint", "TP"):>15s} | '
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

    gens = info.get('gens', [])
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

def report_summary_deep(R, rows):
    if not rows:
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
    by_spawn = defaultdict(list)
    by_gen = defaultdict(list)
    by_death = defaultdict(list)
    by_family = defaultdict(list)

    missing_spawn = 0
    missing_death = 0
    bad_ticks = 0
    neg_time = 0

    for r in dbg:
        by_spawn[r['spawn']].append(r)
        by_gen[r['gen']].append(r)
        by_death[r['death']].append(r)
        by_family[r.get('death_family', death_family(r['death']))].append(r)
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
    report_yield_stuck_detection(R, yield_stuck)
    report_stop_stuck_detection(R, stop_stuck)

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

    # Familias de muerte
    R.p(f'\n-- Muertes por Familia --')
    hdr = f'  {"Familia":>10s} | {"N":>7s} | {"Pct":>7s} | {"FitMed":>10s} | {"tMed":>7s} | {"PenM":>9s} | {"PenV":>9s} | {"PenSS":>9s}'
    R.p(hdr)
    R.p(f'  {"-"*(len(hdr)-2)}')
    for fam, rows_f in sorted(by_family.items(), key=lambda kv: len(kv[1]), reverse=True):
        nf = len(rows_f)
        R.p(
            f'  {fam:>10s} | {nf:>7d} | {sdiv(nf*100, nd):>6.2f}% | {mean([r["fit"] for r in rows_f]):>10.2f} | '
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

    # Correlaciones de componentes con fitness
    fit_vals = [r['fit'] for r in dbg]
    corr_items = [
        ('time', 'Tiempo'),
        ('a', 'Acum_A'),
        ('b', 'Media_B'),
        ('e', 'Acum_E'),
        ('f', 'Acum_F'),
        ('net', 'Acum_NetNormal'),
        ('pen_m', 'Penalty_Muerte'),
        ('pen_v', 'Penalty_Velocidad'),
        ('pen_tv', 'Penalty_TrafficViolation'),
        ('pen_nav', 'Penalty_NavViolation'),
        ('pen_creep', 'Penalty_Creeping'),
        ('pen_rev', 'Penalty_Reverse'),
        ('pen_lazy', 'Penalty_Lazy'),
        ('pen_swstop', 'Penalty_SteeringWhileStopped'),
        ('pen_steer_app', 'Penalty_SteerApproach'),
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
    available_fields = debug_available_fields(dbg)
    derived_corr_fields = {
        'time', 'steer_gap_abs', 'steer_in_avg', 'steer_abs_avg',
        'steer_gap_avg_abs', 'stop_bonus_per', 'yield_bonus_per',
        'stop_done_rate', 'yield_done_rate', 'fit_peak_gain',
    }
    for key, label in corr_items:
        if key not in available_fields and key not in derived_corr_fields:
            continue
        if key == 'steer_gap_abs':
            vals = [abs(r.get('steer_in', 0.0) - r.get('steer_target', 0.0)) for r in dbg]
        else:
            vals = [r.get(key, 0.0) for r in dbg]
        c = pearson_corr(fit_vals, vals)
        corrs.append((abs(c), c, label))
    corrs.sort(reverse=True)

    R.p(f'\n-- Correlaciones con Fitness (Pearson) --')
    for _, c, label in corrs:
        R.p(f'  {label:28s}: {c:+.4f}')

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
    for r in sorted(dbg, key=lambda x: x['fit'])[:top_n]:
        R.p(
            f'  Gen {r["gen"]:>5d} | {r["spawn"].replace("TargetPoint","TP"):>15s} | '
            f'fit={r["fit"]:>10.2f} | t={r["time"]:>4d}s | death={r["death"]}'
        )

    R.p(f'\n-- Mejores {top_n} Coches (raw fitness) --')
    for r in sorted(dbg, key=lambda x: -x['fit'])[:top_n]:
        R.p(
            f'  Gen {r["gen"]:>5d} | {r["spawn"].replace("TargetPoint","TP"):>15s} | '
            f'fit={r["fit"]:>10.2f} | t={r["time"]:>4d}s | death={r["death"]}'
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
    yield_val_total = sum(r.get('yield_val_t', 0.0) for r in dbg_rows)
    stop_val_total = sum(r.get('stop_val_t', 0.0) for r in dbg_rows)
    stop_bonus_total = sum(r.get('stop_bonus', 0.0) for r in dbg_rows)
    yield_bonus_total = sum(r.get('yield_bonus', 0.0) for r in dbg_rows)
    stop_done_total = sum(r.get('stop_done_n', 0.0) for r in dbg_rows)
    yield_done_total = sum(r.get('yield_done_n', 0.0) for r in dbg_rows)
    stop_bonus_per_total = sum(r.get('stop_bonus_per', 0.0) for r in dbg_rows)
    yield_bonus_per_total = sum(r.get('yield_bonus_per', 0.0) for r in dbg_rows)
    stop_done_rate_total = sum(r.get('stop_done_rate', 0.0) for r in dbg_rows)
    yield_done_rate_total = sum(r.get('yield_done_rate', 0.0) for r in dbg_rows)
    steer_in_total = sum(r.get('steer_in', 0.0) for r in dbg_rows)
    steer_target_total = sum(r.get('steer_target', 0.0) for r in dbg_rows)
    steer_gap_total = sum(abs(r.get('steer_in', 0.0) - r.get('steer_target', 0.0)) for r in dbg_rows)

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
        'yield_stuck_detection': yield_stuck or {},
        'stop_stuck_detection': stop_stuck or {},
        'auto_insights': auto_insights or [],
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
            'avg_coast_t': sdiv(sum(r.get('coast_t', 0.0) for r in dbg_rows), len(dbg_rows)),
            'avg_stop_brake': sdiv(sum(r.get('stop_brake', 0.0) for r in dbg_rows), len(dbg_rows)),
            'avg_stop_throttle': sdiv(sum(r.get('stop_throttle', 0.0) for r in dbg_rows), len(dbg_rows)),
            'avg_pen_creep': sdiv(creep_total, len(dbg_rows)),
            'avg_pen_rev': sdiv(rev_total, len(dbg_rows)),
            'avg_pen_lazy': sdiv(lazy_total, len(dbg_rows)),
            'avg_pen_swstop': sdiv(steer_stop_total, len(dbg_rows)),
            'avg_pen_nav': sdiv(sum(r.get('pen_nav', 0.0) for r in dbg_rows), len(dbg_rows)),
            'avg_pen_steer_app': sdiv(steer_approach_total, len(dbg_rows)),
            'avg_yield_val_t': sdiv(yield_val_total, len(dbg_rows)),
            'avg_stop_val_t': sdiv(stop_val_total, len(dbg_rows)),
            'avg_stop_bonus': sdiv(stop_bonus_total, len(dbg_rows)),
            'avg_yield_bonus': sdiv(yield_bonus_total, len(dbg_rows)),
            'avg_stop_done_n': sdiv(stop_done_total, len(dbg_rows)),
            'avg_yield_done_n': sdiv(yield_done_total, len(dbg_rows)),
            'avg_stop_bonus_per': sdiv(stop_bonus_per_total, len(dbg_rows)),
            'avg_yield_bonus_per': sdiv(yield_bonus_per_total, len(dbg_rows)),
            'avg_stop_done_rate': sdiv(stop_done_rate_total, len(dbg_rows)),
            'avg_yield_done_rate': sdiv(yield_done_rate_total, len(dbg_rows)),
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
            'car_index_families': summarize_car_index_families(dbg_rows),
            'brake_share': sdiv(sum(r.get('brake_in', 0.0) for r in dbg_rows), cmd_total),
            'grace_brake_share': sdiv(sum(r.get('brake_grace', 0.0) for r in dbg_rows), grace_cmd_total),
            'stop_brake_share': sdiv(sum(r.get('stop_brake', 0.0) for r in dbg_rows), stop_cmd_total),
            'stop_ctx_tick_coverage': sdiv(stop_ticks_total, ticks_total),
            'death_families': dict(families),
            'death_failure_rows': death_failure_rows,
            'death_failure_pct': sdiv(death_failure_rows * 100.0, len(dbg_rows)),
        },
        'spawn_stop_percentiles': sorted(spawn_stop_stats, key=lambda x: x.get('legal_fail_pct', 0.0), reverse=True)[:20],
        'previous_sessions': previous_sessions,
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ── Graficas ──

def save_fig(fig, name):
    p = os.path.join(OUT_DIR, name)
    if not ENABLE_PLOTS:
        logging.info('Plots disabled, skipping: %s', name)
        plt.close(fig)
        return p
    # Asegurar existencia de carpeta antes de guardar
    try:
        if OUT_DIR and not os.path.exists(OUT_DIR):
            os.makedirs(OUT_DIR, exist_ok=True)
    except Exception:
        logging.warning('No se pudo crear OUT_DIR para guardar figura: %s', OUT_DIR)

    try:
        fig.savefig(p, dpi=150, bbox_inches='tight')
        logging.info('Saved plot: %s', name)
    except Exception as e:
        logging.error('Error saving plot %s: %s', name, e)
        import traceback; traceback.print_exc()
    plt.close(fig)
    return p

def plot_test_model_dashboard(summary, previous_sessions=None, model_dates=None):
    stats = summarize_test_results(summary)
    if not stats:
        return []

    rows = stats['rows']
    derived = stats['derived']
    gens = [r.get('gen_phase', r.get('gen', i + 1)) for i, r in enumerate(rows)]
    rates = [m['success_rate'] for m in derived]
    fitness = [r.get('mean', 0.0) for r in rows]
    times = [r.get('time', 0.0) for r in rows]
    window = max(2, min(5, len(rows)))

    fig = plt.figure(figsize=(20, 12), facecolor='#f4f6f8')
    grid = fig.add_gridspec(
        3, 12,
        height_ratios=[0.78, 2.25, 2.05],
        hspace=0.50,
        wspace=0.75,
    )
    fig.subplots_adjust(left=0.065, right=0.975, top=0.88, bottom=0.075)
    model_text = ''
    if model_dates:
        model_text = ' | '.join(f'{name}: {date}' for name, date in sorted(model_dates.items()))
    title = f'TEST - Comparativa rapida del modelo ({stats["gens"]} generaciones, N={stats["total_n"]})'
    fig.suptitle(title, fontsize=18, fontweight='bold', y=0.985)
    if model_text:
        fig.text(0.5, 0.952, model_text, ha='center', fontsize=9, color='#4b5563')

    cards = [
        ('ACIERTO GLOBAL', f'{stats["success_rate"]:.1f}%', f'IC95% {stats["wilson_lo"]:.1f}-{stats["wilson_hi"]:.1f}%'),
        ('MEDIANA / ESTABILIDAD', f'{stats["success_median"]:.1f}%', f'desv. {stats["success_std"]:.1f} pp'),
        ('MEJOR GENERACION', f'{stats["success_max"]:.1f}%', f'generacion {stats["best_gen"]}'),
        ('FITNESS / TIEMPO', f'{stats["fitness_mean"]:,.0f}', f'{stats["time_mean"]:.1f} s de media'),
    ]
    for col, (label, value, detail) in enumerate(cards):
        ax = fig.add_subplot(grid[0, col * 3:(col + 1) * 3])
        ax.set_facecolor('white')
        for spine in ax.spines.values():
            spine.set_color('#d1d5db')
        ax.set_xticks([])
        ax.set_yticks([])
        ax.text(0.5, 0.76, label, ha='center', va='center', fontsize=9, color='#6b7280', fontweight='bold')
        ax.text(0.5, 0.43, value, ha='center', va='center', fontsize=22, color='#111827', fontweight='bold')
        ax.text(0.5, 0.14, detail, ha='center', va='center', fontsize=9, color='#4b5563')

    ax = fig.add_subplot(grid[1, :9])
    colors = ['#16a34a' if v >= stats['success_rate'] else '#f59e0b' for v in rates]
    ax.bar(gens, rates, color=colors, alpha=0.78, label='Acierto por generacion')
    ax.plot(gens, rates, color='#1f2937', marker='o', linewidth=1.4, markersize=4)
    if len(rates) >= 2:
        ax.plot(gens, rolling(rates, window), color='#2563eb', linewidth=2.8, label=f'Media movil {window}')
    ax.axhline(stats['success_rate'], color='#dc2626', linestyle='--', linewidth=2,
               label=f'Global {stats["success_rate"]:.1f}%')
    ax.set_ylim(0, 100)
    ax.set_title('Acierto por generacion')
    ax.set_xlabel('Generacion de test')
    ax.set_ylabel('Acierto (%)')
    ax.grid(True, axis='y', alpha=0.25)
    ax.legend(loc='upper left', ncols=3, fontsize=9, framealpha=0.92)

    ax = fig.add_subplot(grid[1, 9:12])
    ax.bar(['Aciertos', 'Fallos'], [stats['total_success'], stats['total_fail']],
           color=['#16a34a', '#dc2626'], alpha=0.85)
    ax.set_title('Resultado acumulado')
    ax.set_ylabel('Evaluaciones')
    ax.grid(True, axis='y', alpha=0.25)
    count_max = max(stats['total_success'], stats['total_fail'], 1)
    ax.set_ylim(0, count_max * 1.16)
    for i, value in enumerate((stats['total_success'], stats['total_fail'])):
        ax.text(i, value + count_max * 0.025, str(value), ha='center', va='bottom', fontweight='bold')

    ax = fig.add_subplot(grid[2, :7])
    fit_line, = ax.plot(gens, fitness, color='#7c3aed', marker='o', linewidth=2, label='Fitness medio')
    ax.set_title('Calidad y duracion por generacion')
    ax.set_xlabel('Generacion de test')
    ax.set_ylabel('Fitness medio', color='#7c3aed')
    ax.tick_params(axis='y', labelcolor='#7c3aed')
    ax.grid(True, alpha=0.25)
    ax2 = ax.twinx()
    time_line, = ax2.plot(gens, times, color='#0891b2', marker='s', linewidth=1.8, label='Tiempo medio')
    ax2.set_ylabel('Tiempo medio (s)', color='#0891b2')
    ax2.tick_params(axis='y', labelcolor='#0891b2', pad=3)
    ax2.yaxis.labelpad = 8
    ax.legend(handles=[fit_line, time_line], loc='upper left', fontsize=9, framealpha=0.92)

    ax = fig.add_subplot(grid[2, 8:12])
    historical = [s for s in (previous_sessions or []) if s.get('test_evaluations', 0) > 0]
    comparison = historical[-6:] + [{
        'session': 'ACTUAL',
        'success_mean': stats['success_rate'],
        'test_evaluations': stats['total_n'],
    }]

    def compact_session_label(session):
        if session == 'ACTUAL':
            return session
        match = re.search(r'(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})$', str(session))
        if match:
            return f'{match.group(2)}-{match.group(3)} {match.group(4)}:{match.group(5)}'
        return str(session).replace('traintest_', '').replace('test_', '')[-14:]

    labels = [compact_session_label(s.get('session', '?')) for s in comparison]
    values = [s.get('success_mean', 0.0) for s in comparison]
    bar_colors = ['#94a3b8'] * max(0, len(values) - 1) + ['#2563eb']
    ax.barh(labels, values, color=bar_colors, alpha=0.9)
    comparison_limit = min(100.0, max(40.0, max(values or [0.0]) + 15.0))
    ax.set_xlim(0, comparison_limit)
    ax.set_title('Comparacion con tests anteriores')
    ax.set_xlabel('Acierto global (%)')
    ax.tick_params(axis='y', labelsize=9, pad=4)
    ax.grid(True, axis='x', alpha=0.25)
    for i, value in enumerate(values):
        label_x = min(value + comparison_limit * 0.02, comparison_limit * 0.91)
        ax.text(label_x, i, f'{value:.1f}%', va='center', fontsize=9, fontweight='bold')

    fig.text(
        0.01, 0.008,
        f'Rango: {stats["success_min"]:.1f}-{stats["success_max"]:.1f}% | '
        f'Peor gen: {stats["worst_gen"]} | Fitness max: {stats["fitness_best"]:,.0f}',
        fontsize=9, color='#4b5563'
    )
    return [save_fig(fig, '00_test_model_dashboard.png')]

def plot_debug(dbg):
    saved = []
    gens = sorted(set(r['gen'] for r in dbg))

    # Pre-agrupar para evitar loops O(n²)
    by_gen = defaultdict(list)
    by_gen_spawn = defaultdict(lambda: defaultdict(list))
    spawn_fits = defaultdict(list)
    spawn_time = defaultdict(list)
    spawn_rows = defaultdict(list)
    for r in dbg:
        by_gen[r['gen']].append(r)
        by_gen_spawn[r['gen']][r['spawn']].append(r['fit'])
        spawn_fits[r['spawn']].append(r['fit'])
        spawn_time[r['spawn']].append(r['time'])
        spawn_rows[r['spawn']].append(r)

    # ── 4. Fitness por Spawn (boxplot) ──
    if spawn_fits:
        fig, ax = plt.subplots(figsize=(14, 6))
        names = sorted(spawn_fits.keys())
        data = [spawn_fits[s] for s in names]
        short = [s.replace('TargetPoint','TP') for s in names]
        bp = ax.boxplot(data, tick_labels=short, patch_artist=True, showfliers=True,
                        flierprops=dict(marker='.', markersize=3, alpha=0.4))
        for patch in bp['boxes']:
            patch.set_facecolor('lightblue')
        ax.axhline(y=0, color='r', linestyle='--', alpha=0.5)
        ax.set_title(f'{LABEL} - Fitness por Spawn Point')
        ax.set_xlabel('Spawn'); ax.set_ylabel('Fitness Raw')
        ax.grid(True, alpha=0.3, axis='y'); plt.xticks(rotation=45)
        saved.append(save_fig(fig, '04_spawn_fitness.png'))

    # ── 5. Tiempo por Spawn ──
    if spawn_time:
        fig, ax = plt.subplots(figsize=(14, 6))
        names = sorted(spawn_time.keys())
        data = [spawn_time[s] for s in names]
        short = [s.replace('TargetPoint','TP') for s in names]
        bp = ax.boxplot(data, tick_labels=short, patch_artist=True,
                        flierprops=dict(marker='.', markersize=3, alpha=0.4))
        for patch in bp['boxes']:
            patch.set_facecolor('lightgreen')
        ax.set_title(f'{LABEL} - Tiempo de Vida por Spawn')
        ax.set_xlabel('Spawn'); ax.set_ylabel('Segundos')
        ax.grid(True, alpha=0.3, axis='y'); plt.xticks(rotation=45)
        saved.append(save_fig(fig, '05_spawn_tiempo.png'))

    # ── 6. Fitness medio por spawn (barras horizontales) ──
    if spawn_fits:
        fig, ax = plt.subplots(figsize=(12, 6))
        names = sorted(spawn_fits.keys(), key=lambda s: sdiv(sum(spawn_fits[s]), len(spawn_fits[s])))
        means = [sdiv(sum(spawn_fits[s]), len(spawn_fits[s])) for s in names]
        short = [s.replace('TargetPoint','TP') for s in names]
        colors = ['tomato' if m < 0 else 'steelblue' for m in means]
        ax.barh(short, means, color=colors, alpha=0.8)
        ax.axvline(x=0, color='k', linewidth=0.8)
        ax.set_title(f'{LABEL} - Fitness medio por Spawn (dificultad)')
        ax.set_xlabel('Fitness medio'); ax.set_ylabel('Spawn')
        ax.grid(True, alpha=0.3, axis='x')
        saved.append(save_fig(fig, '06_spawn_ranking.png'))

    # ── 7. Componentes fitness por gen ──
    if len(gens) >= 1:
        g_a, g_e, g_f, g_wait, g_stop_bonus, g_yield_bonus = [], [], [], [], [], []
        g_pm, g_pv, g_ptv, g_pn, g_pc, g_pr, g_pl, g_ps, g_net, g_fit = [], [], [], [], [], [], [], [], [], []
        for g in gens:
            gc = by_gen[g]  # O(1) lookup
            ng = len(gc)
            g_a.append(sdiv(sum(r['a'] for r in gc), ng))
            g_e.append(sdiv(sum(r['e'] for r in gc), ng))
            g_f.append(sdiv(sum(r['f'] for r in gc), ng))
            g_wait.append(sdiv(sum(r.get('wait_bonus', 0.0) for r in gc), ng))
            g_stop_bonus.append(sdiv(sum(r.get('stop_bonus', 0.0) for r in gc), ng))
            g_yield_bonus.append(sdiv(sum(r.get('yield_bonus', 0.0) for r in gc), ng))
            g_pm.append(sdiv(sum(r['pen_m'] for r in gc), ng))
            g_pv.append(sdiv(sum(r['pen_v'] for r in gc), ng))
            g_ptv.append(sdiv(sum(r.get('pen_tv', 0.0) for r in gc), ng))
            g_pn.append(sdiv(sum(r.get('pen_nav', 0.0) for r in gc), ng))
            g_pc.append(sdiv(sum(r.get('pen_creep', 0.0) for r in gc), ng))
            g_pr.append(sdiv(sum(r.get('pen_rev', 0.0) for r in gc), ng))
            g_pl.append(sdiv(sum(r.get('pen_lazy', 0.0) for r in gc), ng))
            g_ps.append(sdiv(sum(r.get('pen_swstop', 0.0) for r in gc), ng))
            g_net.append(sdiv(sum(r['net'] for r in gc), ng))
            g_fit.append(sdiv(sum(r['fit'] for r in gc), ng))

        fig, axes = plt.subplots(3, 1, figsize=(15, 14))
        fig.suptitle(f'{LABEL} - Componentes del Fitness', fontsize=14, fontweight='bold')
        # Usar lineas sin marcadores cuando hay muchas gens (evita miles de markers)
        mk = 'o' if len(gens) <= 300 else ''
        ms = 3 if len(gens) <= 300 else 1

        ax = axes[0]
        if debug_field_available(dbg, 'a'):
            ax.plot(gens, g_a, f'g-{mk}', markersize=ms, label='A', linewidth=1.5)
        if debug_field_available(dbg, 'e'):
            ax.plot(gens, g_e, f'b-{mk}', markersize=ms, label='E (legacy)', linewidth=1.0)
        if debug_field_available(dbg, 'f'):
            ax.plot(gens, g_f, f'c-{mk}', markersize=ms, label='F', linewidth=1.0)
        if debug_field_available(dbg, 'wait_bonus'):
            ax.plot(gens, g_wait, color='tab:olive', linewidth=1.2, label='Wait bonus')
        if debug_field_available(dbg, 'stop_bonus'):
            ax.plot(gens, g_stop_bonus, color='tab:blue', linewidth=1.2, label='Stop bonus')
        if debug_field_available(dbg, 'yield_bonus'):
            ax.plot(gens, g_yield_bonus, color='tab:orange', linewidth=1.2, label='Yield bonus')
        if debug_field_available(dbg, 'net'):
            ax.plot(gens, g_net, 'k-', linewidth=2.5, label='NetNormal')
        ax.set_title('Componentes Positivos (media por gen)')
        ax.set_xlabel(GEN_XLABEL); ax.set_ylabel('Valor'); ax.legend(); ax.grid(True, alpha=0.3)

        ax = axes[1]
        ax.plot(gens, g_pm, f'r-{mk}',  markersize=ms, label='Pen Muerte',    linewidth=1.5)
        ax.plot(gens, g_pv, color='orange', linestyle='-', marker=mk or None, markersize=ms, label='Pen Velocidad', linewidth=1.5)
        ax.plot(gens, g_ptv, color='brown', linestyle='-', marker=mk or None, markersize=ms, label='Pen Trafico', linewidth=1.5)
        ax.plot(gens, g_pn, color='tab:gray', linestyle='-', marker=mk or None, markersize=ms, label='Pen Nav', linewidth=1.2)
        ax.plot(gens, g_pc, color='purple', linestyle='-', marker=mk or None, markersize=ms, label='Pen Creeping', linewidth=1.2)
        ax.plot(gens, g_pr, color='tab:pink', linestyle='-', marker=mk or None, markersize=ms, label='Pen Reverse', linewidth=1.2)
        ax.plot(gens, g_pl, color='tab:olive', linestyle='-', marker=mk or None, markersize=ms, label='Pen Lazy', linewidth=1.2)
        ax.plot(gens, g_ps, color='tab:cyan', linestyle='-', marker=mk or None, markersize=ms, label='Pen SteeringStop', linewidth=1.2)
        ax.set_title('Penalizaciones (media por gen)')
        ax.set_xlabel(GEN_XLABEL); ax.set_ylabel('Valor'); ax.legend(); ax.grid(True, alpha=0.3)

        ax = axes[2]
        ax.plot(gens, g_fit, f'k-{mk}', markersize=ms, linewidth=2,   label='Fitness Final medio')
        if debug_field_available(dbg, 'net'):
            ax.plot(gens, g_net, 'g--', alpha=0.5, linewidth=1, label='NetNormal')
        ax.axhline(y=0, color='r', linestyle='--', alpha=0.4)
        ax.set_title('Fitness Final vs NetNormal (media por gen)')
        ax.set_xlabel(GEN_XLABEL); ax.set_ylabel('Valor'); ax.legend(); ax.grid(True, alpha=0.3)

        plt.tight_layout()
        saved.append(save_fig(fig, '07_componentes.png'))

    # ── 8. Razones de muerte detallado ──
    deaths = Counter(r['death'] for r in dbg)
    if deaths:
        fig, ax = plt.subplots(figsize=(12, max(4, len(deaths)*0.55)))
        reasons = [k for k, _ in deaths.most_common()]
        counts = [v for _, v in deaths.most_common()]
        colors = [death_reason_color(r) for r in reasons]
        short = [short_death_reason(r) for r in reasons]
        ax.barh(short, counts, color=colors, alpha=0.85)
        ax.set_title(f'{LABEL} - Razones de Muerte ({len(dbg)} coches)')
        ax.set_xlabel('Cantidad'); ax.invert_yaxis()
        saved.append(save_fig(fig, '08_muertes_debug.png'))

        grouped = group_death_reasons(deaths)
        if grouped:
            fig, ax = plt.subplots(figsize=(12, max(4, len(grouped)*0.55)))
            reasons = [r for r, _, _ in grouped]
            counts = [c for _, c, _ in grouped]
            colors = [death_reason_color(r) for r in reasons]
            short = [short_death_reason(r) for r in reasons]
            ax.barh(short, counts, color=colors, alpha=0.85)
            add_family_separators(ax, grouped)
            ax.set_title(f'{LABEL} - Razones de Muerte Agrupadas por Familia')
            ax.set_xlabel('Cantidad'); ax.invert_yaxis()
            saved.append(save_fig(fig, '08b_muertes_debug_grupos.png'))

    # ── 9. Distribucion fitness (histograma) ──
    fits = [r['fit'] for r in dbg]
    if fits:
        fig, ax = plt.subplots(figsize=(12, 5))
        q01 = pctl(fits, 1); q99 = pctl(fits, 99)
        clipped = [f for f in fits if q01 <= f <= q99]
        if clipped:
            nbins = min(80, max(10, len(clipped)//10))
            ax.hist(clipped, bins=nbins, color='steelblue', alpha=0.75, edgecolor='black', linewidth=0.3)
            mean_f = sdiv(sum(fits), len(fits))
            ax.axvline(x=0, color='r', linestyle='--', alpha=0.6, label='Fitness = 0')
            ax.axvline(x=mean_f, color='green', linestyle='--', alpha=0.6, label=f'Media = {mean_f:.2f}')
            ax.set_title(f'{LABEL} - Distribucion de Fitness (percentil 1-99)')
            ax.set_xlabel('Fitness'); ax.set_ylabel('Frecuencia'); ax.legend(); ax.grid(True, alpha=0.3)
        saved.append(save_fig(fig, '09_distribucion_fitness.png'))

    # ── 10. Fitness por gen (scatter si pocas gens, stats si muchas) ──
    if len(gens) >= 2:
        fig, ax = plt.subplots(figsize=(15, 6))
        # Usar by_gen para O(n) en lugar de O(n²)
        best_pg = [max(r['fit'] for r in by_gen[g]) for g in gens]
        mean_pg = [sdiv(sum(r['fit'] for r in by_gen[g]), len(by_gen[g])) for g in gens]
        p25_pg  = [pctl([r['fit'] for r in by_gen[g]], 25) for g in gens]
        p75_pg  = [pctl([r['fit'] for r in by_gen[g]], 75) for g in gens]
        if len(gens) <= 200:
            for g in gens:
                gc = [r['fit'] for r in by_gen[g]]
                ax.scatter([g]*len(gc), gc, alpha=0.25, s=6, c='steelblue', zorder=1)
        else:
            # demasiados puntos: rellenar banda P25-P75 en lugar de scatter
            ax.fill_between(gens, p25_pg, p75_pg, alpha=0.2, color='steelblue', label='P25-P75')
        ax.plot(gens, best_pg, 'r-', linewidth=1.5, label='Best', zorder=5)
        ax.plot(gens, mean_pg, 'g-', linewidth=1.5, label='Mean', zorder=5)
        ax.plot(gens, p25_pg,  'b--', linewidth=0.8, alpha=0.6, label='P25', zorder=4)
        ax.plot(gens, p75_pg,  'c--', linewidth=0.8, alpha=0.6, label='P75', zorder=4)
        ax.axhline(y=0, color='k', linestyle='--', alpha=0.3)
        title_suffix = '' if len(gens) <= 200 else ' (banda P25-P75 en lugar de scatter)'
        ax.set_title(f'{LABEL} - Fitness por Generacion{title_suffix}')
        ax.set_xlabel(GEN_XLABEL); ax.set_ylabel('Fitness Raw'); ax.legend(fontsize=8); ax.grid(True, alpha=0.3)
        saved.append(save_fig(fig, '10_fitness_por_gen.png'))

    # ── 11. Heatmap spawn x gen (o spawn x bloque si hay muchas gens) ──
    HEATMAP_MAX_COLS = 150  # max columnas legibles
    if len(gens) >= 2 and len(spawn_fits) >= 2:
        all_spawns = sorted(spawn_fits.keys())
        short = [s.replace('TargetPoint','TP') for s in all_spawns]

        if len(gens) <= HEATMAP_MAX_COLS:
            # Heatmap normal gen a gen
            disp_labels = [str(g) for g in gens]
            matrix = []
            for sp in all_spawns:
                row = []
                for g in gens:
                    gc = by_gen_spawn[g].get(sp, [])
                    row.append(sdiv(sum(gc), len(gc)) if gc else float('nan'))
                matrix.append(row)
            fig_w = max(8, len(gens) * 0.8)
            xlabel = GEN_XLABEL
        else:
            # Agregar en bloques para que quepan en HEATMAP_MAX_COLS columnas
            blk = max(1, len(gens) // HEATMAP_MAX_COLS)
            blocks = [gens[i:i+blk] for i in range(0, len(gens), blk)]
            disp_labels = [f'{b[0]}-{b[-1]}' if len(b)>1 else str(b[0]) for b in blocks]
            matrix = []
            for sp in all_spawns:
                row = []
                for blk_gens in blocks:
                    gc = []
                    for g in blk_gens:
                        gc.extend(by_gen_spawn[g].get(sp, []))
                    row.append(sdiv(sum(gc), len(gc)) if gc else float('nan'))
                matrix.append(row)
            fig_w = max(10, len(blocks) * 0.12)
            xlabel = f'Bloque normalizado ({blk} gens por bloque)'

        fig, ax = plt.subplots(figsize=(fig_w, max(4, len(all_spawns) * 0.5)))
        im = ax.imshow(matrix, aspect='auto', cmap='RdYlGn', interpolation='nearest')
        step = max(1, len(disp_labels) // 30)  # max ~30 etiquetas en eje X
        tick_pos = list(range(0, len(disp_labels), step))
        ax.set_xticks(tick_pos)
        ax.set_xticklabels([disp_labels[i] for i in tick_pos], fontsize=7, rotation=45, ha='right')
        ax.set_yticks(range(len(all_spawns))); ax.set_yticklabels(short, fontsize=8)
        ax.set_xlabel(xlabel); ax.set_ylabel('Spawn')
        ax.set_title(f'{LABEL} - Fitness medio por Spawn x Generacion')
        plt.colorbar(im, ax=ax, label='Fitness medio')
        plt.tight_layout()
        saved.append(save_fig(fig, '11_heatmap_spawn.png'))

    # ── 12. Inputs de control y contexto de parada por gen ──
    if len(gens) >= 1:
        g_thr, g_grace, g_grace_br, g_brake, g_coast = [], [], [], [], []
        g_stop_brake, g_stop_thr, g_stop_ticks = [], [], []
        g_yield_val, g_stop_val = [], []
        g_steer_in, g_steer_tgt, g_steer_gap = [], [], []
        g_brake_share, g_grace_brake_share, g_stop_brake_share = [], [], []
        for g in gens:
            gc = by_gen[g]
            ng = len(gc)
            m_thr = sdiv(sum(r.get('thr_pos', 0.0) for r in gc), ng)
            m_gr = sdiv(sum(r.get('thr_grace', 0.0) for r in gc), ng)
            m_gb = sdiv(sum(r.get('brake_grace', 0.0) for r in gc), ng)
            m_br = sdiv(sum(r.get('brake_in', 0.0) for r in gc), ng)
            m_co = sdiv(sum(r.get('coast_t', 0.0) for r in gc), ng)
            m_sb = sdiv(sum(r.get('stop_brake', 0.0) for r in gc), ng)
            m_st = sdiv(sum(r.get('stop_throttle', 0.0) for r in gc), ng)
            m_sx = sdiv(sum(r.get('t_stop_ctx', 0.0) for r in gc), ng)
            m_yv = sdiv(sum(r.get('yield_val_t', 0.0) for r in gc), ng)
            m_sv = sdiv(sum(r.get('stop_val_t', 0.0) for r in gc), ng)
            m_si = sdiv(sum(r.get('steer_in', 0.0) for r in gc), ng)
            m_stg = sdiv(sum(r.get('steer_target', 0.0) for r in gc), ng)
            m_sgap = sdiv(sum(abs(r.get('steer_in', 0.0) - r.get('steer_target', 0.0)) for r in gc), ng)

            g_thr.append(m_thr)
            g_grace.append(m_gr)
            g_grace_br.append(m_gb)
            g_brake.append(m_br)
            g_coast.append(m_co)
            g_stop_brake.append(m_sb)
            g_stop_thr.append(m_st)
            g_stop_ticks.append(m_sx)
            g_yield_val.append(m_yv)
            g_stop_val.append(m_sv)
            g_steer_in.append(m_si)
            g_steer_tgt.append(m_stg)
            g_steer_gap.append(m_sgap)
            g_brake_share.append(sdiv(m_br, m_br + m_thr))
            g_grace_brake_share.append(sdiv(m_gb, m_gb + m_gr))
            g_stop_brake_share.append(sdiv(m_sb, m_sb + m_st))

        mk = 'o' if len(gens) <= 300 else ''
        ms = 3 if len(gens) <= 300 else 1
        fig, axes = plt.subplots(3, 1, figsize=(15, 13))
        fig.suptitle(f'{LABEL} - Control y Contexto Stop/Semaforo', fontsize=14, fontweight='bold')

        ax = axes[0]
        ax.plot(gens, g_thr, color='tab:green', linestyle='-', marker=mk or None, markersize=ms, label='Acum_ThrottlePos')
        ax.plot(gens, g_grace, color='tab:cyan', linestyle='-', marker=mk or None, markersize=ms, label='Acum_ThrottleDuringGraceTime')
        ax.plot(gens, g_grace_br, color='tab:brown', linestyle='-', marker=mk or None, markersize=ms, label='Acum_BrakeDuringGraceTime')
        ax.plot(gens, g_brake, color='tab:red', linestyle='-', marker=mk or None, markersize=ms, label='Acum_BrakeInput')
        ax.plot(gens, g_coast, color='tab:blue', linestyle='-', marker=mk or None, markersize=ms, label='Acum_CoastTime')
        ax_steer = ax.twinx()
        ax_steer.plot(gens, g_steer_in, color='tab:olive', linestyle='--', marker=mk or None, markersize=ms, label='Acum_SteeringInput')
        ax_steer.plot(gens, g_steer_tgt, color='tab:gray', linestyle='--', marker=mk or None, markersize=ms, label='Acum_TargetSteering')
        ax_steer.plot(gens, g_steer_gap, color='black', linestyle=':', marker=mk or None, markersize=ms, label='SteeringGapAbs')
        ax.set_title('Control global por generacion (media por coche)')
        ax.set_xlabel(GEN_XLABEL); ax.set_ylabel('Acumulado medio')
        ax_steer.set_ylabel('Steering acumulado')
        ax.grid(True, alpha=0.3)
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = ax_steer.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, fontsize=8, loc='upper left')

        ax = axes[1]
        ax.plot(gens, g_stop_brake, color='tab:orange', linestyle='-', marker=mk or None, markersize=ms, label='Acum_StopBrake')
        ax.plot(gens, g_stop_thr, color='tab:purple', linestyle='-', marker=mk or None, markersize=ms, label='Acum_StopThrottle')
        ax.plot(gens, g_stop_ticks, color='tab:gray', linestyle='-', marker=mk or None, markersize=ms, label='Ticks_StopContext')
        ax.plot(gens, g_yield_val, color='tab:pink', linestyle='-', marker=mk or None, markersize=ms, label='YieldValidationTime')
        ax.plot(gens, g_stop_val, color='tab:olive', linestyle='-', marker=mk or None, markersize=ms, label='StopValidationTime')
        ax.set_title('Contexto de parada por generacion (media por coche)')
        ax.set_xlabel(GEN_XLABEL); ax.set_ylabel('Acumulado medio')
        ax.grid(True, alpha=0.3); ax.legend()

        ax = axes[2]
        ax.plot(gens, g_brake_share, color='tab:red', linestyle='-', marker=mk or None, markersize=ms, label='BrakeShare global')
        ax.plot(gens, g_grace_brake_share, color='tab:brown', linestyle='-', marker=mk or None, markersize=ms, label='GraceBrakeShare')
        ax.plot(gens, g_stop_brake_share, color='tab:orange', linestyle='-', marker=mk or None, markersize=ms, label='StopBrakeShare')
        ax.set_title('Ratios de control (0..1)')
        ax.set_xlabel(GEN_XLABEL); ax.set_ylabel('Ratio')
        ax.set_ylim(0.0, 1.0)
        ax.grid(True, alpha=0.3); ax.legend()

        plt.tight_layout()
        saved.append(save_fig(fig, '12_control_inputs.png'))

    # ── 13. Bonos y completados de stop/yield por gen ──
    if len(gens) >= 1:
        g_stop_bonus, g_yield_bonus = [], []
        g_stop_done, g_yield_done = [], []
        for g in gens:
            gc = by_gen[g]
            ng = len(gc)
            g_stop_bonus.append(sdiv(sum(r.get('stop_bonus', 0.0) for r in gc), ng))
            g_yield_bonus.append(sdiv(sum(r.get('yield_bonus', 0.0) for r in gc), ng))
            g_stop_done.append(sdiv(sum(r.get('stop_done_n', 0.0) for r in gc), ng))
            g_yield_done.append(sdiv(sum(r.get('yield_done_n', 0.0) for r in gc), ng))

        mk = 'o' if len(gens) <= 300 else ''
        ms = 3 if len(gens) <= 300 else 1
        fig, axes = plt.subplots(2, 1, figsize=(14, 9))
        fig.suptitle(f'{LABEL} - Bonos y completados Stop/Yield', fontsize=13, fontweight='bold')

        ax = axes[0]
        ax.plot(gens, g_stop_bonus, color='tab:orange', linestyle='-', marker=mk or None, markersize=ms, label='StopCompletionBonus')
        ax.plot(gens, g_yield_bonus, color='tab:purple', linestyle='-', marker=mk or None, markersize=ms, label='YieldCompletionBonus')
        ax.set_title('Bonus por completado (media por coche)')
        ax.set_xlabel(GEN_XLABEL); ax.set_ylabel('Bonus medio')
        ax.grid(True, alpha=0.3); ax.legend()

        ax = axes[1]
        ax.plot(gens, g_stop_done, color='tab:blue', linestyle='-', marker=mk or None, markersize=ms, label='NumStopsCompleted')
        ax.plot(gens, g_yield_done, color='tab:green', linestyle='-', marker=mk or None, markersize=ms, label='NumYieldsCompleted')
        ax.set_title('Completados por generacion (media por coche)')
        ax.set_xlabel(GEN_XLABEL); ax.set_ylabel('Completados')
        ax.grid(True, alpha=0.3); ax.legend()

        plt.tight_layout()
        saved.append(save_fig(fig, '13_completion_bonus.png'))

    # ── 14. CarIndex / genealogia de la poblacion ──
    car_fams = summarize_car_index_families(dbg)
    if car_fams:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 7))
        fig.suptitle(f'{LABEL} - Genealogia CarIndex', fontsize=14, fontweight='bold')
        ordered = sorted(car_fams, key=lambda x: x['n'], reverse=True)
        names = [x['family'] for x in ordered]
        ys = list(range(len(ordered)))
        counts = [x['n'] for x in ordered]
        fit_means = [x['fit_mean'] for x in ordered]
        time_means = [x['time_mean'] for x in ordered]

        ax1.barh(ys, counts, color='tab:blue', alpha=0.8)
        ax1.set_yticks(ys)
        ax1.set_yticklabels(names, fontsize=9)
        ax1.invert_yaxis()
        ax1.set_xlabel('Coches')
        ax1.set_title('Distribucion por familia de origen')
        ax1.grid(True, alpha=0.3, axis='x')

        ax2.barh(ys, fit_means, color='tab:green', alpha=0.75, label='Fitness medio')
        ax2.plot(time_means, ys, color='tab:orange', marker='o', linewidth=1.2, label='Tiempo medio')
        ax2.set_yticks(ys)
        ax2.set_yticklabels(names, fontsize=9)
        ax2.invert_yaxis()
        ax2.set_xlabel('Valor medio')
        ax2.set_title('Rendimiento por familia de origen')
        ax2.grid(True, alpha=0.3, axis='x')
        ax2.legend(fontsize=8, loc='lower right')

        plt.tight_layout()
        saved.append(save_fig(fig, '14_carindex_genealogia.png'))

    # ── 15. Stop/Semaforo por Spawn (percentiles dinamicos) ──
    if len(spawn_fits) >= 2:
        stop_spawn_stats = []
        all_stop_brake = sum(r.get('stop_brake', 0.0) for r in dbg)
        all_stop_thr = sum(r.get('stop_throttle', 0.0) for r in dbg)
        global_stop_share = sdiv(all_stop_brake, all_stop_brake + all_stop_thr) * 100.0
        for sp in sorted(spawn_fits.keys()):
            rows_sp = [r for r in dbg if r.get('spawn') == sp]
            nsp = len(rows_sp)
            legal_fail_n = sum(1 for r in rows_sp if death_family(r.get('death', '')) == 'VIOLATION')
            stop_cov_vals = [sdiv(r.get('t_stop_ctx', 0.0), max(r.get('t_tot', 0.0), 1.0)) * 100.0 for r in rows_sp]
            stop_share_vals = [
                sdiv(r.get('stop_brake', 0.0), r.get('stop_brake', 0.0) + r.get('stop_throttle', 0.0)) * 100.0
                for r in rows_sp if (r.get('stop_brake', 0.0) + r.get('stop_throttle', 0.0)) > 0.0
            ]
            brake_share_vals = [
                sdiv(r.get('brake_in', 0.0), r.get('brake_in', 0.0) + r.get('thr_pos', 0.0)) * 100.0
                for r in rows_sp if (r.get('brake_in', 0.0) + r.get('thr_pos', 0.0)) > 0.0
            ]
            stop_spawn_stats.append({
                'spawn': sp,
                'n': nsp,
                'legal_fail_pct': sdiv(legal_fail_n * 100.0, nsp),
                'stop_ctx_p50': pctl(stop_cov_vals, 50),
                'stop_ctx_p90': pctl(stop_cov_vals, 90),
                'stop_brake_p50': pctl(stop_share_vals, 50),
                'brake_p50': pctl(brake_share_vals, 50),
            })

        stop_spawn_stats = sorted(stop_spawn_stats, key=lambda x: x['legal_fail_pct'], reverse=True)
        max_spawns_plot = 30
        plot_rows = stop_spawn_stats[:max_spawns_plot]
        names = [r['spawn'].replace('TargetPoint', 'TP') for r in plot_rows]
        ys = list(range(len(plot_rows)))

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, max(8, len(plot_rows) * 0.45)))
        fig.suptitle(f'{LABEL} - Stop/Semaforo por Spawn (dinamico)', fontsize=14, fontweight='bold')

        legal_vals = [r['legal_fail_pct'] for r in plot_rows]
        stop_ctx_vals = [r['stop_ctx_p50'] for r in plot_rows]
        ax1.barh(ys, legal_vals, color='tab:red', alpha=0.75, label='LegalFail%')
        ax1.plot(stop_ctx_vals, ys, color='tab:blue', marker='o', linewidth=1.2, label='StopCtx P50%')
        if stop_spawn_stats:
            legal_ref = [r['legal_fail_pct'] for r in stop_spawn_stats if r['legal_fail_pct'] > 0.0 and r['n'] >= MIN_SPAWN_N]
            q3_legal = pctl(legal_ref, 75) if legal_ref else 0.0
            if q3_legal > 0.0:
                ax1.axvline(q3_legal, color='tab:red', linestyle='--', alpha=0.6, label=f'P75 Legal%={q3_legal:.2f}')
        ax1.set_yticks(ys)
        ax1.set_yticklabels(names, fontsize=8)
        ax1.invert_yaxis()
        ax1.set_xlabel('Porcentaje')
        ax1.set_title('Fallo legal y cobertura stop-context (P50) por spawn')
        ax1.grid(True, alpha=0.3, axis='x')
        ax1.legend(fontsize=8)

        stop_share_vals = [r['stop_brake_p50'] for r in plot_rows]
        brake_share_vals = [r['brake_p50'] for r in plot_rows]
        ax2.barh([y + 0.18 for y in ys], stop_share_vals, height=0.35, color='tab:orange', alpha=0.8, label='StopBrake P50%')
        ax2.barh([y - 0.18 for y in ys], brake_share_vals, height=0.35, color='tab:purple', alpha=0.7, label='Brake P50%')
        ax2.axvline(global_stop_share, color='tab:orange', linestyle='--', alpha=0.6, label=f'Global StopBrake%={global_stop_share:.2f}')
        ax2.set_yticks(ys)
        ax2.set_yticklabels(names, fontsize=8)
        ax2.invert_yaxis()
        ax2.set_xlabel('Porcentaje')
        ax2.set_title('Comparativa de frenado (stop-context vs global) por spawn')
        ax2.grid(True, alpha=0.3, axis='x')
        ax2.legend(fontsize=8)

        plt.tight_layout()
        saved.append(save_fig(fig, '15_stop_spawn_percentiles.png'))

    # ── 16. Foco Penalty_Lazy (tendencia + hotspots por spawn) ──
    if len(gens) >= 1 and spawn_rows:
        g_lazy_mean, g_lazy_p90, g_lazy_pct = [], [], []
        for g in gens:
            gc = by_gen[g]
            lazy_vals = [r.get('pen_lazy', 0.0) for r in gc]
            g_lazy_mean.append(mean(lazy_vals))
            g_lazy_p90.append(pctl(lazy_vals, 90))
            g_lazy_pct.append(sdiv(sum(1 for r in gc if is_lazy_reason(r.get('death', ''))) * 100.0, len(gc)))

        total_lazy_pen = sum(r.get('pen_lazy', 0.0) for r in dbg)
        spawn_lazy_stats = []
        for sp, rows_sp in spawn_rows.items():
            vals = [r.get('pen_lazy', 0.0) for r in rows_sp]
            lazy_sum = sum(vals)
            lazy_n = sum(1 for r in rows_sp if is_lazy_reason(r.get('death', '')))
            spawn_lazy_stats.append({
                'spawn': sp,
                'n': len(rows_sp),
                'pen_lazy_mean': mean(vals),
                'pen_lazy_p90': pctl(vals, 90),
                'lazy_pct': sdiv(lazy_n * 100.0, len(rows_sp)),
                'lazy_pen_share': sdiv(lazy_sum * 100.0, total_lazy_pen),
            })

        top_rows = sorted(
            spawn_lazy_stats,
            key=lambda x: (x['pen_lazy_mean'], x['lazy_pct']),
            reverse=True,
        )[:20]

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, max(9, len(top_rows) * 0.45 + 5)))
        fig.suptitle(f'{LABEL} - Foco Penalty_Lazy', fontsize=14, fontweight='bold')

        mk = 'o' if len(gens) <= 300 else ''
        ms = 3 if len(gens) <= 300 else 1
        ax1.plot(gens, g_lazy_mean, color='tab:olive', linestyle='-', marker=mk or None, markersize=ms, linewidth=1.8, label='PenLazy media')
        ax1.plot(gens, g_lazy_p90, color='tab:green', linestyle='--', marker=mk or None, markersize=ms, linewidth=1.5, label='PenLazy P90')
        ax1.set_title('Tendencia temporal de Penalty_Lazy')
        ax1.set_xlabel(GEN_XLABEL)
        ax1.set_ylabel('Penalty_Lazy')
        ax1.grid(True, alpha=0.3)

        ax1b = ax1.twinx()
        ax1b.plot(gens, g_lazy_pct, color='tab:red', linestyle='-', marker=mk or None, markersize=ms, linewidth=1.2, label='LAZY%')
        ax1b.set_ylabel('LAZY%')
        ax1b.set_ylim(0.0, 100.0)

        h1, l1 = ax1.get_legend_handles_labels()
        h2, l2 = ax1b.get_legend_handles_labels()
        ax1.legend(h1 + h2, l1 + l2, fontsize=8, loc='upper left')

        names = [x['spawn'].replace('TargetPoint', 'TP') for x in top_rows]
        ys = list(range(len(top_rows)))
        pen_means = [x['pen_lazy_mean'] for x in top_rows]
        lazy_pct_vals = [x['lazy_pct'] for x in top_rows]
        share_vals = [x['lazy_pen_share'] for x in top_rows]

        ax2.barh(ys, pen_means, color='tab:olive', alpha=0.8, label='PenLazy media')
        ax2.set_yticks(ys)
        ax2.set_yticklabels(names, fontsize=8)
        ax2.invert_yaxis()
        ax2.set_xlabel('Penalty_Lazy medio por coche')
        ax2.set_title('Hotspots de estancamiento por spawn')
        ax2.grid(True, alpha=0.3, axis='x')

        ax2b = ax2.twiny()
        ax2b.plot(lazy_pct_vals, ys, color='tab:red', marker='o', linewidth=1.2, label='LAZY%')
        ax2b.set_xlabel('LAZY% por spawn')
        ax2b.set_xlim(0.0, 100.0)

        for y, v, sh in zip(ys, pen_means, share_vals):
            ax2.text(v, y, f'  {sh:.1f}% pen', va='center', fontsize=7)

        h1, l1 = ax2.get_legend_handles_labels()
        h2, l2 = ax2b.get_legend_handles_labels()
        ax2.legend(h1 + h2, l1 + l2, fontsize=8, loc='lower right')

        plt.tight_layout()
        saved.append(save_fig(fig, '16_penalty_lazy_focus.png'))

    # ── 17. Foco YieldTrap (TIME_FINISHED con bajo fit y alto stop-context) - SIEMPRE SE GENERA ──
    ytrap_plot_enabled = os.environ.get('ANALYSE_YIELD_TRAP_PLOT', '1').strip().lower() not in ('0', 'false', 'no', 'off')
    ytrap = detect_yield_stuck_candidates(dbg) if ytrap_plot_enabled else {}
    has_ytrap = ytrap_plot_enabled and ytrap.get('timefinished_rows', 0) > 0
    
    gen_rows = sorted(ytrap.get('gens', []), key=lambda x: x.get('gen', 0)) if has_ytrap else []
    spawn_rows_y = ytrap.get('spawns', []) if has_ytrap else []

    fig, axes = plt.subplots(2, 1, figsize=(15, max(9, min(16, 7 + len(spawn_rows_y) * 0.22))))
    fig.suptitle(f'{LABEL} - YieldTrap Focus (TIME_FINISHED) - {ytrap.get("timefinished_rows", 0)} casos', fontsize=14, fontweight='bold')

    ax = axes[0]
    if gen_rows:
        x = [int(r.get('gen', 0)) for r in gen_rows]
        tf_n = [int(r.get('tf_n', 0)) for r in gen_rows]
        watch_n = [int(r.get('watch_n', 0)) for r in gen_rows]
        cand_n = [int(r.get('n', 0)) for r in gen_rows]
        cand_pct = [float(r.get('cand_pct_tf', 0.0)) for r in gen_rows]

        ax.bar(x, tf_n, color='lightgray', alpha=0.65, label='TIME_FINISHED')
        ax.plot(x, watch_n, color='tab:orange', marker='o', linewidth=1.5, label='Watch')
        ax.plot(x, cand_n, color='tab:red', marker='o', linewidth=1.8, label='Candidatos')
        ax.set_xlabel(GEN_XLABEL)
        ax.set_ylabel('Conteo')
        ax.grid(True, alpha=0.3)

        axb = ax.twinx()
        axb.plot(x, cand_pct, color='tab:blue', linestyle='--', marker='s', linewidth=1.2, label='Cand/TF%')
        axb.set_ylabel('Cand/TF %')
        axb.set_ylim(0.0, 100.0)

        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = axb.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, fontsize=8, loc='upper left')
    ax.set_title('Deteccion por generacion' if gen_rows else 'Sin datos de YieldTrap')
    if not gen_rows:
        ax.text(0.5, 0.5, 'No hay candidatos de YieldTrap', ha='center', va='center', fontsize=12, transform=ax.transAxes)

    ax = axes[1]
    if spawn_rows_y:
        top_rows = spawn_rows_y[:min(20, len(spawn_rows_y))]
        names = [r.get('spawn', '').replace('TargetPoint', 'TP') for r in top_rows]
        ys = list(range(len(top_rows)))
        tf_n = [int(r.get('tf_n', 0)) for r in top_rows]
        watch_n = [int(r.get('watch_n', 0)) for r in top_rows]
        cand_n = [int(r.get('n', 0)) for r in top_rows]
        cand_pct = [float(r.get('cand_pct_tf', 0.0)) for r in top_rows]

        ax.barh(ys, tf_n, color='lightgray', alpha=0.65, label='TIME_FINISHED')
        ax.barh(ys, watch_n, color='tab:orange', alpha=0.65, label='Watch')
        ax.barh(ys, cand_n, color='tab:red', alpha=0.75, label='Candidatos')
        ax.set_yticks(ys)
        ax.set_yticklabels(names, fontsize=8)
        ax.invert_yaxis()
        ax.set_xlabel('Conteo')
        ax.grid(True, alpha=0.3, axis='x')

        axb = ax.twiny()
        axb.plot(cand_pct, ys, color='tab:blue', marker='o', linewidth=1.2, label='Cand/TF%')
        axb.set_xlim(0.0, 100.0)
        axb.set_xlabel('Cand/TF %')

        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = axb.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, fontsize=8, loc='lower right')
    ax.set_title('Spawns con mas sospecha de atasco' if spawn_rows_y else 'Sin datos de spawns')
    if not spawn_rows_y:
        ax.text(0.5, 0.5, 'No hay datos de spawns con YieldTrap', ha='center', va='center', fontsize=12, transform=ax.transAxes)

    plt.tight_layout()
    saved.append(save_fig(fig, '17_yield_trap_focus.png'))

    # ── 18. Foco StopTrap (TIME_FINISHED en STOP) - SIEMPRE SE GENERA ──
    strap_plot_enabled = os.environ.get('ANALYSE_STOP_TRAP_PLOT', '1').strip().lower() not in ('0', 'false', 'no', 'off')
    strap = detect_stop_stuck_candidates(dbg) if strap_plot_enabled else {}
    has_strap = strap_plot_enabled and strap.get('timefinished_rows', 0) > 0

    gen_rows_s = sorted(strap.get('gens', []), key=lambda x: x.get('gen', 0)) if has_strap else []
    spawn_rows_s = strap.get('spawns', []) if has_strap else []

    fig, axes = plt.subplots(2, 1, figsize=(15, max(9, min(16, 7 + len(spawn_rows_s) * 0.22))))
    fig.suptitle(f'{LABEL} - StopTrap Focus (TIME_FINISHED) - {strap.get("timefinished_rows", 0)} casos', fontsize=14, fontweight='bold')

    ax = axes[0]
    if gen_rows_s:
        x = [int(r.get('gen', 0)) for r in gen_rows_s]
        tf_n = [int(r.get('tf_n', 0)) for r in gen_rows_s]
        watch_n = [int(r.get('watch_n', 0)) for r in gen_rows_s]
        cand_n = [int(r.get('n', 0)) for r in gen_rows_s]
        cand_pct = [float(r.get('cand_pct_tf', 0.0)) for r in gen_rows_s]

        ax.bar(x, tf_n, color='lightgray', alpha=0.65, label='TIME_FINISHED')
        ax.plot(x, watch_n, color='tab:orange', marker='o', linewidth=1.5, label='Watch')
        ax.plot(x, cand_n, color='tab:red', marker='o', linewidth=1.8, label='Candidatos')
        ax.set_xlabel(GEN_XLABEL)
        ax.set_ylabel('Conteo')
        ax.grid(True, alpha=0.3)

        axb = ax.twinx()
        axb.plot(x, cand_pct, color='tab:blue', linestyle='--', marker='s', linewidth=1.2, label='Cand/TF%')
        axb.set_ylabel('Cand/TF %')
        axb.set_ylim(0.0, 100.0)

        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = axb.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, fontsize=8, loc='upper left')
    ax.set_title('Deteccion por generacion' if gen_rows_s else 'Sin datos de StopTrap')
    if not gen_rows_s:
        ax.text(0.5, 0.5, 'No hay candidatos de StopTrap', ha='center', va='center', fontsize=12, transform=ax.transAxes)

    ax = axes[1]
    if spawn_rows_s:
        top_rows = spawn_rows_s[:min(20, len(spawn_rows_s))]
        names = [r.get('spawn', '').replace('TargetPoint', 'TP') for r in top_rows]
        ys = list(range(len(top_rows)))
        tf_n = [int(r.get('tf_n', 0)) for r in top_rows]
        watch_n = [int(r.get('watch_n', 0)) for r in top_rows]
        cand_n = [int(r.get('n', 0)) for r in top_rows]
        cand_pct = [float(r.get('cand_pct_tf', 0.0)) for r in top_rows]

        ax.barh(ys, tf_n, color='lightgray', alpha=0.65, label='TIME_FINISHED')
        ax.barh(ys, watch_n, color='tab:orange', alpha=0.65, label='Watch')
        ax.barh(ys, cand_n, color='tab:red', alpha=0.75, label='Candidatos')
        ax.set_yticks(ys)
        ax.set_yticklabels(names, fontsize=8)
        ax.invert_yaxis()
        ax.set_xlabel('Conteo')
        ax.grid(True, alpha=0.3, axis='x')

        axb = ax.twiny()
        axb.plot(cand_pct, ys, color='tab:blue', marker='o', linewidth=1.2, label='Cand/TF%')
        axb.set_xlim(0.0, 100.0)
        axb.set_xlabel('Cand/TF %')

        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = axb.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, fontsize=8, loc='lower right')
    ax.set_title('Spawns con mas sospecha de atasco' if spawn_rows_s else 'Sin datos de spawns')
    if not spawn_rows_s:
        ax.text(0.5, 0.5, 'No hay datos de spawns con StopTrap', ha='center', va='center', fontsize=12, transform=ax.transAxes)

    plt.tight_layout()
    saved.append(save_fig(fig, '18_stop_trap_focus.png'))

    # ── 19. Diagnostico de steering suavizado/lag ──
    if any(abs(r.get('steer_abs', 0.0)) > 0.0 or abs(r.get('steer_target', 0.0)) > 0.0 for r in dbg):
        g_fit = []
        g_abs = []
        g_gap = []
        g_target = []
        g_applied = []
        for g in gens:
            rows_g = by_gen[g]
            g_fit.append(mean_field(rows_g, 'fit'))
            g_abs.append(mean_field(rows_g, 'steer_abs_avg'))
            g_gap.append(mean_field(rows_g, 'steer_gap_avg_abs'))
            g_target.append(mean_field(rows_g, 'steer_target_avg'))
            g_applied.append(mean_field(rows_g, 'steer_in_avg'))
        fig, ax = plt.subplots(figsize=(12, 6))
        mk = 'o' if len(gens) <= 80 else None
        ms = 3 if len(gens) <= 80 else 0
        ax.plot(gens, g_abs, marker=mk, markersize=ms, label='ABS steering medio/tick')
        ax.plot(gens, g_gap, marker=mk, markersize=ms, label='Gap target-applied medio/tick')
        ax.plot(gens, g_target, linestyle='--', marker=mk, markersize=ms, label='Target steering medio')
        ax.plot(gens, g_applied, linestyle='--', marker=mk, markersize=ms, label='Steering aplicado medio')
        ax.set_title('Diagnostico de steering: suavizado, oscilacion y lag')
        ax.set_xlabel(GEN_XLABEL)
        ax.set_ylabel('Steering normalizado')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best')
        axb = ax.twinx()
        axb.plot(gens, g_fit, linestyle=':', alpha=0.6, label='Fitness medio')
        axb.set_ylabel('Fitness medio')
        h1, l1 = ax.get_legend_handles_labels()
        h2, l2 = axb.get_legend_handles_labels()
        ax.legend(h1 + h2, l1 + l2, loc='best')
        plt.tight_layout()
        saved.append(save_fig(fig, '19_steering_diagnostics.png'))

    # ── 20. Foco Penalty_SteerApproach ──
    if any(r.get('pen_steer_app', 0.0) > 0.0 for r in dbg):
        g_app_mean, g_app_p90, g_app_pct = [], [], []
        for g in gens:
            rows_g = by_gen[g]
            app_vals = [r.get('pen_steer_app', 0.0) for r in rows_g]
            g_app_mean.append(mean(app_vals))
            g_app_p90.append(pctl(app_vals, 90))
            g_app_pct.append(sdiv(sum(1 for v in app_vals if v > 0.0) * 100.0, len(app_vals)))

        app_spawn_stats = []
        total_app_pen = sum(r.get('pen_steer_app', 0.0) for r in dbg)
        for sp, rows_sp in spawn_rows.items():
            app_vals = [r.get('pen_steer_app', 0.0) for r in rows_sp]
            app_spawn_stats.append({
                'spawn': sp,
                'n': len(rows_sp),
                'app_mean': mean(app_vals),
                'app_p90': pctl(app_vals, 90),
                'app_pct': sdiv(sum(1 for v in app_vals if v > 0.0) * 100.0, len(app_vals)),
                'app_share': sdiv(sum(app_vals) * 100.0, total_app_pen),
            })

        top_rows = sorted(app_spawn_stats, key=lambda x: (x['app_mean'], x['app_pct']), reverse=True)[:20]
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, max(9, len(top_rows) * 0.45 + 5)))
        fig.suptitle(f'{LABEL} - Foco Penalty_SteerApproach', fontsize=14, fontweight='bold')

        mk = 'o' if len(gens) <= 300 else ''
        ms = 3 if len(gens) <= 300 else 1
        ax1.plot(gens, g_app_mean, color='tab:olive', linestyle='-', marker=mk or None, markersize=ms, linewidth=1.8, label='SteerApproach media')
        ax1.plot(gens, g_app_p90, color='tab:green', linestyle='--', marker=mk or None, markersize=ms, linewidth=1.5, label='SteerApproach P90')
        ax1.set_title('Tendencia temporal de la penalizacion por aproximacion de steering')
        ax1.set_xlabel(GEN_XLABEL)
        ax1.set_ylabel('Penalty_SteerApproach')
        ax1.grid(True, alpha=0.3)

        ax1b = ax1.twinx()
        ax1b.plot(gens, g_app_pct, color='tab:red', linestyle='-', marker=mk or None, markersize=ms, linewidth=1.2, label='Coches con penalizacion%')
        ax1b.set_ylabel('% coches con penalty')
        ax1b.set_ylim(0.0, 100.0)

        h1, l1 = ax1.get_legend_handles_labels()
        h2, l2 = ax1b.get_legend_handles_labels()
        ax1.legend(h1 + h2, l1 + l2, fontsize=8, loc='upper left')

        names = [x['spawn'].replace('TargetPoint', 'TP') for x in top_rows]
        ys = list(range(len(top_rows)))
        app_means = [x['app_mean'] for x in top_rows]
        app_pct_vals = [x['app_pct'] for x in top_rows]
        share_vals = [x['app_share'] for x in top_rows]

        ax2.barh(ys, app_means, color='tab:olive', alpha=0.8, label='SteerApproach media')
        ax2.set_yticks(ys)
        ax2.set_yticklabels(names, fontsize=8)
        ax2.invert_yaxis()
        ax2.set_xlabel('Penalty_SteerApproach medio por coche')
        ax2.set_title('Hotspots de steering approach por spawn')
        ax2.grid(True, alpha=0.3, axis='x')

        ax2b = ax2.twiny()
        ax2b.plot(app_pct_vals, ys, color='tab:red', marker='o', linewidth=1.2, label='Penalty%')
        ax2b.set_xlabel('% coches con penalty')
        ax2b.set_xlim(0.0, 100.0)

        for y, v, sh in zip(ys, app_means, share_vals):
            ax2.text(v, y, f'  {sh:.1f}% pen', va='center', fontsize=7)

        h1, l1 = ax2.get_legend_handles_labels()
        h2, l2 = ax2b.get_legend_handles_labels()
        ax2.legend(h1 + h2, l1 + l2, fontsize=8, loc='lower right')

        plt.tight_layout()
        saved.append(save_fig(fig, '20_penalty_steer_approach_focus.png'))


    # ── 21. INVALID_BRAIN por generacion y spawn (siempre se genera, aunque esté vacío) ──
    invalid_rows = [r for r in dbg if is_invalid_brain_reason(r.get('death', ''))]
    inv_by_gen = Counter(int(r.get('gen', 0)) for r in invalid_rows) if invalid_rows else Counter()
    inv_by_spawn = Counter(r.get('spawn', '') for r in invalid_rows if r.get('spawn', '')) if invalid_rows else Counter()
    top_spawns = inv_by_spawn.most_common(20) if inv_by_spawn else []
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, max(9, len(top_spawns) * 0.35 + 5)))
    fig.suptitle(f'{LABEL} - INVALID_BRAIN ({len(invalid_rows)} casos)', fontsize=14, fontweight='bold')

    gen_items = sorted(inv_by_gen.items()) if inv_by_gen else []
    if gen_items:
        x = [g for g, _ in gen_items]
        y = [n for _, n in gen_items]
        ax1.bar(x, y, color='tab:red', alpha=0.8)
        ax1.set_xlabel(GEN_XLABEL)
        ax1.set_ylabel('Coches')
        ax1.set_title('Muertes INVALID_BRAIN por generacion')
        ax1.grid(True, alpha=0.3, axis='y')
    else:
        ax1.text(0.5, 0.5, 'No hay muertes INVALID_BRAIN', ha='center', va='center', fontsize=12, transform=ax1.transAxes)
        ax1.set_xticks([])
        ax1.set_yticks([])

    if top_spawns:
        names = [sp.replace('TargetPoint', 'TP') for sp, _ in top_spawns]
        counts = [cnt for _, cnt in top_spawns]
        ys = list(range(len(top_spawns)))
        ax2.barh(ys, counts, color='tab:red', alpha=0.8)
        ax2.set_yticks(ys)
        ax2.set_yticklabels(names, fontsize=8)
        ax2.invert_yaxis()
        ax2.set_xlabel('Coches')
        ax2.set_title('Spawns con mas INVALID_BRAIN')
        ax2.grid(True, alpha=0.3, axis='x')
    else:
        ax2.text(0.5, 0.5, 'No hay spawns con INVALID_BRAIN', ha='center', va='center', fontsize=12, transform=ax2.transAxes)
        ax2.set_xticks([])
        ax2.set_yticks([])

    plt.tight_layout()
    saved.append(save_fig(fig, '21_invalid_brain_focus.png'))

    return saved

def plot_convergence_charts(summary):
    """Genera gráficos de convergencia y estabilidad (siempre, aunque esté vacío)."""
    saved = []
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle(f'{LABEL} - Análisis de Convergencia', fontsize=14, fontweight='bold')
    
    if summary and len(summary) >= 3:
        conv_info = analyze_convergence(summary)
        if conv_info:
            gens = [r['gen'] for r in summary]
            best_vals = [r['best'] for r in summary]
            
            # Panel izq: Fitness + indicador plateau
            ax1.plot(gens, best_vals, 'b-', linewidth=2, label='BestFitness')
            ax1.axhline(y=conv_info['max_best'], color='g', linestyle='--', alpha=0.5, label='Máximo alcanzado')
            threshold = conv_info['max_best'] * 0.99
            ax1.axhline(y=threshold, color='orange', linestyle=':', alpha=0.4, label='Plateau threshold (1%)')
            ax1.fill_between(gens[-conv_info['plateau_gens']:], 
                              min(best_vals), max(best_vals)*1.1, 
                              alpha=0.1, color='red', label=f'Plateau ({conv_info["plateau_gens"]} gens)')
            ax1.set_title('Fitness y Detección de Plateau')
            ax1.set_xlabel(GEN_XLABEL)
            ax1.set_ylabel('BestFitness')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # Panel derecho: Varianza y tendencia
            variance_vals = []
            for i in range(len(summary)):
                rows_at_gen = [summary[i]]
                if rows_at_gen:
                    var = abs(summary[i]['best'] - summary[i]['mean'])
                    variance_vals.append(var)
            
            if variance_vals:
                ax2.plot(gens, variance_vals, 'purple', marker='o', linewidth=2, label='Varianza (Best-Mean)')
                
                # Tendencia reciente
                recent_n = min(10, len(best_vals))
                if recent_n >= 2:
                    recent_gens = gens[-recent_n:]
                    recent_best = best_vals[-recent_n:]
                    z = np.polyfit(range(recent_n), recent_best, 1)
                    p = np.poly1d(z)
                    trend_line = p(range(recent_n))
                    ax2.plot(recent_gens, trend_line, 'r--', linewidth=2, alpha=0.7, label='Tendencia (últimas 10)')
                
                ax2.set_title('Varianza y Tendencia Reciente')
                ax2.set_xlabel(GEN_XLABEL)
                ax2.set_ylabel('Varianza')
                ax2.legend(loc='upper left')
                ax2.grid(True, alpha=0.3)
        else:
            ax1.text(0.5, 0.5, 'Insuficientes datos para análisis de convergencia', 
                    ha='center', va='center', fontsize=12, transform=ax1.transAxes)
            ax2.text(0.5, 0.5, 'Datos insuficientes', 
                    ha='center', va='center', fontsize=12, transform=ax2.transAxes)
            ax1.set_xticks([])
            ax1.set_yticks([])
            ax2.set_xticks([])
            ax2.set_yticks([])
    else:
        ax1.text(0.5, 0.5, 'Datos insuficientes (< 3 generaciones)', 
                ha='center', va='center', fontsize=12, transform=ax1.transAxes)
        ax2.text(0.5, 0.5, 'Datos insuficientes', 
                ha='center', va='center', fontsize=12, transform=ax2.transAxes)
        ax1.set_xticks([])
        ax1.set_yticks([])
        ax2.set_xticks([])
        ax2.set_yticks([])
    
    plt.tight_layout()
    saved.append(save_fig(fig, '22_convergencia.png'))
    
    return saved

def plot_prediction_charts(summary):
    """Genera gráficos de predicción de trayectoria (siempre, aunque esté vacío)."""
    saved = []
    
    fig, ax = plt.subplots(figsize=(14, 6))
    fig.suptitle(f'{LABEL} - Predicción de Trayectoria Fitness', fontsize=14, fontweight='bold')
    
    if summary and len(summary) >= 3:
        pred_info = predict_fitness_trajectory(summary, future_gens=15)
        if pred_info and pred_info['predictions']:
            gens = [r['gen'] for r in summary]
            best_vals = [r['best'] for r in summary]
            
            # Datos históricos
            ax.plot(gens, best_vals, 'b-o', linewidth=2, markersize=4, label='Histórico')
            
            # Predicciones
            pred_gens = [p['gen'] for p in pred_info['predictions']]
            pred_vals = [p['predicted_fitness'] for p in pred_info['predictions']]
            ax.plot(pred_gens, pred_vals, 'r--s', linewidth=2, markersize=5, alpha=0.7, label='Predicción (regresión)')
            
            # Intervalo de confianza simplificado
            std_err = stdev(best_vals[-min(10, len(best_vals)):]) * 1.96 if len(best_vals) > 1 else 0
            if std_err > 0:
                ax.fill_between(pred_gens, 
                                [v - std_err for v in pred_vals], 
                                [v + std_err for v in pred_vals],
                                alpha=0.2, color='red', label=f'IC (95%)')
            
            # Anotaciones
            ax.axvline(x=gens[-1], color='gray', linestyle=':', alpha=0.5, label='Presente')
            ax.set_title(f'Correlación regresión: {pred_info["correlation"]:.4f}')
            ax.set_xlabel(GEN_XLABEL)
            ax.set_ylabel('BestFitness (predicho)')
            ax.legend()
            ax.grid(True, alpha=0.3)
        else:
            ax.text(0.5, 0.5, 'Insuficientes datos para predicción (< 3 gens o sin convergencia)', 
                   ha='center', va='center', fontsize=12, transform=ax.transAxes)
            ax.set_xticks([])
            ax.set_yticks([])
    else:
        ax.text(0.5, 0.5, 'Datos insuficientes para predicción', 
               ha='center', va='center', fontsize=12, transform=ax.transAxes)
        ax.set_xticks([])
        ax.set_yticks([])
    
    plt.tight_layout()
    saved.append(save_fig(fig, '23_prediccion.png'))
    
    return saved

def plot_diversity_charts(debug_rows):
    """Genera gráficos de diversidad genética."""
    saved = []
    if not debug_rows or len(debug_rows) < 20:
        return saved

    bounds = infer_carindex_bounds(debug_rows)
    
    div_info = analyze_diversity(debug_rows)
    if not div_info:
        return saved
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle(f'{LABEL} - Análisis de Diversidad Genética', fontsize=14, fontweight='bold')
    
    # Panel 1: Distribución de familias (pie)
    ax = axes[0, 0]
    families = div_info['families']
    if families:
        labels = list(families.keys())
        sizes = list(families.values())
        colors = ['#ff9999', '#66b3ff', '#99ff99', '#ffcc99', '#ff99cc', '#c2c2f0']
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors[:len(labels)], startangle=90)
        ax.set_title('Distribución de Familias Genéticas')
    
    # Panel 2: Fitness por familia (box)
    ax = axes[0, 1]
    family_stats = div_info['family_stats']
    if family_stats:
        fams = list(family_stats.keys())
        means = [family_stats[f]['mean_fitness'] for f in fams]
        stds = [family_stats[f]['std_fitness'] for f in fams]
        ax.bar(range(len(fams)), means, yerr=stds, capsize=5, alpha=0.7, color='steelblue')
        ax.set_xticks(range(len(fams)))
        ax.set_xticklabels(fams, rotation=45)
        ax.axhline(y=0, color='r', linestyle='--', alpha=0.5)
        ax.set_title('Fitness Medio por Familia (+/- std)')
        ax.set_ylabel('Fitness')
        ax.grid(True, alpha=0.3, axis='y')
    
    # Panel 3: Entropía (gauge)
    ax = axes[1, 0]
    ax.axis('off')
    entropy_norm = div_info['normalized_entropy']
    text_entropy = f"Entropía Normalizada\n{entropy_norm:.2%}"
    color_entropy = 'green' if entropy_norm > 0.6 else 'orange' if entropy_norm > 0.4 else 'red'
    ax.text(0.5, 0.5, text_entropy, ha='center', va='center', fontsize=20, 
            bbox=dict(boxstyle='round', facecolor=color_entropy, alpha=0.3),
            fontweight='bold')
    
    # Panel 4: Tendencia carindex
    ax = axes[1, 1]
    gens_unique = sorted(set(r['gen'] for r in debug_rows))
    
    family_counts_by_gen = defaultdict(lambda: defaultdict(int))
    for r in debug_rows:
        gen = r['gen']
        fam = car_index_family_for_row(r, bounds=bounds)
        family_counts_by_gen[gen][fam] += 1
    
    if family_counts_by_gen:
        fams_present = sorted(set(fam for gen_dict in family_counts_by_gen.values() for fam in gen_dict.keys()))
        for fam in fams_present:
            counts = [family_counts_by_gen[g].get(fam, 0) for g in gens_unique]
            ax.plot(gens_unique, counts, marker='o', label=fam, linewidth=2, markersize=4)
        ax.set_title('Evolución de Composición Familiar')
        ax.set_xlabel(GEN_XLABEL)
        ax.set_ylabel('Conteo')
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    saved.append(save_fig(fig, '24_diversidad.png'))
    
    return saved

def plot_mutation_distributions(dbg):
    """Genera histogramas de distribuciones de mutación (siempre, aunque estén vacíos)."""
    saved = []

    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle(f'{LABEL} - Mutation distributions', fontsize=14, fontweight='bold')

    if dbg:
        mutation_rows = [r for r in dbg if not r.get('is_weight_initialization', False)]
        mut_changed = [r.get('mut_changed', 0.0) for r in mutation_rows]
        mut_rate = [r.get('mut_rate', 0.0) for r in mutation_rows]
        mut_large = [r.get('mut_large', 0.0) for r in mutation_rows]
        parent_delta = [r.get('mut_parent_delta', 0.0) for r in mutation_rows if r.get('mut_parent_fit', 0.0) != 0.0]

        def plot_hist(ax, data, title, xlabel):
            if not data:
                ax.text(0.5, 0.5, 'no data', ha='center', va='center')
                ax.set_title(title)
                return
            if _HAVE_SEABORN:
                sns.histplot(data, bins=min(40, max(10, len(data) // 10)), ax=ax, kde=True, color='steelblue')
            else:
                ax.hist(data, bins=min(40, max(10, len(data) // 10)), color='steelblue', alpha=0.75)
            ax.set_title(title)
            ax.set_xlabel(xlabel)
            ax.grid(True, alpha=0.3)

        plot_hist(axes[0, 0], mut_changed, 'MutChanged', 'count')
        plot_hist(axes[0, 1], [v * 100.0 for v in mut_rate], 'MutRate', 'percent')
        plot_hist(axes[1, 0], mut_large, 'MutNumLarge', 'count')
        plot_hist(axes[1, 1], parent_delta, 'DeltaFit vs Parent', 'fit delta')
    else:
        for ax in axes.flat:
            ax.text(0.5, 0.5, 'Sin datos', ha='center', va='center', fontsize=12, transform=ax.transAxes)
            ax.set_xticks([])
            ax.set_yticks([])

    plt.tight_layout()
    saved.append(save_fig(fig, '25_mutation_dist.png'))
    return saved

def plot_mutation_fit_scatter(dbg):
    """Genera scatter plots de mutación vs fitness (siempre, aunque estén vacíos)."""
    saved = []

    fig, axes = plt.subplots(1, 2, figsize=(15, 6))
    fig.suptitle(f'{LABEL} - Mutation vs fitness', fontsize=14, fontweight='bold')

    if dbg:
        mutation_rows = [r for r in dbg if not r.get('is_weight_initialization', False)]
        mut_rate = [r.get('mut_rate', 0.0) for r in mutation_rows]
        mut_avg = [r.get('mut_avg_mag', 0.0) for r in mutation_rows]
        fit_vals = [r.get('fit', 0.0) for r in mutation_rows]

        ax = axes[0]
        if any(mut_rate):
            if _HAVE_SEABORN:
                sns.regplot(x=mut_rate, y=fit_vals, ax=ax, scatter_kws={'s': 12, 'alpha': 0.4})
            else:
                ax.scatter(mut_rate, fit_vals, s=12, alpha=0.4, color='steelblue')
            ax.set_title('MutRate vs Fitness')
            ax.set_xlabel('mut_rate')
            ax.set_ylabel('fitness')
            ax.grid(True, alpha=0.3)
        else:
            ax.text(0.5, 0.5, 'no mut_rate data', ha='center', va='center')
            ax.set_axis_off()

        ax = axes[1]
        if any(mut_avg):
            if _HAVE_SEABORN:
                sns.regplot(x=mut_avg, y=fit_vals, ax=ax, scatter_kws={'s': 12, 'alpha': 0.4}, color='orange')
            else:
                ax.scatter(mut_avg, fit_vals, s=12, alpha=0.4, color='orange')
            ax.set_title('MutAvgMag vs Fitness')
            ax.set_xlabel('mut_avg_mag')
            ax.set_ylabel('fitness')
            ax.grid(True, alpha=0.3)
        else:
            ax.text(0.5, 0.5, 'no mut_avg_mag data', ha='center', va='center')
            ax.set_axis_off()
    else:
        for ax in axes:
            ax.text(0.5, 0.5, 'Sin datos', ha='center', va='center', fontsize=12, transform=ax.transAxes)
            ax.set_xticks([])
            ax.set_yticks([])

    plt.tight_layout()
    saved.append(save_fig(fig, '26_mutation_fit_scatter.png'))
    return saved

def plot_correlation_heatmap(dbg):
    saved = []
    if not dbg or len(dbg) < 20:
        return saved

    keys = [
        ('fit', 'fit'),
        ('net', 'net'),
        ('pen_m', 'pen_m'),
        ('pen_v', 'pen_v'),
        ('pen_tv', 'pen_tv'),
        ('pen_nav', 'pen_nav'),
        ('pen_lazy', 'pen_lazy'),
        ('pen_creep', 'pen_creep'),
        ('stop_ctx_ratio', 'stop_ctx'),
        ('thr_pos', 'thr_pos'),
        ('brake_in', 'brake_in'),
        ('mut_rate', 'mut_rate'),
        ('mut_avg_mag', 'mut_avg_mag'),
        ('mut_large_rate', 'mut_large_rate'),
        ('mut_parent_delta', 'mut_parent_delta'),
    ]

    series = []
    labels = []
    for key, label in keys:
        vals = [r.get(key, 0.0) for r in dbg]
        if stdev(vals) > 1e-12:
            series.append(vals)
            labels.append(label)

    if len(series) < 2:
        return saved

    corr = np.corrcoef(series)
    corr = np.nan_to_num(corr, nan=0.0, posinf=0.0, neginf=0.0)

    fig, ax = plt.subplots(figsize=(12, 10))
    fig.suptitle(f'{LABEL} - Correlation heatmap', fontsize=14, fontweight='bold')

    if _HAVE_SEABORN:
        sns.heatmap(corr, xticklabels=labels, yticklabels=labels, vmin=-1, vmax=1, cmap='coolwarm', ax=ax)
    else:
        im = ax.imshow(corr, vmin=-1, vmax=1, cmap='coolwarm')
        ax.set_xticks(range(len(labels)))
        ax.set_yticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.set_yticklabels(labels)
        fig.colorbar(im, ax=ax, shrink=0.8)

    plt.tight_layout()
    saved.append(save_fig(fig, '27_corr_heatmap.png'))
    return saved

def plot_mutation_family_summary(dbg):
    saved = []
    if not dbg:
        return saved

    bounds = infer_carindex_bounds(dbg)
    fam_rows = defaultdict(list)
    for r in dbg:
        if r.get('is_weight_initialization', False):
            continue
        fam_rows[car_index_family_for_row(r, bounds=bounds)].append(r)

    fams = []
    mut_rates = []
    fit_means = []
    expected_rates = []
    for fam in sorted(fam_rows.keys()):
        rows_f = fam_rows[fam]
        if not rows_f:
            continue
        fams.append(fam)
        mut_rates.append(mean([x.get('mut_rate', 0.0) for x in rows_f]) * 100.0)
        fit_means.append(mean([x.get('fit', 0.0) for x in rows_f]))
        expected_rates.append(mean([x.get('expected_mut_rate', 0.0) or 0.0 for x in rows_f]) * 100.0)

    if not fams:
        return saved

    fig, ax = plt.subplots(figsize=(12, 6))
    fig.suptitle(f'{LABEL} - Mutation by family', fontsize=14, fontweight='bold')
    ax.bar(fams, mut_rates, color='steelblue', alpha=0.8)
    ax.plot(fams, expected_rates, color='crimson', marker='D', linewidth=1.8, label='expected')
    ax.set_ylabel('mut_rate (%)')
    ax.set_xlabel('family')
    ax.grid(True, alpha=0.3, axis='y')
    ax.legend(fontsize=8, loc='upper left')

    ax2 = ax.twinx()
    ax2.plot(fams, fit_means, color='black', marker='o', linewidth=2)
    ax2.set_ylabel('fitness mean')

    plt.tight_layout()
    saved.append(save_fig(fig, '28_mutation_family.png'))
    return saved

def plot_all(summary, dbg):
    saved = []

    # Si no hay summary, aun asi intenta generar las graficas de debug.
    if not summary:
        if dbg:
            saved += plot_debug(dbg)
        return saved

    gens = [r['gen'] for r in summary]
    w = max(3, min(30, len(gens) // 5))
    pop_den = estimate_population_size(summary)

    # ── 1. Resumen 2x2 ──
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle(f'{LABEL} - Resumen ({len(summary)} gens)', fontsize=14, fontweight='bold')

    ax = axes[0][0]
    v = [r['best'] for r in summary]
    ax.plot(gens, v, 'b-', alpha=0.3, linewidth=0.7)
    if len(v) >= 10:
        ax.plot(gens, rolling(v, w), 'b-', linewidth=2, label=f'MA-{w}')
        ax.legend(fontsize=8)
    else:
        ax.plot(gens, v, 'b-o', linewidth=2)
    ax.set_title('Mejor Fitness (BestCarForWeights)'); ax.set_xlabel(GEN_XLABEL); ax.set_ylabel('BestFitness')
    ax.grid(True, alpha=0.3)

    ax = axes[0][1]
    v = [r['mean'] for r in summary]
    ax.plot(gens, v, 'g-', alpha=0.3, linewidth=0.7)
    if len(v) >= 10:
        ax.plot(gens, rolling(v, w), 'g-', linewidth=2, label=f'MA-{w}')
        ax.legend(fontsize=8)
    else:
        ax.plot(gens, v, 'g-o', linewidth=2)
    ax.axhline(y=0, color='r', linestyle='--', alpha=0.4)
    ax.set_title('Fitness Medio (Poblacion)'); ax.set_xlabel(GEN_XLABEL); ax.set_ylabel('MeanFitness')
    ax.grid(True, alpha=0.3)

    ax = axes[1][0]
    v = [r['time'] for r in summary]
    ax.plot(gens, v, 'm-', alpha=0.3, linewidth=0.7)
    if len(v) >= 10:
        ax.plot(gens, rolling(v, w), 'm-', linewidth=2, label=f'MA-{w}')
        ax.legend(fontsize=8)
    else:
        ax.plot(gens, v, 'm-o', linewidth=2)
    ax.set_title('Tiempo Medio de Vida'); ax.set_xlabel(GEN_XLABEL); ax.set_ylabel('Segundos')
    ax.grid(True, alpha=0.3)

    ax = axes[1][1]
    v = [r['pop_count'] for r in summary]
    ax.bar(gens, v, color='red', alpha=0.6, width=max(1, len(gens)/80))
    ax.set_title(f'Muertes Razon Mas Popular (/{pop_den})'); ax.set_xlabel(GEN_XLABEL); ax.set_ylabel('Count')
    ymax = max(float(pop_den) * 1.05, max(v) * 1.10 if v else 1.0)
    ax.set_ylim(0, ymax); ax.grid(True, alpha=0.3)

    plt.tight_layout()
    saved.append(save_fig(fig, '01_resumen.png'))

    # ── 2. Tendencia BestNorm + MeanNorm ──
    fig, ax = plt.subplots(figsize=(15, 6))
    bv = [r['best'] for r in summary]
    mv = [r['mean'] for r in summary]
    ax.plot(gens, bv, 'b-', alpha=0.2, linewidth=0.5)
    ax.plot(gens, mv, 'g-', alpha=0.2, linewidth=0.5)
    if len(gens) >= 10:
        ax.plot(gens, rolling(bv, w), 'b-', linewidth=2, label=f'BestFit (MA-{w})')
        ax.plot(gens, rolling(mv, w), 'g-', linewidth=2, label=f'MeanFit (MA-{w})')
    else:
        ax.plot(gens, bv, 'b-o', linewidth=2, label='BestFit')
        ax.plot(gens, mv, 'g-o', linewidth=2, label='MeanFit')
    ax.axhline(y=0, color='r', linestyle='--', alpha=0.4)
    ax.set_title(f'{LABEL} - Tendencia Fitness')
    ax.set_xlabel(GEN_XLABEL); ax.set_ylabel('Fitness')
    ax.legend(); ax.grid(True, alpha=0.3)
    saved.append(save_fig(fig, '02_tendencia.png'))

    # ── 3. Razones de muerte (summary) ──
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle(f'{LABEL} - Razones de Muerte', fontsize=13)

    bd = Counter(r['best_death'] for r in summary)
    if bd:
        labs, vals = zip(*bd.most_common())
        short = [short_death_reason(l) for l in labs]
        ax1.barh(short, vals, color='steelblue', alpha=0.8)
    ax1.set_title('Muerte del Mejor Coche'); ax1.set_xlabel('Frecuencia')
    ax1.invert_yaxis()

    pd = Counter(r['pop_death'] for r in summary)
    if pd:
        labs, vals = zip(*pd.most_common())
        short = [short_death_reason(l) for l in labs]
        ax2.barh(short, vals, color='coral', alpha=0.8)
    ax2.set_title('Muerte Mas Popular (Poblacion)'); ax2.set_xlabel('Frecuencia')
    ax2.invert_yaxis()

    plt.tight_layout()
    saved.append(save_fig(fig, '03_muertes_summary.png'))

    # ── 3b. Razones de muerte agrupadas por familia (summary) ──
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle(f'{LABEL} - Razones de Muerte (agrupadas)', fontsize=13)

    bd = Counter(r['best_death'] for r in summary)
    if bd:
        grouped = group_death_reasons(bd)
        if grouped:
            labs = [r for r, _, _ in grouped]
            vals = [c for _, c, _ in grouped]
            colors = [death_reason_color(r) for r in labs]
            short = [short_death_reason(r) for r in labs]
            ax1.barh(short, vals, color=colors, alpha=0.8)
            add_family_separators(ax1, grouped)
    ax1.set_title('Muerte del Mejor Coche'); ax1.set_xlabel('Frecuencia')
    ax1.invert_yaxis()

    pd = Counter(r['pop_death'] for r in summary)
    if pd:
        grouped = group_death_reasons(pd)
        if grouped:
            labs = [r for r, _, _ in grouped]
            vals = [c for _, c, _ in grouped]
            colors = [death_reason_color(r) for r in labs]
            short = [short_death_reason(r) for r in labs]
            ax2.barh(short, vals, color=colors, alpha=0.8)
            add_family_separators(ax2, grouped)
    ax2.set_title('Muerte Mas Popular (Poblacion)'); ax2.set_xlabel('Frecuencia')
    ax2.invert_yaxis()

    plt.tight_layout()
    saved.append(save_fig(fig, '03b_muertes_summary_grupos.png'))

    # ── Debug plots ──
    if dbg:
        saved += plot_debug(dbg)
        # Nuevos gráficos de análisis avanzado
        saved += plot_convergence_charts(summary)
        saved += plot_prediction_charts(summary)
        saved += plot_diversity_charts(dbg)
        saved += plot_mutation_distributions(dbg)
        saved += plot_mutation_fit_scatter(dbg)
        saved += plot_correlation_heatmap(dbg)
        saved += plot_mutation_family_summary(dbg)

    return saved

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
        steer_in_total = sum(r.get('steer_in', 0.0) for r in dbg_rows)
        steer_target_total = sum(r.get('steer_target', 0.0) for r in dbg_rows)
        steer_gap_total = sum(abs(r.get('steer_in', 0.0) - r.get('steer_target', 0.0)) for r in dbg_rows)
        creep_pen = sum(r.get('pen_creep', 0.0) for r in dbg_rows)
        rev_pen = sum(r.get('pen_rev', 0.0) for r in dbg_rows)
        lazy_pen = sum(r.get('pen_lazy', 0.0) for r in dbg_rows)
        steer_stop_pen = sum(r.get('pen_swstop', 0.0) for r in dbg_rows)
        nav_pen = sum(r.get('pen_nav', 0.0) for r in dbg_rows)

        brake_share_global = sdiv(cmd_brk, cmd_brk + cmd_thr)
        stop_brake_share = sdiv(stop_brk, stop_brk + stop_thr)
        stop_ctx_coverage = sdiv(stop_ticks, total_ticks)

        if stop_ctx_coverage > 0.0:
            insights.append(f'Cobertura de contexto stop/semaforo: {stop_ctx_coverage*100:.2f}% de ticks.')

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
        'missing_required': sorted(set(train_meta.get('missing_required', [])) & set(test_meta.get('missing_required', []))),
        'data_rows': train_meta.get('data_rows', 0) + test_meta.get('data_rows', 0),
        'empty_rows': train_meta.get('empty_rows', 0) + test_meta.get('empty_rows', 0),
        'short_rows': train_meta.get('short_rows', 0) + test_meta.get('short_rows', 0),
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

# ── Main ──

def main():
    # Inicializar logging y parseo de argumentos CLI
    logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
    parser = argparse.ArgumentParser(description='Analisis de logs - cognitive-car')
    parser.add_argument('--no-plots', action='store_true', help='No generar ni guardar graficas')
    parser.add_argument('--out-dir', type=str, default=None, help='Directorio de salida (sobrescribe configuracion)')
    args = parser.parse_args()

    global ENABLE_PLOTS, OUT_DIR
    if args.no_plots:
        ENABLE_PLOTS = False
    if args.out_dir:
        OUT_DIR = args.out_dir
    # No crear OUT_DIR aquí para evitar carpetas vacías; se creará cuando haya activos a guardar
    logging.info('Modo: AUTO (deteccion desde Fitness_Debug.csv)')
    logging.info('Out dir (provisional): %s', OUT_DIR)
    csvs = [TRAIN_SUMMARY_FILE, TEST_SUMMARY_FILE, DEBUG_FILE]
    for path in csvs:
        if os.path.exists(path):
            logging.info('  %s: %s bytes', path, f"{os.path.getsize(path):,}")
        else:
            logging.warning('  %s: NO ENCONTRADO', path)

    train_summary_meta = inspect_csv_layout(TRAIN_SUMMARY_FILE, SUMMARY_ALIASES, SUMMARY_REQUIRED_KEYS, min_cols=7)
    test_summary_meta = inspect_csv_layout(TEST_SUMMARY_FILE, SUMMARY_ALIASES, SUMMARY_REQUIRED_KEYS, min_cols=7)
    debug_meta_base = inspect_csv_layout(DEBUG_FILE, DEBUG_ALIASES, DEBUG_REQUIRED_KEYS, min_cols=6)

    train_summary = parse_summary(TRAIN_SUMMARY_FILE)
    test_summary = parse_summary(TEST_SUMMARY_FILE)
    debug_raw = parse_debug(DEBUG_FILE)
    combined_summary = build_combined_summary(train_summary, test_summary)

    # Validation check
    if not debug_raw and not train_summary and not test_summary:
        logging.error('FATAL: No data loaded from any source (debug_raw, train_summary, test_summary all empty)')
    elif not combined_summary:
        logging.warning('WARNING: No summary data loaded (train/test both empty), using debug data as fallback')

    detected_mode, detected_info = detect_mode_from_inputs(debug_raw, train_summary, test_summary)

    combined_summary_meta = build_combined_summary_meta(train_summary_meta, test_summary_meta)

    logging.info('\nModo detectado automaticamente: %s (%s)', detected_mode.upper(), mode_label(detected_mode))
    logging.info('Motivo deteccion: %s', detected_info.get('reason', '-'))
    if detected_info.get('has_training_flag'):
        logging.info('Split debug TRAIN/TEST/UNK: %d / %d / %d',
            detected_info.get('train_debug_rows', 0),
            detected_info.get('test_debug_rows', 0),
            detected_info.get('unknown_debug_rows', 0),
        )
    else:
        logging.info('Fitness_Debug sin columna Training/TrainingMode util; fallback por summaries.')

    debug_meta_base['loaded_rows'] = len(debug_raw)
    debug_meta_base['discarded_rows'] = max(0, debug_meta_base.get('data_rows', 0) - len(debug_raw))

    # Selecciones por fase: train, test y combinada.
    train_debug, train_debug_scope = select_debug_rows_by_mode(debug_raw, 'train')
    test_debug, test_debug_scope = select_debug_rows_by_mode(debug_raw, 'test')
    combined_debug, combined_debug_scope = select_debug_rows_by_mode(debug_raw, 'traintest')

    train_summary_meta['loaded_rows'] = len(train_summary)
    train_summary_meta['discarded_rows'] = max(0, train_summary_meta.get('data_rows', 0) - len(train_summary))
    test_summary_meta['loaded_rows'] = len(test_summary)
    test_summary_meta['discarded_rows'] = max(0, test_summary_meta.get('data_rows', 0) - len(test_summary))

    all_analyses = {
        'train': {
            'mode': 'train',
            'summary': train_summary,
            'debug': train_debug,
            'summary_meta': train_summary_meta,
            'debug_scope': train_debug_scope,
        },
        'test': {
            'mode': 'test',
            'summary': test_summary,
            'debug': test_debug,
            'summary_meta': test_summary_meta,
            'debug_scope': test_debug_scope,
        },
        'traintest': {
            'mode': 'traintest',
            'summary': combined_summary,
            'debug': combined_debug,
            'summary_meta': combined_summary_meta,
            'debug_scope': combined_debug_scope,
        },
    }

    if detected_mode in ('train', 'test'):
        analyses = [all_analyses[detected_mode]]
        logging.info('Ejecucion en modo unico: se generara solo %s.', detected_mode.upper())
    else:
        analyses = [all_analyses['train'], all_analyses['test'], all_analyses['traintest']]
        logging.info('Ejecucion combinada: se generaran TRAIN, TEST y TRAINTEST.')

    results = []
    for item in analyses:
        logging.info('\n[%s] Lanzando analisis separado...', item['mode'].upper())
        result = run_analysis_variant(
            mode=item['mode'],
            summary_rows=item['summary'],
            debug_rows=item['debug'],
            summary_meta_template=item['summary_meta'],
            debug_meta_template=debug_meta_base,
            debug_scope=item['debug_scope'],
            detected_info=detected_info,
            train_summary_rows=len(train_summary),
            test_summary_rows=len(test_summary),
            csvs=csvs,
        )
        results.append(result)

    logging.info('\n%s', '='*76)
    logging.info('  RESUMEN FINAL DE SALIDAS')
    logging.info('%s', '='*76)
    for r in results:
        logging.info('  %s | summary=%4d | debug=%5d | figs=%2d | best=%0.2f | %s',
            r['mode'], r['summary_rows'], r['debug_rows'], r['figures'], r.get('metrics', {}).get('best_max', 0.0), r['out_dir']
        )

    if SAVE_GLOBAL_SUMMARY:
        global_txt, global_json = save_master_summary(BASE_DIR, NOW, detected_info, results)
        logging.info('  Resumen global TXT:  %s', global_txt)
        logging.info('  Resumen global JSON: %s', global_json)
    else:
        logging.info('  Resumen global TXT/JSON: deshabilitado (no se guarda archivo).')
    logging.info('%s\n', '='*76)

if __name__ == '__main__':
    main()
