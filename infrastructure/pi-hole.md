# Pi-hole Setup

Pi-hole provides network-wide ad blocking and DNS management. It acts as a DNS sinkhole to block ads, trackers, and malware at the network level.

## What is Pi-hole?

Pi-hole is a DNS-based ad blocker that runs on your Raspberry Pi. It blocks ads for all devices on your network without requiring software installation on each device.

**Key Features:**
- Network-wide ad blocking
- Blocks ads in apps and games
- Improves browsing speed by blocking trackers
- Web-based admin dashboard
- Custom blocklists and whitelists
- DNS over HTTPS (DoH) support

## Installation

### Prerequisites

Ensure your Pi Zero has a static IP address or a DHCP reservation from your router.

### 1. Run the Pi-hole Installer

```bash
# Download and run the automated installer
curl -sSL https://install.pi-hole.net | bash
```

The installer will guide you through:
- Selecting an upstream DNS provider (e.g., Google, Cloudflare, OpenDNS)
- Choosing blocklists
- Configuring the web interface
- Setting an admin password

### 2. Installation Prompts

During installation, you'll be asked:

1. **Upstream DNS Provider**: Choose Cloudflare (1.1.1.1) or Google (8.8.8.8)
2. **Blocklists**: Keep the default lists (recommended)
3. **Admin Web Interface**: Yes (install lighttpd)
4. **Web Server**: Yes (required for dashboard)
5. **Query Logging**: Yes (recommended for monitoring)
6. **Privacy Mode**: Choose based on your preferences

### 3. Note Your Admin Password

The installer will display your admin password at the end. Save it securely.

```bash
# To change the admin password later
pihole -a -p
```

## Configuration

### Accessing the Admin Dashboard

Open a web browser and navigate to:

```
http://<pi-zero-ip>/admin
```

Or if using Tailscale:

```
http://pi-zero/admin
```

Log in with the admin password.

### Configure Network Devices

To use Pi-hole, you need to point your devices to use the Pi Zero as their DNS server.

#### Option 1: Configure Router (Recommended)

Change your router's DHCP settings to use Pi-hole as the DNS server:

1. Log into your router's admin interface
2. Find DHCP/DNS settings
3. Set Primary DNS to your Pi Zero's IP address
4. Save and reboot router

This applies Pi-hole to all devices on your network automatically.

#### Option 2: Configure Individual Devices

Manually set DNS on each device:

**Windows:**
```
Network Settings > Change Adapter Options >
Right-click connection > Properties > IPv4 >
Preferred DNS Server: <pi-zero-ip>
```

**macOS:**
```
System Preferences > Network > Advanced > DNS >
Add DNS Server: <pi-zero-ip>
```

**Linux:**
```bash
# Edit /etc/resolv.conf
nameserver <pi-zero-ip>
```

## Using Pi-hole

### Dashboard Overview

The web dashboard shows:
- Total queries blocked (percentage and count)
- Top blocked domains
- Top allowed domains
- Query types (A, AAAA, PTR, etc.)
- Clients making queries
- Real-time query log

### Adding Custom Blocklists

