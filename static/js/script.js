// ==================================================
// Zenith JavaScript v13.0
// CART + WISHLIST + MOBILE DRAWER + SEARCH + BADGES
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

    if (!image) {
        return "";
    }

    image = String(image);

    if (
        image.startsWith("http://") ||
        image.startsWith("https://") ||
        image.startsWith("/")
    ) {
        return image;
    }

    return `/static/${image}`;
}


// ==================================================
// ESCAPE HTML
// ==================================================

function escapeHTML(value) {

    if (value === null || value === undefined) {
        return "";
    }

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
    if (existingToast) {
        existingToast.remove();
    }

    const toast = document.createElement("div");
    toast.id = "zenith-toast";
    toast.className = `zenith-toast ${type}`;
    toast.innerHTML = `
        <i class="fa-solid ${type === "success" ? "fa-check-circle" : "fa-info-circle"}"></i>
        <span>${escapeHTML(message)}</span>
    `;

    document.body.appendChild(toast);

    setTimeout(() => {
        toast.classList.add("show");
    }, 10);

    setTimeout(() => {
        toast.classList.remove("show");
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 2500);
}


// ==================================================
// CART SYSTEM
// ==================================================

// --------------------------------------------------
// LOAD CART
// --------------------------------------------------

function loadCart() {

    try {

        const savedCart = localStorage.getItem(CART_STORAGE_KEY);

        if (!savedCart) {
            cart = [];
            return;
        }

        const parsedCart = JSON.parse(savedCart);

        if (Array.isArray(parsedCart)) {
            cart = parsedCart;
        } else {
            cart = [];
        }

    } catch (error) {

        console.error("Cart loading error:", error);

        cart = [];

        localStorage.removeItem(CART_STORAGE_KEY);
    }

    normalizeCart();
}


// --------------------------------------------------
// NORMALIZE CART
// --------------------------------------------------

function normalizeCart() {

    cart = cart

        .filter(item => {
            return (
                item &&
                item.id !== undefined &&
                item.id !== null
            );
        })

        .map(item => {

            let quantity = Number(item.quantity);

            if (
                !Number.isInteger(quantity) ||
                quantity < 1
            ) {
                quantity = 1;
            }

            if (quantity > 10) {
                quantity = 10;
            }

            return {

                id: Number(item.id),

                name: item.name || "Product",

                price: Number(item.price) || 0,

                image: item.image || "",

                quantity: quantity,

                size: item.size || null,

                color: item.color || null
            };
        });

    saveCart();
}


// --------------------------------------------------
// SAVE CART
// --------------------------------------------------

function saveCart() {

    try {

        localStorage.setItem(
            CART_STORAGE_KEY,
            JSON.stringify(cart)
        );

    } catch (error) {

        console.error("Cart save error:", error);
    }
}


// --------------------------------------------------
// FIND PRODUCT IN CART
// --------------------------------------------------

function findProduct(id, size = null, color = null) {

    return cart.find(item => {

        return (

            Number(item.id) === Number(id) &&

            (item.size || null) === (size || null) &&

            (item.color || null) === (color || null)
        );
    });
}


// --------------------------------------------------
// CART COUNT
// --------------------------------------------------

function updateCartCount() {

    const counter = document.getElementById("cart-count");

    if (!counter) {
        return;
    }

    let total = 0;

    cart.forEach(item => {
        total += Number(item.quantity) || 0;
    });

    counter.textContent = total;

    // Also update bottom nav badge
    updateBottomNavBadges();
}


// --------------------------------------------------
// SELECTED SIZE
// --------------------------------------------------

function getSelectedSize() {

    const activeSize = document.querySelector(
        ".size-options button.active, .size-btn-nb.active"
    );

    if (!activeSize) {
        return null;
    }

    return activeSize.textContent.trim() || activeSize.dataset.size || null;
}


// --------------------------------------------------
// SELECTED COLOR
// --------------------------------------------------

function getSelectedColor() {

    const activeColor = document.querySelector(
        ".color-options .color.active, .color-options-nb .color-nb.active"
    );

    if (!activeColor) {
        return null;
    }

    if (activeColor.dataset.color) {
        return activeColor.dataset.color;
    }

    if (activeColor.classList.contains("black")) {
        return "Black";
    }

    if (activeColor.classList.contains("white")) {
        return "White";
    }

    if (activeColor.classList.contains("blue")) {
        return "Blue";
    }

    if (activeColor.classList.contains("red")) {
        return "Red";
    }

    return null;
}


// --------------------------------------------------
// ADD TO CART
// --------------------------------------------------

function addToCart(button) {

    if (!button) {
        return;
    }

    const id = Number(button.dataset.id);
    const name = button.dataset.name || "Product";
    const price = Number(button.dataset.price) || 0;
    const image = button.dataset.image || "";

    if (!id) {
        showToast("Unable to add this product to cart.", "error");
        return;
    }

    // Quantity
    const quantityInput = document.getElementById("quantity");

    let quantity = quantityInput
        ? Number(quantityInput.value)
        : 1;

    if (!Number.isInteger(quantity) || quantity < 1) {
        quantity = 1;
    }

    if (quantity > 10) {
        quantity = 10;
    }

    // Size
    const size = getSelectedSize();

    // Color
    const color = getSelectedColor();

    // Existing product
    const existing = findProduct(id, size, color);

    if (existing) {

        existing.quantity = Number(existing.quantity) + quantity;

        if (existing.quantity > 10) {
            existing.quantity = 10;
        }

    } else {

        cart.push({
            id: id,
            name: name,
            price: price,
            image: image,
            quantity: quantity,
            size: size,
            color: color
        });
    }

    saveCart();
    updateCartCount();

    let message = `${name} added to cart!`;

    if (size) {
        message += ` (Size: ${size})`;
    }

    if (color) {
        message += ` (Color: ${color})`;
    }

    showToast(message);
}


// --------------------------------------------------
// REGISTER CART BUTTONS
// --------------------------------------------------

function registerCartButtons() {

    document.addEventListener("click", function(event) {

        const button = event.target.closest(".add-cart");

        if (!button) return;

        event.preventDefault();
        event.stopPropagation();

        addToCart(button);

    });
}


// --------------------------------------------------
// DISPLAY CART
// --------------------------------------------------

function displayCart() {

    const cartContainer = document.getElementById("cart-items");
    const totalElement = document.getElementById("grand-total");

    if (!cartContainer) {
        return;
    }

    cartContainer.innerHTML = "";

    // Empty cart
    if (cart.length === 0) {

        cartContainer.innerHTML = `

            <div class="empty-cart-nb">

                <div class="empty-cart-icon-nb">
                    <i class="fa-solid fa-cart-shopping"></i>
                </div>

                <h2>Your Cart is Empty</h2>

                <p>
                    Add some products to continue shopping.
                </p>

                <a href="/#products" class="empty-cart-btn-nb">
                    <i class="fa-solid fa-bag-shopping"></i>
                    Continue Shopping
                </a>

            </div>
        `;

        if (totalElement) totalElement.textContent = "0";

        updateCartSummaryNB(0, 0);

        updateCartCount();

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

        const imageUrl = getImageUrl(item.image);

        let variantHTML = "";

        if (item.size) {
            variantHTML += `
                <span>
                    Size:
                    <strong>${escapeHTML(item.size)}</strong>
                </span>
            `;
        }

        if (item.color) {
            variantHTML += `
                <span>
                    Color:
                    <strong>${escapeHTML(item.color)}</strong>
                </span>
            `;
        }

        const cartItem = document.createElement("div");

        cartItem.className = "cart-item";
        cartItem.dataset.index = index;

        cartItem.innerHTML = `

            <div class="cart-product">

                <img
                    src="${escapeHTML(imageUrl)}"
                    alt="${escapeHTML(item.name)}"
                >

                <div class="cart-info">

                    <h3>
                        ${escapeHTML(item.name)}
                    </h3>

                    <p class="cart-price">
                        ₹${price.toLocaleString("en-IN")}
                    </p>

                    ${
                        variantHTML
                            ? `
                                <div class="cart-variants">
                                    ${variantHTML}
                                </div>
                              `
                            : ""
                    }

                </div>

            </div>


            <div class="cart-quantity">

                <button
                    type="button"
                    class="quantity-decrease"
                    data-index="${index}"
                >
                    −
                </button>

                <span>
                    ${quantity}
                </span>

                <button
                    type="button"
                    class="quantity-increase"
                    data-index="${index}"
                >
                    +
                </button>

            </div>


            <div class="cart-subtotal">

                ₹${subtotal.toLocaleString("en-IN")}

            </div>


            <button
                type="button"
                class="remove-btn"
                data-index="${index}"
            >

                <i class="fa-solid fa-trash"></i>

                Remove

            </button>
        `;

        cartContainer.appendChild(cartItem);
    });

    if (totalElement) {
        totalElement.textContent = grandTotal.toLocaleString("en-IN");
    }

    updateCartSummaryNB(grandTotal, totalQty);

    registerCartActions();
}


