from google.cloud import storage
import google.cloud.logging

def get_google_storage_client ():
    return storage.Client()

def get_google_logging_client ():
    logging_client = google.cloud.logging.Client()
    logging_client.setup_logging()
    return logging_client