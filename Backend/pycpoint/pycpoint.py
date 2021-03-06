#!/usr/bin/env python
#
# pycpoint
#
# Copyright (c) 2009 Mark Henkelis
# Portions Copyright Brisa Team <brisa-develop@garage.maemo.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Author: Mark Henkelis <mark.henkelis@tesco.net>

################################################################################
# TODO:
################################################################################
#
# 2) Wrap on_now text (or scroll it)
# 3) Don't process devices that aren't mediaservers, mediarenderers or control points
# 5) Queue manipulation
# 6) Add more details to media list when displaying a queue


# fix this
#DEBUG	sonos                         :2329:_event_renewal_callback() Event renew done cargo=None sid=uuid:EISBCPGQBFTOWBIKEJF timeout=1800
#DEBUG	sonos                         :2329:_event_renewal_callback() Event renew done cargo=None sid=uuid:RINCON_000E5823A88A01400_sub0000000058 timeout=1800
#DEBUG	sonos                         :2329:_event_renewal_callback() Event renew done cargo=None sid=uuid:RINCON_000E5830D2F001400_sub0000000036 timeout=1800
#DEBUG	sonos                         :2329:_event_renewal_callback() Event renew done cargo=None sid=uuid:HHYIWSGZOTJHPKGSYED timeout=1800
#DEBUG	sonos                         :2329:_event_renewal_callback() Event renew done cargo=None sid=uuid:RINCON_000E5823A88A01400_sub0000000059 timeout=1800
#DEBUG	sonos                         :2329:_event_renewal_callback() Event renew done cargo=None sid=uuid:RINCON_000E5830D2F001400_sub0000000037 timeout=1800
#DEBUG	sonos                         :2329:_event_renewal_callback() Event renew done cargo=None sid=uuid:RINCON_000E5830D2F001400_sub0000000038 timeout=1800
#DEBUG	sonos                         :2329:_event_renewal_callback() Event renew done cargo=None sid=uuid:RINCON_000E5830D2F001400_sub0000000039 timeout=1800
#DEBUG	sonos                         :2329:_event_renewal_callback() Event renew done cargo=None sid= timeout=0
#DEBUG	sonos                         :2329:_event_renewal_callback() Event renew done cargo=None sid= timeout=0


# only run counter/get position when playing and now_playing active


# Deactivate stop button when already stopped etc
# When stopping a track that has been paused, if it's the last track in a queue the Sonos returns to the first track in the queue - but we haven't set the metadata for that. ACTUALLY seems to be related to the return of a playlist class.
# Need to subscribe to zone player events (e.g. if the zone name is changed)
# Need to tidy up new classes and rest of code



#import log
from brisa.core import log
from brisa.core.log import modcheck

import brisa

from msgBox import messageBox
from editBox import editBox
#import msgBox

import threading
import gobject

from brisa.core.network import get_active_ifaces, get_ip_address

#print sys.path
#print sys.modules
#sys.path.insert(0,'/home/mark/UPnP/Sonos2/site-packages')
#print sys.path

import re

from Queue import Queue, Empty
from threading import Lock
import datetime
    


from brisa.core.reactors import Gtk2Reactor
reactor = Gtk2Reactor()

from brisa.upnp.control_point.service import Service, SubscribeRequest

import pprint
pp = pprint.PrettyPrinter(indent=4)


import gtk
import gtk.glade
#import gobject

#from threading import Thread

import xml.dom
from xml.dom import minidom
from xml.dom.minidom import parseString


from xml.etree.ElementTree import Element, SubElement, dump

from xml.etree.ElementTree import _ElementInterface
from xml.etree import cElementTree as ElementTree

#from brisa.upnp.control_point import ControlPointAV
from control_point_sonos import ControlPointSonos
#from brisa.threading import ThreadManager, ThreadObject
#from brisa.upnp.didl.didl_lite import Container, Element, ElementItem, SonosMusicTrack, SonosAudioBroadcast, find, SonosItem, MusicAlbum
from brisa.upnp.didl.didl_lite import *     # TODO: fix this
#from brisa.core.network import parse_url
#from brisa.upnp.control_point.control_point import get_service_control_url
from brisa.core.network import parse_xml
from brisa.core.network import parse_url, url_fetch
from brisa.core.threaded_call import run_async_function

from brisa.utils.looping_call import LoopingCall

from music_items import music_item, dump_element, getAlbumArt, prettyPrint

from sonos_service import radiotimeMediaCollection, radiotimeMediaMetadata

from brisa.upnp.soap import HTTPTransport, HTTPError

from optparse import OptionParser

from brisa import url_fetch_attempts, url_fetch_attempts_interval, __skip_service_xml__, __skip_soap_service__, __tolerate_service_parse_failure__, __enable_logging__, __enable_webserver_logging__, __enable_offline_mode__, __enable_events_logging__

try:
    import hildon
    is_hildon = True
    print "is_hildon"
except:
    is_hildon = False
    print "isnt_hildon"

#import sys
#print sys.path
#print sys.modules



# GTK
# When updating GTK directly from the GUI, we are in the GTK thread
# When updating from an event, we are not in the GKT thread so need to call enter/leave

def ppxml(xmlstring):
    print minidom.parseString(xmlstring).toprettyxml()

def ppxmlre(xmlstring):
    newdata = xmlstring.replace("&amp;","&")
    newdata = newdata.replace("&amp;","&")
    newdata = newdata.replace("&amp;","&")
#    newdata = newdata.replace("&quot;","\"")
#    newdata = newdata.replace("&lt;","<")
#    newdata = newdata.replace("&gt;",">")
    newdata = newdata.replace("&","&amp;")
    print minidom.parseString(newdata).toprettyxml()

class ControlPointGUI(object):

    comboBox_server_devices = None
    comboBox_renderer_devices = None
    container_treestore = None
    container_tree_view = None

#    current_server_device = None
#    current_renderer_device = None

    current_media_id = None
#    current_radio_id = None
    current_media_xml = ''
    current_media_type = ''
    current_renderer_events_avt = {}
    current_renderer_events_rc = {}

    playing_window = None
    now_playing = ''
    now_extras = ''
    now_playing_pos = ''
    processing_event = False
    event_queue = Queue()
    last_event_seq = {}
    event_lock = Lock()

    info_window = None
    info = ''

    current_position = {}
    current_track = '-1'
    current_track_duration = ''
    current_track_URI = ''
    current_track_metadata = ''
    current_track_relative_time_position = ''

    current_queue_length = -1
    current_queue_updateid = -1
    
    current_music_item = music_item()

    music_services = {}
    AvailableServiceTypeList = ''
    AvailableServiceListVersion = ''
    test = None

    muted = 0
    play_state = ''
    current_renderer_output_fixed = '1'

#    control_point_manager = None

#    kill_app = False
    media_list = []

    known_zone_players = {}
    known_zone_names = {}
    known_media_servers = {}
    known_media_renderers = {}

    thirdpartymediaservers = {}
    services = {}
    
    zoneattributes = {}
    
    subscriptions = []

    msms_root_items = []
    msms_root_items.append(['All Music', '4'])
    msms_root_items.append(['Genre', '5'])
    msms_root_items.append(['Artist', '6'])
    msms_root_items.append(['Album', '7'])
    msms_root_items.append(['Playlists', 'F'])
    msms_root_items.append(['Folders', '14'])
    msms_root_items.append(['Contributing Artists', '100'])
    msms_root_items.append(['Album Artist', '107'])
    msms_root_items.append(['Composer', '108'])
    msms_root_items.append(['Rating', '101'])

    msms_rating_items = []
    msms_rating_items.append(['1 or more stars', '102'])
    msms_rating_items.append(['2 or more stars', '103'])
    msms_rating_items.append(['3 or more stars', '104'])
    msms_rating_items.append(['4 or more stars', '105'])
    msms_rating_items.append(['5 or more stars', '106'])

    msms_search_lookup = { '4' : 'upnp:class derivedfrom "object.item.audioItem"',
                           '5' : 'upnp:class = "object.container.genre.musicGenre"',
                           '6' : 'upnp:class = "object.container.person.musicArtist"',
                           '7' : 'upnp:class = "object.container.album.musicAlbum"',
                           'F' : 'upnp:class = "object.container.playlistContainer"',
                           '14' : 'upnp:class = "object.storageFolder"',
                           '100' : 'upnp:class = "object.container.person.musicArtist"',
                           '107' : 'upnp:class = "object.container.person.musicArtist"',
                           '108' : 'upnp:class = "object.container.person.musicArtist"',
                           '101' : '' }     # dummy, entries are manually created

    msms_search_lookup_item = { '4' : '',   # dummy, higher search returns items
                                '5' : 'TODO',
                                '6' : 'upnp:artist = "%s"',
                                '7' : 'BROWSE',
                                'F' : 'upnp:TODO = "%s"',
                                '14' : 'upnp:TODO = "%s"',
                                '100' : 'upnp:TODO = "%s"',
                                '107' : 'upnp:TODO = "%s"',
                                '108' : 'upnp:TODO = "%s"',
                                '101' : '' }

    msms_search_browse_sortcriteria = { '4' : '',
                                        '5' : '',
                                        '6' : '',
                                        '7' : '+upnp:originalTrackNumber',
                                        'F' : '',
                                        '14' : '',
                                        '100' : '',
                                        '107' : '',
                                        '108' : '',
                                        '101' : '' }

#dc:title,res,res@duration,upnp:artist,upnp:artist@role,upnp:album,upnp:originalTrackNumber    

#Search("0", upnp:class = "object.container.person.musicArtist", "", "*", 0, 0, "")
#Search("0", upnp:class = "object.container.person.musicArtist", "", "*", 0, 10, "")
#Search("0", upnp:class = "object.container.album.musicAlbum" and upnp:artist = "Artist 1", "", "*", 0, 10, "")
#Browse(RESULT, "BrowseDirectChildren", "", 0, 10, "")

#    idle_count = 0



    usage = "usage: %prog [options] arg"
    parser = OptionParser(usage)
    
    parser.add_option("-m", "--module", action="append", type="string", dest="modcheckmods")
    parser.add_option("-d", "--debug", action="store_true", dest="debug")
    parser.add_option("-q", "--quiet", action="store_true", dest="quiet")

    (options, args) = parser.parse_args()

    print "############## args ###############"
    if options.debug:
        print "option.debug: " + str(options.debug)
        modcheck['all'] = True
    if options.quiet:
        print "option.quiet: " + str(options.quiet)
    if options.modcheckmods:
        for m in options.modcheckmods:
            print "    module: " + str(m)
            modcheck[m] = True
    print "###################################"
    print ""
    print "###################################"
    __enable_webserver_logging__ = True
    __enable_events_logging__ = True
    
    print "url_fetch_attempts                   :" + str(url_fetch_attempts)
    print "url_fetch_attempts_interval          :" + str(url_fetch_attempts_interval)
    print "__skip_service_xml__                 :" + str(__skip_service_xml__)
    print "__skip_soap_service__                :" + str(__skip_soap_service__)
    print "__tolerate_service_parse_failure__   :" + str(__tolerate_service_parse_failure__)
    print "__enable_logging__                   :" + str(__enable_logging__)
    print "__enable_webserver_logging__         :" + str(__enable_webserver_logging__)
    print "__enable_offline_mode__              :" + str(__enable_offline_mode__)
    print "__enable_events_logging__            :" + str(__enable_events_logging__)
    print "###################################"



    def __init__(self):
        signals={"gtk_main_quit": self._main_quit,
                 "on_quit_activate": self._main_quit,
                 "on_info_clicked": self._on_info_clicked}

        log.debug("__init__")

        self.control_point = ControlPointSonos()
        self.control_point.subscribe("new_device_event", self.on_new_device)
        self.control_point.subscribe("removed_device_event", self.on_del_device)
#        self.control_point.subscribe('device_event', self.on_device_event)
        self.control_point.subscribe('device_event_seq', self.on_device_event_seq)

        self.glade_xml = gtk.glade.XML('control_point_gtk.glade')
        self.create_all_screen_objects()
        self.glade_xml.signal_autoconnect(signals)
        self.adjust_main_to_hildon()

        self.control_point.start()
        
        self.info_loop = LoopingCall(self.update_position)
        self.info_loop.start(1, now=True)
        
#        self.control_point.start_search(600.0, "ssdp:all")
        run_async_function(self.control_point.start_search, (600.0, "ssdp:all"), 1)

#        self.idle_id = gobject.idle_add(self.idle_callback)


#    def idle_callback(self):
#        self.idle_count += 1
#        print "<<<< IDLE>>>>" + str(self.idle_count)
#        if self.idle_count == 50000:
#            gobject.source_remove(self.idle_id)
#        return True


    def create_all_screen_objects(self):
        self.create_server_combo_box()
        self.create_renderer_combo_box()
        self.create_container_tree_view()
        self.create_item_media_list()

    def create_server_combo_box(self):
        hbox = self.glade_xml.get_widget("hbox_servers")
        liststore = gtk.ListStore(str, str)
        liststore.set_sort_column_id(0, gtk.SORT_ASCENDING)
        self.comboBox_server_devices = gtk.ComboBox(liststore)
        self.comboBox_server_devices.connect('changed', self._changed_server_devices)
        cell = gtk.CellRendererText()
        self.comboBox_server_devices.pack_start(cell, True)
        self.comboBox_server_devices.add_attribute(cell, 'text', 0)
        hbox.add(self.comboBox_server_devices)
        self.comboBox_server_devices.show()

    def create_renderer_combo_box(self):
        hbox = self.glade_xml.get_widget("hbox_renders")
        liststore = gtk.ListStore(str, str)
        liststore.set_sort_column_id(0, gtk.SORT_ASCENDING)
        self.comboBox_renderer_devices = gtk.ComboBox(liststore)
        self.comboBox_renderer_devices.connect('changed', self._changed_renderer_devices)
        cell = gtk.CellRendererText()
        self.comboBox_renderer_devices.pack_start(cell, True)
        self.comboBox_renderer_devices.add_attribute(cell, 'text', 0)
        hbox.add(self.comboBox_renderer_devices)
        self.comboBox_renderer_devices.show()

    def create_container_tree_view(self):
        self.container_treestore = gtk.TreeStore(str, str, object, str)
#        self.container_treestore.set_sort_column_id(0, gtk.SORT_ASCENDING) # this slows things down massively
        self.container_treeview = gtk.TreeView(self.container_treestore)
        self.container_treeview.set_fixed_height_mode(True)
#        self.container_treeview.set_enable_tree_lines(True)
#        self.container_treeview.set_grid_lines(gtk.TREE_VIEW_GRID_LINES_HORIZONTAL)
        self.container_treeview.connect("row_activated", self._on_container_treeview_activated, '')
        self.container_treeview.connect("button_press_event", self._container_button_press)
        tvcolumn = gtk.TreeViewColumn('Containers')
        tvcolumn.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
        self.container_treeview.append_column(tvcolumn)
        cell = gtk.CellRendererText()
        tvcolumn.pack_start(cell, True)
        tvcolumn.add_attribute(cell, 'text', 0)
        tree_hbox = self.glade_xml.get_widget('tree_hbox')
        tree_hbox.add(self.container_treeview)
        self.container_treeview.show()

    def create_item_media_list(self):
        self.item_media_list_liststore = gtk.ListStore(str, str, str, str)
