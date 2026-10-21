import requests


def get_persons():
    """
    Fetches a list of person names from the Star Wars API.

    Returns:
        list: A list of person names if the request is successful, otherwise a list with an error message.
    """
    res = requests.get('https://swapi.dev/api/people/')
    if res.status_code == 200:
        data = res.json().get('results', [])
        return [person['name'] for person in data]
    return ['Unable to fetch data']
