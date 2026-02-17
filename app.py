from flask import Flask, request, render_template_string
import sqlite3
import pdfplumber

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS items (
        name TEXT PRIMARY KEY,
        purchase_price REAL
    )
    """)
    conn.commit()
    conn.close()

def save_item(name, price):
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO items VALUES (?, ?)", (name, price))
    conn.commit()
    conn.close()

def get_price(name):
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("SELECT purchase_price FROM items WHERE name=?", (name,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 0

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
            save_item(name, price)

        return "<h3>Purchase saved successfully</h3><a href='/'>Back</a>"

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
        result = ""

        for name, sale_price in items:
            purchase_price = get_price(name)
            profit = sale_price - purchase_price
            total_profit += profit
            result += f"{name}: Profit {profit}<br>"

        return f"""
        <h3>Sale Result</h3>
        {result}
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
