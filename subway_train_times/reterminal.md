# reTerminal E-ink Display Setup

This guide covers hardware-specific setup for displaying the subway dashboard on a Seeed Studio reTerminal with an e-ink display.

## Hardware Overview

**reTerminal E1001 Specifications:**
- ESP32-S3 microcontroller
- 800x480 pixel e-ink display (7.5" GDEY075T7)
- Built-in WiFi
- Low power consumption with deep sleep support
- SPI interface for display communication

## Hardware Setup

### Required Components

1. **reTerminal E1001** with e-ink display
2. **USB-C cable** for programming
3. **WiFi network** for connectivity
4. **Raspberry Pi Zero** running the subway server

### Pin Configuration

The Arduino sketch uses these pin definitions (pre-configured for reTerminal):

```
E-Paper Display:
- SCK:  GPIO 7
- MOSI: GPIO 9
- CS:   GPIO 10
- DC:   GPIO 11
- RST:  GPIO 12
- BUSY: GPIO 13

Status LED:
- LED:  GPIO 6

Serial Output:
- RX:   GPIO 44
- TX:   GPIO 43
```

## Software Setup

### 1. Install Arduino IDE

Download and install Arduino IDE from https://www.arduino.cc/en/software

### 2. Install ESP32 Board Support

1. Open Arduino IDE
2. Go to **File > Preferences**
3. Add to "Additional Board Manager URLs":
   ```
   https://espressif.github.io/arduino-esp32/package_esp32_index.json
   ```
4. Go to **Tools > Board > Boards Manager**
5. Search for "esp32"
6. Install "esp32 by Espressif Systems"

### 3. Install Required Libraries

Go to **Sketch > Include Library > Manage Libraries** and install:

1. **GxEPD2** by Jean-Marc Zingg
   - For e-ink display control
   - Install the latest version (>= 1.5.0)

2. **Adafruit GFX Library**
   - Dependency for GxEPD2
   - Should install automatically

The WiFi and HTTPClient libraries are included with ESP32 core.

### 4. Configure the Sketch

Open `/Users/ksn/Documents/source/pi-zero/subway_train_times/reterminal-sketch/reterminal-sketch.ino`

Update the configuration section:

```cpp
// ==================== CONFIGURATION ====================
const char* WIFI_SSID     = "YourNetworkName";
const char* WIFI_PASSWORD = "YourNetworkPassword";
const char* PI_SERVER_URL = "http://192.168.x.x:8080/display.bmp";

const int SLEEP_MINUTES = 1;  // Update interval
// =======================================================
```

**Important:**
- Replace `WIFI_SSID` with your WiFi network name
- Replace `WIFI_PASSWORD` with your WiFi password
- Set `PI_SERVER_URL` to your Pi Zero's IP and port
  - Use local IP (192.168.x.x) for same network
  - Use Tailscale IP (100.x.x.x) for remote access
- Adjust `SLEEP_MINUTES` for update frequency (1-60 recommended)

### 5. Upload to reTerminal

1. Connect reTerminal via USB-C
2. In Arduino IDE, select:
   - **Board:** "ESP32S3 Dev Module"
   - **Port:** Select the COM/serial port for your device
   - **USB CDC On Boot:** "Enabled"
   - **Flash Size:** "16MB (128Mb)"
3. Click **Upload** (arrow button)

The sketch will compile and upload. Monitor the Serial output at 115200 baud to see connection status.

## How It Works

### Fetch-Render Cycle

1. **Wake Up:** ESP32 wakes from deep sleep
2. **Connect WiFi:** Connects to configured network
3. **Fetch Image:** Downloads 1-bit BMP image from Pi server
4. **Parse BMP:** Extracts bitmap data from BMP file
5. **Render:** Draws image to e-ink display
6. **Sleep:** Enters deep sleep for configured duration
7. **Repeat:** Wakes up and repeats cycle

### Power Efficiency

The sketch uses ESP32 deep sleep to minimize power consumption:
- Active time: ~10-15 seconds per update
- Sleep time: Configurable (default 1 minute)
- LED indicates activity (on during update)

### Image Format

The display expects a **1-bit dithered BMP** image:
- Dimensions: 800x480 pixels
- Color depth: 1-bit (black and white)
- File size: ~48KB
- Format: BMP with bottom-up row order

The Pi server (`subway_server.py`) generates this format automatically.

## Monitoring and Debugging

### Serial Monitor

1. Open **Tools > Serial Monitor**
2. Set baud rate to **115200**
3. You'll see output like:

```
Connecting to WiFi........
Connected!
Image Displayed
```

### LED Indicator

The onboard LED (GPIO 6) indicates status:
- **ON (LOW):** Active, fetching/rendering
- **OFF (HIGH):** Deep sleep

### Common Messages

- `Connecting to WiFi...` - Attempting WiFi connection
- `Connected!` - WiFi connected successfully
- `Image Displayed` - Successfully rendered to display
- No output after 10 seconds - Check WiFi credentials or server URL

## Troubleshooting

### Display Not Updating

1. **Check WiFi connection:**
   - Verify SSID and password in sketch
   - Ensure reTerminal is within WiFi range
   - Check Serial Monitor for connection errors

2. **Check server URL:**
   - Ping Pi server from another device
   - Test URL in browser: `http://your-pi-ip:8080/display.bmp`
   - Should download a small BMP file

3. **Check server status:**
   ```bash
   # On Pi Zero
   sudo systemctl status subway-display
   ```

### Display Shows Corrupted Image

1. **Verify image format:**
   - Server must generate 1-bit BMP
   - Check `subway_server.py` uses `img.convert("1")`

2. **Test image manually:**
   - Download BMP from server
   - Verify size is ~48KB (not 385KB)
   - Check dimensions are 800x480

### WiFi Connection Fails

1. **Verify credentials:**
   - Double-check SSID and password
   - SSID is case-sensitive

2. **Check network:**
   - Ensure 2.4GHz WiFi (ESP32 doesn't support 5GHz)
   - Check if network has MAC filtering enabled

3. **Increase timeout:**
   ```cpp
   // In sketch, change:
   while (WiFi.status() != WL_CONNECTED && retries < 20)
   // to:
   while (WiFi.status() != WL_CONNECTED && retries < 40)
   ```

### Upload Fails

1. **Port not found:**
   - Install CP210x USB drivers if needed
   - Try different USB cable (must support data)
   - Restart Arduino IDE

2. **Upload timeout:**
   - Hold BOOT button while uploading
   - Select correct board ("ESP32S3 Dev Module")
   - Enable "USB CDC On Boot"

### E-ink Display Issues

1. **Blank display:**
   - Check power supply (USB-C)
   - Verify GxEPD2 library is installed
   - Check display cable connection

2. **Partial updates:**
   - Normal behavior for e-ink
   - Full refresh happens each update cycle

3. **Ghosting:**
   - E-ink displays retain ghost images
   - Use `display.clearScreen()` for full clear if needed

## Advanced Configuration

### Adjusting Update Frequency

Balance between freshness and power consumption:

```cpp
const int SLEEP_MINUTES = 1;   // Very frequent (high power)
const int SLEEP_MINUTES = 5;   // Balanced
const int SLEEP_MINUTES = 15;  // Low power, less fresh data
```

For subway times, 1-2 minutes is recommended.

### Using Tailscale for Remote Access

If your Pi is on Tailscale:

```cpp
// Use Tailscale IP instead of local IP
const char* PI_SERVER_URL = "http://100.x.x.x:8080/display.bmp";
```

This allows the reTerminal to fetch updates even when away from home network.

### Battery Operation

For battery-powered setups:
1. Increase `SLEEP_MINUTES` to 5-15 minutes
2. Monitor battery level via ESP32 ADC if available
3. Consider solar panel for continuous operation

### Custom Display Layouts

To modify the displayed content, edit `subway_server.py` on the Pi Zero, not the Arduino sketch. The sketch only fetches and displays whatever image the server generates.

## Technical Details

### Display Specifications

- **Model:** GDEY075T7 (Good Display)
- **Size:** 7.5 inch
- **Resolution:** 800 × 480 pixels
- **Colors:** Black and white (1-bit)
- **Refresh time:** ~10 seconds (full refresh)
- **Interface:** SPI

### Memory Constraints

The ESP32-S3 has sufficient RAM for the full display buffer:
- Required buffer: 800 × 480 ÷ 8 = 48,000 bytes
- ESP32-S3 SRAM: 512 KB
- BMP file size: ~48KB

### SPI Configuration

```cpp
SPISettings(4000000, MSBFIRST, SPI_MODE0)
```

- **Clock:** 4 MHz (safe for e-ink)
- **Bit order:** MSB first
- **Mode:** SPI Mode 0

## Files Reference

- **Arduino sketch:** `subway_train_times/reterminal-sketch/reterminal-sketch.ino`
- **Pi server:** `subway_train_times/subway_server.py`
- **Service file:** `subway_train_times/subway-display.service`

## Additional Resources

- [GxEPD2 Library Documentation](https://github.com/ZinggJM/GxEPD2)
- [ESP32 Deep Sleep Guide](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/system/sleep_modes.html)
- [E-Paper Display Datasheet](https://www.good-display.com/product/442.html)
- [reTerminal E1001 Wiki](https://wiki.seeedstudio.com/reterminal_e1001/)
