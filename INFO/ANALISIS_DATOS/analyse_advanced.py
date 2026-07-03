# -*- coding: utf-8 -*-
"""Parte interna de analyse_current.py.

Este archivo se carga desde analyse_current.py dentro del mismo namespace global
para mantener compatibilidad con los imports existentes y con la CLI antigua.
No esta pensado para ejecutarse directamente.
"""

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
    total_censored = sum(int(num(r.get('censored_count', 0), 0.0)) for r in rows)
    rates = [m['success_rate'] for m in derived]
    upper_rates = [m.get('success_rate_upper', m['success_rate']) for m in derived]
    observed_rates = [m.get('success_rate_observed', m['success_rate']) for m in derived]
    weighted_rate = (
        sdiv(total_success * 100.0, total_n)
        if total_n > 0 and (total_success + total_fail + total_censored) > 0
        else mean(rates)
    )
    upper_weighted_rate = (
        sdiv((total_success + total_censored) * 100.0, total_n)
        if total_n > 0 and total_censored > 0
        else weighted_rate
    )
    observed_weighted_rate = (
        sdiv(total_success * 100.0, total_success + total_fail)
        if (total_success + total_fail) > 0
        else weighted_rate
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
        'total_censored': total_censored,
        'censored_pct': sdiv(total_censored * 100.0, total_n),
        'success_rate': weighted_rate,
        'success_rate_upper': upper_weighted_rate,
        'success_rate_observed': observed_weighted_rate,
        'success_mean': mean(rates),
        'success_upper_mean': mean(upper_rates),
        'success_observed_mean': mean(observed_rates),
        'success_median': pctl(rates, 50),
        'success_std': stdev(rates),
        'success_min': min(rates),
        'success_max': max(upper_rates) if total_censored > 0 else max(rates),
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
