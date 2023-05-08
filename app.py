from flask import Flask, render_template, request, jsonify, session, flash
import pyodbc
from jinja2 import Environment
from flask import redirect
from flask_wtf import FlaskForm
from wtforms import StringField, DateField, SelectField
from wtforms.validators import DataRequired
from flask_bootstrap import Bootstrap
from flask_datepicker import datepicker
from datetime import datetime
import os
from gevent.pywsgi import WSGIServer

env = Environment()
env.globals.update(len=len)

app = Flask(__name__)

app.secret_key = '000d88cd9d90036ebdd237eb6b0db000'

Bootstrap(app)
datepicker(app)

class UpgradeForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired()])
    agiblock_version = SelectField('Agiblock Version', choices=[], validators=[DataRequired()])
    plugin_version = SelectField('Plugin Version', choices=[], validators=[DataRequired()])
    date_of_upgrade = DateField('Date of Upgrade', format='%Y-%m-%dT%H:%M:%S.%f', validators=[DataRequired()])

# Replace the values in the connection string with your own
server = 'sql-qa-agiblocks-004.database.windows.net'

database = 'application-python'

username = 'agiboo'

password = 'qzu22TdMn5kCeZa8nL8Q4qMp'

driver = '{ODBC Driver 18 for SQL Server}'

server = 'xxx'

database = 'application-python'

username = 'xxxx'

password = 'xx'

driver = '{ODBC Driver 18 for SQL Server}'

# Establish a connection to the database
conn = pyodbc.connect('DRIVER=' + driver + ';SERVER=' + server + ';PORT=1433;DATABASE=' + database + ';UID=' + username + ';PWD=' + password + ';Connect Timeout=90;')

@app.route('/health')
def health():
    try:
        with conn.cursor() as cursor:
          cursor.execute('SELECT 1')
          cursor.fetchall()
        return jsonify({'status': 'ok'})
    except Exception as e:
        print("Error:", e)
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/', methods=['GET', 'POST'])
def index():
    # Get the values for the first drop-down menu from the database
    with conn.cursor() as cursor:
        cursor.execute('SELECT DISTINCT Cust FROM [dbo].[application-upgrade-table]')
        options1 = [row[0] for row in cursor.fetchall()]

    options2 = []
    results = []
    if request.method == 'POST':
        num_dropdowns = int(request.form.get('numPairs'))
        selected_values = {}
        for i in range(1, num_dropdowns + 1):
            selected_values[f"dropdown{i}"] = request.form.get(f"dropdown{i}")
        if all(selected_values.values()):
            with conn.cursor() as cursor:
                cursor.execute("SELECT DISTINCT Env FROM [dbo].[application-upgrade-table] WHERE Cust= '{}' ORDER BY Env ASC".format(selected_values['dropdown1']))
                options2 = [row[0] for row in cursor.fetchall()]

                session['customer'] = selected_values['dropdown1']
                session['env'] = selected_values['dropdown2']
                cursor.execute("SELECT DISTINCT AgiblocksVersion, Pluginversion FROM [dbo].[application-version] ORDER BY AgiblocksVersion, Pluginversion")
                agiblock_plugin_versions = cursor.fetchall()
                agiblock_versions = sorted(list(set([row[0] for row in agiblock_plugin_versions])))
                plugin_versions = sorted(list(set([row[1] for row in agiblock_plugin_versions])))
                cursor.execute("select a.Subscription,a.Cust,b.Env,a.SiteUrl,a.AgiblockVersion,a.Pluginversion,b.Masterdata,b.Basiscost,b.Businesscentralplaceholderapi,b.Certificates,b.Costofcarry,b.Derivativesintegration,b.Mailer,b.Marketprices,b.Notification,b.Propertycalculator,b.Purchaseallocation,b.Salesallocation,b.Sampling,b.Scaletickets,b.Selfbilling,b.Scheduler,b.Reporting,b.Transportorders,b.MessageOrchestration, b.Selfbillingreporting FROM [dbo].[application-upgrade-table] a inner join [dbo].[application-plugin-table] b  on a.customer=b.customer and a.env=b.env WHERE a.Cust = '{}' AND a.Env = '{}'".format(selected_values['dropdown1'], selected_values['dropdown2']))
                rows = cursor.fetchall()
                column_names = [column[0] for column in cursor.description]
                results = [dict(zip(column_names, row)) for row in rows]
                non_boolean_columns = [column_name for column_name in column_names if cursor.description[column_names.index(column_name)][1] not in (bool, type(None))]
                boolean_columns = [column_name for column_name in column_names if cursor.description[column_names.index(column_name)][1] == bool]
                columns_list = ['Agiblockversion', 'Pluginversion', 'DateofUpgrade']
                form = UpgradeForm()
                form.agiblock_version.choices = [(version, version) for version in agiblock_versions]
                form.plugin_version.choices = [(version, version) for version in plugin_versions]
                session['results'] = results
                session['boolean_columns'] = boolean_columns
                if form.validate_on_submit():
                    print('Form validated successfully!')
                    # Handle form submission
                    name = form.name.data
                    date_of_upgrade = form.date_of_upgrade.data
                versions = {'Agiblockversion': agiblock_versions, 'Pluginversion': plugin_versions}
                return render_template('searchresult.html', results=results, form=form, non_boolean_columns=non_boolean_columns, boolean_columns=boolean_columns, columns_list=columns_list,versions=versions)
           
    return render_template('index.html', options1=options1, options2=options2, results=results)


