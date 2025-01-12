##############################################################################################################
# Motivation: implement various dithering strategies.

# Some of the stackers here are modified versions of the stackers in lsst.sims.maf.stackers.ditherStackers.
# These function similarly to ditherStackers,  with the major difference that dithers here are restricted to
# within the hexagons used to tile the sky. Each of these hexagons is inscribed in a FOV, and having dithers
# restricted to within these hexagons allows avoiding oversampling near the boundaries of the hexagonal tiles.
 
# Also, the stackers here follow new naming scheme:  [Pattern]Dither[Field]Per[Timescale]. The absence of the
# keyword 'Field' implies dither assignment to all fields.

# Humna Awan: humna.awan@rutgers.edu
# Date last modified: 08/18/15
###############################################################################################################
import numpy as np
from lsst.sims.maf.stackers import BaseStacker
from mafContrib.SeasonStacker_v2 import SeasonStacker_v2 as SeasonStacker

__all__ = ['RandomDitherFieldPerVisitStacker',
           'RepulsiveRandomDitherFieldPerVisitStacker',
           'SpiralDitherFieldPerVisitStacker',
           'SequentialHexDitherFieldPerVisitStacker',
           'RandomDitherFieldPerNightStacker',
           'RepulsiveRandomDitherFieldPerNightStacker',
           'SpiralDitherFieldPerNightStacker',
           'SequentialHexDitherFieldPerNightStacker',
           'RandomDitherPerNightStacker',
           'RepulsiveRandomDitherPerNightStacker',
           'SpiralDitherPerNightStacker',
           'SequentialHexDitherPerNightStacker',
           'PentagonDitherFieldPerSeasonStacker',
           'PentagonDiamondDitherFieldPerSeasonStacker',
           'PentagonDitherPerSeasonStacker',
           'PentagonDiamondDitherPerSeasonStacker']

def wrapRADec(ra, dec):
    """
    Wrap RA and Dec values so RA between 0-2pi (using mod),
      and Dec in +/- pi/2.
    """
    # Wrap dec.
    low = np.where(dec < -np.pi/2.0)[0]
    dec[low] = -1 * (np.pi + dec[low])
    ra[low] = ra[low] - np.pi
    high = np.where(dec > np.pi/2.0)[0]
    dec[high] = np.pi - dec[high]
    ra[high] = ra[high] - np.pi
    # Wrap RA.
    ra = ra % (2.0*np.pi)
    return ra, dec

def wrapRA(ra):
    """
    Wrap only RA values into 0-2pi (using mod).
    """
    ra = ra % (2.0*np.pi)
    return ra

def polygonCoords(nside,radius, rotationAngle):
    """
    Find the x,y coords of a polygon.
    """
    eachAngle= 2*np.pi/nside
    xCoords= np.zeros(nside, float)
    yCoords= np.zeros(nside, float)
    for i in range(0,nside):
        xCoords[i]= np.sin(eachAngle*i + rotationAngle)*radius
        yCoords[i]= np.cos(eachAngle*i + rotationAngle)*radius
        
    return zip(xCoords,yCoords)

######################################################################################################
######################################################################################################
# Type 1
class RandomDitherFieldPerVisitStacker(BaseStacker):
    """
    Randomly dither the RA and Dec pointings up to maxDither degrees from center, 
    different offset per visit for each field.
    """
    def __init__(self, raCol='fieldRA', decCol='fieldDec', maxDither=1.75, randomSeed=None):
        # Instantiate the RandomDither object and set internal variables.
        self.raCol = raCol
        self.decCol = decCol
        # Convert maxDither from degrees (internal units for ra/dec are radians)
        self.maxDither = np.radians(maxDither)
        self.randomSeed = randomSeed
        # self.units used for plot labels
        self.units = ['rad', 'rad']
        # Values required for framework operation: this specifies the names of the new columns.
        self.colsAdded = ['RandomDitherFieldPerVisitRA', 'RandomDitherFieldPerVisitDec']
        # Values required for framework operation: this specifies the data columns required from the database.
        self.colsReq = [self.raCol, self.decCol]

    def _generateRandomOffsets(self, noffsets):
        numPoints= noffsets*2
        dithersRad = np.sqrt(np.random.rand(numPoints))*self.maxDither
        dithersTheta = np.random.rand(numPoints)*np.pi*2.0

        xOff = dithersRad * np.cos(dithersTheta)
        yOff = dithersRad * np.sin(dithersTheta)
           
        # set up the hexagon: y=mx+b fortmat. 2h is the height.
        b= np.sqrt(3.0)*self.maxDither
        m= np.sqrt(3.0)
        h= self.maxDither*np.sqrt(3.0)/2.0
        
        # get the points that are inside hexagon
        index= np.where((yOff < m*xOff+b) &
                        (yOff > m*xOff-b) &
                        (yOff < -m*xOff+b) &
                        (yOff > -m*xOff-b) &
                        (yOff < h) &
                        (yOff > -h))[0]
                        
        if (len(index) < noffsets):
            print 'PROBLEM: not enough random points within the hexagon'
            print 'Need ', str(noffsets), 'but have only ', str(len(index)), 'points. Rerun with a different seed?'
        else:
            self.xOff = xOff[index[0:noffsets]]
            self.yOff = yOff[index[0:noffsets]]

    def run(self, simData):
        # Generate random numbers for dither, using defined seed value if desired.
        if self.randomSeed is not None:
            np.random.seed(self.randomSeed)
        # Add new columns to simData, ready to fill with new values.
        simData = self._addStackers(simData)
        # Generate the random dither values.
        noffsets = len(simData[self.raCol])
        self._generateRandomOffsets(noffsets)
        # Add to RA and dec values.
        simData['RandomDitherFieldPerVisitRA'] = simData[self.raCol] + self.xOff/np.cos(simData[self.decCol])
        simData['RandomDitherFieldPerVisitDec'] = simData[self.decCol] + self.yOff
        # Wrap back into expected range.
        simData['RandomDitherFieldPerVisitRA'], simData['RandomDitherFieldPerVisitDec'] = \
                                            wrapRADec(simData['RandomDitherFieldPerVisitRA'], simData['RandomDitherFieldPerVisitDec'])
        return simData

