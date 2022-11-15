
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

  context = dict(movies=data, venues=data2 )
  return render_template("home.html", **context)

@app.route('/home', methods=['POST'])
def home_post():
  session['url'] = request.url
  print("request form", request.form)
  mid = request.form.get("Movie", "")
  vid = request.form.get("Venue", "")
  print(mid, vid)
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
  cursor = g.conn.execute("SELECT * from Movie M where M.mid = {mid}".format(mid=mid)) 
  data = []
  reviews = []
  for result in cursor:
    data.append(result)
  cursor.close()

  cursor = g.conn.execute("SELECT r.rid, r.text, r.time, u.name from Reviews r NATURAL JOIN Users u WHERE r.mid={mid}".format(mid=mid))
  for result in cursor:
    cursor2 = g.conn.execute("SELECT COUNT(*) from Likes l where l.rid = {rid}".format(rid=result['rid']))
    numLikes = 0
    for cnt in cursor2:
      numLikes = cnt['count']
    reviews.append({'uname':result['name'], 'text':result['text'], 'time':result['time'], 'numLikes':numLikes})
  cursor.close
  context = dict(movie = data[0], reviews=reviews)

  return render_template("movie_info.html", **context)

@app.route('/venue_search/<vid>')
def venue_search(vid):
  session['url'] = request.url
  cursor = g.conn.execute("SELECT T.date, M.name, T.starttime, theatrename, mid, vid, sid FROM Movie M NATURAL JOIN Shows S NATURAL JOIN Timing T WHERE vid={vid} ORDER BY T.date, M.name, theatrename, T.starttime ASC".format(vid=vid))
  venue_shows = []
  for result in cursor:
    link = [result["mid"], result["vid"], result["theatrename"], result["sid"]]
    row = [result["date"], result["name"], result["starttime"], result["theatrename"], link]
    venue_shows.append(row)
  print(venue_shows)
  cursor.close()
  
  cursor2 = g.conn.execute("SELECT location, name FROM Venue WHERE vid={vid}".format(vid=vid))
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
  cursor = g.conn.execute("SELECT T.date, M.name, T.starttime, theatrename, mid, vid, sid FROM Movie M NATURAL JOIN Shows S NATURAL JOIN Timing T WHERE vid={vid} AND mid={mid} ORDER BY T.date, M.name, theatrename, T.starttime ASC".format(vid=vid, mid=mid))
  venue_shows = []
  for result in cursor:
    link = [result["mid"], result["vid"], result["theatrename"], result["sid"]]
    row = [result["date"], result["name"], result["starttime"], result["theatrename"], link]
    venue_shows.append(row)
  print(venue_shows)
  cursor.close()
  
  cursor2 = g.conn.execute("SELECT location, name FROM Venue WHERE vid={vid}".format(vid=vid))
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
  cursor = g.conn.execute("SELECT T.date, V.name, theatrename, T.starttime, mid, vid, sid FROM Shows S NATURAL JOIN Timing T NATURAL JOIN Venue V WHERE mid ={mid} ORDER BY T.date, V.name, theatrename, T.starttime".format(mid=mid))
  movie_shows = []
  for result in cursor:
    link = [result["mid"], result["vid"], result["theatrename"], result["sid"]]
    row = [result["date"], result["name"], result["starttime"], result["theatrename"], link]
    movie_shows.append(row)
  print(movie_shows)
  cursor.close()
  
  cursor2 = g.conn.execute("SELECT name, description FROM Movie WHERE mid={mid}".format(mid=mid))
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
  cursor = g.conn.execute("SELECT name FROM Movie WHERE mid={mid}".format(mid=mid))
  for result in cursor:
    booking_details.append(result["name"])
  cursor = g.conn.execute("SELECT name FROM Venue WHERE vid={vid}".format(vid=vid))
  for result in cursor:
    booking_details.append(result["name"])
  booking_details.append(theatrename)
  cursor = g.conn.execute("SELECT date, starttime, endtime FROM Timing WHERE sid={sid}".format(sid=sid))
  for result in cursor:
    booking_details.append(result["date"])
    booking_details.append(result["starttime"])
    booking_details.append(result["endtime"])
  cursor.close()
  if request.method == 'GET':
    cursor = g.conn.execute("SELECT seatnumber, price FROM SEAT  WHERE theatrename like '{theatrename}' AND vid={vid} EXCEPT SELECT seatnumber, price FROM SEAT NATURAL JOIN Ticket WHERE theatrename like '{theatrename}' AND vid={vid} ORDER BY price, seatnumber".format(theatrename=theatrename, vid=vid))
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
    g.conn.execute("INSERT INTO Ticket (tid, time, seatnumber, theatrename, vid, sid, mid, uid) VALUES ({tid}, '{time}', {seatnumber}, '{theatrename}', {vid}, {sid}, {mid}, {uid})".format(tid=tid, time=date.today(), seatnumber=seatnumber, theatrename=theatrename, vid=vid, sid=sid, mid=mid, uid=uid))
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
    print("running on %s:%d" % (HOST, PORT))
    app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

  run()
