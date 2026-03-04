import requests
import json

url = "http://127.0.0.1:5000/chat"
headers = {"Content-Type": "application/json"}
data = {"message": "Show me all the tables"}

try:
    response = requests.post(url, headers=headers, json=data)
    print("Status:", response.status_code)
    print("Response payload:")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print("Error:", e)
