import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter

from prometheus_client import start_http_server
from opentelemetry.exporter.prometheus import PrometheusMetricReader

def setup_telemetry(service_name: str,
                    endpoint: str):
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)

    exporter = OTLPSpanExporter(endpoint=endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))

    trace.set_tracer_provider(provider)

    # Add metrics
    reader = PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=endpoint))
    metrics.set_meter_provider(MeterProvider(metric_readers=[reader]))
    meter = metrics.get_meter(__name__)
    request_counter = meter.create_counter("http.requests", description="Total requests")

    start_http_server(8099)  # Prometheus scrapes this endpoint
    reader = PrometheusMetricReader()
    # metrics.set_meter_provider(MeterProvider(metric_readers=[reader]))  
    


    