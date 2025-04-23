from flask import Flask, render_template, request, redirect, session, flash
from flask_pymongo import PyMongo
from werkzeug.utils import secure_filename
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MongoDB Config
app.config['MONGO_URI'] = 'mongodb://localhost:27017/fooddonation'
mongo = PyMongo(app)
users = mongo.db.users
foods = mongo.db.foods
messages = mongo.db.messages

# Upload folder setup
UPLOAD_FOLDER = 'static/uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user_type = request.form['user_type']
        mobile = request.form['mobile']
        users.insert_one({'username': username, 'password': password, 'user_type': user_type, 'mobile': mobile})
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = users.find_one({'username': username, 'password': password})
        if user:
            session['username'] = username
            session['user_type'] = user.get('user_type')
            session['mobile'] = user.get('mobile')
            return redirect('/dashboard')
        else:
            return 'Invalid credentials'
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect('/login')

    user_type = session.get('user_type')
    if user_type == 'donor':
        food_items = list(foods.find({'donor': session['username']}))
    else:
        food_items = list(foods.find())
        for item in food_items:
            donor_user = users.find_one({'username': item['donor']})
            item['donor_mobile'] = donor_user.get('mobile') if donor_user else "Not Available"

    return render_template('dashboard.html', food_items=food_items)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if 'username' not in session:
        return redirect('/login')

    if request.method == 'POST':
        food_name = request.form.get('food_name')
        quantity = request.form.get('quantity')
        location = request.form.get('location')
        photo = request.files.get('photo')

        # Validate form data
        if not food_name or not quantity or not location:
            flash('All fields are required!', 'error')
            return redirect('/upload')

        if photo:
            filename = secure_filename(photo.filename)
            photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)

            try:
                photo.save(photo_path)
                foods.insert_one({
                    'food_name': food_name,
                    'quantity': quantity,
                    'location': location,
                    'photo': filename,
                    'donor': session['username']
                })
                flash("Food uploaded successfully!", "success")
            except Exception as e:
                flash(f"Failed to upload food: {str(e)}", "error")
        else:
            flash("No photo provided!", "error")

        return redirect('/dashboard')

    return render_template('upload.html')

@app.route('/send_message/<recipient_mobile>', methods=['POST'])
def send_message(recipient_mobile):
    if 'username' not in session:
        return redirect('/login')

    msg = request.form['message']
    messages.insert_one({
        'sender': session['mobile'],
        'recipient': recipient_mobile,
        'message': msg,
        'timestamp': datetime.utcnow()
    })
    flash("Your message has been sent!", "success")
    return redirect('/inbox')

@app.route('/inbox')
def inbox():
    if 'username' not in session:
        return redirect('/login')

    received_msgs = list(messages.find({'recipient': session['mobile']}))
    sent_msgs = list(messages.find({'sender': session['mobile']}))

    return render_template('inbox.html', received=received_msgs, sent=sent_msgs)

@app.route('/reply/<recipient_mobile>', methods=['POST'])
def reply(recipient_mobile):
    if 'username' not in session:
        return redirect('/login')

    # Get the reply message from the form
    reply_message = request.form['reply_message']

    # Insert the reply into the database
    messages.insert_one({
        'sender': session['mobile'],  # Donor's mobile (sender)
        'recipient': recipient_mobile,  # Recipient's mobile
        'message': reply_message,  # Reply message content
        'timestamp': datetime.utcnow()  # Timestamp for the reply
    })

    flash('Your reply has been sent!', 'success')
    return redirect('/inbox')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
