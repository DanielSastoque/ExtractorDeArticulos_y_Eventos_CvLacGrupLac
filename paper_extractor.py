# -*- coding: utf-8 -*-

from config import URL, FIREFOX_EXE, START, END

import pandas as pd
import re
from selenium import webdriver

from BeautifulSoup import BeautifulSoup
import urllib2

from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.expected_conditions import staleness_of
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


##############----------------------- Información obtenida del GrupLac -----------------------##############

tables = pd.read_html(URL)                                  # Lista de todas las tablas html en la página del GrupLac
members_table = tables[5]                                   # Extrae la tabla de integrantes GrupLac


paper_list = tables[7][1][1:]                               # Extrae la tabla de artículos GrupLac
total_papers = len(paper_list)
key_words = ["Survey: ",
             "Publicado en revista especializada: ",
             "ISSN: ", "vol:", "fasc: ",
             "DOI:", "Autores: "]                           # Palabras para extraer información de cada artículo

data = {"paper_name":[], "journal_name":[],
        "ISSN":[], "year":[], "DOI":[],
        "authors":[], "doc_type":[]}                        # Almacen de información objetivo

for i, paper in enumerate(paper_list):
    paper = paper.replace(u"Revisión (Survey):", "Survey:") # Dificulad al tratar con parentesis y dos puntos
    fields = re.split("|".join(key_words), paper)           # Separa los campos en cada artículo

    # Extracción de cada valor
    paper_name, journal_name = fields[1].rsplit(',', 1)
    paper_name = paper_name.rsplit(' ', 1)[0]
    journal_name = journal_name.strip()
    ISSN, year = fields[2].split(", ")
    year = int(year)
    DOI = fields[5].strip()
    authors = fields[6]
    doc_type = "Revisión" if "Survey:" in paper else "Aplicado"

    # Alacenamiento de cada valor
    data["paper_name"].append(paper_name)
    data["journal_name"].append(journal_name)
    data["ISSN"].append(ISSN)
    data["year"].append(year)
    data["DOI"].append(DOI)
    data["authors"].append(authors)
    data["doc_type"].append(doc_type)

    print "Info artículo en GrupLac: {} / {}".format(i, total_papers)


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

key_words = ["En: ", "ed:", "DOI:", "ISSN:", "Palabras:"]   # Palabras para extraer información de cada artículo
stop_words = ["Unidos", "Bajos", "Unido"]                   # Países que se confunden con nombres de revista

hiperlinks = soup.findAll('a')
total_hiperlinks = len(hiperlinks)

for j, link in enumerate(hiperlinks):                       # Cada hiperviculo corresponde a un integrante
    cv_url = link.get('href')
    if "CurriculoCv" in cv_url:
        member += 1
        tables = pd.read_html(cv_url)                       # Extrae tablas html en el CvLac del investigador
        table_index = False
        for i, table in enumerate(tables):                  # Busca la tabla de artículos
            title = table.loc[0][0]
            if type(title) is unicode:
                if title == u"Artículos":
                    table_index = True
                    break

        if table_index:                                     # ¿Se encontró tabla de articulos?
            paper_list = tables[i][0]
        else:
            continue

        total_papers = len(paper_list)
        for i in range(2, len(paper_list), 2):              # Evalúa cada articulo encontrado den la tabla
            paper = paper_list[i]

            quotes_occ = [m.start() for m in re.finditer('"', paper)]   # Nombre de artículo entre comillas dobles
            paper_name = paper[quotes_occ[0]+1:quotes_occ[-1]]
            paper = paper.replace(paper_name, "")

            fields = re.split("|".join(key_words), paper)               # Separa los campos en cada artículo

            # Extracción de cada valor
            authors = fields[0]
            journal_name = fields[1].split(' ', 1)[1] + " - "
            first_word = journal_name.split()[0]
            journal_name = journal_name if first_word.strip() not in stop_words else journal_name.replace(first_word, "")
            ISSN = fields[2].strip()
            year = fields[3].split(",")[-2]
            year = int(year)
            DOI = fields[4].strip()
            doc_type = "Aplicado"

            # Alacenamiento de cada valor, si el artículo se realizó cuando el integrante estaba viculado al grupo
            if work_interval[member][0] <= year <= work_interval[member][1]:
                data["paper_name"].append(paper_name)
                data["journal_name"].append(journal_name)
                data["ISSN"].append(ISSN)
                data["year"].append(year)
                data["DOI"].append(DOI)
                data["authors"].append(authors)
                data["doc_type"].append(doc_type)


            print "Info artículo en CvLac hiperviculo: {} / {}. Artículo: {} / {}".format(j, total_hiperlinks,
                                                                                          i, total_papers)

data = pd.DataFrame.from_dict(data)
data = data[(data.year >= START) & (data.year <= END)].sort_values('year',
                                                                ascending=False).reset_index(drop=True) # Ordena por año

