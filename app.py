from flask import Flask, request, redirect, url_for, render_template_string
import sqlite3
from datetime import datetime

app = Flask(__name__)
DB = "data.db"

# -------------------------
# Database Setup
# -------------------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS purchase(
        item TEXT,
        price REAL,
        gst REAL,
        discount REAL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS sales(
        item TEXT,
        price REAL,
        gst REAL,
        discount REAL,
        date TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS payments(
        customer TEXT,
        amount REAL,
        status TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# -------------------------
# HOME PAGE
# -------------------------
@app.route("/")
def home():
    return render_template_string("""
    <html>
    <head>
        <style>
            body {
                font-family: Arial;
                background: #f4f6f8;
                text-align: center;
            }
            h1 {
                background: #2c3e50;
                color: white;
                padding: 15px;
                margin: 0;
            }
            .grid {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 20px;
                padding: 30px;
            }
            .card {
                background: white;
                padding: 20px;
                border-radius: 12px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
                text-decoration: none;
                color: black;
                font-size: 18px;
            }
            .icon {
                font-size: 40px;
            }
        </style>
    </head>
    <body>

    <h1>jaanu_mm</h1>

    <div class="grid">
        <a class="card" href="/purchase">
            <div class="icon">📥</div>
            Purchase Upload
        </a>

        <a class="card" href="/sale">
            <div class="icon">📤</div>
            Sale Upload
        </a>

        <a class="card" href="/payments">
            <div class="icon">💰</div>
            Customer Payments
        </a>

        <a class="card" href="/send_reminders">
            <div class="icon">📧</div>
            Send Reminders
        </a>

        <a class="card" href="/daily_profit">
            <div class="icon">📊</div>
            Daily Profit
        </a>
    </div>

    </body>
    </html>
    """)

# -------------------------
# PURCHASE
# -------------------------
@app.route("/purchase", methods=["GET", "POST"])
def purchase():
    if request.method == "POST":
        item = request.form["item"]
        price = float(request.form["price"])
        gst = float(request.form["gst"])
        discount = float(request.form["discount"])

        conn = sqlite3.connect(DB)
        c = conn.cursor()

        c.execute("DELETE FROM purchase WHERE item=?", (item,))
        c.execute("INSERT INTO purchase VALUES (?,?,?,?)",
                  (item, price, gst, discount))
        conn.commit()
        conn.close()

        return redirect(url_for("home"))

    return """
    <h2>Upload Purchase</h2>
    <form method="post">
        Item: <input name="item"><br>
        Price: <input name="price"><br>
        GST %: <input name="gst"><br>
        Discount: <input name="discount"><br>
        <button>Save</button>
    </form>
    """

# -------------------------
# SALE
# -------------------------
@app.route("/sale", methods=["GET", "POST"])
def sale():
    if request.method == "POST":
        item = request.form["item"]
        sale_price = float(request.form["price"])
        gst = float(request.form["gst"])
        discount = float(request.form["discount"])
        date = datetime.now().strftime("%Y-%m-%d")

        conn = sqlite3.connect(DB)
        c = conn.cursor()

        c.execute("SELECT price, gst, discount FROM purchase WHERE item=?", (item,))
        row = c.fetchone()

        if row:
            purchase_price, p_gst, p_discount = row
            purchase_final = purchase_price + (purchase_price * p_gst/100) - p_discount
            sale_final = sale_price + (sale_price * gst/100) - discount
            profit = sale_final - purchase_final
        else:
            profit = 0

        c.execute("INSERT INTO sales VALUES (?,?,?,?,?)",
                  (item, sale_price, gst, discount, date))
        conn.commit()
        conn.close()

        return f"<h2>Profit for {item}: {profit}</h2><a href='/'>Back</a>"

    return """
    <h2>Upload Sale</h2>
    <form method="post">
        Item: <input name="item"><br>
        Sale Price: <input name="price"><br>
        GST %: <input name="gst"><br>
        Discount: <input name="discount"><br>
        <button>Calculate</button>
    </form>
    """

# -------------------------
# DAILY PROFIT REPORT
# -------------------------
@app.route("/daily_profit")
def daily_profit():
    today = datetime.now().strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT item, price, gst, discount FROM sales WHERE date=?", (today,))
    sales = c.fetchall()

    total_profit = 0
    result = ""

    for s in sales:
        item, sale_price, gst, discount = s

        c.execute("SELECT price, gst, discount FROM purchase WHERE item=?", (item,))
        row = c.fetchone()

        if row:
            purchase_price, p_gst, p_discount = row
            purchase_final = purchase_price + (purchase_price * p_gst/100) - p_discount
            sale_final = sale_price + (sale_price * gst/100) - discount
            profit = sale_final - purchase_final
            total_profit += profit
            result += f"{item}: Profit {profit:.2f}<br>"

    conn.close()

    return f"""
    <h2>Daily Profit Report ({today})</h2>
    {result}
    <h3>Total Profit: {total_profit:.2f}</h3>
    <a href="/">Back</a>
    """

# -------------------------
# PAYMENTS
# -------------------------
@app.route("/payments", methods=["GET", "POST"])
def payments():
    if request.method == "POST":
        customer = request.form["customer"]
        amount = request.form["amount"]
        status = request.form["status"]

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("INSERT INTO payments VALUES (?,?,?)",
                  (customer, amount, status))
        conn.commit()
        conn.close()

        return redirect(url_for("payments"))

    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM payments")
    rows = c.fetchall()
    conn.close()

    html = "<h2>Customer Payments</h2>"
    html += """
    <form method="post">
        Customer: <input name="customer"><br>
        Amount: <input name="amount"><br>
        Status:
        <select name="status">
            <option>Pending</option>
            <option>Paid</option>
        </select><br>
        <button>Save</button>
    </form>
    <hr>
    """

    for r in rows:
        html += f"{r[0]} - {r[1]} - {r[2]}<br>"

    html += "<br><a href='/'>Back</a>"
    return html

# -------------------------
# REMINDERS
# -------------------------
@app.route("/send_reminders")
def send_reminders():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT * FROM payments WHERE status='Pending'")
    rows = c.fetchall()
    conn.close()

    for r in rows:
        customer, amount, status = r
        print(f"Reminder: {customer} owes {amount}")

    return "<h3>Reminders sent</h3><a href='/'>Back</a>"

# -------------------------
# RUN
# -------------------------
if __name__ == "__main__":
    app.run(debug=True)
