#!/usr/local/bin/python3.5 -u

from flask import Flask, session, escape, request, url_for, redirect, render_template, Markup, flash
from collections import defaultdict
import re, sys, os, glob, jinja2, codecs
import sqlite3 as sql
app = Flask( __name__ )

users_dir = "static/dataset-large"
db = "sql.db"
con = None
#

@app.route( '/test' )
def testView( ):
    return render_template( "error0.html", message="""#YOLOMAN. LOL LLOL OLLOOL OLOL
    @z5117924\n\n<script>alert(\"LOL\")</script>""" )

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

@app.route( '/users/<user_name>' )
def viewUsers( user_name=None ):

    if( user_name == None ):     # Show a random user.
        return render_template( "error.html", message="Please enter a username" )

    username = re.findall( r'z[0-9]{7}', user_name )    # Sanitize input
    if not username:                                    # No user with the username found
        return render_template( "error.html", message="Invalid username %s" % escape( user_name ) )

    u_Info = tuple( )
    p_Info = tuple( )
    m_Info = tuple( )
    c_Info = tuple( )
    if username[ 0 ] == getInfo( username[ 0 ], 'zID' ): # User exists
        con = sql.connect( db )
        con.row_factory = sql.Row
        cur = con.cursor( )
        cur.execute( "SELECT * FROM User WHERE zID=?", [ username[ 0 ] ] )
        result = cur.fetchone( )
        u_Info = result
        cur = con.cursor( )
        cur.execute( "SELECT * FROM Post WHERE zID=? ORDER BY time DESC", [ username[ 0 ] ] )
        result = cur.fetchall( )
        p_Info = result
        cur = con.cursor( )
        cur.execute( "SELECT mateID FROM Mate WHERE zID=?", [ username[ 0 ] ] )
        result = cur.fetchall( )
        m_Info = result
        cur = con.cursor( )
        cur.execute( "SELECT courseID FROM Course WHERE zID=?", [ username[ 0 ] ] )
        result = cur.fetchall( )
        c_Info = result

        con.close( )
    else:
        return render_template( "error.html", message="User %s does not exist." % escape( user_name ) )


    return render_template( "user.html", username=username[ 0 ], uInfo=u_Info, pInfo=p_Info, mInfo=m_Info, cInfo=c_Info )

@app.route('/search/<searchQuery>' )
def search( searchQuery ):
    if len( searchQuery ) > 2:
        u_Info = defaultdict( lambda: None )
        p_Info = defaultdict( lambda: None )
        c_Info = defaultdict( lambda: None )
        r_Info = defaultdict( lambda: None )
        print( "Search Query: " + searchQuery )
        con = sql.connect( db )
        con.row_factory = sql.Row
        cur = con.cursor( )
        cur.execute( "SELECT * FROM User WHERE full_name LIKE ?", [ '%'+searchQuery+'%' ] )
        result = cur.fetchall( )
        u_Info = result
        cur = con.cursor( )
        cur.execute( "SELECT * FROM Post WHERE message LIKE ?", [ '%'+searchQuery+'%' ] )
        result = cur.fetchall( )
        p_Info = result
        cur = con.cursor( )
        cur.execute( "SELECT * FROM Comment WHERE message LIKE ?", [ '%'+searchQuery+'%' ] )
        result = cur.fetchall( )
        c_Info = result
        cur = con.cursor( )
        cur.execute( "SELECT * FROM Reply WHERE message LIKE ?", [ '%'+searchQuery+'%' ] )
        result = cur.fetchall( )
        r_Info = result
        cur = con.cursor( )
        con.close( )
        return render_template( "search.html", uInfo=u_Info, pInfo=p_Info, cInfo=c_Info, rInfo=r_Info )
    else:
        flash( "Please enter at least three characters to search." )
        return render_template( "search.html" )