// --------------------------------------------------
// UPDATE CART SUMMARY (Nobero Style)
// --------------------------------------------------

function updateCartSummaryNB(subtotal, qty) {

    const subtotalEl = document.getElementById("subtotal-nb");
    if (subtotalEl) {
        subtotalEl.textContent = subtotal.toLocaleString("en-IN");
    }

    const countEl = document.getElementById("cart-items-count-nb");
    if (countEl) {
        countEl.textContent = `(${qty})`;
    }

    if (typeof window.updateShippingBar === "function") {
        window.updateShippingBar(subtotal);
    }
}


// --------------------------------------------------
// CART ACTIONS
// --------------------------------------------------

function registerCartActions() {

    const cartContainer = document.getElementById("cart-items");

    if (!cartContainer) {
        return;
    }

    cartContainer.querySelectorAll(".remove-btn").forEach(button => {

        button.addEventListener("click", function(event) {

            event.preventDefault();

            const index = Number(this.dataset.index);

            removeItemByIndex(index);
        });
    });

    cartContainer.querySelectorAll(".quantity-decrease").forEach(button => {

        button.addEventListener("click", function(event) {

            event.preventDefault();

            const index = Number(this.dataset.index);

            changeQuantityByIndex(index, -1);
        });
    });

    cartContainer.querySelectorAll(".quantity-increase").forEach(button => {

        button.addEventListener("click", function(event) {

            event.preventDefault();

            const index = Number(this.dataset.index);

            changeQuantityByIndex(index, 1);
        });
    });
}


