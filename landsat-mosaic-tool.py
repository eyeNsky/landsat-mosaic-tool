"""
MIT License

Copyright (c) 2016 Jon Sellars

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

Please see Exiftool, Gnu Parallel and Enblend for their license.

http://www.sno.phy.queensu.ca/~phil/exiftool/
https://www.gnu.org/software/parallel/
http://enblend.sourceforge.net/index.htm

.ExifTool_config has to be in place for exiftool to write the custom tags.

Expects the output from prep-mosiac.py. Specifically that mismarked pixels in the alpha channel have been set to
black.


"""
import os,glob
from xml.dom.minidom import parse
from osgeo import gdal

blur = '0x4'

# This will compress the original tif after processing.
# If space is really tight, delete original
spaceIsTight = False

# Set up directories
if not os.path.isdir('final'):
    os.mkdir('final')
if not os.path.isdir('big-blur'):
    os.mkdir('big-blur')
if not os.path.isdir('little-blur'):
    os.mkdir('little-blur')
if not os.path.isdir('corr'):
    os.mkdir('corr')
#############################################################################
# Switches for exiftool and enblend
exifSw = 'exiftool -overwrite_original_in_place -ResolutionUnit=inches -XPosition=%s -YPosition=%s -XResolution=1 -YResolution=1 %s'
enblendSw = 'enblend -f %sx%s --no-optimize -a -o ../big-blur/%s.tif LC*.tif'
# 
#############################################################################
# got to have this at ~/.ExifTool_config
def exifToolsConfig():
	etConfig ="""%Image::ExifTool::UserDefined = (
    # All EXIF tags are added to the Main table, and WriteGroup is used to
    # specify where the tag is written (default is ExifIFD if not specified):
    'Image::ExifTool::Exif::Main' => {
        0xd000 => {
            Name => 'XResolution',
            Writable => 'int16u',
        },{
            Name => 'YResolution',
            Writable => 'int16u',
        },{
            Name => 'XPosition',
            Writable => 'int16u',
        },{
            Name => 'YPosition',
            Writable => 'int16u',
        },{
            Name => 'ResolutionUnit',
            Writable => 'int16u',
        }
        # add more user-defined EXIF tags here...
    },
);
print "LOADED!\n";"""
	return etConfig
#############################################################################
def procTifs():
	if not os.path.isdir('scanline'):
		os.mkdir('scanline')
	transSw()

def transSw():
	# check on making scanline width 78 to match nona 
	os.chdir('scanline')
	#basename = os.path.basename(img).split('.')[0]
	print "Parallel Warp"
	#parallelWarp = ('ls ../*.tif | parallel gdalwarp -of VRT  -dstalpha -co ALPHA=YES -srcnodata "0" -dstnodata "0" {} {/.}.vrt')
	#parallelWarp = ('ls ../*.tif | parallel gdalwarp -of VRT -srcnodata "0" -dstnodata "0" {} {/.}.vrt')
	#os.system(parallelWarp)
	print "Parallel Translate"
	parallelTrans = ('''ls ../*.tif | parallel 'gdal_translate -outsize 20%% 20%% -co BLOCKYSIZE=78 -a_nodata "0 0 0" -co TFW=YES {} {/.}.tif' ''')
	os.system(parallelTrans)
	os.chdir('../')

def makeVrt(vrt):
	vrtSw = 'gdalbuildvrt %s.vrt *.tif' % (vrt)
	os.system(vrtSw)

