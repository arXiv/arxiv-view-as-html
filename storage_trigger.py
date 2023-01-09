import functions_framework
import requests

CLOUD_RUN_URL = "https://some-address-here/"

@functions_framework.cloud_event
def on_tex_source_uploaded (cloud_event):
    requests.post(CLOUD_RUN_URL, cloud_event.data)