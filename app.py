from flask import Flask, request, render_template, url_for, session, redirect, jsonify
import pickle
from flask_mail import Mail, Message
import requests
from flask_mysqldb import MySQL
from flask import flash
import plotly.offline as pyo

import dash
from dash import dcc, html
from datetime import datetime
from wordcloud import WordCloud

from dash.dependencies import Input, Output
import MySQLdb.cursors
import re
import matplotlib.pyplot as plt
import io
import seaborn as sns
import base64
import plotly.express as px
from werkzeug.security import generate_password_hash, check_password_hash
from chat import get_response  # Assuming you have a chat module
import pandas as pd

movies = pickle.load(open('movie_list.pkl', 'rb'))
similarity = pickle.load(open('similarity.pkl', 'rb'))

def fetch_poster(movie_id):
    url = "https://api.themoviedb.org/3/movie/{}?api_key=8265bd1679663a7ea12ac168da84d2e8&language=en-US".format(movie_id)
    data = requests.get(url)
    data = data.json()
    poster_path = data['poster_path']
    full_path = "https://image.tmdb.org/t/p/w500/" + poster_path
    return full_path

def recommend(movie):
    title_index = movies[movies['title'] == movie].index
    if not title_index.empty:
        index = title_index[0]
    else:
        search_term = movie.lower().replace(' ', '')
        index = movies[movies['tags'].apply(lambda x: search_term in x.replace(' ', ''))].index[0]

    distances = sorted(list(enumerate(similarity[index])), reverse=True, key=lambda x: x[1])
    recommended_movies_name = []
    recommended_movies_poster = []
    for i in distances[1:6]:
        movie_id = movies.iloc[i[0]].movie_id
        recommended_movies_poster.append(fetch_poster(movie_id))
        recommended_movies_name.append(movies.iloc[i[0]].title)

    return recommended_movies_name, recommended_movies_poster

app = Flask(__name__)
app.secret_key = 'xyzsdfg'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'movie_recommendation'
mysql = MySQL(app)



# Flask-Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Change this to your email server
app.config['MAIL_PORT'] = 587  # Change this to the appropriate port for your email server
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'tmtm.bhais2@gmail.com'  # Change this to your email address
app.config['MAIL_PASSWORD'] = '0173840586oOo'  # Change this to your email password

mail = Mail(app)

@app.route('/')
@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ''
    if request.method == 'POST' and 'Email' in request.form and 'Password' in request.form:
        Email = request.form['Email']
        Password = request.form['Password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM movie_recommendation WHERE Email = %s', (Email,))
        user = cursor.fetchone()

        if user and check_password_hash(user['Password'], Password):
            session['loggedin'] = True
            session['Name'] = user['Name']
            session['Email'] = user['Email']
            session['Password'] = user['Password']  # It's still hashed, not the actual password
            session['Age'] = user['Age']
            session['Gender'] = user['Gender']
            session['State'] = user['State']

            message = 'Logged in successfully!'
            return render_template('index.html', message=message)
        else:
            message = 'Please enter correct email/password!'
    return render_template('login.html', message=message)


@app.route('/logout', methods=['POST'])
def logout():
    session.pop('loggedin', None)
    session.pop('Name', None)
    session.pop('Email', None)
    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    message = ''
    if request.method == 'POST':
        Name = request.form['name']
        Email = request.form['email']
        Password = request.form['password']
        confirm_password = request.form['confirm_password']
        Dob = request.form['dob']
        Gender = request.form['gender']
        State = request.form['state']
        type_user = 'user';

        # Optional preferences
        LikeGenre = request.form.get('like_genre', '')  # Optional, default to empty string if not provided
        LikeActor = request.form.get('like_actor', '')  # Optional, default to empty string if not provided
        LikeDirector = request.form.get('like_director', '')  # Optional, default to empty string if not provided
        dob_datetime = datetime.strptime(Dob, '%Y-%m-%d')
        today = datetime.today()
        Age = today.year - dob_datetime.year - ((today.month, today.day) < (dob_datetime.month, dob_datetime.day))


        if not Name or not Email or not Password or not confirm_password or not Age or not Gender or not State:
            message = 'Please fill out all required fields.'
        elif Password != confirm_password:
            message = 'Passwords do not match.'
        else:
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

            # Check if the email is already in use
            cursor.execute('SELECT * FROM movie_recommendation WHERE Email = %s', (Email,))
            account = cursor.fetchone()

            if account:
                message = 'Email is already in use. Please choose a different one.'
            elif not re.match(r'[^@]+@[^@]+\.[^@]+', Email):
                message = 'Invalid email address!'
            else:
                # Use the default hashing method
                hashed_password = generate_password_hash(Password)
                cursor.execute(
                    'INSERT INTO movie_recommendation (Name, Email, Password, Age, Gender, State, LikeGenre, LikeActor, LikeDirector,type_user) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s,%s)',
                    (Name, Email, hashed_password, Age, Gender, State, LikeGenre, LikeActor, LikeDirector, type_user))
                mysql.connection.commit()
                message = 'Registration successful!'
    return render_template('register.html', message=message)










