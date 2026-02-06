#!/usr/bin/env python3
"""Simple HTTP server with n8n webhook integration for local development."""

import http.server
import os
import urllib.request
import urllib.parse
import json
from pathlib import Path

PORT = 8000

# Read webhook URL from environment variable
N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL", "")

if not N8N_WEBHOOK_URL:
    print("WARNING: N8N_WEBHOOK_URL environment variable not set.")
    print("Set it with: export N8N_WEBHOOK_URL='your-webhook-url'")
    print("Or create a .env.local file with: N8N_WEBHOOK_URL=your-webhook-url")


class ChatHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/" or parsed.path == "/index.html":
            self.serve_file("index.html", "text/html")
        elif parsed.path == "/api/send":
            self.handle_send(parsed.query)
        else:
            self.send_error(404, "Not Found")

    def serve_file(self, filepath, content_type):
        try:
            file_path = Path(__file__).parent / filepath
            content = file_path.read_text()
            self.send_response(200)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.end_headers()
            self.wfile.write(content.encode())
        except FileNotFoundError:
            self.send_error(404, "File Not Found")

    def handle_send(self, query_string):
        params = urllib.parse.parse_qs(query_string)
        message = params.get("message", [""])[0]

        if not message:
            self.send_json({"error": "No message provided"}, 400)
            return

        try:
            # Build webhook URL with message parameter
            encoded_message = urllib.parse.quote(message)
            webhook_url = f"{N8N_WEBHOOK_URL}?message={encoded_message}"

            # Make request to n8n webhook
            req = urllib.request.Request(webhook_url, method="GET")
            with urllib.request.urlopen(req, timeout=30) as response:
                response_data = response.read().decode("utf-8")

                # Try to parse as JSON, otherwise return as text
                try:
                    data = json.loads(response_data)
                    self.send_json({"response": data})
                except json.JSONDecodeError:
                    self.send_json({"response": response_data})

        except urllib.error.URLError as e:
            self.send_json({"error": f"Webhook request failed: {str(e)}"}, 500)
        except Exception as e:
            self.send_json({"error": f"Unexpected error: {str(e)}"}, 500)

    def send_json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {format % args}")


def main():
    server = http.server.HTTPServer(("", PORT), ChatHandler)
    print(f"Server running at http://localhost:{PORT}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")
        server.shutdown()


if __name__ == "__main__":
    main()
