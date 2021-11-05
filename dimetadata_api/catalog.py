
import requests
import json
import urllib
import logging
from os.path import join
import yaml
from pprint import pprint
from rdflib import Graph, term
import re






#####################################
#  Tree utils  function
#  1. load_tree (load json formatted tree structure)
#  2. add_path_id_list  (flat list of all nodes including path: [root, root.node1,root.node2,..]
#  3. add_nodes (recursive function used in 2.
#####################################

# load tree from file
def load_tree(file) :
    with open(file) as f:
        tree = json.load(f)
    return tree

# compute path_id list for tree
def add_path_id_list(tree) :
    if 'nodes' in tree :
        tree['paths'] = {}
        add_nodes(paths = tree['paths'], parent_id ="", nodes = tree['nodes'])

# add identifier to each node to ease comparison
def add_nodes(paths, parent_id, nodes) :
    for n in nodes :
        n['path'] = parent_id+'.'+n['name'] if parent_id else n['name']
        paths[n['path']] = n
        if 'nodes' in n :
            add_nodes(paths, n['path'], n['nodes'])

# read availibility_rdf
def read_availibility_rdf(url) :
    g = Graph()
    g.parse(url)

    # Get file namespace
    ns_file = ''
    for ns_prefix, namespace in g.namespaces():
        if '' == ns_prefix:
            ns_file = namespace
            break

    root = ns_file[ns_file.rfind('/')+1:]
    qresult = g.query("SELECT  ?subj ?obj WHERE { ?subj skos:prefLabel  ?obj}")

    tree = {'name':None,'description':None,'nodes':[]}
    for r in qresult :
        m = re.sub(ns_file,'', r['subj'] )
        if m == ns_file :
            continue
        elif not m:
            tree['name'] = root
            tree['description'] = r['obj'].n3(g.namespace_manager).strip('<>').split('@')[0].strip('"')
        else :
            nr = {'name':m[1:],'description':r['obj'].value,'nodes':[]}
            tree['nodes'].append(nr)
    return tree

#  Util
def get_hierarchy_id(hierarchies, name) :
    '''
    Recursive
    :param hierarchies:
    :param name:
    :return:
    '''
    for h in hierarchies["tagHierarchies"] :
        if h['tagHierarchy']["hierarchyDescriptor"]["name"] == name :
            return h['tagHierarchy']["id"]
    return None

# check if new tags exist in hierarchy
# if yes add parent_id
def check_new_tags(hcontent,new_h_paths) :
    for c in hcontent :
        if c['tagInfo']['tag']['path'] in new_h_paths :
            new_h_paths[c['tagInfo']['tag']['path']]['id'] = c['tagInfo']['tag']['id']
        if len(c['children']) > 0 :
            check_new_tags(c['children'],new_h_paths)


######## GET #####################
#
# Get hierarchies without content/tags
#
def get_hierarchy_names(connection, search=None) :
    logging.info("Get Hierarchies")
    restapi = "/api/v1/catalog/tagHierarchies/"
    url = connection['url'] + restapi
    headers = {'X-Requested-With': 'XMLHttpRequest'}
    params = {"$search":search} if search else {}
    r = requests.get(url, headers=headers, auth=connection['auth'], params = params)

    response = json.loads(r.text)
    if r.status_code != 200:
        logging.error("Get hierarchies: {}".format(response['message']))

    return response

# API Call
# get tags of specified hierarchy with content/tags
#
def get_hierarchy_tags(connection, hierarchy_id) :

    restapi = f"/api/v1/catalog/tagHierarchies/{hierarchy_id}"
    url = connection['url'] + restapi
    params = {"hierarchyId":hierarchy_id,"withTags":True}
    headers = {'X-Requested-With': 'XMLHttpRequest'}

    r = requests.get(url, headers=headers, auth=connection['auth'],params=params)
    response = json.loads(r.text)

    if r.status_code != 200:
        logging.error(f"Get hierarchy: {response['message']}")

    return response


