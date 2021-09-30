import argparse
import os
from posixpath import basename
import sys
from collections import OrderedDict
import cv2
import datetime
#import pprint
import json
import csv


def getListOfFiles(dirName):
    print("Scanning in "+dirName)
    # create a list of file and sub directories 
    # names in the given directory 
    listOfFile = os.listdir(dirName)
    allFiles = list()
    # Iterate over all the entries
    for entry in listOfFile:
        # Create full path
        fullPath = os.path.join(dirName, entry)
        # If entry is a directory then get the list of files in this directory 
        if os.path.isdir(fullPath):
            allFiles = allFiles + getListOfFiles(fullPath)
        else:
            allFiles.append(fullPath)
                
    return allFiles

def printArgs(sourceFolder, predictionFolder, outputFolder, weightsPath, imageSize, confidenceScore, modelPath):
    print("sourceFolder: ", sourceFolder)
    print("predictionFolder: ", predictionFolder)
    print("outputFolder: ", outputFolder)
    print("weightsPath: ", weightsPath)
    print("imageSize: ", str(imageSize))
    print("confidenceScore: ", str(confidenceScore))
    print("modelPath: ", modelPath)

def GetSources(sourceFolder):
    dictSubt = {}
    #load available subtitles list
    subtitlesPath = os.path.join(sourceFolder, "subtitles")
    subtitlesList = getListOfFiles(subtitlesPath)
    for subtPath in subtitlesList:
        split = os.path.splitext(subtPath)
        tmpKey = os.path.basename(split[0])
        if split[1] == ".srt":
            dictSubt[tmpKey] = subtPath
        else :
            print("WARNING: The file "+subtPath+" found is not an .srt subtitles file! This file has been omited.")
        #print("\t"+"("+tmpKey+")"+subtPath+" "+warningTxt) #Debug
    #load available videos list
    dictFiles = {}
    videosPath = os.path.join(sourceFolder, "videos")
    videosList = getListOfFiles(videosPath)    
    for vidPath in videosList:
        tmpKey = os.path.basename(os.path.splitext(vidPath)[0])
        #print("\t"+"("+tmpKey+")"+vidPath) #Debug
        if tmpKey in dictSubt:
            #Create a dictionary {objectName: [videoPath, subtitlesPath, {FrameNum:[Labels]}]}
            dictFiles[tmpKey] = [vidPath, dictSubt[tmpKey], {}]
        else:
            raise Exception("The file "+vidPath+" does not have a matching subtitles file (.srt).")
    print(str(len(dictFiles))+" object(s) were found as source file(s)")
    return dictFiles

def timestamp_to_miliseconds(line):
    timeValues = line.split("-->")
    startValuesTxt = timeValues[0].strip().replace(",",":").split(":")
    endValuesTxt = timeValues[1].strip().replace(",",":").split(":")
    startValuesList = list(map(int, startValuesTxt))    
    endValuesList = list(map(int, endValuesTxt))
    startValueMs = (startValuesList[0] * 60 * 60 * 1000) + (startValuesList[1] * 60000) + (startValuesList[2] * 1000) + startValuesList[3]
    endValueMs = (endValuesList[0] * 60 * 60 * 1000) + (endValuesList[1] * 60000) + (endValuesList[2] * 1000) + endValuesList[3]
    return startValueMs, endValueMs

def Consolidate():
    print("Consolidating!")
    sourceFolder, predictionFolder, outputFolder, weightsPath, imageSize, confidenceScore, inferencePath = \
        args.sourceFolder, args.predictionFolder, args.outputFolder, args.weightsPath, args.imageSize, args.confidenceScore, args.inferencePath
    printArgs(sourceFolder, predictionFolder, outputFolder, weightsPath, imageSize, confidenceScore, inferencePath)

    #Check the videos in the source folder and their subtitles
    #{objectName: [videoPath, subtitlesPath, {FrameNum:[Labels],{sensor:sensorData}}]}
    sourceObjects = GetSources(sourceFolder)

    #loadedInference = dict()

    inferenceFileList = getListOfFiles(predictionFolder)
    for fileTmp in inferenceFileList:
        #print("File ", fileTmp) #Debug
        split = os.path.splitext(fileTmp)
        fileName = os.path.basename(split[0])
        if split[1] == ".txt":
            split2 = fileName.rpartition('_')
            basename = split2[0]
            frameNum = int(split2[2])
