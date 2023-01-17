import functions_framework
import requests

CLOUD_RUN_URL = "https://latexml-conversion-gp2ubwi5mq-uc.a.run.app"

@functions_framework.cloud_event
def on_tex_source_uploaded (cloud_event):
    requests.post(CLOUD_RUN_URL, cloud_event.data)