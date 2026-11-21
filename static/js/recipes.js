/**
 * SmartBaku HoReCa ERP - Recipes Logic
 */

let allRecipes = [];
let allIngredients = [];
let currentRecipeItems = [];
let selectedRecipeId = null;

async function loadRecipes() {
  try {
    const [recData, ingData] = await Promise.all([
      apiFetch("/api/recipes"),
      apiFetch("/api/ingredients"),
    ]);

    allRecipes = recData.items || [];
    allIngredients = ingData.items || [];

    // Populate ingredient picker dropdown
    const picker = document.getElementById("picker-ingredient");
    if (picker) {
      picker.innerHTML = `<option value="">— İnqrediyent seçin —</option>` +
        allIngredients.map(i => `<option value="${i.id}">${i.name} (${i.unit}) - ${Number(i.unit_price).toFixed(2)} ₼</option>`).join("");
    }

    renderRecipeCards(allRecipes);

    // Auto-select first recipe if available and none selected
    if (allRecipes.length > 0 && !selectedRecipeId) {
      selectRecipe(allRecipes[0].id);
    } else if (allRecipes.length === 0) {
      initNewRecipe();
    }
  } catch (err) {
    showToast("Reseptləri yükləyərkən xəta: " + err.message, "error");
  }
}

function renderRecipeCards(recipes) {
  const container = document.getElementById("recipe-cards-container");
  if (!recipes || recipes.length === 0) {
    container.innerHTML = `<div style="padding: 24px; text-align: center; color: var(--slate-500);">Resept tapılmadı.</div>`;
    return;
  }

  container.innerHTML = recipes.map(r => {
    const isSelected = r.id === selectedRecipeId;
    const cost = Number(r.cost_per_serving || 0).toFixed(2);
    const margin = Number(r.margin_percent || 0).toFixed(1);
    const price = Number(r.selling_price).toFixed(2);

    return `
      <div class="recipe-card-item ${isSelected ? 'active' : ''}" onclick="selectRecipe(${r.id})">
        <div style="display: flex; justify-content: space-between; align-items: flex-start;">
          <div class="recipe-card-title">${r.name}</div>
          <span class="badge badge-gray">${r.category}</span>
        </div>
        <div style="margin: 6px 0; font-weight: 700; font-size: 14px; font-family: var(--font-mono); color: var(--slate-900);">
          ${price} ₼
        </div>
        <div class="recipe-card-meta">
          <span>Maya: <strong>${cost} ₼</strong></span>
          <span style="color: ${margin >= 40 ? '#15803d' : '#b45309'};">Marja: <strong>${margin}%</strong></span>
        </div>
      </div>
    `;
  }).join("");

  if (window.lucide) {
    lucide.createIcons();
  }
}

function filterRecipes() {
  const query = document.getElementById("recipe-search").value.toLowerCase().trim();
  const filtered = allRecipes.filter(r =>
    r.name.toLowerCase().includes(query) ||
    r.category.toLowerCase().includes(query)
  );
  renderRecipeCards(filtered);
}

function initNewRecipe() {
  selectedRecipeId = null;
  document.getElementById("editor-title").innerHTML = `<i data-lucide="plus-circle"></i> Yeni Resept Tərtibatı`;
  document.getElementById("rec-id").value = "";
  document.getElementById("recipe-form").reset();
  document.getElementById("btn-delete-recipe").style.display = "none";
  document.getElementById("btn-check-avail").style.display = "none";
  document.getElementById("btn-cook").style.display = "none";

  currentRecipeItems = [];
  renderCurrentRecipeItems();
  recalculateMetrics();

  renderRecipeCards(allRecipes);
  if (window.lucide) lucide.createIcons();
}

function selectRecipe(id) {
  const recipe = allRecipes.find(r => r.id === id);
  if (!recipe) return;

  selectedRecipeId = id;
  document.getElementById("editor-title").innerHTML = `<i data-lucide="book-open"></i> Resept: ${recipe.name}`;
  document.getElementById("rec-id").value = recipe.id;
  document.getElementById("rec-name").value = recipe.name;
  document.getElementById("rec-category").value = recipe.category;
  document.getElementById("rec-price").value = recipe.selling_price;

  document.getElementById("btn-delete-recipe").style.display = "inline-flex";
  document.getElementById("btn-check-avail").style.display = "inline-flex";
  document.getElementById("btn-cook").style.display = "inline-flex";

  // Map items
  currentRecipeItems = (recipe.items || []).map(it => {
    const matchedIng = allIngredients.find(i => i.id === it.ingredient_id);
    return {
      ingredient_id: it.ingredient_id,
      name: it.ingredient_name || matchedIng?.name || "İnqrediyent",
      unit: it.unit || matchedIng?.unit || "kq",
      quantity_needed: parseFloat(it.quantity_needed),
      unit_price: parseFloat(it.unit_price || matchedIng?.unit_price || 0)
    };
  });

  renderCurrentRecipeItems();
  recalculateMetrics();
  renderRecipeCards(allRecipes);
  if (window.lucide) lucide.createIcons();
}

