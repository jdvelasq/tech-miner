"""
TechMiner.RecordsDataFrame
==================================================================================================



"""
import pandas as pd
import math
import numpy as np
from sklearn.decomposition import PCA
from techminer.common import cut_text
from techminer.result import Result
import matplotlib.pyplot as plt
import networkx as nx
from collections import OrderedDict 
from mpl_toolkits.axes_grid1 import make_axes_locatable
from scipy.optimize import minimize
from shapely.geometry import Point, LineString
import matplotlib.colors as colors
import matplotlib.cm as cm


#---------------------------------------------------------------------------------------------
def _minmax(data, minmax):
    """Selectet records among (minval, maxval) = minmax.

    Arguments:
        data : df

    Returns:
        techminer.


    """ 
    if minmax is None:
        return data
    minval, maxval = minmax
    data = data[ data[data.columns[-1]] >= minval ]
    data = data[ data[data.columns[-1]] <= maxval ]
    return data


#------------------------------------------------------------------------------------------------------------
def _expand_column(data, column, sep):

    if sep is None:
        return data

    data[column] = data[column].map(lambda x: x.split(sep) if x is not None else None)
    data[column] = data[column].map(
        lambda x: [z.strip() for z in x] if isinstance(x, list) else x
    )
    data = data.explode(column)
    data.index = range(len(data))
    return data