@app.route('/get_options', methods=['POST'])
def get_options():
    # Get the selected value from dropdown 1
    selected_value = request.form['dropdown1']
    
    # Query the database for the options for dropdown 2 based on the selected value from dropdown 1
    with conn.cursor() as cursor:
        cursor.execute("SELECT DISTINCT Env FROM [dbo].[application-upgrade-table] WHERE Cust = '{}' ORDER BY Env ASC".format(selected_value))
        options2 = [row[0] for row in cursor.fetchall()]
    
    # Return the options for dropdown 2 as a JSON response
    return jsonify({'options': options2})


@app.route('/update', methods=['POST'])
def update():
    # Get the form data submitted by the user
    form_data = request.form.to_dict()
    results = session.get('results')
    # Extract the column names and values from the form data
    non_boolean_columns = []
    non_boolean_values = []
    boolean_columns = []
    boolean_values = []
    customer = session.get('customer')
    env = session.get('env')

    # Define the columns that should trigger update query 1
    update_query1_columns = ['Agiblockversion', 'Pluginversion', 'DateofUpgrade']

    # Define the columns that should trigger update query 2
    update_query2_columns = ['Masterdata', 'Basiscost', 'Businesscentralplaceholderapi', 'Certificates', 'Costofcarry', 'Derivativesintegration', 'Mailer', 'Marketprices', 'Notification', 'Propertycalculator', 'Purchaseallocation', 'Salesallocation', 'Sampling', 'Scaletickets', 'Selfbilling', 'Scheduler', 'Reporting', 'Transportorders', 'MessageOrchestration', 'Selfbillingreporting']
    
    for key, value in form_data.items():
        if value.lower() in ('true', 'false'):
            boolean_columns.append(key)
            boolean_values.append(value.lower() == 'true')
        elif key in update_query1_columns:
            non_boolean_columns.append(key)
            non_boolean_values.append(value)

    # Construct the SQL UPDATE statements
    with conn.cursor() as cursor:

        refresh_query = "SELECT * FROM [dbo].[application-plugin-table] OPTION (LABEL='BeforeUpdate');"
        cursor.execute(refresh_query)

        # Define the columns that should trigger update query  
        if any(col in boolean_columns for col in update_query2_columns):
            update_query = "UPDATE [dbo].[application-plugin-table] SET "
        
            for i in range(len(boolean_columns)):
                column = boolean_columns[i]
                if boolean_values[i]:
                    update_query += "{} = 'true'".format(column)
                else:
                    update_query += "{} = 'false'".format(column)
                if i < len(boolean_columns) - 1:
                    update_query += ", "
        
            update_query += "from [dbo].[application-plugin-table] a join [dbo].[application-upgrade-table] x on a.customer = x.customer and a.env = x.env WHERE x.Cust = '{}' AND x.Env = '{}'".format(customer, env)
        
            cursor.execute(update_query)
            conn.commit()

        refresh_query = "SELECT * FROM [dbo].[application-upgrade-table] OPTION (LABEL='BeforeUpdate');"
        cursor.execute(refresh_query)

        # Define the columns that should trigger update query 1
        if any(col in non_boolean_columns for col in update_query1_columns):
            update_query = "UPDATE [dbo].[application-upgrade-table] SET "

            for i in range(len(update_query1_columns)):
                column = update_query1_columns[i]
                index = non_boolean_columns.index(column)
                value = non_boolean_values[index]

                if column == "DateofUpgrade":
                    value = datetime.strptime(value, "%Y-%m-%dT%H:%M")

                update_query += "{} = '{}'".format(column, value)

                if i < len(update_query1_columns) - 1:
                    update_query += ", "

            update_query += " WHERE Cust = '{}' AND Env = '{}'".format(customer, env)

            # Prompt the user for confirmation before executing the update statement
            flash('Please confirm the following changes:')
            flash('- Customer: {}, Env: {} will be upgraded to Agiblockversion: {} and Pluginversion: {}'.format(customer, env, form_data['Agiblockversion'], form_data['Pluginversion']))
            flash('- Upgrade date: {}'.format(form_data['DateofUpgrade']))

            # Check if any boolean columns were added or removed
            existing_columns = [col for col in boolean_columns if results[0][col]]
            added_columns = [col for col in boolean_columns if col not in existing_columns and boolean_values[boolean_columns.index(col)]]
            removed_columns = [col for col in existing_columns if col not in boolean_columns or not boolean_values[boolean_columns.index(col)]]
            columns_list = ['Agiblockversion', 'Pluginversion', 'DateofUpgrade'] + boolean_columns
            if added_columns:
                flash('- The following plugins were {}{}'.format('added: ' if added_columns else '', ', '.join(added_columns) if added_columns else '')) 
            if removed_columns:
                flash('- The following plugins were {}{}'.format('removed: ' if removed_columns else '', ', '.join(removed_columns) if removed_columns else ''))
                 
            updated_values = {}
            for column_name in columns_list:
                if column_name == 'DateofUpgrade':
                    updated_values[column_name] = request.form[column_name]
                elif column_name in ['Agiblockversion', 'Pluginversion']:
                    updated_values[column_name] = request.form[column_name]
                else:
                    updated_values[column_name] = True if request.form.get(column_name) else False 
            cursor.execute(update_query)
            conn.commit()
            return render_template('confirm_update.html', updated_values=updated_values)
    
        # Redirect the user back to the search page
        return redirect('/')

if __name__ == '__main__':
    # Debug/Development
     app.run(debug=True, host="0.0.0.0", port="5000")
    # Production    
     http_server = WSGIServer(('', 5000), app)
     http_server.serve_forever()