data.loc[:,"paper_name"] = data.paper_name.apply(lambda x: x.lower().strip())                   # Estandariza nombre
data = data.drop_duplicates(["paper_name"]).reset_index(drop=True)                              # Elimina duplicados

data["category"] = ""
data["quartile"] = ""
total_rows = data.shape[0]

########---------- Consulta de categoría y cuartil, en la base de datos Publindex y Scimago ----------#######

launch_browser = True
for index, row in data.iterrows():
    if launch_browser:
        browser = webdriver.Firefox(executable_path='gecko/geckodriver',
                                    firefox_binary=FIREFOX_EXE)                             # Instancia del navegador
        launch_browser = False                                          # Reinicia el navegador cada 20 consultas

    ISSN = row["ISSN"]
    year = row["year"]

    browser.get('http://scienti.colciencias.gov.co:8084/publindex/EnArticulo/busqueda.do')  # Consulta publindex

    issn_text_input = browser.find_element_by_name("nro_issn")                              # Consulta por ISSN
    issn_text_input.send_keys(ISSN)
    issn_text_input.send_keys(Keys.ENTER)


    WebDriverWait(browser, 1E6).until(
        EC.visibility_of_element_located((By.CLASS_NAME, "sepCell")))       # Busca detalles de la revista

    if browser.find_element_by_class_name("sepCell").text == "Detalles":    # Revisa historial categorias Publindex

        browser.find_element_by_class_name("sepCell").send_keys(Keys.ENTER)

        old_page = browser.find_element_by_tag_name('html')                 # Espera a cargar detalles
        WebDriverWait(browser, 10).until(staleness_of(old_page))

        search_out_url = browser.current_url                                # Obtiene url con el historial de categorias

        tables = pd.read_html(search_out_url)
        publindex_cat = tables[1]                                           # Tabla con categorias
        publindex_cat.columns = range(publindex_cat.shape[1])
        IBN_col = [1 if int(IBN_year.split(" - ")[1]) <= year else 0 for IBN_year in publindex_cat.loc[:, 1].dropna()]
        Vig_col = [1 if int(Vig_year.split(" ")[-1]) >= year else 0 for Vig_year in publindex_cat.loc[:, 3].dropna()]
        category_index = [a * b for a,b in zip(IBN_col, Vig_col)]
        if len(category_index) > 0:                                         # Se tienen registros?
            if 1 in category_index:                                         # Se clasificó en el año en cuestión?
                category = publindex_cat.loc[category_index.index(1), 2]    # Categoria según IBN y vigencia
            else:
                category = ""
        else:
            category = ""

        data.loc[index, "category"] = category


    browser.get('https://www.scimagojr.com/journalsearch.php?q={}'.format(ISSN))    # Consulta Scimago por ISSN
    if not ("Sorry, no results were found." in browser.page_source):
        try:
            browser.find_element_by_css_selector("div.search_results > a").send_keys(Keys.ENTER)
        except:
            continue

        old_page = browser.find_element_by_tag_name('html')                 # Espera a cargar detalles
        WebDriverWait(browser, 10).until(staleness_of(old_page))

        search_out_url = browser.current_url                                # Obtiene url con historico de cuartil

        tables = pd.read_html(search_out_url)
        if "Quartile" in tables[1].columns:                                 # Se tienen registros?
            quartile = tables[1][tables[1]["Year"] == int(year)]["Quartile"].real
            quartile = quartile[0] if len(quartile) > 0 else ""
        else:
            quartile = ""

        data.loc[index, "quartile"] = quartile

    if index % 20 == 19:                                                    # Reinicia el navegador cada 20 consultas
        launch_browser = True                                               # evita bug de memoría de selenium
        browser.close()

    print "Consulta Publindex / Scimago: {} / {}".format(index, total_rows)


########---------------------- Ajuste para cumplir el formato Unidad de investigaciones ----------------------#######

ui_columns = ["Nombre A", "Nombre R", "ISSN", "A Public",
              "A1", "A2", "B", "C", "Q",
              "Q1", "Q2", "Q3", "Q4", "N.I",
              "DOI", "Autores", "Tipo"]
data_formated = pd.DataFrame("", index=range(data.shape[0]), columns=ui_columns)

for index, row in data.iterrows():
    data_formated.loc[index, "Nombre A"] = row["paper_name"]
    data_formated.loc[index, "Nombre R"] = row["journal_name"]
    data_formated.loc[index, "ISSN"] = row["ISSN"]
    data_formated.loc[index, "A Public"] = row["year"]
    data_formated.loc[index, row["category"]] = "X"
    data_formated.loc[index, row["quartile"]] = "X"

    if row["quartile"]=="" and row["category"]=="":
        data_formated.loc[index, "N.I"] = "X"

    data_formated.loc[index, "DOI"] = row["DOI"]
    data_formated.loc[index, "Autores"] = row["authors"]
    data_formated.loc[index, "Tipo"] = row["doc_type"]


writer = pd.ExcelWriter('Articulos.xlsx', engine='xlsxwriter')
data_formated.to_excel(writer,'Articulos')
