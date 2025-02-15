import os
import pandas as pd
import plotly.graph_objects as go
import plotly.subplots as sp
import plotly.io as pio

# ✅ Define available indicators
INDICATORS = ["indicator_rsi70_30", "indicator_rsi74_34"]

def load_files_from_directory(directory):
    """
    Load all CSV files from the specified directory into a dictionary of DataFrames.
    """
    file_data = {}
    csv_files = [f for f in os.listdir(directory) if f.endswith(".csv")]

    if not csv_files:
        print("No CSV files found in the directory.")
        return {}

    for file_name in csv_files:
        file_path = os.path.join(directory, file_name)
        df = pd.read_csv(file_path)
        df['Timestamp'] = pd.to_datetime(df['Timestamp'])  # Convert to datetime format
        file_data[file_name] = df

    return file_data

def plot_price_graph(file_data, title="Cryptocurrency Price Data"):
    """
    Create an interactive candlestick chart using Plotly with Bollinger Bands, RSI,
    and a dropdown to select Buy/Sell indicators.
    """
    if not file_data:
        print("No data available to plot.")
        return

    fig = sp.make_subplots(rows=2, cols=1, shared_xaxes=True,
                           vertical_spacing=0.1,
                           row_heights=[0.7, 0.3],
                           subplot_titles=("Price Chart with Bollinger Bands & Trade Signals", "RSI"))

    dataset_buttons = []
    indicator_buttons = []
    dataset_traces = {}  # Store trace indices per dataset
    indicator_traces = {indicator: {} for indicator in INDICATORS}  # Store Buy/Sell traces for each dataset
    total_traces = 0  # Track index of each trace

    # ✅ Default selected dataset and indicator
    selected_dataset = list(file_data.keys())[0]  # First dataset as default
    selected_indicator = INDICATORS[0]

    for i, (file_name, df) in enumerate(file_data.items()):
        dataset_traces[file_name] = []

        # ✅ Candlestick Chart
        fig.add_trace(go.Candlestick(
            x=df['Timestamp'], open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close'],
            name=f"{file_name} - Candlestick",
            visible=(file_name == selected_dataset)  # Only default dataset is visible
        ), row=1, col=1)
        dataset_traces[file_name].append(total_traces)
        total_traces += 1

        # ✅ Bollinger Bands
        for band, color, label in zip(["UpperBand", "LowerBand"], ["green", "red"], ["Upper", "Lower"]):
            fig.add_trace(go.Scatter(
                x=df['Timestamp'], y=df[band],
                mode='lines', name=f"{file_name} - {label} Bollinger Band",
                line=dict(color=color, dash="dot"),
                visible=(file_name == selected_dataset)
            ), row=1, col=1)
            dataset_traces[file_name].append(total_traces)
            total_traces += 1

        # ✅ RSI (Fixed Y-Axis Between 0 - 100)
        fig.add_trace(go.Scatter(
            x=df['Timestamp'], y=df['RSI70_30'],
            mode='lines', name=f"{file_name} - RSI",
            line=dict(color="purple"),
            visible=(file_name == selected_dataset)
        ), row=2, col=1)
        dataset_traces[file_name].append(total_traces)
        total_traces += 1

        # ✅ Buy/Sell Signals for Each Indicator
        for indicator in INDICATORS:
            indicator_traces[indicator][file_name] = []  # Store indicator traces per file

            for signal, color, symbol, label in zip([1, -1], ["green", "red"], ["arrow-up", "arrow-down"], ["BUY", "SELL"]):
                fig.add_trace(go.Scatter(
                    x=df[df[indicator] == signal]['Timestamp'],
                    y=df[df[indicator] == signal]['Close'],
                    mode='markers',
                    name=f"{file_name} - {label} ({indicator})",
                    marker=dict(symbol=symbol, color=color, size=12),
                    visible=(file_name == selected_dataset and indicator == selected_indicator)  # ✅ Show default indicator only
                ), row=1, col=1)
                indicator_traces[indicator][file_name].append(total_traces)
                total_traces += 1

    # ✅ Dropdown for Selecting Dataset
    for file_name in file_data.keys():
        dataset_buttons.append(dict(
            args=[{"visible": [idx in dataset_traces[file_name] or idx in indicator_traces[selected_indicator][file_name] for idx in range(total_traces)]}],
            label=file_name,
            method="update"
        ))

    # ✅ Dropdown for Selecting Indicator
    for indicator in INDICATORS:
        indicator_buttons.append(dict(
            args=[{"visible": [idx in dataset_traces[selected_dataset] or idx in indicator_traces[indicator][selected_dataset] for idx in range(total_traces)]}],
            label=indicator.replace("indicator_", "").upper(),
            method="update"
        ))

    # ✅ Configure Layout & Interactive Features
    fig.update_layout(
        title=title,
        xaxis_title="Timestamp",
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        updatemenus=[
            dict(
                buttons=dataset_buttons,
                direction="down",
                showactive=True,
                x=0.1,
                xanchor="left",
                y=1.2,
                yanchor="top"
            ),
            dict(
                buttons=indicator_buttons,
                direction="down",
                showactive=True,
                x=1,
                xanchor="left",
                y=1.2,
                yanchor="top"
            )
        ],
        autosize=True,
        width=1400,
        height=800
    )

    # ✅ Show the figure
    pio.show(fig)


# ✅ **Main Execution**
if __name__ == "__main__":
    directory_path = "MachD/backtest_results"
    file_data = load_files_from_directory(directory_path)
    plot_price_graph(file_data, title="Cryptocurrency OHLC Data with Selectable RSI Buy/Sell Signals")
