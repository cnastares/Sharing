#!/bin/bash
# Absolute directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Start the clipsync server in the background
python3 "$DIR/clipsync.py" > /dev/null 2>&1 &

# Start Deskflow GUI
deskflow
