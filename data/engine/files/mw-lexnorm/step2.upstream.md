### MWlexnorm/step2

Begun Sep 22, 2018

Recreate analogue of step1b/lexnorm-all.txt based on revised form of 
mw.xml.

#### source of mw.xml
```
curl -o mwxml.zip http://s3.amazonaws.com/sanskrit-lexicon/blobs/mw_xml.zip
unzip mwxml.zip
mv pywork mwxml
rm mwxml.zip
```
mwxml directory contains mw.xml and mw.dtd and license (mwheader.xml)

The .gitignore of this directory excludes the mwxml directory.

#### lexnorm-all2.txt
python lexcat2.py mwxml/mw.xml lexnorm-all2.txt
