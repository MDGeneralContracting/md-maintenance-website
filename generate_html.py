import os
import pandas as pd
import requests
from io import BytesIO
from jinja2 import Template
from datetime import datetime, timedelta

# Fetch Excel URL from environment variable (set in GitHub Secrets)
url = os.environ['EXCEL_URL']

# Download the Excel file with debugging
try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()  # Raise an error for bad HTTP status codes
    excel_data = BytesIO(response.content)
    print(f"Downloaded {len(response.content)} bytes from {url}")
    print(f"Content-Type: {response.headers.get('Content-Type')}")
    # Save the first 100 bytes for inspection (as hex for non-text content)
    print(f"First 100 bytes: {response.content[:100].hex()}")
except requests.RequestException as e:
    print(f"Failed to download Excel file: {e}")
    raise

# Verify the content looks like an Excel file (ZIP signature: PK\x03\x04)
if not response.content.startswith(b'PK\x03\x04'):
    print("Error: Downloaded content is not a valid ZIP-based Excel file (.xlsx).")
    raise ValueError("Invalid Excel file format")

# Read Sheet1 into a DataFrame with explicit engine
try:
    df = pd.read_excel(excel_data, sheet_name='Sheet1', engine='openpyxl', parse_dates=['Completion time'])
except ValueError as e:
    print(f"Error reading Excel file: {e}")
    raise

# Define columns to display
display_columns = [
    'Name', 'Boom Lift ID', 'Completion time', 'Builder', 'Site', 'Hours',
    'Oil Level', 'Gas Level', 'General Issues', 'Continue to Maintenance or Complete'
]
df_display = df[display_columns].copy()

# Fill NaN in General Issues with empty string
df_display['General Issues'] = df_display['General Issues'].fillna('')

# Full data table, sorted by Completion time descending
full_data_table = df_display.sort_values('Completion time', ascending=False).to_html(
    classes='table table-striped', index=False
)

# Latest boom lift summary
latest_boom = df.sort_values('Completion time', ascending=False).drop_duplicates('Boom Lift ID').sort_values('Boom Lift ID')
latest_boom_table = latest_boom[[
    'Boom Lift ID', 'Completion time', 'Name', 'Hours', 'Oil Level', 'Gas Level', 'General Issues'
]].to_html(classes='table table-striped', index=False)

# User summary
user_summary = df.groupby('Name').agg(
    submissions=('Completion time', 'count'),
    latest_submission=('Completion time', 'max'),
    issues=('General Issues', lambda x: (x != '').sum())
).reset_index().sort_values('Name')
user_summary_table = user_summary.to_html(classes='table table-striped', index=False)

# Define pay period start and calculate current period
start_date = datetime(2024, 12, 30)
today = datetime.now()
days_diff = (today - start_date).days
period_number = days_diff // 14
current_period_start = start_date + timedelta(days=period_number * 14)
current_period_end = current_period_start + timedelta(days=13)

# Filter for current pay period
two_week_df = df[
    (df['Completion time'] >= current_period_start) &
    (df['Completion time'] < current_period_end + timedelta(days=1))
].copy()
two_week_df['Date'] = two_week_df['Completion time'].dt.date

# Generate daily review HTML
daily_review_html = ''
if not two_week_df.empty:
    dates = sorted(two_week_df['Date'].unique(), reverse=True)
    for date in dates:
        daily_review_html += f'<h3>{date}</h3>'
        date_group = two_week_df[two_week_df['Date'] == date]
        for name, name_group in date_group.groupby('Name'):
            daily_review_html += f'<h4>{name}</h4>'
            boom_lifts = name_group['Boom Lift ID'].tolist()
            daily_review_html += '<ul>'
            for boom in boom_lifts:
                daily_review_html += f'<li>{boom}</li>'
            daily_review_html += '</ul>'
else:
    daily_review_html = '<p>No submissions in this period.</p>'

# Builder summary for the 2-week period
if not two_week_df.empty:
    builder_summary = two_week_df.groupby('Builder').agg(
        completions=('Completion time', 'count'),
        issues=('General Issues', lambda x: (x != '').sum())
    ).reset_index()
    builder_summary_table = builder_summary.to_html(classes='table table-striped', index=False)
else:
    builder_summary_table = '<p>No submissions in this period.</p>'

# Load Jinja2 template
try:
    with open('template.html') as f:
        template = Template(f.read())
except FileNotFoundError:
    print("Error: template.html not found in the repository.")
    raise

# Render HTML
html_content = template.render(
    full_data_table=full_data_table,
    latest_boom_table=latest_boom_table,
    user_summary_table=user_summary_table,
    current_period_start=current_period_start.strftime('%Y-%m-%d'),
    current_period_end=current_period_end.strftime('%Y-%m-%d'),
    daily_review_html=daily_review_html,
    builder_summary_table=builder_summary_table
)

# Save to index.html
with open('index.html', 'w') as f:
    f.write(html_content)
