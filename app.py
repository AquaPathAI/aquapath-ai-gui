from flask import Flask, render_template, request, jsonify
from route_calculator import calculate_route
app = Flask(__name__)


# Serves the main AquaPath web page.
@app.get("/")
def home():
    return render_template("Aquapath.html")

# For the JavaScript to request a route calculation
@app.post("/calculate-route")
def calculate_route_api():
    # Get the JavaScript's request as a dictionary
    data = request.get_json()

    try:
        # Use the calculate_route() function to evaluate the route
        result = calculate_route(
            data["startPort"],
            data["endPort"]
        )

        # Return the result as JSON
        return jsonify(result)

    # Catch errors caused by the route calculation
    except (KeyError, ValueError) as error:
        # Return the error as JSON
        return jsonify({
            "error": str(error)
        }), 400


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
