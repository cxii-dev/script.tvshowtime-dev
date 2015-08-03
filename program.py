#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import sys
import threading
import xbmc
import xbmcgui
import xbmcaddon
import unicodedata
import json

from resources.lib.tvshowtime import GetCode
from resources.lib.tvshowtime import Authorize
from resources.lib.tvshowtime import IsChecked
from resources.lib.tvshowtime import MarkAsWatched
from resources.lib.tvshowtime import MarkAsUnWatched
from resources.lib.tvshowtime import GetUserInformations
from resources.lib.tvshowtime import SaveShowProgress
from resources.lib.tvshowtime import Show

__addon__         = xbmcaddon.Addon()
__cwd__           = __addon__.getAddonInfo('path')
__icon__          = __addon__.getAddonInfo('icon')
__scriptname__    = __addon__.getAddonInfo('name')
__version__       = __addon__.getAddonInfo('version')
__language__      = __addon__.getLocalizedString
__resource_path__ = os.path.join(__cwd__, 'resources', 'lib')
__resource__      = xbmc.translatePath(__resource_path__).decode('utf-8')

__token__ = __addon__.getSetting('token')
__facebook__ = __addon__.getSetting('facebook')
__twitter__ = __addon__.getSetting('twitter')
__notifications__ = __addon__.getSetting('notifications')
__welcome__ = __addon__.getSetting('welcome')

def start():
    menuitems = []
    if __token__ is '':
        menuitems.append(__language__(33801))
    else:
        menuitems.append(__language__(33803))
        menuitems.append(__language__(33802))
    startmenu = xbmcgui.Dialog().select(__scriptname__, menuitems)
    if startmenu < 0: return
    elif startmenu == 0 and __token__ is '':
        _login = GetCode()
        if _login.is_code:
            Authorization(_login.verification_url, _login.user_code, _login.device_code)
        else:
            xbmcgui.Dialog().ok(__scriptname__, __language__(33804))
    elif startmenu == 1:
        logout = xbmcgui.Dialog().yesno(__scriptname__, __language__(33805))
        if logout == True:
            __addon__.setSetting('token', '')
            __addon__.setSetting('user', '')
            return
        start()
    else:
        first_step()
        
def Authorization(verification_url, user_code, device_code):
    pDialog = xbmcgui.DialogProgress()
    pDialog.create(__scriptname__, "%s: %s" % (__language__(33806), verification_url), "%s: %s" % (__language__(33807), user_code))
    for i in range(0, 100):
        pDialog.update(i)
        xbmc.sleep(5000)  
        if pDialog.iscanceled(): return
        _authorize = Authorize(device_code)
        if _authorize.is_authorized:
            __addon__.setSetting('token', _authorize.access_token)
            user = GetUserInformations(_authorize.access_token)
            if user.is_authenticated:
                if __welcome__ == 'true':
                    xbmcgui.Dialog().ok(__scriptname__, '%s %s' % (__language__(32902), user.username), __language__(33808))
                __addon__.setSetting('user', user.username)
            return
    pDialog.close()

def first_step():
    which_way = xbmcgui.Dialog().select(__language__(33901), ["TVShow Time > Kodi", "Kodi > TVShow Time"])
    if which_way < 0: return
    scan(which_way)
    return
    tvshows = []
    tvshowsid = []
    command = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetTVShows", "params": {"sort": { "order": "ascending", "method": "label" }}, "id": 1}'
    result = json.loads(xbmc.executeJSONRPC(command))                     
    for i in range(0, result['result']['limits']['total']):
        tvshows.append(result['result']['tvshows'][i]['label'])
        tvshowsid.append(result['result']['tvshows'][i]['tvshowid'])
    tvshows.insert(0, __language__(33902))
    tvshowsid.insert(0, "0")
    whattvshow = xbmcgui.Dialog().select(__language__(33903), tvshows)
    if whattvshow < 0: return
    elif whattvshow == 0:
        scan(which_way)
    else:
        seasons = []
        command = '{"jsonrpc": "2.0", "method": "VideoLibrary.GetEpisodes", "params":{"tvshowid": %s, "properties": ["season"], "sort": { "order": "ascending", "method": "season" }}, "id": 1}' % tvshowsid[whattvshow]
        result = json.loads(xbmc.executeJSONRPC(command))                     
        for i in range(0, result['result']['limits']['total']):
            seasons.append(str(result['result']['episodes'][i]['season']))
        seasons = remove_duplicates(seasons)
        seasons.insert(0, __language__(33904))
        whatseason = xbmcgui.Dialog().select(__language__(33905), seasons)
        if whatseason < 0: return
        elif whatseason == 0:
            scan(which_way, tvshowsid[whattvshow])
        else:
            scan(which_way, tvshowsid[whattvshow], whatseason)
        
def remove_duplicates(values):
    output = []
    seen = set()
    for value in values:
        if value not in seen:
            output.append(value)
            seen.add(value)
    return output

