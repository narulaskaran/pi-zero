#!/bin/bash
#
# setup.sh - Idempotent Raspberry Pi Zero Setup Script
#
# This script provisions a Raspberry Pi system for running the subway display server.
# It is designed to be idempotent - safe to run multiple times without breaking anything.
#
# Usage:
#   sudo ./setup.sh
#
# What it does:
#   1. Installs system dependencies (Python, git, fonts, etc.)
#   2. Creates Python virtual environment for subway_train_times
#   3. Installs Python packages from requirements.txt
#   4. Sets up systemd service for subway-display
#   5. Configures automatic git updates via cron
#
# Requirements:
#   - Must be run with sudo
#   - Git repository must be cloned to user's home directory
#

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SUBWAY_DIR="${SCRIPT_DIR}/subway_train_times"
VENV_DIR="${SUBWAY_DIR}/venv"
SERVICE_NAME="subway-display"
SERVICE_FILE="${SUBWAY_DIR}/subway-display.service"
SYSTEMD_DIR="/etc/systemd/system"
UPDATE_SCRIPT="${SCRIPT_DIR}/update-and-restart.sh"

# Get the actual user (not root) when running with sudo
if [ -n "$SUDO_USER" ]; then
    ACTUAL_USER="$SUDO_USER"
else
    ACTUAL_USER="$(whoami)"
fi
USER_HOME=$(eval echo ~${ACTUAL_USER})
LOG_DIR="${USER_HOME}/logs"

#######################################
# Print colored status messages
#######################################
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_header() {
    echo ""
    echo "========================================"
    echo "$1"
    echo "========================================"
    echo ""
}

#######################################
# Check if script is run with sudo
#######################################
check_sudo() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run with sudo"
        echo "Usage: sudo ./setup.sh"
        exit 1
    fi
    print_status "Running as root/sudo"
}

#######################################
# Install system dependencies
#######################################
install_system_dependencies() {
    print_header "Installing System Dependencies"

    # Update package list
    print_status "Updating package list..."
    apt-get update -qq

    # List of packages to install
    local packages=(
        "python3"
        "python3-pip"
        "python3-venv"
        "git"
        "fonts-dejavu"
        "fonts-roboto"
    )

    # Check and install each package
    for package in "${packages[@]}"; do
        if dpkg -l | grep -q "^ii  ${package} "; then
            print_status "${package} is already installed"
        else
            print_status "Installing ${package}..."
            apt-get install -y -qq "${package}"
        fi
    done

    print_status "System dependencies installed"
}

#######################################
# Create Python virtual environment
#######################################
setup_python_venv() {
    print_header "Setting Up Python Virtual Environment"

    if [ -d "${VENV_DIR}" ]; then
        print_warning "Virtual environment already exists at ${VENV_DIR}"
        print_status "Skipping venv creation"
    else
        print_status "Creating virtual environment at ${VENV_DIR}..."
        su - "${ACTUAL_USER}" -c "python3 -m venv ${VENV_DIR}"
        print_status "Virtual environment created"
    fi

    # Install/upgrade pip in venv
    print_status "Upgrading pip in virtual environment..."
    su - "${ACTUAL_USER}" -c "${VENV_DIR}/bin/pip install --upgrade pip -q"

    # Install Python packages from requirements.txt
    if [ -f "${SUBWAY_DIR}/requirements.txt" ]; then
        print_status "Installing Python packages from requirements.txt..."
        su - "${ACTUAL_USER}" -c "${VENV_DIR}/bin/pip install -r ${SUBWAY_DIR}/requirements.txt -q"
        print_status "Python packages installed"
    else
        print_warning "requirements.txt not found at ${SUBWAY_DIR}/requirements.txt"
    fi
}

#######################################
# Setup configuration file
#######################################
setup_config() {
    print_header "Checking Configuration"

    local config_file="${SUBWAY_DIR}/config.yaml"
    local example_config="${SUBWAY_DIR}/config.example.yaml"

    if [ -f "${config_file}" ]; then
        print_status "config.yaml already exists"
    else
        if [ -f "${example_config}" ]; then
            print_warning "config.yaml not found"
            print_status "Copying config.example.yaml to config.yaml..."
            su - "${ACTUAL_USER}" -c "cp ${example_config} ${config_file}"
            print_warning "Please edit ${config_file} with your station details"
        else
            print_error "Neither config.yaml nor config.example.yaml found"
            print_warning "You'll need to create config.yaml manually"
        fi
    fi
}

