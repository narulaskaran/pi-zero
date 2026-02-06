# Infrastructure Setup

This directory contains documentation for setting up the infrastructure components of the Raspberry Pi Zero home server.

## Components

### Network & Remote Access
- [Tailscale Setup](tailscale.md) - Secure remote access to your Pi Zero

### Network Services
- [Pi-hole Setup](pi-hole.md) - Network-wide ad blocking and DNS management

## Quick Overview

The infrastructure is designed to provide:

1. **Secure Remote Access** via Tailscale
   - Access your Pi Zero from anywhere
   - No port forwarding required
   - End-to-end encrypted

2. **Network-wide Ad Blocking** via Pi-hole
   - Block ads and trackers at the DNS level
   - Works for all devices on your network
   - Web-based dashboard for monitoring

## Getting Started

Follow the setup guides in order:

1. Start with [Tailscale](tailscale.md) to establish secure remote access
2. Optionally set up [Pi-hole](pi-hole.md) for network-wide ad blocking

Both services are independent and can be set up separately based on your needs.
