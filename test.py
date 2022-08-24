import pprint
from research import search_scopus
from podcasts import search_podcasts
from videos import search_youtube
from books import search_googlebooks
from tedtalks import search_ted

pp = pprint.PrettyPrinter(depth=6)
results = search_podcasts(search_term="gene", limit=2)
pp.pprint(results) 
results = search_scopus(search_term="gene", limit=2)
pp.pprint(results) 
results = search_youtube(search_term="solar power", limit=2, country="IN")
pp.pprint(results) 
results = search_youtube(search_term="solar power", limit=2)
pp.pprint(results) 
results = search_googlebooks(search_term="hadron collider", limit=2)
pp.pprint(results) 
results = search_ted(search_term="solar", limit=2)
pp.pprint(results) 