#
#  Get Tag ID - with download from
#  1. Load Hierarchies with tags with filter
#  2. Check if hierarchy exists selected by filter
#  3. Check if tag is unique (might exist in several hierarchies or branches
#  4. Crawl in hierarchies for searching matching tag
#
def get_tag_id(connection,tag_name, hierarchy_name = None,tag_path = None) :
    tag_id = None
    hierarchy_id = None
    hierarchies = get_hierarchy_names(connection, search=tag_name)
    # CASE: Not Found
    if hierarchies["count"] == 0 :
        logging.error("Tag not found: {}".format(tag_name))
        return tag_id, hierarchy_id
    # CASE: multiple matches in multiple hierarchies and hierarchy not specified
    if hierarchies["count"] > 1 and hierarchy_name == None:
        logging.error("Tag not unique: {}".format(hierarchies["count"]))
        return tag_id, hierarchy_id
    # CASE: hierarchy specified
    for ht in hierarchies['tagHierarchies'] :
        if ht['tagHierarchy']['hierarchyDescriptor']['name'] == hierarchy_name :
            hierarchy_id = ht["tagHierarchy"]["id"]
            if len(ht["matchInfo"]) > 1  and not tag_path :
                logging.error(f"Multiple tags in same hierarchy \'{hierarchy_name}\': {tag_name} ")
                return tag_id, hierarchy_id
            for mi in ht["matchInfo"] :
                if mi['tagPath'] == tag_path :
                    tag_id = mi['tagId']
                    return tag_id, hierarchy_id
    logging.error(f"Tag not found in specified hierarchy \'{hierarchy_name}\': {tag_name}")
    return tag_id, hierarchy_id

# tag from hierarchy, when hierarchy downloaded already
def get_tag_id_from_hierarchy(tags,name) :
    id = None
    for tag in tags :
        if tag['tagInfo']['tag']['name'] == name :
            id = tag['tagInfo']['tag']['id']
            break
        if len(tag['children']) > 0  :
            id = get_tag_id_from_hierarchy(tag['children'],name)
            if id :
                break
    return id



############# POST #############

#  API Call
#  Add hierarchy name
#
def add_hierarchy(connection, name, description) :
    logging.info(f"Add Hierarchy: {name}")

    restapi = "/api/v1/catalog/tagHierarchies"
    url = connection['url'] + restapi
    headers = {'X-Requested-With': 'XMLHttpRequest'}

    data = {"name": name, "description": description}

    r = requests.post(url, headers=headers, auth=connection['auth'], data=data)

    response = json.loads(r.text)
    if r.status_code != 201:
        logging.error(f"Adding hierarchy: {response['message']}")

    return r.status_code, response


# API Call
# adds tag to hierarchy by ids (hierarchy id and parent id)
#
def add_tag_by_id(connection,hierarchy_id,parent_id,name,description,color='black') :
    logging.info(f"Add tag by id: {name}")

    # Tag with no parentID is set as root tag
    if parent_id :
        data = {"parentId": parent_id, "name": name, "description": description, "color": color}
    else :
        data = {"name": name, "description": description, "color": 'black'}

    restapi = f"/api/v1/catalog/tagHierarchies/{hierarchy_id}/tags"
    url = connection['url'] + restapi
    headers = {'X-Requested-With': 'XMLHttpRequest'}

    r = requests.post(url,headers=headers, auth=connection['auth'],data=data)
    response = json.loads(r.text)
    if not r.status_code in [ 201, 400 ]  :
        logging.error(f"Adding tag status {r.status_code} - {response['message']}")
        raise ValueError(response['message'])

    return r.status_code, response

#
# Add tags tree
#
def add_tags(connection,hierarchy_id,parent_id,nodes) :
    for node in nodes :
        if not 'id' in node :
            status, resp = add_tag_by_id(connection,hierarchy_id,parent_id=parent_id,name=node['name'],description=node['description'])
            node['id'] = resp['id']
        if "nodes" in node :
            add_tags(connection,hierarchy_id,node["id"],node["nodes"])