@app.route('/', methods=['GET', 'POST'])
def auth( ):
    if request.method == 'POST':
        formUser = request.form[ 'zID' ]             # Store username from form
        formPass = request.form[ 'password' ]
        print( "User: " + formUser + "Password: " + formPass )
        formUser = re.findall( r'z[0-9]{7}', formUser )   # Only find zID.
        if not formUser:
            return render_template( "login.html", message="Please enter your zID in the form: z5555555." )
        if not formPass:
            return render_template( "login.html", message="Please enter a password." )

        print( request.form )
        if request.form[ 'action' ] == 'Sign Up':
            flash( "Signing up!" )
            return render_template( "login.html" )
        else:
            con = sql.connect( db )
            cur = con.cursor( )
            query = "SELECT password FROM User WHERE zID = \"{}\"".format( formUser[ 0 ] )
            cur.execute( query )
            con.commit( )
            tmpPass = cur.fetchone( )
            if not tmpPass:
                flash( "The user does not exist" )
                return render_template( "login.html" );
            else:
                if tmpPass[ 0 ] == formPass:
                    session[ 'username' ] = formUser[ 0 ]
                    return redirect( url_for( 'viewUsers', user_name=formUser[ 0 ]) )
                else:
                    flash( "Incorrect password." )
                    return render_template( "login.html" )
        print( "Got to end?" )
        return render_template( "login.html", message="Dead" )
    else:
        return render_template( "login.html" )

@app.route( '/logout' )
def logout( ):
    session.pop( 'username', None )
    return redirect( url_for( 'auth' ) )

@app.route( '/profile_picture/<zID>' )
def showProfPict( zID ):
    username = re.findall( r'z[0-9]{7}', zID )    # Sanitize input
    if not username:                                    # No user with the username found
        return "<p>Invalid username %s</p>" % escape( zID )

    u_ToShow = os.path.join( users_dir, username[ 0 ] )
    imgLoc = os.path.join( u_ToShow, "profile.jpg" )
    if not os.path.isfile( imgLoc ):
        imgLoc = "http://placehold.it/250x250" # Change this to something sensible like a default picture.
    return redirect( imgLoc )

app.secret_key = 'YOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOOL!@#L:@!:'

def getSess( ):
    if 'username' in session:
        return session[ 'username' ]
    else:
        return None

def getInfo( zID, infoName="*" ):
    con = sql.connect( db )
    cur = con.cursor( )
    cur.execute( "SELECT {} FROM User WHERE zID = ?".format( infoName ), (zID, ) )
    con.commit( )
    result = cur.fetchone( )
    con.close( )
    return result[ 0 ]

""" getPost( tID, type )
    tID     - ID of post/comment/reply
    type    - 0 (post), 1 (comment), 2 (reply)
"""
def getPost( tID, type="Post" ):
    if type == "Post":
        colID = "zID"
    elif type == "Comment":
        colID = "pId"
    else:
        colID = "cID"
    con = sql.connect( db )
    con.row_factory = sql.Row
    cur = con.cursor( )
    cur.execute( "SELECT * FROM {} WHERE {} = ?".format( type, colID ), ( tID, ) )
    #print( "SELECT zID, message FROM {} WHERE {} = {}".format( type, colID, tID ) )
    con.commit( )
    result = cur.fetchall( )
    print( result )
    con.close( )
    return result

def doMention( longString ):
    longString = re.sub( r'@(z[0-9]{7})', r'<a href="\1">@\1</a>', str( jinja2.escape( longString ) ) )
    longString = re.sub( r'\\n', r'<br/>', longString )
    return Markup( longString )

# Credits to bbengfort from StackOverflow.
def dictFromRow( row ):
    return dict( zip( row.keys( ), row ) )

