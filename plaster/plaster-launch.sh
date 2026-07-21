#!/usr/bin/env bash

# Go to the project root directory where the package lives
cd "$(dirname "${BASH_SOURCE[0]}")"

# Run the module using python3, matching your working command
exec python3 -m plaster.main
