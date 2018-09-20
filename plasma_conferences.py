#!/usr/bin/env python

import os
import sys
import yaml
import re

def getFileList(searchDir="."):
    fileList = os.listdir(searchDir)
    chosenFiles = [ifile for ifile in fileList if re.search(r'[0-9][0-9][0-9][0-9]\.yaml',ifile)]
    return sorted(chosenFiles, reverse=True)

def printContribution(conf, outFile):
    if not conf.get('contributions'):
        return 1
    contributions = conf['contributions']

    outFile.write('\n    <ul style="list-style-type: disc";>\n')
    for contrib in contributions:
        # if ( len(contributions) > 1 ):
        #     outFile.write('<br/>')
        outFile.write('      <li>' + contrib['type'] + ': ')
        if contrib.get('title'):
            outFile.write('<em>' + contrib['title'] + '</em>, ')
        if contrib.get('author'):
            outFile.write(contrib['author'])
        if contrib.get('proceedings'):
            outFile.write('. Proceedings <a href="' + contrib['proceedings'] + '">here</a>')
        outFile.write('</li>\n')
    outFile.write('    </ul>\n')
    return 0

def printConference(conf, outFile):
    outFile.write('  <li>')
    url = conf.get('url')
    if url:
        outFile.write('<a href="' + url + '">' + conf['conference'] + '</a>')
    else:
        outFile.write(conf['conference'])

    outFile.write(', ' + conf['date'] + ', ' + conf['venue'] + '.')
    if conf.get('type'):
        outFile.write(' ' + conf['type'])
        if conf.get('participants'):
            outFile.write(' ' + str(conf['participants']) + ' participants')
        outFile.write('.')
    printContribution(conf,outFile)
    outFile.write('  </li>\n')
    return 0


def main():

    fileList = getFileList()

    pattern = re.compile(r'[0-9][0-9][0-9][0-9]')

    outFile = open("plasma_conferences.html","w")

    for ifile in fileList:
        year = pattern.search(ifile).group(0)
        outFile.write('\n<h3>' + year + '</h3>\n')
        outFile.write('<ul style="list-style-type: circle;">\n')
        with open(ifile) as file:
            conferences = yaml.load_all(file.read())
            # conferences = yaml.load_all(file.read().encode('ascii','xmlcharrefreplace'))

        for conf in conferences:
            printConference(conf,outFile)

        outFile.write('</ul>\n')

    outFile.close()

    return 0


if __name__ == "__main__":
    rc = main()
    sys.exit(rc)

