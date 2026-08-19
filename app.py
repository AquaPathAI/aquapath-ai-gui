from flask import Flask, render_template, request, jsonify
from route_calculator import calculate_route as calculate_optimal_route
app = Flask(__name__)


# Serves the main AquaPath web page.
@app.get("/")
def home():
    return render_template("Aquapath.html")


@app.get("/about-us")
def about_us():
    return render_template("About us page.html")


@app.get("/how-it-works")
def how_it_works():
    return render_template("About Aquapath.html")


@app.post("/calculate-route")
def calculate_route_api():
    # JavaScript sends the two selected ports as JSON; Flask returns JSON results.
    data = request.get_json()

    try:
        result = calculate_optimal_route(
            data["startPort"],
            data["endPort"]
        )

        return jsonify(result)

    except (KeyError, ValueError) as error:
        return jsonify({
            "error": str(error)
        }), 400


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False)
