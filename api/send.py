"""Vercel serverless function to proxy messages to n8n webhook."""

import os
import json
import urllib.request
import urllib.parse
import urllib.error


def handler(request):
    """Handle incoming requests and proxy to n8n webhook."""
    from http.server import BaseHTTPRequestHandler

    # Get webhook URL from environment variable
    webhook_url = os.environ.get("N8N_WEBHOOK_URL")

    if not webhook_url:
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": "N8N_WEBHOOK_URL not configured"}),
        }

    # Parse query parameters
    query_string = request.query if hasattr(request, "query") else ""
    if hasattr(request, "args"):
        message = request.args.get("message", "")
    else:
        params = urllib.parse.parse_qs(query_string)
        message = params.get("message", [""])[0]

    if not message:
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": "No message provided"}),
        }

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

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps(body),
        }

    except urllib.error.URLError as e:
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": f"Webhook request failed: {str(e)}"}),
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
            },
            "body": json.dumps({"error": f"Unexpected error: {str(e)}"}),
        }