######################################################################################################
class RepulsiveRandomDitherFieldPerVisitStacker(BaseStacker):
    """
    Repulsive-randomly dither the RA and Dec pointings up to maxDither degrees from center, 
    different offset per visit for each field.
    """
    def __init__(self, raCol='fieldRA', decCol='fieldDec', maxDither=1.75, randomSeed=None):
        # Instantiate the RandomDither object and set internal variables.
        self.raCol = raCol
        self.decCol = decCol
        # Convert maxDither from degrees (internal units for ra/dec are radians)
        self.maxDither = np.radians(maxDither)
        self.randomSeed = randomSeed
        # self.units used for plot labels
        self.units = ['rad', 'rad']
        # Values required for framework operation: this specifies the names of the new columns.
        self.colsAdded = ['RepulsiveRandomDitherFieldPerVisitRA', 'RepulsiveRandomDitherFieldPerVisitDec']
        # Values required for framework operation: this specifies the data columns required from the database.
        self.colsReq = [self.raCol, self.decCol]

    def _generateRepRandomOffsets(self, noffsets):
        # Strategy: Tile the circumscribing square with squares. Discard those that fall outside the hexagon.
        # Then choose a square repulsive-randomly, and choose a random point from the chosen square.
        
        squareSide= self.maxDither*2   # circumscribing square. center at (0,0)
        numTiles= (np.ceil(np.sqrt(noffsets))+170)**2    # number of tiles. must be a perfect square.
        tileSide= squareSide/ np.sqrt(numTiles)

        xCenter= np.zeros(numTiles)   # x-coords of the tiles' center
        yCenter= np.zeros(numTiles)   # y-coords of the tiles' center

        # fill in x-coords
        k= 0
        xCenter[k]= -tileSide*((np.sqrt(numTiles)/2.0)-0.5)   # far left x-coord

        temparr= []
        temparr.append(k)
        while (k < (numTiles-1)):
            # fill xCoords for squares right above the x-axis
            if (k < (np.sqrt(numTiles)-1)):
                k+=1
                xCenter[k]= xCenter[k-1]+tileSide
                temparr.append(k)
            else:
                # fill xCoords for squares above/below the first layer of squares.
                for m in temparr:
                    k+=1
                    xCenter[k]= xCenter[m]
            
        # fill in the y-coords
        i= 0
        while (i<numTiles):
            # the highest y-center coord above the x-axis
            if (i==0):
                yCenter[i]= tileSide*((np.sqrt(numTiles)/2.0)-0.5)
            # y-centers below the top one
            else:
                yCenter[i]= yCenter[i-1]-tileSide

            i+=1
            # assign horiztonally adjacent squares the same yCenter
            for j in range(1,int(np.sqrt(numTiles))):
                yCenter[i]= yCenter[i-1]
                i+=1
        
        # set up the hexagon
        b= np.sqrt(3.0)*self.maxDither
        m= np.sqrt(3.0)
        h= self.maxDither*np.sqrt(3.0)/2.0
        
        # find the points that are inside hexagon
        insideHex= np.where((yCenter <= m*xCenter+b) &
                            (yCenter >= m*xCenter-b) &
                            (yCenter <= -m*xCenter+b) &
                            (yCenter >= -m*xCenter-b) &
                            (yCenter <= h) &
                            (yCenter >= -h))[0]  
        
        numPointsInsideHex= len(insideHex)
        print 'numPointsInsideHexagon: ', numPointsInsideHex
        #print 'numPointsOutsideHex: ', numTiles-len(insideHex)
        #print 'need offsets: ', noffsets
        print 'total squares chosen: ', len(xCenter)
        print 'Filling factor for repRandom (Number of points needed/Number of points in hexagon): ', float(noffsets)/numPointsInsideHex

        # if too few points, stop
        if (numPointsInsideHex < noffsets):
            print 'ERROR: Must increase the number of tiling squares, numTiles'
            stop

        # keep only the points that are insside the hexagon
        tempX= xCenter.copy()
        tempY= yCenter.copy()
        xCenter= []
        yCenter= []
        xCenter= list(tempX[insideHex])
        yCenter= list(tempY[insideHex])
        
        # initiate the offsets' array
        xOff= np.zeros(noffsets)
        yOff= np.zeros(noffsets)

        # randomly select a point from the insideHex points. assign a random offset from within that square and 
        # then delete it from insideHex array
        randNumsForLatticeSq= np.random.rand(noffsets*3)
        index_sq= 0    # index for randNumsForLatticeSq
    
        randNumsForPointInSq= np.random.rand(noffsets*2)
        index_pt= 0    # index for randNumsForPointInSq

        randIndex= -1
        
        for q in range(0, noffsets):
            randIndex= int(np.floor(randNumsForLatticeSq[index_sq]*numPointsInsideHex))

            if (randIndex > len(xCenter)-1):    # make sure randIndex access an entry in x/yCenter
                while (randIndex > len(xCenter)-1):  # keep choosing random index until get a valid one
                    index_sq += 1
                    if (index_sq > len(randNumsForLatticeSq)-1):
                        print 'Increase the length of randNumsForLatticeSq array'
                        stop
                randIndex= int(np.floor(randNumsForLatticeSq[index_sq]*numPointsInsideHex))
                index_sq += 1
            else:
                randIndex= int(np.floor(randNumsForLatticeSq[index_sq]*numPointsInsideHex))
                index_sq += 1

            # assign offsets
            xOff[q]= xCenter[randIndex]+(randNumsForPointInSq[index_pt]-0.5)*tileSide
            index_pt+=1
            yOff[q]= yCenter[randIndex]+(randNumsForPointInSq[index_pt]-0.5)*tileSide
            index_pt+=1

            # remove the chosen square to add the repulsion effect
            xCenter.remove(xCenter[randIndex])
            yCenter.remove(yCenter[randIndex])
            numPointsInsideHex-=1
      
        self.xOff = xOff
        self.yOff = yOff

    def run(self, simData):
        # Generate random numbers for dither, using defined seed value if desired.
        if self.randomSeed is not None:
            np.random.seed(self.randomSeed)
        # Add new columns to simData, ready to fill with new values.
        simData = self._addStackers(simData)
        # Generate the random dither values.
        noffsets = len(simData[self.raCol])
        self._generateRepRandomOffsets(noffsets)
        # Add to RA and dec values.
        simData['RepulsiveRandomDitherFieldPerVisitRA'] = simData[self.raCol] + self.xOff/np.cos(simData[self.decCol])
        simData['RepulsiveRandomDitherFieldPerVisitDec'] = simData[self.decCol] + self.yOff
        # Wrap back into expected range.
        simData['RepulsiveRandomDitherFieldPerVisitRA'], simData['RepulsiveRandomDitherFieldPerVisitDec'] = \
                                            wrapRADec(simData['RepulsiveRandomDitherFieldPerVisitRA'], simData['RepulsiveRandomDitherFieldPerVisitDec'])
        return simData