@app.route('/index')
def index():
    print(session)
    if 'loggedin' not in session:
        print("Redirecting to login")
        return redirect(url_for('login'))

    return render_template('index.html', )




@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message_content = request.form['message']

        # Send email
        send_email(name, email, message_content)

        # You may want to add a success message or redirect to a thank-you page
        return render_template('contact.html', success_message="Your message has been sent. Thank you!")

    return render_template('contact.html')

def send_email(name, email, message_content):
    try:
        subject = 'New Contact Form Submission'
        body = f"Name: {name}\nEmail: {email}\n\nMessage:\n{message_content}"

        # Create a Message instance
        message = Message(subject=subject,
                          body=body,
                          sender='tmtm.bhais1@gmail.com',  # Change this to your email address
                          recipients=['tmtm.bhais2@gmail.com'])  # Change this to your desired recipient email address

        # Send the email
        mail.send(message)

        # You may want to log the success or handle any exceptions
        print("Email sent successfully!")

    except Exception as e:
        print(f"Error sending email: {e}")




def recommend_function(search_term, search_type='title'):
    try:
        if search_type == 'title':
            # Search based on title
            index = movies[movies['title'] == search_term].index[0]
        else:
            search_term = search_term.lower().replace(' ', '')
            # Search based on 'tags' (combination of overview, genres, keywords, cast, and crew)
            index = \
                movies[movies['tags'].apply(lambda x: search_term in x.replace(' ', ''))].index[
                    0]

        distances = sorted(list(enumerate(similarity[index])), reverse=True, key=lambda x: x[1])
        recommended_movies = []
        recommended_movie_posters = []
        for i in distances[1:21]:
            movie_id = movies.iloc[i[0]].movie_id
            recommended_movie_posters.append(fetch_poster(movie_id))
            recommended_movies.append({'id': movie_id, 'title': movies.iloc[i[0]].title})

        return recommended_movies, recommended_movie_posters
    except IndexError:
        print("Movie or search term not found.")
        return []

# Update the /recommendation route to use the modified function
@app.route('/recommendation', methods=['GET', 'POST'])
def recommend():
    movie_list = movies['title'].values
    status = False
    search_type = 'title'
    search_input = None
    recommended_movies = []  # Initialize as empty list
    recommended_movies_poster = []  # Initialize as empty list

    error = None

    if request.method == 'POST':
        try:
            if 'search_type' in request.form:
                search_type = request.form['search_type']
                if search_type == 'title':
                    search_input = request.form['movies']
                elif search_type == 'tags':
                    search_input = request.form['tags']

            if search_input:
                recommended_movies, recommended_movies_poster = recommend_function(search_input, search_type)
                status = True
        except ValueError as ve:
            error = {'error': 'Movie not found.'}
        except Exception as e:
            error = {'error': str(e)}
        # Add recommended_movies to the context
        return render_template('prediction.html', error=error, movie_list=movie_list, status=status, search_type=search_type, recommended_movies=recommended_movies,recommended_movies_poster=recommended_movies_poster)
    else:
        return render_template('prediction.html', movie_list=movie_list, status=status, search_type=search_type, recommended_movies=recommended_movies,recommended_movies_poster=recommended_movies_poster)

def fetch_movie_details_local(movie_id):
    # Path to the Excel file
    file_path = "movies_details.xlsx"

    try:
        # Read the Excel file into a pandas DataFrame
        movies_details = pd.read_excel(file_path)

        # Check if the movie_id exists in the DataFrame
        if not movies_details[movies_details['movie_id'] == movie_id].empty:
            movie_details = movies_details[movies_details['movie_id'] == movie_id]

            # Convert the details to a dictionary
            movie_details_dict = movie_details.to_dict(orient='records')[0]

            return movie_details_dict
        else:
            print(f"Movie with ID {movie_id} not found.")
            return {}
    except Exception as e:
        print(f"Error loading movie details: {e}")
        return {}