#        self.item_media_list_liststore.set_sort_column_id(0, gtk.SORT_ASCENDING)
        self.item_media_list_treeview = gtk.TreeView(self.item_media_list_liststore)
        self.item_media_list_treeview.connect("cursor-changed", self._on_media_item_listview_changed)
        self.item_media_list_treeview.connect("row_activated", self._on_media_item_selected)
        self.item_media_list_treeview.connect("button_press_event", self._item_media_list_button_press)
        tvcolumn = gtk.TreeViewColumn('Title')
        self.item_media_list_treeview.append_column(tvcolumn)
        cell = gtk.CellRendererText()
        tvcolumn.pack_start(cell, True)
        tvcolumn.add_attribute(cell, 'text', 0)
        tree_hbox = self.glade_xml.get_widget('list_viewport')
        tree_hbox.add(self.item_media_list_treeview)
        self.item_media_list_treeview.show()

    def show_playing_window(self):
        # at this point we are within a GTK thread so don't use enter/leave
        if self.playing_window == None:
            signals={"gtk_playing_quit": self._playing_quit,
                     "on_playing_quit_activate": self._playing_quit,
                     "on_refresh_clicked": self._on_refresh_clicked,
                     "on_play_clicked": self._on_play_clicked,
                     "on_stop_clicked": self._on_stop_clicked,
                     "on_next_clicked": self._on_next_clicked,
                     "on_previous_clicked": self._on_previous_clicked,
                     "on_mute_clicked": self._on_mute_clicked,
                     "on_volume_value_changed": self._on_volume_changed}
            if is_hildon:
                self.glade_playing_xml = gtk.glade.XML('now_playing_gtk_maemo.glade')
            else:
                self.glade_playing_xml = gtk.glade.XML('now_playing_gtk.glade')
            self.glade_playing_xml.signal_autoconnect(signals)
            self.playing_window = self.glade_playing_xml.get_widget('now_playing_window')
            # trap when top level widget is destroyed within window (won't get window destroy event)
#            gtk_playing_vbox=self.glade_playing_xml.get_widget('playing_vbox')
#            gtk_playing_vbox.connect("destroy", self._playing_destroy)
            self.playing_window.show_all()
            self.adjust_playing_to_hildon()

    def show_info_window(self):
        # at this point we are within a GTK thread so don't use enter/leave
        if self.info_window == None:
            signals={"gtk_info_quit": self._info_quit,
                     "on_info_quit_activate": self._info_quit}
            if is_hildon:
                self.glade_info_xml = gtk.glade.XML('info_gtk_maemo.glade')
            else:
                self.glade_info_xml = gtk.glade.XML('info_gtk.glade')
            self.glade_info_xml.signal_autoconnect(signals)
            self.info_window = self.glade_info_xml.get_widget('info_window')
            # trap when top level widget is destroyed within window (won't get window destroy event)
#            gtk_info_vbox=self.glade_playing_xml.get_widget('info_vbox')
#            gtk_info_vbox.connect("destroy", self._info_destroy)
            self.info_window.show_all()
#            self.adjust_info_to_hildon()    # TODO: create this method

    def create_main_window(self):
        window = hildon.Window()
#        window.set_default_size(-1,-1)
        window.set_title("Control Point")
        window.connect("destroy", self._main_quit)
        main_menu = self._create_main_menu()
        window.set_menu(main_menu)
        window.show_all()
        return window

    def create_playing_window(self):
        window = hildon.Window()
#        window.set_default_size(-1,-1)
        window.set_title("Now Playing")
        window.connect("destroy", self._playing_quit)
        playing_menu = self._create_playing_menu()
        window.set_menu(playing_menu)
        window.show_all()
        return window

    def _create_main_menu(self):
        about_item = gtk.MenuItem("About")
        about_item.connect("activate", self._on_about_activated)
        quit_item = gtk.MenuItem("Quit")
        quit_item.connect("activate", self._main_quit)
        help_menu = gtk.Menu()
        help_menu.append(about_item)
        help_item = gtk.MenuItem("Help")
        help_item.set_submenu(help_menu)
        menu = gtk.Menu()
        menu.append(quit_item)
        menu.show()
        return menu

    def _create_playing_menu(self):
        about_item = gtk.MenuItem("About")
        about_item.connect("activate", self._on_about_activated)
        quit_item = gtk.MenuItem("Quit")
        quit_item.connect("activate", self._playing_quit)
        help_menu = gtk.Menu()
        help_menu.append(about_item)
        help_item = gtk.MenuItem("Help")
        help_item.set_submenu(help_menu)
        menu = gtk.Menu()
        menu.append(quit_item)
        menu.show()
        return menu

    def adjust_main_to_hildon(self):
        """Adjust the GUI to be usable in maemo platform."""
        if is_hildon:
            self.app = hildon.Program()
            hildon_main_window = self.create_main_window()
            self.app.add_window(hildon_main_window)
            gtk_main_vbox=self.glade_xml.get_widget('main_vbox')
            gtk_main_vbox.reparent(hildon_main_window)
            main_menu=self.glade_xml.get_widget('main_menu')
            main_menu.destroy()
            gtk_main_window=self.glade_xml.get_widget('main_window')
            gtk_main_window.destroy()

    def adjust_playing_to_hildon(self):
        """Adjust the GUI to be usable in maemo platform."""
        if is_hildon:
#            self.app = hildon.Program()
            hildon_playing_window = self.create_playing_window()
            self.app.add_window(hildon_playing_window)
            gtk_playing_vbox=self.glade_playing_xml.get_widget('playing_vbox')
            gtk_playing_vbox.reparent(hildon_playing_window)
            playing_menu=self.glade_playing_xml.get_widget('playing_menu')
            playing_menu.destroy()
            gtk_playing_window=self.glade_playing_xml.get_widget('now_playing_window')
            gtk_playing_window.destroy()

    def refresh(self):
        log.info('search device refresh event...')
        # TODO: save current selection in either list
        self.generate_server_list()
        self.generate_render_list()

    def generate_server_list(self):
        self._generate_combo('server')

    def generate_render_list(self):
        self._generate_combo('render')

    def in_liststore(self, list_store, device_name, udn):   # this is way too slow
        for entry in list_store:
            l_name, l_udn = entry
            if l_name == device_name and l_udn == udn:
                return True
        return False

    def _generate_combo(self, type):
        if type=='server':
            combo_box = self.comboBox_server_devices
            devices = self.known_media_servers
        else:
            combo_box = self.comboBox_renderer_devices
            devices = self.known_media_renderers
        gtk.gdk.threads_enter()
        list_store = combo_box.get_model()
        for device_object in devices.values():
            if device_object.udn in self.known_zone_names:
                device_name = self.known_zone_names[device_object.udn]
            else:
                device_name = device_object.friendly_name
            if not self.in_liststore(list_store, device_name, device_object.udn):
                list_store.append([device_name, device_object.udn])
        gtk.gdk.threads_leave()


    def subscribe_to_device(self, service):
        try:
#            log.debug("#### SUBSCRIBE_TO_DEVICE BEFORE")
            service.event_subscribe(self.control_point.event_host, self._event_subscribe_callback, None, True, self._event_renewal_callback)
            self.subscriptions.append(service)
#            log.debug("#### SUBSCRIBE_TO_DEVICE AFTER")
        except:
            raise Exception("Error occured during subscribe to device")

    def subscribe_for_variable(self, device, service, variable):
        try:
#            log.debug("#### SUBSCRIBE_FOR_VARIABLE BEFORE")
            print variable
            print service.get_state_variable(variable)
            service.subscribe_for_variable(variable, self._event_variable_callback)
#            log.debug("#### SUBSCRIBE_FOR_VARIABLE AFTER")
        except:
            raise Exception("Error occured during subscribe for variable")

    def _event_variable_callback(self, name, value):
        print "Event message!"
        print 'State variable:', name
        print 'Variable value:', value

#    def renew_device_subscription(self, device, service):
#        try:
#            log.debug("#### RENEW_DEVICE_SUBSCRIPTION BEFORE")
#            device.services[service].event_renew(self.control_point.event_host, self._event_renewal_callback, None)
#            log.debug("#### RENEW_DEVICE_SUBSCRIPTION AFTER")
#        except:
#            raise Exception("Error occured during device subscription renewal")

    def unsubscribe_from_device(self, service):
        try:
#            log.debug("#### UNSUBSCRIBE_FROM_DEVICE BEFORE")
            service.event_unsubscribe(self.control_point.event_host, self._event_unsubscribe_callback, None)
#            log.debug("#### UNSUBSCRIBE_FROM_DEVICE AFTER")
        except:
            raise Exception("Error occured during unsubscribe from device")

    def cancel_subscriptions(self):
        log.debug("Cancelling subscriptions")
        for service in self.subscriptions:
            log.debug("Service: %s", service)
            self.unsubscribe_from_device(service)

    def get_zone_details(self, device):
        return self.control_point.get_zone_attributes(device)


    def radiotime_getlastupdate(self):
        log.debug("#### radiotime_getlastupdate:")

        '''
        <?xml version="1.0" encoding="utf-8"?>
        <soap:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">
          <soap:Body>
            <getLastUpdateResponse xmlns="http://www.sonos.com/Services/1.1">
              <getLastUpdateResult>
                <catalog>string</catalog>
                <favorites>string</favorites>
                <pollInterval>int</pollInterval>
              </getLastUpdateResult>
            </getLastUpdateResponse>
          </soap:Body>
        </soap:Envelope>
        '''
        
        service = self.control_point.get_rt_service()

        rt_result = service.getLastUpdate()

        log.debug("radiotime_getlastupdate browse_result: %s", rt_result)
        log.debug("radiotime_getlastupdate result: %s", rt_result['Result'])


    def radiotime_getmediaURI(self, id):
        log.debug("#### radiotime_getmediaURI:")
        
        service = self.control_point.get_rt_service()

        rt_result = service.getMediaURI(id=id)

        log.debug("radiotime_getlastupdate browse_result: %s", rt_result)

        return rt_result

        
    def radiotime_getmediaURL(self, rtURI):
        
        if rtURI == '' or rtURI == None:
            return 'No RadioTime URI to dereference'
        else:
            try:
                fd = url_fetch(rtURI)
    #        except HTTPError as detail:    # this is 2.6    
            except HTTPError:
                return (None, HTTPError)

            try:
                data = fd.read()
            except:
                log.debug("#### radiotime_getmediaURL fd is invalid")
                return 'radiotime_getmediaURL fd is invalid'

            return data


    def run_test(self, id, iter=None, root=None):

        log.debug("#### run_test: %s", id)

        win = False
        cd = False
        dp = False
        sp = False

        if win:

            addr = 'http://192.168.0.8:1400/msprox?uuid=02286246-a968-4b5b-9a9a-defd5e9237e0'
            data = '<?xml version="1.0" encoding="utf-8"?><s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/"><s:Body><ns0:Browse xmlns:ns0="urn:schemas-upnp-org:service:ContentDirectory:1">'
            data += '<ObjectID>0</ObjectID>'
#            data += '<BrowseFlag>BrowseDirectChildren</BrowseFlag>'
            data += '<BrowseFlag>BrowseMetadata</BrowseFlag>'
            data += '<Filter>*</Filter>'
            data += '<RequestedCount>20</RequestedCount>'
            data += '<StartingIndex>0</StartingIndex>'
#            data += '<SortCriteria>+dc:title</SortCriteria>'
            data += '<SortCriteria></SortCriteria>'
            data += '</ns0:Browse></s:Body></s:Envelope>'
            namespace = "urn:schemas-upnp-org:service:ContentDirectory:1"
            soapaction = "urn:schemas-upnp-org:service:ContentDirectory:1#Browse"
            encoding='utf-8'

            res = HTTPTransport().call(addr, data, namespace, soapaction, encoding)

            print "TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST"
            print "TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST"
            print "Windows MS Browse:"
            print res            
            print "TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST"
            print "TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST"

        if cd:
        
            service = self.control_point.get_cd_service()

            test_result = service.GetSystemUpdateID()
            print "TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST"
            print "TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST"
            print "GetSystemUpdateID:"
            print test_result
            print "TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST"
            print "TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST"

            test_result = service.GetAllPrefixLocations(ObjectID='G:')
            print "TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST"
            print "TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST"
            print "GetAllPrefixLocations:"
            print test_result
            print "TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST"
            print "TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST"
				
    #				FindPrefix
    #					Prefix 

        if dp:
					 
            service = self.control_point.get_dp_service()

            test_result = service.GetHouseholdID()
            print "TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST"
            print "TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST"
            print "GetHouseholdID:"
            print test_result
            print "TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST"
            print "TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST"
            
            test_result = service.GetZoneInfo()
            print "TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST"
            print "TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST"
            print "GetZoneInfo:"
            print test_result
            print "TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST"
            print "TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST"

        if sp:

            service = self.control_point.get_sp_service()
            
            tests = 'R_AudibleActivation', \
                    'R_UpdatePreference', \
                    'R_CustomerID', \
                    'R_RadioPreference', \
                    'R_ShowRhapUPnP', \
                    'R_BrowseByFolderSort', \
                    'R_AudioInEncodeType', \
                    'R_AvailableSvcTrials', \
                    'R_RadioLocation', \
                    'R_ForceReIndex', \
                    'R_PromoVersion', \
                    'RINCON_AssociatedZPUDN'

            for t in tests:
                test_result = service.GetString(VariableName=t)
                print "TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST"
                print "TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST"
                print "var = " + t
                print test_result
                print "TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST"
                print "TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST TEST"


    def in_treestore(self, parent, title, id, type):    # this is way too slow

        # TODO: replace this with optimised code not based on treestore
        child = self.container_treestore.iter_children(parent)
        while child:
            c_title, c_id, c_xml, c_type = self.container_treestore.get(child, 0, 1, 2, 3)
#           print c_title + " - " + c_id + " - " + c_type
            if c_title == title and c_id == id and c_type == type:
                return True
            child = self.container_treestore.iter_next(child)
        return False


    def get_treestore_root_parent_name(self, iter):

        depth = self.container_treestore.iter_depth(iter)
#        print "######### get_treestore_root_parent_name: depth: " + str(depth)
        parent = iter
        for i in range(1, depth+1):
            parent = self.container_treestore.iter_parent(parent)
        parentname = self.container_treestore.get_value(parent, 0)
#        print "######### get_treestore_root_parent_name: parentname: " + str(parentname)
        return parentname


    def get_treestore_parent_id(self, iter):

        parent = self.container_treestore.iter_parent(iter)
        parentid = self.container_treestore.get_value(parent, 1)
#        print "######### get_treestore_parent_id: parentname: " + str(parentid)
        return parentid


    def container_append(self, iter, tuple):
        self.container_treestore.append(iter, tuple)
        
        
    def liststore_append(self, tuple):
        self.item_media_list_liststore.append(tuple)


    def browse_radiotime(self, id, iter=None, root=None):

        radiotimecount = 2000
        
        log.debug("#### browse_radiotime: %s", id)
        
        service = self.control_point.get_rt_service()

        self.set_messagebar("Browsing...")

        if root == None:
            id_param = id
            browse_result = service.getMetadata(id=id_param, index=0, count=radiotimecount)
        else:
            id_param = root
            if id_param == 'root':
#                browse_result = service.getMetadata(id=id_param, index=0, count=97)
                browse_result = service.getMetadata(id=id_param, index=0, count=radiotimecount)
            else:
                browse_result = service.getMetadata(id=id_param, index=0, count=radiotimecount)
        
        log.debug("browse_radiotime browse_result: %s", browse_result)
        log.debug("browse_radiotime result: %s", browse_result['Result'])

        items = browse_result['Result']
        index = int(browse_result['{http://www.sonos.com/Services/1.1}index'])
        count = int(browse_result['{http://www.sonos.com/Services/1.1}count'])
        returned = count
        total = int(browse_result['{http://www.sonos.com/Services/1.1}total'])
        log.debug("browse_radiotime: index=%s count=%s total=%s", index, count, total)

        self.set_messagebar("Returned %d of %d." % (returned, total))

        if total > radiotimecount:
            while returned < total:
                b = service.getMetadata(id=id_param, index=returned, count=radiotimecount)

                index = int(b['{http://www.sonos.com/Services/1.1}index'])
                count = int(b['{http://www.sonos.com/Services/1.1}count'])
