import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import os

# File to store tracked stocks
STOCKS_FILE = 'tracked_stocks.txt'

def load_tracked_stocks():
    if os.path.exists(STOCKS_FILE):
        with open(STOCKS_FILE, 'r') as file:
            return {line.strip().split(',')[0]: line.strip().split(',')[1] for line in file}
    return {}

def save_tracked_stocks(stocks):
    with open(STOCKS_FILE, 'w') as file:
        for symbol, name in stocks.items():
            file.write(f"{symbol},{name}\n")

# Initialize the session state to keep track of the stocks
if 'tech_stocks' not in st.session_state:
    st.session_state.tech_stocks = load_tracked_stocks()

if 'remove_symbol' not in st.session_state:
    st.session_state.remove_symbol = None

if 'show_confirmation' not in st.session_state:
    st.session_state.show_confirmation = False

def get_timeframe_data(symbols, period=None, start_date=None, end_date=None, interval='1d'):
    stock_data = {}
    for symbol in symbols:
        stock = yf.Ticker(symbol)
        if period:
            hist = stock.history(period=period, interval=interval)
        else:
            hist = stock.history(start=start_date, end=end_date, interval=interval)
        stock_data[symbol] = hist['Close']
    return pd.DataFrame(stock_data)

def calculate_changes(df, y_axis):
    changes = {}
    for column in df.columns:
        start_price = df[column].iloc[0]
        end_price = df[column].iloc[-1]
        if y_axis == 'Dollar Value':
            change = end_price - start_price
        else:
            change = ((end_price - start_price) / start_price) * 100
        changes[column] = change
    return changes

def plot_time_series(df, selected_stocks, y_axis, title):
    fig = go.Figure()
    percent_changes = {}

    for stock in selected_stocks:
        if y_axis == 'Dollar Value':
            fig.add_trace(go.Scatter(x=df.index, y=df[stock], mode='lines', name=stock))
            start_price = df[stock].iloc[0]
            end_price = df[stock].iloc[-1]
            percent_change = ((end_price - start_price) / start_price) * 100
            percent_changes[stock] = percent_change
        else:
            start_price = df[stock].iloc[0]
            percent_change = ((df[stock] - start_price) / start_price) * 100
            fig.add_trace(go.Scatter(x=df.index, y=percent_change, mode='lines', name=stock))
            end_price = df[stock].iloc[-1]
            percent_changes[stock] = ((end_price - start_price) / start_price) * 100

    fig.update_layout(
        title=title,
        xaxis_title='Time',
        yaxis_title='Price ($)' if y_axis == 'Dollar Value' else 'Change (%)',
        legend_title_text='Stocks',
        legend=dict(
            itemsizing='constant',
            itemclick='toggleothers'
        )
    )

    # Add percent changes to legend
    new_legend = []
    for trace in fig.data:
        stock = trace.name
        new_legend.append(f"{stock} ({percent_changes[stock]:.2f}%)" if y_axis == 'Dollar Value' else f"{stock} (${df[stock].iloc[-1]:.2f})")
    for i, trace in enumerate(fig.data):
        trace.name = new_legend[i]

    fig.update_layout(showlegend=True)
    
    st.plotly_chart(fig, use_container_width=True)