// --------------------------------------------------
// CHANGE QUANTITY BY INDEX
// --------------------------------------------------

function changeQuantityByIndex(index, change) {

    if (index < 0 || index >= cart.length) {
        return;
    }

    const product = cart[index];

    let newQuantity = Number(product.quantity) + Number(change);

    if (newQuantity <= 0) {
        removeItemByIndex(index);
        return;
    }

    if (newQuantity > 10) {
        newQuantity = 10;
    }

    product.quantity = newQuantity;

    saveCart();
    updateCartCount();
    displayCart();
}


// --------------------------------------------------
// REMOVE CART ITEM BY INDEX
// --------------------------------------------------

function removeItemByIndex(index) {

    if (index < 0 || index >= cart.length) {
        return;
    }

    cart.splice(index, 1);

    saveCart();
    updateCartCount();
    displayCart();
}


// ==================================================
// PRODUCT PAGE
// ==================================================

function changeImage(element) {

    const mainImage = document.getElementById("main-image");

    if (!mainImage || !element) {
        return;
    }

    const newSrc = element.dataset && element.dataset.img
        ? element.dataset.img
        : (element.querySelector && element.querySelector("img")
            ? element.querySelector("img").src
            : element.src);

    if (newSrc) {
        mainImage.src = newSrc;
    }

    document.querySelectorAll(".thumbnail, .thumb-nb").forEach(img => {
        img.classList.remove("active");
    });

    element.classList.add("active");
}