####################
#  Upload Hierarchy
#  1. Get Hierarchies (w/o tags)              <- get_hierarchy_names
#  2. Get hierarchy by name <new_hierarchy>   <- get_hierarchy_id (no RestAPI
#  3. If hierarchy  (no tags) not exist then create a hierarchy  <- add_hierarchy
#  4. Get hierarchy with tags                 <- get_hierarchy_tags
#  5. Compare downloaded hierarchy with new hierarchy and add new tags (no deletion)  <- check_new_tags
#  6. Add complete new hierarchy              <- add_tags
def upload_hierarchy(connection,new_hierarchy) :
    hierarchies = get_hierarchy_names(connection)
    hierarchy_id = get_hierarchy_id(hierarchies, new_hierarchy['name'])
    if not hierarchy_id:
        status, response = add_hierarchy(connection,new_hierarchy['name'], new_hierarchy['description'])
        if not status == 201:
            raise Exception(f'Hierarchy could not be added: {response}')
        hierarchy_id = response['id']

    hierarchy = get_hierarchy_tags(connection=connection, hierarchy_id=hierarchy_id)
    check_new_tags(hierarchy['content'], new_hierarchy['paths'])
    add_tags(connection,hierarchy_id, "", new_hierarchy['nodes'])




# Add tag to dataset
def add_tag_dataset(connection,connection_id,qualified_name,hierarchy_id,tag_id) :

    qualified_name = urllib.parse.quote(qualified_name,safe='')
    restapi = f"/api/v1/catalog/connections/{connection_id}/datasets/{qualified_name}/tagHierarchies/{hierarchy_id}/tags"
    url = connection['url'] + restapi

    print(f"URL: {url}")
    headers = {'X-Requested-With': 'XMLHttpRequest'}
    data = {"tagId": tag_id}
    r = requests.post(url, headers=headers, auth=connection['auth'], data=data)

    response = json.loads(r.text)
    if r.status_code != 201:
        logging.error("Adding tag to dataset: {}".format(response['message']))

        logging.error(f"URL: {r.url}")

    return response

#########
# MAIN
########
if __name__ == '__main__' :

    logging.basicConfig(level=logging.DEBUG)

    with open('../config.yaml') as yamls:
        params = yaml.safe_load(yamls)

    conn = {'url':params['url'],
            'auth':(params['tenant']+'\\'+ params['user'],params['password'])}
    data_directory = '../data'

    UPLOAD = False
    if UPLOAD :
        # Catalogue from file
        hierarchy_status = load_tree(join(data_directory, 'status.json'))
        add_path_id_list(hierarchy_status)
        pprint('status.json: ')
        pprint(hierarchy_status)

        # Catalogue from RDF File
        hierarchy_availability = read_availibility_rdf('https://www.dcat-ap.de/def/plannedAvailability/1_0.rdf')
        add_path_id_list(hierarchy_availability)
        pprint(hierarchy_availability)

        upload_hierarchy(conn,hierarchy_status)
        upload_hierarchy(conn,hierarchy_availability)

    #upload_hierarchy(join(data_directory,'status.json'))
    #upload_hierarchy('/Users/Shared/data/dqm/availability.json')
    #upload_hierarchy('/Users/Shared/data/dqm/languages.json')

    DOWNLOAD_HIERARCHY = True
    if DOWNLOAD_HIERARCHY :
        hnames = get_hierarchy_names(conn, search='License')
        #print(json.dumps(hnames,indent= 4))
        hierarchy = get_hierarchy_tags(conn, hnames['tagHierarchies'][0]["tagHierarchy"]['id'])
        print(json.dumps(hierarchy,indent= 4))

    #tag_name = 'stable'
    #tag_id, _ = get_tag_id(tag_name =tag_name, hierarchy_name='availability')
    #tag_id, _ = get_tag_id(connection=conn,tag_name =tag_name, hierarchy_name='MetadataQuality',tag_path='stable')
    #tag_id, _ = get_tag_id(tag_name =tag_name)
    #print(f"Tag id \'{tag_name}\' : {tag_id}")