######################################################################################################
class SpiralDitherFieldPerVisitStacker(BaseStacker):
    """
    Offset along an equidistant spiral with numPoints, out to a maximum radius of maxDither.
    Sequential offset for each visit to a field.
    """
    def __init__(self, raCol='fieldRA', decCol='fieldDec', fieldIdCol='fieldID',
                 numPoints=60, maxDither=1.75, nCoils=5):
        self.raCol = raCol
        self.decCol = decCol
        self.fieldIdCol = fieldIdCol
        # Convert maxDither from degrees (internal units for ra/dec are radians)
        self.numPoints = numPoints
        self.nCoils = nCoils
        self.maxDither = np.radians(maxDither)
        # self.units used for plot labels
        self.units = ['rad', 'rad']
        # Values required for framework operation: this specifies the names of the new columns.
        self.colsAdded = ['SpiralDitherFieldPerVisitRA', 'SpiralDitherFieldPerVisitDec']
        # Values required for framework operation: this specifies the data columns required from the database.
        self.colsReq = [self.raCol, self.decCol, self.fieldIdCol]

    def _generateSpiralOffsets(self):
        # First generate a full archimedean spiral ..
        theta = np.arange(0.0001, self.nCoils*np.pi*2., 0.001)
        a = 0.85*self.maxDither/theta.max()
        r = theta*a
        # Then pick out equidistant points along the spiral.
        arc = a / 2.0 *(theta * np.sqrt(1 + theta**2) + np.log(theta + np.sqrt(1 + theta**2)))
        stepsize = arc.max()/float(self.numPoints)
        arcpts = np.arange(0, arc.max(), stepsize)
        arcpts = arcpts[0:self.numPoints]
        rpts = np.zeros(self.numPoints, float)
        thetapts = np.zeros(self.numPoints, float)
        for i, ap in enumerate(arcpts):
            diff = np.abs(arc - ap)
            match = np.where(diff == diff.min())[0]
            rpts[i] = r[match]
            thetapts[i] = theta[match]
        # Translate these r/theta points into x/y (ra/dec) offsets.
        self.xOff = rpts * np.cos(thetapts)
        self.yOff = rpts * np.sin(thetapts)

    def run(self, simData):
        # Add the new columns to simData.
        simData = self._addStackers(simData)
        # Generate the spiral offset vertices.
        self._generateSpiralOffsets()
        # Now apply to observations.
        for fieldid in np.unique(simData[self.fieldIdCol]):
            match = np.where(simData[self.fieldIdCol] == fieldid)[0]
            # Apply sequential dithers, increasing with each visit.
            vertexIdxs = np.arange(0, len(match), 1)
            vertexIdxs = vertexIdxs % self.numPoints
            simData['SpiralDitherFieldPerVisitRA'][match] = simData[self.raCol][match] + \
                                                                self.xOff[vertexIdxs]/np.cos(simData[self.decCol][match])
            simData['SpiralDitherFieldPerVisitDec'][match] = simData[self.decCol][match] + self.yOff[vertexIdxs]
        # Wrap into expected range.
        simData['SpiralDitherFieldPerVisitRA'], simData['SpiralDitherFieldPerVisitDec'] = \
                                        wrapRADec(simData['SpiralDitherFieldPerVisitRA'], simData['SpiralDitherFieldPerVisitDec'])
        return simData

######################################################################################################
class SequentialHexDitherFieldPerVisitStacker(BaseStacker):
    """
    Use offsets from the hexagonal grid of 'hexdither', but visit each vertex sequentially.
    Sequential offset for each visit to a field.
    """
    def __init__(self, raCol='fieldRA', decCol='fieldDec', fieldIdCol='fieldID', maxDither=1.75):
        self.raCol = raCol
        self.decCol = decCol
        self.fieldIdCol = fieldIdCol
        self.maxDither = np.radians(maxDither)
        # self.units used for plot labels
        self.units = ['rad', 'rad']
        # Values required for framework operation: this specifies the names of the new columns.
        self.colsAdded = ['SequentialHexDitherFieldPerVisitRA', 'SequentialHexDitherFieldPerVisitDec']
        # Values required for framework operation: this specifies the data columns required from the database.
        self.colsReq = [self.raCol, self.decCol, self.fieldIdCol]    #*********************************************

    def _generateHexOffsets(self):
        # Set up basics of dither pattern.
        dith_level = 4
        nrows = 2**dith_level
        halfrows = int(nrows/2.)
        # Calculate size of each offset
        dith_size_x = 0.95*self.maxDither*2.0/float(nrows)
        dith_size_y = 0.95*np.sqrt(3)*self.maxDither/float(nrows)  #sqrt 3 comes from hexagon
        # Calculate the row identification number, going from 0 at center
        nid_row = np.arange(-halfrows, halfrows+1, 1)
        # and calculate the number of vertices in each row.
        vert_in_row = np.arange(-halfrows, halfrows+1, 1)
        # First calculate how many vertices we will create in each row.
        total_vert = 0
        for i in range(-halfrows, halfrows+1, 1):
            vert_in_row[i] = (nrows+1) - abs(nid_row[i])
            total_vert += vert_in_row[i]
        self.numPoints = total_vert
        self.xOff = []
        self.yOff = []
        # Calculate offsets over hexagonal grid.
        for i in range(0, nrows+1, 1):
            for j in range(0, vert_in_row[i], 1):
                self.xOff.append(dith_size_x * (j - (vert_in_row[i]-1)/2.0))
                self.yOff.append(dith_size_y * nid_row[i])
        self.xOff = np.array(self.xOff)
        self.yOff = np.array(self.yOff)

    def run(self, simData):
        simData = self._addStackers(simData)
        self._generateHexOffsets()            
        for fieldid in np.unique(simData[self.fieldIdCol]):
            # Identify observations of this field.
            match = np.where(simData[self.fieldIdCol] == fieldid)[0]
            # Apply a sequential dither.
            vertexIdxs = np.arange(0, len(match), 1)
            # Apply sequential dithers, increasing with each visit.
            vertexIdxs = vertexIdxs % self.numPoints
            simData['SequentialHexDitherFieldPerVisitRA'][match] = simData[self.raCol][match] + \
                                                                       self.xOff[vertexIdxs]/np.cos(simData[self.decCol][match])
            simData['SequentialHexDitherFieldPerVisitDec'][match] = simData[self.decCol][match] + self.yOff[vertexIdxs]
        # Wrap into expected range.
        simData['SequentialHexDitherFieldPerVisitRA'], simData['SequentialHexDitherFieldPerVisitDec'] = \
                    wrapRADec(simData['SequentialHexDitherFieldPerVisitRA'], simData['SequentialHexDitherFieldPerVisitDec'])
        return simData

