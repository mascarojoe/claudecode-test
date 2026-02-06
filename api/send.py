"""Vercel serverless function to proxy messages to n8n webhook."""

import os
import json
import urllib.request
import urllib.parse
import urllib.error
from http.server import BaseHTTPRequestHandler


class handler(BaseHTTPRequestHandler):
    """Handle incoming requests and proxy to n8n webhook."""

    def do_GET(self):
        # Get webhook URL from environment variable
        webhook_url = os.environ.get("N8N_WEBHOOK_URL")

        if not webhook_url:
            self._send_json({"error": "N8N_WEBHOOK_URL not configured"}, 500)
            return

        # Parse query parameters
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        message = params.get("message", [""])[0]

        if not message:
            self._send_json({"error": "No message provided"}, 400)
            return

        try:
            # Build webhook URL with message parameter
            encoded_message = urllib.parse.quote(message)
            full_url = f"{webhook_url}?message={encoded_message}"

            # Make request to n8n webhook
            req = urllib.request.Request(full_url, method="GET")
            with urllib.request.urlopen(req, timeout=30) as response:
                response_data = response.read().decode("utf-8")

                # Try to parse as JSON, otherwise return as text
                try:
                    data = json.loads(response_data)
                    body = {"response": data}
                except json.JSONDecodeError:
                    body = {"response": response_data}

            self._send_json(body, 200)

        except urllib.error.URLError as e:
            self._send_json({"error": f"Webhook request failed: {str(e)}"}, 500)
        except Exception as e:
            self._send_json({"error": f"Unexpected error: {str(e)}"}, 500)

    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
