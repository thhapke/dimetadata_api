
import logging
import re

import yaml
from rdflib import Graph, term


logging.basicConfig(level=logging.INFO)

lang_pattern = re.compile(r"\".+\"@(\w{2})")

################## Utils ##################

def parseRDF(file) :
    g = Graph()
    g.parse(file)
    #print(g.serialize(format="turtle"))
    return g

with open('config.yaml') as yamls:
    params = yaml.safe_load(yamls)


url_dcat2 = "https://www.w3.org/ns/dcat2.ttl"
metadata_file = './data/dcat2.ttl'
metadata = parseRDF(url_dcat2)
#print(metadata.serialize(format="turtle"))

dcat_ns = 'http://www.w3.org/ns/dcat#'
prefix = f"PREFIX dcat: <{dcat_ns}> "
select = "SELECT DISTINCT ?var1 ?var2 ?var3 "
filter = f"FILTER(STRSTARTS(STR(?property), \"{dcat_ns}\"))"

q_class = prefix + select + "WHERE { ?p a ?var}. " + filter
#q_prop = prefix + select +"WHERE { ?q1 ?var ?q0 . "+ filter +"}"
q_prop = prefix + select +"WHERE { ?var1 ?r1 ?var2. ?var2 ?r2 ?var3}"

query_att = prefix + "SELECT ?pred ?var " +"WHERE { dcat:dataset ?pred ?var}"
query = prefix + "SELECT ?var ?pred " +"WHERE { ?var ?pred dcat:Dataset}"
query = prefix + "SELECT ?var ?pred " +"WHERE { ?var ?pred rdfs:Class}"
query = prefix + "SELECT ?var ?pred " +"WHERE { ?var ?pred rdf:Property}"

print(f"SPARQL: {query}")

qresult = metadata.query(query)
rlist = []
for rs in qresult:
    rrec = { label:dict() for label in rs.labels}
    rrec['lang'] = list()
    for label in rs.labels :
        if not rs[label] :
            rrec[label]['type'] = None
        elif isinstance(rs[label] ,term.BNode) :
            rrec[label]['type'] = 'bnode'
        elif isinstance(rs[label] ,term.Literal) :
            rrec[label]['type'] = 'literal'
            rrec[label]['lang'] = rs[label].language
            rrec[label]['value'] = rs[label].value
            rrec['lang'].append(rs[label].language)
        elif isinstance(rs[label] ,term.URIRef) :
            rrec[label]['type'] = 'uriref'
            #rrec[label]['lang'] = rs[label].language
            rrec[label]['value'] = rs[label].n3(metadata.namespace_manager).strip('<>')
            #rrec['lang'].append(rs[label].language)
        else :
            rrec[label]['type'] = 'notused'
    rlist.append(rrec)
    if len(rrec['lang']) >1 :
        logging.warning(f'More than one language in result: {rrec} ')
    if len(rrec['lang']) ==0 or rrec['lang'][0] == 'en':
        print(rrec)



