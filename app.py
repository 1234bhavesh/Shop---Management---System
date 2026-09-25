import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from datetime import date
from database import get_connection, create_tables
import urllib.parse

# ---------- SIMPLE LOGIN ----------
def check_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if not st.session_state.logged_in:
        st.title("🔒 Shop Management System - Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Login")

            if submitted:
                # Change these credentials to whatever you and your father want
                if username == st.secrets["username"] and password == st.secrets["password"]:
                    st.session_state.logged_in = True
                    st.rerun()
                else:
                    st.error("Incorrect username or password.")
        st.stop()  # This stops the rest of the app from loading until logged in

check_login()

# Make sure tables exist every time the app starts
create_tables()

# Logout button
with st.sidebar:
    if st.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.rerun()

st.set_page_config(page_title="Shop Management System", layout="wide")
st.title("🏪 Building Material & Plywood Shop - Management System")

# Sidebar menu to navigate between sections
st.sidebar.markdown(
    "<h2 style='color:#1E5B94; margin-bottom:0;'>🏪 Sai Building</h2>"
    "<p style='margin-top:0; color:#1E5B94;'>Material - Dabhadi</p>"
    "<hr>",
    unsafe_allow_html=True
)
menu = st.sidebar.selectbox("Menu", [
    "Dashboard",
    "Add Customer", "View Customers","Manage Customers", "Customer Details",
    "Add Product", "View Products",
    "Record Sale", "View Sales", "Record Payment", "Generate Bill", "Generate Quotation",
    "Add Labour", "Manage Labour", "Labour Details",
    "Mark Attendance", "View Attendance",
    "Manage Vehicles", "Vehicle Expense/Details",
    "Settings"
])

# ---------- ADD CUSTOMER ----------
# ---------- DASHBOARD ----------
if menu == "Dashboard":
    st.markdown(
        "<div style='background:#5b2a00; padding:15px; border-radius:8px; margin-bottom:15px;'>"
        "<h1 style='color:white; margin:0;'>📊 Sai Building Material & Plywood — Business Dashboard</h1>"
        f"<p style='color:#f0e6d6; margin:0;'>Live overview as of {date.today().strftime('%d %B %Y')}</p>"
        "</div>",
        unsafe_allow_html=True
    )
    st.header("📊 Business Dashboard")

    conn = get_connection()
    sales_df = pd.read_sql_query("""
        SELECT sales.*, customers.name AS customer, products.name AS product
        FROM sales
        JOIN customers ON sales.customer_id = customers.id
        JOIN products ON sales.product_id = products.id
    """, conn)
    products_df = pd.read_sql_query("SELECT * FROM products", conn)
    attendance_df = pd.read_sql_query("SELECT * FROM attendance", conn)
    payments_df = pd.read_sql_query("SELECT * FROM payments", conn)

    try:
        vehicle_expenses_df = pd.read_sql_query("SELECT * FROM vehicle_expenses", conn)
        vehicle_earnings_df = pd.read_sql_query("SELECT * FROM vehicle_earnings", conn)
    except Exception:
        vehicle_expenses_df = pd.DataFrame()
        vehicle_earnings_df = pd.DataFrame()

    conn.close()

    # ---- TOP-LEVEL METRICS ----
    total_revenue = sales_df["sale_price"].sum() if not sales_df.empty else 0
    total_profit = sales_df["profit"].sum() if not sales_df.empty else 0
    total_paid_at_sale = sales_df["amount_paid"].sum() if not sales_df.empty else 0
    total_extra_payments = payments_df["amount"].sum() if not payments_df.empty else 0
    total_dues = total_revenue - (total_paid_at_sale + total_extra_payments)

    total_labour_paid = attendance_df["amount_paid"].sum() if not attendance_df.empty else 0

    total_vehicle_expense = vehicle_expenses_df["amount"].sum() if not vehicle_expenses_df.empty else 0
    total_vehicle_earning = vehicle_earnings_df["amount"].sum() if not vehicle_earnings_df.empty else 0
    vehicle_net = total_vehicle_earning - total_vehicle_expense

    st.subheader("💰 Overall Business Summary")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Revenue", f"₹{total_revenue:,.2f}")
    col2.metric("Total Sales Profit", f"₹{total_profit:,.2f}")
    col3.metric("Pending Customer Dues", f"₹{total_dues:,.2f}")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Labour Paid", f"₹{total_labour_paid:,.2f}")
    col2.metric("Vehicle Net (Earnings-Expenses)", f"₹{vehicle_net:,.2f}")
    net_business_profit = total_profit - total_labour_paid + vehicle_net
    col3.metric("Net Business Profit", f"₹{net_business_profit:,.2f}")

    st.markdown("---")

    # ---- LOW STOCK ALERTS ----
    st.subheader("⚠️ Low Stock Alerts")
    if products_df.empty:
        st.info("No products added yet.")
    else:
        low_stock = products_df[products_df["current_stock"] <= products_df["reorder_level"]]
        if low_stock.empty:
            st.success("All products are sufficiently stocked.")
        else:
            st.warning(f"{len(low_stock)} product(s) need reordering:")
            st.dataframe(low_stock[["name", "company", "current_stock", "reorder_level"]], use_container_width=True)

    st.markdown("---")

    # ---- TOP CUSTOMERS ----
    st.subheader("🏆 Top Customers by Purchase Value")
    if sales_df.empty:
        st.info("No sales recorded yet.")
    else:
        top_customers = sales_df.groupby("customer")["sale_price"].sum().sort_values(ascending=False).reset_index()
        top_customers.columns = ["Customer", "Total Purchased (₹)"]
        st.dataframe(top_customers.head(5), use_container_width=True)
        st.bar_chart(top_customers.head(5).set_index("Customer"))

    st.markdown("---")

    # ---- TOP SELLING PRODUCTS ----
    st.subheader("📦 Top Selling Products")
    if sales_df.empty:
        st.info("No sales recorded yet.")
    else:
        top_products = sales_df.groupby("product")["quantity"].sum().sort_values(ascending=False).reset_index()
        top_products.columns = ["Product", "Total Quantity Sold"]
        st.dataframe(top_products.head(5), use_container_width=True)
        st.bar_chart(top_products.head(5).set_index("Product"))

    st.markdown("---")

    # ---- MONTHLY REVENUE TREND ----
    st.subheader("📈 Revenue Trend (by month)")
    if sales_df.empty:
        st.info("No sales recorded yet.")
    else:
        sales_df["sale_date"] = pd.to_datetime(sales_df["sale_date"])
        sales_df["month"] = sales_df["sale_date"].dt.to_period("M").astype(str)
        monthly = sales_df.groupby("month")["sale_price"].sum().reset_index()
        monthly.columns = ["Month", "Revenue (₹)"]
        st.line_chart(monthly.set_index("Month"))
