WWF Social Stats Tracker
===========================================

What does this app do?
----------------------
Keeps a running total of the number of likes, followers and video views across a number of accounts on these social media channels.

It does this by:
* Storing a list of account usernames managed via a simple admin page
* Periodically checking the user IDs against the Facebook, Twitter and YouTube APIs to get the latest number
* Updating the current number on an hourly basis
* Keeping a copy of the current number at the end of each day for interesting analysis one day

You can see it live here: http://wwfsocialstats.appspot.com/

Why was it built like this?
---------------------------
I built this tool one weekend to save the hours of time people were spending on a regular basis to copy and paste this data into an excel file that was only then viewed by a few people in the organisation. 

Why is X not better?
--------------------
The quality and structure of this code is about right for the amount of work it is designed to save staff from completing elsewhere, and it works for the amount of traffic this page receives. If you wanted to scale this up, you should do some optimisation and a little bit of refactoring.

How to install your own copy, and things to note:
-------------------------------------------------
1. Learn how Google App Engine works (it’s a nice system and won’t take long to understand the basics)
2. Fork this repo (or just take a copy of the code)
3. Change application name in app.yaml and setup your corresponding named app on Google App Engine
4. Add your own Twitter API key info into keys_example.py and rename to keys.5
py. Run the app locally
6. Modify the HTML to meet your branding needs (you must remove the panda logo or any WWF copyright material - the code is free to use)
7. You’re unlikely to want the categories of WWF and Earth Hour we use, so you’ll need to modify the logic a little bit for that
Deploy