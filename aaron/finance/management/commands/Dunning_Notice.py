from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

import requests, datetime, csv, openpyxl, os

class Command(BaseCommand):

    def handle(self, *args, **options):

        with open('login.txt', 'r') as document:
                auth_info = {}
                for line in document:
                    line = line.split()
                    if not line:
                        continue
                    auth_info[line[0]] = line[1]

        docparids=('Sales Invoice','Sales Invoice - Terms','Billable Invoice')
        today=datetime.date.today()
        def extract(string, xml):
            x=xml.split(string)
            return(x[1].lstrip('>').rstrip('</'))
        def customerSplit(xml):
            x=xml.split('customer>')
            final=[]
            for i in range (len(x)):
                if i%2==1:
                    final.append(x[i])
            return final
        def makeQuery(payload):
            api_url = 'https://api.intacct.com/ia/xml/xmlgw.phtml'
            controlerid = {'controlerid':'test'}
            api_request = """<?xml version="1.0" encoding="iso-8859-1"?>
            <request>
              <control>
                <senderid>"""+auth_info['mysenderid']+"""</senderid>
                <password>"""+auth_info['mysenderpw']+"""</password>
                <controlid>"""+controlerid['controlerid']+"""</controlid>
                <uniqueid>false</uniqueid>
                <dtdversion>3.0</dtdversion>
              </control>
              <operation>
                <authentication>
                  <login>
                    <userid>"""+auth_info['myuser']+"""</userid>
                    <companyid>"""+auth_info['mycompany']+"""</companyid>
                    <password>"""+auth_info['mypwd']+"""</password>
                  </login>
                </authentication>
                """+payload+"""
              </operation>
            </request>"""
            headers = {"Content-type": "application/x-www-form-urlencoded",
                       "Accept": "text/plain"}
            data={'xmlrequest':api_request}
            r=requests.post(api_url,data=data,headers=headers)
            return r
        def isPastDue(dueDate):
            if today.weekday()!=4:
                if ((today-dueDate).days==9):
                    return [True,9]
                elif ((today-dueDate).days==54):
                    return [True,54]
                elif ((today-dueDate).days==84):
                    return [True,84]
                else:
                    return [False,None]
            else:
                if ((today-dueDate).days in (9,8,7)):
                    return [True,(today-dueDate).days]
                elif ((today-dueDate).days in (54,53,52)):
                    return [True,(today-dueDate).days]
                elif ((today-dueDate).days in (84,83,82)):
                    return [True,(today-dueDate).days]
                else:
                    return [False,None]
        def convertToDateTime(dateString):
            x=dateString.split('/')
            return datetime.date(int(x[2].rstrip('"')),int(x[0].rstrip('"')),int(x[1].rstrip('"')))
        def getInvoices(docparid):
            readMore="""
                    <function controlid="foobar">
                        <readMore>
                            <object>SODOCUMENT</object>
                        </readMore>
                      </function>
                 """
            api_url = 'https://api.intacct.com/ia/xml/xmlgw.phtml'
            controlerid = {'controlerid':'test'}
            payload="""
            <content>
              <function controlid='AK'>
                <readByQuery>
                  <object>SODOCUMENT</object>
                  <docparid>"""+docparid+"""</docparid>
                  <pagesize>1000</pagesize>
                  <query>TOTALDUE > '0'</query>
                  <fields>DOCNO,CUSTVENDID,WHENDUE,TOTALDUE,CUSTVENDNAME,SHIPTOKEY,BILLTOKEY</fields>
                  <returnFormat>csv</returnFormat>
                </readByQuery>
              </function>
              """+readMore*10+"""
            </content>
            """
            api_request = """<?xml version="1.0" encoding="iso-8859-1"?>
            <request>
              <control>
                <senderid>"""+auth_info['mysenderid']+"""</senderid>
                <password>"""+auth_info['mysenderpw']+"""</password>
                <controlid>"""+controlerid['controlerid']+"""</controlid>
                <uniqueid>false</uniqueid>
                <dtdversion>3.0</dtdversion>
              </control>
              <operation>
                <authentication>
                  <login>
                    <userid>"""+auth_info['myuser']+"""</userid>
                    <companyid>"""+auth_info['mycompany']+"""</companyid>
                    <password>"""+auth_info['mypwd']+"""</password>
                  </login>
                </authentication>
                """+payload+"""
              </operation>
            </request>"""
            headers = {"Content-type": "application/x-www-form-urlencoded",
                       "Accept": "text/plain"}
            data={'xmlrequest':api_request}
            r=requests.post(api_url,data=data,headers=headers)
            file=open(docparid+'.csv','w', encoding='utf8')
            file.write(r.text)
            file.close()
        class Customer(object):
            def __init__(self,cid):
                self.cid=cid
                self.invoices=[]
                self.invoiceNums=[]

            def calculatePastDue(self):
                matches=[]

                for invoice in self.invoices:
                    x=isPastDue(invoice[2])
                    if (x[0]):
                        matches.append([invoice,x[1]])
                return matches




        idata=[]
        customers=[]
        custObjects=[]
        for docparid in docparids:
            getInvoices(docparid)
            with open(docparid+'.csv') as file:
                reader=csv.reader(file)
                for row in reader:
                    if row[0]!='DOCNO':
                        row[2]=convertToDateTime(row[2])
                        if isPastDue(row[2]):
                            row[3]=float(row[3])
                            idata.append(row)
        for invoice in idata: # create customers with associated invoices
            if invoice[1] not in customers:
                customers.append(invoice[1])
                custObjects.append(Customer(cid=invoice[1]))
                custObjects[len(custObjects)-1].invoices.append(invoice)
            else:
                for customer in custObjects:
                    if customer.cid==invoice[1]:
                        customer.invoices.append(invoice)
                        continue
        final=[]
        wb=openpyxl.Workbook()
        ws=wb.active
        ws.append(['CID','CUSTOMER','INVOICE','DUEDATE','DAYSPASTDUE','TOTALDUE'])
        for i in range(len(custObjects)):
            matches=custObjects[i].calculatePastDue()
            for k in range(len(matches)):
                ws.append([matches[k][0][1],matches[k][0][4],matches[k][0][0],matches[k][0][2],matches[k][1],matches[k][0][3]])
        os.chdir('C:\\Users\\akazan\\Documents')
        wb.save('DN.xlsx')
