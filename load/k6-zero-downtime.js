// Run during a rolling update to prove zero requests are dropped. Mixes reads
// (GET /api/stats) and writes (POST /api/complaints) — the two paths that
// matter: cached read traffic and the traffic that must never 500.
import http from "k6/http";
import { check, sleep } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://127.0.0.1:8080";
const HOST_HEADER = __ENV.HOST_HEADER || "civicpulse.localhost";

export const options = {
  scenarios: {
    steady: {
      executor: "constant-vus",
      vus: 5,
      duration: __ENV.K6_DURATION || "60s",
    },
  },
  thresholds: {
    http_req_failed: ["rate==0"],
  },
};

const headers = { "Content-Type": "application/json", Host: HOST_HEADER };

export default function () {
  const statsRes = http.get(`${BASE_URL}/api/stats`, { headers });
  check(statsRes, { "stats 200": (r) => r.status === 200 });

  const complaintRes = http.post(
    `${BASE_URL}/api/complaints`,
    JSON.stringify({
      text: "Zero-downtime load test complaint, ignore — streetlight out near G-10 market",
      location: "G-10 Markaz",
    }),
    { headers }
  );
  check(complaintRes, {
    "complaint 201 or 429": (r) => r.status === 201 || r.status === 429,
  });

  sleep(0.2);
}

export function handleSummary(data) {
  return {
    "load/summary.json": JSON.stringify(data),
    stdout: `${data.metrics.http_reqs.values.count} requests, ${data.metrics.http_req_failed.values.passes} failed\n`,
  };
}
