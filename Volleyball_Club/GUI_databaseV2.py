from flask import Flask, request, redirect, session, render_template_string, flash, jsonify
import mysql.connector
from mysql.connector import Error
import webbrowser
import threading
import time
import json

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# Database configuration - UPDATE THESE VALUES
DB_CONFIG = {
    'host': '',
    'port': ,
    'database': ''
}

# Fixed Web login credentials - UPDATE
FIXED_LOGIN = {
    'username': 'ntc353_1',
    'password': 'Draty@01'
}

# MySQL credentials for database connection - UPDATE
MYSQL_CREDENTIALS = {
    'user': '',
    'password': ''
}


def get_db_connection():
    """Get database connection using fixed MySQL credentials"""
    try:
        connection = mysql.connector.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG.get('port', 3306),
            database=DB_CONFIG['database'],
            user=MYSQL_CREDENTIALS['user'],
            password=MYSQL_CREDENTIALS['password']
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None


def test_db_connection():
    """Test database connection with fixed MySQL credentials"""
    try:
        connection = mysql.connector.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG.get('port', 3306),
            database=DB_CONFIG['database'],
            user=MYSQL_CREDENTIALS['user'],
            password=MYSQL_CREDENTIALS['password']
        )
        if connection.is_connected():
            connection.close()
            return True
    except Error:
        return False


def get_table_structure(table_name):
    """Get table structure information"""
    connection = get_db_connection()
    if not connection:
        return None

    try:
        cursor = connection.cursor()
        cursor.execute(f"DESCRIBE `{table_name}`")
        structure = cursor.fetchall()
        cursor.close()
        connection.close()
        return structure
    except Error as e:
        print(f"Error getting table structure: {e}")
        return None


def get_primary_key(table_name):
    """Get primary key column(s) for a table"""
    connection = get_db_connection()
    if not connection:
        return []

    try:
        cursor = connection.cursor()
        cursor.execute(f"""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_KEY = 'PRI'
        """, (DB_CONFIG['database'], table_name))
        pk_cols = [row[0] for row in cursor.fetchall()]
        cursor.close()
        connection.close()
        return pk_cols
    except Error as e:
        print(f"Error getting primary key: {e}")
        return []


