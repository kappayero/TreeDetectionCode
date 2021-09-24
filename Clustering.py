import argparse
import os
import json
import csv
import math
#from subprocess import REALTIME_PRIORITY_CLASS
import geopy.distance



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

def filteredListOfFiles(dirName, filter):
    fullFileList = getListOfFiles(dirName)
    resultingList = []
    for file in fullFileList:
        if file.endswith(filter):
            resultingList.append(file)
    return resultingList

def ReadConfigFile(filePath):
    print("Opening camera configuration file in:",filePath)
    with open(filePath, 'r') as f:
        lines = f.readlines()
    
    loadedData = {}
    for line in lines:
        splittedLine = [item.strip() for item in line.split("=")]
        key_ = splittedLine[0]
        if(key_ == "width" or key_=="height"):
            val_ = int(splittedLine[1])
        elif (key_=="dfov"):
            val_ = float(splittedLine[1])
        else:
            raise ValueError("The key "+key_+" in file "+filePath+"is not a recognised argument. Expected width, height or dfov. I.e: width=3600")
        loadedData[key_] = val_
    return loadedData

def GetCartesianBaseValues(width, height, dfov):
    Cx = width/2 #Position of the centre pixel horizontally
    Cy = height/2 #Position of the centre pixel vertically
    H = ((width**2)+(height**2))**(0.5) #length in pixels of the diagonal
    pd = dfov/H #degrees per pixel
    #print("width [",width,"] height [",height,"] dfov [",dfov,"] -> Cx [",Cx,"] Cy [",Cy,"] pd [",pd,"]")
    return pd, Cx, Cy

def GetAngle(x, y, pd):
    angle = (((x**2)+(y**2))**0.5)*pd
    #print("X[",x,"], Y[",y,"], angle [",angle,"]")
    return angle

def TransformToMetres(x, y, degrees, height):
    distanceMts = height*math.tan(math.radians(degrees)) # distance in metres away from the centre of the image
    
    #print("distancePx [",distancePx,"], heightToTreeLevel[",height,"], distanceMts [",distanceMts,"] Xm [",Xm,"] Ym [",Ym,"] ")
    return distanceMts

def CalculateCoordinate(originLat, originLon, GimYaw, distanceMetres):
    pointCoord = geopy.distance.distance(kilometers=(distanceMetres/1000.0)).destination((originLat, originLon), bearing=GimYaw)
    #print("originLat[", originLat,"], originLon[", originLon,"], GimYaw[", GimYaw,"], distanceMetres[", distanceMetres,"] --> finalLatitude[", pointCoord.latitude,"], finalLongitude[", pointCoord.longitude,"]")
    return pointCoord.latitude, pointCoord.longitude

'''
    def CalculateCoordinate(Xm, Ym, GimYaw):
    degreesToRotate = 0.0
    if GimYaw >= 0:
        degreesToRotate = math.radians(GimYaw)
    else:
        degreesToRotate = math.radians(360.0-GimYaw)

    deg1 = math.cos(degreesToRotate)
    deg2 = math.sin(degreesToRotate)
    Xm2 =  deg1 * (Xm) - deg2 * (Ym)
    Ym2 = deg2 * (Xm) + deg1 * (Ym)

    return Xm2, Ym2'''

'''
def TranslateToCoordinates(X, Y, OriginLat, OriginLon):
    # Define starting point.
    origin = geopy.Point(48.853, 2.349)

    # Define a general distance object, initialized with a distance of 1 km.
    d = geopy.distance.VincentyDistance(kilometers = 1)

    # Use the `destination` method with a bearing of 0 degrees (which is north)
    # in order to go from point `start` 1 km to north.
    print d.destination(point=origin, bearing=0)
    '''

def Clustering():
    framesFolder, outputFolder, vThreshold, hThreshold = \
        args.framesFolder, args.outputFolder, args.verticalThreshold, args.horizontalThreshold
    print("Loading frames data")    
    jsonFiles = filteredListOfFiles(framesFolder, ".json")
    videosList = {}
    for jsonFile in jsonFiles:
        videoName = os.path.splitext(os.path.basename(jsonFile))[0]

        f = open(jsonFile)        
        jsonData = json.load(f)
        videosList[videoName] = jsonData
    
    print("Loaded ", len(videosList), "'.json' files")

    for videoName, videoData in videosList.items():
        #Iterate per frame
        frames = videoData[0]
        frameIndex = 0
        totalFrames = len(frames)
        for frameName, frameData in frames.items():
            frameIndex+=1
            print("Frame")
            #Iterate per bounding box
            for box in boundingBoxesList:
                print("BB")
            if(int(frameIndex)%100==0 or frameIndex == totalFrames):
                print("[",round((frameIndex/totalFrames*100), 1),"%]Frame ", frameName, " of ",  totalFrames)



        #Save the results
        print("\nWriting results:")
        os.makedirs(outputFolder, exist_ok=True)
        finalPathJson = os.path.join(outputFolder,videoName+ ".json")
        finalPathCsv = os.path.join(outputFolder,videoName+ ".csv")
        with open(finalPathJson, 'w', encoding='utf-8') as f:
            json.dump(videoData[0], f, ensure_ascii=False, indent=4)
        print("\t (1/2) Json >> ", finalPathJson)


        line_header = ['Frame', 'Lat', 'Lon', 'Alt', 'TerrainElevation',  'Yaw', 'Pitch', 'Roll', 'GimYaw', 'GimPitch', 'GimRoll', 'BoundingBoxClass', 'BoundingBoxCentre_X', 'BoundingBoxCentre_Y', 'BoundingBox_Width%', 'BoundingBox_Height%', 'BoundingBox_Lat', 'BoundingBox_Lon']
        lines_content = []
        #{FrameNum:[[Labels],{sensor:sensorData}]}
        for frame_key, frame_value in videoData[0].items():
            droneData = []
            if(len(frame_value[1]) > 0):
                droneData = \
                    [frame_value[1]["Lat"], frame_value[1]["Lon"], frame_value[1]["Alt"], frame_value[1]["Height"], \
                    frame_value[1]["Yaw"], frame_value[1]["Pitch"], frame_value[1]["Roll"],\
                    frame_value[1]["GimYaw"], frame_value[1]["GimPitch"], frame_value[1]["GimRoll"],\
                    frame_value[1]["BoundingBox_Lat"], frame_value[1]["BoundingBox_Lon"]]
            else:
                droneData = ['', '', '', '', '', '', '', '', '', '', '', '']

            for label_tmp in frame_value[0]:
                lines_content.append([frame_key] + droneData + label_tmp)
        with open(finalPathCsv, mode='w') as csv_file:
            csv_writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
            csv_writer.writerow(line_header)
            csv_writer.writerows(lines_content)  
        print("\t (2/2) Json >> ", finalPathCsv)  


parser = argparse.ArgumentParser()
parser.add_argument('--framesFolder', type=str,required=True, default='/content/output/localisation_boxes/', help='Folder containing the .json and .csv files as input')
parser.add_argument('--verticalThreshold', required=True, type=int, default=20, help='latitude degrees in which the variation of the bounding box is still considered of the same object')
parser.add_argument('--horizontalThreshold', required=True, type=int, default=20, help='longitude degrees in which the variation of the bounding box is still considered of the same object')
parser.add_argument('--outputFolder', type=str, default='/content/output/clustering/', help='Output folder for the clustering algorithm')
args = parser.parse_args()
print(args)
Clustering()