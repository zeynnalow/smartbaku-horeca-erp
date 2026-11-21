/**
 * SmartBaku HoReCa ERP - Waybills Logic
 */

let allWaybills = [];
let allSuppliers = [];
let allIngredients = [];
let currentRates = {};
let lineItems = [];

async function loadWaybills() {
  const tbody = document.getElementById("waybills-tbody");
  tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 24px; color: var(--slate-500);">Yüklənir...</td></tr>`;

  try {
    const [wbData, supData, ingData, ratesData] = await Promise.all([
      apiFetch("/api/waybills"),
      apiFetch("/api/suppliers"),
      apiFetch("/api/ingredients"),
      apiFetch("/api/currency/rates"),
    ]);

    allWaybills = wbData.items || [];
    allSuppliers = supData.items || [];
    allIngredients = ingData.items || [];
    currentRates = ratesData.rates || {};

    // Populate supplier select in modal
    const supSelect = document.getElementById("wb-supplier");
    if (supSelect) {
      supSelect.innerHTML = `<option value="">— Təchizatçı seçin —</option>` +
        allSuppliers.map(s => `<option value="${s.id}">${s.name} (VÖEN: ${s.voen})</option>`).join("");
    }

    renderWaybillsTable(allWaybills);
  } catch (err) {
    showToast("Qaimələri yükləyərkən xəta: " + err.message, "error");
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--danger); padding: 24px;">Xəta: ${err.message}</td></tr>`;
  }
}

function renderWaybillsTable(waybills) {
  const tbody = document.getElementById("waybills-tbody");
  if (!waybills || waybills.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding: 24px; color: var(--slate-500);">Hələ heç bir qaimə tərtib olunmayıb.</td></tr>`;
    return;
  }

  tbody.innerHTML = waybills.map(w => {
    const dateStr = w.created_at ? w.created_at.slice(0, 16).replace("T", " ") : "—";
    return `
      <tr>
        <td><strong><code>${w.waybill_number}</code></strong></td>
        <td><strong>${w.supplier_name}</strong></td>
        <td class="tabular-nums">${Number(w.subtotal).toFixed(2)} ${w.currency}</td>
        <td class="tabular-nums">${Number(w.edv_amount).toFixed(2)} ${w.currency}</td>
        <td class="tabular-nums"><strong style="color: var(--primary);">${Number(w.total).toFixed(2)} ${w.currency}</strong></td>
        <td><span class="badge badge-gray">${w.currency}</span></td>
        <td style="color: var(--slate-500); font-size: 11.5px;" class="tabular-nums">${dateStr}</td>
        <td style="text-align: right;">
          <button class="btn btn-sm btn-outline" title="Qaiməni Çap Et (PDF)" onclick="printWaybill(${w.id})">
            <i data-lucide="printer"></i>
            <span>Çap</span>
          </button>
        </td>
      </tr>
    `;
  }).join("");

  if (window.lucide) {
    lucide.createIcons();
  }
}

function printWaybill(id) {
  window.open(`/waybills/${id}/print`, "_blank");
}

function openNewWaybillModal() {
  document.getElementById("waybill-form").reset();
  document.getElementById("wb-currency").value = "AZN";
  onCurrencyChange();

  lineItems = [];
  addWaybillLineItem();
  recalculateWaybillTotals();

  openModal("waybill-modal");
  if (window.lucide) lucide.createIcons();
}

function onCurrencyChange() {
  const currency = document.getElementById("wb-currency").value;
  const rateInput = document.getElementById("wb-exchange-rate");

  if (currency === "AZN") {
    rateInput.value = "1.000000";
    rateInput.readOnly = true;
    rateInput.style.backgroundColor = "#F1F5F9";
    rateInput.style.cursor = "not-allowed";
  } else {
    rateInput.readOnly = false;
    rateInput.style.backgroundColor = "#FFFFFF";
    rateInput.style.cursor = "text";
    const rate = currentRates[currency] || 1.0;
    rateInput.value = Number(rate).toFixed(6);
  }
  recalculateWaybillTotals();
}

function addWaybillLineItem() {
  lineItems.push({
    ingredient_id: null,
    quantity: 1,
    unit_price: 0,
    line_total: 0
  });
  renderWaybillLineItems();
}

function removeWaybillLineItem(index) {
  if (lineItems.length <= 1) {
    showToast("Qaimədə ən azı 1 sətir olmalıdır!", "error");
    return;
  }
  lineItems.splice(index, 1);
  renderWaybillLineItems();
  recalculateWaybillTotals();
}

