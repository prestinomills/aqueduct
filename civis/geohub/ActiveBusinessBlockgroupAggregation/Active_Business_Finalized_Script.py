#!/usr/bin/env python
# coding: utf-8

# In[2]:


# %load active_business_script.py
"""
Created on Wed May  1 08:51:03 2019

@author: myrfid041
"""

import os
pwd=os.getcwd()
import sys
#!{sys.executable} -m pip install sodapy
from sodapy import Socrata
import pandas as pd
import numpy as np
#!{sys.executable} -m pip install geopandas
import geopandas as gpd
#import  install altair.vegalite.v2 as alt
import folium
import xlsxwriter
from shapely.geometry import Point
#!{sys.executable} -m pip install arcgis
from arcgis.gis import GIS
from arcgis.features.summarize_data import join_features
import json
import credentials
from IPython.display import display
from arcgis.features import FeatureLayer
from arcgis.features import FeatureLayerCollection
import json
from copy import deepcopy
import intake_civis

lahub_user = os.environ["LAHUB_ACC_USERNAME"]
lahub_pass = os.environ["LAHUB_ACC_PASSWORD"]


#---Setting the Outputs
ABOutput=pwd+'/Listing_of_Active_Businesses.csv'



#---Pulling Active Business Data
client = Socrata("data.lacity.org", None)
abiz = pd.DataFrame(client.get('ngkp-kqkn', limit=10000000))



#---Pull NAIC Industry Table
n_table='../naics_industry_table.csv'
naics_table=pd.read_csv(n_table)


def chunks(l, n, z):
    """Yield successive n-sized chunks from l."""
    for i in range(0, len(l), n):
        chunk_list=l[i:i + n]
        z.edit_features(updates= chunk_list)
        print("update successful")


def abOutput(x):
    x.to_csv(ABOutput)


def top10(x):
    x.pred_ind=x.idxmax(axis=1)
    predom_industries=pd.DataFrame(x.pred_ind.value_counts())[0:12]
    predom_industries=predom_industries.index.tolist()
    predom_industries.remove('Professional, Scientific, and Technical Services');
    predom_industries.remove('Other Services (except Public Administration)');
    return predom_industries

def dataprep(x,y):
    df=x
    df=df.dropna(subset=['location_1','naics'])
    df['location_2']=df['location_1'].astype('str') #Prepping location data to parse (x,y) values
    df['location_2']=df['location_2'].str[34:-2]
    locations = df["location_2"].str.split(",", n = 1, expand = True) #Creating a dataframe with x,y coordinates
    locations[1] =locations[1].str[1:]
    df['lon']=locations[0]
    df['lat']=locations[1]
    df=df.dropna(subset=['lat','lon'])
    df['naics_sector'] = df['naics'].str[:2].astype('str')
    dfn=y
    dfn['naics_sector']=dfn['naics_sector'].astype('str')
    df2=pd.merge(df,dfn,how='inner',on='naics_sector',validate='m:1')
    df2.lon=df.lon.astype(float)
    df2.lat=df.lat.astype(float)
    # Create geometry column
    df2['geometry'] = df2.apply(
        lambda row: Point(row.lon, row.lat), axis=1)
    # Rename columns
    df2.rename(columns = {'lon': 'longitude', 'lat':'latitude'}, inplace=True)
    df2=df2.dropna(subset=['longitude','latitude'])
    gdf = gpd.GeoDataFrame(df2, geometry = 'geometry')
    # Set CRS
    gdf.crs = {'init':'epsg:4326'}
    # Drop NAs, then project to CA State Plane
    gdf = gdf[gdf.geometry.notna()]
    gdf = gdf.to_crs({'init':'epsg:2229'})
    block = gpd.read_file('./LACounty_Blockgroup/')
    block.crs={'init':'epsg:2229'}
    sjoin=gpd.sjoin(gdf,block,how='inner',op='intersects')
    sjoin2=sjoin.pivot_table(index='GEOID10',values='business_name',columns=['naics_industry'],aggfunc=len)
    sjoin2=sjoin2.fillna(0)
    abOutput(sjoin2)
    predom_ind=top10(sjoin2)
    return predom_ind


def go():
    predom=dataprep(abiz,naics_table)
    updated_csv_df = pd.read_csv(ABOutput)
    updated_csv_df['GEOID10']=updated_csv_df['GEOID10'].astype(str)
    updated_csv_df.dtypes
    updated_csv_df['GEOID10'] = updated_csv_df['GEOID10'].apply(lambda x: '{0:0>12}'.format(x))
    geohub_updates(updated_csv_df,credentials.lahub_user,credentials.lahub_pass,predom)


