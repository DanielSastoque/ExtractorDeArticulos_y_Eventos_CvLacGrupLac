# -*- coding: utf-8 -*-

from config import URL, START, END

import pandas as pd
import re
import unicodedata

from BeautifulSoup import BeautifulSoup
import urllib2


##############----------------------- Información obtenida del GrupLac -----------------------##############

tables = pd.read_html(URL)                                  # Lista de todas las tablas html en la página del GrupLac
members_table = tables[5]                                   # Extrae la tabla de integrantes GrupLac


events_list = tables[36][1][1:]                             # Extrae la tabla de eventos GrupLac
total_events = len(events_list)
key_words = ["Congreso : ", "Otro : ", "Encuentro : ",
             u"Ámbito:", ", desde ",
             "Instituciones asociadas",
             "- hasta", u"Tipos de participación: "]        # Palabras para extraer información de cada evento

data = {"event_name":[], "event_date":[], "cv_url":[],
        "event_year":[], "event_scope":[]}                  # Almacen de información objetivo

for i, event in enumerate(events_list):
    fields = re.split("|".join(key_words), event)           # Separa los campos en cada evento
    event_name = fields[1]
    event_date = " - ".join([date.strip() for date in fields[2:4]])
    event_date = event_date.strip()
    event_scope = fields[4]
    event_year = int(event_date.split("-")[0])

    if "null" in event_scope:
        event_scope = "Internacional" if "International" in event_name  or "North American" in event_name \
                                      else "Nacional"

    # Alacenamiento de cada valor
    data["event_name"].append(event_name)
    data["event_date"].append(event_date)
    data["event_scope"].append(event_scope)
    data["event_year"].append(event_year)
    data["cv_url"].append(URL)

    print "Info evento en GrupLac: {} / {}".format(i, total_events)


########---------- Información obtenida del CvLac de cada integrante listado en el GrupLac ----------#######

def activty_interval(linkage):                              # Intervalo de tiempo en que el integrante participa
    start, end = linkage.split(" - ")
    start = int(start.split("/")[0])
    end = END if "Actual" in end else int(end.split("/")[0])

    start = max(start, START)
    end = min(end, END)

    return start, end

work_interval = map(activty_interval, members_table.loc[2:, 3])     # Intervalo de viculación para cada integrante
member = -1                                                         # Indice de integrante en la tabla GrupLac

html_GrupLac_page = urllib2.urlopen(URL)                    # Extrae html de la pagína GrupLac
soup = BeautifulSoup(html_GrupLac_page)

key_words = ["Nombre del evento:", "Tipo de evento: ", u"institución:",
             u"Ámbito: ", "Realizado el:"]                  # Palabras para extraer información de cada evento

hiperlinks = soup.findAll('a')
total_hiperlinks = len(hiperlinks)

for j, link in enumerate(hiperlinks):                       # Cada hiperviculo corresponde a un integrante
    cv_url = link.get('href')
    if "CurriculoCv" in cv_url:
        member += 1
        tables = pd.read_html(cv_url)                       # Extrae tablas html en el CvLac del investigador
        table_index = False
        for i, table in enumerate(tables):                  # Busca la tabla de eventos
            title = table.loc[0][0]
            if type(title) is unicode:
                title = unicodedata.normalize('NFKD', title).encode('ascii', 'ignore')
                if title == "Eventos cientificos":
                    table_index = True
                    break

        if table_index:                                     # ¿Se encontró tabla de eventos?
            events_list = tables[i][0]
        else:
            continue

        total_events = len(events_list)
        for i, event in enumerate(events_list):                     # Evalúa cada articulo encontrado en la tabla
            if type(event) is unicode or type(event) is str:
                if "Nombre del evento" in event:
                    fields = re.split("|".join(key_words), event)   # Separa los campos en cada evento

                    event_name = fields[1].strip()
                    event_date = " - ".join([date.replace("00:00:00.0", "").strip()
                                             for date in fields[4].split("en")[0].split(",")])
                    event_scope = fields[3]

                    if len(fields) < 6:                             # Contiene información de institución asociada?
                        continue
                    if not "UNIVERSIDAD DISTRITAL" in fields[5]:    # Es la universidad la institución asociada?
                        continue

                    if len(event_date) > 3:                         # Contiene el año del evento?
                        event_year = int(event_date.split("-")[0])
                    else:
                        continue

                    # Alacenamiento de cada valor, si el artículo se realizó cuando el integrante estaba viculado al grupo
                    if work_interval[member][0] <= event_year <= work_interval[member][1]:
                        data["event_name"].append(event_name)
                        data["event_date"].append(event_date)
                        data["event_scope"].append(event_scope)
                        data["event_year"].append(event_year)
                        data["cv_url"].append(cv_url)


                    print "Info artículo en CvLac hiperviculo: {} / {}. Artículo: {} / {}".format(j, total_hiperlinks,
                                                                                              i, total_events)


data = pd.DataFrame.from_dict(data)
data = data[(data.event_year >= START) & (data.event_year <= END)].sort_values('event_year',
                                                            ascending=False).reset_index(drop=True) # Ordena por año

data = data.drop_duplicates(["event_date"]).reset_index(drop=True)                                  # Elimina duplicados


########---------------------- Ajuste para cumplir el formato Unidad de investigaciones ----------------------#######

data = data[["event_name", "event_date", "event_scope", "cv_url"]]

writer = pd.ExcelWriter('Eventos.xlsx', engine='xlsxwriter')
data.to_excel(writer,'Eventos')