def main( ):

    # Make getInfo callable from Jinja.
    app.jinja_env.globals.update( getInfo=getInfo )
    app.jinja_env.globals.update( getSess=getSess )
    app.jinja_env.globals.update( dictFromRow=dictFromRow )
    app.jinja_env.globals.update( getPost=getPost )
    app.jinja_env.filters['doMention'] = doMention


    global con
    if os.path.isfile( db ): return
    # We don't need to recreate the database if it already exists.

    # print( "Creating Database..." )
    con = sql.connect( db )
    cur = con.cursor( )
    cur.execute( '''\
    CREATE TABLE IF NOT EXISTS "User"
        ("zID" TEXT PRIMARY KEY  NOT NULL  UNIQUE ,
        "full_name" TEXT,
        "email" TEXT,
        "password" TEXT,
        "birthday" TEXT,
        "home_suburb" TEXT,
        "program" TEXT )''' )
    cur.execute( ''' \
    CREATE TABLE "Post" ("pID" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE  DEFAULT 0,
    "zID" TEXT,
    "message" TEXT,
    "time" TEXT,
    "longitude" TEXT,
    "latitude" TEXT)''' )
    cur.execute( ''' \
    CREATE TABLE "Comment" ("cID" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE  DEFAULT 0,
    "pID" TEXT,
    "zID" TEXT,
    "message" TEXT,
    "time" TEXT)''' )
    cur.execute( ''' \
    CREATE TABLE "Reply" ("rID" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL UNIQUE  DEFAULT 0,
    "cID" TEXT,
    "pID" TEXT,
    "zID" TEXT,
    "message" TEXT,
    "time" TEXT)''' )
    cur.execute( '''CREATE TABLE "Mate" ("zID" TEXT NOT NULL , "mateID" TEXT)''' )
    cur.execute( '''CREATE TABLE "Course" ("zID" TEXT NOT NULL , "courseID" TEXT)''' )
    con.commit( );

    con.close( )
    parseDataset( )

