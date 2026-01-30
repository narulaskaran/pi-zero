#!/usr/bin/env python3
"""
MTA Subway Train Times - Config-Driven Edition

This script fetches real-time train arrival information from the MTA GTFS feed
for configured subway stops. Configure your stops in config.yaml.

Usage:
    python get_train_times.py

Requirements:
    pip install -r requirements.txt
"""

import sys
from datetime import datetime
from pathlib import Path

import yaml
from nyct_gtfs import NYCTFeed

# Mapping of train routes to their GTFS feed URLs
ROUTE_TO_FEED = {
    'A': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace',
    'C': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace',
    'E': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-ace',
    'B': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm',
    'D': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm',
    'F': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm',
    'M': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-bdfm',
    'G': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-g',
    'J': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz',
    'Z': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-jz',
    'N': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw',
    'Q': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw',
    'R': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw',
    'W': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-nqrw',
    'L': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-l',
    '1': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs',
    '2': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs',
    '3': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs',
    '4': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs',
    '5': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs',
    '6': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs',
    '7': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs',
    'SI': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-si',
    'SIR': 'https://api-endpoint.mta.info/Dataservice/mtagtfsfeeds/nyct%2Fgtfs-si',
}


def load_config(config_path="config.yaml"):
    """Load configuration from YAML file."""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)

        if not config:
            print(f"Error: Config file '{config_path}' is empty")
            sys.exit(1)

        # Support both 'stations' and 'stops' for backwards compatibility
        stations = config.get('stations') or config.get('stops')
        if not stations:
            print(f"Error: No stations configured in '{config_path}'")
            sys.exit(1)

        return config

    except FileNotFoundError:
        print(f"Error: Config file '{config_path}' not found")
        print("Please create a config.yaml file with your station configuration")
        sys.exit(1)

    except yaml.YAMLError as e:
        print(f"Error parsing YAML config: {e}")
        sys.exit(1)


def get_train_times_for_station(station_config, num_trains=10):
    """
    Fetch and display train times for a configured station.

    Args:
        station_config: Dictionary containing station configuration
        num_trains: Number of upcoming trains to display per direction
    """
    station_name = station_config['name']
    routes = station_config['routes']

    # Support both single stop_id and multiple stop_ids
    stop_ids = station_config.get('stop_ids', [station_config.get('stop_id')])
    if not isinstance(stop_ids, list):
        stop_ids = [stop_ids]

    # Get direction labels
    directions = station_config.get('directions', {
        'uptown': 'UPTOWN',
        'downtown': 'DOWNTOWN'
    })

    # Group routes by their feed to minimize API calls
    feed_to_routes = {}
    for route in routes:
        if route not in ROUTE_TO_FEED:
            print(f"Warning: Unknown route '{route}', skipping")
            continue

        feed_url = ROUTE_TO_FEED[route]
        if feed_url not in feed_to_routes:
            feed_to_routes[feed_url] = []
        feed_to_routes[feed_url].append(route)

    # Collect all trains for both directions
    uptown_arrivals = []  # List of (arrival_time, route, minutes_away)
    downtown_arrivals = []

    try:
        # Fetch trains from each feed
        for feed_url, feed_routes in feed_to_routes.items():
            feed = NYCTFeed(feed_url)

            # Check each stop ID
            for stop_id_base in stop_ids:
                uptown_stop_id = f"{stop_id_base}N"
                downtown_stop_id = f"{stop_id_base}S"

                # Get uptown trains
                uptown_trips = feed.filter_trips(
                    headed_for_stop_id=uptown_stop_id,
                    underway=True
                )

                for trip in uptown_trips:
                    route = trip.route_id

                    # Filter by configured routes
                    if route not in routes:
                        continue

                    for update in trip.stop_time_updates:
                        if update.stop_id == uptown_stop_id:
                            arrival_time = update.arrival
                            now = datetime.now()
                            minutes_away = int((arrival_time - now).total_seconds() / 60)

                            if minutes_away >= 0:
                                uptown_arrivals.append((arrival_time, route, minutes_away))
                            break

                # Get downtown trains
                downtown_trips = feed.filter_trips(
                    headed_for_stop_id=downtown_stop_id,
                    underway=True
                )

                for trip in downtown_trips:
                    route = trip.route_id

                    # Filter by configured routes
                    if route not in routes:
                        continue

                    for update in trip.stop_time_updates:
                        if update.stop_id == downtown_stop_id:
                            arrival_time = update.arrival
                            now = datetime.now()
                            minutes_away = int((arrival_time - now).total_seconds() / 60)

                            if minutes_away >= 0:
                                downtown_arrivals.append((arrival_time, route, minutes_away))
                            break

        # Sort by arrival time
        uptown_arrivals.sort(key=lambda x: x[0])
        downtown_arrivals.sort(key=lambda x: x[0])

        # Display results
        print(f"\n{'=' * 70}")
        print(f"Station: {station_name}")
        print(f"{'=' * 70}")

        print(f"\n{directions['uptown']}:")
        print("-" * 70)
        if uptown_arrivals:
            for _, route, minutes_away in uptown_arrivals[:num_trains]:
                time_str = f"{minutes_away} min" if minutes_away > 0 else "Arriving"
                print(f"  {route} Train: {time_str}")
        else:
            print("  No trains currently scheduled")

        print(f"\n{directions['downtown']}:")
        print("-" * 70)
        if downtown_arrivals:
            for _, route, minutes_away in downtown_arrivals[:num_trains]:
                time_str = f"{minutes_away} min" if minutes_away > 0 else "Arriving"
                print(f"  {route} Train: {time_str}")
        else:
            print("  No trains currently scheduled")

    except Exception as e:
        print(f"\nError fetching data for {station_name}: {e}")
        print("Please verify the stop ID and routes are correct")


def main():
    """Main execution function."""
    # Determine config path
    script_dir = Path(__file__).parent
    config_path = script_dir / "config.yaml"

    # Load configuration
    config = load_config(config_path)

    # Get number of trains to display
    num_trains = config.get('num_trains', 10)

    print(f"\nFetching MTA train times...")
    print(f"Time: {datetime.now().strftime('%I:%M %p')}")

    # Process each configured station
    for station in config.get('stations', config.get('stops', [])):
        get_train_times_for_station(station, num_trains)

    print(f"\n{'=' * 70}\n")


if __name__ == "__main__":
    main()
