// ==================================================
// UrbanWear JavaScript v9.0
// CART + PERSISTENT WISHLIST
// ==================================================

"use strict";


// ==================================================
// GLOBAL DATA
// ==================================================

let cart = [];
let wishlist = [];

const CART_STORAGE_KEY = "cart";
const WISHLIST_STORAGE_KEY = "urbanwear_wishlist";


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
// CART SYSTEM
// ==================================================

// --------------------------------------------------
// LOAD CART
// --------------------------------------------------

function loadCart() {

    try {

        const savedCart =
            localStorage.getItem(CART_STORAGE_KEY);

        if (!savedCart) {
            cart = [];
            return;
        }

        const parsedCart =
            JSON.parse(savedCart);

        if (Array.isArray(parsedCart)) {
            cart = parsedCart;
        } else {
            cart = [];
        }

    } catch (error) {

        console.error(
            "Cart loading error:",
            error
        );

        cart = [];

        localStorage.removeItem(
            CART_STORAGE_KEY
        );
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

            let quantity =
                Number(item.quantity);

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

                name:
                    item.name ||
                    "Product",

                price:
                    Number(item.price) || 0,

                image:
                    item.image ||
                    "",

                quantity:
                    quantity,

                size:
                    item.size || null,

                color:
                    item.color || null
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

        console.error(
            "Cart save error:",
            error
        );
    }
}


// --------------------------------------------------
// FIND PRODUCT IN CART
// --------------------------------------------------

function findProduct(
    id,
    size = null,
    color = null
) {

    return cart.find(item => {

        return (

            Number(item.id) === Number(id) &&

            (item.size || null) ===
            (size || null) &&

            (item.color || null) ===
            (color || null)
        );
    });
}


// --------------------------------------------------
// CART COUNT
// --------------------------------------------------

function updateCartCount() {

    const counter =
        document.getElementById("cart-count");

    if (!counter) {
        return;
    }

    let total = 0;

    cart.forEach(item => {

        total +=
            Number(item.quantity) || 0;
    });

    counter.textContent = total;
}


// --------------------------------------------------
// SELECTED SIZE
// --------------------------------------------------

function getSelectedSize() {

    const activeSize =
        document.querySelector(
            ".size-options button.active"
        );

    if (!activeSize) {
        return null;
    }

    return activeSize.textContent.trim();
}


// --------------------------------------------------
// SELECTED COLOR
// --------------------------------------------------

