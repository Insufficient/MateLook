#!/usr/bin/env python3.5 -u
#!/usr/local/bin/python3.5 -u

from flask import Flask, session, escape, request, url_for, redirect, render_template, Markup, flash, send_file
from collections import defaultdict
import re, sys, os, glob, jinja2, io
import sqlite3 as sql
import datetime
app = Flask( __name__ )
#app.config[ 'send_file_max_age_default' ]

users_dir = "static/dataset-large"
db = "sql.db"
con = None
#

"""
    Serve static files
"""
@app.route('/static/<path:path>')
def send_static_file(path):
    return send_from_directory('static', path)

@app.route( '/test' )
def testView( ):
    con = sql.connect( db )
    cur = con.cursor( )
    cur.execute( "SELECT mateID FROM Mate WHERE zID = ?", [ "z5013363", ] )
    results = cur.fetchall( )
    string = [', '.join(w) for w in results]
    string = '","'.join( string )
    mates = "(\"{}\")".format( string )
    return render_template( "error0.html", message=mates )

"""
    View a user's profile page.
"""
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

        cur.execute( "SELECT mateID FROM Mate WHERE zID = ?", [ username[ 0 ] ] )
        results = cur.fetchall( )
        string = [', '.join(w) for w in results]
        string = '","'.join( string )
        mates = "(\"{}\",\"{}\")".format( username[ 0 ], string )
        # Get their mates and store it into a string.
        # cur = con.cursor( )
        cur.execute( "SELECT * FROM Post WHERE zID IN {} OR MESSAGE LIKE ? ORDER BY time DESC LIMIT 10, 5".format( mates ), [ "%" + username[ 0 ] + "%" ] )
        # cur.execute( "SELECT * FROM Post WHERE zID IN {} ORDER BY time DESC".format( mates ) )
        result = cur.fetchall( )
        p_Info = result
        # cur = con.cursor( )
        cur.execute( "SELECT mateID FROM Mate WHERE zID=?", [ username[ 0 ] ] )
        result = cur.fetchall( )
        m_Info = result
        # cur = con.cursor( )
        cur.execute( "SELECT courseID FROM Course WHERE zID=?", [ username[ 0 ] ] )
        result = cur.fetchall( )
        c_Info = result

        con.close( )
    else:
        return render_template( "error.html", message="User %s does not exist." % escape( user_name ) )
    return render_template( "user.html", username=username[ 0 ], uInfo=u_Info, pInfo=p_Info, mInfo=m_Info, cInfo=c_Info )

"""
    Edit a user's information
"""
@app.route( '/edit', methods=[ 'POST' ] )
def editInfo( ):
    if request.method != 'POST':
        return redirect( url_for( 'auth' ) )

    zID = request.form[ 'zID' ]
    full_name = request.form[ 'full_name' ]
    email = request.form[ 'email' ]
    password = request.form[ 'password' ]
    birthday = request.form[ 'birthday' ]
    home_suburb = request.form[ 'home_suburb' ]
    program = request.form[ 'program' ]
    blurb = request.form[ 'blurb' ]

    if not zID or not full_name or not email or not password:
        flash( "zID, full name, email and password are all required." )
        return redirect( url_for( 'viewUsers', user_name=zID ) )

    if getSess( ) != zID:
        flash( "You cannot edit another users' information." )
        return redirect( url_for( 'viewUsers', user_name=zID ) )


    con = sql.connect( db )
    cur = con.cursor( )
    cur.execute( "SELECT zID FROM User WHERE zID=? AND password=?", ( zID, password ) )
    results = cur.fetchone( )
    if not results:
        flash( "You have entered the incorrect password." )
        return redirect( url_for( 'viewUsers', user_name=zID ) )

    cur.execute( "UPDATE User SET zID=?, full_name=?, email=?, birthday=?,      \
                    home_suburb=?, program=?, blurb=? WHERE zID=?",             \
                    ( zID, full_name, email, birthday, home_suburb, program,    \
                    blurb, zID ) )
    con.commit( )
    return redirect( url_for( 'viewUsers', user_name=zID ) )

