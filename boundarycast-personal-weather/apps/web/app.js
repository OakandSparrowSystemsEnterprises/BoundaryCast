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

function label(v) { return String(v ?? 'unknown').replaceAll('_', ' '); }

// Escape anything user- or API-supplied before it reaches innerHTML.
function esc(v) {
  return String(v ?? '').replace(/[&<>"']/g, (c) => (
    { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]
  ));
}

const SCOPE_LABELS = {
  exact_location: 'Exact location',
  microclimate_adjusted: 'Microclimate adjusted',
  nearby_observation_area: 'Nearby observation area',
  official_forecast_area: 'Official forecast area',
  official_alert_only: 'Official alert only',
  unsupported_specific_claim: 'Unsupported specific claim',
};

const SCOPE_LADDER = ['exact_location', 'microclimate_adjusted', 'nearby_observation_area', 'official_forecast_area'];
let activeLocationName = 'San Francisco, California';
let activeLocationKind = 'demo starting point';

function showActiveLocation() {
  $('locationNow').innerHTML = `Showing: <strong>${esc(activeLocationName)}</strong> <span>${esc(activeLocationKind)}</span>`;
}

function scopeLadderHtml(v) {
  const special = v.claim_scope === 'official_alert_only' || v.claim_scope === 'unsupported_specific_claim';
  const rows = SCOPE_LADDER.map(s => {
    const granted = v.claim_scope === s;
    const requested = v.requested_scope === s;
    return `<div class="rung ${granted ? 'granted' : ''}${requested && !granted ? ' requested' : ''}">
      <span class="rung-dot"></span><span class="rung-name">${label(s)}</span>
      ${requested ? '<span class="rung-tag">requested</span>' : ''}
      ${granted ? '<span class="rung-tag got">granted</span>' : ''}
    </div>`;
  }).join('');
  const specialRow = special
    ? `<div class="rung special granted"><span class="rung-dot"></span><span class="rung-name">${label(v.claim_scope)}</span><span class="rung-tag got">${v.claim_scope === 'official_alert_only' ? 'governs' : 'withheld'}</span></div>`
    : '';
  return `<div class="ladder"><small>Claim scope ladder — how specific the evidence lets us be</small>${rows}${specialRow}</div>`;
}

function checksHtml(e) {
  const entries = Object.entries(e).filter(([, val]) => typeof val === 'boolean');
  const passing = entries.filter(([, val]) => val).length;
  const pills = entries.map(([k, val]) =>
    `<span class="check ${val ? 'ok' : 'bad'}">${val ? '✓' : '✗'} ${esc(label(k))}</span>`).join('');
  return `<details class="checks"><summary>Epistemology — ${passing}/${entries.length} checks passing</summary><div class="check-grid">${pills}</div></details>`;
}

function bandHtml(c) {
  const b = c.uncertainty_interval;
  if (!b) return '';
  return `<div class="band"><small>Uncertainty band (public proxy)</small>
    <div class="band-bar"><span>${esc(b.temperature_low_f)}°F</span><div class="band-track"><div class="band-fill"></div></div><span>${esc(b.temperature_high_f)}°F</span></div>
    <small>±${esc(b.spread_f)}°F from observation distance, evidence staleness, and microclimate context</small></div>`;
}

function showError(message) {
  $('result').innerHTML = `
    <h2>Forecast Verdict</h2>
    <div class="verdict">boundary failed</div>
    <p>${esc(message)}</p>
  `;
}

const MARKETS = {
  temp100: { metric: 'temperature_f', operator: 'gt', threshold: 100 },
  temp80: { metric: 'temperature_f', operator: 'gt', threshold: 80 },
  wind25: { metric: 'wind_mph', operator: 'gt', threshold: 25 },
  rain50: { metric: 'precip_probability', operator: 'gt', threshold: 0.5 },
  alert: { metric: 'alert_active', operator: 'gt', threshold: 0 },
};

function coordinatesValid() {
  const lat = numberOrNull($('lat').value);
  const lon = numberOrNull($('lon').value);
  return lat !== null && lon !== null && lat >= -90 && lat <= 90 && lon >= -180 && lon <= 180;
}

