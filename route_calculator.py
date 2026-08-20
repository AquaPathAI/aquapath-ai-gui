import csv
import requests

# This file contains only the reusable Python route-calculation logic.
# Flask imports calculate_route() when the website receives a route request.


PORT_COORDINATES = {
    # --- ASIA & MIDDLE EAST ---
    "Mumbai": (18.94, 72.83), "Singapore": (1.29, 103.85),
    "Shanghai": (31.23, 121.47), "Tokyo": (35.67, 139.65),
    "Dubai": (25.20, 55.27), 
    # --- AFRICA & CHOKEPOINTS ---
    "Aden": (12.79, 44.98), "Suez": (29.96, 32.55), 
    "Cape Town": (-33.92, 18.42),
    # --- EUROPE ---
    "Gibraltar": (36.14, -5.35), "Rotterdam": (51.92, 4.48),
    "Hamburg": (53.55, 9.99), 
    # --- THE AMERICAS ---
    "New York": (40.71, -74.00), "Los Angeles": (34.05, -118.24), 
    "Panama Canal": (9.14, -79.72), "Santos": (-23.96, -46.33)
}

MARITIME_NETWORK = {
    # --- ASIA & MIDDLE EAST ---
    "Mumbai": {"Aden": 1650, "Dubai": 930, "Singapore": 2440, "Cape Town": 4600},
    "Singapore": {"Mumbai": 2440, "Shanghai": 2500, "Tokyo": 2900, "Los Angeles": 7600},
    "Shanghai": {"Singapore": 2500, "Tokyo": 1000, "Los Angeles": 5700},
    "Tokyo": {"Shanghai": 1000, "Singapore": 2900, "Los Angeles": 5400, "Panama Canal": 7600},
    "Dubai": {"Mumbai": 930, "Aden": 1400},
    
    # --- AFRICA & CHOKEPOINTS ---
    "Aden": {"Dubai": 1400, "Mumbai": 1650, "Suez": 1300, "Cape Town": 3900},
    "Suez": {"Aden": 1300, "Gibraltar": 1900},
    "Cape Town": {"Mumbai": 4600, "Aden": 3900, "Santos": 3300, "Gibraltar": 4500},
    
    # --- EUROPE ---
    "Gibraltar": {"Suez": 1900, "Cape Town": 4500, "Rotterdam": 1300, "New York": 3100},
    "Rotterdam": {"Gibraltar": 1300, "Hamburg": 250, "New York": 3400},
    "Hamburg": {"Rotterdam": 250, "New York": 3500},
    
    # --- THE AMERICAS ---
    "New York": {"Gibraltar": 3100, "Rotterdam": 3400, "Hamburg": 3500, "Panama Canal": 2000, "Santos": 4800},
    "Los Angeles": {"Tokyo": 5400, "Shanghai": 5700, "Singapore": 7600, "Panama Canal": 2900},
    "Panama Canal": {"Los Angeles": 2900, "New York": 2000, "Santos": 3400, "Tokyo": 7600},
    "Santos": {"Cape Town": 3300, "Panama Canal": 3400, "New York": 4800}
}


def find_all_paths(graph, start, end, path=None):
    # Finds all possible routes between the start and end ports without looping.
    # Args:
    #     graph (dict): The network of ports (nodes) and their connections (edges).
    #     start (str): The starting port for the route.
    #     end (str): The destination port for the route.
    #     path (list, optional): The current path history to prevent cycles.
    # Returns:
    #     list: A list of all valid paths connecting the start and end ports.

    # Initialize the path list on the first call 
    if path is None:
        path = []
    
    # Add the current port to the path history. 
    # This prevents us from visiting the same port twice and creating loops.
    path = path + [start]
    
    # Base Case: If the start and end ports are the same, a valid route has been found. 
    # Return it as a single-item list.
    if start == end:
        return [path]

    # If the starting port is not in the graph, it means there are no routes from this port. 
    # Return an empty list to indicate failure.        
    if start not in graph:
        return []
    
    # Recursive Case: Explore each neighboring port (connected via an edge) 
    # and continue searching for valid paths to the destination.
    paths = []
    for node in graph[start]:
        # Only continue down this path if this port 
        # has not already been visited in our current path history. 
        # This ensures that cycles are avoided and only valid routes are considered.
        if node not in path:
            # For each valid neighboring port, make a recursive call 
            # to find all paths from that neighbor to the destination. 
            # Also pass along the current path history 
            # so that it can be updated in deeper recursive calls.
            newpaths = find_all_paths(graph, node, end, path)
            # Add any new valid paths found from this neighbour 
            # to our overall list of paths. 
            # This builds up the complete list of valid routes
            # from the start to the end port.
            for newpath in newpaths:
                paths.append(newpath)
    return paths


