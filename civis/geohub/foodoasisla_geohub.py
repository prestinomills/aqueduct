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
output = pwd +'/Food Oasis LA.csv'
fla_layer = '9423899063404659b3c4507667b4893d'


def Flagnum(flag):
    if(flag == True):
        return 1;
    else:
        return 0

def foodoasisla(json, output):
    r = requests.get(json)
    j = r.json()
    df = pandas.DataFrame.from_dict(j)
    #fix column that looks like a dictionary
    split_df = (pandas.DataFrame.from_records(df.categories)
                         .rename(columns = 
                                 {0: "one", 1: "two", 2: "three", 3: "four"}
                                )
                        )
    # Need cleaning, since one row can have up to 4 different entires with the `categories` column
    category_df = pandas.DataFrame()
    for col in ["one", "two", "three", "four"]:
        # This apply function unpacks all the dictionary key/value pairs
        # However many items are in there, it'll create new columns for it
        this_col_df = split_df[col].apply(pandas.Series)
        print("Unpack our dictionary")
        category_df = category_df.append(this_col_df, sort=False)
        
        
    # Clean up, drop NaN values
    category_df = (category_df[category_df.stakeholder_id.notna()]
                   .reset_index(drop=True)
                   .drop(columns = ["id", "display_order"])
                    .rename(columns = {"name": "category_name"})
                   .astype({"stakeholder_id": int})
                  )
    df2 = pandas.merge(df, 
                   category_df, 
                   left_on = "id", 
                   right_on = "stakeholder_id",
                   validate = "1:m"
              )
    df3 = df2.drop(columns = ["categories"])
    df3['categories'] = df3[['id','category_name']].groupby(['id'])['category_name'].transform(lambda x: ' & '.join(x))
    df4 = df3.drop_duplicates(subset = ['id'])

    df4['FPF'] = df4.apply(lambda x: 'Food Pantry' in x.categories, axis=1)
    df4['MPF'] = df4.apply(lambda x: 'Meal Program' in x.categories, axis=1)
    df4['OTF'] = df4.apply(lambda x: 'Other' in x.categories, axis=1)
    df4['SHF'] = df4.apply(lambda x: 'Shelter' in x.categories, axis=1)
    df4['FBF'] = df4.apply(lambda x: 'Food Bank' in x.categories, axis=1)
    df4['CCF'] = df4.apply(lambda x: 'Care Center' in x.categories, axis=1)
    df4['UKF'] = df4.apply(lambda x: 'Unknown' in x.categories, axis=1)
    df4['CGF'] = df4.apply(lambda x: 'Community Garden' in x.categories, axis=1)

    df4['Food Pantry Flag'] = df4.FPF.apply(Flagnum)
    df4['Meal Program Flag'] = df4.MPF.apply(Flagnum)
    df4['Other Flag'] = df4.OTF.apply(Flagnum)
    df4['Shelter Flag'] = df4.SHF.apply(Flagnum)
    df4['Food Bank Flag'] = df4.FBF.apply(Flagnum)
    df4['Care Center Flag'] = df4.CCF.apply(Flagnum)
    df4['Unknown Flag'] = df4.UKF.apply(Flagnum)
    df4['Community Garden Flag'] = df4.CGF.apply(Flagnum)

    fla = df4[['name','address1','address2','city','state','zip','phone','latitude','longitude','website','notes','email','facebook','twitter','pinterest','linkedin','description','donationSchedule','donationDeliveryInstructions','donationNotes','covidNotes','categoryNotes','eligibilityNotes','is_verified','Food Pantry Flag', 'Meal Program Flag', 'Other Flag', 'Shelter Flag', 'Food Bank Flag', 'Care Center Flag', 'Unknown Flag', 'Community Garden Flag']].copy()
    
    fla.index.name='UNIQID'
    fla.to_csv(output)

if __name__ == "__main__":
    foodoasisla(URL,output)
    update_geohub_layer(lahub_user, lahub_pass, fla_layer, output)