function currentEvidenceBody() {
  return {
    latitude: numberOrNull($('lat').value) ?? 37.7749,
    longitude: numberOrNull($('lon').value) ?? -122.4194,
    precision_meters: numberOrNull($('precision').value) ?? 25,
    surface_exposure: valueOrNull($('surface').value),
    shade_exposure: valueOrNull($('shade').value),
    wind_exposure: valueOrNull($('wind').value),
    elevation_meters: numberOrNull($('elevation').value),
    nearby_water: boolOrNull($('water').value),
    urban_density: valueOrNull($('urban').value),
    // Live evidence when the server has BOUNDARYCAST_LIVE_EVIDENCE=1;
    // the server falls back to demo stubs automatically if live fails.
    demo_mode: false,
    ...scenarioOverrides()
  };
}

$('resolve').addEventListener('click', async () => {
  if (!coordinatesValid()) {
    $('oracleResult').innerHTML = '<p>Latitude must be between -90 and 90 and longitude between -180 and 180.</p>';
    return;
  }
  const marketKey = $('market').value;
  const body = {
    ...currentEvidenceBody(),
    ...MARKETS[marketKey],
    market_id: `market_demo_${marketKey}`,
    question: $('market').options[$('market').selectedIndex].text,
    minimum_scope: $('minScope').value,
  };
  const button = $('resolve');
  button.disabled = true;
  $('oracleResult').innerHTML = '<p>Resolving against governed forecast claim...</p>';
  try {
    const res = await fetch('/api/v1/oracle/resolve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    if (!res.ok) {
      const detail = await res.text();
      $('oracleResult').innerHTML = `<p>The oracle rejected the request (HTTP ${res.status}). ${esc(detail.slice(0, 300))}</p>`;
      return;
    }
    const d = await res.json();
    const basis = d.resolution_basis;
    $('oracleResult').innerHTML = `
      <div class="resolution resolution-${esc(d.resolution)}">${esc(d.resolution)}</div>
      ${d.resolution_confidence ? `<p><strong>Confidence:</strong> ${esc(d.resolution_confidence)}</p>` : ''}
      <p>${esc(d.detail)}</p>
      ${d.escalation ? `<p class="fallback">Unresolved (<code>${esc(d.unresolved_reason)}</code>) — escalate to <strong>${esc(d.escalation)}</strong>. The oracle does not pretend.</p>` : ''}
      <div class="grid">
        <div class="pill"><small>Resolution basis scope</small><br><strong>${label(basis.claim_scope)}</strong></div>
        <div class="pill"><small>Market minimum scope</small><br><strong>${label(basis.requested_minimum_scope)}</strong></div>
        <div class="pill"><small>BoundaryCast verdict</small><br><strong>${label(basis.gatekeeper_verdict)}</strong></div>
        <div class="pill"><small>Evidence score</small><br><strong>${basis.evidence_score}</strong></div>
        <div class="pill"><small>Uncertainty</small><br><strong>${label(basis.uncertainty)}</strong></div>
        <div class="pill"><small>Observed value</small><br><strong>${d.condition.observed_value ?? '—'}</strong></div>
      </div>
      <h3>Resolution record</h3>
      <p>Artifact <code>${d.artifact.artifact_hash.slice(0, 18)}...</code> — replayable at <code>${d.replay_endpoint}</code><br>
      <small>Every resolution is bound to a hash-chained, replayable decision artifact.</small></p>
    `;
  } catch (error) {
    $('oracleResult').innerHTML = `<p>Could not reach the BoundaryCast API. ${esc(String(error))}</p>`;
  } finally {
    button.disabled = false;
  }
});

// --- Use my location: real coordinates from the browser, never stored ---

$('geo').addEventListener('click', () => {
  if (!navigator.geolocation) {
    $('locationStatus').textContent = 'Geolocation unavailable in this browser — using demo coordinates.';
    return;
  }
  $('locationStatus').textContent = 'Locating…';
  navigator.geolocation.getCurrentPosition((pos) => {
    $('lat').value = pos.coords.latitude.toFixed(4);
    $('lon').value = pos.coords.longitude.toFixed(4);
    $('precision').value = Math.max(1, Math.min(100000, Math.round(pos.coords.accuracy || 25)));
    activeLocationName = `Current location (${pos.coords.latitude.toFixed(3)}, ${pos.coords.longitude.toFixed(3)})`;
    activeLocationKind = 'live device location';
    showActiveLocation();
    const accuracy = Math.round(pos.coords.accuracy || 25);
    $('locationStatus').textContent = accuracy <= 250
      ? `Using your live location (accurate within ${accuracy} m) — never stored.`
      : `Device location is only accurate within ${accuracy} m. Exact scope requires 250 m or better; enable precise location services and retry.`;
    $('run').click();
  }, () => {
    $('locationStatus').textContent = 'Location permission denied — using demo coordinates.';
  }, { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 });
});

