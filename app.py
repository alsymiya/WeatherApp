from flask import Flask, Response, request, render_template, redirect, url_for
import requests
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import json
import csv
import io
from fpdf import FPDF
from utils.util import format_file_structure, get_file_structure, format_weather_data

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Fetch the API key from the environment variable
API_KEY = os.getenv("API_KEY")
BASE_URL = "http://api.openweathermap.org/data/2.5/weather"


# Construct an absolute path for the database file
db_path = os.path.join(os.path.abspath(os.getcwd()), 'database', 'weather.db')

# Ensure the database directory exists
os.makedirs(os.path.dirname(db_path), exist_ok=True)

# Configure the database
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}' # 'sqlite:///weather.db' # I dislike the default instance folder 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Define the WeatherRequest model
class WeatherRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    location = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.String(10), nullable=False)
    end_date = db.Column(db.String(10), nullable=False)
    temperature_data = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<WeatherRequest {self.location} ({self.start_date} to {self.end_date})>"


# Homepage 
@app.route('/', methods=['GET', 'POST'])
def home():
    weather_data = None
    error = None
    description = ""
    file_structure = format_file_structure(get_file_structure(os.getcwd()))  # Get formatted project file structure

    # Load description from a .txt file
    try:
        with open('disclaimer.txt', 'r') as file:
            description = file.readlines()
    except FileNotFoundError:
        description = "Disclaimer file not found. Please ensure 'disclaimer.txt' exists."

    if request.method == 'POST':
        location = request.form.get('location')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        if location:
            try:
                if start_date and not end_date:
                    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
                    end_date = (start_date_obj + timedelta(days=5)).strftime('%Y-%m-%d')
                elif end_date and not start_date:
                    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
                    start_date = (end_date_obj - timedelta(days=5)).strftime('%Y-%m-%d')
                elif start_date and end_date:
                    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
                    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')

                    if end_date_obj <= start_date_obj:
                        raise ValueError("End date must be greater than start date.")

                # Set default date range if neither is provided
                if not start_date:
                    start_date = datetime.now().strftime('%Y-%m-%d')
                if not end_date:
                    end_date = (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d')

                params = {'q': location, 'appid': API_KEY, 'units': 'metric'}
                response = requests.get(BASE_URL, params=params)
                response.raise_for_status()
                weather_data = response.json()

                # Store the request in the database
                new_request = WeatherRequest(
                    location=location,
                    start_date=start_date,
                    end_date=end_date,
                    temperature_data=json.dumps(weather_data) 
                )
                db.session.add(new_request)
                db.session.commit()

                return redirect(url_for('requests_view'))

            except ValueError as e:
                error = str(e)
            except requests.exceptions.RequestException as e:
                error = f"Error fetching weather data: {e}"
        else:
            error = "Please provide at least a location."

    return render_template(
        'index.html',
        weather_data=weather_data,
        error=error,
        description=description,
        file_structure=file_structure
    )


# Read / View 
@app.route('/requests', methods=['GET'])
def requests_view():
    request_id = request.args.get('id')
    if request_id:
        # Query a specific weather request by ID
        weather_request = WeatherRequest.query.get_or_404(request_id)
        return render_template('requests_view.html', requests=[weather_request], single_view=True)
    else:
        # Show all requests if no specific ID is provided
        requests = WeatherRequest.query.all()
        return render_template('requests_view.html', requests=requests, single_view=False)


# Read and process data in lines. 
@app.context_processor
def utility_functions():
    return dict(format_weather_data=format_weather_data)


# Update / Edit
@app.route('/requests/edit/<int:request_id>', methods=['GET', 'POST'])
def requests_edit(request_id):
    weather_request = WeatherRequest.query.get_or_404(request_id)

    if request.method == 'POST':
        location = request.form.get('location')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        try:
            # Validate input fields
            if not location:
                raise ValueError("Location cannot be empty.")

            if start_date and end_date:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
                if end_date_obj <= start_date_obj:
                    raise ValueError("End date must be greater than start date.")
            
            # Update fields only if new values are provided
            weather_request.location = location or weather_request.location
            weather_request.start_date = start_date or weather_request.start_date
            weather_request.end_date = end_date or weather_request.end_date

            # Commit changes to the database
            db.session.commit()
            return redirect(url_for('requests_view'))

        except ValueError as e:
            return render_template('requests_edit.html', request=weather_request, error=str(e))

    return render_template('requests_edit.html', request=weather_request, error=None)


# Delete 
@app.route('/requests/delete/<int:request_id>', methods=['POST'])
def requests_delete(request_id):
    weather_request = WeatherRequest.query.get_or_404(request_id)
    try:
        db.session.delete(weather_request)
        db.session.commit()
        return redirect(url_for('requests_view'))
    except Exception as e:
        return f"An error occurred while deleting the request: {e}", 500


# Data exports 
@app.route('/export/<format>', methods=['GET'])
def export_data(format):
    # Query all weather requests from the database
    weather_requests = WeatherRequest.query.all()

    if not weather_requests:
        return "No data available to export.", 404

    if format == 'json':
        # Export as JSON
        data = [
            {
                "id": wr.id,
                "location": wr.location,
                "start_date": wr.start_date,
                "end_date": wr.end_date,
                "temperature_data": wr.temperature_data,
            }
            for wr in weather_requests
        ]
        response = Response(json.dumps(data, indent=4), mimetype="application/json")
        response.headers["Content-Disposition"] = "attachment; filename=weather_data.json"
        return response

    elif format == 'csv':
        # Export as CSV using an in-memory buffer
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Location", "Start Date", "End Date", "Temperature Data"])  # Write headers
        for wr in weather_requests:
            writer.writerow([wr.id, wr.location, wr.start_date, wr.end_date, wr.temperature_data])
        response = Response(output.getvalue(), mimetype="text/csv")
        response.headers["Content-Disposition"] = "attachment; filename=weather_data.csv"
        output.close()  # Close the buffer
        return response

    elif format == 'pdf':
        # Export as PDF
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        pdf.cell(200, 10, txt="Weather Requests Data", ln=True, align="C")
        pdf.ln(10)

        for wr in weather_requests:
            formatted_data = format_weather_data(wr.temperature_data)
            pdf.cell(0, 10, txt=f"ID: {wr.id}, Location: {wr.location}", ln=True)
            pdf.cell(0, 10, txt=f"Start Date: {wr.start_date}, End Date: {wr.end_date}", ln=True)
            pdf.ln(5)  # Add spacing between metadata and weather details

            if "Error" in formatted_data:
                pdf.cell(0, 10, txt="Error parsing weather data.", ln=True)
            else:
                # Add formatted weather details to the PDF
                for key, value in formatted_data.items():
                    pdf.cell(0, 10, txt=f"{key}: {value}", ln=True)
            
            pdf.ln(10)  # Add spacing before the next request

        response = Response(pdf.output(dest='S').encode('latin1'))
        response.headers["Content-Disposition"] = "attachment; filename=weather_data.pdf"
        response.mimetype = "application/pdf"
        return response

    else:
        return "Unsupported export format. Please use 'json', 'csv', or 'pdf'.", 400


if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Ensure the database and tables are created
    app.run(debug=True)