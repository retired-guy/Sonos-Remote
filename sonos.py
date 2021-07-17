import soco
import requests
import textwrap
import io,os,sys,time
import pigpio
import re
import screencontrols as scr

from evdev import InputDevice, categorize, ecodes
import time
from time import sleep
from threading import Thread
try:
    from Queue import Queue
except ImportError:
    from queue import Queue

from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
from PIL import ImageOps
#import numpy as np

########################################
## Sonos zone to monitor - CHANGE ME! ##
zone = soco.SoCo('192.168.68.128')
########################################

## Touchscreen event worker thread
def event_thread():
  for event in dev.read_loop():
    if event.type == ecodes.EV_KEY:
      absevent = categorize(event)
      if absevent.event.value == 0:
        handle_event(dev)

## Red and Blue color channels are reversed from normal RGB on pi framebuffer
def swap_redblue(img):
  "Swap red and blue channels in image"
  r, g, b, a = img.split()
  return Image.merge("RGBA", (b, g, r, a))

## Paint image to screen at position
def blit(img, pos):

  size = img.size
  w = size[0]
  h = size[1]
#  x = pos[0]
#  y = pos[1]

#  n = np.array(img)
#  n[:,:,[0,1,2]] = n[:,:,[2,1,0]]
#  fb[y:y+h,x:x+w] = n

  img = swap_redblue(img)
  fb.seek(4 * ((pos[1]) * fbw + pos[0]))

  iby = img.tobytes()
  for i in range(h):
    fb.write(iby[4*i*w:4*(i+1)*w])
    fb.seek(4 * (fbw - w), 1)

## Clear the screen, set backlight brightness
def initscreen():
  try:
    scr.screenon()
  except Exception:
    pass

  img = Image.new('RGBA', (800, 480))
  blit(img,(0,0))

  displaycontrols(False)

## Show track progress as red line
def displayprogress(seek,duration):
  progress = seek / duration * 370
  img = Image.new('RGBA', (370, 6))  

  draw = ImageDraw.Draw(img)
  draw.line((0,0,progress,0),fill='red',width=6)

  blit(img,(430,410))

## Paint << || >> and vol controls
def displaycontrols(status):

  img = Image.new('RGBA',size=(370,70),color=(0,0,0,255))

#  img.paste(ctls[0], (0,0))
  img.paste(ctls[6], (5,10))
  img.paste(ctls[5], (170,10))
  img.paste(ctls[1], (240,10))
  img.paste(ctls[2], (310,10))

  if status:
    img.paste(ctls[4], (90,10))
  else:
    img.paste(ctls[3], (90,10))

  blit(img,(430,410))

## Display artist, song title, album title
def displaymeta(album,title,artist):

  img = Image.new('RGBA',size=(370,410),color=(0,0,0,255))

  tw1 = textwrap.TextWrapper(width=15)
  tw2 = textwrap.TextWrapper(width=20)
  s = "\n"

  if artist is None: 
    artist = ""
  if title is None:
    title = ""
  if album is None:
    album = ""

  artist = s.join(tw2.wrap(artist))
  album = s.join(tw2.wrap(album))

  draw = ImageDraw.Draw(img)
  draw.text((10,50), artist, (191,245,245),font=fonts[1])
  draw.text((10,200), album, (255,255,255),font=fonts[1])

  blit(img,(430,0))

  img = Image.new('RGBA',size=(800,50),color=(0,0,0,255))
  draw = ImageDraw.Draw(img)
  draw.text((0,0),  title, (255,255,255),font=fonts[0])

  blit(img,(0,0))

## Grab the album cover and display
def getcoverart(cover_url):

  try:
    img = Image.open(requests.get(cover_url, stream=True).raw)
    img = img.resize((430,430))
    img = img.convert('RGBA')

    blit(img,(0,50))
  except Exception as e:
    print(e)
    pass

