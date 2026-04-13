#!/bin/bash
cd "$(dirname "$0")" || exit 1
source venv/bin/activate
claude "$@"
