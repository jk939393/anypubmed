import os
import json
import quart
import quart_cors
from quart import request, jsonify, Response
import requests
from bs4 import BeautifulSoup

app = quart_cors.cors(quart.Quart(__name__), allow_origin="https://chat.openai.com")

# ENV variables for your Discovery Engine config
PROJECT_ID = os.getenv("PROJECT_ID", "403687177884")
ENGINE_ID = os.getenv("ENGINE_ID", "pubmed_1738348862932")
SERVING_CONFIG_ID = os.getenv("SERVING_CONFIG_ID", "default_search")

# For authentication, you might store a short-lived token or
# a service account key. If you have a service account,
# you'd typically use google.auth, but here's a basic approach:
ACCESS_TOKEN = os.getenv("DISCOVERY_ACCESS_TOKEN", "ya29.a0AXeO80TC7NV0clXgjDAAT9XtumGsFEwOPMM9I1R6C8U8KeIIbvgfHmUwQMMaQOlkklrLrs8KcBXe742tCb1mc9H9dh9Yjv_2ypniTjxETpbJh_goyVvj2f9lkXDhY-xyxwzKFzwcajvyY2cO7XbEE0Ac753GdOhGImoz_PfJaCgYKAdMSARMSFQHGX2MijrqpNZgvKNjS5V1kwNQllw0175")

# Build the Discovery Engine servingConfigs endpoint
DISCOVERY_ENDPOINT = (
    f"https://discoveryengine.googleapis.com/v1alpha/"
    f"projects/{PROJECT_ID}/locations/global/collections/default_collection/"
    f"engines/{ENGINE_ID}/servingConfigs/{SERVING_CONFIG_ID}:search"
)

@app.route("/vertex_pubmed_search", methods=["POST"])
async def get_pubmed_search_results():
    """
    POST /vertex_pubmed_search
    Expects JSON body with { "query": <string>, "pageSize": <int> }.
    Calls Vertex AI Search (Discovery Engine) and returns the result.
    """
    try:
        body = await request.get_json()
        query = body.get("query", "Alzheimer's")  # default if missing
        page_size = body.get("pageSize", 5)

        request_body = {
            "query": query,
            "pageSize": page_size,
            "queryExpansionSpec": { "condition": "AUTO" },
            "spellCorrectionSpec": { "mode": "AUTO" }
        }

        headers = {
            "Authorization": f"Bearer {ACCESS_TOKEN}",
            "Content-Type": "application/json"
        }

        resp = requests.post(DISCOVERY_ENDPOINT, headers=headers, json=request_body)
        if resp.status_code != 200:
            return jsonify({
                "error": f"Discovery Engine call failed with status {resp.status_code}",
                "details": resp.text
            }), resp.status_code

        # Return the raw JSON from Discovery Engine
        return jsonify(resp.json()), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/get_full_abstract", methods=["POST"])
async def get_full_abstract():
    """
    POST /get_full_abstract
    Expects JSON body with { "url": "..." }.
    Fetches the URL's HTML and returns extracted text paragraphs.
    """
    try:
        body = await request.get_json()
        url = body.get("url")
        if not url:
            return jsonify({"error": "No URL provided"}), 400

        # Simple fetch (no advanced parsing)
        resp = requests.get(url)
        if resp.status_code != 200:
            return jsonify({"error": f"Failed to retrieve URL: {resp.status_code}"}), 400

        # Very basic 'paragraph' extraction
        text_lines = resp.text.split("\n")

        return jsonify({"data": text_lines}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/openapi.yaml", methods=["GET"])
async def openapi_spec():
    """
    Serve local openapi.yaml, so ChatGPT can discover endpoints.
    """
    try:
        with open("openapi.yaml") as f:
            spec = f.read()
        return Response(spec, mimetype="text/yaml")
    except FileNotFoundError:
        return Response("openapi.yaml not found", status=404)

@app.route("/.well-known/ai-plugin.json", methods=['GET'])
async def plugin_manifest():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://anypubmed.anygpt.ai/.well-known/ai-plugin.json")
        print(f"Request headers: {request.headers}")
        print(f"Current working directory: {os.getcwd()}")

        print(f"Received response: {response.text}")  # Print the response

        if response.status_code == 200:
            json_data = response.text  # Get the JSON as a string
            return Response(json_data, mimetype="application/json")
        else:
            return f"Failed to fetch data. Status code: {response.status_code}", 400
    except Exception as e:
        print(f"An error occurred: {e}")  # Print the exception
        return str(e), 500

@app.get("/logo.png")
async def plugin_logo():
    filename = 'logo.png'
    return await quart.send_file(filename, mimetype='image/png')

def main():
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
