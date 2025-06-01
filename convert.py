import argparse
import os

def main(inputFileName, outputFileName):
    print(f"input file: {inputFileName}")
    inputPath, inputExtension = os.path.splitext(inputFileName)
    inputExtension = inputExtension.lower()

    if  inputExtension != ".csv":
        print(f"Error, input file extension is {inputExtension}, but should be .csv or .CSV")

    realOutputFile = outputFileName
    if realOutputFile is None:
        realOutputFile = inputPath + ".gpx"

    print(f"output file: {realOutputFile}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description ='Convert custom CSV to GPX.')
    parser.add_argument('-if', '--inputfile')
    parser.add_argument('-of', '--outputfile')

    args = parser.parse_args()
    main(args.inputfile, args.outputfile)
