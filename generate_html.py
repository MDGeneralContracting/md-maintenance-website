import os
import pandas as pd
import requests
from io import BytesIO
from jinja2 import Template
from datetime import datetime, timedelta

# GitHub raw CSV URL
CSV_URL = 'https://raw.githubusercontent.com/MDGeneralContracting/md-maintenance-website/main/data/boom_lift_data.csv'
response = requests.get(CSV_URL, timeout=10)
response.raise_for_status()
df = pd.read_csv(pd.io.common.StringIO(response.text), parse_dates=['Completion time'])

# Fill missing values
df['General Issues'] = df['General Issues'].fillna('')
df['Maintenance Work'] = df['Maintenance Work'].fillna('')
df['Oil Change'] = df['Oil Change'].fillna(False)
df['Annual Inspection'] = df['Annual Inspection'].fillna(False)
df['NDT'] = df['NDT'].fillna(False)
df['Radiator Repair'] = df['Radiator Repair'].fillna(False)
df['Other Work'] = df['Other Work'].fillna('')
for col in ['Oil Change Cost', 'Annual Inspection Cost', 'NDT Cost', 'Radiator Repair Cost', 'Other Work Cost', 'Cost of Maintenance']:
    df[col] = df[col].fillna(0)

# Define valid boom lift IDs (unchanged)
valid_boom_lifts = [
    'B_GNE_001', 'B_GNE_002', 'B_GNE_003', 'B_GNE_004',
    'B_GNE_005', 'B_GNE_006', 'B_GNE_007', 'B_GNE_008',
    'B_JLG_001', 'B_SNK_001'
]

# Filter dataframe
valid_df = df[df['Boom Lift ID'].isin(valid_boom_lifts)].copy()
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
    'General Issues', 'Last Maintenance', 'Oil Change', 'Hours Since Oil Change', 'Annual Inspection'
]
boom_lift_summary = pd.DataFrame({'Boom Lift ID': valid_boom_lifts})
current_status = valid_df.sort_values('Completion time').groupby('Boom Lift ID').last().reset_index()
last_maintenance = valid_df[valid_df['Maintenance Work'].notna() & (valid_df['Maintenance Work'] != '')].sort_values('Completion time').groupby('Boom Lift ID').last().reset_index()
last_maintenance['Last Maintenance'] = last_maintenance['Completion time'].dt.strftime('%Y-%m-%d')
oil_changes = valid_df[valid_df['Maintenance Work'].str.lower().str.contains('oil change', na=False)].sort_values('Completion time').groupby('Boom Lift ID').last().reset_index()
oil_changes['Oil Change'] = oil_changes['Hours'].astype(int)  # Hours at last oil change
oil_changes['Oil Change Hours'] = oil_changes['Hours'].astype(int)  # Temporary for calculation
annual_inspections = valid_df[valid_df['Maintenance Work'].str.lower().str.contains('annual inspection', na=False)].sort_values('Completion time').groupby('Boom Lift ID').last().reset_index()
annual_inspections['Annual Inspection'] = annual_inspections['Completion time'].dt.strftime('%Y-%m-%d')  # Use date instead of hours

# Merge data into summary
boom_lift_summary = boom_lift_summary.merge(
    current_status[['Boom Lift ID', 'Completion time', 'Name', 'Hours', 'Oil Level', 'Gas Level', 'General Issues']],
    on='Boom Lift ID', how='left'
).merge(last_maintenance[['Boom Lift ID', 'Last Maintenance']], on='Boom Lift ID', how='left').merge(
    oil_changes[['Boom Lift ID', 'Oil Change', 'Oil Change Hours']], on='Boom Lift ID', how='left'
).merge(annual_inspections[['Boom Lift ID', 'Annual Inspection']], on='Boom Lift ID', how='left')

# Calculate Hours Since Oil Change
boom_lift_summary['Hours Since Oil Change'] = boom_lift_summary.apply(
    lambda row: int(row['Hours'] - row['Oil Change Hours']) if pd.notnull(row['Oil Change Hours']) else 'No Data',
    axis=1
)

