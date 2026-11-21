/**
 * SmartBaku HoReCa ERP - Suppliers Logic
 */

let allSuppliers = [];

async function loadSuppliers() {
  const tbody = document.getElementById("suppliers-tbody");
  tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 24px; color: var(--slate-500);">Yüklənir...</td></tr>`;

  try {
    const data = await apiFetch("/api/suppliers");
    allSuppliers = data.items || [];
    renderSuppliersTable(allSuppliers);
  } catch (err) {
    showToast("Təchizatçılar yüklənərkən xəta: " + err.message, "error");
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--danger); padding: 24px;">Xəta: ${err.message}</td></tr>`;
  }
}

function renderSuppliersTable(suppliers) {
  const tbody = document.getElementById("suppliers-tbody");
  if (!suppliers || suppliers.length === 0) {
    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 24px; color: var(--slate-500);">Qeydiyyatda heç bir təchizatçı yoxdur.</td></tr>`;
    return;
  }

  tbody.innerHTML = suppliers.map(s => `
    <tr>
      <td><span style="color: var(--slate-400); font-family: var(--font-mono); font-size: 11px;">#${s.id}</span></td>
      <td><strong>${s.name}</strong></td>
      <td><code>${s.voen}</code></td>
      <td class="tabular-nums">${s.phone}</td>
      <td>${s.email ? `<a href="mailto:${s.email}" style="color:var(--primary);text-decoration:none;">${s.email}</a>` : '<span style="color:#94a3b8;">—</span>'}</td>
      <td>${s.address || '<span style="color:#94a3b8;">—</span>'}</td>
      <td style="text-align: right; white-space: nowrap;">
        <button class="btn btn-sm btn-icon" title="Redaktə et" onclick="openSupplierEditModal(${s.id})">
          <i data-lucide="pencil"></i>
        </button>
        <button class="btn btn-sm btn-icon" style="color: var(--danger);" title="Sil" onclick="deleteSupplier(${s.id})">
          <i data-lucide="trash-2"></i>
        </button>
      </td>
    </tr>
  `).join("");

  if (window.lucide) {
    lucide.createIcons();
  }
}

function openSupplierAddModal() {
  document.getElementById("supplier-modal-title").innerText = "Yeni Təchizatçı Əlavə Et";
  document.getElementById("sup-id").value = "";
  document.getElementById("supplier-form").reset();
  openModal("supplier-modal");
}

function openSupplierEditModal(id) {
  const sup = allSuppliers.find(s => s.id === id);
  if (!sup) return;

  document.getElementById("supplier-modal-title").innerText = "Təchizatçını Redaktə Et";
  document.getElementById("sup-id").value = sup.id;
  document.getElementById("sup-name").value = sup.name;
  document.getElementById("sup-voen").value = sup.voen;
  document.getElementById("sup-phone").value = sup.phone;
  document.getElementById("sup-email").value = sup.email || "";
  document.getElementById("sup-address").value = sup.address || "";

  openModal("supplier-modal");
}

async function handleSupplierSubmit(e) {
  e.preventDefault();
  const id = document.getElementById("sup-id").value;
  const isEdit = Boolean(id);

  const voen = document.getElementById("sup-voen").value.trim();

  // Strict 10-digit VÖEN validation
  if (!/^\d{10}$/.test(voen)) {
    showToast("VÖEN dəqiq 10 rəqəmdən ibarət olmalıdır (Məs: 1400598371)!", "error");
    document.getElementById("sup-voen").focus();
    return;
  }

  const payload = {
    name: document.getElementById("sup-name").value.trim(),
    voen: voen,
    phone: document.getElementById("sup-phone").value.trim(),
    email: document.getElementById("sup-email").value.trim() || null,
    address: document.getElementById("sup-address").value.trim() || null,
  };

  try {
    const url = isEdit ? `/api/suppliers/${id}` : "/api/suppliers";
    const method = isEdit ? "PUT" : "POST";

    await apiFetch(url, {
      method: method,
      body: JSON.stringify(payload)
    });

    closeModal("supplier-modal");
    showToast(isEdit ? "Təchizatçı yeniləndi!" : "Yeni təchizatçı əlavə edildi!", "success");
    loadSuppliers();
  } catch (err) {
    showToast(`Xəta: ${err.message}`, "error");
  }
}

async function deleteSupplier(id) {
  const sup = allSuppliers.find(s => s.id === id);
  const name = sup ? `"${sup.name}"` : "bu təchizatçını";

  if (!confirm(`${name} silinsin? Əgər inqrediyentlərdə və ya qaimələrdə bağlıdırsa, silinməyəcək.`)) {
    return;
  }

  try {
    await apiFetch(`/api/suppliers/${id}`, { method: "DELETE" });
    showToast("Təchizatçı silindi!", "success");
    loadSuppliers();
  } catch (err) {
    showToast(`Silinmə xətası: ${err.message}`, "error");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadSuppliers();
});
