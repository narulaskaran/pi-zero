# MTA Subway Train Times

Real-time NYC subway train arrival information from the MTA GTFS feed.

## Features

- Fetches real-time train arrivals for configured stations
- Consolidates all trains by station and direction
- Sorts trains by arrival time
- Supports all NYC subway lines
- Simple YAML configuration

## Installation

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Copy the example config and edit it with your stations:

```bash
cp config.example.yaml config.yaml
```

Then edit `config.yaml` to configure your stations:

```yaml
stations:
  - name: "Your Station Name"
    stop_id: "A21"  # Base stop ID without N/S suffix
    routes: ["B", "C"]  # Train routes to display
    directions:
      uptown: "UPTOWN"
      downtown: "DOWNTOWN"
```

Find stop IDs at: http://web.mta.info/developers/data/nyct/subway/Stations.csv

## Usage

```bash
# Activate virtual environment if not already active
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run the script
python get_train_times.py
```

## Example Output

```
Fetching MTA train times...
Time: 11:48 AM

======================================================================
Station: Times Square - 42nd St
======================================================================

UPTOWN:
----------------------------------------------------------------------
  1 Train: Arriving
  2 Train: 2 min
  1 Train: 5 min
  3 Train: 8 min
  2 Train: 12 min

DOWNTOWN:
----------------------------------------------------------------------
  3 Train: 1 min
  1 Train: 3 min
  2 Train: 6 min
  1 Train: 9 min

======================================================================
```
