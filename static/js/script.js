// ==================================================
// Zenith JavaScript v16.1
// CART + WISHLIST + MOBILE DRAWER + SEARCH + BADGES
// + HERO CAROUSEL (SWIPE FIXED ✅)
// + GLOBAL OFFER TIMER ✅
// + SHOP THE LOOK ✅
// + CUSTOMIZATION STUDIO ✅ (COLOR + LOGO + TEXT + FONT)
// + COLOR-SPECIFIC IMAGES ✅
// + CART HORIZONTAL COMPACT LAYOUT ✅
// + QUICK ADD — CAPTURE PHASE FIX ✅
// + LAZY LOADING FOR CART & WISHLIST IMAGES ✅
// + COUPON SYNC (CART ↔ CHECKOUT) ✅
// + COUPON CSS INJECTION (bypass cache) ✅
// + REVIEWS CSS INJECTION (bypass cache) ✅
// + MINI-CART SIDE DRAWER (TITAN STYLE) ✅ 🆕
// ==================================================

"use strict";


// ==================================================
// GLOBAL DATA
// ==================================================

let cart = [];
let wishlist = [];

const CART_STORAGE_KEY = "cart";
const WISHLIST_STORAGE_KEY = "zenith_wishlist";


// ==================================================
// IMAGE URL HELPER
// ==================================================

function getImageUrl(image) {
    if (!image) return "";
    image = String(image);
    if (image.startsWith("http://") || image.startsWith("https://") || image.startsWith("/")) {
        return image;
    }
    return `/static/${image}`;
}


// ==================================================
// ESCAPE HTML
// ==================================================

function escapeHTML(value) {
    if (value === null || value === undefined) return "";
    return String(value)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}


// ==================================================
// TOAST NOTIFICATION
// ==================================================

function showToast(message, type = "success") {
    const existingToast = document.getElementById("zenith-toast");
    if (existingToast) existingToast.remove();

    const toast = document.createElement("div");
    toast.id = "zenith-toast";
    toast.className = `zenith-toast ${type}`;
    toast.innerHTML = `
        <i class="fa-solid ${type === "success" ? "fa-check-circle" : "fa-info-circle"}"></i>
        <span>${escapeHTML(message)}</span>
    `;

    document.body.appendChild(toast);

    setTimeout(() => { toast.classList.add("show"); }, 10);
    setTimeout(() => {
        toast.classList.remove("show");
        setTimeout(() => { toast.remove(); }, 300);
    }, 2500);
}


// ==================================================
// CART SYSTEM
// ==================================================

function loadCart() {
    try {
        const savedCart = localStorage.getItem(CART_STORAGE_KEY);
        if (!savedCart) { cart = []; return; }
        const parsedCart = JSON.parse(savedCart);
        cart = Array.isArray(parsedCart) ? parsedCart : [];
    } catch (error) {
        console.error("Cart loading error:", error);
        cart = [];
        localStorage.removeItem(CART_STORAGE_KEY);
    }
    normalizeCart();
}


function normalizeCart() {
    cart = cart
        .filter(item => item && item.id !== undefined && item.id !== null)
        .map(item => {
            let quantity = Number(item.quantity);
            if (!Number.isInteger(quantity) || quantity < 1) quantity = 1;
            if (quantity > 10) quantity = 10;
            return {
                id: Number(item.id),
                name: item.name || "Product",
                price: Number(item.price) || 0,
                image: item.image || "",
                quantity: quantity,
                size: item.size || null,
                color: item.color || null,
                customization: item.customization || null,
                is_customized: item.is_customized || false
            };
        });
    saveCart();
}


function saveCart() {
    try {
        localStorage.setItem(CART_STORAGE_KEY, JSON.stringify(cart));
    } catch (error) {
        console.error("Cart save error:", error);
    }
}


function findProduct(id, size = null, color = null, isCustomized = false) {
    return cart.find(item => {
        if (isCustomized) return false;
        if (item.is_customized) return false;
        return (
            Number(item.id) === Number(id) &&
            (item.size || null) === (size || null) &&
            (item.color || null) === (color || null)
        );
    });
}


function updateCartCount() {
    const counter = document.getElementById("cart-count");
    if (counter) {
        let total = 0;
        cart.forEach(item => { total += Number(item.quantity) || 0; });
        counter.textContent = total;
    }
    updateBottomNavBadges();
    updateMiniCartCount();
}


function getSelectedSize() {
    const activeSize = document.querySelector(
        ".size-options button.active, .size-btn-nb.active, .size-btn-custom-nb.active"
    );
    if (!activeSize) return null;
    return activeSize.textContent.trim() || activeSize.dataset.size || null;
}


function getSelectedColor() {
    const activeColor = document.querySelector(
        ".color-options .color.active, .color-options-nb .color-nb.active"
    );
    if (!activeColor) return null;
    if (activeColor.dataset.color) return activeColor.dataset.color;
    if (activeColor.classList.contains("black")) return "Black";
    if (activeColor.classList.contains("white")) return "White";
    if (activeColor.classList.contains("blue")) return "Blue";
    if (activeColor.classList.contains("red")) return "Red";
    return null;
}


function addToCart(button) {
    if (!button) return;

    const id = Number(button.dataset.id);
    const name = button.dataset.name || "Product";
    const price = Number(button.dataset.price) || 0;
    const image = button.dataset.image || "";

    if (!id) {
        showToast("Unable to add this product to cart.", "error");
        return;
    }

    const quantityInput = document.getElementById("quantity");
    let quantity = quantityInput ? Number(quantityInput.value) : 1;
    if (!Number.isInteger(quantity) || quantity < 1) quantity = 1;
    if (quantity > 10) quantity = 10;

    const size = getSelectedSize();
    const color = getSelectedColor();
    const existing = findProduct(id, size, color);

    if (existing) {
        existing.quantity = Number(existing.quantity) + quantity;
        if (existing.quantity > 10) existing.quantity = 10;
    } else {
        cart.push({
            id: id, name: name, price: price, image: image,
            quantity: quantity, size: size, color: color,
            customization: null, is_customized: false
        });
    }

    saveCart();
    updateCartCount();

    let message = `${name} added to cart!`;
    if (size) message += ` (Size: ${size})`;
    if (color) message += ` (Color: ${color})`;
    showToast(message);

    // 🆕 Titan-style: open mini-cart drawer
    openMiniCart();
}


function registerCartButtons() {
    document.addEventListener("click", function(event) {
        const button = event.target.closest(".add-cart");
        if (!button) return;
        event.preventDefault();
        event.stopPropagation();
        addToCart(button);
    }, true);
}


