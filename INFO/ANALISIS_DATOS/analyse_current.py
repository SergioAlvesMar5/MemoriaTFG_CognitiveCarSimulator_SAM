#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Analisis completo de entrenamiento/testing para cognitive-car.
Genera informe de texto + graficas en una carpeta con fecha.
"""
import os, shutil, csv, sys
import json, math, copy, re
import unicodedata
from datetime import datetime
from collections import defaultdict, Counter
from functools import lru_cache
from typing import Any, Callable, TYPE_CHECKING

import numpy as np
import argparse
import logging
_CLI_NO_PLOTS = __name__ == '__main__' and '--no-plots' in sys.argv
if not _CLI_NO_PLOTS:
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    try:
        import seaborn as sns  # pyright: ignore[reportMissingModuleSource]
        _HAVE_SEABORN = True
    except Exception:
        sns = None
        _HAVE_SEABORN = False
else:
    matplotlib = None
    plt = None
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
NETWORK_OUTPUT_WEIGHTS_TOTAL = max(1, NETWORK_HIDDEN_COUNT * NETWORK_OUTPUT_COUNT)
TEST_MIN_TIME = float(os.environ.get('ANALYSE_TEST_MIN_TIME', '60'))
TEST_MIN_FITNESS = float(os.environ.get('ANALYSE_TEST_MIN_FITNESS', '25000'))
TEST_USE_FITNESS = str(
    os.environ.get('ANALYSE_TEST_USE_FITNESS', 'false')
).strip().lower() in ('1', 'true', 'yes', 'on')
MUTATION_RATE_DYNAMIC_MIN = float(os.environ.get('ANALYSE_MUTATION_RATE_MIN', str(1.0 / max(WEIGHTS_TOTAL, 1))))
MUTATION_RATE_DYNAMIC_MAX = float(os.environ.get(
    'ANALYSE_MUTATION_RATE_MAX',
    str(NETWORK_OUTPUT_WEIGHTS_TOTAL / max(WEIGHTS_TOTAL, 1)),
))
MUTATION_RATE_LARGE_MIN = float(os.environ.get(
    'ANALYSE_MUTATION_LARGE_MIN',
    str((NETWORK_OUTPUT_WEIGHTS_TOTAL + 1.0) / max(WEIGHTS_TOTAL, 1)),
))
MUTATION_RATE_LARGE_MAX = float(os.environ.get(
    'ANALYSE_MUTATION_LARGE_MAX',
    str((NETWORK_OUTPUT_WEIGHTS_TOTAL * 2.0) / max(WEIGHTS_TOTAL, 1)),
))
MUTATION_TOP_SPAWNS = max(5, int(os.environ.get('ANALYSE_MUTATION_TOP_SPAWNS', '15')))
MUTATION_TOP_GENS = max(10, int(os.environ.get('ANALYSE_MUTATION_TOP_GENS', '20')))
CARINDEX_MUT_LOADED_END = max(3, int(os.environ.get('ANALYSE_CARINDEX_MUT_LOADED_END', '20')))
CARINDEX_MUT_SESSION_END = max(
    CARINDEX_MUT_LOADED_END + 1,
    int(os.environ.get('ANALYSE_CARINDEX_MUT_SESSION_END', os.environ.get('ANALYSE_CARINDEX_MUT_BEST_END', '38')))
)

# Control de graficas (permitir deshabilitar desde CLI)
ENABLE_PLOTS = not _CLI_NO_PLOTS

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
    'debugacumsteerapproachpenalty': 'pen_steer_app',
    'acumpenaltysteerapproach': 'pen_steer_app',
    'acumalignmentpenalty': 'pen_align',
    'debugacumalignmentpenalty': 'pen_align',
    'acumpenaltyalignment': 'pen_align',
    'alignmentpenalty': 'pen_align',
    'numcaroverlaps': 'car_overlaps',
    'debugnumcaroverlaps': 'car_overlaps',
    'caroverlaps': 'car_overlaps',
    # diagnosticos 30-06-2026
    'numyieldfreepasses': 'yield_free_passes',
    'debugnumyieldfreepasses': 'yield_free_passes',
    'yieldfreepasses': 'yield_free_passes',
    'speedatyieldvalidation': 'yield_validation_speed',
    'debugspeedatyieldvalidation': 'yield_validation_speed',
    'acumtimeblockedatcrossing': 'crossing_blocked_t',
    'debugacumtimeblockedatcrossing': 'crossing_blocked_t',
    'timeblockedatcrossing': 'crossing_blocked_t',
    'frontobstatdeath': 'front_obst_death',
    'debugfrontobstatdeath': 'front_obst_death',
    'acumsteerapproachwrongdir': 'steer_app_wrong',
    'debugacumsteerapproachwrongdir': 'steer_app_wrong',
    'acumsteerapproachrightdir': 'steer_app_right',
    'debugacumsteerapproachrightdir': 'steer_app_right',
    'acumcaroverlappenaltyshadow': 'car_overlap_pen_shadow',
    'debugacumcaroverlappenaltyshadow': 'car_overlap_pen_shadow',
    'caroverlappenaltyshadow': 'car_overlap_pen_shadow',
    'firststeerafterreleaseticks': 'first_steer_release_ticks',
    'debugfirststeerafterreleaseticks': 'first_steer_release_ticks',
    'firststeerafterreleaseticksaicontroller': 'first_steer_release_ticks',
    'debugfirststeerafterreleaseticksaicontroller': 'first_steer_release_ticks',
    # metricas reales aplicadas al fitness (01-07-2026)
    'acumcaroverlappenalty': 'car_overlap_penalty',
    'debugacumcaroverlappenalty': 'car_overlap_penalty',
    'caroverlappenalty': 'car_overlap_penalty',
    'acumqueuewaitbonus': 'queue_wait_bonus',
    'debugacumqueuewaitbonus': 'queue_wait_bonus',
    'queuewaitbonus': 'queue_wait_bonus',
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
    # roundabout metrics (11-06-2026+)
    'numroundaboutsentered': 'round_entered_n',
    'debugnumroundaboutsentered': 'round_entered_n',
    'numroundaboutscompleted': 'round_completed_n',
    'debugnumroundaboutscompleted': 'round_completed_n',
    'acumspeedatroundaboutentry': 'round_entry_speed',
    'debugacumspeedatroundaboutentry': 'round_entry_speed',
    'acumfrontobstatroundaboutentry': 'round_entry_front',
    'debugacumfrontobstatroundaboutentry': 'round_entry_front',
    'ticksinroundabout': 'round_ticks',
    'debugticksinroundabout': 'round_ticks',
    'acumsteeringinroundabout': 'round_steer',
    'debugacumsteeringinroundabout': 'round_steer',
    'acumthrottleinroundabout': 'round_throttle',
    'debugacumthrottleinroundabout': 'round_throttle',
    'collisionsinroundabout': 'round_collisions',
    'debugcollisionsinroundabout': 'round_collisions',
    'acumroundaboutbonus': 'round_bonus',
    'debugacumroundaboutbonus': 'round_bonus',
    'roundaboutbonus': 'round_bonus',
    'acumrndcompletionbonus': 'round_completion_bonus',
    'debugacumrndcompletionbonus': 'round_completion_bonus',
    'rndcompletionbonus': 'round_completion_bonus',
    'roundaboutcompletionbonus': 'round_completion_bonus',
    'acumrndentrypenalty': 'round_entry_penalty',
    'debugacumrndentrypenalty': 'round_entry_penalty',
    'rndentrypenalty': 'round_entry_penalty',
    'roundaboutentrypenalty': 'round_entry_penalty',
    'acumrndthrottlepenalty': 'round_throttle_penalty',
    'debugacumrndthrottlepenalty': 'round_throttle_penalty',
    'rndthrottlepenalty': 'round_throttle_penalty',
    'roundaboutthrottlepenalty': 'round_throttle_penalty',
    # roundabout exit diagnostics (12-06-2026+)
    'rcurrentexitnumber': 'round_current_exit',
    'debugrcurrentexitnumber': 'round_current_exit',
    'rentrydirfirst': 'round_dir_first',
    'debugrentrydirfirst': 'round_dir_first',
    'rentrydirsecond': 'round_dir_second',
    'debugrentrydirsecond': 'round_dir_second',
    'rentrydirthird': 'round_dir_third',
    'debugrentrydirthird': 'round_dir_third',
    'rexit1count': 'round_exit1_count',
    'debugrexit1count': 'round_exit1_count',
    'rexit2count': 'round_exit2_count',
    'debugrexit2count': 'round_exit2_count',
    'rexit3pluscount': 'round_exit3_count',
    'debugrexit3pluscount': 'round_exit3_count',
    'rexit1deaths': 'round_exit1_deaths',
    'debugrexit1deaths': 'round_exit1_deaths',
    'rexit2deaths': 'round_exit2_deaths',
    'debugrexit2deaths': 'round_exit2_deaths',
    'rexit3plusdeaths': 'round_exit3_deaths',
    'debugrexit3plusdeaths': 'round_exit3_deaths',
    'rexit1steering': 'round_exit1_steer',
    'debugrexit1steering': 'round_exit1_steer',
    'rexit2steering': 'round_exit2_steer',
    'debugrexit2steering': 'round_exit2_steer',
    'rexit3plussteering': 'round_exit3_steer',
    'debugrexit3plussteering': 'round_exit3_steer',
    'rexit1ticks': 'round_exit1_ticks',
    'debugrexit1ticks': 'round_exit1_ticks',
    'rexit2ticks': 'round_exit2_ticks',
    'debugrexit2ticks': 'round_exit2_ticks',
    'rexit3plusticks': 'round_exit3_ticks',
    'debugrexit3plusticks': 'round_exit3_ticks',
    'rexit1throttle': 'round_exit1_throttle',
    'debugrexit1throttle': 'round_exit1_throttle',
    'rexit2throttle': 'round_exit2_throttle',
    'debugrexit2throttle': 'round_exit2_throttle',
    'rexit3plusthrottle': 'round_exit3_throttle',
    'debugrexit3plusthrottle': 'round_exit3_throttle',
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

# ?? Carga modular ??

if TYPE_CHECKING:
    # Estos nombres se inyectan en runtime mediante _load_analysis_parts().
    # Las anotaciones evitan falsos positivos de Pylance/Pyright sin duplicar
    # imports reales ni cambiar el namespace compartido del analizador.
    align_debug_to_completed_summary: Callable[..., Any]
    analyze_convergence: Callable[..., Any]
    build_combined_summary: Callable[..., Any]
    build_combined_summary_meta: Callable[..., Any]
    classify_test_outcome: Callable[..., Any]
    collision_death_context: Callable[..., Any]
    correlation_sample: Callable[..., Any]
    death_family_detail_for_row: Callable[..., Any]
    detect_debug_schema: Callable[..., Any]
    detect_mode_from_inputs: Callable[..., Any]
    group_debug_death_families: Callable[..., Any]
    infer_label_from_debug_rows: Callable[..., Any]
    inspect_csv_layout: Callable[..., Any]
    lifetime_distribution_bins: Callable[..., Any]
    metric_exposure_count: Callable[..., Any]
    metric_values: Callable[..., Any]
    mode_label: Callable[..., Any]
    mutation_profile_for_row: Callable[..., Any]
    normalize_header_token: Callable[..., Any]
    parse_debug: Callable[..., Any]
    parse_summary: Callable[..., Any]
    pctl: Callable[..., Any]
    predict_fitness_trajectory: Callable[..., Any]
    rolling: Callable[..., Any]
    run_analysis_variant: Callable[..., Any]
    save_master_summary: Callable[..., Any]
    select_debug_rows_by_mode: Callable[..., Any]
    select_test_summary_rows: Callable[..., Any]
    stop_violation_subtype: Callable[..., Any]
    summarize_collision_deaths: Callable[..., Any]
    summarize_test_results: Callable[..., Any]

_ANALYSE_PARTS = (
    # Utilidades base, normalizacion de razones, familias, metricas situacionales.
    'analyse_utils.py',
    # Convergencia, diversidad, prediccion y resumen de resultados de test.
    'analyse_advanced.py',
    # Lectura de Summary/Fitness_Debug y derivadas por coche.
    'analyse_parsers.py',
    # Informe de texto, resumen ejecutivo, comparativas y JSON opcional.
    'analyse_reports.py',
    # Todas las graficas.
    'analyse_plots.py',
    # Orquestacion: seleccion de modo, insights, guardado y ejecucion por variante.
    'analyse_pipeline.py',
)

def _load_analysis_parts():
    """Carga las fases del analizador manteniendo la API publica antigua."""
    for filename in _ANALYSE_PARTS:
        part_path = os.path.join(BASE_DIR, filename)
        with open(part_path, encoding='utf-8') as fh:
            code = compile(fh.read(), part_path, 'exec')
        exec(code, globals())

_load_analysis_parts()

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
        logging.warning('WARNING: No summary data loaded (train/test both empty); se reconstruira desde Fitness_Debug si hay datos')

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
