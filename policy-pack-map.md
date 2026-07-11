<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>BoundaryCast | Your Weather</title>
  <link rel="stylesheet" href="styles.css" />
</head>
<body>
  <main class="shell">
    <section class="hero">
      <p class="eyebrow">BoundaryCast</p>
      <h1>Your Weather</h1>
      <p class="sub">A governed personal forecast for the exact place you are, with evidence, caution, and replayable proof.</p>
    </section>

    <section class="card controls">
      <label>Latitude <input id="lat" type="number" step="0.0001" min="-90" max="90" value="37.7974" /></label>
      <label>Longitude <input id="lon" type="number" step="0.0001" min="-180" max="180" value="-121.2161" /></label>
      <label>Precision meters <input id="precision" type="number" min="1" value="25" /></label>
      <label>Surface exposure <input id="surface" placeholder="asphalt, grass, roof" /></label>
      <label>Shade exposure <input id="shade" placeholder="open sun, tree shade, building shade" /></label>
      <label>Wind exposure <input id="wind" placeholder="sheltered, open, exposed" /></label>
      <label>Elevation meters <input id="elevation" type="number" step="1" placeholder="unknown" /></label>
      <label>Nearby water
        <select id="water"><option value="">unknown</option><option value="true">yes</option><option value="false">no</option></select>
      </label>
      <label>Urban density
        <select id="urban"><option value="">unknown</option><option>low</option><option>medium</option><option>high</option></select>
      </label>
      <button id="run">Generate governed forecast</button>
    </section>

    <section class="card" id="result">
      <h2>Forecast Verdict</h2>
      <p>Run the demo to generate a governed personal forecast.</p>
    </section>
  </main>
  <script src="app.js"></script>
</body>
</html>
