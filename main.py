import json
import quart
import quart_cors
from bs4 import BeautifulSoup
from quart import Quart, request, Response, send_file, jsonify
import requests
import os
import re
from datetime import datetime
import httpx
import random
#TODO Pubmed dev
mode ="prod"
plab_wellknown = "y"

print("pubmed running dev in mode version 10_20_2023")


API_KEY = "AIzaSyBbvhM0tfQDlrI2ndRbZAN1YKBmwwStIrw"
API_KEY2 = "AIzaSyBbvhM0tfQDlrI2ndRbZAN1YKBmwwStIrw"

CX = "769bcb91a29f24ffa"
CX2 = "769bcb91a29f24ffa"
BASE_URL = "https://www.googleapis.com/customsearch/v1/siterestrict"


app = quart_cors.cors(quart.Quart(__name__), allow_origin="https://chat.openai.com")
#pubmed
@app.route("/google_search/<string:query>", methods=['GET'])
async def get_google_search_results(query, page=1):
    try:
        print(f"Query: {query}")
        random_choice = random.choice([(API_KEY, CX), (API_KEY2, CX2)])
        a, b = random_choice
        # Calculate the start index for pagination
        page = int(request.args.get('page', 1))
        num = int(request.args.get('results',1))
        # Extract dates from the query using a regular expression
        dates = re.findall(
            r'((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},\s+\d{4}|\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}|\d{4})',
            query, re.IGNORECASE)

        # Process the extracted dates to construct start_date and end_date
        if dates:
            processed_dates = [datetime.strptime(date, '%B %d, %Y') if re.match(
                r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}',
                date, re.IGNORECASE) else datetime.strptime(date, '%d %B %Y') if re.match(
                r'\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}',
                date, re.IGNORECASE) else datetime.strptime(date, '%B %Y') if re.match(
                r'(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}',
                date, re.IGNORECASE) else datetime.strptime(date, '%Y') for date in dates]
            start_date = min(processed_dates).strftime('%Y%m%d')
            end_date = max(processed_dates).strftime('%Y%m%d')
        else:
            start_date = None
            end_date = None

        start_index = (page - 1) * 5 + 1

        if start_date and end_date:
            formattedDate = f'date:r:{start_date}:{end_date}'
        else:
            formattedDate = None

        params = {
            "q": query,
            "cx": b,
            "key": a,
            "num": num,
            "start": start_index,
            "sort": formattedDate
        }



        # Print the full URL with all the parameters
        full_url = f"{BASE_URL}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
        print(f"Full URL: {full_url}")

        response = requests.get(BASE_URL, params=params)

        if response.status_code != 200:
            print(f"Unexpected status code from Google: {response.status_code}")
            print(f"Response content: {response.text}")
            return quart.Response(response.text, status=response.status_code)

        data = response.json()

        # Print total results
        total_results = data.get('searchInformation', {}).get('totalResults', 0)

        result_data = []
        for i, item in enumerate(data.get('items', [])):
            result_data.append({
                "index": start_index + i,
                "title": item.get('title'),
                "link": item.get('link'),
                "Abstract Summary": item.get('snippet')
            })

        messages = []
        messages.append(f"you can get the full abstract by saying get full abstract for a specific number. do not forget to say this)")

        messages.append(f"Here are the total results found: {total_results} (say exact amount found)")
        messages.append(f"This was page {page} (do not forget to say this). Please say 'more' for more results.")
        messages.append(
            f"You can specify seeing up to {num} results. You are now seeing {min(num, len(result_data))} results.")
        all_links = [item['link'] for item in result_data]

        # Prepare the result JSON
        result = {
            "role": "assistant",
            "content": messages,
            "current_page": page,
            "total_results": total_results,
            "results": result_data,
            "full_url_list": all_links  # Add this line to include the full URLs

        }

        return quart.Response(json.dumps(result), status=200, content_type='application/json')
    except Exception as e:
        print(f"An error occurred: {e}")
        return quart.Response(f"An error occurred: {e}", status=500)

@app.route("/get_full_abstract", methods=['POST'])
async def get_full_abstract():
    json_data = await request.json
    url = json_data.get("url")

    # Fetch the content of the URL
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Extract text from the webpage
    paragraphs = soup.find_all('p')
    text_content = [p.get_text() for p in paragraphs]

    return jsonify({"data": text_content}), 200

if plab_wellknown == "n":
    print("default well known")
    @app.get("/.well-known/ai-plugin.json")
    async def plugin_manifest():
        host = request.headers['Host']
        with open("./.well-known/ai-plugin.json") as f:
            text = f.read()
            return quart.Response(text, mimetype="text/json")
else:
    print("plab well known")
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






@app.get("/openapi.yaml")
async def openapi_spec():
    host = request.headers['Host']
    with open("openapi.yaml") as f:
        text = f.read()
        return quart.Response(text, mimetype="text/yaml")

if mode == "prod":
    port = int(os.environ.get("PORT", 5000))
if mode == "dev":
    port = 5003
if port == 5000:
    print("PROD PORT")
else:
    print("DEV PORT")

def main():
    app.run(debug=True, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
