import requests

def get_jsonplaceholder_data():
    """Fetch data from jsonplaceholder posts endpoint."""
    url = 'https://jsonplaceholder.typicode.com/posts/1'
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f'Error fetching data: {e}')
        return None

if __name__ == '__main__':
    data = get_jsonplaceholder_data()
    if data:
        print('Data received:', data)
    else:
        print('No data received.')