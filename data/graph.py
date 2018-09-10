import numpy as np
import h5py
import random
import logging
import networkx as nx
import gene_datasets
import pandas as pd
import itertools
import academictorrents as at


class Graph(object):
    def __init__(self):
        pass

    def intersection_with(self, dataset):
        # Drop duplicate columns in dataset.def


        l = dataset.df.columns.tolist()
        duplicates = set([x for x in l if l.count(x) > 1])
        for dup in duplicates:
            l.remove(dup)
        dataset.df = dataset.df.groupby(lambda x:x, axis=1).mean()
        dataset.df = dataset.df[l]
        dataset.node_names = dataset.df.columns.tolist()
        dataset.data = dataset.df.as_matrix()

        # find intersection with graph
    	intersection = np.intersect1d(self.node_names, dataset.df.columns.tolist())

        # filter rows/columns in graph that aren't in dataset
        self.df = self.df[intersection].filter(items=intersection, axis='index')

        #add zero'd columns/rows to graph for genes present only in dataset
    	diff = np.setdiff1d(dataset.node_names, intersection)
    	zeros = pd.DataFrame(0, index=diff.tolist(), columns=diff.tolist())
        self.df = pd.concat([self.df, zeros]).fillna(0.)
        self.df = self.df[l].loc[l]

        self.adj = self.df.as_matrix()

    def load_random_adjacency(self, nb_nodes, approx_nb_edges, scale_free=True):
        nodes = np.arange(nb_nodes)

        # roughly nb_edges edges (sorry, it's not exact, but heh)
        if scale_free:
            # Read: https://en.wikipedia.org/wiki/Scale-free_network
            # There is a bunch of bells and swittle, but after a few handwavy tests, the defaults parameters seems okay.
            edges = np.array(nx.scale_free_graph(nb_nodes).edges())
        else:
            edges = np.array([(i, ((((i + np.random.randint(nb_nodes - 1)) % nb_nodes) + 1) % nb_nodes))
                             for i in [np.random.randint(nb_nodes) for i in range(approx_nb_edges)]])

        # Adding self loop.
        edges = np.concatenate((edges, np.array([(i, i) for i in nodes])))

        # adjacent matrix
        A = np.zeros((nb_nodes, nb_nodes))
        A[edges[:, 0], edges[:, 1]] = 1.
        A[edges[:, 1], edges[:, 0]] = 1.
        self.adj = A
        self.df = pd.DataFrame(np.array(self.adj))
        self.node_names = list(range(nb_nodes))

    def load_graph(self, path):
        f = h5py.File(at.get(path))
        self.adj = np.array(f['graph_data']).astype('float32')
        self.node_names = np.array(f['gene_names'])
        self.df = pd.DataFrame(np.array(self.adj))
        self.df.columns = self.node_names
        self.df.index = self.node_names

    def build_correlation_graph(self, dataset, threshold=0.2):
        corr = np.corrcoef(dataset, rowvar=False)
        corr = np.nan_to_num(corr)
        corr = (np.abs(corr) > threshold).astype(float)
        print "The correlation graph has {} average neighbours".format((corr > 0.).sum(0).mean())

        self.adj = corr
        self.df = pd.DataFrame(np.array(self.adj))
        self.node_names = list(range(self.adj.shape[0]))


    def add_master_nodes(self, nb_master_nodes):
        if nb_master_nodes > 0:
            master = pd.DataFrame(1., index=['master_{}'.format(i) for i in range(nb_master_nodes)], columns=['master_{}'.format(i) for i in range(nb_master_nodes)])
            self.df = pd.concat([self.df, master]).fillna(1,)
            self.node_names = self.df.columns
        self.adj = self.df.as_matrix()


def get_hash(graph):
    if graph == "regnet":
        return "3c8ac6e7ab6fbf962cedb77192177c58b7518b23"
    elif graph == "genemania":
        return "ae2691e4f4f068d32f83797b224eb854b27bd3ee"