def calculate_total_distance(path):
    # Calculates the total nautical miles of a given path.
    # Args:
    #     path (list): A list of port names representing a valid route.
    # Returns:
    #     int: The accumulated distance of the entire journey in Nautical Miles.


    # Initialize a distance accumulator to sum up 
    # the distances between each pair of ports in the path
    total_distance = 0
    # Loop through the path list, 
    # taking pairs of consecutive ports (port_a and port_b) 
    # and looking up the distance between them in our MARITIME_NETWORK graph.
    for i in range(len(path) - 1):
        port_a = path[i]
        port_b = path[i+1]
        total_distance += MARITIME_NETWORK[port_a][port_b]
    return total_distance


def evaluate_full_path(path):
    # Fetches live weather via APIs and traffic via CSV.
    # Calculates safety risk using our Machine Learning formulas.
    # Args:
    #    path (list): A list of port names representing the maritime route.
    # Returns:
    #    tuple: (final_score, avg_wave, avg_wind, traffic_density, used_fallback)

    # Initialize accumulators and counters for averaging
    total_wind = 0
    total_wave = 0
    successful_wind_checks = 0
    successful_wave_checks = 0

    # Traffic data is only available for legs between ports, 
    # hence they are counted separately to calculate
    # an average traffic density across the entire route.
    total_traffic = 0
    successful_traffic_checks = 0
    
    # --- FETCH LIVE WEATHER (Open-Meteo API) ---
    for port in path:
        pt = PORT_COORDINATES[port]
        # Wind Speed API
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={pt[0]}&longitude={pt[1]}&current=wind_speed_10m"
        # Wave Height API
        marine_url = f"https://marine-api.open-meteo.com/v1/marine?latitude={pt[0]}&longitude={pt[1]}&current=wave_height"

        try:
            # Timeout of 3 seconds to prevent hanging if the API is unreachable
            wind_response = requests.get(weather_url, timeout=3)
            wave_response = requests.get(marine_url, timeout=3)
            
            # Only add to the total if a valid response was received (status code 200), 
            # and count how many successful checks happened for averaging later
            if wind_response.status_code == 200:
                total_wind += wind_response.json()["current"]["wind_speed_10m"]
                successful_wind_checks += 1
            if wave_response.status_code == 200:
                total_wave += wave_response.json()["current"]["wave_height"]
                successful_wave_checks += 1
        except Exception:
            pass # Skip safely if there is no internet connection

    # --- FETCH LOCAL TRAFFIC (CSV Database) ---
    for i in range(len(path) - 1):
        # Each leg of the journey is between two ports, 
        # so check the traffic data for each leg separately. 
        # This allows us to average traffic across the entire route.
        leg_start = path[i]
        leg_end = path[i+1]
        try:
            with open("traffic_data.csv", mode="r") as file:
                reader = csv.reader(file)
                next(reader) 
                for row in reader:
                    if (row[0] == leg_start and row[1] == leg_end) or (row[0] == leg_end and row[1] == leg_start):
                        total_traffic += int(row[2])
                        successful_traffic_checks += 1
                        break
        except FileNotFoundError:
            pass # Skip safely if the CSV file is missing

    # --- CALCULATE AVERAGES ---
    # Trigger the fallback warning if every single port failed.
    if successful_wind_checks > 0:
        used_fallback = False
        wind_speed = total_wind / successful_wind_checks
    else:
        used_fallback = True
        wind_speed = 15.0
        
    if successful_wave_checks > 0:
        wave_height = total_wave / successful_wave_checks
    else:
        wave_height = 2.0
        used_fallback = True
        
    if successful_traffic_checks > 0:
        traffic_density = total_traffic / successful_traffic_checks
    else:
        traffic_density = 20 

    # --- APPLY MACHINE LEARNING FORMULAS ---
    # Weather Risk (Calculated via Orange3 Linear Regression)
    weather_risk = (wave_height * 0.5107) + (wind_speed * 0.024) + 0.0105
    
    # Clamp the risk between 0.0 and 5.0
    weather_risk = max(0.0, min(5.0, weather_risk)) 
        
    # Traffic Risk (Calculated via Orange3 Linear Regression)
    traffic_risk = (traffic_density * 0.0484) + 0.0407
    
    # Clamp the risk between 0.0 and 5.0
    traffic_risk = max(0.0, min(5.0, traffic_risk))
        
    # Final Hybrid Score (65% Weather, 35% Traffic)
    # Uses custom weights to balance the importance of weather and traffic
    final_score = (weather_risk * 0.65) + (traffic_risk * 0.35)
    
    # Returns the final safety score, the average wave height, 
    # average wind speed, traffic density, 
    # and whether fallback values were used due to API failure.
    return {
        "score": round(final_score, 2),
        "wave_height": round(wave_height, 1),
        "wind_speed": round(wind_speed, 1),
        "traffic_density": int(traffic_density),
        "used_fallback": used_fallback
    }



