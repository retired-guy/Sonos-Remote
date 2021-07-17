#screen brightness lib
import pigpio
from threading import Timer

gpio = pigpio.pi()
screenstate = 0
t = None

def screenon():
    global screenstate
    global t
    global gpio

    if not t is None:
      try:
        t.cancel()
        print("timeout cancelled!")
        t = None
      except:
        pass

    if screenstate == 1:
      return

    screenstate = 1
    try:
      gpio.set_PWM_dutycycle(19, 50)
      print("screen brightness set")
    except Exception as e:
      print(e)
      pass

def blankscreen():
    global screenstate
    global gpio

    if screenstate == 0:
        return

    if t is None:
      return

    screenstate = 0

    try:
      gpio.set_PWM_dutycycle(19, 0)
    except Exception as e:
      print(e)
      pass

def screenoff():
    global t

    if t is None:
      t = Timer(10, blankscreen)
      t.start()
      print("timeout started!")

