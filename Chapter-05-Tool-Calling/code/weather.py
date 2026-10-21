import requests

def print_weather_data(data, location_name="Location"):
    """
    Format weather data from Open-Meteo API into a readable string.
    """
    # Weather code descriptions (WMO Weather interpretation codes)
    weather_codes = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Foggy",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snow",
        73: "Moderate snow",
        75: "Heavy snow",
        77: "Snow grains",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        85: "Slight snow showers",
        86: "Heavy snow showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail"
    }

    # Extract current weather data
    current = data['current_weather']
    temp = current['temperature']
    windspeed = current['windspeed']
    winddirection = current['winddirection']
    weathercode = current['weathercode']
    is_day = current['is_day']

    # Get weather description
    weather_desc = weather_codes.get(weathercode, f"Unknown (code {weathercode})")

    # Determine day or night
    time_of_day = "☀️ Day" if is_day else "🌙 Night"

    lines = [
        "",
        "="*50,
        f"🌍 Weather for {location_name}",
        "="*50,
        f"📍 Location: {data['latitude']}°N, {data['longitude']}°E",
        f"⛰️  Elevation: {data['elevation']}m",
        f"⏰ Time: {current['time']} ({data['timezone_abbreviation']})",
        "",
        f"{time_of_day}",
        f"🌡️  Temperature: {temp}°C",
        f"🌤️  Condition: {weather_desc}",
        f"💨 Wind Speed: {windspeed} km/h",
        f"🧭 Wind Direction: {winddirection}°",
        "="*50,
        "",
    ]
    return "\n".join(lines)

# Get weather for a location (latitude, longitude)
url = "https://api.open-meteo.com/v1/forecast"

places = {
    "Seattle": {
        "latitude": 47.6062,
        "longitude": -122.3321
    },
    "London": {
        "latitude": 51.5074,
        "longitude": -0.1278
    },
}

def get_weather(place="London"):
    """
    Fetch and display weather for a given place
    
    Args:
        place: Name of the place (must exist in places dict). Defaults to "London"
    """
    params = places[place]
    params["current_weather"] = True
    response = requests.get(url, params=params)
    data = response.json()
    
    # Use the formatted output
    return print_weather_data(data, place)

if __name__ == '__main__':
    print(get_weather())