#!/bin/bash
#
# update-and-restart.sh
# Pulls latest code from git and restarts the subway server if there are changes.
# Run via cron every 15 minutes.
#
# Crontab entry:
#   */15 * * * * ~/pi-zero/update-and-restart.sh >> ~/logs/update.log 2>&1

REPO_DIR="~/pi-zero"
SERVICE_NAME="subway-display"
LOG_PREFIX="[$(date '+%Y-%m-%d %H:%M:%S')]"

cd "$REPO_DIR" || exit 1

# Fetch latest from remote
git fetch origin main

# Check if there are any changes
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" != "$REMOTE" ]; then
    echo "$LOG_PREFIX Changes detected, pulling updates..."
    git pull origin main
    
    echo "$LOG_PREFIX Restarting $SERVICE_NAME service..."
    sudo systemctl restart "$SERVICE_NAME"
    
    echo "$LOG_PREFIX Service restarted. New commit: $(git rev-parse --short HEAD)"
else
    echo "$LOG_PREFIX No changes detected."
fi