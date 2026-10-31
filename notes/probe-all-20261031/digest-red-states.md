# RED states: gate failures and log digest (log lines redacted; botocore upload headers omitted)

## ar  task 69fb466cdf68429083f4687bbe55cef4
blocking FAIL gates: D: dry scrape completed but wrote zero objects
keyword lines from the log (max 6):
  none
last 10 log lines before the report (redacted):
  18:40:06 DEBUG openstates.stats: Stat emission is not enabled.
  18:40:06 DEBUG urllib3.connectionpool: https://www.arkleg.state.ar.us:443 "GET /Bills/Search HTTP/1.1" 200 None
  18:40:07 DEBUG urllib3.connectionpool: https://www.arkleg.state.ar.us:443 "GET /Bills/Search HTTP/1.1" 200 None
  18:40:07 INFO scrapelib: GET - 'https://arkleg.state.ar.us/Home/FTPDocument?path=%2FSessionInformation%2FLegislativeMeasures.txt'
  18:40:07 DEBUG urllib3.connectionpool: https://arkleg.state.ar.us:443 "GET /Home/FTPDocument?path=%2FSessionInformation%2FLegislativeMeasures.txt HTTP/1.1" 200 2
  18:40:07 INFO scrapelib: GET - 'https://arkleg.state.ar.us/Home/FTPDocument?path=%2FSessionInformation%2FLegislativeMeasures.txt'
  18:40:08 DEBUG urllib3.connectionpool: https://arkleg.state.ar.us:443 "GET /Home/FTPDocument?path=%2FSessionInformation%2FLegislativeMeasures.txt HTTP/1.1" 200 2
  18:40:08 INFO scrapelib: GET - 'https://arkleg.state.ar.us/Home/FTPDocument?path=%2FSessionInformation%2FChamberActions.txt'
  18:40:09 DEBUG urllib3.connectionpool: https://arkleg.state.ar.us:443 "GET /Home/FTPDocument?path=%2FSessionInformation%2FChamberActions.txt HTTP/1.1" 200 2
  18:40:09 WARNING openstates: ARBillScraper raised EmptyScrape, continuing without any results

## ct  task 8d75dd0854c94542a177f42920a093b8
blocking FAIL gates: D: dry scrape raised: FTPError: error while retrieving ftp://ftp.cga.ct.gov/pub/data/committee.csv
keyword lines from the log (max 6):
  none
last 10 log lines before the report (redacted):
  18:40:07 DEBUG openstates.stats: Stat emission is not enabled.
  18:40:07 DEBUG urllib3.connectionpool: https://search.cga.state.ct.us:443 "GET /r/basic/Fbuttons.asp HTTP/1.1" 200 16605
  18:40:07 DEBUG urllib3.connectionpool: https://search.cga.state.ct.us:443 "GET /r/basic/Fbuttons.asp HTTP/1.1" 200 16605
  18:40:07 INFO scrapelib: GET - 'ftp://ftp.cga.ct.gov/pub/data/committee.csv'
  18:41:07 WARNING scrapelib: got error while retrieving ftp://ftp.cga.ct.gov/pub/data/committee.csv sleeping for 10 seconds before retry
  18:42:17 WARNING scrapelib: got error while retrieving ftp://ftp.cga.ct.gov/pub/data/committee.csv sleeping for 20 seconds before retry
  18:43:37 WARNING scrapelib: got error while retrieving ftp://ftp.cga.ct.gov/pub/data/committee.csv sleeping for 40 seconds before retry

## dc  task 218f1b5a47974fffabb74b98e8cfd222
blocking FAIL gates: A: could not import scraper module 'dc': KeyError: 'DC_API_KEY'
keyword lines from the log (max 6):
  none
last 10 log lines before the report (redacted):
  18:40:07 DEBUG openstates.stats: Stat emission is not enabled.

## il  task 736b38f8b72a4385a60d604c9e90f3ab
blocking FAIL gates: A: get_session_list() raised HTTPError('403 Client Error: Forbidden for url: https://ilga.gov/API/Legislation/GetGeneralAssemblies'); D: dry scrape raised: KeyError: None
keyword lines from the log (max 6):
  18:40:14 DEBUG urllib3.connectionpool: https://ilga.gov:443 "GET /API/Legislation/GetGeneralAssemblies HTTP/1.1" 403 3988
