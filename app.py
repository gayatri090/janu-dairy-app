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
        base_price REAL,
        gst REAL,
        discount REAL
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
        "SELECT base_price FROM purchase WHERE item=? ORDER BY id DESC LIMIT 1",
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
    <h1>Jaanu_mm</h1>
    <a href="/purchase">Upload Purchase PDF</a><br><br>
    <a href="/sale">Upload Sale PDF</a><br><br>
    <a href="/payments">Customer Payments</a><br><br>
    <a href="/reminders">Send Payment Reminders</a>
    """


# -----------------------------
# Purchase Upload
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
            gst = 5.0
            discount = 0.0

            old_price = check_price_change(cursor, item, price)
            if old_price is not None:
                alerts.append(f"{item}: {old_price} → {price}")

            cursor.execute("""
                INSERT INTO purchase (item, base_price, gst, discount)
                VALUES (?, ?, ?, ?)
            """, (item, price, gst, discount))

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
# Sale Upload + Profit
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
        rows = ""

        for item, sale_price in sale_items:
            total_amount += sale_price

            cursor.execute("""
                SELECT base_price, gst, discount
                FROM purchase
                WHERE item=?
                ORDER BY id DESC
                LIMIT 1
            """, (item,))
            row = cursor.fetchone()

            if row:
                base_price, gst, discount = row

                purchase_no_gst = base_price * (1 - discount/100)
                purchase_with_gst = purchase_no_gst * (1 + gst/100)

                sale_no_gst = sale_price * (1 - discount/100)
                sale_with_gst = sale_no_gst * (1 + gst/100)

                profit = sale_no_gst - purchase_no_gst
                total_profit += profit
            else:
                discount = 0
                purchase_no_gst = 0
                purchase_with_gst = 0
                sale_no_gst = sale_price
                sale_with_gst = sale_price
                profit = 0

            rows += f"""
            <tr>
                <td>{item}</td>
                <td>{discount}</td>
                <td>{round(purchase_no_gst,2)}</td>
                <td>{round(purchase_with_gst,2)}</td>
                <td>{round(sale_no_gst,2)}</td>
                <td>{round(sale_with_gst,2)}</td>
                <td>{round(profit,2)}</td>
            </tr>
            """

        # Save payment
        cursor.execute("""
            INSERT INTO payments (customer, amount, email, status)
            VALUES (?, ?, ?, ?)
        """, (customer, total_amount, email, "pending"))

        conn.commit()
        conn.close()

        return f"""
        <h2>Sale Invoice</h2>
        <table border="1" cellpadding="8">
            <tr>
                <th>Item</th>
                <th>Discount %</th>
                <th>Purchase (No GST)</th>
                <th>Purchase (With GST)</th>
                <th>Sale (No GST)</th>
                <th>Sale (With GST)</th>
                <th>Profit</th>
            </tr>
            {rows}
        </table>
        <h2>Total Profit: {round(total_profit,2)}</h2>
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
# Customer Payment Screen
# -----------------------------
@app.route("/payments")
def payments():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT id, customer, amount, status FROM payments")
    rows = cursor.fetchall()

    table_rows = ""
    for row in rows:
        payment_id, customer, amount, status = row

        if status == "pending":
            action = f'<a href="/mark_paid/{payment_id}">Mark Paid</a>'
        else:
            action = "Paid"

        table_rows += f"""
        <tr>
            <td>{customer}</td>
            <td>{amount}</td>
            <td>{status}</td>
            <td>{action}</td>
        </tr>
        """

    conn.close()

    return f"""
    <h2>Customer Payments</h2>
    <table border="1" cellpadding="8">
        <tr>
            <th>Customer</th>
            <th>Amount</th>
            <th>Status</th>
            <th>Action</th>
        </tr>
        {table_rows}
    </table>
    <br>
    <a href="/">Back</a>
    """


# -----------------------------
# Mark Payment as Paid
# -----------------------------
@app.route("/mark_paid/<int:payment_id>")
def mark_paid(payment_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE payments
        SET status='paid'
        WHERE id=?
    """, (payment_id,))

    conn.commit()
    conn.close()

    return """
    <h2>Payment marked as paid</h2>
    <a href="/payments">Back to Payments</a>
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