function displayCart() {
    const cartContainer = document.getElementById("cart-items");
    const totalElement = document.getElementById("grand-total");

    if (!cartContainer) return;
    cartContainer.innerHTML = "";

    if (cart.length === 0) {
        cartContainer.innerHTML = `
            <div class="empty-cart-nb">
                <div class="empty-cart-icon-nb">
                    <i class="fa-solid fa-cart-shopping"></i>
                </div>
                <h2>Your Cart is Empty</h2>
                <p>Add some products to continue shopping.</p>
                <a href="/#products" class="empty-cart-btn-nb">
                    <i class="fa-solid fa-bag-shopping"></i>
                    Continue Shopping
                </a>
            </div>
        `;
        if (totalElement) totalElement.textContent = "0";
        updateCartSummaryNB(0, 0);
        updateCartCount();
        clearCouponIfCartEmpty();
        return;
    }

    let grandTotal = 0;
    let totalQty = 0;

    cart.forEach((item, index) => {
        const price = Number(item.price) || 0;
        const quantity = Number(item.quantity) || 1;
        const subtotal = price * quantity;
        grandTotal += subtotal;
        totalQty += quantity;

        let cartImage = item.image;
        if (item.is_customized && item.customization) {
            const color = item.color || "white";
            const colorImageMap = {
                "white": "images/tshirts/tshirt-front.png",
                "red": "images/tshirts/tshirt-red.png",
                "green": "images/tshirts/tshirt-green.png",
                "cream": "images/tshirts/tshirt-cream.png",
                "pista": "images/tshirts/tshirt-pista.png",
                "pink": "images/tshirts/tshirt-pink.png"
            };
            if (colorImageMap[color]) cartImage = colorImageMap[color];
        }

        const imageUrl = getImageUrl(cartImage);

        let variantHTML = "";
        if (item.size) variantHTML += `<span>Size: <strong>${escapeHTML(item.size)}</strong></span>`;
        if (item.color) variantHTML += `<span>Color: <strong>${escapeHTML(item.color)}</strong></span>`;

        let customizationHTML = "";
        if (item.is_customized && item.customization) {
            const cust = item.customization;
            const front = cust.front || {};
            const back = cust.back || {};

            const fontSummary = (side) => {
                if (!side.text) return "";
                const parts = [];
                if (side.text_font) {
                    const fontName = side.text_font.split(",")[0].replace(/['"]/g, "").trim();
                    parts.push(fontName);
                }
                if (side.text_weight && side.text_weight !== "700") {
                    const weightMap = { "300": "Light", "500": "Regular", "700": "Bold" };
                    parts.push(weightMap[side.text_weight] || side.text_weight);
                }
                if (side.text_style === "italic") parts.push("Italic");
                if (side.text_spacing !== undefined && Number(side.text_spacing) !== 1) {
                    const spacingMap = { 0: "Tight", 1: "Normal", 3: "Wide" };
                    parts.push(spacingMap[Number(side.text_spacing)] || "Normal");
                }
                return parts.length ? `<span class="cart-custom-font-nb"><i class="fa-solid fa-font"></i> ${escapeHTML(parts.join(" · "))}</span>` : "";
            };

            customizationHTML = `
                <div class="cart-customization-nb">
                    <div class="cart-custom-badge-nb">
                        <i class="fa-solid fa-palette"></i>
                        Customized
                    </div>
                    ${
                        front.logo || front.text
                            ? `<div class="cart-custom-side-nb">
                                <span class="cart-custom-label-nb">Front:</span>
                                ${front.logo ? `<span class="cart-custom-tag-nb"><i class="fa-solid fa-mountain"></i> ${escapeHTML(front.logo.replace('mountain-', 'Mountain '))}</span>` : ""}
                                ${front.text ? `<span class="cart-custom-tag-nb"><i class="fa-solid fa-font"></i> ${escapeHTML(front.text)}</span>` : ""}
                                ${fontSummary(front)}
                              </div>`
                            : ""
                    }
                    ${
                        back.logo || back.text
                            ? `<div class="cart-custom-side-nb">
                                <span class="cart-custom-label-nb">Back:</span>
                                ${back.logo ? `<span class="cart-custom-tag-nb"><i class="fa-solid fa-mountain"></i> ${escapeHTML(back.logo.replace('mountain-', 'Mountain '))}</span>` : ""}
                                ${back.text ? `<span class="cart-custom-tag-nb"><i class="fa-solid fa-font"></i> ${escapeHTML(back.text)}</span>` : ""}
                                ${fontSummary(back)}
                              </div>`
                            : ""
                    }
                </div>
            `;
        }

        const cartItem = document.createElement("div");
        cartItem.className = "cart-item";
        cartItem.dataset.index = index;

        cartItem.innerHTML = `
            <img class="cart-item-img"
                 src="${escapeHTML(imageUrl)}"
                 alt="${escapeHTML(item.name)}"
                 loading="lazy">

            <div class="cart-info">
                <h3>
                    ${escapeHTML(item.name)}
                    ${item.is_customized ? `<span class="customized-badge-inline"><i class="fa-solid fa-palette"></i></span>` : ""}
                </h3>
                <p class="cart-price">₹${price.toLocaleString("en-IN")}</p>
                ${variantHTML ? `<div class="cart-variants">${variantHTML}</div>` : ""}
                ${customizationHTML}

                <div class="cart-item-controls-mobile">
                    <div class="cart-quantity">
                        <button type="button" class="quantity-decrease" data-index="${index}">−</button>
                        <span>${quantity}</span>
                        <button type="button" class="quantity-increase" data-index="${index}">+</button>
                    </div>
                    <div class="cart-subtotal">₹${subtotal.toLocaleString("en-IN")}</div>
                    <button type="button" class="remove-btn" data-index="${index}" aria-label="Remove item">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </div>
            </div>

            <div class="cart-quantity cart-quantity-desktop">
                <button type="button" class="quantity-decrease" data-index="${index}">−</button>
                <span>${quantity}</span>
                <button type="button" class="quantity-increase" data-index="${index}">+</button>
            </div>
            <div class="cart-subtotal cart-subtotal-desktop">
                ₹${subtotal.toLocaleString("en-IN")}
            </div>
            <button type="button" class="remove-btn remove-btn-desktop" data-index="${index}" aria-label="Remove item">
                <i class="fa-solid fa-trash"></i>
            </button>
        `;

        cartContainer.appendChild(cartItem);
    });

    if (totalElement) totalElement.textContent = grandTotal.toLocaleString("en-IN");
    updateCartSummaryNB(grandTotal, totalQty);
    registerCartActions();
    revalidateCouponOnCartChange();
}


function updateCartSummaryNB(subtotal, qty) {
    const subtotalEl = document.getElementById("subtotal-nb");
    if (subtotalEl) subtotalEl.textContent = subtotal.toLocaleString("en-IN");

    const countEl = document.getElementById("cart-items-count-nb");
    if (countEl) countEl.textContent = `(${qty})`;

    if (typeof window.updateShippingBar === "function") {
        window.updateShippingBar(subtotal);
    }
}


function registerCartActions() {
    const cartContainer = document.getElementById("cart-items");
    if (!cartContainer) return;

    cartContainer.querySelectorAll(".remove-btn").forEach(button => {
        button.addEventListener("click", function(event) {
            event.preventDefault();
            removeItemByIndex(Number(this.dataset.index));
        });
    });

    cartContainer.querySelectorAll(".quantity-decrease").forEach(button => {
        button.addEventListener("click", function(event) {
            event.preventDefault();
            changeQuantityByIndex(Number(this.dataset.index), -1);
        });
    });

    cartContainer.querySelectorAll(".quantity-increase").forEach(button => {
        button.addEventListener("click", function(event) {
            event.preventDefault();
            changeQuantityByIndex(Number(this.dataset.index), 1);
        });
    });
}


function changeQuantityByIndex(index, change) {
    if (index < 0 || index >= cart.length) return;
    const product = cart[index];
    let newQuantity = Number(product.quantity) + Number(change);
    if (newQuantity <= 0) { removeItemByIndex(index); return; }
    if (newQuantity > 10) newQuantity = 10;
    product.quantity = newQuantity;
    saveCart();
    updateCartCount();
    displayCart();
    renderMiniCart(); // 🆕 keep drawer synced
}


function removeItemByIndex(index) {
    if (index < 0 || index >= cart.length) return;
    cart.splice(index, 1);
    saveCart();
    updateCartCount();
    displayCart();
    renderMiniCart(); // 🆕 keep drawer synced
}


// ==================================================
// 🆕 MINI-CART SIDE DRAWER (TITAN STYLE)
// ==================================================

function openMiniCart() {
    const drawer = document.getElementById("minicartDrawer");
    const overlay = document.getElementById("minicartOverlay");
    if (!drawer || !overlay) return;

    renderMiniCart();
    drawer.classList.add("open");
    overlay.classList.add("show");
    document.body.classList.add("minicart-open");
}


function closeMiniCart() {
    const drawer = document.getElementById("minicartDrawer");
    const overlay = document.getElementById("minicartOverlay");
    if (!drawer || !overlay) return;

    drawer.classList.remove("open");
    overlay.classList.remove("show");
    document.body.classList.remove("minicart-open");
}


function goToCheckout() {
    // If cart is empty, don't allow checkout
    if (!cart || cart.length === 0) {
        showToast("Your cart is empty.", "error");
        return;
    }
    window.location.href = "/checkout";
}


function updateMiniCartCount() {
    const countEl = document.getElementById("minicartCount");
    if (!countEl) return;
    let total = 0;
    cart.forEach(item => { total += Number(item.quantity) || 0; });
    countEl.textContent = `(${total})`;
}


function renderMiniCart() {
    const container = document.getElementById("minicartItems");
    const footer = document.getElementById("minicartFooter");
    const subtotalEl = document.getElementById("minicartSubtotal");
    if (!container) return;

    container.innerHTML = "";
    updateMiniCartCount();

    // Empty state
    if (!cart || cart.length === 0) {
        container.innerHTML = `
            <div class="minicart-empty">
                <div class="minicart-empty-icon">
                    <i class="fa-solid fa-bag-shopping"></i>
                </div>
                <h4>Your cart is empty</h4>
                <p>Looks like you haven't added anything yet.</p>
                <a href="/#products" class="minicart-empty-btn" onclick="closeMiniCart()">
                    <i class="fa-solid fa-arrow-right"></i>
                    Start Shopping
                </a>
            </div>
        `;
        if (subtotalEl) subtotalEl.textContent = "0";
        if (footer) footer.style.display = "none";
        return;
    }

    if (footer) footer.style.display = "";

    let subtotal = 0;

    cart.forEach((item, index) => {
        const price = Number(item.price) || 0;
        const quantity = Number(item.quantity) || 1;
        const lineTotal = price * quantity;
        subtotal += lineTotal;

        // Customized color image
        let itemImage = item.image;
        if (item.is_customized && item.customization) {
            const color = item.color || "white";
            const colorImageMap = {
                "white": "images/tshirts/tshirt-front.png",
                "red": "images/tshirts/tshirt-red.png",
                "green": "images/tshirts/tshirt-green.png",
                "cream": "images/tshirts/tshirt-cream.png",
                "pista": "images/tshirts/tshirt-pista.png",
                "pink": "images/tshirts/tshirt-pink.png"
            };
            if (colorImageMap[color]) itemImage = colorImageMap[color];
        }
        const imgUrl = getImageUrl(itemImage);

        // Variant chips
        let variantLine = "";
        if (item.size) variantLine += `<span class="minicart-variant">Size: ${escapeHTML(item.size)}</span>`;
        if (item.color) variantLine += `<span class="minicart-variant">Color: ${escapeHTML(item.color)}</span>`;
        if (item.is_customized) variantLine += `<span class="minicart-variant custom"><i class="fa-solid fa-palette"></i> Custom</span>`;

        const row = document.createElement("div");
        row.className = "minicart-item";
        row.dataset.index = index;

        row.innerHTML = `
            <a href="/product/${Number(item.id)}" class="minicart-item-img-wrap" onclick="closeMiniCart()">
                <img src="${escapeHTML(imgUrl)}" alt="${escapeHTML(item.name)}" loading="lazy">
            </a>

            <div class="minicart-item-info">
                <h4 class="minicart-item-name">${escapeHTML(item.name)}</h4>
                ${variantLine ? `<div class="minicart-item-variants">${variantLine}</div>` : ""}
                <div class="minicart-item-price">₹${price.toLocaleString("en-IN")}</div>

                <div class="minicart-item-controls">
                    <div class="minicart-qty">
                        <button type="button" class="minicart-qty-btn" data-action="decrease" data-index="${index}" aria-label="Decrease quantity">−</button>
                        <span>${quantity}</span>
                        <button type="button" class="minicart-qty-btn" data-action="increase" data-index="${index}" aria-label="Increase quantity">+</button>
                    </div>
                    <button type="button" class="minicart-remove" data-action="remove" data-index="${index}" aria-label="Remove item">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </div>
            </div>

            <div class="minicart-line-total">₹${lineTotal.toLocaleString("en-IN")}</div>
        `;

        container.appendChild(row);
    });

    if (subtotalEl) subtotalEl.textContent = subtotal.toLocaleString("en-IN");
}


function registerMiniCart() {
    const container = document.getElementById("minicartItems");
    if (!container) return;

    // Event delegation — qty +/- and remove
    container.addEventListener("click", function(event) {
        const btn = event.target.closest("button[data-action]");
        if (!btn) return;
        event.preventDefault();

        const action = btn.dataset.action;
        const index = Number(btn.dataset.index);
        if (Number.isNaN(index) || index < 0 || index >= cart.length) return;

        if (action === "increase") {
            const newQty = Number(cart[index].quantity) + 1;
            if (newQty > 10) {
                showToast("Max 10 per item allowed.", "error");
                return;
            }
            cart[index].quantity = newQty;
            saveCart();
            updateCartCount();
            renderMiniCart();
            if (document.getElementById("cart-items")) displayCart();
        } else if (action === "decrease") {
            const newQty = Number(cart[index].quantity) - 1;
            if (newQty <= 0) {
                cart.splice(index, 1);
                showToast("Item removed from cart");
            } else {
                cart[index].quantity = newQty;
            }
            saveCart();
            updateCartCount();
            renderMiniCart();
            if (document.getElementById("cart-items")) displayCart();
        } else if (action === "remove") {
            cart.splice(index, 1);
            saveCart();
            updateCartCount();
            renderMiniCart();
            if (document.getElementById("cart-items")) displayCart();
            showToast("Item removed from cart");
        }
    });

    // Close on Escape
    document.addEventListener("keydown", function(event) {
        if (event.key === "Escape") {
            const drawer = document.getElementById("minicartDrawer");
            if (drawer && drawer.classList.contains("open")) {
                closeMiniCart();
            }
        }
    });
}


// ==================================================
// COUPON HELPERS — CART ↔ CHECKOUT SYNC
// ==================================================

function clearCouponIfCartEmpty() {
    if (cart.length === 0) {
        try {
            localStorage.removeItem("zenith_coupon_code");
            localStorage.removeItem("zenith_coupon_discount");
        } catch (e) { /* ignore */ }
    }
}


async function revalidateCouponOnCartChange() {
    const couponCode = localStorage.getItem("zenith_coupon_code");
    if (!couponCode) return;

    const subtotalEl = document.getElementById("subtotal-nb");
    if (!subtotalEl) return;

    const subtotal = parseFloat((subtotalEl.textContent || "0").replace(/,/g, "")) || 0;
    if (subtotal <= 0) { clearCouponIfCartEmpty(); return; }

    try {
        const response = await fetch("/api/coupon/validate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ code: couponCode, amount: subtotal })
        });
        const data = await response.json();

        if (data.valid) {
            try {
                localStorage.setItem("zenith_coupon_discount", data.discount);
            } catch (e) { /* ignore */ }
        } else {
            try {
                localStorage.removeItem("zenith_coupon_code");
                localStorage.removeItem("zenith_coupon_discount");
            } catch (e) { /* ignore */ }
            if (document.getElementById("cart-items")) {
                showToast("Coupon removed: " + (data.message || "no longer valid"), "error");
            }
        }
    } catch (err) {
        console.warn("Coupon revalidate failed:", err);
    }
}


// ==================================================
// CUSTOMIZATION — ADD TO CART
// ==================================================

function addCustomizedToCart() {
    const customizePage = document.querySelector(".customize-page-nb");
    if (!customizePage) return;

    const urlParts = window.location.pathname.split("/");
    const productId = Number(urlParts[urlParts.length - 1]);
    if (!productId) { showToast("Product not found.", "error"); return; }

    const productData = window.customizeProductData || null;
    if (!productData) { showToast("Product data missing.", "error"); return; }

    const activeColor = document.querySelector(".color-swatch-nb.active");
    const selectedColor = activeColor ? activeColor.dataset.color : "white";
    const selectedColorImageFront = activeColor ? (activeColor.dataset.imageFront || "tshirt-front.png") : "tshirt-front.png";
    const selectedColorImageBack = activeColor ? (activeColor.dataset.imageBack || "tshirt-back.png") : "tshirt-back.png";

    const activeSize = document.querySelector(".size-btn-custom-nb.active");
    const selectedSize = activeSize ? activeSize.dataset.size : "M";

    const frontLogo = window.selectedFrontLogo || null;
    const frontText = window.selectedFrontText || "";
    const frontLogoSize = window.selectedFrontLogoSize || 60;
    const frontLogoPos = window.selectedFrontLogoPos || { top: 38, left: 50 };
    const frontTextSize = window.selectedFrontTextSize || 16;
    const frontTextColor = window.selectedFrontTextColor || "#1a1a1a";
    const frontTextPos = window.selectedFrontTextPos || { top: 55, left: 50 };
    const frontTextFont = window.selectedFrontTextFont || "'Inter', sans-serif";
    const frontTextWeight = window.selectedFrontTextWeight || "700";
    const frontTextStyle = window.selectedFrontTextStyle || "normal";
    const frontTextSpacing = window.selectedFrontTextSpacing !== undefined ? window.selectedFrontTextSpacing : 1;

    const backLogo = window.selectedBackLogo || null;
    const backText = window.selectedBackText || "";
    const backLogoSize = window.selectedBackLogoSize || 60;
    const backLogoPos = window.selectedBackLogoPos || { top: 38, left: 50 };
    const backTextSize = window.selectedBackTextSize || 16;
    const backTextColor = window.selectedBackTextColor || "#1a1a1a";
    const backTextPos = window.selectedBackTextPos || { top: 55, left: 50 };
    const backTextFont = window.selectedBackTextFont || "'Inter', sans-serif";
    const backTextWeight = window.selectedBackTextWeight || "700";
    const backTextStyle = window.selectedBackTextStyle || "normal";
    const backTextSpacing = window.selectedBackTextSpacing !== undefined ? window.selectedBackTextSpacing : 1;

    let customizationPrice = 0;
    if (frontLogo) customizationPrice += 50;
    if (frontText) customizationPrice += 50;
    if (backLogo) customizationPrice += 50;
    if (backText) customizationPrice += 50;

    const basePrice = Number(productData.price) || 0;
    const totalPrice = basePrice + customizationPrice;

    const customization = {
        color_front_image: selectedColorImageFront,
        color_back_image: selectedColorImageBack,
        front: {
            logo: frontLogo, text: frontText,
            logo_size: frontLogoSize, logo_position: frontLogoPos,
            text_size: frontTextSize, text_color: frontTextColor,
            text_position: frontTextPos, text_font: frontTextFont,
            text_weight: frontTextWeight, text_style: frontTextStyle,
            text_spacing: frontTextSpacing
        },
        back: {
            logo: backLogo, text: backText,
            logo_size: backLogoSize, logo_position: backLogoPos,
            text_size: backTextSize, text_color: backTextColor,
            text_position: backTextPos, text_font: backTextFont,
            text_weight: backTextWeight, text_style: backTextStyle,
            text_spacing: backTextSpacing
        }
    };

    const existingIndex = cart.findIndex(item =>
        item.is_customized &&
        Number(item.id) === productId &&
        JSON.stringify(item.customization) === JSON.stringify(customization) &&
        item.size === selectedSize &&
        item.color === selectedColor
    );

    if (existingIndex !== -1) {
        cart[existingIndex].quantity = Number(cart[existingIndex].quantity) + 1;
        if (cart[existingIndex].quantity > 10) cart[existingIndex].quantity = 10;
        showToast("Customized item quantity updated!");
    } else {
        cart.push({
            id: productId,
            name: productData.name + " (Custom)",
            price: totalPrice,
            image: "images/tshirts/" + selectedColorImageFront,
            quantity: 1,
            size: selectedSize,
            color: selectedColor,
            customization: customization,
            is_customized: true
        });
        showToast("Customized product added to cart! 🎨");
    }

    saveCart();
    updateCartCount();

    // 🆕 Open mini-cart instead of redirect
    setTimeout(() => { openMiniCart(); }, 300);
}


// ==================================================
// PRODUCT PAGE
// ==================================================

function changeImage(element) {
    const mainImage = document.getElementById("main-image");
    if (!mainImage || !element) return;

    const newSrc = element.dataset && element.dataset.img
        ? element.dataset.img
        : (element.querySelector && element.querySelector("img")
            ? element.querySelector("img").src
            : element.src);

    if (newSrc) mainImage.src = newSrc;

    document.querySelectorAll(".thumbnail, .thumb-nb").forEach(img => {
        img.classList.remove("active");
    });
    element.classList.add("active");
}


function registerSizeButtons() {
    const buttons = document.querySelectorAll(".size-options button, .size-btn-nb");
    buttons.forEach(button => {
        button.addEventListener("click", function(event) {
            event.preventDefault();
            buttons.forEach(btn => btn.classList.remove("active"));
            this.classList.add("active");
            const label = document.getElementById("selected-size-nb");
            if (label && this.dataset.size) label.textContent = this.dataset.size;
        });
    });
}


function registerColorButtons() {
    const colors = document.querySelectorAll(".color-options .color, .color-options-nb .color-nb");
    colors.forEach(color => {
        color.addEventListener("click", function(event) {
            event.preventDefault();
            colors.forEach(c => c.classList.remove("active"));
            this.classList.add("active");
            const label = document.getElementById("selected-color-nb");
            if (label && this.dataset.color) label.textContent = this.dataset.color;
        });
    });
}


// ==================================================
// WISHLIST SYSTEM
// ==================================================

function loadWishlist() {
    try {
        const savedWishlist = localStorage.getItem(WISHLIST_STORAGE_KEY);
        if (!savedWishlist) { wishlist = []; return; }
        const parsedWishlist = JSON.parse(savedWishlist);
        wishlist = Array.isArray(parsedWishlist) ? parsedWishlist : [];
    } catch (error) {
        console.error("Wishlist loading error:", error);
        wishlist = [];
        localStorage.removeItem(WISHLIST_STORAGE_KEY);
    }
    normalizeWishlist();
}


function normalizeWishlist() {
    const uniqueProducts = new Map();
    wishlist.forEach(item => {
        if (!item || item.id === undefined || item.id === null) return;
        const id = Number(item.id);
        if (!id) return;
        if (!uniqueProducts.has(id)) {
            uniqueProducts.set(id, {
                id: id,
                name: item.name || "Product",
                price: Number(item.price) || 0,
                old_price: Number(item.old_price) || 0,
                image: item.image || "",
                rating: item.rating || "",
                description: item.description || ""
            });
        }
    });
    wishlist = Array.from(uniqueProducts.values());
}


function saveWishlist() {
    try {
        localStorage.setItem(WISHLIST_STORAGE_KEY, JSON.stringify(wishlist));
    } catch (error) {
        console.error("Wishlist save error:", error);
    }
}


function isInWishlist(id) {
    return wishlist.some(item => Number(item.id) === Number(id));
}


function updateWishlistCount() {
    const counters = document.querySelectorAll("#wishlist-count, #wishlist-count-nb");
    counters.forEach(counter => { counter.textContent = wishlist.length; });
    updateBottomNavBadges();
}


function getWishlistProductData(button) {
    if (!button) return null;

    let id = Number(button.dataset.id);
    let name = button.dataset.name || "";
    let price = Number(button.dataset.price) || 0;
    let oldPrice = Number(button.dataset.oldPrice || button.dataset.old_price) || 0;
    let image = button.dataset.image || "";
    let rating = button.dataset.rating || "";
    let description = button.dataset.description || "";

    const card = button.closest(".card, .product-card-nb, .related-card-nb");
    if (card) {
        const cartButton = card.querySelector(".add-cart");
        if (cartButton) {
            if (!id) id = Number(cartButton.dataset.id);
            if (!name) name = cartButton.dataset.name || "";
            if (!price) price = Number(cartButton.dataset.price) || 0;
            if (!image) image = cartButton.dataset.image || "";
        }
        if (!oldPrice) {
            const oldPriceElement = card.querySelector(".price span, .product-price-nb span");
            if (oldPriceElement) oldPrice = Number(oldPriceElement.textContent.replace(/[^\d]/g, "")) || 0;
        }
        if (!rating) {
            const ratingElement = card.querySelector(".rating, .product-rating-nb");
            if (ratingElement) rating = ratingElement.textContent.trim();
        }
    }

    if (!id) return null;

    return {
        id: id, name: name || "Product", price: price,
        old_price: oldPrice, image: image,
        rating: rating, description: description
    };
}


function toggleWishlist(button) {
    if (!button) return;

    const product = getWishlistProductData(button);
    if (!product) {
        showToast("Unable to add this product to wishlist.", "error");
        return;
    }

    const existingIndex = wishlist.findIndex(item => Number(item.id) === Number(product.id));

    if (existingIndex !== -1) {
        wishlist.splice(existingIndex, 1);
        saveWishlist();
        updateWishlistCount();
        updateWishlistButtons();
        showToast(`${product.name} removed from wishlist`);
        return;
    }

    wishlist.push(product);
    saveWishlist();
    updateWishlistCount();
    updateWishlistButtons();
    showToast(`${product.name} added to wishlist ❤️`);
}


function updateWishlistButtons() {
    const buttons = document.querySelectorAll(".wishlist-btn, .wishlist-btn-nb, .wishlist-btn-icon");
    buttons.forEach(button => {
        const product = getWishlistProductData(button);
        if (!product) return;

        const active = isInWishlist(product.id);
        const icon = button.querySelector("i");

        if (active) {
            button.classList.add("active");
            button.setAttribute("aria-label", "Remove from wishlist");
            button.setAttribute("title", "Remove from wishlist");
            if (icon) {
                icon.classList.remove("fa-regular");
                icon.classList.add("fa-solid");
            }
        } else {
            button.classList.remove("active");
            button.setAttribute("aria-label", "Add to wishlist");
            button.setAttribute("title", "Add to wishlist");
            if (icon) {
                icon.classList.remove("fa-solid");
                icon.classList.add("fa-regular");
            }
        }
    });
}


function registerWishlistButtons() {
    document.addEventListener("click", function(event) {
        const button = event.target.closest(".wishlist-btn, .wishlist-btn-nb, .wishlist-btn-icon");
        if (!button) return;
        event.preventDefault();
        event.stopPropagation();
        toggleWishlist(button);
    });
    updateWishlistButtons();
}


function removeFromWishlist(id) {
    const numericId = Number(id);
    wishlist = wishlist.filter(item => Number(item.id) !== numericId);
    saveWishlist();
    updateWishlistCount();
    updateWishlistButtons();
    if (document.getElementById("wishlist-items")) displayWishlist();
    showToast("Removed from wishlist");
}


function clearWishlist() {
    if (wishlist.length === 0) return;
    const confirmed = confirm("Are you sure you want to remove all wishlist items?");
    if (!confirmed) return;
    wishlist = [];
    saveWishlist();
    updateWishlistCount();
    updateWishlistButtons();
    displayWishlist();
    showToast("Wishlist cleared");
}


function addWishlistItemToCart(id) {
    const product = wishlist.find(item => Number(item.id) === Number(id));
    if (!product) return;

    const existing = findProduct(product.id, null, null);
    if (existing) {
        existing.quantity = Number(existing.quantity) + 1;
        if (existing.quantity > 10) existing.quantity = 10;
    } else {
        cart.push({
            id: product.id, name: product.name, price: product.price,
            image: product.image, quantity: 1, size: null, color: null,
            customization: null, is_customized: false
        });
    }
    saveCart();
    updateCartCount();
    showToast(`${product.name} added to cart!`);

    // 🆕 Open mini-cart
    openMiniCart();
}


// ==================================================
// WISHLIST PAGE
// ==================================================

function displayWishlist() {
    const container = document.getElementById("wishlist-items");
    const emptyState = document.getElementById("wishlist-empty");
    const clearButton = document.getElementById("clear-wishlist");

    if (!container) return;
    container.innerHTML = "";

    if (wishlist.length === 0) {
        if (emptyState) {
            emptyState.style.display = "block";
        } else {
            container.innerHTML = `
                <div class="empty-wishlist">
                    <div class="empty-wishlist-icon">❤️</div>
                    <h2>Your Wishlist is Empty</h2>
                    <p>Save your favorite products here and come back later.</p>
                    <a href="/#products" class="continue-shopping">Continue Shopping</a>
                </div>
            `;
        }
        if (clearButton) clearButton.style.display = "none";
        updateWishlistCount();
        return;
    }

    if (emptyState) emptyState.style.display = "none";
    if (clearButton) clearButton.style.display = "inline-flex";

    wishlist.forEach(product => {
        const item = document.createElement("div");
        item.className = "wishlist-card-nb";
        item.dataset.id = product.id;

        const imageUrl = getImageUrl(product.image);

        item.innerHTML = `
            <a href="/product/${Number(product.id)}" class="wishlist-img-wrap-nb">
                <img src="${escapeHTML(imageUrl)}" alt="${escapeHTML(product.name)}" loading="lazy">
            </a>
            <button type="button" class="wishlist-remove-nb" data-id="${Number(product.id)}" aria-label="Remove from wishlist">
                <i class="fa-solid fa-xmark"></i>
            </button>
            <div class="wishlist-info-nb">
                <span class="wishlist-cat-nb">Wishlist</span>
                <h3 class="wishlist-name-nb">
                    <a href="/product/${Number(product.id)}">${escapeHTML(product.name)}</a>
                </h3>
                ${product.rating ? `<div class="wishlist-rating-nb"><i class="fa-solid fa-star"></i>${escapeHTML(product.rating)}</div>` : ""}
                <p class="wishlist-price-nb">
                    ₹${Number(product.price).toLocaleString("en-IN")}
                    ${product.old_price ? `<del>₹${Number(product.old_price).toLocaleString("en-IN")}</del>` : ""}
                </p>
                <div class="wishlist-actions-nb">
                    <button type="button" class="wishlist-add-cart-nb" data-id="${Number(product.id)}">
                        <i class="fa-solid fa-cart-plus"></i> Add to Cart
                    </button>
                    <button type="button" class="wishlist-remove-btn-nb" data-id="${Number(product.id)}" aria-label="Remove">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                </div>
            </div>
        `;

        container.appendChild(item);
    });

    registerWishlistPageActions();
}


function registerWishlistPageActions() {
    const container = document.getElementById("wishlist-items");
    if (!container) return;

    container.querySelectorAll(".wishlist-add-cart-nb").forEach(button => {
        button.addEventListener("click", function(event) {
            event.preventDefault();
            event.stopPropagation();
            addWishlistItemToCart(Number(this.dataset.id));
        });
    });

    container.querySelectorAll(".wishlist-remove-btn-nb, .wishlist-remove-nb").forEach(button => {
        button.addEventListener("click", function(event) {
            event.preventDefault();
            event.stopPropagation();
            removeFromWishlist(Number(this.dataset.id));
        });
    });
}


// ==================================================
// MOBILE DRAWER
// ==================================================

function openDrawer() {
    const drawer = document.getElementById("mobile-drawer");
    const overlay = document.getElementById("drawer-overlay");
    if (drawer) drawer.classList.add("open");
    if (overlay) overlay.classList.add("show");
    document.body.style.overflow = "hidden";
    document.body.classList.add("drawer-open");
}


function closeDrawer() {
    const drawer = document.getElementById("mobile-drawer");
    const overlay = document.getElementById("drawer-overlay");
    if (drawer) drawer.classList.remove("open");
    if (overlay) overlay.classList.remove("show");
    document.body.style.overflow = "";
    document.body.classList.remove("drawer-open");
}


function registerDrawer() {
    const hamburgerBtn = document.getElementById("hamburger-btn");
    const drawerClose = document.getElementById("drawer-close");
    const drawerOverlay = document.getElementById("drawer-overlay");

    if (hamburgerBtn) hamburgerBtn.addEventListener("click", function(e) { e.preventDefault(); openDrawer(); });
    if (drawerClose) drawerClose.addEventListener("click", closeDrawer);
    if (drawerOverlay) drawerOverlay.addEventListener("click", closeDrawer);

    document.querySelectorAll(".drawer-nav a").forEach(link => {
        link.addEventListener("click", function() { setTimeout(closeDrawer, 150); });
    });

    document.addEventListener("keydown", function(e) {
        if (e.key === "Escape") closeDrawer();
    });
}


// ==================================================
// BOTTOM NAV
// ==================================================

function registerBottomNav() {
    const currentPath = window.location.pathname;
    document.querySelectorAll(".bottom-nav-item").forEach(item => item.classList.remove("active"));

    if (currentPath === "/" || currentPath === "") {
        const homeItem = document.querySelector('.bottom-nav-item[data-page="home"]');
        if (homeItem) homeItem.classList.add("active");
    }
    if (currentPath === "/cart") {
        const cartItem = document.querySelector('.bottom-nav-item[data-page="cart"]');
        if (cartItem) cartItem.classList.add("active");
    }
    if (currentPath === "/wishlist") {
        const wishlistItem = document.querySelector('.bottom-nav-item[data-page="wishlist"]');
        if (wishlistItem) wishlistItem.classList.add("active");
    }
    if (currentPath === "/profile" || currentPath === "/orders") {
        const profileItem = document.querySelector('.bottom-nav-item[data-page="profile"]');
        if (profileItem) profileItem.classList.add("active");
    }
    if (currentPath === "/login" || currentPath === "/signup") {
        const loginItem = document.querySelector('.bottom-nav-item[data-page="login"]');
        if (loginItem) loginItem.classList.add("active");
    }
}


// ==================================================
// BOTTOM NAV BADGES
// ==================================================

function updateBottomNavBadges() {
    const cartCountEl = document.getElementById('cart-count');
    const wishlistCountEl = document.getElementById('wishlist-count');

    const cartCount = cartCountEl ? parseInt(cartCountEl.textContent) || 0 : 0;
    const wishlistCount = wishlistCountEl ? parseInt(wishlistCountEl.textContent) || 0 : 0;

    const bottomCartBadge = document.getElementById('bottom-cart-count');
    const bottomWishlistBadge = document.getElementById('bottom-wishlist-count');

    if (bottomCartBadge) {
        bottomCartBadge.textContent = cartCount;
        bottomCartBadge.classList.toggle('show', cartCount > 0);
    }
    if (bottomWishlistBadge) {
        bottomWishlistBadge.textContent = wishlistCount;
        bottomWishlistBadge.classList.toggle('show', wishlistCount > 0);
    }
}


// ==================================================
// SEARCH OVERLAY
// ==================================================

function registerSearch() {
    const searchBtn = document.getElementById('search-btn');
    const searchOverlay = document.getElementById('search-overlay');
    const searchClose = document.getElementById('search-close');
    const searchInput = document.getElementById('search-input');

    function openSearch() {
        if (!searchOverlay) return;
        searchOverlay.classList.add('show');
        document.body.style.overflow = 'hidden';
        setTimeout(function() { if (searchInput) searchInput.focus(); }, 300);
    }

    function closeSearch() {
        if (!searchOverlay) return;
        searchOverlay.classList.remove('show');
        document.body.style.overflow = '';
        if (searchInput) searchInput.value = '';
    }

    if (searchBtn) searchBtn.addEventListener('click', openSearch);
    if (searchClose) searchClose.addEventListener('click', closeSearch);
    if (searchOverlay) {
        searchOverlay.addEventListener('click', function(e) {
            if (e.target === searchOverlay) closeSearch();
        });
    }

    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && searchOverlay && searchOverlay.classList.contains('show')) {
            closeSearch();
        }
    });
}


