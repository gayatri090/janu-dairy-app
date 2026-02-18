from flask import Flask, request
import sqlite3
import pdfplumber
from datetime import datetime, timedelta

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect("data.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS items (
        name TEXT PRIMARY KEY,
        purchase_price REAL,
        gst REAL,
        discount REAL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS purchases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        due_date TEXT,
        paid INTEGER
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item TEXT,
        sale_price REAL,
        profit REAL
    )
    """)

    conn.commit()
    conn.close()

def save_item(name, price, gst, discount):
    conn = sqlite3.connect("data.db")
    c = conn.cursor()

    c.execute("SELECT purchase_price FROM items WHERE name=?", (name,))
    old = c.fetchone()

    if old and old[0] != price:
        print(f"PRICE ALERT: {name} changed from {old[0]} to {price}")

    c.execute("INSERT OR REPLACE INTO items VALUES (?, ?, ?, ?)",
              (name, price, gst, discount))

    conn.commit()
    conn.close()

def get_item(name):
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("SELECT purchase_price, gst, discount FROM items WHERE name=?", (name,))
    result = c.fetchone()
    conn.close()
    return result if result else (0, 0, 0)

def check_payment_reminders():
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    today = datetime.now().date()

    c.execute("SELECT id, due_date FROM purchases WHERE paid=0")
    rows = c.fetchall()

    for row in rows:
        due = datetime.strptime(row[1], "%Y-%m-%d").date()
        if today > due:
            print(f"PAYMENT REMINDER: Invoice {row[0]} is overdue")

    conn.close()

def read_pdf(file):
    items = []
    with pdfplumber.open(file) as pdf:
        text = ""
        for page in pdf.pages:
            text += page.extract_text() + "\n"

    lines = text.split("\n")
    for line in lines:
        parts = line.split()
        if len(parts) >= 2:
            name = parts[0]
            try:
                price = float(parts[-1])
                items.append((name, price))
            except:
                pass
    return items

@app.route("/")
def home():
    check_payment_reminders()
    return """
    <h2>Janu Dairy App</h2>
    <a href='/purchase'>Upload Purchase PDF</a><br><br>
    <a href='/sale'>Upload Sale PDF</a>
    """

@app.route("/purchase", methods=["GET", "POST"])
def purchase():
    if request.method == "POST":
        file = request.files["pdf"]
        items = read_pdf(file)

        for name, price in items:
            gst = 5
            discount = 0
            save_item(name, price, gst, discount)

        # Save purchase invoice with due date
        conn = sqlite3.connect("data.db")
        c = conn.cursor()
        due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        c.execute("INSERT INTO purchases (date, due_date, paid) VALUES (?, ?, ?)",
                  (datetime.now().strftime("%Y-%m-%d"), due_date, 0))
        conn.commit()
        conn.close()

        return "<h3>Purchase saved</h3><a href='/'>Back</a>"

    return """
    <h3>Upload Purchase PDF</h3>
    <form method="post" enctype="multipart/form-data">
        <input type="file" name="pdf">
        <button type="submit">Upload</button>
    </form>
    """

@app.route("/sale", methods=["GET", "POST"])
def sale():
    if request.method == "POST":
        file = request.files["pdf"]
        items = read_pdf(file)

        total_profit = 0
        rows = ""

        conn = sqlite3.connect("data.db")
        c = conn.cursor()

        for name, sale_price in items:
            purchase_price, gst, discount = get_item(name)

            purchase_net = purchase_price * (1 - discount/100)
            sale_net = sale_price * (1 - discount/100)

            profit = sale_net - purchase_net
            total_profit += profit

            c.execute("INSERT INTO sales (item, sale_price, profit) VALUES (?, ?, ?)",
                      (name, sale_price, profit))

            rows += f"""
            <tr>
                <td>{name}</td>
                <td>{purchase_net}</td>
                <td>{sale_net}</td>
                <td>{profit}</td>
            </tr>
            """

        conn.commit()
        conn.close()

        return f"""
        <h3>Sale Invoice</h3>
        <table border="1" cellpadding="8">
            <tr>
                <th>Item</th>
                <th>Purchase Net</th>
                <th>Sale Net</th>
                <th>Profit</th>
            </tr>
            {rows}
        </table>
        <h2>Total Profit: {total_profit}</h2>
        <a href='/'>Back</a>
        """

    return """
    <h3>Upload Sale PDF</h3>
    <form method="post" enctype="multipart/form-data">
        <input type="file" name="pdf">
        <button type="submit">Upload</button>
    </form>
    """

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
