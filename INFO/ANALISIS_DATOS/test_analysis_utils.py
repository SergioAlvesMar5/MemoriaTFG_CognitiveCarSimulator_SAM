import math
import csv
import os
import runpy
import tempfile
import numpy as np
import analyse_current as ac
from analyse_current import (
    DEBUG_ALIASES,
    DEBUG_REQUIRED_KEYS,
    NETWORK_OUTPUT_WEIGHTS_TOTAL,
    WEIGHTS_TOTAL,
    align_debug_to_completed_summary,
    classify_test_outcome,
    collision_death_context,
    correlation_sample,
    detect_debug_schema,
    death_family_detail_for_row,
    group_debug_death_families,
    infer_label_from_debug_rows,
    inspect_csv_layout,
    lifetime_distribution_bins,
    normalize_header_token,
    metric_values,
    metric_exposure_count,
    mutation_profile_for_row,
    parse_debug,
    parse_summary,
    pctl,
    rolling,
    sdiv,
    stop_violation_subtype,
    analyze_convergence,
    predict_fitness_trajectory,
    select_test_summary_rows,
    summarize_collision_deaths,
    summarize_test_results,
    wilson_ci,
)


def test_analyse_utils_loads_with_own_imports():
    path = os.path.join(os.path.dirname(__file__), 'analyse_utils.py')
    ns = runpy.run_path(path)
    assert ns['normalize_header_token']('Acum_PenaltyVelocidad') == 'acumpenaltyvelocidad'
    assert callable(ns['detect_debug_schema'])


def test_external_ai_brief_accepts_test_without_summary():
    class DummyReport:
        def __init__(self):
            self.lines = []

        def p(self, line):
            self.lines.append(line)

    old_state = ac.MODE, ac.LABEL, ac.SUMMARY_FILE, ac.DEBUG_FILE
    try:
        ac.MODE = 'test'
        ac.LABEL = 'TEST'
        ac.SUMMARY_FILE = 'Test_Summary.csv'
        ac.DEBUG_FILE = 'Fitness_Debug.csv'

        R = DummyReport()
        ac.report_external_ai_brief(
            R,
            summary_rows=[],
            debug_rows=[],
            summary_meta={'mapped_keys': []},
            debug_meta={'mapped_keys': []},
            debug_scope={'raw_total': 0, 'selected_total': 0},
            data_coherence={
                'status': 'ok',
                'summary_rows': 0,
                'summary_gens': 0,
                'summary_gen_min': 0,
                'summary_gen_max': 0,
                'debug_rows': 0,
                'debug_gens': 0,
                'debug_gen_min': 0,
                'debug_gen_max': 0,
                'expected_debug_rows': 0,
                'warnings': [],
            },
            detected_info={'mode': 'test', 'reason': 'unit test'},
            gen_norm_info={'summary_count': 0, 'debug_count': 0},
            auto_insights=[],
        )
    finally:
        ac.MODE, ac.LABEL, ac.SUMMARY_FILE, ac.DEBUG_FILE = old_state

    text = '\n'.join(R.lines)
    assert 'No hay Summary seleccionado' in text
    assert 'MultiTestingMode desactivado' in text


def test_program_updates_0307_report_documents_semantic_changes():
    class DummyReport:
        def __init__(self):
            self.lines = []

        def p(self, line):
            self.lines.append(line)

    R = DummyReport()
    ac.report_program_updates_0307(
        R,
        [
            {
                '_schema': '2026-07-01-overlap-penalty-queue-wait',
                '_available_fields': {
                    'queue_wait_bonus',
                    'crossing_blocked_t',
                    't_stop_ctx_tl',
                    't_stop_ctx_stop',
                    't_stop_ctx_yield',
                },
                't_stop_ctx_tl': 3.0,
                't_stop_ctx_stop': 5.0,
                't_stop_ctx_yield': 7.0,
                'crossing_blocked_t': 0.4,
                'wait_bonus': 1.0,
                'pen_creep': 2.0,
                'pen_rev': 3.0,
                'pen_cw': 4.0,
            }
        ],
    )

    text = '\n'.join(R.lines)
    assert 'Novedades del Programa 03/07' in text
    assert 'FreeRun' in text
    assert 'ReleaseFadeAlpha' in text
    assert 'ventana dinamica' in text
    assert 'REVERSING_WRONG' in text


