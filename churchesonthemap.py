#!/usr/bin/python

import logging

from rdflib import BNode, Literal, Graph, URIRef
from rdflib.namespace import Namespace, RDF, RDFS, VOID, XSD

from sqlite2rdf import content_of_table, schema_of_table

GRAPH_LABEL_NL = "Kerken op de kaart"
GRAPH_DESCRIPTION_NL = "Nederlandse kerken die tussen 1800 en 1970 gebouwd" +\
                       " zijn, verzamelt door Herman Wesselink tijdens zijn" +\
                       " promotietraject aan de Vrije Universiteit Amsterdam."
MAIN_TABLE = "01_Hoofdtabel_Kerken"
CLASSNAME_MAP = { "01_Hoofdtabel_Kerken": "Kerk",
                 "011_Naam_Kerk": "Naamgeving",
                 "012_Denominatie": "Denominatie",
                 "013_Architect": "Architect",
                 "014_Bronnen": "Bron" }
LOOKUP_LINK_MAP = { "01_Hoofdtabel_Kerken": 
                     { "huidige_bestemming": "Lookup_Huidige_bestemming",
                       "monumenten_status": "Lookup_Monumentenstatus",
                       "opmerkingen_stijl": "Lookup_School",
                       "stijl": "Lookup_Stijl",
                       "vorm_type": "Lookup_Vorm_type" },
                   "012_Denominatie":
                     { "denominatie": "Lookup_Denominatie" },
                   "014_Bronnen":
                     { "type_bron": "Lookup_Brontype" } }

logger = logging.getLogger(__name__)

def convert(c, tables, ns, lookup_map):
    base = Namespace(ns)
    g = Graph()

    g.add((URIRef(base), RDF.type, VOID.Dataset))
    g.add((URIRef(base), RDFS.label, Literal(GRAPH_LABEL_NL, lang="nl")))
    g.add((URIRef(base), RDFS.comment, Literal(GRAPH_DESCRIPTION_NL, lang="nl")))

    if MAIN_TABLE in tables:
        logger.info("Converting {}".format(MAIN_TABLE))
        references = convert_main_table(c, MAIN_TABLE, g, base, lookup_map)

    tables.remove(MAIN_TABLE)
    for table in tables:
        logger.info("Converting {}".format(table))
        convert_secondary_table(c, table, g, base, lookup_map, references)

    return (g, GRAPH_LABEL_NL.replace(" ", "_"))

def convert_main_table(c, tablename, g, base, lookup_map):
    classname = CLASSNAME_MAP[tablename]

    classnode = URIRef(base+classname)
    g.add((classnode, RDF.type, RDFS.Class))
    g.add((classnode, RDFS.label, Literal(classname, lang="nl")))

    lookup = None if tablename not in LOOKUP_LINK_MAP else LOOKUP_LINK_MAP[tablename]
    references = dict()
    schema = schema_of_table(c, tablename)
    for rec in content_of_table(c, tablename):
        node = URIRef(base + BNode().toPython())

        # store link for later references
        if 'ID' not in rec._fields:
            continue
        references[rec.ID] = node

        # add node to graph
        g.add((node, RDF.type, classnode))
        g.add((node, RDFS.label, Literal("{} {}".format(classname, rec.ID),
                                         datatype=XSD.string)))

        # add attributes to graph
        for idx, field in enumerate(rec._fields):
            datatype = XSD.anyType
            if schema[idx].type == "INTEGER":
                datatype = XSD.integer
            if schema[idx].type == "TEXT":
                datatype = XSD.string

            value = int(rec[idx]) if datatype is XSD.integer else rec[idx]
            if value is None:
                continue
            if lookup is not None and type(value) is str and field.lower() in lookup:
                lookup_table = lookup[field.lower()]
                if lookup_table in lookup_map:
                    if value.lower() in lookup_map[lookup_table]:
                        g.add((node, URIRef(base+field.lower()), lookup_map[lookup_table][value.lower()]))
                        continue
            g.add((node, URIRef(base+field.lower()), Literal(value, datatype=datatype)))

    return references

def convert_secondary_table(c, tablename, g, base, lookup_map, references):
    classname = CLASSNAME_MAP[tablename]
    
    classnode = URIRef(base+classname)
    g.add((classnode, RDF.type, RDFS.Class))
    g.add((classnode, RDFS.label, Literal(classname, lang="nl")))
    backlink = URIRef(base+classname.lower())

    lookup = None if tablename not in LOOKUP_LINK_MAP else LOOKUP_LINK_MAP[tablename]
    schema = schema_of_table(c, tablename)
    for refidx, rec in enumerate(content_of_table(c, tablename), 1):
        node = URIRef(base + BNode().toPython())

        # add node to graph
        g.add((node, RDF.type, classnode))
        g.add((node, RDFS.label, Literal("{} {}".format(classname, rec.ID),
                                         datatype=XSD.string)))

        # add backlink if in references
        if refidx in references:
            g.add((references[refidx], backlink, node))

        # add attributes to graph
        for idx, field in enumerate(rec._fields):
            datatype = XSD.anyType
            if schema[idx].type == "INTEGER":
                datatype = XSD.integer
            if schema[idx].type == "TEXT":
                datatype = XSD.string

            value = int(rec[idx]) if datatype is XSD.integer else rec[idx]
            if value is None:
                continue
            if lookup is not None and type(value) is str and field.lower() in lookup:
                lookup_table = lookup[field.lower()]
                if lookup_table in lookup_map:
                    if value.lower() in lookup_map[lookup_table]:
                        g.add((node, URIRef(base+field.lower()), lookup_map[lookup_table][value.lower()]))
                        continue
            g.add((node, URIRef(base+field.lower()), Literal(value, datatype=datatype)))

