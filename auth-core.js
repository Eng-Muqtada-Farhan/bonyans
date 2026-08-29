/**
 * بُنيان — Auth Core v1.1 (Logic Only)
 * Single source of truth for authentication state and JWT validation.
 * No DOM access. No UI. No redirects.
 * Communicates with UI layer via CustomEvents only.
 * Load order: auth-core.js → auth-ui.js → bunyan-nav.js
 */
(function () {
  'use strict';

  var S = {
    userToken:    'project_user_token',
    userId:       'project_user_id',
    userName:     'project_user_name',
    companyToken: 'COMPANY_TOKEN',
    companyId:    'company_id',
    adminToken:   'admin_token',
  };

  /* ── JWT decode + expiry check ─────────────────────────── */
  function validateJWT(token) {
    if (!token || typeof token !== 'string') return null;
    try {
      var b64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
      var payload = JSON.parse(atob(b64));
      if (!payload.exp || Date.now() / 1000 >= payload.exp) return null;
      return payload;
    } catch (e) {
      return null;
    }
  }

  /* ── Single auth state resolver ─────────────────────────── */
  function getAuthState() {
    var adminRaw   = localStorage.getItem(S.adminToken) || localStorage.getItem('token');
    var companyRaw = localStorage.getItem(S.companyToken);
    var userRaw    = localStorage.getItem(S.userToken);
    var userName   = localStorage.getItem(S.userName) || '';
    var companyId  = localStorage.getItem(S.companyId) || null;
    var userId     = parseInt(localStorage.getItem(S.userId) || '0') || null;

    // Admin
    if (adminRaw) {
      var ap = validateJWT(adminRaw);
      if (ap && ap.sub === 'admin') {
        return { role: 'admin', token: adminRaw, name: 'أدمن', userId: null, companyId: null };
      }
    }

    // Legacy company token (COMPANY_TOKEN)
    if (companyRaw) {
      var cp = validateJWT(companyRaw);
      if (cp && (cp.type === 'company' || cp.type === 'user')) {
        return { role: 'company', token: companyRaw, name: '', userId: null, companyId: companyId };
      }
      // Expired — clean up silently
      if (!cp) localStorage.removeItem(S.companyToken);
    }

    // User token + saved company_id = company member
    if (userRaw && companyId) {
      var up = validateJWT(userRaw);
      if (up) {
        return { role: 'company', token: userRaw, name: userName, userId: userId, companyId: companyId };
      }
      // Expired — clean all three
      localStorage.removeItem(S.userToken);
      localStorage.removeItem(S.userId);
      localStorage.removeItem(S.companyId);
    }

    // Regular user
    if (userRaw) {
      var pp = validateJWT(userRaw);
      if (pp && pp.type === 'user') {
        return { role: 'user', token: userRaw, name: userName, userId: userId, companyId: null };
      }
      if (!pp) {
        localStorage.removeItem(S.userToken);
        localStorage.removeItem(S.userId);
      }
    }

    return { role: 'guest', token: null, name: '', userId: null, companyId: null };
  }

  /* ── isAuthenticated: any non-guest role ────────────────── */
  function isAuthenticated() {
    return getAuthState().role !== 'guest';
  }

  /* ── openLoginModal: fires event only, no DOM ───────────── */
  function openLoginModal() {
    window.dispatchEvent(new Event('auth:login:open'));
  }

  /* ── logout: token cleanup then fires event, no redirect ── */
  function logout() {
    Object.keys(S).forEach(function (k) { localStorage.removeItem(S[k]); });
    localStorage.removeItem('token');
    localStorage.removeItem('project_company_id');
    window.dispatchEvent(new Event('auth:logout'));
  }

  /* ── Public API ─────────────────────────────────────────── */
  window.authCore = {
    getAuthState:    getAuthState,
    isAuthenticated: isAuthenticated,
    openLoginModal:  openLoginModal,
    logout:          logout,
    validateJWT:     validateJWT,
  };

})();
