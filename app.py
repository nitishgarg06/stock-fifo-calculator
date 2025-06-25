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
    df = pd.read_csv(url, skiprows=14)
    df.rename(columns={
        'Symbol': 'Stock',
        'Trade Date': 'Date',
        'Trade Type': 'Trade Type',
        'Quantity': 'Quantity',
        'Price': 'Price'
    }, inplace=True)
    df['Date'] = pd.to_datetime(df['Date'])
    df['Quantity'] = pd.to_numeric(df['Quantity'])
    df['Price'] = pd.to_numeric(df['Price'])
    return df[['Stock', 'Date', 'Trade Type', 'Quantity', 'Price']]

# --- Get current holdings (net shares) ---
def get_current_holdings(df):
    df['SignedQty'] = df.apply(lambda row: row['Quantity'] if row['Trade Type'].lower() == 'buy' else -row['Quantity'], axis=1)
    holdings = df.groupby('Stock')['SignedQty'].sum()
    holdings = holdings[holdings > 0]
    return holdings

# --- Calculate weighted average buy price per stock ---
def get_avg_buy_price(df, stock):
    buys = df[(df['Stock'] == stock) & (df['Trade Type'].str.lower() == 'buy')]
    if buys.empty:
        return None
    total_qty = buys['Quantity'].sum()
    total_cost = (buys['Quantity'] * buys['Price']).sum()
    return total_cost / total_qty

# --- FIFO cost calculation ---
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
        raise ValueError(f"Not enough shares to sell. Requested {sell_qty}, but only {sell_qty - remaining} available.")

    return total_cost

# --- Selling price calculation ---
def calculate_selling_price(df, stock, qty_to_sell, profit_percent):
    total_cost = calculate_fifo_cost(df, stock, qty_to_sell)
    desired_revenue = total_cost * (1 + profit_percent / 100)
    sell_price = desired_revenue / qty_to_sell
    return sell_price

def main():
    st.title("Stock Portfolio & Selling Price Calculator")

    # Load data
    try:
        dfs = [load_and_clean_tradebook(url) for url in csv_urls]
        combined_df = pd.concat(dfs, ignore_index=True)
    except Exception as e:
        st.error(f"Error loading CSV files from GitHub: {e}")
        return

    holdings = get_current_holdings(combined_df)
    if holdings.empty:
        st.warning("No stocks with positive holdings found in the data.")
        return

    # Menu choice
    option = st.sidebar.radio("Choose an option:", ("View Portfolio", "Calculate Selling Price"))

    if option == "View Portfolio":
        latest_date = combined_df['Date'].max()
        st.subheader(f"Active Portfolio as of {latest_date.date()}")

        portfolio_data = []
        for stock, qty in holdings.items():
            avg_price = get_avg_buy_price(combined_df, stock)
            portfolio_data.append({
                "Stock": stock,
                "Quantity": int(qty),
                "Avg Buy Price (₹)": f"{avg_price:.2f}" if avg_price else "N/A"
            })

        st.table(portfolio_data)

    else:  # Calculate Selling Price
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
