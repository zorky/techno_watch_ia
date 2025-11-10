import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '30s', target: 10 },  // Monte à 10 users en 30s
    { duration: '1m', target: 50 },   // Monte à 50 users en 1 min
    { duration: '30s', target: 100 }, // Monte à 100 users en 30s
    { duration: '1m', target: 100 },  // Reste à 100 users pendant 1 min
    { duration: '30s', target: 0 },   // Redescend à 0
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% des requêtes < 500ms
    http_req_failed: ['rate<0.01'],   // Moins de 1% d'erreurs
  },
};

export default function () {
  // Test 1: Page principale (tous les articles)
  let res = http.get('http://localhost:8000/');
  check(res, {
    'status is 200': (r) => r.status === 200,
    'response time < 500ms': (r) => r.timings.duration < 500,
  });

  sleep(1); // Pause de 1s entre les requêtes

  // Test 2: Filtrage par date
  res = http.get('http://localhost:8000/?date=2024');
  check(res, {
    'status is 200': (r) => r.status === 200,
  });

  sleep(1);
}