def update_desc(x,y,z):
    active_biz=z.content.get(y)    
    text = """
    This layer is aggregating <a href="https://data.lacity.org/A-Prosperous-City/Listing-of-Active-Businesses/6rrh-rzua">Listing of Active Businesses Data</a> that have geospatial information associated. The top 10 most frequent industries in block groups are:
    {}

    """
    
    item_props = {'title' : 'Active Businesses Data by Block Group', 'description':text.format(x)}
    active_biz.update(item_properties=item_props)
    print("updates made!")


def geohub_updates(x,user,pas,topz):
    gis = GIS('https://lahub.maps.arcgis.com',  username=user, password=pas)
    output_layer_name = '067a9242fbef4afeb1ca0744952e5724'
    actbus=gis.content.search(output_layer_name)
    ActiveBusinesses_item = actbus[0]
    ActiveBusinesses_flayer = ActiveBusinesses_item.layers[0]
    ActiveBusinesses_flayer
    ActiveBusinesses_fset = ActiveBusinesses_flayer.query() #querying without any conditions returns all the features
    ActiveBusinesses_fset.sdf.head()
    ActiveBusinesses_fset.sdf.shape
    ActiveBusinesses_fset.sdf.dtypes
    overlap_rows = pd.merge(left = ActiveBusinesses_fset.sdf, 
                        right = x, 
                        how='inner',
                        on = 'GEOID10')
    overlap_rows.head(5)

    # overlap_rows.to_csv("C:\\Users\\mad10412\\Desktop\\Merged.csv")
    overlap_rows.shape

    #Perform updates

    features_for_update = [] #list containing corrected features
    all_features = ActiveBusinesses_fset.features

    for GEOID10 in overlap_rows['GEOID10']:
        # get the feature to be updated
        original_feature = [f for f in all_features if f.attributes['GEOID10'] == GEOID10][0]
        feature_to_be_updated = deepcopy(original_feature)

        # get the matching row from csv
        matching_row = x.where(x.GEOID10 == GEOID10).dropna()

        # assign the updated values
        feature_to_be_updated.attributes['Accommodation_and_Food_Services'] = matching_row['Accommodation and Food Services'].values[0]
        feature_to_be_updated.attributes['Administrative_and_Support_and_'] = matching_row['Administrative and Support and Waste Management and Remediation Services'].values[0]
        feature_to_be_updated.attributes['Agriculture__Forestry__Fishing_'] = matching_row['Agriculture, Forestry, Fishing and Hunting'].values[0]
        feature_to_be_updated.attributes['Arts__Entertainment__and_Recrea'] = matching_row['Arts, Entertainment, and Recreation'].values[0]
        feature_to_be_updated.attributes['Construction'] = matching_row['Construction'].values[0]
        feature_to_be_updated.attributes['Educational_Services'] = matching_row['Educational Services'].values[0]
        feature_to_be_updated.attributes['Finance_and_Insurance'] = matching_row['Finance and Insurance'].values[0]
        feature_to_be_updated.attributes['Health_Care_and_Social_Assistan'] = matching_row['Health Care and Social Assistance'].values[0]
        feature_to_be_updated.attributes['Information'] = matching_row['Information'].values[0]
        feature_to_be_updated.attributes['Manufacturing'] = matching_row['Manufacturing'].values[0]
        feature_to_be_updated.attributes['Medical_Marijuana_Collective'] = matching_row['Medical Marijuana Collective'].values[0]
        feature_to_be_updated.attributes['Mining'] = matching_row['Mining'].values[0]
        feature_to_be_updated.attributes['Not_Classified'] = matching_row['Not Classified'].values[0]
        feature_to_be_updated.attributes['Other_Services__except_Public_A'] = matching_row['Other Services (except Public Administration)'].values[0]
        feature_to_be_updated.attributes['Professional__Scientific__and_T'] = matching_row['Professional, Scientific, and Technical Services'].values[0]
        feature_to_be_updated.attributes['Real_Estate_Rental_and_Leasing'] = matching_row['Real Estate Rental and Leasing'].values[0]
        feature_to_be_updated.attributes['Retail_Trade'] = matching_row['Retail Trade'].values[0]
        feature_to_be_updated.attributes['Transportation_and_Warehousing'] = matching_row['Transportation and Warehousing'].values[0]
        feature_to_be_updated.attributes['Utilities'] = matching_row['Utilities'].values[0]
        feature_to_be_updated.attributes['Wholesale_Trade'] = matching_row['Wholesale Trade'].values[0]

        #add this to the list of features to be updated
        features_for_update.append(feature_to_be_updated)
    chunks(features_for_update, 1000,ActiveBusinesses_flayer)
    update_desc(topz,output_layer_name,gis)


get_ipython().run_cell_magic('time', '', 'if __name__ == "__main__":\n\tgo()')



