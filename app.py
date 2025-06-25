import streamlit as st
import pandas as pd

def load_and_clean_tradebook(file):
    # We assume the actual header is at line 12 (index 11)
    df = pd.read_csv(file, skiprows=14)
    #st.write(f"Columns detected: {df.columns.tolist()}")
    #st.write(df.head(3))

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
    buys = transactions_df[(transactions_df['Stock'] == stock) & 
                           (transactions_df['Trade Type'].str.lower() == 'buy')].sort_values(by='Date')
    remaining = sell_qty
    total_cost = 0.0

    for _, row in buys.iterrows():
        available_qty = row['Quantity']
        price = row['Price']

        if remaining <= 0:
            break

        qty_to_use = min(available_qty, remaining)
        total_cost += qty_to_use * price
        remaining -= qty_to_use

    if remaining > 0:
        raise ValueError("Not enough shares to sell the requested quantity.")

    return total_cost

def calculate_selling_price(transactions_df, stock, qty_to_sell, profit_percent):
    # Filter transactions for the stock
    stock_trades = transactions_df[transactions_df['Stock'] == stock]

    # Calculate total cost of shares to sell using FIFO
    total_cost = calculate_fifo_cost(stock_trades, qty_to_sell)

    # Calculate total desired revenue to achieve profit_percent
    desired_revenue = total_cost * (1 + profit_percent / 100)

    # Selling price per share
    selling_price = desired_revenue / qty_to_sell

    return selling_price

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
