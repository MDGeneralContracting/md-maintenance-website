import os
import pandas as pd
import requests
from io import BytesIO
from jinja2 import Template
from datetime import datetime, timedelta

# Download Excel file
url = os.environ['EXCEL_URL']
response = rescatuests.get(url, timeout=10)
response.raise_for_status()
excel_data = BytesIO(response.content)

# Read Sheet1
df = pd.read_excel(excel_data, sheet_name='Sheet1', engine='openpyxl', parse_dates=['Completion time'])
df['General Issues'] = df['General Issues'].fillna('')

# Helper function to generate HTML table compatible with DataTables
def generate_html_table(df, columns):
    headers = ''.join(f'<th>{col}</th>' for col in columns)
    rows = ''
    for _, row in df.iterrows():
        cells = ''.join(f'<td>{row[col]}</td>' for col in columns)
        rows += f'<tr>{cells}</tr>'
    return f'<table class="data-table" id="data-table"><thead><tr>{headers}</tr></thead><tbody>{rows}</tbody></table>'

# Full Data Table
display_columns = [
    'Name', 'Boom Lift ID', 'Completion time', 'Builder', 'Site', 'Hours',
    'Oil Level', 'Gas Level', 'General Issues', 'Continue to Maintenance or Complete'
]
full_data_df = df[display_columns].sort_values('Completion time', ascending=False)
full_data_table = generate_html_table(full_data_df, display_columns)

# Latest Boom Lift Summary
boom_columns = ['Boom Lift ID', 'Completion time', 'Name', 'Hours', 'Oil Level', 'Gas Level', 'General Issues']
latest_boom = df.sort_values('Completion time', ascending=False).drop_duplicates('Boom Lift ID').sort_values('Boom Lift ID')
latest_boom_table = generate_html_table(latest_boom[boom_columns], boom_columns)

# User Summary
user_summary = df.groupby('Name').agg(
    submissions=('Completion time', 'count'),
    latest_submission=('Completion time', 'max'),
    issues=('General Issues', lambda x: (x != '').sum())
).reset_index().sort_values('Name')
user_columns = ['Name', 'submissions', 'latest_submission', 'issues']
user_summary_table = generate_html_table(user_summary, user_columns)

# 2-Week Summary
start_date = datetime(2024, 12, 30)
today = datetime.now()
days_diff = (today - start_date).days
period_number = days_diff // 14
current_period_start = start_date + timedelta(days=period_number * 14)
current_period_end = current_period_start + timedelta(days=13)
two_week_df = df[
    (df['Completion time'] >= current_period_start) &
    (df['Completion time'] < current_period_end + timedelta(days=1))
].copy()
two_week_df['Date'] = two_week_df['Completion time'].dt.date

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

builder_summary = two_week_df.groupby('Builder').agg(
    completions=('Completion time', 'count'),
    issues=('General Issues', lambda x: (x != '').sum())
).reset_index() if not two_week_df.empty else pd.DataFrame(columns=['Builder', 'completions', 'issues'])
builder_columns = ['Builder', 'completions', 'issues']
builder_summary_table = generate_html_table(builder_summary, builder_columns)

# Base Template with DataTables CDN
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
            '<div class="daily-review">' + daily_review_html + '</div>'
            '<h3>Builder Summary</h3>'
            '<div class="table-container">' + builder_summary_table + '</div>'
        )
    }
}

# Generate each page
template = Template(base_template)
for filename, data in pages.items():
    html_content = template.render(page_title=data['page_title'], content=data['content'])
    with open(filename, 'w') as f:
        f.write(html_content)
