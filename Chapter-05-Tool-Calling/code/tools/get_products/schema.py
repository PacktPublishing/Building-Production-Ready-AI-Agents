get_products_tool = {
    'type': 'function',
    'function': {
        'name': 'get_products',
        'description': 'Fetch a list of product names from the database, optionally filtered by max price.',
        'parameters': {
            'type': 'object',
            'required': [],
            'properties': {
                'max_price': {'type': 'number', 'description': 'Optional max price filter (e.g., 500)'},
            },
        },
    },
}