def parseVrt(vrt):
	vrtBasename = os.path.basename(vrt).split('.')[0]
	enList = '%s.list' % vrtBasename
	enListFile = open(vrtBasename+'.list','w')
	vrtInfo = parse(vrt)
	GeoTransform = vrtInfo.getElementsByTagName('GeoTransform')
	for gt in GeoTransform:
		geot = gt.firstChild.data.split(',')
		pixelX = float(geot[1])
		pixelY = float(geot[5])
		# Get ULX,ULY
		ULX = float(geot[0]) + (pixelX/2)
		ULY = float(geot[3]) + (pixelY/2)
        tfw = open(vrtBasename+'.tfw','w')
        tfwTxt = '%s\n0\n0\n%s\n%s\n%s' % (pixelX,pixelY,ULX,ULY)
        tfw.write(tfwTxt)
        tfw.close()	

	VRTDataset = vrtInfo.getElementsByTagName('VRTDataset')
	for (name,value) in VRTDataset[0].attributes.items():
		if name == 'rasterXSize':
			rasterXSize = value
		if name == 'rasterYSize':
			rasterYSize = value
	print 'Mosaic size is:' ,rasterXSize, rasterYSize		
	band1 = vrtInfo.getElementsByTagName('VRTRasterBand')[0]
	sources = band1.getElementsByTagName('SimpleSource')
	if len(sources) == 0:
		sources = band1.getElementsByTagName('ComplexSource')
	
	for source in sources:
		SourceFilename = source.getElementsByTagName('SourceFilename')
		for node in SourceFilename:
			image_id = node.firstChild.data
			imageListTxt = '%s\n'%image_id
			enListFile.write(imageListTxt)
		SrcRect = source.getElementsByTagName('SrcRect')
		DstRect = source.getElementsByTagName('DstRect')
		loop = 0
		for (name, value) in DstRect[loop].attributes.items():
			#print name,value
			if name == 'xSize': # image width
				xSize = value
			if name == 'ySize': # image height
				ySize = value
			if name == 'xOff':  # x offset into mosaic
				xOff = value
			if name == 'yOff':  # y offset into mosaic
				yOff = value
		print 'adding exif to %s' % image_id		
		addExif = exifSw % (xOff,yOff,image_id)
		# this step writes .sh to pass to parallel
		#os.system(addExif)
		exif_sh = open('exif-%s.sh'%image_id,'w')
		exif_sh.write(addExif)
	enListFile.close() 
	return rasterXSize, rasterYSize, enList, vrtBasename,pixelX,pixelY,ULX,ULY

def calcImgExt(img):
    dataset = gdal.Open(img)
    # get epsg code
    try:
        epsg = dataset.GetProjectionRef().split(',')[-1].split('"')[1]
    except:
        epsg = 0
        #print dataset.GetDescription(),'has no projection'
    geot = dataset.GetGeoTransform()
    # Get image height width and heigth in pixels
    rastX = dataset.RasterXSize
    rastY = dataset.RasterYSize
    # Get pixel sizes
    pixelX = geot[1]
    pixelY = geot[5]
    # Get ULX,ULY
    ULX = geot[0]
    ULY = geot[3]
    # Calculate URX,LRY
    URX = ULX+(pixelX * rastX)
    LRY = ULY+(pixelY * rastY)
    dataset = None
    #bboxSize = ULX,LRY,URX,ULY,rastX,rastY,pixelX,pixelY
    #return bboxSize
    return pixelX,rastX,rastY,ULX,LRY,URX,ULY

def wldTemplate():
	'''Template for worldfiles'''
	wt = '''%s\n0\n0\n-%s\n%s\n%s'''
	return wt

procTifs()
os.chdir('scanline')
makeVrt('mosaic')
vrtIn = 'mosaic.vrt'
mosaicXSize, mosaicYSize, mosaicList, mosaicBasename,mosaicPixelX,mosaicPixelY,mosaicULX,mosaicULY = parseVrt(vrtIn)
mosaicLRX = mosaicULX + (int(mosaicXSize)*mosaicPixelX)
mosaicLRY = mosaicULY + (int(mosaicYSize)*mosaicPixelY)
# int the corners
mosaicLRX = int(mosaicLRX)
mosaicLRY = int(mosaicLRY)
mosaicULX = int(mosaicULX)
mosaicULY = int(mosaicULY)
# process the exif cmds
exifProc = 'ls exif*.sh | parallel bash {}'
os.system(exifProc)
os.system('rm exif*.sh')
# Create reducted resolution mosaic of all input images
enblendCmd = enblendSw % ( mosaicXSize, mosaicYSize, mosaicBasename )

os.system(enblendCmd)
os.system('cp mosaic.tfw ../big-blur')
os.chdir('../')

# ccfm-> closest to center feathered mosaic
ccfm = glob.glob('big-blur/mos*.tif')
for mos_fm in ccfm:
	mosResolution,fmRasterXSize,fmRasterYSize,fmULX,fmLRY,fmURX,fmULY = calcImgExt(mos_fm)
	basename = os.path.basename(mos_fm).replace('.tif','')
	# Blur this feathered mosaic 
	imBlurBigMos = 'convert %s -blur %s - | convert - \( %s -channel a -separate +channel \) -alpha off -compose copy_opacity -composite big-blur/%s.png' % (mos_fm,blur,mos_fm,basename)
	wldCmd = wldTemplate()%(mosResolution,mosResolution,fmULX,fmULY)
	mvWldCmd = open('big-blur/%s.pgw' % (basename),'w')
	mvWldCmd.write(wldCmd)
	mvWldCmd.close()
	shCmd = open(('%s.sh'%basename),'w')
	shCmd.write(imBlurBigMos)
	shCmd.close()
