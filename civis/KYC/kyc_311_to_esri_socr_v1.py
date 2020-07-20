#!/usr/bin/env python
# coding: utf-8

import os
pwd=os.getcwd()
import sys
#!{sys.executable} -m pip install sodapy
from sodapy import Socrata
import pandas as pd
import numpy as np
from arcgis.gis import GIS
from shapely.geometry import Point
import geopandas as gpd
from arcgis.features import FeatureLayerCollection
import intake_civis

lahub_user = os.environ["LAHUB_ACC_USERNAME"]
lahub_pass = os.environ["LAHUB_ACC_PASSWORD"]
socrata_token = 'LJ60SFL7ZqoC4IWosLhEmJV2a'
socrata_user = os.environ["SOCRATA_ACC_USERNAME"]
socrata_pass = os.environ["SOCRATA_ACC_PASSWORD"]
myla311_layer = '4db3e9c3d13543b6a686098e0603ddcf'
pwd = os.getcwd()
OUTPUT_FILE = pwd + "/MyLA311 Service Requests Last 6 Months.csv"

def prep_311_data(file,token,user,pas):
    client = Socrata("data.lacity.org", token, username=user, password=pas)
    df = pd.DataFrame(client.get('rq3b-xjk8', limit=10000000))
    df2=df[(df.requesttype != 'Homeless Encampment')]
    df2.to_csv(file, index=False)

def update_geohub_layer(user, pw, layer, update_data):
    geohub = GIS('https://lahub.maps.arcgis.com', user, pw)
    flayer = geohub.content.get(layer)
    flayer_collection = FeatureLayerCollection.fromitem(flayer)
    flayer_collection.manager.overwrite(update_data)


if __name__ == "__main__":
    prep_311_data(OUTPUT_FILE,socrata_token,socrata_user,socrata_pass)
    update_geohub_layer(lahub_user, lahub_pass, myla311_layer, OUTPUT_FILE)
