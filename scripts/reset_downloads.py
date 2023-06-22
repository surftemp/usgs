import requests
import sys
import argparse

parser = argparse.ArgumentParser()

parser.add_argument('-u', '--username', required=True, help='Username')
parser.add_argument('-p', '--password', required=True, help='Password')

args = parser.parse_args()
username = args.username
password = args.password

download_labels_url = "https://m2m.cr.usgs.gov/api/api/json/stable/download-labels"
download_order_remove_url = "https://m2m.cr.usgs.gov/api/api/json/stable/download-order-remove"
download_retrieve_url = "https://m2m.cr.usgs.gov/api/api/json/stable/download-retrieve"
download_remove_url = "https://m2m.cr.usgs.gov/api/api/json/stable/download-remove"
login_url = "https://m2m.cr.usgs.gov/api/api/json/stable/login"

login_payload = {'username': username, 'password': password}
resp = requests.post(login_url,json=login_payload)
api_key = resp.json()["data"]

headers = {'X-Auth-Token': api_key}
resp = requests.post(download_labels_url,json={},headers=headers)

downloads = resp.json()["data"]
if downloads is None:
    print("No downloads found")
    sys.exit(0)
else:
    print("Found %d downloads"%(len(downloads)))

idx = 0
total = len(downloads)
for download in downloads:
    label = download["label"]
    resp = requests.post(download_order_remove_url, json={"label":label}, headers=headers)
    resp = requests.post(download_retrieve_url, json={"label":label}, headers=headers)
    print(resp.json())

    data = resp.json()["data"]

    idx += 1
    print(idx/total)
    for requested in data["requested"]:
        download_id = requested["downloadId"]
        resp = requests.post(download_remove_url, json={"downloadId": download_id}, headers=headers)
        print(resp)
        print(download_id)




