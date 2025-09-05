import streamlit as st
import pandas as pd
import os
from dateutil import parser
import re
import plotly.express as px
from datetime import datetime, timedelta

# --- Configuration and Setup ---
st.set_page_config(
    page_title="Daily Production Analysis Dashboard",
    page_icon="📊",
    layout="wide",
)

# --- Data Loading and Caching ---
@st.cache_data
def load_and_preprocess_data(data_dir="data"):
    """
    Loads all CSV files from the specified directory, extracts dates from filenames
    or content, and returns a list of dictionaries containing the date and dataframe.

    Returns:
        list: A list of dictionaries, where each dictionary has 'date' and 'df' keys.
              Returns an empty list if no files are found.
    """
    all_files_data = []
    if not os.path.exists(data_dir):
        st.error(f"The directory '{data_dir}' was not found. Please make sure it exists.")
        return []

    files = [f for f in os.listdir(data_dir) if f.endswith('.csv')]

    for filename in files:
        file_path = os.path.join(data_dir, filename)
        try:
            with open(file_path, 'r') as f:
                first_line = f.readline()
                # Use regex to find potential date strings in the first line
                date_match = re.search(r'Date:\s*([^\,]+)', first_line, re.IGNORECASE)
                file_date = None
                if date_match:
                    try:
                        # Parse the extracted date string
                        file_date = parser.parse(date_match.group(1).strip()).date()
                    except parser.ParserError:
                        st.warning(f"Could not parse date from content in '{filename}'. Falling back to filename.")

                # Fallback to parsing date from filename if not in content
                if not file_date:
                    try:
                        file_date = parser.parse(filename, fuzzy=True).date()
                    except parser.ParserError:
                        st.warning(f"Could not parse a valid date from the filename: '{filename}'. Skipping file.")
                        continue
            
            # Read the CSV data, skipping the initial date row
            df = pd.read_csv(file_path, skiprows=1)
            df.columns = [col.strip() for col in df.columns] # Clean column names
            df['Date'] = file_date
            all_files_data.append({"date": file_date, "df": df})

        except Exception as e:
            st.error(f"An error occurred while processing {filename}: {e}")
    
    # Sort data by date
    all_files_data.sort(key=lambda x: x["date"])
    return all_files_data

# --- UI and Analysis Functions ---
def display_single_day_analysis(selected_data):
    """Displays the analysis for a single selected day."""
    st.header(f"Analysis for {selected_data['date'].strftime('%d %B, %Y')}")

    df = selected_data['df']
    
    # Clean numeric columns
    for col in ['Standard', 'Actual']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.extract(r'(\d+\.?\d*)').astype(float)

    # --- Key Metrics ---
    st.subheader("Key Performance Indicators (KPIs)")
    
    try:
        total_production_actual = df[df['Particulars'] == 'Production target']['Actual'].iloc[0]
        total_production_standard = df[df['Particulars'] == 'Production target']['Standard'].iloc[0]
        oee_pellet_I = df[(df['Particulars'] == 'Pellet-I') & (df['Standard'] < 1)]['Actual'].iloc[0] * 100
        oee_pellet_II = df[(df['Particulars'] == 'Pellet-II') & (df['Standard'] < 1)]['Actual'].iloc[0] * 100
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Production", f"{total_production_actual:.2f} TPD", f"{((total_production_actual-total_production_standard)/total_production_standard)*100:.1f}% vs Target")
        col2.metric("Pellet-I OEE", f"{oee_pellet_I:.1f}%")
        col3.metric("Pellet-II OEE", f"{oee_pellet_II:.1f}%")
    except (IndexError, TypeError):
        st.warning("Could not calculate all KPIs. Data might be missing or in an unexpected format.")


    # --- Detailed Analysis Points ---
    st.subheader("Analysis Points")
    for _, row in df.iterrows():
        if 'Remark' in row and pd.notna(row['Remark']):
            particular = row.get('Particulars', 'N/A')
            remark = row['Remark']
            responsible = row.get('Responsible person', 'N/A')
            
            # Use an expander for each point to keep the UI clean
            with st.expander(f"**{particular}**: {remark.split('.')[0]}"):
                st.markdown(f"- **Details:** {remark}")
                if pd.notna(responsible):
                    st.markdown(f"- **Responsible Person:** {responsible}")


    with st.expander("Show Raw Data for the Day"):
        st.dataframe(df)

