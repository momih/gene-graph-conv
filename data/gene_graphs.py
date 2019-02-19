""" This file contains the wrapper around our gene interaction graph, which is essentially a big adjacency matrix"""

import csv
import numpy as np
import pandas as pd
import h5py
import networkx as nx
import academictorrents as at


class GeneInteractionGraph(object):
    """ This class manages the data pertaining to the relationships between genes.
        It has an nx_graph, and some helper functions.
    """
    def __init__(self, relabel_genes=True):
        self.load_data()
        if relabel_genes:
            self.relabel()

    def load_data(self):
        raise NotImplementedError

    def first_degree(self, gene):
        neighbors = set([gene])
        # If the node is not in the graph, we will just return that node
        try:
            neighbors = neighbors.union(set(self.nx_graph.neighbors(gene)))
        except Exception as e:
            #print(e)
            pass
        neighborhood = np.asarray(nx.to_numpy_matrix(self.nx_graph.subgraph(neighbors)))
        return neighbors, neighborhood

    def bfs_sample_neighbors(self, gene, num_neighbors, include_self=True):
        neighbors = nx.OrderedGraph()
        if include_self:
            neighbors.add_node(gene)
        bfs = nx.bfs_edges(self.nx_graph, gene)
        for u, v in bfs:
            if neighbors.number_of_nodes() == num_neighbors:
                break
            neighbors.add_node(v)

        for node in neighbors.nodes():
            for u, v, d in self.nx_graph.edges(node, data="weight"):
                if neighbors.has_node(u) and neighbors.has_node(v):
                    neighbors.add_weighted_edges_from([(u, v, d)])
        return neighbors

    def adj(self):
        return nx.to_numpy_matrix(self.nx_graph)

    def relabel(self):
        # This gene code map was generated on February 18th, 2019
        # at this URL: https://www.genenames.org/cgi-bin/download/custom?col=gd_app_sym&col=gd_prev_sym&status=Approved&status=Entry%20Withdrawn&hgnc_dbtag=on&order_by=gd_app_sym_sort&format=text&submit=submit
        # it enables us to map the gene names to the newest version of the gene labels
        with open('gene_code_map.txt') as csv_file:
            csv_reader = csv.reader(csv_file, delimiter='\t')
            line_count = 0
            x = {row[0]: row[1] for row in csv_reader}
            map = {}

            for key, val in x.items():
                for v in val.split(", "):
                    map[v] = key
            remapped_nx_graph = nx.relabel.relabel_nodes(self.nx_graph, map)
            self.nx_graph = remapped_nx_graph

class RegNetGraph(GeneInteractionGraph):
    def __init__(self, at_hash="e109e087a8fc8aec45bae3a74a193922ce27fc58", datastore=""):
        self.at_hash = at_hash
        self.datastore = datastore
        super(RegNetGraph, self).__init__()

    def load_data(self):
        self.nx_graph = nx.OrderedGraph(nx.readwrite.gpickle.read_gpickle(at.get(self.at_hash, datastore=self.datastore)))


class GeneManiaGraph(GeneInteractionGraph):
    def __init__(self, at_hash="5adbacb0b7ea663ac4a7758d39250a1bd28c5b40", datastore=""):
        self.at_hash = at_hash
        self.datastore = datastore
        super(GeneManiaGraph, self).__init__()

    def load_data(self):
        self.nx_graph = nx.OrderedGraph(nx.readwrite.gpickle.read_gpickle(at.get(self.at_hash, datastore=self.datastore)))


class EcoliEcocycGraph(GeneInteractionGraph):
    def __init__(self, path):  # data/ecocyc-21.5-pathways.col
        self.path = path
        super(EcoliEcocycGraph, self).__init__()

    def load_data(self):
        d = pd.read_csv(self.path, sep="\t", skiprows=40,header=None)
        d = d.set_index(0)
        del d[1]
        d = d.loc[:,:110] # filter gene ids

        # collect global names for nodes so all adj are aligned
        node_names = d.as_matrix().reshape(-1).astype(str)
        node_names = np.unique(node_names[node_names!= "nan"]) # nan removal

        #stores all subgraphs and their pathway names
        adjs = []
        adjs_name = []
        # for each pathway create a graph, add the edges and create a matrix
        for i, name in enumerate(d.index):
            G=nx.Graph()
            G.add_nodes_from(node_names)
            pathway_genes = np.unique(d.iloc[i].dropna().astype(str).as_matrix())
            for e1, e2 in itertools.product(pathway_genes, pathway_genes):
                G.add_edge(e1, e2)
            adj = nx.to_numpy_matrix(G)
            adjs.append(adj)
            adjs_name.append(name)

        #collapse all graphs to one graph
        adj = np.sum(adjs,axis=0)
        adj = np.clip(adj,0,1)

        self.adj = adj
        self.adjs = adjs
        self.adjs_name = adjs_name