def parseDataset( ):
    users = sorted( glob.glob( os.path.join( users_dir, "*" ) ) )
    con = sql.connect( db )
    pInc = 0
    cInc = 0
    for user in users:
        """
            Read user information from user.txt
        """
        u_FileDetails = os.path.join( user, "user.txt" )
        u_Info = defaultdict( lambda: None )
        uID = re.findall( r'z[0-9]{7}', user )
        with open( u_FileDetails ) as f:
            for line in f:
                line = line.rstrip( )   # Chomp
                lineInfo = line.split( "=", 1 ) # Split on '='
                if len( lineInfo ) != 2: break;     # Skip this line if it doesnt have what we need

                if lineInfo[ 0 ] == "mates" or lineInfo[ 0 ] == "courses":            # Special case for parsing mates/courses
                    lineInfo[ 1 ] = re.sub( r'(\[|\])', '', lineInfo[ 1 ] )
                    infoList = lineInfo[ 1 ].split( ', ' )
                    infoList.pop( )    # Remove last useless element

                    if lineInfo[ 0 ] == "mates":
                        for mate in infoList:  # Loop through the mates of each user
                            cur = con.cursor( )
                            cur.execute( "INSERT INTO Mate VALUES( ?, ? )", ( uID[ 0 ], mate ) )
                    else:
                        for course in infoList:
                            cur = con.cursor( )
                            cur.execute( "INSERT INTO Course VALUES( ?, ? )", ( uID[ 0 ], course ) )

                u_Info[ lineInfo[ 0 ] ] = lineInfo[ 1 ]

        cur = con.cursor( )
        # query = "INSERT INTO {} VALUES(\"{}\",\"{}\",\"{}\",\"{}\",\"{}\", \"{}\");".format( "User",     \
        #         u_Info[ "zid"], u_Info[ "full_name" ], u_Info[ "email" ], u_Info[ "password" ], \
        #         u_Info[ "birthday" ], u_Info[ "home_suburb" ] )
        # cur.execute( query )
        cur.execute( "INSERT INTO User VALUES (?, ?, ?, ?, ?, ?, ?)", ( u_Info[ "zid"],     \
                u_Info[ "full_name" ], u_Info[ "email" ], u_Info[ "password" ],             \
                u_Info[ "birthday" ], u_Info[ "home_suburb" ], u_Info[ "program" ] ) )
        """
            Read posts/comments/replies
            ( zID, message, time, from, longitude, latitude )
        """
        posts = sorted( glob.glob( os.path.join( user, "posts", "*" ) ) )
        for post in posts:
            p_Info = defaultdict( lambda: None )
            u_PostDetails = os.path.join( post, "post.txt" )
            with codecs.open( u_PostDetails, 'r', encoding='utf-8') as p:
                for line in p:
                    line = line.rstrip( )   # Chomp
                    lineInfo = line.split( "=", 1 ) # Split on '='
                    if len( lineInfo ) != 2: break;     # Skip this line if it doesnt have what we need

                    p_Info[ lineInfo[ 0 ] ] = lineInfo[ 1 ]

            pInc += 1
            cur = con.cursor( )
            cur.execute( "INSERT INTO Post VALUES( ?, ?, ?, ?, ?, ? )", (       \
                None, p_Info[ "from" ], p_Info[ "message" ], p_Info[ "time" ],  \
                p_Info[ "longitude" ], p_Info[ "latitude" ] ) )


            """ Store comments """
            if not os.path.isdir( os.path.join( post, "comments" ) ):      # Check if a comments folder exists.
                continue

            comments = sorted( glob.glob( os.path.join( post, "comments", "*" ) ) )
            for comment in comments:
                c_Info = defaultdict( lambda: None )
                u_CommDetails = os.path.join( comment, "comment.txt" )
                with codecs.open( u_CommDetails, 'r', encoding='utf-8') as p:
                    for line in p:
                        line = line.rstrip( )   # Chomp
                        lineInfo = line.split( "=", 1 ) # Split on '='
                        if len( lineInfo ) != 2: break;     # Skip this line if it doesnt have what we need

                        if( lineInfo[ 0 ] == "message" ):       # If we find z5555555, convert it into @z5555555
                            lineInfo[ 1 ] = re.sub( r'(z[0-9]{7})', r'@\1', lineInfo[ 1 ] )

                        c_Info[ lineInfo[ 0 ] ] = lineInfo[ 1 ]

                cInc += 1
                cur = con.cursor( )
                cur.execute( "INSERT INTO Comment VALUES( ?, ?, ?, ?, ? )", (       \
                    None, pInc, c_Info[ "from" ], c_Info[ "message" ],              \
                    c_Info[ "time" ] ) )

                if not os.path.isdir( os.path.join( comment, "replies" ) ):      # Check if a comments folder exists.
                    continue

                replies = sorted( glob.glob( os.path.join( comment, "replies", "*" ) ) )
                for reply in replies:
                    r_Info = defaultdict( lambda: None )
                    u_ReplDetails = os.path.join( reply, "reply.txt" )
                    with codecs.open( u_ReplDetails, 'r', encoding='utf-8') as p:
                        for line in p:
                            line = line.rstrip( )   # Chomp
                            lineInfo = line.split( "=", 1 ) # Split on '='
                            if len( lineInfo ) != 2: break;     # Skip this line if it doesnt have what we need

                            if( lineInfo[ 0 ] == "message" ):       # If we find z5555555, convert it into @z5555555
                                lineInfo[ 1 ] = re.sub( r'(z[0-9]{7})', r'@\1', lineInfo[ 1 ] )

                            r_Info[ lineInfo[ 0 ] ] = lineInfo[ 1 ]

                    cur = con.cursor( )
                    cur.execute( "INSERT INTO Reply VALUES( ?, ?, ?, ?, ?, ? )", (      \
                        None, cInc, pInc, r_Info[ "from" ], r_Info[ "message" ],        \
                        c_Info[ "time" ] ) )

    con.commit( )
    con.close( )

main( )

if __name__ == "__main__":
    app.run( debug=True, port=5000, host="0.0.0.0" )


# OLD CODE
"""
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
"""

"""
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
            if tmpPass[ 0 ] == formPass:
                session[ 'username' ] = formUser[ 0 ]
                return redirect( url_for( 'index' ) )
            else:
                return render_template( "error.html", message="Incorrect password." )
        return render_template( "error.html", message="Invalid error!" )
    elif 'username' in session:
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
"""