#######################################
# Setup systemd service
#######################################
setup_systemd_service() {
    print_header "Setting Up Systemd Service"

    if [ ! -f "${SERVICE_FILE}" ]; then
        print_error "Service file not found at ${SERVICE_FILE}"
        return 1
    fi

    # Create customized service file with actual username
    local temp_service="/tmp/${SERVICE_NAME}.service"
    sed -e "s|<USER>|${ACTUAL_USER}|g" \
        -e "s|/home/<USER>/pi-zero|${SCRIPT_DIR}|g" \
        "${SERVICE_FILE}" > "${temp_service}"

    # Check if service is already installed
    if [ -f "${SYSTEMD_DIR}/${SERVICE_NAME}.service" ]; then
        # Compare files to see if update is needed
        if cmp -s "${temp_service}" "${SYSTEMD_DIR}/${SERVICE_NAME}.service"; then
            print_status "Service file is already up to date"
        else
            print_status "Updating service file..."
            cp "${temp_service}" "${SYSTEMD_DIR}/${SERVICE_NAME}.service"
            systemctl daemon-reload
            print_status "Service file updated"
        fi
    else
        print_status "Installing service file..."
        cp "${temp_service}" "${SYSTEMD_DIR}/${SERVICE_NAME}.service"
        systemctl daemon-reload
        print_status "Service file installed"
    fi

    rm -f "${temp_service}"

    # Enable service to start on boot
    if systemctl is-enabled "${SERVICE_NAME}" &>/dev/null; then
        print_status "Service is already enabled"
    else
        print_status "Enabling service to start on boot..."
        systemctl enable "${SERVICE_NAME}"
    fi

    # Start service if not already running
    if systemctl is-active "${SERVICE_NAME}" &>/dev/null; then
        print_status "Service is already running"
    else
        print_status "Starting service..."
        systemctl start "${SERVICE_NAME}"
    fi

    # Show service status
    print_status "Service status:"
    systemctl status "${SERVICE_NAME}" --no-pager -l || true
}

#######################################
# Setup cron job for automatic updates
#######################################
setup_cron_job() {
    print_header "Setting Up Automatic Updates"

    # Create logs directory if it doesn't exist
    if [ ! -d "${LOG_DIR}" ]; then
        print_status "Creating logs directory at ${LOG_DIR}..."
        su - "${ACTUAL_USER}" -c "mkdir -p ${LOG_DIR}"
    else
        print_status "Logs directory already exists"
    fi

    # Make update script executable
    if [ -f "${UPDATE_SCRIPT}" ]; then
        chmod +x "${UPDATE_SCRIPT}"
        print_status "Update script is executable"
    else
        print_warning "Update script not found at ${UPDATE_SCRIPT}"
        print_warning "Skipping cron job setup"
        return 1
    fi

    # Check if cron job already exists
    local cron_command="*/15 * * * * ${UPDATE_SCRIPT} >> ${LOG_DIR}/update.log 2>&1"

    if su - "${ACTUAL_USER}" -c "crontab -l 2>/dev/null | grep -F '${UPDATE_SCRIPT}'" &>/dev/null; then
        print_status "Cron job for automatic updates already exists"
    else
        print_status "Adding cron job for automatic updates (every 15 minutes)..."
        # Add cron job for the actual user (not root)
        (su - "${ACTUAL_USER}" -c "crontab -l 2>/dev/null" || true; echo "${cron_command}") | \
            su - "${ACTUAL_USER}" -c "crontab -"
        print_status "Cron job added"
    fi
}

#######################################
# Display final instructions
#######################################
show_completion_message() {
    print_header "Setup Complete"

    echo "The Raspberry Pi has been successfully configured!"
    echo ""
    echo "Next steps:"
    echo "  1. Edit the configuration file:"
    echo "     ${SUBWAY_DIR}/config.yaml"
    echo ""
    echo "  2. Restart the service after editing config:"
    echo "     sudo systemctl restart ${SERVICE_NAME}"
    echo ""
    echo "  3. View service logs:"
    echo "     sudo journalctl -u ${SERVICE_NAME} -f"
    echo ""
    echo "  4. Check service status:"
    echo "     sudo systemctl status ${SERVICE_NAME}"
    echo ""
    echo "  5. View update logs:"
    echo "     tail -f ${LOG_DIR}/update.log"
    echo ""
    print_status "The system will automatically check for updates every 15 minutes"
    echo ""
}

#######################################
# Main execution flow
#######################################
main() {
    print_header "Raspberry Pi Zero Setup Script"
    echo "User: ${ACTUAL_USER}"
    echo "Repository: ${SCRIPT_DIR}"
    echo "Service: ${SERVICE_NAME}"
    echo ""

    check_sudo
    install_system_dependencies
    setup_python_venv
    setup_config
    setup_systemd_service
    setup_cron_job
    show_completion_message
}

# Run main function
main "$@"
