Streamlit Daily Analysis App
This application provides a dashboard to analyze daily production data from a series of CSV files. It's designed to handle messy date formats in file names and content, offering analysis for both single days and date ranges.

How to Use
Place Your Data:

Create a folder named data in the same directory as the app.py file.

Place all your daily analysis CSV files (like Analysis point .xlsx - 07-july.csv) inside this data folder.

Install Dependencies:

You need to have Python installed. Then, install the required libraries using pip:

pip install streamlit pandas python-dateutil plotly

Run the App:

Open your terminal or command prompt.

Navigate to the directory where you saved app.py.

Run the following command:

streamlit run app.py

The application will open in a new tab in your web browser.

Features
Smart Date Parsing: Automatically extracts dates from file content (e.g., "Date: 7-July-2025") or from messy file names.

Single Day Analysis: Select a specific date to view detailed KPIs and analysis points for that day.

Date Range Analysis: Select a start and end date to view aggregated data and trend charts for:

Overall Equipment Effectiveness (OEE)

Total Daily Production

Interactive Charts: Utilizes Plotly for interactive and insightful visualizations.

Caching: Caches loaded data for faster performance on subsequent runs.
