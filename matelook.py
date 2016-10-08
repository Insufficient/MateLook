#!/usr/local/bin/python3.5 -u

from flask import Flask, session, escape, request, url_for, redirect, render_template
from collections import defaultdict
import re, sys, os, glob
import sqlite3 as sql
app = Flask( __name__ )

users_dir = "static/dataset-large"
db = "sql.db"
con = None
#

@app.route( '/', methods=['GET', 'POST'] )
def index( ):
    if request.method == 'POST':
        formUser = request.form[ 'username' ]             # Store username from form
        formPass = request.form[ 'password' ]

        formUser = re.findall( r'z[0-9]{7}', formUser )   # Only find zID.
        if not formUser:
            return render_template( "error.html", message="Please enter your zID in the form: z5555555." )
            #return "Please enter your zID in the form: z5555555."
        if not formPass:
            return render_template( "error.html", message="Please enter a password." )

        con = sql.connect( db )
        cur = con.cursor( )
        query = "SELECT password FROM User WHERE zID = \"{}\"".format( formUser[ 0 ] )
        cur.execute( query )
        con.commit( )
        tmpPass = cur.fetchone( )
        if not tmpPass:
            return render_template( "error.html", message="The user does not exist" );
        else:
            print( "[{}]\n\tForm: {}\n\tActual: {}".format( formUser, formPass, tmpPass[ 0 ] ) )
            if tmpPass[ 0 ] == formPass:
                session[ 'username' ] = formUser[ 0 ]
                return redirect( url_for( 'index' ) )
            else:
                return render_template( "error.html", message="Incorrect password." )
        return render_template( "error.html", message="Invalid error!" )

    if 'username' in session:
        return ''' \
        <h2>Logged in as %s</h2>
        <a href="logout"><button>Logout</button></a>
        ''' % escape( session[ 'username'] )
    else:
        return '''
            <form action="" method="post">
                <label>Username</label>
                <p><input type=text name=username>
                <p><input type=password name=password>
                <p><input type=submit value=Login>
            </form>
        '''

@app.route( '/user/<user_name>' )
def viewUser( user_name=None ):

    if( user_name == None ):     # Show a random user.
        return "<p>Please enter a username</p>"

    username = re.findall( r'z[0-9]{7}', user_name )    # Sanitize input
    if not username:                                    # No user with the username found
        return "<p>Invalid username %s</p>" % escape( user_name )

    u_ToShow = os.path.join( users_dir, username[ 0 ] )
    u_FileName = os.path.join( u_ToShow, "user.txt" )

    if not os.path.isfile( u_FileName ):
        return "<p>User does not exist.%s</p>" % escape( user_name )

    with open( u_FileName ) as f:
        u_Info = defaultdict( )
        for line in f:
            line = line.rstrip( )   # Chomp
            lineInfo = line.split( "=", 1 ) # Split on '='
            if len( lineInfo ) != 2: break;     # Skip this line if it doesnt have what we need

            if lineInfo[ 0 ] == "mates":
                lineInfo[ 1 ] = re.sub( r'(\[|\])', '', lineInfo[ 1 ] )
                mates = lineInfo[ 1 ].split( ', ' )
                mates.pop( )    # Remove last useless element

                u_Info[ lineInfo[ 0 ] ] = mates
            else:
                u_Info[ lineInfo[ 0 ] ] = lineInfo[ 1 ]

    #print( u_Info );
    imgLoc = os.path.join( u_ToShow, "profile.jpg" )
    if not os.path.isfile( imgLoc ):
        imgLoc = None


    return render_template( "user.html", username=username[ 0 ], uInfo=u_Info, img=imgLoc )


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['username'] = request.form['username']
        return redirect(url_for('index'))
    else:
        return '<h1>Sorry bicboi.</h1>'

@app.route( '/logout' )
def logout( ):
    session.pop( 'username', None )
    return redirect( url_for( 'index' ) )

app.secret_key = 'YOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOL!@#L:@!:'


def main( ):
    global con
    if os.path.isfile( db ): return
    # We don't need to recreate the database if it already exists.

    print( "Creating Database..." )
    con = sql.connect( db )
    cur = con.cursor( )
    cur.execute( '''\
    CREATE TABLE IF NOT EXISTS "User"
        ("zID" TEXT PRIMARY KEY  NOT NULL  UNIQUE ,
        "full_name" TEXT,
        "email" TEXT,
        "password" TEXT,
        "birthday" TEXT,
        "home_suburb" TEXT )''' )
    cur.execute('SELECT SQLITE_VERSION()')
    data = cur.fetchone()
    print( "SQLite version: %s" % data )

    con.close( )
    parseDataset( )

def parseDataset( ):
    users = sorted( glob.glob( os.path.join( users_dir, "*" ) ) )
    con = sql.connect( db )
    for user in users:
        print( "User: " + user )
        u_FileName = os.path.join( user, "user.txt" )
        u_Info = defaultdict( lambda: None )
        with open( u_FileName ) as f:
            for line in f:
                line = line.rstrip( )   # Chomp
                lineInfo = line.split( "=", 1 ) # Split on '='
                if len( lineInfo ) != 2: break;     # Skip this line if it doesnt have what we need

                if lineInfo[ 0 ] == "mates" or lineInfo[ 0 ] == "courses" or lineInfo[ 0 ] == "programs": continue
                u_Info[ lineInfo[ 0 ] ] = lineInfo[ 1 ]

        cur = con.cursor( )
        query = "INSERT INTO {} VALUES(\"{}\",\"{}\",\"{}\",\"{}\",\"{}\", \"{}\");".format( "User",     \
                u_Info[ "zid"], u_Info[ "full_name" ], u_Info[ "email" ], u_Info[ "password" ], \
                u_Info[ "birthday" ], u_Info[ "home_suburb" ] )
        print( "Query: " + query )
        cur.execute( query )

    con.commit( )
    con.close( )

main( )

if __name__ == "__main__":
    app.run( debug=True, port=5000, host="0.0.0.0" )
