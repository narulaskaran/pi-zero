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
python get_train_times.py
```

## Example Output

```
======================================================================
Station: 81st Street - Museum of Natural History
======================================================================

UPTOWN (Towards Bronx):
----------------------------------------------------------------------
  C Train: 2 min
  B Train: 5 min
  C Train: 12 min

DOWNTOWN (Towards Brooklyn):
----------------------------------------------------------------------
  B Train: Arriving
  C Train: 4 min
  B Train: 8 min
```
