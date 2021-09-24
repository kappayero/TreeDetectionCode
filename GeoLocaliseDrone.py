import argparse
import os
from osgeo import gdal,osr
import json
import csv

#DEBUG
import matplotlib.pyplot as plt



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

def GetExtent(ds):
    """ Return list of corner coordinates from a gdal Dataset """
    xmin, xpixel, _, ymax, _, ypixel = ds.GetGeoTransform()
    width, height = ds.RasterXSize, ds.RasterYSize
    xmax = xmin + width * xpixel
    ymin = ymax + height * ypixel

    return (xmin, ymax), (xmax, ymax), (xmax, ymin), (xmin, ymin)

def ReprojectCoords(coords,src_srs,tgt_srs):
    """ Reproject a list of x,y coordinates. """
    trans_coords=[]
    transform = osr.CoordinateTransformation( src_srs, tgt_srs)
    for x,y in coords:
        x,y,z = transform.TransformPoint(x,y)
        trans_coords.append([x,y])
    return trans_coords

def GetAltitudeFromLatLon(lat_, lon_, indataset):
    #indataset = gdal.Open( infile)
    srs = osr.SpatialReference()
    srs.ImportFromWkt(indataset.GetProjection())

    srsLatLong = srs.CloneGeogCS()
    ct = osr.CoordinateTransformation(srsLatLong, srs)
    (X, Y, height) = ct.TransformPoint(lon_, lat_)

    # Report results
    #print('longitude: %f\t\tlatitude: %f' % (lon_, lat_))
    #print('X: %f\t\tY: %f' % (X, Y))
    #VALUE OF COORDINATE IN METRES
    #print(X ,Y)

    #driver = gdal.GetDriverByName('GTiff')
    band = indataset.GetRasterBand(1)

    cols = indataset.RasterXSize
    rows = indataset.RasterYSize

    transform = indataset.GetGeoTransform()

    xOrigin = transform[0]
    yOrigin = transform[3]
    pixelWidth = transform[1]
    pixelHeight = -transform[5]
    data = band.ReadAsArray(0, 0, cols, rows)

    col = int((X - xOrigin) / pixelWidth )
    row = int((yOrigin - Y ) / pixelHeight)
    #ROW AND COLUMN VALUE
    #print("R,C: ",row,col)
    #Data AT THAT ROW COLUMN
    return data[row][col]
    
def GetRasterCorners(ds):
    ext=GetExtent(ds)
    src_srs=osr.SpatialReference()
    src_srs.ImportFromWkt(ds.GetProjection())
    tgt_srs = src_srs.CloneGeogCS()
    geo_ext=ReprojectCoords(ext, src_srs, tgt_srs)
    return geo_ext

def GetRelevantTifFile(lat_, lon_, tileList):
    X = lon_
    Y = lat_
    for tile in tileList:
        P2 = tile[1]
        P3 = tile[2]
        P4 = tile[3]
        if(P3[0] > X >= P4[0]):
            if(P2[1] > Y >= P3[1]):
                #print("GetRelevantTifFile >> Tile found! ", tile[4])
                return tile[4]


