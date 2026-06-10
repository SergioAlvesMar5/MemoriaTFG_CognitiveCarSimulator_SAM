import math
import csv
import os
import tempfile
import numpy as np
from analyse_current import (
    WEIGHTS_TOTAL,
    align_debug_to_completed_summary,
    classify_test_outcome,
    mutation_profile_for_row,
    parse_debug,
    pctl,
    rolling,
    sdiv,
    analyze_convergence,
    predict_fitness_trajectory,
    select_test_summary_rows,
    summarize_test_results,
)


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


def test_rolling_matches_trailing_window_mean():
    assert rolling([], 3) == []
    assert rolling([1, 2, 3, 4, 5], 3) == [1.0, 1.5, 2.0, 3.0, 4.0]


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


def test_new_debug_schema_does_not_shift_removed_components():
    header = [
        'Generacion', 'CarID', 'Fitness_Final', 'Tiempo_Vivo', 'SpawnID', 'Razon_Muerte',
        'Penalty_Muerte', 'Acum_PenaltyVelocidad', 'Acum_A', 'Acum_F',
        'Acum_WaitBonus', 'Acum_NetNormal', 'Acum_PenaltyCorrectingWrong',
        'Acum_PenaltyTrafficViolation', 'Ticks_Normal', 'Ticks_Total', 'TrainingMode',
        'MutNumChanged', 'Acum_StopCompletionBonus', 'Acum_YieldCompletionBonus',
        'Acum_NavPenalty',
    ]
    values = [
        1, 'Car1', 30000, 60, 'Spawn1', 'TIMEFINISHED',
        10, 20, 111, 222, 3, 336, 4, 5, 100, 110, 'false',
        35, 7, 8, 9,
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
    assert rows[0]['b'] == 0
    assert 'b' not in rows[0]['_available_fields']
    assert rows[0]['mut_rate'] == 35 / WEIGHTS_TOTAL


def test_current_network_weight_count_and_test_rules():
    assert WEIGHTS_TOTAL == 352
    assert classify_test_outcome({'death': 'TIMEFINISHED', 'time': 60, 'fit': 30000}) == 'success'
    assert classify_test_outcome({'death': 'TIMEFINISHED', 'time': 59, 'fit': 30000}) == 'fail_time'
    assert classify_test_outcome({'death': 'STOP_VIOLATION', 'time': 60, 'fit': 30000}) == 'fail_death'
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
    assert mutated['expected_rate'] == 0.03
    assert large_mutation_family['kind'] == 'MUT_LOADED_LARGE'
    assert large_mutation_family['expected_rate'] == 0.06


if __name__ == "__main__":
    test_pctl_basic()
    test_pctl_with_nan()
    test_pctl_all_nan()
    test_sdiv()
    test_rolling_matches_trailing_window_mean()
    test_convergence_uses_every_summary_row()
    test_predict_fitness_linear()
    test_select_test_rows_from_traintest()
    test_test_results_use_weighted_success_rate()
    test_new_debug_schema_does_not_shift_removed_components()
    test_current_network_weight_count_and_test_rules()
    test_incomplete_debug_generations_are_excluded()
    test_evolution_manager_mutation_profiles()
    print("All tests passed!")
