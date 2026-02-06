# Tailscale Setup

Tailscale provides secure remote access to your Raspberry Pi Zero without requiring port forwarding or complex firewall configurations.

## What is Tailscale?

Tailscale creates a secure, private network (VPN) between your devices using WireGuard. Once installed, you can access your Pi Zero from anywhere as if it were on your local network.

## Installation

### 1. Install Tailscale on Raspberry Pi Zero

```bash
# Update package list
sudo apt update

# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh
```

### 2. Authenticate and Connect

```bash
# Start Tailscale and authenticate
sudo tailscale up

# Follow the authentication URL printed in the terminal
# Log in with your Tailscale account to authorize the device
```

### 3. Verify Connection

```bash
# Check Tailscale status
tailscale status

# Get your Pi's Tailscale IP address
tailscale ip -4
```

Your Pi Zero will receive a Tailscale IP address (typically in the 100.x.x.x range).

## Configuration

### Enable Auto-start on Boot

Tailscale should start automatically after installation. Verify with:

```bash
sudo systemctl status tailscaled
```

If not enabled:

```bash
sudo systemctl enable tailscaled
sudo systemctl start tailscaled
```

### Set a MagicDNS Name

In the Tailscale web dashboard (https://login.tailscale.com/admin/machines):
1. Find your Pi Zero device
2. Click on the three dots menu
3. Select "Edit device name"
4. Set a memorable name (e.g., "pi-zero")

Now you can access your Pi using `pi-zero` instead of the IP address.

## Usage

### Accessing Your Pi Zero

Once Tailscale is running on both your Pi and your client device:

```bash
# SSH into your Pi Zero using Tailscale IP
ssh username@100.x.x.x

# Or using MagicDNS name
ssh username@pi-zero
```

### Accessing Web Services

If running web services (like the subway display server):

```bash
# Access via IP
http://100.x.x.x:8080

# Or via MagicDNS name
http://pi-zero:8080
```

## Useful Commands

```bash
# Check connection status
tailscale status

# View your Tailscale IP addresses
tailscale ip

# Temporarily disconnect
sudo tailscale down

# Reconnect
sudo tailscale up

# View detailed logs
sudo journalctl -u tailscaled

# Check version
tailscale version
```

## Troubleshooting

### Cannot Connect After Setup

1. Verify Tailscale is running:
   ```bash
   sudo systemctl status tailscaled
   ```

2. Check if authentication is complete:
   ```bash
   tailscale status
   ```
   Should show your devices listed, not "logged out"

3. Ensure your client device also has Tailscale installed and is logged in to the same account

### Connection Drops After Reboot

Ensure Tailscale is enabled to start on boot:
```bash
sudo systemctl enable tailscaled
```

### Firewall Issues

Tailscale handles most firewall traversal automatically. If issues persist:
```bash
# On Pi Zero, allow Tailscale through firewall
sudo ufw allow in on tailscale0
```

## Security Notes

- Tailscale uses end-to-end encryption via WireGuard
- Your traffic does not route through Tailscale's servers (except for coordination)
- You can enable/disable devices from the Tailscale web dashboard
- Use SSH keys instead of passwords for additional security

## Additional Resources

- [Tailscale Documentation](https://tailscale.com/kb/)
- [Tailscale Admin Console](https://login.tailscale.com/admin/machines)
- [WireGuard Protocol](https://www.wireguard.com/)