######################################################################################################
######################################################################################################
# Type 2
class RandomDitherFieldPerNightStacker(RandomDitherFieldPerVisitStacker):
    """
    Randomly dither the RA and Dec pointings up to maxDither degrees from center, one dither offset 
    per new night of observation of a field.
    """
    def __init__(self, raCol='fieldRA', decCol='fieldDec', fieldIdCol='fieldID', nightCol='night',
                 maxDither=1.75, randomSeed=None):
        # Instantiate the RandomDither object and set internal variables.
        super(RandomDitherFieldPerNightStacker, self).__init__(raCol=raCol, decCol=decCol,
                                                                   maxDither=maxDither, randomSeed=randomSeed)
        self.nightCol = nightCol
        self.fieldIdCol = fieldIdCol
        # Values required for framework operation: this specifies the names of the new columns.
        self.colsAdded = ['RandomDitherFieldPerNightRA', 'RandomDitherFieldPerNightDec']
        # Values required for framework operation: this specifies the data columns required from the database.
        self.colsReq.append(self.nightCol)
        self.colsReq.append(self.fieldIdCol)
        
    def run(self, simData):
        # Generate random numbers for dither, using defined seed value if desired.
        if self.randomSeed is not None:
            np.random.seed(self.randomSeed)
        # Add the new columns to simData.
        simData = self._addStackers(simData)

        # Generate the random dither values, one per night.
        self._generateRandomOffsets(len(simData[self.raCol]))

        delta= 0   # counter to ensure new random numbers are chosen every time
        for fieldid in np.unique(simData[self.fieldIdCol]):
            # Identify observations of this field.
            match = np.where(simData[self.fieldIdCol] == fieldid)[0]

            # Apply dithers, increasing each night.
            vertexIdxs = np.arange(0, len(match), 1)+delta
            delta= delta + len(vertexIdxs)   # ensure that the same xOff/yOff entries are not chosen
            nights = simData[self.nightCol][match]
            vertexIdxs = np.searchsorted(np.unique(nights), nights)
            vertexIdxs = vertexIdxs % len(self.xOff)            
            simData['RandomDitherFieldPerNightRA'][match] = simData[self.raCol][match] + \
                                                                self.xOff[vertexIdxs]/np.cos(simData[self.decCol][match])
            simData['RandomDitherFieldPerNightDec'][match] = simData[self.decCol][match] + self.yOff[vertexIdxs]
        # Wrap into expected range.
        simData['RandomDitherFieldPerNightRA'], simData['RandomDitherFieldPerNightDec'] = \
                                wrapRADec(simData['RandomDitherFieldPerNightRA'], simData['RandomDitherFieldPerNightDec'])
        return simData

######################################################################################################
class RepulsiveRandomDitherFieldPerNightStacker(RepulsiveRandomDitherFieldPerVisitStacker):
    """
    Repulsive-randomly dither the RA and Dec pointings up to maxDither degrees from center, one dither offset 
    per new night of observation of a field.
    """
    def __init__(self, raCol='fieldRA', decCol='fieldDec', fieldIdCol='fieldID', nightCol='night',
                 maxDither=1.75, randomSeed=None):
        # Instantiate the RandomDither object and set internal variables.
        super(RepulsiveRandomDitherFieldPerNightStacker, self).__init__(raCol=raCol, decCol=decCol,
                                                                   maxDither=maxDither, randomSeed=randomSeed)
        self.nightCol = nightCol
        self.fieldIdCol = fieldIdCol
        # Values required for framework operation: this specifies the names of the new columns.
        self.colsAdded = ['RepulsiveRandomDitherFieldPerNightRA', 'RepulsiveRandomDitherFieldPerNightDec']
        # Values required for framework operation: this specifies the data columns required from the database.
        self.colsReq.append(self.nightCol)
        self.colsReq.append(self.fieldIdCol)
        
    def run(self, simData):
        # Generate random numbers for dither, using defined seed value if desired.
        if self.randomSeed is not None:
            np.random.seed(self.randomSeed)
        # Add the new columns to simData.
        simData = self._addStackers(simData)

        # Generate the random dither values, one per night.
        self._generateRepRandomOffsets(len(simData[self.raCol]))

        delta= 0   # counter to ensure new random numbers are chosen every time
        for fieldid in np.unique(simData[self.fieldIdCol]):
            # Identify observations of this field.
            match = np.where(simData[self.fieldIdCol] == fieldid)[0]

            # Apply dithers, increasing each night.
            vertexIdxs = np.arange(0, len(match), 1)+delta
            delta= delta + len(vertexIdxs)   # ensure that the same xOff/yOff entries are not chosen
            nights = simData[self.nightCol][match]
            vertexIdxs = np.searchsorted(np.unique(nights), nights)
            vertexIdxs = vertexIdxs % len(self.xOff)            
            simData['RepulsiveRandomDitherFieldPerNightRA'][match] = simData[self.raCol][match] + \
                                                                self.xOff[vertexIdxs]/np.cos(simData[self.decCol][match])
            simData['RepulsiveRandomDitherFieldPerNightDec'][match] = simData[self.decCol][match] + self.yOff[vertexIdxs]
        # Wrap into expected range.
        simData['RepulsiveRandomDitherFieldPerNightRA'], simData['RepulsiveRandomDitherFieldPerNightDec'] = \
                                wrapRADec(simData['RepulsiveRandomDitherFieldPerNightRA'], simData['RepulsiveRandomDitherFieldPerNightDec'])
        return simData

