import os
import pandas as pd
import requests
from io import BytesIO
from jinja2 import Template
from datetime import datetime, timedelta

# Download Excel file from environment variable URL
url = os.environ['EXCEL_URL']
response = requests.get(url, timeout=10)
response.raise_for_status()
excel_data = BytesIO(response.content)

# Read 'Sheet1' from the Excel file
df = pd.read_excel(excel_data, sheet_name='Sheet1', engine='openpyxl', parse_dates=['Completion time'])
df['General Issues'] = df['General Issues'].fillna('')
df['Maintenance Work'] = df['Maintenance Work'].fillna('')  # Ensure no NaN values
df['Cost of Maintenance'] = df['Cost of Maintenance'].fillna(0)  # Default to 0 if missing

# Define valid boom lift IDs
valid_boom_lifts = [
    'B_GNE_001', 'B_GNE_002', 'B_GNE_003', 'B_GNE_004', 
    'B_GNE_005', 'B_GNE_006', 'B_GNE_007', 'B_GNE_008', 
    'B_JLG_001', 'B_SNK_001'
]

# Filter dataframe to only include valid boom lift IDs
valid_df = df[df['Boom Lift ID'].isin(valid_boom_lifts)].copy()

# Convert 'Hours' to integer where possible
valid_df['Hours'] = valid_df['Hours'].apply(lambda x: int(x) if pd.notnull(x) else 0)

# Helper function to generate HTML table with a unique ID
def generate_html_table(df, columns, table_id):
    headers = ''.join(f'<th>{col}</th>' for col in columns)
    rows = ''
    for _, row in df.iterrows():
        cells = ''.join(f'<td>{row[col]}</td>' for col in columns)
        rows += f'<tr>{cells}</tr>'
    return f'<table class="data-table" id="{table_id}"><thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table>'

# Full Data Table with Maintenance Columns
display_columns = [
    'Completion time', 'Name', 'Boom Lift ID', 'Hours', 'Oil Level', 'Gas Level', 
    'General Issues', 'Maintenance Work', 'Cost of Maintenance'
]
full_data_df = valid_df[display_columns].sort_values('Completion time', ascending=False)
full_data_table = generate_html_table(full_data_df, display_columns, "full-data-table")

# Boom Lift Summary
boom_columns = [
    'Boom Lift ID', 'Completion time', 'Name', 'Hours', 'Oil Level', 'Gas Level', 
    'General Issues', 'Last Maintenance', 'Oil Change', 'Annual Inspection'
]

# Create a base dataframe with all valid boom lift IDs
boom_lift_summary = pd.DataFrame({'Boom Lift ID': valid_boom_lifts})

# Get the most recent submission for each boom lift (current status)
current_status = valid_df.sort_values('Completion time').groupby('Boom Lift ID').last().reset_index()

# Get the most recent maintenance date (any non-empty Maintenance Work)
maintenance_submissions = valid_df[valid_df['Maintenance Work'].notna() & (valid_df['Maintenance Work'] != '')]
last_maintenance = maintenance_submissions.sort_values('Completion time').groupby('Boom Lift ID').last().reset_index()
last_maintenance['Last Maintenance'] = last_maintenance['Completion time'].dt.strftime('%Y-%m-%d')
last_maintenance = last_maintenance[['Boom Lift ID', 'Last Maintenance']]

# Get hours at the most recent oil change
oil_changes = valid_df[valid_df['Maintenance Work'].str.contains('Oil Change', na=False)]
oil_change_latest = oil_changes.sort_values('Completion time').groupby('Boom Lift ID').last().reset_index()
oil_change_latest['Oil Change'] = oil_change_latest['Hours'].astype(int)
oil_change_latest = oil_change_latest[['Boom Lift ID', 'Oil Change']]

# Get hours at the most recent annual inspection
annual_inspections = valid_df[valid_df['Maintenance Work'].str.contains('Annual Inspection', na=False)]
annual_inspection_latest = annual_inspections.sort_values('Completion time').groupby('Boom Lift ID').last().reset_index()
annual_inspection_latest['Annual Inspection'] = annual_inspection_latest['Hours'].astype(int)
annual_inspection_latest = annual_inspection_latest[['Boom Lift ID', 'Annual Inspection']]

# Merge all data into the summary table
boom_lift_summary = boom_lift_summary.merge(
    current_status[['Boom Lift ID', 'Completion time', 'Name', 'Hours', 'Oil Level', 'Gas Level', 'General Issues']],
    on='Boom Lift ID', how='left'
).merge(
    last_maintenance, on='Boom Lift ID', how='left'
).merge(
    oil_change_latest, on='Boom Lift ID', how='left'
).merge(
    annual_inspection_latest, on='Boom Lift ID', how='left'
)

# Format columns for display
boom_lift_summary['Completion time'] = boom_lift_summary['Completion time'].apply(
    lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) else 'No Data Available'
)
for col in ['Name', 'Oil Level', 'Gas Level', 'General Issues', 'Last Maintenance']:
    boom_lift_summary[col] = boom_lift_summary[col].fillna('No Data Available')
