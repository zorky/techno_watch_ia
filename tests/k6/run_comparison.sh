#!/bin/bash
# run_comparison.sh

echo "🚀 Démarrage des tests de comparaison SYNC vs ASYNC..."

echo ""
echo "📊 Test 1/2 : Mode ASYNC avec scénarios réalistes..."
k6 run -e MODE=async --out json=results_realistic_async.json test_realistic_scenarios.js

echo ""
echo "📊 Test 2/2 : Mode SYNC avec scénarios réalistes..."
k6 run -e MODE=sync --out json=results_realistic_sync.json test_realistic_scenarios.js

echo ""
echo "📈 Génération du rapport de comparaison..."
python analyse.py results_realistic_async.json results_realistic_sync.json
# python analyse.py

echo ""
echo "✅ Tests terminés ! Consultez comparison.png pour les graphiques."