def test_build_synthetic_summary_from_debug_reconstructs_test_kpis():
    rows = [
        {'gen': 0, 'car': 'A', 'fit': 100.0, 'time': 120.0, 'death': 'TIMEFINISHED'},
        {'gen': 0, 'car': 'B', 'fit': 20.0, 'time': 5.0, 'death': 'LAZY'},
        {'gen': 0, 'car': 'C', 'fit': -10.0, 'time': 50.0, 'death': 'COLLISION_WITH_WALL'},
    ]

    summary, debug, info = ac.build_synthetic_summary_from_debug(rows, 'test', summary_meta={'data_rows': 1})

    assert info['enabled'] is True
    assert info['rows'] == 1
    assert {r['gen'] for r in debug} == {1}
    assert debug[0]['gen_debug_raw'] == 0
    assert len(summary) == 1
    row = summary[0]
    assert row['gen'] == 1
    assert row['eval_n'] == 3
    assert row['best'] == 100.0
    assert row['success_count'] == 1
    assert row['fail_count'] == 2
    assert row['fail_collision_count'] == 1
    assert abs(row['success_rate'] - (100.0 / 3.0)) < 1e-9
    assert row['synthetic_from_debug'] is True


def test_build_synthetic_summary_freerun_adds_censored_bounds():
    old_env = os.environ.get('ANALYSE_FREERUN_EXPECTED_LIVE_CARS')
    os.environ['ANALYSE_FREERUN_EXPECTED_LIVE_CARS'] = '2'
    try:
        rows = [
            {'gen': 0, 'car': 'A', 'spawn': 'BP_SpawnPoint1', 'fit': 10.0, 'time': 10.0, 'death': 'LAZY'},
            {'gen': 0, 'car': 'B', 'spawn': 'BP_SpawnPoint1', 'fit': 1000.0, 'time': 1000.0, 'death': 'TIMEFINISHED'},
        ]
        summary, debug, info = ac.build_synthetic_summary_from_debug(rows, 'test', summary_meta={'data_rows': 0})
    finally:
        if old_env is None:
            os.environ.pop('ANALYSE_FREERUN_EXPECTED_LIVE_CARS', None)
        else:
            os.environ['ANALYSE_FREERUN_EXPECTED_LIVE_CARS'] = old_env

    censoring = info['freerun_censoring']
    assert censoring['enabled'] is True
    assert censoring['censored_alive_count'] == 2
    assert len(summary) == 1
    row = summary[0]
    assert row['observed_terminal_count'] == 2
    assert row['censored_count'] == 2
    assert row['eval_n'] == 4
    assert row['success_count'] == 1
    assert row['fail_count'] == 1
    assert row['success_rate'] == 25.0
    assert row['success_rate_upper'] == 75.0
    assert debug[0]['free_run_censored_alive_count'] == 2
    assert censoring['session_elapsed_estimate_s'] == 1010.0
    assert censoring['censored_age_estimates_s'][0] == 0.0
    assert censoring['censored_age_estimates_s'][1] == 1010.0
    assert row['session_elapsed_estimate_s'] == 1010.0
    assert debug[0]['free_run_censored_age_estimates'] == [0.0, 1010.0]


def test_pctl_basic():
    vals = [0, 1, 2, 3, 4]
    assert pctl(vals, 50) == 2
    assert pctl(vals, 0) == 0
    assert pctl(vals, 100) == 4


def test_pctl_with_nan():
    vals = [0, 1, float('nan'), 3]
    # pctl should ignore NaN and return a numeric value
    v = pctl(vals, 50)
    assert isinstance(v, float)
    assert not math.isnan(v)


def test_pctl_all_nan():
    vals = [float('nan'), float('nan')]
    assert pctl(vals, 50) == 0.0


def test_sdiv():
    assert sdiv(10, 2) == 5
    assert sdiv(1, 0) == 0


def test_wilson_ci_clamps_out_of_range_counts():
    lo, hi = wilson_ci(31, 29)
    assert 0.0 <= lo <= hi <= 1.0
    assert hi == 1.0


def test_rolling_matches_trailing_window_mean():
    assert rolling([], 3) == []
    assert rolling([1, 2, 3, 4, 5], 3) == [1.0, 1.5, 2.0, 3.0, 4.0]


