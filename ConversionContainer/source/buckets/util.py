from google.cloud import storage
import google.cloud.logging

def get_google_storage_client ():
    return storage.Client()