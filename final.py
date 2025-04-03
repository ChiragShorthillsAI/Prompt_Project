import requests
import csv
import gzip
import json
import time
import pandas as pd
import matplotlib.pyplot as plt

def scrape_nifty50_data(csv_filename="nifty50_data.csv"):
    """
    Scrape NIFTY 50 stock data from NSE and save it to a CSV file.
    """
    url = "https://www.nseindia.com/api/equity-stockIndices?index=NIFTY%2050"

    # Updated headers with an extra Origin header.
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/90.0.4430.85 Safari/537.36"
        ),
        "Accept": "application/json, text/plain, */*",
        # Removing Accept-Encoding to force uncompressed response.
        # "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "en-US,en;q=0.9",
        "Origin": "https://www.nseindia.com",
        "Connection": "keep-alive",
        "Referer": "https://www.nseindia.com/",
        "X-Requested-With": "XMLHttpRequest"
    }

    session = requests.Session()
    session.headers.update(headers)

    # Access the NSE homepage first to set up cookies.
    try:
        homepage_response = session.get("https://www.nseindia.com", timeout=5)
        if homepage_response.status_code != 200:
            print(f"Error accessing NSE homepage: HTTP {homepage_response.status_code}")
            return
    except requests.exceptions.RequestException as e:
        print(f"Could not open nseindia.com: {e}")
        return

    # Pause briefly to allow cookies to be set.
    time.sleep(1)

    # Fetch data from the API endpoint.
    try:
        response = session.get(url, timeout=10)
        print("Response status code:", response.status_code)
        print("Response headers:", response.headers)
        
        if response.status_code != 200:
            print(f"Error: HTTP {response.status_code}")
            print("Response content:", response.text)
            return

        try:
            data = response.json()
        except ValueError:
            # If automatic decompression did not occur, try manual decompression.
            data_text = gzip.decompress(response.content).decode('utf-8')
            data = json.loads(data_text)
    except requests.exceptions.RequestException as e:
        print(f"Could not fetch data from {url}: {e}")
        return

    # Extract the list of stock data from the "data" key.
    stock_data_list = data.get("data", [])
    if not stock_data_list:
        print("No stock data found in the response.")
        return

    # Define the CSV header. Added "perChange30d" in case it's available.
    csv_headers = [
        "symbol",
        "open",
        "dayHigh",
        "dayLow",
        "lastPrice",
        "previousClose",
        "change",
        "pChange",
        "totalTradedVolume",
        "totalTradedValue",
        "yearHigh",
        "yearLow",
        "lastUpdateTime",
        "perChange30d"  # Ensure this field exists; if not, it will be blank.
    ]

    try:
        with open(csv_filename, mode="w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=csv_headers)
            writer.writeheader()
            for stock in stock_data_list:
                row = {
                    "symbol": stock.get("symbol", ""),
                    "open": stock.get("open", ""),
                    "dayHigh": stock.get("dayHigh", ""),
                    "dayLow": stock.get("dayLow", ""),
                    "lastPrice": stock.get("lastPrice", ""),
                    "previousClose": stock.get("previousClose", ""),
                    "change": stock.get("change", ""),
                    "pChange": stock.get("pChange", ""),
                    "totalTradedVolume": stock.get("totalTradedVolume", ""),
                    "totalTradedValue": stock.get("totalTradedValue", ""),
                    "yearHigh": stock.get("yearHigh", ""),
                    "yearLow": stock.get("yearLow", ""),
                    "lastUpdateTime": stock.get("lastUpdateTime", ""),
                    "perChange30d": stock.get("perChange30d", "")
                }
                writer.writerow(row)
        print(f"Data successfully saved to {csv_filename}")
    except Exception as e:
        print(f"Error writing to CSV: {e}")

def analyze_and_visualize(csv_filename="nifty50_data.csv"):
    # Read the CSV file.
    df = pd.read_csv(csv_filename)

    # Ensure numeric columns are properly converted.
    numeric_columns = [
        "open", "dayHigh", "dayLow", "lastPrice", "previousClose", "change",
        "pChange", "totalTradedVolume", "totalTradedValue", "yearHigh", "yearLow", "perChange30d"
    ]
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # 1. Top 5 gainers and losers of the day (using percentage change 'pChange').
    top5_gainers = df.sort_values(by="pChange", ascending=False).head(5)
    top5_losers = df.sort_values(by="pChange", ascending=True).head(5)

    print("Top 5 Gainers of the Day:")
    print(top5_gainers[["symbol", "pChange"]])
    print("\nTop 5 Losers of the Day:")
    print(top5_losers[["symbol", "pChange"]])

    # 2. Identify 5 stocks that are currently 30% below their 52-week high.
    # Condition: lastPrice <= 70% of yearHigh.
    df_below_high = df.loc[df["lastPrice"] <= (0.70 * df["yearHigh"])].copy()
    # Calculate percentage below high.
    df_below_high["pctBelowHigh"] = ((df_below_high["yearHigh"] - df_below_high["lastPrice"]) / df_below_high["yearHigh"]) * 100
    stocks_30_below_high = df_below_high.sort_values(by="pctBelowHigh", ascending=False).head(5)
    print("\n5 Stocks 30% below their 52-week high (or more):")
    print(stocks_30_below_high[["symbol", "lastPrice", "yearHigh", "pctBelowHigh"]])

    # 3. Identify 5 stocks that are currently 20% up their 52-week low.
    # Condition: lastPrice >= 120% of yearLow.
    df_above_low = df.loc[df["lastPrice"] >= (1.20 * df["yearLow"])].copy()
    # Calculate percentage above low.
    df_above_low["pctAboveLow"] = ((df_above_low["lastPrice"] - df_above_low["yearLow"]) / df_above_low["yearLow"]) * 100
    stocks_20_above_low = df_above_low.sort_values(by="pctAboveLow", ascending=False).head(5)
    print("\n5 Stocks 20% above their 52-week low (or more):")
    print(stocks_20_above_low[["symbol", "lastPrice", "yearLow", "pctAboveLow"]])

    # 4. Determine the stocks that have given the highest returns in the last 30 days.
    top30_returns = df.sort_values(by="perChange30d", ascending=False).head(5)
    print("\nTop 5 Stocks by 30-day Returns:")
    print(top30_returns[["symbol", "perChange30d"]])

    # 5. Create a bar chart for top 5 gainers and losers of the day.
    fig, axs = plt.subplots(1, 2, figsize=(14, 6))

    # Bar chart for Top 5 Gainers.
    axs[0].bar(top5_gainers["symbol"], top5_gainers["pChange"], color='green')
    axs[0].set_title("Top 5 Gainers")
    axs[0].set_xlabel("Stock Symbol")
    axs[0].set_ylabel("Daily % Change")
    axs[0].tick_params(axis='x', rotation=45)

    # Bar chart for Top 5 Losers.
    axs[1].bar(top5_losers["symbol"], top5_losers["pChange"], color='red')
    axs[1].set_title("Top 5 Losers")
    axs[1].set_xlabel("Stock Symbol")
    axs[1].set_ylabel("Daily % Change")
    axs[1].tick_params(axis='x', rotation=45)

    plt.tight_layout()
    # Save the plot as a PNG file instead of showing it interactively.
    plt.savefig("gainers_losers.png")
    plt.close()
    print("Plot saved as 'gainers_losers.png'.")

if __name__ == "__main__":
    csv_file = "nifty50_data.csv"
    # Scrape data and save to CSV.
    scrape_nifty50_data(csv_file)
    
    # After scraping, analyze and visualize the data.
    analyze_and_visualize(csv_file)
