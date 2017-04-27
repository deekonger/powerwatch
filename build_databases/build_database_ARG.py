# This Python file uses the following encoding: utf-8
"""
PowerWatch
build_database_argentina.py
Get power plant data from Argentina and convert to PowerWatch format.
Data Source: Ministerio de Energia y Mineria, Argentina
Data Portal: http://datos.minem.gob.ar/index.php
Generation Data : http://energia3.mecon.gov.ar/contenidos/archivos/Reorganizacion/informacion_del_mercado/publicaciones/mercado_electrico/estadisticosectorelectrico/2015/A1.POT_GEN_COMB_POR_CENTRAL_2015.xlsx
Additional information: http://datos.minem.gob.ar/api/search/dataset?q=centrales
Additional information: http://datos.minem.gob.ar/api/rest/dataset/
Additional information: https://www.minem.gob.ar/www/706/24621/articulo/noticias/1237/aranguren-e-ibarra-presentaron-el-portal-de-datos-abiertos-del-ministerio-de-energia-y-mineria.html
Issues:
- Several plants are listed as mobile ("movil"); the largest is http://www.enarsa.com.ar/index.php/es/energiaelectrica/386-unidades-de-emergencia-movil .
- These cannot be geolocated.
"""

import csv
import datetime
import xlrd
import sys
import os
import json

sys.path.insert(0, os.pardir)
import powerwatch as pw

# params
COUNTRY_NAME = u"Argentina"
SOURCE_NAME = u"Ministerio de Energía y Minería"
SOURCE_URL = u"http://energia3.mecon.gov.ar/contenidos/archivos/Reorganizacion/informacion_del_mercado/publicaciones/mercado_electrico/estadisticosectorelectrico/2015/A1.POT_GEN_COMB_POR_CENTRAL_2015.xlsx"
SAVE_CODE = u"ARG"
RAW_FILE_NAME = pw.make_file_path(fileType="raw", subFolder=SAVE_CODE, filename="A1.POT_GEN_COMB_POR_CENTRAL_2015.xlsx")
LOCATION_FILE_NAME = pw.make_file_path(fileType="resource", subFolder=SAVE_CODE, filename="locations_ARG.csv")
COMMISSIONING_YEAR_FILE_NAME = pw.make_file_path(fileType="resource", subFolder=SAVE_CODE, filename="commissioning_years_ARG.csv")
CSV_FILE_NAME = pw.make_file_path(fileType = "src_csv", filename = "argentina_database.csv")
SAVE_DIRECTORY = pw.make_file_path(fileType = "src_bin")
YEAR_OF_DATA = 2015
CAPACITY_CONVERSION_TO_MW = 0.001       # capacity values are given in kW in the raw data
GENERATION_CONVERSION_TO_GWH = 0.001    # generation values are given in MWh in the raw data

# other parameters
COLS = {'owner':1, 'name':2, 'fuel':3, 'grid':4, 'capacity':6, 'generation':7}
TAB = "POT_GEN"
START_ROW = 8

gen_start = datetime.date(YEAR_OF_DATA,1,1)
gen_stop = datetime.date(YEAR_OF_DATA,12,31)

# optional raw file(s) download
downloaded = pw.download(COUNTRY_NAME, {RAW_FILE_NAME:SOURCE_URL})

# set up fuel type thesaurus
fuel_thesaurus = pw.make_fuel_thesaurus()

# create dictionary for power plant objects
plants_dictionary = {}

# extract powerplant information from file(s)
print(u"Reading in plants...")

# read locations
locations_dictionary = {}
with open(LOCATION_FILE_NAME,'r') as f:
    datareader = csv.reader(f)
    headers = datareader.next()
    for row in datareader:
        locations_dictionary[pw.format_string(row[0])] = [row[1],row[2]]

# read commissioning years
commissioning_years_dictionary = {}
with open(COMMISSIONING_YEAR_FILE_NAME,'r') as f:
    datareader = csv.reader(f)
    headers = datareader.next()
    for row in datareader:
        commissioning_years_dictionary[pw.format_string(row[0])] = row[1]

# read data from csv and parse
count = 1

wb = xlrd.open_workbook(RAW_FILE_NAME)
ws = wb.sheet_by_name(TAB)

# treat first data row specially for plant name
rv0 = ws.row_values(START_ROW)
current_plant_name = pw.format_string(rv0[COLS['name']])
current_owner = pw.format_string(rv0[COLS['owner']])
current_fuel_types = pw.standardize_fuel(rv0[COLS['fuel']],fuel_thesaurus)
current_capacity_sum = float(rv0[COLS['capacity']]) * CAPACITY_CONVERSION_TO_MW
current_generation_sum = float(rv0[COLS['generation']]) * GENERATION_CONVERSION_TO_GWH

