## Performances tests

K6 https://k6.io/ - https://github.com/grafana/k6 


### Installation 

https://grafana.com/docs/k6/latest/set-up/install-k6/ 

Sous Windows (MSI) : https://github.com/grafana/k6/releases/ ou winget install k6 --source winget

Tests K6 : ~/tests/k6

Vérification installation :

```
$ k6 run --vus 1 --duration 1s test_articles_async.js
$ k6 run --vus 1 --duration 1s test_articles_sync.js
```

**Stress tests** 

```
$ k6 run --vus 50 --duration 60s test_articles_async.js
$ k6 run --vus 50 --duration 60s test_articles_sync.js
$ k6 run --vus 50 --duration 60s --out json=results_async.json test_articles_async.js
$ k6 run --vus 50 --duration 60s --out json=results_sync.json test_articles_sync.js
```

```
$ k6 run --vus 50 --duration 60s test_articles_async.js > results_async.txt 2>&1
$ k6 run --vus 50 --duration 60s test_articles_sync.js > results_sync.txt 2>&1
```

