import pprint, urllib2, re, smtplib, mimetypes, iso8601
from xml.sax import make_parser
from xml.sax.handler import ContentHandler
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from time import mktime


# *** Configure ***
craigslist_feed = "http://sfbay.craigslist.org/search/apa/sfc?query=&srchType=A&minAsk=&maxAsk=2000&bedrooms=2&nh=149&nh=4&nh=5&nh=9&nh=11&nh=12&nh=10&nh=20&nh=18&nh=21&nh=29&format=rss"
message = "Hi,\n\nThis is an email message sent to every matching listing. Please call me, I want to rent something.\n\nSincerely,\n~Jordan"

# *** Definitions ***
latest_listing_date_fp = open('./latest_listing.txt', 'r+')
latest_listing_date = latest_listing_date_fp.read()
orig_latest_listing_date = latest_listing_date
latest_listing_date_fp.close()
def sendMail(to, subject, text):
  print "Sending mail to " + to
  gmailUser = 'youremail@gmail.com'
  gmailPassword = 'gmailpassword'
  
  msg = MIMEMultipart()
  msg['From'] = gmailUser
  msg['To'] = to
  msg['Subject'] = subject
  msg.attach(MIMEText(text))
  
  mailServer = smtplib.SMTP('smtp.gmail.com', 587)
  mailServer.ehlo()
  mailServer.starttls()
  mailServer.ehlo()
  mailServer.login(gmailUser, gmailPassword)
  mailServer.sendmail(gmailUser, to, msg.as_string())
  mailServer.close()
class CraigslistParser(ContentHandler):
  def __init__(self):
    self.curItem = {}
    self.curTag = ''
    self.inItem = False
    self.items = []

  def startElement(self, name, attrs): 
    if(name == 'item'):
      self.inItem = True
      self.curItem = {}

    self.curTag = name

    if(self.inItem and self.curTag != 'item'):
      self.curItem[self.curTag] = ''

  def endElement(self, name):
    if(name == 'item'):
      self.inItem = False
      self.items.append(self.curItem)
    self.curTag = ''


  def characters (self, ch): 
    if(self.curTag and self.inItem and self.curTag != 'item'):
      self.curItem[self.curTag] += ch

#
# Go Time!
#

parser = make_parser()
curHandler = CraigslistParser()

parser.setContentHandler(curHandler)

#feed_contents = urllib2.urlopen(craigslist_feed).read()
#pprint.pprint(feed_contents)
parser.parse(craigslist_feed)
curHandler.items.reverse()
#parser.parse(open(craigslist_feed))

#pprint.pprint(curHandler.items)


listings = []

for raw in curHandler.items:
  listing = {}
  listing['title'] = raw['dc:title']
  listing['link'] = raw['link']
  listing['phone'] = ''
  
  # Parsing dates into non-bullshit format
  listing['date'] = str(mktime(iso8601.parse_date(raw['dcterms:issued']).timetuple()))
  
  # Fetch the content 
  response = urllib2.urlopen(raw['link'])
  listing_html = response.read()
  
  # Searching for phone numbers by stripping out all non-content characters
  description_scrunched = re.sub('[^a-z0-9]', '', raw['description'])
  phone = re.search('([0-9]{10,11})', description_scrunched)
  if(phone):
    pnum = phone.group()
    listing['phone'] = pnum[:3]+"."+pnum[3:][:3]+"."+pnum[6:]
  
  # Pull email from description, or fetch the anonymous email if needed
  email_match = re.search('(\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}\b)', raw['description'])
  if(not email_match):
    #Email not found in description. Extract from listing
    email_match = re.search('(hous\-[a-z0-9]+\-[0-9]+@craigslist\.org)', listing_html)
    if(not email_match):
      continue
  
  email = email_match.group()
  listing['email'] = email
  
  listings.append(listing)
  
sent_messages = []
print "Latest Listing Date: '" + latest_listing_date + "'"
for listing in listings:
  print "Listing: " + listing['title']
  print "Has date: " + str(listing['date'])
  if(latest_listing_date == '' or latest_listing_date < listing['date']):
    to = listing['email']
    subject = "Re: "+listing['title']
    sendMail(to, subject, message)
    latest_listing_date = listing['date']
    sent_messages.append(listing)
if(orig_latest_listing_date != latest_listing_date):
  latest_listing_date_fp = open('./latest_listing.txt', 'w')
  latest_listing_date_fp.write(latest_listing_date)
  
  contents = "Sent messages to: \n\n"
  for listing in sent_messages:
    contents += listing['link'] + "\n"
    contents += listing['title'] + "\n"
    contents += listing['phone'] + "\n\n"
  subject = "Re: New craigslist messages sent!"
  to = "youraddress@gmail.com"
  sendMail(to, subject, contents)
  

