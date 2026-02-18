from flask import Flask, request
import sqlite3
import pdfplumber
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

DB_NAME = "data.db"


# -----------------------------
# Database Setup
# -----------------------------
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS purchase (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item TEXT,
        price REAL
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer TEXT,
        amount REAL,
        email TEXT,
        status TEXT
    )
    """)

    conn.commit()
    conn.close()


# -----------------------------
# Price Change Checker
# -----------------------------
def check_price_change(cursor, item, new_price):
    cursor.execute(
        "SELECT price FROM purchase WHERE item=? ORDER BY id DESC LIMIT 1",
        (item,))
    row = cursor.fetchone()

    if row:
        old_price = row[0]
        if old_price != new_price:
            return old_price
    return None


# -----------------------------
# PDF Extractor
# -----------------------------
def extract_items_from_pdf(file):
    items = []

    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            lines = text.split("\n")

            for line in lines:
                parts = line.split()

                if len(parts) >= 2:
                    item = parts[0]
                    try:
                        price = float(parts[-1])
                        items.append((item, price))
                    except:
                        continue

    return items


# -----------------------------
# Email Sender
# -----------------------------
def send_email(to_email, amount):
    sender = "your_email@gmail.com"
    password = "your_app_password"

    msg = MIMEText(f"Payment reminder: You have pending amount ₹{amount}")
    msg["Subject"] = "Payment Reminder"
    msg["From"] = sender
    msg["To"] = to_email

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(sender, password)
        server.sendmail(sender, to_email, msg.as_string())
        server.quit()
        return True
    except:
        return False


# -----------------------------
# Home
# -----------------------------
@app.route("/")
def home():
    return """
    <h1>Janu Dairy App</h1>
    <a href="/purchase">Upload Purchase PDF</a><br><br>
    <a href="/sale">Upload Sale PDF</a><br><br>
    <a href="/reminders">Send Payment Reminders</a>
    """


# -----------------------------
# Purchase
# -----------------------------
@app.route("/purchase", methods=["GET", "POST"])
def purchase():
    if request.method == "POST":
        file = request.files["pdf"]
        items = extract_items_from_pdf(file)

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        alerts = []

        for item, price in items:
            old_price = check_price_change(cursor, item, price)

            if old_price is not None:
                alerts.append(f"{item}: {old_price} → {price}")

            cursor.execute(
                "INSERT INTO purchase (item, price) VALUES (?, ?)",
                (item, price)
            )

        conn.commit()
        conn.close()

        if alerts:
            alert_text = "<br>".join(alerts)
            return f"""
            <h2>Price Change Alert</h2>
            {alert_text}
            <br><br>
            <a href="/">Back</a>
            """
        else:
            return """
            <h2>Purchase saved. No price changes.</h2>
            <a href="/">Back</a>
            """

    return """
    <h2>Upload Purchase PDF</h2>
    <form method="post" enctype="multipart/form-data">
        <input type="file" name="pdf">
        <button type="submit">Upload</button>
    </form>
    """


# -----------------------------
# Sale + Profit + Payment Save
# -----------------------------
@app.route("/sale", methods=["GET", "POST"])
def sale():
    if request.method == "POST":
        file = request.files["pdf"]
        customer = request.form.get("customer", "Unknown")
        email = request.form.get("email", "")

        sale_items = extract_items_from_pdf(file)

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        total_profit = 0
        total_amount = 0
        result_text = ""

        for item, sale_price in sale_items:
            total_amount += sale_price

            cursor.execute(
                "SELECT price FROM purchase WHERE item=? ORDER BY id DESC LIMIT 1",
                (item,))
            row = cursor.fetchone()

            if row:
                purchase_price = row[0]
                profit = sale_price - purchase_price
                total_profit += profit
            else:
                profit = 0

            result_text += f"{item}: Profit {profit}<br>"

        # Save payment record
        cursor.execute("""
            INSERT INTO payments (customer, amount, email, status)
            VALUES (?, ?, ?, ?)
        """, (customer, total_amount, email, "pending"))

        conn.commit()
        conn.close()

        return f"""
        <h2>Sale Result</h2>
        {result_text}
        <br>
        <h2>Total Profit: {total_profit}</h2>
        <a href="/">Back</a>
        """

    return """
    <h2>Upload Sale PDF</h2>
    <form method="post" enctype="multipart/form-data">
        Customer Name: <input type="text" name="customer"><br><br>
        Customer Email: <input type="text" name="email"><br><br>
        <input type="file" name="pdf">
        <button type="submit">Upload</button>
    </form>
    """


# -----------------------------
# Payment Reminders
# -----------------------------
@app.route("/reminders")
def reminders():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT customer, amount, email FROM payments WHERE status='pending'")
    rows = cursor.fetchall()

    result = ""

    for customer, amount, email in rows:
        if email:
            success = send_email(email, amount)
            if success:
                result += f"Reminder sent to {customer} ({email})<br>"
            else:
                result += f"Failed to send to {customer}<br>"
        else:
            result += f"No email for {customer}<br>"

    conn.close()

    return f"""
    <h2>Reminder Results</h2>
    {result}
    <br>
    <a href="/">Back</a>
    """


# -----------------------------
# Start App
# -----------------------------
if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5000)