# Format dates and handle missing data
boom_lift_summary['Completion time'] = boom_lift_summary['Completion time'].apply(
    lambda x: x.strftime('%Y-%m-%d') if pd.notnull(x) else 'No Data Available'
)
for col in ['Name', 'Oil Level', 'Gas Level', 'General Issues', 'Last Maintenance', 'Annual Inspection']:
    boom_lift_summary[col] = boom_lift_summary[col].fillna('No Data Available')
for col in ['Hours', 'Oil Change']:
    boom_lift_summary[col] = boom_lift_summary[col].apply(
        lambda x: int(x) if pd.notnull(x) else 'No Data Available'
    )

# Generate the table
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

# Base Template without Dropdown (for non-summary pages)
base_template_no_dropdown = """
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
        {{ content | safe }}
    </main>
</body>
</html>
"""

# Base Template with Dropdown (for summary pages)
base_template_with_dropdown = """
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
    print(f"Generating file: two-week-summary-{start_date.strftime('%Y-%m-%d')}.html")
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
    current_start_date = start_date.strftime('%Y-%m-%d')  # Specific to this page
    
    html_content = Template(base_template_with_dropdown).render(
        page_title=f'2-Week Summary ({start_date.strftime("%Y-%m-%d")})',
        content=content,
        pay_periods=pay_periods,
        current_start_date=current_start_date
    )
    with open(filename, 'w') as f:
        f.write(html_content)
    print(f"Successfully wrote: {filename}")

# Save the current period to two-week-summary.html
print("Generating file: two-week-summary.html")
latest_start_date = recent_start_dates[0].strftime('%Y-%m-%d')  # Current period
daily_review_html, builder_summary_table = generate_pay_period_summary(recent_start_dates[0])
end_date = recent_start_dates[0] + timedelta(days=13)
current_content = f"""
    <h2>2-Week Summary ({latest_start_date} to {end_date.strftime('%Y-%m-%d')})</h2>
    <h3>Daily Review</h3>
    {daily_review_html}
    <h3>Builder Summary</h3>
    <div class="table-container">{builder_summary_table}</div>
