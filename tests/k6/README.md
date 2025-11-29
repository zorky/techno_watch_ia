## Performances tests

K6 https://k6.io/ - https://github.com/grafana/k6 


### Installation 

https://grafana.com/docs/k6/latest/set-up/install-k6/ 

Sous Windows (MSI) : https://github.com/grafana/k6/releases/ ou winget install k6 --source winget

Tests K6 : ~/tests/k6

Vérification installation :

```bash
$ k6 run --vus 1 --duration 1s test_articles_async.js
$ k6 run --vus 1 --duration 1s test_articles_sync.js
```

### Stressing

Lancer uvicorn avec 4 ou + workers, sans reload et avec un minimum de logs

```bash
$ uvicorn web:app --workers 4 --log-level warning --no-access-log
```

**Stress tests** 

```bash
$ k6 run test_articles_async.js
$ k6 run test_articles_sync.js
```
avec rapport JSON :

```bash
$ k6 run --out json=results_async.json test_articles_async.js
$ k6 run --out json=results_sync.json test_articles_sync.js
```

avec rapport texte :

```bash
$ k6 run test_articles_async.js > results_async.txt 2>&1
$ k6 run test_articles_sync.js > results_sync.txt 2>&1
```

### Rapports

Comparaison avec le script analyse.py : compare les 2 fichiers json async et sync

```bash
$ python analyse.py
```

K6 reporter https://github.com/benc-uk/k6-reporter
