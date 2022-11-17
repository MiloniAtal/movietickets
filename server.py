
"""
Columbia's COMS W4111.001 Introduction to Databases
Example Webserver
To run locally:
    python3 server.py
Go to http://localhost:8111 in your browser.
A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""
from html import escape
import os
  # accessible as a variable in index.html:
from sqlalchemy import *
from sqlalchemy.pool import NullPool
import flask
from flask import Flask, request, render_template, g, redirect, Response, session
from datetime import date
from datetime import date
from psycopg2.extensions import AsIs



tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)
app.secret_key = 'BAD_SECRET_KEY'


#
# The following is a dummy URI that does not connect to a valid database. You will need to modify it to connect to your Part 2 database in order to use the data.
#
# XXX: The URI should be in the format of:
#
#     postgresql://USER:PASSWORD@34.75.94.195/proj1part2
#
# For example, if you had username gravano and password foobar, then the following line would be:
#
#     DATABASEURI = "postgresql://gravano:foobar@34.75.94.195/proj1part2"
#
DATABASEURI = "postgresql://vw2283:6795@34.75.94.195/proj1part2"


#
# This line creates a database engine that knows how to connect to the URI above.
#
engine = create_engine(DATABASEURI)

#
# Example of running queries in your database
# Note that this will probably not work if you already have a table named 'test' in your database, containing meaningful data. This is only an example showing you how to run queries in your database using SQLAlchemy.
#
engine.execute("""CREATE TABLE IF NOT EXISTS test (
  id serial,
  name text
);""")
engine.execute("""INSERT INTO test(name) VALUES ('grace hopper'), ('alan turing'), ('ada lovelace');""")


@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request.

  The variable g is globally accessible.
  """
  try:
    g.conn = engine.connect()
  except:
    print("uh oh, problem connecting to database")
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't, the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass

@app.route('/signup', methods=['GET','POST'] )
def signup():
  if(request.method == 'POST'):
    name,email,dob,address,password = request.form.get("name", ""), request.form.get("email",""), request.form.get("dob",""), request.form.get("address",""), request.form.get("password","")
    print(name,email,dob,address,password)
    numUsers = 0
    cursor = g.conn.execute("SELECT MAX(uid) from users")
    for res in cursor:
      numUsers = res['max']+1
    cursor.close()

    cursor = g.conn.execute("INSERT into users values(%(uid)s, %(name)s, %(address)s, %(dob)s, %(email)s)", {'uid':numUsers, 'name':name, 'address':address, 'dob':dob, 'email':email})
    cursor.close()

    return redirect('/login')

    
  return render_template('/signup.html')
  

@app.route('/home')
def home():
  session['url'] = request.url
  cursor = g.conn.execute("SELECT name,stars,mid FROM movie")
  data = []
  for result in cursor:
    data.append({'name':result['name'], 'stars':result['stars'], 'mid':result['mid']})  # can also be accessed using result[0]
  cursor.close()

  cursor = g.conn.execute("SELECT name,location,vid FROM venue")
  data2 = []
  for result in cursor:
    data2.append({'name':result['name'], 'location':result['location'], 'vid':result['vid']})  # can also be accessed using result[0]
  cursor.close()

  cursor = g.conn.execute("SELECT mid, COUNT(*) AS count FROM Ticket GROUP BY mid ORDER BY count DESC LIMIT 2")
  famous_movie = []
  for result in cursor:
    mid = result["mid"]
    cursor2 = g.conn.execute("SELECT name FROM Movie WHERE mid=%s",(mid,))
    for res in cursor2:
      name = res["name"]
    famous_movie.append([mid, name, result["count"]])
  cursor2.close()
  cursor.close()

  cursor = g.conn.execute("SELECT vid, COUNT(*) AS count FROM Ticket GROUP BY vid ORDER BY count DESC LIMIT 2")
  famous_venue = []
  for result in cursor:
    vid = result["vid"]
    cursor2 = g.conn.execute("SELECT name, location FROM Venue WHERE vid=%(vid)s",{'vid':vid})
    for res in cursor2:
      name = res["name"]
      location = res["location"]
    famous_venue.append([vid, name, result["count"], location])
  cursor2.close()
  cursor.close()
  context = dict(movies=data, venues=data2, famous_movie=famous_movie, famous_venue=famous_venue)
  return render_template("home.html", **context)

