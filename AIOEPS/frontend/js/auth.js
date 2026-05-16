/**
 * auth.js — Shared API Client + Auth Utilities
 * AIOEPS - AI Based Online Examination Proctoring System
 */

const API_BASE = 'http://localhost:5000/api';

// ─── API Helper ──────────────────────────────────────────────────────────────
const API = {
  /** Return headers with JWT if available. */
  _headers() {
    const token = localStorage.getItem('aioeps_token');
    const h = { 'Content-Type': 'application/json' };
    if (token) h['Authorization'] = `Bearer ${token}`;
    return h;
  },

  async _fetch(url, opts = {}) {
    try {
      const res = await fetch(url, { headers: this._headers(), ...opts });
      if (res.status === 401) { Auth.logout(); return { success: false, message: 'Session expired. Please login again.' }; }
      return await res.json();
    } catch (err) {
      // Check if it's a connection refused error
      if (err.message && (err.message.includes('fetch') || err.message.includes('NetworkError') || err.message.includes('Failed'))) {
        console.error('❌ Backend not reachable at localhost:5000 — run python app.py');
        return { success: false, message: '❌ Backend server not running. Open terminal → cd backend → python app.py' };
      }
      return { success: false, message: 'Network error: ' + err.message };
    }
  },

  get:    (path)       => API._fetch(`${API_BASE}${path}`),
  delete: (path)       => API._fetch(`${API_BASE}${path}`, { method: 'DELETE' }),
  post:   (path, body) => API._fetch(`${API_BASE}${path}`, {
    method: 'POST', body: JSON.stringify(body)
  }),
  put:    (path, body) => API._fetch(`${API_BASE}${path}`, {
    method: 'PUT', body: JSON.stringify(body)
  }),

  // ── Auth ──────────────────────────────────────────────────────────────────
  login:    (email, password) => API.post('/auth/login',    { email, password }),
  register: (name, email, password, role) =>
            API.post('/auth/register', { name, email, password, role }),
  me:       ()                => API.get('/auth/me'),

  // ── Student ───────────────────────────────────────────────────────────────
  getExams:      ()           => API.get('/student/exams'),
  startExam:     (examId)     => API.post(`/student/exams/${examId}/start`, {}),
  getQuestions:  (examId)     => API.get(`/student/exams/${examId}/questions`),
  submitExam:    (sid, answers) => API.post(`/student/sessions/${sid}/submit`, { answers }),
  getResult:     (sid)        => API.get(`/student/results/${sid}`),
  myResults:     ()           => API.get('/student/my-results'),
  getDashboard:  ()           => API.get('/student/dashboard'),

  // ── Admin ─────────────────────────────────────────────────────────────────
  adminDashboard: ()          => API.get('/admin/dashboard'),
  getStudents:    ()          => API.get('/admin/students'),
  addStudent:     (data)      => API.post('/admin/students', data),
  deleteStudent:  (id)        => API.delete(`/admin/students/${id}`),
  getAdminExams:  ()          => API.get('/admin/exams'),
  createExam:     (data)      => API.post('/admin/exams', data),
  updateExamStatus: (id, st)  => API.put(`/admin/exams/${id}/status`, { status: st }),
  addQuestion:    (eid, q)    => API.post(`/admin/exams/${eid}/questions`, q),
  getWarnings:    ()          => API.get('/admin/warnings'),
  getResults:     ()          => API.get('/admin/results'),
  getStoredAnswers: ()        => API.get('/admin/stored-answers'),
  getAIAnalysis:  ()          => API.get('/admin/ai-analysis'),
  getSettings:    ()          => API.get('/admin/settings'),
  saveSettings:   (d)         => API.post('/admin/settings', d),

  // ── Proctor ───────────────────────────────────────────────────────────────
  logAlert:    (sessionId, warningType, severity, snapshot) =>
               API.post('/proctor/alert', { session_id: sessionId, warning_type: warningType, severity, snapshot }),
  logStress:   (sessionId, bpm)  => API.post('/proctor/stress',    { session_id: sessionId, bpm }),
  logKeystroke:(sessionId, data) => API.post('/proctor/keystroke', { session_id: sessionId, key_data: data }),
  getLive:     ()                => API.get('/proctor/live'),
  terminate:   (sessionId)       => API.post(`/proctor/terminate/${sessionId}`, {}),
  checkPlagiarism: (answer, subject, references) =>
                   API.post('/proctor/plagiarism', { answer, subject, references }),
  federatedUpdate: (behaviorData) =>
                   API.post('/proctor/federated/local-update', { behavior_data: behaviorData }),
  getFederatedModel: () => API.get('/proctor/federated/model'),
  realtimeStats: () => API.get('/proctor/realtime-stats'),
};

// ─── Auth Utilities ──────────────────────────────────────────────────────────
const Auth = {
  getToken() { return localStorage.getItem('aioeps_token'); },
  getUser()  { return JSON.parse(localStorage.getItem('aioeps_user') || 'null'); },
  isLoggedIn(){ return !!this.getToken(); },

  requireAuth(role = null) {
    if (!this.isLoggedIn()) { window.location.href = '/'; return null; }
    const user = this.getUser();
    if (role && user?.role !== role) { window.location.href = '/'; return null; }
    return user;
  },

  logout() {
    localStorage.removeItem('aioeps_token');
    localStorage.removeItem('aioeps_user');
    localStorage.removeItem('aioeps_session');
    window.location.href = '/';
  }
};

// ─── Toast Notifications ─────────────────────────────────────────────────────
function showToast(message, type = 'info', duration = 3500) {
  let container = document.getElementById('toast-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  const icons = { success:'✅', error:'❌', warning:'⚠️', info:'ℹ️' };
  toast.innerHTML = `<span>${icons[type]||'ℹ️'}</span><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0'; toast.style.transform = 'translateX(100%)';
    toast.style.transition = '0.3s'; setTimeout(() => toast.remove(), 300);
  }, duration);
}

// ─── Format Helpers ───────────────────────────────────────────────────────────
function formatTime(seconds) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  if (h > 0) return `${h}:${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
  return `${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;
}

function formatDate(dateStr) {
  if (!dateStr) return '-';
  return new Date(dateStr).toLocaleDateString('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric'
  });
}

function severityBadge(sev) {
  const map = { Critical:'danger', High:'danger', Medium:'warning', Low:'info' };
  return `<span class="badge badge-${map[sev]||'neutral'}">${sev}</span>`;
}

function resultBadge(res) {
  return res === 'Pass'
    ? '<span class="badge badge-success">✅ Pass</span>'
    : '<span class="badge badge-danger">❌ Fail</span>';
}

function statusBadge(st) {
  const map = { active:'info', submitted:'success', terminated:'danger', ongoing:'warning', upcoming:'neutral', completed:'success' };
  return `<span class="badge badge-${map[st]||'neutral'}">${st}</span>`;
}