def GeoLocaliseDrone():
    framesFolder, demFolder, outputFolder = \
        args.framesFolder, args.demFolder, args.outputFolder
    print("Loading frames data")    
    jsonFiles = filteredListOfFiles(framesFolder, ".json")
    videosList = {}
    for jsonFile in jsonFiles:
        videoName = os.path.splitext(os.path.basename(jsonFile))[0]
        videoFramesData = {}
        f = open(jsonFile)
        videosList[videoName] = json.load(f)
    
    print("Loaded ", len(videosList), " .json files")

    print("Loading .tif files")
    tifFiles = filteredListOfFiles(demFolder, ".tif")
    print("GeoTif files found: ",len(tifFiles))

    tileList = []
    indexTile = 1
    numTiles = len(tifFiles)
    for tile in tifFiles:
        print("(", indexTile, " of ", numTiles, ")Opening: ", tile)
        raster = gdal.Open(tile, gdal.GA_ReadOnly)
        corners_tmp = GetRasterCorners(raster)
        corners_tmp.append(tile)
        tileList.append(corners_tmp)
        indexTile += 1

    #for val in tileList:
    #    print(type(val), ": ", val)

    print("GeoTif files indexed. Starting translation of bounding boxes per frame...")
    for videoName, videoData in videosList.items():
        indexFrame = 0
        for frameNum, frameData in videoData.items():
            indexFrame += 1
            if(int(indexFrame)%100==0):
                print("[",round((indexFrame/len(videoData)*100), 1),"%]Frame ", frameNum, " of ",  len(videoData))
            #listOfBoundingBoxes = frameData[0]
            droneSensorData = frameData[1]
            if(len(droneSensorData) > 1):
                lat_ = droneSensorData["Lat"]
                lon_ = droneSensorData["Lon"]
                relevantTifFile = GetRelevantTifFile(lat_, lon_, tileList)

                raster = gdal.Open(relevantTifFile, gdal.GA_ReadOnly)
                height = GetAltitudeFromLatLon(lat_, lon_, raster)
                #print(height, type(height))
                videosList[videoName][frameNum][1]["Height"] = height.item()
            else:
                print("WARNING: The frame ", frameNum, " of video ", videoName, " does not contain sensor data. This frame will be ignored.")
            
            
    
        #Save the results
        print("\nWriting results:")
        os.makedirs(outputFolder, exist_ok=True)
        finalPathJson = os.path.join(outputFolder,videoName+ ".json")
        finalPathCsv = os.path.join(outputFolder,videoName+ ".csv")
        with open(finalPathJson, 'w', encoding='utf-8') as f:
            json.dump(videoData, f, ensure_ascii=False, indent=4)
        print("\t (1/2) Json >> ", finalPathJson)


        line_header = ['Frame', 'Lat', 'Lon', 'Alt', 'TerrainElevation',  'Yaw', 'Pitch', 'Roll', 'GimYaw', 'GimPitch', 'GimRoll', 'Timestamp', 'BoundingBoxClass', 'BoundingBoxCentre_X', 'BoundingBoxCentre_Y', 'BoundingBox_Width%', 'BoundingBox_Height%', ]
        lines_content = []
        #{FrameNum:[[Labels],{sensor:sensorData}]}
        for frame_key, frame_value in videoData.items():
            droneData = []
            if(len(frame_value[1]) > 1):
                droneData = \
                    [frame_value[1]["Lat"], frame_value[1]["Lon"], frame_value[1]["Alt"], frame_value[1]["Height"], \
                    frame_value[1]["Yaw"], frame_value[1]["Pitch"], frame_value[1]["Roll"],\
                    frame_value[1]["GimYaw"], frame_value[1]["GimPitch"], frame_value[1]["GimRoll"], frame_value[1]["Timestamp"]]
            else:
                droneData = ['', '', '', '', '', '', '', '', '', '', '']

            for label_tmp in frame_value[0]:
                lines_content.append([frame_key] + droneData + label_tmp)
        with open(finalPathCsv, mode='w') as csv_file:
            csv_writer = csv.writer(csv_file, delimiter=',', quotechar='"', quoting=csv.QUOTE_ALL)
            csv_writer.writerow(line_header)
            csv_writer.writerows(lines_content)  
        print("\t (2/2) Json >> ", finalPathCsv)  



parser = argparse.ArgumentParser()
parser.add_argument('--framesFolder', type=str, default='/content/output/consolidation/', help='Folder containing the .json and .csv files')
parser.add_argument('--demFolder', type=str, default='/content/input/DEM/', help='Input folder containing all the GeoTIF images')
parser.add_argument('--outputFolder', type=str, default='/content/output/localisation/', help='Output folder for the localisation algorithm')
args = parser.parse_args()
print(args)
GeoLocaliseDrone()



