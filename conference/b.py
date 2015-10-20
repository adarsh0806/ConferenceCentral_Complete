from datetime import datetime

import endpoints
from protorpc import messages
from protorpc import message_types
from protorpc import remote

from google.appengine.api import memcache
from google.appengine.api import taskqueue
from google.appengine.ext import ndb

from models import ConflictException
from models import Profile
from models import ProfileMiniForm
from models import ProfileForm
from models import StringMessage
from models import BooleanMessage
from models import Conference
from models import ConferenceForm
from models import ConferenceForms
from models import ConferenceQueryForm
from models import ConferenceQueryForms
from models import TeeShirtSize

from settings import WEB_CLIENT_ID
from settings import ANDROID_CLIENT_ID
from settings import IOS_CLIENT_ID
from settings import ANDROID_AUDIENCE

from utils import getUserId

from const import EMAIL_SCOPE, API_EXPLORER_CLIENT_ID, MEMCACHE_ANNOUNCEMENTS_KEY, ANNOUNCEMENT_TPL, DEFAULTS, OPERATORS, FIELDS, CONF_GET_REQUEST, CONF_POST_REQUEST

# - - - Profile objects - - - - - - - - - - - - - - - - - - -

def _copyProfileToForm(self, prof):
    """Copy relevant fields from Profile to ProfileForm."""
    # copy relevant fields from Profile to ProfileForm
    pf = ProfileForm()
    for field in pf.all_fields():
        if hasattr(prof, field.name):
            # convert t-shirt string to Enum; just copy others
            if field.name == 'teeShirtSize':
                setattr(pf, field.name, getattr(TeeShirtSize, getattr(prof, field.name)))
            else:
                setattr(pf, field.name, getattr(prof, field.name))
    pf.check_initialized()
    return pf


def _getProfileFromUser(self):
    """Return user Profile from datastore, creating new one if non-existent."""
    # make sure user is authed
    user = endpoints.get_current_user()
    if not user:
        raise endpoints.UnauthorizedException('Authorization required')

    # get Profile from datastore
    user_id = getUserId(user)
    p_key = ndb.Key(Profile, user_id)
    profile = p_key.get()
    # create new Profile if not there
    if not profile:
        profile = Profile(
            key = p_key,
            displayName = user.nickname(),
            mainEmail= user.email(),
            teeShirtSize = str(TeeShirtSize.NOT_SPECIFIED),
        )
        profile.put()

    return profile      # return Profile


def _doProfile(self, save_request=None):
    """Get user Profile and return to user, possibly updating it first."""
    # get user Profile
    prof = self._getProfileFromUser()

    # if saveProfile(), process user-modifyable fields
    if save_request:
        for field in ('displayName', 'teeShirtSize'):
            if hasattr(save_request, field):
                val = getattr(save_request, field)
                if val:
                    setattr(prof, field, str(val))
                    #if field == 'teeShirtSize':
                    #    setattr(prof, field, str(val).upper())
                    #else:
                    #    setattr(prof, field, val)
                    prof.put()

    # return ProfileForm
    return self._copyProfileToForm(prof)


@endpoints.method(message_types.VoidMessage, ProfileForm,
        path='profile', http_method='GET', name='getProfile')
def getProfile(self, request):
    """Return user profile."""
    return self._doProfile()


@endpoints.method(ProfileMiniForm, ProfileForm,
        path='profile', http_method='POST', name='saveProfile')
def saveProfile(self, request):
    """Update & return user profile."""
    return self._doProfile(request)


# - - - Announcements - - - - - - - - - - - - - - - - - - - -

@staticmethod
def _cacheAnnouncement():
    """Create Announcement & assign to memcache; used by
    memcache cron job & putAnnouncement().
    """
    confs = Conference.query(ndb.AND(
        Conference.seatsAvailable <= 5,
        Conference.seatsAvailable > 0)
    ).fetch(projection=[Conference.name])

    if confs:
        # If there are almost sold out conferences,
        # format announcement and set it in memcache
        announcement = ANNOUNCEMENT_TPL % (
            ', '.join(conf.name for conf in confs))
        memcache.set(MEMCACHE_ANNOUNCEMENTS_KEY, announcement)
    else:
        # If there are no sold out conferences,
        # delete the memcache announcements entry
        announcement = ""
        memcache.delete(MEMCACHE_ANNOUNCEMENTS_KEY)

    return announcement


