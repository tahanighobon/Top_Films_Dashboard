import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from streamlit_option_menu import option_menu
from numerize.numerize import numerize
from streamlit_extras.metric_cards import style_metric_cards
from fpdf import FPDF
from io import BytesIO
import requests
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import warnings
import time

# ============================
# Page Config
# ============================
st.set_page_config(page_title="Top 250 Movies Dashboard", page_icon=":movie_camera:", layout="wide")
st.subheader(":movie_camera: Top 250 Movies Dashboard")
st.markdown('##')

# ============================
# Load Data
# ============================
df = pd.read_csv("IMDB Top 250 Movies.csv")

# ============================
# Data Cleaning & Formatting
# ============================
def parse_box_office(value):
    if pd.isna(value):
        return 0
    value = str(value).replace('$', '').replace(',', '').strip()
    if value.endswith('M'):
        return float(value[:-1]) * 1_000_000
    elif value.endswith('K'):
        return float(value[:-1]) * 1_000
    else:
        try:
            return float(value)
        except ValueError:
            return 0

df['box_office'] = df['box_office'].apply(parse_box_office)
df['rating'] = pd.to_numeric(df['rating'], errors='coerce')

# ============================
# Sidebar Filters
# ============================
st.sidebar.image("logo.png", caption="")

st.sidebar.header("Filters")

certificate = df['certificate'].dropna().unique()
certificate = ['All'] + list(certificate)
selected_certificate = st.sidebar.selectbox("Select certificate", certificate)

min_year = int(df['year'].min())
max_year = int(df['year'].max())
selected_years = st.sidebar.slider("Select Year Range", min_year, max_year, (min_year, max_year))

# ============================
# Sidebar Genre Filter
# ============================
def sideBar():
    with st.sidebar:
        selected_genre = option_menu(
            menu_title="Main Menu",
            options=['All Movies', 'Sci-Fi'],
            icons=['🎞️', '🚀']
        )
    return selected_genre

selected_genre = sideBar()

# ============================
# Apply Filters (Certificate + Year + Genre)
# ============================
if selected_certificate == "All":
    filtered_df = df[
        (df['year'] >= selected_years[0]) & (df['year'] <= selected_years[1])
    ]
else:
    filtered_df = df[
        (df['certificate'] == selected_certificate) &
        (df['year'] >= selected_years[0]) & (df['year'] <= selected_years[1])
    ]

# ✨ Apply genre filter here before rendering
if selected_genre == "Sci-Fi":
    filtered_df = filtered_df[filtered_df['genre'].str.contains("Sci-Fi", case=False, na=False)]

# ============================
# Header Text
# ============================
if selected_genre == "Sci-Fi":
    st.markdown("## 🚀 Dashboard for Sci-Fi Movies")
else:
    st.markdown("## 🎬 Dashboard for All Movies")

# ============================
# Home KPIs
# ============================
def Home():
    with st.expander("Dataset"):
        showData = st.multiselect('Filter:', df.columns, default=[])
        st.write(filtered_df[showData])

    total_movies = len(filtered_df)
    if total_movies > 0:
        top_movie_rating = filtered_df.loc[filtered_df["rating"].idxmax(), "name"]
        top_movie_box_office = filtered_df.loc[filtered_df["box_office"].idxmax(), "name"]
        most_common_genre = filtered_df["genre"].mode()[0]
    else:
        top_movie_rating = "N/A"
        top_movie_box_office = "N/A"
        most_common_genre = "N/A"

    col1, col2, col3, col4 = st.columns(4, gap="large")

    with col1:
        st.info('Total No. Movies', icon="📍")
        st.metric(label="Movies", value=f"{total_movies:,.0f}")

    with col2:
        st.info('Top Movie Rating', icon="⭐")
        st.metric(label="Movie", value=top_movie_rating)

    with col3:
        st.info('Top Movie Box Office', icon="💰")
        st.metric(label="Movie", value=top_movie_box_office)

    with col4:
        st.info('Most Common Genre', icon="🎥")
        st.metric(label="Genre", value=most_common_genre)

    st.markdown("""---""")

Home()

# ============================
# Graphs Section
# ============================
def graphs():
    if filtered_df.empty:
        st.warning("No data to display for the selected filters.")
        return

    top_genres = filtered_df['genre'].value_counts().head(10).reset_index()
    top_genres.columns = ['Genre', 'Number of Movies']
    fig_genres = px.bar(top_genres, x='Genre', y='Number of Movies',
                        title='Top 10 Most Frequent Genres',
                        labels={'Genre': 'Genre', 'Number of Movies': 'Number of Movies'},
                        color='Number of Movies', color_continuous_scale='Inferno')

    certificate_counts = filtered_df['certificate'].value_counts()
    fig_certificate_donut = px.pie(certificate_counts, names=certificate_counts.index, values=certificate_counts.values,
                                   title='Distribution by Certificate', hole=0.4, color=certificate_counts.index)

    top_directors = filtered_df['directors'].value_counts().head(10).reset_index()
    top_directors.columns = ['Director', 'Number of Movies']
    fig_directors_pie = px.pie(top_directors, names='Director', values='Number of Movies',
                               title='Top 10 Directors', color='Number of Movies',
                               color_discrete_sequence=px.colors.sequential.Viridis)

    col1, col2, col3 = st.columns(3)
    col1.plotly_chart(fig_genres)
    col2.plotly_chart(fig_certificate_donut)
    col3.plotly_chart(fig_directors_pie)

    movies_by_year = filtered_df.groupby('year').size().reset_index(name='number_of_movies')
    fig_area_chart = px.area(movies_by_year, x='year', y='number_of_movies',
                             title='Number of Movies per Year',
                             labels={'year': 'Year', 'number_of_movies': 'Number of Movies'},
                             template='plotly', color_discrete_sequence=['lightblue'])
    st.plotly_chart(fig_area_chart)

graphs()

# ============================
# Tables Section
# ============================
def tables():
    if filtered_df.empty:
        st.warning("No data to display in tables.")
        return

    cast_counts = filtered_df['casts'].str.split(',').explode().value_counts().head(10)
    top_10_rating = filtered_df[['name', 'rating']].sort_values(by='rating', ascending=False).head(10)
    top_10_gross = filtered_df[['name', 'box_office']].sort_values(by='box_office', ascending=False).head(10)
    top_10_runtime = filtered_df[['name', 'run_time']].sort_values(by='run_time', ascending=False).head(10)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("Top Actors")
        st.dataframe(cast_counts)

    with col2:
        st.subheader("Highest Rating")
        st.dataframe(top_10_rating[['name', 'rating']])

    with col3:
        st.subheader("Highest Revenue")
        st.dataframe(top_10_gross[['name', 'box_office']])

tables()

# ============================
# Theme (Optional)
# ============================
hide_st_style = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)