// ==================================================
// HEADER SCROLL SHADOW
// ==================================================

function registerHeaderScroll() {
    const mainHeader = document.querySelector('.main-header');
    if (!mainHeader) return;

    function handleScroll() {
        if (window.scrollY > 10) {
            mainHeader.classList.add('is-scrolled');
        } else {
            mainHeader.classList.remove('is-scrolled');
        }
    }

    window.addEventListener('scroll', handleScroll, { passive: true });
    handleScroll();
}


// ==================================================
// HERO CAROUSEL
// ==================================================

function registerHeroCarousel() {
    const carousel = document.getElementById('heroCarousel');
    const slides = document.querySelectorAll('.hero-slide');
    const prevBtn = document.getElementById('heroPrev');
    const nextBtn = document.getElementById('heroNext');
    const dotsContainer = document.getElementById('heroDots');

    if (!carousel || slides.length === 0) return;

    let currentIndex = 0;
    let autoPlayTimer = null;
    const AUTO_PLAY_INTERVAL = 5000;

    function createDots() {
        if (!dotsContainer) return;
        dotsContainer.innerHTML = '';
        slides.forEach((slide, index) => {
            const dot = document.createElement('button');
            dot.className = 'hero-dot' + (index === 0 ? ' active' : '');
            dot.setAttribute('aria-label', `Go to slide ${index + 1}`);
            dot.setAttribute('data-index', index);
            dot.addEventListener('click', () => { goToSlide(index); resetAutoPlay(); });
            dotsContainer.appendChild(dot);
        });
    }

    function goToSlide(index) {
        if (index < 0) index = slides.length - 1;
        if (index >= slides.length) index = 0;
        slides.forEach(slide => slide.classList.remove('active'));
        if (dotsContainer) {
            dotsContainer.querySelectorAll('.hero-dot').forEach(dot => dot.classList.remove('active'));
        }
        slides[index].classList.add('active');
        if (dotsContainer) {
            const activeDot = dotsContainer.querySelector(`.hero-dot[data-index="${index}"]`);
            if (activeDot) activeDot.classList.add('active');
        }
        currentIndex = index;
    }

    function nextSlide() { goToSlide(currentIndex + 1); }
    function prevSlide() { goToSlide(currentIndex - 1); }
    function startAutoPlay() { stopAutoPlay(); autoPlayTimer = setInterval(nextSlide, AUTO_PLAY_INTERVAL); }
    function stopAutoPlay() { if (autoPlayTimer) { clearInterval(autoPlayTimer); autoPlayTimer = null; } }
    function resetAutoPlay() { stopAutoPlay(); startAutoPlay(); }

    if (prevBtn) prevBtn.addEventListener('click', () => { prevSlide(); resetAutoPlay(); });
    if (nextBtn) nextBtn.addEventListener('click', () => { nextSlide(); resetAutoPlay(); });

    let touchStartX = 0, touchStartY = 0, touchEndX = 0, touchEndY = 0, isSwiping = false;

    carousel.addEventListener('touchstart', function(e) {
        touchStartX = e.changedTouches[0].screenX;
        touchStartY = e.changedTouches[0].screenY;
        touchEndX = touchStartX;
        touchEndY = touchStartY;
        isSwiping = false;
        stopAutoPlay();
    }, { passive: true });

    carousel.addEventListener('touchmove', function(e) {
        touchEndX = e.changedTouches[0].screenX;
        touchEndY = e.changedTouches[0].screenY;
        const diffX = Math.abs(touchEndX - touchStartX);
        const diffY = Math.abs(touchEndY - touchStartY);
        if (diffX > diffY && diffX > 10) {
            isSwiping = true;
            if (e.cancelable) e.preventDefault();
        }
    }, { passive: false });

    carousel.addEventListener('touchend', function(e) {
        if (!isSwiping) { startAutoPlay(); return; }
        const swipeThreshold = 30;
        const diff = touchStartX - touchEndX;
        if (diff > swipeThreshold) nextSlide();
        else if (diff < -swipeThreshold) prevSlide();
        isSwiping = false;
        startAutoPlay();
    }, { passive: true });

    document.addEventListener('keydown', function(e) {
        const rect = carousel.getBoundingClientRect();
        if (rect.bottom < 0 || rect.top > window.innerHeight) return;
        if (e.key === 'ArrowLeft') { prevSlide(); resetAutoPlay(); }
        else if (e.key === 'ArrowRight') { nextSlide(); resetAutoPlay(); }
    });

    carousel.addEventListener('mouseenter', stopAutoPlay);
    carousel.addEventListener('mouseleave', startAutoPlay);

    document.addEventListener('visibilitychange', function() {
        if (document.hidden) stopAutoPlay();
        else startAutoPlay();
    });

    createDots();
    startAutoPlay();
}


