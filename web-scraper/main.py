"""
Author: Carlos Climent
Created on: 10/06/2021
Last update: 10/06/2021
"""

from os import uname
from bs4 import BeautifulSoup
import bs4
import requests
import pandas as pd
import json

URL_BASE = "https://www.redpiso.es/"


def get_city_urls(s, URL_BASE):
    """
    inputs:
        s: Session object
        URL_BASE: home url
    returns:
        a list where each element contains the url for a particular city
    """
    response = s.get(URL_BASE)
    urls_list = []
    cities_list = []
    soup = BeautifulSoup(response.content, 'lxml')
    for option in soup.find('select', {'id': 'prv'}):
        if type(option) is not bs4.element.NavigableString:
            urls_list.append(f"{URL_BASE}venta-viviendas/{option['value']}")
            cities_list.append(option['value'])
    return urls_list, cities_list


def get_flat_urls(s, URL_CITY, flat_urls):
    """
    inputs:
        s: Session object
        URL_CITY: URL for a given city
    returns:
        a list of all the add urls in that given city url
    """
    response = s.get(URL_CITY)
    soup = BeautifulSoup(response.content, 'lxml')
    adds = soup.find_all('a', {'class': 'item-link'})

    if adds == []:
        return flat_urls

    else:
        for add in adds:
            flat_urls.append(add["href"])
        
        if 'pagina' in URL_CITY:
            url_to_list = URL_CITY.split('-')
            NEW_URL_CITY = '-'.join(url_to_list[:-1]) + '-' +str(int(url_to_list[-1]) + 1)
        else:
                NEW_URL_CITY = URL_CITY + '/pagina-2'
        return get_flat_urls(s, NEW_URL_CITY, flat_urls)


def scrape_add(s, URL_FLAT, city):
    """
    inputs:
        s: Session object
        URL_FLAT: URL for a given add
    returns:
        json object with the required fields
    """
    response = s.get(URL_FLAT)
    soup = BeautifulSoup(response.content, 'lxml')

    #unique identifier
    unique_id = soup.find('div', {'class': 'property-reference'}).find('p').text
    unique_id_clean = unique_id.replace("REF: ", "")

    #offer price
    offer_price = soup.find('div', {'class': 'property-contact-item'}).find('h2').text
    try:
        offer_price_clean = float(offer_price.replace(" €", "").replace(".", ""))
    except ValueError:
        offer_price_clean = offer_price
    #coordinates
    try:
        coordinates = soup.find('img', {'class': 'img-property-map'})['src']
        start = coordinates.find("center=")
        coordinates = coordinates[start + len('center=') : start + len('center=') + 19]
        coordinates_list = coordinates.split(',')
        coordinates_clean = {
            "latitude": float(coordinates_list[0].replace('&', '')),
            "longitude": float(coordinates_list[1].replace('&', ''))
        }
    except:
        coordinates_clean = {
            "latitude": None,
            "longitude": None
        }


    #property feature items (including real state surface and antiquity)
    property_feature_items = soup.find_all('div', {'class': 'col-lg-3 col-md-4 col-sm-6 property-features-item'})
    rest_of_features = []

    antiquity_clean = None
    real_state_surface_clean = None
    for item in property_feature_items:
        if "Metros:" in item.text:
            real_state_surface = item.text
            real_state_surface_clean = float(real_state_surface.replace("Metros: ", "")[3:-4])
        elif "Año de" in item.text:
            antiquity_clean = item.text[-5:-1]
        else:
            rest_of_features.append(item.text.replace("\n", "").strip())

    #publication date
    publication_date = soup.find_all('span', {'class': 'property-visits'})[1].text
    publication_date_clean = publication_date.strip()

    #description
    try:
        description = soup.find('div', {'class': 'col-md-6'}).find('p').text
    except:
        description = None

    data = {
        'id': unique_id_clean,
        'offer_price': offer_price_clean,
        'city': city,
        'coordinates': coordinates_clean,
        'real_state_surface': real_state_surface_clean,
        'antiquity': antiquity_clean,
        'publication_date': publication_date_clean,
        'description': description,
        'avaliable_features': rest_of_features
    }
    return data


if __name__ == '__main__':
    # ESTABLISH A SESSION
    s = requests.Session()

    # GET CITY URLS
    city_urls_list, cities_urls_list = get_city_urls(s, URL_BASE)

    # GET FLAT URLS INTO A DICT
    print('\nGetting all URLS...')
    flat_urls = {}
    for city_url, city in zip(city_urls_list, cities_urls_list):
        print(f'City: {city}')
        flat_urls[city] = get_flat_urls(s, city_url, [])
    print("########################")
    #remove: flat_urls_list = get_flat_urls(s, city_urls_list[1])

    # SCRAPE A GIVEN FLAT

    # LOOP TO GET ALL FLATS
    print('\nGetting all flats')
    scrapped_data = []
    for key in flat_urls.keys():
        print(f'Scraping city {key}, with {len(flat_urls[key])} total flats')
        for url in flat_urls[key]:
            scrapped_data.append(scrape_add(s, url, key))
    
    #remove scrapped_flat = scrape_add(s, flat_urls_list[0])

    # OUTPUT RESULTS
    with open("data.json", "w", encoding='utf8') as file:
        json.dump(scrapped_data, file, indent=4, ensure_ascii=False)

