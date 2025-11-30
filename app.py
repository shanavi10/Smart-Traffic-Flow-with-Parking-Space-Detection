from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import json
import random
from datetime import datetime
from data_loader import load_vehicle_data, get_random_vehicles
from simulation import SimulationEngine, TrafficPredictor
import threading
import time
import numpy as np
from flask import Flask, render_template, request, jsonify, session
import sqlite3
from detect import Detection
import requests
from pprint import pprint
import secrets
import cv2
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import inch
import sqlite3
import telepot
bot = telepot.Bot("8369998459:AAEgpUwXtqU-zi32cLEeK7O-MalbzqrMDew")
chat_id = "1806485448"

connection = sqlite3.connect('user_data.db')
cursor = connection.cursor()

command = """CREATE TABLE IF NOT EXISTS admin(name TEXT, password TEXT, mobile TEXT, email TEXT)"""
cursor.execute(command)

command = """CREATE TABLE IF NOT EXISTS dashboard(id INTEGER PRIMARY KEY AUTOINCREMENT, Type TEXT, number TEXT, entry TEXT, exit TEXT, time TEXT, price TEXT, payment TEXT, Date TEXT)"""
cursor.execute(command)

app = Flask(__name__)
app.config.from_object('config.Config')

db = SQLAlchemy(app)

# User model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Initialize simulation engine and traffic predictor
simulation_engine = SimulationEngine()
traffic_predictor = TrafficPredictor()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/parking')
def parking():
    connection = sqlite3.connect('user_data.db')
    cursor = connection.cursor()
    cursor.execute("select * from dashboard")
    results=cursor.fetchall()
    return render_template('home.html', results=results)

