import streamlit as st
import pandas as pd

# Example raw URLs of your CSV files in the repo
csv_urls = [
    "https://raw.githubusercontent.com/nitishgarg06/stock-fifo-calculator/main/data/tradebook-YYY528-EQ-01Apr23_to_31Mar24.csv",
    "https://raw.githubusercontent.com/nitishgarg06/stock-fifo-calculator/main/data/tradebook-YYY528-EQ-01Apr24_to_31Mar25.csv",
    "https://raw.githubusercontent.com/nitishgarg06/stock-fifo-calculator/main/data/tradebook-YYY528-EQ-01Apr25_to_24Jun25.csv",
]

# --- Load and clean one CSV ---
def load_and_clean_tradebook(url):
    # Skip first 14 rows to get header at row 15 (0-indexed 14)
    df = pd.read_csv(url, skiprows=14)
    # Rename columns for convenience (use exact header names)
    df.rename(columns={
        'Symbol': 'Stock',
        'Trade Date': 'Date',
        'Trade Type': 'Trade Type',
        'Quantity': 'Quantity',
        'Price': 'Price'
    }, inplace=True)
    # Convert types
    df['Date'] = pd.to_datetime(df['Date'])
    df['Quantity'] = pd.to_numeric(df['Quantity'])
    df['Price'] = pd.to_numeric(df['Price'])
    return df[['Stock', 'Date', 'Trade Type', 'Quantity', 'Price']]

# --- Get current holdings (net shares) ---
def get_current_holdings(df):
    # Buy adds shares, sell subtracts shares
    df['SignedQty'] = df.apply(lambda row: row['Quantity'] if row['Trade Type'].lower() == 'buy' else -row['Quantity'], axis=1)
    holdings = df.groupby('Stock')['SignedQty'].sum()
    holdings = holdings[holdings > 0]  # only positive holdings
    return holdings

# --- FIFO cost calculation for shares to sell ---
def calculate_fifo_cost(df, stock, sell_qty):
    buys = df[(df['Stock'] == stock) & (df['Trade Type'].str.lower() == 'buy')].sort_values('Date')
    remaining = sell_qty
    total_cost = 0.0

    for _, row in buys.iterrows():
        if remaining <= 0:
            break
        qty_available = row['Quantity']
        qty_used = min(qty_available, remaining)
        total_cost += qty_used * row['Price']
        remaining -= qty_used

    if remaining > 0:
        raise ValueError(f"Not enough shares to sell. You requested {sell_qty}, but only {sell_qty - remaining} available.")

    return total_cost

# --- Calculate selling price per share for desired profit ---
def calculate_selling_price(df, stock, qty_to_sell, profit_percent):
    total_cost = calculate_fifo_cost(df, stock, qty_to_sell)
    desired_revenue = total_cost * (1 + profit_percent / 100)
    sell_price = desired_revenue / qty_to_sell
    return sell_price

# --- Main Streamlit app ---
def main():
    st.title("Stock Selling Price Calculator (FIFO)")

    st.info("This app loads your stock transaction CSVs from GitHub and calculates the selling price for a desired profit.")

    # Load data from GitHub CSVs
    try:
        dfs = [load_and_clean_tradebook(url) for url in csv_urls]
        combined_df = pd.concat(dfs, ignore_index=True)
    except Exception as e:
        st.error(f"Error loading CSV files from GitHub: {e}")
        return

    # Get current holdings
    holdings = get_current_holdings(combined_df)
    if holdings.empty:
        st.warning("No stocks with positive holdings found in the uploaded data.")
        return

    # Stock selection dropdown
    stock = st.selectbox("Select stock to sell", holdings.index.tolist())

    max_qty = int(holdings[stock])
    qty_to_sell = st.number_input("Quantity to sell", min_value=1, max_value=max_qty, value=1)
    profit_percent = st.number_input("Desired profit percentage (%)", min_value=0.0, value=10.0, format="%.2f")

    if st.button("Calculate Selling Price"):
        try:
            price = calculate_selling_price(combined_df, stock, qty_to_sell, profit_percent)
            st.success(f"Sell {qty_to_sell} shares of {stock} at ₹{price:.2f} per share to achieve {profit_percent}% profit.")
        except Exception as e:
            st.error(f"Calculation error: {e}")

if __name__ == "__main__":
    main()