elif menu == "Add Customer":
    st.header("Add New Customer")

    with st.form("customer_form", clear_on_submit=True):
        name = st.text_input("Customer Name")
        phone = st.text_input("Phone Number")
        address = st.text_area("Address")
        submitted = st.form_submit_button("Save Customer")

        if submitted:
            if name.strip() == "":
                st.error("Name is required.")
            else:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO customers (name, phone, address) VALUES (?, ?, ?)",
                    (name, phone, address)
                )
                conn.commit()
                conn.close()
                st.success(f"Customer '{name}' added successfully!")

# ---------- VIEW CUSTOMERS ----------
elif menu == "View Customers":
    st.header("All Customers")

    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM customers", conn)
    conn.close()

    if df.empty:
        st.info("No customers added yet.")
    else:
        st.dataframe(df, use_container_width=True)

# ---------- CUSTOMER DETAILS ----------
elif menu == "Customer Details":
    st.header("Customer Details")

    conn = get_connection()
    customers_df = pd.read_sql_query("SELECT * FROM customers", conn)

    if customers_df.empty:
        st.info("No customers yet.")
    else:
        selected_customer = st.selectbox("Select Customer", customers_df["name"])
        cust_row = customers_df[customers_df["name"] == selected_customer].iloc[0]
        customer_id = int(cust_row["id"])

        st.subheader(f"📇 {cust_row['name']}")
        col1, col2 = st.columns(2)
        col1.write(f"**Phone:** {cust_row['phone']}")
        col2.write(f"**Address:** {cust_row['address']}")

        # Purchase history
        sales_query = """
            SELECT products.name AS product, sales.quantity, sales.sale_price AS amount,
                   sales.amount_paid, sales.profit, sales.sale_date
            FROM sales
            JOIN products ON sales.product_id = products.id
            WHERE sales.customer_id = ?
            ORDER BY sales.sale_date DESC
        """
        purchases_df = pd.read_sql_query(sales_query, conn, params=(customer_id,))

        # Extra payments made later (not tied to a specific sale)
        payments_query = "SELECT amount, payment_date, note FROM payments WHERE customer_id = ? ORDER BY payment_date DESC"
        payments_df = pd.read_sql_query(payments_query, conn, params=(customer_id,))
        conn.close()

        if purchases_df.empty:
            st.info("No purchases recorded for this customer yet.")
        else:
            st.subheader("Purchase History")
            purchases_df["due"] = purchases_df["amount"] - purchases_df["amount_paid"]
            st.dataframe(purchases_df, use_container_width=True)

            total_purchased = purchases_df["amount"].sum()
            total_paid_at_sale = purchases_df["amount_paid"].sum()
            total_extra_payments = payments_df["amount"].sum() if not payments_df.empty else 0

            total_paid = total_paid_at_sale + total_extra_payments
            remaining_due = total_purchased - total_paid

            st.subheader("💰 Payment Summary")
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Purchased", f"₹{total_purchased:,.2f}")
            col2.metric("Total Paid", f"₹{total_paid:,.2f}")
            col3.metric("Remaining Due", f"₹{remaining_due:,.2f}",
                        delta=None if remaining_due == 0 else "⚠️ Pending",
                        delta_color="inverse")

        if not payments_df.empty:
            st.subheader("Additional Payments Received")
            st.dataframe(payments_df, use_container_width=True)