// ==================================================
// GLOBAL OFFER TIMER
// ==================================================

function registerOfferTimer() {
    const hoursEl = document.getElementById('timer-hours');
    const minsEl = document.getElementById('timer-mins');
    const secsEl = document.getElementById('timer-secs');

    if (!hoursEl || !minsEl || !secsEl) return;

    let saleEndTime = localStorage.getItem('zenith_sale_end');
    if (!saleEndTime) {
        saleEndTime = new Date().getTime() + (6 * 60 * 60 * 1000);
        localStorage.setItem('zenith_sale_end', saleEndTime);
    } else {
        saleEndTime = Number(saleEndTime);
    }

    function updateTimer() {
        const now = new Date().getTime();
        const diff = saleEndTime - now;
        if (diff <= 0) {
            hoursEl.textContent = '00';
            minsEl.textContent = '00';
            secsEl.textContent = '00';
            localStorage.removeItem('zenith_sale_end');
            return;
        }
        const hours = Math.floor(diff / (1000 * 60 * 60));
        const mins = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
        const secs = Math.floor((diff % (1000 * 60)) / 1000);
        hoursEl.textContent = String(hours).padStart(2, '0');
        minsEl.textContent = String(mins).padStart(2, '0');
        secsEl.textContent = String(secs).padStart(2, '0');
    }

    updateTimer();
    setInterval(updateTimer, 1000);
}


