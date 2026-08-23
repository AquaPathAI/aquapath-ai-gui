"use strict";
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
    return port.dataset.port ?? "";
}
// This matches the equirectangular projection used by the world-map image.
function latLonToPixel(latitude, longitude, width, height) {
    return {
        x: ((longitude + 180) / 360) * width,
        y: ((90 - latitude) / 180) * height
    };
}
// Draws a line between two points on the canvas, wrapping around the edges if necessary.
function drawWrappedLine(context, start, end, width) {
    const xDifference = end.x - start.x;
    // If the line does not need to wrap, draw it normally.
    if (Math.abs(xDifference) <= width / 2) {
        context.moveTo(start.x, start.y);
        context.lineTo(end.x, end.y);
        return;
    }
    // Continue the short path at the other edge when crossing the date line
    // The offset decides whether the line should wrap to the left or right side of the canvas.
    const offset = xDifference > 0 ? -width : width;
    // Draw two lines: one from the start point to the edge, and another from the opposite edge to the end point.
    context.moveTo(start.x, start.y);
    context.lineTo(end.x + offset, end.y);
    context.moveTo(start.x - offset, start.y);
    context.lineTo(end.x, end.y);
}
// Draws the calculated routes and ports on the canvas overlaying the world map.
function drawRouteMap(result) {
    // Set the canvas size to match the world map image, accounting for device pixel ratio for high-DPI displays.
    const mapBounds = worldMap.getBoundingClientRect();
    const width = mapBounds.width;
    const height = mapBounds.height;
    const pixelRatio = window.devicePixelRatio || 1;
    // If the map is not visible or has zero dimensions, skip drawing to avoid errors.
    if (width === 0 || height === 0) {
        return;
    }
    // Set the canvas size and style to match the world map dimensions.
    routeCanvas.width = Math.round(width * pixelRatio);
    routeCanvas.height = Math.round(height * pixelRatio);
    routeCanvas.style.width = `${width}px`;
    routeCanvas.style.height = `${height}px`;
    // Get the drawing function context
    const context = routeCanvas.getContext("2d");
    if (context === null) {
        return;
    }
    // Transform the context to account for the pixel ratio
    context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
    // Clear the canvas before drawing new routes
    context.clearRect(0, 0, width, height);
    // Get an object with keys of ports and values of their pixel coordinates for drawing.
    const pointsByName = Object.fromEntries(
    // Loop through the ports in the result
    result.ports.map((port) => [
        // The key is the port name
        port.name,
        // The value is the pixel coordinates of the port on the canvas
        latLonToPixel(port.lat, port.lon, width, height)
    ]));
    // Define colors for the three routes to be drawn on the canvas
    const routeColors = ["#42e8ff", "#ffdf3e", "#ff5f9a"];
    // Loop through each route in the result and draw it on the canvas
    result.routes.forEach((route, index) => {
        // Set up the drawing context for the current route
        context.beginPath();
        context.strokeStyle = routeColors[index];
        context.lineWidth = 3.5;
        context.lineJoin = "round";
        context.lineCap = "round";
        // Set the line dash pattern based on the route index for visual distinction
        // If it is the second route, use a dashed line pattern of 11 pixels on and 8 pixels off
        // If it is the third route, use a dashed line pattern of 3 pixels on and 8 pixels off
        context.setLineDash(index === 1 ? [11, 8] : index === 2 ? [3, 8] : []);
        // Loop through the points in the route's path and draw lines between them, wrapping around the edges if necessary
        for (let pointIndex = 0; pointIndex < route.path.length - 1; pointIndex += 1) {
            drawWrappedLine(context, pointsByName[route.path[pointIndex]], pointsByName[route.path[pointIndex + 1]], width);
        }
        // Stroke the path to render it on the canvas
        context.stroke();
        // Reset the line dash pattern to solid for subsequent drawings
        context.setLineDash([]);
    });
    // Draw the ports on the canvas, highlighting those that are part of any route
    Object.entries(pointsByName).forEach(([name, point]) => {
        // Draw a white circle with a dark border for the port
        context.beginPath();
        context.fillStyle = "#ffffff";
        context.arc(point.x, point.y, 4, 0, Math.PI * 2);
        context.fill();
        context.lineWidth = 1.5;
        context.strokeStyle = "#160236";
        context.stroke();
        // If the port is part of any route, draw its name next to it
        if (result.routes.some((route) => route.path.includes(name))) {
            context.font = "600 12px Inter, sans-serif";
            context.fillStyle = "#160236";
            context.strokeStyle = "rgba(255, 255, 255, 0.9)";
            context.lineWidth = 3;
            context.strokeText(name, point.x + 7, point.y - 7);
            context.fillText(name, point.x + 7, point.y - 7);
        }
    });
}
// Creates the three result cards from the JSON returned by the Flask API.
function showRouteResults(result) {
    // Loop through the routes in the result and 
    // create an HTML article for each one, 
    // displaying its rank, score, path, distance, 
    // wave height, wind speed, and traffic density.
    routeList.innerHTML = result.routes.map((route) => `
        <article class="route-card route-card-${route.rank}">
            <h3>Route ${route.rank} <span>Score: ${route.score} / 5.00</span></h3>
            <p>${route.path.join(" → ")}</p>
            <p>${route.distance} NM · Waves ${route.wave_height} m · Wind ${route.wind_speed} km/h · Traffic ${route.traffic_density}</p>
        </article>
    `).join("");
    // Show the route results section and update the loading screen message.
    routeResults.hidden = false;
    loadingScreen.innerHTML = "<h2>Routes calculated</h2>";
    if (worldMap.complete) {
        // If the world map image is already loaded, draw the route map immediately.
        drawRouteMap(result);
    }
    else {
        // If the world map image is not yet loaded, 
        // wait for it to load before drawing the route map.
        worldMap.addEventListener("load", () => drawRouteMap(result), { once: true });
    }
    // Redraw the route map when the window is resized to maintain alignment with the world map.
    window.addEventListener("resize", () => drawRouteMap(result), { once: true });
}
// Add click event listeners to each port button to handle selection.
ports.forEach((port) => {
    port.addEventListener("click", () => {
        // Unselect all other ports
        ports.forEach((otherPort) => otherPort.classList.remove("selected"));
        // Select the clicked port and store it as the currently selected port
        port.classList.add("selected");
        selectedPort = port;
    });
});
// Add click event listener to the input button to handle the selection of 
// start and end ports, 
// and to start route calculation.
inputButton.addEventListener("click", async () => {
    // The same button advances users through start, end, and calculation stages.
    // If no port is confirmed as the start port, 
    // confirm the currently selected port as the start port.
    if (startPort === null) {
        if (selectedPort === null) {
            // If no port is selected, alert the user to select a start port.
            alert("Please select a start port.");
            // Return to wait for the user to select a start port.
            return;
        }
        // Confirm the selected port as the start port,
        startPort = getPortName(selectedPort);
        // Unselect the port
        selectedPort.classList.remove("selected");
        selectedPort = null;
        // Update the button text to prompt for the end port selection.
        inputButton.textContent = "Choose End Port";
        // Return to wait for the user to select an end port.
        return;
    }
    // If the start port is confirmed but no end port is confirmed,
    // confirm the currently selected port as the end port.
    if (endPort === null) {
        if (selectedPort === null) {
            // If no port is selected, alert the user to select an end port.
            alert("Please select an end port.");
            // Return to wait for the user to select an end port.
            return;
        }
        if (getPortName(selectedPort) === startPort) {
            // If the selected end port is the same as the start port, 
            // alert the user to select a different end port.
            alert("Start and end ports cannot be the same.");
            // Return to wait for the user to select a different end port.
            return;
        }
        // Confirm the selected port as the end port,
        endPort = getPortName(selectedPort);
        // Unselect the port
        selectedPort.classList.remove("selected");
        selectedPort = null;
        // Make all the port buttons unclickable to prevent further selection
        ports.forEach((port) => port.disabled = true);
        // Update the button text to indicate that the user can now calculate the route.
        inputButton.textContent = "Calculate Route";
        // Change the color of the button to indicate that the user can now calculate the route.
        inputButton.style.backgroundColor = "#42e8ff";
        inputButton.style.color = "#160236";
        // Return to wait for the user to click the button to calculate the route.
        return;
    }
    // If both start and end ports are confirmed, 
    // disable the button
    inputButton.disabled = true;
    // hide the input and port grid,
    portGrid.style.display = "none";
    inputButton.style.display = "none";
    introBox.style.display = "none";
    // and show the loading screen while calculating the route.
    loadingScreen.classList.add("is-visible");
    try {
        // Fetch the route calculation from the Flask API, 
        // sending the start and end ports as JSON in a POST request.
        const response = await fetch("/calculate-route", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ startPort, endPort })
        });
        // Parse the JSON response from the API.
        const result = await response.json();
        // If the response is not OK, 
        // throw an error with the message from the API or a default message.
        if (!response.ok) {
            throw new Error(result.error || "Route calculation failed.");
        }
        // If the route calculation is successful,
        // display the route results on the page.
        showRouteResults(result);
    }
    catch (error) {
        // The catch block handles any errors 
        // that occur during the fetch or JSON parsing process.
        // Log the error to the console for debugging purposes.
        console.error(error);
        // Display an error message on the loading screen to inform the user.
        const message = error instanceof Error ? error.message : "Unknown error.";
        loadingScreen.innerHTML = `
            <h2>Route calculation failed.</h2>
            <p>${message}</p>
        `;
    }
});