# ---------- ADD PRODUCT ----------
elif menu == "Add Product":
    st.header("Add New Product")

    with st.form("product_form", clear_on_submit=True):
        name = st.text_input("Product Name (e.g., Ambuja Cement 50kg)")
        company = st.selectbox("Company", ["Ambuja", "ACC", "Concrete Plus", "Rajuri", "Uma", "Kamdhenu", "Other"])
        category = st.selectbox("Category", ["Cement", "Steel", "Other Material"])
        unit = st.selectbox("Unit", ["bag", "ton", "piece", "kg"])
        cost_price = st.number_input("Cost Price (per unit)", min_value=0.0, step=1.0)
        selling_price = st.number_input("Selling Price (per unit)", min_value=0.0, step=1.0)
        current_stock = st.number_input("Current Stock", min_value=0.0, step=1.0)
        reorder_level = st.number_input("Reorder Level (low stock warning)", min_value=0.0, step=1.0)

        submitted = st.form_submit_button("Save Product")

        if submitted:
            if name.strip() == "":
                st.error("Product name is required.")
            else:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """INSERT INTO products
                       (name, company, category, unit, cost_price, selling_price, current_stock, reorder_level)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (name, company, category, unit, cost_price, selling_price, current_stock, reorder_level)
                )
                conn.commit()
                conn.close()
                st.success(f"Product '{name}' added successfully!")

# ---------- VIEW PRODUCTS ----------
elif menu == "View Products":
    st.header("All Products / Stock")

    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM products", conn)
    conn.close()

    if df.empty:
        st.info("No products added yet.")
    else:
        low_stock = df[df["current_stock"] <= df["reorder_level"]]
        if not low_stock.empty:
            st.warning(f"⚠️ {len(low_stock)} product(s) are at or below reorder level!")

        st.dataframe(df, use_container_width=True)

# ---------- RECORD SALE ----------
elif menu == "Record Sale":
    st.header("Record New Sale")

    conn = get_connection()
    customers_df = pd.read_sql_query("SELECT id, name FROM customers", conn)
    products_df = pd.read_sql_query("SELECT id, name, selling_price, cost_price, current_stock FROM products", conn)
    conn.close()

    if customers_df.empty or products_df.empty:
        st.warning("Please add at least one customer and one product before recording a sale.")
    else:
        with st.form("sale_form", clear_on_submit=True):
            customer_name = st.selectbox("Customer", customers_df["name"])
            product_name = st.selectbox("Product", products_df["name"])
            quantity = st.number_input("Quantity Sold", min_value=0.0, step=1.0)
            amount_paid_now = st.number_input("Amount Paid Now (₹) — leave 0 if fully on credit", min_value=0.0, step=100.0)
            sale_date = st.date_input("Sale Date", value=date.today())

            submitted = st.form_submit_button("Record Sale")

            if submitted:
                if quantity <= 0:
                    st.error("Quantity must be greater than 0.")
                else:
                    customer_id = int(customers_df[customers_df["name"] == customer_name]["id"].values[0])
                    product_row = products_df[products_df["name"] == product_name].iloc[0]
                    product_id = int(product_row["id"])
                    selling_price = float(product_row["selling_price"])
                    cost_price = float(product_row["cost_price"])
                    available_stock = float(product_row["current_stock"])

                    if quantity > available_stock:
                        st.error(f"Not enough stock! Only {available_stock} units of '{product_name}' available.")
                    else:
                        total_sale_amount = quantity * selling_price
                        profit = (selling_price - cost_price) * quantity

                        conn = get_connection()
                        cursor = conn.cursor()

                        cursor.execute(
                            """INSERT INTO sales (customer_id, product_id, quantity, sale_price, amount_paid, sale_date, profit)
                               VALUES (?, ?, ?, ?, ?, ?, ?)""",
                            (customer_id, product_id, quantity, total_sale_amount, amount_paid_now, str(sale_date), profit)
                        )

                        cursor.execute(
                            "UPDATE products SET current_stock = current_stock - ? WHERE id = ?",
                            (quantity, product_id)
                        )

                        conn.commit()
                        conn.close()

                        due_now = total_sale_amount - amount_paid_now
                        if due_now > 0:
                            st.success(f"Sale recorded! Total: ₹{total_sale_amount:.2f}, Paid: ₹{amount_paid_now:.2f}, Due: ₹{due_now:.2f}")
                        else:
                            st.success(f"Sale recorded! Total: ₹{total_sale_amount:.2f} — fully paid.")

# ---------- VIEW SALES ----------
elif menu == "View Sales":
    st.header("Sales History")

    conn = get_connection()
    query = """
        SELECT sales.id, customers.name AS customer, products.name AS product,
               sales.quantity, sales.sale_price AS total_amount, sales.profit, sales.sale_date
        FROM sales
        JOIN customers ON sales.customer_id = customers.id
        JOIN products ON sales.product_id = products.id
        ORDER BY sales.sale_date DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        st.info("No sales recorded yet.")
    else:
        st.dataframe(df, use_container_width=True)

        total_revenue = df["total_amount"].sum()
        total_profit = df["profit"].sum()

        col1, col2 = st.columns(2)
        col1.metric("Total Revenue", f"₹{total_revenue:,.2f}")
        col2.metric("Total Profit", f"₹{total_profit:,.2f}")

# ---------- RECORD PAYMENT ----------
elif menu == "Record Payment":
    st.header("Record Customer Payment (Clear Dues)")

    conn = get_connection()
    customers_df = pd.read_sql_query("SELECT id, name FROM customers", conn)
    conn.close()

    if customers_df.empty:
        st.warning("Please add a customer first.")
    else:
        with st.form("payment_form", clear_on_submit=True):
            customer_name = st.selectbox("Customer", customers_df["name"])
            amount = st.number_input("Amount Received (₹)", min_value=0.0, step=100.0)
            payment_date = st.date_input("Payment Date", value=date.today())
            note = st.text_input("Note (optional)")

            submitted = st.form_submit_button("Save Payment")

            if submitted:
                if amount <= 0:
                    st.error("Amount must be greater than 0.")
                else:
                    customer_id = int(customers_df[customers_df["name"] == customer_name]["id"].values[0])
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "INSERT INTO payments (customer_id, amount, payment_date, note) VALUES (?, ?, ?, ?)",
                        (customer_id, amount, str(payment_date), note)
                    )
                    conn.commit()
                    conn.close()
                    st.success(f"Payment of ₹{amount:.2f} recorded for {customer_name}.")

