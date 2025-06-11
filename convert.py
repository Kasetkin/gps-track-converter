import argparse
import os
from queue import SimpleQueue
import xml.etree.ElementTree as ET
from dataclasses import dataclass
import matplotlib.pyplot as plt

### After conversion to GPX you can edit it in Viking or something similar. For example -- cut the begining and the ending of the track.
### Also, it's good to filter GPX track by speed and minimal distance, you can do it in OsmAnd on Android or "GPS Track Editor" on Windows.
### GPSBabel isn't very good, because it can not filter by max.speed (or I don't know how to do it).
###
### Link for simple and really good soft (works with Wine)
### http://www.gpstrackeditor.com/transfer/GpsTrackEditor-1.15.141.exe

@dataclass
class TrackPoint:
    timestamp: str = ""
    lat: float = 666.0
    lon: float = 666.0
    alt: float = -999999999.0
    hdop: float = -1.0
    vdop: float = -1.0
    pdop: float = -1.0
    satInView: int = -1
    heading: float = -1.0
    speed: float = -1.0
    temperature: float = -300.0
    humidity: float = -1.0
    pressure: float = -1.0
    pressureAlt: float = -1.0
    line: int = -1

MAX_PDOP = 4.0
MAX_HDOP = 5.0
MAX_VDOP = 5.0
DEFAULT_ID = "!XXXXXXXX"
AVERAGING_WINDOW_SIZE = 101

### fix GPS altitude using atmosphere pressure data
### Formula for p(alt) = 1013.25 hPa * [ 1 − 6.5 * alt / (288150 m) ]^5.255
### so, reverse formula will be
### alt(p) = [ 1 - (p / 1013.25) ^ (1 / 5.255) ] * 288150 / 6.5
###     precalculated values:
###         1 / 5.255 == 0.190294957184
###         288150 / 6.5 == 44330.7692308
### it can be optimized if necessary, but probably it has no meaning
def pressureToAlt(p: float) -> float:
    return 44330.7692308 * (1.0 - pow(p / 1013.25, 0.190294957184))


def altitudeCorrection(altsGps: list, altsPress: list) -> list:
    if len(altsGps) != len(altsPress):
        print(f"Error!!! len(gps) should be equal to len(press), but it is {len(altsGps)} and {len(altsPress)}")
        system.exit(1)

    if len(altsGps) < AVERAGING_WINDOW_SIZE:
        print(f"Error!!! len(gps) should be >= {AVERAGING_WINDOW_SIZE}, but it is {len(altsGps)}")
        system.exit(1)

    gpsQueue = SimpleQueue()
    gpsQueueSum = 0
    pressQueue = SimpleQueue()
    pressQueueSum = 0

    correctionsList = list()

    for index in range(0, len(altsGps)):
        gps = altsGps[index]
        press = altsPress[index]

        while gpsQueue.qsize() >= AVERAGING_WINDOW_SIZE:
            oldValue = gpsQueue.get_nowait()
            gpsQueueSum -= oldValue

        gpsQueue.put_nowait(gps)
        gpsQueueSum += gps

        while pressQueue.qsize() >= AVERAGING_WINDOW_SIZE:
            oldValue = pressQueue.get_nowait()
            pressQueueSum -= oldValue

        pressQueue.put_nowait(press)
        pressQueueSum += press

        if pressQueue.qsize() == AVERAGING_WINDOW_SIZE and gpsQueue.qsize() == AVERAGING_WINDOW_SIZE:
            correction = float(gpsQueueSum - pressQueueSum)
            correction /= float(AVERAGING_WINDOW_SIZE)
            correctionsList.append(correction)

    print(f"corrections list size = {len(correctionsList)}")


    firstWindowCorrection = correctionsList[0]
    resultList = list()
    for index in range(0, AVERAGING_WINDOW_SIZE):
        resultList.append(altsPress[index] + firstWindowCorrection)

    for index in range(AVERAGING_WINDOW_SIZE, len(altsGps)):
        correctionForIndex = correctionsList[index - AVERAGING_WINDOW_SIZE]
        resultList.append(altsPress[index] + correctionForIndex)

    return resultList