######################################################################################################
class SpiralDitherFieldPerNightStacker(SpiralDitherFieldPerVisitStacker):
    """
    Offset along an equidistant spiral with numPoints, out to a maximum radius of maxDither.
    Sequential offset for each new night of observation of a field.
    """
    def __init__(self, raCol='fieldRA', decCol='fieldDec', fieldIdCol='fieldID', nightCol='night',
                 numPoints=60, maxDither=1.75, nCoils=5):
        super(SpiralDitherFieldPerNightStacker, self).__init__(raCol=raCol, decCol=decCol, fieldIdCol=fieldIdCol,
                                                         numPoints=numPoints, maxDither=maxDither, nCoils=nCoils)
        self.nightCol = nightCol
        # Values required for framework operation: this specifies the names of the new columns.
        self.colsAdded = ['SpiralDitherFieldPerNightRA', 'SpiralDitherFieldPerNightDec']
        # Values required for framework operation: this specifies the data columns required from the database.
        self.colsReq.append(self.nightCol)

    def run(self, simData):
        simData = self._addStackers(simData)
        self._generateSpiralOffsets()
        for fieldid in np.unique(simData[self.fieldIdCol]):
            # Identify observations of this field.
            match = np.where(simData[self.fieldIdCol] == fieldid)[0]
            # Apply a sequential dither, increasing each night.
            vertexIdxs = np.arange(0, len(match), 1)
            nights = simData[self.nightCol][match]
            vertexIdxs = np.searchsorted(np.unique(nights), nights)
            vertexIdxs = vertexIdxs % self.numPoints
            simData['SpiralDitherFieldPerNightRA'][match] = simData[self.raCol][match] + \
                                                                self.xOff[vertexIdxs]/np.cos(simData[self.decCol][match])
            simData['SpiralDitherFieldPerNightDec'][match] = simData[self.decCol][match] + self.yOff[vertexIdxs]
        # Wrap into expected range.
        simData['SpiralDitherFieldPerNightRA'], simData['SpiralDitherFieldPerNightDec'] = \
                    wrapRADec(simData['SpiralDitherFieldPerNightRA'],  simData['SpiralDitherFieldPerNightDec'])
        return simData

######################################################################################################   
class SequentialHexDitherFieldPerNightStacker(SequentialHexDitherFieldPerVisitStacker):
    """
    Use offsets from the hexagonal grid of 'hexdither', but visit each vertex sequentially.
    Sequential offset for every new night of observation of a field.
    """
    def __init__(self, raCol='fieldRA', decCol='fieldDec', fieldIdCol='fieldID', nightCol='night', maxDither=1.75):
        super(SequentialHexDitherFieldPerNightStacker, self).__init__(raCol=raCol, decCol=decCol, fieldIdCol=fieldIdCol, maxDither=maxDither) #***************
        self.nightCol = nightCol
        # Values required for framework operation: this specifies the names of the new columns.
        self.colsAdded = ['SequentialHexDitherFieldPerNightRA', 'SequentialHexDitherFieldPerNightDec']
        # Values required for framework operation: this specifies the data columns required from the database.
        self.colsReq.append(self.nightCol)

    def run(self, simData):
        simData = self._addStackers(simData)
        self._generateHexOffsets()
        for fieldid in np.unique(simData[self.fieldIdCol]):
            # Identify observations of this field.
            match = np.where(simData[self.fieldIdCol] == fieldid)[0]
            # Apply a sequential dither, increasing each night.
            vertexIdxs = np.arange(0, len(match), 1)
            nights = simData[self.nightCol][match]
            vertexIdxs = np.searchsorted(np.unique(nights), nights)
            vertexIdxs = vertexIdxs % self.numPoints
            simData['SequentialHexDitherFieldPerNightRA'][match] = simData[self.raCol][match] + \
                                                                       self.xOff[vertexIdxs]/np.cos(simData[self.decCol][match])
            simData['SequentialHexDitherFieldPerNightDec'][match] = simData[self.decCol][match] + self.yOff[vertexIdxs]
        # Wrap into expected range.
        simData['SequentialHexDitherFieldPerNightRA'], simData['SequentialHexDitherFieldPerNightDec'] = \
          wrapRADec(simData['SequentialHexDitherFieldPerNightRA'], simData['SequentialHexDitherFieldPerNightDec'])
        return simData

######################################################################################################
######################################################################################################    
# Type 3
class RandomDitherPerNightStacker(RandomDitherFieldPerVisitStacker):
    """
    Randomly dither the RA and Dec pointings up to maxDither degrees from center, one dither offset 
    per night for all the fields.
    """
    def __init__(self, raCol='fieldRA', decCol='fieldDec', nightCol='night', maxDither=1.75, randomSeed=None):
        # Instantiate the RandomDither object and set internal variables.
        self.raCol = raCol
        self.decCol = decCol
        self.nightCol = nightCol
        # Convert maxDither from degrees (internal units for ra/dec are radians)
        self.maxDither = np.radians(maxDither)
        self.randomSeed = randomSeed
        # self.units used for plot labels
        self.units = ['rad', 'rad']
        # Values required for framework operation: this specifies the names of the new columns.
        self.colsAdded = ['RandomDitherPerNightRA', 'RandomDitherPerNightDec']
        # Values required for framework operation: this specifies the data columns required from the database.
        self.colsReq = [self.raCol, self.decCol, self.nightCol]

    def run(self, simData):
        # Generate random numbers for dither, using defined seed value if desired.
        if self.randomSeed is not None:
            np.random.seed(self.randomSeed)
        # Add the new columns to simData.
        simData = self._addStackers(simData)
        # Generate the random dither values, one per night.
        nights = np.unique(simData[self.nightCol])
        self._generateRandomOffsets(len(nights))
        # Add to RA and dec values.
        for n, x, y in zip(nights, self.xOff, self.yOff):
            match = np.where(simData[self.nightCol] == n)[0]
            simData['RandomDitherPerNightRA'][match] = simData[self.raCol][match] + x/np.cos(simData[self.decCol][match])
            simData['RandomDitherPerNightDec'][match] = simData[self.decCol][match] + y
        # Wrap RA/Dec into expected range.
        simData['RandomDitherPerNightRA'], simData['RandomDitherPerNightDec'] = \
                wrapRADec(simData['RandomDitherPerNightRA'], simData['RandomDitherPerNightDec'])
        return simData