# Radiotime reduces the number of results available as you query and increase the index
#                total = int(b['{http://www.sonos.com/Services/1.1}total'])
                for item in b['Result'].getchildren():
                    items.append(item)
                returned += count
                log.debug("browse_radiotime: index=%s count=%s total=%s", index, count, total)

                self.set_messagebar("Returned %d of %d." % (returned, total))
                
        for item in items.getchildren():
            '''
			<mediaCollection>
				<id>y1</id>
				<title>Music</title>
				<itemType>container</itemType>
				<authRequired>false</authRequired>
				<canPlay>false</canPlay>
				<canEnumerate>true</canEnumerate>
				<canCache>true</canCache>
				<homogeneous>false</homogeneous>
				<canAddToFavorite>false</canAddToFavorite>
				<canScroll>false</canScroll>
			</mediaCollection>

			<mediaCollection>
				<id>p115805</id>
				<title>104.1 Music</title>
				<itemType>show</itemType>
				<authRequired>false</authRequired>
				<canPlay>false</canPlay>
				<canEnumerate>true</canEnumerate>
				<canCache>false</canCache>
				<homogeneous>false</homogeneous>
				<canAddToFavorite>false</canAddToFavorite>
				<canScroll>false</canScroll>
			</mediaCollection>
			
            <mediaMetadata>
                <id>s1254</id>
                <title>Radio Cook Islands 630 (Community)</title>
                <itemType>stream</itemType>
                <language>en</language>
                <country>COK</country>
                <genreId>g249</genreId>
                <genre>Community</genre>
                <twitterId/>
                <liveNow>true</liveNow>
                <onDemand>false</onDemand>
                <streamMetadata>
                    <bitrate>16</bitrate>
                    <reliability>55</reliability>
                    <logo>http://radiotime-logos.s3.amazonaws.com/s1254q.gif</logo>
                    <title>630 AM</title>
                    <subtitle>Avarua, Cook Islands</subtitle>
                    <secondsRemaining>0</secondsRemaining>
                    <secondsToNextShow>0</secondsToNextShow>
                    <nextShowSeconds>0</nextShowSeconds>
                </streamMetadata>
            </mediaMetadata>

			<mediaMetadata>
                <id>p115805:schedule</id>
                <title>Next available in 6 hours 59 minutes</title>
                <itemType>other</itemType>
                <language>en</language>
                <country>USA</country>
                <genreId>g115</genreId>
                <genre>Modern Rock</genre>
                <twitterId>1041itjustrocks</twitterId>
                <liveNow>false</liveNow>
                <onDemand>false</onDemand>
                <streamMetadata>
                    <currentShowId>p115805</currentShowId>
                    <currentShow>104.1 Music</currentShow>
                    <currentHost/>
                    <bitrate>0</bitrate>
                    <reliability>0</reliability>
                    <logo>http://radiotime-logos.s3.amazonaws.com/s32717q.gif</logo>
                    <secondsRemaining>0</secondsRemaining>
                    <secondsToNextShow>25145</secondsToNextShow>
                    <nextShowStationId>s32717</nextShowStationId>
                    <nextShowSeconds>3600</nextShowSeconds>
                </streamMetadata>
			</mediaMetadata>
            
			<mediaMetadata>
				<id>t31332491:p116360</id>
				<title>the neapolitan revival</title>
                <mimeType>audio/vnd.radiotime</mimeType>
                <itemType>track</itemType>
                <liveNow>false</liveNow>
                <onDemand>true</onDemand>
                <trackMetadata>
                    <artist>John Aielli</artist>
                    <albumArtURI>http://radiotime-logos.s3.amazonaws.com/p0q.gif</albumArtURI>
                    <genre>Music Talk</genre>
                    <duration>0</duration>
                    <associatedShow>Aielli Unleashed podcast</associatedShow>
                    <associatedHost>John Aielli</associatedHost>
                </trackMetadata>
			</mediaMetadata>
            
            '''

            element = ElementTree.fromstring(item.text)

            id = element.find('{http://www.sonos.com/Services/1.1}id').text
            title = element.find('{http://www.sonos.com/Services/1.1}title').text
            itemType = element.find('{http://www.sonos.com/Services/1.1}itemType').text
            xml = [None, None]    # nothing to play at this level

            if itemType == 'container':
#                if not self.in_treestore(iter, title, id, "RADIOTIME"):
                self.container_append(iter, [title, id, xml, "RADIOTIME"])

            elif itemType == 'show':
#                if not self.in_treestore(iter, title, id, "RADIOTIME"):
                self.container_append(iter, [title, id, xml, "RADIOTIME"])

            elif itemType == 'other':
            
                xml = None    # cannnot play these future items

                self.liststore_append([title, id, xml, "RADIOTIME"])
                
            elif itemType == 'track':
            
                radiotype = radiotimeMediaMetadata().from_element(element)

                (model, iter) = self.container_treeview.get_selection().get_selected()
                parentname = model.get_value(iter, 0)
                parentid = model.get_value(iter, 1)
                parentxml = model.get_value(iter, 2)
                parenttype = model.get_value(iter, 3)

                xml =  '<item id="' + 'F00030020' + radiotype.id + '" parentID="' + 'F000b0064' + parentid + '" restricted="true">'
                xml += '<dc:title>' + radiotype.title + '</dc:title>'
                xml += '<upnp:class>object.item.audioItem.musicTrack.recentShow</upnp:class>'
                xml += '<desc id="cdudn" nameSpace="urn:schemas-rinconnetworks-com:metadata-1-0/">RINCON_AssociatedZPUDN</desc>'
                xml += '</item>'

                self.liststore_append([title, id, xml, "RADIOTIME"])
                
            elif itemType == 'stream':

                radiotype = radiotimeMediaMetadata().from_element(element)

# TODO:
# find out where other attribs come from

                (model, iter) = self.container_treeview.get_selection().get_selected()
                parentname = model.get_value(iter, 0)
                parentid = model.get_value(iter, 1)
                parentxml = model.get_value(iter, 2)
                parenttype = model.get_value(iter, 3)

                xml =  '<item id="' + 'F00090020' + radiotype.id + '" parentID="' + 'F00080064' + parentid + '" restricted="true">'
                xml += '<dc:title>' + radiotype.title + '</dc:title>'
                xml += '<upnp:class>object.item.audioItem.audioBroadcast</upnp:class>'
                xml += '<desc id="cdudn" nameSpace="urn:schemas-rinconnetworks-com:metadata-1-0/">RINCON_AssociatedZPUDN</desc>'
                xml += '</item>'

                self.liststore_append([title, id, xml, "RADIOTIME"])

            else:

                # TODO: also need to cater for 'program'

                print "HELP HELP HELP HELP HELP HELP HELP HELP HELP HELP HELP"
                print "HELP HELP HELP HELP HELP HELP HELP HELP HELP HELP HELP"
                print "HELP HELP HELP HELP HELP HELP HELP HELP HELP HELP HELP"

                print "Unknown itemType " + str(itemType) + " in browseRadiotime!"

                print "HELP HELP HELP HELP HELP HELP HELP HELP HELP HELP HELP"
                print "HELP HELP HELP HELP HELP HELP HELP HELP HELP HELP HELP"
                print "HELP HELP HELP HELP HELP HELP HELP HELP HELP HELP HELP"




    def get_queue_length(self, id):
        log.debug("#### get_queue_length: %s", id)
        mscount = 2
        browse_result = self.control_point.browse(id, 'BrowseDirectChildren', '*', 0, mscount, '+dc:title')
        self.current_queue_length = int(browse_result['TotalMatches'])
        self.current_queue_updateid = int(browse_result['UpdateID'])


    def browse_media_server(self, id, iter=None):
        log.debug("#### browse_media_server: %s", id)
        
        mscount = 2000
        
#        search_capabilities = self.control_point.get_search_capabilites()
#        log.debug("#### browse_media_server search capabilities: %s", search_capabilities)
#        sort_capabilities = self.control_point.get_sort_capabilities()
#        log.debug("#### browse_media_server sort capabilities: %s", sort_capabilities)
#{'SearchCaps': 'upnp:class,dc:title,dc:creator,res@protocolInfo'}

# TODO: need to decide how to cater for multiple server types - maybe we stick to audio for now

#       browse_result = self.control_point.browse(id, 'BrowseDirectChildren', '*', 0, mscount, 'dc:title')
        # dc:title not supported on NAS? Need to check with GetSortCriteria...
#        browse_result = self.control_point.browse(id, 'BrowseDirectChildren', '*', 0, mscount, '')

        self.set_messagebar("Browsing...")
        
        browse_result = self.control_point.browse(id, 'BrowseDirectChildren', '*', 0, mscount, '+dc:title')
        
        if 'faultcode' in browse_result:
            messageBox(browse_result['detail'],'Browse Response Error')
            return
        elif not 'Result' in browse_result:
            messageBox('UNKNOWN RESPONSE FROM BROWSE REQUEST','Browse Response Error')
            return
        
        items = browse_result['Result']
        total = int(browse_result['TotalMatches'])
        returned = int(browse_result['NumberReturned'])
#        log.debug("browse_media_server: %s items, %s total, %s returned", items, total, returned)

        self.set_messagebar("Returned %d of %d." % (returned, total))

        if total > mscount:
            while returned < total:
#                b = self.control_point.browse(id, 'BrowseDirectChildren', '*', returned, mscount, '')
                b = self.control_point.browse(id, 'BrowseDirectChildren', '*', returned, mscount, '+dc:title')
                items = items + b['Result']
                returned += int(b['NumberReturned'])
                self.set_messagebar("Returned %d of %d." % (returned, total))
                
        for item in items:

            if isinstance(item, Container):

                '''
                <container 
                        childCount="0" 
                        id="A:ALBUMARTIST/30%20Seconds%20To%20Mars/A%20Beautiful%20Lie" 
                        parentID="A:ALBUMARTIST/30%20Seconds%20To%20Mars" 
                        restricted="true" 
                        searchable="false" >
                    <dc:title>A Beautiful Lie</dc:title>
                    <upnp:class>object.container.album.musicAlbum</upnp:class>
                    <dc:creator>30 Seconds To Mars</dc:creator>
                    <upnp:writeStatus>NOT_WRITABLE</upnp:writeStatus>
                    <res protocolInfo="x-rincon-playlist:*:*:*">x-rincon-playlist:RINCON_000E5830D2F001400#A:ALBUMARTIST/30%20Seconds%20To%20Mars/A%20Beautiful%20Lie</res>
                    <upnp:albumArtURI>/getaa?u=x-file-cifs%3a%2f%2fNAS%2fMusic%2f30%2520Seconds%2520to%2520Mars%2fA%2520Beautiful%2520Lie%2f30%2520Seconds%2520to%2520Mars%2520-%2520Attack.mp3&v=229</upnp:albumArtURI>
                </container>
                
                <item id="A:ALBUMARTIST/30%20Seconds%20To%20Mars/A%20Beautiful%20Lie" 
                      parentID="A:ALBUMARTIST/30%20Seconds%20To%20Mars" 
                      restricted="true">
                    <dc:title>A Beautiful Lie</dc:title>
                    <upnp:class>object.container.album.musicAlbum</upnp:class>
                    <desc id="cdudn" nameSpace="urn:schemas-rinconnetworks-com:metadata-1-0/">RINCON_AssociatedZPUDN</desc>
                </item>                

current_media_id: A:ALBUMARTIST/30%20Seconds%20To%20Mars/A%20Beautiful%20Lie
current_media_xml: <item id="A:ALBUMARTIST/30%20Seconds%20To%20Mars/A%20Beautiful%20Lie" 
                         parentID="A:ALBUMARTIST/30%20Seconds%20To%20Mars" 
                         restricted="true">
                       <dc:title>A Beautiful Lie</dc:title>
                       <upnp:class>object.container.album.musicAlbum</upnp:class>
                       <desc id="cdudn" nameSpace="urn:schemas-rinconnetworks-com:metadata-1-0/">RINCON_AssociatedZPUDN</desc>
                    </item>

                '''

#                meta = self.control_point.browse(id, 'BrowseMetadata', '*', 0, 20, '+dc:title')
#                print "MMMMMMMMMMMMMMMMMMMMMMMMMM"
#                print meta
#                print "id: " + str(id)
#                print ElementTree.tostring(meta['Result'][0].to_didl_element())
#                print "MMMMMMMMMMMMMMMMMMMMMMMMMM"

                data = self.convert_item_to_uridata(item)

                # check if current server is a zone player
                current_server = self.control_point.get_current_server()
                if current_server.udn in self.known_zone_players:
                    # as it's a Sonos, adjust the items to display
                    '''
			        <container id="A:" parentID="0" restricted="true">
					        Attributes
					        object.container
			        <container id="S:" parentID="0" restricted="false">
					        Music Shares
					        object.container
			        <container id="Q:" parentID="0" restricted="true">
					        Queues
					        object.container
			        <container id="SQ:" parentID="0" restricted="true">
					        Saved Queues
					        object.container
			        <container id="R:" parentID="0" restricted="true">
					        Internet Radio
					        object.container
			        <container id="G:" parentID="0" restricted="true">
					        Now Playing
					        object.container
			        <container id="AI:" parentID="0" restricted="true">
					        Audio Inputs
					        object.container
			        <container id="EN:" parentID="0" restricted="true">
					        Entire Network
					        object.container
                    '''
                    if item.id == "A:":
                        item.title = "Music Library"
                    elif item.id == "S:":
                        pass
                    elif item.id == "Q:":
                        # for the current queue, there is a single child avt 0 that is the queue
                        item.id = "Q:0"                    
                        item.title = "Current Queue"
                    elif item.id == "SQ:":
                        item.title = "Sonos Playlists"
                    elif item.id == "R:":
                        item.title = "DO NOT DISPLAY"
                    elif item.id == "G:":
                        item.title = "DO NOT DISPLAY"
                    elif item.id == "AI:":
                        item.title = "Line-In"
                    elif item.id == "EN:":
                        item.title = "DO NOT DISPLAY"
                    else:
                        # let everything else through
                        pass

                    if not item.title == "DO NOT DISPLAY":
                    
#                        if not self.in_treestore(iter, item.title, item.id, "SONOSMUSICSERVER"):
                        self.container_append(iter, [item.title, item.id, data, "SONOSMUSICSERVER"])

                else:
#                    if not self.in_treestore(iter, item.title, item.id, "MUSICSERVER"):  THIS IS WAY TOO SLOW
                    self.container_append(iter, [item.title, item.id, data, "MUSICSERVER"])

            else:

                # TODO: save items in temp list, then post process them to:
                # 1) Suppress duplicates, choosing which to display from a list based on type (e.g. FLAC vs MP3)
                # 2) Display extra info for duplicates (e.g. location)
                # 3) Other things?
                # Make this/these options selectable via a config option

                xml = item.to_string()
                xml = xml.replace('xmlns:ns0="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/"','')
                xml = xml.replace('ns0:','')

                # check if current server is a zone player
                current_server = self.control_point.get_current_server()
                if current_server.udn in self.known_zone_players:
                    self.liststore_append([item.title, item.resources[0].value, xml, "SONOSMUSICSERVER"])
                else:
                    self.liststore_append([item.title, item.resources[0].value, xml, "MUSICSERVER"])


        # only append on first call for a server
        if iter == None:

            # if current server is a zone player, append some more container items
            current_server = self.control_point.get_current_server()
            if current_server.udn in self.known_zone_players:
                
                service_result = self.control_point.get_music_services()
                log.debug("get_music_services result: %s", service_result['AvailableServiceDescriptorList'])
                items = service_result['AvailableServiceDescriptorList']
                
                xml = [None, None]    # nothing to play at this level

                for item in items:
                
