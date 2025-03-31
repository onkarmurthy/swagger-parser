# API Client Generator

This project is a Python-based API client generator that dynamically creates client classes from a Swagger (OpenAPI) JSON specification. It helps automate API consumption by generating request methods, data models, and services based on the provided API definition.

## Features

- **Automatic Class Generation**: Converts OpenAPI definitions into Python data classes and service clients.
- **Enum Support**: Generates Enums for API-defined enumeration values.
- **Dependency Sorting**: Ensures correct ordering of model definitions based on dependencies.
- **Service Client Classes**: Creates API request functions for each defined endpoint.
- **Request Handling**: Supports path, query, and body parameters in API calls.

## Installation

To use this tool, you need Python 3.7+ and `requests` library installed. Install dependencies with:

```sh
pip install requests
```

## Usage

### Generate API Client

Run the script with a Swagger URL to generate an API client:

```sh
python generate_api.py
```

By default, the script fetches the Swagger JSON from `https://petstore.swagger.io/v2/swagger.json`. You can modify this URL in the script or pass a local JSON file.

### Example Usage of Generated Client

After generating the `generated_api.py` file, you can use it as follows:

```python
from generated_api import APIClient

api_client = APIClient(base_url="https://api.example.com", api_key="your_api_key")

# Example API Call
response = api_client.pet_service.get_pet_by_id(pet_id=123)
print(response)
```

### Sample Output

```json
{
  "id": 123,
  "name": "Fluffy",
  "status": "available"
}
```

### Generated File Output

```python
class userService:
    def __init__(self, base_url, headers):
        self.base_url = base_url
        self.headers = headers
    
    def create_users_with_list_input(self, ) -> Any:
        url = f"{self.base_url}/user/createWithList"
        params = {} if [] else None
        headers = self.headers

        response = requests.post(url, headers=headers, params=params, json=None)
        return response.json() if response.status_code == 200 else response.json()
            
    def get_user_by_name(self, username) -> User:
        url = f"{self.base_url}/user/{username}"
        params = {} if [] else None
        headers = self.headers

        response = requests.get(url, headers=headers, params=params, json=None)
        return response.json() if response.status_code == 200 else response.json()
            
    def update_user(self, username, data: User) -> Any:
        url = f"{self.base_url}/user/{username}"
        params = {} if [] else None
        headers = self.headers

        response = requests.put(url, headers=headers, params=params, json=data.__dict__ if isinstance(data, User) else data)
        return response.json() if response.status_code == 200 else response.json()
            
    def delete_user(self, username) -> Any:
        url = f"{self.base_url}/user/{username}"
        params = {} if [] else None
        headers = self.headers

        response = requests.delete(url, headers=headers, params=params, json=None)
        return response.json() if response.status_code == 200 else response.json()
            
    def login_user(self, username, password) -> Any:
        url = f"{self.base_url}/user/login"
        params = {"username": username, "password": password} if ['username', 'password'] else None
        headers = self.headers

        response = requests.get(url, headers=headers, params=params, json=None)
        return response.json() if response.status_code == 200 else response.json()
            
    def logout_user(self, ) -> Any:
        url = f"{self.base_url}/user/logout"
        params = {} if [] else None
        headers = self.headers

        response = requests.get(url, headers=headers, params=params, json=None)
        return response.json() if response.status_code == 200 else response.json()
            
    def create_users_with_array_input(self, ) -> Any:
        url = f"{self.base_url}/user/createWithArray"
        params = {} if [] else None
        headers = self.headers

        response = requests.post(url, headers=headers, params=params, json=None)
        return response.json() if response.status_code == 200 else response.json()
            
    def create_user(self, data: User) -> Any:
        url = f"{self.base_url}/user"
        params = {} if [] else None
        headers = self.headers

        response = requests.post(url, headers=headers, params=params, json=data.__dict__ if isinstance(data, User) else data)
        return response.json() if response.status_code == 200 else response.json()
            
        
class APIClient:
    def __init__(self, base_url, api_key=None):
        self.base_url = base_url
        self.headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}" if api_key else None}
        self.userservice = userService(self.base_url, self.headers)
```

After generating the `generated_api.py` file, you can use it as follows:

```python
from generated_api import APIClient

api_client = APIClient(base_url="https://api.example.com", api_key="your_api_key")

# Example API Call
response = api_client.pet_service.get_pet_by_id(pet_id=123)
print(response)
```

### Sample Output

```json
{
  "id": 123,
  "name": "Fluffy",
  "status": "available"
}
```

After generating the `generated_api.py` file, you can use it as follows:

```python
from generated_api import APIClient

api_client = APIClient(base_url="https://api.example.com", api_key="your_api_key")

# Example API Call
response = api_client.pet_service.get_pet_by_id(pet_id=123)
print(response)
```

## Configuration

Modify `generate_api.py` to customize:
- API base URL
- Authentication headers
- Request timeout settings

## Contributing

Feel free to open issues and contribute via pull requests. If you encounter any bugs or want to add enhancements, contributions are welcome!

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

