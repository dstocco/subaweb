#!/usr/bin/env python

import os
import sys
import requests
import argparse
import datetime
import yaml
import xml.etree.ElementTree as ET


def isSameTitle(title, refTitle):
    words = title.split(' ')
    nWords = len(words)
    nFound = 0
    for word in words:
        if word in refTitle:
            nFound += 1
    return float(nFound)/float(nWords) > 0.6


def isDuplicated(contrib, mergedContributions):
    for merged in mergedContributions:
        if contrib.get('lastname') and merged.get('lastname'):
            if contrib['lastname'] == merged['lastname']:
                if isSameTitle(contrib['title'], merged['title']):
                    return True
    return False


def addContribution(event, mergedList):
    # Add the contributions
    for mergedEvent in mergedList:
        if event['start'] == mergedEvent['start'] and event['end'] == mergedEvent['end']:
            for contrib in event['contributions']:
                if isDuplicated(contrib, mergedEvent['contributions']):
                    print('Duplicated contribution:')
                    print(contrib)
                else:
                    mergedEvent['contributions'].append(contrib)
            return
    mergedList.append(event)


def mergeEvents(eventList):
    # Merges the contributions in the same event
    mergedList = []
    for event in eventList:
        addContribution(event, mergedList)
    return mergedList


def getSearchName(name, ns='http://www.tei-c.org/ns/1.0'):
    return '{' + ns + '}' + name


def getSearchChild(name, tag=''):
    outSearch = './/' + getSearchName(name)
    if len(tag) > 0:
        outSearch += '/' + tag
    return outSearch


def parseFile(filename):
    # Parse the file from HAL
    tree = ET.parse(filename)
    root = tree.getroot()
    eventList = []
    for bib in root.iter(getSearchName('biblFull')):
        event = {}
        eventList.append(event)
        contrib = {}
        event['contributions'] = [contrib]

        struct = bib.find(getSearchChild('biblStruct'))
        meet = struct.find(getSearchChild('meeting'))

        # Get conference info
        event['conference'] = meet.find(getSearchChild('title')).text
        event['start'] = datetime.datetime.strptime(
            meet.find('.//*[@type="start"]').text, '%Y-%m-%d').date()
        event['end'] = datetime.datetime.strptime(
            meet.find('.//*[@type="end"]').text, '%Y-%m-%d').date()
        event['venue'] = meet.find(getSearchChild(
            'settlement')).text + ', ' + meet.find(getSearchChild('country')).text
        event['audience'] = bib.find('.//*[@type="audience"]').text

        # Get contribution info
        contrib['type'] = 'Talk'  # TODO: check for posters
        contrib['title'] = struct.find(getSearchChild('title')).text
        author = struct.findall('.//*[@role="aut"]')
        contrib['firstname'] = author[0].find(
            getSearchChild('forename')).text
        contrib['lastname'] = author[0].find(
            getSearchChild('surname')).text
        invited = bib.find('.//*[@type="invited"]').text
        contrib['invited'] = invited == 'Yes'

        # This info might be missing
        for el in bib.findall('.//*[@type="doi"]'):
            contrib['proceedings'] = 'https://dx.doi.org/' + el.text
    return eventList


def getHalFile(year, group='SUBATECH-PLASMA'):
    # Gets the conferences from HAL
    url = 'https://api.archives-ouvertes.fr/search/imt-atlantique/?omitHeader=true&wt=xml-tei&q=collName_t%3A%28' + group + \
        '%29+AND++conferenceStartDateY_i%3A%28' + \
        str(year) + '%29&fq=collCode_s%3AIMT-ATLANTIQUE&fq=NOT+status_i%3A111&defType=edismax&rows=1000'

    outFilename = 'data_from_hal/hal_' + group + '_' + str(year) + '.xml'

    if os.path.exists(outFilename):
        print(outFilename + ' exists: reload from web? [y/n]')
        answer = sys.stdin.readline().strip()
        if (answer != 'y'):
            return outFilename

    print('Querying url ' + url)
    req = requests.get(url)
    with open(outFilename, 'w') as outFile:
        outFile.write(req.text)

    return outFilename


