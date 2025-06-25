import streamlit as st
import pandas as pd

# --------- PAGE CONFIG & THEME -----------
st.set_page_config(
    page_title="Pro Broker Stock App",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Inject custom CSS for pro dark theme + styling
st.markdown("""
<style>
body {
    background-color: #0E1117;
    color: #D0D5DD;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}
h1, h2, h3 {
    color: #0F9D58;
    font-weight: 700;
}
.css-1d391kg {
    background-color: #12191E;
    padding: 1rem 1.5rem;
    border-radius: 8px;
}
main .block-container {
    padding-top: 1rem;
    padding-left: 2rem;
    padding-right: 2rem;
}
.stButton>button {
    background-color: #0F9D58;
    color: white;
    border-radius: 5px;
    padding: 8px 24px;
    font-weight: 600;
    transition: background-color 0.3s ease;
}
.stButton>button:hover {
    background-color: #0b7a44;
}
table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 1rem;
}
th, td {
    border-bottom: 1px solid #2e2e2e;
    padding: 0.75rem 1rem;
    text-align: left;
    font-size: 0.9rem;
}
th {
    background-color: #1a1f27;
    color: #0F9D58;
}
.stTextInput>div>input, .stNumberInput>div>input {
    background-color: #1a1f27;
    border: none;
    border-radius: 6px;
    padding: 8px 12px;
    color: #D0D5DD;
    font-weight: 600;
}
.stSelectbox>div>div>div>span {
    color: #D0D5DD;
    font-weight: 600;
}
.card {
    background-color: #1a1f27;
    padding: 1rem 2rem;
    border-radius: 12px;
    margin-bottom: 1.5rem;
    box-shadow: 0 2px 10px rgb(0 0 0 / 0.4);
}
</style>
""", unsafe_allow_html=True)

st.markdown("### 📈 Pro Broker Stock App")

# ---------- HELPER FUNCTIONS -------------

@st.cache_data
def load_and_clean_csv(urls):
    dfs = []
    for url in urls:
        df = pd.read_csv(url, skiprows=14)
        # Keep relevant columns only
        df = df[['Symbol', 'Trade Date', 'Trade Type', 'Quantity', 'Price']]
        # Clean data
        df['Trade Date'] = pd.to_datetime(df['Trade Date'])
        df['Quantity'] = pd.to_numeric(df['Quantity'])
        df['Price'] = pd.to_numeric(df['Price'])
        dfs.append(df)
    combined_df = pd.concat(dfs, ignore_index=True)
    return combined_df.sort_values('Trade Date')

def get_current_holdings(df):
    holdings = {}
    for idx, row in df.iterrows():
        symbol = row['Symbol']
        qty = row['Quantity'] if row['Trade Type'].lower() == 'buy' else -row['Quantity']
        price = row['Price']
        if symbol not in holdings:
            holdings[symbol] = []
        holdings[symbol].append({'qty': qty, 'price': price, 'date': row['Trade Date']})

    # Now calculate net holdings per symbol using FIFO (simulate batches)
    current_holdings = {}
    for symbol, transactions in holdings.items():
        net_qty = sum(t['qty'] for t in transactions)
        if net_qty <= 0:
            continue  # no holdings or sold out

        # Build FIFO queue for remaining shares
        fifo = []
        for t in transactions:
            if t['qty'] > 0:
                fifo.append({'qty': t['qty'], 'price': t['price'], 'date': t['date']})
            else:
                # Remove qty from fifo in FIFO order
                qty_to_remove = -t['qty']
                while qty_to_remove > 0 and fifo:
                    batch = fifo[0]
                    if batch['qty'] > qty_to_remove:
                        batch['qty'] -= qty_to_remove
                        qty_to_remove = 0
                    else:
                        qty_to_remove -= batch['qty']
                        fifo.pop(0)
        # Store remaining fifo batches as current holding
        current_holdings[symbol] = fifo
    return current_holdings

def calculate_selling_price(fifo_batches, qty_to_sell, profit_pct):
    qty_needed = qty_to_sell
    cost_price_total = 0
    qty_counted = 0

    for batch in fifo_batches:
        batch_qty = batch['qty']
        if qty_needed <= 0:
            break
        qty_from_batch = min(batch_qty, qty_needed)
        cost_price_total += qty_from_batch * batch['price']
        qty_counted += qty_from_batch
        qty_needed -= qty_from_batch

    if qty_counted < qty_to_sell:
        raise ValueError("Not enough shares to sell that quantity.")

    # Calculate selling price per share to achieve desired profit %
    total_cost = cost_price_total
    desired_total_sale = total_cost * (1 + profit_pct / 100)
    selling_price = desired_total_sale / qty_to_sell

    return round(selling_price, 2)

# ------------- APP LOGIC -------------------

# Your CSV URLs here (from GitHub raw URLs or elsewhere)
csv_urls = [
    "https://raw.githubusercontent.com/nitishgarg06/stock-fifo-calculator/main/data/tradebook-YYY528-EQ-01Apr23_to_31Mar24.csv",
    "https://raw.githubusercontent.com/nitishgarg06/stock-fifo-calculator/main/data/tradebook-YYY528-EQ-01Apr24_to_31Mar25.csv",
    "https://raw.githubusercontent.com/nitishgarg06/stock-fifo-calculator/main/data/tradebook-YYY528-EQ-01Apr25_to_24Jun25.csv",
]

try:
    df = load_and_clean_csv(csv_urls)
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

current_holdings = get_current_holdings(df)
available_stocks = list(current_holdings.keys())

# Use radio buttons on main page (mobile friendly)
option = st.radio("Choose an option:", ("View Portfolio", "Calculate Selling Price"))

# --------- VIEW PORTFOLIO ----------
if option == "View Portfolio":
    st.subheader("Your Active Portfolio")
    if not available_stocks:
        st.info("You have no active holdings.")
    else:
        portfolio_data = []
        for stock, batches in current_holdings.items():
            total_qty = sum(b['qty'] for b in batches)
            avg_price = sum(b['qty'] * b['price'] for b in batches) / total_qty
            portfolio_data.append({
                "Stock": stock,
                "Quantity": total_qty,
                "Avg Buy Price (₹)": round(avg_price, 2)
            })
        portfolio_df = pd.DataFrame(portfolio_data)
        st.table(portfolio_df)

# -------- CALCULATE SELLING PRICE --------
else:
    st.subheader("Selling Price Calculator")

    if not available_stocks:
        st.info("No stocks available to sell.")
        st.stop()

    stock = st.selectbox("Select Stock to Sell", available_stocks)
    max_qty = sum(b['qty'] for b in current_holdings[stock])
    qty = st.number_input("Quantity to Sell", min_value=1, max_value=max_qty, value=1)
    profit_pct = st.number_input("Desired Profit %", min_value=0.0, value=10.0, format="%.2f")

    if st.button("Calculate Selling Price"):
        try:
            selling_price = calculate_selling_price(current_holdings[stock], qty, profit_pct)
            st.success(f"Sell {qty} shares of {stock} at ₹{selling_price} per share to achieve {profit_pct}% profit.")
        except ValueError as ve:
            st.error(str(ve))
