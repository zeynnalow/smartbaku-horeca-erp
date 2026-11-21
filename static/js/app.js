/**
 * SmartBaku HoReCa ERP - Global Client Utilities
 */

// Reusable Fetch Wrapper
async function apiFetch(url, options = {}) {
  const config = {
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  };

  try {
    const response = await fetch(url, config);

    if (response.status === 204) {
      return null;
    }

    const data = await response.json().catch(() => null);

    if (!response.ok) {
      const errorMsg = data?.error || `Xəta baş verdi (Status: ${response.status})`;
      const err = new Error(errorMsg);
      err.status = response.status;
      err.code = data?.code || "UNKNOWN_ERROR";
      err.details = data?.details || null;
      throw err;
    }

    return data;
  } catch (err) {
    console.error("API Xətası:", err);
    throw err;
  }
}

// Toast Notifications
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span>${message}</span>
    <button style="background:none;border:none;color:#fff;cursor:pointer;font-weight:bold;">&times;</button>
  `;

  const closeBtn = toast.querySelector("button");
  closeBtn.onclick = () => toast.remove();

  container.appendChild(toast);

  setTimeout(() => {
    if (toast.parentElement) {
      toast.style.opacity = "0";
      toast.style.transform = "translateY(16px)";
      toast.style.transition = "all 0.2s ease";
      setTimeout(() => toast.remove(), 200);
    }
  }, 4000);
}

// Currency Rates in Navbar
async function loadNavbarCurrency() {
  const el = document.getElementById("nav-currency-rates");
  if (!el) return;

  try {
    const data = await apiFetch("/api/currency/rates");
    const rates = data.rates || {};
    const usd = rates.USD ? Number(rates.USD).toFixed(2) : "1.70";
    const eur = rates.EUR ? Number(rates.EUR).toFixed(2) : "1.85";
    el.innerHTML = `<span class="rate-dot"></span> $ 1 = ${usd} ₼ &bull; € 1 = ${eur} ₼`;
    el.title = `Mənbə: ${data.source} (${data.fetched_at || 'bu gün'}). Yeniləmək üçün klikləyin.`;
  } catch (e) {
    el.innerHTML = `<span class="rate-dot"></span> Məzənnə əlçatan deyil`;
  }
}

async function syncCurrencyRates() {
  try {
    showToast("Məzənnələr cbar.az ilə sinxronlaşdırılır...", "info");
    const data = await apiFetch("/api/currency/sync", { method: "POST" });
    showToast(`Məzənnələr yeniləndi (${data.source})`, "success");
    loadNavbarCurrency();
    // Refresh dashboard if present
    if (typeof loadDashboardCurrencyTable === "function") {
      loadDashboardCurrencyTable();
    }
  } catch (err) {
    showToast(`Sinxronlaşdırma xətası: ${err.message}`, "error");
  }
}

// Modal helper functions
function openModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) {
    modal.classList.add("open");
    if (window.lucide) {
      lucide.createIcons();
    }
  }
}

function closeModal(modalId) {
  const modal = document.getElementById(modalId);
  if (modal) modal.classList.remove("open");
}

// Format numbers
function formatAZN(val) {
  return Number(val || 0).toFixed(2) + " ₼";
}

document.addEventListener("DOMContentLoaded", () => {
  loadNavbarCurrency();
  const currencyBadge = document.getElementById("nav-currency-rates");
  if (currencyBadge) {
    currencyBadge.addEventListener("click", syncCurrencyRates);
  }
});
