#!/usr/bin/python

from argparse import ArgumentParser
from collections import namedtuple  
from datetime import datetime
import logging
import sqlite3

from rdflib import BNode, Literal, Graph, URIRef
from rdflib.namespace import Namespace, RDF, RDFS, SKOS, XSD

import churchesonthemap as domain


def run(args, time):
    graphs = convert(sqlite3.connect(args.input), Namespace(args.namespace))
    for graph, name in graphs:
        graph.serialize(destination=args.output_path+name+ext_of(args.serialization_format),\
                        format=args.serialization_format)

def convert(conn, ns):
    c = conn.cursor()
    graphs = []

    tables = table_list(c)
    lookup_tables = {table for table in tables if table.startswith('Lookup_')}

    lookup_map = {}
    for table in lookup_tables:
        logger.info("Converting {}".format(table))
        graphs.append(skosify_table(c, table, ns, lookup_map))
    tables.difference_update(lookup_tables)

    graphs.append(domain.convert(c, tables, ns, lookup_map))

    return graphs

def skosify_table(c, tablename, ns, lookup_map):
    table_map = {}
    base = Namespace(ns + 'vocab/')
    g = Graph()

    root = URIRef(base + BNode().toPython())
    g.add((root, RDF.type, SKOS.ConceptScheme))
    g.add((root, RDFS.label, Literal(tablename, datatype=XSD.string)))
    g.add((root, SKOS.prefLabel, Literal(tablename, datatype=XSD.string)))

    for rec in content_of_table(c, tablename):
        # assume one string attribute only
        node = URIRef(base + BNode().toPython())
        g.add((node, RDF.type, SKOS.Concept))
        g.add((node, RDFS.label, Literal(rec[0].title(), datatype=XSD.string)))
        g.add((node, SKOS.inScheme, root))
        g.add((node, SKOS.prefLabel, Literal(rec[0].title(), datatype=XSD.string)))
    
        table_map[rec[0].lower()] = node

    lookup_map[tablename] = table_map

    return (g, tablename)
        
def table_list(c):
    return {e[0] for e in c.execute("SELECT name FROM sqlite_master WHERE type='table';")}

def content_of_table(c, tablename=''):
    Record = namedtuple('Record', [e.name for e in schema_of_table(c, tablename)])
    return [Record(*e) for e in c.execute("SELECT * FROM '{}'".format(tablename))]

def schema_of_table(c, tablename=''):
    Attribute = namedtuple('Attribute', ['name', 'type'])
    return [Attribute(e[1].replace('-','_'), e[2]) for e in c.execute("PRAGMA table_info('{}')".format(tablename))]

def print_header():
    header = 'SQLite to RDF translator'
    print(header)

def set_logging(args, time):
    logfile = "{}{}.log".format(args.logdir, time) if args.logdir.endswith("/")\
            else "{}/{}.log".format(args.logdir, time)
    logging.basicConfig(filename=logfile,
                        format='%(asctime)s %(levelname)s: %(message)s',
                        level=logging.INFO)

    if args.verbose:
        logging.getLogger().addHandler(logging.StreamHandler())

def ext_of(format):
    if format == 'n3':
        return '.n3'
    elif format == 'nquads':
        return '.nq'
    elif format == 'ntriples':
        return '.nt'
    elif format == 'pretty-xml':
        return '.xml'
    elif format == 'trig':
        return '.trig'
    elif format == 'trix':
        return '.trix'
    elif format == 'turtle':
        return '.ttl'
    elif format == 'xml':
        return '.xml'
    else:
        return '.rdf'

if __name__ == "__main__":
    time = datetime.now().isoformat()

    parser = ArgumentParser()
    parser.add_argument("-f", "--serialization_format", help="serialization format of output",\
                        choices=["n3", "nquads", "ntriples", "pretty-xml", "trig", "trix", "turtle", "xml"], default='turtle')
    parser.add_argument("-i", "--input", help="Input file", default=None)
    parser.add_argument("-o", "--output_path", help="Output path", default="./")
    parser.add_argument("-v", "--verbose", help="Increase output verbosity", action="store_true")
    parser.add_argument("--logdir", help="Path to store logs at", default="./")
    parser.add_argument("--namespace", help="Base namespace of graph", default="http://rdf.example.org/")
    args = parser.parse_args()
    
    set_logging(args, time)
    logger = logging.getLogger(__name__)
    logger.info("Arguments:\n{}".format(
        "\n".join(["\t{}: {}".format(arg,getattr(args, arg)) for arg in vars(args)])))

    print_header()
    run(args, time)

    logging.shutdown()
