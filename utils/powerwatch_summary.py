"""Create summary of the powerwatch database."""

import sys
import os
import csv
import argparse

sys.path.insert(0, os.pardir)
import powerwatch as pw

DEFAULT_DATABASE_FILE = os.path.join(pw.OUTPUT_DIR, "powerwatch_data.csv")
DEFAULT_SUMMARY_FILE = os.path.join(pw.OUTPUT_DIR, "powerwatch_summary.csv")

def summary_fieldnames():
	"""Ordered list of output CSV fields; equivalently the header."""
	return ['country',
			'iso_code',
			'count',
			'total_capacity_gw',
			'max_capacity_mw',
			'count_distinct_fuel',
			'count_distinct_name',
			'count_distinct_owner',
			'count_distinct_source',
			'count_fuel_coal',
			'capacity_gw_fuel_coal',
			'count_fuel_gas',
			'capacity_gw_fuel_gas',
			'count_fuel_oil',
			'capacity_gw_fuel_oil',
			'count_fuel_petcoke',
			'capacity_gw_fuel_petcoke',
			'count_fuel_hydro',
			'capacity_gw_fuel_hydro',
			'count_fuel_nuclear',
			'capacity_gw_fuel_nuclear',
			'count_fuel_wind',
			'capacity_gw_fuel_wind',
			'count_fuel_solar',
			'capacity_gw_fuel_solar',
			'count_fuel_geothermal',
			'capacity_gw_fuel_geothermal',
			'count_fuel_biomass',
			'capacity_gw_fuel_biomass',
			'count_fuel_cogeneration',
			'capacity_gw_fuel_cogeneration',
			'count_fuel_waste',
			'capacity_gw_fuel_waste',
			'count_fuel_wave_and_tidal',
			'capacity_gw_fuel_wave_and_tidal',
			'count_fuel_other',
			'capacity_gw_fuel_other',
			'count_null_name',
			'count_null_pw_idnr',
			'count_null_capacity_mw',
			'count_null_year_of_capacity_data',
			'count_null_owner',
			'count_null_source',
			'count_null_url',
			'count_null_latitude',
			'count_null_longitude',
			'count_null_fuel',
			'count_null_generation_gwh_all',
			'count_generation_gwh_2012',
			'count_generation_gwh_2013',
			'count_generation_gwh_2014',
			'count_generation_gwh_2015',
			'count_generation_gwh_2016']

