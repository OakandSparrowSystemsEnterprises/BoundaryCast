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

const SCOPE_LABELS = {
  exact_location: 'Exact location',
  microclimate_adjusted: 'Microclimate adjusted',
  nearby_observation_area: 'Nearby observation area',
  official_forecast_area: 'Official forecast area',
  official_alert_only: 'Official alert only',
  unsupported_specific_claim: 'Unsupported specific claim',
};

function showError(message) {
  $('result').innerHTML = `
    <h2>Forecast Verdict</h2>
    <div class="verdict">boundary failed</div>
    <p>${message}</p>
  `;
}

const MARKETS = {
  temp100: { metric: 'temperature_f', operator: 'gt', threshold: 100 },
  temp80: { metric: 'temperature_f', operator: 'gt', threshold: 80 },
  wind25: { metric: 'wind_mph', operator: 'gt', threshold: 25 },
  rain50: { metric: 'precip_probability', operator: 'gt', threshold: 0.5 },
  alert: { metric: 'alert_active', operator: 'gt', threshold: 0 },
};

function currentEvidenceBody() {
  const scenario = $('scenario').value;
  return {
    latitude: numberOrNull($('lat').value) ?? 37.7974,
    longitude: numberOrNull($('lon').value) ?? -121.2161,
    precision_meters: numberOrNull($('precision').value) ?? 25,
    surface_exposure: valueOrNull($('surface').value),
    shade_exposure: valueOrNull($('shade').value),
    wind_exposure: valueOrNull($('wind').value),
    elevation_meters: numberOrNull($('elevation').value),
    nearby_water: boolOrNull($('water').value),
    urban_density: valueOrNull($('urban').value),
    demo_mode: true,
    simulate_alert: scenario === 'alert',
    simulate_no_official_forecast: scenario === 'no_forecast' || scenario === 'nothing',
    simulate_no_observation: scenario === 'no_observation' || scenario === 'nothing'
  };
}

$('resolve').addEventListener('click', async () => {
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
      $('oracleResult').innerHTML = `<p>The oracle rejected the request (HTTP ${res.status}). ${detail.slice(0, 300)}</p>`;
      return;
    }
    const d = await res.json();
    const basis = d.resolution_basis;
    $('oracleResult').innerHTML = `
      <div class="resolution resolution-${d.resolution}">${d.resolution}</div>
      ${d.resolution_confidence ? `<p><strong>Confidence:</strong> ${d.resolution_confidence}</p>` : ''}
      <p>${d.detail}</p>
      ${d.escalation ? `<p class="fallback">Unresolved (<code>${d.unresolved_reason}</code>) — escalate to <strong>${d.escalation}</strong>. The oracle does not pretend.</p>` : ''}
      <div class="grid">
        <div class="pill"><small>Resolution basis scope</small><br><strong>${label(basis.claim_scope)}</strong></div>
        <div class="pill"><small>Market minimum scope</small><br><strong>${label(basis.requested_minimum_scope)}</strong></div>
        <div class="pill"><small>Gatekeeper verdict</small><br><strong>${label(basis.gatekeeper_verdict)}</strong></div>
        <div class="pill"><small>Evidence score</small><br><strong>${basis.evidence_score}</strong></div>
        <div class="pill"><small>Uncertainty</small><br><strong>${label(basis.uncertainty)}</strong></div>
        <div class="pill"><small>Observed value</small><br><strong>${d.condition.observed_value ?? '—'}</strong></div>
      </div>
      <h3>Resolution record</h3>
      <p>Artifact <code>${d.artifact.artifact_hash.slice(0, 18)}...</code> — replayable at <code>${d.replay_endpoint}</code><br>
      <small>Every resolution is bound to a hash-chained, replayable decision artifact.</small></p>
    `;
  } catch (error) {
    $('oracleResult').innerHTML = `<p>Could not reach the BoundaryCast API. ${String(error)}</p>`;
  } finally {
    button.disabled = false;
  }
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

    $('result').innerHTML = `
      <h2>Forecast Verdict</h2>
      <div class="verdict">${label(v.product_verdict)}</div>
      <div class="scope-badge scope-${v.claim_scope}">Forecast Scope: ${SCOPE_LABELS[v.claim_scope] ?? label(v.claim_scope)}</div>
      <p>${c.public_message}</p>
      ${fallbackNote}
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
      <h3>Why this scope?</h3>
      <p>${v.scope_reason_codes.map(x => `<code>${x}</code>`).join(' ')}</p>
      <h3>Why this verdict?</h3>
      <p>${v.reason_codes.length ? v.reason_codes.map(x => `<code>${x}</code>`).join(' ') : 'Evidence is sufficient for publication.'}</p>
      <h3>Artifact Status</h3>
      <p><code>${data.artifact.artifact_hash.slice(0, 18)}...</code> — ${replayStatus}<br>
      <small>location binding: <code>${data.artifact.location_binding_type}</code> · zero-cache: no identity, no location history</small></p>
    `;
  } catch (error) {
    showError(`Could not reach the BoundaryCast API. ${String(error)}`);
  } finally {
    button.disabled = false;
  }
});
