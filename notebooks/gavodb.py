dbmaster = 'postgres://viewer:viewer%40123@dbmaster.linea.gov.br:5432/production'
dbproduction = 'postgres://untrustedprod:untrusted@desdb4.linea.gov.br:5432/prod_gavo'
dbtesting = 'postgres://untrusted:untrusted@desdb4.linea.gov.br:5432/gavo'

import numpy as np
import sqlalchemy

class DBManager():
    """
    Object to connetc to DBs and get info (and tables)

    Attributes
    ----------
    conn: sqlalchemy.create_engine().connect()
        Connection to production DB
    conn_meta: sqlalchemy.create_engine().connect()
        Connection to consultation DB

    """
    def __init__(self):
        self.conn = None
        self.conn_meta = None
    def connect_to_master(self):
        if self.conn_meta is None:
            self.conn_meta = sqlalchemy.create_engine(dbmaster).connect()
        return
    def connect_to_production(self):
        if self.conn is None:
            self.conn = sqlalchemy.create_engine(dbproduction).connect()
        return
    def get_tablelist_from_pid(self, pid):
        """
        Get all output tables for a given process id

        Parameters
        ----------
        pid: str
            Process id

        Returns
        -------
        list
            All output tables from a given pid
        """
        self.connect_to_master()
        tables = self.conn_meta.execute(
            sqlalchemy.sql.text(('select t.schema_name, t.table_name from '
                                 '(select * from products where process_id=%s) p '
                                 'inner join tables t on p.table_id=t.table_id')%pid)
            ).fetchall()
        return ['.'.join(t) for t in tables]
    def get_unique_band_table(self, pid, bands, find_format='%s'):
        """
        Gets output table for required bands

        Parameters
        ----------
        pid: str
            Process id
        bands: list, tuple, str
            List of bands
        find_format: str
            String with a format to search the band in the tables, must
            contain a %s for the band

        Returns
        -------
        tables_dict: OrderedDict
            Dictionary with a corresponding table for each band
        """
        tables = self.get_tablelist_from_pid(pid)
        # add names to a dict
        tables_dict = OrderedDict()
        for b in bands:
            for tb in tables:
                if find_format%b in tb:
                    if b in tables_dict:
                        raise ValueError(f'band already found on tables: {tables}')
                    else:
                        tables_dict[b] = tb
        return tables_dict
    def get_db_table(self, table_name, columns):
        """
        Get table from db

        Parameters
        ----------
        table_name: str
            Name of table in DB
        columns: list
            Columns to extract from table

        Returns
        -------
        numpy array
            2D Array in column order
        """
        self.connect_to_production()
        return np.transpose(
            self.conn.execute(
                sqlalchemy.sql.text(
                    'select %s from %s'%(', '.join(columns), table_name)
                )
            ).fetchall()
        )
    def get_pype_input(self, pid):
        """
        Get pype_input.xml content

        Parameters
        ----------
        pid: str
            Process id

        Returns
        -------
        str
            pype_input.xml content
        """
        self.connect_to_master()
        return self.conn_meta.execute(
                    sqlalchemy.sql.text(
                        f'select pype_input from processes where process_id={pid}'
                    )
                ).fetchall()[0][0]#.split('\\n')
    def get_config(self, pid):
        """
        Get config.xml content

        Parameters
        ----------
        pid: str
            Process id

        Returns
        -------
        str
            config.xml content
        """
        self.connect_to_master()
        return self.conn_meta.execute(
                    sqlalchemy.sql.text(
                        f'select xml_config from processes where process_id={pid}'
                    )
                ).fetchall()[0][0]
    def get_output_files(self, pid):
        """
        Get all output file paths

        Parameters
        ----------
        pid: str
            Process id

        Returns
        -------
        list
            List with all output file paths
        """
        self.connect_to_master()
        return [i[0] for i in self.conn_meta.execute(
                    sqlalchemy.sql.text(
                        f'select file_locator.uri from'
                        f' (select * from products where process_id={pid}) p'
                        ' inner join file_locator on p.file_id=file_locator.file_id'
                        )
                    ).fetchall()
                ]
    def get_property_in_xml(self, xmlfile, string_in_prop, property):
        """
        Get the property of a product given a known sting in the line of a product in a xml

        Parameters
        ----------
        xmlfile: str
            Text inside a xml file
        string_in_prop: str
            Known string in the same line of required product
        property: str
            Name of the required property

        Returns
        -------
        str
            Property
        """
        lines = [i for i in xmlfile.split('\n') if string_in_prop in i]
        if len(lines)==0:
            raise ValueError(f'No products found with {string_in_prop} in line')
        elif len(lines)>1:
            raise ValueError(f'too many products found with {string_in_prop} in line:\n{lines}')
        else:
            return lines[0].split(f'{property}="')[1].split('"')[0]
    def get_pid_in_xml(self, xmlfile, string_in_prop):
        """
        Get the process id given a known sting in the line of a product in a xml

        Parameters
        ----------
        xmlfile: str
            Text inside a xml file
        string_in_prop: str
            Known string in the same line of required product

        Returns
        -------
        str
            Process id
        """
        return self.get_property_in_xml(xmlfile, string_in_prop, 'process_id')
    def get_value_in_xml(self, xmlfile, string_in_prop):
        """
        Get the value, given a known sting in the line of a product in a xml

        Parameters
        ----------
        xmlfile: str
            Text inside a xml file
        string_in_prop: str
            Known string in the same line of required product

        Returns
        -------
        str
            Value of product
        """
        return self.get_property_in_xml(xmlfile, string_in_prop, 'value')

#--------- gabolv_features ---------#

    def get_db_table_columns_names(self, table_name):
        """
        Get table from db

        Parameters
        ----------
        table_name: str
            Name of table in DB
        columns: list
            Columns to extract from table

        Returns
        -------
        numpy array
            2D Array in column order
        """
        self.connect_to_production()
        query = 'select * from %s limit 1'%(table_name)
        stm = sqlalchemy.sql.text(query)
        columns_names = self.conn.execute(stm).keys()
        
        return columns_names
    
    def get_db_table_new(self, table_name, columns, limit = False):
        """
        Get table from db

        Parameters
        ----------
        table_name: str
            Name of table in DB
        columns: list
            Columns to extract from table

        Returns
        -------
        numpy array
            2D Array in column order
        """
        self.connect_to_production()
        
        if limit:
            query = 'select %s from %s limit %s'%(', '.join(columns), table_name, limit)
        
        else:
            query = 'select %s from %s'%(', '.join(columns), table_name)
        
        return np.transpose(
                    self.conn.execute(
                        sqlalchemy.sql.text(
                            query
                )
            ).fetchall()
        )
            