import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000/sync';

export const options = {
  stages: [
    { duration: '30s', target: 10 },  // Monte à 10 users en 30s
    { duration: '1m', target: 50 },   // Monte à 50 users en 1 min
    { duration: '30s', target: 100 }, // Monte à 100 users en 30s
    { duration: '1m', target: 200 },  // Reste à 200 users pendant 1 min
    { duration: '30s', target: 0 },   // Redescend à 0
  ],
  thresholds: {
    http_req_duration: [
      'p(50)<200',  // 50% des requêtes < 200ms
      'p(95)<500', // 95% des requêtes < 500ms
      'p(99)<1000', // 99% des requêtes < 1s
    ], 
    http_req_failed: ['rate<0.01'],   // Moins de 1% d'erreurs
  },
};

export default function () {
  // Test 1: Page principale (tous les articles)
  let res = http.get(`${BASE_URL}/`, {
      tags: { name: 'HomePage' }
    });
  check(res, {
    'HomePage: status is 200': (r) => r.status === 200,
    'HomePage: response time OK': (r) => r.timings.duration < 500,
  });
  
  sleep(Math.random() * 2 + 1); // Temps de pause entre 1 et 3 secondes pour le comportement

  // Test 2: Filtrage par date  
  res = http.get(`${BASE_URL}/?date=2025-10-29`, {
    tags: { name: 'FilterByDate' }
  });
  check(res, {
    'FilterByDate: status is 200': (r) => r.status === 200,
    'FilterByDate: response time OK': (r) => r.timings.duration < 600,
  });

  sleep(Math.random() * 2 + 1); // Temps de pause entre 1 et 3 secondes pour le comportement
}