// ==================================================
// SHOP THE FULL LOOK
// ==================================================

function addAllLookItems() {
    const lookSection = document.querySelector(".shop-look-nb");
    if (!lookSection) return;

    const buttons = lookSection.querySelectorAll(".shop-look-add-nb");
    if (buttons.length === 0) return;

    let addedCount = 0;

    buttons.forEach(button => {
        const id = Number(button.dataset.id);
        const name = button.dataset.name || "Product";
        const price = Number(button.dataset.price) || 0;
        const image = button.dataset.image || "";
        if (!id) return;

        const existing = findProduct(id, null, null);
        if (existing) {
            existing.quantity = Number(existing.quantity) + 1;
            if (existing.quantity > 10) existing.quantity = 10;
        } else {
            cart.push({
                id: id, name: name, price: price, image: image,
                quantity: 1, size: null, color: null,
                customization: null, is_customized: false
            });
        }
        addedCount++;
    });

    if (addedCount > 0) {
        saveCart();
        updateCartCount();
        showToast(`${addedCount} items added to cart! 🛒`);

        // 🆕 Open mini-cart
        openMiniCart();
    }
}


// ==================================================
// INITIALIZATION
// ==================================================

document.addEventListener("DOMContentLoaded", function() {

    console.log("🚀 Zenith JS v16.1 loaded — Mini-Cart Drawer ✅");

    loadCart();
    loadWishlist();

    registerCartButtons();
    registerWishlistButtons();
    registerDrawer();
    registerSearch();
    registerHeaderScroll();
    registerSizeButtons();
    registerColorButtons();
    registerBottomNav();
    registerMiniCart(); // 🆕

    registerHeroCarousel();
    registerOfferTimer();

    updateCartCount();
    updateWishlistCount();
    updateBottomNavBadges();
    renderMiniCart(); // 🆕

    if (document.getElementById("cart-items")) displayCart();
    if (document.getElementById("wishlist-items")) displayWishlist();

    const clearBtn = document.getElementById("clear-wishlist");
    if (clearBtn) clearBtn.addEventListener("click", clearWishlist);
});