// --- Destination lookup: separate from device location, zero history ---

$('destinationForm').addEventListener('submit', async (event) => {
  event.preventDefault();
  const query = $('destination').value.trim();
  if (query.length < 2) return;
  const target = $('destinationResults');
  target.innerHTML = '<p>Finding locations...</p>';
  try {
    const res = await fetch(`/api/v1/locations/search?q=${encodeURIComponent(query)}`);
    if (!res.ok) throw new Error(`search failed (HTTP ${res.status})`);
    const data = await res.json();
    target.innerHTML = data.results.length ? data.results.map((place, index) => `
      <button type="button" class="destination-result" data-place="${index}">
        <strong>${esc(place.name)}</strong><small>${Number(place.latitude).toFixed(3)}, ${Number(place.longitude).toFixed(3)}</small>
      </button>`).join('') : '<p>No matching destinations found.</p>';
    target.querySelectorAll('[data-place]').forEach((button) => {
      button.addEventListener('click', () => {
        const place = data.results[Number(button.dataset.place)];
        $('lat').value = Number(place.latitude).toFixed(4);
        $('lon').value = Number(place.longitude).toFixed(4);
        $('precision').value = 1000;
        activeLocationName = place.name;
        activeLocationKind = 'destination forecast';
        showActiveLocation();
        target.innerHTML = `<p class="destination-selected">Checking ${esc(place.name)} now.</p>`;
        $('run').click();
      });
    });
  } catch (error) {
    target.innerHTML = `<p>Could not search locations. ${esc(String(error))}</p>`;
  }
});

// --- Call the Weather ---

function scenarioOverrides() {
  const scenario = $('scenario').value;
  return {
    simulate_alert: scenario === 'alert',
    simulate_no_official_forecast: scenario === 'no_forecast' || scenario === 'nothing',
    simulate_no_observation: scenario === 'no_observation' || scenario === 'nothing'
  };
}

function marketCard(m) {
  const res = m.resolution;
  const total = m.pools.YES + m.pools.NO;
  const yesPct = total > 0 ? Math.round((m.pools.YES / total) * 100) : 50;
  const payoutRows = (m.payouts ?? []).map(p =>
    `<small>${esc(p.trader)} (${esc(p.kind)}): ${esc(p.payout)}</small>`).join('<br>');
  return `
    <div class="market">
      <div class="market-q"><strong>${esc(m.question)}</strong></div>
      <div class="market-meta">
        <span class="pill-inline">status: <strong>${esc(label(m.status))}</strong></span>
        <span class="pill-inline">YES pool: ${m.pools.YES}</span>
        <span class="pill-inline">NO pool: ${m.pools.NO}</span>
        <span class="pill-inline">implied YES: ${yesPct}%</span>
      </div>
      ${m.status === 'open' ? `
        <div class="market-actions">
          <button data-stake="YES" data-market="${m.market_id}">Stake 10 on YES</button>
          <button data-stake="NO" data-market="${m.market_id}">Stake 10 on NO</button>
          <button data-settle="${m.market_id}" class="settle">Resolve with BoundaryCast</button>
        </div>` : `
        <div class="market-resolution">
          <strong>${esc(res.resolution)}</strong>${res.resolution_confidence ? ` (${esc(res.resolution_confidence)})` : ''} — ${esc(res.detail)}<br>
          <small>BoundaryCast verdict: ${res.gatekeeper_verdict} · claim scope: ${label(res.claim_scope)} · artifact <code>${res.artifact_hash.slice(0, 14)}...</code></small><br>
          <small>reason codes: ${[...(res.scope_reason_codes ?? []), ...(res.reason_codes ?? [])].map(x => `<code>${x}</code>`).join(' ') || '<code>none</code>'}</small>
          ${payoutRows ? `<br>${payoutRows}` : ''}
        </div>`}
    </div>`;
}