@app.route( '/delete', methods=[ 'POST' ] )
def delete( ):
    cParent = request.form[ 'parent' ]
    cType = request.form[ 'type' ]
    zID = request.form[ 'zID' ]

    if 'Post' in cType:
        colName = 'pID'
        # Check if session username is the parent username.
    elif 'Comment' in cType:
        colName = 'cID'
    elif 'Reply' in cType:
        colName = 'rID'
    else:
        return "You cannot access that column."

    if zID != getSess( ):
        return "You cannot delete this comment/post/reply."

    con = sql.connect( db )
    cur = con.cursor( )
    cur.execute( "SELECT zID FROM {} WHERE {} = ?".format( cType, colName ), [ cParent ] )
    print( "SELECT zID FROM {} WHERE {} = {}".format( cType, colName, cParent ) )
    results = cur.fetchone( )
    if not results:
        return "The comment/post/reply does not exist."

    try:
        if 'Post' in cType:
            cur.execute( "DELETE FROM Comment WHERE pID = ?", [ cParent ] )
            cur.execute( "DELETE FROM Reply WHERE pID = ?", [ cParent ] )
        if 'Comment' in cType:
            cur.execute( "DELETE FROM Reply WHERE cID = ?", [ cParent ] )
            
        cur.execute( "DELETE FROM {} WHERE {} = ?".format( cType, colName ), [ cParent ] )
    except sqlite3.Error as e:
        print( "An error occurred!", e.args[ 0 ] )

    con.commit( )
    con.close( )
    return "You have deleted the comment."

"""
    Create posts/comments/replies
"""
@app.route( '/create', methods=[ 'POST' ] )
def create( ):
    cType = request.form[ 'type' ]              # Post, Comment or Reply
    cParent = request.form[ 'parent' ]
    cMessage = request.form[ 'message' ]
    zID = request.form[ 'zID' ]                 # Person making the post

    if not cMessage or not cParent or len( cMessage ) == 0:
        flash( "Please enter a message." )
        return render_template( "user.html" )

    if 'Post' in cType:
        colName = 'zID'
        # Check if session username is the parent username.
    elif 'Comment' in cType:
        colName = 'pID'
        cType = 'Post'
    elif 'Reply' in cType:
        colName = 'cID'
        cType = 'Comment'
    else:
        flash( "You cannot access that column.")
        return render_template( "user.html" )

    con = sql.connect( db )
    cur = con.cursor( )
    cur.execute( "SELECT zID FROM {} WHERE {} = ?".format( cType, colName ), [ cParent ] )
    con.commit( )
    result = cur.fetchone( )
    if not result:
        flash( "You cannot make a post/comment/reply to that parent." )
        return render_template( "user.html" )

    cDate = datetime.datetime.now( )
    # We need to preserve newlines and etc somehow.

    if colName == 'zID':                            # New post
        cur.execute( "INSERT INTO Post VALUES (?,?,?,?,?,?)", (   \
            None, cParent, cMessage, cDate, None, None ) )
    elif colName == 'pID':
        cur.execute( "INSERT INTO Comment VALUES (?,?,?,?,?)", (   \
            None, cParent, zID, cMessage, cDate ) )
    elif colName == 'cID':
        cur = con.cursor( )
        cur.execute( "SELECT cID FROM Comment WHERE pID = ?", [ cParent ] )
        result = cur.fetchone( )
        if not result:
            flash( "You cannot make a post/comment/reply to that parent." )
            return render_template( "user.html" )
        else:
            cur.execute( "INSERT INTO Reply VALUES (?,?,?,?,?,?)", (   \
                None, result[ 0 ], cParent, zID, cMessage, cDate ) )

    con.commit( )
    con.close( )
    return redirect( url_for( 'viewUsers', user_name=cParent ) )



"""
    Search AJAX page
"""
@app.route('/search', methods=['POST'] )
def search( ):
    searchQuery = request.form[ 'search' ]
    if searchQuery != None and len( searchQuery ) > 2:
        u_Info = defaultdict( lambda: None )
        p_Info = defaultdict( lambda: None )
        c_Info = defaultdict( lambda: None )
        r_Info = defaultdict( lambda: None )
        # print( "Search Query: " + searchQuery )
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


