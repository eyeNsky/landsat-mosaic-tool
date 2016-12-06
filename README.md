# landsat-mosaic-tool
Utility to download, pansharpen and mosaic landsat data.

# General workflow for Ubuntu 14.04 on AWS
Provision VM...log on.
sudo apt-get install unzip
wget https://github.com/eyeNsky/landsat-mosaic-tool/archive/master.zip
unzip master.zip
cp landsat-mosaic-tool-master/*.py .
python prep-mosaic.py setup
printf 'echo LC80210382015287LGN00\necho LC80210392015287LGN00\necho LC80210402015287LGN00\n' > scenes.sh
bash scenes.sh | parallel python prep-mosaic.py {}
cd mosaic
python ../landsat-mosaic-tool.py

The tiled output will be in final/
