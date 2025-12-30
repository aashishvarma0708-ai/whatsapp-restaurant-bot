# app.py
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
# Utility functions
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
# Button & List helpers
# -----------------------------
def send_buttons(resp, body, buttons):
    """
    Send button style interactive message.
    buttons: list of dicts {"id": "menu", "title": "Menu"}
    """
    msg = resp.message()
    msg.body(body)
    msg.content_type = 'application/json'
    msg.body = {
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": {"id": b["id"], "title": b["title"]}} 
                    for b in buttons
                ]
            }
        }
    }


def send_list(resp, body, sections):
    """
    Send list style interactive message.
    sections: [{"title": "Menu", "rows": [{"id": "starters","title":"Starters"}]}]
    """
    msg = resp.message()
    msg.body(body)
    msg.content_type = 'application/json'
    msg.body = {
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": body},
            "action": {
                "button": "View Menu",
                "sections": sections
            }
        }
    }

# -----------------------------
# WhatsApp Webhook
# -----------------------------
@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    incoming = request.form.get("Body", "").strip().lower()
    user = request.form.get("From", "")
    session = get_session(user)
    resp = MessagingResponse()

    # -------------------------
    # Welcome message
    # -------------------------
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
        return str(resp)

    # -------------------------
    # Menu categories
    # -------------------------
    if incoming == "menu":
        send_list(
            resp,
            "📋 Select a category",
            [
                {
                    "title": "Menu",
                    "rows": [
                        {"id": "starters", "title": "🥗 Starters"},
                        {"id": "main_course", "title": "🍛 Main Course"},
                        {"id": "desserts", "title": "🍰 Desserts"},
                        {"id": "drinks", "title": "🥤 Soft Drinks"}
                    ]
                }
            ]
        )
        session["state"] = "category"
        return str(resp)

    # -------------------------
    # Show items in category
    # -------------------------
    if incoming in MENU:
        rows = [{"id": item["id"], "title": f"{item['name']} ₹{item['price']}"} for item in MENU[incoming]]
        send_list(
            resp,
            f"Select an item from {incoming.title()}",
            [{"title": incoming.title(), "rows": rows}]
        )
        session["state"] = "item"
        session["category"] = incoming
        return str(resp)

    # -------------------------
    # Add item to cart
    # -------------------------
    for cat in MENU:
        for item in MENU[cat]:
            if incoming == item["id"]:
                session["last_item"] = item
                # Add item with qty 1 initially
                session["cart"].append({"name": item["name"], "qty": 1, "price": item["price"]})
                send_buttons(
                    resp,
                    f"✅ {item['name']} added to cart. Choose quantity:",
                    [
                        {"id": "qty1", "title": "+1"},
                        {"id": "qty2", "title": "+2"},
                        {"id": "done_qty", "title": "✅ Done"}
                    ]
                )
                session["state"] = "quantity"
                return str(resp)

    # -------------------------
    # Quantity handling
    # -------------------------
    if session.get("state") == "quantity":
        cart_item = session["cart"][-1]
        if incoming == "qty1":
            cart_item["qty"] += 1
        elif incoming == "qty2":
            cart_item["qty"] += 2
        elif incoming == "done_qty":
            send_buttons(
                resp,
                "Item added to cart 🛒 What next?",
                [
                    {"id": "menu", "title": "➕ Add More"},
                    {"id": "cart", "title": "🛒 View Cart"},
                    {"id": "checkout", "title": "✅ Checkout"}
                ]
            )
            session["state"] = "cart_action"
            return str(resp)

        send_buttons(
            resp,
            f"{cart_item['name']} qty: {cart_item['qty']}",
            [
                {"id": "qty1", "title": "+1"},
                {"id": "qty2", "title": "+2"},
                {"id": "done_qty", "title": "✅ Done"}
            ]
        )
        return str(resp)

    # -------------------------
    # View cart / Checkout
    # -------------------------
    if incoming == "cart":
        text = "🛒 Your Cart:\n"
        total = 0
        for c in session["cart"]:
            text += f"- {c['name']} x{c['qty']}\n"
            total += c["price"] * c["qty"]
        text += f"\nTotal: ₹{total}"
        send_buttons(
            resp,
            text,
            [
                {"id": "menu", "title": "➕ Add More"},
                {"id": "checkout", "title": "✅ Checkout"}
            ]
        )
        session["state"] = "cart_view"
        return str(resp)

    if incoming == "checkout":
        send_buttons(
            resp,
            "Choose payment method",
            [
                {"id": "upi", "title": "💳 UPI"},
                {"id": "cash", "title": "💵 Cash at Counter"}
            ]
        )
        session["state"] = "payment"
        return str(resp)

    # -------------------------
    # Payment handling
    # -------------------------
    if session.get("state") == "payment":
        order = {
            "customer": {"phone": user},
            "cart": session["cart"],
            "payment": incoming,
            "status": "Confirmed"
        }
        save_order(order)
        resp.message("🎉 Order Confirmed!\nYour food is being prepared 🍳")
        session.clear()
        return str(resp)

    # -------------------------
    # Fallback
    # -------------------------
    resp.message("Please use the buttons above 👆")
    return str(resp)

# -----------------------------
# Admin Dashboard
# -----------------------------
@app.route("/admin")
def admin():
    key = request.args.get("key")
    if key != "restaurant123":
        return "Unauthorized", 401

    orders = []
    if os.path.exists("orders"):
        for f in os.listdir("orders"):
            if f.endswith(".json"):
                with open(f"orders/" + f) as file:
                    orders.append(json.load(file))

    return render_template("admin.html", orders=orders)

# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
