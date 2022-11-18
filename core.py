

import numpy as np
import matplotlib.pyplot as plt
import pylab as pl
import math



import numpy as np
import matplotlib.pyplot as plt
import pylab as pl
import math

## Add betting odds here
bet1 = 13 / 10
bet2 = 9 / 4
bet3 = 153 / 40
precision = 5
# Add betting odds here


def line_intersection(line1, line2):
    xdiff = (line1[0][0] - line1[1][0], line2[0][0] - line2[1][0])
    ydiff = (line1[0][1] - line1[1][1], line2[0][1] - line2[1][1])

    def det(a, b):
        return a[0] * b[1] - a[1] * b[0]

    div = det(xdiff, ydiff)
    if div == 0:
        raise Exception('lines do not intersect')

    d = (det(*line1), det(*line2))
    x = det(d, xdiff) / div
    y = det(d, ydiff) / div
    return x, y
# finds the coordinates of intersection of the bets

def points(bet1,bet2,bet3,precision):

    # precision is the square root of how many points it checks in a square unit on the graph, so if precision is 2 then it checks every 1/2 unit in the x and y direction so it checks say (0,0) (0,0.5) (0.5,0) (0.5,0.5)
    pointsX = []
    # values of x in the profit region, value at the corresponding value in pointsY is the corresponding y value of the point
    pointsY = []
    z = 10
    # this is the default bet on the 3rd bet, e.g 10 pounds
    width = 50
    # width of the graph
    testX = width / 2
    # test x value used to find the intersection points of the 3 bet graphs
    bet1P1 = [0, -z]
    bet1P2 = [testX, bet1 * testX - z]
    bet2P1 = [0, z / bet2]
    bet2P2 = [testX, (z + testX) / bet2]
    bet3P1 = [0, z * bet3]
    bet3P2 = [testX, -testX + z * bet3]
    # points on each lines used to find points of intersections between the lines

    intersection = [line_intersection([bet1P1, bet1P2], [bet2P1, bet2P2]),
                    line_intersection([bet1P1, bet1P2], [bet3P1, bet3P2]),
                    line_intersection([bet2P1, bet2P2], [bet3P1, bet3P2])]
    # points of intersection line_intersection[0] bet 1 bet 2, line_intersection[1] bet1 bet3 and line_intersection[2] bet2 bet3
    maxX = intersection[0][0]
    maxY = intersection[0][1]
    minX = intersection[0][0]
    minY = intersection[0][1]

    for i in range(3):
        if (intersection[i][0] > maxX):
            maxX = intersection[i][0]
        if (intersection[i][0] < minX):
            minX = intersection[i][0]
        if (intersection[i][1] > maxY):
            maxY = intersection[i][1]
        if (intersection[i][1] < minY):
            minY = intersection[i][1]
    # finds the maximum and minimum x and y values of the intersection which is used to create the "search zone", where the code below checks to see if that point is profitable or not
    maxX = math.floor(maxX)
    maxY = math.floor(maxY)
    minX = math.ceil(minX)
    minY = math.ceil(minY)
    # makes this values integers to reduce confusion with long floats

    # checks thru every point in the search zone varying by 1/precision, the larger the precision the more points are checked to see if they are profitable
    for i in range((maxX - minX) * precision + 1):
        currentX = minX + ((1 / precision) * i)
        for j in range((maxY - minY) * precision - 1):
            currentY = minY + (1 / precision) * j
            print(currentX, " , ", currentY)
            if (currentY < (bet1 * currentX) - z and currentY > (z + currentX) / bet2 and currentY < -currentX + (
                    z * bet3)):
                pointsX.append(currentX)
                pointsY.append(currentY)
                # adds points to array in order to plot
    print("Max X ", maxX)
    print("Min X ", minX)
    print("Max Y ", maxY)
    print("Min Y ", minY)
    print(pointsX)
    print(pointsY)
    x = np.arange(0, width, 1 / precision)
    plt.scatter(pointsX, pointsY)
    plt.plot(x, bet1 * x - z, color='red', label="bet1")
    # bounded below
    plt.plot(x, (z + x) / bet2, color='green', label="bet2")
    # bounded above
    plt.plot(x, -x + z * bet3, color='royalblue', label="bet3")
    # bounded below
    plt.vlines(minX, -width, width, color='black')
    plt.vlines(maxX, -width, width, color='black')
    plt.hlines(minY, -width, width, color='black')
    plt.hlines(maxY, -width, width, color='black')
    plt.legend()
    pl.xlim([0, maxX+10])
    pl.ylim([0, maxY+10])
    plt.fill_between(x, bet1 * x - z, alpha=.4, color='red')
    plt.fill_between(x, (10 + x) / bet2, 1000, alpha=.4, color='yellow')
    plt.fill_between(-x + 10 * bet3, x, step="pre", alpha=.4, color='royalblue')
    plt.fill()
    plt.fill()
    plt.show()
points(bet1,bet2,bet3,precision)
##