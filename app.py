import streamlit as st
import pandas as pd

def load_and_clean_tradebook(file):
    # We assume the actual header is at line 12 (index 11)
    df = pd.read_csv(file, skiprows=14)
    st.write(f"Columns detected: {df.columns.tolist()}")
    st.write(df.head(3))

    # Keep only relevant columns and rename for consistency
    df = df[['Symbol', 'Trade Date', 'Trade Type', 'Quantity', 'Price']].copy()
    df.rename(columns={'Symbol':'Stock','Trade Date':'Date'}, inplace=True)
    df['Date'] = pd.to_datetime(df['Date'])
    df['Quantity'] = pd.to_numeric(df['Quantity'])
    df['Price'] = pd.to_numeric(df['Price'])
    return df


# Add get_current_holdings here, right after load_and_clean_tradebook
def get_current_holdings(df):
    df['Quantity'] = pd.to_numeric(df['Quantity'])
    df['SignedQty'] = df.apply(lambda row: row['Quantity'] if row['Trade Type'].lower() == 'buy' else -row['Quantity'], axis=1)
    
    holdings = df.groupby('Stock')['SignedQty'].sum()
    holdings = holdings[holdings > 0]  # only stocks with positive holdings
    return holdings

def calculate_fifo_cost(transactions_df, sell_qty):
    buys = transactions_df[transactions_df['Trade Type'].str.lower() == 'buy'].sort_values(by='Date')
    remaining = sell_qty
    total_cost = 0.0

    for _, row in buys.iterrows():
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
        # Load all files
        dfs = [load_and_clean_tradebook(f) for f in uploaded_files]
        combined_df = pd.concat(dfs, ignore_index=True)
        
        # Get current holdings and stock list
        holdings = get_current_holdings(combined_df)
        available_stocks = holdings.index.tolist()

        if not available_stocks:
            st.warning("No stocks currently held in portfolio.")
        else:
            stock = st.selectbox("Select Stock", available_stocks)
            
            # Show inputs only after a stock is selected
            qty_to_sell = st.number_input("Quantity to sell", min_value=1, max_value=int(holdings[stock]))
            profit_percent = st.number_input("Desired Profit %", min_value=0.0, format="%.2f")
            
            if st.button("Calculate Selling Price"):
                # Your FIFO calculation and display here
                try:
                    sell_price = calculate_selling_price(combined_df, stock, qty_to_sell, profit_percent)
                    st.success(f"Selling price per share: ₹{sell_price:.2f}")
                except Exception as e:
                    st.error(f"Calculation error: {e}")

    except Exception as e:
        st.error(f"Failed to process CSV files: {e}")
else:
    st.info("Please upload one or more CSV files to continue.")