def scan(way):
    if way == 1:
        pDialog = xbmcgui.DialogProgressBG()
        pDialog.create('TVShow Time > Kodi', __language__(33906))
        pDialog.update(0, message=__language__(33906))
        tvshowList = getTvshowList()
        total = len(tvshowList)  
        for i in range(0, total):
            log('SaveShowProgress(*, %s, %s, %s)' % (tvshowList[i]['show_id'], tvshowList[i]['season'], tvshowList[i]['episode']))
            show_progress = SaveShowProgress(__token__, tvshowList[i]['show_id'], tvshowList[i]['season'], tvshowList[i]['episode'])
            if show_progress.is_set:
                log("tvshow=%s" % tvshowList[i]['title'])
                log("show_progress.is_set=%s" % show_progress.is_set)
            pDialog.update(((100/total)*(i+1)), message=tvshowList[i]['title'])
            if ((i+1) % 30) == 0 and i < (total-1):
                pDialog.update(((100/total)*(i+1)), message=__language__(33908))
                xbmc.sleep(60000)
        xbmcgui.Dialog().ok("TVShow Time > Kodi", __language__(33907))  
    else:
        pDialog = xbmcgui.DialogProgressBG()
        pDialog.create('Kodi > TVShow Time', __language__(33906))
        pDialog.update(0, message=__language__(33906))
        tvshowList = getTvshowList()
        total = len(tvshowList)                                   
        for i in range(0, total):
            log('Show(*, %s)' % tvshowList[i]['show_id'])
            show = Show(__token__, tvshowList[i]['show_id'])            
            if show.is_found:
                log('setTvshowProgress(*, %s, %s, %s)' % (show.id, show.last_season_seen, show.last_episode_seen))
                tvshowProgress = setTvshowProgress(show.id, show.last_season_seen, show.last_episode_seen)
                pDialog.update(((100/total)*(i+1)), message=show.showname)
                if ((i+1) % 30) == 0 and i < (total-1):
                    pDialog.update(((100/total)*(i+1)), message=__language__(33908))
                    xbmc.sleep(60000)
        xbmcgui.Dialog().ok("Kodi > TVShow Time", __language__(33907)) 
    pDialog.close() 
        
def getTvshowList():
    rpccmd = {'jsonrpc': '2.0', 'method': 'VideoLibrary.GetTVShows', 'params': { 'properties': ['title', 'imdbnumber'] }, 'id': 'libTvShows'}
    rpccmd = json.dumps(rpccmd)
    result = xbmc.executeJSONRPC(rpccmd)
    tvshows = json.loads(result)
    tvshows = tvshows['result']['tvshows']
    log('tvshows=%s' % tvshows)  
    tvshowList = []
    for tvshow in tvshows:
        rpccmd = {'jsonrpc': '2.0', 'method': 'VideoLibrary.GetEpisodes', 'params': {'tvshowid': tvshow['tvshowid'], 'properties': ['title', 'season', 'episode']}, 'id': 1}
        rpccmd = json.dumps(rpccmd)
        result = xbmc.executeJSONRPC(rpccmd)
        episodes = json.loads(result)  
        episodes = episodes['result']['episodes']
        lastEpisode = None
        lastSeasonNr = 0
        lastEpisodeNr = 0
        for episode in episodes:
            if (episode['season'] > lastSeasonNr):
                lastSeasonNr = episode['season']
                lastEpisodeNr = episode['episode']
                lastEpisode = episode
            elif (episode['season'] == lastSeasonNr and episode['episode'] > lastEpisodeNr):
                lastEpisodeNr = episode['episode']
                lastEpisode = episode
        if lastEpisode != None:
            tvshowList.append({
                'title': tvshow['title'],
                'show_id': tvshow['imdbnumber'],
                'season': lastEpisode['season'],
                'episode': lastEpisode['episode']
            })
    log('list=%s' % tvshowList)
    return tvshowList
    
def setTvshowProgress(show_id, last_season_seen, last_episode_seen):
    rpccmd = {'jsonrpc': '2.0', 'method': 'VideoLibrary.GetTVShows', 'params': { 'properties': ['title', 'imdbnumber'] }, 'id': 'libTvShows'}
    rpccmd = json.dumps(rpccmd)
    result = xbmc.executeJSONRPC(rpccmd)
    tvshows = json.loads(result)
    tvshows = tvshows['result']['tvshows']
    log('tvshows=%s' % tvshows)
    for tvshow in tvshows:
        if int(tvshow['imdbnumber']) == int(show_id):
            log('tvshow=%s' % tvshow)
            rpccmd = {'jsonrpc': '2.0', 'method': 'VideoLibrary.GetEpisodes', 'params': {'tvshowid': tvshow['tvshowid'], 'properties': ['title', 'season', 'episode']}, 'id': 1}
            rpccmd = json.dumps(rpccmd)
            result = xbmc.executeJSONRPC(rpccmd)
            episodes = json.loads(result)  
            episodes = episodes['result']['episodes']
            for episode in episodes:
                log('episode=%s' % episode) 
                if (episode['season'] <= last_season_seen and episode['episode'] <= last_episode_seen):               
                    command2 = '{"jsonrpc": "2.0", "id": 1, "method": "VideoLibrary.SetEpisodeDetails", "params": {"episodeid" : %s, "playcount": %s}}' % (episode['episodeid'], 1)
                    result2 = json.loads(xbmc.executeJSONRPC(command2))
                    log('watched=%s' % 1)
                else:         
                    command2 = '{"jsonrpc": "2.0", "id": 1, "method": "VideoLibrary.SetEpisodeDetails", "params": {"episodeid" : %s, "playcount": %s}}' % (episode['episodeid'], 0)
                    result2 = json.loads(xbmc.executeJSONRPC(command2))
                    log('watched=%s' % 0)
 
def formatNumber(number):
    if len(number) < 2:
         number = '0%s' % number
    return number
     
def formatName(filename):
    filename = filename.strip()
    filename = filename.replace(' ', '.')
    return filename	 
    
def notif(msg, time=5000):
    if __notifications__ == 'true':
        xbmcgui.Dialog().notification(encode(__scriptname__), encode(msg), time=time, icon=__icon__)

def log(msg):
    xbmc.log("### [%s] - %s" % (__scriptname__, encode(msg), ),
            level=xbmc.LOGDEBUG) #100 #xbmc.LOGDEBUG

def encode(string):
    result = ''
    try:
        result = string.encode('UTF-8','replace')
    except UnicodeDecodeError:
        result = 'Unicode Error'
    return result         

start()
