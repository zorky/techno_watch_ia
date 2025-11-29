import json
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime
from collections import defaultdict

def parse_k6_json(filepath):
    """Parse le fichier JSON de K6 et extrait les métriques"""
    metrics = {
        'timestamps': [],
        'vus': [],
        'http_reqs': [],
        'http_req_duration': [],
        'http_req_duration_time': [],
        'http_req_failed': [],
        'checks': [],
        'checks_time': []
    }
    
    with open(filepath, 'r') as f:
        for line in f:
            data = json.loads(line.strip())
            
            if data['type'] == 'Point':
                timestamp = datetime.fromisoformat(data['data']['time'].replace('Z', '+00:00'))
                metric_name = data['metric']
                value = data['data']['value']
                
                if metric_name == 'vus':
                    metrics['timestamps'].append(timestamp)
                    metrics['vus'].append(value)
                elif metric_name == 'http_reqs':
                    metrics['http_reqs'].append(value)
                elif metric_name == 'http_req_duration':
                    metrics['http_req_duration'].append(value)
                    metrics['http_req_duration_time'].append(timestamp)
                elif metric_name == 'http_req_failed':
                    metrics['http_req_failed'].append(value)
                elif metric_name == 'checks':
                    metrics['checks'].append(value)
                    metrics['checks_time'].append(timestamp)
    
    return metrics

