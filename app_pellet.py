import streamlit as st
import pandas as pd
from dateutil import parser
from datetime import date
import io

# --- Configuration and Setup ---
st.set_page_config(
    page_title="KPI Analysis Report",
    page_icon="📊",
    layout="wide",
)

@st.cache_data
def generate_analysis_report(uploaded_file, selected_date):
    """
    Extracts specific KPIs from predefined rows and columns in an Excel sheet
    matching the selected date, and compiles them into a structured report.

    Args:
        uploaded_file: The Streamlit UploadedFile object.
        selected_date: The date selected by the user.

    Returns:
        A pandas DataFrame containing the analysis report, or None if data isn't found.
    """
    if not uploaded_file:
        return None

    try:
        xls = pd.ExcelFile(uploaded_file)
        target_sheet_name = None

        # Find the sheet that matches the selected date
        for sheet_name in xls.sheet_names:
            try:
                if parser.parse(sheet_name, fuzzy=True).date() == selected_date:
                    target_sheet_name = sheet_name
                    break
            except (parser.ParserError, TypeError):
                continue

        if not target_sheet_name:
            st.warning(f"No sheet found in '{uploaded_file.name}' for the date {selected_date.strftime('%d-%b-%Y')}.")
            return None

        # Load the specific sheet, skipping the top 3 rows (0, 1, 2)
        df = pd.read_excel(xls, sheet_name=target_sheet_name, header=None, skiprows=3)

        # Define the locations of the machines and KPIs by their new row/column index
        # Machines: row index after skipping top 3 rows
        machine_map = {
            'Chipper I': 1,
            'Chipper II': 2,
            'Drier': 4,
            'Pellet I': 6,
            'Pellet II': 7
        }
        
        # KPIs: column index
        kpi_map = {
            'Operation Time': 3,
            'Production Rate': 7,
            'Quality': 10,
            'OEE': 11
        }
        
        report_data = []
        serial_number = 1

        for machine, row_idx in machine_map.items():
            for kpi, col_idx in kpi_map.items():
                try:
                    # Extract the actual value from the specified cell
                    actual_value = df.iloc[row_idx, col_idx]
                    
                    # Create a descriptive remark
                    remark = f"{kpi} for {machine} is {actual_value}."
                    
                    # For Operation Time, add shortage data from column 4
                    if kpi == 'Operation Time':
                        shortage = df.iloc[row_idx, 4]
                        remark += f" Shortage: {shortage}."

                    report_data.append({
                        'Serial Number': serial_number,
                        'Particulars': machine,
                        'KPI': kpi,
                        'Actual': actual_value,
                        'Remarks': remark,
                        'Date': selected_date.strftime('%Y-%m-%d')
                    })
                    serial_number += 1

                except IndexError:
                    st.error(f"Could not read data for '{machine}' at row {row_idx}, column {col_idx}. The sheet might have an unexpected structure.")
                    continue
        
        if not report_data:
            return None

        # Create the final DataFrame from the collected data
        report_df = pd.DataFrame(report_data)
        # Reorder columns to match request, dropping the temporary KPI column
        report_df = report_df[['Serial Number', 'Particulars', 'Actual', 'Remarks', 'Date']]
        return report_df

    except Exception as e:
        st.error(f"An error occurred while processing the file: {e}")
        return None

# --- Main Application UI and Logic ---
def main():
    st.title("📊 KPI-Based Analysis Report Generator")
    st.markdown("This tool extracts specific KPIs from your uploaded Excel file based on a fixed structure.")

    # --- Sidebar for User Input ---
    with st.sidebar:
        st.header("⚙️ Controls")
        
        uploaded_file = st.file_uploader(
            "Upload your dashboard file",
            type=["xlsx"]
        )

        if uploaded_file:
            # Get available dates from the uploaded file's sheet names
            try:
                xls = pd.ExcelFile(uploaded_file)
                available_dates = []
                for sheet_name in xls.sheet_names:
                    try:
                        dt = parser.parse(sheet_name, fuzzy=True).date()
                        available_dates.append(dt)
                    except (parser.ParserError, TypeError):
                        continue
                
                if available_dates:
                    min_date, max_date = min(available_dates), max(available_dates)
                    selected_date = st.date_input(
                        "Select Date for Report", 
                        value=max_date, 
                        min_value=min_date, 
                        max_value=max_date
                    )
                else:
                    st.warning("No valid date sheets found in the file.")
                    selected_date = None

            except Exception as e:
                st.error(f"Failed to read sheet names: {e}")
                selected_date = None

            if st.button("Generate Report", type="primary") and selected_date:
                report_df = generate_analysis_report(uploaded_file, selected_date)
                st.session_state.report_df = report_df
                st.session_state.report_generated = True
        else:
             st.info("Please upload an XLSX file to begin.")

    # --- Main Panel for Displaying Report ---
    if 'report_generated' in st.session_state and st.session_state.report_generated:
        report_df = st.session_state.get('report_df')

        if report_df is not None and not report_df.empty:
            st.success("Analysis report generated successfully.")
            
            # Display the generated report dataframe
            st.dataframe(report_df)

            # Prepare CSV data for download
            csv = report_df.to_csv(index=False).encode('utf-8')
            
            st.download_button(
               label="⬇️ Download Report as CSV",
               data=csv,
               file_name=f"analysis_report_{st.session_state.get('selected_date', date.today()).strftime('%Y%m%d')}.csv",
               mime="text/csv",
            )
        else:
            st.error("Failed to generate the report. Please check the file format and selected date.")

    else:
        st.info("Use the controls in the sidebar to upload a file and generate your report.")

if __name__ == "__main__":
    main()