function registerSizeButtons() {

    const buttons = document.querySelectorAll(
        ".size-options button, .size-btn-nb"
    );

    buttons.forEach(button => {

        button.addEventListener("click", function(event) {

            event.preventDefault();

            buttons.forEach(btn => {
                btn.classList.remove("active");
            });

            this.classList.add("active");

            const label = document.getElementById("selected-size-nb");
            if (label && this.dataset.size) {
                label.textContent = this.dataset.size;
            }
        });
    });
}


function registerColorButtons() {

    const colors = document.querySelectorAll(
        ".color-options .color, .color-options-nb .color-nb"
    );

    colors.forEach(color => {

        color.addEventListener("click", function(event) {

            event.preventDefault();

            colors.forEach(c => {
                c.classList.remove("active");
            });

            this.classList.add("active");

            const label = document.getElementById("selected-color-nb");
            if (label && this.dataset.color) {
                label.textContent = this.dataset.color;
            }
        });
    });
}


// ==================================================
// WISHLIST SYSTEM
// ==================================================

function loadWishlist() {

    try {

        const savedWishlist = localStorage.getItem(WISHLIST_STORAGE_KEY);

        if (!savedWishlist) {
            wishlist = [];
            return;
        }

        const parsedWishlist = JSON.parse(savedWishlist);

        if (Array.isArray(parsedWishlist)) {
            wishlist = parsedWishlist;
        } else {
            wishlist = [];
        }

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

        if (!item || item.id === undefined || item.id === null) {
            return;
        }

        const id = Number(item.id);

        if (!id) {
            return;
        }

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

        localStorage.setItem(
            WISHLIST_STORAGE_KEY,
            JSON.stringify(wishlist)
        );

    } catch (error) {

        console.error("Wishlist save error:", error);
    }
}


function isInWishlist(id) {

    return wishlist.some(item => {
        return Number(item.id) === Number(id);
    });
}


function updateWishlistCount() {

    const counters = document.querySelectorAll("#wishlist-count, #wishlist-count-nb");

    counters.forEach(counter => {
        counter.textContent = wishlist.length;
    });

    // Also update bottom nav badge
    updateBottomNavBadges();
}


function getWishlistProductData(button) {

    if (!button) {
        return null;
    }

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

            if (!id) {
                id = Number(cartButton.dataset.id);
            }

            if (!name) {
                name = cartButton.dataset.name || "";
            }

            if (!price) {
                price = Number(cartButton.dataset.price) || 0;
            }

            if (!image) {
                image = cartButton.dataset.image || "";
            }
        }

        if (!oldPrice) {
            const oldPriceElement = card.querySelector(".price span, .product-price-nb span");
            if (oldPriceElement) {
                oldPrice = Number(oldPriceElement.textContent.replace(/[^\d]/g, "")) || 0;
            }
        }

        if (!rating) {
            const ratingElement = card.querySelector(".rating, .product-rating-nb");
            if (ratingElement) {
                rating = ratingElement.textContent.trim();
            }
        }
    }

    if (!id) {
        return null;
    }

    return {
        id: id,
        name: name || "Product",
        price: price,
        old_price: oldPrice,
        image: image,
        rating: rating,
        description: description
    };
}


function toggleWishlist(button) {

    if (!button) {
        return;
    }

    const product = getWishlistProductData(button);

    if (!product) {
        showToast("Unable to add this product to wishlist.", "error");
        return;
    }

    const existingIndex = wishlist.findIndex(item => {
        return Number(item.id) === Number(product.id);
    });

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

        if (!product) {
            return;
        }

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

    wishlist = wishlist.filter(item => {
        return Number(item.id) !== numericId;
    });

    saveWishlist();
    updateWishlistCount();
    updateWishlistButtons();

    if (document.getElementById("wishlist-items")) {
        displayWishlist();
    }

    showToast("Removed from wishlist");
}


function clearWishlist() {

    if (wishlist.length === 0) {
        return;
    }

    const confirmed = confirm(
        "Are you sure you want to remove all wishlist items?"
    );

    if (!confirmed) {
        return;
    }

    wishlist = [];

    saveWishlist();
    updateWishlistCount();
    updateWishlistButtons();
    displayWishlist();

    showToast("Wishlist cleared");
}


