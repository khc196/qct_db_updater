import db
import os
import time
import shutil
import json
import yaml
import requests
import sys
import ast
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
import pandas as pd

META_MINIMIZED = "\\\\automotive-linux\\meta_minimized"
DOWNLOAD_PATH = os.getcwd()+"\\release_notes_download"
DRIVER_PATH = os.getcwd()+'\\db\\chromedriver.exe'
OPENGROK_PATH = "\\\\automotive-linux\\opengrok_source"
OPENGROK2_PATH = "\\\\automotive-linux\\opengrok_source_LA_MDM"
chrome_options = Options()
prefs = {"plugins.plugins_disabled" : "Chrome PDF Viewer", "download.prompt_for_download": False, "plugins.always_open_pdf_externally": True, "download.default_directory": DOWNLOAD_PATH + "\\"} 
chrome_options.add_experimental_option("prefs", prefs)
driver = None
list_mm = []
request_url = "https://automotive-linux:9999/db/"
sp_url = request_url + "sp/"
build_url = request_url + "build/"
sp_data = []
build_data = []

updated_count = 0
def check():
    dirnames = os.listdir(META_MINIMIZED)
    for dirname in dirnames:
        full_dirname = os.path.join(META_MINIMIZED, dirname)
        if os.path.isdir(full_dirname): 
            if full_dirname.find("signed") > -1:
                continue
            elif full_dirname.find("early_init") > -1:
                continue
            elif full_dirname.find("ethcam") > -1:
                continue    
            elif full_dirname.find("INT") > -1 :
                continue
            elif full_dirname.find("PRODMizar") > -1 :
                continue
            elif full_dirname.find("err") > -1 :
                continue
            elif full_dirname.find("perf") > -1 :
                continue
            elif full_dirname.find("back") > -1 :
                continue
            elif full_dirname.find(".doing") > -1:
                continue
            list_mm.append(dirname)
    print 'Meta check'
    for build in build_data:
        print build['name'], ' ...',
        hasMeta = False
        for mm in list_mm:
            if mm == build['name']:
                print 'has meta'
                hasMeta = True
                break
        if not hasMeta:
            print 'has no meta, Delete it from DB'
            requests.delete(build_url+str(build['id'])+'/', verify=False)
    return len(list_mm)
    
def start(test=False):
    global driver, sp_data, build_data
    
    response_s = requests.get(sp_url, headers={"Content-Type": "application/json"}, verify=False)
    response_b = requests.get(build_url, headers={"Content-Type": "application/json"}, verify=False)
    sp_data = response_s.json()
    build_data = response_b.json()
    
    if test:    
        driver = webdriver.Chrome('chromedriver.exe', chrome_options=chrome_options)
        loginQTI(True)
    else:
        driver = webdriver.Chrome(DRIVER_PATH, chrome_options=chrome_options)
        loginQTI()
def quit():
    global driver
    try:
        driver.quit()
    except:
        pass
def loginQTI(test=False) :
    driver.get("https://createpoint.qti.qualcomm.com/dashboard")
    driver.implicitly_wait(5)
    if test:
        f = open("logininfo", 'r')
    else:
        f = open(os.getcwd()+"\\db\\logininfo", 'r')
    id_login = f.readline().split()[0]
    id_password = f.readline().split()[0]
    driver.find_element_by_name('USER').send_keys(id_login)
    driver.find_element_by_name('PASSWORD_INPUT').send_keys(id_password)
    driver.find_element_by_xpath('//*[@id="submitBtn"]').click()
    while True :
        try:
            #WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, '//*[@id="ackForm"]/div/input')))
            print "Login Successfully!"
            break # it will break from the loop once the specific element will be present. 
        except TimeoutException:
            print "Loading took too much time!-Try again"
    driver.find_element_by_xpath('//*[@id="ackForm"]/div/input').click() 

