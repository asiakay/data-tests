# First, ensure you have streamlit_jupyter installed
!pip install streamlit_jupyter

import streamlit_jupyter as stj
import streamlit as st

# Define a function to run the Streamlit app
def run_streamlit_app():
    import requests
    import pandas as pd
    import matplotlib.pyplot as plt
    import seaborn as sns
    from geopy.geocoders import Nominatim
    from geopy.distance import geodesic
    import geopandas as gpd

    # Define the resource ID and API endpoint
    resource_id = '5de268d6-e3a5-4f5c-b43a-0d293b377b50'
    url = f'https://data.boston.gov/api/3/action/datastore_search?resource_id={resource_id}&limit=100'

    # Make the request
    response = requests.get(url)
    data = response.json()

    # Extract records from the response
    records = data['result']['records']

    # Convert to DataFrame
    df = pd.DataFrame.from_records(records)

    # Convert latitude and longitude to numeric values
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')

    # Drop rows with missing or invalid latitude/longitude
    df = df.dropna(subset=['latitude', 'longitude'])

    # Sample data for schools - replace with actual data
    schools_url = "https://gisportal.boston.gov/arcgis/rest/services/Education/OpenData/MapServer/0/query?outFields=*&where=1%3D1&f=geojson"
    response = requests.get(schools_url)
    schools_geojson = response.json()

    # Parse the GeoJSON data
    schools_gdf = gpd.GeoDataFrame.from_features(schools_geojson['features'])

    # Extract relevant columns
    schools_df = pd.DataFrame({
        'school_name': schools_gdf['SCH_NAME'],
        'latitude': schools_gdf.geometry.y,
        'longitude': schools_gdf.geometry.x
    })

    # Add a column to indicate zoning violations (for demonstration purposes, assume some logic to determine this)
    df['zoning_violation'] = df['app_license_status'].apply(lambda x: x == 'Violation')  # Example condition

    # Function to check if an address is in compliance
    def check_compliance(address):
        geolocator = Nominatim(user_agent="geoapi")
        location = geolocator.geocode(address)
        if location:
            address_lat, address_lon = location.latitude, location.longitude
            for index, row in df.iterrows():
                dist = geodesic((address_lat, address_lon), (row['latitude'], row['longitude'])).feet
                if dist < 2640:
                    return False, location
            for index, row in schools_df.iterrows():
                dist = geodesic((address_lat, address_lon), (row['latitude'], row['longitude'])).feet
                if dist < 2640:
                    return False, location
            return True, location
        return None, None

    # Streamlit application
    st.title("Cannabis Establishment Compliance Checker")
    address = st.text_input("Enter an address to check compliance:")

    if address:
        compliant, location = check_compliance(address)
        if location:
            st.write(f"Address: {address}")
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

# Run the Streamlit app in the notebook
stj.run(run_streamlit_app)