parallelCmd = 'ls mos*.sh | parallel bash {}'
os.system(parallelCmd)
os.system('rm mos*.sh')	

makeMosFmVrt = 'gdalbuildvrt -srcnodata "0 0 0" mosFM.vrt big-blur/*.png'
os.system(makeMosFmVrt)
mos_tifs = glob.glob('*.tif')
for mos_tif in mos_tifs:
	args = {}
	pixelX,RasterXSize,RasterYSize,ULX,LRY,URX,ULY = calcImgExt(mos_tif)
	basename = os.path.basename(mos_tif).replace('.tif','')
	thisSH = open('correction-%s.sh'%basename,'w')
	args['basename'] = basename
	args['RasterXSize'] = RasterXSize
	# Make TFW for output mosiac tile
	tfw4corr = wldTemplate() % (pixelX,pixelX,ULX,ULY)
	thisTFW = open('corr/%s.tfw'%basename,'w')
	thisTFW.write(tfw4corr)
	thisTFW.close()
	# Resample mosaic tile to match feathered mosiac
	resampleLittleBlur = 'gdalwarp -co TFW=YES -tr %s %s %s little-blur/%s.tif\n' % (mosResolution,mosResolution,mos_tif,basename)
	thisSH.write(resampleLittleBlur)
	# Blur resampled mosiac tile
	imBlurLittleMos = 'mogrify -blur %s little-blur/%s.tif\n' % (blur,basename)
	thisSH.write(imBlurLittleMos)
	# Clip out corresponding area in feathered mosaic
	warpFM = 'gdalwarp -te %s %s %s %s  mosFM.vrt big-blur/%s.tif\n' %(ULX,LRY,URX,ULY,basename)
	thisSH.write(warpFM)
	# Subtract fwd and rev
	dstCmd = 'composite -compose minus_dst little-blur/%s.tif big-blur/%s.tif little-blur/dst%s.tif\n' %(basename,basename,basename)
	thisSH.write(dstCmd)
	srcCmd = 'composite -compose minus_src little-blur/%s.tif big-blur/%s.tif little-blur/src%s.tif\n' %(basename,basename,basename)
	thisSH.write(srcCmd)
	# Apply fwd and rev delta and limit to area of original alpha.
	corrCmd = 'composite -quiet -compose minus_dst %(basename)s.tif  little-blur/dst%(basename)s.tif -resize %(RasterXSize)s - | composite -quiet -compose plus - little-blur/src%(basename)s.tif -resize %(RasterXSize)s - | convert - \( %(basename)s.tif -channel a -separate +channel -morphology Erode:8 Disk -blur 0x16 \) -alpha off -compose copy_opacity -composite corr/%(basename)s.tif\n ' % args
	thisSH.write(corrCmd)
	#seamCmd = 'mogrify -channel a -blur 0x4 -morphology Erode:4 Disk corr/%(basename)s.tif\n' % args
	#thisSH.write(seamCmd)
	# Clean up intermediate files
	cleanCmd = 'rm little-blur/dst%(basename)s.tif little-blur/src%(basename)s.tif little-blur/%(basename)s.tif big-blur/%(basename)s.tif\n' % args
	thisSH.write(cleanCmd)
	# Enable to compress original image
	gzCmd = 'gzip %s\n' % mos_tif
	if spaceIsTight:
		thisSH.write(gzCmd)
	thisSH.close()
print 'Start color correction...'
parallelCmd = 'ls correction-*.sh | parallel -j 16 bash {}'
os.system(parallelCmd)
os.system('rm correction-*.sh')
writerCMD = 'gdalwarp -q -wo SKIP_NOSOURCE=YES -te %s %s %s %s  -srcnodata "0 0 0" -co TILED=YES  corr/*.tif final/%s.tif'
print 'Start writing tiles...'
counter=0
offset	= 100000
os.system('pwd')
for xVal in range(mosaicULX,mosaicLRX+offset,offset):
	for yVal in range(mosaicLRY,mosaicULY+offset,offset):
		writerSH = open(('writer-%s.sh'%counter),'w')
		writerTXT = writerCMD % (xVal,yVal,xVal+offset,yVal+offset,counter)
		writerSH.write(writerTXT)
		writerSH.close()
		counter += 1
parallelCmd = 'ls writer-*.sh | parallel bash {}'
os.system(parallelCmd)



