import streamlit as st
import pandas as pd

def load_and_clean_tradebook(file):
    # We assume the actual header is at line 12 (index 11)
    df = pd.read_csv(file, skiprows=11)

    # Keep only relevant columns and rename for consistency
    df = df[['Symbol', 'Trade Date', 'Trade Type', 'Quantity', 'Price']].copy()
    df.rename(columns={
        'Symbol': 'Stock',
        'Trade Date': 'Date',
    }, inplace=True)

    # Filter only buy trades
    df = df[df['Trade Type'].str.lower() == 'buy']

    # Convert data types
    df['Date'] = pd.to_datetime(df['Date'])
    df['Quantity'] = pd.to_numeric(df['Quantity'])
    df['Price'] = pd.to_numeric(df['Price'])

    return df[['Date', 'Stock', 'Quantity', 'Price']]

def calculate_fifo_cost(transactions_df, sell_qty):
    transactions_df = transactions_df.sort_values(by='Date')  # FIFO
    remaining = sell_qty
    total_cost = 0.0

    for _, row in transactions_df.iterrows():
        available_qty = row['Quantity']
        price = row['Price']

        if remaining <= 0:
            break

        if available_qty <= remaining:
            total_cost += available_qty * price
            remaining -= available_qty
        else:
            total_cost += remaining * price
            remaining = 0

    if remaining > 0:
        raise ValueError("Not enough shares to sell the requested quantity.")

    return total_cost

def get_selling_price(df, stock_name, sell_qty, profit_pct):
    df_stock = df[df['Stock'].str.upper() == stock_name.upper()]
    if df_stock.empty:
        raise ValueError(f"No buy transactions found for stock: {stock_name}")

    total_available = df_stock['Quantity'].sum()
    if sell_qty > total_available:
        raise ValueError(f"Trying to sell {sell_qty} shares but only {total_available} available.")

    total_cost = calculate_fifo_cost(df_stock, sell_qty)
    desired_profit = total_cost * (profit_pct / 100)
    total_sale_value = total_cost + desired_profit
    selling_price_per_share = total_sale_value / sell_qty

    return round(selling_price_per_share, 2)

# Streamlit UI
st.title("📊 FIFO Stock Selling Price Calculator")

st.markdown("""
Upload your **tradebook CSV files** (same format as your example).  
The app will automatically clean and combine them.
""")

uploaded_files = st.file_uploader("Upload CSV files", type="csv", accept_multiple_files=True)

if uploaded_files:
    try:
        dfs = [load_and_clean_tradebook(file) for file in uploaded_files]
        combined_df = pd.concat(dfs, ignore_index=True)
        st.success("✅ Files loaded!")

        stock_list = combined_df['Stock'].unique().tolist()
        stock = st.selectbox("Select Stock", stock_list)

        sell_qty = st.number_input("Quantity to Sell", min_value=1)
        profit_pct = st.number_input("Desired Profit (%)", min_value=0.0, step=0.1)

        if st.button("Calculate Selling Price"):
            try:
                price = get_selling_price(combined_df, stock, sell_qty, profit_pct)
                st.success(f"💰 Selling Price per Share: **${price}**")
            except Exception as e:
                st.error(f"Error: {e}")

    except Exception as e:
        st.error(f"Failed to process CSV files: {e}")
else:
    st.info("Upload your tradebook CSV files to get started.")
