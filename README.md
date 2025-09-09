# BadPie
## Proof-of-concept Python package index/mirror proxy tool

![BadPie Logo](BadPie.png)

**Dependencies**

- python3
- flask>=2.0.0
- requests>=2.25.0

**Usage**

```
python3 app_hash_modify.py
# or
python3 app_hash_remove.py
```

**Overview**

BadPie is a proof-of-concept Python package index/mirror proxy tool that demonstrates supply chain attack vectors by intercepting and modifying Python packages during installation.

The tool implements two different approaches:

- **app_hash_modify.py** - Preserves and updates SHA256 hashes for modified packages
- **app_hash_remove.py** - Strips SHA256 hashes from package URLs to bypass verification

**Examples**

Start the malicious PyPI mirror:

```
python3 app_hash_modify.py
 * Running on http://127.0.0.1:5000
 * Debug mode: off
```

Configure pip to use the malicious mirror and install a package:

```
pip install --index-url http://localhost:5000/simple/ requests
Looking in indexes: http://localhost:5000/simple/
Collecting requests>=2.31.0
  Downloading http://localhost:5000/simple/requests/requests-2.32.4-py3-none-any.whl.metadata (4.9 kB)
--snip---
Installing collected packages: urllib3, idna, charset_normalizer, certifi, requests
Successfully installed certifi-2025.8.3 charset_normalizer-3.4.2 idna-3.10 requests-2.32.4 urllib3-2.5.0
```

The package has been modified bbut pip verification passes due to hash manipulation.

**Configuration**

Modify the `PACKAGES_TO_MODIFY` list to target specific packages:

```python
PACKAGES_TO_MODIFY = ["requests", "urllib3", "certifi"]
```

Update `MODIFICATION_CODE` to inject your payload:

```python
MODIFICATION_CODE = '''
# Your code here
print('hello world')
'''
```

**Technical Details**

- Intercepts package index requests and rewrites URLs to point to the malicious mirror
- Downloads original packages from PyPI and modifies wheel files on-the-fly
- Injects malicious code into `__init__.py` files of target packages
- Caches modified packages for subsequent requests to improve performance
- Handles SHA256 hash verification through preservation/updating or removal

**Disclaimer**

**For informational and educational purposes only.** This tool is intended for security research, penetration testing, and educational demonstrations. Do not use this tool for malicious purposes or against systems you do not own or have explicit permission to test.

**Author**

- [@dtmsecurity](https://x.com/dtmsecurity)
- [@dtm@infosec.exchange](https://infosec.exchange/@dtm)
- [dtm.uk](https://dtm.uk/)
