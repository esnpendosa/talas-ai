/**
 * TALAS AI — App JavaScript
 * Utility functions untuk UI TALAS AI
 *
 * PRINSIP KEAMANAN:
 * - Jangan kirim dokumen ke cloud tanpa konfirmasi
 * - Jangan cache dokumen regulasi di service worker
 * - Semua API call pakai token dari memory, bukan localStorage
 */

'use strict';

/**
 * Format angka dengan pemisah ribuan (Indonesia)
 * @param {number} n
 * @returns {string}
 */
function formatNumber(n) {
  if (n === null || n === undefined || n === '—') return '—';
  return new Intl.NumberFormat('id-ID').format(n);
}

/**
 * Format tanggal ke format Indonesia
 * @param {string} isoString
 * @returns {string}
 */
function formatDate(isoString) {
  if (!isoString) return '—';
  try {
    return new Intl.DateTimeFormat('id-ID', {
      year: 'numeric', month: 'long', day: 'numeric',
      hour: '2-digit', minute: '2-digit',
    }).format(new Date(isoString));
  } catch {
    return isoString;
  }
}

/**
 * Escape HTML untuk mencegah XSS
 * @param {string} str
 * @returns {string}
 */
function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.appendChild(document.createTextNode(String(str)));
  return div.innerHTML;
}

/**
 * Tampilkan notifikasi toast sederhana
 * @param {string} message
 * @param {'success'|'warning'|'error'} type
 */
function showToast(message, type = 'success') {
  const existing = document.getElementById('talas-toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.id = 'talas-toast';
  const colors = {
    success: '#059669',
    warning: '#d97706',
    error: '#dc2626',
  };
  Object.assign(toast.style, {
    position: 'fixed',
    bottom: '1.5rem',
    right: '1.5rem',
    background: colors[type] || colors.success,
    color: 'white',
    padding: '0.75rem 1.25rem',
    borderRadius: '8px',
    fontSize: '0.875rem',
    fontWeight: '600',
    zIndex: '9999',
    boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
    maxWidth: '320px',
    animation: 'fadeIn 0.2s ease',
  });
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => toast.remove(), 4000);
}

/**
 * Konfirmasi sebelum operasi destruktif
 * @param {string} message
 * @returns {boolean}
 */
function confirmAction(message) {
  return window.confirm(message);
}

/**
 * Deteksi apakah user di mobile
 * @returns {boolean}
 */
function isMobile() {
  return window.innerWidth <= 768;
}

// Export untuk digunakan di inline scripts
window.TalasUI = {
  formatNumber,
  formatDate,
  escapeHtml,
  showToast,
  confirmAction,
  isMobile,
};
