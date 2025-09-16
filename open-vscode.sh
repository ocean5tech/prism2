#!/bin/bash
# Script to open VS Code from WSL
cd /home/wyatt/prism2

# Method 1: Try direct command
code . 2>/dev/null

# Method 2: If failed, try with full path
if [ $? -ne 0 ]; then
    echo "Trying alternative method..."
    cmd.exe /c "code $(wslpath -w $(pwd))"
fi