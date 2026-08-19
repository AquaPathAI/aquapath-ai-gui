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
    "Mumbai": {"Aden": 1650, "Dubai": 930, "Singapore": 2440, "Cape Town": 4600},
    "Singapore": {"Mumbai": 2440, "Shanghai": 2500, "Tokyo": 2900, "Los Angeles": 7600},
    "Shanghai": {"Singapore": 2500, "Tokyo": 1000, "Los Angeles": 5700},
    "Tokyo": {"Shanghai": 1000, "Singapore": 2900, "Los Angeles": 5400, "Panama Canal": 7600},
    "Dubai": {"Mumbai": 930, "Aden": 1400},
    "Aden": {"Dubai": 1400, "Mumbai": 1650, "Suez": 1300, "Cape Town": 3900},
    "Suez": {"Aden": 1300, "Gibraltar": 1900},
    "Cape Town": {"Mumbai": 4600, "Aden": 3900, "Santos": 3300, "Gibraltar": 4500},
    "Gibraltar": {"Suez": 1900, "Cape Town": 4500, "Rotterdam": 1300, "New York": 3100},
    "Rotterdam": {"Gibraltar": 1300, "Hamburg": 250, "New York": 3400},
    "Hamburg": {"Rotterdam": 250, "New York": 3500},
    "New York": {"Gibraltar": 3100, "Rotterdam": 3400, "Hamburg": 3500, "Panama Canal": 2000, "Santos": 4800},
    "Los Angeles": {"Tokyo": 5400, "Shanghai": 5700, "Singapore": 7600, "Panama Canal": 2900},
    "Panama Canal": {"Los Angeles": 2900, "New York": 2000, "Santos": 3400, "Tokyo": 7600},
    "Santos": {"Cape Town": 3300, "Panama Canal": 3400, "New York": 4800}
}


def find_all_paths(graph, start, end, path=None):
    if path is None:
        path = []

    path = path + [start]

    if start == end:
        return [path]

    if start not in graph:
        return []

    paths = []

    for port in graph[start]:
        if port not in path:
            paths.extend(find_all_paths(graph, port, end, path))

    return paths


def calculate_total_distance(path):
    total_distance = 0

    for index in range(len(path) - 1):
        total_distance += MARITIME_NETWORK[path[index]][path[index + 1]]

    return total_distance


def evaluate_full_path(path):
    total_wind = 0
    total_wave = 0
    wind_checks = 0
    wave_checks = 0
    total_traffic = 0
    traffic_checks = 0

    for port in path:
        latitude, longitude = PORT_COORDINATES[port]

        weather_url = (
            f"https://api.open-meteo.com/v1/forecast?"
            f"latitude={latitude}&longitude={longitude}&current=wind_speed_10m"
        )

        marine_url = (
            f"https://marine-api.open-meteo.com/v1/marine?"
            f"latitude={latitude}&longitude={longitude}&current=wave_height"
        )

        try:
            wind_response = requests.get(weather_url, timeout=5)
            wave_response = requests.get(marine_url, timeout=5)

            if wind_response.status_code == 200:
                wind_speed = wind_response.json()["current"]["wind_speed_10m"]

                if wind_speed is not None:
                    total_wind += wind_speed
                    wind_checks += 1

            if wave_response.status_code == 200:
                wave_height = wave_response.json()["current"]["wave_height"]

                if wave_height is not None:
                    total_wave += wave_height
                    wave_checks += 1

        except (requests.RequestException, KeyError):
            pass

    for index in range(len(path) - 1):
        leg_start = path[index]
        leg_end = path[index + 1]

        try:
            with open("traffic_data.csv", mode="r") as file:
                reader = csv.reader(file)
                next(reader, None)

                for row in reader:
                    if (
                        (row[0] == leg_start and row[1] == leg_end)
                        or (row[0] == leg_end and row[1] == leg_start)
                    ):
                        total_traffic += int(row[2])
                        traffic_checks += 1
                        break

        except FileNotFoundError:
            pass

    used_fallback = False

    if wind_checks > 0:
        wind_speed = total_wind / wind_checks
    else:
        wind_speed = 15.0
        used_fallback = True

    if wave_checks > 0:
        wave_height = total_wave / wave_checks
    else:
        wave_height = 2.0
        used_fallback = True

    if traffic_checks > 0:
        traffic_density = total_traffic / traffic_checks
    else:
        traffic_density = 20
    
    weather_risk = (wave_height * 0.5107) + (wind_speed * 0.024) + 0.0105
    weather_risk = max(0.0, min(5.0, weather_risk))

    traffic_risk = (traffic_density * 0.0484) + 0.0407
    traffic_risk = max(0.0, min(5.0, traffic_risk))

    final_score = (weather_risk * 0.65) + (traffic_risk * 0.35)

    return {
        "score": round(final_score, 2),
        "wave_height": round(wave_height, 1),
        "wind_speed": round(wind_speed, 1),
        "traffic_density": int(traffic_density),
        "used_fallback": used_fallback
    }


def find_best_route(scored_routes, tolerance=0.25):
    best_route = scored_routes[0]

    for route in scored_routes[1:]:
        if route["score"] < best_route["score"]:
            if (
                abs(best_route["score"] - route["score"]) <= tolerance
                and best_route["distance"] < route["distance"]
            ):
                continue

            best_route = route

        elif abs(route["score"] - best_route["score"]) <= tolerance:
            if route["distance"] < best_route["distance"]:
                best_route = route

    return best_route


def calculate_route(start_port, end_port):
    # Finds, evaluates, and ranks the three shortest candidate paths.
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