function renderCurrentRecipeItems() {
  const tbody = document.getElementById("recipe-items-tbody");
  if (!currentRecipeItems || currentRecipeItems.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--slate-500); padding: 14px;">Tərkibdə inqrediyent yoxdur.</td></tr>`;
    return;
  }

  tbody.innerHTML = currentRecipeItems.map((it, idx) => {
    const itemCost = it.quantity_needed * it.unit_price;
    return `
      <tr>
        <td><strong>${it.name}</strong></td>
        <td><span class="badge badge-gray">${it.unit}</span></td>
        <td>
          <input type="number" class="form-control tabular-nums" style="width: 90px; display: inline-block; padding: 3px 6px; font-size: 12px;"
            step="0.0001" min="0.0001" value="${it.quantity_needed}"
            onchange="updateItemQuantity(${idx}, this.value)">
        </td>
        <td class="tabular-nums">${it.unit_price.toFixed(2)} ₼</td>
        <td class="tabular-nums"><strong>${itemCost.toFixed(2)} ₼</strong></td>
        <td style="text-align: center;">
          <button type="button" class="btn-icon" style="color: var(--danger);" onclick="removeRecipeItem(${idx})" title="Çıxar">
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

function addIngredientToRecipe() {
  const select = document.getElementById("picker-ingredient");
  const qtyInput = document.getElementById("picker-qty");

  const ingId = parseInt(select.value);
  const qty = parseFloat(qtyInput.value);

  if (!ingId) {
    showToast("Zəhmət olmasa inqrediyent seçin", "error");
    return;
  }
  if (isNaN(qty) || qty <= 0) {
    showToast("Zəhmət olmasa düzgün miqdar daxil edin", "error");
    return;
  }

  const ingredient = allIngredients.find(i => i.id === ingId);
  if (!ingredient) return;

  const existingIdx = currentRecipeItems.findIndex(i => i.ingredient_id === ingId);
  if (existingIdx >= 0) {
    currentRecipeItems[existingIdx].quantity_needed += qty;
  } else {
    currentRecipeItems.push({
      ingredient_id: ingredient.id,
      name: ingredient.name,
      unit: ingredient.unit,
      quantity_needed: qty,
      unit_price: parseFloat(ingredient.unit_price || 0)
    });
  }

  select.value = "";
  qtyInput.value = "";
  renderCurrentRecipeItems();
  recalculateMetrics();
}

function updateItemQuantity(idx, val) {
  const qty = parseFloat(val);
  if (isNaN(qty) || qty <= 0) {
    showToast("Miqdar 0-dan böyük olmalıdır", "error");
    renderCurrentRecipeItems();
    return;
  }
  currentRecipeItems[idx].quantity_needed = qty;
  renderCurrentRecipeItems();
  recalculateMetrics();
}

function removeRecipeItem(idx) {
  currentRecipeItems.splice(idx, 1);
  renderCurrentRecipeItems();
  recalculateMetrics();
}

function recalculateMetrics() {
  const cost = currentRecipeItems.reduce((acc, it) => acc + (it.quantity_needed * it.unit_price), 0);
  const price = parseFloat(document.getElementById("rec-price").value) || 0;

  document.getElementById("display-cost").innerText = cost.toFixed(2) + " ₼";

  let margin = 0;
  if (price > 0) {
    margin = ((price - cost) / price) * 100;
  }
  const marginEl = document.getElementById("display-margin");
  marginEl.innerText = margin.toFixed(1) + "%";
  marginEl.style.color = margin >= 40 ? "#15803d" : "#b45309";
}

document.getElementById("rec-price")?.addEventListener("input", recalculateMetrics);

async function handleRecipeSave(e) {
  e.preventDefault();
  const id = document.getElementById("rec-id").value;
  const isEdit = Boolean(id);

  if (currentRecipeItems.length === 0) {
    showToast("Reseptdə ən azı 1 inqrediyent olmalıdır!", "error");
    return;
  }

  const payload = {
    name: document.getElementById("rec-name").value.trim(),
    category: document.getElementById("rec-category").value,
    selling_price: parseFloat(document.getElementById("rec-price").value) || 0,
    items: currentRecipeItems.map(it => ({
      ingredient_id: it.ingredient_id,
      quantity_needed: it.quantity_needed
    }))
  };

  try {
    const url = isEdit ? `/api/recipes/${id}` : "/api/recipes";
    const method = isEdit ? "PUT" : "POST";

    const saved = await apiFetch(url, {
      method: method,
      body: JSON.stringify(payload)
    });

    showToast(isEdit ? "Resept yeniləndi!" : "Yeni resept yaradıldı!", "success");
    await loadRecipes();
    selectRecipe(saved.id);
  } catch (err) {
    showToast(`Yadda saxlama xətası: ${err.message}`, "error");
  }
}

async function deleteCurrentRecipe() {
  if (!selectedRecipeId) return;
  const recipe = allRecipes.find(r => r.id === selectedRecipeId);
  const name = recipe ? `"${recipe.name}"` : "bu resepti";

  if (!confirm(`${name} reseptini silmək istədiyinizə əminsiniz?`)) return;

  try {
    await apiFetch(`/api/recipes/${selectedRecipeId}`, { method: "DELETE" });
    showToast("Resept silindi!", "success");
    selectedRecipeId = null;
    await loadRecipes();
  } catch (err) {
    showToast(`Silinmə xətası: ${err.message}`, "error");
  }
}

async function checkCurrentRecipeAvailability() {
  if (!selectedRecipeId) return;

  try {
    const res = await apiFetch(`/api/recipes/${selectedRecipeId}/check`, {
      method: "POST",
      body: JSON.stringify({ servings: 1 })
    });

    const banner = document.getElementById("avail-status-banner");
    if (res.can_cook) {
      banner.style.background = "#f0fdf4";
      banner.style.color = "#166534";
      banner.style.border = "1px solid #bbf7d0";
      banner.innerHTML = `<span style="font-weight:600;">Status:</span> Bütün inqrediyentlər stokda yetərlidir. Hazırlanma mümkündür.`;
    } else {
      banner.style.background = "#fef2f2";
      banner.style.color = "#991b1b";
      banner.style.border = "1px solid #fecaca";
      banner.innerHTML = `<span style="font-weight:600;">Diqqət:</span> Bəzi xammal ehtiyatları yetərsizdir.`;
    }

    const tbody = document.getElementById("avail-tbody");
    tbody.innerHTML = res.items.map(it => `
      <tr class="${it.sufficient ? '' : 'stock-red'}">
        <td><strong>${it.ingredient_name}</strong></td>
        <td class="tabular-nums">${Number(it.required).toFixed(4)} ${it.unit}</td>
        <td class="tabular-nums">${Number(it.available).toFixed(2)} ${it.unit}</td>
        <td>${it.sufficient ? '<span class="badge badge-green"><span class="badge-dot"></span>Yetərli</span>' : '<span class="badge badge-red"><span class="badge-dot"></span>Çatışmır</span>'}</td>
      </tr>
    `).join("");

    openModal("avail-modal");
  } catch (err) {
    showToast("Yoxlama zamanı xəta: " + err.message, "error");
  }
}

function openCookModal() {
  if (!selectedRecipeId) return;
  const recipe = allRecipes.find(r => r.id === selectedRecipeId);
  if (!recipe) return;

  document.getElementById("cook-recipe-name").innerText = `${recipe.name} (${recipe.selling_price} ₼)`;
  document.getElementById("cook-servings").value = 1;
  openModal("cook-modal");
  if (window.lucide) lucide.createIcons();
}

async function handleCookSubmit(e) {
  e.preventDefault();
  if (!selectedRecipeId) return;

  const servings = parseInt(document.getElementById("cook-servings").value);
  if (isNaN(servings) || servings < 1) {
    showToast("Porsiya sayı ən azı 1 olmalıdır", "error");
    return;
  }

  try {
    const res = await apiFetch(`/api/recipes/${selectedRecipeId}/cook`, {
      method: "POST",
      body: JSON.stringify({ servings: servings })
    });

    closeModal("cook-modal");
    showToast(`${res.recipe_name} (${servings} porsiya) hazırlandı və stokdan silindi!`, "success");

    // Refresh data
    await loadRecipes();
    selectRecipe(selectedRecipeId);
  } catch (err) {
    if (err.code === "INSUFFICIENT_STOCK" && err.details) {
      const shortages = Array.isArray(err.details) ? err.details : [err.details];
      const detailStr = shortages.map(s => `• ${s.ingredient_name}: mövcud ${s.available}, tələb ${s.requested}`).join("<br>");

      const banner = document.getElementById("avail-status-banner");
      banner.style.background = "#fef2f2";
      banner.style.color = "#991b1b";
      banner.style.border = "1px solid #fecaca";
      banner.innerHTML = `<strong>Stok Çatışmazlığı Səbəbindən Hazırlana Bilməz:</strong><br>${detailStr}`;

      closeModal("cook-modal");
      openModal("avail-modal");
    } else {
      showToast(`Hazırlama xətası: ${err.message}`, "error");
    }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  loadRecipes();
});
