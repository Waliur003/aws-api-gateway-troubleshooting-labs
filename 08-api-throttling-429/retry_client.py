import json
import os
import random
import time
import urllib.error
import urllib.request

API_URL = os.environ["API_URL"]

MAX_ATTEMPTS = 5
BASE_DELAY = 0.5
MAX_DELAY = 8.0

for attempt in range(MAX_ATTEMPTS):

    try:
        request = urllib.request.Request(
            API_URL,
            method="GET"
        )

        with urllib.request.urlopen(
            request,
            timeout=10
        ) as response:

            body = json.loads(response.read())

            print("HTTP Status:", response.status)
            print(json.dumps(body, indent=2))

            break

    except urllib.error.HTTPError as error:

        print("HTTP Status:", error.code)

        if error.code != 429:
            raise

        if attempt == MAX_ATTEMPTS - 1:
            print("Maximum retries reached")
            break

        delay_cap = min(
            MAX_DELAY,
            BASE_DELAY * (2 ** attempt)
        )

        delay = random.uniform(0, delay_cap)

        print(f"Retrying after {delay:.2f} seconds")

        time.sleep(delay)