def getLinks(url, name) :
    print 'get Links... ',
    driver.get(url)
    html = driver.page_source
    soup = BeautifulSoup(html, 'html.parser')
    
    tables = soup.find_all("table")
    for table in tables:
        if "Release Notes" in str(table) or "Release notes" in str(table) or 'External Build' in str(table) or 'External META' in str(table):
            table_ = table

    height = len(table_.find_all("tr"))
    #print table_.find_all
    width = len(table_.find_all("tr")[0].find_all("th"))
    if width == 0:
        width = len(table_.find_all("tr")[0].find_all("td"))
        td_flag = True
    #print 'height: ', height
    #print 'width: ', width
    new_table = pd.DataFrame(columns=range(0,width+3), index=range(0,height))
    row_marker=0
    erb_id = 0
    rnd_id = 0
    rd_id = 0
    for row in table_.find_all("tr"):
        build_name = ""
        rno_name_ = ""
        release_date_ = ""
        column_marker = 0
        columns = row.find_all("td")
        if len(columns) == 0:
            columns = row.find_all("th")
        for column in columns:
            if row_marker == 0:
                new_table.iat[row_marker, column_marker] = column.get_text()
                pointer = column.get_text().lower()
                if pointer == 'external release build' or pointer == 'mainline' or 'meta id' in pointer or 'external' in pointer:
                    erb_id = column_marker
                elif pointer == 'release notes doc id' or pointer == 'release notes' or pointer == 'release notes dcn':
                    rnd_id = column_marker
                elif pointer == 'release date' or pointer == 'date':
                    rd_id = column_marker
            else:
                if column_marker == erb_id: 
                    try:
                        new_table.iat[row_marker, column_marker] = column.a['href']
                        build_name = column.get_text().encode('ascii', 'ignore').strip()
                    except:
                        pass
                elif column_marker == rnd_id:
                    try:
                        new_table.iat[row_marker, column_marker] = column.a['href']
                        rno_name_ = column.get_text().encode('ascii', 'ignore').strip()
                    except:
                        rno_name_ = column.get_text().encode('ascii', 'ignore').strip()
                elif column_marker == rd_id:
                    try:
                        new_table.iat[row_marker, column_marker] = column.get_text().encode('ascii', 'ignore')
                        release_date_ = column.get_text().encode('ascii', 'ignore').strip()
                    except:
                        pass
                else:
                    new_table.iat[row_marker, column_marker] = column.get_text().encode('ascii', 'ignore')
            column_marker += 1
        new_table.iat[row_marker, column_marker] = build_name
        new_table.iat[row_marker, column_marker+1] = rno_name_
        new_table.iat[row_marker, column_marker+2] = release_date_
        row_marker += 1
    wiki_link = ""
    rno_download_link = ""
    rno_name = ""
    release_date = ""
    for row in new_table.itertuples() :
        if not name in row[width+1]:
            continue        
        wiki_link = row[erb_id+1]
        rno_download_link = row[rnd_id+1]
        rno_name = row[width+2]
        release_date = row[width+3]
        #print row
    print 'wiki: ', wiki_link
    print 'rno link: ', rno_download_link
    print 'rno name: ', rno_name
    print 'release date: ', release_date
    print 'Done'
    return wiki_link, rno_download_link, rno_name, release_date

def downloadRNO(download_link):
    print 'download RNO...',
    driver.get(download_link)
    driver.implicitly_wait(5)
    
    try:
        url_download = driver.find_element_by_xpath('//*[@id="list-search-results"]/div/div/header/h4/a[1]').get_attribute('href')
    except:
        return 
    driver.get(url_download)
    print 'Done'
def check_GVM_ID(build):
    print 'check GVM ID...',
    gvm_id = ""
    try:
        with open(META_MINIMIZED+'/'+build+'/'+'gvm_plf_tag', 'r') as f:
            lines = f.readlines()
        lines = [x.strip() for x in lines]
        gvm_id = lines[0]
    except:
        pass
    print 'Done'
    print 'GVM ID: ', gvm_id
    return gvm_id
def check_APPS_ID(build):
    print 'check APPS ID...',
    apps_id = ""
    try:
        with open(META_MINIMIZED+'/'+build+'/'+'apps_plf_tag', 'r') as f:
            lines = f.readlines()
        lines = [x.strip() for x in lines]  
        apps_id = lines[0]
    except:
        pass
    print 'Done'
    print 'APPS ID: ', apps_id
    return apps_id
def check_AU_TAG(build):
    print 'check AU TAG...',
    au_tag = ""
    try:
        if 'HQX' in build:
            with open(META_MINIMIZED+'/'+build+'/'+'gvm_plf_tag', 'r') as f:
                lines = f.readlines()
        else:
            with open(META_MINIMIZED+'/'+build+'/'+'apps_plf_tag', 'r') as f:
                lines = f.readlines()
        lines = [x.strip() for x in lines]
        au_tag = 'AU_' + lines[1].split('_AU_')[1].split('.plf')[0]
    except:
        pass
    print 'Done'
    print 'AU TAG: ', au_tag
    return au_tag
