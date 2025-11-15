import json
from collections import defaultdict

ASYNC_FILE = "results_async.json"
SYNC_FILE = "results_sync.json"

def parse_k6_json(filename):
    metrics = defaultdict(list)
    with open(filename, 'r') as f:
        for line in f:
            try:
                data = json.loads(line)
                if data.get('type') == 'Point':
                    metric_name = data['metric']
                    value = data['data']['value']
                    metrics[metric_name].append(value)
            except:
                pass
    return metrics

def calculate_stats(values):
    if not values:
        return {}
    sorted_values = sorted(values)
    return {
        'avg': sum(values) / len(values),
        'min': min(values),
        'max': max(values),
        'p50': sorted_values[len(values) // 2],
        'p95': sorted_values[int(len(values) * 0.95)],
        'p99': sorted_values[int(len(values) * 0.99)],
    }

print("=" * 70)
print("🔥 COMPARAISON SYNC vs ASYNC")
print("=" * 70)

sync_metrics = parse_k6_json(SYNC_FILE)
async_metrics = parse_k6_json(ASYNC_FILE)

sync_duration = calculate_stats(sync_metrics.get('http_req_duration', []))
async_duration = calculate_stats(async_metrics.get('http_req_duration', []))

print("\n📊 TEMPS DE RÉPONSE HTTP (millisecondes)")
print("-" * 70)
print(f"{'Métrique':<15} {'SYNC':>15} {'ASYNC':>15} {'Amélioration':>15}")
print("-" * 70)

for metric in ['avg', 'min', 'max', 'p50', 'p95', 'p99']:
    sync_val = sync_duration.get(metric, 0)
    async_val = async_duration.get(metric, 0)
    improvement = ((sync_val - async_val) / sync_val * 100) if sync_val else 0
    print(f"{metric.upper():<15} {sync_val:>13.2f}ms {async_val:>13.2f}ms {improvement:>13.1f}%")

print("\n" + "=" * 70)