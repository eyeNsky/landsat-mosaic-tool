#!/usr/bin/env python
'''
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

Please see landsat-util for their license.

https://github.com/developmentseed/landsat-util

Options parser code
***************************************
# MBUtil: a tool for MBTiles files
# Supports importing, exporting, and more
# 
# (c) Development Seed 2012
# (c) 2016 ePi Rational, Inc.
# Licensed under BSD
***************************************

'''

import os,sys
from optparse import OptionParser
from xml.dom.minidom import parse
def init_vm():
	cmd = '''
sudo apt-get update
sudo apt-get -y install imagemagick geotiff-bin enblend exiftool s3cmd gdal-bin python-pip python-gdal python-numpy python-scipy libgdal-dev libatlas-base-dev gfortran libfreetype6-dev parallel 
sudo pip install Cython
sudo pip install landsat-util
'''
	fout = open('init.sh','w')
	fout.write(cmd)
	fout.close()
	os.system('bash init.sh')

def parseInfo(anXML):
	histInfo = parse(anXML)
	pam = histInfo.getElementsByTagName("PAMRasterBand")
	histMean = 9999

	for pd in pam[0:2]:
		md = pd.getElementsByTagName("Metadata")
		MDIS = md[0].getElementsByTagName("MDI")
		thisMean = int(float(MDIS[1].firstChild.data))
		if thisMean < histMean:
			histMean = thisMean
			histStd = int(float(MDIS[3].firstChild.data))
	histMean = float(histMean)	
	return int((histMean/255)*100)

def process(sceneID,procDir):
	args = {}
	args['sceneID'] = sceneID
	args['procDir'] = procDir
	# Download scene
	# No sharpen
	#downloadCmd = 'landsat download %(sceneID)s -b 654 -p ' % args
	# Pansharpen
	downloadCmd = 'landsat download %(sceneID)s -b 654 --pansharpen -p ' % args
	#downloadCmd = 'landsat download %(sceneID)s -b 432 -p ' % args 
	os.system(downloadCmd)

	if not os.path.isdir('temp'):
		os.system('mkdir temp')
	if not os.path.isdir(procDir+'/mosaic'):
		os.system('mkdir %s/mosaic'%procDir)

	warpCmd = 'gdalwarp -srcnodata "0 0 0" -tr 15 15 -dstalpha  -co TFW=YES -r cubic ~/landsat/processed/%(sceneID)s/%(sceneID)s_bands_654_pan.TIF %(procDir)s/mosaic/%(sceneID)s.tif ' % args
	os.system(warpCmd)
	#mvCmd = 'mv ~/landsat/processed/%(sceneID)s/%(sceneID)s_bands_654_pan.TIF %(procDir)s/mosaic/%(sceneID)s.tif ' % args
	#os.system(mvCmd)
	tfwCmd = 'listgeo -tfw %(procDir)s/mosaic/%(sceneID)s.tif ' % args
	os.system(tfwCmd)
	infoCmd = 'gdalinfo -stats %(procDir)s/mosaic/%(sceneID)s.tif' % args
	os.system(infoCmd)
	levelVal = parseInfo('%(procDir)s/mosaic/%(sceneID)s.tif.aux.xml' % args)
	args['levelVal'] = levelVal
	imCmd = 'mogrify -level %(levelVal)s%%,100%% %(procDir)s/mosaic/%(sceneID)s.tif' % args
	print imCmd
	os.system(imCmd)
	cleanUp = 'rm -r ~/landsat/downloads/%(sceneID)s* && rm -r ~/landsat/processed/%(sceneID)s* ' % args
	print cleanUp
	#os.system(cleanUp)

if __name__ == '__main__':
	parser = OptionParser(usage="""usage: %prog [options] setup/scene

	Examples:

	Prepare VM for processing:
	$ prep-mosaic.py setup

	Setup takes a while and you should see:
	Successfully installed landsat-util...
	Upon completion.

	Process a scene:
	$ prep-mosaic.py LC80110312013227LGN00

	Process a scene to specific existing directory:
	$ prep-mosaic.py --working-dir /path/to/existing/directory LC80110312013227LGN00""")

	parser.add_option('--working-dir', dest='workdir',
	    help='''Defaults to /home/ubuntu''',
	    default='/home/ubuntu')
	    
	    
	(options, cli) = parser.parse_args()    
	options = options.__dict__
	if not os.path.isdir(options['workdir']):
		print '\nERROR: Working directory must exist.\n'
		parser.print_help()
		sys.exit(1)

	if len(cli) != 1:
	    parser.print_help()
	    sys.exit(1)

	if cli[0] == 'setup':
		init_vm()

	else:
		process(cli[0],options['workdir']) 