## Handle Touchscreen events
def handle_event(dev):

  x1 = dev.absinfo(ecodes.ABS_X).value
  y1 = dev.absinfo(ecodes.ABS_Y).value
  x=int((y1/480)*800)
  y=int(480-(x1/800)*480)
  scr.screenon()

  if x >= 430 and y >= 400:
    if x>= 740:
      v = min(zone.volume,96)
      zone.volume = v + 4
    elif x>= 670:
      v = max(zone.volume,4)
      zone.volume = v - 4
    elif x>= 600:
      zone.next()
    elif x>= 520:
      if playerstatus == 'PLAYING':
        zone.pause()
      else:
        zone.play()
    else:
      zone.previous()      

## Get seconds from time
def get_sec(time_str):
  h, m, s = time_str.split(':')
  return int(h) * 3600 + int(m) * 60 + int(s)

## Handle Sonos AV Events
def parseavevent(event):
  global playerstatus

  try:
    playerstate = event.transport_state
  except AttributeError:
    return

  if playerstate == "TRANSITIONING":
    return

  if playerstate == "PLAYING":
    displaycontrols(True)
    scr.screenon()
  else:
    displaycontrols(False)
    scr.screenoff()

  playerstatus = playerstate
  try:
    metadata = event.current_track_meta_data
  except AttributeError:
    return

  # This can happen if the the player becomes part of a group
  try:
    if metadata == "" or not hasattr(metadata, "album_art_uri"):
      return
  except Exception as e:
    print(e)
    return
  try:
    if metadata.album_art_uri.startswith("http"):
      albumart = metadata.album_art_uri
    else:
      albumart = "http://%s:1400%s#.jpg" % (
              zone.ip_address,
              metadata.album_art_uri)

    getcoverart(albumart)

  except Exception as e:
    print(e)
    pass

  # Is this a radio track
  try:
    if type(metadata) is soco.data_structures.DidlItem:
      currenttrack = metadata.stream_content
      creator = ""
      album = ""
    else:
      if hasattr(metadata, 'album'):
        album = metadata.album
      elif hasattr(event, "enqueued_transport_uri_meta_data") and \
                    hasattr(event.enqueued_transport_uri_meta_data, 'title'):
        album = event.enqueued_transport_uri_meta_data.title
      else:
        album = ""

      if hasattr(metadata, 'creator'):
        creator = metadata.creator
      else:
        creator = ""
      currenttrack = metadata.title
      
    displaymeta(album,currenttrack,creator)
  except Exception as e:
    print(e)
    pass


ctls = [] 
ctls.append( Image.open('./images/fond.png') )
ctls.append( Image.open('./images/volumedown.png') )
ctls.append( Image.open('./images/volumeup.png') )
ctls.append( Image.open('./images/play.png') )
ctls.append( Image.open('./images/pause.png') )
ctls.append( Image.open('./images/next.png') )
ctls.append( Image.open('./images/previous.png') )

fonts = []
fonts.append( ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 30) )
fonts.append( ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf', 28) )
fonts.append(  ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf', 18) )

data = None
ticks = 0
old_nowplaying = ''
old_url = ''
old_status = ''
seek = 0
duration = 0
progress = 0
playerstatus = ""

#h, w, c = 480, 800, 4
#fb = np.memmap('/dev/fb0', dtype='uint8',mode='w+', shape=(h,w,c))
fbw, fbh = 800, 480   # framebuffer dimensions
fb = open("/dev/fb0", "wb")

queue = Queue()

## Clear the screen
initscreen()

info = zone.avTransport.subscribe(
            auto_renew=True, event_queue=queue)

## Touchscreen input device
dev = InputDevice('/dev/input/event1')

## Start touch event handler thread
th = Thread(target=event_thread)
th.start()

## Start monitoring events for zone
while True:
  try:
    if (playerstatus == "PLAYING"):
      track_info = zone.get_current_track_info()
      position = get_sec(track_info['position'])
      duration = get_sec(track_info['duration'])
      if duration == 0:
        displayprogress(0,1)
      else:
        displayprogress(position,duration)
    else:
      scr.screenoff()

    ## If any Sonos events, handle them
    if not queue.empty():
      ev = queue.get()
      if ev.service.service_type == "AVTransport":
        parseavevent(ev)

  except Exception as e:
    print("Exception:",e)

  sleep(1)


