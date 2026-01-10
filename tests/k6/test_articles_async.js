import http from 'k6/http';
import { check, sleep } from 'k6';
import { commonOptions, createChecks } from './common-options.js';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';

export const options = commonOptions;

export default function () {
  // Test 1: Page principale (tous les articles)
  let res = http.get(`${BASE_URL}/`, {
    tags: { name: 'HomePage' }
  });
  check(res, createChecks('HomePage', 500));

  sleep(Math.random() * 2 + 1);

  // Test 2: Filtrage par date
  res = http.get(`${BASE_URL}/?date=2025-10-29`, {
    tags: { name: 'FilterByDate' }
  });
  check(res, createChecks('FilterByDate', 600));

  sleep(Math.random() * 2 + 1);
}