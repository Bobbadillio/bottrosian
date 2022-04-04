# Adapted from https://softwareengineering.stackexchange.com/questions/200522/how-to-deal-with-database-connections-in-a-python-library-module
import psycopg2
import logging

class Postgres(object):
    _instance = None

    def __new__(cls,url):
        if cls._instance is None:
            cls._instance = object.__new__(cls)
            try:
                connection = Postgres._instance.connection = psycopg2.connect(url, sslmode='require')
                cursor = Postgres._instance.cursor = connection.cursor()
                cursor.execute('SELECT VERSION()')
                db_version = cursor.fetchone()

            except Exception as error:
                logging.log(logging.WARNING, 'Error: connection not established {}'.format(error))
                Postgres._instance = None

            else:
                logging.log(logging.INFO,'connection established\n{}'.format(db_version[0]))

        return cls._instance

    def __init__(self,url):
        self.connection = self._instance.connection
        self.cursor = self._instance.cursor

    def query(self, query, params=None):
        try:
            with self.connection, self.connection.cursor() as cursor:
                cursor.execute(query,params)
        except Exception as error:
            logging.log(logging.WARNING, 'error execting query "{}", error: {}'.format(query, error))
            return None
        else:
            return result

    def __del__(self):
        self.connection.close()
        self.cursor.close()