function renderWaybillLineItems() {
  const tbody = document.getElementById("wb-items-tbody");
  const currency = document.getElementById("wb-currency").value || "AZN";

  tbody.innerHTML = lineItems.map((item, idx) => {
    const ingOptions = allIngredients.map(i => `
      <option value="${i.id}" ${item.ingredient_id === i.id ? 'selected' : ''}>
        ${i.name} (${i.unit}) - Son qiymət: ${Number(i.unit_price).toFixed(2)} ₼
      </option>
    `).join("");

    return `
      <tr>
        <td>
          <select class="form-control" onchange="onLineItemIngredientChange(${idx}, this.value)" required>
            <option value="">— İnqrediyent seçin —</option>
            ${ingOptions}
          </select>
        </td>
        <td>
          <input type="number" class="form-control tabular-nums" step="0.01" min="0.01" value="${item.quantity}"
            oninput="onLineItemQtyChange(${idx}, this.value)" required placeholder="Miqdar">
        </td>
        <td>
          <input type="number" class="form-control tabular-nums" step="0.01" min="0" value="${item.unit_price}"
            oninput="onLineItemPriceChange(${idx}, this.value)" required placeholder="Qiymət">
        </td>
        <td style="text-align: right; font-weight: 600;" class="tabular-nums">
          ${item.line_total.toFixed(2)} ${currency}
        </td>
        <td style="text-align: center;">
          <button type="button" class="btn-icon" style="color: var(--danger);" onclick="removeWaybillLineItem(${idx})" title="Sətiri sil">
            <i data-lucide="x"></i>
          </button>
        </td>
      </tr>
    `;
  }).join("");

  if (window.lucide) {
    lucide.createIcons();
  }
}

function onLineItemIngredientChange(idx, val) {
  const ingId = parseInt(val);
  lineItems[idx].ingredient_id = ingId || null;

  if (ingId) {
    const ing = allIngredients.find(i => i.id === ingId);
    if (ing) {
      lineItems[idx].unit_price = parseFloat(ing.unit_price || 0);
    }
  }

  updateLineTotal(idx);
  renderWaybillLineItems();
  recalculateWaybillTotals();
}

function onLineItemQtyChange(idx, val) {
  lineItems[idx].quantity = parseFloat(val) || 0;
  updateLineTotal(idx);
  recalculateWaybillTotals();
}

function onLineItemPriceChange(idx, val) {
  lineItems[idx].unit_price = parseFloat(val) || 0;
  updateLineTotal(idx);
  recalculateWaybillTotals();
}

function updateLineTotal(idx) {
  const item = lineItems[idx];
  item.line_total = (item.quantity || 0) * (item.unit_price || 0);
  const tbody = document.getElementById("wb-items-tbody");
  const currency = document.getElementById("wb-currency").value || "AZN";
  if (tbody.children[idx]) {
    tbody.children[idx].children[3].innerText = `${item.line_total.toFixed(2)} ${currency}`;
  }
}

function recalculateWaybillTotals() {
  const currency = document.getElementById("wb-currency").value || "AZN";
  const subtotal = lineItems.reduce((acc, it) => acc + (it.line_total || 0), 0);
  const edvAmount = Math.round((subtotal * 18.00 / 100) * 100) / 100;
  const total = subtotal + edvAmount;

  document.getElementById("display-subtotal").innerText = `${subtotal.toFixed(2)} ${currency}`;
  document.getElementById("display-edv").innerText = `${edvAmount.toFixed(2)} ${currency}`;
  document.getElementById("display-total").innerText = `${total.toFixed(2)} ${currency}`;
}

async function handleWaybillSubmit(e) {
  e.preventDefault();

  const supplierId = parseInt(document.getElementById("wb-supplier").value);
  if (!supplierId) {
    showToast("Zəhmət olmasa təchizatçı seçin", "error");
    return;
  }

  // Validate items
  for (let i = 0; i < lineItems.length; i++) {
    const item = lineItems[i];
    if (!item.ingredient_id) {
      showToast(`Sətir ${i + 1}: İnqrediyent seçilməyib!`, "error");
      return;
    }
    if (item.quantity <= 0) {
      showToast(`Sətir ${i + 1}: Miqdar 0-dan böyük olmalıdır!`, "error");
      return;
    }
  }

  const payload = {
    supplier_id: supplierId,
    currency: document.getElementById("wb-currency").value,
    exchange_rate: parseFloat(document.getElementById("wb-exchange-rate").value) || 1.0,
    notes: document.getElementById("wb-notes").value.trim() || "",
    items: lineItems.map(it => ({
      ingredient_id: it.ingredient_id,
      quantity: it.quantity,
      unit_price: it.unit_price
    }))
  };

  try {
    const created = await apiFetch("/api/waybills", {
      method: "POST",
      body: JSON.stringify(payload)
    });

    closeModal("waybill-modal");
    showToast(`Qaimə ${created.waybill_number} tərtib edildi və stoklar artırıldı!`, "success");
    await loadWaybills();
  } catch (err) {
    showToast(`Qaimə tərtibatı xətası: ${err.message}`, "error");
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadWaybills();
});
