#!/bin/bash
# Bridge script to handle downloads from the UI

PLATFORM=$1
PLATFORM_FOLDER=$2
REPO_PATH=$3

if [ -z "$PLATFORM" ]; then
  echo "Usage: $0 <platform> [platform_folder] [repo_path]"
  exit 1
fi

echo "Starting download for $PLATFORM..."
echo "Target folder: /storage/roms/$PLATFORM_FOLDER"
if [ -n "$REPO_PATH" ]; then
  echo "Source path hint: $REPO_PATH"
fi
echo ""

# Create target directory
mkdir -p "/storage/roms/$PLATFORM_FOLDER"

# Launch Python tools with platform pre-selected
cd /storage/roms/ports/fetcher
export PYTHONPATH="./lib:$PYTHONPATH"

# Fetch list using the project's supported source mapping.
platform_json="$(python3 fetcher.py "$PLATFORM" 2>/tmp/fetcher_bridge_err.log)"
if [ $? -ne 0 ] || [ -z "$platform_json" ]; then
  echo "Error fetching file list for $PLATFORM."
  if [ -s /tmp/fetcher_bridge_err.log ]; then
    cat /tmp/fetcher_bridge_err.log
  fi
  exit 1
fi

printf '%s\n' "$platform_json" | python3 -c '
import json
import sys

data = json.load(sys.stdin)
if data.get("status") != "success":
    print(f"Error fetching file list: {data.get('"'"'error'"'"', '"'"'unknown error'"'"')}")
    sys.exit(1)

files = data.get("files", [])
print(f"Found {len(files)} files available for download")
print("First 10 files:")
for i, item in enumerate(files[:10], 1):
    print(f"{i:2d}. {item.get('"'"'filename'"'"', '"'"''"'"')}")
if len(files) > 10:
    print(f"... and {len(files) - 10} more")
'
if [ $? -ne 0 ]; then
  echo "Failed to parse file list output."
  exit 1
fi

echo ""
echo "Download preparation completed!"
