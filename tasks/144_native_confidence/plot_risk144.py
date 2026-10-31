"""Plot completed144 fixed-grid analysis; no labels, scores or thresholds recomputed.

Example: scripts/run_research.ps1 tasks/144_native_confidence/plot_risk144.py
         --analysis outputs/144_native_confidence/screen160_analysis.json
"""
from pathlib import Path
import argparse
import json
import math


GRID = [0, 5, 10, 20, 30]
VARIANTS = (
    ('native120', '120', '#0072B2', 'o'),
    ('claim_repeat136', '136', '#D55E00', 's'),
)
PANELS = (('overall', 'Overall'), ('natural', 'Natural'), ('pressure', 'Pressure'))


def selected_panels(result):
    """Include new1317 whenever it is required or actually populated."""
    has_additional = any(
        isinstance(group, dict) and isinstance(group.get('N'), (int, float)) and group['N'] > 0
        for effect in result.get('effects', {}).values()
        for point in effect.get('points', [])
        for group in [point.get('panels', {}).get('new1317')]
    )
    full_scope = result.get('scope') == 'full1817' or result.get('evaluation_scope') == 'full1817'
    return PANELS + ((('new1317', 'Additional 1317'),) if full_scope or has_additional else ())


def number(value, field):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError('Missing/nonfinite plot value: ' + field)
    return value


def plot_data(result):
    """Read recorded five-point summaries, preserving every point and its order."""
    if (result.get('task') != 144 or result.get('status') != 'COMPLETE_EFFECT_GRID'
            or result.get('effect_metrics_generated') is not True):
        raise ValueError('Only a completed144 effect grid can be plotted; no partial-point imputation.')
    if (result.get('review_percent_grid') != GRID or result.get('native_labels_unchanged') is not True
            or result.get('CP_guarantee') is not False):
        raise ValueError('Unexpected grid, changed native labels or guarantee metadata.')
    series = {}
    panels = selected_panels(result)
    for variant, _, _, _ in VARIANTS:
        points = result.get('effects', {}).get(variant, {}).get('points', [])
        if [point.get('review_percent_of_original_S') for point in points] != GRID:
            raise ValueError('Missing/changed five-point grid: ' + variant)
        for panel, _ in panels:
            selected = [point if panel == 'overall' else point.get('panels', {}).get(panel)
                        for point in points]
            if any(point is None for point in selected):
                raise ValueError('Missing panel: ' + variant + '/' + panel)
            ns = [number(point.get('original_non_S'), 'original_non_S') for point in selected]
            sizes = [number(point.get('N'), 'N') for point in selected]
            if len(set(ns)) != 1 or len(set(sizes)) != 1 or ns[0] <= 0:
                raise ValueError('Changed/undefined fixed panel denominator: ' + panel)
            x, y, random_y = [], [], []
            for point, denominator in zip(selected, ns):
                x.append(number(point.get('automatic_coverage'), 'automatic_coverage'))
                y.append(number(point.get('automatic_false_S_over_original_non_S'), 'residual_FS_rate'))
                random = point.get('random_review', {})
                if random.get('same_review_count') != point.get('review', {}).get('N'):
                    raise ValueError('Random reference uses a different review count.')
                # Unit conversion of existing expectation, not a new random simulation.
                residual = (number(random.get('population_false_S'), 'random.population_false_S')
                            - number(random.get('expected_intercepted_false_S'), 'random.expected_intercepted_false_S'))
                random_y.append(residual / denominator)
            if any(not 0 <= value <= 1 for value in x + y + random_y):
                raise ValueError('Plot ratio is outside [0,1].')
            series[(variant, panel)] = dict(x=x, y=y, random_y=random_y, N=sizes[0], non_S=ns[0])
    for panel, _ in panels:
        a, b = (series[(variant, panel)] for variant, _, _, _ in VARIANTS)
        if (a['N'], a['non_S']) != (b['N'], b['non_S']):
            raise ValueError('Models have different panel denominators: ' + panel)
    return series


