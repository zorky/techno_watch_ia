// common-options.js
// Configuration partagée pour les tests K6

// export const options = createOptions({
//   http_req_duration: ['p(50)<100', 'p(95)<300', 'p(99)<800'],
// });

export const commonOptions = {
  scenarios: {
    stress_test: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 10 },   // Monte à 10 users en 30s
        { duration: '1m', target: 50 },    // Monte à 50 users en 1 min
        { duration: '30s', target: 100 },  // Monte à 100 users en 30s
        { duration: '1m', target: 200 },   // Reste à 200 users pendant 1 min
        { duration: '30s', target: 0 },    // Redescend à 0
      ],
      gracefulRampDown: '30s',
    },
  },
  thresholds: {
    http_req_duration: [
      'p(50)<200',   // 50% des requêtes < 200ms
      'p(95)<500',   // 95% des requêtes < 500ms
      'p(99)<1000',  // 99% des requêtes < 1s
    ],
    http_req_failed: ['rate<0.01'],  // Moins de 1% d'erreurs
    checks: ['rate>0.99'],            // 99% des checks doivent passer
    // ...createOptions, // Permet d'ajouter des thresholds spécifiques par test
  },
};

// Helper pour créer des checks standardisés
export function createChecks(name, maxDuration = 500) {
  return {
    [`${name}: status is 200`]: (r) => r.status === 200,
    [`${name}: response time OK`]: (r) => r.timings.duration < maxDuration,
  };
}

// Helper pour le sleep aléatoire
export function randomSleep(min = 1, max = 3) {
  sleep(Math.random() * (max - min) + min);
}