######################################################################################################
class RepulsiveRandomDitherPerNightStacker(RepulsiveRandomDitherFieldPerVisitStacker):
    """
    Repulsive-randomly dither the RA and Dec pointings up to maxDither degrees from center, one dither offset 
    per night for all the fields.
    """
    def __init__(self, raCol='fieldRA', decCol='fieldDec', nightCol='night', maxDither=1.75, randomSeed=None):
        # Instantiate the RandomDither object and set internal variables.
        self.raCol = raCol
        self.decCol = decCol
        self.nightCol = nightCol
        # Convert maxDither from degrees (internal units for ra/dec are radians)
        self.maxDither = np.radians(maxDither)
        self.randomSeed = randomSeed
        # self.units used for plot labels
        self.units = ['rad', 'rad']
        # Values required for framework operation: this specifies the names of the new columns.
        self.colsAdded = ['RepulsiveRandomDitherPerNightRA', 'RepulsiveRandomDitherPerNightDec']
        # Values required for framework operation: this specifies the data columns required from the database.
        self.colsReq = [self.raCol, self.decCol, self.nightCol]

    def run(self, simData):
        # Generate random numbers for dither, using defined seed value if desired.
        if self.randomSeed is not None:
            np.random.seed(self.randomSeed)
        # Add the new columns to simData.
        simData = self._addStackers(simData)
        # Generate the random dither values, one per night.
        nights = np.unique(simData[self.nightCol])
        self._generateRepRandomOffsets(len(nights))
        # Add to RA and dec values.
        for n, x, y in zip(nights, self.xOff, self.yOff):
            match = np.where(simData[self.nightCol] == n)[0]
            simData['RepulsiveRandomDitherPerNightRA'][match] = simData[self.raCol][match] + x/np.cos(simData[self.decCol][match])
            simData['RepulsiveRandomDitherPerNightDec'][match] = simData[self.decCol][match] + y
        # Wrap RA/Dec into expected range.
        simData['RepulsiveRandomDitherPerNightRA'], simData['RepulsiveRandomDitherPerNightDec'] = \
                wrapRADec(simData['RepulsiveRandomDitherPerNightRA'], simData['RepulsiveRandomDitherPerNightDec'])
        return simData

######################################################################################################
class SpiralDitherPerNightStacker(SpiralDitherFieldPerVisitStacker):
    """
    Offset along an equidistant spiral with numPoints, out to a maximum radius of maxDither.
    Sequential offset per night for all fields.
    """
    def __init__(self, raCol='fieldRA', decCol='fieldDec', fieldIdCol='fieldID', nightCol='night',
                 numPoints=60, maxDither=1.75, nCoils=5):
        super(SpiralDitherPerNightStacker, self).__init__(raCol=raCol, decCol=decCol, fieldIdCol=fieldIdCol,
                                                         numPoints=numPoints, maxDither=maxDither, nCoils=nCoils)
        self.nightCol = nightCol
        # Values required for framework operation: this specifies the names of the new columns.
        self.colsAdded = ['SpiralDitherPerNightRA', 'SpiralDitherPerNightDec']
        # Values required for framework operation: this specifies the data columns required from the database.
        self.colsReq.append(self.nightCol)

    def run(self, simData):
        simData = self._addStackers(simData)
        self._generateSpiralOffsets()

        nights = np.unique(simData[self.nightCol])
        # Add to RA and dec values.
        vertexID= 0
        for n in nights:
            match = np.where(simData[self.nightCol] == n)[0]
            vertexID= vertexID % self.numPoints
            
            simData['SpiralDitherPerNightRA'][match] = simData[self.raCol][match] + self.xOff[vertexID]/np.cos(simData[self.decCol][match])
            simData['SpiralDitherPerNightDec'][match] = simData[self.decCol][match] + self.yOff[vertexID]
            vertexID += 1
        # Wrap RA/Dec into expected range.
        simData['SpiralDitherPerNightRA'], simData['SpiralDitherPerNightDec'] = \
                            wrapRADec(simData['SpiralDitherPerNightRA'],simData['SpiralDitherPerNightDec'])
        return simData

######################################################################################################    
class SequentialHexDitherPerNightStacker(SequentialHexDitherFieldPerVisitStacker):
    """
    Use offsets from the hexagonal grid of 'hexdither', but visit each vertex sequentially.
    Sequential offset per night for all fields.
    """
    def __init__(self, raCol='fieldRA', decCol='fieldDec', fieldIdCol='fieldID', nightCol='night', maxDither=1.75):
        super(SequentialHexDitherPerNightStacker, self).__init__(raCol=raCol, decCol=decCol, fieldIdCol=fieldIdCol, maxDither=maxDither)
        self.nightCol = nightCol
        # Values required for framework operation: this specifies the names of the new columns.
        self.colsAdded = ['SequentialHexDitherPerNightRA', 'SequentialHexDitherPerNightDec']
        # Values required for framework operation: this specifies the data columns required from the database.
        self.colsReq.append(self.nightCol)
    
    def run(self, simData):
        # Add the new columns to simData.
        simData = self._addStackers(simData)
        # Generate the spiral dither values
        self._generateHexOffsets()

        nights = np.unique(simData[self.nightCol])
        # Add to RA and dec values.
        vertexID= 0
        for n in nights:
            match = np.where(simData[self.nightCol] == n)[0]
            vertexID= vertexID % self.numPoints
            simData['SequentialHexDitherPerNightRA'][match] = simData[self.raCol][match] + self.xOff[vertexID]/np.cos(simData[self.decCol][match])
            simData['SequentialHexDitherPerNightDec'][match] = simData[self.decCol][match] + self.yOff[vertexID]
            vertexID += 1
        # Wrap RA/Dec into expected range.
        simData['SequentialHexDitherPerNightRA'], simData['SequentialHexDitherPerNightDec'] = \
                            wrapRADec(simData['SequentialHexDitherPerNightRA'],simData['SequentialHexDitherPerNightDec'])
        return simData