@app.route('/home', methods=['POST'])
def home_post():
  session['url'] = request.url
  print("request form", request.form)
  mid = request.form.get("Movie", "")
  vid = request.form.get("Venue", "")

  if(mid == "Choose Movie" and len(vid) > 0):
    redirect_url = "venue_search/"+vid
    return redirect(redirect_url)

  if(len(mid) > 0 and vid == "Choose Venue"):
    redirect_url = "movie_info/"+mid
    return redirect(redirect_url)

  if(len(mid) > 0 and len(vid) > 0):
    redirect_url = "venue_search/"+vid+"/"+mid
    return redirect(redirect_url)



@app.route('/login')
def login():
  return render_template("login.html")

@app.route('/logout')
def logout():
  if("url" in session.keys()):
    url = session['url']
  else:
    url = "/home"
  session.clear()
  return redirect(url)

  

@app.route('/login', methods=['POST'])
def login_post():
  email = request.form.get('email')
  password = request.form.get('password')
  query_string = "SELECT name, uid FROM users where email = %s"
 
  cursor = g.conn.execute(query_string, (email,))
  names = []
  ids = []
  for result in cursor:
    names.append(result['name'])
    ids.append(result['uid'])

  if(len(names) == 0):
    return render_template("login.html")

  if(len(names) == 1):
    session['id'] = ids[0]
    session['name'] = names[0]

  if("url" in session.keys()):
    return redirect(session['url'])
  else:
    return redirect("/home")

@app.route('/movie_info/<mid>')
def movieInfo(mid):

  session['url'] = request.url
  cursor = g.conn.execute("SELECT * from Movie M where M.mid = %(mid)s",{'mid':mid}) 
  data = []
  reviews = []
  for result in cursor:
    data.append(result)
  cursor.close()

  cursor = g.conn.execute("SELECT r.rid, r.text, r.time, u.name from Reviews r NATURAL JOIN Users u WHERE r.mid=%(mid)s",{'mid':mid})
  for result in cursor:
    cursor2 = g.conn.execute("SELECT COUNT(*) from Likes l where l.rid = %s",(result['rid']))
    liked = 0
    
    if('id' in session):
      cursor3 = g.conn.execute("SELECT COUNT(*) from Likes l where l.rid=%s and l.uid=%s",(result['rid'],session['id']))
      for cnt in cursor3:
        if(cnt['count'] == 1): 
          liked = 1

    numLikes = 0
    for cnt in cursor2:
      numLikes = cnt['count']
    reviews.append({'uname':result['name'], 'text':result['text'], 'time':result['time'], 'rid':result['rid'], 'numLikes':numLikes, 'liked':liked})
  cursor.close
  
  cursor = g.conn.execute("SELECT genre FROM Movie where mid=%(mid)s",{'mid':mid})
  genre_list = []

  for result in cursor:
    if(result["genre"]):
      genres = result["genre"]
      genre_list = [word.strip() for word in genres.split(',')]
  reco_mid = []
  for genre in genre_list:
    cursor = g.conn.execute("SELECT mid FROM Movie where genre like '%%%(genre)s%%'",{'genre':AsIs(genre)})
    for result in cursor:
      reco_mid.append(result["mid"])
  reco_mid = list(set(reco_mid))
  recos = []
  for rmid in reco_mid:
    if(int(rmid) != int(mid)):
      cursor = g.conn.execute("SELECT name FROM Movie WHERE mid=%(mid)s",{'mid':rmid})
      for result in cursor:
        recos.append([rmid, result["name"]])
  cursor.close()

  context = dict(movie = data[0], reviews=reviews, recos=recos)
  return render_template("movie_info.html", **context)


@app.route('/profile')
def profile():
  if('id' not in session):
    return redirect('/login')

    
  uid = session['id']
  bookings = []
  info = []
  reviews = []
  likedReviews = []

  cursor = g.conn.execute("SELECT * from users WHERE uid=%(uid)s",{'uid':uid})
  for res in cursor:
    info = {'name':res['name'], 'address':res['address'], 'dob':res['dob'], 'email':res['email']}
  cursor.close()

  cursor = g.conn.execute("SELECT r.text, m.name FROM reviews r, movie m, likes l WHERE l.uid=%(uid)s AND l.rid=r.rid",{'uid':uid})
  for res in cursor:
    likedReviews.append({'text':res['text'], 'moviename':res['name']})
  cursor.close()
  
  cursor = g.conn.execute("SELECT r.text, r.time, m.name FROM reviews r NATURAL JOIN movie m WHERE r.uid=%(uid)s",{'uid':uid})
  for res in cursor:
    reviews.append({'text':res['text'], 'date':res['time'], 'moviename':res['name']})
  cursor.close()

  cursor = g.conn.execute("SELECT distinct m.name AS moviename, v.name as venuename, t.time from movie m, venue v, ticket t WHERE m.mid = t.mid AND v.vid = t.vid AND t.uid = %(uid)s",{'uid':uid})
  for res in cursor:
    bookings.append({'venue':res['venuename'], 'moviename':res['moviename'], 'time':res['time']})
  cursor.close()

  context = dict(bookings = bookings, likedReviews = likedReviews, info = info, reviews = reviews)
  
  return render_template("user_profile.html", **context)



