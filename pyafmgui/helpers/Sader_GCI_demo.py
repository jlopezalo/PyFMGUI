# Version 0.20
#
# Requires the Requests and XML installed
#
# MIT License
#
# Copyright (c) 2016 - 2020 John Sader and Jason Kilpatrick
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software. The name "Sader Method - Global
# Calibration Initiative" or the equivalent "Sader Method GCI" and its URL 
# "sadermethod.org" shall be listed prominently in the title of any future 
# realization/modification of this software and its rendering in any AFM software
# or other platform, as it does in the header of this software and its rendering. 
# Reference to this software by any third party software or platform shall include
# the name "Sader Method - Global Calibration Initiative" or the equivalent "Sader
# Method GCI" and its URL "sadermethod.org".
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import requests
import xml.etree.ElementTree as etree

Version = 'Python API/0.20'
Type = 'text/xml'
url = 'https://sadermethod.org/api/1.1/api.php'


def SaderGCI_GetLeverList( UserName, Password ):
    payload = '''<?xml version="1.0" encoding="UTF-8" ?>
    <saderrequest>
      <username>'''+UserName+'''</username>
      <password>'''+Password+'''</password>
      <operation>LIST</operation>
    </saderrequest>'''
    headers = {'user-agent': Version, 'Content-type': Type}
    r = requests.post(url, data=payload, headers=headers)
    doc = etree.fromstring(r.content)
    
    cantilever_ids = doc.findall('./cantilevers/cantilever/id')
    cantilever_labels = doc.findall('./cantilevers/cantilever/label')

    for a in range(len(cantilever_ids)):
        print (cantilever_labels[a].text,cantilever_ids[a].text.replace('data_','(')+')')

        
def SaderGCI_CalculateK( UserName, Password, LeverNumber, Frequency, QFactor ):
    payload = '''<?xml version="1.0" encoding="UTF-8" ?>
    <saderrequest>
        <username>'''+UserName+'''</username>
        <password>'''+Password+'''</password>
        <operation>UPLOAD</operation>
        <cantilever>
            <id>data_'''+str(LeverNumber)+'''</id>
            <frequency>'''+str(Frequency)+'''</frequency>
            <quality>'''+str(QFactor)+'''</quality>
        </cantilever>
    </saderrequest>'''
    headers = {'user-agent': Version, 'Content-type': Type}
    r = requests.post(url, data=payload, headers=headers)
    print (r.text)
    doc = etree.fromstring(r.content)
    if (doc.find('./status/code').text == 'OK'):
        print ("Sader GCI Spring Constant = "+doc.find('./cantilever/k_sader').text+', 95% C.I. Error = '+doc.find('./cantilever/percent').text+'% from '+doc.find('./cantilever/samples').text+' samples.')
        # Added return statement for the GCI Spring Constant
        return float(doc.find('./cantilever/k_sader').text)

        
def SaderGCI_CalculateAndUploadK( UserName, Password, LeverNumber, Frequency, QFactor, SpringK ):
    payload = '''<?xml version="1.0" encoding="UTF-8" ?>
    <saderrequest>
        <username>'''+UserName+'''</username>
        <password>'''+Password+'''</password>
        <operation>UPLOAD</operation>
        <cantilever>
            <id>data_'''+str(LeverNumber)+'''</id>
            <frequency>'''+str(Frequency)+'''</frequency>
            <quality>'''+str(QFactor)+'''</quality>
            <constant>'''+str(SpringK)+'''</constant>
            <comment>'''+Version+'''</comment>
        </cantilever>
    </saderrequest>'''
    headers = {'user-agent': Version, 'Content-type': Type}
    r = requests.post(url, data=payload, headers=headers)
    print (r.text)
    doc = etree.fromstring(r.content)
    if (doc.find('./status/code').text == 'OK'):
        print ("Sader GCI Spring Constant = "+doc.find('./cantilever/k_sader').text+', 95% C.I. Error = '+doc.find('./cantilever/percent').text+'% from '+doc.find('./cantilever/samples').text+' samples.')