#                    if not self.in_treestore(None, item.Name, item.Id, item.Name + "_ROOT"):
                    self.container_append(None, [item.Name, item.Id, xml, item.Name + "_ROOT"])

                    self.music_services[item.Name] = item

                    '''                    
	                <AvailableServiceDescriptorList>
		                <Service Capabilities="31" Id="0" MaxMessagingChars="0" Name="Napster" SecureUri="https://api.napster.com/device/soap/v1" Uri="http://api.napster.com/device/soap/v1" Version="1.0">
			                <Policy Auth="UserId" PollInterval="30"/>
			                <Presentation>
				                <Strings Uri="http://update-services.sonos.com/services/napster/string.xml" Version="1"/>
				                <Logos Large="http://www.napster.com/services/Sonos/LargeLogo.png" Small="http://www.napster.com/services/Sonos/SmallLogo.png"/>
			                </Presentation>
		                </Service>
		                <Service Capabilities="0" Id="254" MaxMessagingChars="0" Name="RadioTime" SecureUri="http://legato.radiotime.com/Radio.asmx" Uri="http://legato.radiotime.com/Radio.asmx" Version="1.1">
			                <Policy Auth="Anonymous" PollInterval="0"/>
			                <Presentation/>
		                </Service>
		                <Service Capabilities="19" Id="2" MaxMessagingChars="0" Name="Deezer" SecureUri="https://moapi.sonos.com/Deezer/SonosAPI.php" Uri="http://moapi.sonos.com/Deezer/SonosAPI.php" Version="1.1">
			                <Policy Auth="UserId" PollInterval="60"/>
			                <Presentation/>
		                </Service>
	                </AvailableServiceDescriptorList>
                    ''' 
                        
                '''
                <AvailableServiceTypeList>7,11,519</AvailableServiceTypeList>
                <AvailableServiceListVersion>RINCON_000E5823A88A01400:236</AvailableServiceListVersion>
                '''
                self.AvailableServiceTypeList = service_result['AvailableServiceTypeList']
                self.AvailableServiceListVersion = service_result['AvailableServiceListVersion']

            # if current server is a zone player, append any third party media server items
            current_server = self.control_point.get_current_server()
            if current_server.udn in self.known_zone_players:

                zt_sid = self.control_point.get_zt_service(current_server).event_sid
                mediaservers = self.thirdpartymediaservers[zt_sid]
                xml = [None, None]    # nothing to play at this level

                for num, mediaserver in mediaservers.items():

                    if mediaserver['Name'].find('Windows Media') != -1:
                        type = 'MSMEDIASERVER_ROOT'
                    else:
                        type = 'THIRDPARTYMEDIASERVER_ROOT'
                        
#                    if not self.in_treestore(None, mediaserver['Name'], mediaserver['UDN'], type):
                    self.container_append(None, [mediaserver['Name'], mediaserver['UDN'], xml, type])

            # testing            
#            if not self.in_treestore(None, 'TEST', 'TEST', 'TEST_ROOT'):
            self.container_append(iter, ['TEST', 'TEST', '', 'TEST_ROOT'])
           

    def browse_thirdparty_media_server(self, name, id, iter=None, root=None):
        log.debug("#### browse_thirdparty_media_server: %s", id)
        
        tpmscount = 2000
        
        if root == None:
            id_param = id
        else:
            id_param = '0'

        self.set_messagebar("Browsing...")

        browse_result = self.control_point.browsetpms(name, id_param, 'BrowseDirectChildren', '*', 0, tpmscount, 'dc:title')
#        browse_result = self.control_point.browsetpms(name, id_param, 'BrowseDirectChildren', '*', 0, tpmscount, '+dc:title')
        
        if 'faultcode' in browse_result:
            messageBox(browse_result['detail'],'Browse Response Error')
            return
        elif not 'Result' in browse_result:
            messageBox('UNKNOWN RESPONSE FROM BROWSE REQUEST','Browse Response Error')
            return
        
        items = browse_result['Result']
        total = int(browse_result['TotalMatches'])
        returned = int(browse_result['NumberReturned'])
#        log.debug("browse_media_server: %s items, %s total, %s returned", items, total, returned)

        self.set_messagebar("Returned %d of %d." % (returned, total))

        if total > tpmscount:
            while returned < total:
#                b = self.control_point.browsetpms(name, id_param, 'BrowseDirectChildren', '*', returned, tpmscount, '')
                b = self.control_point.browsetpms(name, id_param, 'BrowseDirectChildren', '*', returned, tpmscount, '+dc:title')
                items = items + b['Result']
                returned += int(b['NumberReturned'])

                self.set_messagebar("Returned %d of %d." % (returned, total))
                
        for item in items:

            if isinstance(item, Container):


#                meta = self.control_point.browsetpms(name, item.id, 'BrowseMetadata', '*', 0, 20, 'dc:title')
#                print "MMMMMMMMMMMMMMMMMMMMMMMMMM"
#                print meta
#                print "name: " + str(name)
#                print "item.id: " + str(item.id)
#                print meta['Result'][0].to_string()
#                print "MMMMMMMMMMMMMMMMMMMMMMMMMM"

                data = self.convert_item_to_uridata(item)

#                if not self.in_treestore(iter, item.title, item.id, "THIRDPARTYMEDIASERVER"):
                self.container_append(iter, [item.title, item.id, data, "THIRDPARTYMEDIASERVER"])

            else:

                xml = item.to_string()
                xml = xml.replace('xmlns:ns0="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/"','')
                xml = xml.replace('ns0:','')

                self.liststore_append([item.title, item.resources[0].value, xml, "THIRDPARTYMEDIASERVER"])


    def search_ms_media_server(self, name, id, iter=None, root=None):

        log.debug("#### search_ms_media_server: %s", id)
        
        msmscount = 2000
        
        if root != None:

            # root items - manually create list
            for item in self.msms_root_items:
                if not self.in_treestore(iter, item[0], item[1], "MSMEDIASERVER"):
                    self.container_append(iter, [item[0], item[1], '', "MSMEDIASERVER"])
            return

        elif id == '101':
        
            # rating items - manually create list
            for item in self.msms_rating_items:
                if not self.in_treestore(iter, item[0], item[1], "MSMEDIASERVER"):
                    self.container_append(iter, [item[0], item[1], '', "MSMEDIASERVER"])
            return

        # not special processing, use SOAP action            
        id_param = id

        self.set_messagebar("Browsing...")

        action = 'SEARCH'
        if id in self.msms_search_lookup:
            searchcriteria = self.msms_search_lookup[id]
            searchcriteria += ' and @refID exists false'
        else:
            parentid = self.get_treestore_parent_id(iter)
            searchitem = self.msms_search_lookup_item[parentid]
            if searchitem == 'BROWSE':
                # we are at object level, so Browse instead
                action = 'BROWSE'
                sortcriteria = self.msms_search_browse_sortcriteria[parentid]
            else:
                searchcriteria = self.msms_search_lookup[parentid] + " and " + searchitem
                searchcriteria += ' and @refID exists false'

        if action == 'SEARCH':
            browse_result = self.control_point.searchtpms(name, id_param, searchcriteria, 'dc:title,res,res@duration,upnp:artist,upnp:artist@role,upnp:album,upnp:originalTrackNumber', 0, msmscount, '+dc:title')
        else:
            browse_result = self.control_point.browsetpms(name, id_param, 'BrowseDirectChildren', 'dc:title,res,res@duration,upnp:artist,upnp:artist@role,upnp:album,upnp:originalTrackNumber', 0, msmscount, sortcriteria)
        
        if 'faultcode' in browse_result:
            messageBox(browse_result['detail'],'Browse Response Error')
            return
        elif not 'Result' in browse_result:
            messageBox('UNKNOWN RESPONSE FROM BROWSE REQUEST','Browse Response Error')
            return
        
        items = browse_result['Result']
        total = int(browse_result['TotalMatches'])
        returned = int(browse_result['NumberReturned'])

        self.set_messagebar("Returned %d of %d." % (returned, total))

        if total > msmscount:
            while returned < total:
                if action == 'SEARCH':
                    b = self.control_point.searchtpms(name, id_param, searchcriteria, 'dc:title,res,res@duration,upnp:artist,upnp:artist@role,upnp:album,upnp:originalTrackNumber', 0, msmscount, '+dc:title')
                else:
                    b = self.control_point.browsetpms(name, id_param, 'BrowseDirectChildren', 'dc:title,res,res@duration,upnp:artist,upnp:artist@role,upnp:album,upnp:originalTrackNumber', 0, msmscount, sortcriteria)
                items = items + b['Result']
                returned += int(b['NumberReturned'])
                self.set_messagebar("Returned %d of %d." % (returned, total))
                
        for item in items:

            if isinstance(item, Container):

                data = self.convert_item_to_uridata(item)
                
#                if not self.in_treestore(iter, item.title, item.id, "MSMEDIASERVER"):
                self.container_append(iter, [item.title, item.id, data, "MSMEDIASERVER"])

            else:

                xml = item.to_string()
                xml = xml.replace('xmlns:ns0="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/"','')
                xml = xml.replace('ns0:','')
                
                self.liststore_append([item.title, item.resources[0].value, xml, "MSMEDIASERVER"])


    def convert_item_to_uridata(self, item):

        if item.resources != []:
            uri = item.resources[0].value
        else:
            uri = ''
#            uri = 'x-rincon-playlist:RINCON_000E5830D2F001400#' + item.id

        root = ElementTree.Element('item')
        root.attrib['id'] = item.id
        root.attrib['parentID'] = item.parent_id
        if item.restricted:
            root.attrib['restricted'] = 'true'
        else:
            root.attrib['restricted'] = 'false'

        ElementTree.SubElement(root, 'dc:title').text = item.title
        ElementTree.SubElement(root, 'upnp:class').text = item.upnp_class
        desc = ElementTree.SubElement(root, 'desc')
        desc.attrib['id'] = "cdudn"
        desc.attrib['nameSpace'] = "urn:schemas-rinconnetworks-com:metadata-1-0/"
        desc.text = 'RINCON_AssociatedZPUDN'
        
        xml = ElementTree.tostring(root)
        xml = xml.replace('xmlns:ns0="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/"','')
        xml = xml.replace('ns0:','')
    
        data = uri, xml

        return uri, xml


    def remove_non_sonos_elements(self, data):

        # Sonos has a problem with the length of the item string on NOTIFY - it seems
        # only to return 1024 chars max
        # Multiple res elements or extraneous (not used by Sonos) elements can blow the limit
        
        # Remove all but the correct audio res (if they exist)
        # TODO: Asset sends multiple audio res - for now use the first, but need to know which to select
        # TODO: keep the items we want (rather than deleting some known not-wants) as we don't know what else will be passed
        '''
        NAS
            <res duration="00:04:52" nrAudioChannels="2" protocolInfo="http-get:*:audio/x-ms-wma:DLNA.ORG_PN=WMABASE;DLNA.ORG_OP=01" sampleFrequency="44100">http://192.168.0.4:58080/mshare/1/10004:ca8:primary/%28I%20Got%20That%29%20Boom%20Boom.wma</res>
            <res protocolInfo="http-get:*:image/jpeg:DLNA.ORG_PN=JPEG_TN;DLNA.ORG_OP=01;DLNA.ORG_CI=1">http://192.168.0.4:58080/mshare/1/10004:ca8:albumart/%28I%20Got%20That%29%20Boom%20Boom.jpg</res>
            <res protocolInfo="http-get:*:image/jpeg:DLNA.ORG_PN=JPEG_TN;DLNA.ORG_OP=01;DLNA.ORG_CI=1">http://192.168.0.4:58080/mshare/1/10004:ca8:thumbnail/%28I%20Got%20That%29%20Boom%20Boom.jpg</res>
        Asset
            <res bitrate="128000" bitsPerSample="16" duration="00:03:18.000" nrAudioChannels="2" protocolInfo="http-get:*:audio/mpeg:DLNA.ORG_PN=MP3;DLNA.ORG_OP=01" sampleFrequency="44100" size="3176490">http://192.168.0.10:50041/content/c2/b16/f44100/6819.mp3</res>
            <res bitrate="128000" bitsPerSample="16" duration="00:03:18.000" nrAudioChannels="2" protocolInfo="http-get:*:audio/wav:DLNA.ORG_PN=WAV;DLNA.ORG_OP=01" sampleFrequency="44100" size="3176490">http://192.168.0.10:50041/content/c2/b16/f44100/6819.wav</res>
            <res bitrate="128000" bitsPerSample="16" duration="00:03:18.000" nrAudioChannels="2" protocolInfo="http-get:*:audio/L16;rate=44100;channels=2:DLNA.ORG_PN=LPCM;DLNA.ORG_OP=01" sampleFrequency="44100" size="3176490">http://192.168.0.10:50041/content/c2/b16/f44100/6819.l16</res>
            <res bitrate="128000" bitsPerSample="16" duration="00:03:18.000" nrAudioChannels="2" protocolInfo="http-get:*:audio/mpeg:DLNA.ORG_PN=MP3;DLNA.ORG_OP=01" sampleFrequency="44100" size="3176490">http://192.168.0.10:50041/content/c2/b16/f44100/6819.mp3</res>
        '''

        # remove all but first res - assumes res are consecutive
        firstres = re.search('<res[^<]*</res>', data)
        if firstres != None:
            data = re.sub('<res.*</res>' , firstres.group(), data)
        
        # for now remove extra artist info, genre and date
        firstart = re.search('<upnp:artist[^<]*</upnp:artist>', data)
        if firstart != None:
            data = re.sub('<upnp:artist.*</upnp:artist>' , firstart.group(), data)

        data = re.sub('<upnp:genre.*</upnp:genre>' , '', data)

        data = re.sub('<dc:date.*</dc:date>' , '', data)

        return data


    def update_info(self):

        if self.info_window == None:
            return

        gtk.gdk.threads_enter()
        bv = self.glade_info_xml.get_widget("info")
        bv.get_buffer().set_text(self.info)
        gtk.gdk.threads_leave()


    def update_position(self):

        if self.playing_window == None:
            return

        if self.play_state != 'PLAYING':
            return

#        print "Update pos. win=" + str(self.playing_window) + " state=" + str(self.play_state)

        '''
        {'AbsTime': 'NOT_IMPLEMENTED'
         'Track': '1'
         'TrackDuration': '0:02:50'
         'TrackURI': 'x-file-cifs://NAS/Music/Clannad/Past%20Present/11%20Robin%20(The%20Hooded%20Man).flac'
         'AbsCount': '2147483647'
         'TrackMetaData': '<DIDL-Lite xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/" xmlns:r="urn:schemas-rinconnetworks-com:metadata-1-0/" xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/"><item id="-1" parentID="-1" restricted="true"><res protocolInfo="x-file-cifs:*:audio/flac:*" duration="0:02:50">x-file-cifs://NAS/Music/Clannad/Past%20Present/11%20Robin%20(The%20Hooded%20Man).flac</res><r:streamContent></r:streamContent><dc:title>Robin (The Hooded Man)</dc:title><upnp:class>object.item.audioItem.musicTrack</upnp:class><dc:creator>Clannad</dc:creator><upnp:album>Past Present</upnp:album><upnp:originalTrackNumber>11</upnp:originalTrackNumber><r:albumArtist>Clannad</r:albumArtist></item></DIDL-Lite>'
         'RelCount': '2147483647'
         'RelTime': '0:01:29'}
        '''
        pos = self.control_point.get_position_info()
        reltime = ''
        if 'RelTime' in pos:
            if pos['RelTime'] != 'NOT_IMPLEMENTED':
                reltime = pos['RelTime']
        trackduration = ''
        if 'TrackDuration' in pos:
            if pos['TrackDuration'] != 'NOT_IMPLEMENTED':
                trackduration = pos['TrackDuration']

        td = re.sub('0', '', trackduration)
        td = re.sub(':', '', td)
        if td == '':
            trackduration = ''
                
        if reltime != '':
            self.now_playing_pos = reltime
        if reltime != '' and trackduration != '':
            self.now_playing_pos += " / "
        if trackduration != '':
            self.now_playing_pos += trackduration

        gtk.gdk.threads_enter()
        bv = self.glade_playing_xml.get_widget("position")
        bv.set_text(self.now_playing_pos)
        gtk.gdk.threads_leave()

        
    def check_play(self):
        # check if already playing:
        #     if playing, pause
        #     if paused, unpause (play)
        # else
        #     unpause (i.e. play without setting AVTransport