def test_correlation_sample_excludes_rows_without_exposure():
    rows = [
        {'fit': 10, 'round_exit2_count': 0, 'round_exit2_death_rate': 0},
        {'fit': 20, 'round_exit2_count': 2, 'round_exit2_death_rate': 0.5},
        {'fit': 30, 'round_exit2_count': 1, 'round_exit2_death_rate': 0},
    ]
    fits, rates = correlation_sample(rows, 'round_exit2_death_rate')
    assert fits == [20.0, 30.0]
    assert rates == [0.5, 0.0]


def test_metric_values_exclude_situational_zeros_without_exposure():
    rows = [
        {'round_entered_n': 0, 'round_entry_front_avg': 0.0},
        {'round_entered_n': 2, 'round_entry_front_avg': 0.75},
        {'round_entered_n': 1, 'round_entry_front_avg': 0.0},
    ]
    assert metric_values(rows, 'round_entry_front_avg') == [0.75, 0.0]
    assert metric_exposure_count(rows, 'round_entry_front_avg') == 2
    bonus_rows = [
        {'round_entered_n': 0, 'round_bonus_per_entry': 0.0},
        {'round_entered_n': 2, 'round_bonus_per_entry': -15.0},
        {'round_entered_n': 1, 'round_bonus_per_entry': 0.0},
    ]
    assert metric_values(bonus_rows, 'round_bonus_per_entry') == [-15.0, 0.0]


def test_lifetime_distribution_bins_are_relative_to_max_time():
    rows = [
        {'time': 0.0, 'car': 'C0'},
        {'time': 5.0, 'car': 'C5'},
        {'time': 50.0, 'car': 'C50'},
        {'time': 100.0, 'car': 'C100'},
    ]
    info = lifetime_distribution_bins(rows, step_pct=10)
    assert info['max_time'] == 100.0
    assert info['total'] == 4
    assert info['bins'][0]['pct_label'] == '0-9%'
    assert info['bins'][-1]['pct_label'] == '90-100%'
    assert info['bins'][0]['sec_start'] == 0.0
    assert info['bins'][0]['sec_end'] == 10.0
    assert info['bins'][5]['count'] == 1
    assert info['bins'][-1]['count'] == 1
    assert info['max_row']['car'] == 'C100'


def test_lifetime_distribution_bins_places_censored_age_estimates():
    rows = [
        {
            'time': 20.0,
            'car': 'C20',
            'free_run_censored_alive_count': 2,
            'free_run_censored_age_estimates': [5.0, 120.0],
        },
        {'time': 100.0, 'car': 'C100'},
    ]
    info = lifetime_distribution_bins(rows, step_pct=10)
    assert info['max_time'] == 120.0
    assert info['max_source'] == 'censored_estimated'
    assert info['total'] == 4
    assert info['censored_age_estimate_count'] == 2
    assert info['censored_unbinned_count'] == 0
    assert sum(b['count'] for b in info['bins']) == 2
    assert sum(b['censored_count'] for b in info['bins']) == 2
    assert info['bins'][0]['censored_count'] == 1
    assert info['bins'][-1]['censored_count'] == 1


def test_infer_label_from_debug_rows_prefers_phase_flags():
    assert infer_label_from_debug_rows([{'training': False}], fallback='AUTO') == 'TEST'
    assert infer_label_from_debug_rows([{'training': True}], fallback='AUTO') == 'ENTRENAMIENTO'
    assert infer_label_from_debug_rows([{'training': True}, {'training': False}], fallback='AUTO') == 'TRAIN+TEST'


def test_convergence_uses_every_summary_row():
    rows = [
        {'gen': 1, 'best': 10.0, 'mean': 7.0},
        {'gen': 2, 'best': 12.0, 'mean': 8.0},
        {'gen': 3, 'best': 15.0, 'mean': 9.0},
    ]
    stats = analyze_convergence(rows)
    assert stats is not None
    assert stats['avg_variance'] == (3.0 + 4.0 + 6.0) / 3.0


def test_predict_fitness_linear():
    # create synthetic summary with increasing best values
    rows = [{'gen': i+1, 'best': float(10 + i*2), 'mean': 0, 'time': 0} for i in range(10)]
    preds = predict_fitness_trajectory(rows, future_gens=3)
    assert preds is not None
    assert 'predictions' in preds
    assert len(preds['predictions']) == 3
    assert all('predicted_fitness' in p for p in preds['predictions'])