def main(inputFileName, outputFileName):
    print(f"input file: {inputFileName}")
    inputPath, inputExtension = os.path.splitext(inputFileName)
    inputExtension = inputExtension.lower()

    if  inputExtension != ".csv":
        print(f"Error, input file extension is {inputExtension}, but should be .csv or .CSV")
        sys.exit(1)

    realOutputFile = outputFileName
    if realOutputFile is None:
        realOutputFile = inputPath + ".gpx"

    print(f"output file: {realOutputFile}")

    inFile = open(inputFileName, 'r')
    inLines = [line.rstrip() for line in inFile]

    allIDs = set()
    trackById = dict()

    lineIndex = 0

    ### check lines and get all IDs
    for line in inLines:
        if line[len(line) - 1] == ';':
            line = line[:-1]

        elements = line.split(';')
        elementsCount = len(elements)
        if elementsCount % 2 != 0:
            print(f"Error, number of elements {elementsCount} in string \n {line} \n, should be even, but it but isn't")
            print(f"Inpput line: {lineIndex + 1}")
            sys.exit(1)

        lineId = DEFAULT_ID
        newPoint = TrackPoint()
        newPoint.line = lineIndex

        for (key, value) in zip(elements[::2], elements[1::2]) :
            print(f"Line index {lineIndex}; for key {key} value is {value}")
            if key == "ID":
                lineId = value

            if key == "LAT":
                newPoint.lat = float(value)

            if key == "LON":
                newPoint.lon = float(value)

            if key == "HDOP":
                newPoint.hdop = float(value)

            if key == "VDOP":
                newPoint.vdop = float(value)

            if key == "PDOP":
                newPoint.pdop = float(value)

            if key == "ALT":
                newPoint.alt = float(value)

            if key == "DT":
                newPoint.timestamp = str(value)

            if key == "TEMP":
                newPoint.temperature = float(value)

            if key == "HUMID":
                newPoint.humidity = float(value)

            if key == "PRESS":
                newPoint.pressure = float(value)

        allIDs.add(lineId)
        if not lineId in trackById:
            trackById[lineId] = list()

        lineIndex += 1
        track = trackById[lineId]

        if (len(newPoint.timestamp) > 0) and (newPoint.timestamp != "1970-01-01T00:00:00Z"):
            if (abs(newPoint.lat) > 0.000001) or (abs(newPoint.lat) > 0.000001):
                if (newPoint.hdop < 0.0) or ((newPoint.hdop > 0.0) and (newPoint.hdop < MAX_HDOP)):
                    if (newPoint.pdop < 0.0) or ((newPoint.pdop > 0.0) and (newPoint.pdop < MAX_PDOP)):
                        if (newPoint.vdop < 0.0) or ((newPoint.vdop > 0.0) and (newPoint.vdop < MAX_VDOP)):
                            track.append(newPoint)


    for deviceId in allIDs:
        ALTITUDE_TO_FIX = -1234567
        altsGps = list()
        altsPress = list()

        track = trackById[deviceId]
        # meanTrackGpsAlt = 0.0
        # meanTrackPressAlt = 0.0
        counter = int(0)
        for point in track:
            gpsAlt = point.alt
            hasGpsAlt = (gpsAlt > -10000.0) and (abs(gpsAlt) > 0.000001)
            hasAirPressure = point.pressure > 0.000001
            if hasGpsAlt and hasAirPressure:
                altFromPress = pressureToAlt(point.pressure)
                point.pressureAlt = ALTITUDE_TO_FIX
                print(f"ALT: gps {gpsAlt:.3f}, press {altFromPress:.3f}")
                # meanTrackGpsAlt += gpsAlt
                # meanTrackPressAlt += altFromPress
                altsGps.append(gpsAlt)
                altsPress.append(altFromPress)
                counter += 1

        correctedAlts = altitudeCorrection(altsGps, altsPress)

        # meanTrackGpsAlt /= counter
        # meanTrackPressAlt /= counter
        # meanAltCorrection = meanTrackGpsAlt - meanTrackPressAlt
        # print(f"Mean ALT: gps {gpsAlt:.3f}, press {altFromPress:.3f}, points {counter}, alt correction: {meanAltCorrection:.3f}")

        ### \TODO use sliding window instead of one value (meanAltCorrection)

        index = 0
        for point in track:
            if point.pressureAlt == ALTITUDE_TO_FIX:
                point.pressureAlt = correctedAlts[index]
                index += 1
                print(f"Corrected ALT: gps {point.alt:.3f}, press {point.pressureAlt:.3f}")

        xValues = range(0, counter)
        plt.plot(xValues, altsGps, color='green')
        plt.plot(xValues, altsPress, color='blue')
        plt.plot(xValues, correctedAlts, color='red')
        plt.show()




    ### generate GPX for each deviceID
    for deviceId in allIDs:
        rootArgs = dict()
        rootArgs["version"] = "1.1"
        rootArgs["creator"] = "automatic-gpx-converter"
        root = ET.Element("gpx", rootArgs)

        metaNode = ET.SubElement(root, "metadata")
        b1 = ET.SubElement(metaNode, "name")
        b1.text = "###GPX###NAME###"
        b2 = ET.SubElement(metaNode, "time")
        b2.text = "2024-04-20T07:28:44Z"

        trackNode = ET.SubElement(root, "trk")
        trackName = ET.SubElement(trackNode, "name")
        b1.text = "###TRACK###NAME###"

        segmentNode = ET.SubElement(trackNode, "trkseg")

        track = trackById[deviceId]
        DEFAULT_POINT = TrackPoint()
        for point in track:
            trkptArgs = dict()
            latStr = "{:.10f}".format(point.lat)
            lonStr = "{:.10f}".format(point.lon)
            if (abs(point.lat) > 0.000001) or (abs(point.lat) > 0.000001):
                trkptArgs["lat"] = latStr
                trkptArgs["lon"] = lonStr

            trkptNode = ET.SubElement(segmentNode, "trkpt", trkptArgs)

            altForGpx = DEFAULT_POINT.alt
            if (point.pressureAlt > 0.000001):
                altForGpx = point.pressureAlt
            else:
                if (point.alt > -10000.0) and (abs(point.alt) > 0.000001):
                    altForGpx = point.alt

            if altForGpx > -10000.0:
                elevationNode = ET.SubElement(trkptNode, "ele")
                elevationNode.text = "{:.10f}".format(altForGpx)

            if (len(point.timestamp) > 0) and (point.timestamp != "1970-01-01T00:00:00Z"):
                timeNode = ET.SubElement(trkptNode, "time")
                timeNode.text = point.timestamp

            if point.satInView >= 0:
                satNode = ET.SubElement(trkptNode, "sat")
                satNode.text = str(point.satInView)

            if point.hdop > 0.0:
                hdopNode = ET.SubElement(trkptNode, "hdop")
                hdopNode.text = "{:.3f}".format(point.hdop)

            if point.vdop > 0.0:
                vdopNode = ET.SubElement(trkptNode, "vdop")
                vdopNode.text = "{:.3f}".format(point.vdop)

            if point.pdop > 0.0:
                pdopNode = ET.SubElement(trkptNode, "pdop")
                pdopNode.text = "{:.3f}".format(point.pdop)

            hasTemperature = point.temperature > -274.0
            hasPressure = point.pressure > 0.0
            hasHumidity = point.humidity >= 0.0
            needExtensions = hasTemperature or hasHumidity or hasPressure
            if needExtensions:
                extensionsNode = ET.SubElement(trkptNode, "extensions")
                gpxtpxExtensionNode = ET.SubElement(extensionsNode, "gpxtpx:TrackPointExtension")
                if hasTemperature:
                    tempNode = ET.SubElement(gpxtpxExtensionNode, "gpxtpx:atemp")
                    tempNode.text = str(point.temperature)

                # if hasHumidity:
                #     humidityNode = ET.SubElement(gpxtpxExtensionNode, "gpxtpx:humid")
                #     humidityNode.text = str(point.humidity)
                #
                # if hasPressure:
                #     pressureNode = ET.SubElement(gpxtpxExtensionNode, "gpxtpx:pressure")
                #     pressureNode.text = str(point.pressure)

        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ", level=0)

        with open (realOutputFile, "wb") as outFile :
            tree.write(outFile, encoding="utf-8", xml_declaration=True)

    print(f"list of IDs in file: {allIDs}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description ='Convert custom CSV to GPX.')
    parser.add_argument('-if', '--inputfile')
    parser.add_argument('-of', '--outputfile')

    args = parser.parse_args()
    main(args.inputfile, args.outputfile)
