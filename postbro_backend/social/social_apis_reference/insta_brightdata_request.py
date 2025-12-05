import requests
import json

headers = {
    "Authorization": "Bearer 75bce21d87491d0436be141991c08467ad2cfc87b46719d32894b541b90babad",
    "Content-Type": "application/json",
}

data = json.dumps({
    "input": [{"url":"https://www.instagram.com/gymshark/p/DRSgo06CN4o/"}],
})

response = requests.post(
    "https://api.brightdata.com/datasets/v3/scrape?dataset_id=gd_lk5ns7kz21pck8jpis&notify=false&include_errors=true",
    headers=headers,
    data=data
)

print(response.json())