@app.route('/write_review/<mid>', methods=['POST'])
def writeReview(mid): 
  reviewText = request.form['review']
  numReviews = 0
  cursor = g.conn.execute("SELECT MAX(rid) from reviews")
  for res in cursor:
    numReviews = res['max']+1
  cursor.close()

  cursor = g.conn.execute("INSERT into reviews(rid,text,time,uid,mid) values (%(numReviews)s, %(reviewText)s, %(date)s, %(uid)s, %(mid)s)",{'numReviews':numReviews, 'reviewText':reviewText, 'date': date.today().isoformat(),'uid':session['id'], 'mid':mid})
  cursor.close()
  
  return redirect("/movie_info/{mid}".format(mid=mid))
  
@app.route('/like_review/<rid>/<mid>')
def likeReview(rid,mid):
  cursor = g.conn.execute("INSERT into likes(rid,uid) values (%(rid)s,%(uid)s)",{'rid':rid,'uid':session['id']})
  cursor.close()
  return redirect("/movie_info/{mid}".format(mid=mid))


# Example of adding new data to the database
@app.route('/add', methods=['POST'])
def add():
  name = request.form['name']
  g.conn.execute('INSERT INTO test(name) VALUES (%s)', name)
  return redirect('/')


@app.route('/venue_search')
def venues_search(vid):
  session['url'] = request.url
  cursor = g.conn.execute("SELECT T.date, M.name, T.starttime, theatrename, mid, vid, sid FROM Movie M NATURAL JOIN Shows S NATURAL JOIN Timing T WHERE vid=%(vid)s ORDER BY T.date, M.name, theatrename, T.starttime ASC", {'vid':vid})
  venue_shows = []
  for result in cursor:
    link = [result["mid"], result["vid"], result["theatrename"], result["sid"]]
    row = [result["date"], result["name"], result["starttime"], result["theatrename"], link]
    venue_shows.append(row)
  print(venue_shows)
  cursor.close()
  
  cursor2 = g.conn.execute("SELECT location, name FROM Venue WHERE vid=%(vid)s",{'vid':vid})
  venue_details = []
  for result in cursor2:
    venue_details.append(result["location"])
    venue_details.append(result["name"])
  cursor2.close()
  context = dict(data = venue_shows, details = venue_details)
  return render_template("venue_search.html", **context)

@app.route('/venue_search/<vid>')
def venue_search(vid):
  session['url'] = request.url
  cursor = g.conn.execute("SELECT T.date, M.name, T.starttime, theatrename, mid, vid, sid FROM Movie M NATURAL JOIN Shows S NATURAL JOIN Timing T WHERE vid=%(vid)s ORDER BY T.date, M.name, theatrename, T.starttime ASC",{'vid':vid})
  venue_shows = []
  for result in cursor:
    link = [result["mid"], result["vid"], result["theatrename"], result["sid"]]
    row = [result["date"], result["name"], result["starttime"], result["theatrename"], link]
    venue_shows.append(row)
  print(venue_shows)
  cursor.close()
  
  cursor2 = g.conn.execute("SELECT location, name FROM Venue WHERE vid=%(vid)s",{'vid':vid})
  venue_details = []
  for result in cursor2:
    venue_details.append(result["location"])
    venue_details.append(result["name"])
  cursor2.close()
  context = dict(data = venue_shows, details = venue_details)
  return render_template("venue_search.html", **context)

@app.route('/venue_search/<vid>/<mid>')
def venue_movie_search(vid, mid):
  session['url'] = request.url
  cursor = g.conn.execute("SELECT T.date, M.name, T.starttime, theatrename, mid, vid, sid FROM Movie M NATURAL JOIN Shows S NATURAL JOIN Timing T WHERE vid=%(vid)s AND mid=%(mid)s ORDER BY T.date, M.name, theatrename, T.starttime ASC",{'vid':vid, 'mid':mid})
  venue_shows = []
  for result in cursor:
    link = [result["mid"], result["vid"], result["theatrename"], result["sid"]]
    row = [result["date"], result["name"], result["starttime"], result["theatrename"], link]
    venue_shows.append(row)
  print(venue_shows)
  cursor.close()
  
  cursor2 = g.conn.execute("SELECT location, name FROM Venue WHERE vid=%(vid)s",{'vid':vid})
  venue_details = []
  for result in cursor2:
    venue_details.append(result["location"])
    venue_details.append(result["name"])
  cursor2.close()
  context = dict(data = venue_shows, details = venue_details)
  return render_template("venue_search.html", **context)