last 10 log lines before the report (redacted):
  18:40:14 DEBUG openstates.stats: Stat emission is not enabled.
  18:40:14 DEBUG urllib3.connectionpool: https://ilga.gov:443 "GET /API/Legislation/GetGeneralAssemblies HTTP/1.1" 403 3988

## in  task 9c559896b2c04c9fb3a1c10b80f77af4
blocking FAIL gates: A: get_session_list() raised KeyError('INDIANA_API_KEY'); D: dry scrape raised: KeyError: 'INDIANA_API_KEY'
keyword lines from the log (max 6):
  none
last 10 log lines before the report (redacted):
  18:40:13 DEBUG openstates.stats: Stat emission is not enabled.

## mn  task 588ea64771f14496b30fc24a8de5590f
blocking FAIL gates: D: dry scrape raised: ScrapeError: no objects returned from MNBillScraper scrape
keyword lines from the log (max 6):
  none
last 10 log lines before the report (redacted):
  18:44:19 INFO scrapelib: GET - 'https://www.revisor.mn.gov/bills/status_result.php?body=Senate&search=topic&session=0942025&topic[]=2457&submit_topic=GO'
  18:44:20 DEBUG urllib3.connectionpool: https://www.revisor.mn.gov:443 "GET /bills/status_result.php?body=Senate&search=topic&session=0942025&topic%5B%5D=2457&submit_topic=GO HTTP/1.1" 200 None
  18:44:20 INFO scrapelib: GET - 'https://www.revisor.mn.gov/bills/status_result.php?body=Senate&search=topic&session=0942025&topic[]=2458&submit_topic=GO'
  18:44:21 DEBUG urllib3.connectionpool: https://www.revisor.mn.gov:443 "GET /bills/status_result.php?body=Senate&search=topic&session=0942025&topic%5B%5D=2458&submit_topic=GO HTTP/1.1" 200 None
  18:44:21 INFO scrapelib: GET - 'https://www.revisor.mn.gov/bills/status_result.php?body=Senate&search=topic&session=0942025&topic[]=2459&submit_topic=GO'
  18:44:22 DEBUG urllib3.connectionpool: https://www.revisor.mn.gov:443 "GET /bills/status_result.php?body=Senate&search=topic&session=0942025&topic%5B%5D=2459&submit_topic=GO HTTP/1.1" 200 None
  18:44:22 INFO scrapelib: GET - 'https://www.revisor.mn.gov/bills/status_result.php?body=Senate&search=topic&session=0942025&topic[]=2460&submit_topic=GO'
  18:44:23 DEBUG urllib3.connectionpool: https://www.revisor.mn.gov:443 "GET /bills/status_result.php?body=Senate&search=topic&session=0942025&topic%5B%5D=2460&submit_topic=GO HTTP/1.1" 200 None
  18:44:23 INFO scrapelib: GET - 'https://www.revisor.mn.gov/bills/status_result.php?body=Senate&search=topic&session=0942025&topic[]=2461&submit_topic=GO'
  18:44:24 DEBUG urllib3.connectionpool: https://www.revisor.mn.gov:443 "GET /bills/status_result.php?body=Senate&search=topic&session=0942025&topic%5B%5D=2461&submit_topic=GO HTTP/1.1" 200 None

## nh  task 27f8a98c25e149a39662179426b7aa85
blocking FAIL gates: D: dry scrape raised: ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
keyword lines from the log (max 6):
  18:41:56 DEBUG urllib3.connectionpool: https://gc.nh.gov:443 "GET /bill_status/legacy/bs2016/bill_docket.aspx?lsr=1166&sy=2026&sortoption=&txtsessionyear=2026 HTTP/1.1" 403 3691