for col in ['Hours', 'Oil Change', 'Annual Inspection']:
    boom_lift_summary[col] = boom_lift_summary[col].apply(
        lambda x: int(x) if pd.notnull(x) else 'No Data Available'
    )

latest_boom_table = generate_html_table(boom_lift_summary[boom_columns], boom_columns, "latest-boom-table")

# User Summary
user_summary = valid_df.groupby('Name').agg(
    submissions=('Completion time', 'count'),
    latest_submission=('Completion time', 'max'),
    issues=('General Issues', lambda x: (x != '').sum())
).reset_index().sort_values('Name')
user_columns = ['Name', 'submissions', 'latest_submission', 'issues']
user_summary_table = generate_html_table(user_summary, user_columns, "user-summary-table")

# 2-Week Summary with Calendar Styling
start_date = datetime(2024, 12, 30)
today = datetime.now()
days_diff = (today - start_date).days
period_number = days_diff // 14
current_period_start = start_date + timedelta(days=period_number * 14)
current_period_end = current_period_start + timedelta(days=13)
two_week_df = valid_df[
    (valid_df['Completion time'] >= current_period_start) &
    (valid_df['Completion time'] < current_period_end + timedelta(days=1))
].copy()
two_week_df['Date'] = two_week_df['Completion time'].dt.date

daily_review_html = '<div class="calendar"><div class="calendar-grid">'
days = [current_period_start + timedelta(days=i) for i in range(14)]
for day in days:
    day_str = day.strftime('%Y-%m-%d')
    day_group = two_week_df[two_week_df['Date'] == day.date()]
    submissions = ''
    if not day_group.empty:
        for name, name_group in day_group.groupby('Name'):
            boom_lifts = name_group['Boom Lift ID'].tolist()
            submissions += f'<p><strong>{name}</strong>: {", ".join(boom_lifts)}</p>'
    else:
        submissions = '<p class="no-submissions">No submissions</p>'
    daily_review_html += (
        f'<div class="calendar-day">'
        f'<h4>{day.strftime("%a, %b %d")}</h4>'
        f'{submissions}'
        f'</div>'
    )
daily_review_html += '</div></div>'

builder_summary = two_week_df.groupby('Builder').agg(
    completions=('Completion time', 'count'),
    issues=('General Issues', lambda x: (x != '').sum())
).reset_index() if not two_week_df.empty else pd.DataFrame(columns=['Builder', 'completions', 'issues'])
builder_columns = ['Builder', 'completions', 'issues']
builder_summary_table = generate_html_table(builder_summary, builder_columns, "builder-summary-table")

# Base HTML Template with DataTables CDN
base_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>M&D General Contracting - {{ page_title }}</title>
    <link rel="stylesheet" href="style.css">
    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
    <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <script src="script.js" defer></script>
</head>
<body>
    <header>
        <img src="M&D General Contracting_E4_Cropped.png" alt="M&D Logo" class="logo">
        <h1>M&D General Contracting</h1>
        <nav>
            <ul>
                <li><a href="index.html">Home</a></li>
                <li><a href="full-data.html">Full Data</a></li>
                <li><a href="user-summary.html">User Summary</a></li>
                <li><a href="two-week-summary.html">2-Week Summary</a></li>
            </ul>
        </nav>
    </header>
    <main>
        {{ content }}
    </main>
</body>
</html>
"""

# Define page contents
pages = {
    'index.html': {
        'page_title': 'Home',
        'content': (
            '<div class="summary">'
            '<h2>Welcome</h2>'
            '<p>This website tracks boom lift information submitted daily by M&D General Contracting\'s installers, '
            'providing real-time insights into equipment usage and maintenance needs.</p>'
            '</div>'
            '<h2>Latest Boom Lift Summary</h2>'
            '<div class="table-container">' + latest_boom_table + '</div>'
        )
    },
    'full-data.html': {
        'page_title': 'Full Data',
        'content': (
            '<h2>Full Data</h2>'
            '<div class="table-container">' + full_data_table + '</div>'
        )
    },
    'user-summary.html': {
        'page_title': 'User Summary',
        'content': (
            '<h2>User Summary</h2>'
            '<div class="table-container">' + user_summary_table + '</div>'
        )
    },
    'two-week-summary.html': {
        'page_title': '2-Week Summary',
        'content': (
            f'<h2>2-Week Summary ({current_period_start.strftime("%Y-%m-%d")} to {current_period_end.strftime("%Y-%m-%d")})</h2>'
            '<h3>Daily Review</h3>'
            f'{daily_review_html}'
            '<h3>Builder Summary</h3>'
            '<div class="table-container">' + builder_summary_table + '</div>'
        )
    }
}

# Generate each HTML page
template = Template(base_template)
for filename, data in pages.items():
    html_content = template.render(page_title=data['page_title'], content=data['content'])
    with open(filename, 'w') as f:
        f.write(html_content)
