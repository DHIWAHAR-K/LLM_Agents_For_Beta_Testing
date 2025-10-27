"""
Full-Featured E-commerce REST API for LLM Beta Testing.

Run with:
    uvicorn aut_service:app --reload --port 8000
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="Scamazon E-Commerce API", version="2.0.0")

# Mount static files
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Mount images directory
images_dir = Path(__file__).parent / "images"
if images_dir.exists():
    app.mount("/images", StaticFiles(directory=str(images_dir)), name="images")

# In-memory storage
_PRODUCTS: List[Dict] = []
_CARTS: Dict[str, List[Dict]] = {}  # session_id -> list of cart items
_ORDERS: List[Dict] = []
_REVIEWS: Dict[str, List[Dict]] = {}  # product_id -> list of reviews
_USERS: Dict[str, Dict] = {}  # email -> user data

# Pydantic models
class Product(BaseModel):
    name: str
    description: str
    price: float
    stock: int
    category: str = "general"

class CartItem(BaseModel):
    product_id: str
    quantity: int

class CheckoutRequest(BaseModel):
    session_id: str = "default"
    shipping_address: Optional[Dict[str, str]] = None
    payment_method: Optional[str] = None

class Review(BaseModel):
    rating: int
    title: str
    comment: str
    reviewer_name: str = "Anonymous"

class UserRegister(BaseModel):
    email: str
    password: str
    name: str

class UserLogin(BaseModel):
    email: str
    password: str


# Initialize comprehensive product catalog
def _init_product_catalog():
    global _PRODUCTS, _REVIEWS
    if not _PRODUCTS:
        products = [
            # ELECTRONICS (15 products)
            {
                "id": "prod_1",
                "name": "Premium Wireless Headphones",
                "description": "Noise-cancelling over-ear headphones with 30-hour battery life, premium sound quality, and comfortable design perfect for travel and work.",
                "price": 299.99,
                "stock": 45,
                "category": "Electronics",
                "rating": 4.5,
                "reviews_count": 1247,
                "image": "/images/product_1_wireless_bluetooth_headphones_with_noise_cancellat.jpg",
                "brand": "AudioTech",
                "specs": {"Battery": "30 hours", "Connectivity": "Bluetooth 5.0", "Weight": "250g"}
            },
            {
                "id": "prod_2",
                "name": "Smart Watch Pro",
                "description": "Advanced fitness tracker with heart rate monitor, GPS, sleep tracking, and 7-day battery life. Perfect for athletes and health enthusiasts.",
                "price": 399.99,
                "stock": 28,
                "category": "Electronics",
                "rating": 4.7,
                "reviews_count": 892,
                "image": "/images/product_2_smart_watch_fitness_tracker.jpg",
                "brand": "FitTech",
                "specs": {"Display": "1.4 inch AMOLED", "Battery": "7 days", "Water Resistant": "5ATM"}
            },
            {
                "id": "prod_3",
                "name": "Ultrabook Laptop 15\"",
                "description": "Powerful ultrabook with Intel i7 processor, 16GB RAM, 512GB SSD. Perfect for professionals and creators who need performance on the go.",
                "price": 1299.99,
                "stock": 15,
                "category": "Electronics",
                "rating": 4.8,
                "reviews_count": 543,
                "image": "/images/product_8_laptop_stand_aluminum_adjustable.jpg",
                "brand": "TechBook",
                "specs": {"Processor": "Intel i7", "RAM": "16GB", "Storage": "512GB SSD"}
            },
            {
                "id": "prod_4",
                "name": "4K Action Camera",
                "description": "Waterproof action camera with 4K video recording, image stabilization, and wide-angle lens. Perfect for adventure and sports.",
                "price": 349.99,
                "stock": 32,
                "category": "Electronics",
                "rating": 4.6,
                "reviews_count": 678,
                "image": "/images/product_1_wireless_bluetooth_headphones_with_noise_cancellat.jpg",
                "brand": "ProCam",
                "specs": {"Resolution": "4K 60fps", "Waterproof": "10m", "Battery": "2 hours recording"}
            },
            {
                "id": "prod_5",
                "name": "Wireless Gaming Mouse",
                "description": "High-precision wireless gaming mouse with 16000 DPI, RGB lighting, and ergonomic design. Perfect for gamers and professionals.",
                "price": 79.99,
                "stock": 67,
                "category": "Electronics",
                "rating": 4.4,
                "reviews_count": 1523,
                "image": "/images/product_6_wireless_mouse_with_precision_tracking.jpg",
                "brand": "GameGear",
                "specs": {"DPI": "16000", "Battery": "70 hours", "Buttons": "8 programmable"}
            },
            {
                "id": "prod_6",
                "name": "Portable Bluetooth Speaker",
                "description": "Waterproof portable speaker with 360° sound, 12-hour battery life, and premium bass. Perfect for outdoor adventures.",
                "price": 129.99,
                "stock": 89,
                "category": "Electronics",
                "rating": 4.3,
                "reviews_count": 2341,
                "image": "/images/product_14_bluetooth_speaker_waterproof.jpg",
                "brand": "SoundWave",
                "specs": {"Battery": "12 hours", "Waterproof": "IPX7", "Range": "30m"}
            },
            {
                "id": "prod_7",
                "name": "USB-C Hub 7-in-1",
                "description": "Universal USB-C hub with HDMI, USB 3.0, SD card reader, and power delivery. Essential for modern laptops.",
                "price": 49.99,
                "stock": 156,
                "category": "Electronics",
                "rating": 4.5,
                "reviews_count": 876,
                "image": "/images/product_20_usb_hub_7-port_with_power.jpg",
                "brand": "ConnectPro",
                "specs": {"Ports": "7", "4K Support": "Yes", "Power Delivery": "100W"}
            },
            {
                "id": "prod_8",
                "name": "Mechanical Keyboard RGB",
                "description": "Premium mechanical keyboard with Cherry MX switches, full RGB lighting, and aluminum frame. Perfect for typing and gaming.",
                "price": 159.99,
                "stock": 43,
                "category": "Electronics",
                "rating": 4.7,
                "reviews_count": 1098,
                "image": "/images/product_5_mechanical_gaming_keyboard_rgb.jpg",
                "brand": "KeyMaster",
                "specs": {"Switches": "Cherry MX Blue", "RGB": "Per-key", "Layout": "Full size"}
            },
            {
                "id": "prod_9",
                "name": "Wireless Earbuds Pro",
                "description": "True wireless earbuds with active noise cancellation, 24-hour battery life, and premium sound quality.",
                "price": 189.99,
                "stock": 78,
                "category": "Electronics",
                "rating": 4.6,
                "reviews_count": 3421,
                "image": "/images/product_10_noise_cancelling_earbuds_pro.jpg",
                "brand": "AudioTech",
                "specs": {"ANC": "Yes", "Battery": "24h with case", "Codec": "AAC, aptX"}
            },
            {
                "id": "prod_10",
                "name": "27\" 4K Monitor",
                "description": "Professional 4K IPS monitor with HDR support, 99% sRGB coverage, and USB-C connectivity. Perfect for creators.",
                "price": 499.99,
                "stock": 22,
                "category": "Electronics",
                "rating": 4.8,
                "reviews_count": 432,
                "image": "/images/product_21_4k_ultra_hd_monitor_27_inch.jpg",
                "brand": "ViewPro",
                "specs": {"Resolution": "3840x2160", "Panel": "IPS", "Refresh": "60Hz"}
            },

            # SPORTS & FITNESS (8 products)
            {
                "id": "prod_11",
                "name": "Premium Yoga Mat",
                "description": "Extra thick 6mm yoga mat with non-slip surface, eco-friendly material, and carrying strap. Perfect for yoga and pilates.",
                "price": 39.99,
                "stock": 234,
                "category": "Sports",
                "rating": 4.7,
                "reviews_count": 1876,
                "image": "/images/product_29_yoga_mat_non-slip_extra_thick.jpg",
                "brand": "YogaPro",
                "specs": {"Thickness": "6mm", "Material": "TPE", "Size": "183x61cm"}
            },
            {
                "id": "prod_12",
                "name": "Running Shoes Pro",
                "description": "Lightweight running shoes with responsive cushioning and breathable mesh. Designed for marathon runners and daily training.",
                "price": 139.99,
                "stock": 89,
                "category": "Sports",
                "rating": 4.6,
                "reviews_count": 2341,
                "image": "/images/product_29_yoga_mat_non-slip_extra_thick.jpg",
                "brand": "RunFast",
                "specs": {"Weight": "240g", "Drop": "8mm", "Cushioning": "Responsive foam"}
            },
            {
                "id": "prod_13",
                "name": "Adjustable Dumbbell Set",
                "description": "Space-saving adjustable dumbbells with 5-25kg weight range. Perfect for home gym and strength training.",
                "price": 299.99,
                "stock": 34,
                "category": "Sports",
                "rating": 4.8,
                "reviews_count": 567,
                "image": "/images/product_31_dumbbells_adjustable_pair.jpg",
                "brand": "FitHome",
                "specs": {"Range": "5-25kg", "Increments": "2.5kg", "Material": "Steel"}
            },
            {
                "id": "prod_14",
                "name": "Resistance Bands Set",
                "description": "Premium resistance bands set with 5 levels, door anchor, and carrying bag. Perfect for strength training anywhere.",
                "price": 29.99,
                "stock": 167,
                "category": "Sports",
                "rating": 4.5,
                "reviews_count": 1234,
                "image": "/images/product_30_resistance_bands_set_of_5.jpg",
                "brand": "FlexFit",
                "specs": {"Levels": "5", "Material": "Natural latex", "Resistance": "5-70 lbs"}
            },
            {
                "id": "prod_15",
                "name": "Foam Roller",
                "description": "High-density foam roller for muscle recovery and massage. Essential for athletes and fitness enthusiasts.",
                "price": 24.99,
                "stock": 198,
                "category": "Sports",
                "rating": 4.6,
                "reviews_count": 892,
                "image": "/images/product_29_yoga_mat_non-slip_extra_thick.jpg",
                "brand": "RecoverPro",
                "specs": {"Length": "33cm", "Density": "High", "Surface": "Textured"}
            },
            {
                "id": "prod_16",
                "name": "Sports Water Bottle",
                "description": "Insulated sports water bottle with straw, 32oz capacity, and leak-proof lid. Keeps drinks cold for 24 hours.",
                "price": 29.99,
                "stock": 234,
                "category": "Sports",
                "rating": 4.7,
                "reviews_count": 3421,
                "image": "/images/product_32_water_bottle_insulated_32oz.jpg",
                "brand": "HydratePro",
                "specs": {"Capacity": "32oz", "Insulation": "24h cold", "Material": "Stainless steel"}
            },
            {
                "id": "prod_17",
                "name": "Jump Rope Speed",
                "description": "Professional speed jump rope with ball bearings and adjustable length. Perfect for cardio and HIIT workouts.",
                "price": 19.99,
                "stock": 156,
                "category": "Sports",
                "rating": 4.4,
                "reviews_count": 654,
                "image": "/images/product_29_yoga_mat_non-slip_extra_thick.jpg",
                "brand": "CardioFit",
                "specs": {"Length": "Adjustable", "Handles": "Ergonomic foam", "Bearings": "Ball bearing"}
            },
            {
                "id": "prod_18",
                "name": "Gym Gloves",
                "description": "Padded gym gloves with wrist support and breathable fabric. Perfect for weightlifting and cross-training.",
                "price": 24.99,
                "stock": 123,
                "category": "Sports",
                "rating": 4.5,
                "reviews_count": 1098,
                "image": "/images/product_29_yoga_mat_non-slip_extra_thick.jpg",
                "brand": "LiftPro",
                "specs": {"Material": "Breathable mesh", "Padding": "Gel", "Closure": "Velcro strap"}
            },

            # HOME & LIVING (13 products)
            {
                "id": "prod_19",
                "name": "Smart LED Light Bulbs 4-Pack",
                "description": "WiFi-enabled smart LED bulbs with color changing, voice control, and scheduling. Compatible with Alexa and Google Home.",
                "price": 49.99,
                "stock": 145,
                "category": "Home",
                "rating": 4.6,
                "reviews_count": 2134,
                "image": "/images/product_36_smart_light_bulbs_rgb_4-pack.jpg",
                "brand": "SmartHome",
                "specs": {"Wattage": "9W", "Colors": "16M+", "Lifespan": "25000h"}
            },
            {
                "id": "prod_20",
                "name": "Air Purifier HEPA",
                "description": "High-efficiency air purifier with HEPA filter, covers 500 sq ft, removes 99.97% of allergens and pollutants.",
                "price": 179.99,
                "stock": 67,
                "category": "Home",
                "rating": 4.7,
                "reviews_count": 1543,
                "image": "/images/product_26_air_purifier_hepa_filter.jpg",
                "brand": "PureAir",
                "specs": {"Coverage": "500 sq ft", "Filters": "HEPA + Carbon", "Noise": "24dB"}
            },
            {
                "id": "prod_21",
                "name": "Coffee Maker Programmable",
                "description": "12-cup programmable coffee maker with thermal carafe, auto-shutoff, and brew strength control.",
                "price": 89.99,
                "stock": 98,
                "category": "Home",
                "rating": 4.5,
                "reviews_count": 2876,
                "image": "/images/product_28_coffee_maker_programmable_12-cup.jpg",
                "brand": "BrewMaster",
                "specs": {"Capacity": "12 cups", "Type": "Thermal carafe", "Timer": "24h programmable"}
            },
            {
                "id": "prod_22",
                "name": "Vacuum Cleaner Robot",
                "description": "Smart robot vacuum with app control, mapping technology, and self-charging. Perfect for hardwood and carpet.",
                "price": 349.99,
                "stock": 45,
                "category": "Home",
                "rating": 4.8,
                "reviews_count": 987,
                "image": "/images/product_51_robot_vacuum_with_mapping.jpg",
                "brand": "CleanBot",
                "specs": {"Battery": "120min", "Mapping": "Smart mapping", "Suction": "2000Pa"}
            },
            {
                "id": "prod_23",
                "name": "Bed Sheets Queen Size",
                "description": "Premium microfiber bed sheets set with deep pockets, wrinkle-resistant, and ultra-soft fabric. Set includes fitted sheet, flat sheet, and 2 pillowcases.",
                "price": 39.99,
                "stock": 234,
                "category": "Home",
                "rating": 4.6,
                "reviews_count": 3421,
                "image": "/images/product_29_yoga_mat_non-slip_extra_thick.jpg",
                "brand": "SleepWell",
                "specs": {"Material": "Microfiber", "Pocket Depth": "16 inches", "Thread Count": "1800"}
            },
            {
                "id": "prod_24",
                "name": "Electric Kettle 1.7L",
                "description": "Fast-boiling electric kettle with temperature control, auto shutoff, and boil-dry protection. Perfect for tea and coffee.",
                "price": 44.99,
                "stock": 167,
                "category": "Home",
                "rating": 4.4,
                "reviews_count": 1654,
                "image": "/images/product_42_electric_kettle_fast_boil.jpg",
                "brand": "QuickBoil",
                "specs": {"Capacity": "1.7L", "Power": "1500W", "Material": "Stainless steel"}
            },
            {
                "id": "prod_25",
                "name": "Cutting Board Set",
                "description": "Bamboo cutting board set with juice groove, 3 sizes included. Eco-friendly and knife-friendly surface.",
                "price": 34.99,
                "stock": 145,
                "category": "Home",
                "rating": 4.7,
                "reviews_count": 1098,
                "image": "/images/product_45_cutting_board_set_bamboo.jpg",
                "brand": "ChefPro",
                "specs": {"Material": "Bamboo", "Pieces": "3", "Sizes": "Small, Medium, Large"}
            },
            {
                "id": "prod_26",
                "name": "Storage Bins 6-Pack",
                "description": "Collapsible fabric storage bins with handles, perfect for closet organization, toys, and laundry.",
                "price": 29.99,
                "stock": 198,
                "category": "Home",
                "rating": 4.5,
                "reviews_count": 2341,
                "image": "/images/product_43_food_storage_containers_set.jpg",
                "brand": "OrganizePro",
                "specs": {"Material": "Non-woven fabric", "Size": "13x13x13 inches", "Pieces": "6"}
            },
            {
                "id": "prod_27",
                "name": "Humidifier Ultrasonic",
                "description": "Cool mist ultrasonic humidifier with 2.2L capacity, whisper-quiet operation, and auto shutoff. Perfect for bedroom.",
                "price": 59.99,
                "stock": 123,
                "category": "Home",
                "rating": 4.6,
                "reviews_count": 1876,
                "image": "/images/product_53_humidifier_ultrasonic_cool_mist.jpg",
                "brand": "MistPro",
                "specs": {"Capacity": "2.2L", "Runtime": "24h", "Noise": "28dB"}
            },
            {
                "id": "prod_28",
                "name": "Shower Curtain Set",
                "description": "Waterproof shower curtain with rust-resistant hooks, 72x72 inches, machine washable, modern design.",
                "price": 24.99,
                "stock": 234,
                "category": "Home",
                "rating": 4.3,
                "reviews_count": 987,
                "image": "/images/product_59_blackout_curtains_2_panels.jpg",
                "brand": "BathPro",
                "specs": {"Size": "72x72 inches", "Material": "Polyester", "Hooks": "12 included"}
            },
            {
                "id": "prod_29",
                "name": "Kitchen Knife Set",
                "description": "15-piece professional knife set with wooden block, high-carbon stainless steel blades, and ergonomic handles.",
                "price": 79.99,
                "stock": 89,
                "category": "Home",
                "rating": 4.8,
                "reviews_count": 1543,
                "image": "/images/product_44_knife_set_professional_15-piece.jpg",
                "brand": "SharpEdge",
                "specs": {"Pieces": "15", "Material": "High-carbon steel", "Storage": "Wooden block"}
            },
            {
                "id": "prod_30",
                "name": "Throw Pillows 4-Pack",
                "description": "Decorative throw pillows with soft covers and plush filling, 18x18 inches, perfect for couch and bed.",
                "price": 34.99,
                "stock": 167,
                "category": "Home",
                "rating": 4.5,
                "reviews_count": 2134,
                "image": "/images/product_57_pillow_memory_foam_cooling.jpg",
                "brand": "ComfortHome",
                "specs": {"Size": "18x18 inches", "Material": "Polyester", "Pieces": "4"}
            },
            {
                "id": "prod_31",
                "name": "Toaster 4-Slice",
                "description": "Stainless steel 4-slice toaster with bagel function, 6 browning settings, and removable crumb tray.",
                "price": 49.99,
                "stock": 98,
                "category": "Home",
                "rating": 4.4,
                "reviews_count": 1098,
                "image": "/images/product_48_instant_pot_6_quart.jpg",
                "brand": "ToastMaster",
                "specs": {"Slots": "4", "Settings": "6 browning levels", "Features": "Bagel, defrost, reheat"}
            }
        ]
        
        _PRODUCTS.extend(products)
        
        # Initialize some sample reviews
        _REVIEWS["prod_1"] = [
            {"rating": 5, "title": "Amazing sound quality!", "comment": "Best headphones I've ever owned.", "reviewer_name": "John D.", "date": "2024-01-15"},
            {"rating": 4, "title": "Great, but pricey", "comment": "Excellent product but a bit expensive.", "reviewer_name": "Sarah M.", "date": "2024-01-10"}
        ]


# API Endpoints

@app.get("/", response_class=HTMLResponse)
def serve_homepage():
    """Serve the e-commerce homepage."""
    html_path = Path(__file__).parent / "templates" / "index.html"
    if html_path.exists():
        return html_path.read_text()
    return "<h1>Scamazon</h1><p>Homepage template not found</p>"


@app.get("/products", response_class=HTMLResponse)
def serve_products_page(sort: str = Query(None)):
    """Serve the products listing page."""
    html_path = Path(__file__).parent / "templates" / "products.html"
    if html_path.exists():
        return html_path.read_text()
    return "<h1>Products</h1><p>Products page template not found</p>"


@app.get("/product/{product_id}", response_class=HTMLResponse)
def serve_product_detail(product_id: str):
    """Serve the product detail page."""
    html_path = Path(__file__).parent / "templates" / "product-detail.html"
    if html_path.exists():
        return html_path.read_text()
    return f"<h1>Product {product_id}</h1><p>Product detail template not found</p>"


@app.get("/cart", response_class=HTMLResponse)
def serve_cart_page():
    """Serve the shopping cart page."""
    html_path = Path(__file__).parent / "templates" / "cart.html"
    if html_path.exists():
        return html_path.read_text()
    return "<h1>Cart</h1><p>Cart page template not found</p>"


@app.get("/checkout", response_class=HTMLResponse)
def serve_checkout_page():
    """Serve the checkout page."""
    html_path = Path(__file__).parent / "templates" / "checkout.html"
    if html_path.exists():
        return html_path.read_text()
    return "<h1>Checkout</h1><p>Checkout page template not found</p>"


@app.get("/account", response_class=HTMLResponse)
def serve_account_page():
    """Serve the account page."""
    html_path = Path(__file__).parent / "templates" / "account.html"
    if html_path.exists():
        return html_path.read_text()
    return "<h1>Account</h1><p>Account page template not found</p>"


@app.get("/search", response_class=HTMLResponse)
def serve_search_page(q: str = Query(None)):
    """Serve the search results page."""
    html_path = Path(__file__).parent / "templates" / "search.html"
    if html_path.exists():
        return html_path.read_text()
    return f"<h1>Search Results for: {q}</h1><p>Search page template not found</p>"


@app.get("/order-confirmation", response_class=HTMLResponse)
def serve_order_confirmation():
    """Serve the order confirmation page."""
    html_path = Path(__file__).parent / "templates" / "order-confirmation.html"
    if html_path.exists():
        return html_path.read_text()
    return "<h1>Order Confirmation</h1><p>Order confirmation template not found</p>"


# API Endpoints
@app.get("/api/products")
def get_products(
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort: str = "name",
    page: int = 1,
    limit: int = 12
):
    """Get all products with optional filtering and pagination."""
    _init_product_catalog()
    
    filtered = _PRODUCTS.copy()
    
    # Apply filters
    if category:
        filtered = [p for p in filtered if p.get("category", "").lower() == category.lower()]
    if min_price is not None:
        filtered = [p for p in filtered if p["price"] >= min_price]
    if max_price is not None:
        filtered = [p for p in filtered if p["price"] <= max_price]
    
    # Sort
    if sort == "price_asc":
        filtered.sort(key=lambda x: x["price"])
    elif sort == "price_desc":
        filtered.sort(key=lambda x: x["price"], reverse=True)
    elif sort == "name":
        filtered.sort(key=lambda x: x["name"])
    elif sort == "rating":
        filtered.sort(key=lambda x: x.get("rating", 0), reverse=True)
    
    # Pagination
    start = (page - 1) * limit
    end = start + limit
    
    return {
        "products": filtered[start:end],
        "total": len(filtered),
        "page": page,
        "limit": limit,
        "total_pages": (len(filtered) + limit - 1) // limit
    }


@app.get("/api/products/{product_id}")
def get_product(product_id: str):
    """Get a single product by ID."""
    _init_product_catalog()
    
    product = next((p for p in _PRODUCTS if p["id"] == product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    return product


@app.post("/api/products")
def create_product(product: Product):
    """Create a new product (admin operation)."""
    _init_product_catalog()
    
    # Validation
    if product.price < 0:
        raise HTTPException(status_code=400, detail="Price cannot be negative")
    if product.stock < 0:
        raise HTTPException(status_code=400, detail="Stock cannot be negative")
    
    new_product = {
        "id": f"prod_{len(_PRODUCTS) + 1}",
        "name": product.name,
        "description": product.description,
        "price": product.price,
        "stock": product.stock,
        "category": product.category,
        "rating": 0,
        "reviews_count": 0,
        "image": "/images/product_1_wireless_bluetooth_headphones_with_noise_cancellat.jpg"
    }
    _PRODUCTS.append(new_product)
    return new_product


@app.post("/api/cart/add")
def add_to_cart(item: CartItem, session_id: str = Query("default")):
    """Add item to shopping cart."""
    _init_product_catalog()
    
    # Validation
    if item.quantity <= 0:
        raise HTTPException(status_code=400, detail="Quantity must be positive")
    if item.quantity > 100:
        raise HTTPException(status_code=400, detail="Quantity cannot exceed 100")
    
    # Check if product exists
    product = next((p for p in _PRODUCTS if p["id"] == item.product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Check stock
    if item.quantity > product["stock"]:
        raise HTTPException(status_code=400, detail=f"Only {product['stock']} items available")
    
    # Initialize cart if needed
    if session_id not in _CARTS:
        _CARTS[session_id] = []
    
    # Add or update item in cart
    existing = next((c for c in _CARTS[session_id] if c["product_id"] == item.product_id), None)
    if existing:
        existing["quantity"] += item.quantity
    else:
        _CARTS[session_id].append({
            "product_id": item.product_id,
            "quantity": item.quantity,
            "added_at": datetime.now().isoformat()
        })
    
    return {"message": "Item added to cart", "cart_size": len(_CARTS[session_id])}


@app.get("/api/cart")
def get_cart(session_id: str = Query("default")):
    """Get shopping cart contents."""
    _init_product_catalog()
    
    if session_id not in _CARTS:
        return {"items": [], "total": 0}
    
    cart_items = []
    total = 0
    
    for item in _CARTS[session_id]:
        product = next((p for p in _PRODUCTS if p["id"] == item["product_id"]), None)
        if product:
            subtotal = product["price"] * item["quantity"]
            total += subtotal
            cart_items.append({
                "product": product,
                "quantity": item["quantity"],
                "subtotal": subtotal
            })
    
    return {"items": cart_items, "total": total}


@app.delete("/api/cart")
def clear_cart(session_id: str = Query("default")):
    """Clear entire shopping cart."""
    if session_id in _CARTS:
        _CARTS[session_id] = []
    return {"message": "Cart cleared", "cart_size": 0}


@app.delete("/api/cart/all")
def clear_all_carts():
    """Clear all shopping carts for all sessions."""
    _CARTS.clear()
    return {"message": "All carts cleared", "total_sessions_cleared": len(_CARTS)}


@app.delete("/api/cart/item/{product_id}")
def remove_from_cart(product_id: str, session_id: str = Query("default")):
    """Remove item from shopping cart."""
    _init_product_catalog()
    
    # Initialize cart if it doesn't exist (shouldn't happen, but handle gracefully)
    if session_id not in _CARTS:
        return {"message": "Item removed from cart", "cart_size": 0}
    
    # Find and remove the item
    cart = _CARTS[session_id]
    initial_length = len(cart)
    _CARTS[session_id] = [item for item in cart if item["product_id"] != product_id]
    
    # If item wasn't found, that's okay - just return success
    # (idempotent operation)
    cart_size = len(_CARTS[session_id])
    
    # If cart is now empty, we can optionally remove the session
    # But keep it for consistency - empty cart is still a valid state
    if cart_size == 0:
        # Keep empty cart session for consistency
        pass
    
    return {"message": "Item removed from cart", "cart_size": cart_size}


@app.put("/api/cart/item/{product_id}")
def update_cart_item(product_id: str, quantity: int = Query(..., ge=1, le=100), session_id: str = Query("default")):
    """Update item quantity in shopping cart."""
    _init_product_catalog()
    
    if session_id not in _CARTS:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    # Find the item
    item = next((c for c in _CARTS[session_id] if c["product_id"] == product_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found in cart")
    
    # Check product stock
    product = next((p for p in _PRODUCTS if p["id"] == product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if quantity > product["stock"]:
        raise HTTPException(status_code=400, detail=f"Only {product['stock']} items available")
    
    # Update quantity
    item["quantity"] = quantity
    
    return {"message": "Item quantity updated", "cart_size": len(_CARTS[session_id])}


@app.post("/api/checkout")
def checkout(request: CheckoutRequest):
    """Process checkout and create order."""
    _init_product_catalog()
    
    if request.session_id not in _CARTS or not _CARTS[request.session_id]:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    # Create order
    order = {
        "id": str(uuid4()),
        "items": _CARTS[request.session_id].copy(),
        "total": sum(
            next((p["price"] for p in _PRODUCTS if p["id"] == item["product_id"]), 0) * item["quantity"]
            for item in _CARTS[request.session_id]
        ),
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "shipping_address": request.shipping_address,
        "payment_method": request.payment_method
    }
    
    _ORDERS.append(order)
    
    # Clear cart
    _CARTS[request.session_id] = []
    
    return {"order_id": order["id"], "message": "Order placed successfully", "order": order}


@app.get("/api/orders")
def get_orders(session_id: str = Query("default")):
    """Get order history."""
    return {"orders": _ORDERS}


@app.post("/api/products/{product_id}/reviews")
def add_review(product_id: str, review: Review):
    """Add a review for a product."""
    _init_product_catalog()
    
    # Validation
    if review.rating < 1 or review.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    # Check if product exists
    product = next((p for p in _PRODUCTS if p["id"] == product_id), None)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Add review
    if product_id not in _REVIEWS:
        _REVIEWS[product_id] = []
    
    _REVIEWS[product_id].append({
        "rating": review.rating,
        "title": review.title,
        "comment": review.comment,
        "reviewer_name": review.reviewer_name,
        "date": datetime.now().isoformat()
    })
    
    return {"message": "Review added successfully"}


@app.get("/api/products/{product_id}/reviews")
def get_reviews(product_id: str):
    """Get reviews for a product."""
    _init_product_catalog()
    
    if product_id not in _REVIEWS:
        return {"reviews": [], "count": 0, "average_rating": 0}
    
    reviews = _REVIEWS[product_id]
    avg_rating = sum(r["rating"] for r in reviews) / len(reviews) if reviews else 0
    
    return {
        "reviews": reviews,
        "count": len(reviews),
        "average_rating": round(avg_rating, 2)
    }


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


# Initialize catalog on startup
_init_product_catalog()