def proceed(build):
    # if not 'HQX' in build:
    #     return
    global updated_count
    updated_count += 1
    full_dirname = os.path.join(META_MINIMIZED, build)
    print build, " start"
    original = None
    for b in build_data:
        b = yaml.safe_load(json.dumps(b))
        if b['name'] == build:
            original = b
            break
    url = ""
    wiki_link = ""
    rno_link = ""
    rno_name = ""
    fastboot = full_dirname+"\\common\\build\\fastboot_complete.py"
    qfil = full_dirname+"\\QFIL"
    release_date = ""
    apps_id = check_APPS_ID(build)
    au_tag = check_AU_TAG(build)
    gvm_id = ""
    if 'HQX' in build:
        gvm_id = check_GVM_ID(build)
    if(build.find("PROD") > -1):
        flag = False
        sp_name = ""
        for sp in sp_data:
            sp = yaml.safe_load(json.dumps(sp))
            if sp['name'] + '-' in build:
                sp_id_fk = sp['id']
                sp_name = sp['name']
                url = sp['wiki']
                flag = True
                print 'SP: ', sp_name
                break
        if not flag:
            print "no sp matched, delete it from DB"
            if original != None:
                r = requests.delete(url=build_url+str(original['id'])+'/', verify=False)
            return
        if not url == "" and not url == None:
            wiki_link, rno_link, rno_name, release_date = getLinks(url, build)
        if not rno_link == "" and not type(rno_link) == float and '.com' in rno_link:
            rno_path = full_dirname + "\\" + rno_name + ".pdf"
            if original == None or original['release_note'] == "" or original['release_note'] == None or not os.path.isfile(rno_path):
                downloadRNO(rno_link)
                time.sleep(8)
            else:
                rno_name = original['release_note']
            ws_filenames = os.listdir(DOWNLOAD_PATH)
            for filename in ws_filenames:
                if rno_name.lower() in filename.lower() :
                    try :
                        shutil.move(DOWNLOAD_PATH + "\\" +filename, rno_path)
                        print "PDF Downloaded"
                        break
                    except : 
                        pass
        if not os.path.isdir(qfil):
            os.makedirs(qfil)
        status = 0
        print "Check if there is the source on server... ",
        if 'HQX.' in build and not gvm_id == "":
            print ' GVM: ',
            if os.path.isdir(OPENGROK_PATH + '\\' + gvm_id) or os.path.isdir(OPENGROK2_PATH + '\\' + gvm_id):
                print 'OK'
                status += 2
            else:
                print 'NO'
        if not apps_id == "":            
            if os.path.isdir(OPENGROK_PATH + '\\' + apps_id) or os.path.isdir(OPENGROK2_PATH + '\\' + apps_id):
                print "OK"
                status += 1
            else:
                print "NO"

        print build, " done"
        
        print "Update DB..."
        headers = {'Content-type': 'application/json; charset=utf-8'}
        if not original == None :
            print "Update data"
            print 'sp id fk: ', sp_id_fk
            print 'name: ', build
            print 'wiki: ', wiki_link
            print 'release note: ', rno_name
            print 'fastboot: ', fastboot
            print 'qfil: ', qfil
            print 'release date: ', release_date
            print 'apps id: ', apps_id
            if 'HQX' in build:
                print 'gvm id: ', gvm_id
            print 'au tag: ', au_tag
            
            data = {
                'id': original['id'],
                'sp_id_fk': sp_id_fk,
                'name': build,
                'wiki': str(wiki_link),
                'release_note': rno_name,
                'fastboot': fastboot,
                'qfil': qfil,
                'release_date': release_date,
                'apps_id': apps_id,
                'au_tag': au_tag,
                'status': status,
                'gvm_id': gvm_id,
            }
            # print '\n#####original data#####'
            # print original
            # print '\n####new data####'
            # print data
            if not cmp(original, data) == 0:
                print 'REST api(PUT) call...',
                r = requests.put(url=build_url+str(original['id'])+'/', headers=headers, data=json.dumps(data), verify=False)
                print 'Done'
            else:
                print 'No change.'
            #print r.text
        else :
            print "insert new data"
            print 'sp id fk: ', sp_id_fk
            print 'name: ', build
            print 'wiki: ', wiki_link
            print 'release note: ', rno_name
            print 'fastboot: ', fastboot
            print 'qfil: ', qfil
            print 'release date: ', release_date
            print 'apps id: ', apps_id
            if 'HQX' in build:
                print 'gvm id: ', gvm_id
            print 'au tag: ', au_tag
            data = {
                'sp_id_fk': sp_id_fk,
                'name': build,
                'wiki': wiki_link,
                'release_note': rno_name,
                'fastboot': fastboot,
                'qfil': qfil,
                'release_date': release_date,
                'apps_id': apps_id,
                'au_tag': au_tag,
                'status': 1,
                'gvm_id': gvm_id,
            }
            print 'REST api(POST) call...',
            r = requests.post(url=build_url, headers=headers, data=json.dumps(data), verify=False)
            print 'Done'
            #print r.text
        
        print "Update Completed"
        #mydb.commit()
    
if __name__ == '__main__':
    starttime = time.time()
    start(True)
    check()
    for build in list_mm:
        proceed(build)
        print int(float(updated_count)/float(len(list_mm)) * 100), '%'
        print("=============================================================================================================")
    endtime = time.time()
    elapsed = int(endtime - starttime)
    
    print 'elapsed time : {:02d} min {:02d} sec'.format(elapsed % 3600 // 60, elapsed % 60)
    try:
        input("Press any key...")
    except:
        pass
    finally:
        quit()
    