// ==================================================
// COUPON DROPDOWN — JAVASCRIPT CSS INJECTION
// Bypass CSS file caching issue ✅
// ==================================================

(function injectCouponStyles() {
    if (document.getElementById("coupon-injected-styles")) return;

    const style = document.createElement("style");
    style.id = "coupon-injected-styles";
    style.textContent = `
        /* Coupon Input Wrapper */
        .coupon-input-wrap-nb {
            position: relative !important;
            display: flex !important;
            align-items: stretch !important;
            width: 100% !important;
            gap: 0 !important;
            border: none !important;
            background: transparent !important;
        }

        /* Coupon Input */
        .coupon-input-wrap-nb input {
            flex: 1 1 auto !important;
            min-width: 0 !important;
            width: auto !important;
            padding: 12px 16px !important;
            border: 1.5px solid #e0e0e0 !important;
            border-right: none !important;
            border-radius: 6px 0 0 6px !important;
            font-size: 13px !important;
            background: #fafafa !important;
            letter-spacing: 1px !important;
            text-transform: uppercase !important;
            color: #1a1a1a !important;
            outline: none !important;
            font-family: 'Courier New', monospace !important;
            font-weight: 600 !important;
            box-sizing: border-box !important;
        }

        .coupon-input-wrap-nb input:focus {
            border-color: #c9a961 !important;
            background: #fff !important;
            box-shadow: 0 0 0 3px rgba(201, 169, 97, 0.15) !important;
        }

        .coupon-input-wrap-nb input:disabled {
            background: #f0f0f0 !important;
            color: #666 !important;
            cursor: not-allowed !important;
        }

        .coupon-input-wrap-nb input::placeholder {
            color: #aaa !important;
            text-transform: none !important;
            letter-spacing: 0 !important;
            font-family: 'Inter', sans-serif !important;
            font-weight: 400 !important;
        }

        /* Apply/Remove Button */
        .coupon-apply-btn-nb {
            flex: 0 0 auto !important;
            padding: 12px 22px !important;
            background: #1a1a1a !important;
            color: #fff !important;
            border: none !important;
            border-radius: 0 6px 6px 0 !important;
            font-size: 11px !important;
            font-weight: 700 !important;
            letter-spacing: 1.5px !important;
            text-transform: uppercase !important;
            cursor: pointer !important;
            white-space: nowrap !important;
            font-family: 'Inter', sans-serif !important;
        }

        .coupon-apply-btn-nb:hover:not(:disabled) {
            background: #c9a961 !important;
            color: #1a1a1a !important;
        }

        .coupon-apply-btn-nb.remove-state-nb {
            background: #dc3545 !important;
            color: #fff !important;
        }

        /* Suggestions Dropdown */
        .coupon-suggestions-nb {
            position: absolute !important;
            top: calc(100% + 6px) !important;
            left: 0 !important;
            right: 0 !important;
            width: 100% !important;
            min-width: 100% !important;
            max-width: 100% !important;
            flex: none !important;
            flex-grow: 0 !important;
            flex-shrink: 0 !important;
            flex-basis: auto !important;
            box-sizing: border-box !important;
            background: #ffffff !important;
            border: 1.5px solid #e0e0e0 !important;
            border-radius: 8px !important;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15) !important;
            max-height: 320px !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
            z-index: 99999 !important;
            display: none !important;
            transform: none !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        .coupon-suggestions-nb.show-nb { display: block !important; }

        .coupon-suggestions-header-nb {
            padding: 10px 14px !important;
            background: #faf8f5 !important;
            border-bottom: 1px solid #f0f0f0 !important;
            font-size: 10px !important;
            font-weight: 700 !important;
            letter-spacing: 1.5px !important;
            text-transform: uppercase !important;
            color: #c9a961 !important;
            display: flex !important;
            align-items: center !important;
            gap: 6px !important;
            position: sticky !important;
            top: 0 !important;
            z-index: 1 !important;
        }

        .coupon-suggestion-item-nb {
            display: flex !important;
            justify-content: space-between !important;
            align-items: center !important;
            padding: 12px 14px !important;
            border-bottom: 1px dashed #f0f0f0 !important;
            cursor: pointer !important;
            transition: background 0.15s ease !important;
            gap: 10px !important;
            width: 100% !important;
            box-sizing: border-box !important;
        }

        .coupon-suggestion-item-nb:last-child { border-bottom: none !important; }
        .coupon-suggestion-item-nb:hover:not(.disabled-nb) { background: #faf8f5 !important; }
        .coupon-suggestion-item-nb.disabled-nb { opacity: 0.55 !important; cursor: not-allowed !important; }

        .coupon-suggestion-left-nb {
            display: flex !important;
            flex-direction: column !important;
            gap: 3px !important;
            flex: 1 1 auto !important;
            min-width: 0 !important;
        }

        .coupon-suggestion-code-nb {
            font-family: 'Courier New', monospace !important;
            font-weight: 700 !important;
            font-size: 12px !important;
            background: #1a1a1a !important;
            color: #c9a961 !important;
            padding: 3px 9px !important;
            border-radius: 4px !important;
            display: inline-block !important;
            align-self: flex-start !important;
            letter-spacing: 1.5px !important;
            white-space: nowrap !important;
        }

        .coupon-suggestion-desc-nb {
            font-size: 12px !important;
            font-weight: 600 !important;
            color: #28a745 !important;
            margin-top: 4px !important;
            white-space: nowrap !important;
        }

        .coupon-suggestion-meta-nb {
            font-size: 10.5px !important;
            color: #888 !important;
            white-space: nowrap !important;
        }

        .coupon-suggestion-right-nb {
            color: #c9a961 !important;
            font-size: 16px !important;
            margin-left: 8px !important;
            flex-shrink: 0 !important;
        }

        .not-eligible-nb {
            font-size: 9px !important;
            color: #dc3545 !important;
            font-weight: 700 !important;
            text-transform: uppercase !important;
            letter-spacing: 0.5px !important;
            white-space: nowrap !important;
        }

        .coupon-suggestion-loading-nb,
        .coupon-suggestion-empty-nb {
            padding: 18px 14px !important;
            text-align: center !important;
            color: #999 !important;
            font-size: 12px !important;
        }

        /* Parent containers — overflow visible */
        .cart-nb,
        .cart-grid-nb,
        .cart-summary-col-nb,
        .cart-summary-nb,
        .coupon-box-nb {
            overflow: visible !important;
        }

        .cart-summary-col-nb,
        .cart-summary-nb,
        .coupon-box-nb {
            position: relative !important;
        }
    `;

    document.head.appendChild(style);
    console.log("✅ Coupon CSS injected via JS — 100% working!");
})();


