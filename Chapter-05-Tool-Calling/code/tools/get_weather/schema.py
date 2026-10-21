get_weather_tool = {
    'type': 'function',
    'function': {
        'name': 'get_weather',
        'description': 'Fetch current weather for a given location (Seattle or London)',
        'parameters': {
            'type': 'object',
            'required': ['place'],
            'properties': {
                'place': {'type': 'string', 'description': 'The name of the place to get weather for (Seattle or London)'},
            },
        },
    },
}
