import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 10,
  duration: "60s",
  thresholds: {
    http_req_failed: ["rate==0"],
  },
};

export default function () {
  const res = http.get("http://127.0.0.1:8080/ready", {
    headers: { Host: "civicpulse.localhost" },
  });
  check(res, { "status is 200": (r) => r.status === 200 });
  sleep(0.2);
}
