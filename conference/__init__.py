#!/usr/bin/env python


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


# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -


@endpoints.api(name='conference', version='v1', audiences=[ANDROID_AUDIENCE],
    allowed_client_ids=[WEB_CLIENT_ID, API_EXPLORER_CLIENT_ID, ANDROID_CLIENT_ID, IOS_CLIENT_ID],
    scopes=[EMAIL_SCOPE])
class ConferenceApi(remote.Service):
    """Conference API v0.1"""

    from a import _copyConferenceToForm,_createConferenceObject,_updateConferenceObject,createConference,updateConference,getConference,getConferencesCreated,_getQuery,_formatFilters,queryConferences
    from b import _copyProfileToForm,_getProfileFromUser,_doProfile,getProfile,saveProfile,_cacheAnnouncement,getAnnouncement,_conferenceRegistration,getConferencesToAttend,registerForConference,unregisterFromConference,filterPlayground

api = endpoints.api_server([ConferenceApi]) # register API
