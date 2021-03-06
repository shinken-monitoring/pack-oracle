#!/usr/bin/env python
############################## drop_invalid_synonyms #################
# Version : 1.0
# Date : Jun 29 2016
# Author  : Romain Forlot ( rforlot[At] yahoo [dot] com )
# Help : http://blog.claneys.com
# Licence : GPL - http://www.fsf.org/licenses/gpl.txt
#################################################################
#
# Help : ./drop_invalid_synonyms.py -c <connect-string> -u <oracle_user> -p <oracle_password> -s <$SERVICESTATE$ macro> -t <$SERVICESTATETYPE$ macro>
#
# This plugin is meant to be used with Oracle-invalid-objects service 
# which at CRITICAL SOFT state will seek and drop invalid synonyms in db

import os, re, sys

# You'll need to install this module : easy_install cx_Oracle
# Prior to be able to install it, you must install python-devel package
# relative to your GNU/linux distro
import cx_Oracle

from subprocess import Popen, PIPE
from optparse import OptionParser


OK = 0
WARNING = 1
CRITICAL = 2
UNKNOWN = 3

VERSION = '1.0'

class OracleDB():

    def __init__(self, connect, username, password, service_state, service_state_type):
        self.connect = connect
        self.username = username
        self.password = password
        self.service_state = service_state
        self.service_state_type = service_state_type
        

    def do_connect(self, method="cx_Oracle"):
        '''
        Initialize sqlplus connection to
        the oracle database.
        method : support only oracle by now, using sqlplus.
        OHOME : ORACLE_HOME, default: retrieve ORACLE_HOME environment variable.
        user : user used to connect
        password : password of user
        base : name of database to connect to. With an Oracle DB it is the connect string
        '''
    
        # Connection selection dictionnary
        # Only sqlplus for now.
        connection = { 'cx_Oracle' : self.cx_Oracle() }
        try:
            res = connection[method]
            return res
        except KeyError:
            sys.exit('Wrong connection method')
    
    def cx_Oracle(self):
            c = self.username+'/'+self.password+'@'+self.connect
            try:
                session = cx_Oracle.connect(c)
                return session
            except (OSError, ValueError) as err:
                sys.exit("Connection got a problem : %s" % err.strerror)
    
    @staticmethod
    def execute_request(session, request):
        '''
        Execute a SQL query and return result into a list
        session: Oracle DB session opened
        request: SQL request to execute
        '''

        cursor = session.cursor()
        
        try:
            cursor.execute(request)
        except cx_Oracle.DatabaseError as e:
            print e
            sys.exit('Error on request execution')

			try:
				return cursor.fetchall()
			except cx_Oracle.InterfaceError as e:
				pass

    def get_synonyms2drop(self, session):
        '''
        Get invalid synonyms to drop
        session : session object connected to the database.
        '''

        request_private = 'SELECT \'DROP SYNONYM \'||DS.OWNER||\'.\'||DS.SYNONYM_NAME FROM DBA_SYNONYMS DS, DBA_OBJECTS DO WHERE DS.TABLE_OWNER = DO.OWNER(+) AND DO.OWNER IS NULL AND DS.TABLE_NAME = DO.OBJECT_NAME(+) AND DO.OBJECT_NAME IS NULL AND DS.OWNER NOT IN (\'SYS\',\'PUBLIC\') AND DS.TABLE_OWNER NOT IN (\'SYS\',\'SYSTEM\') AND DS.DB_LINK IS NULL ORDER BY DS.TABLE_OWNER, DS.TABLE_NAME'
        request_public = 'SELECT \'DROP PUBLIC SYNONYM \'||OBJECT_NAME FROM dba_objects WHERE status = \'INVALID\' AND object_name NOT LIKE \'BIN$%\'AND object_type = \'SYNONYM\'AND owner NOT IN (\'SYS\', \'SYSTEM\')'
        invalid_private_synonyms = self.execute_request(session, request_private)
        invalid_public_synonyms = self.execute_request(session, request_public)

        requests = []

        for request in invalid_private_synonyms:
           requests.append(request[0])
        for request in invalid_public_synonyms:
           requests.append(request[0])

        return requests

    def process_invalid_synonyms(self, session):
        '''
        Process requests dropping synonyms from create_drop_synonyms_request method
        synonyms2drop: list or tuple of requests that drop synonyms
        session: Oracle opened session
        '''

        synonyms2drop_requests = self.get_synonyms2drop(session)

        for request in synonyms2drop_requests:
            if not request.startswith('DROP SYNONYM') and not request.startswith('DROP PUBLIC SYNONYM'):
                print('Very wrong request trying to be executed : %s.' % request )
                exit(CRITICAL)
            
            print('Dropping %s' % request.split(' ')[2])
            self.execute_request(session, request)

    def main(self):
        if self.service_state == 'CRITICAL' or self.service_state == 'WARNING':
            if self.service_state_type == 'SOFT':
                print('Detected some invalid objects, trying to drop invalid synonyms.')
                session = self.do_connect()
                self.process_invalid_synonyms(session)
                exit(OK) 

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option('-c', '--connect', dest='connect', help='Connect string to Sydel Univers Oracle Database. See your tnsnames.ora')
    parser.add_option('-u', '--username', dest='username', help='Oracle user to connect at database')
    parser.add_option('-p', '--password', dest='password', help='Oracle password')
    parser.add_option('-s', '--service-state', dest='service_state', help='Service state from $SERVICESTATE$ macro')
    parser.add_option('-t', '--service-state-type', dest='service_state_type', help='Service state type from $SERVICESTATETYPE$ macro')

    opts, args = parser.parse_args()

    if args:
        parser.error("does not take any positional arguments")
    
    OracleDB(**vars(opts)).main()