@app.route('/movie_details/<int:movie_id>', methods=['GET', 'POST'])
def movie_details(movie_id):
    # Fetch movie details
    movie_details_dict = fetch_movie_details_local(movie_id)
    movie_poster = fetch_poster(movie_id)

    # Handle feedback form submission
    if request.method == 'POST':
        # Fetch feedback details from the form
        rating = request.form['rating']
        feedback = request.form['feedback']

        # Insert feedback into the database
        cursor = mysql.connection.cursor()
        cursor.execute(
            'INSERT INTO movie_feedback (Name, Email, Movie_name, Rating, text_feedback) VALUES (%s, %s, %s, %s, %s)',
            (session['Name'], session['Email'], movie_details_dict['title'], rating, feedback)
        )
        mysql.connection.commit()

        # Show a success message
        flash('Your feedback has been submitted successfully!', 'success')

    return render_template('movie_details.html', movie_details=movie_details_dict, movie_poster=movie_poster)



def fetch_demographics_data():
    # Fetch user demographics data from the database
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM movie_recommendation')
    demographics_data = cursor.fetchall()

    # Convert data to a DataFrame

    return demographics_data

def analyze_demographics():
    # Fetch user demographics data from the database
    demographics_data = fetch_demographics_data()
    df_demographics = pd.DataFrame(demographics_data, columns=['Age', 'Gender', 'State', 'LikeGenre', 'LikeActor', 'LikeDirector', 'text_feedback'])

    # Age Distribution Analysis
    age_distribution = df_demographics['Age'].value_counts()

    # Gender Distribution Analysis
    gender_distribution = df_demographics['Gender'].value_counts()

    # State-wise Analysis
    state_distribution = df_demographics['State'].value_counts()

    # Genre, Actor, and Director Preferences Analysis
    genre_distribution = df_demographics['LikeGenre'].value_counts()
    actor_distribution = df_demographics['LikeActor'].value_counts()
    director_distribution = df_demographics['LikeDirector'].value_counts()

    # Feedback Analysis
    feedback_distribution = df_demographics['text_feedback'].value_counts()

    return {
        'age_distribution': age_distribution,
        'gender_distribution': gender_distribution,
        'state_distribution': state_distribution,
        'genre_distribution': genre_distribution,
        'actor_distribution': actor_distribution,
        'director_distribution': director_distribution,
        'feedback_distribution': feedback_distribution
    }





def is_admin(email):
    try:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT type_user FROM movie_recommendation WHERE Email = %s', (email,))
        user = cursor.fetchone()
        return user and user['type_user'] == 'admin'
    except Exception as e:
        print(f"Error accessing the database: {e}")
        return False
    finally:
        # Close the cursor
        cursor.close()

# ... (previous code)

# Dashboard route
@app.route('/dashboard')
def dashboard():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    # Check if the logged-in user is an admin
    if is_admin(session.get('Email', '')):
        # Fetch demographics data
        demographics_data = fetch_demographics_data()

        # Analyze demographics data
        demographics_analysis = analyze_demographics()

        # Create plots using Plotly Express (px)
        age_plot = px.bar(x=demographics_analysis['age_distribution'].index, y=demographics_analysis['age_distribution'].values, title='Age Distribution')
        gender_plot = px.pie(values=demographics_analysis['gender_distribution'].values, names=demographics_analysis['gender_distribution'].index, title='Gender Distribution')
        state_plot = px.bar(x=demographics_analysis['state_distribution'].index, y=demographics_analysis['state_distribution'].values, title='State Distribution')
        feedback_plot = px.bar(x=demographics_analysis['feedback_distribution'].index, y=demographics_analysis['feedback_distribution'].values, title='Feedback Distribution')
        genre_plot = px.bar(x=demographics_analysis['genre_distribution'].index, y=demographics_analysis['genre_distribution'].values, title='Genre Distribution')
        actor_plot = px.bar(x=demographics_analysis['actor_distribution'].index, y=demographics_analysis['actor_distribution'].values, title='Actor Distribution')
        director_plot = px.bar(x=demographics_analysis['director_distribution'].index, y=demographics_analysis['director_distribution'].values, title='Director Distribution')

        # Additional analyses and plots
        num_feedback_plot = px.histogram(demographics_data, x='num_feedback', title='Number of Feedback Distribution')
        age_gender_plot = px.box(demographics_data, x='Gender', y='Age', points='all', title='Age Distribution by Gender')
        state_feedback_plot = px.scatter(demographics_data, x='State', y='num_feedback', color='Gender', size='num_feedback', title='Feedback Count by State')

        # Get a random text feedback
        random_feedback = demographics_analysis['feedback_distribution'].sample().index[0]
        df_demographics = pd.DataFrame(demographics_data,
                                       columns=['Age', 'Gender', 'State', 'LikeGenre', 'LikeActor', 'LikeDirector',
                                                'text_feedback'])

        # Generate Feedback Word Cloud

        # Analyze Correlations and display the heatmap

        return render_template('dashboard.html',
                               age_plot=age_plot,
                               gender_plot=gender_plot,
                               state_plot=state_plot,
                               feedback_plot=feedback_plot,
                               num_feedback_plot=num_feedback_plot,
                               age_gender_plot=age_gender_plot,
                               state_feedback_plot=state_feedback_plot,
                               random_feedback=random_feedback,
                               genre_plot=genre_plot,
                               actor_plot=actor_plot,
                               director_plot=director_plot,)
    else:
        return render_template('dashboard_unauthorized.html')  # Create a template for unauthorized access