def test_select_test_rows_from_traintest():
    rows = [
        {'source_phase': 'train', 'success_rate': 99},
        {'source_phase': 'test', 'success_rate': 25},
    ]
    selected = select_test_summary_rows(rows)
    assert len(selected) == 1
    assert selected[0]['success_rate'] == 25


def test_test_results_use_weighted_success_rate():
    rows = [
        {'gen': 1, 'success_count': 1, 'fail_count': 1, 'eval_n': 2, 'success_rate': 50,
         'best': 10, 'mean': 5, 'time': 2},
        {'gen': 2, 'success_count': 9, 'fail_count': 1, 'eval_n': 10, 'success_rate': 90,
         'best': 20, 'mean': 15, 'time': 4},
    ]
    stats = summarize_test_results(rows)
    assert stats is not None
    assert stats['total_n'] == 12
    assert abs(stats['success_rate'] - (10 / 12 * 100)) < 1e-9
    assert stats['success_median'] == 70


def test_summary_parser_handles_accented_headers_by_alias():
    assert normalize_header_token('Raz\u00f3n_Muerte M\u00e1s Popular') == 'razonmuertemaspopular'

    header = [
        'N', 'Fracaso', 'Exito', 'FailRate', 'SuccessRate',
        'Generaci\u00f3n', 'MejorFitnessNorm', 'FitnessMedio', 'TiempoMedio',
        'Raz\u00f3nMuerteMejorCoche', 'Raz\u00f3nMuerteM\u00e1sPopular',
        'MuertosPorRaz\u00f3nM\u00e1sPopular',
    ]
    values = [
        54, 40, 14, 74.074074, 25.925926,
        7, 76098.49, 30662.61, 49.98,
        'TIMEFINISHED', 'TIMEFINISHED', 14,
    ]
    path = ''
    try:
        with tempfile.NamedTemporaryFile('w', newline='', suffix='.csv', delete=False, encoding='utf-8') as tmp:
            writer = csv.writer(tmp)
            writer.writerow(header)
            writer.writerow(values)
            path = tmp.name
        rows = parse_summary(path)
    finally:
        if path and os.path.exists(path):
            os.unlink(path)

    assert len(rows) == 1
    assert rows[0]['gen'] == 7
    assert rows[0]['best'] == 76098.49
    assert rows[0]['pop_count'] == 14
    assert rows[0]['success_count'] == 14
    assert rows[0]['fail_count'] == 40
    assert rows[0]['eval_n'] == 54