"""
with open('two-week-summary.html', 'w') as f:
    f.write(Template(base_template_with_dropdown).render(
        page_title='2-Week Summary (Current)',
        content=current_content,
        pay_periods=pay_periods,
        current_start_date=latest_start_date
    ))
print("Successfully wrote: two-week-summary.html")

# Generate other pages without dropdown
pages = {
    'submit.html': {
        'page_title': 'Submit Boom Lift Data',
        'content': '''
            <h2>Submit Boom Lift Data</h2>
            <form id="boom-lift-form" method="POST">
                <label for="role">Role:</label><br>
                <select id="role" name="role" required onchange="toggleForm()">
                    <option value="">Select Role</option>
                    <option value="installer">Installer</option>
                    <option value="mechanic">Mechanic</option>
                </select><br><br>

                <!-- Installer Form -->
                <div id="installer-form" style="display: none;">
                    <label for="installer-name">User Name:</label><br>
                    <select id="installer-name" name="Name">
                        <option value="">Select Name</option>
                        <option value="Domogoj Cutuk">Domogoj Cutuk</option>
                        <option value="Stanko Lukenda">Stanko Lukenda</option>
                        <option value="Ivan Primorac">Ivan Primorac</option>
                        <option value="C&3Js">C&3Js</option>
                        <option value="KCA">KCA</option>
                        <option value="Shawn Jackman">Shawn Jackman</option>
                        <option value="Srecko Pivac">Srecko Pivac</option>
                        <option value="Nikola Rotim">Nikola Rotim</option>
                        <option value="Xtreme Aluminum">Xtreme Aluminum</option>
                        <option value="M&D Admin">M&D Admin</option>
                        <option value="Mechanic">Mechanic</option>
                    </select><br><br>

                    <label for="boom-lift-id">Boom Lift ID:</label><br>
                    <select id="boom-lift-id" name="Boom Lift ID" required onchange="updateHoursValidation()">
                        <option value="">Select Boom Lift</option>
                        <option value="B_GNE_001">B_GNE_001</option>
                        <option value="B_GNE_002">B_GNE_002</option>
                        <option value="B_GNE_003">B_GNE_003</option>
                        <option value="B_GNE_004">B_GNE_004</option>
                        <option value="B_GNE_005">B_GNE_005</option>
                        <option value="B_GNE_006">B_GNE_006</option>
                        <option value="B_GNE_007">B_GNE_007</option>
                        <option value="B_GNE_008">B_GNE_008</option>
                        <option value="B_JLG_001">B_JLG_001</option>
                        <option value="B_SNK_001">B_SNK_001</option>
                    </select><br><br>

                    <label for="builder">Builder:</label><br>
                    <select id="builder" name="Builder" onchange="toggleOtherBuilder()">
                        <option value="">Select Builder</option>
                        <option value="Mattamy">Mattamy</option>
                        <option value="Caivan">Caivan</option>
                        <option value="Eden Oak">Eden Oak</option>
                        <option value="Branthaven">Branthaven</option>
                        <option value="Charleston">Charleston</option>
                        <option value="Dincenzo">Dincenzo</option>
                        <option value="Other">Other</option>
                    </select>
                    <input type="text" id="other-builder" name="Other Builder" style="display: none;" placeholder="Specify Other"><br><br>

                    <label for="site">Site:</label><br>
                    <input type="text" id="site" name="Site" required><br><br>

                    <input type="hidden" id="completion-time" name="Completion time">

                    <label for="location">Location:</label><br>
                    <button type="button" id="get-location" onclick="getGeolocation()">Use My Location</button>
                    <input type="text" id="location" name="Location" readonly><br><br>

                    <label for="hours">Hours:</label><br>
                    <input type="number" id="hours" name="Hours" required min="0" step="1"><br><br>

                    <label for="oil-level">Oil Level:</label><br>
                    <select id="oil-level" name="Oil Level" required>
                        <option value="">Select Level</option>
                        <option value="High">High</option>
                        <option value="Sufficient">Sufficient</option>
                        <option value="Low">Low</option>
                    </select><br><br>

                    <label for="gas-level">Gas Level:</label><br>
                    <select id="gas-level" name="Gas Level" required>
                        <option value="">Select Level</option>
                        <option value="Full">Full</option>
                        <option value="Half">Half</option>
                        <option value="Low">Low</option>
                    </select><br><br>

                    <label for="general-issues">General Issues:</label><br>
                    <textarea id="general-issues" name="General Issues"></textarea><br><br>

                    <label><input type="checkbox" id="certify-installer" required> I certify that the information is correct</label><br><br>
                </div>

                <!-- Mechanic Form -->
                <div id="mechanic-form" style="display: none;">
                    <label for="mechanic-name">User Name:</label><br>
                    <select id="mechanic-name" name="Name">
                        <option value="">Select Name</option>
                        <option value="M&D Admin">M&D Admin</option>
                        <option value="Mechanic">Mechanic</option>
                    </select><br><br>

                    <label for="mechanic-boom-lift-id">Boom Lift ID:</label><br>
                    <select id="mechanic-boom-lift-id" name="Boom Lift ID" required onchange="updateHoursValidation()">
                        <option value="">Select Boom Lift</option>
                        <option value="B_GNE_001">B_GNE_001</option>
                        <option value="B_GNE_002">B_GNE_002</option>
                        <option value="B_GNE_003">B_GNE_003</option>
                        <option value="B_GNE_004">B_GNE_004</option>
                        <option value="B_GNE_005">B_GNE_005</option>
                        <option value="B_GNE_006">B_GNE_006</option>
                        <option value="B_GNE_007">B_GNE_007</option>
                        <option value="B_GNE_008">B_GNE_008</option>
                        <option value="B_JLG_001">B_JLG_001</option>
                        <option value="B_SNK_001">B_SNK_001</option>
                    </select><br><br>

                    <label for="mechanic-builder">Builder:</label><br>
                    <select id="mechanic-builder" name="Builder" onchange="toggleOtherBuilderMechanic()">
                        <option value="">Select Builder</option>
                        <option value="Mattamy">Mattamy</option>
                        <option value="Caivan">Caivan</option>
                        <option value="Eden Oak">Eden Oak</option>
                        <option value="Branthaven">Branthaven</option>
                        <option value="Charleston">Charleston</option>
                        <option value="Dincenzo">Dincenzo</option>
                        <option value="Other">Other</option>
                    </select>
                    <input type="text" id="mechanic-other-builder" name="Other Builder" style="display: none;" placeholder="Specify Other"><br><br>

                    <label for="mechanic-site">Site:</label><br>
                    <input type="text" id="mechanic-site" name="Site" required><br><br>

                    <input type="hidden" id="mechanic-completion-time" name="Completion time">

                    <label for="mechanic-location">Location:</label><br>
                    <button type="button" id="mechanic-get-location" onclick="getGeolocationMechanic()">Use My Location</button>
                    <input type="text" id="mechanic-location" name="Location" readonly><br><br>

                    <label for="mechanic-hours">Hours:</label><br>
                    <input type="number" id="mechanic-hours" name="Hours" required min="0" step="1"><br><br>

                    <label for="mechanic-oil-level">Oil Level:</label><br>
                    <select id="mechanic-oil-level" name="Oil Level" required>
                        <option value="">Select Level</option>
                        <option value="High">High</option>
                        <option value="Sufficient">Sufficient</option>
                        <option value="Low">Low</option>
                    </select><br><br>

                    <label for="mechanic-gas-level">Gas Level:</label><br>
                    <select id="mechanic-gas-level" name="Gas Level" required>
                        <option value="">Select Level</option>
                        <option value="Full">Full</option>
                        <option value="Half">Half</option>
                        <option value="Low">Low</option>
                    </select><br><br>

                    <label>Oil Change:</label><br>
                    <input type="checkbox" id="oil-change" name="Oil Change" onchange="toggleOilChangeCost()"> Completed
                    <input type="number" id="oil-change-cost" name="Oil Change Cost" style="display: none;" step="0.01" placeholder="Cost"><br><br>

                    <label>Annual Inspection:</label><br>
                    <input type="checkbox" id="annual-inspection" name="Annual Inspection" onchange="toggleAnnualInspectionCost()"> Completed
                    <input type="number" id="annual-inspection-cost" name="Annual Inspection Cost" style="display: none;" step="0.01" placeholder="Cost"><br><br>

                    <label>NDT:</label><br>
                    <input type="checkbox" id="ndt" name="NDT" onchange="toggleNDTCost()"> Completed
                    <input type="number" id="ndt-cost" name="NDT Cost" style="display: none;" step="0.01" placeholder="Cost"><br><br>

                    <label>Radiator Repair:</label><br>
                    <input type="checkbox" id="radiator-repair" name="Radiator Repair" onchange="toggleRadiatorRepairCost()"> Completed
                    <input type="number" id="radiator-repair-cost" name="Radiator Repair Cost" style="display: none;" step="0.01" placeholder="Cost"><br><br>

                    <label for="other-work">Other Work Completed:</label><br>
                    <textarea id="other-work" name="Other Work" onchange="toggleOtherWorkCost()"></textarea>
                    <input type="number" id="other-work-cost" name="Other Work Cost" style="display: none;" step="0.01" placeholder="Cost"><br><br>

                    <label for="maintenance-work">Final Maintenance Work Description:</label><br>
                    <textarea id="maintenance-work" name="Maintenance Work"></textarea><br><br>

                    <label><input type="checkbox" id="certify-mechanic" required> I certify that the information is correct</label><br><br>
                </div>

                <button type="submit">Submit</button>
            </form>
            <p id="submission-message" style="display: none;">Submission successful!</p>
        '''
    },
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

# Generate remaining HTML pages without dropdown
template = Template(base_template_no_dropdown)
for filename, data in pages.items():
    print(f"Generating file: {filename}")
    html_content = template.render(
        page_title=data['page_title'],
        content=data['content']
    )
    with open(filename, 'w') as f:
        f.write(html_content)
    print(f"Successfully wrote: {filename}")