# ---------- GENERATE BILL ----------
elif menu == "Generate Bill":
    st.header("🧾 Generate Customer Bill")

    conn = get_connection()
    customers_df = pd.read_sql_query("SELECT * FROM customers", conn)

    if customers_df.empty:
        st.info("No customers yet.")
    else:
        selected_customer = st.selectbox("Select Customer", customers_df["name"])
        cust_row = customers_df[customers_df["name"] == selected_customer].iloc[0]
        customer_id = int(cust_row["id"])

        sales_query = """
            SELECT sales.id, products.name AS product, products.unit, sales.quantity,
                   sales.sale_price AS amount, sales.amount_paid, sales.sale_date
            FROM sales
            JOIN products ON sales.product_id = products.id
            WHERE sales.customer_id = ?
            ORDER BY sales.sale_date DESC
        """
        purchases_df = pd.read_sql_query(sales_query, conn, params=(customer_id,))
        conn.close()

        if purchases_df.empty:
            st.info("No purchases found for this customer.")
        else:
            st.subheader("Select items to include in this bill")
            selected_ids = []
            for _, row in purchases_df.iterrows():
                label = f"{row['sale_date']} — {row['product']} x {row['quantity']} = ₹{row['amount']:.2f} (Paid: ₹{row['amount_paid']:.2f})"
                if st.checkbox(label, key=f"bill_{row['id']}"):
                    selected_ids.append(row["id"])

            st.markdown("---")
            col1, col2 = st.columns(2)
            bill_no = col1.text_input("Bill No.", value=f"SB-{date.today().strftime('%Y%m%d')}-{customer_id}")
            bill_date = col2.date_input("Bill Date", value=date.today())

            st.subheader("Delivery Details")
            col1, col2 = st.columns(2)
            contact_phone = col1.text_input("Contact Phone Number", value=cust_row['phone'])
            delivery_location = col2.text_input("Delivery Location (village/area)")

            st.subheader("Additional Charges (optional)")
            col1, col2 = st.columns(2)
            labour_charge = col1.number_input("Labour Charge (₹)", min_value=0.0, step=50.0)
            vehicle_charge = col2.number_input("Vehicle/Transport Charge (₹)", min_value=0.0, step=50.0)

            apply_gst = st.checkbox("Add GST to this bill")
            gst_percent = 0.0
            if apply_gst:
                gst_percent = st.selectbox("GST Rate (%)", [5, 12, 18, 28], index=2)

            payment_mode = st.selectbox("Payment Mode", ["Cash", "UPI", "Card", "Bank Transfer"])

            if st.button("Generate Bill Preview") and selected_ids:
                bill_items = purchases_df[purchases_df["id"].isin(selected_ids)].reset_index(drop=True)

                material_total = bill_items["amount"].sum()
                material_paid = bill_items["amount_paid"].sum()
                subtotal = material_total + labour_charge + vehicle_charge
                gst_amount = (subtotal * gst_percent / 100) if apply_gst else 0
                grand_total = subtotal + gst_amount
                balance_due = grand_total - material_paid

                items_rows = ""
                for i, item in bill_items.iterrows():
                    rate = item['amount'] / item['quantity'] if item['quantity'] else 0
                    items_rows += (
                        "<tr>"
                        f"<td class='c'>{i+1}</td>"
                        f"<td>{item['product']}</td>"
                        f"<td class='c'>{item['unit']}</td>"
                        f"<td class='c'>{item['quantity']}</td>"
                        f"<td class='r'>{rate:.2f}</td>"
                        f"<td class='r'>{item['amount']:.2f}</td>"
                        "</tr>"
                    )

                delivery_line = delivery_location if delivery_location else "Same as address"

                bill_document = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Bill - {bill_no}</title>
