// Traces every fetch() call the SPA makes (i.e. every /api/* request) and
// exports them via OTLP/HTTP to a *relative* path - never an absolute
// collector URL, matching the same rule the API client already follows
// (see docs/adr/0002-frontend-runtime-config.md).
import { WebTracerProvider } from "@opentelemetry/sdk-trace-web";
import { BatchSpanProcessor } from "@opentelemetry/sdk-trace-base";
import { OTLPTraceExporter } from "@opentelemetry/exporter-trace-otlp-http";
import { registerInstrumentations } from "@opentelemetry/instrumentation";
import { FetchInstrumentation } from "@opentelemetry/instrumentation-fetch";
import { resourceFromAttributes } from "@opentelemetry/resources";
import { ATTR_SERVICE_NAME } from "@opentelemetry/semantic-conventions";

export function initTelemetry(): void {
  const provider = new WebTracerProvider({
    resource: resourceFromAttributes({ [ATTR_SERVICE_NAME]: "civicpulse-frontend" }),
    spanProcessors: [new BatchSpanProcessor(new OTLPTraceExporter({ url: "/otlp/v1/traces" }))],
  });
  provider.register();

  registerInstrumentations({
    instrumentations: [
      new FetchInstrumentation({
        propagateTraceHeaderCorsUrls: [/\/api\//],
        ignoreUrls: [/\/otlp\//],
      }),
    ],
  });
}
