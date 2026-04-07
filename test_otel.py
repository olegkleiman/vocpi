# test_otel.py
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME

resource = Resource.create({SERVICE_NAME: "vocpi-test"})
provider = TracerProvider(resource=resource)

# Send directly to Jaeger HTTP port (14318 = host-mapped port)
exporter = OTLPSpanExporter(endpoint="http://localhost:14318/v1/traces")
provider.add_span_processor(SimpleSpanProcessor(exporter))
trace.set_tracer_provider(provider)

tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span("test-span") as span:
    span.set_attribute("user.id", "123")
    span.set_attribute("terminal.serial", "542-242-668")
    span.set_attribute("environment", "development")

    span.add_event("processing started", attributes={
        "message": "Hello from vocpi!",
        "step": 1
    })

    print("Span created!")

print("Done.")