def find_best_route(scored_routes, tolerance=0.25):
    # Selects the best route based on the lowest safety score, with a tie-breaker for distance if scores are close.
    
    # Args:
    #     scored_routes (list): A list of dictionaries containing route paths, scores, and distances.
    #     tolerance (float): The acceptable difference in safety scores to consider routes as tied.
    # Returns:
    #    dict: The dictionary representing the best route with keys 'path', 'score', 'string', and 'distance'.

    # Start by assuming the first route in our list is the best one
    best_route = scored_routes[0]

    # Loop through the rest of the evaluated routes to find the true optimal choice
    for route in scored_routes[1:]:
        # Condition A: If this route is strictly safer than our current best, select it
        if route['score'] < best_route['score']:
            # Tie-breaker: Is the old route's score within the tolerance of this new route?
            # And is the old route physically shorter? If so, keep the shorter one!
            if abs(best_route['score'] - route['score']) <= tolerance and best_route['distance'] < route['distance']:
                continue  # Skip updating; stick with the shorter route
            best_route = route
            
        # Condition B: If the safety scores are practically a tie 
        # (within the tolerance of each other)
        elif abs(route['score'] - best_route['score']) <= tolerance:
            # If the alternative route is physically shorter, pick it as the tie-breaker
            if route['distance'] < best_route['distance']:
                best_route = route

    return best_route



def calculate_route(start_port, end_port):
    # Finds, evaluates, and ranks the three shortest candidate paths.

    # 
    if start_port not in MARITIME_NETWORK or end_port not in MARITIME_NETWORK:
        raise ValueError("Please choose valid ports.")

    if start_port == end_port:
        raise ValueError("Start and end ports must be different.")

    all_paths = find_all_paths(MARITIME_NETWORK, start_port, end_port)

    if not all_paths:
        raise ValueError("No maritime route was found.")

    routes_with_distance = []

    for path in all_paths:
        routes_with_distance.append({
            "path": path,
            "distance": calculate_total_distance(path)
        })

    routes_with_distance.sort(key=lambda route: route["distance"])
    top_routes = routes_with_distance[:3]

    scored_routes = []

    for route in top_routes:
        evaluation = evaluate_full_path(route["path"])

        scored_routes.append({
            "path": route["path"],
            "distance": route["distance"],
            "score": evaluation["score"],
            "wave_height": evaluation["wave_height"],
            "wind_speed": evaluation["wind_speed"],
            "traffic_density": evaluation["traffic_density"],
            "used_fallback": evaluation["used_fallback"]
        })

    # Rank the three evaluated candidates using the score-and-distance rule
    # from the original terminal application.
    remaining_routes = scored_routes.copy()
    ranked_routes = []

    while remaining_routes:
        next_best_route = find_best_route(remaining_routes)
        ranked_routes.append(next_best_route)
        remaining_routes.remove(next_best_route)

    best_route = ranked_routes[0]

    return {
        "message": "Optimal route calculated successfully!",
        "start_port": start_port,
        "end_port": end_port,
        "path": best_route["path"],
        "distance": best_route["distance"],
        "score": best_route["score"],
        "wave_height": best_route["wave_height"],
        "wind_speed": best_route["wind_speed"],
        "traffic_density": best_route["traffic_density"],
        "used_fallback": best_route["used_fallback"],
        "routes": [
            {
                "rank": index + 1,
                "path": route["path"],
                "distance": route["distance"],
                "score": route["score"],
                "wave_height": route["wave_height"],
                "wind_speed": route["wind_speed"],
                "traffic_density": route["traffic_density"],
                "used_fallback": route["used_fallback"]
            }
            for index, route in enumerate(ranked_routes)
        ],
        "ports": [
            {"name": name, "lat": coordinates[0], "lon": coordinates[1]}
            for name, coordinates in PORT_COORDINATES.items()
        ]
    }