async function loadMarkets() {
  try {
    const [data, replay] = await Promise.all([
      fetch('/api/v1/markets').then(r => r.json()),
      fetch('/api/v1/replay').then(r => r.json()).catch(() => null),
    ]);
    const replayLine = replay
      ? `<p class="replay-line">Replay status: ${replay.ok ? `artifact chain verified (${replay.count} artifacts)` : `CHAIN FAILED — ${esc(replay.error)}`}</p>`
      : '';
    const cf = data.crowd_feedback;
    const crowdLine = cf && cf.markets_scored
      ? `<p class="crowd-line">🏆 Crowd vs oracle: ${cf.crowd_correct}/${cf.markets_scored} calls right · Brier ${cf.crowd_brier_score} — your stakes are votes, recorded as a calibration signal the forecast can train on.</p>`
      : '<p class="crowd-line">🏆 Call YES or NO below — the crowd\'s calls get scored against BoundaryCast and recorded as a training signal.</p>';
    $('marketBoard').innerHTML = replayLine + crowdLine + (data.markets.length
      ? data.markets.map(marketCard).join('')
      : '<p>No weather calls yet. Load the demonstration calls.</p>');
  } catch (error) {
    $('marketBoard').innerHTML = `<p>Could not load markets. ${esc(String(error))}</p>`;
  }
}

$('seedMarkets').addEventListener('click', async () => {
  await fetch('/api/v1/markets/reset-demo', { method: 'POST' });
  loadMarkets();
});
$('refreshMarkets').addEventListener('click', loadMarkets);

$('marketBoard').addEventListener('click', async (event) => {
  const btn = event.target.closest('button');
  if (!btn) return;
  try {
    if (btn.dataset.stake) {
      await fetch(`/api/v1/markets/${btn.dataset.market}/stake`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ side: btn.dataset.stake, amount: 10, trader: 'you' })
      });
    } else if (btn.dataset.settle) {
      btn.disabled = true;
      await fetch(`/api/v1/markets/${btn.dataset.settle}/settle`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        // Settle against the location and evidence currently visible in the
        // app, never the synthetic coordinates stored in the seeded call.
        body: JSON.stringify(currentEvidenceBody())
      });
    } else {
      return;
    }
  } catch (error) {
    $('marketBoard').insertAdjacentHTML('afterbegin',
      `<p>Market action failed. ${esc(String(error))}</p>`);
  } finally {
    btn.disabled = false;
  }
  loadMarkets();
});

