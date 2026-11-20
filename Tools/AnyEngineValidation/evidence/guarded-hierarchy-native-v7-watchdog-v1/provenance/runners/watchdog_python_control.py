"""One read-only independent loopback observation, never a business retry."""
import argparse
import http.client
import json
import time
from urllib.parse import urlsplit

parser = argparse.ArgumentParser()
parser.add_argument('--endpoint', required=True)
parser.add_argument('--path', choices=('/v1/auth', '/v1/health'), required=True)
parser.add_argument('--request-id', required=True)
args = parser.parse_args()
url = urlsplit(args.endpoint)
if url.scheme != 'http' or url.hostname != '127.0.0.1' or not url.port or url.path or url.query or url.fragment or url.username:
    raise SystemExit('owned_loopback_required')
start = time.monotonic()
result = {'phase': 'independent-python-control', 'method': 'GET', 'path': args.path,
          'originalRequestID': args.request_id, 'timestampUnixMs': time.time_ns() // 1_000_000,
          'businessResultSupplied': False, 'maximumRequests': 1}
connection = http.client.HTTPConnection('127.0.0.1', url.port, timeout=9)
try:
    # No retries, redirect following, token/header logging or payload export.
    connection.request('GET', args.path, headers={'Content-Type': 'application/json'})
    response = connection.getresponse()
    result['headersTimestampUnixMs'] = time.time_ns() // 1_000_000
    result['status'] = response.status
    length = response.getheader('Content-Length')
    if length is not None:
        result['contentLength'] = int(length) if length.isascii() and length.isdigit() and len(length) <= 10 else 'invalid'
    encoding = response.getheader('Transfer-Encoding')
    if encoding is not None:
        result['transferEncoding'] = encoding.lower() if encoding.lower() in ('chunked', 'identity') else 'other'
    raw = response.read(65537)
    result['byteCount'] = len(raw)
    result['completeWithinBound'] = len(raw) <= 65536
    result['outcome'] = 'response' if len(raw) <= 65536 else 'response_over_bound'
except Exception as error:
    # Types only; exceptions may contain URLs or arbitrary server material.
    result['outcome'] = 'transport_error'
    result['errorType'] = type(error).__name__
finally:
    connection.close()
    result['finishedTimestampUnixMs'] = time.time_ns() // 1_000_000
    result['elapsedMs'] = int((time.monotonic() - start) * 1000)
print(json.dumps(result, sort_keys=True), flush=True)
