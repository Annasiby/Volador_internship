import requests

BASE_URL = "https://jsonplaceholder.typicode.com"


def fetch_posts():
    response = requests.get(
        f"{BASE_URL}/posts",
        timeout=10
    )
    response.raise_for_status()
    return response.json()