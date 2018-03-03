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


logger = logging.getLogger(__name__)

def convert(c, tables, ns):
    base = Namespace(ns)
    g = Graph()

    g.add((URIRef(base), RDF.type, VOID.Dataset))
    g.add((URIRef(base), RDFS.label, Literal(GRAPH_LABEL_NL, lang="nl")))
    g.add((URIRef(base), RDFS.comment, Literal(GRAPH_DESCRIPTION_NL, lang="nl")))

    if MAIN_TABLE in tables:
        logger.info("Converting {}".format(MAIN_TABLE))
        references = convert_main_table(c, MAIN_TABLE, g, base)

    tables.remove(MAIN_TABLE)
    for table in tables:
        logger.info("Converting {}".format(table))
        convert_secondary_table(c, table, g, base, references)

    return (g, GRAPH_LABEL_NL.replace(" ", "_"))

def convert_main_table(c, tablename, g, base):
    classname = CLASSNAME_MAP[tablename]

    classnode = URIRef(base+classname)
    g.add((classnode, RDF.type, RDFS.Class))
    g.add((classnode, RDFS.label, Literal(classname, lang="nl")))

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
            g.add((node, URIRef(base+field.lower()), Literal(value, datatype=datatype)))

    return references

def convert_secondary_table(c, tablename, g, base, references):
    classname = CLASSNAME_MAP[tablename]
    
    classnode = URIRef(base+classname)
    g.add((classnode, RDF.type, RDFS.Class))
    g.add((classnode, RDFS.label, Literal(classname, lang="nl")))
    backlink = URIRef(base+classname.lower())

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
            g.add((node, URIRef(base+field.lower()), Literal(value, datatype=datatype)))

