import json
import sys
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

ASYNC_FILE = "results_async.json"
SYNC_FILE = "results_sync.json"

def parse_k6_json(filename):
    """Parse le fichier JSON de K6 et extrait toutes les métriques"""
    metrics = defaultdict(list)
    try:
        with open(filename, 'r') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if data.get('type') == 'Point':
                        metric_name = data['metric']
                        value = data['data']['value']
                        metrics[metric_name].append(value)
                except json.JSONDecodeError:
                    pass
    except FileNotFoundError:
        print(f"❌ Erreur: Le fichier '{filename}' n'existe pas")
        sys.exit(1)
    return metrics

def calculate_stats(values):
    """Calcule les statistiques d'une liste de valeurs"""
    if not values:
        return {}
    sorted_values = sorted(values)
    n = len(values)
    return {
        'count': n,
        'avg': sum(values) / n,
        'min': min(values),
        'max': max(values),
        'p50': sorted_values[n // 2],
        'p75': sorted_values[int(n * 0.75)],
        'p90': sorted_values[int(n * 0.90)],
        'p95': sorted_values[int(n * 0.95)],
        'p99': sorted_values[int(n * 0.99)],
    }

def print_comparison_table(sync_stats, async_stats, title, unit="ms"):
    """Affiche un tableau de comparaison formaté"""
    print(f"\n📊 {title}")
    print("-" * 80)
    print(f"{'Métrique':<15} {'SYNC':>15} {'ASYNC':>15} {'Diff':>15} {'% Change':>15}")
    print("-" * 80)
    
    metrics_order = ['count', 'avg', 'min', 'max', 'p50', 'p75', 'p90', 'p95', 'p99']
    
    for metric in metrics_order:
        if metric not in sync_stats or metric not in async_stats:
            continue
            
        sync_val = sync_stats[metric]
        async_val = async_stats[metric]
        
        if metric == 'count':
            # Pour le count, pas de pourcentage
            print(f"{metric.upper():<15} {sync_val:>15.0f} {async_val:>15.0f} {async_val - sync_val:>15.0f} {'':>15}")
        else:
            diff = async_val - sync_val
            pct_change = ((async_val - sync_val) / sync_val * 100) if sync_val else 0
            
            # Indicateur de performance (🟢 mieux, 🔴 pire)
            indicator = "🟢" if async_val < sync_val else "🔴" if async_val > sync_val else "⚪"
            
            print(f"{metric.upper():<15} {sync_val:>13.2f}{unit} {async_val:>13.2f}{unit} "
                  f"{diff:>13.2f}{unit} {pct_change:>13.1f}% {indicator}")

def calculate_throughput(metrics):
    """Calcule le débit (requests per second)"""
    http_reqs = metrics.get('http_reqs', [])
    if len(http_reqs) > 1:
        # Estimation basée sur le nombre total de requêtes
        return http_reqs[-1] if http_reqs else 0
    return 0

def print_summary(sync_metrics, async_metrics):
    """Affiche un résumé global"""
    sync_total_reqs = calculate_throughput(sync_metrics)
    async_total_reqs = calculate_throughput(async_metrics)
    
    sync_failures = sum(sync_metrics.get('http_req_failed', []))
    async_failures = sum(async_metrics.get('http_req_failed', []))
    
    sync_checks = sync_metrics.get('checks', [])
    async_checks = async_metrics.get('checks', [])
    
    sync_success_rate = (sum(sync_checks) / len(sync_checks) * 100) if sync_checks else 0
    async_success_rate = (sum(async_checks) / len(async_checks) * 100) if async_checks else 0
    
    print("\n" + "=" * 80)
    print("📈 RÉSUMÉ GLOBAL")
    print("=" * 80)
    print(f"\n{'Métrique':<30} {'SYNC':>20} {'ASYNC':>20}")
    print("-" * 80)
    print(f"{'Requêtes totales':<30} {sync_total_reqs:>20.0f} {async_total_reqs:>20.0f}")
    print(f"{'Requêtes échouées':<30} {sync_failures:>20.0f} {async_failures:>20.0f}")
    print(f"{'Taux de succès':<30} {sync_success_rate:>19.2f}% {async_success_rate:>19.2f}%")

def create_comparison_charts(sync_duration, async_duration, output_file='comparison.png'):
    """Crée des graphiques de comparaison"""
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle('Comparaison Sync vs Async', fontsize=16, fontweight='bold')
    
    # Graphique 1: Comparaison des percentiles
    ax1 = axes[0, 0]
    metrics = ['p50', 'p75', 'p90', 'p95', 'p99']
    sync_values = [sync_duration.get(m, 0) for m in metrics]
    async_values = [async_duration.get(m, 0) for m in metrics]
    
    x = np.arange(len(metrics))
    width = 0.35
    
    ax1.bar(x - width/2, sync_values, width, label='Sync', color='#F77F00', alpha=0.8)
    ax1.bar(x + width/2, async_values, width, label='Async', color='#06A77D', alpha=0.8)
    ax1.set_xlabel('Percentiles')
    ax1.set_ylabel('Temps de réponse (ms)')
    ax1.set_title('Comparaison des percentiles')
    ax1.set_xticks(x)
    ax1.set_xticklabels([m.upper() for m in metrics])
    ax1.legend()
    ax1.grid(True, alpha=0.3, axis='y')
    
    # Graphique 2: Distribution des temps de réponse
    ax2 = axes[0, 1]
    stats_sync = [sync_duration.get('min', 0), sync_duration.get('p50', 0), 
                  sync_duration.get('p95', 0), sync_duration.get('max', 0)]
    stats_async = [async_duration.get('min', 0), async_duration.get('p50', 0), 
                   async_duration.get('p95', 0), async_duration.get('max', 0)]
    
    ax2.plot(['Min', 'P50', 'P95', 'Max'], stats_sync, marker='o', 
             linewidth=2, markersize=8, label='Sync', color='#F77F00')
    ax2.plot(['Min', 'P50', 'P95', 'Max'], stats_async, marker='s', 
             linewidth=2, markersize=8, label='Async', color='#06A77D')
    ax2.set_ylabel('Temps de réponse (ms)')
    ax2.set_title('Distribution des temps de réponse')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    
    # Graphique 3: Amélioration en pourcentage
    ax3 = axes[1, 0]
    improvements = []
    labels = []
    for metric in ['p50', 'p95', 'p99', 'avg']:
        sync_val = sync_duration.get(metric, 0)
        async_val = async_duration.get(metric, 0)
        if sync_val > 0:
            improvement = ((async_val - sync_val) / sync_val * 100)
            improvements.append(improvement)
            labels.append(metric.upper())
    
    colors = ['#06A77D' if x < 0 else '#D62828' for x in improvements]
    ax3.barh(labels, improvements, color=colors, alpha=0.8)
    ax3.axvline(x=0, color='black', linewidth=0.8)
    ax3.set_xlabel('Changement (%)')
    ax3.set_title('Amélioration/Dégradation par métrique')
    ax3.grid(True, alpha=0.3, axis='x')
    
    # Ajouter les valeurs sur les barres
    for i, v in enumerate(improvements):
        ax3.text(v + (2 if v > 0 else -2), i, f'{v:.1f}%', 
                va='center', ha='left' if v > 0 else 'right')
    
    # Graphique 4: Score card
    ax4 = axes[1, 1]
    ax4.axis('off')
    
    # Calculer le gagnant
    winner_count = sum(1 for imp in improvements if imp < 0)
    total_metrics = len(improvements)
    
    # Utiliser des caractères ASCII pour éviter les warnings
    verdict = "*** ASYNC GAGNE ***" if winner_count > total_metrics / 2 else "*** SYNC GAGNE ***"
    verdict_color = '#06A77D' if winner_count > total_metrics / 2 else '#F77F00'
    
    summary_text = f"""
    {verdict}
    
    Metriques meilleures:
    - Async: {winner_count}/{total_metrics}
    - Sync: {total_metrics - winner_count}/{total_metrics}
    
    Temps de reponse moyens:
    - Sync: {sync_duration.get('avg', 0):.2f} ms
    - Async: {async_duration.get('avg', 0):.2f} ms
    
    P95:
    - Sync: {sync_duration.get('p95', 0):.2f} ms
    - Async: {async_duration.get('p95', 0):.2f} ms
    """
    
    ax4.text(0.5, 0.5, summary_text, transform=ax4.transAxes,
            fontsize=12, verticalalignment='center', horizontalalignment='center',
            bbox=dict(boxstyle='round', facecolor=verdict_color, alpha=0.2),
            family='monospace', fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\n✅ Graphiques de comparaison sauvegardés : {output_file}")
    plt.show()

def main():
    print("=" * 80)
    print("🔥 COMPARAISON DÉTAILLÉE SYNC vs ASYNC")
    print("=" * 80)
    
    sync_metrics = parse_k6_json(SYNC_FILE)
    async_metrics = parse_k6_json(ASYNC_FILE)
    
    # Statistiques de temps de réponse
    sync_duration = calculate_stats(sync_metrics.get('http_req_duration', []))
    async_duration = calculate_stats(async_metrics.get('http_req_duration', []))
    
    print_comparison_table(sync_duration, async_duration, 
                          "TEMPS DE RÉPONSE HTTP (millisecondes)", "ms")
    
    # Résumé global
    print_summary(sync_metrics, async_metrics)
    
    print("\n" + "=" * 80)
    
    # Générer les graphiques
    if sync_duration and async_duration:
        create_comparison_charts(sync_duration, async_duration)

if __name__ == "__main__":
    main()