def test_new_debug_schema_does_not_shift_removed_components():
    header = [
        'Generacion', 'CarID', 'Fitness_Final', 'Tiempo_Vivo', 'SpawnID', 'Razon_Muerte',
        'Penalty_Muerte', 'Acum_PenaltyVelocidad', 'Acum_A', 'Acum_F',
        'Acum_WaitBonus', 'Acum_NetNormal', 'Acum_PenaltyCorrectingWrong',
        'Acum_PenaltyTrafficViolation', 'Ticks_Normal', 'Ticks_Total', 'TrainingMode',
        'MutNumChanged', 'Acum_StopCompletionBonus', 'Acum_YieldCompletionBonus',
        'Acum_NavPenalty', 'NumRoundaboutsEntered', 'NumRoundaboutsCompleted',
        'Acum_SpeedAtRoundaboutEntry', 'Acum_FrontObstAtRoundaboutEntry',
        'Ticks_InRoundabout', 'Acum_SteeringInRoundabout',
        'Acum_ThrottleInRoundabout', 'CollisionsInRoundabout',
        'R_CurrentExitNumber', 'R_EntryDir_First', 'R_EntryDir_Second', 'R_EntryDir_Third',
        'R_Exit1_Count', 'R_Exit2_Count', 'R_Exit3Plus_Count',
        'R_Exit1_Deaths', 'R_Exit2_Deaths', 'R_Exit3Plus_Deaths',
        'R_Exit1_Steering', 'R_Exit2_Steering', 'R_Exit3Plus_Steering',
        'R_Exit1_Ticks', 'R_Exit2_Ticks', 'R_Exit3Plus_Ticks',
        'R_Exit1_Throttle', 'R_Exit2_Throttle', 'R_Exit3Plus_Throttle',
        'Acum_RoundaboutBonus', 'Acum_RndCompletionBonus',
        'Acum_RndEntryPenalty', 'Acum_RndThrottlePenalty',
    ]
    values = [
        1, 'Car1', 30000, 60.5, 'Spawn1', 'TIMEFINISHED',
        10, 20, 111, 222, 3, 336, 4, 5, 100, 110, 'false',
        35, 7, 8, 9, 3, 2, 1500, 1.8, 40, 12, 20, 1,
        2, 2, 1, 0, 3, 2, 1, 1, 1, 0, 10, 8, 6, 20, 10, 5, 12, 4, -1,
        123.5, 200.0, 50.0, 26.5,
    ]
    path = ''
    try:
        with tempfile.NamedTemporaryFile('w', newline='', suffix='.csv', delete=False, encoding='utf-8') as tmp:
            writer = csv.writer(tmp)
            writer.writerow(header)
            writer.writerow(values)
            path = tmp.name
        rows = parse_debug(path)
    finally:
        if path and os.path.exists(path):
            os.unlink(path)

    assert len(rows) == 1
    assert rows[0]['a'] == 111
    assert rows[0]['f'] == 222
    assert rows[0]['time'] == 60.5
    assert rows[0]['b'] == 0
    assert 'b' not in rows[0]['_available_fields']
    assert rows[0]['mut_rate'] == 35 / WEIGHTS_TOTAL
    assert rows[0]['_schema'] == '2026-06-roundabout-bonus-breakdown'
    assert rows[0]['round_completion_rate'] == 2 / 3
    assert rows[0]['round_collision_rate'] == 1 / 3
    assert rows[0]['round_entry_speed_avg'] == 500
    assert rows[0]['round_entry_front_avg'] == 0.6
    assert rows[0]['round_bonus'] == 123.5
    assert rows[0]['round_bonus_per_entry'] == 123.5 / 3
    assert rows[0]['round_bonus_per_completion'] == 123.5 / 2
    assert rows[0]['round_bonus_per_tick'] == 123.5 / 40
    assert rows[0]['round_completion_bonus'] == 200
    assert rows[0]['round_entry_penalty'] == 50
    assert rows[0]['round_throttle_penalty'] == 26.5
    assert rows[0]['round_completion_bonus_per_completion'] == 100
    assert rows[0]['round_entry_penalty_per_entry'] == 50 / 3
    assert rows[0]['round_throttle_penalty_per_tick'] == 26.5 / 40
    assert rows[0]['round_steer_avg'] == 0.3
    assert rows[0]['round_throttle_avg'] == 0.5
    assert rows[0]['round_tick_ratio'] == 40 / 110
    assert rows[0]['round_dir_first_share'] == 2 / 3
    assert rows[0]['round_dir_second_share'] == 1 / 3
    assert rows[0]['round_exit1_death_rate'] == 1 / 3
    assert rows[0]['round_exit2_death_rate'] == 1 / 2
    assert rows[0]['round_exit3_death_rate'] == 0
    assert rows[0]['round_exit1_steer_avg'] == 0.5
    assert rows[0]['round_exit2_steer_avg'] == 0.8
    assert rows[0]['round_exit3_throttle_avg'] == -0.2


def test_debug_parser_supports_alignment_penalty_23_06():
    header = [
        'Generacion', 'CarID', 'Fitness_Final', 'Tiempo_Vivo', 'SpawnID', 'Razon_Muerte',
        'Acum_AlignmentPenalty',
    ]
    values = [1, 'Car1', 100, 12, 'Spawn1', 'TIMEFINISHED', 77.5]
    path = ''
    try:
        with tempfile.NamedTemporaryFile('w', newline='', suffix='.csv', delete=False, encoding='utf-8') as tmp:
            writer = csv.writer(tmp)
            writer.writerow(header)
            writer.writerow(values)
            path = tmp.name
        rows = parse_debug(path)
    finally:
        if path and os.path.exists(path):
            os.unlink(path)

    assert len(rows) == 1
    assert rows[0]['pen_align'] == 77.5
    assert 'pen_align' in rows[0]['_available_fields']
    assert rows[0]['_schema'] == '2026-06-alignment-penalty'