def main():
    st.title('Top Tech Stocks Tracker')

    # Sidebar for filters and stock list
    with st.sidebar:
        st.title("Filters")

        # Time period selection
        period = st.radio(
            "Select Time Period",
            ('1d', '5d', '1mo', '3mo', '6mo', 'ytd', 'Custom Date Range')
        )

        # Date range selection if 'Custom Date Range' is selected
        if period == 'Custom Date Range':
            start_date = st.date_input("Start Date", value=pd.to_datetime("2023-01-01"))
            end_date = st.date_input("End Date", value=pd.to_datetime("today"))
            if start_date > end_date:
                st.error("End Date must fall after Start Date")
        else:
            start_date, end_date = None, None

        # Y-axis selection
        y_axis = st.radio(
            "Y-Axis",
            ('Dollar Value', 'Percentage Change')
        )

        # Stock selection mode
        selection_mode = st.radio(
            "Selection Mode",
            ('Top Gainers', 'Top Losers', 'Manual Selection')
        )

    interval = '1m' if period == '1d' else '1d'
    if period == 'Custom Date Range':
        timeframe_data = get_timeframe_data(list(st.session_state.tech_stocks.keys()), start_date=start_date, end_date=end_date, interval=interval)
    else:
        timeframe_data = get_timeframe_data(list(st.session_state.tech_stocks.keys()), period=period, interval=interval)

    changes = calculate_changes(timeframe_data, y_axis)

    if selection_mode == 'Top Gainers':
        selected_stocks = sorted(changes, key=changes.get, reverse=True)[:10]
        plot_time_series(timeframe_data, selected_stocks, y_axis, "Top 10 Gainers")
    elif selection_mode == 'Top Losers':
        selected_stocks = sorted(changes, key=changes.get)[:10]
        plot_time_series(timeframe_data, selected_stocks, y_axis, "Top 10 Losers")
    else:  # Manual Selection
        selected_stocks = st.multiselect(
            "Select up to 25 stocks to compare",
            options=list(st.session_state.tech_stocks.keys()),
            default=list(st.session_state.tech_stocks.keys())[:5],
            max_selections=25
        )
        if selected_stocks:
            gainer_stocks = [stock for stock in selected_stocks if changes[stock] > 0]
            loser_stocks = [stock for stock in selected_stocks if changes[stock] <= 0]
            if gainer_stocks:
                plot_time_series(timeframe_data, gainer_stocks, y_axis, "Selected Gainers")
            if loser_stocks:
                plot_time_series(timeframe_data, loser_stocks, y_axis, "Selected Losers")
        else:
            st.write("Please select at least one stock to display the chart.")

    # Input box to add new stocks
    st.write("### Add a new stock to track")
    new_stock = st.text_input("Enter stock symbol")
    if st.button("Add Stock"):
        if new_stock:
            new_stock_upper = new_stock.upper()
            if new_stock_upper not in st.session_state.tech_stocks:
                try:
                    stock = yf.Ticker(new_stock_upper)
                    stock_info = stock.info
                    st.session_state.tech_stocks[new_stock_upper] = stock_info['longName']
                    save_tracked_stocks(st.session_state.tech_stocks)
                    st.write(f"Added {new_stock_upper} ({stock_info['longName']}) to the list of tracked stocks.")
                except Exception as e:
                    st.write(f"Failed to add stock. Please check the symbol. Error: {e}")
            else:
                st.write(f"{new_stock_upper} is already in the list of tracked stocks.")

    # Right panel to show currently tracked stocks in a table
    with st.expander("Tracked Stocks", expanded=False):
        st.write("Currently Tracking:")

        # Create a DataFrame for tracked stocks
        tracked_stocks_data = []
        for symbol, name in st.session_state.tech_stocks.items():
            stock = yf.Ticker(symbol)
            market_cap = stock.info.get('marketCap', 0) / 1e9  # Convert to billions
            tracked_stocks_data.append({
                'Symbol': symbol,
                'Name': name,
                'Market Cap ($B)': market_cap
            })

        tracked_stocks_df = pd.DataFrame(tracked_stocks_data)

        # Display the table headers
        col1, col2, col3, col4 = st.columns([1, 2, 2, 1])
        col1.write("**Symbol**")
        col2.write("**Name**")
        col3.write("**Market Cap ($B)**")
        col4.write("")

        # Display the table with remove buttons
        for idx, row in tracked_stocks_df.iterrows():
            col1, col2, col3, col4 = st.columns([1, 2, 2, 1])
            col1.write(row['Symbol'])
            col2.write(row['Name'])
            col3.write(f"{row['Market Cap ($B)']:.2f}")
            if col4.button("Remove", key=f"remove_{row['Symbol']}"):
                st.session_state.remove_symbol = row['Symbol']
                st.session_state.show_confirmation = True

        if st.session_state.show_confirmation:
            symbol = st.session_state.remove_symbol
            st.warning(f"Are you sure you want to remove {symbol}?")
            col_confirm, col_cancel = st.columns(2)
            if col_confirm.button("Yes", key="confirm_remove"):
                del st.session_state.tech_stocks[symbol]
                save_tracked_stocks(st.session_state.tech_stocks)
                st.session_state.show_confirmation = False
                st.experimental_rerun()
            if col_cancel.button("No", key="cancel_remove"):
                st.session_state.show_confirmation = False

if __name__ == "__main__":
    main()
