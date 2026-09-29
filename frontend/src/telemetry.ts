/**
 * OpenTelemetry Web tracing: instruments the SPA's own fetch calls to /api and
 * exports spans to Jaeger, same-origin through nginx's /otel/ proxy (see nginx.conf)
 * - never a baked-in Jaeger URL, matching ADR 0002's runtime-config approach for /api.
 * A no-op in effect if Jaeger isn't running: the exporter just fails silently.
 */
import { registerInstrumentations } from "@opentelemetry/instrumentation";
import { FetchInstrumentation } from "@opentelemetry/instrumentation-fetch";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";
import { Resource } from "@opentelemetry/resources";
import { ATTR_SERVICE_NAME } from "@opentelemetry/semantic-conventions";
import { BatchSpanProcessor } from "@opentelemetry/sdk-trace-base";
import { WebTracerProvider } from "@opentelemetry/sdk-trace-web";

export function initTelemetry(): void {
  const provider = new WebTracerProvider({
    resource: new Resource({ [ATTR_SERVICE_NAME]: "civicpulse-frontend" }),
  });
  provider.addSpanProcessor(
    new BatchSpanProcessor(
      new OTLPTraceExporter({ url: `${window.location.origin}/otel/v1/traces` }),
    ),
  );
  provider.register();

  registerInstrumentations({
    instrumentations: [
      new FetchInstrumentation({
        propagateTraceHeaderCorsUrls: [new RegExp(`^${window.location.origin}/api/`)],
      }),
    ],
  });
}