#            self.play_state = self.control_point.GetTransportInfo()



#            state = self.control_point.get_transport_state()
#            log.debug("play state: %s", state)
#transportStates = [ 'STOPPED', 'PLAYING', 'TRANSITIONING', 'PAUSED_PLAYBACK', 'PAUSED_RECORDING', 'RECORDING', 'NO_MEDIA_PRESENT' ]
        if self.play_state == 'PLAYING' or self.play_state == 'TRANSITIONING':
            self.pause()
        elif self.play_state == 'PAUSED_PLAYBACK':
            self.unpause()
        else:
            # we want to play without setting AVTransport, which is what unpause does
            self.unpause()

    def pause(self):
        try:
            self.control_point.pause()
            self.set_play_label_only('Resume')
            self.play_state = 'PAUSED_PLAYBACK'
        except Exception, e:
            log.info('Choose a Renderer to pause Music. Specific problem: %s' % \
                     str(e))

    def unpause(self):
        try:
            self.control_point.unpause()
            self.set_play_label_only('Pause')
            self.play_state = 'PLAYING'
        except Exception, e:
            log.info('Choose a Renderer to unpause Music. Specific problem: %s' % \
                     str(e))


    def play_now_noqueue(self):

        self.fix_metadata()
        uri = self.current_media_id
        xml = self.current_media_xml
#        print "@@@@ uri: " + str(uri)
#        print "@@@@ xml: " + str(xml)
        self.control_point.set_avtransport_uri(uri, xml)
        self.play()

    def play_now_queue(self):

        # TODO: don't offer this and associated menu options for renderers that don't support them
        # TODO: track updates to queue UpdateID so we know if it has changed since we started and need to re-fetch
        
        desiredfirsttrack = 0
        enqueuenext = 1
        uri = self.current_media_id
        xml = self.current_media_xml
        unit = 'TRACK_NR'
        target = self.current_queue_length

        print "@@@@@@ play_now_queue"
        print "@@@@@@ pnq uri: " + str(uri)
        print "@@@@@@ pnq xml: " + str(xml)
        
        self.fix_metadata()
        self.control_point.add_uri_to_queue(uri, xml, desiredfirsttrack, enqueuenext)
        self.control_point.set_avtransport_uri(uri, xml)
        self.control_point.seek(unit, target)
        self.play()

    
    def play_next_queue(self):

        desiredfirsttrack = self.current_queue_length + 1
        enqueuenext = 1
        uri = self.current_media_id
        xml = self.current_media_xml
        
        self.fix_metadata()
        self.control_point.add_uri_to_queue(uri, xml, desiredfirsttrack, enqueuenext)

    def play_end_queue(self):

        desiredfirsttrack = 0
        enqueuenext = 0
        uri = self.current_media_id
        xml = self.current_media_xml
        
        self.fix_metadata()
        self.control_point.add_uri_to_queue(uri, xml, desiredfirsttrack, enqueuenext)

    def play_sample_noqueue(self):

        unit = 'REL_TIME'
        target = "0:00:20"

        self.fix_metadata()
        uri = self.current_media_id
        xml = self.current_media_xml
        self.control_point.set_avtransport_uri(uri, xml)
        self.control_point.seek(unit, target)
        self.play()

        # TODO: some tracks don't play for several seconds - need to wait for them to start playing before setting the timeout
        wait = 5
        renderer = self.control_point.get_current_renderer()
        run_async_function(self.sample_stop, (renderer, uri, target, wait), wait)


    def sample_stop(self, renderer, uri, start, wait):
        # stop playing on renderer that sample was started on, if track is same and wait has expired
        if renderer == self.control_point.get_current_renderer():
            self.get_position_info()
            if uri == self.current_track_URI:
                startsecs = self.makeseconds(start)
                endsecs = startsecs + wait
                currsecs = self.makeseconds(self.current_track_relative_time_position )
                delta = endsecs - currsecs
                # allow +- 1 sec 
                if delta <= 1 and delta >= -1:
                    self.stop()


    def update_playlist_name(self, id, currenttagvalue, newtagvalue):

        currenttagvalue = '<dc:title>' + currenttagvalue + '</dc:title>'
        newtagvalue = '<dc:title>' + newtagvalue + '</dc:title>'
        res = self.control_point.update_object(id, currenttagvalue, newtagvalue)
        if res == {}:
            return True
        else:
            return False


    def makeseconds(self, time):
        h, m, s = time.split(':')
        return (int(h)*60*60 + int(m)*60 +int(s))


    def fix_metadata(self):

        if self.current_media_id != None and self.current_media_xml != '':

            # if current renderer is Sonos, need to remove extraneous elements from the XML
            # otherwise we could blow the item length limit when returned on NOTIFY
            # note that this is not foolproof as we still manage to blow some elements
            
            # check if current renderer is a zoneplayer
            current_renderer = self.control_point.get_current_renderer()
            if current_renderer.udn in self.known_zone_players:

                self.current_media_xml = self.remove_non_sonos_elements(self.current_media_xml)

            else:

                print "@@@ current_media_id: " + str(self.current_media_id)

                # if current renderer is not a zoneplayer, need to replace Sonos protocol type with standard
                if self.current_media_id.startswith('x-file-cifs:'):
                    self.current_media_id = re.sub('x-file-cifs:', 'smb:', self.current_media_id)
                elif self.current_media_id.startswith('x-sonosapi-stream'):
                    # TODO: work out which URL to use
                    self.current_media_id = self.music_item_station_url.split('\n')[0]
                    print "@@@ new current_media_id: " + str(self.current_media_id)

            '''
            # if current renderer is not on the local machine and the data refers to localhost, replace with external IP
            # TODO: at the moment we don't check whether renderer is local...
            
            ip = self._get_ip()
            print "@@@@@@@@@@@@@@@@@"
            print "@@@@@@@@@@@@@@@@@"
            print "@@@@@@@@@@@@@@@@@"
            print "@@@@ before: " + str(self.current_media_id)
            self.current_media_id = re.sub('127.0.0.1', ip, self.current_media_id)
            print "@@@@ before: " + str(self.current_media_id)
            print "@@@@@@@@@@@@@@@@@"
            print "@@@@@@@@@@@@@@@@@"
            print "@@@@@@@@@@@@@@@@@"
            '''

    def _get_ip(self):
        ifaces = get_active_ifaces()
        if ifaces:
            host = get_ip_address(ifaces[0])
        else:
            host = 'localhost'
        return host



    def play(self):
        try:
                
            # TODO: check the result of play
            self.control_point.play()

            # brisa renderer is not eventing lastchange - until we fix that send a dummy event
            current_renderer = self.control_point.get_current_renderer()
            if current_renderer.udn not in self.known_zone_players:

                # send the equivalent of a NOTIFY - call device_event with a dummy lastchange

                xml = self.current_media_xml
                # HACK: need to send either DIDL-Lite or item
                if xml.startswith('<DIDL-Lite'):
                    metadata = xml
                else:
                    metadata = '<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:r="urn:schemas-rinconnetworks-com:metadata-1-0/" xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/">' + xml + '</DIDL-Lite>'

                    # metadata needs converting to reference form for embedding
                    
                    metadata = metadata.replace("&","&amp;")
                    metadata = metadata.replace("\"","&quot;")
                    metadata = metadata.replace("'","&apos;")
                    metadata = metadata.replace("<","&lt;")
                    metadata = metadata.replace(">","&gt;")
                    
                change = {}
                changexml = '<Event xmlns="urn:schemas-upnp-org:metadata-1-0/AVT/" xmlns:r="urn:schemas-rinconnetworks-com:metadata-1-0/"><InstanceID val="0">'
                changexml += '<TransportState val="PLAYING"/><CurrentPlayMode val="NORMAL"/>'
                changexml += '<CurrentTrackMetaData val="' + metadata + '"/>'
                changexml += '</InstanceID></Event>'
                change['LastChange'] = changexml

                #sid = self.control_point.get_at_service().event_sid
                sid = current_renderer.udn  # event_sid is not set as eventing is not working
                
                run_async_function(self.on_device_event_seq, (sid, 1, change), 0.001)

        except Exception, e:
            log.info('Choose a Renderer to play Music. Specific problem: %s' % \
                     str(e))



# play process:
#
#   if media item selected
#       set AVTransport
#       play
#   if play clicked
#       if there is a current track from get_position_info
#           unpause
#       else
#           do nothing


    def stop(self):
#        print "@@@ play_state: " + str(self.play_state)
        if self.play_state != '' and self.play_state != 'STOPPED':
            try:
                self.control_point.stop()
                self.set_play_label_only('Play')
                self.play_state = 'STOPPED'
            except Exception, e:
                log.info('Choose a Renderer to stop Music. Specific problem: %s' % \
                         str(e))

    def toggle_mute(self):
        if self.muted == 1:
            self.muted = 0
            self.set_mute_label_only('Mute')
        else:
            self.muted = 1
            self.set_mute_label_only('UnMute')

    def set_mute_label_only(self, label):
        if self.playing_window == None:
            return
        bv = self.glade_playing_xml.get_widget("button_mute")
        bv.set_label(label)


#self.Button = gtk.Button('Name')
# image,label =  self.Button.get_children()[0].get_children()[0].get_children()
# label.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse('#FFFFFF'))



    def set_mute(self, mute_value):
        if isinstance(mute_value, str):
            mute_value = int(mute_value)
        self.muted = mute_value
        if mute_value == 0:
            mute_after = 'Mute'
        else:
            mute_after = 'UnMute'
        if self.playing_window == None:
            return
        bv = self.glade_playing_xml.get_widget("button_mute")
        bv.set_label(mute_after)

    def set_play_label_only(self, label):
        if self.playing_window == None:
            return
        bv = self.glade_playing_xml.get_widget("button_play")
        bv.set_label(label)

    def set_play(self, state):
#        print ">>>>>>>>>>>>> TRANSPORT STATE " + state
        self.play_state = state
#transportStates = [ 'STOPPED', 'PLAYING', 'TRANSITIONING', 'PAUSED_PLAYBACK', 'PAUSED_RECORDING', 'RECORDING', 'NO_MEDIA_PRESENT' ]
        if state == 'PLAYING' or state == 'TRANSITIONING':
            state_label = 'Pause'
        elif state == 'PAUSED_PLAYBACK':
            state_label = 'Resume'
        elif state == 'STOPPED':
            state_label = 'Play'
        if self.playing_window == None:
            return
        bv = self.glade_playing_xml.get_widget("button_play")
        bv.set_label(state_label)

    def set_messagebar(self, text):
        bv = self.glade_xml.get_widget("messagebar")
        bv.set_label(text)
        while gtk.events_pending():
            gtk.main_iteration_do()


    def mute(self):
        try:
            self.control_point.mute(self.muted)
        except Exception, e:
            log.info('Choose a Renderer to mute Music. Specific problem: %s' % \
                     str(e))

    def next(self):
        self.control_point.next()

    def previous(self):
        self.control_point.previous()

    def volume(self, volume):
        try:
            self.control_point.set_volume(volume)
        except Exception, e:
            log.info('Choose a Renderer to change volume. Specific problem: %s' % \
                     str(e))

#    def _main_quit(self, window):
#        self.control_point.stop_search()
#        ThreadManager().stop_all()
#        gtk.gdk.threads_leave()
#        gtk.main_quit()
#        quit()
    def _main_quit(self, window=None):
        if window:
            window.destroy()
        self.cancel_subscriptions()
        reactor.main_quit()

    def _playing_quit(self, window):
        print "_playing_quit"
        self.playing_window.destroy()
        self.playing_window = None

    def _playing_destroy(self, window):
        print "_playing_destroy"
        self.playing_window.destroy()
        self.playing_window = None

    def _info_quit(self, window):
        print "_info_quit"
        self.info_window.destroy()
        self.info_window = None

    def _info_destroy(self, window):
        print "_info_destroy"
        self.info_window.destroy()
        self.info_window = None


    def _item_media_list_button_press(self, treeview, event):
    
        current_renderer = self.control_point.get_current_renderer()
        if current_renderer == None:
            messageBox('Please select a renderer', 'Selection Error')
        else:
#            print "_item_media_list_button_press"
            if event.button == 1 or event.button == 3:
                x = int(event.x)
                y = int(event.y)
                pthinfo = treeview.get_path_at_pos(x, y)
                if pthinfo is not None:
                    path, col, cellx, celly = pthinfo
                    treeview.grab_focus()
                    treeview.set_cursor( path, col, 0)
                    if event.button == 1 and event.type == gtk.gdk._2BUTTON_PRESS:
                        self._on_media_item_selected(treeview, path, -1, '')
                    elif event.button == 1 and event.type == gtk.gdk.BUTTON_PRESS:
                        self._on_media_item_listview_changed(treeview)
                    elif event.button == 3 and event.type == gtk.gdk.BUTTON_PRESS:
                            options = ["Play now don't queue", "Play now add to queue", "Add to queue next", "Add to end of queue", "Play sample"]
                            rightmenu = gtk.Menu()
                            for option in options:
                                menu_item = gtk.MenuItem(option)
                                menu_item.connect("activate", self._on_item_media_list_optionmenu_activate, option, treeview) 
                                menu_item.show()
                                rightmenu.append(menu_item)
                            rightmenu.popup(None, None, None, event.button, event.time)
                return True

    def _container_button_press(self, treeview, event):
#        print "_container_button_press"
        if event.button == 1 or event.button == 3:
            x = int(event.x)
            y = int(event.y)
            pthinfo = treeview.get_path_at_pos(x, y)
            if pthinfo is not None:
                path, col, cellx, celly = pthinfo
                treeview.grab_focus()
                treeview.set_cursor( path, col, 0)
                if event.button == 1 and event.type == gtk.gdk._2BUTTON_PRESS:
                    self._on_container_treeview_activated(treeview, path, -1, '')
                elif event.button == 1 and event.type == gtk.gdk.BUTTON_PRESS:
                    self._on_container_treeview_click(treeview, path)
                elif event.button == 3 and event.type == gtk.gdk.BUTTON_PRESS:

                    (model, iter) = treeview.get_selection().get_selected()
                    
                    title, id, (self.current_media_id, self.current_media_xml), self.current_media_type = model.get(iter, 0, 1, 2, 3)
