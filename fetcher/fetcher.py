#!/usr/bin/env python3
"""
File Fetcher with Caching
"""
import urllib.request
import urllib.parse
import re
import sys
import json
import os
import time

# Platform URLs Single Source of Truth
# "FOLDER_NAME": "YOUR_LINK_GOES_HERE",
PLATFORM_URLS = {
    "pico-8": "https://github.com/amosjerbi/fetcher/tree/main/pico-8",
}

CACHE_DIR = "/tmp/file_cache"
CACHE_EXPIRY = 3600  # 1 hour cache

def ensure_cache_dir():
    """Create cache directory if it doesn't exist"""
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)

def get_cache_file(platform_name):
    """Get cache file path for platform"""
    safe_name = platform_name.replace(" ", "_").replace("/", "_")
    return os.path.join(CACHE_DIR, f"{safe_name}.json")

def is_cache_valid(cache_file):
    """Check if cache file is valid and not expired"""
    if not os.path.exists(cache_file):
        return False
    
    # Check if cache is not too old
    cache_time = os.path.getmtime(cache_file)
    current_time = time.time()
    
    return (current_time - cache_time) < CACHE_EXPIRY

def load_from_cache(cache_file):
    """Load file list from cache"""
    try:
        with open(cache_file, 'r') as f:
            return json.load(f)
    except:
        return None

def save_to_cache(cache_file, data):
    """Save file list to cache"""
    try:
        # Avoid caching empty success payloads that can mask transient source issues.
        if isinstance(data, dict) and data.get("status") == "success" and data.get("count", 0) == 0:
            return
        with open(cache_file, 'w') as f:
            json.dump(data, f)
    except:
        pass

def simple_html_parse(html_content, max_files=999):
    """Complete HTML parsing - get ALL files"""
    # Support common ROM/archive formats across different source sites.
    file_pattern = (
        r'href="([^"]*\.(?:zip|7z|rar|iso|chd|cue|bin|gb|gbc|gba|nds|n64|z64|v64|nes|sfc|smc|gen|md|p8\.png))"'
    )
    matches = re.findall(file_pattern, html_content, flags=re.IGNORECASE)
    
    files = []
    
    for match in matches:
        # Skip parent directory links but allow GitHub blob links
        if match.startswith('../'):
            continue
            
        # Extract filename from GitHub blob URLs like /user/repo/blob/main/file.zip
        if match.startswith('/') and '/blob/' in match:
            # Preserve the repository-relative path after /blob/<branch>/.
            parts = match.split('/')
            try:
                blob_index = parts.index('blob')
                filename = '/'.join(parts[blob_index + 2:])
            except ValueError:
                filename = match.lstrip('/')
        elif match.startswith('/'):
            # Preserve relative path and strip any query/fragment.
            parsed = urllib.parse.urlsplit(match)
            filename = parsed.path.lstrip('/')
            if parsed.query:
                filename = f"{filename}?{parsed.query}"
        elif match.startswith('http://') or match.startswith('https://'):
            # Preserve path/query from external links instead of truncating to basename.
            parsed = urllib.parse.urlsplit(match)
            filename = parsed.path.lstrip('/')
            if parsed.query:
                filename = f"{filename}?{parsed.query}"
        else:
            filename = match
            
        # Clean up the file name for display
        display_name = urllib.parse.unquote(
            os.path.basename(urllib.parse.urlsplit(filename).path)
        )
        lower_name = display_name.lower()
        if lower_name.endswith('.p8.png'):
            display_name = display_name[:-7]  # Remove .p8.png extension for display
        else:
            # Remove one extension for display (e.g. .zip, .gb, .7z).
            display_name = re.sub(r'\.[^.]+$', '', display_name)
        
        files.append({
            "name": display_name,
            "filename": filename  # Use just the filename for download
        })
        
        # Removed the count limit - now gets ALL files
    
    return files

def fetch_file_list(platform_name, max_files=999):
    """Fast file list fetching with caching"""
    ensure_cache_dir()
    cache_file = get_cache_file(platform_name)
    
    # Try cache first
    if is_cache_valid(cache_file):
        print(f"Loading {platform_name} from cache...", file=sys.stderr)
        cached_data = load_from_cache(cache_file)
        if cached_data and cached_data.get("count", 0) > 0:
            return cached_data
    
    if platform_name not in PLATFORM_URLS:
        return {"error": f"Platform {platform_name} not found"}
    
    url = PLATFORM_URLS[platform_name]
    
    try:
        print(f"Fast-fetching {platform_name} files...", file=sys.stderr)
        
        # Create request with optimized headers and timeout
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'File Downloader/1.0 (Fast Fetcher)')
        req.add_header('Connection', 'keep-alive')
        
        response = urllib.request.urlopen(req, timeout=15)  # Increased timeout for better reliability
        html = response.read().decode('utf-8', errors='ignore')
        
        # Fast HTML parsing - only get first 15 files
        files = simple_html_parse(html, max_files)
        
        print(f"Found {len(files)} files (showing first {max_files})", file=sys.stderr)
        
        result = {
            "platform": platform_name,
            "count": len(files),
            "files": files,
            "status": "success",
            "cached": False,
            "note": f"Showing first {max_files} files for speed"
        }
        
        # Save to cache for next time
        save_to_cache(cache_file, result)
        
        return result
        
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        return {"error": f"Failed to fetch files: {str(e)}", "status": "error"}

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 fetcher.py <platform_name>")
        sys.exit(1)
    
    platform = sys.argv[1]
    result = fetch_file_list(platform)
    print(json.dumps(result, indent=2))
