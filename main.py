from flask import Flask, request, jsonify, send_file, Response
import requests
import xml.etree.ElementTree as ET
import time
import csv
import io
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def index():
    return send_file('search.html')

@app.route('/process-sites', methods=['POST'])
def process_sites():
    try:
        data = request.get_json()
        sites = data.get('sites', [])
        as_of_date = data.get('asOfDate')

        print(f"Received sites: {sites}")
        print(f"As of date: {as_of_date}")

        # Convert "as of" date to datetime object if provided
        as_of_date_obj = None
        if as_of_date:
            try:
                as_of_date_obj = datetime.strptime(as_of_date, "%Y-%m-%d")
            except ValueError:
                print(f"Invalid date format: {as_of_date}")

        # Collect all URLs from all sites
        all_urls = []
        
        for site in sites:
            sitemap_url = f"https://{site}/sitemap.xml"
            try:
                print(f"Fetching sitemap for {site}...")
                urls = fetch_sitemap(sitemap_url)
                
                for url_data in urls:
                    # Filter by date if provided
                    if as_of_date_obj and url_data.get('lastmod'):
                        try:
                            url_date = datetime.strptime(url_data['lastmod'][:10], "%Y-%m-%d")
                            if url_date < as_of_date_obj:
                                continue
                        except (ValueError, TypeError):
                            pass
                    
                    all_urls.append({
                        'site': site,
                        'url': url_data['url'],
                        'lastmod': url_data.get('lastmod', '')
                    })
                    
            except Exception as e:
                print(f"Error processing {site}: {e}")
                # Add error row
                all_urls.append({
                    'site': site,
                    'url': f"ERROR: {str(e)}",
                    'lastmod': ''
                })

        print(f"Found {len(all_urls)} URLs")
        
        # Return JSON data instead of CSV
        return jsonify(all_urls)
        
    except Exception as e:
        print(f"Error in process_sites: {e}")
        return {"error": str(e)}, 500

def fetch_sitemap(url):
    """
    Fetch and parse a sitemap URL, returning all URLs found along with their last modification dates.
    If the sitemap contains links to other sitemaps, it will recursively fetch them.
    """
    urls = []
    try:
        response = requests.get(url, timeout=30)
        time.sleep(0.1)
        response.raise_for_status()
        root = ET.fromstring(response.content)

        # Check if this sitemap contains links to other sitemaps
        for sitemap in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap"):
            loc = sitemap.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
            if loc is not None:
                print(f"Found nested sitemap: {loc.text}")
                urls.extend(fetch_sitemap(loc.text))  # Recursively fetch nested sitemaps

        # Extract URLs and their last modification dates from the current sitemap
        for url_elem in root.findall(".//{http://www.sitemaps.org/schemas/sitemap/0.9}url"):
            loc = url_elem.find("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")
            lastmod = url_elem.find("{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod")
            if loc is not None:
                urls.append({
                    "url": loc.text,
                    "lastmod": lastmod.text if lastmod is not None else None
                })

    except requests.exceptions.RequestException as e:
        print(f"Error fetching sitemap: {e}")
        raise
    except ET.ParseError as e:
        print(f"Error parsing sitemap: {e}")
        raise

    return urls

if __name__ == '__main__':
    app.run(debug=True, port=5000)