@endpoints.method(message_types.VoidMessage, StringMessage,
        path='conference/announcement/get',
        http_method='GET', name='getAnnouncement')
def getAnnouncement(self, request):
    """Return Announcement from memcache."""
    return StringMessage(data=memcache.get(MEMCACHE_ANNOUNCEMENTS_KEY) or "")


# - - - Registration - - - - - - - - - - - - - - - - - - - -

@ndb.transactional(xg=True)
def _conferenceRegistration(self, request, reg=True):
    """Register or unregister user for selected conference."""
    retval = None
    prof = self._getProfileFromUser() # get user Profile

    # check if conf exists given websafeConfKey
    # get conference; check that it exists
    wsck = request.websafeConferenceKey
    conf = ndb.Key(urlsafe=wsck).get()
    if not conf:
        raise endpoints.NotFoundException(
            'No conference found with key: %s' % wsck)

    # register
    if reg:
        # check if user already registered otherwise add
        if wsck in prof.conferenceKeysToAttend:
            raise ConflictException(
                "You have already registered for this conference")

        # check if seats avail
        if conf.seatsAvailable <= 0:
            raise ConflictException(
                "There are no seats available.")

        # register user, take away one seat
        prof.conferenceKeysToAttend.append(wsck)
        conf.seatsAvailable -= 1
        retval = True

    # unregister
    else:
        # check if user already registered
        if wsck in prof.conferenceKeysToAttend:

            # unregister user, add back one seat
            prof.conferenceKeysToAttend.remove(wsck)
            conf.seatsAvailable += 1
            retval = True
        else:
            retval = False

    # write things back to the datastore & return
    prof.put()
    conf.put()
    return BooleanMessage(data=retval)


@endpoints.method(message_types.VoidMessage, ConferenceForms,
        path='conferences/attending',
        http_method='GET', name='getConferencesToAttend')
def getConferencesToAttend(self, request):
    """Get list of conferences that user has registered for."""
    prof = self._getProfileFromUser() # get user Profile
    conf_keys = [ndb.Key(urlsafe=wsck) for wsck in prof.conferenceKeysToAttend]
    conferences = ndb.get_multi(conf_keys)

    # get organizers
    organisers = [ndb.Key(Profile, conf.organizerUserId) for conf in conferences]
    profiles = ndb.get_multi(organisers)

    # put display names in a dict for easier fetching
    names = {}
    for profile in profiles:
        names[profile.key.id()] = profile.displayName

    # return set of ConferenceForm objects per Conference
    return ConferenceForms(items=[self._copyConferenceToForm(conf, names[conf.organizerUserId])\
        for conf in conferences]
    )


@endpoints.method(CONF_GET_REQUEST, BooleanMessage,
        path='conference/{websafeConferenceKey}',
        http_method='POST', name='registerForConference')
def registerForConference(self, request):
    """Register user for selected conference."""
    return self._conferenceRegistration(request)


@endpoints.method(CONF_GET_REQUEST, BooleanMessage,
        path='conference/{websafeConferenceKey}',
        http_method='DELETE', name='unregisterFromConference')
def unregisterFromConference(self, request):
    """Unregister user for selected conference."""
    return self._conferenceRegistration(request, reg=False)


@endpoints.method(message_types.VoidMessage, ConferenceForms,
        path='filterPlayground',
        http_method='GET', name='filterPlayground')
def filterPlayground(self, request):
    """Filter Playground"""
    q = Conference.query()
    # field = "city"
    # operator = "="
    # value = "London"
    # f = ndb.query.FilterNode(field, operator, value)
    # q = q.filter(f)
    q = q.filter(Conference.city=="London")
    q = q.filter(Conference.topics=="Medical Innovations")
    q = q.filter(Conference.month==6)

    return ConferenceForms(
        items=[self._copyConferenceToForm(conf, "") for conf in q]
    )
