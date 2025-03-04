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
df['Maintenance Work'] = df['Maintenance Work'].fillna('')
df['Cost of Maintenance'] = df['Cost of Maintenance'].fillna(0)

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
boom_lift_summary = pd.DataFrame({'Boom Lift ID': valid_boom_lifts})
current_status = valid_df.sort_values('Completion time').groupby('Boom Lift ID').last().reset_index()
last_maintenance = valid_df[valid_df['Maintenance Work'].notna() & (valid_df['Maintenance Work'] != '')].sort_values('Completion time').groupby('Boom Lift ID').last().reset_index()
last_maintenance['Last Maintenance'] = last_maintenance['Completion time'].dt.strftime('%Y-%m-%d')
oil_changes = valid_df[valid_df['Maintenance Work'].str.lower().str.contains('oil change', na=False)].sort_values('Completion time').groupby('Boom Lift ID').last().reset_index()
oil_changes['Oil Change'] = oil_changes['Hours'].astype(int)
annual_inspections = valid_df[valid_df['Maintenance Work'].str.lower().str.contains('annual inspection', na=False)].sort_values('Completion time').groupby('Boom Lift ID').last().reset_index()
annual_inspections['Annual Inspection'] = annual_inspections['Hours'].astype(int)

boom_lift_summary = boom_lift_summary.merge(
    current_status[['Boom Lift ID', 'Completion time', 'Name', 'Hours', 'Oil Level', 'Gas Level', 'General Issues']],
    on='Boom Lift ID', how='left'
).merge(last_maintenance[['Boom Lift ID', 'Last Maintenance']], on='Boom Lift ID', how='left').merge(
    oil_changes[['Boom Lift ID', 'Oil Change']], on='Boom Lift ID', how='left'
).merge(annual_inspections[['Boom Lift ID', 'Annual Inspection']], on='Boom Lift ID', how='left')

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

# 2-Week Summary with Dropdown for Pay Periods
start_date = datetime(2024, 12, 30)  # Initial pay period start date
today = datetime.now()
days_diff = (today - start_date).days
period_number = days_diff // 14

# Generate all pay periods from start_date to current period
all_start_dates = [start_date + timedelta(days=14 * i) for i in range(period_number + 1)]
all_start_dates.reverse()  # Most recent first

# Limit to current and previous 10 periods (11 total)
recent_start_dates = all_start_dates[:11]

# Precompute pay periods with start and end dates
pay_periods = []
for start in recent_start_dates:
    end = start + timedelta(days=13)
    pay_periods.append({
        'start': start.strftime('%Y-%m-%d'),
        'end': end.strftime('%Y-%m-%d'),
        'filename': f"two-week-summary-{start.strftime('%Y-%m-%d')}.html"
    })

# Function to generate summary for a given pay period
def generate_pay_period_summary(start_date):
    end_date = start_date + timedelta(days=13)
    period_df = valid_df[
        (valid_df['Completion time'] >= start_date) &
        (valid_df['Completion time'] < end_date + timedelta(days=1))
    ].copy()
    period_df['Date'] = period_df['Completion time'].dt.date

    # Daily Review Calendar
    daily_review_html = '<div class="calendar"><div class="calendar-grid">'
    days = [start_date + timedelta(days=i) for i in range(14)]
    for day in days:
        day_group = period_df[period_df['Date'] == day.date()]
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

    # Builder Summary
    builder_summary = period_df.groupby('Builder').agg(
        completions=('Completion time', 'count'),
        issues=('General Issues', lambda x: (x != '').sum())
    ).reset_index() if not period_df.empty else pd.DataFrame(columns=['Builder', 'completions', 'issues'])
    builder_columns = ['Builder', 'completions', 'issues']
    builder_summary_table = generate_html_table(builder_summary, builder_columns, "builder-summary-table")

    return daily_review_html, builder_summary_table

# Base Template with DataTables CDN and Pay Period Dropdown
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
        <div class="pay-period-selector">
            <label for="pay-period-select">Select Pay Period: </label>
            <select id="pay-period-select">
                {% for period in pay_periods %}
                <option value="{{ period.filename }}"
                        {% if period.start == current_start_date %}selected{% endif %}>
                    {{ period.start }} to {{ period.end }}
                </option>
                {% endfor %}
            </select>
            <script>
                document.getElementById('pay-period-select').addEventListener('change', function() {
                    window.location.href = this.value;
                });
            </script>
        </div>
        {{ content | safe }}
    </main>
</body>
</html>
"""

# Generate pages for each pay period
for i, start_date in enumerate(recent_start_dates):
    daily_review_html, builder_summary_table = generate_pay_period_summary(start_date)
    end_date = start_date + timedelta(days=13)
    content = f"""
        <h2>2-Week Summary ({start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')})</h2>
        <h3>Daily Review</h3>
        {daily_review_html}
        <h3>Builder Summary</h3>
        <div class="table-container">{builder_summary_table}</div>
    """
    filename = f"two-week-summary-{start_date.strftime('%Y-%m-%d')}.html"
    if i == 0:  # Current period
        current_start_date = start_date.strftime('%Y-%m-%d')
        current_content = content
    
    html_content = Template(base_template).render(
        page_title=f'2-Week Summary ({start_date.strftime("%Y-%m-%d")})',
        content=content,
        pay_periods=pay_periods,
        current_start_date=current_start_date
    )
    with open(filename, 'w') as f:
        f.write(html_content)

# Save the current period to two-week-summary.html
with open('two-week-summary.html', 'w') as f:
    f.write(Template(base_template).render(
        page_title='2-Week Summary (Current)',
        content=current_content,
        pay_periods=pay_periods,
        current_start_date=current_start_date
    ))

# Generate other pages
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
    }
}

# Generate remaining HTML pages
template = Template(base_template)
for filename, data in pages.items():
    html_content = template.render(
        page_title=data['page_title'],
        content=data['content'],
        pay_periods=pay_periods,
        current_start_date=current_start_date
    )
    with open(filename, 'w') as f:
        f.write(html_content)