$('run').addEventListener('click', async () => {
  const lat = numberOrNull($('lat').value);
  const lon = numberOrNull($('lon').value);

  if (lat === null || lon === null || lat < -90 || lat > 90 || lon < -180 || lon > 180) {
    showError('Latitude must be between -90 and 90 and longitude between -180 and 180.');
    return;
  }

  const body = { ...currentEvidenceBody(), requested_scope: $('requestedScope').value };

  const button = $('run');
  button.disabled = true;
  $('result').innerHTML = '<h2>Forecast Verdict</h2><p>Checking evidence, policy, scope, and artifact path...</p>';

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
    const loc = data.location_context;
    const alertCount = v.claim_scope === 'official_alert_only' ? 'ACTIVE — alert governs' : 'none active';
    const locationSpecificity = `${loc.precision_meters} m ${loc.personal_location_language_allowed ? '(personal-location language allowed)' : '(too coarse for personal-location language)'}`;
    const fallbackNote = v.fallback_applied
      ? `<p class="fallback">Requested scope <code>${label(v.requested_scope)}</code> was not supported by the evidence, so BoundaryCast fell back to the highest supported scope instead of refusing to answer.</p>`
      : '';

    let replayStatus = 'recorded';
    try {
      const replay = await (await fetch('/api/v1/replay')).json();
      replayStatus = replay.ok ? `chain verified (${replay.count} artifacts)` : `chain FAILED: ${replay.error}`;
    } catch { replayStatus = 'recorded (replay check unavailable)'; }

    const b = c.uncertainty_interval;
    const alertChip = c.alert_active
      ? `<span class="chip chip-alert">⚠ ${esc(c.alert_headline || 'Official alert active')}</span>`
      : '<span class="chip chip-ok">No official alerts</span>';
    const live = Object.values(data.evidence_sources ?? {}).some(s => String(s).includes('live'));
    const unavailable = Object.values(data.evidence_sources ?? {}).some(s => String(s).includes('unavailable'));
    const sourceChip = `<span class="chip">${live ? '🌐 live public data' : unavailable ? 'live data unavailable' : 'demo data'}</span>`;

    $('result').innerHTML = `
      <div class="instant">
        <div class="instant-temp">${c.temperature_f ?? '—'}<span class="deg">°F</span></div>
        <div class="instant-main">
          <div class="instant-line">${esc(c.summary)}</div>
          <div class="forecast-place">${esc(activeLocationName)} · ${esc(activeLocationKind)}</div>
          <div class="instant-sub">${b ? `${esc(b.temperature_low_f)}–${esc(b.temperature_high_f)}°F expected · ` : ''}${c.precip_probability != null ? Math.round(c.precip_probability * 100) + '% rain chance · ' : ''}checked ${e.evidence_score != null ? Math.round(e.evidence_score * 100) : 0}% of evidence gates</div>
          <div class="chip-row">${alertChip}<span class="chip">${SCOPE_LABELS[v.claim_scope] ?? esc(label(v.claim_scope))}</span><span class="chip">${label(v.product_verdict)}</span>${sourceChip}</div>
        </div>
      </div>
      <div class="scope-badge scope-${esc(v.claim_scope)}">Forecast Scope: ${SCOPE_LABELS[v.claim_scope] ?? esc(label(v.claim_scope))}</div>
      <p>${esc(c.public_message)}</p>
      ${fallbackNote}
      ${scopeLadderHtml(v)}
      <details class="govdetail">
        <summary>Full governance detail — verdict, evidence, uncertainty, artifact</summary>
        <h2>Forecast Verdict</h2>
        <div class="verdict">${label(v.product_verdict)}</div>
        <div class="grid">
          <div class="pill"><small>Forecast scope</small><br><strong>${label(v.claim_scope)}</strong></div>
          <div class="pill"><small>Requested scope</small><br><strong>${label(v.requested_scope)}</strong></div>
          <div class="pill"><small>Location specificity</small><br><strong>${locationSpecificity}</strong></div>
          <div class="pill"><small>Microclimate confidence</small><br><strong>${v.microclimate_confidence}</strong></div>
          <div class="pill"><small>Evidence score</small><br><strong>${e.evidence_score}</strong></div>
          <div class="pill"><small>Uncertainty</small><br><strong>${label(e.uncertainty)}</strong></div>
          <div class="pill"><small>Official alert</small><br><strong>${alertCount}</strong></div>
          <div class="pill"><small>Knowledge state</small><br><strong>${e.knowledge_state}</strong></div>
          <div class="pill"><small>Temperature</small><br><strong>${c.temperature_f ?? 'unknown'}${c.temperature_f != null ? '°F' : ''}</strong></div>
          <div class="pill"><small>Precipitation</small><br><strong>${c.precip_probability != null ? Math.round(c.precip_probability * 100) + '%' : 'unknown'}</strong></div>
        </div>
        ${bandHtml(c)}
        ${checksHtml(e)}
        <h3>Why this scope?</h3>
        <p>${v.scope_reason_codes.map(x => `<code>${x}</code>`).join(' ')}</p>
        <h3>Why this verdict?</h3>
        <p>${v.reason_codes.length ? v.reason_codes.map(x => `<code>${x}</code>`).join(' ') : 'Evidence is sufficient for publication.'}</p>
        <h3>Artifact Status</h3>
        <p><code>${data.artifact.artifact_hash.slice(0, 18)}...</code> — ${replayStatus}<br>
        <small>location binding: <code>${data.artifact.location_binding_type}</code> · zero-cache: no identity, no location history</small></p>
      </details>
    `;
  } catch (error) {
    showError(`Could not reach the BoundaryCast API. ${String(error)}`);
  } finally {
    button.disabled = false;
  }
});

// --- Auto-populate on load: the answer, not a form ---
(async function init() {
  showActiveLocation();
  try { await fetch('/api/v1/markets/seed-demo', { method: 'POST' }); } catch { /* board shows its own error */ }
  loadMarkets();
  $('run').click();
})();