last 10 log lines before the report (redacted):
  18:41:54 WARNING openstates: Missing version_id for SB298, can't build bill page
  18:41:54 INFO scrapelib: GET - 'https://gc.nh.gov/bill_status/legacy/bs2016/bill_docket.aspx?lsr=1166&sy=2026&sortoption=&txtsessionyear=2026'
  18:41:55 DEBUG urllib3.connectionpool: https://gc.nh.gov:443 "GET /bill_status/legacy/bs2016/bill_docket.aspx?lsr=1166&sy=2026&sortoption=&txtsessionyear=2026 HTTP/1.1" 200 2725
  18:41:55 INFO openstates: Retrying fetch of docket page, try number 2
  18:41:55 INFO scrapelib: GET - 'https://gc.nh.gov/bill_status/legacy/bs2016/bill_docket.aspx?lsr=1166&sy=2026&sortoption=&txtsessionyear=2026'
  18:41:56 DEBUG urllib3.connectionpool: https://gc.nh.gov:443 "GET /bill_status/legacy/bs2016/bill_docket.aspx?lsr=1166&sy=2026&sortoption=&txtsessionyear=2026 HTTP/1.1" 403 3691
  18:41:56 WARNING scrapelib: sleeping for 10 seconds before retry
  18:42:06 DEBUG urllib3.connectionpool: Resetting dropped connection: gc.nh.gov
  18:42:06 WARNING scrapelib: got ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')) sleeping for 20 seconds before retry
  18:42:26 WARNING scrapelib: got ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')) sleeping for 40 seconds before retry

## nj  task 0e36edad4d894538871cec6a4d3ec6f5
blocking FAIL gates: D: dry scrape raised: ScrapeError: no objects returned from NJBillScraper scrape
keyword lines from the log (max 6):
  none
last 10 log lines before the report (redacted):
  18:40:57 WARNING openstates: No such file: S2026End.txt
  18:40:57 INFO scrapelib: GET - 'https://pub.njleg.state.nj.us/votes/S2027.zip'
  18:40:57 DEBUG urllib3.connectionpool: https://pub.njleg.state.nj.us:443 "GET /votes/S2027.zip HTTP/1.1" 404 1245
  18:40:57 WARNING openstates: could not find https://pub.njleg.state.nj.us/votes/S2027.zip
  18:40:57 INFO scrapelib: GET - 'https://pub.njleg.state.nj.us/votes/CA2026-2027.zip'
  18:40:58 DEBUG urllib3.connectionpool: https://pub.njleg.state.nj.us:443 "GET /votes/CA2026-2027.zip HTTP/1.1" 200 68045
  18:40:59 WARNING openstates: No such file: CA2026-2027End.txt
  18:40:59 INFO scrapelib: GET - 'https://pub.njleg.state.nj.us/votes/CS2026-2027.zip'
  18:40:59 DEBUG urllib3.connectionpool: https://pub.njleg.state.nj.us:443 "GET /votes/CS2026-2027.zip HTTP/1.1" 200 47150
  18:41:00 WARNING openstates: No such file: CS2026-2027End.txt

## nm  task 7df0d2fdf8a749eebdaf39b54e27aa7e
blocking FAIL gates: D: dry scrape raised: FileNotFoundError: [Errno 2] No such file or directory: 'mdb-export'
keyword lines from the log (max 6):
  none
last 10 log lines before the report (redacted):
  18:40:54 DEBUG openstates.stats: Stat emission is not enabled.
  18:40:55 DEBUG urllib3.connectionpool: https://www.nmlegis.gov:443 "GET / HTTP/1.1" 200 27991
  18:40:55 DEBUG urllib3.connectionpool: https://www.nmlegis.gov:443 "GET / HTTP/1.1" 200 27941
  18:40:55 INFO scrapelib: GET - 'https://www.nmlegis.gov/Sessions/26%20Regular/other/'
  18:40:56 DEBUG urllib3.connectionpool: https://www.nmlegis.gov:443 "GET /Sessions/26%20Regular/other/ HTTP/1.1" 200 351
  18:40:56 INFO scrapelib: GET - 'https://www.nmlegis.gov/Sessions/26%20Regular/other/LegInfo26.zip'
  18:40:57 DEBUG urllib3.connectionpool: https://www.nmlegis.gov:443 "GET /Sessions/26%20Regular/other/LegInfo26.zip HTTP/1.1" 200 4373904
  18:40:57 WARNING openstates: Failed to read mdb file. Have you installed 'mdbtools' ?

## ny  task 0c78b3674d43480493b61c824246bb0b
blocking FAIL gates: A: get_session_list() raised KeyError('NEW_YORK_API_KEY'); D: dry scrape raised: KeyError: 'NEW_YORK_API_KEY'
keyword lines from the log (max 6):
  none