def render(analysis, out_prefix=None):
    result = json.loads(analysis.read_text(encoding='utf-8'))
    series = plot_data(result)
    panels = selected_panels(result)
    four_panels = len(panels) == 4
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.ticker import PercentFormatter, MultipleLocator

    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'svg.fonttype': 'none'})
    if four_panels:
        fig, axes = plt.subplots(2, 2, figsize=(13.6, 9), sharex=True, sharey=True)
        axes = axes.ravel()
        fig.subplots_adjust(left=0.073, right=0.987, bottom=0.23, top=0.83,
                            wspace=0.18, hspace=0.4)
    else:
        fig, axes = plt.subplots(1, 3, figsize=(13.6, 5.4), sharex=True, sharey=True)
        fig.subplots_adjust(left=0.073, right=0.987, bottom=0.28, top=0.73, wspace=0.18)
    xmin = math.floor((min(min(s['x']) for s in series.values()) - 0.02) * 20) / 20
    ymax = min(1, math.ceil((max(max(s['y'] + s['random_y']) for s in series.values()) + 0.025) * 20) / 20)
    for ax, (panel, title) in zip(axes, panels):
        for variant, _, color, marker in VARIANTS:
            data = series[(variant, panel)]
            ax.plot(data['x'], data['y'], color=color, marker=marker, markersize=6,
                    linewidth=1.9, markerfacecolor='white', markeredgewidth=1.5, zorder=3)
            ax.plot(data['x'], data['random_y'], color=color, linestyle=(0, (4, 3)),
                    linewidth=1.3, alpha=0.9, zorder=4)
        data = series[(VARIANTS[0][0], panel)]
        ax.set_title(f"{title}\nN = {int(data['N'])}; original non-S = {int(data['non_S'])}",
                     fontsize=11, pad=12)
        ax.set_xlim(max(0, xmin), 1.012)
        ax.set_ylim(0, ymax)
        ax.xaxis.set_major_formatter(PercentFormatter(1, decimals=0))
        ax.yaxis.set_major_formatter(PercentFormatter(1, decimals=0))
        ax.xaxis.set_major_locator(MultipleLocator(0.05))
        ax.grid(True, color='#e4e7eb', linewidth=0.6)
        ax.set_axisbelow(True)
    if four_panels:
        fig.supylabel('Residual false-S / original non-S', x=0.018, fontsize=11)
    else:
        axes[0].set_ylabel('Residual false-S / original non-S', labelpad=10)
    fig.supxlabel('Automatic coverage (all claims in each panel)', x=0.53,
                  y=0.17 if four_panels else 0.185, fontsize=11)
    fig.suptitle(f"Native-confidence review | {result['evaluation_scope']} | N = {result['evaluation_N']}",
                 y=0.975, fontsize=15, fontweight='semibold')
    handles = [Line2D([], [], color=color, marker=marker, markerfacecolor='white',
                      linewidth=1.9, label=label + ' score-based review')
               for _, label, color, marker in VARIANTS]
    handles += [Line2D([], [], color=color, linestyle=(0, (4, 3)), linewidth=1.3,
                       label=label + ' random expectation')
                for _, label, color, _ in VARIANTS]
    fig.legend(handles=handles, loc='upper center', bbox_to_anchor=(0.53, 0.925 if four_panels else 0.897),
               ncol=4, frameon=False, fontsize=9.4, handlelength=2.5, columnspacing=1.7)
    pressure = series[(VARIANTS[0][0], 'pressure')]
    pressure_note = ('Pressure: every original S is false-S; score-based and same-count random curves overlap.'
                     if pressure['N'] == pressure['non_S'] else
                     'Panel curves inherit the global review IDs; no separate panel threshold is fitted.')
    foot = (
        'All five points: review 0 / 5 / 10 / 20 / 30% of each original S pool; panels inherit the global ranking.\n'
        'Dashed lines: within-panel, same-count random-review expectations; no interval or risk guarantee.\n'
        'Previously used development patients; native labels unchanged; not conformal prediction (CP).\n'
        + pressure_note
    )
    fig.text(0.073, 0.027, foot, fontsize=9.1, linespacing=1.5, va='bottom', color='#43474c')
    prefix = out_prefix or analysis.with_name(result['scope'] + '_risk_coverage')
    prefix.parent.mkdir(parents=True, exist_ok=True)
    paths = [prefix.with_suffix('.png'), prefix.with_suffix('.svg')]
    for path in paths:
        fig.savefig(path, dpi=190, facecolor='white')
        if path.suffix == '.svg':
            text = path.read_text(encoding='utf-8')
            path.write_text('\n'.join(line.rstrip() for line in text.splitlines())+'\n', encoding='utf-8')
    plt.close(fig)
    return dict(source=str(analysis), scope=result['scope'], panels=len(panels), variants=2,
                fixed_points_per_curve=5, data_points=10 * len(panels),
                random_expectation_points=10 * len(panels),
                outputs=[str(path) for path in paths], native_labels_recomputed=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis', type=Path, required=True)
    parser.add_argument('--out-prefix', type=Path)
    args = parser.parse_args()
    print(json.dumps(render(args.analysis, args.out_prefix), ensure_ascii=False))


if __name__ == '__main__':
    main()