# Enhanced HTML Templates
LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>MySQL Dashboard - Login</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 400px; margin: 50px auto; padding: 20px; }
        .form-group { margin-bottom: 15px; }
        input[type="text"], input[type="password"] { width: 100%; padding: 8px; margin: 5px 0; box-sizing: border-box; }
        button { background-color: #4CAF50; color: white; padding: 10px 20px; border: none; cursor: pointer; width: 100%; }
        button:hover { background-color: #45a049; }
        .error { color: red; margin: 10px 0; }
        .success { color: green; margin: 10px 0; }
    </style>
</head>
<body>
    <h2>MySQL Database Login</h2>
    {% if message %}
        <div class="{% if error %}error{% else %}success{% endif %}">{{ message }}</div>
    {% endif %}
    <form method="POST">
        <div class="form-group">
            <label>Database Username:</label>
            <input type="text" name="username" required>
        </div>
        <div class="form-group">
            <label>Database Password:</label>
            <input type="password" name="password" required>
        </div>
        <button type="submit">Login</button>
    </form>
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>MySQL Dashboard</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1200px; margin: 20px auto; padding: 20px; }
        .header { background-color: #f4f4f4; padding: 15px; margin-bottom: 20px; }
        .nav { margin-bottom: 20px; }
        .nav a { margin-right: 15px; text-decoration: none; background-color: #4CAF50; color: white; padding: 8px 16px; }
        .nav a:hover { background-color: #45a049; }
        .logout { float: right; background-color: #f44336; }
        .logout:hover { background-color: #da190b; }
        .card { border: 1px solid #ddd; margin-bottom: 20px; padding: 15px; }
        .card h3 { margin-top: 0; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #f2f2f2; }
        .btn { background-color: #008CBA; color: white; padding: 5px 10px; text-decoration: none; margin: 2px; border: none; cursor: pointer; }
        .btn:hover { background-color: #007B9A; }
        .btn-create { background-color: #4CAF50; }
        .btn-create:hover { background-color: #45a049; }
        .btn-edit { background-color: #ff9800; }
        .btn-edit:hover { background-color: #e68900; }
        .btn-delete { background-color: #f44336; }
        .btn-delete:hover { background-color: #da190b; }
        textarea { width: 100%; height: 200px; font-family: monospace; }
        .success { color: green; margin: 10px 0; padding: 10px; background-color: #d4edda; border: 1px solid #c3e6cb; border-radius: 4px; }
        .error { color: red; margin: 10px 0; padding: 10px; background-color: #f8d7da; border: 1px solid #f5c6cb; border-radius: 4px; }
        .form-row { margin-bottom: 15px; }
        .form-row label { display: block; margin-bottom: 5px; font-weight: bold; }
        .form-row input, .form-row select { width: 100%; padding: 8px; box-sizing: border-box; }
        .form-actions { margin-top: 20px; }
        .modal { display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.5); }
        .modal-content { background-color: white; margin: 5% auto; padding: 20px; border: 1px solid #888; width: 80%; max-width: 600px; border-radius: 5px; }
        .close { color: #aaa; float: right; font-size: 28px; font-weight: bold; cursor: pointer; }
        .close:hover { color: black; }
        .actions-column { width: 200px; }
    </style>
    <script>
        function confirmDelete(table, id) {
            if (confirm('Are you sure you want to delete this record? This action cannot be undone.')) {
                window.location.href = '/delete/' + table + '/' + id;
            }
        }

        function showModal(modalId) {
            document.getElementById(modalId).style.display = 'block';
        }

        function hideModal(modalId) {
            document.getElementById(modalId).style.display = 'none';
        }
    </script>
</head>
<body>
    <div class="header">
        <h1 style="margin:0; display: inline;">Montréal Volleyball Club (MVC)</h1>
        <span style="float: right;">Connected as: {{ session.username }}</span>
    </div>

    <div class="nav">
        <a href="/">Dashboard</a>
        <a href="/tables">View Tables</a>
        <a href="/query8">Query 8</a>
        <a href="/query21">Query 21</a>
        <a href="/query22">Query 22</a>
        <a href="/logout" class="logout">Logout</a>
    </div>

    {% if message %}
        <div class="{% if error %}error{% else %}success{% endif %}">{{ message }}</div>
    {% endif %}

    {% if page == 'dashboard' %}
        <div class="card">
            <h3>Montréal Volleyball Club (MVC) - Dashboard Overview</h3>
            <p>Welcome to the MVC Database Management System</p>

            {% if dashboard_stats %}
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0;">
                    <div style="background: #e3f2fd; padding: 15px; border-radius: 5px; text-align: center;">
                        <h4 style="margin: 0; color: #1976d2;">{{ dashboard_stats.total_members }}</h4>
                        <p style="margin: 5px 0; color: #666;">Total Members</p>
                    </div>
                    <div style="background: #f3e5f5; padding: 15px; border-radius: 5px; text-align: center;">
                        <h4 style="margin: 0; color: #7b1fa2;">{{ dashboard_stats.active_teams }}</h4>
                        <p style="margin: 5px 0; color: #666;">Active Teams</p>
                    </div>
                    <div style="background: #e8f5e8; padding: 15px; border-radius: 5px; text-align: center;">
                        <h4 style="margin: 0; color: #388e3c;">{{ dashboard_stats.total_locations }}</h4>
                        <p style="margin: 5px 0; color: #666;">Club Locations</p>
                    </div>
                    <div style="background: #fff3e0; padding: 15px; border-radius: 5px; text-align: center;">
                        <h4 style="margin: 0; color: #f57c00;">{{ dashboard_stats.upcoming_sessions }}</h4>
                        <p style="margin: 5px 0; color: #666;">Upcoming Sessions</p>
                    </div>
                </div>

                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0;">
                    <div>
                        <h4>Member Statistics</h4>
                        <table style="width: 100%; font-size: 0.9em;">
                            <tr><td>Minor Members (Under 18):</td><td><strong>{{ dashboard_stats.minor_members }}</strong></td></tr>
                            <tr><td>Major Members (18+):</td><td><strong>{{ dashboard_stats.major_members }}</strong></td></tr>
                            <tr><td>Paid Members:</td><td><strong>{{ dashboard_stats.paid_members }}</strong></td></tr>
                            <tr><td>Payment Pending:</td><td><strong>{{ dashboard_stats.unpaid_members }}</strong></td></tr>
                        </table>
                    </div>
                    <div>
                        <h4>Club Activity</h4>
                        <table style="width: 100%; font-size: 0.9em;">
                            <tr><td>Total Personnel:</td><td><strong>{{ dashboard_stats.total_personnel }}</strong></td></tr>
                            <tr><td>Active Coaches:</td><td><strong>{{ dashboard_stats.coaches }}</strong></td></tr>
                            <tr><td>Recent Payments:</td><td><strong>${{ "%.2f"|format(dashboard_stats.recent_payments) }}</strong></td></tr>
                            <tr><td>Total Revenue (2024):</td><td><strong>${{ "%.2f"|format(dashboard_stats.total_revenue) }}</strong></td></tr>
                        </table>
                    </div>
                </div>

                {% if dashboard_stats.recent_members %}
                    <div style="margin: 20px 0;">
                        <h4>Recent Member Registrations</h4>
                        <table style="font-size: 0.9em;">
                            <tr>
                                <th>Name</th>
                                <th>Age</th>
                                <th>Location</th>
                                <th>Payment Status</th>
                            </tr>
                            {% for member in dashboard_stats.recent_members %}
                                <tr>
                                    <td>{{ member[0] }} {{ member[1] }}</td>
                                    <td>{{ member[2] }}</td>
                                    <td>{{ member[3] }}</td>
                                    <td>
                                        <span style="color: {% if member[4] %}green{% else %}red{% endif %};">
                                            {% if member[4] %}✓ Paid{% else %}⚠ Pending{% endif %}
                                        </span>
                                    </td>
                                </tr>
                            {% endfor %}
                        </table>
                    </div>
                {% endif %}
            {% endif %}

            <div style="margin: 20px 0; padding: 15px; background-color: #f8f9fa; border-radius: 5px;">
                <p><strong>Quick Actions:</strong></p>
                <a href="/tables" class="btn" style="margin: 5px;">Manage Tables</a>
                <a href="/query8" class="btn" style="margin: 5px;">Location Report</a>
                <a href="/query21" class="btn" style="margin: 5px;">Test Triggers</a>
                <a href="/query22" class="btn" style="margin: 5px;">Email Logs</a>
            </div>
        </div>
    {% endif %}

    {% if page == 'tables' %}
        <div class="card">
            <h3>Database Tables</h3>
            {% if tables %}
                <table>
                    <tr>
                        <th>Table Name</th>
                        <th class="actions-column">Actions</th>
                    </tr>
                    {% for table in tables %}
                    <tr>
                        <td>{{ table[0] }}</td>
                        <td>
                            <a href="/table/{{ table[0] }}" class="btn">View Data</a>
                            <a href="/create/{{ table[0] }}" class="btn btn-create">Create</a>
                        </td>
                    </tr>
                    {% endfor %}
                </table>
            {% else %}
                <p>No tables found in the database.</p>
            {% endif %}
        </div>
    {% endif %}

    {% if page == 'query' %}
        <div class="card">
            <h3>Execute SQL Query</h3>
            <form method="POST">
                <textarea name="sql_query" placeholder="Enter your SQL query here...">{{ query or '' }}</textarea><br><br>
                <button type="submit" class="btn">Execute Query</button>
            </form>
        </div>

        {% if results %}
            <div class="card">
                <h3>Query Results</h3>
                {% if results.data %}
                    <table>
                        {% if results.columns %}
                            <tr>
                                {% for col in results.columns %}
                                    <th>{{ col }}</th>
                                {% endfor %}
                            </tr>
                        {% endif %}
                        {% for row in results.data %}
                            <tr>
                                {% for cell in row %}
                                    <td>{{ cell }}</td>
                                {% endfor %}
                            </tr>
                        {% endfor %}
                    </table>
                    <p>{{ results.data|length }} rows returned</p>
                {% else %}
                    <p>Query executed successfully. {{ results.affected_rows }} rows affected.</p>
                {% endif %}
            </div>
        {% endif %}
    {% endif %}

    {% if page == 'table_view' %}
        <div class="card">
            <h3>Table: {{ table_name }}</h3>
            <div style="margin-bottom: 15px;">
                <a href="/create/{{ table_name }}" class="btn btn-create">Add New Record</a>
            </div>
            {% if table_data %}
                <table>
                    {% if table_data.columns %}
                        <tr>
                            {% for col in table_data.columns %}
                                <th>{{ col }}</th>
                            {% endfor %}
                            <th class="actions-column">Actions</th>
                        </tr>
                    {% endif %}
                    {% for row in table_data.data %}
                        <tr>
                            {% for cell in row %}
                                <td>{{ cell if cell is not none else 'NULL' }}</td>
                            {% endfor %}
                            <td>
                                {% if primary_keys %}
                                    {% set row_id = [] %}
                                    {% for pk in primary_keys %}
                                        {% set pk_index = table_data.columns.index(pk) %}
                                        {% set _ = row_id.append(row[pk_index]|string) %}
                                    {% endfor %}
                                    {% set id_string = row_id|join('|') %}
                                    <a href="/edit/{{ table_name }}/{{ id_string }}" class="btn btn-edit">Edit</a>
                                    <button onclick="confirmDelete('{{ table_name }}', '{{ id_string }}')" class="btn btn-delete">Delete</button>
                                {% endif %}
                            </td>
                        </tr>
                    {% endfor %}
                </table>
                <p>{{ table_data.data|length }} rows displayed</p>
            {% else %}
                <p>No data found in this table.</p>
            {% endif %}
        </div>
    {% endif %}

    {% if page == 'query8' %}
        <div class="card">
            <h3>Query 8 - Location Summary Report</h3>
            <p>This query provides a comprehensive overview of all locations including general managers, member counts, and team information.</p>

            {% if query8_results %}
                <table>
                    <tr>
                        <th>Location ID</th>
                        <th>Location Name</th>
                        <th>Address</th>
                        <th>City</th>
                        <th>Province</th>
                        <th>Postal Code</th>
                        <th>Phone</th>
                        <th>Website</th>
                        <th>Type</th>
                        <th>Capacity</th>
                        <th>General Manager</th>
                        <th>Minor Members</th>
                        <th>Major Members</th>
                        <th>Team Count</th>
                    </tr>
                    {% for row in query8_results %}
                        <tr>
                            <td>{{ row[0] }}</td>
                            <td>{{ row[1] }}</td>
                            <td>{{ row[2] }}</td>
                            <td>{{ row[3] }}</td>
                            <td>{{ row[4] }}</td>
                            <td>{{ row[5] }}</td>
                            <td>{{ row[6] }}</td>
                            <td>{{ row[7] if row[7] else 'N/A' }}</td>
                            <td>{{ row[8] }}</td>
                            <td>{{ row[9] }}</td>
                            <td>{{ row[10] if row[10] else 'No Manager Assigned' }}</td>
                            <td>{{ row[11] }}</td>
                            <td>{{ row[12] }}</td>
                            <td>{{ row[13] }}</td>
                        </tr>
                    {% endfor %}
                </table>
                <p>{{ query8_results|length }} location(s) found</p>
            {% else %}
                <p>No results found or query not executed yet.</p>
            {% endif %}

            <div style="margin-top: 20px;">
                <a href="/query8?execute=1" class="btn btn-create">Execute Query 8</a>
            </div>
        </div>
    {% endif %}
    {% if page == 'query21' %}
        <div class="card">
            <h3>Query 21 - Trigger Testing Operations</h3>
            <p>This section tests various database triggers and constraints including time conflicts, age requirements, team memberships, and capacity limits.</p>

            <div style="margin-bottom: 20px;">
                <h4>Available Test Operations:</h4>
                <div style="margin: 10px 0;">
                    <a href="/query21?test=1" class="btn btn-create">Test 1: Team Formation Player Assignment</a>
                    <p style="margin: 5px 0; color: #666; font-size: 0.9em;">Tests player time conflict prevention trigger</p>
                </div>
                <div style="margin: 10px 0;">
                    <a href="/query21?test=2" class="btn btn-create">Test 2: Add Young Player (Under 11)</a>
                    <p style="margin: 5px 0; color: #666; font-size: 0.9em;">Tests minimum age requirement trigger</p>
                </div>
                <div style="margin: 10px 0;">
                    <a href="/query21?test=3" class="btn btn-create">Test 3: Overlapping Team Membership</a>
                    <p style="margin: 5px 0; color: #666; font-size: 0.9em;">Tests unique active team membership trigger</p>
                </div>
                <div style="margin: 10px 0;">
                    <a href="/query21?test=4" class="btn btn-create">Test 4: Capacity Limit Update</a>
                    <p style="margin: 5px 0; color: #666; font-size: 0.9em;">Tests location capacity constraint trigger</p>
                </div>
            </div>

            {% if query21_results %}
                <div class="card" style="background-color: #f8f9fa; border-left: 4px solid #17a2b8;">
                    <h4>Test Results:</h4>
                    {% for result in query21_results %}
                        <div style="margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 4px;">
                            <strong>{{ result.test_name }}</strong><br>
                            <span class="{% if result.success %}success{% else %}error{% endif %}">
                                {{ result.message }}
                            </span>
                            {% if result.details %}
                                <br><small style="color: #666;">{{ result.details }}</small>
                            {% endif %}
                        </div>
                    {% endfor %}
                </div>
            {% endif %}
        </div>
    {% endif %}

    {% if page == 'query22' %}
        <div class="card">
            <h3>Query 22 - Email Log Operations</h3>
            <p>This section manages email logging functionality including welcome messages and coach notifications.</p>

            <div style="margin-bottom: 20px;">
                <h4>Available Email Operations:</h4>
                <div style="margin: 10px 0;">
                    <a href="/query22?action=welcome" class="btn btn-create">Send Welcome Email</a>
                    <p style="margin: 5px 0; color: #666; font-size: 0.9em;">Log a welcome email for new members</p>
                </div>
                <div style="margin: 10px 0;">
                    <a href="/query22?action=notify_coaches" class="btn btn-create">Notify All Coaches</a>
                    <p style="margin: 5px 0; color: #666; font-size: 0.9em;">Send practice session reminders to all coaches</p>
                </div>
                <div style="margin: 10px 0;">
                    <a href="/query22?action=view_logs" class="btn">View Recent Email Logs</a>
                    <p style="margin: 5px 0; color: #666; font-size: 0.9em;">Display the most recent email log entries</p>
                </div>
            </div>

            {% if email_logs %}
                <div class="card">
                    <h4>Recent Email Logs:</h4>
                    <table>
                        <tr>
                            <th>Log ID</th>
                            <th>Date/Time</th>
                            <th>Sender Location</th>
                            <th>Receiver Email</th>
                            <th>Subject</th>
                            <th>Body Preview</th>
                        </tr>
                        {% for log in email_logs %}
                            <tr>
                                <td>{{ log[0] }}</td>
                                <td>{{ log[1] }}</td>
                                <td>{{ log[2] if log[2] else 'System' }}</td>
                                <td>{{ log[3] }}</td>
                                <td>{{ log[4] }}</td>
                                <td>{{ log[5][:100] }}{% if log[5] and log[5]|length > 100 %}...{% endif %}</td>
                            </tr>
                        {% endfor %}
                    </table>
                    <p>{{ email_logs|length }} email log(s) displayed</p>
                </div>
            {% endif %}

            {% if query22_results %}
                <div class="card" style="background-color: #f8f9fa; border-left: 4px solid #28a745;">
                    <h4>Operation Results:</h4>
                    {% for result in query22_results %}
                        <div style="margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 4px;">
                            <strong>{{ result.operation }}</strong><br>
                            <span class="{% if result.success %}success{% else %}error{% endif %}">
                                {{ result.message }}
                            </span>
                            {% if result.count %}
                                <br><small style="color: #666;">{{ result.count }} records affected</small>
                            {% endif %}
                        </div>
                    {% endfor %}
                </div>
            {% endif %}
        </div>
    {% endif %}

    {% if page == 'create' or page == 'edit' %}
        <div class="card">
            <h3>{{ 'Edit' if page == 'edit' else 'Create New' }} Record in {{ table_name }}</h3>
            <form method="POST">
                {% for col in table_structure %}
                    {% set field_name = col[0] %}
                    {% set field_type = col[1] %}
                    {% set is_nullable = col[2] == 'YES' %}
                    {% set field_key = col[3] %}
                    {% set default_value = col[4] %}
                    {% set extra = col[5] %}

                    <div class="form-row">
                        <label for="{{ field_name }}">
                            {{ field_name }}
                            {% if field_key == 'PRI' %} (Primary Key){% endif %}
                            {% if not is_nullable and field_key != 'PRI' and 'auto_increment' not in extra.lower() %} *{% endif %}
                        </label>

                        {% if 'auto_increment' in extra.lower() and page == 'create' %}
                            <input type="text" value="Auto-generated" disabled>
                            <input type="hidden" name="{{ field_name }}" value="">
                        {% elif 'enum' in field_type.lower() %}
                            {% set enum_values = field_type.replace('enum(', '').replace(')', '').replace("'", '').split(',') %}
                            <select name="{{ field_name }}" {% if not is_nullable and field_key != 'PRI' %}required{% endif %}>
                                {% if is_nullable %}<option value="">NULL</option>{% endif %}
                                {% for enum_val in enum_values %}
                                    <option value="{{ enum_val.strip() }}" 
                                        {% if page == 'edit' and current_data and current_data.get(field_name) == enum_val.strip() %}selected{% endif %}>
                                        {{ enum_val.strip() }}
                                    </option>
                                {% endfor %}
                            </select>
                        {% elif 'text' in field_type.lower() or 'longtext' in field_type.lower() %}
                            <textarea name="{{ field_name }}" rows="3" {% if not is_nullable and field_key != 'PRI' %}required{% endif %}>{% if page == 'edit' and current_data %}{{ current_data.get(field_name, '') }}{% endif %}</textarea>
                        {% else %}
                            <input type="text" name="{{ field_name }}" 
                                value="{% if page == 'edit' and current_data %}{{ current_data.get(field_name, '') }}{% endif %}"
                                {% if not is_nullable and field_key != 'PRI' and 'auto_increment' not in extra.lower() %}required{% endif %}
                                {% if field_key == 'PRI' and page == 'edit' %}readonly{% endif %}>
                        {% endif %}

                        <small style="color: #666;">
                            Type: {{ field_type }}
                            {% if default_value %} | Default: {{ default_value }}{% endif %}
                            {% if extra %} | {{ extra }}{% endif %}
                        </small>
                    </div>
                {% endfor %}

                <div class="form-actions">
                    <button type="submit" class="btn btn-create">{{ 'Update' if page == 'edit' else 'Create' }} Record</button>
                    <a href="/table/{{ table_name }}" class="btn">Cancel</a>
                </div>
            </form>
        </div>
    {% endif %}

</body>
</html>
"""


@app.route('/')
def dashboard():
    if 'logged_in' not in session or not session.get('logged_in'):
        return redirect('/login')

    # Get dashboard statistics
    dashboard_stats = get_dashboard_stats()

    return render_template_string(DASHBOARD_TEMPLATE,
                                  page='dashboard',
                                  session=session,
                                  DB_CONFIG=DB_CONFIG,
                                  dashboard_stats=dashboard_stats)


def get_dashboard_stats():
    """Get dashboard statistics from database"""
    connection = get_db_connection()
    if not connection:
        return None

    try:
        cursor = connection.cursor()
        stats = {}

        # Total members
        cursor.execute("SELECT COUNT(*) FROM ClubMember")
        stats['total_members'] = cursor.fetchone()[0]

        # Active teams
        cursor.execute("SELECT COUNT(*) FROM Team")
        stats['active_teams'] = cursor.fetchone()[0]

        # Total locations
        cursor.execute("SELECT COUNT(*) FROM Location")
        stats['total_locations'] = cursor.fetchone()[0]

        # Upcoming sessions (next 30 days)
        cursor.execute("""
            SELECT COUNT(*) FROM Session 
            WHERE SessionDate >= CURDATE() AND SessionDate <= DATE_ADD(CURDATE(), INTERVAL 30 DAY)
        """)
        stats['upcoming_sessions'] = cursor.fetchone()[0]

        # Minor vs Major members
        cursor.execute("SELECT COUNT(*) FROM ClubMember WHERE isMinor = TRUE")
        stats['minor_members'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM ClubMember WHERE isMinor = FALSE")
        stats['major_members'] = cursor.fetchone()[0]

        # Paid vs Unpaid members
        cursor.execute("SELECT COUNT(*) FROM ClubMember WHERE PaymentStatus = TRUE")
        stats['paid_members'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM ClubMember WHERE PaymentStatus = FALSE")
        stats['unpaid_members'] = cursor.fetchone()[0]

        # Total personnel
        cursor.execute("SELECT COUNT(*) FROM Personnel")
        stats['total_personnel'] = cursor.fetchone()[0]

        # Active coaches
        cursor.execute("SELECT COUNT(*) FROM Personnel WHERE Role LIKE '%Coach%'")
        stats['coaches'] = cursor.fetchone()[0]

        # Recent payments (last 30 days)
        cursor.execute("""
            SELECT COALESCE(SUM(Amount), 0) FROM Payment 
            WHERE PaymentDate >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        """)
        stats['recent_payments'] = float(cursor.fetchone()[0] or 0)

        # Total revenue for 2024
        cursor.execute("""
            SELECT COALESCE(SUM(Amount), 0) FROM Payment 
            WHERE MembershipYear = 2024
        """)
        stats['total_revenue'] = float(cursor.fetchone()[0] or 0)

        # Recent member registrations (last 5)
        cursor.execute("""
            SELECT p.FirstName, p.LastName, 
                   TIMESTAMPDIFF(YEAR, p.DateOfBirth, CURDATE()) as Age,
                   l.name, cm.PaymentStatus
            FROM ClubMember cm
            JOIN Person p ON cm.ClubMemberID = p.PersonID
            LEFT JOIN Location l ON cm.locationID = l.locationID
            ORDER BY cm.ClubMemberID DESC
            LIMIT 5
        """)
        stats['recent_members'] = cursor.fetchall()

        cursor.close()
        connection.close()

        return stats

    except Error as e:
        print(f"Error fetching dashboard stats: {e}")
        return None


@app.route('/login', methods=['GET', 'POST'])
def login():
    message = None
    error = False

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == FIXED_LOGIN['username'] and password == FIXED_LOGIN['password']:
            if test_db_connection():
                session['logged_in'] = True
                session['username'] = username
                return redirect('/')
            else:
                message = 'Database connection failed! Check MySQL credentials.'
                error = True
        else:
            message = 'Invalid login credentials!'
            error = True

    return render_template_string(LOGIN_TEMPLATE, message=message, error=error)


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


@app.route('/tables')
def tables():
    if 'logged_in' not in session:
        return redirect('/login')

    connection = get_db_connection()
    tables_list = []
    message = None
    error = False

    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute("SHOW TABLES")
            tables_list = cursor.fetchall()
            cursor.close()
            connection.close()
        except Error as e:
            message = f"Error fetching tables: {e}"
            error = True
    else:
        message = 'Database connection failed!'
        error = True

    return render_template_string(DASHBOARD_TEMPLATE,
                                  page='tables',
                                  tables=tables_list,
                                  session=session,
                                  message=message,
                                  error=error)


@app.route('/query', methods=['GET', 'POST'])
def query():
    if 'logged_in' not in session:
        return redirect('/login')

    results = None
    message = None
    error = False
    query_text = ''

    if request.method == 'POST':
        query_text = request.form['sql_query']
        connection = get_db_connection()

        if connection:
            try:
                cursor = connection.cursor()
                cursor.execute(query_text)

                if query_text.strip().upper().startswith('SELECT'):
                    data = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description] if cursor.description else []
                    results = {'data': data, 'columns': columns}
                else:
                    connection.commit()
                    results = {'affected_rows': cursor.rowcount}

                cursor.close()
                connection.close()
                message = "Query executed successfully!"

            except Error as e:
                message = f"Query error: {e}"
                error = True
        else:
            message = 'Database connection failed!'
            error = True

    return render_template_string(DASHBOARD_TEMPLATE,
                                  page='query',
                                  results=results,
                                  session=session,
                                  message=message,
                                  error=error,
                                  query=query_text)


@app.route('/query21')
def query21():
    if 'logged_in' not in session:
        return redirect('/login')

    query21_results = []
    message = None
    error = False

    test_num = request.args.get('test')

    if test_num:
        connection = get_db_connection()

        if connection:
            try:
                cursor = connection.cursor()

                if test_num == '1':
                    # Test 1: Team Formation Player Assignment
                    try:
                        cursor.execute("""
                            INSERT INTO TeamFormationPlayer (FormationID, TeamID, ClubMemberID, PositionID)
                            VALUES (2004, 2, 101, 2)
                        """)
                        connection.commit()
                        query21_results.append({
                            'test_name': 'Test 1: Team Formation Player Assignment',
                            'success': True,
                            'message': 'Player assignment successful',
                            'details': 'ClubMember 101 assigned to Formation 2004'
                        })
                    except Error as e:
                        query21_results.append({
                            'test_name': 'Test 1: Team Formation Player Assignment',
                            'success': False,
                            'message': f'Assignment failed: {str(e)}',
                            'details': 'This may be due to time conflict or constraint violation'
                        })

                elif test_num == '2':
                    # Test 2: Add Young Player (Under 11)
                    try:
                        cursor.execute("""
                            INSERT INTO Person (
                                PersonID, FirstName, LastName, DateOfBirth, PhoneNo, Email, Address, City, Province, PostalCode, SSN
                            ) VALUES (
                                1201, 'Young', 'Player', '2015-01-01', '514-555-1212', 'young@example.com',
                                '999 Young St', 'Montreal', 'QC', 'H3Z2Y7', 'YNG001'
                            )
                        """)
                        cursor.execute("""
                            INSERT INTO ClubMember (ClubMemberID, PaymentStatus, isMinor)
                            VALUES (1201, TRUE, TRUE)
                        """)
                        connection.commit()
                        query21_results.append({
                            'test_name': 'Test 2: Add Young Player (Under 11)',
                            'success': False,
                            'message': 'Young player added successfully (This should have been blocked!)',
                            'details': 'Age requirement trigger may not be working properly'
                        })
                    except Error as e:
                        query21_results.append({
                            'test_name': 'Test 2: Add Young Player (Under 11)',
                            'success': True,
                            'message': f'Correctly blocked: {str(e)}',
                            'details': 'Minimum age requirement trigger working properly'
                        })

                elif test_num == '3':
                    # Test 3: Overlapping Team Membership
                    try:
                        # First insertion
                        cursor.execute("""
                            INSERT INTO memberTeam (TeamID, ClubMemberID, StartDate, EndDate) 
                            VALUES (2, 1001, '2025-06-01', '2025-09-01')
                        """)
                        connection.commit()

                        # Second overlapping insertion
                        cursor.execute("""
                            INSERT INTO memberTeam (TeamID, ClubMemberID, StartDate, EndDate)
                            VALUES (3, 1001, '2025-07-15', '2025-10-01')
                        """)
                        connection.commit()

                        query21_results.append({
                            'test_name': 'Test 3: Overlapping Team Membership',
                            'success': False,
                            'message': 'Overlapping membership added (This should have been blocked!)',
                            'details': 'Multiple active team membership trigger may not be working'
                        })
                    except Error as e:
                        query21_results.append({
                            'test_name': 'Test 3: Overlapping Team Membership',
                            'success': True,
                            'message': f'Correctly blocked: {str(e)}',
                            'details': 'Unique active team membership trigger working properly'
                        })

                elif test_num == '4':
                    # Test 4: Capacity Limit Update
                    try:
                        # First update (should work)
                        cursor.execute("UPDATE Location SET Capacity = 30 WHERE locationID = 1")
                        connection.commit()

                        # Second update (should fail)
                        cursor.execute("UPDATE Location SET Capacity = 1 WHERE locationID = 1")
                        connection.commit()

                        query21_results.append({
                            'test_name': 'Test 4: Capacity Limit Update',
                            'success': False,
                            'message': 'Capacity reduced below member count (This should have been blocked!)',
                            'details': 'Capacity constraint trigger may not be working properly'
                        })
                    except Error as e:
                        query21_results.append({
                            'test_name': 'Test 4: Capacity Limit Update',
                            'success': True,
                            'message': f'Correctly blocked: {str(e)}',
                            'details': 'Capacity constraint trigger working properly'
                        })

                cursor.close()
                connection.close()

                message = f"Test {test_num} execution completed"

            except Error as e:
                message = f"Error executing test {test_num}: {e}"
                error = True
        else:
            message = 'Database connection failed!'
            error = True

    return render_template_string(DASHBOARD_TEMPLATE,
                                  page='query21',
                                  query21_results=query21_results,
                                  session=session,
                                  message=message,
                                  error=error)


@app.route('/query22')
def query22():
    if 'logged_in' not in session:
        return redirect('/login')

    query22_results = []
    email_logs = []
    message = None
    error = False

    action = request.args.get('action')

    if action:
        connection = get_db_connection()

        if connection:
            try:
                cursor = connection.cursor()

                if action == 'welcome':
                    # Send Welcome Email
                    cursor.execute("""
                        INSERT INTO EmailLog (EmailDate, ReceiverEmail, Subject, BodyPreview)
                        VALUES (NOW(), 'example@domain.com', 'Welcome to the MVC Club!', 
                               'Thank you for registering. Your membership is now active.')
                    """)
                    connection.commit()

                    query22_results.append({
                        'operation': 'Welcome Email',
                        'success': True,
                        'message': 'Welcome email logged successfully',
                        'count': cursor.rowcount
                    })

                elif action == 'notify_coaches':
                    # Notify All Coaches
                    cursor.execute("""
                        INSERT INTO EmailLog (EmailDate, ReceiverEmail, Subject, BodyPreview)
                        SELECT 
                          NOW(),
                          p.Email,
                          'Upcoming Practice Session – Reminder',
                          CONCAT('Dear ', p.FirstName, ', you have an upcoming practice session scheduled. Please check the portal for details.')
                        FROM 
                          Personnel per
                        JOIN 
                          Person p ON p.PersonID = per.PersonnelID
                        WHERE 
                          per.Role = 'Coach'
                    """)
                    connection.commit()

                    query22_results.append({
                        'operation': 'Coach Notifications',
                        'success': True,
                        'message': 'Practice session reminders sent to all coaches',
                        'count': cursor.rowcount
                    })

                if action == 'view_logs' or action in ['welcome', 'notify_coaches']:
                    # View Recent Email Logs
                    cursor.execute("SELECT * FROM EmailLog ORDER BY LogID DESC LIMIT 10")
                    email_logs = cursor.fetchall()

                cursor.close()
                connection.close()

                if action != 'view_logs':
                    message = f"Email operation '{action}' completed successfully"
                else:
                    message = "Recent email logs retrieved"

            except Error as e:
                message = f"Error executing email operation: {e}"
                error = True
        else:
            message = 'Database connection failed!'
            error = True

    return render_template_string(DASHBOARD_TEMPLATE,
                                  page='query22',
                                  query22_results=query22_results,
                                  email_logs=email_logs,
                                  session=session,
                                  message=message,
                                  error=error)


@app.route('/query8')
def query8():
    if 'logged_in' not in session:
        return redirect('/login')

    query8_results = None
    message = None
    error = False

    # Check if we should execute the query
    if request.args.get('execute') == '1':
        connection = get_db_connection()

        if connection:
            try:
                cursor = connection.cursor()

                # The Query 8 SQL
                query_sql = """
                SELECT 
                    l.locationID,
                    l.name AS LocationName,
                    l.Address,
                    l.City,
                    l.Province,
                    l.PostalCode,
                    l.PhoneNo,
                    l.WebAddress,
                    l.Type,
                    l.Capacity,
                    -- General Manager Name (Administrator with no end date)
                    (
                        SELECT CONCAT(p.FirstName, ' ', p.LastName)
                        FROM Personnel per
                        JOIN Personnel_Location pl ON per.PersonnelID = pl.PersonnelID
                        JOIN Person p ON p.PersonID = per.PersonnelID
                        WHERE pl.LocationID = l.locationID
                          AND per.Role = 'Administrator'
                          AND pl.EndDate IS NULL
                        LIMIT 1
                    ) AS GeneralManagerName,
                    -- Count of minor members
                    COUNT(CASE WHEN cm.isMinor = TRUE THEN 1 END) AS MinorMembers,
                    -- Count of major members
                    COUNT(CASE WHEN cm.isMinor = FALSE THEN 1 END) AS MajorMembers,
                    -- Number of teams at this location
                    (
                        SELECT COUNT(*)
                        FROM Team t
                        WHERE t.LocationID = l.locationID
                    ) AS TeamCount
                FROM Location l
                -- Left join to include locations even if they have no members
                LEFT JOIN ClubMember cm ON cm.locationID = l.locationID
                GROUP BY 
                    l.locationID, l.name, l.Address, l.City, l.Province, l.PostalCode,
                    l.PhoneNo, l.WebAddress, l.Type, l.Capacity
                ORDER BY 
                    l.Province ASC,
                    l.City ASC
                """

                cursor.execute(query_sql)
                query8_results = cursor.fetchall()
                cursor.close()
                connection.close()

                message = f"Query 8 executed successfully! Found {len(query8_results)} locations."

            except Error as e:
                message = f"Error executing Query 8: {e}"
                error = True
        else:
            message = 'Database connection failed!'
            error = True

    return render_template_string(DASHBOARD_TEMPLATE,
                                  page='query8',
                                  query8_results=query8_results,
                                  session=session,
                                  message=message,
                                  error=error)


@app.route('/table/<table_name>')
def view_table(table_name):
    if 'logged_in' not in session:
        return redirect('/login')

    connection = get_db_connection()
    table_data = None
    message = None
    error = False
    primary_keys = get_primary_key(table_name)

    if connection:
        try:
            cursor = connection.cursor()
            cursor.execute(f"SELECT * FROM `{table_name}` LIMIT 100")
            data = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            table_data = {'data': data, 'columns': columns}
            cursor.close()
            connection.close()
        except Error as e:
            message = f"Error fetching table data: {e}"
            error = True
    else:
        message = 'Database connection failed!'
        error = True

    return render_template_string(DASHBOARD_TEMPLATE,
                                  page='table_view',
                                  table_name=table_name,
                                  table_data=table_data,
                                  primary_keys=primary_keys,
                                  session=session,
                                  message=message,
                                  error=error)


@app.route('/create/<table_name>', methods=['GET', 'POST'])
def create_record(table_name):
    if 'logged_in' not in session:
        return redirect('/login')

    table_structure = get_table_structure(table_name)
    message = None
    error = False

    if request.method == 'POST':
        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor()

                # Build INSERT query
                columns = []
                values = []
                placeholders = []

                for col_info in table_structure:
                    col_name = col_info[0]
                    col_extra = col_info[5]

                    # Skip auto-increment columns
                    if 'auto_increment' in col_extra.lower():
                        continue

                    form_value = request.form.get(col_name)
                    if form_value is not None and form_value != '':
                        columns.append(f"`{col_name}`")
                        values.append(form_value)
                        placeholders.append('%s')

                if columns:
                    query = f"INSERT INTO `{table_name}` ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
                    cursor.execute(query, values)
                    connection.commit()
                    message = f"Record created successfully in {table_name}!"
                else:
                    message = "No data to insert!"
                    error = True

                cursor.close()
                connection.close()

                if not error:
                    return redirect(f'/table/{table_name}')

            except Error as e:
                message = f"Error creating record: {e}"
                error = True
        else:
            message = 'Database connection failed!'
            error = True

    return render_template_string(DASHBOARD_TEMPLATE,
                                  page='create',
                                  table_name=table_name,
                                  table_structure=table_structure,
                                  session=session,
                                  message=message,
                                  error=error)


@app.route('/edit/<table_name>/<record_id>', methods=['GET', 'POST'])
def edit_record(table_name, record_id):
    if 'logged_in' not in session:
        return redirect('/login')

    table_structure = get_table_structure(table_name)
    primary_keys = get_primary_key(table_name)
    message = None
    error = False
    current_data = {}

    # Parse the record ID (might be composite)
    record_values = record_id.split('|')

    if len(record_values) != len(primary_keys):
        message = "Invalid record identifier!"
        error = True
        return render_template_string(DASHBOARD_TEMPLATE,
                                      page='edit',
                                      table_name=table_name,
                                      table_structure=table_structure,
                                      current_data=current_data,
                                      session=session,
                                      message=message,
                                      error=error)

    # Get current record data
    connection = get_db_connection()
    if connection:
        try:
            cursor = connection.cursor()

            # Build WHERE clause for primary key(s)
            where_conditions = []
            where_values = []
            for i, pk in enumerate(primary_keys):
                where_conditions.append(f"`{pk}` = %s")
                where_values.append(record_values[i])

            where_clause = " AND ".join(where_conditions)

            cursor.execute(f"SELECT * FROM `{table_name}` WHERE {where_clause}", where_values)
            row = cursor.fetchone()

            if row:
                columns = [desc[0] for desc in cursor.description]
                current_data = dict(zip(columns, row))
            else:
                message = "Record not found!"
                error = True

            cursor.close()
            connection.close()

        except Error as e:
            message = f"Error fetching record: {e}"
            error = True

    if request.method == 'POST' and not error:
        connection = get_db_connection()
        if connection:
            try:
                cursor = connection.cursor()

                # Build UPDATE query
                set_clauses = []
                update_values = []

                for col_info in table_structure:
                    col_name = col_info[0]

                    # Skip primary key columns in UPDATE
                    if col_name in primary_keys:
                        continue

                    form_value = request.form.get(col_name)
                    if form_value is not None:
                        set_clauses.append(f"`{col_name}` = %s")
                        update_values.append(form_value if form_value != '' else None)

                if set_clauses:
                    # Add WHERE clause values
                    update_values.extend(where_values)

                    query = f"UPDATE `{table_name}` SET {', '.join(set_clauses)} WHERE {where_clause}"
                    cursor.execute(query, update_values)
                    connection.commit()
                    message = f"Record updated successfully in {table_name}!"
                else:
                    message = "No data to update!"
                    error = True

                cursor.close()
                connection.close()

                if not error:
                    return redirect(f'/table/{table_name}')

            except Error as e:
                message = f"Error updating record: {e}"
                error = True
        else:
            message = 'Database connection failed!'
            error = True

    return render_template_string(DASHBOARD_TEMPLATE,
                                  page='edit',
                                  table_name=table_name,
                                  table_structure=table_structure,
                                  current_data=current_data,
                                  session=session,
                                  message=message,
                                  error=error)


@app.route('/delete/<table_name>/<record_id>')
def delete_record(table_name, record_id):
    if 'logged_in' not in session:
        return redirect('/login')

    primary_keys = get_primary_key(table_name)
    record_values = record_id.split('|')

    if len(record_values) != len(primary_keys):
        return redirect(f'/table/{table_name}')

    connection = get_db_connection()
    message = None
    error = False

    if connection:
        try:
            cursor = connection.cursor()

            # Build WHERE clause for primary key(s)
            where_conditions = []
            where_values = []
            for i, pk in enumerate(primary_keys):
                where_conditions.append(f"`{pk}` = %s")
                where_values.append(record_values[i])

            where_clause = " AND ".join(where_conditions)

            cursor.execute(f"DELETE FROM `{table_name}` WHERE {where_clause}", where_values)
            connection.commit()

            if cursor.rowcount > 0:
                message = f"Record deleted successfully from {table_name}!"
            else:
                message = "No record was deleted. Record may not exist."
                error = True

            cursor.close()
            connection.close()

        except Error as e:
            message = f"Error deleting record: {e}"
            error = True
    else:
        message = 'Database connection failed!'
        error = True

    # Redirect back to table view with message
    session['flash_message'] = message
    session['flash_error'] = error
    return redirect(f'/table/{table_name}')


def open_browser():
    """Open browser after a short delay"""
    time.sleep(1.5)
    webbrowser.open('http://127.0.0.1:5000')


if __name__ == '__main__':
    threading.Thread(target=open_browser, daemon=True).start()

    print("Starting Enhanced MySQL Dashboard...")
    print("Opening browser at http://127.0.0.1:5000")
    print("Press Ctrl+C to stop the server")

    # switch host to 0.0.0.0 for public IP
    app.run(debug=False, host='127.0.0.1', port=5000, use_reloader=False)