######################################################################################################
######################################################################################################
# Type 4
class PentagonDitherFieldPerSeasonStacker(BaseStacker):
    """
    Offset along two pentagons, one inverted and inside the other.
    Sequential offset for each field on a visit in new season.
    """
    def __init__(self, raCol='fieldRA', decCol='fieldDec',
                 fieldIdCol='fieldID', expMJDCol= 'expMJD', maxDither= 1.75):
        self.raCol = raCol
        self.decCol = decCol
        self.fieldIdCol = fieldIdCol
        self.expMJDCol= expMJDCol
        # Convert maxDither from degrees (internal units for ra/dec are radians)
        self.maxDither = np.radians(maxDither)
        # self.units used for plot labels
        self.units = ['rad', 'rad']
        # Values required for framework operation: this specifies the names of the new columns.
        self.colsAdded = ['PentagonDitherFieldPerSeasonRA', 'PentagonDitherFieldPerSeasonDec']
        # Values required for framework operation: this specifies the data columns required from the database.
        self.colsReq = [self.raCol, self.decCol, self.fieldIdCol, self.expMJDCol]
            
    def _generatePentagonOffsets(self):
        # inner pentagon tuples
        nside= 5
        inner= polygonCoords(nside, self.maxDither/2.5, 0.0)
        # outer pentagon tuples
        outerTemp= polygonCoords(nside, self.maxDither/1.3, np.pi)
        # reorder outer tuples' order
        outer= []
        outer[0:3]= outerTemp[2:5]
        outer[4:6]= outerTemp[0:2]
        # join inner and outer coordiantes' array
        self.xOff= np.concatenate((zip(*inner)[0],zip(*outer)[0]), axis=0)
        self.yOff= np.concatenate((zip(*inner)[1],zip(*outer)[1]), axis=0)

    def run(self, simData):
        # find the seasons associated with each visit.
        seasonSimData= SeasonStacker().run(simData)
        seasons= seasonSimData['season']

        # check how many entries in the >10 season
        ind= np.where(seasons > 9)[0]
        print 'Seasons to wrap ', np.unique(seasons[ind])
        # should be only 1 extra seasons ..
        if len(np.unique(seasons[ind])) > 1:
            print 'ERROR: Too many seasons'
            stop
        # wrap the season around: 10th == 0th
        seasons[ind]= seasons[ind]%10
                
        # Add the new columns to simData.
        simData = self._addStackers(simData)
        # Generate the spiral offset vertices.
        self._generatePentagonOffsets()
        
        # Now apply to observations.
        for fieldid in np.unique(simData[self.fieldIdCol]):
            match = np.where(simData[self.fieldIdCol] == fieldid)[0]
            seasonsVisited = seasons[match]
            # Apply sequential dithers, increasing with each season.
            vertexIdxs = np.searchsorted(np.unique(seasonsVisited), seasonsVisited)
            vertexIdxs = vertexIdxs % len(self.xOff)
            simData['PentagonDitherFieldPerSeasonRA'][match] = simData[self.raCol][match] + \
              self.xOff[vertexIdxs]/np.cos(simData[self.decCol][match])
            simData['PentagonDitherFieldPerSeasonDec'][match] = simData[self.decCol][match] + self.yOff[vertexIdxs]
        # Wrap into expected range.
        simData['PentagonDitherFieldPerSeasonRA'], simData['PentagonDitherFieldPerSeasonDec'] = \
                                        wrapRADec(simData['PentagonDitherFieldPerSeasonRA'], simData['PentagonDitherFieldPerSeasonDec'])
        return simData

######################################################################################################
class PentagonDiamondDitherFieldPerSeasonStacker(BaseStacker):
    """
    Offset along a diamond circumscribed by a pentagon.
    Sequential offset for each field on a visit in new season.
    """
    def __init__(self, raCol='fieldRA', decCol='fieldDec',
                 fieldIdCol='fieldID', expMJDCol= 'expMJD', maxDither= 1.75):
        self.raCol = raCol
        self.decCol = decCol
        self.fieldIdCol = fieldIdCol
        self.expMJDCol= expMJDCol
        # Convert maxDither from degrees (internal units for ra/dec are radians)
        self.maxDither = np.radians(maxDither)
        # self.units used for plot labels
        self.units = ['rad', 'rad']
        # Values required for framework operation: this specifies the names of the new columns.
        self.colsAdded = ['PentagonDiamondDitherFieldPerSeasonRA', 'PentagonDiamondDitherFieldPerSeasonDec']
        # Values required for framework operation: this specifies the data columns required from the database.
        self.colsReq = [self.raCol, self.decCol, self.fieldIdCol, self.expMJDCol]

           
    def _generateOffsets(self):
        # outer pentagon tuples
        pentCoord= polygonCoords(5,self.maxDither/1.3, 0)
        # inner diamond tuples
        diamondCoord= polygonCoords(4, self.maxDither/2.5, np.pi/2)

        # join inner and outer coordiantes' array + a point in the middle (origin)
        self.xOff= np.concatenate(([0],zip(*diamondCoord)[0],zip(*pentCoord)[0]), axis=0)
        self.yOff= np.concatenate(([0],zip(*diamondCoord)[1],zip(*pentCoord)[1]), axis=0)

    def run(self, simData):
        # find the seasons associated with each visit.
        seasonSimData= SeasonStacker().run(simData)
        seasons= seasonSimData['season']

        # check how many entries in the >10 season
        ind= np.where(seasons > 9)[0]
        print 'Seasons to wrap ', np.unique(seasons[ind])
        # should be only 1 extra seasons ..
        if len(np.unique(seasons[ind])) > 1:
            print 'ERROR: Too many seasons'
            stop
        # wrap the season around: 10th == 0th
        seasons[ind]= seasons[ind]%10
            
        # Add the new columns to simData.
        simData = self._addStackers(simData)
        # Generate the spiral offset vertices.
        self._generateOffsets()
        
        # Now apply to observations.
        for fieldid in np.unique(simData[self.fieldIdCol]):
            match = np.where(simData[self.fieldIdCol] == fieldid)[0]
            seasonsVisited = seasons[match]    
            # Apply sequential dithers, increasing with each season.
            vertexIdxs = np.searchsorted(np.unique(seasonsVisited), seasonsVisited)
            vertexIdxs = vertexIdxs % len(self.xOff)
            simData['PentagonDiamondDitherFieldPerSeasonRA'][match] = simData[self.raCol][match] + \
              self.xOff[vertexIdxs]/np.cos(simData[self.decCol][match])
            simData['PentagonDiamondDitherFieldPerSeasonDec'][match] = simData[self.decCol][match] + self.yOff[vertexIdxs]
        # Wrap into expected range.
        simData['PentagonDiamondDitherFieldPerSeasonRA'], simData['PentagonDiamondDitherFieldPerSeasonDec'] = \
                                                          wrapRADec(simData['PentagonDiamondDitherFieldPerSeasonRA'],
                                                                    simData['PentagonDiamondDitherFieldPerSeasonDec'])
        return simData