# TODO: fix other browse XMLs (remember tuple!)

                    print "@@@@ title: " + str(title)
                    print "@@@@ id: " + str(id)
                    print "@@@@ cmi: " + str(self.current_media_id)
                    print "@@@@ cmx: " + str(self.current_media_xml)
                    print "@@@@ cmt: " + str(self.current_media_type)

                    # all types other than stated will have no popup
                    options = None

                    if id == 'SQ:':
                        # no menu at this level for playlists
                        pass
                    elif id.startswith('SQ:'):
                        options = ["Play now don't queue", "Play now add to queue", "Add to queue next", "Add to end of queue", "Rename playlist"]
                    elif id == "Q:0":
                        options = ["Play now"]
                    elif self.current_media_type == "MUSICSERVER" or self.current_media_type == "SONOSMUSICSERVER" or \
                         self.current_media_type == "THIRDPARTYMEDIASERVER" or self.current_media_type == "MSMEDIASERVER":
                        options = ["Play now don't queue", "Play now add to queue", "Add to queue next", "Add to end of queue"]

                    '''
                    if self.current_media_type == "RadioTime_ROOT":
                    elif self.current_media_type == "Napster_ROOT":
                    elif self.current_media_type == "Deezer_ROOT":
                    elif self.current_media_type == "RADIOTIME":
                    elif self.current_media_type == "THIRDPARTYMEDIASERVER_ROOT":
                    elif self.current_media_type == "MSMEDIASERVER_ROOT":
                    elif self.current_media_type == "TEST_ROOT":
                    '''
                    
                    if options != None:
                        rightmenu = gtk.Menu()
                        for option in options:
                            menu_item = gtk.MenuItem(option)
                            menu_item.connect("activate", self._on_container_optionmenu_activate, option, treeview) 
                            menu_item.show()
                            rightmenu.append(menu_item)
                        rightmenu.popup(None, None, None, event.button, event.time)
            return True

    def _on_item_media_list_optionmenu_activate(self, menuitem, option, treeview):
        print "<<<<< item_media_list: " + option + " >>>>>"
        
        (model, iter) = treeview.get_selection().get_selected()
        self.current_media_id = model.get_value(iter, 1)
        self.current_media_xml = model.get_value(iter, 2)
        self.current_media_type = model.get_value(iter, 3)

        if option == "Play now don't queue":
            self.play_now_noqueue()
        elif option == "Play now add to queue":
            self.play_now_queue()
        elif option == "Add to queue next":
            self.play_next_queue()
        elif option == "Add to end of queue":
            self.play_end_queue()
        elif option == "Play sample":
            self.play_sample_noqueue()

    def _on_container_optionmenu_activate(self, menuitem, option, treeview):
        print "<<<<< container: " + option + " >>>>>"

        if option == "Play now":
            self.play_now_noqueue()
        elif option == "Play now don't queue":
            self.play_now_noqueue()
        elif option == "Play now add to queue":
            self.play_now_queue()
        elif option == "Add to queue next":
            self.play_next_queue()
        elif option == "Add to end of queue":
            self.play_end_queue()
        elif option == "Play sample":
            self.play_sample_noqueue()
        elif option == "Rename playlist":
            (model, iter) = treeview.get_selection().get_selected()
            # TODO: save title and id from earlier call
            title = model.get_value(iter, 0)
            id = model.get_value(iter, 1)
            newtitle = editBox('New playlist name:','Rename playlist', title).newtext
            ret = self.update_playlist_name(id, title, newtitle)
            if ret == True:
                self.container_treestore.set_value(iter, 0, newtitle)
            else:
                messageBox('Unable to rename playlist','Error')

            # TODO: check result

#note - if queue is changed need to retrieve it and update the list if it's in there (either that or invalidate it so it is re-fetched)
#note - need to add same functionality to renderer window
#note - also need to be selective when we can queue/play something (e.g. can we from the root?)






    def _changed_server_devices(self, combobox):
        # at this point we are within a GTK thread so don't use enter/leave
        model = combobox.get_model()
        index = combobox.get_active()
        if type(index) == int and index >= 0:
            self.container_treestore.clear()
            self.music_services = {}
#            self.services = {}
            self.current_queue_length = -1
            self.current_queue_updateid = -1
            try:
                server = self.known_media_servers[model[index][1]]
                self.control_point.set_current_server(server)
                if server.udn in self.known_zone_players:
                    self.control_point.set_current_zoneplayer(server)
                self.item_media_list_liststore.clear()

                # for Sonos, need to know how many items are in the queue
                if server.udn in self.known_zone_players:
                    self.get_queue_length("Q:0")
                   
                # get the root entries                                    
                self.browse_media_server(0)

#                log.debug("Media server controlled: %s UDN: %s", model[index][0], model[index][1])
            except KeyError, k:
                pass

    def _changed_renderer_devices(self, combobox):
        # at this point we are within a GTK thread so don't use enter/leave
        model = combobox.get_model()
        index = combobox.get_active()
        if type(index) == int and index >= 0:
            try:
                # unsubscribe from events from previous renderer
                current_renderer = self.control_point.get_current_renderer()
                if current_renderer != None:
#                    self.renew_loop.stop()
                    self.unsubscribe_from_device(self.control_point.get_at_service(current_renderer))
                    self.unsubscribe_from_device(self.control_point.get_rc_service(current_renderer))
                    self.current_renderer_events_avt = {}
                    self.current_renderer_events_rc = {}
                    self.now_playing = ''
                    self.now_extras = ''
                    self.now_playing_pos = ''
                    self.clear_position_info()
                    self.last_event_seq = {}
                self.show_playing_window()
                # set new renderer
                self.control_point.set_current_renderer(self.known_media_renderers[model[index][1]])
                current_renderer = self.control_point.get_current_renderer()
                # subscribe to events from this device
                
                self.subscribe_to_device(self.control_point.get_at_service(current_renderer))
                self.subscribe_to_device(self.control_point.get_rc_service(current_renderer))

#                print "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
#                print "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
#                print "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
#                self.subscribe_for_variable(current_renderer, self.control_point.get_at_service(), "TransportState")
#                self.subscribe_for_variable(current_renderer, self.control_point.get_rc_service(), "Volume")
#                print "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
#                print "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
#                print "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"

#                # set up for subscription renewals
#                # TODO: parameterise TIMEOUT
#                refresh_time = 0.97 * 1800
#                self.renew_loop = LoopingCall(self._renew_subscriptions)
#                self.renew_loop.start(refresh_time, now=False)
#                log.debug("Media renderer controlled: %s", model[index][0])
                self.get_position_info()
            except:
                pass


#    def _renew_subscriptions(self):
#        """ Renew subscriptions
#        """
#        self.renew_device_subscription(self.control_point.current_renderer, self.control_point.avt_s)
#        self.renew_device_subscription(self.control_point.current_renderer, self.control_point.rc_s)


    def on_new_device(self, device_object):
        log.debug('got new device: %s' % str(device_object))
#        log.debug('new device type: %s' % str(device_object.device_type))

#        log.debug('fn: %s' % str(device_object.friendly_name))
#        log.debug('m : %s' % str(device_object.manufacturer))
#        log.debug('mu: %s' % str(device_object.manufacturer_url))
#        log.debug('md: %s' % str(device_object.model_description))
#        log.debug('mn: %s' % str(device_object.model_name))
#        log.debug('mn: %s' % str(device_object.model_number))
#        log.debug('mu: %s' % str(device_object.model_url))
#        log.debug('sn: %s' % str(device_object.serial_number))
#        log.debug('ud: %s' % str(device_object.udn))
#        log.debug('up: %s' % str(device_object.upc))
#        log.debug('pu: %s' % str(device_object.presentation_url))

#        log.debug('new device udn: %s' % str(device_object.udn))
#        log.debug('new device services: %s' % str(device_object.services))

# TODO: need to check whether we need to cater for multiple child levels
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
# it appears that 0.10 brings all services back via the root device - so the zoneplayer has avt, rc etc
# TODO: DO WE NEED TO CHECK FOR CHILD DEVICES ANY MORE?
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

        device_list = []
        if device_object.devices:
#            log.debug('HAS child devices')
            root_device = device_object
            root_device.devices = []
            device_list.append(root_device)
            device_list.extend(device_object.devices)
        else:
#            log.debug('NO child devices')
            device_list.append(device_object)

        for device_item in device_list:

#            log.debug('new device: %s' % str(device_item))
            log.debug('new device type: %s' % str(device_item.device_type))
            log.debug('new device udn: %s' % str(device_item.udn))                                    
            log.debug('new device services: %s' % str(device_item.services))
            
# new device services: {
#'urn:microsoft.com:service:X_MS_MediaReceiverRegistrar:1': <brisa.upnp.control_point.service.Service object at 0x7fb9c8058910>, 
#'urn:schemas-upnp-org:service:ContentDirectory:1': <brisa.upnp.control_point.service.Service object at 0x7fb9f005bf10>, 
#'urn:schemas-upnp-org:service:ConnectionManager:1': <brisa.upnp.control_point.service.Service object at 0x7fb9dc076090>}
            
            # assumes root device is processed first so that zone name is known
            t = device_item.device_type
            if 'ZonePlayer' in t:
                self.on_new_zone_player(device_item)
            elif 'MediaServer' in t:
                self.on_new_media_server(device_item)
            elif 'MediaRenderer' in t:
                self.on_new_media_renderer(device_item)

    def on_new_zone_player(self, device_object):
        self.known_zone_players[device_object.udn] = device_object
        
#        self.control_point.set_current_zoneplayer(device_object)
        self.zoneattributes[device_object.udn] = self.get_zone_details(device_object)
        log.debug('new zone player - %s' % self.zoneattributes[device_object.udn]['CurrentZoneName'])

        # subscribe to events from this device
        self.subscribe_to_device(self.control_point.get_zt_service(device_object))

#        # HACK: assuming udn's of children are as below
#        self.known_zone_names[device_object.udn + '_MS'] = self.zoneattributes['CurrentZoneName']
#        self.known_zone_names[device_object.udn + '_MR'] = self.zoneattributes['CurrentZoneName']

        self.known_zone_names[device_object.udn] = self.zoneattributes[device_object.udn]['CurrentZoneName']

#        log.debug('<###### KNOWN_ZONE_PLAYERS ######>')
#        log.debug('known_zone_players: %s' % self.known_zone_players)
#        log.debug('<###### KNOWN_ZONE_PLAYERS ######>')
        # now register zoneplayer as server and renderer
        # TODO: check whether they have these capabilities first

        self.on_new_media_server(device_object)
        self.on_new_media_renderer(device_object)

    def on_new_media_server(self, device_object):
#        log.debug('new media server')
        self.known_media_servers[device_object.udn] = device_object

        # subscribe to events from this device
        self.subscribe_to_device(self.control_point.get_cd_service(device_object))
        
        if 'urn:microsoft.com:service:X_MS_MediaReceiverRegistrar:1' in device_object.services:
            # MS device, probably MS Media Player

            # subscribe to events from MediaReceiverRegistrar
            self.subscribe_to_device(self.control_point.get_mrr_service(device_object))

            # register with service
#            self.control_point.register_with_registrar(device_object)
        
#        log.debug('<###### KNOWN_MEDIA_SERVERS ######>')
#        log.debug('known_media_servers: %s' % self.known_media_servers)
#        log.debug('<###### KNOWN_MEDIA_SERVERS ######>')
        self.refresh()

    def on_new_media_renderer(self, device_object):
#        log.debug('new media renderer')
        self.known_media_renderers[device_object.udn] = device_object
#        log.debug('<###### KNOWN_MEDIA_RENDERERS ######>')
#        log.debug('known_media_renderers: %s' % self.known_media_renderers)
#        log.debug('<###### KNOWN_MEDIA_RENDERERS ######>')
        self.refresh()

    def on_del_device(self, udn):
#        log.debug('deleted media server')
        # TODO: unsubscribe from events from deleted device
        if udn in self.known_zone_players:
            del self.known_zone_players[udn]
            del self.known_media_servers[udn]
            del self.known_media_renderers[udn]
        elif udn in self.known_media_servers:
            del self.known_media_servers[udn]
        elif udn in self.known_media_renderers:
            del self.known_media_renderers[udn]
        self.refresh()


    def display_album_art(self, pixbuf, name):

#        print "display_album_art"
#        print "pixbuf: " + str(pixbuf)
#        print "name: " + str(name)

        # window can have been destroyed whilst waiting for album art...
        # TODO: don't destroy window when updates in progress, or try/catch
        if self.playing_window != None:
        
            eb = self.glade_playing_xml.get_widget("imagebutton")
            if is_hildon:
                pass
                # TODO: work out how to remove previous label
                #eb.set_label(' ')
            else:
                eb.set_label(name)
            if pixbuf == None:
                image = gtk.Image()
                image.show()
                eb.set_image(image)
            else:
                pixmap, mask = pixbuf.render_pixmap_and_mask()
                del pixbuf
                image = gtk.Image()
                image.set_from_pixmap(pixmap, mask)
                image.show()
                eb.set_image(image)
                del pixmap


    def display_music_location(self):

        if self.current_media_type == 'RADIOTIME':
            id = self.current_media_id
            if 'x-sonosapi-stream' in id:
                id = re.search('[^:]*:([^?]*)\?.*', id)
                if id != None:
                    id = id.group(1)
            self.music_item_station_uri = self.radiotime_getmediaURI(id)
            self.music_item_station_url = self.radiotime_getmediaURL(self.music_item_station_uri)
#            self.music_item_station_url = self.radiotime_getmediaURL(self.music_item_station_uri).split('\n')[0]
            self.info = "URI:\n" + str(self.music_item_station_uri) + '\n' + "URL:\n" + str(self.music_item_station_url)
            self.info += "\n\n" + self.current_media_xml
            self.update_info()
        else:
        
            self.info = ''
            for r in re.finditer('<res[^<]*</res>', self.current_media_xml):
                self.info += r.group(0) + "\n\n"
            self.info += "\n" + self.current_media_xml
            self.update_info()






            '''
FAILURE FROM ASSET RT - DIRECT
DEBUG	sonos                         :1573:play() #### ControlPointGUI.play current_media_id: http://192.168.0.10:26125/content/c2/b16/f44100/[INTER-RADIO]24.wav
DEBUG	sonos                         :1574:play() #### ControlPointGUI.play current_media_xml: <item id="[INTER-RADIO]24-au87" parentID="au87" refID="" restricted="true" ><dc:title> Rock FM 97.4 (Top 40-Pop)  [64kbps]</dc:title><upnp:class>object.item.audioItem.audioBroadcast</upnp:class><upnp:writeStatus>NOT_WRITABLE</upnp:writeStatus><res bitsPerSample="16" nrAudioChannels="2" protocolInfo="http-get:*:audio/wav:DLNA.ORG_PN=WAV;DLNA.ORG_OP=01" sampleFrequency="44100">http://192.168.0.10:26125/content/c2/b16/f44100/[INTER-RADIO]24.wav</res><upnp:albumArtURI>http://radiotime-logos.s3.amazonaws.com/s6924q.png</upnp:albumArtURI></item>
DEBUG	sonos                         :1575:play() #### ControlPointGUI.play current_media_type: MUSICSERVER
DEBUG	sonos                         :2058:on_device_event() device_event sid: uuid:RINCON_000E5830D2F001400_sub0000000010
DEBUG	sonos                         :2059:on_device_event() device_event c_v: {'LastChange': '<Event xmlns="urn:schemas-upnp-org:metadata-1-0/AVT/" xmlns:r="urn:schemas-rinconnetworks-com:metadata-1-0/"><InstanceID val="0"><TransportState val="STOPPED"/><CurrentPlayMode val="NORMAL"/><NumberOfTracks val="1"/><CurrentTrack val="1"/><CurrentSection val="0"/><CurrentTrackURI val="http://192.168.0.10:26125/content/c2/b16/f44100/[INTER-RADIO]24.wav"/><CurrentTrackDuration val="0:00:00"/><CurrentTrackMetaData val="&lt;DIDL-Lite xmlns:dc=&quot;http://purl.org/dc/elements/1.1/&quot; xmlns:upnp=&quot;urn:schemas-upnp-org:metadata-1-0/upnp/&quot; xmlns:r=&quot;urn:schemas-rinconnetworks-com:metadata-1-0/&quot; xmlns=&quot;urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/&quot;&gt;&lt;item id=&quot;-1&quot; parentID=&quot;-1&quot; restricted=&quot;true&quot;&gt;&lt;res protocolInfo=&quot;http-get:*:application/octet-stream:*&quot;&gt;http://192.168.0.10:26125/content/c2/b16/f44100/[INTER-RADIO]24.wav&lt;/res&gt;&lt;r:streamContent&gt;&lt;/r:streamContent&gt;&lt;r:radioShowMd&gt;&lt;/r:radioShowMd&gt;&lt;dc:title&gt;[INTER-RADIO]24.wav&lt;/dc:title&gt;&lt;upnp:class&gt;object.item&lt;/upnp:class&gt;&lt;/item&gt;&lt;/DIDL-Lite&gt;"/><r:NextTrackURI val=""/><r:NextTrackMetaData val=""/><r:EnqueuedTransportURI val="http://192.168.0.10:26125/content/c2/b16/f44100/[INTER-RADIO]24.wav"/><r:EnqueuedTransportURIMetaData val="&lt;DIDL-Lite xmlns=&quot;urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/&quot; xmlns:dc=&quot;http://purl.org/dc/elements/1.1/&quot; xmlns:r=&quot;urn:schemas-rinconnetworks-com:metadata-1-0/&quot; xmlns:upnp=&quot;urn:schemas-upnp-org:metadata-1-0/upnp/&quot;&gt;&lt;item id=&quot;[INTER-RADIO]24-au87&quot; parentID=&quot;au87&quot; refID=&quot;&quot; restricted=&quot;true&quot; &gt;&lt;dc:title&gt; Rock FM 97.4 (Top 40-Pop)  [64kbps]&lt;/dc:title&gt;&lt;upnp:class&gt;object.item.audioItem.audioBroadcast&lt;/upnp:class&gt;&lt;upnp:writeStatus&gt;NOT_WRITABLE&lt;/upnp:writeStatus&gt;&lt;res bitsPerSample=&quot;16&quot; nrAudioChannels=&quot;2&quot; protocolInfo=&quot;http-get:*:audio/wav:DLNA.ORG_PN=WAV;DLNA.ORG_OP=01&quot; sampleFrequency=&quot;44100&quot;&gt;http://192.168.0.10:26125/content/c2/b16/f44100/[INTER-RADIO]24.wav&lt;/res&gt;&lt;upnp:albumArtURI&gt;http://radiotime-logos.s3.amazonaws.com/s6924q.png&lt;/upnp:albumArtURI&gt;&lt;/item&gt;&lt;/DIDL-Lite&gt;"/><PlaybackStorageMedium val="NETWORK"/><AVTransportURI val="http://192.168.0.10:26125/content/c2/b16/f44100/[INTER-RADIO]24.wav"/><AVTransportURIMetaData val="&lt;DIDL-Lite xmlns=&quot;urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/&quot; xmlns:dc=&quot;http://purl.org/dc/elements/1.1/&quot; xmlns:r=&quot;urn:schemas-rinconnetworks-com:metadata-1-0/&quot; xmlns:upnp=&quot;urn:schemas-upnp-org:metadata-1-0/upnp/&quot;&gt;&lt;item id=&quot;[INTER-RADIO]24-au87&quot; parentID=&quot;au87&quot; refID=&quot;&quot; restricted=&quot;true&quot; &gt;&lt;dc:title&gt; Rock FM 97.4 (Top 40-Pop)  [64kbps]&lt;/dc:title&gt;&lt;upnp:class&gt;object.item.audioItem.audioBroadcast&lt;/upnp:class&gt;&lt;upnp:writeStatus&gt;NOT_WRITABLE&lt;/upnp:writeStatus&gt;&lt;res bitsPerSample=&quot;16&quot; nrAudioChannels=&quot;2&quot; protocolInfo=&quot;http-get:*:audio/wav:DLNA.ORG_PN=WAV;DLNA.ORG_OP=01&quot; sampleFrequency=&quot;44100&quot;&gt;http://192.168.0.10:26125/content/c2/b16/f44100/[INTER-RADIO]24.wav&lt;/res&gt;&lt;upnp:albumArtURI&gt;http://radiotime-logos.s3.amazonaws.com/s6924q.png&lt;/upnp:albumArtURI&gt;&lt;/item&gt;&lt;/DIDL-Lite&gt;"/><CurrentTransportActions val="Play, Stop, Pause, Seek, Next, Previous"/></InstanceID></Event>'}
            '''



    def on_device_event_seq(self, sid, seq, changed_vars):
    
        # check it is an rc event - just pass these through without seq/queueing
        # TODO: add separate queue/seq for these?
        if 'LastChange' in changed_vars and changed_vars['LastChange'] != None:
            if self.control_point.get_rc_service().event_sid == sid:    
                self.process_device_event_seq(sid, seq, changed_vars)
                return
    
        seq = int(seq)
        # don't process events that come late in sequence
        for k, v in changed_vars.items():
