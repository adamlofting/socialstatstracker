import cgi
import datetime
import urllib
import webapp2
import logging
import os
import json
import random
# GAE
from google.appengine.ext import ndb
from google.appengine.api import users
# 3rd party
import jinja2
import twitter
import keys

# Templating
jinja_environment = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))


# Models
class SocialAccount(ndb.Model):
    """An account to track"""
    account_username = ndb.StringProperty()
    account_type = ndb.StringProperty(choices=['facebook', 'twitter', 'youtube', 'googleplus'])
    grouping = ndb.StringProperty() # earthhour, wwf
    count = ndb.IntegerProperty(default=1)
    
    def display_name(self):
        if self.account_username == 'WWF':
            return 'WWF (International)'
        else:
            return self.account_username


class SocialAccountRecord(ndb.Model):
    """For tracking stats over time"""
    account_username = ndb.StringProperty()
    account_type = ndb.StringProperty(choices=['facebook', 'twitter', 'youtube', 'googleplus'])
    count = ndb.IntegerProperty()
    created_on = ndb.DateProperty()
    unique_day_data_mash = ndb.StringProperty()
    updated = ndb.DateTimeProperty(auto_now=True)


class TotalCount(ndb.Model):
    """A utility model"""
    facebook = ndb.IntegerProperty(default=0)
    twitter = ndb.IntegerProperty(default=0)
    youtube = ndb.IntegerProperty(default=0)


# Handlers
class MainPage(webapp2.RequestHandler):
    def get(self):
        all_social_accounts = get_all_social_accounts_by_count()
        totals_wwf = get_totals(all_social_accounts, 'wwf')
        totals_earthhour = get_totals(all_social_accounts, 'earthhour')
        template_values = { 
            'all_social_accounts':all_social_accounts,
            'totals_wwf':totals_wwf,
            'totals_earthhour':totals_earthhour
            }
        jinja_environment.filters['format_number'] = format_number
        # Write out Page
        template = jinja_environment.get_template('index.html')
        self.response.out.write(template.render(template_values))


class AdminPage(webapp2.RequestHandler):
    def get(self):        
        template_values = { 
            'all_social_accounts':get_all_social_accounts(), 
            'logout_url': users.create_logout_url("/")
            }
        # Write out Page
        template = jinja_environment.get_template('admin.html')
        self.response.out.write(template.render(template_values))


class AddAccount(webapp2.RequestHandler):
    def post(self):
        account_username = self.request.get('account_username')
        account_type = self.request.get('account_type')
        grouping = self.request.get('grouping')

        if not account_username:
            self.redirect('/admin/?account-name-is-required')
            return

        account = SocialAccount(parent=get_app_key())
        account.account_username = account_username
        account.account_type = account_type
        account.grouping = grouping
        account.put()

        get_latest_count(account)

        self.redirect('/admin/?done')


class DeleteAccount(webapp2.RequestHandler):
    def get(self, account_id=None):        
        if account_id:            
            account_to_delete = SocialAccount.get_by_id(int(account_id), parent=get_app_key())
            account_to_delete.key.delete()
            self.redirect('/admin/?deleted') 
            return
        else:
            self.redirect('/admin/?invalid')        
        

class RefreshStats(webapp2.RequestHandler):
    def get(self):             
        refresh_stats()
        self.redirect('/admin/?refreshed')


class CronRefreshStats(webapp2.RequestHandler):
    def get(self):             
        refresh_stats()


# Functions
def refresh_stats():
    records = []
    social_accounts = get_all_social_accounts()
    twitter_accounts_checked = 0
    random.shuffle(social_accounts) # this is to mix up sort order in case of API limit overloads
    for social_account in social_accounts:
        if social_account.account_type == 'twitter':
            twitter_accounts_checked += 1
            if twitter_accounts_checked < 100:
                record = get_latest_count(social_account, get_twitter_api())
        else:
            record = get_latest_count(social_account, get_twitter_api())
        if record:
            records.append(record)
    ndb.put_multi(records)  