// ==================================================
// REVIEWS — JAVASCRIPT CSS INJECTION
// Bypass CSS file caching/override issue ✅
// ==================================================

(function injectReviewsStyles() {
    if (document.getElementById("reviews-injected-styles")) return;

    const style = document.createElement("style");
    style.id = "reviews-injected-styles";
    style.textContent = `
        /* Reviews Section — High specificity override */
        html body section.reviews-section-nb {
            display: block !important;
            padding: 80px 8% !important;
            background: #faf8f5 !important;
            border-top: 1px solid #e8e2d9 !important;
        }

        html body section.reviews-section-nb .reviews-container-nb {
            display: grid !important;
            grid-template-columns: 380px 1fr !important;
            gap: 40px !important;
            max-width: 1200px !important;
            margin: 0 auto !important;
            align-items: start !important;
        }

        html body section.reviews-section-nb .reviews-left-nb {
            display: flex !important;
            flex-direction: column !important;
            gap: 25px !important;
            position: sticky !important;
            top: 120px !important;
            min-width: 0 !important;
        }

        html body section.reviews-section-nb .reviews-right-nb {
            display: block !important;
            min-width: 0 !important;
        }

        html body section.reviews-section-nb .rating-summary-nb {
            display: block !important;
            background: #fff !important;
            border: 1px solid #e8e2d9 !important;
            padding: 30px !important;
            text-align: center !important;
        }

        html body section.reviews-section-nb .summary-score-nb {
            display: block !important;
            padding-bottom: 22px !important;
            margin-bottom: 22px !important;
            border-bottom: 1px dashed #e8e2d9 !important;
        }

        html body section.reviews-section-nb .summary-number-nb {
            font-family: 'Playfair Display', serif !important;
            font-size: 56px !important;
            font-weight: 600 !important;
            color: #1a1a1a !important;
            line-height: 1 !important;
            margin-bottom: 8px !important;
            display: block !important;
        }

        html body section.reviews-section-nb .summary-stars-nb {
            font-size: 18px !important;
            letter-spacing: 3px !important;
            margin-bottom: 10px !important;
            display: block !important;
        }

        html body section.reviews-section-nb .summary-count-nb {
            font-size: 12px !important;
            color: #888 !important;
            letter-spacing: 0.5px !important;
            display: block !important;
        }

        html body section.reviews-section-nb .summary-bars-nb {
            display: flex !important;
            flex-direction: column !important;
            gap: 10px !important;
        }

        html body section.reviews-section-nb .bar-row-nb {
            display: flex !important;
            flex-direction: row !important;
            align-items: center !important;
            gap: 12px !important;
            width: 100% !important;
        }

        html body section.reviews-section-nb .bar-label-nb {
            width: 32px !important;
            flex-shrink: 0 !important;
            display: inline-flex !important;
            align-items: center !important;
            gap: 3px !important;
            font-size: 12px !important;
            font-weight: 600 !important;
            color: #555 !important;
        }

        html body section.reviews-section-nb .bar-label-nb i {
            color: #c9a961 !important;
            font-size: 10px !important;
        }

        html body section.reviews-section-nb .bar-track-nb {
            flex: 1 1 auto !important;
            height: 8px !important;
            background: #f0ece6 !important;
            border-radius: 4px !important;
            overflow: hidden !important;
            display: block !important;
            min-width: 0 !important;
        }

        html body section.reviews-section-nb .bar-fill-nb {
            height: 100% !important;
            background: linear-gradient(90deg, #c9a961, #D4AF37) !important;
            border-radius: 4px !important;
            transition: width 0.6s ease !important;
            width: 0%;
        }

        html body section.reviews-section-nb .bar-count-nb {
            min-width: 28px !important;
            text-align: right !important;
            flex-shrink: 0 !important;
            font-size: 12px !important;
            font-weight: 600 !important;
            color: #1a1a1a !important;
        }

        html body section.reviews-section-nb .reviews-list-nb {
            display: flex !important;
            flex-direction: column !important;
            gap: 18px !important;
        }

        html body section.reviews-section-nb .write-review-box-nb,
        html body section.reviews-section-nb .user-review-box-nb,
        html body section.reviews-section-nb .review-card-nb {
            display: block !important;
            background: #fff !important;
            border: 1px solid #e8e2d9 !important;
            padding: 25px !important;
        }

        html body section.reviews-section-nb .no-reviews-nb {
            display: block !important;
            text-align: center !important;
            padding: 60px 30px !important;
            background: #fff !important;
            border: 1px dashed #e8e2d9 !important;
        }

        /* Responsive */
        @media (max-width: 992px) {
            html body section.reviews-section-nb .reviews-container-nb {
                grid-template-columns: 1fr !important;
                gap: 30px !important;
            }
            html body section.reviews-section-nb .reviews-left-nb {
                position: static !important;
            }
        }

        @media (max-width: 768px) {
            html body section.reviews-section-nb {
                padding: 50px 5% !important;
            }
        }
    `;

    document.head.appendChild(style);
    console.log("✅ Reviews CSS injected via JS — layout fixed!");
})();


// ==================================================
// APPLY BAR WIDTHS AFTER RENDER (for review distribution bars)
// ==================================================

document.addEventListener("DOMContentLoaded", function() {
    setTimeout(function() {
        document.querySelectorAll('.bar-fill-nb[data-width]').forEach(function(el) {
            var w = parseFloat(el.getAttribute('data-width')) || 0;
            el.style.width = w + '%';
        });
    }, 100);
});
