async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(path, {
      ...options,
      headers: options.body
        ? { "Content-Type": "application/json", ...options.headers }
        : options.headers,
    });
  } catch {
    throw new Error("Cannot reach the Meridian Backend. Please try again.");
  }

  if (response.status === 204) return null;
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = Array.isArray(body.detail)
      ? body.detail.map((item) => item.msg).join("; ")
      : body.detail;
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return body;
}

function json(method, payload) {
  return { method, body: JSON.stringify(payload) };
}

export const faqApi = {
  listFaqs: () => request("/api/admin/faqs"),
  createFaq: (payload) => request("/api/admin/faqs", json("POST", payload)),
  updateFaq: (id, payload) => request(`/api/admin/faqs/${id}`, json("PUT", payload)),
  deleteFaq: (id) => request(`/api/admin/faqs/${id}`, { method: "DELETE" }),
  listUnanswered: () => request("/api/admin/unanswered"),
  convertUnanswered: (id, payload) =>
    request(`/api/admin/unanswered/${id}/convert`, json("POST", payload)),
  dismissUnanswered: (id) =>
    request(`/api/admin/unanswered/${id}/dismiss`, { method: "POST" }),
  listVoices: () => request("/api/admin/voices"),
  activateVoice: (id) =>
    request(`/api/admin/voices/${id}/activate`, { method: "POST" }),
  voicePreviewUrl: (id) => `/api/admin/voices/${id}/preview`,
};
