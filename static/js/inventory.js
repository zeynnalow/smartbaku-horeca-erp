/**
 * SmartBaku HoReCa ERP - Inventory Logic
 */

let allIngredients = [];
let allSuppliers = [];

async function loadIngredients() {
  const tbody = document.getElementById("ingredients-tbody");
  tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; padding: 24px; color: var(--slate-500);">Məlumatlar yüklənir...</td></tr>`;

  try {
    const [ingData, supData] = await Promise.all([
      apiFetch("/api/ingredients"),
      apiFetch("/api/suppliers"),
    ]);

    allIngredients = ingData.items || [];
    allSuppliers = supData.items || [];

    // Populate supplier dropdown in form
    const supSelect = document.getElementById("ing-supplier");
    if (supSelect) {
      supSelect.innerHTML = `<option value="">— Təchizatçı seçin —</option>` +
        allSuppliers.map(s => `<option value="${s.id}">${s.name}</option>`).join("");
    }

    renderIngredientsTable(allIngredients);
  } catch (err) {
    showToast("İnventar məlumatları yüklənərkən xəta: " + err.message, "error");
    tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; color: var(--danger); padding: 24px;">Xəta: ${err.message}</td></tr>`;
  }
}

function renderIngredientsTable(items) {
  const tbody = document.getElementById("ingredients-tbody");
  if (!items || items.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" style="text-align: center; padding: 24px; color: var(--slate-500);">Heç bir inqrediyent tapılmadı.</td></tr>`;
    return;
  }

  tbody.innerHTML = items.map(item => {
    const qty = Number(item.quantity);
    const min = Number(item.min_stock);

    let rowClass = "stock-green";
    let badge = `<span class="badge badge-green"><span class="badge-dot"></span>Yetərli</span>`;

    if (qty <= min) {
      rowClass = "stock-red";
      badge = `<span class="badge badge-red"><span class="badge-dot"></span>Kritik az</span>`;
    } else if (qty <= 2 * min) {
      rowClass = "stock-yellow";
      badge = `<span class="badge badge-yellow"><span class="badge-dot"></span>Diqqət</span>`;
    }

    return `
      <tr class="${rowClass}">
        <td><span style="color: var(--slate-400); font-family: var(--font-mono); font-size: 11px;">#${item.id}</span></td>
        <td><strong>${item.name}</strong></td>
        <td><span class="badge badge-gray">${item.unit}</span></td>
        <td class="stock-cell">${qty.toFixed(2)}</td>
        <td class="tabular-nums">${min.toFixed(2)}</td>
        <td class="tabular-nums">${Number(item.unit_price).toFixed(2)} ₼</td>
        <td>${item.supplier_name || '<span style="color:#94a3b8;">—</span>'}</td>
        <td>${badge}</td>
        <td style="text-align: right; white-space: nowrap;">
          <button class="btn btn-sm btn-icon" title="Stok dəyiş" onclick="openAdjustModal(${item.id})">
            <i data-lucide="scale"></i>
          </button>
          <button class="btn btn-sm btn-icon" title="Redaktə et" onclick="openEditModal(${item.id})">
            <i data-lucide="pencil"></i>
          </button>
          <button class="btn btn-sm btn-icon" style="color: var(--danger);" title="Sil" onclick="deleteIngredient(${item.id})">
            <i data-lucide="trash-2"></i>
          </button>
        </td>
      </tr>
    `;
  }).join("");

  if (window.lucide) {
    lucide.createIcons();
  }
}

function openAddModal() {
  document.getElementById("modal-title").innerText = "Yeni İnqrediyent Əlavə Et";
  document.getElementById("ing-id").value = "";
  document.getElementById("ingredient-form").reset();
  openModal("ingredient-modal");
}

function openEditModal(id) {
  const item = allIngredients.find(i => i.id === id);
  if (!item) return;

  document.getElementById("modal-title").innerText = "İnqrediyenti Redaktə Et";
  document.getElementById("ing-id").value = item.id;
  document.getElementById("ing-name").value = item.name;
  document.getElementById("ing-unit").value = item.unit;
  document.getElementById("ing-quantity").value = item.quantity;
  document.getElementById("ing-min-stock").value = item.min_stock;
  document.getElementById("ing-price").value = item.unit_price;
  document.getElementById("ing-supplier").value = item.supplier_id || "";

  openModal("ingredient-modal");
}

async function handleIngredientSubmit(e) {
  e.preventDefault();
  const id = document.getElementById("ing-id").value;
  const isEdit = Boolean(id);

  const payload = {
    name: document.getElementById("ing-name").value.trim(),
    unit: document.getElementById("ing-unit").value,
    quantity: parseFloat(document.getElementById("ing-quantity").value) || 0,
    min_stock: parseFloat(document.getElementById("ing-min-stock").value) || 0,
    unit_price: parseFloat(document.getElementById("ing-price").value) || 0,
    supplier_id: document.getElementById("ing-supplier").value ? parseInt(document.getElementById("ing-supplier").value) : null,
  };

  try {
    const url = isEdit ? `/api/ingredients/${id}` : "/api/ingredients";
    const method = isEdit ? "PUT" : "POST";

    await apiFetch(url, {
      method: method,
      body: JSON.stringify(payload)
    });

    closeModal("ingredient-modal");
    showToast(isEdit ? "İnqrediyent uğurla yeniləndi!" : "Yeni inqrediyent əlavə edildi!", "success");
    loadIngredients();
  } catch (err) {
    showToast(`Xəta: ${err.message}`, "error");
  }
}

async function deleteIngredient(id) {
  const item = allIngredients.find(i => i.id === id);
  const name = item ? `"${item.name}"` : "bu inqrediyenti";
  if (!confirm(`${name} silinsin? Əgər reseptlərdə və ya qaimələrdə istifadə olunubsa, silinməyəcək.`)) {
    return;
  }

  try {
    await apiFetch(`/api/ingredients/${id}`, { method: "DELETE" });
    showToast("İnqrediyent silindi!", "success");
    loadIngredients();
  } catch (err) {
    showToast(`Silinmə xətası: ${err.message}`, "error");
  }
}

function openAdjustModal(id) {
  const item = allIngredients.find(i => i.id === id);
  if (!item) return;

  document.getElementById("adjust-ing-id").value = item.id;
  document.getElementById("adjust-ing-name").innerText = `${item.name} (Cari: ${item.quantity} ${item.unit})`;
  document.getElementById("adjust-delta").value = "";
  openModal("adjust-modal");
}

async function handleStockAdjust(e) {
  e.preventDefault();
  const id = document.getElementById("adjust-ing-id").value;
  const delta = parseFloat(document.getElementById("adjust-delta").value);

  if (isNaN(delta) || delta === 0) {
    showToast("Zəhmət olmasa sıfırdan fərqli miqdar daxil edin", "error");
    return;
  }

  try {
    await apiFetch(`/api/ingredients/${id}/adjust-stock`, {
      method: "POST",
      body: JSON.stringify({ delta: delta })
    });

    closeModal("adjust-modal");
    showToast("Stok miqdarı yeniləndi!", "success");
    loadIngredients();
  } catch (err) {
    showToast(`Stok dəyişmə xətası: ${err.message}`, "error");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadIngredients();
});
