import streamlit as st
import pandas as pd
import numpy as np

# --- CONFIG ---
# Replace these URLs with your GitHub raw CSV URLs
csv_urls = [
    "https://raw.githubusercontent.com/nitishgarg06/stock-fifo-calculator/main/data/tradebook-YYY528-EQ-01Apr23_to_31Mar24.csv",
    "https://raw.githubusercontent.com/nitishgarg06/stock-fifo-calculator/main/data/tradebook-YYY528-EQ-01Apr24_to_31Mar25.csv",
    "https://raw.githubusercontent.com/nitishgarg06/stock-fifo-calculator/main/data/tradebook-YYY528-EQ-01Apr25_to_24Jun25.csv"
]

# Stocks to ignore until bought again
ignored_stocks = {"UNITDSPR", "RTNPOWER", "RTNPOWER-BE", "SHAKTIPUMP-BE", "SHAKTIPUMP", "SWSOLAR-BE", "SWSOLAR-T"}

# Stocks to merge (JIOFIN-BE and JIOFIN as JIOFIN)
stock_aliases = {"JIOFIN-BE": "JIOFIN"}

# --- FUNCTIONS ---

def load_and_clean_data():
    dfs = []
    for url in csv_urls:
        df = pd.read_csv(url, skiprows=14)  # header at row 15 (0-indexed 14)
        dfs.append(df)
    df = pd.concat(dfs, ignore_index=True)

    # Rename JIOFIN-BE to JIOFIN
    df['Symbol'] = df['Symbol'].replace(stock_aliases)

    # Filter only buy and sell trades
    df = df[df['Trade Type'].isin(['buy', 'sell'])]

    # Remove ignored stocks until bought again
    # We'll determine holdings first, so here just keep for now

    # Convert Trade Date to datetime
    df['Trade Date'] = pd.to_datetime(df['Trade Date'])

    # Sort by Trade Date for FIFO
    df = df.sort_values(['Symbol', 'Trade Date', 'Order Execution Time'])

    return df

def get_current_holdings(df):
    # Calculate net quantity per stock
    holdings = {}
    for symbol, group in df.groupby('Symbol'):
        net_qty = group.loc[group['Trade Type'] == 'buy', 'Quantity'].sum() - group.loc[group['Trade Type'] == 'sell', 'Quantity'].sum()
        if net_qty > 0:
            holdings[symbol] = net_qty
    # Remove ignored stocks until bought again (only those currently held)
    holdings = {s: q for s, q in holdings.items() if s not in ignored_stocks}
    return holdings

def get_fifo_lots(df, stock):
    """Return list of (qty, price) tuples for remaining shares of stock based on FIFO after sells."""
    df_stock = df[df['Symbol'] == stock].copy()
    buys = []
    sells = []
    for _, row in df_stock.iterrows():
        if row['Trade Type'] == 'buy':
            buys.append([row['Quantity'], row['Price']])
        else:
            # sell
            qty_to_sell = row['Quantity']
            while qty_to_sell > 0 and buys:
                if buys[0][0] <= qty_to_sell:
                    qty_to_sell -= buys[0][0]
                    buys.pop(0)
                else:
                    buys[0][0] -= qty_to_sell
                    qty_to_sell = 0
    return buys

def calculate_avg_buy_price(lots):
    if not lots:
        return 0
    total_qty = sum(q for q, _ in lots)
    total_cost = sum(q * p for q, p in lots)
    return total_cost / total_qty if total_qty else 0

def calculate_selling_price(lots, qty_to_sell, profit_pct):
    """
    Given FIFO lots, qty to sell, and desired profit%, return the selling price per share.
    """
    remaining_qty = qty_to_sell
    total_cost = 0
    for i, (lot_qty, lot_price) in enumerate(lots):
        if remaining_qty <= 0:
            break
        qty_from_lot = min(lot_qty, remaining_qty)
        total_cost += qty_from_lot * lot_price
        remaining_qty -= qty_from_lot
    if remaining_qty > 0:
        return None  # Not enough shares to sell
    desired_total = total_cost * (1 + profit_pct / 100)
    selling_price = desired_total / qty_to_sell
    return selling_price

def display_portfolio(df):
    holdings = get_current_holdings(df)
    if not holdings:
        st.write("You have no current holdings (excluding ignored stocks).")
        return
    st.write("### Current Portfolio Holdings")
    data = []
    total_value = 0
    for stock, qty in holdings.items():
        lots = get_fifo_lots(df, stock)
        avg_price = calculate_avg_buy_price(lots)
        current_value = qty * avg_price
        total_value += current_value
        data.append({"Stock": stock, "Quantity": qty, "Avg Buy Price (INR)": round(avg_price, 2), "Value (INR)": round(current_value, 2)})
    df_holdings = pd.DataFrame(data)
    st.dataframe(df_holdings)
    st.write(f"**Total Portfolio Value (INR): ₹{round(total_value, 2):,}**")

# --- STREAMLIT APP ---

st.set_page_config(page_title="Stock FIFO Calculator", layout="centered", page_icon="💹")

st.markdown("""
<style>
body {
    background-color: #121212;
    color: #e0e0e0;
}
.stButton>button {
    background-color: #2196F3;
    color: white;
}
</style>
""", unsafe_allow_html=True)

st.title("Stock FIFO Selling Price Calculator")

# Load and prepare data once
df = load_and_clean_data()

option = st.radio("Choose an option:", ["Portfolio View", "Selling Price Calculator"])

if option == "Portfolio View":
    display_portfolio(df)

elif option == "Selling Price Calculator":
    holdings = get_current_holdings(df)
    if not holdings:
        st.write("No stocks available for sale in your portfolio.")
        st.stop()

    stock = st.selectbox("Select Stock", sorted(holdings.keys()))
    lots = get_fifo_lots(df, stock)
    total_qty = sum(q for q, _ in lots)

    qty_type = st.radio("Quantity to sell type:", ["Units", "Percent"])
    if qty_type == "Units":
        qty_to_sell = st.number_input(f"Enter quantity to sell (max {total_qty} units):", min_value=1, max_value=int(total_qty), step=1)
    else:
        pct = st.slider("Enter quantity to sell as % of holding:", min_value=1, max_value=100)
        qty_to_sell = int((pct / 100) * total_qty)

    profit_pct = st.number_input("Enter desired profit % on total shares sold:", min_value=0.0, step=0.1, format="%.2f")

    if st.button("Calculate Selling Price"):
        selling_price = calculate_selling_price(lots, qty_to_sell, profit_pct)
        if selling_price is None:
            st.error("Not enough shares available to sell this quantity.")
        else:
            st.success(f"Required Selling Price per share to achieve {profit_pct}% profit: ₹{selling_price:.2f}")