def display_date_range_analysis(filtered_data):
    """Displays aggregated analysis and visualizations for a date range."""
    if not filtered_data:
        st.warning("No data available for the selected date range.")
        return

    start_date = filtered_data[0]['date'].strftime('%d %b, %Y')
    end_date = filtered_data[-1]['date'].strftime('%d %b, %Y')
    st.header(f"Aggregated Analysis from {start_date} to {end_date}")

    # Combine all dataframes
    combined_df = pd.concat([item['df'] for item in filtered_data], ignore_index=True)
    
    # Clean numeric columns
    for col in ['Standard', 'Actual']:
        if col in combined_df.columns:
            combined_df[col] = combined_df[col].astype(str).str.extract(r'(\d+\.?\d*)').astype(float)

    # --- Trend Charts ---
    st.subheader("Performance Trends Over Time")
    
    # OEE Trend
    try:
        oee_df = combined_df[combined_df['Standard'] < 1.0].copy() # OEE rows have standard < 1
        oee_df = oee_df[oee_df['Particulars'].isin(['Pellet-I', 'Pellet-II', 'Drier', 'Chipper I', 'Chipper II'])]
        
        if not oee_df.empty:
            fig_oee = px.line(oee_df, x='Date', y='Actual', color='Particulars', 
                                title='Overall Equipment Effectiveness (OEE) Trend',
                                labels={'Actual': 'OEE Value', 'Date': 'Date'}, markers=True)
            fig_oee.update_layout(yaxis_title="OEE", legend_title="Equipment")
            st.plotly_chart(fig_oee, use_container_width=True)
        else:
            st.info("No OEE data available for trend analysis in the selected range.")

    except Exception as e:
        st.error(f"Could not generate OEE trend chart: {e}")

    # Production Trend
    try:
        prod_df = combined_df[combined_df['Particulars'] == 'Production target'].copy()
        if not prod_df.empty:
            fig_prod = px.bar(prod_df, x='Date', y='Actual', color='Actual',
                              title='Total Daily Production (TPD)',
                              labels={'Actual': 'Production (TPD)', 'Date': 'Date'},
                              text='Actual')
            fig_prod.add_scatter(x=prod_df['Date'], y=prod_df['Standard'], mode='lines', name='Target', line=dict(color='red', dash='dash'))
            fig_prod.update_layout(legend_title="Metric")
            st.plotly_chart(fig_prod, use_container_width=True)
        else:
             st.info("No Production Target data available for trend analysis in the selected range.")
    except Exception as e:
        st.error(f"Could not generate Production trend chart: {e}")
        
    with st.expander("Show Combined Raw Data for the Range"):
        st.dataframe(combined_df)


# --- Main Application ---
def main():
    """Main function to run the Streamlit app."""
    st.title("📊 Daily Production Analysis")

    # Load data
    all_data = load_and_preprocess_data()

    if not all_data:
        st.warning("No data files found or processed. Please check the 'data' directory.")
        return

    # Get available dates from the loaded data
    available_dates = [item['date'] for item in all_data]
    min_date = min(available_dates)
    max_date = max(available_dates)

    # --- Sidebar for User Input ---
    st.sidebar.header("Select Analysis Period")
    analysis_type = st.sidebar.radio(
        "Choose Analysis Type",
        ("Single Day", "Date Range")
    )

    if analysis_type == "Single Day":
        selected_date = st.sidebar.date_input(
            "Select a Date",
            value=max_date,
            min_value=min_date,
            max_value=max_date
        )
        
        # Find the data for the selected date
        data_for_date = next((item for item in all_data if item["date"] == selected_date), None)
        
        if data_for_date:
            display_single_day_analysis(data_for_date)
        else:
            st.info(f"No data available for {selected_date.strftime('%d %B, %Y')}.")

    elif analysis_type == "Date Range":
        selected_range = st.sidebar.date_input(
            "Select Date Range",
            value=(max_date - timedelta(days=7), max_date),
            min_value=min_date,
            max_value=max_date,
            key="date_range_picker"
        )
        
        if len(selected_range) == 2:
            start_date, end_date = selected_range
            
            # Filter data within the selected range
            filtered_data = [
                item for item in all_data 
                if start_date <= item["date"] <= end_date
            ]
            
            if filtered_data:
                display_date_range_analysis(filtered_data)
            else:
                st.info("No data available for the selected date range.")
        else:
            st.warning("Please select a valid date range (start and end date).")


if __name__ == "__main__":
    # Create a dummy data directory for demonstration if it doesn't exist
    if not os.path.exists('data'):
        os.makedirs('data')
        st.info("Created a 'data' directory. Please place your CSV files there and refresh.")
    main()
