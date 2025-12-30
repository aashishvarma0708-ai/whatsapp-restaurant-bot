from flask import Flask, request, render_template
from twilio.twiml.messaging_response import MessagingResponse
import os, json, time

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
# Helper functions
# -----------------------------
def get_session(user):
    if user not in sessions:
        sessions[user] = {"cart": [], "state": "welcome", "last_item": None}
    return sessions[user]

def save_order(order):
    os.makedirs("orders", exist_ok=True)
    order["id"] = f"ORD{int(time.time())}"
    with open(f"orders/{order['id']}.json", "w") as f:
        json.dump(order, f, indent=4)

def send_buttons(resp, body, buttons):
    msg = resp.message(body=body)
    msg._message.append({
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body},
            "action": {"buttons": [{"type": "reply", "reply": {"id": b["id"], "title": b["title"]}} for b in buttons]}
        }
    })

def send_list(resp, body, sections):
    msg = resp.message(body=body)
    msg._message.append({
        "type": "interactive",
        "interactive": {"type": "list", "body": {"text": body}, "action": {"button": "View Menu", "sections": sections}}
    })

# -----------------------------
# WhatsApp webhook
# -----------------------------
@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    user = request.form.get("From")
    body = request.form.get("Body", "").strip().lower()
    session = get_session(user)
    resp = MessagingResponse()

    # -------------------------
    # WELCOME
    # -------------------------
    if session["state"] == "welcome":
        send_buttons(resp, "👋 Welcome to Our Restaurant!\nHow can we help you?", [
            {"id": "menu", "title": "📋 Menu"},
            {"id": "reserve", "title": "🍽 Reserve Table"},
            {"id": "cart", "title": "🛒 Cart"}
        ])
        session["state"] = "home"
        return str(resp)

    # -------------------------
    # HOME BUTTONS
    # -------------------------
    if body in ["menu", "📋 menu"]:
        send_list(resp, "📋 Select a category", [
            {"title": "Menu", "rows": [
                {"id": "starters", "title": "🥗 Starters"},
                {"id": "main_course", "title": "🍛 Main Course"},
                {"id": "desserts", "title": "🍰 Desserts"},
                {"id": "drinks", "title": "🥤 Soft Drinks"}
            ]}
        ])
        session["state"] = "category"
        return str(resp)

    if body in ["cart", "🛒 cart"]:
        if not session["cart"]:
            resp.message("🛒 Your cart is empty")
            return str(resp)
        else:
            text = "🛒 Your Cart:\n"
            total = 0
            for c in session["cart"]:
                text += f"- {c['name']} x{c['qty']}\n"
                total += c["price"] * c["qty"]
            text += f"\nTotal: ₹{total}"
            send_buttons(resp, text, [
                {"id": "menu", "title": "➕ Add More"},
                {"id": "remove_item", "title": "❌ Remove Item"},
                {"id": "checkout", "title": "✅ Checkout"}
            ])
            session["state"] = "cart_action"
            return str(resp)

    # -------------------------
    # CATEGORY → ITEMS
    # -------------------------
    if body in MENU:
        rows = [{"id": item["id"], "title": f"{item['name']} ₹{item['price']}"} for item in MENU[body]]
        send_list(resp, "Select an item", [{"title": body.title(), "rows": rows}])
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
                session["cart"].append({"name": item["name"], "qty": 1, "price": item["price"]})
                send_buttons(resp, f"✅ {item['name']} added to cart. Choose quantity:", [
                    {"id": "add1", "title": "➕ +1"},
                    {"id": "add2", "title": "➕ +2"},
                    {"id": "done", "title": "✅ Done"}
                ])
                session["state"] = "quantity"
                return str(resp)

    # -------------------------
    # QUANTITY HANDLING
    # -------------------------
    if session["state"] == "quantity":
        cart_item = session["cart"][-1]
        if body == "add1" or body == "➕ +1":
            cart_item["qty"] += 1
        elif body == "add2" or body == "➕ +2":
            cart_item["qty"] += 2
        elif body == "done" or body == "✅ done":
            send_buttons(resp, "Item added to cart 🛒\nWhat next?", [
                {"id": "menu", "title": "➕ Add More"},
                {"id": "cart", "title": "🛒 View Cart"},
                {"id": "checkout", "title": "✅ Checkout"}
            ])
            session["state"] = "cart_action"
            return str(resp)
        send_buttons(resp, f"{cart_item['name']} qty: {cart_item['qty']}", [
            {"id": "add1", "title": "➕ +1"},
            {"id": "add2", "title": "➕ +2"},
            {"id": "done", "title": "✅ Done"}
        ])
        return str(resp)

    # -------------------------
    # CART ACTIONS
    # -------------------------
    if session["state"] == "cart_action":
        if body in ["menu", "➕ add more"]:
            session["state"] = "category"
            send_list(resp, "📋 Select a category", [
                {"title": "Menu", "rows": [
                    {"id": "starters", "title": "🥗 Starters"},
                    {"id": "main_course", "title": "🍛 Main Course"},
                    {"id": "desserts", "title": "🍰 Desserts"},
                    {"id": "drinks", "title": "🥤 Soft Drinks"}
                ]}
            ])
            return str(resp)
        elif body in ["checkout", "✅ checkout"]:
            send_buttons(resp, "Choose payment method:", [
                {"id": "upi", "title": "💳 UPI"},
                {"id": "cash", "title": "💵 Cash at Counter"}
            ])
            session["state"] = "payment"
            return str(resp)
        elif body in ["remove_item", "❌ remove item"]:
            rows = [{"id": str(i), "title": f"{c['name']} x{c['qty']}"} for i, c in enumerate(session["cart"])]
            send_list(resp, "Select item to remove:", [{"title": "Cart Items", "rows": rows}])
            session["state"] = "remove_item"
            return str(resp)

    # -------------------------
    # REMOVE ITEM
    # -------------------------
    if session["state"] == "remove_item":
        try:
            index = int(body)
            removed = session["cart"].pop(index)
            send_buttons(resp, f"❌ {removed['name']} removed from cart", [
                {"id": "menu", "title": "➕ Add More"},
                {"id": "cart", "title": "🛒 View Cart"},
                {"id": "checkout", "title": "✅ Checkout"}
            ])
            session["state"] = "cart_action"
        except:
            resp.message("Invalid selection. Please choose an item from the list.")
        return str(resp)

    # -------------------------
    # PAYMENT
    # -------------------------
    if session["state"] == "payment":
        if body in ["upi", "💳 upi", "cash", "💵 cash"]:
            order = {"customer": {"phone": user}, "cart": session["cart"], "payment": body, "status": "Confirmed"}
            save_order(order)
            resp.message("🎉 Order Confirmed!\nYour food is being prepared 🍳")
            session.clear()
            return str(resp)

    # -------------------------
    # FALLBACK
    # -------------------------
    resp.message("Please choose an option using the buttons above 👆")
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
