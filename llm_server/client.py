import requests

url = "http://localhost:8000/chat/completions"
messages = [
    {"role": "user", "content": "Hello, how are you?"}
]

response = requests.post(url, json={"messages": messages})
print(response.json()) 