function addWishlistItemToCart(id) {

    const product = wishlist.find(item => {
        return Number(item.id) === Number(id);
    });

    if (!product) {
        return;
    }

    const existing = findProduct(product.id, null, null);

    if (existing) {

        existing.quantity = Number(existing.quantity) + 1;

        if (existing.quantity > 10) {
            existing.quantity = 10;
        }

    } else {

        cart.push({
            id: product.id,
            name: product.name,
            price: product.price,
            image: product.image,
            quantity: 1,
            size: null,
            color: null
        });
    }

    saveCart();
    updateCartCount();

    showToast(`${product.name} added to cart!`);
}


// ==================================================
// WISHLIST PAGE (NOBERO STYLE)
// ==================================================

function displayWishlist() {

    const container = document.getElementById("wishlist-items");
    const emptyState = document.getElementById("wishlist-empty");
    const clearButton = document.getElementById("clear-wishlist");

    if (!container) {
        return;
    }

    container.innerHTML = "";

    if (wishlist.length === 0) {

        if (emptyState) {
            emptyState.style.display = "block";
        } else {

            container.innerHTML = `

                <div class="empty-wishlist">

                    <div class="empty-wishlist-icon">
                        ❤️
                    </div>

                    <h2>Your Wishlist is Empty</h2>

                    <p>
                        Save your favorite products here
                        and come back later.
                    </p>

                    <a href="/#products" class="continue-shopping">
                        Continue Shopping
                    </a>

                </div>
            `;
        }

        if (clearButton) {
            clearButton.style.display = "none";
        }

        updateWishlistCount();

        return;
    }

    if (emptyState) {
        emptyState.style.display = "none";
    }

    if (clearButton) {
        clearButton.style.display = "inline-flex";
    }

    wishlist.forEach(product => {

        const item = document.createElement("div");

        item.className = "wishlist-card-nb";
        item.dataset.id = product.id;

        const imageUrl = getImageUrl(product.image);

        item.innerHTML = `

            <a href="/product/${Number(product.id)}" class="wishlist-img-wrap-nb">

                <img
                    src="${escapeHTML(imageUrl)}"
                    alt="${escapeHTML(product.name)}"
                >

            </a>

            <button
                type="button"
                class="wishlist-remove-nb"
                data-id="${Number(product.id)}"
                aria-label="Remove from wishlist"
            >
                <i class="fa-solid fa-xmark"></i>
            </button>

            <div class="wishlist-info-nb">

                <span class="wishlist-cat-nb">Wishlist</span>

                <h3 class="wishlist-name-nb">
                    <a href="/product/${Number(product.id)}">
                        ${escapeHTML(product.name)}
                    </a>
                </h3>

                ${
                    product.rating
                        ? `
                            <div class="wishlist-rating-nb">
                                <i class="fa-solid fa-star"></i>
                                ${escapeHTML(product.rating)}
                            </div>
                          `
                        : ""
                }

                <p class="wishlist-price-nb">
                    ₹${Number(product.price).toLocaleString("en-IN")}
                    ${
                        product.old_price
                            ? `<del>₹${Number(product.old_price).toLocaleString("en-IN")}</del>`
                            : ""
                    }
                </p>

                <div class="wishlist-actions-nb">

                    <button
                        type="button"
                        class="wishlist-add-cart-nb"
                        data-id="${Number(product.id)}"
                    >
                        <i class="fa-solid fa-cart-plus"></i>
                        Add to Cart
                    </button>

                    <button
                        type="button"
                        class="wishlist-remove-btn-nb"
                        data-id="${Number(product.id)}"
                        aria-label="Remove"
                    >
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

    if (!container) {
        return;
    }

    container.querySelectorAll(".wishlist-add-cart-nb").forEach(button => {

        button.addEventListener("click", function(event) {

            event.preventDefault();
            event.stopPropagation();

            const id = Number(this.dataset.id);

            addWishlistItemToCart(id);
        });
    });

    container.querySelectorAll(".wishlist-remove-btn-nb, .wishlist-remove-nb").forEach(button => {

        button.addEventListener("click", function(event) {

            event.preventDefault();
            event.stopPropagation();

            const id = Number(this.dataset.id);

            removeFromWishlist(id);
        });
    });
}


// ==================================================
// MOBILE DRAWER
// ==================================================

function openDrawer() {

    const drawer = document.getElementById("mobile-drawer");
    const overlay = document.getElementById("drawer-overlay");

    if (drawer) {
        drawer.classList.add("open");
    }

    if (overlay) {
        overlay.classList.add("show");
    }

    document.body.style.overflow = "hidden";
    document.body.classList.add("drawer-open");
}


function closeDrawer() {

    const drawer = document.getElementById("mobile-drawer");
    const overlay = document.getElementById("drawer-overlay");

    if (drawer) {
        drawer.classList.remove("open");
    }

    if (overlay) {
        overlay.classList.remove("show");
    }

    document.body.style.overflow = "";
    document.body.classList.remove("drawer-open");
}


function registerDrawer() {

    const hamburgerBtn = document.getElementById("hamburger-btn");
    const drawerClose = document.getElementById("drawer-close");
    const drawerOverlay = document.getElementById("drawer-overlay");

    if (hamburgerBtn) {
        hamburgerBtn.addEventListener("click", function(e) {
            e.preventDefault();
            openDrawer();
        });
    }

    if (drawerClose) {
        drawerClose.addEventListener("click", closeDrawer);
    }

    if (drawerOverlay) {
        drawerOverlay.addEventListener("click", closeDrawer);
    }

    // Close drawer on link click
    const drawerLinks = document.querySelectorAll(".drawer-nav a");
    drawerLinks.forEach(link => {
        link.addEventListener("click", function() {
            setTimeout(closeDrawer, 150);
        });
    });

    // Close on Escape key
    document.addEventListener("keydown", function(e) {
        if (e.key === "Escape") {
            closeDrawer();
        }
    });
}


// ==================================================
// BOTTOM NAV — ACTIVE STATE + BADGES
// ==================================================

function registerBottomNav() {

    const currentPath = window.location.pathname;
    const bottomNavItems = document.querySelectorAll(".bottom-nav-item");

    bottomNavItems.forEach(item => {
        item.classList.remove("active");
    });

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
// BOTTOM NAV BADGES — Sync with Cart/Wishlist
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
        if (cartCount > 0) {
            bottomCartBadge.classList.add('show');
        } else {
            bottomCartBadge.classList.remove('show');
        }
    }

    if (bottomWishlistBadge) {
        bottomWishlistBadge.textContent = wishlistCount;
        if (wishlistCount > 0) {
            bottomWishlistBadge.classList.add('show');
        } else {
            bottomWishlistBadge.classList.remove('show');
        }
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
        setTimeout(function() {
            if (searchInput) searchInput.focus();
        }, 300);
    }

    function closeSearch() {
        if (!searchOverlay) return;
        searchOverlay.classList.remove('show');
        document.body.style.overflow = '';
        if (searchInput) searchInput.value = '';
    }

    if (searchBtn) {
        searchBtn.addEventListener('click', openSearch);
    }

    if (searchClose) {
        searchClose.addEventListener('click', closeSearch);
    }

    if (searchOverlay) {
        searchOverlay.addEventListener('click', function(e) {
            if (e.target === searchOverlay) {
                closeSearch();
            }
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
// INITIALIZE
// ==================================================

document.addEventListener("DOMContentLoaded", function() {

    // Load storage
    loadCart();
    loadWishlist();

    // Register buttons
    registerCartButtons();
    registerWishlistButtons();
    registerSizeButtons();
    registerColorButtons();

    // Mobile drawer + bottom nav
    registerDrawer();
    registerBottomNav();

    // Search overlay
    registerSearch();

    // Header scroll shadow
    registerHeaderScroll();

    // Update counters
    updateCartCount();
    updateWishlistCount();

    // Update wishlist hearts
    updateWishlistButtons();

    // Display cart if cart page
    displayCart();

    // Display wishlist if wishlist page
    displayWishlist();

    // Clear wishlist button
    const clearButton = document.getElementById("clear-wishlist");

    if (clearButton) {
        clearButton.addEventListener("click", clearWishlist);
    }
});
