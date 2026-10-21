subtract_two_numbers_tool = {
    'type': 'function',
    'function': {
        'name': 'subtract_two_numbers',
        'description': 'Subtract two numbers',
        'parameters': {
            'type': 'object',
            'required': ['a', 'b'],
            'properties': {
                'a': {'type': 'integer', 'description': 'The first number'},
                'b': {'type': 'integer', 'description': 'The second number'},
            },
        },
    },
}