def test_debug_parser_supports_car_overlaps_26_06():
    header = [
        'Generacion', 'CarID', 'Fitness_Final', 'Tiempo_Vivo', 'SpawnID', 'Razon_Muerte',
        'Ticks_Total', 'Acum_AlignmentPenalty', 'NumCarOverlaps',
    ]
    values = [1, 'Car1', 100, 20, 'Spawn1', 'TIMEFINISHED', 200, 1.5, 4]
    path = ''
    try:
        with tempfile.NamedTemporaryFile('w', newline='', suffix='.csv', delete=False, encoding='utf-8') as tmp:
            writer = csv.writer(tmp)
            writer.writerow(header)
            writer.writerow(values)
            path = tmp.name
        rows = parse_debug(path)
    finally:
        if path and os.path.exists(path):
            os.unlink(path)

    assert len(rows) == 1
    assert rows[0]['car_overlaps'] == 4
    assert rows[0]['car_overlap_per_sec'] == 4 / 20
    assert rows[0]['car_overlap_per_tick'] == 4 / 200
    assert 'car_overlaps' in rows[0]['_available_fields']
    assert rows[0]['_schema'] == '2026-06-car-overlap-alignment'


def test_debug_schema_detects_full_car_overlap_26_06():
    keys = {
        'car_overlaps',
        'pen_align',
        'round_completion_bonus',
        'round_entry_penalty',
        'round_throttle_penalty',
    }
    assert detect_debug_schema(keys) == '2026-06-car-overlap-alignment-roundabout-bonus-breakdown'


def test_debug_parser_supports_yield_crossing_diagnostics_30_06():
    header = [
        'Generacion', 'CarID', 'Fitness_Final', 'Tiempo_Vivo', 'SpawnID', 'Razon_Muerte',
        'Ticks_Total', 'Ticks_StopContext', 'NumYieldsCompleted', 'NumCarOverlaps',
        'NumYieldFreePasses', 'SpeedAtYieldValidation', 'Acum_TimeBlockedAtCrossing',
        'FrontObstAtDeath', 'Acum_SteerApproachWrongDir', 'Acum_SteerApproachRightDir',
        'Acum_CarOverlapPenaltyShadow', 'FirstSteerAfterReleaseTicks',
    ]
    values = [
        1, 'Car1', 100, 20, 'Spawn1', 'STOP_VIOLATION_TIMEOUT',
        200, 9.0, 2, 4,
        1, 263.5, 0.9,
        0.12, 3.0, 1.0,
        50.0, 14,
    ]
    path = ''
    try:
        with tempfile.NamedTemporaryFile('w', newline='', suffix='.csv', delete=False, encoding='utf-8') as tmp:
            writer = csv.writer(tmp)
            writer.writerow(header)
            writer.writerow(values)
            path = tmp.name
        rows = parse_debug(path)
    finally:
        if path and os.path.exists(path):
            os.unlink(path)

    assert len(rows) == 1
    row = rows[0]
    assert row['_schema'] == '2026-06-30-yield-crossing-overlap-diagnostics'
    assert row['death_canon'] == 'STOP_VIOLATION'
    assert row['death_family_detail'] == 'STOP_VIOLATION_TIMEOUT'
    assert stop_violation_subtype(row['death']) == 'TIMEOUT'
    assert classify_test_outcome(row) == 'fail_death'
    assert row['yield_free_passes'] == 1
    assert row['yield_validation_seen'] == 1.0
    assert row['crossing_blocked_per_stop_tick'] == 0.1
    assert row['crossing_blocked_per_life_sec'] == 0.045
    assert row['car_overlap_shadow_per_overlap'] == 12.5
    assert row['steer_app_wrong_share'] == 0.75
    assert row['first_steer_release_seen'] == 1.0
    assert metric_values(rows, 'yield_validation_speed') == [263.5]


