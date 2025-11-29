import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';
import { commonOptions, createChecks } from './common-options.js';

// Permet de basculer entre SYNC et ASYNC via variable d'environnement
// Usage: k6 run -e MODE=sync test_realistic_scenarios.js
// Usage: k6 run -e MODE=async test_realistic_scenarios.js
// Exécution : k6 run -e MODE=sync --out json=results_realistic_sync.json test_realistic_scenarios.js
// ou utiliser run_comparison.sh pour automatiser
const MODE = __ENV.MODE || 'async';  // 'sync' ou 'async'
const BASE_PATH = MODE === 'sync' ? '/sync' : '';
const BASE_URL = (__ENV.BASE_URL || 'http://localhost:8000') + BASE_PATH;

const errorRate = new Rate('errors');

export const options = commonOptions;

// export const options = {
//   scenarios: {
//     // Scénario 1: Trafic constant (utilisateurs normaux)
//     constant_load: {
//       executor: 'constant-vus',
//       vus: 50,
//       duration: '2m',
//       startTime: '0s',
//     },
    
//     // Scénario 2: Pic soudain (trafic viral, newsletter)
//     spike: {
//       executor: 'ramping-vus',
//       startTime: '2m',
//       stages: [
//         { duration: '10s', target: 200 },  // Pic soudain
//         { duration: '1m', target: 200 },   // Maintien
//         { duration: '10s', target: 50 },   // Retour à la normale
//       ],
//     },
    
//     // Scénario 3: Montée progressive (heure de pointe)
//     gradual_ramp: {
//       executor: 'ramping-arrival-rate',
//       startTime: '3m10s',
//       timeUnit: '1s',
//       preAllocatedVUs: 100,
//       maxVUs: 300,
//       stages: [
//         { duration: '1m', target: 10 },   // 10 req/s
//         { duration: '1m', target: 50 },   // 50 req/s
//         { duration: '1m', target: 100 },  // 100 req/s
//         { duration: '1m', target: 50 },   // Retour
//         { duration: '1m', target: 10 },   // Calm down
//       ],
//     },
//   },
  
//   thresholds: {
//     http_req_duration: ['p(95)<500', 'p(99)<1000'],
//     'http_req_duration{scenario:constant_load}': ['p(95)<300'],
//     'http_req_duration{scenario:spike}': ['p(95)<800'],
//     http_req_failed: ['rate<0.05'],  // 5% d'erreurs max
//     errors: ['rate<0.05'],
//   },
// };

export default function () {
  const responses = http.batch([
    ['GET', `${BASE_URL}/`, null, { tags: { name: 'HomePage', mode: MODE } }],
    ['GET', `${BASE_URL}/?date=2025-10-29`, null, { tags: { name: 'FilterByDate', mode: MODE } }],
  ]);

  responses.forEach((res) => {
    const success = check(res, createChecks(res.name, 1000));    
    errorRate.add(!success);
  });

//   responses.forEach((res) => {
//     const success = check(res, {
//       'status is 200': (r) => r.status === 200,
//       'response time OK': (r) => r.timings.duration < 1000,
//     });
    
//     errorRate.add(!success);
//   });

  // Think time variable selon le scénario
  sleep(Math.random() * 2 + 1);
}