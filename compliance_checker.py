import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import geopandas as gpd
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Get the API key from the environment variable
api_key = os.getenv('GOOGLE_API_KEY')

# Define the resource ID and API endpoint
resource_id = '5de268d6-e3a5-4f5c-b43a-0d293b377b50'
url = f'https://data.boston.gov/api/3/action/datastore_search?resource_id={resource_id}&limit=100'

# Function to get data from API
@st.cache_data
def get_data(url):
    # Make the request
    response = requests.get(url)
    if response.status_code != 200:
        st.error("Failed to fetch data from the API")
        return None
    data = response.json()
    # Extract records from the response
    records = data['result']['records']
    # Convert to DataFrame
    df = pd.DataFrame.from_records(records)
    # Convert latitude and longitude to numeric values
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    # Drop rows with missing or invalid latitude/longitude
    df.dropna(subset=['latitude', 'longitude'], inplace=True)
    return df 

# Load data
df = get_data(url)

# Data for schools 
@st.cache_data
def get_schools_data():
    schools_url = "https://gisportal.boston.gov/arcgis/rest/services/Education/OpenData/MapServer/0/query?outFields=*&where=1%3D1&f=geojson"
    response = requests.get(schools_url)
    if response.status_code != 200:
        st.error("Failed to fetch schools data")
        return None
    schools_geojson = response.json()
    # Parse the GeoJSON data
    schools_gdf = gpd.GeoDataFrame.from_features(schools_geojson['features'])
    # Extract relevant columns
    schools_df = pd.DataFrame({
        'school_name': schools_gdf['SCH_NAME'],
        'latitude': schools_gdf.geometry.y,
        'longitude': schools_gdf.geometry.x
        })
    return schools_df

schools_df = get_schools_data()
    

# Add a column to indicate zoning violations (for demonstration purposes, assume some logic to determine this)
df['zoning_violation'] = df['app_license_status'].apply(lambda x: x == 'Violation')  # Example condition

# Function to check if an address is in compliance
def check_compliance(address):
    geolocator = Nominatim(user_agent="geoapi")
    location = geolocator.geocode(address)
    if not location:
        return None, None
    
    address_lat, address_lon = location.latitude, location.longitude
    
    for index, row in df.iterrows():
            dist = geodesic((address_lat, address_lon), (row['latitude'], row['longitude'])).feet
            if dist < 2640:
                return False, location
            
    for index, row in schools_df.iterrows():
            dist = geodesic((address_lat, address_lon), (row['latitude'], row['longitude'])).feet
            if dist < 2640:
                return False, location
            
    return False, location
   

# Function to get address suggestions from Google Places API
def get_address_suggestions(query, api_key):
    url = f"https://maps.googleapis.com/maps/api/place/autocomplete/json?input={query}&types=address&key={api_key}"
    response = requests.get(url)
    if response.status_code !=200:
        return []
    suggestions = response.json().get('predictions', [])
    return [suggestion['description'] for suggestion in suggestions]

# Streamlit application
st.title("Establishment Compliance Checker")


# Address input with auto-suggestions
address_input = st.text_input("Start typing an address to check compliance:")

if address_input:
    suggestions = get_address_suggestions(address_input, api_key)
    selected_address = st.selectbox("Select an address:", suggestions)
else: 
    selected_address = None
    
if selected_address: 
    compliant, location = check_compliance(selected_address)

    if location: 
        st.write(f"Address: {selected_address}")
        st.write(f"Location: Latitude {location.latitude}, Longitude {location.longitude}")
        if compliant:
            st.success("The address is in compliance with zoning regulations.")
        else: 
            st.error("The address is NOT in compliance with zoning regulations.")

        # Generate the plot
        plt.figure(figsize=(14, 10))

        # Plot regular cannabis establishments
        sns.scatterplot(x='longitude', y='latitude', hue='app_license_status', data=df, s=100, palette='viridis', edgecolor="w", legend='full')

        # Plot cannabis establishments with violations with a distinct marker and color
        sns.scatterplot(x='longitude', y='latitude', data=df[df['zoning_violation'] == True], s=100, color='red', marker='P', edgecolor="w", label='Violations')

        # Plot the input address
        plt.scatter(location.longitude, location.latitude, color='blue', s=200, marker='*', label='Input Address')

        # Adding labels for business names
        for line in range(0, df.shape[0]):
            plt.text(df.longitude.iloc[line], df.latitude.iloc[line], df.app_business_name.iloc[line], horizontalalignment='left', size='medium', color='black', weight='semibold')

        plt.title('Cannabis Establishments and Zoning Violations')
        plt.xlabel('Longitude')
        plt.ylabel('Latitude')
        plt.grid(True)
        plt.legend()
        st.pyplot(plt)
    else:
        st.error("Could not geocode the address. Please try another address.")