# ... (other Flask routes and app configurations)


@app.route('/profile')
def profile():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    # Fetch user details from the database based on the session email
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM movie_recommendation WHERE Email = %s', (session['Email'],))
    user = cursor.fetchone()

    return render_template('profile.html', user=user)

@app.route('/edit_profile', methods=['POST'])
def edit_profile():
    if 'loggedin' not in session:
        return jsonify({'status': 'error', 'message': 'User not logged in'})

    if request.method == 'POST':
        # Fetch the updated user details from the form
        updated_name = request.form['name']
        updated_age = request.form['age']
        updated_gender = request.form['gender']
        updated_state = request.form['state']

        # Update user details in the database
        cursor = mysql.connection.cursor()
        cursor.execute(
            'UPDATE movie_recommendation SET Name=%s, Age=%s, Gender=%s, State=%s WHERE Email=%s',
            (updated_name, updated_age, updated_gender, updated_state, session['Email'])
        )
        mysql.connection.commit()

        # Update the session with the new details
        session['Name'] = updated_name
        session['Age'] = updated_age
        session['Gender'] = updated_gender
        session['State'] = updated_state

        return jsonify({'status': 'success', 'message': 'Profile updated successfully'})

    return jsonify({'status': 'error', 'message': 'Invalid request'})

@app.route('/change_password', methods=['POST'])
def change_password():
    if 'loggedin' not in session:
        return jsonify({'status': 'error', 'message': 'User not logged in'})

    if request.method == 'POST':
        # Fetch the current and new passwords from the form
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        # Fetch user details from the database based on the session email
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM movie_recommendation WHERE Email = %s', (session['Email'],))
        user = cursor.fetchone()

        # Check if the current password matches the stored hashed password
        if user and check_password_hash(user['Password'], current_password):
            # Check if the new password and confirm password match
            if new_password == confirm_password:
                # Update the password in the database
                hashed_password = generate_password_hash(new_password)
                cursor.execute(
                    'UPDATE movie_recommendation SET Password=%s WHERE Email=%s',
                    (hashed_password, session['Email'])
                )
                mysql.connection.commit()

                return jsonify({'status': 'success', 'message': 'Password changed successfully'})
            else:
                return jsonify({'status': 'error', 'message': 'New password and confirm password do not match'})
        else:
            return jsonify({'status': 'error', 'message': 'Current password is incorrect'})

    return jsonify({'status': 'error', 'message': 'Invalid request'})

@app.route('/feedback', methods=['POST'])
def feedback():
    if 'loggedin' not in session:
        return jsonify({'status': 'error', 'message': 'User not logged in'})

    if request.method == 'POST':
        # Fetch feedback details from the form
        rating = request.form.get('rating')
        text_feedback = request.form.get('text_feedback')

        # Update feedback in the database
        cursor = mysql.connection.cursor()
        cursor.execute(
            'UPDATE movie_recommendation SET num_feedback=%s, text_feedback=%s WHERE Email=%s',
            (rating, text_feedback, session['Email'])
        )
        mysql.connection.commit()

        return jsonify({'status': 'success', 'message': 'Feedback submitted successfully'})

    return jsonify({'status': 'error', 'message': 'Invalid request'})


@app.route('/predict', methods=['POST'])
def predict():
    text = request.get_json().get('message')
    response = get_response(text)
    message = {'answer': response}
    return jsonify(message)




