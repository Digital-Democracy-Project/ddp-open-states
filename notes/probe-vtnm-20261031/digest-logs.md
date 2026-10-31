# Vermont and New Mexico probe logs on revision 44 (redacted; botocore upload headers omitted)

## vt  task c1b75813a6c248618da305651ddfbd38  (3451 lines in the stream; 3163 before the echoed report)
### first 40 lines (redacted)
  /opt/venv/lib/python3.10/site-packages/google/api_core/_python_version_support.py:242: FutureWarning: You are using a non-supported Python version (3.10.22). Google will not post any further updates to google.api_core supporting t
    warnings.warn(message, FutureWarning)
  22:40:40 DEBUG openstates.stats: Stat emission is not enabled.
  22:40:40 DEBUG urllib3.connectionpool: Starting new HTTP connection (1): legislature.vermont.gov:80
  22:40:41 DEBUG urllib3.connectionpool: http://legislature.vermont.gov:80 "GET /bill/search/2016 HTTP/1.1" 200 14807
  22:40:41 DEBUG urllib3.connectionpool: Starting new HTTP connection (1): legislature.vermont.gov:80
  22:40:41 DEBUG urllib3.connectionpool: http://legislature.vermont.gov:80 "GET /bill/search/2016 HTTP/1.1" 200 14807
  22:40:41 INFO scrapelib: GET - 'http://legislature.vermont.gov/bill/loadBillsReleased/2026/'
  22:40:41 DEBUG urllib3.connectionpool: Starting new HTTP connection (1): legislature.vermont.gov:80
  22:40:42 DEBUG urllib3.connectionpool: http://legislature.vermont.gov:80 "GET /bill/loadBillsReleased/2026/ HTTP/1.1" 200 11
  22:40:42 INFO scrapelib: GET - 'http://legislature.vermont.gov/bill/loadBillsIntroduced/2026/'
  22:40:43 DEBUG urllib3.connectionpool: http://legislature.vermont.gov:80 "GET /bill/loadBillsIntroduced/2026/ HTTP/1.1" 200 60053
  22:40:43 INFO scrapelib: GET - 'http://legislature.vermont.gov/bill/loadAllResolutionsByChamber/2026/both'
  22:40:43 DEBUG urllib3.connectionpool: http://legislature.vermont.gov:80 "GET /bill/loadAllResolutionsByChamber/2026/both HTTP/1.1" 200 29236
  22:40:43 INFO scrapelib: GET - 'http://legislature.vermont.gov/bill/status/2026/H.1'
  22:40:45 DEBUG urllib3.connectionpool: http://legislature.vermont.gov:80 "GET /bill/status/2026/H.1 HTTP/1.1" 200 16168
  22:40:45 INFO scrapelib: GET - 'http://legislature.vermont.gov/bill/loadBillDetailedStatus/2026/27'
  22:40:45 DEBUG urllib3.connectionpool: http://legislature.vermont.gov:80 "GET /bill/loadBillDetailedStatus/2026/27 HTTP/1.1" 200 2407
  22:40:45 INFO openstates: save bill H 1 in 2025-2026 as bill_1b660098-d57c-11f1-bd3b-0a58a9feac02.json
  22:40:45 DEBUG openstates: {
      "_id": "1b660098-d57c-11f1-bd3b-0a58a9feac02",
      "abstracts": [],
      "actions": [
          {
              "description": "Read first time and referred to the Committee on Government Operations and Military Affairs",
              "date": "2025-01-09",
              "organization_id": "~{\"classification\": \"lower\"}",
              "classification": [
                  "introduction"
              ],
              "related_entities": []
          },
          {
              "description": "Notice Calendar: Favorable with Amendment",
              "date": "2025-03-12",
              "organization_id": "~{\"classification\": \"lower\"}",
              "classification": [],
              "related_entities": []
          },
          {
### last 20 log lines before the report (redacted, upload headers omitted)
                      "url": "http://legislature.vermont.gov/Documents/2026/Docs/ACTS/ACTM001/ACTM001%20As%20Enacted.pdf",
                      "media_type": "application/pdf"
                  }
              ],
              "date": "",
              "classification": ""
          },
          {
              "note": "Act SummaryOpens in a new window",
              "links": [
                  {
                      "url": "http://legislature.vermont.gov/Documents/2026/Docs/ACTS/ACTM001/ACTM001%20Act%20Summary.pdf",
                      "media_type": "application/pdf"
                  }
              ],
              "date": "",
              "classification": ""
          }
      ]
  }
### keyword lines (Traceback, 406, 403, HTTPError, mdb-export, refus, WAF, ERROR): 0


