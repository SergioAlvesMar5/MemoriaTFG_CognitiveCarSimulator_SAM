import math
import numpy as np
from analyse_current import pctl, sdiv, predict_fitness_trajectory


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


def test_predict_fitness_linear():
    # create synthetic summary with increasing best values
    rows = [{'gen': i+1, 'best': float(10 + i*2), 'mean': 0, 'time': 0} for i in range(10)]
    preds = predict_fitness_trajectory(rows, future_gens=3)
    assert preds is not None
    assert 'predictions' in preds
    assert len(preds['predictions']) == 3
    assert all('predicted_fitness' in p for p in preds['predictions'])


if __name__ == "__main__":
    test_pctl_basic()
    test_pctl_with_nan()
    test_pctl_all_nan()
    test_sdiv()
    test_predict_fitness_linear()
    print("All tests passed!")