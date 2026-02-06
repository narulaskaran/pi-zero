#!/bin/bash
#
# update-and-restart.sh
# Pulls latest code from git and restarts the subway server if there are changes.
# Run via cron every 15 minutes.
#
# Crontab entry:
#   */15 * * * * ~/pi-zero/update-and-restart.sh >> ~/logs/update.log 2>&1

REPO_DIR="$HOME/pi-zero"
SERVICE_NAME="subway-display"
LOG_PREFIX="[$(date '+%Y-%m-%d %H:%M:%S')]"

cd "$REPO_DIR" || exit 1

# Stash any local changes to prevent merge conflicts
if ! git diff-index --quiet HEAD --; then
    echo "$LOG_PREFIX Local changes detected, stashing..."
    git stash push -m "Auto-stash before update $(date '+%Y-%m-%d %H:%M:%S')"
fi

# Fetch latest from remote
git fetch origin main

# Check if there are any changes
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" != "$REMOTE" ]; then
    echo "$LOG_PREFIX Changes detected, pulling updates..."
    git pull origin main

    # Check and install Python dependencies if requirements.txt exists
    if [ -f "subway_train_times/requirements.txt" ]; then
        echo "$LOG_PREFIX Installing/updating Python dependencies..."
        if [ -d "subway_train_times/venv" ]; then
            # Use existing venv
            subway_train_times/venv/bin/pip install -r subway_train_times/requirements.txt --quiet
            echo "$LOG_PREFIX Dependencies updated."
        else
            echo "$LOG_PREFIX Warning: venv not found, skipping dependency installation."
        fi
    fi

    echo "$LOG_PREFIX Restarting $SERVICE_NAME service..."
    sudo systemctl restart "$SERVICE_NAME"

    echo "$LOG_PREFIX Service restarted. New commit: $(git rev-parse --short HEAD)"
else
    echo "$LOG_PREFIX No changes detected."
fi