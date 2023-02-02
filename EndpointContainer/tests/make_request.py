import requests

url = "https://endpoint-gp2ubwi5mq-uc.a.run.app/upload"
myobj = {'somekey': 'somevalue'}
signed_url = requests.post(url, data = myobj)

print(signed_url.content)