<style>
  @page {{ size: A4; margin: 12mm; }}
  * {{ box-sizing: border-box; font-family: Arial, Helvetica, sans-serif; }}
  body {{ margin: 0; padding: 0; font-size: 13px; color: #000; }}
  table {{ border-collapse: collapse; width: 100%; }}
  .outer {{ border: 2px solid #333; padding: 15px; max-width: 750px; margin: auto; }}
  .center {{ text-align: center; }}
  .r {{ text-align: right; }}
  .c {{ text-align: center; }}
  .shopname {{ font-size: 22px; font-weight: bold; color: #5b2a00; margin: 0; }}
  .tagline {{ font-size: 11px; margin: 2px 0; }}
  .invoice-band {{ background: #3a1a00; color: #fff; padding: 5px; font-size: 15px; font-weight: bold; }}
  .box {{ border: 1px solid #333; padding: 6px; }}
  .box-title {{ background: #3a1a00; color: #fff; padding: 2px 6px; font-size: 12px; font-weight: bold; }}
  .items th, .items td {{ border: 1px solid #333; padding: 4px 6px; font-size: 12px; }}
  .items th {{ background: #f0e6d6; }}
  .totals td {{ padding: 3px 6px; font-size: 12px; }}
  .totals .grand {{ font-weight: bold; background: #f0e6d6; }}
  .sign td {{ padding-top: 30px; font-size: 12px; }}
  .terms {{ font-size: 10px; }}
</style>
</head>
<body>
<div class="outer">

  <table>
    <tr><td class="center">
      <p class="shopname">SAI BUILDING MATERIAL & PLYWOOD</p>
      <p class="tagline"><b>DABHADI</b></p>
      <p class="tagline">CEMENT | STEEL | CONCRETE PLUS | ALL BUILDING MATERIALS</p>
      <p class="tagline">Dabhadi, Malegaon</p>
    </td></tr>
  </table>

  <hr style="border-top:2px solid #333; margin:6px 0;">

  <table>
    <tr><td class="invoice-band center">BILL / INVOICE</td></tr>
  </table>

  <table style="margin-top:6px;">
    <tr>
      <td><b>Bill No.:</b> {bill_no}</td>
      <td class="r"><b>Date:</b> {bill_date}</td>
    </tr>
  </table>

  <table style="margin-top:8px;">
    <tr><td class="box">
      <span class="box-title">Customer Details</span><br>
      <b>Customer Name:</b> {cust_row['name']}<br>
      <b>Address:</b> {cust_row['address']}<br>
      <b>Delivery Location:</b> {delivery_line}<br>
      <b>Mobile No.:</b> {contact_phone}
    </td></tr>
  </table>

  <table class="items" style="margin-top:8px;">
    <tr>
      <th style="width:8%;">Sr No.</th>
      <th style="width:34%;">Item Name</th>
      <th style="width:12%;">Unit</th>
      <th style="width:12%;">Qty</th>
      <th style="width:17%;">Rate (Rs)</th>
      <th style="width:17%;">Amount (Rs)</th>
    </tr>
    {items_rows}
  </table>

  <table class="totals" style="margin-top:8px;">
    <tr><td style="width:70%;"></td><td>Material Total</td><td class="r">Rs {material_total:.2f}</td></tr>
    <tr><td></td><td>Labour Charge</td><td class="r">Rs {labour_charge:.2f}</td></tr>
    <tr><td></td><td>Transport Charge</td><td class="r">Rs {vehicle_charge:.2f}</td></tr>
    <tr><td></td><td>GST ({gst_percent}%)</td><td class="r">Rs {gst_amount:.2f}</td></tr>
    <tr class="grand"><td></td><td>GRAND TOTAL</td><td class="r">Rs {grand_total:.2f}</td></tr>
  </table>

  <table style="margin-top:8px;">
    <tr><td class="box">
      <span class="box-title">Payment Details</span><br>
      <b>Payment Mode:</b> {payment_mode} &nbsp;&nbsp;
      <b>Paid:</b> Rs {material_paid:.2f} &nbsp;&nbsp;
      <b>Balance:</b> Rs {balance_due:.2f}
    </td></tr>
  </table>

  <table class="terms" style="margin-top:6px;">
    <tr><td>
      <b>Terms:</b><br>
      1) Goods once sold will not be taken back.<br>
      2) Please check material before leaving the shop.<br>
      3) Payment due within the agreed period.
    </td></tr>
  </table>

  <table class="sign">
    <tr>
      <td style="width:50%;">_______________________<br>Customer Signature</td>
      <td class="r">_______________________<br>Authorized Signature</td>
    </tr>
  </table>

  <table>
    <tr><td class="center" style="font-style:italic; padding-top:8px;">Thank You! Visit Again!</td></tr>
  </table>

</div>
</body>
</html>"""

                st.success("Bill generated successfully!")
                st.download_button(
                    label="⬇️ Download Bill (open it, then press Ctrl+P → Save as PDF)",
                    data=bill_document,
                    file_name=f"{bill_no}.html",
                    mime="text/html"
                )

                clean_phone = contact_phone.replace(" ", "").replace("-", "")
                if len(clean_phone) == 10:
                    clean_phone = "91" + clean_phone

                whatsapp_message = (
                    f"Hello {cust_row['name']}, here is your bill {bill_no} from "
                    f"Sai Building Material. Total: Rs {grand_total:.2f}, "
                    f"Balance Due: Rs {balance_due:.2f}."
                )
                encoded_message = urllib.parse.quote(whatsapp_message)
                whatsapp_url = f"https://wa.me/{clean_phone}?text={encoded_message}"

                st.markdown(
                    f"[📲 Open WhatsApp Chat with {cust_row['name']}]({whatsapp_url})",
                    unsafe_allow_html=True
                )
                st.caption("Download the bill above, open it in your browser, press Ctrl+P → Save as PDF, then attach that PDF in the WhatsApp chat opened above.")

                st.components.v1.html(bill_document, height=900, scrolling=True)
# ---------- ADD LABOUR ----------
elif menu == "Add Labour":
    st.header("Add Labour")

    with st.form("labour_form", clear_on_submit=True):
        name = st.text_input("Labour Name")
        submitted = st.form_submit_button("Save Labour")

        if submitted:
            if name.strip() == "":
                st.error("Name is required.")
            else:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO labour (name) VALUES (?)", (name,))
                conn.commit()
                conn.close()
                st.success(f"Labour '{name}' added successfully!")

# ---------- MANAGE LABOUR ----------
elif menu == "Manage Labour":
    st.header("Manage Labour")

    conn = get_connection()
    labour_df = pd.read_sql_query("SELECT * FROM labour", conn)
    conn.close()

    if labour_df.empty:
        st.info("No labour added yet. Go to 'Add Labour' first.")
    else:
        st.subheader("Current Labour")
        st.dataframe(labour_df, use_container_width=True)

        st.subheader("Remove Labour")
        st.caption("Note: removing labour keeps their past attendance/payment history, they just won't appear for new entries.")
        labour_to_remove = st.selectbox("Select labour to remove", labour_df["name"])

        if st.button("Remove Selected Labour", type="primary"):
            labour_id = int(labour_df[labour_df["name"] == labour_to_remove]["id"].values[0])
            conn = get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM labour WHERE id = ?", (labour_id,))
            conn.commit()
            conn.close()
            st.success(f"'{labour_to_remove}' removed from active labour list.")
            st.rerun()

# ---------- LABOUR DETAILS ----------
elif menu == "Labour Details":
    st.header("Labour Details")

    conn = get_connection()
    labour_df = pd.read_sql_query("SELECT * FROM labour", conn)

    if labour_df.empty:
        st.info("No labour added yet.")
    else:
        selected_labour = st.selectbox("Select Labour", labour_df["name"])
        labour_row = labour_df[labour_df["name"] == selected_labour].iloc[0]
        labour_id = int(labour_row["id"])

        st.subheader(f"👷 {labour_row['name']}")

        query = """
            SELECT attendance_date, present, work_done, amount_paid
            FROM attendance
            WHERE labour_id = ?
            ORDER BY attendance_date DESC
        """
        history_df = pd.read_sql_query(query, conn, params=(labour_id,))
        conn.close()

        if history_df.empty:
            st.info("No attendance records for this labour yet.")
        else:
            st.dataframe(history_df, use_container_width=True)

            total_paid = history_df["amount_paid"].sum()
            days_present = history_df["present"].sum()
            total_days = len(history_df)

            col1, col2, col3 = st.columns(3)
            col1.metric("Total Paid", f"₹{total_paid:,.2f}")
            col2.metric("Days Present", int(days_present))
            col3.metric("Total Days Recorded", total_days)

# ---------- MARK ATTENDANCE ----------
elif menu == "Mark Attendance":
    st.header("Mark Daily Attendance & Payment")

    conn = get_connection()
    labour_df = pd.read_sql_query("SELECT id, name FROM labour", conn)
    conn.close()

    if labour_df.empty:
        st.warning("Please add labour first.")
    else:
        attendance_date = st.date_input("Attendance Date", value=date.today())
        st.write("Enter details for each labour:")

        entries = {}
        for _, row in labour_df.iterrows():
            st.markdown(f"**{row['name']}**")
            col1, col2, col3 = st.columns(3)
            present = col1.checkbox("Present", value=True, key=f"present_{row['id']}")
            work_done = col2.text_input("Work done", key=f"work_{row['id']}")
            amount_paid = col3.number_input("Amount paid (₹)", min_value=0.0, step=10.0, key=f"pay_{row['id']}")
            entries[row["id"]] = (present, work_done, amount_paid)

        if st.button("Save Attendance"):
            conn = get_connection()
            cursor = conn.cursor()
            for labour_id, (present, work_done, amount_paid) in entries.items():
                cursor.execute(
                    """INSERT INTO attendance (labour_id, attendance_date, present, work_done, amount_paid)
                       VALUES (?, ?, ?, ?, ?)""",
                    (labour_id, str(attendance_date), 1 if present else 0, work_done, amount_paid)
                )
            conn.commit()
            conn.close()
            st.success(f"Attendance saved for {attendance_date}!")

# ---------- VIEW ATTENDANCE ----------
elif menu == "View Attendance":
    st.header("Attendance & Payment History")

    conn = get_connection()
    query = """
        SELECT labour.name, attendance.attendance_date, attendance.present,
               attendance.work_done, attendance.amount_paid
        FROM attendance
        JOIN labour ON attendance.labour_id = labour.id
        ORDER BY attendance.attendance_date DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    if df.empty:
        st.info("No attendance records yet.")
    else:
        st.subheader("Overall Summary")
        summary = df.groupby("name")["amount_paid"].sum().reset_index()
        summary.columns = ["Labour Name", "Total Paid (₹)"]
        st.dataframe(summary, use_container_width=True)

        st.subheader("Detailed Records (per labour)")
        for labour_name in df["name"].unique():
            with st.expander(f"👷 {labour_name}"):
                person_df = df[df["name"] == labour_name].drop(columns=["name"])
                st.dataframe(person_df, use_container_width=True)

                total_paid = person_df["amount_paid"].sum()
                days_present = person_df["present"].sum()
                total_days = len(person_df)

                col1, col2, col3 = st.columns(3)
                col1.metric("Total Paid", f"₹{total_paid:,.2f}")
                col2.metric("Days Present", int(days_present))
                col3.metric("Total Days Recorded", total_days)

# ---------- MANAGE VEHICLES (Add + View + Remove) ----------
elif menu == "Manage Vehicles":
    st.header("Manage Vehicles")

    st.subheader("Add New Vehicle")
    with st.form("vehicle_form", clear_on_submit=True):
        name = st.text_input("Vehicle Name (e.g., Tempo 1, Pickup)")
        vehicle_number = st.text_input("Vehicle Number (e.g., MH15AB1234)")
        submitted = st.form_submit_button("Save Vehicle")

        if submitted:
            if name.strip() == "":
                st.error("Vehicle name is required.")
            else:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("INSERT INTO vehicles (name, vehicle_number) VALUES (?, ?)", (name, vehicle_number))
                conn.commit()
                conn.close()
                st.success(f"Vehicle '{name}' added successfully!")

    st.markdown("---")
    st.subheader("Current Vehicles")

    conn = get_connection()
    vehicles_df = pd.read_sql_query("SELECT * FROM vehicles", conn)
    conn.close()

    if vehicles_df.empty:
        st.info("No vehicles added yet.")
    else:
        st.dataframe(vehicles_df, use_container_width=True)

        st.subheader("Remove Vehicle")
        st.warning("This will permanently delete the vehicle AND all its expense/earning history. This cannot be undone.")
        vehicle_to_remove = st.selectbox("Select vehicle to remove", vehicles_df["name"])

        confirm_vehicle_text = st.text_input("Type the vehicle's exact name to confirm deletion")

        if st.button("Permanently Delete Vehicle"):
            if confirm_vehicle_text.strip() == vehicle_to_remove.strip():
                vehicle_id = int(vehicles_df[vehicles_df["name"] == vehicle_to_remove]["id"].values[0])
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM vehicle_expenses WHERE vehicle_id = ?", (vehicle_id,))
                cursor.execute("DELETE FROM vehicle_earnings WHERE vehicle_id = ?", (vehicle_id,))
                cursor.execute("DELETE FROM vehicles WHERE id = ?", (vehicle_id,))
                conn.commit()
                conn.close()
                st.success(f"'{vehicle_to_remove}' and all its records have been deleted.")
                st.rerun()
            else:
                st.error("Name doesn't match. Please type it exactly to confirm.")

# ---------- VEHICLE EXPENSE/DETAILS (Record + View combined) ----------
elif menu == "Vehicle Expense/Details":
    st.header("Vehicle Expense, Earning and Details")

    conn = get_connection()
    vehicles_df = pd.read_sql_query("SELECT id, name, vehicle_number FROM vehicles", conn)
    conn.close()

    if vehicles_df.empty:
        st.warning("Please add a vehicle first in Manage Vehicles.")
    else:
        selected_vehicle = st.selectbox("Select Vehicle", vehicles_df["name"])
        vehicle_row = vehicles_df[vehicles_df["name"] == selected_vehicle].iloc[0]
        vehicle_id = int(vehicle_row["id"])

        st.subheader(f"{vehicle_row['name']} ({vehicle_row['vehicle_number']})")

        st.markdown("#### Record New Entry")
        entry_type = st.radio("Entry Type", ["Expense", "Earning"])

        with st.form("vehicle_entry_form", clear_on_submit=True):
            amount = st.number_input("Amount (Rs)", min_value=0.0, step=50.0)
            entry_date = st.date_input("Date", value=date.today())

            expense_type = "Other"
            if entry_type == "Expense":
                expense_type = st.selectbox("Expense Type", ["Fuel", "Repair", "Maintenance", "Other"])
            note = st.text_input("Note (optional)")

            submitted = st.form_submit_button("Save Entry")

            if submitted:
                if amount <= 0:
                    st.error("Amount must be greater than 0.")
                else:
                    conn = get_connection()
                    cursor = conn.cursor()

                    if entry_type == "Expense":
                        cursor.execute(
                            "INSERT INTO vehicle_expenses (vehicle_id, expense_type, amount, expense_date, note) VALUES (?, ?, ?, ?, ?)",
                            (vehicle_id, expense_type, amount, str(entry_date), note)
                        )
                        st.success(f"Expense of Rs {amount:.2f} recorded.")
                    else:
                        cursor.execute(
                            "INSERT INTO vehicle_earnings (vehicle_id, amount, earning_date, note) VALUES (?, ?, ?, ?)",
                            (vehicle_id, amount, str(entry_date), note)
                        )
                        st.success(f"Earning of Rs {amount:.2f} recorded.")

                    conn.commit()
                    conn.close()

        st.markdown("---")
        st.markdown("#### Summary and History")

        conn = get_connection()
        expenses_df = pd.read_sql_query(
            "SELECT expense_date, expense_type, amount, note FROM vehicle_expenses WHERE vehicle_id = ? ORDER BY expense_date DESC",
            conn, params=(vehicle_id,)
        )
        earnings_df = pd.read_sql_query(
            "SELECT earning_date, amount, note FROM vehicle_earnings WHERE vehicle_id = ? ORDER BY earning_date DESC",
            conn, params=(vehicle_id,)
        )
        conn.close()

        total_expense = expenses_df["amount"].sum() if not expenses_df.empty else 0
        total_earning = earnings_df["amount"].sum() if not earnings_df.empty else 0
        net_profit = total_earning - total_expense

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Earnings", f"Rs {total_earning:,.2f}")
        col2.metric("Total Expenses", f"Rs {total_expense:,.2f}")
        col3.metric("Net Profit/Loss", f"Rs {net_profit:,.2f}")

        st.markdown("**Expense History**")
        if expenses_df.empty:
            st.info("No expenses recorded yet.")
        else:
            st.dataframe(expenses_df, use_container_width=True)

        st.markdown("**Earning History**")
        if earnings_df.empty:
            st.info("No earnings recorded yet.")
        else:
            st.dataframe(earnings_df, use_container_width=True)

elif menu == "Generate Quotation":
    st.header("Generate Price Quotation")
    st.caption("This is only an estimate for the customer — it does NOT record a sale or affect stock.")

    conn = get_connection()
    products_df = pd.read_sql_query("SELECT id, name, unit, selling_price FROM products", conn)
    conn.close()

    if products_df.empty:
        st.info("Please add products first.")
    else:
        customer_name = st.text_input("Customer Name")
        customer_phone = st.text_input("Customer Phone (optional)")

        st.subheader("Add Items to Quotation")

        if "quote_items" not in st.session_state:
            st.session_state.quote_items = []

        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        selected_product = col1.selectbox("Product", products_df["name"])

        # Pre-fill rate with the product's selling price, but let it be edited
        default_rate = float(products_df[products_df["name"] == selected_product]["selling_price"].values[0])
        quantity = col2.number_input("Quantity", min_value=0.0, step=1.0, key="quote_qty")
        rate = col3.number_input("Rate (Rs)", min_value=0.0, step=10.0, value=default_rate, key="quote_rate")

        current_amount = quantity * rate
        col4.metric("Amount", f"Rs {current_amount:,.2f}")

        add_clicked = st.button("+ Add Item")

        if add_clicked and quantity > 0:
            product_row = products_df[products_df["name"] == selected_product].iloc[0]
            st.session_state.quote_items.append({
                "product": selected_product,
                "unit": product_row["unit"],
                "quantity": quantity,
                "rate": rate,
                "amount": rate * quantity
            })

        if st.session_state.quote_items:
            st.subheader("Quotation Items")
            items_df = pd.DataFrame(st.session_state.quote_items)
            st.dataframe(items_df, use_container_width=True)

            if st.button("Clear All Items"):
                st.session_state.quote_items = []
                st.rerun()

            quote_total = items_df["amount"].sum()
            st.metric("Estimated Total", f"Rs {quote_total:,.2f}")

            if st.button("Generate Printable Quotation"):
                items_rows = ""
                for i, item in items_df.iterrows():
                    items_rows += (
                        "<tr>"
                        f"<td class='c'>{i+1}</td>"
                        f"<td>{item['product']}</td>"
                        f"<td class='c'>{item['unit']}</td>"
                        f"<td class='c'>{item['quantity']}</td>"
                        f"<td class='r'>{item['rate']:.2f}</td>"
                        f"<td class='r'>{item['amount']:.2f}</td>"
                        "</tr>"
                    )

                quote_document = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Quotation</title>
<style>
  @page {{ size: A4; margin: 12mm; }}
  * {{ box-sizing: border-box; font-family: Arial, Helvetica, sans-serif; }}
  body {{ margin: 0; padding: 0; font-size: 13px; color: #000; }}
  table {{ border-collapse: collapse; width: 100%; }}
  .outer {{ border: 2px solid #333; padding: 15px; max-width: 750px; margin: auto; }}
  .center {{ text-align: center; }}
  .r {{ text-align: right; }}
  .c {{ text-align: center; }}
  .shopname {{ font-size: 22px; font-weight: bold; color: #5b2a00; margin: 0; }}
  .tagline {{ font-size: 11px; margin: 2px 0; }}
  .invoice-band {{ background: #3a1a00; color: #fff; padding: 5px; font-size: 15px; font-weight: bold; }}
  .box {{ border: 1px solid #333; padding: 6px; }}
  .box-title {{ background: #3a1a00; color: #fff; padding: 2px 6px; font-size: 12px; font-weight: bold; }}
  .items th, .items td {{ border: 1px solid #333; padding: 4px 6px; font-size: 12px; }}
  .items th {{ background: #f0e6d6; }}
  .totals td {{ padding: 3px 6px; font-size: 12px; }}
  .totals .grand {{ font-weight: bold; background: #f0e6d6; }}
  .sign td {{ padding-top: 30px; font-size: 12px; }}
  .terms {{ font-size: 10px; }}
</style>
</head>
<body>
<div class="outer">

  <table>
    <tr><td class="center">
      <p class="shopname">SAI BUILDING MATERIAL & PLYWOOD</p>
      <p class="tagline"><b>DABHADI</b></p>
      <p class="tagline">CEMENT | STEEL | CONCRETE PLUS | ALL BUILDING MATERIALS</p>
      <p class="tagline">Dabhadi, Malegaon</p>
    </td></tr>
  </table>

  <hr style="border-top:2px solid #333; margin:6px 0;">

  <table>
    <tr><td class="invoice-band center">QUOTATION / ESTIMATE</td></tr>
  </table>

  <table style="margin-top:6px;">
    <tr>
      <td><b>Quotation No.:</b> Q-{date.today().strftime('%Y%m%d')}</td>
      <td class="r"><b>Date:</b> {date.today()}</td>
    </tr>
  </table>

  <table style="margin-top:8px;">
    <tr><td class="box">
      <span class="box-title">Customer Details</span><br>
      <b>Customer Name:</b> {customer_name if customer_name else '-'}<br>
      <b>Mobile No.:</b> {customer_phone if customer_phone else '-'}
    </td></tr>
  </table>

  <table class="items" style="margin-top:8px;">
    <tr>
      <th style="width:8%;">Sr No.</th>
      <th style="width:34%;">Item Name</th>
      <th style="width:12%;">Unit</th>
      <th style="width:12%;">Qty</th>
      <th style="width:17%;">Rate (Rs)</th>
      <th style="width:17%;">Amount (Rs)</th>
    </tr>
    {items_rows}
  </table>

  <table class="totals" style="margin-top:8px;">
    <tr class="grand"><td style="width:70%;"></td><td>ESTIMATED TOTAL</td><td class="r">Rs {quote_total:.2f}</td></tr>
  </table>

  <table class="terms" style="margin-top:8px;">
    <tr><td>
      <b>Terms:</b><br>
      1) This is an estimate only, not a final bill.<br>
      2) Prices may vary at the time of actual purchase.<br>
      3) Quotation valid for 7 days from the date above.
    </td></tr>
  </table>

  <table class="sign">
    <tr>
      <td style="width:50%;">_______________________<br>Customer Signature</td>
      <td class="r">_______________________<br>Authorized Signature</td>
    </tr>
  </table>

  <table>
    <tr><td class="center" style="font-style:italic; padding-top:8px;">Thank You! Visit Again!</td></tr>
  </table>

</div>
</body>
</html>"""

                st.success("Quotation generated!")
                st.download_button(
                    label="⬇️ Download Quotation (open it, then press Ctrl+P to print)",
                    data=quote_document,
                    file_name=f"Quotation_{date.today()}.html",
                    mime="text/html"
                )
                st.components.v1.html(quote_document, height=800, scrolling=True)

elif menu == "Manage Customers":
    st.header("Manage Customers")

    conn = get_connection()
    customers_df = pd.read_sql_query("SELECT * FROM customers", conn)
    conn.close()

    if customers_df.empty:
        st.info("No customers added yet.")
    else:
        st.dataframe(customers_df, use_container_width=True)

        st.markdown("---")
        st.subheader("Remove a Customer")
        st.warning("This will permanently delete the customer AND all their purchase/payment history. This cannot be undone.")

        customer_to_remove = st.selectbox("Select customer to remove", customers_df["name"])
        customer_id = int(customers_df[customers_df["name"] == customer_to_remove]["id"].values[0])

        confirm_text = st.text_input(f"Type the customer's exact name to confirm deletion")

        if st.button("Permanently Delete Customer"):
            if confirm_text.strip() == customer_to_remove.strip():
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM sales WHERE customer_id = ?", (customer_id,))
                cursor.execute("DELETE FROM payments WHERE customer_id = ?", (customer_id,))
                cursor.execute("DELETE FROM customers WHERE id = ?", (customer_id,))
                conn.commit()
                conn.close()
                st.success(f"'{customer_to_remove}' and all their records have been deleted.")
                st.rerun()
            else:
                st.error("Name doesn't match. Please type it exactly to confirm.")

elif menu == "Settings":
    st.header("Settings")

    st.subheader("Clear Specific Data")
    st.caption("Use these buttons to clear leftover test data from a specific section, without affecting other sections.")

    col1, col2, col3 = st.columns(3)

    if col1.button("Clear Attendance History"):
        conn = get_connection()
        conn.execute("DELETE FROM attendance")
        conn.commit()
        conn.close()
        st.success("Attendance history cleared.")
        st.rerun()

    if col2.button("Clear Sales & Payments"):
        conn = get_connection()
        conn.execute("DELETE FROM sales")
        conn.execute("DELETE FROM payments")
        conn.commit()
        conn.close()
        st.success("Sales and payments cleared.")
        st.rerun()

    if col3.button("Clear Vehicle Records"):
        conn = get_connection()
        conn.execute("DELETE FROM vehicle_expenses")
        conn.execute("DELETE FROM vehicle_earnings")
        conn.commit()
        conn.close()
        st.success("Vehicle expense/earning records cleared.")
        st.rerun()

    st.markdown("---")
    st.subheader("Reset Everything")
    st.error("This deletes ALL data in the entire app — customers, products, sales, labour, vehicles, everything. This cannot be undone.")

    confirm_reset = st.text_input("Type exactly: DELETE ALL DATA")

    if st.button("Reset Entire Database"):
        if confirm_reset.strip() == "DELETE ALL DATA":
            conn = get_connection()
            cursor = conn.cursor()
            tables = ["sales", "payments", "products", "customers",
                      "attendance", "labour",
                      "vehicle_expenses", "vehicle_earnings", "vehicles"]
            for table in tables:
                try:
                    cursor.execute(f"DELETE FROM {table}")
                except Exception:
                    pass
            conn.commit()
            conn.close()
            st.success("All data cleared. The app is now fresh.")
            st.rerun()
        else:
            st.error("Text doesn't match. Type 'DELETE ALL DATA' exactly.")