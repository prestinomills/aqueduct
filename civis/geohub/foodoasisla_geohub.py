import requests
import pandas
import os
pwd=os.getcwd()
import sys
from arcgis.gis import GIS
from arcgis.features import FeatureLayerCollection
import intake_civis

lahub_user = os.environ["LAHUB_ACC_USERNAME"]
lahub_pass = os.environ["LAHUB_ACC_PASSWORD"]
URL = "https://foodoasis.la/api/stakeholderbests?categoryIds[]=1&categoryIds[]=9&latitude=33.99157326008516&longitude=-118.25853610684041&distance=5&isInactive=either&verificationStatusId=0&maxLng=-117.83718436872704&maxLat=34.193301591847344&minLng=-118.67988784495431&minLat=33.78936487151597&tenantId=1"
output = pwd +'/foodoasisla.csv'
flayer = '61129345f82a49718f294e52174bef2e'


def foodoasisla(json, output):
    r = requests.get(json)
    j = r.json()
    fla = pandas.DataFrame.from_dict(j)
    fla.index.name='UNIQID'
    fla.to_csv(output)

def update_geohub_layer(user, pw, layer, update_data):
    geohub = GIS('https://lahubcom.maps.arcgis.com', user, pw)
    flayer = geohub.content.get(layer)
    flayer_collection = FeatureLayerCollection.fromitem(flayer)
    flayer_collection.manager.overwrite(update_data)

if __name__ == "__main__":
    foodoasisla(URL,output)
    update_geohub_layer(lahub_user, lahub_pass, fla_layer, output)
