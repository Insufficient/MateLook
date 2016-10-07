#!/usr/local/bin/python3.5 -u

import os
import cgitb; cgitb.enable( )
from wsgiref.handlers import CGIHandler
from matelook import app

#os.environ[ 'SERVER_NAME' ] = '127.0.0.1'
#os.environ[ 'SERVER_PORT' ] = '5000'
#os.environ[ 'PATH_INFO' ] = ""
#os.environ[ 'REQUEST_METHOD' ] = 'GET'
CGIHandler().run(app)
