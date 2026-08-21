// Pull DOM elements for later use.
const ports = document.querySelectorAll(".port-button");
const inputButton = document.getElementById("input");
const portGrid = document.querySelector(".port-grid");
const loadingScreen = document.getElementById("loading-screen");
const introBox = document.querySelector(".intro-box");
const routeResults = document.getElementById("route-results");
const routeList = document.getElementById("route-list");
const worldMap = document.getElementById("world-map");
const routeCanvas = document.getElementById("route-canvas");

// Variables to track the selected ports and the current stage of the input process.
let selectedPort = null;
let startPort = null;
let endPort = null;

// Returns the port name from the data-port attribute of the clicked button.
function getPortName(port) {
    // data-port avoids sending visual flag emojis to the Python route calculator.
    return port.dataset.port;
}

// This matches the equirectangular projection used by the world-map image.
function latLonToPixel(latitude, longitude, width, height) {
    return {
        x: ((longitude + 180) / 360) * width,
        y: ((90 - latitude) / 180) * height
    };
}

function drawWrappedLine(context, start, end, width) {
    const xDifference = end.x - start.x;

    if (Math.abs(xDifference) <= width / 2) {
        context.moveTo(start.x, start.y);
        context.lineTo(end.x, end.y);
        return;
    }

    // Continue the short path at the other edge when crossing the date line.
    const offset = xDifference > 0 ? -width : width;
    context.moveTo(start.x, start.y);
    context.lineTo(end.x + offset, end.y);
    context.moveTo(start.x - offset, start.y);
    context.lineTo(end.x, end.y);
}

function drawRouteMap(result) {
    const mapBounds = worldMap.getBoundingClientRect();
    const width = mapBounds.width;
    const height = mapBounds.height;
    const pixelRatio = window.devicePixelRatio || 1;

    if (width === 0 || height === 0) {
        return;
    }

    routeCanvas.width = Math.round(width * pixelRatio);
    routeCanvas.height = Math.round(height * pixelRatio);
    routeCanvas.style.width = `${width}px`;
    routeCanvas.style.height = `${height}px`;

    const context = routeCanvas.getContext("2d");
    context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
    context.clearRect(0, 0, width, height);

    const pointsByName = Object.fromEntries(
        result.ports.map((port) => [
            port.name,
            latLonToPixel(port.lat, port.lon, width, height)
        ])
    );
    const routeColors = ["#42e8ff", "#ffdf3e", "#ff5f9a"];

    result.routes.forEach((route, index) => {
        context.beginPath();
        context.strokeStyle = routeColors[index];
        context.lineWidth = 3.5;
        context.lineJoin = "round";
        context.lineCap = "round";
        context.setLineDash(index === 1 ? [11, 8] : index === 2 ? [3, 8] : []);

        for (let pointIndex = 0; pointIndex < route.path.length - 1; pointIndex += 1) {
            drawWrappedLine(
                context,
                pointsByName[route.path[pointIndex]],
                pointsByName[route.path[pointIndex + 1]],
                width
            );
        }

        context.stroke();
        context.setLineDash([]);
    });

    Object.entries(pointsByName).forEach(([name, point]) => {
        context.beginPath();
        context.fillStyle = "#ffffff";
        context.arc(point.x, point.y, 4, 0, Math.PI * 2);
        context.fill();
        context.lineWidth = 1.5;
        context.strokeStyle = "#160236";
        context.stroke();

        if (result.routes.some((route) => route.path.includes(name))) {
            context.font = "600 12px Poppins, sans-serif";
            context.fillStyle = "#160236";
            context.strokeStyle = "rgba(255, 255, 255, 0.9)";
            context.lineWidth = 3;
            context.strokeText(name, point.x + 7, point.y - 7);
            context.fillText(name, point.x + 7, point.y - 7);
        }
    });
}

function showRouteResults(result) {
    // Creates the three result cards from the JSON returned by the Flask API.
    routeList.innerHTML = result.routes.map((route) => `
        <article class="route-card route-card-${route.rank}">
            <h3>Route ${route.rank} <span>Score: ${route.score} / 5.00</span></h3>
            <p>${route.path.join(" → ")}</p>
            <p>${route.distance} NM · Waves ${route.wave_height} m · Wind ${route.wind_speed} km/h · Traffic ${route.traffic_density}</p>
        </article>
    `).join("");

    routeResults.hidden = false;
    loadingScreen.innerHTML = "<h2>Routes calculated</h2>";

    if (worldMap.complete) {
        drawRouteMap(result);
    } else {
        worldMap.addEventListener("load", () => drawRouteMap(result), { once: true });
    }

    window.addEventListener("resize", () => drawRouteMap(result), { once: true });
}

ports.forEach((port) => {
    port.addEventListener("click", () => {
        ports.forEach((otherPort) => otherPort.classList.remove("selected"));
        port.classList.add("selected");
        selectedPort = port;
    });
});

inputButton.addEventListener("click", async () => {
    // The same button advances users through start, end, and calculation stages.
    if (startPort === null) {
        if (selectedPort === null) {
            alert("Please select a start port.");
            return;
        }

        startPort = getPortName(selectedPort);
        selectedPort.classList.remove("selected");
        selectedPort = null;
        inputButton.textContent = "Choose End Port";
        return;
    }

    if (endPort === null) {
        if (selectedPort === null) {
            alert("Please select an end port.");
            return;
        }

        if (getPortName(selectedPort) === startPort) {
            alert("Start and end ports cannot be the same.");
            return;
        }

        endPort = getPortName(selectedPort);
        selectedPort.classList.remove("selected");
        selectedPort = null;
        inputButton.textContent = "Calculate Route";
        return;
    }

    inputButton.disabled = true;
    portGrid.style.display = "none";
    inputButton.style.display = "none";
    introBox.style.display = "none";
    loadingScreen.classList.add("is-visible");

    try {
        // Fetch sends the selected ports to the Flask /calculate-route endpoint.
        const response = await fetch("/calculate-route", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ startPort, endPort })
        });
        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Route calculation failed.");
        }

        showRouteResults(result);
        
    } catch (error) {
        console.error(error);
        loadingScreen.innerHTML = `
            <h2>Route calculation failed.</h2>
            <p>${error.message}</p>
        `;
    }
});
