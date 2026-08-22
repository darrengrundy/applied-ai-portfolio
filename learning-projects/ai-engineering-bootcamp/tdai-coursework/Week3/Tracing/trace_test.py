import os
from dotenv import load_dotenv

load_dotenv()

from openai import OpenAI

# --- OpenTelemetry ---
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
from opentelemetry.instrumentation.openai import OpenAIInstrumentor

# Configure OTEL — export to console and Application Insights
provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
provider.add_span_processor(SimpleSpanProcessor(AzureMonitorTraceExporter(
    connection_string=os.getenv("TRACE_CONNECTION_STRING")
)))
trace.set_tracer_provider(provider)

# Instrument OpenAI so API calls appear as spans
OpenAIInstrumentor().instrument()

# --- Azure OpenAI client ---
client = OpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    base_url=os.getenv("ENDPOINT_URL").rstrip("/") + "/openai/deployments/" + os.getenv("DEPLOYMENT_NAME_GPT_4_mini") + "/",
    default_query={"api-version": os.getenv("API_VERSION")}
)

# --- Chat completion ---
response = client.chat.completions.create(
    model=os.getenv("DEPLOYMENT_NAME_GPT_4_mini"),
    messages=[
        {"role": "user", "content": "Write a short poem about AI."}
    ]
)

print("\n=== MODEL RESPONSE ===\n")
print(response.choices[0].message.content)