def get_totals(all_social_accounts, grouping='wwf'):
    totals = TotalCount()
    for social_account in all_social_accounts:

        if social_account.grouping == grouping:

            if social_account.account_type == 'facebook':
                totals.facebook += social_account.count

            if social_account.account_type == 'twitter':
                totals.twitter += social_account.count

            if social_account.account_type == 'youtube':
                totals.youtube += social_account.count

    return totals


def record_latest_count(social_account, count):
    record = None
    if count:
        if count > 0:
            today = datetime.date.today()
            datamash_for_quick_lookup = str(today) + social_account.account_type + social_account.account_username

            # only keep the latest record for any day
            q = SocialAccountRecord.query(SocialAccountRecord.unique_day_data_mash == datamash_for_quick_lookup)
            q.filter()            
            record = q.get()

            if not record:
                record = SocialAccountRecord() # create a new one

            record.account_username = social_account.account_username
            record.account_type = social_account.account_type
            record.count = count
            record.created_on = today
            record.unique_day_data_mash = datamash_for_quick_lookup
            # record.put() # bubble up and put_multi

            # if not social_account.grouping:
            #     social_account.grouping = 'wwf' # this was a temporary measure to update old records after the addition of EH accounts
            social_account.count = count
            social_account.put()

    return record


def get_latest_count(social_account, api=None):
    record = None
    if social_account.account_type == 'facebook':
        record = get_latest_facebook_count(social_account)

    if social_account.account_type == 'youtube':
        record = get_latest_youtube_count(social_account)
    
    if social_account.account_type == 'twitter':
        record = get_latest_twitter_count(social_account, api)
    return record


def get_latest_facebook_count(social_account):
    api_url = "http://graph.facebook.com/" + social_account.account_username
    page_likes = None
    try:
        j = json.loads(urllib.urlopen(api_url).read())        
        if j:
            page_likes = int(j['likes'])            
    except Exception as e:
        logging.error("Error fetching facebook API")
        logging.error(e)
    
    record = None
    if page_likes:        
        record = record_latest_count(social_account, page_likes)
    return record
    

def get_latest_youtube_count(social_account):
    api_url = "https://gdata.youtube.com/feeds/api/users/" + social_account.account_username + "?alt=json"
    video_views = None
    try:
        j = json.loads(urllib.urlopen(api_url).read())    
        if j:
            video_views = int(j['entry']['yt$statistics']['totalUploadViews'])            
    except Exception as e:
        logging.error("Error fetching facebook API")
        logging.error(e)
    
    record = None
    if video_views:
        record = record_latest_count(social_account, video_views)
    return record

def get_latest_twitter_count(social_account, api):
    if not api:
        api = get_twitter_api()
    
    followers = None
    try:
        twitter_user = api.GetUser(screen_name=social_account.account_username)      
        if twitter_user:
            followers = twitter_user.followers_count
    except Exception as e:
        logging.error("Error fetching twitter API")
        logging.error(e)

    record = None
    if followers:
        record = record_latest_count(social_account, followers)
    return record

# Utility
def get_app_key():
    """Constructs a fixed Datastore key for the app for strong consistency for all admins."""
    return ndb.Key('AppFixedKey', 'HappyPanda') # This is hacky, but works for our needs


def get_all_social_accounts():
    q = SocialAccount.query(ancestor=get_app_key())
    q = q.order(SocialAccount.account_username)
    return list(q.iter())  


def get_all_social_accounts_by_count():
    q = SocialAccount.query(ancestor=get_app_key())
    q = q.order(-SocialAccount.count)
    return list(q.iter()) 


def format_number(value):
    return "{:,}".format(value)


def get_twitter_api():
    return twitter.Api(consumer_key=keys.TWITTER_CONSUMER_KEY,
                        consumer_secret=keys.TWITTER_CONSUMER_SECRET,
                        access_token_key=keys.TWITTER_ACCESS_TOKEN_KEY,
                        access_token_secret=keys.TWITTER_ACCESS_TOKEN_SECRET,
                        cache=None)  


app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/admin/?', AdminPage),
    ('/admin/add', AddAccount),
    ('/admin/delete/(\d+)', DeleteAccount),
    ('/admin/refresh', RefreshStats),
    ('/cron/refresh', CronRefreshStats)
], debug=True)