######################################################################################################
######################################################################################################
class PentagonDitherPerSeasonStacker(PentagonDitherFieldPerSeasonStacker):
    """
    Offset along two pentagons, one inverted and inside the other.
    Sequential offset for all fields every season.
    """
    def __init__(self, raCol='fieldRA', decCol='fieldDec',
                 fieldIdCol='fieldID', expMJDCol= 'expMJD', maxDither= 1.75):
        super(PentagonDitherPerSeasonStacker, self).__init__(raCol=raCol, decCol=decCol,
                                                                       fieldIdCol=fieldIdCol, expMJDCol=expMJDCol, maxDither=maxDither)
        # Values required for framework operation: this specifies the names of the new columns.
        self.colsAdded = ['PentagonDitherPerSeasonRA', 'PentagonDitherPerSeasonDec']
   
    def run(self, simData):
        # find the seasons associated with each visit.
        seasonSimData= SeasonStacker().run(simData)
        seasons= seasonSimData['season']
        years= seasonSimData['year']
        
        # check how many entries in the >10 season
        ind= np.where(seasons > 9)[0]
        print 'Seasons to wrap ', np.unique(seasons[ind]), 'with total entries: ', len(seasons[ind])
        # should be only 1 extra seasons ..
        #if len(np.unique(seasons[ind])) > 1:
        #    print 'ERROR: Too many seasons'
        #    stop
        # wrap the season around: 10th == 0th
        seasons[ind]= seasons[ind]%10

        # Add the new columns to simData.
        simData = self._addStackers(simData)
        # Generate the spiral offset vertices.
        self._generatePentagonOffsets()

        print 'Total visits for all fields:', len(seasons)
        print ''
        # for debugging; fill dithered as non-dithered
        #simData['PentagonDitherPerSeasonRA'] = simData[self.raCol]
        #simData['PentagonDitherPerSeasonDec'] = simData[self.decCol]

        
        # Add to RA and dec values.
        vertexID= 0
        for s in np.unique(seasons):
            #match = np.where((seasons == s) & (years == 5))[0]   # for debugging purposes; check only the first year's data.
            match = np.where(seasons == s)[0]

            # print details
            print 'season', s
            print 'numEntries ', len(match), '; ', float(len(match))/len(seasons)*100, '% of total'
            matchYears= np.unique(years[match])
            print 'Corresponding years: ', matchYears
            for i in matchYears:
                print '     Entries in year', i, ': ', len(np.where(i == years[match])[0])    
            print ''
            
            vertexID= vertexID %  len(self.xOff)
            simData['PentagonDitherPerSeasonRA'][match] = simData[self.raCol][match] + self.xOff[vertexID]/np.cos(simData[self.decCol][match])
            simData['PentagonDitherPerSeasonDec'][match] = simData[self.decCol][match] + self.yOff[vertexID]
            vertexID += 1

        # Wrap into expected range.
        simData['PentagonDitherPerSeasonRA'], simData['PentagonDitherPerSeasonDec'] = \
                                        wrapRADec(simData['PentagonDitherPerSeasonRA'], simData['PentagonDitherPerSeasonDec'])
        return simData

######################################################################################################
class PentagonDiamondDitherPerSeasonStacker(PentagonDiamondDitherFieldPerSeasonStacker):
    """
    Offset along a diamond circumscribed by a pentagon.
    Sequential offset for all fields every season.
    """
    def __init__(self, raCol='fieldRA', decCol='fieldDec',
                 fieldIdCol='fieldID', expMJDCol= 'expMJD', maxDither= 1.75):
        super(PentagonDiamondDitherPerSeasonStacker, self).__init__(raCol=raCol, decCol=decCol,
                                                                       fieldIdCol=fieldIdCol, expMJDCol=expMJDCol, maxDither=maxDither)
        # Values required for framework operation: this specifies the names of the new columns.
        self.colsAdded = ['PentagonDiamondDitherPerSeasonRA', 'PentagonDiamondDitherPerSeasonDec']
   
    def run(self, simData):
        # find the seasons associated with each visit.
        seasonSimData= SeasonStacker().run(simData)
        seasons= seasonSimData['season']
        
        # check how many entries in the >10 season
        ind= np.where(seasons > 9)[0]
        print 'Seasons to wrap ', np.unique(seasons[ind])
        # should be only 1 extra seasons ..
        if len(np.unique(seasons[ind])) > 1:
            print 'ERROR: Too many seasons'
            stop
        # wrap the season around: 10th == 0th
        seasons[ind]= seasons[ind]%10
        
        # Add the new columns to simData.
        simData = self._addStackers(simData)
        # Generate the spiral offset vertices.
        self._generateOffsets()

        uniqSeasons = np.unique(seasons)
        # Add to RA and dec values.
        vertexID= 0
        for s in uniqSeasons:
            match = np.where(seasons == s)[0]
            vertexID= vertexID %  len(self.xOff)
            simData['PentagonDiamondDitherPerSeasonRA'][match] = simData[self.raCol][match] + self.xOff[vertexID]/np.cos(simData[self.decCol][match])
            simData['PentagonDiamondDitherPerSeasonDec'][match] = simData[self.decCol][match] + self.yOff[vertexID]
            vertexID += 1

        # Wrap into expected range.
        simData['PentagonDiamondDitherPerSeasonRA'], simData['PentagonDiamondDitherPerSeasonDec'] = \
                                        wrapRADec(simData['PentagonDiamondDitherPerSeasonRA'],
                                                  simData['PentagonDiamondDitherPerSeasonDec'])
        return simData


    