#            if k == "LastChange": print str(datetime.datetime.now()) + " @@@@      event=" + str(k) + " seq=" + str(seq) + " sid=" + sid
            if (sid, k) in self.last_event_seq:
#                if k == "LastChange": print str(datetime.datetime.now()) + " @@@@      last seq=" + str(self.last_event_seq[(sid, k)])
                if self.last_event_seq[(sid, k)] > seq:
#                    if k == "LastChange": print str(datetime.datetime.now()) + " @@@@      rejected (seq=" + str(seq) + " last seq=" + str(self.last_event_seq[(sid, k)])
                    self.check_event_queue()
                    return
#            if k == "LastChange": print str(datetime.datetime.now()) + " @@@@      set seq=" + str(seq)
            self.last_event_seq[(sid, k)] = seq

        # queue up events so they are processed in order
#        if k == "LastChange": print str(datetime.datetime.now()) + " @@@@      queued"
        self.event_queue.put((sid, seq, changed_vars))
        self.check_event_queue()


    def check_event_queue(self):
        # process events from queue one at a time
#        print str(datetime.datetime.now()) + " @@@@@@    ceq called"
        to_process = True
        while to_process == True:
#            print str(datetime.datetime.now()) + " @@@@@@    loop"
            self.event_lock.acquire()
#            print str(datetime.datetime.now()) + " @@@@@@    locked"
            try:
                (sid, seq, changed_vars) = self.event_queue.get(False)
#                print str(datetime.datetime.now()) + " @@@@@@    dequeued"
                self.process_device_event_seq(sid, seq, changed_vars)
#                print str(datetime.datetime.now()) + " @@@@@@    after process"
            except Empty:
                to_process = False
#                print str(datetime.datetime.now()) + " @@@@@@    empty"
            finally:
                self.event_lock.release()
#                print str(datetime.datetime.now()) + " @@@@@@    finally"


    def process_device_event_seq(self, sid, seq, changed_vars):
        # GUI updates from device events are not in GTK thread so need to call enter/leave
#        if is_hildon == True:
#            aafilename = '/home/user/MyDocs/Sonos/albumart.jpeg'                    
#        else:
#            aafilename = '/home/mark/UPnP/BRisa/Sonos/albumart.jpeg'                    
        if not 'SystemUpdateID' in changed_vars:
            log.debug('device_event sid: %s' % sid)
            log.debug('device_event seq: %s' % seq)
            log.debug('device_event c_v: %s' % str(changed_vars))

        # check it is a LastChange event
        if 'LastChange' in changed_vars and changed_vars['LastChange'] != None:
            if self.control_point.get_rc_service().event_sid == sid:
#            if self.control_point.get_current_renderer().get_rc_service().event_sid == sid:
                # event from RenderingControl
                ns = "{urn:schemas-upnp-org:metadata-1-0/RCS/}"
                elt = self.from_string(changed_vars['LastChange'])
                self.remove_namespace(elt, ns)
                # check if it is initial event message
                if self.current_renderer_events_rc == {}:
                    # save all tags
                    self.process_event_tags_rc(elt, self.current_renderer_events_rc)
#                    log.debug('cre_rc: %s' % self.current_renderer_events_rc)
                    # set GUI as appropriate
                    # set volume control
                    if 'OutputFixed' in self.current_renderer_events_rc:
                        self.current_renderer_output_fixed = self.current_renderer_events_rc['OutputFixed']
                    else:
                        self.current_renderer_output_fixed = '0'
                    if self.playing_window != None:
                        gtk.gdk.threads_enter()
                        bv = self.glade_playing_xml.get_widget("button_volume")
                        if self.current_renderer_output_fixed == '1':
                            bv.set_sensitive(False)
                        else:
                            bv.set_sensitive(True)
                        if 'Volume_Master' in self.current_renderer_events_rc:
                            bv.set_value(float(self.current_renderer_events_rc['Volume_Master']))
                        # set mute status
                        if 'Mute_Master' in self.current_renderer_events_rc:
                            self.set_mute(self.current_renderer_events_rc['Mute_Master'])
                        gtk.gdk.threads_leave()
                else:
                    # not initial message, update vars
                    tag_list = {}                    
                    self.process_event_tags_rc(elt, tag_list)
                    # process changed tags                    
#                    log.debug('tl: %s' % tag_list)
                    for key, value in tag_list.iteritems():
                        self.current_renderer_events_rc[key] = value
                        # set GUI as appropriate
                        if self.playing_window != None:
                            gtk.gdk.threads_enter()
                            if key == 'Volume_Master':
                                bv = self.glade_playing_xml.get_widget("button_volume")
                                bv.set_value(float(value))
                            elif key == 'Mute_Master':
    #                            log.debug('MUTE is: %s' % value)
                                self.set_mute(value)
                            elif key == 'OutputFixed':
                                # TODO: check whether we need to move the next line out of the if statement
                                self.current_renderer_output_fixed = value
                                bv = self.glade_playing_xml.get_widget("button_volume")
                                if self.current_renderer_output_fixed == '1':
                                    bv.set_sensitive(False)
                                else:
                                    bv.set_sensitive(True)
                            gtk.gdk.threads_leave()
#                return
            elif self.control_point.get_at_service().event_sid == sid or (self.control_point.get_at_service().event_sid == '' and self.control_point.get_current_renderer().udn == sid):
                # event from AVTransport
#                print str(datetime.datetime.now()) + " @@@@@@@@  AVT start"
                # TODO: check if we need to remove the ns, and if it is actually removed anyway
                ns = "{urn:schemas-upnp-org:metadata-1-0/AVT/}"
                elt = self.from_string(changed_vars['LastChange'])
                self.remove_namespace(elt, ns)
                # check if it is initial event message
                if self.current_renderer_events_avt == {}:
                    # save all tags
                    self.process_event_tags_avt(elt, self.current_renderer_events_avt)
                    # set GUI as appropriate
                    old_playing = 'old'
                    old_extras = 'old'
                    old_albumart = 'old'
                    self.now_playing, self.now_extras = self.current_music_item.unwrap_metadata(self.current_renderer_events_avt)
                    if self.playing_window != None:
                        if self.now_playing != old_playing:
                            gtk.gdk.threads_enter()
                            bv = self.glade_playing_xml.get_widget("now_playing")
                            bv.set_text(self.now_playing)
                            gtk.gdk.threads_leave()
                        if self.now_extras != old_extras:
                            gtk.gdk.threads_enter()
                            bv = self.glade_playing_xml.get_widget("extras")
                            bv.set_text(self.now_extras)
                            gtk.gdk.threads_leave()
                        if self.current_music_item.music_item_albumartURI != old_albumart:
                            # HACK: sending avt service of current renderer in case current_server is not selected - uses same URL...
                            # TODO: can we get this from zone player instead?
                            pbuf, text = getAlbumArt(self.control_point.get_at_service(), self.current_music_item.music_item_albumartURI)
                            gtk.gdk.threads_enter()
                            self.display_album_art(pbuf, text)
                            gtk.gdk.threads_leave()
                    # transport state
                    self.set_play(self.current_renderer_events_avt['TransportState'])
                else:
                    # not initial message, update vars
                    tag_list = {}
                    self.process_event_tags_avt(elt, tag_list)
#                    log.debug('tl: %s' % tag_list)
                    # save changed tags                    
                    for key, value in tag_list.iteritems():
                        self.current_renderer_events_avt[key] = value
                    # process changed tags (after saving them as need all related ones to be updated too)
                    for key, value in tag_list.iteritems():
                        # set GUI as appropriate
                        if key == 'CurrentTrackMetaData':
                            old_playing = self.now_playing
                            old_extras = self.now_extras
                            old_albumart = self.current_music_item.music_item_albumartURI
                            self.now_playing, self.now_extras = self.current_music_item.unwrap_metadata(self.current_renderer_events_avt)
                            if self.playing_window != None:
                                if self.now_playing != old_playing:
                                    gtk.gdk.threads_enter()
                                    bv = self.glade_playing_xml.get_widget("now_playing")
                                    bv.set_text(self.now_playing)
                                    gtk.gdk.threads_leave()
                                if self.now_extras != old_extras:
                                    gtk.gdk.threads_enter()
                                    bv = self.glade_playing_xml.get_widget("extras")
                                    bv.set_text(self.now_extras)
                                    gtk.gdk.threads_leave()
                                if self.current_music_item.music_item_albumartURI != old_albumart:
                                    # HACK: sending current_renderer in case current_server is not selected - uses same URL...
                                    # TODO: can we get this from zone player instead?
                                    pbuf, text = getAlbumArt(self.control_point.get_at_service(), self.current_music_item.music_item_albumartURI)
                                    gtk.gdk.threads_enter()
                                    self.display_album_art(pbuf, text)
                                    gtk.gdk.threads_leave()
                        elif key == 'TransportState':
                            self.set_play(value)
#                print str(datetime.datetime.now()) + " @@@@@@@@  AVT end"
#                return
            
        elif 'ThirdPartyMediaServers' in changed_vars:

            # for these, need to associate them with each zoneplayer
            # - use sid

            elt = self.from_string(changed_vars['ThirdPartyMediaServers'])
            '''
            'ThirdPartyMediaServers': '
            <MediaServers>
                <Ex 
                    CURL="http://192.168.0.3:1400/msprox?uuid=02286246-a968-4b5b-9a9a-defd5e9237e0" 
                    EURL="http://192.168.0.10:2869/upnphost/udhisapi.dll?event=uuid:02286246-a968-4b5b-9a9a-defd5e9237e0+urn:upnp-org:serviceId:ContentDirectory"
                    T="2"
                    EXT="1"/>
                <MediaServer 
                    Name="Windows Media (Henkelis)" 
                    UDN="02286246-a968-4b5b-9a9a-defd5e9237e0" 
                    Location="http://192.168.0.10:2869/upnphost/udhisapi.dll?content=uuid:02286246-a968-4b5b-9a9a-defd5e9237e0"/>
                <Ex 
                    CURL="http://192.168.0.10:56043/ContentDirectory/50565062-8a5b-7f33-c3de-168e9401eaee/control.xml" 
                    EURL="http://192.168.0.10:56043/ContentDirectory/50565062-8a5b-7f33-c3de-168e9401eaee/event.xml" 
                    T="1" 
                    EXT=""/>
                <MediaServer 
                    Name="Asset UPnP: HENKELIS" 
                    UDN="50565062-8a5b-7f33-c3de-168e9401eaee" 
                    Location="http://192.168.0.10:56043/DeviceDescription.xml"/>
                <Service UDN="USERNAME" Md="" Password="PASSWORD"/>
            </MediaServers>
            '''
            mediaserver = {}
            mediaservers = {}
            c = 0
            for entry in elt:
                # assumes Ex entry comes before MediaServer entry!
                if entry.tag == 'Ex':
                    mediaserver['CURL'] = entry.attrib['CURL']
                    mediaserver['EURL'] = entry.attrib['EURL']
                    mediaserver['T'] = entry.attrib['T']
                    mediaserver['EXT'] = entry.attrib['EXT']
                if entry.tag == 'MediaServer':
