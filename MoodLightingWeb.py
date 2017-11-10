import time, sys, threading,Queue
import pigpio
from ColorResult import ColorResult
from flask import Flask,request
import random

#Set these to the pins you've connected the mosfets to 
rPin = 17
gPin = 22
bPin = 24

app = Flask(__name__)

running = True

pi = pigpio.pi()
q = Queue.Queue()

currentTime = 0
pos = 0
nextPos = 2


#Linear interpolation between two values.
def interpolate(startValue,endValue,stepNumber,lastStepNumber):
		if(stepNumber > lastStepNumber):
			return endValue
		return (endValue - startValue) * stepNumber / lastStepNumber + startValue

#Interpolate between two colours and return the new colour as a ColorResult.
def interp(colorOne,colorTwo,step,stepMax):
	r = interpolate(colorOne.r,colorTwo.r,step,stepMax)
	g = interpolate(colorOne.g,colorTwo.g,step,stepMax)
	b = interpolate(colorOne.b,colorTwo.b,step,stepMax)
	return ColorResult(r,g,b)


#Set the LEDs to the given colour result	
def updateColor(result):
	global pi
	pi.set_PWM_dutycycle(rPin,result.r)
	pi.set_PWM_dutycycle(gPin,result.g)
	pi.set_PWM_dutycycle(bPin,result.b)

	
#Start the threaded method
#While it's running, just waits for the queue to not be empty
#When the queue is no longer empty, start a fade show with the data in the queue	
def run():
	global q
	while(running):
		if(not q.empty()):
			colors = q.get()
			fadeTime = q.get()
			pauseTime = q.get()
			random = q.get()
			print "Starting"
			q.put(1)
			start(colors,fadeTime,pauseTime,random)

#Selects the next random colour			
def generateNextColor(colors):
	global nextPos
	done = False
	while not done:
		i = random.randrange(0,len(colors))
		if i != nextPos:
			done = True
			return i
	

#Start a fade show with the given array of Colors, fadeTime, pauseTime and random setting.
def start(colors,fadeTime,pauseTime,random):
	global nextPos
	global pos
	global currentTime
	last = time.time() * 1000.0
	while(not q.empty()):
		now = time.time() * 1000.0
		delta = now - last
		last = time.time() * 1000.0
		col1 = colors[pos]
		c2 = nextPos
		col2 = colors[c2]
		result = interp(col1,col2,currentTime,fadeTime)
		updateColor(result)
		currentTime += delta
		if(currentTime >= fadeTime + pauseTime):
			currentTime = 0
			if not random:
				pos += 1
				nextPos += 1
			else:
				pos = nextPos
				nextPos = generateNextColor(colors)
		if(pos == len(colors)):
			pos = 0
		if(nextPos == len(colors)):
			nextPos = 0
	print "Stopped"
	currentTime = 0
	pos = 0
	nextPos = 2
	updateColor(ColorResult(0,0,0))			

#The /fade endpoint	
@app.route("/fade")
def fade():
	global t
	global tEvent
	if(q.empty()):
		fadeTime = int(request.args.get("fadeTime"))
		pauseTime = int(request.args.get("pauseTime"))
		random = request.args.get("random")
		colorsArg = request.args.get("colors")
		colSplit = colorsArg.split(":")
		colors = []
		for color in colSplit:
			print color
			col = color.split(",")
			colors.append(ColorResult(int(col[0]),int(col[1]),int(col[2])))
		q.put(colors)
		q.put(fadeTime)
		q.put(pauseTime)
		q.put(random)
	else:
		return "1"
	return "0"

#The /stop endpoint
@app.route("/stop")
def stop():
	if(not q.empty()):
		t = q.get()
		return "0"
	else:
		return "1"		

if __name__ == "__main__":
	t = threading.Thread(target=run,args = ())
	t.start()
	print "Thread started"
	app.debug = False
	app.run(host='0.0.0.0')
