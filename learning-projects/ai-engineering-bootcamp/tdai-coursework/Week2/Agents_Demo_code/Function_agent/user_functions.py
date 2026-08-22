import json

def fetch_weather(location: str) -> str:
    """Fetch weather for a given city."""
    mock_weather_data = {
        "New York": "Sunny, 25°C",
        "London": "Cloudy, 18°C",
        "Tokyo": "Rainy, 22°C",
        "Melbourne" : "Windy, 17°C"
    }
    weather = mock_weather_data.get(location, "Weather data not available.")
    return json.dumps({"weather": weather})

weather_tool_definition = {
    "name": "fetch_weather",
    "description": "Fetch weather for a given city.",
    "parameters": {
        "type": "object",
        "properties": {
            "location": {
                "type": "string",
                "description": "The city name"
            }
        },
        "required": ["location"]
    }
}