#                    mediaserver['Name'] = "Sonos: " + entry.attrib['Name']
                    mediaserver['Name'] = entry.attrib['Name']
                    mediaserver['UDN'] = entry.attrib['UDN']
                    mediaserver['Location'] = entry.attrib['Location']
                    self.control_point.make_third_party_mediaserver_service(mediaserver)
                    mediaservers[c] = mediaserver
                    c += 1
                    mediaserver = {}
                   
                if entry.tag == 'Service':
                    services = {}
                    services['UDN'] = entry.attrib['UDN']
                    services['Md'] = entry.attrib['Md']
                    services['Password'] = entry.attrib['Password']
                    
                    self.services[services['UDN']] = services

            self.thirdpartymediaservers[sid] = mediaservers

            '''
            ZoneGroupTopology
            <e:propertyset xmlns:e="urn:schemas-upnp-org:event-1-0">
                <e:property>
                    <ZoneGroupState>
                        <ZoneGroups>
                            <ZoneGroup Coordinator="RINCON_000E5830D2F001400" ID="RINCON_000E5830D2F001400:1">
                                <ZoneGroupMember UUID="RINCON_000E5830D2F001400" Location="http://192.168.0.3:1400/xml/zone_player.xml" ZoneName="Kitchen" Icon="x-rincon-roomicon:kitchen" SoftwareVersion="11.7-19141" MinCompatibleVersion="10.20-00000" BootSeq="136"/>
                            </ZoneGroup>
                            <ZoneGroup Coordinator="RINCON_000E5823A88A01400" ID="RINCON_000E5823A88A01400:3">
                                <ZoneGroupMember UUID="RINCON_000E5823A88A01400" Location="http://192.168.0.14:1400/xml/zone_player.xml" ZoneName="Living Room" Icon="x-rincon-roomicon:living" SoftwareVersion="11.7-19141" MinCompatibleVersion="10.20-00000" BootSeq="84"/>
                            </ZoneGroup>
                        </ZoneGroups>
                    </ZoneGroupState>
                </e:property>
                <e:property>
                    <ThirdPartyMediaServers>
                        <MediaServers>
                            <Service UDN="USERNAME" Md="" Password="PASSWORD"/>
                        </MediaServers>
                    </ThirdPartyMediaServers>
                </e:property>
                <e:property>
                    <AvailableSoftwareUpdate>
                        <UpdateItem xmlns="urn:schemas-rinconnetworks-com:update-1-0" Type="Software" Version="11.7-19141" UpdateURL="http://update.sonos.com/firmware/Gold/v3.0-Hendrix-GC2_Gold/^11.7-19141" DownloadSize="0"/>
                    </AvailableSoftwareUpdate>
                </e:property>
                <e:property>
                    <AlarmRunSequence>RINCON_000E5823A88A01400:84:0</AlarmRunSequence>
                </e:property>
            </e:propertyset>

            'ThirdPartyMediaServers':
            <MediaServers>
                <Ex CURL="http://192.168.0.7:1400/msprox?uuid=02286246-a968-4b5b-9a9a-defd5e9237e0" 
                    EURL="http://192.168.0.10:2869/upnphost/udhisapi.dll?event=uuid:02286246-a968-4b5b-9a9a-defd5e9237e0+urn:upnp-org:serviceId:ContentDirectory" 
                    T="2" 
                    EXT="1"/>
                <MediaServer Name="Windows Media (Henkelis)" 
                             UDN="02286246-a968-4b5b-9a9a-defd5e9237e0" 
                             Location="http://192.168.0.10:2869/upnphost/udhisapi.dll?content=uuid:02286246-a968-4b5b-9a9a-defd5e9237e0"/>
                <Service UDN="USERNAME" Md="" Password="PASSWORD"/>
            </MediaServers>

            ContentDirectory
            <e:propertyset xmlns:e="urn:schemas-upnp-org:event-1-0">
                <e:property><SystemUpdateID>9</SystemUpdateID></e:property>
                <e:property><ContainerUpdateIDs>S:,3</ContainerUpdateIDs></e:property>
                <e:property><ShareListRefreshState>NOTRUN</ShareListRefreshState></e:property>
                <e:property><ShareIndexInProgress>0</ShareIndexInProgress></e:property>
                <e:property><ShareIndexLastError></ShareIndexLastError></e:property>
                <e:property><UserRadioUpdateID>RINCON_000E5823A88A01400,11</UserRadioUpdateID></e:property>
                <e:property><SavedQueuesUpdateID>RINCON_000E5830D2F001400,6</SavedQueuesUpdateID></e:property>
                <e:property><ShareListUpdateID>RINCON_000E5823A88A01400,195</ShareListUpdateID></e:property>
                <e:property><RecentlyPlayedUpdateID>RINCON_000E5823A88A01400,0</RecentlyPlayedUpdateID></e:property>
            </e:propertyset>

            '''


    def process_event_tags_rc(self, elt, event_list):
        # save values
        InstanceID = elt.find('InstanceID')
        if InstanceID != None:
            event_list['InstanceID'] = InstanceID.get('val')    # not checking this at present, assuming zero
            for child in elt.findall('InstanceID/*'):
                nodename = child.tag                
                nodechannel = child.get('channel')
                if nodechannel != None:
                    nodename += '_' + nodechannel
                val = child.get('val')
                event_list[nodename] = val

    def process_event_tags_avt(self, elt, event_list):
        # save values
        InstanceID = elt.find('InstanceID')
        if InstanceID != None:
            event_list['InstanceID'] = InstanceID.get('val')    # not checking this at present, assuming zero
            for child in elt.findall('InstanceID/*'):
                nodename = child.tag
                val = child.get('val')
                event_list[nodename] = val
                # check for metadata associated with tag
                if nodename.endswith('MetaData'):
                    if val != '' and val != 'NOT_IMPLEMENTED':
    #                    log.debug('PROCESS EVENT TAGS AVT val: %s' % val)
                        # get the item element from within the DIDL-lite element
                        
    #                    print "val: " + str(val)

                        # Sonos has an issue with returning more than 1024 characters in the val attrib of
                        # r:EnqueuedTransportURIMetaData and AVTransportURIMetaData in a NOTIFY
                        # (strangely there is no problem with CurrentTrackMetaData)
                        # NOTE - when Sonos sets those itself it doesn't set some elements so they don't exceed 1024
                        # - if those elements are not complete, ignore them (TODO: work out whether that affects 
                        # any further processing we do that needs them)
                        # TODO: work out how to stop these attribs exceeding 1024 chars

                        if val.endswith('</DIDL-Lite>'):

                            item = ElementItem().from_string(val)[0]
                            # get the class of the item
                            upnp_class = find(item, 'upnp', 'class').text

                            # check if current renderer is a zone player
                            current_renderer = self.control_point.get_current_renderer()

                            is_sonos = False
                            if current_renderer.udn in self.known_zone_players:
                                is_sonos = True
                                # as it's a Sonos, parse the attributes into a Sonos object to capture the extended elements
                                if upnp_class == 'object.item.audioItem.audioBroadcast':
                                    elt = SonosAudioBroadcast()
                                elif upnp_class == 'object.item.audioItem.musicTrack':
                                    elt = SonosMusicTrack()
                                elif upnp_class == 'object.item.audioItem.musicTrack.recentShow':
                                    elt = SonosMusicTrackShow()
                                elif upnp_class == 'object.item':
                                    elt = SonosItem()
                                    '''                                    
                                    <r:EnqueuedTransportURI val="x-rincon-playlist:RINCON_000E5830D2F001400#A:ALBUMARTIST/Jeff%20Buckley/"/>
                                    <r:EnqueuedTransportURIMetaData val="<DIDL-Lite xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/" xmlns:r="urn:schemas-rinconnetworks-com:metadata-1-0/" xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/">
                                        <item id="A:ALBUMARTIST/Jeff%20Buckley/" parentID="A:ALBUMARTIST/Jeff%20Buckley" restricted="true">
                                            <dc:title>All</dc:title>
                                            <upnp:class>object.container.playlistContainer.sameArtist</upnp:class>
                                            <desc id="cdudn" nameSpace="urn:schemas-rinconnetworks-com:metadata-1-0/">RINCON_AssociatedZPUDN</desc>
                                        </item>
                                    </DIDL-Lite>                                    
                                    '''
# XML created by selecting all from artist
# THIS NEEDS TESTING...                                    
                                elif upnp_class.startswith('object.container.playlistContainer'):
                                    elt = PlaylistContainer()
                                else:
                                    # oops, don't know what we're dealing with - pass to non-sonos processing
                                    # TODO: decide which other classes we need to Sonos-ise
                                    is_sonos = False
                                if is_sonos:
                                    elt.from_element(item)

                            if not is_sonos:
                                # not a Sonos or we don't recognise the class, get the outer class name
                                # TODO: do we want to move this to didl-lite (so it recognises the classes from there)?
                                names = upnp_class.split('.')
                                class_name = names[-1]
                                class_name = "%s%s" % (class_name[0].upper(), class_name[1:])
                                try:
                                    upnp_class = eval(class_name)
                                    elt = upnp_class()
                                    elt.from_element(item)
                                    print "@@ elt: " + str(elt)
                                except Exception, e:
                                    raise UnknownClassError('Unknown upnp class: ' + upnp_class) 

                            event_list[nodename] = elt


    def get_position_info(self):
        self.current_position = self.control_point.get_position_info()
        self.current_track = self.current_position['Track']
        self.current_track_duration = self.current_position['TrackDuration']
        self.current_track_URI = self.current_position['TrackURI']
        self.current_track_metadata = self.current_position['TrackMetaData']
        self.current_track_relative_time_position = self.current_position['RelTime']

    def clear_position_info(self):
        self.current_position = {}
        self.current_track = '-1'
        self.current_track_duration = ''
        self.current_track_URI = ''
        self.current_track_metadata = ''
        self.current_track_relative_time_position = ''

    def _event_subscribe_callback(self, cargo, subscription_id, timeout):
        log.debug('Event subscribe done cargo=%s sid=%s timeout=%s', cargo, subscription_id, timeout)

    def _event_renewal_callback(self, cargo, subscription_id, timeout):
# TODO: add error processing for if renewal fails - basically resubscribe. NEW - check if this is catered for in 0.10.0
        log.debug('Event renew done cargo=%s sid=%s timeout=%s', cargo, subscription_id, timeout)

    def _event_unsubscribe_callback(self, cargo, subscription_id):
        log.debug('Event unsubscribe done cargo=%s sid=%s', cargo, subscription_id)

    def from_string(self, aString):
        elt = parse_xml(aString)
#        print "from_string 1 (parse) - " + str(elt)
        elt = elt.getroot()
#        print "from_string 2 (root) - " + str(elt)
        return elt

    def remove_namespace(self, doc, ns):
        """Remove namespace in the passed document in place."""
        nsl = len(ns)
        for elem in doc.getiterator():
            if elem.tag.startswith(ns):
                elem.tag = elem.tag[nsl:]

    def _on_refresh_clicked(self, button):
        pass
#        rt = RefreshThread(self.control_point.force_discovery)
#        rt.start()


    def _on_container_treeview_click(self, treeview, path):
        # at this point we are within a GTK thread so don't use enter/leave
        if treeview.row_expanded(path):
            treeview.collapse_row(path)
        else:
            treeview.expand_row(path, False)
            
    def _on_container_treeview_activated(self, treeview, path, row, data):
        # at this point we are within a GTK thread so don't use enter/leave
        (model, iter) = treeview.get_selection().get_selected()
        if treeview.row_expanded(path):
            treeview.collapse_row(path)
        else:
            self.item_media_list_liststore.clear()
            
            name = model.get_value(iter, 0)
            id = model.get_value(iter, 1)
            xml = model.get_value(iter, 2)
            type = model.get_value(iter, 3)

            # disconnect model from view and disable sorting to speed updates up
            self.container_treeview.freeze_child_notify()
#            self.container_treeview.set_model(None)
#            self.container_treestore.set_sort_column_id(-1, gtk.SORT_ASCENDING)

            # TODO: replace these literals with items from MusicServices list - remember we need to know what type they are....
            if type == "RadioTime_ROOT":
                self.radiotime_getlastupdate()
                self.browse_radiotime(id, iter, "root")
            elif type == "Napster_ROOT":
                self.browse_napster(id, iter)
            elif type == "Deezer_ROOT":
                self.browse_deezer(id, iter)
            elif type == "RADIOTIME":
                self.browse_radiotime(id, iter)
            elif type == "MUSICSERVER" or type == "SONOSMUSICSERVER":
                self.browse_media_server(id, iter)
            elif type == "THIRDPARTYMEDIASERVER_ROOT":
                self.browse_thirdparty_media_server(name, id, iter, "root")
            elif type == "THIRDPARTYMEDIASERVER":
                name = self.get_treestore_root_parent_name(iter)
                self.browse_thirdparty_media_server(name, id, iter)
            elif type == "MSMEDIASERVER_ROOT":
                self.search_ms_media_server(name, id, iter, "root")
            elif type == "MSMEDIASERVER":
                name = self.get_treestore_root_parent_name(iter)
                self.search_ms_media_server(name, id, iter)
                
            elif type == "TEST_ROOT":
                self.run_test(id, iter, "root")

            # reconnect model re-enable sorting 
#            self.container_treestore.set_sort_column_id(0, gtk.SORT_ASCENDING)
#            self.container_treeview.set_model(self.container_treestore)
            self.container_treeview.thaw_child_notify()

            treeview.expand_to_path(path)

    def _on_media_item_listview_changed(self, listview):
        # at this point we are within a GTK thread so don't use enter/leave
        (model, iter) = listview.get_selection().get_selected()
        self.current_media_id = model.get_value(iter, 1)
        self.current_media_xml = model.get_value(iter, 2)
        self.current_media_type = model.get_value(iter, 3)

        if self.current_media_type == "RADIOTIME":
            uri = 'x-sonosapi-stream:' + self.current_media_id + '?sid=' + self.music_services['RadioTime'].Id + '&flags=32'
            self.current_media_id = uri

        if self.info_window != None:
            run_async_function(self.display_music_location, (), 0.001)

    def _on_media_item_selected(self, play_button, *args, **kwargs):
        # default
        self.play_now_noqueue()

    def _on_play_clicked(self, play_button, *args, **kwargs):
        self.check_play()

    def _on_stop_clicked(self, stop_button, *args, **kwargs):
        self.stop()

    def _on_next_clicked(self, next_button, *args, **kwargs):
        self.next()

    def _on_previous_clicked(self, previous_button, *args, **kwargs):
        self.previous()

    def _on_mute_clicked(self, mute_button, *args, **kwargs):
        self.toggle_mute()
        self.mute()

    def _on_volume_changed(self, volume_button, *args, **kwargs):
        if self.current_renderer_output_fixed == '1':
            return
# TODO: must be a cleaner way to get this
        volume = args[0]    
#        log.debug('VOLUME: %s' % volume)
        self.volume(volume=volume)

    def _on_info_clicked(self, info_button, *args, **kwargs):
        self.show_info_window()

    def _on_about_activated(self, widget):
        pass # TODO

    def destroy_server_combo_box(self):
        self.comboBox_server_devices.destroy()

    def destroy_renderer_combo_box(self):
        self.comboBox_renderer_devices.destroy()

class Error(Exception):
    """Base class for exceptions in this module."""
    pass

class UnknownClassError(Error):
    """Exception raised for errors in classes.
    Attributes:
        message -- explanation of the error
    """
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return repr(self.message)

def sync_gtk_message(fun):
    def worker((R, condition, function, args, kwargs)):
        R.result = apply(function, args, kwargs)
        condition.acquire()
        condition.notify()
        condition.release()
    def fun2(*args, **kwargs):
        condition = threading.Condition()
        condition.acquire()
        class R: pass
        gobject.idle_add(worker, (R, condition, fun, args, kwargs))
        condition.wait()
        condition.release()
        return R.result
    return fun2

def async_gtk_message(fun):
    def worker((function, args, kwargs)):
        apply(function, args, kwargs)
    def fun2(*args, **kwargs):
        gobject.idle_add(worker, (fun, args, kwargs))
    return fun2



#class RefreshThread(ThreadObject):
#    handle = None
#
#    def __init__(self, handle):
#        Thread.__init__(self)
#        self.handle = handle
#
#    def run(self):
#        self.handle()


#def main():
#    try:
#        gui = ControlPointGUI()
#        gtk.gdk.threads_init()
#        gtk.main()
#    except KeyboardInterrupt, e:
#        quit()
def main():
    gui = ControlPointGUI()
#    gtk.gdk.threads_init()
    gtk.gdk.threads_enter()
    reactor.main()
    gtk.gdk.threads_leave()
    gui.control_point.destroy()


#        import traceback        
#        traceback.print_stack()


#def quit():
#    from sys import exit
#    log.debug('Exiting ControlPoint!')
#    exit(0)


if __name__ == "__main__":
    main()
