(function () {
  "use strict";

  var tg = window.Telegram && window.Telegram.WebApp;
  // Brauzerda ochilganda platform = "unknown" bo'ladi
  var inTelegram = !!(tg && tg.platform && tg.platform !== "unknown");
  // Menyu/inline tugmadan ochilganda query_id bo'ladi — u holda sendData ishlamaydi
  var canSendData = inTelegram && !(tg.initDataUnsafe && tg.initDataUnsafe.query_id);

  var CART_KEY = "tmart_cart_v1";
  var CUSTOMER_KEY = "tmart_customer_v1";

  var state = {
    products: [],
    byId: {},
    settings: {},
    cart: load(CART_KEY) || {},
    filter: "all",
    query: "",
    view: "catalog"
  };

  var $ = function (id) { return document.getElementById(id); };

  function load(key) {
    try { return JSON.parse(localStorage.getItem(key)); } catch (e) { return null; }
  }
  function save(key, value) {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch (e) { /* e'tiborsiz */ }
  }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function money(n) {
    return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, " ") + " " + (state.settings.currency || "so'm");
  }
  function haptic(type) {
    try { if (inTelegram && tg.HapticFeedback) tg.HapticFeedback.impactOccurred(type || "light"); } catch (e) {}
  }
  function toast(msg, ms) {
    var t = $("toast");
    t.textContent = msg;
    t.classList.remove("hidden");
    clearTimeout(toast._t);
    toast._t = setTimeout(function () { t.classList.add("hidden"); }, ms || 2500);
  }

  // ---------- Hisob-kitob ----------
  function cartItems() {
    return Object.keys(state.cart).filter(function (id) {
      var p = state.byId[id];
      return p && p.available !== false && state.cart[id] > 0;
    }).map(function (id) { return { product: state.byId[id], qty: state.cart[id] }; });
  }
  function cartCount() { return cartItems().reduce(function (s, i) { return s + i.qty; }, 0); }
  function subtotal() { return cartItems().reduce(function (s, i) { return s + i.qty * i.product.price; }, 0); }
  function deliveryMode() {
    var r = document.querySelector('input[name="delivery"]:checked');
    return r ? r.value : "delivery";
  }
  function deliveryFee(mode) {
    if (mode !== "delivery") return 0;
    var free = state.settings.free_delivery_from;
    if (free && subtotal() >= free) return 0;
    return state.settings.delivery_fee || 0;
  }

  function setQty(id, qty) {
    qty = Math.max(0, Math.min(99, qty));
    if (qty === 0) delete state.cart[id]; else state.cart[id] = qty;
    save(CART_KEY, state.cart);
    haptic("light");
    renderAll();
  }

  // ---------- Rasm / placeholder ----------
  function thumbHtml(p) {
    var ph = '<div class="placeholder ' + esc(p.category) + '">🍜</div>';
    if (!p.image) return ph;
    return '<img src="' + esc(p.image) + '" alt="' + esc(p.name) + '" loading="lazy" ' +
      'onerror="this.outerHTML=\'' + ph.replace(/"/g, "&quot;") + '\'">';
  }
  function stepperHtml(id, qty) {
    return '<div class="stepper"><button data-act="dec" data-id="' + esc(id) + '">−</button>' +
      '<span>' + qty + '</span><button data-act="inc" data-id="' + esc(id) + '">+</button></div>';
  }

  // ---------- Katalog ----------
  function renderCatalog() {
    var q = state.query.toLowerCase();
    var list = state.products.filter(function (p) {
      if (state.filter !== "all" && p.category !== state.filter) return false;
      if (q && (p.name + " " + (p.description || "")).toLowerCase().indexOf(q) === -1) return false;
      return true;
    });
    $("empty").classList.toggle("hidden", list.length > 0);
    $("grid").innerHTML = list.map(function (p) {
      var qty = state.cart[p.id] || 0;
      var soldout = p.available === false;
      var flag = p.category === "korea" ? "🇰🇷 Koreya" : p.category === "china" ? "🇨🇳 Xitoy" : "";
      var spicy = p.spicy > 0 ? '<span class="spicy">' + "🌶".repeat(Math.min(3, p.spicy)) + "</span>" : "";
      var action = soldout
        ? '<button class="add-btn" disabled>Tugagan</button>'
        : qty > 0 ? stepperHtml(p.id, qty)
        : '<button class="add-btn" data-act="inc" data-id="' + esc(p.id) + '">+ Savatchaga</button>';
      return '<div class="card' + (soldout ? " soldout" : "") + '">' +
        '<div class="thumb">' + thumbHtml(p) + (flag ? '<span class="badge">' + flag + "</span>" : "") + spicy + "</div>" +
        '<div class="card-body"><div class="card-name">' + esc(p.name) + "</div>" +
        '<div class="card-desc">' + esc(p.description || "") + "</div>" +
        '<div class="price">' + money(p.price) + "</div>" + action + "</div></div>";
    }).join("");
  }

  // ---------- Savatcha ----------
  function totalsHtml(mode) {
    var sub = subtotal();
    var rows = '<div class="row"><span>Mahsulotlar (' + cartCount() + ' dona)</span><span>' + money(sub) + "</span></div>";
    var fee = 0;
    if (mode) {
      fee = deliveryFee(mode);
      if (mode === "delivery") {
        rows += '<div class="row"><span>Yetkazib berish</span><span>' + (fee ? money(fee) : "bepul") + "</span></div>";
      }
    }
    rows += '<div class="row total"><span>Jami</span><span>' + money(sub + fee) + "</span></div>";
    var notes = [];
    var free = state.settings.free_delivery_from;
    if (free && sub < free) notes.push(money(free) + " dan ortiq buyurtmada yetkazib berish bepul");
    var min = state.settings.min_order || 0;
    if (sub < min) notes.push("Eng kam buyurtma: " + money(min));
    notes.forEach(function (n) { rows += '<div class="note">' + n + "</div>"; });
    return rows;
  }

  function renderCart() {
    var items = cartItems();
    $("cart-empty").classList.toggle("hidden", items.length > 0);
    $("cart-list").innerHTML = items.map(function (i) {
      var p = i.product;
      return '<div class="cart-row"><div class="mini">' + thumbHtml(p) + "</div>" +
        '<div class="cart-info"><div class="card-name">' + esc(p.name) + "</div>" +
        '<div class="price">' + money(p.price * i.qty) + "</div></div>" + stepperHtml(p.id, i.qty) + "</div>";
    }).join("");
    $("cart-totals").innerHTML = items.length ? totalsHtml(null) : "";
  }

  function renderCheckout() {
    var mode = deliveryMode();
    $("address-field").classList.toggle("hidden", mode !== "delivery");
    var pickup = $("pickup-info");
    pickup.classList.toggle("hidden", mode !== "pickup" || !state.settings.pickup_address);
    pickup.textContent = "📍 Olib ketish manzili: " + (state.settings.pickup_address || "");
    $("checkout-totals").innerHTML = totalsHtml(mode);
  }

  // ---------- Navigatsiya va asosiy tugma ----------
  function show(view) {
    state.view = view;
    ["catalog", "cart", "checkout"].forEach(function (v) {
      $("view-" + v).classList.toggle("hidden", v !== view);
    });
    $("form-error").classList.add("hidden");
    window.scrollTo(0, 0);
    renderAll();
  }

  function mainButtonState() {
    var count = cartCount();
    if (state.view === "catalog") {
      return { text: "🛒 Savatcha (" + count + ") · " + money(subtotal()), visible: count > 0, enabled: true };
    }
    if (state.view === "cart") {
      var ok = subtotal() >= (state.settings.min_order || 0);
      return { text: ok ? "Rasmiylashtirish →" : "Eng kam buyurtma: " + money(state.settings.min_order), visible: count > 0, enabled: ok };
    }
    return { text: "✅ Buyurtma berish · " + money(subtotal() + deliveryFee(deliveryMode())), visible: count > 0, enabled: true };
  }

  function updateButtons() {
    var s = mainButtonState();
    if (inTelegram) {
      tg.MainButton.setParams({ text: s.text, color: s.enabled ? "#FF7A00" : "#9AA0A6", text_color: "#FFFFFF", is_visible: s.visible, is_active: s.enabled });
      if (state.view === "catalog") tg.BackButton.hide(); else tg.BackButton.show();
    } else {
      $("bottom-bar").classList.toggle("hidden", !s.visible && state.view === "catalog");
      $("main-btn").textContent = s.visible ? s.text : "Savatcha bo'sh";
      $("main-btn").disabled = !s.visible || !s.enabled;
      $("back-btn").classList.toggle("hidden", state.view === "catalog");
    }
  }

  function onMain() {
    if (state.view === "catalog") return show("cart");
    if (state.view === "cart") {
      if (subtotal() < (state.settings.min_order || 0)) return;
      return show("checkout");
    }
    submit();
  }
  function onBack() {
    if (state.view === "checkout") show("cart");
    else if (state.view === "cart") show("catalog");
  }

  function renderAll() {
    if (state.view === "catalog") renderCatalog();
    if (state.view === "cart") renderCart();
    if (state.view === "checkout") renderCheckout();
    updateButtons();
  }

  // ---------- Buyurtma yuborish ----------
  function formError(msg, field) {
    var el = $("form-error");
    el.textContent = msg;
    el.classList.remove("hidden");
    if (field) { field.classList.add("invalid"); field.focus(); }
    try { if (inTelegram) tg.HapticFeedback.notificationOccurred("error"); } catch (e) {}
  }

  function submit() {
    var f = $("form");
    Array.prototype.forEach.call(f.querySelectorAll(".invalid"), function (el) { el.classList.remove("invalid"); });
    var name = f.elements.namedItem("name").value.trim();
    var phone = f.elements.namedItem("phone").value.trim();
    var mode = deliveryMode();
    var address = f.elements.namedItem("address").value.trim();
    var comment = f.elements.namedItem("comment").value.trim();

    if (name.length < 2) return formError("Ismingizni kiriting.", f.elements.namedItem("name"));
    var digits = phone.replace(/\D/g, "");
    if (digits.length < 9 || digits.length > 15) return formError("Telefon raqamini to'g'ri kiriting.", f.elements.namedItem("phone"));
    if (mode === "delivery" && address.length < 5) return formError("Yetkazib berish manzilini kiriting.", f.elements.namedItem("address"));
    if (subtotal() < (state.settings.min_order || 0)) return formError("Eng kam buyurtma: " + money(state.settings.min_order));

    save(CUSTOMER_KEY, { name: name, phone: phone, address: address });

    var payload = JSON.stringify({
      v: 1,
      items: cartItems().map(function (i) { return [i.product.id, i.qty]; }),
      name: name,
      phone: phone,
      delivery: mode,
      address: mode === "delivery" ? address : "",
      comment: comment
    });

    if (!inTelegram) {
      // Brauzerda test: bot o'rniga ma'lumotni ko'rsatamiz
      window.__lastOrder = payload;
      toast("Test rejimi (Telegram'dan tashqarida).\nBotga yuboriladigan ma'lumot:\n" + payload, 8000);
      return;
    }
    if (!canSendData) {
      formError("Buyurtma berish uchun do'konni botdagi pastki «🛒 Do'konni ochish» tugmasi orqali oching.");
      return;
    }
    state.cart = {};
    save(CART_KEY, state.cart);
    tg.sendData(payload); // Telegram Mini App'ni yopadi va ma'lumotni botga yuboradi
  }

  // ---------- Hodisalar ----------
  function bind() {
    document.body.addEventListener("click", function (e) {
      var btn = e.target.closest("[data-act]");
      if (!btn) return;
      var id = btn.getAttribute("data-id");
      var qty = state.cart[id] || 0;
      setQty(id, btn.getAttribute("data-act") === "inc" ? qty + 1 : qty - 1);
    });
    $("chips").addEventListener("click", function (e) {
      var chip = e.target.closest(".chip");
      if (!chip) return;
      state.filter = chip.getAttribute("data-cat");
      Array.prototype.forEach.call(document.querySelectorAll(".chip"), function (c) { c.classList.toggle("active", c === chip); });
      haptic("light");
      renderCatalog();
    });
    $("search").addEventListener("input", function (e) { state.query = e.target.value.trim(); renderCatalog(); });
    $("form").addEventListener("change", function () { renderCheckout(); updateButtons(); });
    $("form").addEventListener("submit", function (e) { e.preventDefault(); });
    $("main-btn").addEventListener("click", onMain);
    $("back-btn").addEventListener("click", onBack);
    if (inTelegram) {
      tg.MainButton.onClick(onMain);
      tg.BackButton.onClick(onBack);
    }
  }

  function prefill() {
    var c = load(CUSTOMER_KEY) || {};
    var f = $("form");
    var user = inTelegram && tg.initDataUnsafe && tg.initDataUnsafe.user;
    f.elements.namedItem("name").value = c.name || (user ? [user.first_name, user.last_name].filter(Boolean).join(" ") : "");
    f.elements.namedItem("phone").value = c.phone || "+998 ";
    f.elements.namedItem("address").value = c.address || "";
  }

  function init() {
    if (inTelegram) {
      tg.ready();
      tg.expand();
      try { tg.setHeaderColor("#141414"); } catch (e) {}
    }
    bind();
    prefill();
    fetch("products.json", { cache: "no-store" })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (data) {
        state.settings = data.settings || {};
        state.products = data.products || [];
        state.byId = {};
        state.products.forEach(function (p) { state.byId[p.id] = p; });
        // Katalogdan o'chirilgan mahsulotlarni savatchadan olib tashlaymiz
        Object.keys(state.cart).forEach(function (id) { if (!state.byId[id]) delete state.cart[id]; });
        save(CART_KEY, state.cart);
        renderAll();
      })
      .catch(function () {
        $("grid").innerHTML = '<p class="muted center">Mahsulotlarni yuklab bo\'lmadi. Internetni tekshirib, qayta oching.</p>';
      });
  }

  init();
})();