"""
    Login page
"""
@app.route('/', methods=['GET', 'POST'])
def auth( ):
    loggedIn = getSess( )
    if loggedIn != None:                                # Redirect users to view page if they are logged in
        return redirect( url_for( 'viewUsers', user_name=loggedIn ) )
    if request.method == 'POST':
        formUser = request.form[ 'zID' ]                    # Store username from form
        formPass = request.form[ 'password' ]               # Store password from form
        formEmail = request.form[ 'email' ]                 # Store email from form
        formName = request.form[ 'name' ]

        formUser = re.findall( r'z[0-9]{7}', formUser )     # Store only zID

        if not formUser:
            flash( "Please enter your zID in the form: z5555555." )
            return render_template( "login.html" )
        if not formPass:
            flash( "Please enter a password." )
            return render_template( "login.html", user=formUser[ 0 ] )

        if request.form[ 'action' ] == 'Sign Up':
            if not formEmail:
                flash( "Please enter a email!" )
                return render_template( "login.html", user=formUser[ 0 ], pw=formPass )

            con = sql.connect( db )
            cur = con.cursor( )
            cur.execute( "SELECT zID FROM User WHERE zID=?", [ formUser[ 0 ] ] )
            con.commit( )
            result = cur.fetchone( )
            if not result:
                try:
                    cur.execute( "INSERT INTO User VALUES (?, ?, ?, ?, ?, ?, ?)", ( \
                    formUser[ 0 ], formName, formEmail, formPass, None, None, None ) )
                    con.commit( )
                    return redirect( url_for( 'viewUsers', user_name=formUser[ 0 ] ) )
                except sqlite3.Error as e:
                    print( "An error occurred!", e.args[ 0 ] )
            else:
                flash( "The user " + formUser[ 0 ] + " already exists." )
                return render_template( "login.html" )

            flash( "Signing up!" )
            return render_template( "login.html" )
        else:
            con = sql.connect( db )
            cur = con.cursor( )
            # Pls change
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
                    return redirect( url_for( 'viewUsers', user_name=formUser[ 0 ] ) )
                else:
                    flash( "Incorrect password." )
                    return render_template( "login.html", user=formUser[ 0 ] )
        return render_template( "login.html", message="Dead" )
    else:
        return render_template( "login.html" )

"""
    Logout page
"""
@app.route( '/logout' )
def logout( ):
    session.pop( 'username', None )
    return redirect( url_for( 'auth' ) )

"""
    Render posts (AJAX)
"""
@app.route( '/post', methods=[ 'POST' ] )
def viewPost( ):
    user_name = request.form[ 'zID' ]
    pageNum = request.form[ 'pageNum' ]

    if( user_name == None ):     # Show a random user.
        return render_template( "error.html", message="Please enter a username" )

    username = re.findall( r'z[0-9]{7}', user_name )    # Sanitize input
    if not username:                                    # No user with the username found
        return render_template( "error.html", message="Invalid username %s" % escape( user_name ) )

    p_Info = tuple( )
    if username[ 0 ] == getInfo( username[ 0 ], 'zID' ): # User exists
        con = sql.connect( db )
        con.row_factory = sql.Row
        cur = con.cursor( )
        cur.execute( "SELECT mateID FROM Mate WHERE zID = ?", [ username[ 0 ] ] )
        results = cur.fetchall( )
        string = [', '.join(w) for w in results]
        string = '","'.join( string )
        mates = "(\"{}\",\"{}\")".format( username[ 0 ], string )
        # Get their mates and store it into a string.
        cur.execute( "SELECT * FROM Post WHERE zID IN {} OR MESSAGE LIKE ? ORDER BY time DESC LIMIT {}, 10".format( mates, pageNum ), [ "%" + username[ 0 ] + "%" ] )
        result = cur.fetchall( )
        p_Info = result

        con.close( )
    else:
        return render_template( "error.html", message="User %s does not exist." % escape( user_name ) )
    return render_template( "post.html", pInfo=p_Info )

"""
    Serve profile images statically
"""
@app.route( '/profile_picture/<zID>' )
def showProfPict( zID ):
    username = re.findall( r'z[0-9]{7}', zID )                      # Sanitize input
    if not username:                                                # No user with the username found
        return "<p>Invalid username %s</p>" % escape( zID )

    u_ToShow = os.path.join( users_dir, username[ 0 ] )
    imgLoc = os.path.join( u_ToShow, "profile.jpg" )
    if not os.path.isfile( imgLoc ):
        #imgLoc = "http://placehold.it/250x250" # Change this to something sensible like a default picture.
        imgLoc = os.path.join( users_dir, "default.png" )
    return send_file( imgLoc, mimetype='image/jpg' )

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
    if result:
        return result[ 0 ]
    else:
        return None

""" getPost( tID, type )
    tID     - ID of post/comment/reply
    zID     - zID of user that made this post.
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
    # print( result )
    con.close( )
    return result

def doMention( longString ):
    longString = re.sub( r'@(z[0-9]{7})', r'<a href="\1">@\1</a>', str( jinja2.escape( longString ) ) )
    matches = re.findall( r'>@(z[0-9]{7})<', longString )
    for match in matches:
        swapFrom = ">@{}<".format( match )
        swapInto = ">@{}<".format( getInfo( match, "full_name" ) )
        longString = re.sub( swapFrom, swapInto, longString )

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
            with io.open( u_PostDetails, 'r', encoding='utf-8') as p:
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
                with io.open( u_CommDetails, 'r', encoding='utf-8') as p:
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
                    with io.open( u_ReplDetails, 'r', encoding='utf-8') as p:
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
    app.run( debug=True, port=5000, host="0.0.0.0", threaded=True) # 0.0.0.0