test_print = False
for row_id in range(START_ROW+1, ws.nrows):
    rv = ws.row_values(row_id) 

    row_fuel = pw.format_string(rv[COLS['fuel']],None)
    row_name = pw.format_string(rv[COLS['name']],None)
    row_grid = pw.format_string(rv[COLS['grid']],None)

    if row_grid == u"AISLADO":
        continue                    # don't add islanded generators (not grid-connected)

    if row_fuel:

        if row_name:

            if current_plant_name:

                # assign ID number, make PowerPlant object, add to dictionary
                idnr = pw.make_id(SAVE_CODE,count)
                annual_generation = pw.PlantGenerationObject(gwh=current_generation_sum,start_date=gen_start,end_date=gen_stop,source=SOURCE_NAME)
                new_plant = pw.PowerPlant(plant_idnr=idnr,plant_name=current_plant_name,plant_owner=current_owner,
                    plant_fuel=current_fuel_types,plant_country=COUNTRY_NAME,plant_capacity=current_capacity_sum,
                    plant_cap_year=YEAR_OF_DATA,plant_source=SOURCE_NAME,plant_source_url=SOURCE_URL,
                    plant_generation=annual_generation)
                plants_dictionary[idnr] = new_plant
                count += 1

            # reset all current values to this row
            current_plant_name = row_name
            current_fuel_types = pw.standardize_fuel(row_fuel,fuel_thesaurus)
            current_owner = pw.format_string(rv[COLS['owner']],None)
            try:
                current_capacity_sum = float(rv[COLS['capacity']]) * CAPACITY_CONVERSION_TO_MW
            except:
                print(u"-Error: Can't read capacity for plant {0}.".format(current_plant_name))
                current_capacity_sum = 0.0
            try:
                current_generation_sum = float(rv[COLS['generation']]) * GENERATION_CONVERSION_TO_GWH
            except:
                print(u"-Error: Can't read generation for plant {0}; value is {1}.".format(current_plant_name,rv[COLS['generation']]))
                current_generation_sum = 0.0
    
        else:
            # additional unit of current plant
            current_capacity_sum += float(rv[COLS['capacity']]) * CAPACITY_CONVERSION_TO_MW
            current_generation_sum += float(rv[COLS['generation']]) * GENERATION_CONVERSION_TO_GWH
            current_fuel_types.update(pw.standardize_fuel(row_fuel,fuel_thesaurus))

    else:

        if current_plant_name:

            # assign ID number, make PowerPlant object, add to dictionary
            idnr = pw.make_id(SAVE_CODE,count)
            annual_generation = pw.PlantGenerationObject(gwh=current_generation_sum,start_date=gen_start,end_date=gen_stop,source=SOURCE_NAME)
            new_plant = pw.PowerPlant(plant_idnr=idnr,plant_name=current_plant_name,plant_owner=current_owner,
                plant_fuel=current_fuel_types,plant_country=COUNTRY_NAME,plant_capacity=current_capacity_sum,
                plant_cap_year=YEAR_OF_DATA,plant_source=SOURCE_NAME,plant_source_url=SOURCE_URL,
                plant_generation=annual_generation)
            plants_dictionary[idnr] = new_plant
            count += 1

            # reset all current values to null
            current_plant_name = pw.NO_DATA_UNICODE
            current_fuel_types = pw.NO_DATA_SET.copy()
            current_owner = pw.NO_DATA_UNICODE
            current_capacity_sum = 0.0
            current_generation_sum = 0.0

        else:
            continue

# now assign locations and commissioning years
location_not_found = []
year_not_found = []

for idnr,plant in plants_dictionary.iteritems():

    if plant.name in locations_dictionary.keys():
        coords = locations_dictionary[plant.name]
        plant.location = pw.LocationObject(pw.NO_DATA_UNICODE,coords[0],coords[1])
 
    else:
        location_not_found.append(plant)

    if plant.name in commissioning_years_dictionary.keys():
        plant.commissioning_year = commissioning_years_dictionary[plant.name]

    else:
        year_not_found.append(plant)

"""
print("Locations not found for these plants:")
location_not_found.sort(key = lambda x:x.capacity, reverse=True)
for plant in location_not_found:
    if 'MOVIL' not in plant.name:
        print(u"{0}, {1} MW".format(plant.name, plant.capacity))

print("Commissioning year not found for these plants:")
year_not_found.sort(key = lambda x:x.capacity, reverse=True)
for plant in year_not_found:
    print(u"{0}, {1} MW".format(plant.name, plant.capacity))
"""

# report on plants read from file
print(u"...read {0} plants.".format(len(plants_dictionary)))

# write database to csv format
pw.write_csv_file(plants_dictionary,CSV_FILE_NAME)

# save database
pw.save_database(plants_dictionary,SAVE_CODE,SAVE_DIRECTORY)
print(u"Pickled database to {0}".format(SAVE_DIRECTORY))