def printContribution(conf, outFile):
    # Generates the html code for the contributions
    if not conf.get('contributions'):
        return 1
    contributions = conf['contributions']

    outFile.write('\n    <ul style="list-style-type: disc";>\n')
    for contrib in contributions:
        outFile.write('      <li>')
        if contrib.get('invited') and contrib['invited'] is True:
            outFile.write('Invited ')
        outFile.write(contrib['type'])
        contribDetails = ''
        if contrib.get('title'):
            contribDetails += ' <em>' + contrib['title'] + '</em>,'
        if contrib.get('firstname'):
            contribDetails += ' ' + \
                contrib['firstname'] + ' ' + contrib['lastname'].upper()
        if (len(contribDetails) > 0):
            outFile.write(': ' + contribDetails)
        if contrib.get('proceedings'):
            outFile.write('. Proceedings <a href="' +
                          contrib['proceedings'] + '">here</a>')
        outFile.write('</li>\n')
    outFile.write('    </ul>\n')
    return 0


def printEvent(event, outFile):
    # Generate the html code for the event
    outFile.write('  <li>')
    url = event.get('url')
    name = event['conference']
    if event.get('alias'):
        name = event['alias']
    if url:
        outFile.write('<a href="' + url + '">' + name + '</a>')
    else:
        outFile.write(name)

    outFile.write(
        ', ' + event['start'].strftime('%d/%m/%y') + ', ' + event['venue'] + '.')
    if event.get('type'):
        outFile.write(' ' + event['type'] + '.')
    if event.get('participants'):
        outFile.write(' ' + str(event['participants']) + ' participants.')
    printContribution(event, outFile)
    outFile.write('  </li>\n')
    return 0


def addMissingInfos(eventList, infos):
    for item in infos:
        for event in eventList:
            if item['conference'] == event['conference']:
                for key in item.keys():
                    if not event.get(key):
                        event[key] = item[key]


def completeInfo(eventList, additionalInfoFile):
    if os.path.exists(additionalInfoFile):
        with open(additionalInfoFile) as inFile:
            infos = list(yaml.safe_load_all(inFile.read()))
            addMissingInfos(eventList, infos)


def checkEvents(mergedEvents):
    # Check events to spot missing or duplicated info
    for event in mergedEvents:
        if not event.get('url'):
            print('Missing url for ' + event['conference'])
        # if not event.get('contributions'):
        #     # This happens for organized conferences
        #     continue
        # contributions = event['contributions']
        # for icontr in range(len(contributions)):
        #     if (not contributions[icontr].get('lastname')):
        #         # This happens if the contribution is the conference organization
        #         continue
        #     for jcontr in range(icontr+1, len(contributions)):
        #         if (not contributions[jcontr].get('lastname')):
        #             # This happens if the contribution is the conference organization
        #             continue
        #         if contributions[icontr]['lastname'] == contributions[jcontr]['lastname']:
        #             print('Possible duplication for event: ' +
        #                   event['conference'] + '  author: ' + contributions[icontr]['lastname'])
        #             print('Titles: ')
        #             print('  - ' + contributions[icontr]['title'])
        #             print('  - ' + contributions[jcontr]['title'])


def main():
    parser = argparse.ArgumentParser(description='Utility for conferences')
    parser.add_argument("--min", help="Minimum year",
                        type=int, dest='min', default=2008)
    parser.add_argument("--group", help="Group",
                        dest="group", default="SUBATECH-PLASMA")

    args = parser.parse_args()

    now = datetime.datetime.now()

    outFile = open("plasma_conferences.html", "w")

    for year in reversed(range(args.min, now.year+1)):
        # Get events from hal
        eventList = []
        if (year >= 2015):
            halFilename = getHalFile(year, args.group)
            eventList += parseFile(halFilename)
            # Add some information to better link with yaml
            completeInfo(
                eventList, 'additionalInfo/additionalInfo_' + str(year) + '.yaml')

        # Get events from yaml
        yamlFilename = 'data/plasma_conferences_' + str(year) + '.yaml'
        if os.path.exists(yamlFilename):
            with open(yamlFilename) as inFile:
                eventList += list(yaml.safe_load_all(inFile.read()))

        # Remove empty objects
        eventList = [evt for evt in eventList if evt is not None]

        # Merge the events
        mergedEvents = mergeEvents(
            sorted(eventList, key=lambda it: it['start'], reverse=True))

        if (year > 2015):
            checkEvents(mergedEvents)

        # Write the html
        outFile.write('\n<h3>' + str(year) + '</h3>\n')
        outFile.write('<ul style="list-style-type: circle;">\n')
        for event in mergedEvents:
            printEvent(event, outFile)
        outFile.write('</ul>\n')

    outFile.close()

    return 0


if __name__ == "__main__":
    rc = main()
    sys.exit(rc)
