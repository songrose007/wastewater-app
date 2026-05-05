const BASE_URL = '/api/v1';

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${url}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `请求失败: ${res.status}`);
  }
  return res.json();
}

export const api = {
  // Generic request for custom endpoints
  request,

  // Projects
  createProject: (data: { name: string; description?: string; wastewater_type: string }) =>
    request('/projects', { method: 'POST', body: JSON.stringify(data) }),

  listProjects: () => request('/projects'),

  getProject: (id: string) => request(`/projects/${id}`),

  deleteProject: (id: string) => request(`/projects/${id}`, { method: 'DELETE' }),

  // Water Quality
  saveWaterQuality: (projectId: string, data: Record<string, unknown>) =>
    request(`/projects/${projectId}/water-quality`, { method: 'POST', body: JSON.stringify(data) }),

  getWaterQuality: (projectId: string) => request(`/projects/${projectId}/water-quality`),

  // Process Selection
  selectProcess: (projectId: string) =>
    request(`/projects/${projectId}/select-process`, { method: 'POST' }),

  confirmRoute: (projectId: string, routeId: string) =>
    request(`/projects/${projectId}/confirm-route`, {
      method: 'POST',
      body: JSON.stringify({ route_id: routeId }),
    }),

  getSelectedRoute: (projectId: string) => request(`/projects/${projectId}/selected-route`),

  // Calculation
  runCalculation: (projectId: string, parameterOverrides?: Record<string, Record<string, number>>) =>
    request(`/projects/${projectId}/calculate`, {
      method: 'POST',
      body: JSON.stringify({ parameter_overrides: parameterOverrides || {} }),
    }),

  getCalculations: (projectId: string) => request(`/projects/${projectId}/calculations`),

  recalculateUnit: (projectId: string, unitCode: string, params: Record<string, unknown>) =>
    request(`/projects/${projectId}/calculate/${unitCode}`, {
      method: 'POST',
      body: JSON.stringify({ unit_code: unitCode, parameters: params }),
    }),

  getDesignParams: (projectId: string) =>
    request(`/projects/${projectId}/design-params`),

  // Equipment
  selectEquipment: (projectId: string) =>
    request(`/projects/${projectId}/select-equipment`, { method: 'POST' }),

  getEquipment: (projectId: string) =>
    request(`/projects/${projectId}/equipment`),

  // Cost
  estimateCost: (projectId: string) =>
    request(`/projects/${projectId}/estimate-cost`, { method: 'POST' }),

  getCost: (projectId: string) =>
    request(`/projects/${projectId}/cost`),

  // Presets
  listPresets: () => request('/presets'),

  getPreset: (id: number) => request(`/presets/${id}`),

  createPreset: (data: { name: string; description?: string; wastewater_type?: string; is_default?: boolean; parameters: { unit_code: string; param_name: string; param_value: number }[] }) =>
    request('/presets', { method: 'POST', body: JSON.stringify(data) }),

  updatePreset: (id: number, data: Record<string, unknown>) =>
    request(`/presets/${id}`, { method: 'PUT', body: JSON.stringify(data) }),

  deletePreset: (id: number) =>
    request(`/presets/${id}`, { method: 'DELETE' }),

  // Report
  generateReport: (projectId: string) =>
    request(`/projects/${projectId}/report`, { method: 'POST' }),
};
