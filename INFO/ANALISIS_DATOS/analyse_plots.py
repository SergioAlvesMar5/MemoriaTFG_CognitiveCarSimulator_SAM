# -*- coding: utf-8 -*-
"""Parte interna de analyse_current.py.

Este archivo se carga desde analyse_current.py dentro del mismo namespace global
para mantener compatibilidad con los imports existentes y con la CLI antigua.
No esta pensado para ejecutarse directamente.
"""

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

def lifetime_distribution_bins(debug_rows, step_pct=10):
    step_pct = max(1, min(100, int(step_pct or 10)))
    if 100 % step_pct != 0:
        step_pct = 10
    n_bins = max(1, 100 // step_pct)

    rows = []
    for r in debug_rows or []:
        t = num(r.get('time', 0.0), 0.0)
        if math.isfinite(t) and t >= 0.0:
            rows.append((t, r))
    if not rows:
        return {
            'max_time': 0.0,
            'max_row': {},
            'total': 0,
            'bins': [],
        }

    max_time, max_row = max(rows, key=lambda item: item[0])
    counts = [0 for _ in range(n_bins)]
    for t, _ in rows:
        if max_time <= 0.0:
            idx = 0
        else:
            pct = sdiv(t * 100.0, max_time)
            idx = min(n_bins - 1, int(pct // step_pct))
        counts[idx] += 1

    total = len(rows)
    bins = []
    accum = 0
    for i, count in enumerate(counts):
        pct_start = i * step_pct
        pct_end_exclusive = min(100, (i + 1) * step_pct)
        pct_label = f'{pct_start}-{pct_end_exclusive - 1}%'
        if i == n_bins - 1:
            pct_label = f'{pct_start}-100%'

        sec_start = max_time * pct_start / 100.0
        sec_end = max_time * pct_end_exclusive / 100.0
        accum += count
        bins.append({
            'pct_start': pct_start,
            'pct_end': pct_end_exclusive,
            'pct_label': pct_label,
            'sec_start': sec_start,
            'sec_end': sec_end,
            'count': count,
            'car_pct': sdiv(count * 100.0, total),
            'accum_pct': sdiv(accum * 100.0, total),
        })

    return {
        'max_time': max_time,
        'max_row': max_row,
        'total': total,
        'bins': bins,
    }

def plot_lifetime_distribution(dbg):
    """Distribucion de tiempo vivo normalizada por el coche mas longevo."""
    saved = []
    if not dbg:
        return saved

    try:
        step_pct = int(os.environ.get('ANALYSE_LIFETIME_BIN_PCT', '10'))
    except ValueError:
        step_pct = 10
    info = lifetime_distribution_bins(dbg, step_pct=step_pct)
    bins = info.get('bins', [])
    if not bins:
        return saved

    max_time = info.get('max_time', 0.0)
    max_row = info.get('max_row', {}) or {}
    labels = [b['pct_label'] for b in bins]
    values = [b['car_pct'] for b in bins]
    counts = [b['count'] for b in bins]
    sec_labels = [
        f'{b["sec_start"]:.1f}-{b["sec_end"]:.1f}s'
        for b in bins
    ]
    xlabels = [f'{label}\n{seconds}' for label, seconds in zip(labels, sec_labels)]
    max_detail = (
        f'Coche maximo: {max_time:.2f}s | Gen {max_row.get("gen", "-")} | '
        f'{max_row.get("car", "-")} | '
        f'{str(max_row.get("spawn", "-")).replace("TargetPoint", "TP")} | '
        f'{short_death_reason(max_row.get("death", "-"))}'
    )

    fig = plt.figure(figsize=(16, 11.2))
    grid = fig.add_gridspec(3, 1, height_ratios=[3.05, 0.58, 1.78], hspace=0.0)
    fig.subplots_adjust(left=0.08, right=0.98, top=0.905, bottom=0.065)
    ax = fig.add_subplot(grid[0])
    ax_gap = fig.add_subplot(grid[1])
    ax_table = fig.add_subplot(grid[2])
    ax_gap.axis('off')
    fig.suptitle(
        f'{LABEL} - Distribucion porcentual del tiempo vivo (100% = {max_time:.2f}s)',
        fontsize=15,
        fontweight='bold',
        y=0.982,
    )
    fig.text(
        0.5,
        0.955,
        max_detail,
        ha='center',
        va='center',
        fontsize=10,
        color='#374151',
    )

    colors = plt.cm.Blues(np.linspace(0.38, 0.86, len(bins)))
    bars = ax.bar(range(len(bins)), values, color=colors, edgecolor='#1f2937', linewidth=0.8)
    if bars:
        bars[-1].set_edgecolor('black')
        bars[-1].set_linewidth(1.6)

    y_max = max(values) if values else 0.0
    ax.set_ylim(0, max(5.0, y_max * 1.22))
    ax.set_xticks(range(len(bins)))
    ax.set_xticklabels(xlabels, fontsize=8)
    ax.set_ylabel('% de coches')
    ax.set_xlabel('Tramo de vida respecto al coche mas longevo (100%)')
    ax.xaxis.labelpad = 12
    ax.margins(x=0.045)
    ax.grid(True, axis='y', alpha=0.3)

    for i, bar in enumerate(bars):
        h = bar.get_height()
        ax.text(
            bar.get_x() + bar.get_width() / 2.0,
            h + max(0.25, y_max * 0.015),
            f'{values[i]:.1f}%\nN={counts[i]}',
            ha='center',
            va='bottom',
            fontsize=8,
        )

    ax_table.axis('off')
    table_rows = []
    for b in bins:
        if b['pct_end'] >= 100:
            sec_range = f'{b["sec_start"]:.2f} <= t <= {b["sec_end"]:.2f}s'
        else:
            sec_range = f'{b["sec_start"]:.2f} <= t < {b["sec_end"]:.2f}s'
        table_rows.append([
            b['pct_label'],
            sec_range,
            str(b['count']),
            f'{b["car_pct"]:.2f}%',
            f'{b["accum_pct"]:.2f}%',
        ])
    table = ax_table.table(
        cellText=table_rows,
        colLabels=['Tramo %', 'Rango en segundos', 'Coches', '% coches', '% acum.'],
        cellLoc='center',
        colLoc='center',
        bbox=[0.02, 0.04, 0.96, 0.92],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    table.scale(1.0, 1.28)
    for (row, col), cell in table.get_celld().items():
        if row == 0:
            cell.set_facecolor('#dbeafe')
            cell.set_text_props(weight='bold')
        elif row % 2 == 0:
            cell.set_facecolor('#f8fafc')

    fig.text(
        0.075,
        0.025,
        'Los tramos son relativos al tiempo maximo real del lote; por eso el rango en segundos cambia entre ejecuciones.',
        fontsize=8,
        color='#4b5563',
    )
    saved.append(save_fig(fig, '01b_distribucion_tiempo_vida.png'))
    return saved

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
        g_a, g_e, g_f, g_wait, g_queue_wait, g_stop_bonus, g_yield_bonus = [], [], [], [], [], [], []
        g_pm, g_pv, g_ptv, g_pn, g_pc, g_pr, g_pl, g_ps, g_pa, g_poverlap, g_net, g_fit = [], [], [], [], [], [], [], [], [], [], [], []
        for g in gens:
            gc = by_gen[g]  # O(1) lookup
            ng = len(gc)
            g_a.append(sdiv(sum(r['a'] for r in gc), ng))
            g_e.append(sdiv(sum(r['e'] for r in gc), ng))
            g_f.append(sdiv(sum(r['f'] for r in gc), ng))
            g_wait.append(sdiv(sum(r.get('wait_bonus', 0.0) for r in gc), ng))
            g_queue_wait.append(sdiv(sum(r.get('queue_wait_bonus', 0.0) for r in gc), ng))
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
            g_pa.append(sdiv(sum(r.get('pen_align', 0.0) for r in gc), ng))
            g_poverlap.append(sdiv(sum(r.get('car_overlap_penalty', 0.0) for r in gc), ng))
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
        if debug_field_available(dbg, 'queue_wait_bonus'):
            ax.plot(gens, g_queue_wait, color='tab:green', linestyle=':', linewidth=1.4, label='Queue wait bonus')
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
        if debug_field_available(dbg, 'pen_align'):
            ax.plot(gens, g_pa, color='black', linestyle='--', marker=mk or None, markersize=ms, label='Pen Alignment', linewidth=1.2)
        if debug_field_available(dbg, 'car_overlap_penalty'):
            ax.plot(gens, g_poverlap, color='tab:red', linestyle=':', marker=mk or None, markersize=ms, label='Pen CarOverlap real', linewidth=1.3)
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

        grouped = group_debug_death_families(dbg, split_roundabout_collisions=True)
        if grouped:
            fig, ax = plt.subplots(figsize=(12, max(4, len(grouped)*0.55)))
            reasons = [r for r, _, _ in grouped]
            counts = [c for _, c, _ in grouped]
            colors = [death_group_color(r) for r in reasons]
            short = [short_death_reason(r) for r in reasons]
            ax.barh(short, counts, color=colors, alpha=0.85)
            add_family_separators(ax, grouped)
            ax.set_title(f'{LABEL} - Razones de Muerte Agrupadas (colisiones separadas)')
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

    # 13b. Diagnosticos 30/06-01/07: ceda, cruce, release, steer approach y solapes
    if len(gens) >= 1 and (
        debug_field_available(dbg, 'yield_free_passes')
        or debug_field_available(dbg, 'crossing_blocked_t')
        or debug_field_available(dbg, 'first_steer_release_ticks')
        or debug_field_available(dbg, 'steer_app_wrong')
        or debug_field_available(dbg, 'car_overlap_penalty')
    ):
        g_yield_free, g_yield_done = [], []
        g_cross_blocked, g_yield_speed = [], []
        g_release_ticks, g_wrong_share, g_overlap_shadow, g_overlap_penalty = [], [], [], []
        for g in gens:
            gc = by_gen[g]
            ng = len(gc)
            g_yield_free.append(sdiv(sum(r.get('yield_free_passes', 0.0) for r in gc), ng))
            g_yield_done.append(sdiv(sum(r.get('yield_done_n', 0.0) for r in gc), ng))
            g_cross_blocked.append(sdiv(sum(r.get('crossing_blocked_t', 0.0) for r in gc), ng))
            g_yield_speed.append(mean(metric_values(gc, 'yield_validation_speed')))
            g_release_ticks.append(mean(metric_values(gc, 'first_steer_release_ticks')))
            g_wrong_share.append(mean(metric_values(gc, 'steer_app_wrong_share')) * 100.0)
            g_overlap_shadow.append(mean(metric_values(gc, 'car_overlap_shadow_per_overlap')))
            g_overlap_penalty.append(mean(metric_values(gc, 'car_overlap_penalty_per_overlap')))

        mk = 'o' if len(gens) <= 300 else ''
        ms = 3 if len(gens) <= 300 else 1
        fig, axes = plt.subplots(3, 1, figsize=(15, 12))
        fig.suptitle(f'{LABEL} - Diagnosticos 30/06-01/07: Ceda, Cruce, Release y Solapes', fontsize=13, fontweight='bold')

        ax = axes[0]
        if debug_field_available(dbg, 'yield_free_passes'):
            ax.plot(gens, g_yield_free, color='tab:blue', marker=mk or None, markersize=ms, label='NumYieldFreePasses/coche')
        ax.plot(gens, g_yield_done, color='tab:green', marker=mk or None, markersize=ms, label='NumYieldsCompleted/coche')
        ax.set_title('Validaciones y completados de ceda')
        ax.set_xlabel(GEN_XLABEL)
        ax.set_ylabel('Media por coche')
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=8)

        ax = axes[1]
        if debug_field_available(dbg, 'crossing_blocked_t'):
            ax.plot(gens, g_cross_blocked, color='tab:red', marker=mk or None, markersize=ms, label='TimeBlockedAtCrossing/coche')
        if debug_field_available(dbg, 'yield_validation_speed'):
            ax2 = ax.twinx()
            ax2.plot(gens, g_yield_speed, color='tab:purple', linestyle='--', marker=mk or None, markersize=ms, label='SpeedAtYieldValidation exp.')
            ax2.set_ylabel('Velocidad expuesta')
            h1, l1 = ax.get_legend_handles_labels()
            h2, l2 = ax2.get_legend_handles_labels()
            ax.legend(h1 + h2, l1 + l2, fontsize=8, loc='upper left')
        else:
            ax.legend(fontsize=8)
        ax.set_title('Bloqueo de cruce y velocidad puntual al validar ceda')
        ax.set_xlabel(GEN_XLABEL)
        ax.set_ylabel('Segundos por coche')
        ax.grid(True, alpha=0.3)

        ax = axes[2]
        if debug_field_available(dbg, 'first_steer_release_ticks'):
            ax.plot(gens, g_release_ticks, color='tab:orange', marker=mk or None, markersize=ms, label='FirstSteerAfterRelease exp.')
        if debug_field_available(dbg, 'steer_app_wrong') or debug_field_available(dbg, 'steer_app_right'):
            ax2 = ax.twinx()
            ax2.plot(gens, g_wrong_share, color='tab:brown', linestyle='--', marker=mk or None, markersize=ms, label='SteerApproach wrong share %')
            ax2.set_ylabel('Wrong share (%)')
            ax2.set_ylim(0.0, 100.0)
            h1, l1 = ax.get_legend_handles_labels()
            h2, l2 = ax2.get_legend_handles_labels()
            ax.legend(h1 + h2, l1 + l2, fontsize=8, loc='upper left')
        if debug_field_available(dbg, 'car_overlap_pen_shadow'):
            ax.plot(gens, g_overlap_shadow, color='black', linestyle=':', marker=mk or None, markersize=ms, label='OverlapShadow/overlap exp.')
            ax.legend(fontsize=8, loc='upper left')
        if debug_field_available(dbg, 'car_overlap_penalty'):
            ax.plot(gens, g_overlap_penalty, color='tab:red', linestyle='-.', marker=mk or None, markersize=ms, label='OverlapPenalty/overlap exp.')
            ax.legend(fontsize=8, loc='upper left')
        ax.set_title('Reaccion tras release, direccion de approach y solapes')
        ax.set_xlabel(GEN_XLABEL)
        ax.set_ylabel('Ticks / severidad')
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        saved.append(save_fig(fig, '13b_yield_crossing_release.png'))

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
    expected_min_rates = []
    expected_max_rates = []
    for fam in sorted(fam_rows.keys()):
        rows_f = fam_rows[fam]
        if not rows_f:
            continue
        fams.append(fam)
        mut_rates.append(mean([x.get('mut_rate', 0.0) for x in rows_f]) * 100.0)
        fit_means.append(mean([x.get('fit', 0.0) for x in rows_f]))
        expected_min_rates.append(mean([x.get('expected_mut_rate_min', 0.0) or 0.0 for x in rows_f]) * 100.0)
        expected_max_rates.append(mean([x.get('expected_mut_rate_max', 0.0) or 0.0 for x in rows_f]) * 100.0)

    if not fams:
        return saved

    fig, ax = plt.subplots(figsize=(12, 6))
    fig.suptitle(f'{LABEL} - Mutation by family', fontsize=14, fontweight='bold')
    ax.bar(fams, mut_rates, color='steelblue', alpha=0.8)
    ax.plot(fams, expected_min_rates, color='crimson', marker='D', linewidth=1.4, label='expected min')
    ax.plot(fams, expected_max_rates, color='crimson', marker='D', linestyle='--', linewidth=1.4, label='expected max')
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

def plot_roundabout_summary(dbg):
    saved = []
    if not dbg or not debug_field_available(dbg, 'round_entered_n'):
        return saved
    plot_label = infer_label_from_debug_rows(dbg)

    by_gen = defaultdict(list)
    for row in dbg:
        by_gen[row.get('gen', 0)].append(row)
    gens = sorted(by_gen)
    if not gens:
        return saved

    entered = [sum(r.get('round_entered_n', 0.0) for r in by_gen[g]) for g in gens]
    completed = [sum(r.get('round_completed_n', 0.0) for r in by_gen[g]) for g in gens]
    collisions = [sum(r.get('round_collisions', 0.0) for r in by_gen[g]) for g in gens]
    completion_pct = [ratio_or_nan(c, e, 100.0) for c, e in zip(completed, entered)]
    collision_pct = [ratio_or_nan(c, e, 100.0) for c, e in zip(collisions, entered)]
    entry_speed = [
        ratio_or_nan(
            sum(r.get('round_entry_speed', 0.0) for r in by_gen[g]),
            sum(r.get('round_entered_n', 0.0) for r in by_gen[g]),
        )
        for g in gens
    ]
    entry_front = [
        ratio_or_nan(
            sum(r.get('round_entry_front', 0.0) for r in by_gen[g]),
            sum(r.get('round_entered_n', 0.0) for r in by_gen[g]),
        )
        for g in gens
    ]
    steer_avg = [
        ratio_or_nan(
            sum(r.get('round_steer', 0.0) for r in by_gen[g]),
            sum(r.get('round_ticks', 0.0) for r in by_gen[g]),
        )
        for g in gens
    ]
    throttle_avg = [
        ratio_or_nan(
            sum(r.get('round_throttle', 0.0) for r in by_gen[g]),
            sum(r.get('round_ticks', 0.0) for r in by_gen[g]),
        )
        for g in gens
    ]

    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle(f'{plot_label} - Diagnostico de Rotondas', fontsize=14, fontweight='bold')

    axes[0, 0].plot(gens, entered, label='Entradas', color='tab:blue')
    axes[0, 0].plot(gens, completed, label='Completadas', color='tab:green')
    axes[0, 0].set_title('Entradas y completadas')
    axes[0, 0].legend()

    axes[0, 1].plot(gens, completion_pct, label='Completion %', color='tab:green')
    axes[0, 1].plot(gens, collision_pct, label='Collision %', color='tab:red')
    axes[0, 1].set_title('Resultado por entrada (huecos = sin entrada)')
    axes[0, 1].set_ylabel('Porcentaje')
    axes[0, 1].legend()

    axes[1, 0].plot(gens, entry_speed, label='Velocidad entrada', color='tab:orange')
    axes[1, 0].set_title('Contexto de entrada (solo generaciones con entrada)')
    axes[1, 0].set_ylabel('Velocidad entrada')
    axes[1, 0].tick_params(axis='y', labelcolor='tab:orange')
    ax_front = axes[1, 0].twinx()
    ax_front.plot(gens, entry_front, label='Obstaculo frontal entrada', color='tab:purple', marker='o')
    ax_front.set_ylabel('Obstaculo frontal entrada')
    ax_front.tick_params(axis='y', labelcolor='tab:purple')
    lines = axes[1, 0].get_lines() + ax_front.get_lines()
    axes[1, 0].legend(lines, [line.get_label() for line in lines], loc='best')

    axes[1, 1].plot(gens, steer_avg, label='ABS steering/tick', color='tab:blue')
    axes[1, 1].plot(gens, throttle_avg, label='Throttle/tick', color='tab:brown')
    axes[1, 1].set_title('Control dentro de la rotonda (solo ticks en rotonda)')
    axes[1, 1].legend()

    for ax in axes.flat:
        ax.set_xlabel(GEN_XLABEL)
        ax.grid(True, alpha=0.3)
    ax_front.grid(False)

    plt.tight_layout()
    saved.append(save_fig(fig, '29_roundabout.png'))
    return saved

def plot_roundabout_exit_summary(dbg):
    saved = []
    if not dbg or not debug_field_available(dbg, 'round_exit1_count'):
        return saved
    plot_label = infer_label_from_debug_rows(dbg)

    labels = ['Exit1', 'Exit2', 'Exit3+']
    counts = [
        sum(r.get(f'round_exit{i}_count', 0.0) for r in dbg)
        for i in (1, 2, 3)
    ]
    deaths = [
        sum(r.get(f'round_exit{i}_deaths', 0.0) for r in dbg)
        for i in (1, 2, 3)
    ]
    ticks = [
        sum(r.get(f'round_exit{i}_ticks', 0.0) for r in dbg)
        for i in (1, 2, 3)
    ]
    death_rates = [sdiv(d * 100.0, c) for d, c in zip(deaths, counts)]
    steer_avg = [
        sdiv(sum(r.get(f'round_exit{i}_steer', 0.0) for r in dbg), tick)
        for i, tick in zip((1, 2, 3), ticks)
    ]
    throttle_avg = [
        sdiv(sum(r.get(f'round_exit{i}_throttle', 0.0) for r in dbg), tick)
        for i, tick in zip((1, 2, 3), ticks)
    ]
    directions = [
        sum(r.get('round_dir_first', 0.0) for r in dbg),
        sum(r.get('round_dir_second', 0.0) for r in dbg),
        sum(r.get('round_dir_third', 0.0) for r in dbg),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f'{plot_label} - Rotondas por Salida', fontsize=14, fontweight='bold')

    axes[0, 0].bar(labels, directions, color=['tab:blue', 'tab:orange', 'tab:green'])
    axes[0, 0].set_title('Direcciones asignadas al entrar')
    axes[0, 0].set_ylabel('Cantidad')

    x = np.arange(len(labels))
    axes[0, 1].bar(x - 0.18, counts, width=0.36, label='Exposiciones', color='steelblue')
    axes[0, 1].bar(x + 0.18, deaths, width=0.36, label='Muertes', color='tomato')
    axes[0, 1].set_xticks(x)
    axes[0, 1].set_xticklabels(labels)
    axes[0, 1].set_title('Exposicion y muertes')
    axes[0, 1].legend()

    axes[1, 0].bar(labels, death_rates, color='crimson', alpha=0.8)
    axes[1, 0].set_title('Muertes por exposicion')
    axes[1, 0].set_ylabel('Porcentaje')

    axes[1, 1].plot(labels, steer_avg, marker='o', label='ABS steering/tick')
    axes[1, 1].plot(labels, throttle_avg, marker='o', label='Throttle/tick')
    axes[1, 1].set_title('Control medio por tramo')
    axes[1, 1].legend()

    for ax in axes.flat:
        ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()
    saved.append(save_fig(fig, '30_roundabout_exits.png'))
    return saved

def plot_roundabout_bonus(dbg):
    saved = []
    if not dbg or not debug_field_available(dbg, 'round_bonus'):
        return saved
    plot_label = infer_label_from_debug_rows(dbg)

    by_gen = defaultdict(list)
    for row in dbg:
        by_gen[row.get('gen', 0)].append(row)
    gens = sorted(by_gen)
    if not gens:
        return saved

    bonus = [sum(r.get('round_bonus', 0.0) for r in by_gen[g]) for g in gens]
    completion_bonus = [sum(r.get('round_completion_bonus', 0.0) for r in by_gen[g]) for g in gens]
    entry_penalty = [sum(r.get('round_entry_penalty', 0.0) for r in by_gen[g]) for g in gens]
    throttle_penalty = [sum(r.get('round_throttle_penalty', 0.0) for r in by_gen[g]) for g in gens]
    entered = [sum(r.get('round_entered_n', 0.0) for r in by_gen[g]) for g in gens]
    completed = [sum(r.get('round_completed_n', 0.0) for r in by_gen[g]) for g in gens]
    ticks = [sum(r.get('round_ticks', 0.0) for r in by_gen[g]) for g in gens]
    collisions = [sum(r.get('round_collisions', 0.0) for r in by_gen[g]) for g in gens]
    bonus_per_entry = [ratio_or_nan(b, e) for b, e in zip(bonus, entered)]
    bonus_per_tick = [ratio_or_nan(b, t) for b, t in zip(bonus, ticks)]
    completion_pct = [ratio_or_nan(c, e, 100.0) for c, e in zip(completed, entered)]
    collision_pct = [ratio_or_nan(c, e, 100.0) for c, e in zip(collisions, entered)]

    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    fig.suptitle(f'{plot_label} - RoundaboutBonus', fontsize=14, fontweight='bold')

    axes[0, 0].axhline(0.0, color='black', linewidth=0.8, alpha=0.4)
    axes[0, 0].plot(gens, bonus, label='Bonus neto', color='tab:green', marker='o')
    if debug_field_available(dbg, 'round_completion_bonus'):
        axes[0, 0].plot(gens, completion_bonus, label='Completion bonus', color='tab:blue', alpha=0.8)
        axes[0, 0].plot(gens, [-v for v in entry_penalty], label='-Entry penalty', color='tab:red', alpha=0.8)
        axes[0, 0].plot(gens, [-v for v in throttle_penalty], label='-Throttle penalty', color='tab:orange', alpha=0.8)
    axes[0, 0].set_title('Bonus neto y contribuciones')
    axes[0, 0].set_ylabel('Fitness')
    axes[0, 0].legend()

    axes[0, 1].axhline(0.0, color='black', linewidth=0.8, alpha=0.4)
    axes[0, 1].plot(gens, bonus_per_entry, label='Bonus/entrada', color='tab:blue', marker='o')
    axes[0, 1].set_title('Bonus por entrada')
    axes[0, 1].legend()

    axes[1, 0].axhline(0.0, color='black', linewidth=0.8, alpha=0.4)
    axes[1, 0].plot(gens, bonus_per_tick, label='Bonus/tick rotonda', color='tab:purple', marker='o')
    axes[1, 0].set_title('Bonus por tick dentro de rotonda')
    axes[1, 0].legend()

    axes[1, 1].plot(gens, completion_pct, label='Completion %', color='tab:green')
    axes[1, 1].plot(gens, collision_pct, label='Collision %', color='tab:red')
    axes[1, 1].set_title('Resultado por entrada')
    axes[1, 1].set_ylabel('Porcentaje')
    axes[1, 1].legend()

    for ax in axes.flat:
        ax.set_xlabel(GEN_XLABEL)
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    saved.append(save_fig(fig, '31_roundabout_bonus.png'))
    return saved

def plot_all(summary, dbg):
    saved = []

    # Si no hay summary, aun asi intenta generar las graficas de debug.
    if not summary:
        if dbg:
            saved += plot_lifetime_distribution(dbg)
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
    if dbg:
        saved += plot_lifetime_distribution(dbg)

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
        saved += plot_roundabout_summary(dbg)
        saved += plot_roundabout_exit_summary(dbg)
        saved += plot_roundabout_bonus(dbg)

    return saved
