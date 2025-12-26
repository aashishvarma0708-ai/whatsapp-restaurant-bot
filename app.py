from flask import Flask, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
import uuid, datetime, os, json

app = Flask(__name__)

# =====================
# MENU DATA
# =====================
MENU = {
    "starters": {
        "1": {"name": "Paneer Tikka", "price": 180},
        "2": {"name": "Chicken 65", "price": 220},
        "3": {"name": "Veg Manchurian", "price": 160}
    },
    "main": {
        "1": {"name": "Butter Chicken", "price": 320},
        "2": {"name": "Veg Biryani", "price": 220},
        "3": {"name": "Chicken Biryani", "price": 280}
    },
    "desserts": {
        "1": {"name": "Gulab Jamun", "price": 90},
        "2": {"name": "Ice Cream", "price": 120},
        "3": {"name": "Brownie", "price": 150}
    },
    "drinks": {
        "1": {"name": "Coke", "price": 40},
        "2": {"name": "Sprite", "price": 40},
        "3": {"name": "Water Bottle", "price": 20}
    }
}

user_sessions = {}

ORDERS_DIR = "orders"
os.makedirs(ORDERS_DIR, exist_ok=True)

# =====================
# POS PRINT
# =====================
def print_to_pos(text):
    print("\n====== PRINT TO CHEF ======\n")
    print(text)
    print("\n===========================\n")

# =====================
# HELPERS
# =====================
def cart_total(cart):
    return sum(i["price"] * i["qty"] for i in cart)

def cart_count(cart):
    return sum(i["qty"] for i in cart)

# =====================
# WHATSAPP WEBHOOK
# =====================
@app.route("/whatsapp", methods=["POST"])
def whatsapp():
    msg = request.form.get("Body", "").strip().lower()
    user = request.form.get("From")
    resp = MessagingResponse()

    if user not in user_sessions:
        user_sessions[user] = {
            "state": "welcome",
            "cart": [],
            "category": None,
            "item": None,
            "order": {}
        }

    s = user_sessions[user]

    # ---- WELCOME ----
    if s["state"] == "welcome":
        s["state"] = "home"
        resp.message(
            "👋 Welcome to ABC Restaurant\n\n"
            "Reply:\n"
            "1️⃣ View Menu\n"
            "2️⃣ Reserve a Table"
        )
        return str(resp)

    # ---- HOME ----
    if s["state"] == "home":
        if msg == "1":
            s["state"] = "category"
            resp.message(
                "🍽️ Menu Categories\n\n"
                "1️⃣ Starters\n"
                "2️⃣ Main Course\n"
                "3️⃣ Desserts\n"
                "4️⃣ Soft Drinks"
            )
        elif msg == "2":
            resp.message("📞 Please call restaurant to reserve table")
        else:
            resp.message("Reply 1 or 2")
        return str(resp)

    # ---- CATEGORY ----
    if s["state"] == "category":
        mapping = {"1": "starters", "2": "main", "3": "desserts", "4": "drinks"}
        if msg in mapping:
            s["category"] = mapping[msg]
            s["state"] = "items"

            text = f"🍴 {s['category'].title()}\n\n"
            for k, v in MENU[s["category"]].items():
                text += f"{k}. {v['name']} - ₹{v['price']}\n"

            resp.message(text + "\nReply item number")
        else:
            resp.message("Invalid category")
        return str(resp)

    # ---- ITEM SELECT ----
    if s["state"] == "items":
        items = MENU[s["category"]]
        if msg in items:
            s["item"] = items[msg]
            s["state"] = "qty"
            resp.message(f"How many {s['item']['name']}?")
        else:
            resp.message("Invalid item")
        return str(resp)

    # ---- QUANTITY ----
    if s["state"] == "qty":
        if msg.isdigit() and 1 <= int(msg) <= 10:
            s["cart"].append({
                "name": s["item"]["name"],
                "price": s["item"]["price"],
                "qty": int(msg)
            })
            s["state"] = "post_add"
            resp.message(
                f"✅ Added to cart\n\n"
                f"Cart Items: {cart_count(s['cart'])}\n\n"
                "Reply:\n"
                "1️⃣ Add more\n"
                "2️⃣ View Cart"
            )
        else:
            resp.message("Enter valid quantity (1–10)")
        return str(resp)

    # ---- AFTER ADD ----
    if s["state"] == "post_add":
        if msg == "1":
            s["state"] = "category"
            resp.message(
    "🍽️ Menu Categories\n\n"
    "1️⃣ Starters\n"
    "2️⃣ Main Course\n"
    "3️⃣ Desserts\n"
    "4️⃣ Soft Drinks"
)

        elif msg == "2":
            s["state"] = "cart"
            text = "🛒 Your Cart\n\n"
            for i in s["cart"]:
                text += f"{i['name']} x{i['qty']} ₹{i['price']*i['qty']}\n"
            text += f"\nTotal ₹{cart_total(s['cart'])}\n\nReply 1 Remove | 2 Checkout"
            resp.message(text)
        else:
            resp.message("Reply 1 or 2")
        return str(resp)

    # ---- CART ----
    if s["state"] == "cart":
        if msg == "2":
            s["state"] = "order_type"
            resp.message("Order Type:\n1️⃣ Dine In\n2️⃣ Home Delivery")
        else:
            resp.message("Checkout only supported")
        return str(resp)

    # ---- ORDER TYPE ----
    if s["state"] == "order_type":
        s["order"]["type"] = "Dine In" if msg == "1" else "Delivery"
        s["state"] = "name"
        resp.message("Enter your name")
        return str(resp)

    # ---- NAME ----
    if s["state"] == "name":
        s["order"]["name"] = msg
        s["state"] = "location"
        resp.message(
            "Enter table number" if s["order"]["type"] == "Dine In"
            else "Enter delivery address"
        )
        return str(resp)

    # ---- LOCATION ----
    if s["state"] == "location":
        s["order"]["location"] = msg
        s["state"] = "phone"
        resp.message("Enter phone number")
        return str(resp)

    # ---- PHONE ----
    if s["state"] == "phone":
        s["order"]["phone"] = msg
        s["state"] = "payment"
        resp.message("Payment:\n1️⃣ UPI\n2️⃣ Cash at Counter")
        return str(resp)

    # ---- PAYMENT ----
    if s["state"] == "payment":
        payment = "UPI" if msg == "1" else "Cash"
        order_id = "ORD" + str(uuid.uuid4())[:6]

        order_data = {
            "id": order_id,
            "time": str(datetime.datetime.now()),
            "cart": s["cart"],
            "total": cart_total(s["cart"]),
            "payment": payment,
            **s["order"]
        }

        # Save order
        with open(f"{ORDERS_DIR}/{order_id}.json", "w") as f:
            json.dump(order_data, f, indent=4)

        # Print
        print_to_pos(json.dumps(order_data, indent=2))

        # Reset
        user_sessions[user] = {"state": "welcome", "cart": []}

        resp.message(f"✅ Order Confirmed\nOrder ID: {order_id}")
        return str(resp)

    resp.message("Restarting. Reply hi")
    return str(resp)

# =====================
# DASHBOARD API
# =====================
@app.route("/dashboard")
def dashboard():
    orders = []
    for f in os.listdir(ORDERS_DIR):
        with open(f"{ORDERS_DIR}/{f}") as file:
            orders.append(json.load(file))
    return jsonify(orders)

if __name__ == "__main__":
    app.run(port=5000, debug=True)