def test_debug_parser_supports_overlap_penalty_and_queue_wait_01_07():
    header = [
        'Generacion', 'CarID', 'Fitness_Final', 'Tiempo_Vivo', 'SpawnID', 'Razon_Muerte',
        'Acum_PenaltyVelocidad', 'Ticks_Total', 'NumCarOverlaps', 'Acum_CarOverlapPenaltyShadow',
        'Acum_CarOverlapPenalty', 'Acum_QueueWaitBonus',
    ]
    values = [
        [1, 'Car1', 100, 20, 'Spawn1', 'COLLISION', 10.0, 200, 4, 50.0, 12.0, 6.0],
        [1, 'Car2', 80, 10, 'Spawn1', 'TIMEFINISHED', 0.0, 100, 0, 0.0, 0.0, 0.0],
    ]
    path = ''
    try:
        with tempfile.NamedTemporaryFile('w', newline='', suffix='.csv', delete=False, encoding='utf-8') as tmp:
            writer = csv.writer(tmp)
            writer.writerow(header)
            writer.writerows(values)
            path = tmp.name
        rows = parse_debug(path)
    finally:
        if path and os.path.exists(path):
            os.unlink(path)

    assert detect_debug_schema(['car_overlap_penalty', 'queue_wait_bonus']) == '2026-07-01-overlap-penalty-queue-wait'
    assert len(rows) == 2
    row = rows[0]
    assert row['_schema'] == '2026-07-01-overlap-penalty-queue-wait'
    assert row['car_overlap_penalty'] == 12.0
    assert row['queue_wait_bonus'] == 6.0
    assert row['car_overlap_penalty_per_overlap'] == 3.0
    assert row['pen_v_per_life_sec'] == 0.5
    assert row['queue_wait_bonus_per_life_sec'] == 0.3
    assert row['queue_wait_bonus_fit_share'] == 6.0
    assert metric_values(rows, 'car_overlap_penalty_per_overlap') == [3.0]
    assert metric_exposure_count(rows, 'car_overlap_penalty_per_overlap') == 1
    assert metric_values(rows, 'pen_v_per_life_sec') == [0.5]
    assert metric_exposure_count(rows, 'pen_v_per_life_sec') == 1
    assert metric_values(rows, 'queue_wait_bonus_per_life_sec') == [0.3]
    assert metric_exposure_count(rows, 'queue_wait_bonus_per_life_sec') == 1


def test_csv_layout_reports_duplicate_mapped_headers():
    header = [
        'Generacion', 'CarID', 'Fitness_Final', 'Tiempo_Vivo', 'SpawnID', 'Razon_Muerte',
        'Acum_SteerApproachPenalty', 'Acum_SteerApproachPenalty',
    ]
    values = [1, 'Car1', 100, 12, 'Spawn1', 'TIMEFINISHED', 3.0, 4.0]
    path = ''
    try:
        with tempfile.NamedTemporaryFile('w', newline='', suffix='.csv', delete=False, encoding='utf-8') as tmp:
            writer = csv.writer(tmp)
            writer.writerow(header)
            writer.writerow(values)
            path = tmp.name
        meta = inspect_csv_layout(path, DEBUG_ALIASES, DEBUG_REQUIRED_KEYS, min_cols=6)
    finally:
        if path and os.path.exists(path):
            os.unlink(path)

    assert meta['duplicate_headers'] == ['Acum_SteerApproachPenalty x2']
    assert meta['duplicate_mapped_keys'] == ['pen_steer_app: Acum_SteerApproachPenalty, Acum_SteerApproachPenalty']
    assert meta['long_rows'] == 0


