import matplotlib.pyplot as plt

xPoints = range(90)
yPoints = []
start = 1000
rate = 1.0152605
for x in range(len(xPoints)):
    yPoints.append( start*rate**x)

plt.plot(xPoints,yPoints, label = "exponential")
##plt.plot(xPoints,xPoints, label = "f(x) = x")
plt.legend()
plt.show()