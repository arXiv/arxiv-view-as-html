from google.cloud import storage

def get_google_storage_client () -> storage.Client:
    return storage.Client()