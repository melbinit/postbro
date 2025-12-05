import requests
import json

headers = {
    "Authorization": "Bearer 75bce21d87491d0436be141991c08467ad2cfc87b46719d32894b541b90babad",
    "Content-Type": "application/json",
}

data = json.dumps({
    "input": [{"url":"https://www.youtube.com/watch?v=bTTd5qtzpZs","country":"","transcription_language":""}],
})

response = requests.post(
    "https://api.brightdata.com/datasets/v3/scrape?dataset_id=gd_lk56epmy2i5g7lzu0k&notify=false&include_errors=true",
    headers=headers,
    data=data
)

print(response.json())