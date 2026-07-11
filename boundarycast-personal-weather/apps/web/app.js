const $ = (id) => document.getElementById(id);

function valueOrNull(v) { return v && v.trim() ? v.trim() : null; }

function numberOrNull(v) {
  if (v === null || v === undefined || String(v).trim() === '') return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function boolOrNull(v) {
  if (v === 'true') return true;
  if (v === 'false') return false;
  return null;
}

function showError(message) {
  $('result').innerHTML = `
    <h2>Forecast Verdict</h2>
    <div class="verdict">boundary failed</div>
    <p>${message}</p>
  `;
}

$('run').addEventListener('click', async () => {
  const lat = numberOrNull($('lat').value);
  const lon = numberOrNull($('lon').value);
  const precision = numberOrNull($('precision').value);

  if (lat === null || lon === null || lat < -90 || lat > 90 || lon < -180 || lon > 180) {
    showError('Latitude must be between -90 and 90 and longitude between -180 and 180.');
    return;
  }

  const body = {
    latitude: lat,
    longitude: lon,
    precision_meters: precision ?? 25,
    surface_exposure: valueOrNull($('surface').value),
    shade_exposure: valueOrNull($('shade').value),
    wind_exposure: valueOrNull($('wind').value),
    elevation_meters: numberOrNull($('elevation').value),
    nearby_water: boolOrNull($('water').value),
    urban_density: valueOrNull($('urban').value),
    demo_mode: true
  };

  const button = $('run');
  button.disabled = true;
  $('result').innerHTML = '<h2>Forecast Verdict</h2><p>Checking evidence, policy, and artifact path...</p>';

  try {
    const res = await fetch('/api/v1/personal-forecast', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });

    if (!res.ok) {
      const detail = await res.text();
      showError(`The API rejected the request (HTTP ${res.status}). ${detail.slice(0, 300)}`);
      return;
    }

    const data = await res.json();
    const v = data.verdict;
    const c = data.claim;
    const e = data.epistemology;

    $('result').innerHTML = `
      <h2>Forecast Verdict</h2>
      <div class="verdict">${v.product_verdict.replaceAll('_', ' ')}</div>
      <p>${c.summary}</p>
      <div class="grid">
        <div class="pill"><small>Microclimate confidence</small><br><strong>${v.microclimate_confidence}</strong></div>
        <div class="pill"><small>Knowledge state</small><br><strong>${e.knowledge_state}</strong></div>
        <div class="pill"><small>Evidence score</small><br><strong>${e.evidence_score}</strong></div>
        <div class="pill"><small>Uncertainty</small><br><strong>${e.uncertainty.replaceAll('_', ' ')}</strong></div>
        <div class="pill"><small>Temperature</small><br><strong>${c.temperature_f ?? 'unknown'}°F</strong></div>
        <div class="pill"><small>Precipitation</small><br><strong>${Math.round((c.precip_probability ?? 0) * 100)}%</strong></div>
      </div>
      <h3>Why</h3>
      <p>${v.reason_codes.length ? v.reason_codes.map(x => `<code>${x}</code>`).join(' ') : 'Evidence is sufficient for publication.'}</p>
      <h3>Artifact</h3>
      <p>Created: <code>${data.artifact.artifact_hash.slice(0, 18)}...</code></p>
    `;
  } catch (error) {
    showError(`Could not reach the BoundaryCast API. ${String(error)}`);
  } finally {
    button.disabled = false;
  }
});
