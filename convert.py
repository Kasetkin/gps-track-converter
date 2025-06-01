import argparse
import os
import xml.etree.ElementTree as ET
from dataclasses import dataclass

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
    line: int = -1

DEFAULT_ID = "!XXXXXXXX"



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
        elements = line.split(';')
        elementsCount = len(elements)
        if elementsCount % 2 != 0:
            print(f"Error, number of elements {elementsCount} in string \n {line} \n, should be even, but it but isn't")
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

            if key == "ALT":
                newPoint.alt = float(value)

            if key == "DT":
                newPoint.timestamp = str(value)

        allIDs.add(lineId)
        if not lineId in trackById:
            trackById[lineId] = list()

        track = trackById[lineId]
        track.append(newPoint)

        lineIndex += 1

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
        for point in track:
            trkptArgs = dict()
            trkptArgs["lat"] = "{:.10f}".format(point.lat)
            trkptArgs["lon"] = "{:.10f}".format(point.lon)
            trkptNode = ET.SubElement(segmentNode, "trkpt", trkptArgs)

            if point.alt > -10000.0:
                elevationNode = ET.SubElement(trkptNode, "ele")
                elevationNode.text = "{:.10f}".format(point.alt)

            if len(point.timestamp) > 0:
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
