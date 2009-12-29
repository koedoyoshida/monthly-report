# Event Administration pages.
# coding=utf-8
import datetime
import hashlib

from google.appengine.api import users

import schema
import send_notification
import webapp_generic

class NewEvent(webapp_generic.WebAppGenericProcessor):
    """Form to create a new event."""
    def process_input(self):
        template_values = {
            'nickname': users.get_current_user().nickname(),
            'eventid': "na", # set it to N/A to later set it to something else...?
            'new_entry': True
            }
        self.template_render_output(template_values, 'EditEvent.html')

class EditEvent(webapp_generic.WebAppGenericProcessor):
    """Load from the existing data and edit the event"""
    def process_input(self):
        eventid = self.request.get('eventid')
        event = self.load_event_with_eventid(eventid)
        if event == None:
            self.response.out.write('Event id %s not found' % (eventid))
            return
        if not self.check_auth_owner(event):
            self.response.out.write('Not your event')
            return

        template_values = {
            'nickname': event.owner.nickname(), # the owner might be not me.
            'owners_email': (','.join(event.owners_email)),
            'eventid': event.eventid,
            'title': event.title,
            'location': event.location,
            'content': event.content,
            'prework': event.prework,
            'event_date': event.event_date,
            'new_entry': False
            }
        self.template_render_output(template_values, 'EditEvent.html')


def generate_eventid(event_title, username, time):
    """Create a sha1 hash hex string to use as event ID."""
    sourcestring = event_title + username + time
    h = hashlib.sha1()
    h.update(sourcestring.encode('utf-8'))
    return h.hexdigest()


class RegisterEvent(webapp_generic.WebAppGenericProcessor):
    """Load from the existing database and edit the event content"""
    def process_input(self):
        eventid = self.request.get('eventid')
        title = self.request.get('title')
        user = users.get_current_user()

        if eventid == 'na':
            # if it's new, create a new item
            event = schema.Event()
            eventid = generate_eventid(title, user.email(), datetime.datetime.now().isoformat(' '))
            event.eventid = eventid
            event.owner = user
        else:
            event = self.load_event_with_eventid(eventid)
            if event == None:
                self.response.out.write('Event id %s not found' % (eventid))
                return

        event.eventid = eventid
        event.owners_email = self.request.get('owners_email').split(',')
        event.title = title
        event.location = self.request.get('location')
        event.content = self.request.get('content')
        event.prework = self.request.get('prework')
        event.event_date = self.request.get('event_date')
        event.put()

        send_notification.send_notification_to_user_and_owner(user.email(), 
                                                              event.owner.email(),
                                                              event.owners_email,
                                                              "[Debian登録システム] イベント %s が更新されました" % 
                                                              event.title.encode('utf-8'), """
このメールは自動送信です。

イベントの詳細

%s
""" % event.title.encode('utf-8'))

        self.redirect('/thanks?eventid=%s' % eventid)


class ViewEventSummary(webapp_generic.WebAppGenericProcessor):
    """View summary of registered users for a given event."""
    def process_input(self):
        eventid = self.request.get('eventid')
        event = self.load_event_with_eventid(eventid)
        if not event:
            self.response.out.write('Event id %s not found' % (eventid))
            return
        if not self.check_auth_owner(event):
            self.response.out.write("""
You are not allowed to see a summary""")
            return

        attendances = schema.Attendance.gql('WHERE eventid = :1 ORDER BY timestamp DESC', 
                                     eventid)
        for attendance in attendances:
            self.response.out.write("""
<li>%s: %s</li>
""" % (attendance.user.nickname(), 
       attendance.prework))
