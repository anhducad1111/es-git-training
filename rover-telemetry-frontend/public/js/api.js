window.Api = (function () {
  function buildQuery(params) {
    const usp = new URLSearchParams();
    Object.entries(params || {}).forEach(([key, value]) => {
      if (value !== undefined && value !== null && value !== '') {
        usp.set(key, value);
      }
    });
    const qs = usp.toString();
    return qs ? `?${qs}` : '';
  }

  async function request(path, options) {
    const url = `${window.APP_CONFIG.API_BASE_URL}${path}`;
    let response;
    try {
      response = await fetch(url, options || {});
    } catch (networkError) {
      throw { code: 'NETWORK_ERROR', message: networkError.message, request_id: null };
    }
    const contentType = response.headers.get('content-type') || '';
    let body = null;
    try {
      body = contentType.includes('application/json') ? await response.json() : null;
    } catch (parseError) {
      throw { code: 'UNKNOWN_ERROR', message: `Failed to parse JSON response: ${parseError.message}`, request_id: null };
    }
    if (!response.ok) {
      throw (body && body.error) || { code: 'UNKNOWN_ERROR', message: `HTTP ${response.status}`, request_id: null };
    }
    return body;
  }

  function jsonBody(data) {
    return { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) };
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
  }

  return {
    escapeHtml,
    health: () => request('/health'),
    rovers: () => request('/rovers'),
    latest: (uid) => request(`/rovers/${uid}/latest`),
    readings: (uid, params) => request(`/rovers/${uid}/readings${buildQuery(params)}`),
    summary: (uid, params) => request(`/rovers/${uid}/summary${buildQuery(params)}`),
    events: (uid, params) => request(`/rovers/${uid}/events${buildQuery(params)}`),
    validationErrorsSummary: (windowStr) => request(`/validation-errors/summary${buildQuery({ window: windowStr })}`),
    sensorLimits: () => request('/config/sensor-limits'),
    putSensorLimit: (field, minMax) => request(`/config/sensor-limits/${field}`, jsonBody(minMax)),
    system: () => request('/system'),
    systemHistory: (params) => request(`/system/history${buildQuery(params)}`),
    exportUrl: (uid, params) => `${window.APP_CONFIG.API_BASE_URL}/rovers/${uid}/export${buildQuery(params)}`,
    media: (uid, params) => request(`/rovers/${uid}/media${buildQuery(params)}`),
    deleteMedia: (uid, id) => request(`/rovers/${uid}/media/${id}`, { method: 'DELETE' }),
  };
})();