#            /*if not basename in loadedInference:
#                loadedInference[basename] = OrderedDict()

            with open(fileTmp, 'r') as reader:
                #print("opening '"+basename+"' frame "+frameNum) #Debug
                attr = []
                for line in reader.readlines():
                    x = line.split(' ')
                    x.pop()
                    attr.append([int(x[0]), float(x[1]), float(x[2]), float(x[3]), float(x[4])])
                    
            ((sourceObjects[basename])[2])[frameNum] = [attr, {}]
            # {baseName : {frameNum, (labels)}}
    
    #sort
    for keySort, valueSort in sourceObjects.items():
        unsortedDict = valueSort[2]
        sourceObjects[keySort][2] = OrderedDict(sorted(unsortedDict.items()))

    #Print - Debug
    print("Number of objects: ", len(sourceObjects.keys()))
    for keyOne, valueOne in sourceObjects.items():
        print("\tVideo '", keyOne, "' has ", len(valueOne[2]))
        #for keyTwo, valueTwo in valueOne[2].items():
            #print("\t\tFrame ", keyTwo)

    #Load Subtitles data per video
    for keyObjFPS, valueObjFPS in sourceObjects.items():

        #Load Subtitles file
        subtitles = OrderedDict()
        with open(valueObjFPS[1], 'r', encoding='utf-8') as f:
            text = f.readlines()
            startMs = 0
            endMs = 0
            l = 0
            for line_ in text:
                #print("line:", line_, "->", l)
                if l == 1:
                    startMs, endMs = timestamp_to_miliseconds(line_)
                    #print("Start: ", startMs, " End: ", endMs)
                elif l == 2:
                    vals = line_.split(" ")
                    varDict = {}
                    #print("Vals:", vals)
                    for var in vals:
                        #print("Var:", var)
                        sd = var.split(":")
                        if(len(sd)==2):
                            varDict[sd[0]] = float(sd[1])

                    subtitles[startMs] = [endMs, varDict]
                    startMs = 0
                    endMs = 0
                l+=1
                if(l==4):
                    l=0
        subtitles = OrderedDict(sorted(subtitles.items()))
        #pprint.pprint(subtitles)

        #Get FPS of video        
        cam = cv2.VideoCapture(valueObjFPS[0])
        fps = cam.get(cv2.CAP_PROP_FPS)
        #print("FPS:", fps)

        #loop the frames dictionary
        for frameIndexKey, frameIndexValues in valueObjFPS[2].items():
            #print("Matching frame ", frameIndexKey, " with subtitles values")
            timestamp = float(frameIndexKey)/fps
            frameMs = 1000.0*timestamp
            #timestampR = datetime.datetime.fromtimestamp(frameMs//1000)
            #print("\t\tFrame: ", frameIndexKey, " -> timestamp: ", timestamp, " -> frameMs:", round(frameMs,2))
            relevantSubt = {}
            for d_key, d_value in subtitles.items():
                if(frameMs >= d_key):
                    if(frameMs < d_value[0]):
                        relevantSubt = dict(d_value[1])
                else:
                    break
            if(len(relevantSubt) == 0):
                print("\t\t\tWarning! No sensor data found in the .srt file for frame "+str(frameIndexKey)+"!")
            relevantSubt["Timestamp"] = timestamp
            frameIndexValues[1] = relevantSubt
            sourceObjects[keyObjFPS][2][frameIndexKey] = frameIndexValues
            #print(sourceObjects[keyObjFPS][2][frameIndexKey])
        
        #print(sourceObjects[keyObjFPS][2])
        #pprint.pprint(sourceObjects[keyObjFPS])


        frame_count = int(cam.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count/fps
        print('fps = ' + str(fps))
        print('number of frames = ' + str(frame_count))
        print('duration (ms) = ' + str(duration*1000.0))
        minutes = int(duration/60)
        seconds = duration%60
        print('duration (M:S) = ' + str(minutes) + ':' + str(seconds))

        #Save the results
        print("\nWriting results:")
        os.makedirs(outputFolder, exist_ok=True)
        finalPathJson = os.path.join(outputFolder,keyObjFPS+ ".json")
        finalPathCsv = os.path.join(outputFolder,keyObjFPS+ ".csv")
        with open(finalPathJson, 'w', encoding='utf-8') as f:
            json.dump(sourceObjects[keyObjFPS][2], f, ensure_ascii=False, indent=4)
        print("\t (1/2) Json >> ", finalPathJson)


        line_header = ['Frame', 'Lat', 'Lon', 'Alt', 'Yaw', 'Pitch', 'Roll', 'GimYaw', 'GimPitch', 'GimRoll', 'Timestamp', 'BoundingBoxClass', 'BoundingBoxCentre_X', 'BoundingBoxCentre_Y', 'BoundingBox_Width%', 'BoundingBox_Height%', ]
        lines_content = []
        #{FrameNum:[[Labels],{sensor:sensorData}]}
        for frame_key, frame_value in sourceObjects[keyObjFPS][2].items():
            droneData = []
            if(len(frame_value[1]) > 1):
                droneData = \
                    [frame_value[1]["Lat"], frame_value[1]["Lon"], frame_value[1]["Alt"],\
                    frame_value[1]["Yaw"], frame_value[1]["Pitch"], frame_value[1]["Roll"],\
                    frame_value[1]["GimYaw"], frame_value[1]["GimPitch"], frame_value[1]["GimRoll"], frame_value[1]["Timestamp"]]
            else:
                droneData = ['', '', '', '', '', '', '', '', '', '']

            for label_tmp in frame_value[0]:
                lines_content.append([frame_key] + droneData + label_tmp)
        with open(finalPathCsv, mode='w') as csv_file:
            csv_writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
            csv_writer.writerow(line_header)
            csv_writer.writerows(lines_content)  
        print("\t (2/2) Json >> ", finalPathCsv)

    


parser = argparse.ArgumentParser()
parser.add_argument('--sourceFolder', type=str, default='/content/input/source/', help='Folder containing the video folder and srt subtitles folder')
parser.add_argument('--predictionFolder', type=str, default='/content/output/inference/', help='Output folder for the prediction model')
parser.add_argument('--outputFolder', type=str, default='/content/output/localisation/', help='Output folder for the localisation algorithm')  # output folder
parser.add_argument('--weightsPath', type=str, default='/content/input/weights/weights.pt', help='Path of the weights file of the prediction model')
parser.add_argument('--imageSize', type=int, default=448, help='Size of the images used at model training')
parser.add_argument('--confidenceScore', type=float, default=0.4, help='Confidence score used when predicting')
parser.add_argument('--inferencePath', type=str, default='/content/ScaledYOLOv4/inference/output/', help='Path of the predictor result folder')
args = parser.parse_args()
print(args)
Consolidate()



