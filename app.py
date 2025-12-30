from twilio.twiml.messaging_response import MessagingResponse
from flask import Flask, request, render_template
from twilio.twiml.messaging_response import MessagingResponse
import os, json, time
def send_buttons(resp, body, buttons):
    msg = resp.message(body=body)
    msg._message.append({
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body},
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": b["id"],
                            "title": b["title"]
                        }
                    } for b in buttons
                ]
            }
        }
    })


def send_list(resp, body, sections):
    msg = resp.message(body=body)
    msg._message.append({
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": body},
            "action": {
                "button": "View Menu",
                "sections": sections
            }
        }
    })


app = Flask(__name__)

# -----------------------------
# In-memory session storage
# -----------------------------
sessions = {}

MENU = {
    "starters": [
        {"id": "chicken_wings", "name": "Chicken Wings", "price": 180},
        {"id": "veg_roll", "name": "Veg Spring Roll", "price": 120},
        {"id": "paneer_tikka", "name": "Paneer Tikka", "price": 160}
    ],
    "main_course": [
        {"id": "chicken_biryani", "name": "Chicken Biryani", "price": 250},
        {"id": "paneer_butter", "name": "Paneer Butter Masala", "price": 220},
        {"id": "fried_rice", "name": "Veg Fried Rice", "price": 180}
    ],
    "desserts": [
        {"id": "gulab_jamun", "name": "Gulab Jamun", "price": 80},
        {"id": "ice_cream", "name": "Ice Cream", "price": 90}
    ],
    "drinks": [
        {"id": "coke", "name": "Coca Cola", "price": 50},
        {"id": "sprite", "name": "Sprite", "price": 50}
    ]
}

# -----------------------------
# Utility
# -----------------------------
def get_session(user):
    if user not in sessions:
        sessions[user] = {
            "cart": [],
            "state": "welcome",
            "last_item": None
        }
    return sessions[user]


def save_order(order):
    os.makedirs("orders", exist_ok=True)
    order["id"] = f"ORD{int(time.time())}"
    with open(f"orders/{order['id']}.json", "w") as f:
        json.dump(order, f, indent=4)

# -----------------------------
# WhatsApp Webhook
# -----------------------------
@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming = request.form.get("Body", "").strip().lower()
    resp = MessagingResponse()

    if incoming in ["hi", "hello", "hey"]:
        send_buttons(
            resp,
            "👋 Welcome to Our Restaurant\nHow can I help you?",
            [
                {"id": "menu", "title": "📋 Menu"},
                {"id": "reserve", "title": "🍽 Reserve Table"},
                {"id": "cart", "title": "🛒 Cart"}
            ]
        )

    elif incoming == "menu":
        send_list(
            resp,
            "📋 Select a category",
            [
                {
                    "title": "Menu",
                    "rows": [
                        {"id": "starters", "title": "🥗 Starters"},
                        {"id": "main", "title": "🍛 Main Course"},
                        {"id": "dessert", "title": "🍰 Desserts"},
                        {"id": "drinks", "title": "🥤 Soft Drinks"}
                    ]
                }
            ]
        )

    elif incoming == "starters":
        send_list(
            resp,
            "🥗 Starters",
            [
                {
                    "title": "Starters",
                    "rows": [
                        {"id": "add_soup", "title": "Tomato Soup – ₹120"},
                        {"id": "add_fries", "title": "French Fries – ₹100"},
                        {"id": "add_paneer", "title": "Paneer Tikka – ₹180"}
                    ]
                }
            ]
        )

    elif incoming.startswith("add_"):
        item = incoming.replace("add_", "").replace("_", " ").title()
        resp.message(f"✅ {item} added to cart")

        send_buttons(
            resp,
            "What would you like to do next?",
            [
                {"id": "menu", "title": "➕ Add More"},
                {"id": "cart", "title": "🛒 View Cart"},
                {"id": "checkout", "title": "✅ Checkout"}
            ]
        )

    elif incoming == "cart":
        resp.message("🛒 Your cart has items (demo)")
        send_buttons(
            resp,
            "Proceed?",
            [
                {"id": "menu", "title": "➕ Add More"},
                {"id": "checkout", "title": "✅ Checkout"}
            ]
        )

    elif incoming == "checkout":
        resp.message("✅ Order confirmed! Thank you 🙏")

    else:
        resp.message("Please choose using the buttons above 👆")

    return str(resp)


    # -------------------------
    # WELCOME
    # -------------------------
    if session["state"] == "welcome":
        msg.body("Welcome to ABC Restaurant 🍽️\nHow can we help you?")
        msg.button("🍴 View Menu")
        msg.button("🪑 Reserve Table")
        msg.button("📞 Contact")
        session["state"] = "home"
        return str(resp)

    # -------------------------
    # HOME BUTTON HANDLING
    # -------------------------
    if body == "🍴 View Menu":
        msg.body("Select a category")
        msg.list(
            "Menu Categories",
            sections=[{
                "title": "Categories",
                "rows": [
                    {"id": "starters", "title": "Starters"},
                    {"id": "main_course", "title": "Main Course"},
                    {"id": "desserts", "title": "Desserts"},
                    {"id": "drinks", "title": "Soft Drinks"}
                ]
            }]
        )
        session["state"] = "category"
        return str(resp)

    # -------------------------
    # CATEGORY → ITEMS
    # -------------------------
    if body in MENU:
        rows = []
        for item in MENU[body]:
            rows.append({
                "id": item["id"],
                "title": f"{item['name']} ₹{item['price']}"
            })

        msg.body("Select an item")
        msg.list(
            "Menu Items",
            sections=[{
                "title": "Items",
                "rows": rows
            }]
        )
        session["state"] = "item"
        session["category"] = body
        return str(resp)

    # -------------------------
    # ITEM SELECTED
    # -------------------------