#---------------------------------------------------------------------------------------------
class RecordsDataFrame(pd.DataFrame):
    """Class to represent a dataframe of bibliographic records.
    """

    #----------------------------------------------------------------------------------------------
    @property
    def _constructor_expanddim(self):
        return self
    
    #----------------------------------------------------------------------------------------------
    def _add_documents_by_terms_to_label(self, result, column, sep):

        count = self.documents_by_terms(column, sep)
        count = {key : value for key, value in zip(count[count.columns[0]], count[count.columns[1]])}
        result[column] = result[column].map(lambda x: cut_text(str(x) + ' [' + str(count[x]) + ']'))
        return result

    #----------------------------------------------------------------------------------------------
    def _years_list(self):

        df = self[['Year']].copy()
        df['Year'] = df['Year'].map(lambda x: None if np.isnan(x) else x)
        df = df.dropna()
        df['Year'] = df['Year'].map(int)
        minyear = min(df.Year)
        maxyear = max(df.Year)
        return pd.Series(0, index=range(minyear, maxyear+1), name='Year')

    #----------------------------------------------------------------------------------------------
    def _aduna_map(self, column, sep=None, top_n=None, figsize=(12,10), font_size=10):
        """
        """
        # computes the number of documents by term
        tdf_matrix = self.tdf(column, sep, top_n)        
        tdf_matrix.columns = [cut_text(w) for w in tdf_matrix.columns]

        ## figure properties
        plt.figure(figsize=figsize)

        ## graph
        graph = nx.Graph()

        ## adds nodes to graph
        terms = list(set(tdf_matrix.columns.tolist()))
        docs = [str(i) for i in range(len(tdf_matrix.index.tolist()))]
        
        graph.add_nodes_from(terms)
        graph.add_nodes_from(docs)

        for col in terms:
            for idx in tdf_matrix.index:

                if tdf_matrix.at[idx, col] > 0:
                    graph.add_edge(col, str(idx)) 

        ## graph layout
        path_length = nx.shortest_path_length(graph)
        distances = pd.DataFrame(index=graph.nodes(), columns=graph.nodes())
        for row, data in path_length:
            for col, dist in data.items():
                distances.loc[row,col] = dist
        distances = distances.fillna(distances.max().max())
        layout = nx.kamada_kawai_layout(graph, dist=distances.to_dict())

        ## draw terms nodes
        nx.draw_networkx_nodes(
            graph, 
            layout, 
            nodelist=terms, 
            node_size=300,
            node_color='red')

        nx.draw_networkx_nodes(
            graph, 
            layout, 
            nodelist=docs, 
            node_size=200,
            edgecolors='black',
            node_color='lightgray') 

        x_left, x_right = plt.xlim()
        y_left, y_right = plt.ylim()
        delta_x = (x_right - x_left) * 0.01
        delta_y = (y_right - y_left) * 0.01
        # for node in terms:
        #     x_pos, y_pos = layout[node]
        #     plt.text(
        #         x_pos + delta_x, 
        #         y_pos + delta_y, 
        #         node, 
        #         size=font_size,
        #         ha='left',
        #         va='bottom',
        #         bbox=dict(
        #             boxstyle="square",
        #             ec='gray',
        #             fc='white',
        #             ))

        ## edges
        nx.draw_networkx_edges(
            graph, 
            layout,
            width=1
        )

        plt.axis('off')

    #----------------------------------------------------------------------------------------------
    def auto_corr(self, column, sep=None, top_n=20, cut_value=0):
        """Computes the autocorrelation among items in a column of the dataframe.

        >>> from techminer.datasets import load_test_cleaned
        >>> rdf = load_test_cleaned().data
        >>> rdf.auto_corr(column='Authors', sep=',', top_n=5) # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
               Authors (row)     Authors (col)  Autocorrelation                                                ID
        0        Wang J. [7]       Wang J. [7]              1.0  [[*3*], [*10*], [*15*], [*80*], [*87*], [*128*]]
        1       Zhang G. [4]      Zhang G. [4]              1.0                [[*27*], [*78*], [*117*], [*119*]]
        2   Hernandez G. [3]  Hernandez G. [3]              1.0                         [[*52*], [*94*], [*100*]]
        3         Yan X. [3]        Yan X. [3]              1.0                          [[*13*], [*44*], [*85*]]
        4       Tefas A. [3]      Tefas A. [3]              1.0                         [[*8*], [*110*], [*114*]]
        5   Hernandez G. [3]       Wang J. [7]              0.0                                              None
        6       Tefas A. [3]  Hernandez G. [3]              0.0                                              None
        7       Tefas A. [3]        Yan X. [3]              0.0                                              None
        8       Tefas A. [3]      Zhang G. [4]              0.0                                              None
        9       Tefas A. [3]       Wang J. [7]              0.0                                              None
        10  Hernandez G. [3]      Tefas A. [3]              0.0                                              None
        11       Wang J. [7]        Yan X. [3]              0.0                                              None
        12  Hernandez G. [3]        Yan X. [3]              0.0                                              None
        13  Hernandez G. [3]      Zhang G. [4]              0.0                                              None
        14       Wang J. [7]      Tefas A. [3]              0.0                                              None
        15      Zhang G. [4]       Wang J. [7]              0.0                                              None
        16        Yan X. [3]  Hernandez G. [3]              0.0                                              None
        17       Wang J. [7]      Zhang G. [4]              0.0                                              None
        18        Yan X. [3]      Zhang G. [4]              0.0                                              None
        19        Yan X. [3]       Wang J. [7]              0.0                                              None
        20      Zhang G. [4]      Tefas A. [3]              0.0                                              None
        21      Zhang G. [4]  Hernandez G. [3]              0.0                                              None
        22      Zhang G. [4]        Yan X. [3]              0.0                                              None
        23       Wang J. [7]  Hernandez G. [3]              0.0                                              None
        24        Yan X. [3]      Tefas A. [3]              0.0                                              None

        """
        result = self.cross_corr(
            column_r=column, column_c=column, sep_r=sep, sep_c=sep, top_n=top_n, cut_value=cut_value)
        result._call = 'auto_corr'
        return result


    #----------------------------------------------------------------------------------------------
    def citations_by_terms(self, column, sep=None, top_n=None, minmax=None):
        """Computes the number of citations by item in a column.

        >>> from techminer.datasets import load_test_cleaned
        >>> rdf = load_test_cleaned().data
        >>> rdf.citations_by_terms(column='Authors', sep=',', top_n=10)
                    Authors  Cited by                                  ID
        0     Yeh W.-C. [1]     188.0                           [[*140*]]
        1   Hsieh T.-J. [1]     188.0                           [[*140*]]
        2   Hsiao H.-F. [1]     188.0                           [[*140*]]
        3  Hussain A.J. [2]      52.0                  [[*125*], [*139*]]
        4     Krauss C. [1]      49.0                            [[*62*]]
        5    Fischer T. [1]      49.0                            [[*62*]]
        6       Wang J. [7]      46.0  [[*80*], [*87*], [*128*], [*128*]]
        7    Liatsis P. [1]      42.0                           [[*139*]]
        8    Ghazali R. [1]      42.0                           [[*139*]]
        9  Yoshihara A. [1]      37.0                           [[*124*]]
        >>> rdf.citations_by_terms(column='Authors', sep=',', minmax=(30,50))
                       Authors  Cited by                                  ID
        0        Krauss C. [1]      49.0                            [[*62*]]
        1       Fischer T. [1]      49.0                            [[*62*]]
        2          Wang J. [7]      46.0  [[*80*], [*87*], [*128*], [*128*]]
        3       Liatsis P. [1]      42.0                           [[*139*]]
        4       Ghazali R. [1]      42.0                           [[*139*]]
        5     Yoshihara A. [1]      37.0                           [[*124*]]
        6     Matsubara T. [1]      37.0                           [[*124*]]
        7         Akita R. [1]      37.0                           [[*124*]]
        8        Uehara K. [1]      37.0                           [[*124*]]
        9      Passalis N. [3]      31.0                  [[*110*], [*114*]]
        10      Gabbouj M. [3]      31.0                  [[*110*], [*114*]]
        11   Kanniainen J. [3]      31.0                  [[*110*], [*114*]]
        12        Tefas A. [3]      31.0                  [[*110*], [*114*]]
        13  Tsantekidis A. [2]      31.0                  [[*110*], [*114*]]
        14    Iosifidis A. [3]      31.0                  [[*110*], [*114*]]

        """
        data = self[[column, 'Cited by', 'ID']].dropna()
        data = _expand_column(data, column, sep)

        numcitations = data.groupby([column], as_index=True).agg({
            'Cited by': np.sum
        })

        result = pd.DataFrame({
            column : numcitations.index,
            'Cited by' : numcitations['Cited by'].tolist()
        })
        result = result.sort_values(by='Cited by', ascending=False)
        result.index = result[column]

        if top_n is not None and len(result) > top_n:
            result = result.head(top_n)


        result = _minmax(result, minmax)


        result['ID'] = None
        for current_term in result[result.columns[0]]:
            selected_IDs = data[data[column] == current_term]['ID']
            if len(selected_IDs):
                result.at[current_term,'ID'] = selected_IDs.tolist()

        ## counts the number of documents --------------------------------------------------------

        resul = self._add_documents_by_terms_to_label(result, column, sep)

        ## end -----------------------------------------------------------------------------------
        
        result.index = list(range(len(result)))

        return Result(result, call='citations_by_terms')

    #----------------------------------------------------------------------------------------------
    def citations_by_terms_by_year(self, column, sep=None, top_n=None, minmax=None):
        """Computes the number of citations by term by year in a column.

        >>> from techminer.datasets import load_test_cleaned
        >>> rdf = load_test_cleaned().data
        >>> rdf.citations_by_terms_by_year('Authors', sep=',', top_n=5)
                    Authors       Year  Cited by         ID
        0   Hsiao H.-F. [1]   2011 [2]     188.0  [[*140*]]
        1   Hsieh T.-J. [1]   2011 [2]     188.0  [[*140*]]
        2  Hussain A.J. [2]   2011 [2]      42.0  [[*139*]]
        3  Hussain A.J. [2]   2016 [5]      10.0  [[*125*]]
        4     Krauss C. [1]  2018 [52]      49.0   [[*62*]]
        5     Yeh W.-C. [1]   2011 [2]     188.0  [[*140*]]

        """
        data = self[[column, 'Cited by', 'Year', 'ID']].dropna()
        data['Year'] = data['Year'].map(int)
        data = _expand_column(data, column, sep)

        numcitations = data.groupby(by=[column, 'Year'], as_index=True).agg({
            'Cited by': np.sum
        })

        ## results dataframe
        a = [t for t,_ in numcitations.index]
        b = [t for _,t in numcitations.index]
        result = pd.DataFrame({
            column : a,
            'Year' : b,
            'Cited by' : numcitations['Cited by'].tolist()
        })

        ## rows
        top = self.citations_by_terms(column, sep)
        if top_n is not None and len(top) > top_n:
            top = top[0:top_n][column].tolist()
            top = [u[0:u.find('[')].strip()  for u in top]
            selected = [True if row[0] in top else False for idx, row in result.iterrows()] 
            result = result[selected]

        result = _minmax(result, minmax)
        

        result['ID'] = None
        for idx, row in result.iterrows():
            selected_IDs = data[(data[column] == row[0]) & (data['Year'] == row[1])]['ID']
            if len(selected_IDs):
                result.at[idx, 'ID'] = selected_IDs.tolist()
            
    
        ## counts the number of ddcuments only in the results matrix -----------------------

        resul = self._add_documents_by_terms_to_label(result, column, sep)
        resul = self._add_documents_by_terms_to_label(result, 'Year', sep=None)
        result.index = list(range(len(result)))
        return Result(result, call='citations_by_terms_by_year')

    #----------------------------------------------------------------------------------------------
    def citations_by_year(self, cumulative=False):
        """Computes the number of citations by year.

        >>> from techminer.datasets import load_test_cleaned
        >>> rdf = load_test_cleaned().data
        >>> rdf.citations_by_year().head()
               Year  Cited by                                    ID
        0  2010 [3]      21.0                    [[*142*], [*143*]]
        1  2011 [2]     230.0                    [[*139*], [*140*]]
        2  2012 [2]      16.0                    [[*137*], [*138*]]
        3  2013 [4]      36.0  [[*133*], [*134*], [*135*], [*136*]]
        4  2014 [2]      23.0                    [[*131*], [*132*]]

        """

        ## computes number of citations
        data = self[['Year', 'Cited by', 'ID']].dropna()
        data['Year'] = data['Year'].map(int)
        citations = data.groupby(['Year'], as_index=True).agg({
            'Cited by': np.sum
        })

        result = self._years_list()
        result = result.to_frame()
        result['Year'] = result.index
        result['Cited by'] = 0
        result.at[citations.index, 'Cited by'] = citations['Cited by'].tolist()
        result.index = list(range(len(result)))

        ## IDs ---------------------------------------------------------------------------------
        result['ID'] = None
        for idx, row in result.iterrows():
            selected_IDs = data[(data['Year'] == row[0]) & (data['Cited by'] > 0)]['ID']
            if len(selected_IDs):
                result.at[idx, 'ID'] = selected_IDs.tolist()

        ## end ----------------------------------------------------------------------------------

        if cumulative is True:
            result['Cited by'] = result['Cited by'].cumsum()

       ## counts the number of documents --------------------------------------------------------

        count = self.documents_by_year(cumulative=cumulative)
        count = {key : value for key, value in zip(count[count.columns[0]], count[count.columns[1]])}
        result['Year'] = result['Year'].map(lambda x: cut_text(str(x) + ' [' + str(count[x]) + ']'))

        ## end -----------------------------------------------------------------------------------

        return Result(result, call='citations_by_year')

    #----------------------------------------------------------------------------------------------
    def co_ocurrence(self, column_r, column_c, sep_r=None, sep_c=None, top_n=None, minmax=None):
        """Computes the number of documents containing two given items in different columns.

        >>> from techminer.datasets import load_test_cleaned
        >>> rdf = load_test_cleaned().data
        >>> rdf.co_ocurrence(column_r='Authors', sep_r=',', column_c='Document Type', top_n=5)
              Authors (row)    Document Type (col)  Num Documents                                         ID
        0  Hernandez G. [3]  Conference Paper [12]              3                  [[*52*], [*94*], [*100*]]
        1      Tefas A. [3]  Conference Paper [12]              3                  [[*8*], [*110*], [*114*]]
        2       Wang J. [7]            Article [8]              5  [[*3*], [*10*], [*80*], [*128*], [*128*]]
        3       Wang J. [7]  Conference Paper [12]              2                           [[*15*], [*87*]]
        4        Yan X. [3]            Article [8]              1                                   [[*44*]]
        5        Yan X. [3]  Conference Paper [12]              2                           [[*13*], [*85*]]
        6      Zhang G. [4]            Article [8]              2                          [[*27*], [*117*]]
        7      Zhang G. [4]  Conference Paper [12]              2                          [[*78*], [*119*]]

        """




        ## computes the number of documents by term by term        
        data = self[[column_r, column_c, 'ID']].dropna()
        top_r = self.documents_by_terms(column_r, sep_r)
        top_c = self.documents_by_terms(column_c, sep_c)

        data.columns = [column_r + ' (row)', column_c + ' (col)', 'ID' ]
        column_r +=  ' (row)'
        column_c +=  ' (col)'

        data = _expand_column(data, column_r, sep_r)
        data = _expand_column(data, column_c, sep_c)

        ## number of documents
        numdocs = data.groupby(by=[column_r, column_c]).size()

        ## results dataframe
        a = [t for t,_ in numdocs.index]
        b = [t for _,t in numdocs.index]
        result = pd.DataFrame({
            column_r : a,
            column_c : b,
            'Num Documents' : numdocs.tolist()
        })

        ## compute top_n terms
        if top_n is not None:
            ## rows
            # top = self.documents_by_terms(column_r, sep_r)
            if len(top_r) > top_n:
                top_r = top_r[0:top_n][top_r.columns[0]].tolist()
                selected = [True if row[0] in top_r else False for idx, row in result.iterrows()] 
                result = result[selected]

            ## cols
            # top = self.documents_by_terms(column_c, sep_c)
            if len(top_c) > top_n:
                top_c = top_c[0:top_n][top_c.columns[0]].tolist()
                selected = [True if row[1] in top_c else False for idx, row in result.iterrows()] 
                result = result[selected]
            
        result = _minmax(result, minmax)


        ## collects the references
        result['ID'] = None
        for idx, row in result.iterrows():
            term0 = row[0]
            term1 = row[1]
            selected_IDs = data[(data[column_r] == term0) & (data[column_c] == term1)]['ID']
            if len(selected_IDs):
                result.at[idx, 'ID'] = selected_IDs.tolist()

        result.index = list(range(len(result)))

        ## counts the number of ddcuments only in the results matrix -----------------------

        result = Result(result, call='citations_by_year')
        result._add_count_to_label(column_r)
        result._add_count_to_label(column_c)
        return result

    #----------------------------------------------------------------------------------------------
    def coverage(self):
        """Counts the number of None values per column.


        Returns:
            Pandas DataFrame.

        >>> from techminer.datasets import load_test_cleaned
        >>> rdf = load_test_cleaned().data
        >>> rdf.coverage()
                         Field  Number of items Coverage (%)
        0              Authors              144      100.00%
        1         Author(s) ID              144      100.00%
        2                Title              144      100.00%
        3                 Year              144      100.00%
        4         Source title              144      100.00%
        5               Volume               97       67.36%
        6                Issue               27       18.75%
        7             Art. No.               49       34.03%
        8           Page start              119       82.64%
        9             Page end              119       82.64%
        10          Page count                0        0.00%
        11            Cited by               68       47.22%
        12                 DOI              133       92.36%
        13        Affiliations              143       99.31%
        14       Document Type              144      100.00%
        15         Access Type               16       11.11%
        16              Source              144      100.00%
        17                 EID              144      100.00%
        18            Abstract              144      100.00%
        19     Author Keywords              124       86.11%
        20      Index Keywords              123       85.42%
        21          References              137       95.14%
        22            keywords              144      100.00%
        23                CONF              144      100.00%
        24  keywords (cleaned)              144      100.00%
        25            SELECTED              144      100.00%
        26                  ID              144      100.00%

        """

        result = pd.DataFrame({
            'Field': self.columns,
            'Number of items': [len(self) - self[col].isnull().sum() for col in self.columns],
            'Coverage (%)': [ '{:5.2%}'.format((len(self) - self[col].isnull().sum()) / len(self)) for col in self.columns]
        })

        return result

    #----------------------------------------------------------------------------------------------
    def cross_corr(self, column_r, column_c=None, sep_r=None, sep_c=None, top_n=20, cut_value=0):
        """Computes the crosscorrelation among items in two different columns of the dataframe.

        >>> from techminer.datasets import load_test_cleaned
        >>> rdf = load_test_cleaned().data
        >>> rdf.cross_corr(column_r='Authors', sep_r=',', column_c='Author Keywords', sep_c=';', top_n=5)
                     Authors               Author Keywords  Crosscorrelation                 ID
        0         Yan X. [3]     Financial time series [7]          0.218218           [[*13*]]
        1   Hernandez G. [3]            Deep learning [34]          0.198030  [[*94*], [*100*]]
        2       Zhang G. [4]     Financial time series [7]          0.188982          [[*119*]]
        3       Zhang G. [4]            Deep learning [34]          0.171499  [[*27*], [*117*]]
        4       Zhang G. [4]            Deep Learning [10]          0.158114           [[*78*]]
        5        Wang J. [7]            Deep learning [34]          0.140028    [[*3*], [*87*]]
        6        Wang J. [7]            Deep Learning [10]          0.129099           [[*15*]]
        7         Yan X. [3]            Deep learning [34]          0.099015           [[*13*]]
        8   Hernandez G. [3]                     LSTM [18]          0.000000               None
        9       Tefas A. [3]  Recurrent neural network [8]          0.000000               None
        10      Tefas A. [3]            Deep Learning [10]          0.000000               None
        11      Tefas A. [3]                     LSTM [18]          0.000000               None
        12      Tefas A. [3]            Deep learning [34]          0.000000               None
        13  Hernandez G. [3]     Financial time series [7]          0.000000               None
        14  Hernandez G. [3]  Recurrent neural network [8]          0.000000               None
        15  Hernandez G. [3]            Deep Learning [10]          0.000000               None
        16        Yan X. [3]            Deep Learning [10]          0.000000               None
        17        Yan X. [3]  Recurrent neural network [8]          0.000000               None
        18       Wang J. [7]                     LSTM [18]          0.000000               None
        19        Yan X. [3]                     LSTM [18]          0.000000               None
        20      Zhang G. [4]  Recurrent neural network [8]          0.000000               None
        21      Zhang G. [4]                     LSTM [18]          0.000000               None
        22       Wang J. [7]     Financial time series [7]          0.000000               None
        23       Wang J. [7]  Recurrent neural network [8]          0.000000               None
        24      Tefas A. [3]     Financial time series [7]          0.000000               None
        

        """ 
 
        if column_r == column_c:
            sep_c = None
            column_c = None

        tdf_r = self.tdf(column_r, sep_r, top_n)
        if column_c is not None:
            tdf_c = self.tdf(column_c, sep_c, top_n)
        else:
            tdf_c = tdf_r.copy()
            
        if column_c is not None:
            col0 = column_r
            col1 = column_c
            col2 = 'Crosscorrelation'
        else:
            col0 = column_r + ' (row)'
            col1 = column_r + ' (col)'
            col2 = 'Autocorrelation'

        terms_r = tdf_r.columns.tolist()
        terms_c = tdf_c.columns.tolist()

        result =  pd.DataFrame({
            col0 : [None] * (len(terms_r) * len(terms_c)),
            col1 : [None] * (len(terms_r) * len(terms_c)),
            col2 : [0.0] * (len(terms_r) * len(terms_c))   
        })

        result['ID'] = None

        idx = 0
        for a in terms_r:
            for b in terms_c:

                s1 = tdf_r[a]
                s2 = tdf_c[b]

                num = np.sum((s1 * s2))
                den = np.sqrt(np.sum(s1**2) * np.sum(s2**2))
                value =  num / den
                result.at[idx, col0] = a
                result.at[idx, col1] = b
                result.at[idx, col2] = value

                selected_IDs = self[(s1 > 0) & (s2 > 0)]['ID']
                if len(selected_IDs):
                    result.at[idx, 'ID'] = selected_IDs.tolist()

                idx += 1

        #result = result.style.format('{0:.4}')

        ## cluster computation -------------------------------------------------------------------
        
        ## number of clusters
        mtx = Result(result.copy(), call='cross_corr')
        mtx = mtx.tomatrix()
        mtx = mtx.applymap(lambda x: 1 if x > 0 else 0)
        mtx = mtx.transpose()
        mtx = mtx.drop_duplicates()
        mtx = mtx.transpose()
        clusters = mtx.columns

        ## dataframe with relationships among items
        map_cluster = []
        map_from = []
        map_to = []
        map_similariry = []
        map_color = []

        norm = colors.Normalize(vmin=0, vmax=len(clusters))
        cmap = cm.get_cmap('tab20')

        ## similarity computation
        for idx_cluster, cluster_term in enumerate(clusters):

            ## terms in r selected in the current cluster
            cluster_index = mtx.index[mtx[cluster_term] > 0]

            for idx0_r, term0_r in enumerate(cluster_index):
                for idx1_r, term1_r in enumerate(cluster_index):

                    if idx1_r  <= idx0_r:
                        continue
                    
                    ## docs related to term0 and term1
                    idx = (tdf_r[term0_r] > 0) | (tdf_r[term1_r] > 0)

                    tdf_similarity = tdf_c[ (idx) & (tdf_c[cluster_term] > 0)]

                    jaccard = 0.0
                    n_jaccard = 0

                    for idx_i, doc_i in tdf_similarity.iterrows():
                        for idx_j, doc_j in tdf_similarity.iterrows():
                    
                            if idx_i == idx_j:
                                break

                            terms_i = doc_i.tolist()
                            terms_j = doc_j.tolist()
                            intersection = [i*j for i, j in zip(terms_i, terms_j)]

                            len_i = sum(terms_i)
                            len_j = sum(terms_j)
                            len_c = sum(intersection)

                            jaccard += float(len_c) / (len_i + len_j - len_c)
                            n_jaccard += 1

                    if n_jaccard == 0:
                        jaccard = 1.0
                    else:
                        jaccard = jaccard / n_jaccard

                    map_cluster += [cluster_term]
                    map_from += [term0_r]
                    map_to += [term1_r]
                    map_similariry += [jaccard]
                    map_color += [cmap(norm(idx_cluster))]

        map_data = pd.DataFrame({
            'cluster' : map_cluster,
            'from_node' : map_from,
            'to_node' : map_to,
            'similarity' : map_similariry,
            'color' : map_color 
        })
        map_data = map_data.drop_duplicates(subset=['from_node', 'to_node'])

        ## end -----------------------------------------------------------------------------------

        ## line style for diagrams ---------------------------------------------------------------
        map_data['linewidth'] = None
        map_data['linestyle'] = None

        for idx, row in map_data.iterrows():

                if row[3] >= 0.75:
                    map_data.at[idx, 'linewidth'] = 4
                    map_data.at[idx, 'linestyle'] = '-' 
                elif row[3] >= 0.50:
                    map_data.at[idx, 'linewidth'] = 2
                    map_data.at[idx, 'linestyle'] = '-' 
                elif row[3] >= 0.25:
                    map_data.at[idx, 'linewidth'] = 2
                    map_data.at[idx, 'linestyle'] = '--' 
                elif row[3] < 0.25:
                    map_data.at[idx, 'linewidth'] = 1
                    map_data.at[idx, 'linestyle'] = ':'
                else: 
                    map_data.at[idx, 'linewidth'] = 0
                    map_data.at[idx, 'linestyle'] = '-'

        ## end -----------------------------------------------------------------------------------

        ## adds number of records to columns -----------------------------------------------------
        num = self.documents_by_terms(column_r, sep_r)
        new_names = {}
        for idx, row in num.iterrows():
            old_name = row[0]
            new_name = old_name + ' [' + str(row[1]) + ']'
            new_names[old_name] = new_name

        result[col0] = result[col0].map(lambda x: new_names[x])

        ## >>> adds number of records to cluster nodes ------------------------------------------------
        map_data['from_node'] = map_data['from_node'].map(lambda x: new_names[x])
        map_data['to_node'] = map_data['to_node'].map(lambda x: new_names[x])
        ## <<< end ------------------------------------------------------------------------------------

        if column_c is not None:
            num = self.documents_by_terms(column_c, sep_c)
            new_names = {}
            for idx, row in num.iterrows():
                old_name = row[0]
                new_name = old_name + ' [' + str(row[1]) + ']'
                new_names[old_name] = new_name

        result[col1] = result[col1].map(lambda x: new_names[x])
        ## end ------------------------------------------------------------------------------------

        result = result.sort_values(col2, ascending=False)
        result.index = list(range(len(result)))
        return Result(result, call='cross_corr', cluster_data=map_data)


    #----------------------------------------------------------------------------------------------
    def documents_by_terms(self, column, sep=None, top_n=None, minmax=None):
        """Computes the number of documents per term in a given column.

        >>> from techminer.datasets import load_test_cleaned
        >>> rdf = load_test_cleaned().data
        >>> rdf.documents_by_terms('Authors', sep=',').head(5)
                Authors  Num Documents                                                 ID
        0       Wang J.              7  [[*3*], [*10*], [*15*], [*80*], [*87*], [*128*...
        1      Zhang G.              4                 [[*27*], [*78*], [*117*], [*119*]]
        2        Yan X.              3                           [[*13*], [*44*], [*85*]]
        3  Hernandez G.              3                          [[*52*], [*94*], [*100*]]
        4      Tefas A.              3                          [[*8*], [*110*], [*114*]]

        """

        # computes the number of documents by term
        data = self[[column, 'ID']].dropna()
        data = _expand_column(data, column, sep)

        numdocs = data.groupby(column, as_index=False).size()
        
        ## dataframe with results
        result = pd.DataFrame({
            column : numdocs.index,
            'Num Documents' : numdocs.tolist()
        })
        result = result.sort_values(by='Num Documents', ascending=False)
        result.index = result[column]

        ## compute top_n terms
        if top_n is not None and len(result) > top_n:
            result = result.head(top_n)


        result = _minmax(result, minmax)


        result['ID'] = None
        for current_term in result[result.columns[0]]:
            selected_IDs = data[data[column] == current_term]['ID']
            if len(selected_IDs):
                result.at[current_term,'ID'] = selected_IDs.tolist()

        result.index = list(range(len(result)))

        return Result(result, call='documents_by_terms')

    #----------------------------------------------------------------------------------------------
    def documents_by_year(self, cumulative=False):
        """Computes the number of documents per year.

        >>> from techminer.datasets import load_test_cleaned
        >>> rdf = load_test_cleaned().data
        >>> rdf.documents_by_year().head()
           Year  Num Documents                                    ID
        0  2010              3           [[*141*], [*142*], [*143*]]
        1  2011              2                    [[*139*], [*140*]]
        2  2012              2                    [[*137*], [*138*]]
        3  2013              4  [[*133*], [*134*], [*135*], [*136*]]
        4  2014              2                    [[*131*], [*132*]]
        >>> rdf.documents_by_year(cumulative=True).head()
           Year  Num Documents                                    ID
        0  2010              3           [[*141*], [*142*], [*143*]]
        1  2011              5                    [[*139*], [*140*]]
        2  2012              7                    [[*137*], [*138*]]
        3  2013             11  [[*133*], [*134*], [*135*], [*136*]]
        4  2014             13                    [[*131*], [*132*]]
        """

        ## number of documents by year
        numdocs = self.groupby('Year')[['Year']].count()

        ## dataframe with results
        result = self._years_list()
        result = result.to_frame()
        result['Year'] = result.index
        result['Num Documents'] = 0
        result.at[numdocs.index.tolist(), 'Num Documents'] = numdocs['Year'].tolist()
        result.index = result['Year']

        if cumulative is True:
            result['Num Documents'] = result['Num Documents'].cumsum()

        result['ID'] = None
        for current_term in result['Year']:
            selected_IDs = self[self['Year'] == current_term]['ID']            
            if len(selected_IDs):
                result.at[current_term,'ID'] = selected_IDs.tolist()

        result.index = list(range(len(result)))

        return Result(result, call='documents_by_year')

    #----------------------------------------------------------------------------------------------
    def factor_analysis(self, column, sep=None, n_components=None, top_n=10):
        """Computes the matrix of factors for terms in a given column.

        >>> from techminer.datasets import load_test_cleaned
        >>> rdf = load_test_cleaned().data
        >>> rdf.factor_analysis(
        ...    column='Authors', 
        ...    sep=',', 
        ...    n_components=5, 
        ...    top_n=40).tomatrix().head(5) # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
                               F0        F1        F2        F3        F4
        Wang J. [7]      -0.025355 -0.040096 -0.695298  0.624399  0.223693
        Zhang G. [4]     -0.017487 -0.028221  0.452656  0.559642 -0.167425
        Yan X. [3]       -0.010094 -0.013940 -0.057740 -0.006361 -0.018068
        Hernandez G. [3] -0.029542  0.489821  0.002071  0.023022  0.012202
        Tefas A. [3]      0.425717  0.023641  0.001237  0.014415  0.007825

        """


        tdf = self.tdf(column, sep, top_n)
        terms = tdf.columns.tolist()

        if n_components is None:
            n_components = int(math.sqrt(len(set(terms))))

        pca = PCA(n_components=n_components)
        
        values = np.transpose(pca.fit(X=tdf.values).components_)

        cols = [['F'+str(i) for i in range(n_components)] for k in range(len(terms))]
        rows = [[t for n in range(n_components) ] for t in terms]
        values = [values[i,j] for i in range(len(terms)) for j in range(n_components)]

        cols = [e for row in cols for e in row]
        rows = [e for row in rows for e in row]

        result = pd.DataFrame({
            column : rows,
            'Factor' : cols,
            'value' : values})


        ## cluster computation -------------------------------------------------------------------
        
        tdf_r = self.tdf(column, sep, top_n)
        tdf_c = tdf_r

        ## number of clusters
        mtx = Result(result.copy(), call='factor_analysis')
        mtx = mtx.tomatrix()
        mtx = mtx.applymap(lambda x: 1 if x > 0 else 0)
        mtx = mtx.transpose()
        mtx = mtx.drop_duplicates()
        mtx = mtx.transpose()
        clusters = mtx.columns

        ## dataframe with relationships among items
        map_cluster = []
        map_from = []
        map_to = []
        map_similariry = []
        map_color = []

        norm = colors.Normalize(vmin=0, vmax=len(clusters))
        cmap = cm.get_cmap('tab20')


        ## similarity computation
        for idx_cluster, cluster_term in enumerate(clusters):

            ## terms in r selected in the current cluster
            cluster_index = mtx.index[mtx[cluster_term] > 0]

            for idx0_r, term0_r in enumerate(cluster_index):
                for idx1_r, term1_r in enumerate(cluster_index):

                    if idx1_r  <= idx0_r:
                        continue
                    
                    ## docs related to term0 and term1
                    idx = (tdf_r[term0_r] > 0) | (tdf_r[term1_r] > 0)

                    tdf_similarity = tdf_c[idx]

                    jaccard = 0.0
                    n_jaccard = 0

                    for idx_i, doc_i in tdf_similarity.iterrows():
                        for idx_j, doc_j in tdf_similarity.iterrows():
                    
                            if idx_i == idx_j:
                                break

                            terms_i = doc_i.tolist()
                            terms_j = doc_j.tolist()
                            intersection = [i*j for i, j in zip(terms_i, terms_j)]

                            len_i = sum(terms_i)
                            len_j = sum(terms_j)
                            len_c = sum(intersection)

                            jaccard += float(len_c) / (len_i + len_j - len_c)
                            n_jaccard += 1

                    if n_jaccard == 0:
                        jaccard = 1.0
                    else:
                        jaccard = jaccard / n_jaccard

                    map_cluster += [cluster_term]
                    map_from += [term0_r]
                    map_to += [term1_r]
                    map_similariry += [jaccard]
                    map_color += [cmap(norm(idx_cluster))]

        map_data = pd.DataFrame({
            'cluster' : map_cluster,
            'from_node' : map_from,
            'to_node' : map_to,
            'similarity' : map_similariry,
            'color' : map_color  
        })
        map_data = map_data.drop_duplicates(subset=['from_node', 'to_node'])
        ## end -----------------------------------------------------------------------------------

         ## line style for diagrams ---------------------------------------------------------------
        map_data['linewidth'] = None
        map_data['linestyle'] = None

        for idx, row in map_data.iterrows():

                if row[3] >= 0.75:
                    map_data.at[idx, 'linewidth'] = 4
                    map_data.at[idx, 'linestyle'] = '-' 
                elif row[3] >= 0.50:
                    map_data.at[idx, 'linewidth'] = 2
                    map_data.at[idx, 'linestyle'] = '-' 
                elif row[3] >= 0.25:
                    map_data.at[idx, 'linewidth'] = 2
                    map_data.at[idx, 'linestyle'] = '--' 
                elif row[3] < 0.25:
                    map_data.at[idx, 'linewidth'] = 1
                    map_data.at[idx, 'linestyle'] = ':'
                else: 
                    map_data.at[idx, 'linewidth'] = 0
                    map_data.at[idx, 'linestyle'] = '-'

        ## end -----------------------------------------------------------------------------------


        ## adds number of records to columns
        num = self.documents_by_terms(column, sep)
        new_names = {}
        for idx, row in num.iterrows():
            old_name = row[0]
            new_name = old_name + ' [' + str(row[1]) + ']'
            new_names[old_name] = new_name
        result[column] = result[column].map(lambda x: new_names[x])
        ## end 

        ## >>> adds number of records to cluster nodes ------------------------------------------------
        map_data['from_node'] = map_data['from_node'].map(lambda x: new_names[x])
        map_data['to_node'] = map_data['to_node'].map(lambda x: new_names[x])
        ## <<< end ------------------------------------------------------------------------------------

        return Result(result, call='factor_analysis', cluster_data=map_data)

    #----------------------------------------------------------------------------------------------
    def generate_ID(self):
        """Generates a unique ID for each document.
        """
        self['ID'] = [ '[*'+str(x)+ '*]' for x in range(len(self))]
        self.index = self['ID']
        return self

    #----------------------------------------------------------------------------------------------
    def get_records_by_IDs(self, IDs):
        """Extracts records using the ID number.
        """
        result = None
        for ID in IDs:
            rdf = self[self['ID'] == ID].copy()
            if result is None:
                result = rdf
            else:
                result = result.append(rdf)
        return result

    #----------------------------------------------------------------------------------------------
    def most_cited_documents(self, top_n=10, minmax=None):
        """ Returns the top N most cited documents and citations > min_value .
        
        Args:
            top_n (int) : number of documents to be returned.
            minmax ((int, int) tuple) : minimal number of citations

        Results:
            pandas.DataFrame


        >>> from techminer.datasets import load_test_cleaned
        >>> rdf = load_test_cleaned().data
        >>> rdf.most_cited_documents(top_n=5)[['Authors', 'Title']]
                                                     Authors                                              Title
        140              Hsieh T.-J., Hsiao H.-F., Yeh W.-C.  Forecasting stock markets using wavelet transf...
        62                             Fischer T., Krauss C.  Deep learning with long short-term memory netw...
        139             Ghazali R., Hussain A.J., Liatsis P.  Dynamic Ridge Polynomial Neural Network: Forec...
        124  Akita R., Yoshihara A., Matsubara T., Uehara K.  Deep learning for stock prediction using numer...
        134                         Sharma V., Srinivasan D.  A hybrid intelligent model based on recurrent ...

        """
        result = self.sort_values(by='Cited by', ascending=False)

        if top_n is not None and len(result) > top_n:
            result = result[0:top_n]

        if minmax is not None:
            minval, maxval = minmax
            result = result[ result['Cited by'] >= minval ]
            result = result[ result['Cited by'] <= maxval ]
        
        return result[['Title', 'Authors', 'Year', 'Cited by', 'ID']]

    #----------------------------------------------------------------------------------------------
    @property
    def num_of_sources(self):
        """Returns the number of source titles in the dataframe.

        >>> from techminer.datasets import load_test_cleaned
        >>> rdf = load_test_cleaned().data
        >>> rdf.num_of_sources
        103

        """
        return len(self['Source title'].unique())

    #----------------------------------------------------------------------------------------------
    def ocurrence(self, column, sep=None, top_n=None, minmax=None):
        """

        >>> from techminer.datasets import load_test_cleaned
        >>> rdf = load_test_cleaned().data
        >>> rdf.ocurrence(column='Authors', sep=',', top_n=10)
               Authors (row)     Authors (col)  Num Documents                                                 ID
        0     Ar\xe9valo A. [9]    Ar\xe9valo A. [9]              3                          [[*52*], [*94*], [*100*]]
        1     Ar\xe9valo A. [9]  Hernandez G. [9]              3                          [[*52*], [*94*], [*100*]]
        2     Ar\xe9valo A. [9]   Sandoval J. [9]              3                          [[*52*], [*94*], [*100*]]
        3   Hernandez G. [9]    Ar\xe9valo A. [9]              3                          [[*52*], [*94*], [*100*]]
        4   Hernandez G. [9]  Hernandez G. [9]              3                          [[*52*], [*94*], [*100*]]
        5   Hernandez G. [9]   Sandoval J. [9]              3                          [[*52*], [*94*], [*100*]]
        6   Iosifidis A. [6]  Iosifidis A. [6]              3                          [[*8*], [*110*], [*114*]]
        7   Iosifidis A. [6]      Tefas A. [6]              3                          [[*8*], [*110*], [*114*]]
        8    Sandoval J. [9]    Ar\xe9valo A. [9]              3                          [[*52*], [*94*], [*100*]]
        9    Sandoval J. [9]  Hernandez G. [9]              3                          [[*52*], [*94*], [*100*]]
        10   Sandoval J. [9]   Sandoval J. [9]              3                          [[*52*], [*94*], [*100*]]
        11      Tefas A. [6]  Iosifidis A. [6]              3                          [[*8*], [*110*], [*114*]]
        12      Tefas A. [6]      Tefas A. [6]              3                          [[*8*], [*110*], [*114*]]
        13       Wang J. [9]       Wang J. [9]              9  [[*3*], [*10*], [*15*], [*80*], [*87*], [*128*...
        14         Wu J. [3]         Wu J. [3]              3                          [[*34*], [*66*], [*115*]]
        15        Yan X. [3]        Yan X. [3]              3                           [[*13*], [*44*], [*85*]]
        16      Zhang G. [4]      Zhang G. [4]              4                 [[*27*], [*78*], [*117*], [*119*]]
        17      Zhang Y. [3]      Zhang Y. [3]              3                            [[*4*], [*6*], [*109*]]

        """

        ## computes the number of documents by term by term        
        data = self[[column, 'ID']].dropna()
        data.columns = [column + ' (row)', 'ID']
        data[column + ' (col)'] = data[column + ' (row)'].copy() 
        top = self.documents_by_terms(column, sep)
        
        column_r = column + ' (row)'
        column_c = column + ' (col)'
        data = data[[column_r, column_c, 'ID']]

        data = _expand_column(data, column_r, sep)
        data = _expand_column(data, column_c, sep)

        ## number of documents
        numdocs = data.groupby(by=[column_r, column_c]).size()

        ## results dataframe
        a = [t for t,_ in numdocs.index]
        b = [t for _,t in numdocs.index]
        result = pd.DataFrame({
            column_r : a,
            column_c : b,
            'Num Documents' : numdocs.tolist()
        })

        ## compute top_n terms
        if top_n is not None:
            ## rows
            # top = self.documents_by_terms(column_r, sep_r)
            if len(top) > top_n:

                top = top[0:top_n][top.columns[0]].tolist()

                selected = [True if row[0] in top else False for idx, row in result.iterrows()] 
                result = result[selected]

                selected = [True if row[1] in top else False for idx, row in result.iterrows()] 
                result = result[selected]
            

        result = _minmax(result, minmax)


        ## collects the references
        result['ID'] = None
        for idx, row in result.iterrows():
            term0 = row[0]
            term1 = row[1]
            selected_IDs = data[(data[column_r] == term0) & (data[column_c] == term1)]['ID']
            if len(selected_IDs):
                result.at[idx, 'ID'] = selected_IDs.tolist()

        result.index = list(range(len(result)))

        ## counts the number of ddcuments only in the results matrix -----------------------

        result = Result(result, call='ocurrence')
        result._add_count_to_label(column_r)
        result._add_count_to_label(column_c)
        return result


    #----------------------------------------------------------------------------------------------
    def tdf(self, column, sep, top_n=20):
        """

        >>> from techminer.datasets import load_test_cleaned
        >>> rdf = load_test_cleaned().data
        >>> rdf.tdf('Authors', sep=',', top_n=5).head() # doctest: +ELLIPSIS +NORMALIZE_WHITESPACE
           Wang J.  Zhang G.  Yan X.  Hernandez G.  Tefas A.
        0      0.0       0.0     0.0           0.0       0.0
        1      0.0       0.0     0.0           0.0       0.0
        2      0.0       0.0     0.0           0.0       0.0
        3      1.0       0.0     0.0           0.0       0.0
        4      0.0       0.0     0.0           0.0       0.0

        """

        ## computa los N terminos mas frecuentes
        x = self.documents_by_terms(column, sep=sep)
        terms = x[x.columns[0]].tolist()
        if top_n is not None and len(terms) > top_n:
            terms = terms[0:top_n]
        
        tdf = pd.DataFrame(
            data = np.zeros((len(self), len(terms))),
            columns = terms,
            index = self.index)

        for idx in self.index:
            txt = self.loc[idx, column]
            if txt is not None:
                if sep is not None:
                    txt = [t.strip() for t in txt.split(sep)]
                else:
                    txt = [txt.strip()] 
                for t in txt:
                    if t in terms:
                        tdf.at[idx, t] = 1

        return tdf

    #----------------------------------------------------------------------------------------------
    def terms_by_terms_by_year(self, column_r, column_c, sep_r=None, sep_c=None, top_n=None, minmax=None):
        """

        >>> from techminer.datasets import load_test_cleaned
        >>> rdf = load_test_cleaned().data
        >>> rdf.terms_by_terms_by_year(column_r='Authors', sep_r=',', column_c='Author Keywords', sep_c=';', top_n=5)
                       Authors            Author Keywords      Year  Num Documents                 ID
        519   Hernandez G. [2]          Deep learning [7]  2018 [4]              2  [[*94*], [*100*]]
        1582       Wang J. [3]          Deep Learning [2]  2019 [5]              1           [[*15*]]
        1583       Wang J. [3]          Deep learning [7]  2018 [4]              1           [[*87*]]
        1584       Wang J. [3]          Deep learning [7]  2019 [5]              1            [[*3*]]
        1741        Yan X. [2]          Deep learning [7]  2019 [5]              1           [[*13*]]
        1745        Yan X. [2]  Financial time series [2]  2019 [5]              1           [[*13*]]
        1853      Zhang G. [4]          Deep Learning [2]  2018 [4]              1           [[*78*]]
        1854      Zhang G. [4]          Deep learning [7]  2017 [2]              1          [[*117*]]
        1855      Zhang G. [4]          Deep learning [7]  2019 [5]              1           [[*27*]]
        1856      Zhang G. [4]  Financial time series [2]  2017 [2]              1          [[*119*]]

        """
        
        ## computes the number of documents by term by term

        data = self[[column_r, column_c, 'Year', 'ID']].dropna()
        data = _expand_column(data, column_r, sep_r)
        data = _expand_column(data, column_c, sep_c)
        
        numdocs = data.groupby(by=[column_r, column_c, 'Year']).size()

        ## results dataframe
        a = [t for t,_,_ in numdocs.index]
        b = [t for _,t,_ in numdocs.index]
        y = [t for _,_,t in numdocs.index]
        result = pd.DataFrame({
            column_r : a,
            column_c : b,
            'Year' : y,
            'Num Documents' : numdocs.tolist()
        })

        ## compute top_n terms
        if top_n is not None:
            ## rows
            top = self.documents_by_terms(column_r, sep_r)
            if len(top) > top_n:
                top = top[0:top_n][column_r].tolist()
                selected = [True if row[0] in top else False for idx, row in result.iterrows()] 
                result = result[selected]

            ## cols
            top = self.documents_by_terms(column_c, sep_c)
            if len(top) > top_n:
                top = top[0:top_n][column_c].tolist()
                selected = [True if row[1] in top else False for idx, row in result.iterrows()] 
                result = result[selected]
            
        result = _minmax(result, minmax)

        result['ID'] = None
        for idx, row in result.iterrows():
            term0 = row[0]
            term1 = row[1]
            term2 = row[2]
            selected_IDs = data[
                (data[column_r] == term0) & (data[column_c] == term1) & (data['Year'] == term2)
            ]['ID']
            if len(selected_IDs):
                result.at[idx, 'ID'] = selected_IDs.tolist()

        ## counts the number of ddcuments only in the results matrix -----------------------

        result = Result(result, call='terms_by_terms_by_year')
        result._add_count_to_label(column_r)
        result._add_count_to_label(column_c)
        result._add_count_to_label('Year')
        return result

    #----------------------------------------------------------------------------------------------
    def terms_by_year(self, column, sep=None, top_n=None, minmax=None):
        """

        >>> from techminer.datasets import load_test_cleaned
        >>> rdf = load_test_cleaned().data
        >>> rdf.terms_by_year(column='Author Keywords', sep=';', top_n=5).head()
              Author Keywords       Year  Num Documents                                                ID
        0  Deep Learning [10]  2018 [37]              6  [[*54*], [*78*], [*79*], [*86*], [*95*], [*97*]]
        1  Deep Learning [10]  2019 [27]              4                  [[*15*], [*23*], [*26*], [*36*]]
        2  Deep learning [34]   2013 [3]              1                                         [[*134*]]
        3  Deep learning [34]   2016 [2]              1                                         [[*125*]]
        4  Deep learning [34]   2017 [7]              2                                [[*117*], [*120*]]
        >>> rdf.terms_by_year('Author Keywords',  minmax=(2,3), sep=';').head()
                             Author Keywords       Year  Num Documents                  ID
        0                          ARIMA [2]  2017 [13]              2  [[*115*], [*122*]]
        1                            CNN [4]  2018 [47]              2    [[*72*], [*89*]]
        2                            CNN [4]  2019 [33]              2    [[*18*], [*50*]]
        3  Convolutional Neural Networks [2]  2018 [47]              2    [[*78*], [*79*]]
        4   Convolutional neural network [4]  2018 [47]              2    [[*64*], [*77*]]
        >>> rdf.terms_by_year('Author Keywords',  top_n=3, minmax=(1,3), sep=';').head()
             Author Keywords      Year  Num Documents                  ID
        0  Deep learning [4]  2013 [3]              1           [[*134*]]
        1  Deep learning [4]  2016 [1]              1           [[*125*]]
        2  Deep learning [4]  2017 [5]              2  [[*117*], [*120*]]
        3           LSTM [6]  2013 [3]              2  [[*133*], [*135*]]
        4           LSTM [6]  2015 [1]              1           [[*130*]]

        """

        ## computes the number of documents by year
        data = self[[column, 'Year', 'ID']].dropna()
        data = _expand_column(data, column, sep)

        numdocs = data.groupby(by=[column, 'Year'], as_index=False).size()

        ## dataframe with results
        idx_term = [t for t,_ in numdocs.index]
        idx_year = [t for _,t in numdocs.index]
        result = pd.DataFrame({
            column : idx_term,
            'Year' : idx_year,
            'Num Documents' : numdocs.tolist()
        })

        ## compute top_n terms
        if top_n is not None:
            top = self.documents_by_terms(column, sep)
            if len(top) > top_n:
                top = top[0:top_n][column].tolist()
                selected = [True if row[0] in top else False for idx, row in result.iterrows()] 
                result = result[selected]

        result = _minmax(result, minmax)
        
        result['ID'] = None
        for idx, row in result.iterrows():
            current_term = row[0]
            year = row[1]
            selected_IDs = data[(data[column] == current_term) & (data['Year'] == year)]['ID']
            if len(selected_IDs):
                result.at[idx, 'ID'] = selected_IDs.tolist()

        result.index = list(range(len(result)))

        ## adds the number of documents to text ---------------------------------------------------

        result = Result(result, call='terms_by_year')
        result._add_count_to_label(column)
        result._add_count_to_label('Year')
        return result