@app.route('/entry')
def entry():
    connection = sqlite3.connect('user_data.db')
    cursor = connection.cursor()
    Type = Detection()
    import cv2
    vs = cv2.VideoCapture(0)
    while True:
        ret, frame = vs.read()
        cv2.imshow('numberplate', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            cv2.imwrite('frame.png', frame)
            break
    vs.release()
    cv2.destroyAllWindows()

    number = None
    try:
        with open('frame.png', 'rb') as fp:
            response = requests.post(
                'https://api.platerecognizer.com/v1/plate-reader/',
                files=dict(upload=fp),
                headers={'Authorization': 'Token 81dda232b51e3f7c7620f0830834a6d8c94e0120'})
        results = response.json()
        number = results['results'][0]['plate']
    except:
        print('no numberplate')

    if number:
        number = number.upper()
        connection = sqlite3.connect('user_data.db')
        cursor = connection.cursor()

        from datetime import datetime
        now = datetime.now()
        etime = now.strftime("%H:%M:%S")
        Date = now.strftime("%Y-%m-%d")
        cursor.execute('insert into dashboard (Type, number, entry, Date) values(?,?,?,?)',[Type, number, etime, Date])
        connection.commit()

        cursor.execute("select * from dashboard")
        results=cursor.fetchall()
        return render_template('home.html', results=results)
    else:
        cursor.execute("select * from dashboard")
        results=cursor.fetchall()
        return render_template('home.html', results=results)

@app.route('/exit')
def exit():
    connection = sqlite3.connect('user_data.db')
    cursor = connection.cursor()
    import cv2
    vs = cv2.VideoCapture(0)
    while True:
        ret, frame = vs.read()
        cv2.imshow('numberplate', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            cv2.imwrite('frame.png', frame)
            break
    vs.release()
    cv2.destroyAllWindows()
    
    number = None
    try:
        with open('frame.png', 'rb') as fp:
            response = requests.post(
                'https://api.platerecognizer.com/v1/plate-reader/',
                files=dict(upload=fp),
                headers={'Authorization': 'Token 81dda232b51e3f7c7620f0830834a6d8c94e0120'})
        results = response.json()
        number = results['results'][0]['plate']
    except:
        print('no numberplate')

    if number:
        number = number.upper()
        from datetime import datetime
        now = datetime.now()
        etime = now.strftime("%H:%M:%S")

        from datetime import datetime, timedelta
        cursor.execute("select * from dashboard where number = '"+number+"'")
        result=cursor.fetchone()
        if result:
            time1 = datetime.strptime(result[3], "%H:%M:%S")
            time2 = datetime.strptime(etime, "%H:%M:%S")

            time_difference = time2 - time1

            minutes_difference = time_difference.total_seconds() / 60

            minutes_difference = '{:f}'.format(minutes_difference)

            print("Time difference in minutes:", minutes_difference)

            if result[1] == 'car':
                amount = float(minutes_difference) * 20
            else:
                amount = float(minutes_difference) * 10
            amount = str(int(amount))
            message = f"Vehicle with number plate {number} entered at {time1} and exited at {time2}. Total parking duration is {time_difference}, and the amount to be paid is ₹{amount}."
            bot.sendMessage(chat_id, message)

            cursor.execute("update dashboard set exit=?, time = ?, price = ? where number = ?", [etime, minutes_difference, amount, number])
            connection.commit()

            cursor.execute("update dashboard set payment = 'paid' where number = '"+number+"'")
            connection.commit()

            cursor.execute("select * from dashboard")
            results=cursor.fetchall()
            return render_template('home.html', results=results)
        else:
            cursor.execute("select * from dashboard")
            results=cursor.fetchall()
            return render_template('home.html', results=results, msg = "Wrong numberplate recognised")
    
@app.route('/Delete', methods=['GET', 'POST'])
def Delete():
    connection = sqlite3.connect('user_data.db')
    cursor = connection.cursor()
    if request.method == 'POST':

        From = request.form['from']
        To = request.form['to']

        cursor.execute("delete from dashboard where Date >= '"+From+"' and Date <= '"+To+"'")
        connection.commit()

        cursor.execute("select * from dashboard")
        results=cursor.fetchall()
        return render_template('home.html', results=results)
    cursor.execute("select * from dashboard")
    results=cursor.fetchall()
    return render_template('home.html', results=results)

@app.route('/download', methods=['GET', 'POST'])
def download():
    connection = sqlite3.connect('user_data.db')
    cursor = connection.cursor()
    if request.method == 'POST':

        From = request.form['from']
        To = request.form['to']

        query = "SELECT id, Type, number, entry, exit, time, Date FROM dashboard where Date >= '"+From+"' and Date <= '"+To+"'"
        cursor.execute(query)
        results = cursor.fetchall()
        print(results)

        from datetime import datetime
        now = datetime.now()
        Date = now.strftime("%Y-%m-%d")

        # Create PDF document
        doc = SimpleDocTemplate(f'static/{Date}.pdf', pagesize=letter)
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        
        # Add title
        title = Paragraph(f"Dashboard Report ({From} to {To})", 
                        styles['Title'])
        elements.append(title)
        elements.append(Spacer(1, 0.25 * inch))
        
        # Prepare data for table
        data = [['ID', 'Type', 'Number', 'Entry', 'Exit', 'Time', 'Date']]  # Headers
        for row in results:
            data.append([str(item) for item in row])
        
        # Create table
        table = Table(data)
        
        # Add style to table
        style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ])
        table.setStyle(style)
        
        # Add table to elements
        elements.append(table)
        
        # Build PDF
        doc.build(elements)
        print(f"PDF report generated: static/{Date}.pdf")

        query = "SELECT * FROM dashboard"
        cursor.execute(query)
        results = cursor.fetchall()
        print(results)
        return render_template('home.html', results=results, path = f'http://127.0.0.1:5000/static/{Date}.pdf')
    cursor.execute("select * from dashboard")
    results=cursor.fetchall()
    return render_template('home.html', results=results)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Validation
        if not username or not email or not password:
            flash('Please fill all fields', 'error')
            return render_template('register.html')
            
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists', 'error')
            return render_template('register.html')
        
        # Create new user
        new_user = User(username=username, email=email)
        new_user.set_password(password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            flash('An error occurred during registration', 'error')
    
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in to access this page', 'error')
        return redirect(url_for('login'))
    
    return render_template('dashboard.html', username=session['username'])

@app.route('/simulation')
def simulation():
    if 'user_id' not in session:
        flash('Please log in to access this page', 'error')
        return redirect(url_for('login'))
    
    return render_template('simulation.html')

@app.route('/get_vehicle_data')
def get_vehicle_data():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authorized'}), 401
        
    vehicle_count = session.get('vehicle_count', 5) * 4  # 4 roads
    vehicles = get_random_vehicles(vehicle_count)
    
    # Update simulation engine configuration
    simulation_engine.update_config(
        session.get('vehicle_count', 5),
        session.get('ai_prediction', True),
        session.get('emergency_priority', True)
    )
    
    simulation_engine.set_vehicles(vehicles)
    return jsonify(vehicles)

@app.route('/start_simulation')
def start_simulation():
    simulation_engine.start()
    return jsonify({'status': 'started'})

@app.route('/stop_simulation')
def stop_simulation():
    simulation_engine.stop()
    return jsonify({'status': 'stopped'})

@app.route('/get_simulation_state')
def get_simulation_state():
    try:
        return jsonify(simulation_engine.get_state())
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get_simulation_stats')
def get_simulation_stats():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authorized'}), 401
        
    # Calculate statistics from simulation
    vehicles = simulation_engine.vehicles
    if vehicles:
        avg_speed = sum(v['speed'] for v in vehicles) / len(vehicles)
        avg_latency = sum(v.get('latency', 0) for v in vehicles) / len(vehicles)
        avg_signal = sum(v.get('signal_strength', 0) for v in vehicles) / len(vehicles)
    else:
        avg_speed, avg_latency, avg_signal = 0, 0, 0
        
    return jsonify({
        'active_vehicles': len(vehicles),
        'avg_speed': round(avg_speed, 1),
        'avg_latency': round(avg_latency, 1),
        'avg_signal': round(avg_signal, 1)
    })

@app.route('/update_config', methods=['POST'])
def update_config():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authorized'}), 401
        
    data = request.get_json()
    session['vehicle_count'] = int(data.get('vehicle_count', 5))
    session['ai_prediction'] = bool(data.get('ai_prediction', True))
    session['emergency_priority'] = bool(data.get('emergency_priority', True))
    
    return jsonify({'status': 'success'})

# Add vehicles to specific roads
@app.route('/add_vehicles_north')
def add_vehicles_north():
    simulation_engine.add_vehicles_to_road('north', 3)
    return jsonify({'status': 'vehicles added to north'})

@app.route('/add_vehicles_south')
def add_vehicles_south():
    simulation_engine.add_vehicles_to_road('south', 3)
    return jsonify({'status': 'vehicles added to south'})

@app.route('/add_vehicles_east')
def add_vehicles_east():
    simulation_engine.add_vehicles_to_road('east', 3)
    return jsonify({'status': 'vehicles added to east'})

@app.route('/add_vehicles_west')
def add_vehicles_west():
    simulation_engine.add_vehicles_to_road('west', 3)
    return jsonify({'status': 'vehicles added to west'})

# Add ambulance to specific roads with priority
@app.route('/add_ambulance_north')
def add_ambulance_north():
    simulation_engine.add_ambulance_with_priority('north')
    return jsonify({'status': 'ambulance added to north with priority'})

@app.route('/add_ambulance_south')
def add_ambulance_south():
    simulation_engine.add_ambulance_with_priority('south')
    return jsonify({'status': 'ambulance added to south with priority'})

@app.route('/add_ambulance_east')
def add_ambulance_east():
    simulation_engine.add_ambulance_with_priority('east')
    return jsonify({'status': 'ambulance added to east with priority'})

@app.route('/add_ambulance_west')
def add_ambulance_west():
    simulation_engine.add_ambulance_with_priority('west')
    return jsonify({'status': 'ambulance added to west with priority'})

@app.route('/clear_all_vehicles')
def clear_all_vehicles():
    simulation_engine.clear_all_vehicles()
    return jsonify({'status': 'all vehicles cleared'})

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)