last 10 log lines before the report (redacted):
  18:40:59 DEBUG openstates.stats: Stat emission is not enabled.

## tn  task 230b342146fb4d3782aecba51c9e066a
blocking FAIL gates: D: dry scrape raised: IndexError: list index out of range
keyword lines from the log (max 6):
  none
last 10 log lines before the report (redacted):
  18:41:32 DEBUG openstates.stats: Stat emission is not enabled.
  18:41:32 DEBUG urllib3.connectionpool: https://www.capitol.tn.gov:443 "GET /legislation/archives.html HTTP/1.1" 200 53047
  18:41:33 DEBUG urllib3.connectionpool: https://wapp.capitol.tn.gov:443 "GET /apps/Indexes/BillsByIndex HTTP/1.1" 200 None
  18:41:33 DEBUG urllib3.connectionpool: https://www.capitol.tn.gov:443 "GET /legislation/archives.html HTTP/1.1" 200 53047
  18:41:33 DEBUG urllib3.connectionpool: https://wapp.capitol.tn.gov:443 "GET /apps/Indexes/BillsByIndex HTTP/1.1" 200 None
  18:41:33 INFO scrapelib: GET - 'https://wapp.capitol.tn.gov/apps/Indexes/SpecialSessionBillIndex?ga=114&specsessNum=1'
  18:41:33 DEBUG urllib3.connectionpool: https://wapp.capitol.tn.gov:443 "GET /apps/Indexes/SpecialSessionBillIndex?ga=114&specsessNum=1 HTTP/1.1" 200 None
  18:41:33 INFO scrapelib: GET - 'https://wapp.capitol.tn.gov/apps/BillInfo/Default?BillNumber=HB6001&ga=114'
  18:41:34 DEBUG urllib3.connectionpool: https://wapp.capitol.tn.gov:443 "GET /apps/BillInfo/Default?BillNumber=HB6001&ga=114 HTTP/1.1" 200 None

## tx  task d64d0128cea2455e9164b35c1f4adcfe
blocking FAIL gates: D: dry scrape raised: TimeoutError: [Errno 110] Connection timed out
keyword lines from the log (max 6):
  none
last 10 log lines before the report (redacted):
  18:41:33 DEBUG openstates.stats: Stat emission is not enabled.
  18:41:33 DEBUG urllib3.connectionpool: https://capitol.texas.gov:443 "GET / HTTP/1.1" 200 11161
  18:41:33 DEBUG urllib3.connectionpool: https://capitol.texas.gov:443 "GET / HTTP/1.1" 200 11161

## wi  task 55454bbb311a41feaa84e95db541c72c
blocking FAIL gates: D: dry scrape raised: HTTPError: 429 while retrieving https://docs.legis.wisconsin.gov/2025/related/fe/my6_sb1
keyword lines from the log (max 6):
  none
last 10 log lines before the report (redacted):
  18:46:09 WARNING scrapelib: sleeping for 20 seconds before retry
  18:46:29 DEBUG urllib3.connectionpool: Resetting dropped connection: docs.legis.wisconsin.gov
  18:46:29 DEBUG urllib3.connectionpool: https://docs.legis.wisconsin.gov:443 "GET /document/fiscalestimates/2025/MY6/SB1 HTTP/1.1" 302 141
  18:46:29 DEBUG urllib3.connectionpool: Resetting dropped connection: docs.legis.wisconsin.gov
  18:46:29 DEBUG urllib3.connectionpool: https://docs.legis.wisconsin.gov:443 "GET /2025/related/fe/my6_sb1 HTTP/1.1" 429 134
  18:46:29 WARNING scrapelib: sleeping for 40 seconds before retry
  18:47:09 DEBUG urllib3.connectionpool: Resetting dropped connection: docs.legis.wisconsin.gov
  18:47:09 DEBUG urllib3.connectionpool: https://docs.legis.wisconsin.gov:443 "GET /document/fiscalestimates/2025/MY6/SB1 HTTP/1.1" 302 141
  18:47:09 DEBUG urllib3.connectionpool: Resetting dropped connection: docs.legis.wisconsin.gov
  18:47:10 DEBUG urllib3.connectionpool: https://docs.legis.wisconsin.gov:443 "GET /2025/related/fe/my6_sb1 HTTP/1.1" 429 134
