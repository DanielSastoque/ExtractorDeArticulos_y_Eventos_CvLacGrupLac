# ExtractorDeArticulos_y_Eventos_CvLacGrupLac

Este repositorio contiene tres Python scripts:
- config.py: Archivo de configuración.
- paper_extractor.py: Extractor de artículos.
- conference_extrator.py: Extractor de eventos.

En el archivo de configuración se debe indicar:
- Ubicación del ejecutable del navegador web Firefox.
- URL del GrupLac correspondiente al grupo de investigación que se quiere analizar.
- Intervalo de fechas sobre el que se va a realizar la extracción.

En general, el procedimiento es el siguiente:

Se obtiene el listado de artículos publicados en la página GrupLac del grupo. A partir del listado de integrantes (la cual contiene las url a cada CvLac), que aparece también en el GrupLac, se obtiene el listado de artículos para cada uno; a partir de cada CvLac. Se elimina la información duplicada, y, a través del intervalo de vinculación de cada integrante, se decide que artículos se excluyen del listado. Se procede de la misma forma con la información de los eventos.

Una vez está definido el listado de artículos, se usa el ISSN de cada uno para consultar, la clasificación y el cuartil correspondiente, en Publindex y en Scimago. Esto se hace a través de Web scraping.

Cada Script de extracción, genera un documento .xlsx con los datos recolectados.

Aclaración:
- Este software ha sido probado únicamente con el GrupLac del grupo LAMIC de la Universidad Distrital Francisco José de Caldas. Sin
embargo, no hay nada que impida el buen funcionamiento del programa con otros GrupLac.
- Este software ha sido probado únicamente en Debian Jessie AMD64.
- Se recomienda el uso de VirtualEnv, instalando los requerimientos listados en el archivo: requirements.txt
