import requests
import logging

class RequestManager:
    def __init__(self, timeout=60, max_retries=5):
        self.timeout = timeout
        self.max_retries = max_retries
        self.logger = logging.getLogger()

    def make_request(self, url):
        for attempt in range(self.max_retries):
            try:
                response = requests.get(url, timeout=self.timeout)
                self.logger.info(f"Request to {url} returned with status code {response.status_code}.")
                return response.status_code
            except requests.Timeout:
                self.logger.warning(f"Timeout occurred for {url}. Attempt {attempt + 1} of {self.max_retries}.")
            except Exception as e:
                self.logger.error(f"An error occurred for {url}: {e}")
                return f"An error occurred: {e}"

        self.logger.error(f"Request failed after {self.max_retries} retries for {url}.")
        return "Request failed after maximum retries."
