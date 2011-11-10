import urllib2
import re
from collections import defaultdict

counties_26 = """Carlow
Dublin
Kildare
Kilkenny
Laois
Longford
Louth
Meath
Offaly
Westmeath
Wexford
Wicklow
Clare
Cork
Kerry
Limerick
Tipperary
Waterford
Galway
Leitrim
Mayo
Roscommon
Sligo
Cavan
Donegal
Monaghan""".split()

def parse_census_2011_table_8():
    # BeautifulSoup failed to read this soup, so just use a regex instead!
    res = urllib2.urlopen('http://www.cso.ie/census/Table8_files/sheet001.htm')
    content = res.read()
    trs = re.findall(re.compile('<tr[^>]*>\s*?<td[^>]*>([^<]*?)</td>\s*?<td[^>]*>([\d,\.-]*?)</td>\s*?<td[^>]*>([\d,\.-]*?)</td>\s*?<td[^>]*>([\d,\.-]*?)</td>\s*?<td[^>]*>([\d,\.-]*?)</td>\s*?<td[^>]*>([\d,\.-]*?)</td>\s*?<td[^>]*>([\d,\.-]*?)</td>\s*?</tr>', re.S), content)
    return trs
    
def normalize_census_name(name):
    if re.match('^\d\d\d\s', name):
        name = name[4:]
    name = name.split(',')[0].replace(' Urban', '').replace(' Rural', '').replace('(Part)', '')
    name = re.sub(' [A-Z]$', '', name) #  Beaumont A, Beaumont B
    name = re.sub(' No\. \d+$', '', name) #  Athy No. 1
    return name

def group_by_county_norm_name(trs):
    county_names = defaultdict(list)
    county = None
    for tr in trs:
        if not tr[0]:
            continue
        # Decision: Ignore Population of rural areas.
        if 'rural' in tr[0].lower():
            continue
        name, pop_2011 = re.sub('\s+', ' ', tr[0]), int(tr[2].replace(',', ''))
        county_ending = ',? Co\.? (.*)$'
        county_m = re.search(county_ending, name)
        if county_m:
            if county_m.groups()[0] != county:
                # Double check that current county matches suffix on name
                print county_m.groups()[0], county
            name = re.sub(county_ending, '', name)
        if re.match('^\d\d\d\s', name):
            # Decision: Ignore population of parts of cities
            if not name.endswith(' City'):
                county_names[(county, normalize_census_name(name))].append((name, pop_2011))
        else:
            if name in counties_26:
               county = name
            elif name in ['North Tipperary', 'South Tipperary']:
               county = 'Tipperary'
    return county_names

def verify_census(trs):
    mismatches = []
    totals = []
    prev_leaf = False
    for tr in trs:
        if not tr[0]:
	    continue
        name, pop_2011 = re.sub('\s+', ' ', tr[0]), int(tr[2].replace(',', ''))
        if re.match('^\d\d\d\s', name):
            totals[-1][-1] += pop_2011
	    prev_leaf = True
        else:
	    if prev_leaf:
	        prev_total = totals.pop(-1)
		if prev_total[1] != prev_total[2]:
		    mismatches.append(prev_total)
	        else:
                    if totals:
		        totals[-1][-1] += prev_total[1]
		prev_leaf = False
            totals.append([name, pop_2011, 0])
    if mismatches:
        print "Verify failed,", len(mismatches), "mismatches"

if __name__ == '__main__':
    trs = parse_census_2011_table_8()
    county_names = group_by_county_norm_name(trs)
    uniques = []
    for (county, norm_name), name_pops in county_names.items():
        if len(name_pops) == 1:
            # unique location name in a county
            # if there is only one osm node in the county with this norm_name,
            # should be confident to assign the population to the node
            census_name, population = name_pops[0]
            uniques.append((county, norm_name))
        else:
            # we probably have two locations with the same name in the county. No way of knowing which is which
            # todo: try to merge the various ['Beaumont A', 'Beaumont B', 'Beaumont C'] and total the population
            # but don't merge (hypothetical) ['Dundrum A', 'Dundrum B', 'Dundrum Rural']
            names = [np[0] for np in name_pops]
            total_pop = sum([np[1] for np in name_pops])
    print len(uniques), 'places ready to import'
                