def test_collision_deaths_split_roundabout_vs_normal():
    header = [
        'Generacion', 'CarID', 'Fitness_Final', 'Tiempo_Vivo', 'SpawnID', 'Razon_Muerte',
        'CollisionsInRoundabout',
    ]
    values = [
        [1, 'CarRound', 100, 12, 'Spawn1', 'COLLISION_WITH_BP_IntersectionBorder139', 1],
        [1, 'CarNormal', 90, 10, 'Spawn2', 'COLLISION_WITH_NavModifierVolume35', 0],
        [1, 'CarStop', 80, 9, 'Spawn3', 'STOP_VIOLATION', 0],
    ]
    path = ''
    try:
        with tempfile.NamedTemporaryFile('w', newline='', suffix='.csv', delete=False, encoding='utf-8') as tmp:
            writer = csv.writer(tmp)
            writer.writerow(header)
            writer.writerows(values)
            path = tmp.name
        rows = parse_debug(path)
    finally:
        if path and os.path.exists(path):
            os.unlink(path)

    by_car = {r['car']: r for r in rows}
    assert collision_death_context(by_car['CarRound']) == 'COLLISION_ROUNDABOUT'
    assert death_family_detail_for_row(by_car['CarRound']) == 'COLLISION_ROUNDABOUT'
    assert collision_death_context(by_car['CarNormal']) == 'COLLISION_NORMAL'
    assert death_family_detail_for_row(by_car['CarNormal']) == 'COLLISION_NORMAL'
    assert collision_death_context(by_car['CarStop']) == 'NO_COLLISION'

    stats = summarize_collision_deaths(rows)
    assert stats['total'] == 2
    assert stats['roundabout'] == 1
    assert stats['normal'] == 1
    grouped = group_debug_death_families(rows)
    assert grouped[:3] == [
        ('COLLISION_ROUNDABOUT', 1, 'COLLISION_ROUNDABOUT'),
        ('COLLISION_NORMAL', 1, 'COLLISION_NORMAL'),
        ('VIOLATION', 1, 'VIOLATION'),
    ]


def test_current_network_weight_count_and_test_rules():
    assert WEIGHTS_TOTAL == 352
    assert classify_test_outcome({'death': 'TIMEFINISHED', 'time': 60, 'fit': 30000}) == 'success'
    assert classify_test_outcome({'death': 'TIMEFINISHED', 'time': 59, 'fit': 30000}) == 'fail_time'
    assert classify_test_outcome({'death': 'STOP_VIOLATION', 'time': 60, 'fit': 30000}) == 'fail_death'
    assert classify_test_outcome({'death': 'STOP_VIOLATION_EXIT', 'time': 60, 'fit': 30000}) == 'fail_death'
    assert classify_test_outcome({'death': 'STOP_VIOLATION_TIMEOUT', 'time': 60, 'fit': 30000}) == 'fail_death'
    assert classify_test_outcome(
        {'death': 'TIMEFINISHED', 'time': 60, 'fit': 20000},
        use_fitness=True,
    ) == 'fail_fitness'


def test_incomplete_debug_generations_are_excluded():
    summary = [{'gen': 1}, {'gen': 2}, {'gen': 3}]
    debug = [{'gen': 1}, {'gen': 2}, {'gen': 3}, {'gen': 4}, {'gen': 4}]
    selected, info = align_debug_to_completed_summary(summary, debug, 'test')
    assert [row['gen'] for row in selected] == [1, 2, 3]
    assert info['excluded_rows'] == 2
    assert info['excluded_generations'] == [4]


def test_evolution_manager_mutation_profiles():
    bounds = {'mut_loaded_end': 25, 'mut_session_end': 48}

    initial = mutation_profile_for_row(
        {'gen': 1, 'car_index': 10, 'mut_changed': WEIGHTS_TOTAL, 'mut_parent_fit': 0},
        bounds=bounds,
    )
    assert initial['kind'] == 'INITIAL_RANDOM'
    assert initial['is_initialization'] is True
    assert initial['expected_rate'] is None

    seed = mutation_profile_for_row(
        {'gen': 2, 'car_index': 1, 'mut_changed': 0, 'mut_parent_fit': 100},
        bounds=bounds,
    )
    mutated = mutation_profile_for_row(
        {'gen': 2, 'car_index': 3, 'mut_changed': 11, 'mut_parent_fit': 100},
        bounds=bounds,
    )
    large_mutation_family = mutation_profile_for_row(
        {'gen': 2, 'car_index': 49, 'mut_changed': 21, 'mut_parent_fit': 100},
        bounds=bounds,
    )
    assert seed['expected_rate'] == 0
    assert mutated['expected_rate'] is None
    assert mutated['expected_min'] == 1 / WEIGHTS_TOTAL
    assert mutated['expected_max'] == 32 / WEIGHTS_TOTAL
    assert large_mutation_family['kind'] == 'MUT_LOADED_LARGE'
    assert large_mutation_family['expected_rate'] is None
    assert large_mutation_family['expected_min'] == 33 / WEIGHTS_TOTAL
    assert large_mutation_family['expected_max'] == (NETWORK_OUTPUT_WEIGHTS_TOTAL * 2) / WEIGHTS_TOTAL


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith('test_') and callable(fn):
            fn()
    print("All tests passed!")
