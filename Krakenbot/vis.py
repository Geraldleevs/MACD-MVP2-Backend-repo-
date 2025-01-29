import os
import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio

def load_files_from_directory(directory):
    """
    Load all CSV files from the specified directory into a dictionary of DataFrames.
    """
    file_data = {}
    csv_files = [f for f in os.listdir(directory) if f.endswith(".csv")]

    if not csv_files:
        print("No CSV files found in the directory.")
        return None

    print("\nAvailable Data Files:")
    for idx, file_name in enumerate(csv_files, start=1):
        print(f"{idx}. {file_name}")

    try:
        choice = int(input("\nEnter the number of the file you want to view: ")) - 1
        if 0 <= choice < len(csv_files):
            file_name = csv_files[choice]
            file_path = os.path.join(directory, file_name)
            df = pd.read_csv(file_path)
            df['Timestamp'] = pd.to_datetime(df['Timestamp'])  # Ensure proper timestamp format
            return {file_name: df}
        else:
            print("Invalid selection. Exiting.")
            return None
    except ValueError:
        print("Invalid input. Please enter a number.")
        return None


def plot_price_graph(file_data, title="Cryptocurrency Price Data"):
    """
    Create an interactive candlestick chart using Plotly with dynamic y-axis scaling.
    """
    if not file_data:
        print("No data available to plot.")
        return

    fig = go.Figure()

    dropdown_buttons = []

    for i, (file_name, df) in enumerate(file_data.items()):
        # Ensure the required columns exist
        if not {'Open', 'High', 'Low', 'Close'}.issubset(df.columns):
            print(f"Skipping {file_name} - Missing OHLC columns")
            continue

        # Add OHLC Candlestick trace
        fig.add_trace(go.Candlestick(
            x=df['Timestamp'],
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name=file_name,
            visible=(i == 0)  # Show only the first file by default
        ))

        # Add dropdown menu option for this file
        dropdown_buttons.append(
            dict(
                args=[{"visible": [j == i for j in range(len(file_data))]}],
                label=file_name,
                method="update"
            )
        )

    # Add interactive layout features
    fig.update_layout(
        title=title,
        xaxis_title="Timestamp",
        yaxis_title="Price",
        template="plotly_dark",
        xaxis_rangeslider_visible=True,  # Enables scroll and zoom functionality
        updatemenus=[dict(
            buttons=dropdown_buttons,
            direction="down",
            showactive=True,
            x=0.1,
            xanchor="left",
            y=1.15,
            yanchor="top"
        )],
        autosize=True,
        width=1400,
        height=800
    )

    # Enable dynamic y-axis adjustment using Plotly relayout event
    fig.update_layout(yaxis=dict(autorange=True, fixedrange=False))

    # Show the figure in an interactive window
    pio.show(fig)


# Main Execution
if __name__ == "__main__":
    # Replace with your actual directory containing CSV files
    directory_path = "backtest_results"

    # Load selected CSV file
    file_data = load_files_from_directory(directory_path)

    # Plot the price graph for the selected file
    plot_price_graph(file_data, title="Cryptocurrency OHLC Data")