def country_summary(db_conn, country, iso_code):
	"""
	Get a country-level summary of the database.

	Parameters
	----------
	db_conn : sqlite3.Connection
		Open database connection.
	country : str
		Standard country name used in the database.
	iso_code : str
		3 character country code.

	Returns
	-------
	Dict holding the summarized metrics for the country.

	"""
	summary = {'country': country, 'iso_code': iso_code}
	c = db_conn.cursor()

	# count number of powerplants
	stmt = '''SELECT COUNT(*) FROM powerplants
				WHERE (country=?)'''
	query = c.execute(stmt, (country,))
	summary['count'], = query.fetchone()

	# skip rest of summary if there aren't any powerplants
	if not summary['count']:
		return summary

	# compute total capacity
	stmt = '''SELECT SUM(capacity_mw) FROM powerplants
				WHERE (country=?)'''
	query = c.execute(stmt, (country,))
	total_capacity_mw, = query.fetchone()
	summary['total_capacity_gw'] = total_capacity_mw / 1000

	# compute maximum single capacity
	stmt = '''SELECT MAX(capacity_mw) FROM powerplants
				WHERE (country=?)'''
	query = c.execute(stmt, (country,))
	summary['max_capacity_mw'], = query.fetchone()

	# count distinct fuel types 
	stmt = '''SELECT COUNT(*) FROM (
				SELECT DISTINCT(fuel1) from powerplants
					WHERE (country="{0}" AND fuel1 IS NOT NULL)
				UNION
				SELECT DISTINCT(fuel2) from powerplants
					WHERE (country="{0}" AND fuel2 IS NOT NULL)
				UNION
				SELECT DISTINCT(fuel3) from powerplants
					WHERE (country="{0}" AND fuel3 IS NOT NULL)
				UNION
				SELECT DISTINCT(fuel4) from powerplants
					WHERE (country="{0}" AND fuel4 IS NOT NULL)
				) AS temp'''.format(country)
	query = c.execute(stmt)
	summary['count_distinct_fuel'], = query.fetchone()

	# fuel-specific summaries
	fuel_list = pw.make_fuel_thesaurus().keys()
	for fuel in fuel_list:
		fuel_column_name = '_'.join(fuel.lower().split())
		stmt = '''SELECT COUNT(*) FROM powerplants
					WHERE (country=?
						AND (fuel1="{fuel}"
							OR fuel2="{fuel}"
							OR fuel3="{fuel}"
							OR fuel4="{fuel}"))'''.format(fuel=fuel)
		query = c.execute(stmt, (country,))
		summary['count_fuel_{0}'.format(fuel_column_name)], = query.fetchone()

		stmt = '''SELECT SUM(capacity_mw) FROM powerplants
					WHERE (country=?
						AND (fuel1="{fuel}"
							OR fuel2="{fuel}"
							OR fuel3="{fuel}"
							OR fuel4="{fuel}"))'''.format(fuel=fuel)
		query = c.execute(stmt, (country,))
		fuel_capacity_mw, = query.fetchone()
		summary_name = 'capacity_gw_fuel_{0}'.format(fuel_column_name)
		if fuel_capacity_mw is None:
			summary[summary_name] = 0
		else:
			summary[summary_name] = fuel_capacity_mw / 1000

	# count distinct fields
	count_distinct_list = ['name', 'owner', 'source']
	for field in count_distinct_list:
		stmt = '''SELECT COUNT(DISTINCT({field})) FROM powerplants
					WHERE (country=?
						AND {field} IS NOT NULL)'''.format(field=field)
		query = c.execute(stmt, (country,))
		summary['count_distinct_{0}'.format(field)], = query.fetchone()

	# count null fields
	count_null_list = ['name', 'pw_idnr',
			'capacity_mw', 'year_of_capacity_data',
			'owner', 'source', 'url', 'latitude', 'longitude']
	for field in count_null_list:
		stmt = '''SELECT COUNT(*) FROM powerplants
					WHERE (country=?
						AND {field} IS NULL)'''.format(field=field)
		query = c.execute(stmt, (country,))
		summary['count_null_{0}'.format(field)], = query.fetchone()

	# count null fuel occurrences
	stmt = '''SELECT COUNT(*) FROM powerplants
				WHERE (country=?
					AND fuel1 IS NULL
					AND fuel2 IS NULL
					AND fuel3 IS NULL
					AND fuel4 is NULL)'''
	query = c.execute(stmt, (country,))
	summary['count_null_fuel'], = query.fetchone()

	# count null generation data for all years
	stmt = '''SELECT COUNT(*) FROM powerplants
				WHERE (country=?
					AND generation_gwh_2012 IS NULL
					AND generation_gwh_2013 IS NULL
					AND generation_gwh_2014 IS NULL
					AND generation_gwh_2015 IS NULL
					AND generation_gwh_2016 IS NULL)'''
	query = c.execute(stmt, (country,))
	summary['count_null_generation_gwh_all'], = query.fetchone()

	# count null generation years
	for year in range(2012,2017):
		field = 'generation_gwh_{0}'.format(year)
		stmt = '''SELECT COUNT(*) FROM powerplants
					WHERE (country=?
						AND {field} IS NOT NULL)'''.format(field=field)
		query = c.execute(stmt, (country,))
		summary['count_{0}'.format(field)], = query.fetchone()

	return summary


### MAIN ###
if __name__ == '__main__':
	argparser = argparse.ArgumentParser(description="Summarize PowerWatch.")
	argparser.add_argument('-i', '--input', type=str, default=DEFAULT_DATABASE_FILE)
	argparser.add_argument('-o', '--output', type=str, default=DEFAULT_SUMMARY_FILE)
	argparser.add_argument('--country', type=str, nargs='+',
		help="ISO-3 country codes; all countries are processed by default.")
	args = argparser.parse_args()

	# prepare list of country codes
	countries = {v.iso_code: k for k, v in pw.make_country_dictionary().iteritems()}
	if args.country is None:
		args.country = sorted(countries.keys(), key=lambda k: countries[k])
	else:
		args.country = [country_name.upper() for country_name in args.country]
		for iso_code in args.country:
			if iso_code not in countries:
				raise ValueError('iso code <{0}> is invalid'.format(iso_code))

	# make sqlite database
	db_conn = pw.copy_csv_to_sqlite(args.input, ':memory:', return_connection=True)

	# summarize country-level data
	country_summaries = {}
	for iso_code in args.country:
		country_summaries[iso_code] = country_summary(db_conn, countries[iso_code], iso_code)

	# write summary output
	with open(args.output, 'wb') as fout:
		writer = csv.DictWriter(fout, fieldnames=summary_fieldnames())
		writer.writeheader()
		for iso_code in args.country:
			writer.writerow(country_summaries[iso_code])

