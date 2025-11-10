## Performances tests

K6 https://k6.io/ - https://github.com/grafana/k6 


### Installation 

https://grafana.com/docs/k6/latest/set-up/install-k6/ 

Sous Windows (MSI) : https://github.com/grafana/k6/releases/ ou winget install k6 --source winget

Tests K6 : ~/tests/k6

Vérification installation :

```
$ k6 run --vus 1 --duration 1s test_articles.js
```

Stress 

```
$ k6 run --vus 50 --duration 30s test_articles.js
$ k6 run --vus 50 --duration 30s --out json=results_async.json test_articles.js
```

```
$ k6 run --vus 50 --duration 30s test_articles.js > results_sync.txt 2>&1
```