## nm  task da58490c6cdf4bfca4f8b0a5073421e0  (1675 lines in the stream; 1386 before the echoed report)
### first 40 lines (redacted)
  /opt/venv/lib/python3.10/site-packages/google/api_core/_python_version_support.py:242: FutureWarning: You are using a non-supported Python version (3.10.22). Google will not post any further updates to google.api_core supporting t
    warnings.warn(message, FutureWarning)
  22:40:42 DEBUG openstates.stats: Stat emission is not enabled.
  22:40:42 DEBUG urllib3.connectionpool: Starting new HTTPS connection (1): www.nmlegis.gov:443
  22:40:42 DEBUG urllib3.connectionpool: https://www.nmlegis.gov:443 "GET / HTTP/1.1" 200 27934
  22:40:42 DEBUG urllib3.connectionpool: Starting new HTTPS connection (1): www.nmlegis.gov:443
  22:40:43 DEBUG urllib3.connectionpool: https://www.nmlegis.gov:443 "GET / HTTP/1.1" 200 27924
  22:40:43 INFO scrapelib: GET - 'https://www.nmlegis.gov/Sessions/26%20Regular/other/'
  22:40:43 DEBUG urllib3.connectionpool: Starting new HTTPS connection (1): www.nmlegis.gov:443
  /opt/venv/lib/python3.10/site-packages/urllib3/connectionpool.py:1064: InsecureRequestWarning: Unverified HTTPS request is being made to host 'www.nmlegis.gov'. Adding certificate verification is strongly advised. See: https://url
    warnings.warn(
  22:40:43 DEBUG urllib3.connectionpool: https://www.nmlegis.gov:443 "GET /Sessions/26%20Regular/other/ HTTP/1.1" 200 351
  22:40:43 INFO scrapelib: GET - 'https://www.nmlegis.gov/Sessions/26%20Regular/other/LegInfo26.zip'
  /opt/venv/lib/python3.10/site-packages/urllib3/connectionpool.py:1064: InsecureRequestWarning: Unverified HTTPS request is being made to host 'www.nmlegis.gov'. Adding certificate verification is strongly advised. See: https://url
    warnings.warn(
  22:40:44 DEBUG urllib3.connectionpool: https://www.nmlegis.gov:443 "GET /Sessions/26%20Regular/other/LegInfo26.zip HTTP/1.1" 200 4373904
  22:40:45 INFO openstates: Getting doc at https://www.nmlegis.gov/Sessions/26%20Regular/bills/senate/
  22:40:45 INFO scrapelib: GET - 'https://www.nmlegis.gov/Sessions/26%20Regular/bills/senate/'
  /opt/venv/lib/python3.10/site-packages/urllib3/connectionpool.py:1064: InsecureRequestWarning: Unverified HTTPS request is being made to host 'www.nmlegis.gov'. Adding certificate verification is strongly advised. See: https://url
    warnings.warn(
  22:40:46 DEBUG urllib3.connectionpool: https://www.nmlegis.gov:443 "GET /Sessions/26%20Regular/bills/senate/ HTTP/1.1" 200 27865
  22:40:46 WARNING openstates: No match, skipping PREFILE
  22:40:46 INFO openstates: Getting doc at https://www.nmlegis.gov/Sessions/26%20Regular/resolutions/senate/
  22:40:46 INFO scrapelib: GET - 'https://www.nmlegis.gov/Sessions/26%20Regular/resolutions/senate/'
  /opt/venv/lib/python3.10/site-packages/urllib3/connectionpool.py:1064: InsecureRequestWarning: Unverified HTTPS request is being made to host 'www.nmlegis.gov'. Adding certificate verification is strongly advised. See: https://url
    warnings.warn(
  22:40:47 DEBUG urllib3.connectionpool: https://www.nmlegis.gov:443 "GET /Sessions/26%20Regular/resolutions/senate/ HTTP/1.1" 200 966
  22:40:47 INFO openstates: Getting doc at https://www.nmlegis.gov/Sessions/26%20Regular/memorials/senate/
  22:40:47 INFO scrapelib: GET - 'https://www.nmlegis.gov/Sessions/26%20Regular/memorials/senate/'
  /opt/venv/lib/python3.10/site-packages/urllib3/connectionpool.py:1064: InsecureRequestWarning: Unverified HTTPS request is being made to host 'www.nmlegis.gov'. Adding certificate verification is strongly advised. See: https://url
    warnings.warn(
  22:40:48 DEBUG urllib3.connectionpool: https://www.nmlegis.gov:443 "GET /Sessions/26%20Regular/memorials/senate/ HTTP/1.1" 200 2599
  22:40:48 INFO scrapelib: GET - 'https://www.nmlegis.gov/Sessions/26%20Regular/Amendments_In_Context/'
  /opt/venv/lib/python3.10/site-packages/urllib3/connectionpool.py:1064: InsecureRequestWarning: Unverified HTTPS request is being made to host 'www.nmlegis.gov'. Adding certificate verification is strongly advised. See: https://url
    warnings.warn(
  22:40:49 DEBUG urllib3.connectionpool: https://www.nmlegis.gov:443 "GET /Sessions/26%20Regular/Amendments_In_Context/ HTTP/1.1" 200 2501
  22:40:49 INFO scrapelib: GET - 'https://www.nmlegis.gov/Sessions/26%20Regular/firs/'
  /opt/venv/lib/python3.10/site-packages/urllib3/connectionpool.py:1064: InsecureRequestWarning: Unverified HTTPS request is being made to host 'www.nmlegis.gov'. Adding certificate verification is strongly advised. See: https://url
    warnings.warn(
  22:40:50 DEBUG urllib3.connectionpool: https://www.nmlegis.gov:443 "GET /Sessions/26%20Regular/firs/ HTTP/1.1" 200 13254
### last 20 log lines before the report (redacted, upload headers omitted)
      "title": "HEALTH PROFESSIONAL AUTONOMY ACT",
      "versions": [
          {
              "note": "introduced version",
              "links": [
                  {
                      "url": "https://www.nmlegis.gov/Sessions/26%20Regular/bills/senate/SB0016.HTML",
                      "media_type": "text/html"
                  },
                  {
                      "url": "https://www.nmlegis.gov/Sessions/26%20Regular/bills/senate/SB0016.PDF",
                      "media_type": "application/pdf"
                  }
              ],
              "date": "",
              "classification": ""
          }
      ]
  }
  Written to /tmp/probe-nm-plla_9_b/notes/nm-onboarding-probe-20261031.md
### keyword lines (Traceback, 406, 403, HTTPError, mdb-export, refus, WAF, ERROR): 0