def create_dashboard(metrics, output_file='k6_dashboard.png'):
    """Crée un dashboard avec plusieurs graphiques"""
    fig, axes = plt.subplots(2, 2, figsize=(16, 10))
    fig.suptitle('K6 Load Test Dashboard', fontsize=16, fontweight='bold')
    
    # Convertir timestamps en secondes relatives
    if metrics['timestamps']:
        start_time = metrics['timestamps'][0]
        time_seconds = [(t - start_time).total_seconds() for t in metrics['timestamps']]
        
        # Graphique 1: Virtual Users (Rampe)
        ax1 = axes[0, 0]
        ax1.plot(time_seconds, metrics['vus'], linewidth=2, color='#2E86AB')
        ax1.fill_between(time_seconds, metrics['vus'], alpha=0.3, color='#2E86AB')
        ax1.set_title('Virtual Users (VUs) - Rampe de charge', fontweight='bold')
        ax1.set_xlabel('Temps (secondes)')
        ax1.set_ylabel('Nombre de VUs')
        ax1.grid(True, alpha=0.3)
        ax1.set_ylim(bottom=0)
        
        # Graphique 2: HTTP Request Duration
        ax2 = axes[0, 1]
        if metrics['http_req_duration'] and metrics['http_req_duration_time']:
            # Utiliser les timestamps spécifiques aux durées
            start_time = metrics['timestamps'][0]
            duration_time_seconds = [(t - start_time).total_seconds() 
                                    for t in metrics['http_req_duration_time']]
            
            # Grouper par intervalle de temps pour calculer percentiles
            df = pd.DataFrame({
                'time': duration_time_seconds,
                'duration': metrics['http_req_duration']
            })
            # Grouper par tranches de 10 secondes
            df['time_bucket'] = (df['time'] // 10) * 10
            grouped = df.groupby('time_bucket')['duration'].agg(['mean', 'median', 
                                                                  lambda x: x.quantile(0.95),
                                                                  lambda x: x.quantile(0.99)])
            grouped.columns = ['mean', 'p50', 'p95', 'p99']
            
            ax2.plot(grouped.index, grouped['p50'], label='P50', linewidth=2, color='#06A77D')
            ax2.plot(grouped.index, grouped['p95'], label='P95', linewidth=2, color='#F77F00')
            ax2.plot(grouped.index, grouped['p99'], label='P99', linewidth=2, color='#D62828')
            ax2.axhline(y=200, color='green', linestyle='--', alpha=0.5, label='Seuil P50 (200ms)')
            ax2.axhline(y=500, color='orange', linestyle='--', alpha=0.5, label='Seuil P95 (500ms)')
            ax2.set_title('Temps de réponse HTTP', fontweight='bold')
            ax2.set_xlabel('Temps (secondes)')
            ax2.set_ylabel('Durée (ms)')
            ax2.legend(loc='upper left')
            ax2.grid(True, alpha=0.3)
        
        # Graphique 3: HTTP Requests Rate
        ax3 = axes[1, 0]
        if len(metrics['http_reqs']) > 1 and len(time_seconds) > 10:
            # Calculer le rate (requêtes par seconde)
            req_rate = []
            time_rate = []
            window = min(10, len(metrics['http_reqs']) // 2)  # Fenêtre adaptative
            max_index = min(len(metrics['http_reqs']), len(time_seconds))
            
            for i in range(window, max_index):
                rate = (metrics['http_reqs'][i] - metrics['http_reqs'][i-window])
                req_rate.append(rate)
                time_rate.append(time_seconds[i])
            
            if req_rate:  # Vérifier qu'on a des données
                ax3.plot(time_rate, req_rate, linewidth=2, color='#06A77D')
                ax3.fill_between(time_rate, req_rate, alpha=0.3, color='#06A77D')
                ax3.set_title('Débit de requêtes HTTP', fontweight='bold')
                ax3.set_xlabel('Temps (secondes)')
                ax3.set_ylabel('Requêtes (sur fenêtre glissante)')
                ax3.grid(True, alpha=0.3)
            else:
                ax3.text(0.5, 0.5, 'Pas assez de données', 
                        ha='center', va='center', transform=ax3.transAxes)
                ax3.set_title('Débit de requêtes HTTP', fontweight='bold')
        else:
            ax3.text(0.5, 0.5, 'Données insuffisantes pour le débit', 
                    ha='center', va='center', transform=ax3.transAxes)
            ax3.set_title('Débit de requêtes HTTP', fontweight='bold')
        
        # Graphique 4: Success Rate
        ax4 = axes[1, 1]
        if metrics['checks'] and metrics['checks_time']:
            start_time = metrics['timestamps'][0]
            checks_time_seconds = [(t - start_time).total_seconds() 
                                  for t in metrics['checks_time']]
            
            # Calculer le taux de succès
            success_rate = [v * 100 for v in metrics['checks']]
            
            ax4.plot(checks_time_seconds, success_rate, linewidth=2, color='#06A77D')
            ax4.fill_between(checks_time_seconds, success_rate, 100, alpha=0.3, 
                           where=[v >= 99 for v in success_rate], color='#06A77D', label='OK (>99%)')
            ax4.fill_between(checks_time_seconds, success_rate, 100, alpha=0.3, 
                           where=[v < 99 for v in success_rate], color='#D62828', label='NOK (<99%)')
            ax4.axhline(y=99, color='orange', linestyle='--', alpha=0.5, label='Seuil (99%)')
            ax4.set_title('Taux de succès des checks', fontweight='bold')
            ax4.set_xlabel('Temps (secondes)')
            ax4.set_ylabel('Succès (%)')
            ax4.set_ylim([95, 100.5])
            ax4.legend(loc='lower left')
            ax4.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"✅ Dashboard sauvegardé : {output_file}")
    plt.show()

def print_summary(metrics):
    """Affiche un résumé textuel des métriques"""
    print("\n" + "="*60)
    print("📊 RÉSUMÉ DES RÉSULTATS K6")
    print("="*60)
    
    if metrics['vus']:
        print(f"\n🔹 Virtual Users:")
        print(f"   • Max VUs: {max(metrics['vus'])}")
        print(f"   • Durée totale: {len(metrics['timestamps'])} points de données")
    
    if metrics['http_req_duration']:
        durations = sorted(metrics['http_req_duration'])
        print(f"\n🔹 Temps de réponse HTTP:")
        print(f"   • Moyenne: {sum(durations)/len(durations):.2f} ms")
        print(f"   • P50 (médiane): {durations[len(durations)//2]:.2f} ms")
        print(f"   • P95: {durations[int(len(durations)*0.95)]:.2f} ms")
        print(f"   • P99: {durations[int(len(durations)*0.99)]:.2f} ms")
        print(f"   • Max: {max(durations):.2f} ms")
    
    if metrics['checks']:
        success_rate = sum(metrics['checks']) / len(metrics['checks']) * 100
        print(f"\n🔹 Checks:")
        print(f"   • Taux de succès: {success_rate:.2f}%")
    
    print("\n" + "="*60 + "\n")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python k6_analyzer.py results.json [output.png]")
        sys.exit(1)
    
    json_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else 'k6_dashboard.png'
    
    print(f"📖 Lecture du fichier: {json_file}")
    metrics = parse_k6_json(json_file)
    
    print_summary(metrics)
    create_dashboard(metrics, output_file)