for cat in MENU:
    for item in MENU[cat]:
        if body == item["id"]:
            session["last_item"] = item

            # add with qty = 1 initially
            session["cart"].append({
                "name": item["name"],
                "qty": 1,
                "price": item["price"]
            })

            msg.body(f"✅ {item['name']} added\nChoose quantity")
            msg.button("➕ +1")
            msg.button("➕ +2")
            msg.button("✅ Done")

            session["state"] = "quantity"
            return str(resp)
# -------------------------
# QUANTITY HANDLING
# -------------------------
if session["state"] == "quantity":
    cart_item = session["cart"][-1]  # last added item

    if body == "➕ +1":
        cart_item["qty"] += 1
        msg.body(f"{cart_item['name']} qty: {cart_item['qty']}")
        msg.button("➕ +1")
        msg.button("➕ +2")
        msg.button("✅ Done")
        return str(resp)

    if body == "➕ +2":
        cart_item["qty"] += 2
        msg.body(f"{cart_item['name']} qty: {cart_item['qty']}")
        msg.button("➕ +1")
        msg.button("➕ +2")
        msg.button("✅ Done")
        return str(resp)

    if body == "✅ Done":
        msg.body("Item added to cart 🛒\nWhat next?")
        msg.button("➕ Add More")
        msg.button("🛒 View Cart")
        msg.button("✅ Checkout")
        session["state"] = "cart_action"
        return str(resp)



    # -------------------------
    # CART ACTIONS
    # -------------------------
    if body == "➕ Add More":
        msg.body("Select a category")
        msg.list(
            "Menu Categories",
            sections=[{
                "title": "Categories",
                "rows": [
                    {"id": "starters", "title": "Starters"},
                    {"id": "main_course", "title": "Main Course"},
                    {"id": "desserts", "title": "Desserts"},
                    {"id": "drinks", "title": "Soft Drinks"}
                ]
            }]
        )
        session["state"] = "category"
        return str(resp)

    if body == "🛒 View Cart":
    text = "🛒 Your Cart:\n"
    total = 0

    for c in session["cart"]:
        text += f"- {c['name']} x{c['qty']}\n"
        total += c["price"] * c["qty"]

    text += f"\nTotal: ₹{total}"

    msg.body(text)
    msg.button("➕ Add More")
    msg.button("❌ Remove Item")
    msg.button("✅ Checkout")
    session["state"] = "cart_view"
    return str(resp)

    if body == "❌ Remove Item" and session["cart"]:
    rows = []

    for idx, item in enumerate(session["cart"]):
        rows.append({
            "id": str(idx),
            "title": f"{item['name']} x{item['qty']}"
        })

    msg.body("Select item to remove")
    msg.list(
        "Remove from Cart",
        sections=[{
            "title": "Cart Items",
            "rows": rows
        }]
    )

    session["state"] = "remove_item"
    return str(resp)
    if session["state"] == "remove_item":
    try:
        index = int(body)
        removed = session["cart"].pop(index)

        msg.body(f"❌ {removed['name']} removed from cart")
        msg.button("🛒 View Cart")
        msg.button("➕ Add More")
        msg.button("✅ Checkout")

        session["state"] = "cart_action"
        return str(resp)
    except:
        msg.body("Invalid selection. Please choose an item from the list.")
        return str(resp)



    if body == "✅ Checkout":
        msg.body("Choose payment method")
        msg.button("💳 UPI")
        msg.button("💵 Cash at Counter")
        session["state"] = "payment"
        return str(resp)

    # -------------------------
    # PAYMENT & CONFIRM
    # -------------------------
    if body in ["💳 UPI", "💵 Cash at Counter"]:
        order = {
            "customer": {"phone": user},
            "cart": session["cart"],
            "payment": body,
            "status": "Confirmed"
        }
        save_order(order)

        msg.body("🎉 Order Confirmed!\nYour food is being prepared 🍳")
        session.clear()
        return str(resp)

    msg.body("Please choose an option using the buttons.")
    return str(resp)

# -----------------------------
# ADMIN DASHBOARD
# -----------------------------
@app.route("/admin")
def admin():
    key = request.args.get("key")
    if key != "restaurant123":
        return "Unauthorized", 401

    orders = []
    if os.path.exists("orders"):
        for f in os.listdir("orders"):
            with open(f"orders/{f}") as file:
                orders.append(json.load(file))

    return render_template("admin.html", orders=orders)

# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