function getSelectedColor() {

    const activeColor =
        document.querySelector(
            ".color-options .color.active"
        );

    if (!activeColor) {
        return null;
    }

    if (activeColor.dataset.color) {

        return activeColor.dataset.color;
    }

    if (
        activeColor.classList.contains("black")
    ) {
        return "Black";
    }

    if (
        activeColor.classList.contains("white")
    ) {
        return "White";
    }

    if (
        activeColor.classList.contains("blue")
    ) {
        return "Blue";
    }

    if (
        activeColor.classList.contains("red")
    ) {
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

    const id =
        Number(button.dataset.id);

    const name =
        button.dataset.name ||
        "Product";

    const price =
        Number(button.dataset.price) || 0;

    const image =
        button.dataset.image || "";

    if (!id) {

        alert(
            "Unable to add this product to cart."
        );

        return;
    }


    // Quantity

    const quantityInput =
        document.getElementById("quantity");

    let quantity =
        quantityInput
            ? Number(quantityInput.value)
            : 1;

    if (
        !Number.isInteger(quantity) ||
        quantity < 1
    ) {
        quantity = 1;
    }

    if (quantity > 10) {
        quantity = 10;
    }


    // Size

    const size =
        getSelectedSize();


    // Color

    const color =
        getSelectedColor();


    // Existing product

    const existing =
        findProduct(
            id,
            size,
            color
        );


    if (existing) {

        existing.quantity =
            Number(existing.quantity) +
            quantity;

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


    let message =
        `${name} added to cart!`;

    if (size) {
        message += `\nSize: ${size}`;
    }

    if (color) {
        message += `\nColor: ${color}`;
    }

    alert(message);
}


// --------------------------------------------------
// REGISTER CART BUTTONS
// --------------------------------------------------

function registerCartButtons() {

    const buttons =
        document.querySelectorAll(
            ".add-cart"
        );

    buttons.forEach(button => {

        if (
            button.dataset.cartRegistered ===
            "true"
        ) {
            return;
        }

        button.dataset.cartRegistered =
            "true";

        button.addEventListener(
            "click",
            function(event) {

                event.preventDefault();
                event.stopPropagation();

                addToCart(this);
            }
        );
    });
}


// --------------------------------------------------
// DISPLAY CART
// --------------------------------------------------

function displayCart() {

    const cartContainer =
        document.getElementById(
            "cart-items"
        );

    const totalElement =
        document.getElementById(
            "grand-total"
        );

    if (
        !cartContainer ||
        !totalElement
    ) {
        return;
    }


    cartContainer.innerHTML = "";


    // Empty cart

    if (cart.length === 0) {

        cartContainer.innerHTML = `

            <div class="empty-cart">

                <div class="empty-cart-icon">
                    🛒
                </div>

                <h2>
                    Your Cart is Empty
                </h2>

                <p>
                    Add some products to continue shopping.
                </p>

                <a
                    href="/#products"
                    class="continue-shopping"
                >
                    Continue Shopping
                </a>

            </div>
        `;

        totalElement.textContent = "0";

        updateCartCount();

        return;
    }


    let grandTotal = 0;


    cart.forEach((item, index) => {

        const price =
            Number(item.price) || 0;

        const quantity =
            Number(item.quantity) || 1;

        const subtotal =
            price * quantity;

        grandTotal += subtotal;


        const imageUrl =
            getImageUrl(item.image);


        let variantHTML = "";


        if (item.size) {

            variantHTML += `

                <span>
                    Size:
                    <strong>
                        ${escapeHTML(item.size)}
                    </strong>
                </span>
            `;
        }


        if (item.color) {

            variantHTML += `

                <span>
                    Color:
                    <strong>
                        ${escapeHTML(item.color)}
                    </strong>
                </span>
            `;
        }


        const cartItem =
            document.createElement("div");

        cartItem.className =
            "cart-item";

        cartItem.dataset.index =
            index;


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


    totalElement.textContent =
        grandTotal.toLocaleString("en-IN");


    registerCartActions();
}


// --------------------------------------------------
// CART ACTIONS
// --------------------------------------------------

function registerCartActions() {

    const cartContainer =
        document.getElementById(
            "cart-items"
        );

    if (!cartContainer) {
        return;
    }


    // Remove

    cartContainer
        .querySelectorAll(".remove-btn")
        .forEach(button => {

            button.addEventListener(
                "click",
                function(event) {

                    event.preventDefault();

                    const index =
                        Number(
                            this.dataset.index
                        );

                    removeItemByIndex(index);
                }
            );
        });


    // Decrease

    cartContainer
        .querySelectorAll(
            ".quantity-decrease"
        )
        .forEach(button => {

            button.addEventListener(
                "click",
                function(event) {

                    event.preventDefault();

                    const index =
                        Number(
                            this.dataset.index
                        );

                    changeQuantityByIndex(
                        index,
                        -1
                    );
                }
            );
        });


    // Increase

    cartContainer
        .querySelectorAll(
            ".quantity-increase"
        )
        .forEach(button => {

            button.addEventListener(
                "click",
                function(event) {

                    event.preventDefault();

                    const index =
                        Number(
                            this.dataset.index
                        );

                    changeQuantityByIndex(
                        index,
                        1
                    );
                }
            );
        });
}


// --------------------------------------------------
// CHANGE QUANTITY
// --------------------------------------------------

function changeQuantityByIndex(
    index,
    change
) {

    if (
        index < 0 ||
        index >= cart.length
    ) {
        return;
    }

    const product =
        cart[index];

    let newQuantity =
        Number(product.quantity) +
        Number(change);


    if (newQuantity <= 0) {

        removeItemByIndex(index);

        return;
    }


    if (newQuantity > 10) {
        newQuantity = 10;
    }


    product.quantity =
        newQuantity;


    saveCart();

    updateCartCount();

    displayCart();
}


// --------------------------------------------------
// CHANGE QUANTITY BY PRODUCT
// --------------------------------------------------

function changeQuantity(
    id,
    change,
    size = null,
    color = null
) {

    const index =
        cart.findIndex(item => {

            return (

                Number(item.id) ===
                Number(id) &&

                (item.size || null) ===
                (size || null) &&

                (item.color || null) ===
                (color || null)
            );
        });


    if (index === -1) {
        return;
    }


    changeQuantityByIndex(
        index,
        change
    );
}


// --------------------------------------------------
// REMOVE CART ITEM
// --------------------------------------------------

function removeItemByIndex(index) {

    if (
        index < 0 ||
        index >= cart.length
    ) {
        return;
    }


    cart.splice(index, 1);


    saveCart();

    updateCartCount();

    displayCart();
}


// --------------------------------------------------
// REMOVE CART ITEM BY ID
// --------------------------------------------------

function removeItem(
    id,
    size = null,
    color = null
) {

    const index =
        cart.findIndex(item => {

            return (

                Number(item.id) ===
                Number(id) &&

                (item.size || null) ===
                (size || null) &&

                (item.color || null) ===
                (color || null)
            );
        });


    if (index === -1) {
        return;
    }


    removeItemByIndex(index);
}


// ==================================================
// PRODUCT PAGE
// ==================================================

// --------------------------------------------------
// IMAGE GALLERY
// --------------------------------------------------

function changeImage(element) {

    const mainImage =
        document.getElementById(
            "main-image"
        );

    if (
        !mainImage ||
        !element
    ) {
        return;
    }


    mainImage.src =
        element.src;


    document
        .querySelectorAll(".thumbnail")
        .forEach(img => {

            img.classList.remove(
                "active"
            );
        });


    element.classList.add(
        "active"
    );
}


// --------------------------------------------------
// SIZE BUTTONS
// --------------------------------------------------

function registerSizeButtons() {

    const buttons =
        document.querySelectorAll(
            ".size-options button"
        );


    buttons.forEach(button => {

        button.addEventListener(
            "click",
            function(event) {

                event.preventDefault();

                buttons.forEach(btn => {

                    btn.classList.remove(
                        "active"
                    );
                });

                this.classList.add(
                    "active"
                );
            }
        );
    });
}


// --------------------------------------------------
// COLOR BUTTONS
// --------------------------------------------------

function registerColorButtons() {

    const colors =
        document.querySelectorAll(
            ".color-options .color"
        );


    colors.forEach(color => {

        color.addEventListener(
            "click",
            function(event) {

                event.preventDefault();

                colors.forEach(c => {

                    c.classList.remove(
                        "active"
                    );
                });

                this.classList.add(
                    "active"
                );
            }
        );
    });
}


// ==================================================
// WISHLIST SYSTEM
// ==================================================

// --------------------------------------------------
// LOAD WISHLIST
// --------------------------------------------------

function loadWishlist() {

    try {

        const savedWishlist =
            localStorage.getItem(
                WISHLIST_STORAGE_KEY
            );


        if (!savedWishlist) {

            wishlist = [];

            return;
        }


        const parsedWishlist =
            JSON.parse(savedWishlist);


        if (Array.isArray(parsedWishlist)) {

            wishlist =
                parsedWishlist;

        } else {

            wishlist = [];
        }

    } catch (error) {

        console.error(
            "Wishlist loading error:",
            error
        );

        wishlist = [];

        localStorage.removeItem(
            WISHLIST_STORAGE_KEY
        );
    }


    normalizeWishlist();
}


// --------------------------------------------------
// NORMALIZE WISHLIST
// --------------------------------------------------

function normalizeWishlist() {

    const uniqueProducts =
        new Map();


    wishlist.forEach(item => {

        if (
            !item ||
            item.id === undefined ||
            item.id === null
        ) {
            return;
        }


        const id =
            Number(item.id);


        if (!id) {
            return;
        }


        if (
            !uniqueProducts.has(id)
        ) {

            uniqueProducts.set(
                id,
                {

                    id: id,

                    name:
                        item.name ||
                        "Product",

                    price:
                        Number(item.price) ||
                        0,

                    old_price:
                        Number(item.old_price) ||
                        0,

                    image:
                        item.image ||
                        "",

                    rating:
                        item.rating ||
                        "",

                    description:
                        item.description ||
                        ""
                }
            );
        }
    });


    wishlist =
        Array.from(
            uniqueProducts.values()
        );
}


// --------------------------------------------------
// SAVE WISHLIST
// --------------------------------------------------

function saveWishlist() {

    try {

        localStorage.setItem(
            WISHLIST_STORAGE_KEY,
            JSON.stringify(wishlist)
        );

    } catch (error) {

        console.error(
            "Wishlist save error:",
            error
        );
    }
}


// --------------------------------------------------
// CHECK WISHLIST
// --------------------------------------------------

function isInWishlist(id) {

    return wishlist.some(item => {

        return Number(item.id) ===
            Number(id);
    });
}


// --------------------------------------------------
// WISHLIST COUNT
// --------------------------------------------------

function updateWishlistCount() {

    const counters =
        document.querySelectorAll(
            "#wishlist-count"
        );


    counters.forEach(counter => {

        counter.textContent =
            wishlist.length;
    });
}


// --------------------------------------------------
// GET WISHLIST PRODUCT DATA
// --------------------------------------------------

function getWishlistProductData(button) {

    if (!button) {
        return null;
    }


    const card =
        button.closest(".card");


    let id =
        Number(button.dataset.id);


    let name =
        button.dataset.name || "";


    let price =
        Number(button.dataset.price) || 0;


    let oldPrice =
        Number(button.dataset.oldPrice) || 0;


    let image =
        button.dataset.image || "";


    let rating =
        button.dataset.rating || "";


    let description =
        button.dataset.description || "";


    // ------------------------------------------------
    // GET DATA FROM CARD
    // ------------------------------------------------

    if (card) {

        const cartButton =
            card.querySelector(".add-cart");


        if (cartButton) {

            if (!id) {

                id =
                    Number(
                        cartButton.dataset.id
                    );
            }


            if (!name) {

                name =
                    cartButton.dataset.name ||
                    "";
            }


            if (!price) {

                price =
                    Number(
                        cartButton.dataset.price
                    ) || 0;
            }


            if (!image) {

                image =
                    cartButton.dataset.image ||
                    "";
            }
        }


        const oldPriceElement =
            card.querySelector(
                ".price span"
            );


        if (
            oldPriceElement &&
            !oldPrice
        ) {

            oldPrice =
                Number(
                    oldPriceElement.textContent
                        .replace(/[^\d]/g, "")
                ) || 0;
        }


        const ratingElement =
            card.querySelector(".rating");


        if (
            ratingElement &&
            !rating
        ) {

            rating =
                ratingElement.textContent.trim();
        }
    }


    if (!id) {
        return null;
    }


    return {

        id: id,

        name:
            name ||
            "Product",

        price:
            price,

        old_price:
            oldPrice,

        image:
            image,

        rating:
            rating,

        description:
            description
    };
}


// --------------------------------------------------
// TOGGLE WISHLIST
// --------------------------------------------------

function toggleWishlist(button) {

    if (!button) {
        return;
    }


    const product =
        getWishlistProductData(button);


    if (!product) {

        alert(
            "Unable to add this product to wishlist."
        );

        return;
    }


    const existingIndex =
        wishlist.findIndex(item => {

            return Number(item.id) ===
                Number(product.id);
        });


    // ------------------------------------------------
    // REMOVE
    // ------------------------------------------------

    if (existingIndex !== -1) {

        wishlist.splice(
            existingIndex,
            1
        );

        saveWishlist();

        updateWishlistCount();

        updateWishlistButtons();

        return;
    }


    // ------------------------------------------------
    // ADD
    // ------------------------------------------------

    wishlist.push(product);


    saveWishlist();

    updateWishlistCount();

    updateWishlistButtons();
}


// --------------------------------------------------
// UPDATE WISHLIST BUTTONS
// --------------------------------------------------

function updateWishlistButtons() {

    const buttons =
        document.querySelectorAll(
            ".wishlist-btn"
        );


    buttons.forEach(button => {

        const product =
            getWishlistProductData(button);


        if (!product) {
            return;
        }


        const active =
            isInWishlist(product.id);


        const icon =
            button.querySelector("i");


        if (active) {

            button.classList.add(
                "active"
            );


            button.setAttribute(
                "aria-label",
                "Remove from wishlist"
            );


            button.setAttribute(
                "title",
                "Remove from wishlist"
            );


            if (icon) {

                icon.classList.remove(
                    "fa-regular"
                );

                icon.classList.add(
                    "fa-solid"
                );
            }

        } else {

            button.classList.remove(
                "active"
            );


            button.setAttribute(
                "aria-label",
                "Add to wishlist"
            );


            button.setAttribute(
                "title",
                "Add to wishlist"
            );


            if (icon) {

                icon.classList.remove(
                    "fa-solid"
                );

                icon.classList.add(
                    "fa-regular"
                );
            }
        }
    });
}


// --------------------------------------------------
// REGISTER WISHLIST BUTTONS
// --------------------------------------------------

function registerWishlistButtons() {

    document.addEventListener("click", function(event) {

        const button = event.target.closest(".wishlist-btn");

        if (!button) return;

        event.preventDefault();
        event.stopPropagation();

        toggleWishlist(button);

    });

    updateWishlistButtons();
}


// --------------------------------------------------
// REMOVE FROM WISHLIST
// --------------------------------------------------

function removeFromWishlist(id) {

    const numericId =
        Number(id);


    wishlist =
        wishlist.filter(item => {

            return Number(item.id) !==
                numericId;
        });


    saveWishlist();

    updateWishlistCount();

    updateWishlistButtons();


    if (
        document.getElementById(
            "wishlist-items"
        )
    ) {

        displayWishlist();
    }
}


// --------------------------------------------------
// CLEAR WISHLIST
// --------------------------------------------------

function clearWishlist() {

    if (wishlist.length === 0) {
        return;
    }


    const confirmed =
        confirm(
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
}


// --------------------------------------------------
// ADD WISHLIST ITEM TO CART
// --------------------------------------------------

function addWishlistItemToCart(id) {

    const product =
        wishlist.find(item => {

            return Number(item.id) ===
                Number(id);
        });


    if (!product) {
        return;
    }


    const existing =
        findProduct(
            product.id,
            null,
            null
        );


    if (existing) {

        existing.quantity =
            Number(existing.quantity) + 1;


        if (existing.quantity > 10) {

            existing.quantity = 10;
        }

    } else {

        cart.push({

            id:
                product.id,

            name:
                product.name,

            price:
                product.price,

            image:
                product.image,

            quantity:
                1,

            size:
                null,

            color:
                null
        });
    }


    saveCart();

    updateCartCount();


    alert(
        `${product.name} added to cart!`
    );
}


// ==================================================
// WISHLIST PAGE
// ==================================================

// --------------------------------------------------
// DISPLAY WISHLIST
// --------------------------------------------------

function displayWishlist() {

    const container =
        document.getElementById(
            "wishlist-items"
        );


    const emptyState =
        document.getElementById(
            "wishlist-empty"
        );


    const clearButton =
        document.getElementById(
            "clear-wishlist"
        );


    if (!container) {
        return;
    }


    container.innerHTML = "";


    // ------------------------------------------------
    // EMPTY
    // ------------------------------------------------

    if (wishlist.length === 0) {

        if (emptyState) {

            emptyState.style.display =
                "block";

        } else {

            container.innerHTML = `

                <div class="empty-wishlist">

                    <div class="empty-wishlist-icon">
                        ❤️
                    </div>

                    <h2>
                        Your Wishlist is Empty
                    </h2>

                    <p>
                        Save your favorite products here
                        and come back later.
                    </p>

                    <a
                        href="/#products"
                        class="continue-shopping"
                    >
                        Continue Shopping
                    </a>

                </div>
            `;
        }


        if (clearButton) {

            clearButton.style.display =
                "none";
        }


        updateWishlistCount();

        return;
    }


    // ------------------------------------------------
    // SHOW WISHLIST
    // ------------------------------------------------

    if (emptyState) {

        emptyState.style.display =
            "none";
    }


    if (clearButton) {

        clearButton.style.display =
            "inline-flex";
    }


    // ------------------------------------------------
    // CREATE PRODUCTS
    // ------------------------------------------------

    wishlist.forEach(product => {

        const item =
            document.createElement("div");


        item.className =
            "wishlist-item";


        item.dataset.id =
            product.id;


        const imageUrl =
            getImageUrl(
                product.image
            );


        item.innerHTML = `

            <div class="wishlist-product">

                <a
                    href="/product/${Number(product.id)}"
                    class="wishlist-image-link"
                >

                    <img
                        src="${escapeHTML(imageUrl)}"
                        alt="${escapeHTML(product.name)}"
                    >

                </a>


                <div class="wishlist-info">

                    <h3>

                        <a
                            href="/product/${Number(product.id)}"
                        >
                            ${escapeHTML(product.name)}
                        </a>

                    </h3>


                    ${
                        product.rating
                            ? `
                                <div class="wishlist-rating">
                                    ⭐⭐⭐⭐⭐
                                    (${escapeHTML(product.rating)})
                                </div>
                              `
                            : ""
                    }


                    <p class="wishlist-price">

                        ₹${Number(product.price)
                            .toLocaleString("en-IN")}

                        ${
                            product.old_price
                                ? `
                                    <span>
                                        ₹${Number(product.old_price)
                                            .toLocaleString("en-IN")}
                                    </span>
                                  `
                                : ""
                        }

                    </p>

                </div>

            </div>


            <div class="wishlist-actions">

                <button
                    type="button"
                    class="wishlist-cart-btn"
                    data-id="${Number(product.id)}"
                >

                    <i class="fa-solid fa-cart-plus"></i>

                    Add To Cart

                </button>


                <button
                    type="button"
                    class="wishlist-remove-btn"
                    data-id="${Number(product.id)}"
                >

                    <i class="fa-solid fa-trash"></i>

                    Remove

                </button>

            </div>
        `;


        container.appendChild(item);
    });


    registerWishlistPageActions();
}


// --------------------------------------------------
// WISHLIST PAGE ACTIONS
// --------------------------------------------------

function registerWishlistPageActions() {

    const container =
        document.getElementById(
            "wishlist-items"
        );


    if (!container) {
        return;
    }


    // Add to cart

    container
        .querySelectorAll(
            ".wishlist-cart-btn"
        )
        .forEach(button => {

            button.addEventListener(
                "click",
                function(event) {

                    event.preventDefault();

                    event.stopPropagation();


                    const id =
                        Number(
                            this.dataset.id
                        );


                    addWishlistItemToCart(id);
                }
            );
        });


    // Remove

    container
        .querySelectorAll(
            ".wishlist-remove-btn"
        )
        .forEach(button => {

            button.addEventListener(
                "click",
                function(event) {

                    event.preventDefault();

                    event.stopPropagation();


                    const id =
                        Number(
                            this.dataset.id
                        );


                    removeFromWishlist(id);
                }
            );
        });
}


// ==================================================
// BUY NOW
// ==================================================

function registerBuyButton() {

    const button =
        document.querySelector(
            ".buy-btn"
        );


    if (!button) {
        return;
    }


    button.addEventListener(
        "click",
        function(event) {

            event.preventDefault();

            alert(
                "Checkout feature coming soon!"
            );
        }
    );
}


// ==================================================
// CHECKOUT
// ==================================================

function registerCheckoutButton() {

    const button =
        document.querySelector(
            ".checkout-btn"
        );


    if (!button) {
        return;
    }


    button.addEventListener(
        "click",
        function(event) {

            event.preventDefault();


            if (cart.length === 0) {

                alert(
                    "Your cart is empty."
                );

                return;
            }


            alert(
                "Checkout feature coming soon!"
            );
        }
    );
}


// ==================================================
// INITIALIZE
// ==================================================

document.addEventListener(
    "DOMContentLoaded",
    function() {


        // Load storage

        loadCart();

        loadWishlist();


        // Register buttons

        registerCartButtons();

        registerWishlistButtons();

        registerSizeButtons();

        registerColorButtons();

        registerBuyButton();

        registerCheckoutButton();


        // Update counters

        updateCartCount();

        updateWishlistCount();


        // Update wishlist hearts

        updateWishlistButtons();


        // Display cart if cart page

        displayCart();


        // Display wishlist if wishlist page

        displayWishlist();


        // Clear wishlist

        const clearButton =
            document.getElementById(
                "clear-wishlist"
            );


        if (clearButton) {

            clearButton.addEventListener(
                "click",
                clearWishlist
            );
        }
    }
);