1. Go to **Group Management > Adlists**
2. Add blocklist URLs (find lists at https://firebog.net/)
3. Click **Save and Update**
4. Go to **Tools > Update Gravity**

### Whitelisting Domains

If a website breaks due to blocking:

1. Go to **Whitelist**
2. Enter the domain
3. Click **Add to Whitelist**

Or via command line:
```bash
pihole -w example.com
```

### Blacklisting Additional Domains

```bash
# Add to blacklist via command line
pihole -b ads.example.com

# Or use the web interface: Blacklist > Add domain
```

## Maintenance

### Update Pi-hole

```bash
# Update Pi-hole to the latest version
pihole -up
```

### Update Blocklists (Gravity)

```bash
# Update all blocklists
pihole -g
```

This is automatically done weekly, but you can run it manually anytime.

### Restart DNS Service

```bash
# Restart Pi-hole DNS service
pihole restartdns
```

### Disable/Enable Pi-hole Temporarily

```bash
# Disable for 5 minutes
pihole disable 5m

# Disable indefinitely
pihole disable

# Re-enable
pihole enable
```

### View Logs

```bash
# View live query log
pihole -t

# View detailed logs
pihole -c -e
```

## Backup and Restore

### Backup Configuration

Via web interface:
1. Go to **Settings > Teleporter**
2. Click **Backup** to download a tar.gz file

### Restore Configuration

1. Go to **Settings > Teleporter**
2. Upload your backup file
3. Click **Restore**

## Troubleshooting

### DNS Resolution Not Working

1. Check Pi-hole service status:
   ```bash
   pihole status
   ```

2. Restart if needed:
   ```bash
   pihole restartdns
   ```

3. Verify port 53 is listening:
   ```bash
   sudo netstat -tulpn | grep :53
   ```

### Websites Not Loading

Some sites may break if their domains are blocked:

1. Check the query log in the dashboard
2. Whitelist the blocked domain
3. Or temporarily disable Pi-hole:
   ```bash
   pihole disable 5m
   ```

### Admin Interface Not Accessible

```bash
# Restart web server
sudo service lighttpd restart

# Check if lighttpd is running
sudo systemctl status lighttpd
```

### Pi-hole Not Blocking After Router Configuration

1. Verify DHCP settings on router
2. Renew DHCP lease on client devices
3. Check DNS settings on devices:
   ```bash
   # Linux/macOS
   nslookup google.com

   # Should show Pi-hole IP as server
   ```

## Advanced Configuration

### DNS over HTTPS (DoH)

Install cloudflared for encrypted DNS queries:

```bash
# Install cloudflared
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm

# Make executable
chmod +x cloudflared-linux-arm
sudo mv cloudflared-linux-arm /usr/local/bin/cloudflared

# Create cloudflared user
sudo useradd -s /usr/sbin/nologin -r -M cloudflared

# Create config
sudo nano /etc/default/cloudflared
```

Add:
```
CLOUDFLARED_OPTS=--port 5053 --upstream https://1.1.1.1/dns-query
```

```bash
# Install service
sudo cloudflared service install
sudo systemctl start cloudflared
sudo systemctl enable cloudflared

# Configure Pi-hole to use cloudflared
# In web interface: Settings > DNS > Custom
# Set to 127.0.0.1#5053
```

### Using Alternative Blocklists

Popular blocklist collections:
- [Firebog](https://firebog.net/) - Curated lists
- [OISD](https://oisd.nl/) - All-in-one list
- [Steven Black's hosts](https://github.com/StevenBlack/hosts) - Comprehensive lists

## Performance Notes

The Raspberry Pi Zero (especially Zero W) has limited resources:

- Pi-hole runs efficiently on the Zero
- Large blocklists (>1M domains) may cause slowdowns
- Consider using optimized lists like OISD
- Monitor CPU/memory usage via the dashboard

## Useful Commands Reference

```bash
# Check status
pihole status

# Update Pi-hole
pihole -up

# Update gravity (blocklists)
pihole -g

# Restart DNS
pihole restartdns

# View real-time queries
pihole -t

# Whitelist domain
pihole -w example.com

# Blacklist domain
pihole -b ads.example.com

# Disable for 5 minutes
pihole disable 5m

# Enable
pihole enable

# View statistics
pihole -c -e

# Reconfigure
pihole -r

# Uninstall
pihole uninstall
```

## Additional Resources

- [Pi-hole Documentation](https://docs.pi-hole.net/)
- [Pi-hole Community Forum](https://discourse.pi-hole.net/)
- [Pi-hole GitHub](https://github.com/pi-hole/pi-hole)
- [Regex Filters Guide](https://docs.pi-hole.net/ftldns/regex/overview/)
