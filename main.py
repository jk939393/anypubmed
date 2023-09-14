import json

import quart
import quart_cors
from quart import request
import requests
import urllib.parse
API_KEY = "AIzaSyBBqPWmXUkgnessbwHyAueFBPa6UDBMPRo"
CX = "4299ecf0db6824aae"
a=API_KEY
b= CX
BASE_URL = "https://www.googleapis.com/customsearch/v1"


app = quart_cors.cors(quart.Quart(__name__), allow_origin="https://chat.openai.com")
#pubmed


@app.route("/google_search/<string:query>", methods=['GET'])
async def get_google_search_results(query):
    try:
        query = urllib.parse.quote(query)
        print(f"Encoded query: {query}")

        response = requests.get(BASE_URL, params={
            "q": query,
            "cx": CX,
            "key": API_KEY
        })

        if response.status_code != 200:
            print(f"Unexpected status code from Google: {response.status_code}")
            print(f"Response content: {response.text}")
            return quart.Response(response.text, status=response.status_code)

        data = response.json()
        return quart.Response(json.dumps(data), status=200, content_type='application/json')
    except Exception as e:
        print(f"An error occurred: {e}")
        return quart.Response(f"An error occurred: {e}", status=500)



@app.get("/logo.png")
async def plugin_logo():
    filename = 'logo.png'
    return await quart.send_file(filename, mimetype='image/png')

@app.get("/.well-known/ai-plugin.json")
async def plugin_manifest():
    host = request.headers['Host']
    with open("./.well-known/ai-plugin.json") as f:
        text = f.read()
        return quart.Response(text, mimetype="text/json")

@app.get("/openapi.yaml")
async def openapi_spec():
    host = request.headers['Host']
    with open("openapi.yaml") as f:
        text = f.read()
        return quart.Response(text, mimetype="text/yaml")

def main():
    app.run(debug=True, host="0.0.0.0", port=5003)

if __name__ == "__main__":
    main()
