import collections
import concurrent.futures
import os
import urllib.error
import urllib.request

API_URL = os.environ["API_URL"]

TOTAL_REQUESTS = 30
MAX_WORKERS = 10


def send_request(number):
    request = urllib.request.Request(
        API_URL,
        method="GET"
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=10
        ) as response:
            return number, response.status

    except urllib.error.HTTPError as error:
        return number, error.code

    except Exception as error:
        return number, str(error)


with concurrent.futures.ThreadPoolExecutor(
    max_workers=MAX_WORKERS
) as executor:

    results = list(
        executor.map(
            send_request,
            range(1, TOTAL_REQUESTS + 1)
        )
    )

counts = collections.Counter()

for number, status in results:
    print(f"Request {number:02d}: {status}")
    counts[str(status)] += 1

print("\nSummary:")

for status, count in sorted(counts.items()):
    print(f"HTTP {status}: {count}")
