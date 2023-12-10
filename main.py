import streamlit as st
import streamlit_authenticator as stauth
import requests
import pickle
from deta import Deta
import pandas as pd
import os
import plotly.express as px
from PIL import Image
import base64
from io import BytesIO
from dependacies import sign_up, fetch_users
from streamlit_option_menu import option_menu

st.set_page_config(
    page_title='Movie Recommender System',
    page_icon='🎬',
    initial_sidebar_state='collapsed'
)

try:
    users = fetch_users()
    emails = []
    usernames = []
    passwords = []
    genders = []
    states = []

    for user in users:
        emails.append(user['key'])
        usernames.append(user['username'])
        passwords.append(user['password'])
        genders.append(user['Gender'])
        states.append(user['City'])

    credentials = {'usernames': {}}
    for index in range(len(emails)):
        credentials['usernames'][usernames[index]] = {'name': emails[index], 'password': passwords[index],
                                                      'Gender': genders[index], 'City': states[index]}

    Authenticator = stauth.Authenticate(credentials, cookie_name='Streamlit', key='abcdef', cookie_expiry_days=4)

    email, authentication_status, username = Authenticator.login(':green[Login]', 'main')

    info, info1 = st.columns(2)

    if not authentication_status:
        sign_up()

    if username:
        if username in usernames:
            if authentication_status:
                # let User see app
                Authenticator.logout('Sign Out', 'sidebar')

                selected = option_menu(
                    menu_title=None,
                    options=["Home", "Dashboard", "History", "My profile", "About us"],
                    icons=["house", "pie-chart", "clock-history", "person-circle", "book"],
                    menu_icon="cast",
                    default_index=0,
                    orientation="horizontal"
                )
                if selected == "Home":
                    def fetch_poster(movie_id):
                        url = "https://api.themoviedb.org/3/movie/{}?api_key=8265bd1679663a7ea12ac168da84d2e8&language=en-US".format(
                            movie_id)
                        data = requests.get(url)
                        data = data.json()
                        poster_path = data['poster_path']
                        full_path = "https://image.tmdb.org/t/p/w500/" + poster_path
                        return full_path


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
                                st.warning(f"Movie with ID {movie_id} not found.")
                                return {}
                        except Exception as e:
                            st.error(f"Error loading movie details: {e}")
                            return {}




                    def recommend(search_term, search_type='title'):
                        try:
                            if search_type == 'title':
                                # Search based on title
                                index = movies[movies['title'] == search_term].index[0]
                            else:
                                search_term = search_term.lower().replace(' ', '')
                                # Search based on 'tags' (combination of overview, genres, keywords, cast, and crew)
                                index = movies[movies['tags'].apply(lambda x: search_term in x.replace(' ', ''))].index[
                                    0]

                            distances = sorted(list(enumerate(similarity[index])), reverse=True, key=lambda x: x[1])
                            recommended_movie_names = []
                            recommended_movie_posters = []
                            for i in distances[1:21]:
                                # fetch the movie poster
                                movie_id = movies.iloc[i[0]].movie_id
                                recommended_movie_posters.append(fetch_poster(movie_id))
                                recommended_movie_names.append(movies.iloc[i[0]].title)

                            return recommended_movie_names, recommended_movie_posters

                        except IndexError:
                            print("Movie or search term not found.")


                    # Streamlit code
                    movies = pickle.load(open('movie_list.pkl', 'rb'))
                    similarity = pickle.load(open('similarity.pkl', 'rb'))

                    movie_list = movies['title'].values

                    search_type = st.selectbox(
                        "Choose your search type",
                        ['title', 'tags']
                    )

                    if search_type == 'title':
                        selected_movie = st.selectbox(
                            "Select a movie from the dropdown",
                            movie_list
                        )
                    else:
                        selected_movie = st.text_input("Type a tag")

                    if search_type and selected_movie:
                        recommended_movie_names, recommended_movie_posters = recommend(selected_movie, search_type)

                        # Display the top 20 recommended movies
                        st.subheader("Top 20 Recommended Movies:")

                        num_recommendations = min(20, len(recommended_movie_names))

                        for i in range(0, num_recommendations, 3):
                            cols = st.columns(3)
                            for j in range(3):
                                if i + j < num_recommendations:
                                    with cols[j]:
                                        if st.button(recommended_movie_names[i + j]):
                                            # Fetch movie details from local dataset
                                            selected_movie_details = fetch_movie_details_local(
                                                movies[movies['title'] == recommended_movie_names[i + j]].iloc[
                                                    0].movie_id
                                            )
                                            # Create a new page for movie details
                                            st.markdown("<h1 style='text-align: center;'>Movie Details</h1>",
                                                        unsafe_allow_html=True)
                                            st.button("Back to Recommendations", key="back_button",
                                                      on_click=lambda: st.experimental_rerun())

                                            # Display movie details using the function
                                            def display_movie_details(selected_movie_details):
                                                st.title(selected_movie_details['title'])
                                                st.image(fetch_poster(selected_movie_details['movie_id']))

                                                # Display other details in a nice format
                                                st.subheader("Overview")
                                                st.write(selected_movie_details['overview'])

                                                st.subheader("Homepage")
                                                homepage_value = selected_movie_details['homepage']

                                                # Check if 'homepage' is iterable (list, tuple, etc.)
                                                if isinstance(homepage_value, (list, tuple)):
                                                    homepage_value = ", ".join(homepage_value)

                                                # Display as a clickable link
                                                st.markdown(f"[{homepage_value}]({homepage_value})")

                                                st.subheader("Genres")
                                                st.write(selected_movie_details['genres'])

                                                st.subheader("Rating of the movie")
                                                st.write(selected_movie_details['vote_average'])

                                                st.subheader("Directors of the movie")
                                                st.write(selected_movie_details['directors'])

                                                st.subheader("Visual effects producers")
                                                st.write(selected_movie_details['visual_effects_producers'])

                                                st.subheader("Production Design")
                                                st.write(selected_movie_details['Production Design'])

                                                st.subheader("Dialogue Editor")
                                                st.write(selected_movie_details['Dialogue Editor'])
                                            display_movie_details(selected_movie_details)
                                        else:
                                            st.image(recommended_movie_posters[i + j])



                if selected == "Dashboard":

                    # Fetch user data
                    users = fetch_users()

                    # Create a DataFrame from the user data
                    df = pd.DataFrame(users)

                    # Sidebar
                    st.sidebar.title('User Analysis Dashboard')
                    selected_chart = st.sidebar.selectbox('Select Chart Type', ['Bar Chart', 'Pie Chart'])

                    # Main content
                    st.title('User Analysis Dashboard')

                    if selected_chart == 'Bar Chart':
                        st.subheader('User Distribution by Gender and City')
                        fig = px.bar(df, x='Gender', color='City', title='User Distribution by Gender and City')
                        st.plotly_chart(fig)

                    elif selected_chart == 'Pie Chart':
                        st.subheader('Distribution of Gender Among Users')
                        fig = px.pie(df, names='Gender', title='Distribution of Gender Among Users')
                        st.plotly_chart(fig)

                    # Additional analysis can be added based on your data and requirements

                    # Display raw data
                    st.subheader('Raw User Data')
                    st.write(df)

                if selected == "History":
                    # New code for My Profile page
                    st.subheader(f"Welcome, {username}!")

                if selected == "My profile":
                    # New code for My Profile page
                    st.subheader(f"Welcome, {username}!")

                    # Display user information
                    st.write(f"Username: {username}")
                    st.write(f"Email: {email}")
                    st.write(f"Gender: {genders[usernames.index(username)]}")
                    st.write(f"City: {states[usernames.index(username)]}")

                    # Allow users to upload a profile picture
                    uploaded_file = st.file_uploader("Upload a profile picture", type=["png", "jpg", "jpeg"])
                    if uploaded_file is not None:
                        # Save the profile picture
                        image = Image.open(uploaded_file)

                        # Display the profile picture in a small circle in the top left corner
                        st.image(image, caption='Uploaded Image', width=100, use_container_width=True,
                                 output_format="JPEG")


            elif not authentication_status:
                with info:
                    st.error('Incorrect Password or username')
            else:
                with info:
                    st.warning('Please feed in your credentials')
        else:
            with info:
                st.warning('Username does not exist, Please Sign up')


except Exception as e:
    st.write(f"An error occurred: {e}")