@app.route('/movie_search/<mid>')
def movie_search(mid):
  session['url'] = request.url
  cursor = g.conn.execute("SELECT T.date, V.name, theatrename, T.starttime, mid, vid, sid FROM Shows S NATURAL JOIN Timing T NATURAL JOIN Venue V WHERE mid =%(mid)s ORDER BY T.date, V.name, theatrename, T.starttime",{'mid':mid})
  movie_shows = []
  for result in cursor:
    link = [result["mid"], result["vid"], result["theatrename"], result["sid"]]
    row = [result["date"], result["name"], result["starttime"], result["theatrename"], link]
    movie_shows.append(row)
  print(movie_shows)
  cursor.close()
  
  cursor2 = g.conn.execute("SELECT name, description FROM Movie WHERE mid=%(mid)s",{'mid':mid})
  movie_details = []
  for result in cursor2:
    movie_details.append(result["name"])
    movie_details.append(result["description"])
    movie_details.append(mid)
  cursor2.close()
  context = dict(data = movie_shows, details = movie_details)
  return render_template("movie_search.html", **context)

@app.route('/booking/<mid>/<vid>/<theatrename>/<sid>', methods=["GET", "POST"])
def booking(mid, vid, theatrename, sid):
  session['url'] = request.url
  booking_details = []
  cursor = g.conn.execute("SELECT name FROM Movie WHERE mid=%s",(mid))
  for result in cursor:
    booking_details.append(result["name"])
  cursor = g.conn.execute("SELECT name FROM Venue WHERE vid=%s",(vid))
  for result in cursor:
    booking_details.append(result["name"])
  booking_details.append(theatrename)
  cursor = g.conn.execute("SELECT date, starttime, endtime FROM Timing WHERE sid=%s",(sid))
  for result in cursor:
    booking_details.append(result["date"])
    booking_details.append(result["starttime"])
    booking_details.append(result["endtime"])
  cursor.close()
  if request.method == 'GET':
    cursor = g.conn.execute("SELECT seatnumber, price FROM SEAT WHERE theatrename like %(theatreName)s AND vid=%(vid)s EXCEPT SELECT seatnumber, price FROM SEAT NATURAL JOIN Ticket WHERE theatrename like %(theatreName)s AND vid=%(vid)s ORDER BY price, seatnumber",{'theatreName':theatrename,'vid':vid, 'theatreName':theatrename, 'vid':vid})
    available_seats = []
    for result in cursor:
      row = [result["seatnumber"], result["price"]]
      available_seats.append(row)
    cursor.close()
    context = dict(data = available_seats, details = booking_details)
    return render_template("booking.html", **context),{"Refresh": "30; url=/home"}
  if request.method == 'POST':
    result = request.form
    seatnumber = request.form.get("SeatNumber","")
    cursor = g.conn.execute("SELECT MAX(tid) FROM Ticket")
    for result in cursor:
      tid = result["max"] + 1
    cursor.close()
    print("TID")
    print(tid)
    uid = session['id']
    g.conn.execute("INSERT INTO Ticket (tid, time, seatnumber, theatrename, vid, sid, mid, uid) VALUES (%(ticketId)s, %(date)s, %(seatNumber)s, %(theatreName)s, %(vid)s, %(sid)s, %(mid)s, %(uid)s)",{'ticketId':tid, 'date':date.today(), 'seatNumber':seatnumber, 'theatreName':theatrename, 'vid':vid, 'sid':sid, 'mid':mid, 'uid':uid})
    booking_details.append(seatnumber)
    context = dict(details = booking_details)
    return render_template("booking_complete.html",**context)
  

  
  

if __name__ == "__main__":
  import click

  @click.command()
  @click.option('--debug', is_flag=True)
  @click.option('--threaded', is_flag=True)
  @click.argument('HOST', default='0.0.0.0')
  @click.argument('PORT', default=8111, type=int)
  def run(debug, threaded, host, port):
    """
    This function handles command line parameters.
    Run the server using:

        python3 server.py

    Show the help text using:

        python3 server.py --help

    """

    HOST, PORT = host, port
    print("running on %s:%s" % (HOST, PORT))
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

  run()
