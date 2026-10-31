
## Tasks that crashed before uploading anything (no result.json)
### ca  task 436e0a9e2967405c829496d1f28f2f36  (28 lines, last event see CloudWatch)
full traceback and what preceded it (redacted):
  18:40:10 DEBUG urllib3.connectionpool: Starting new HTTPS connection (1): www.leginfo.ca.gov:443
  18:40:10 DEBUG urllib3.connectionpool: https://www.leginfo.ca.gov:443 "GET /bilinfo.html HTTP/1.1" 200 None
  Traceback (most recent call last):
    File "/app/verify-jurisdiction", line 1522, in <module>
      sys.exit(main())
    File "/app/verify-jurisdiction", line 1450, in main
      gate_d_result, bill_files, _scrape_report = run_gate_d(
    File "/app/verify-jurisdiction", line 580, in run_gate_d
      scraper = bills_cls(juris, datadir, strict_validation=False)
    File "/opt/openstates-scrapers/scrapers/ca/bills.py", line 220, in __init__
      self.engine = create_engine(conn_str)
    File "<string>", line 2, in create_engine
    File "/opt/venv/lib/python3.10/site-packages/sqlalchemy/util/deprecations.py", line 375, in warned
      return fn(*args, **kwargs)
    File "/opt/venv/lib/python3.10/site-packages/sqlalchemy/engine/create.py", line 544, in create_engine
      dbapi = dialect_cls.dbapi(**dbapi_args)
    File "/opt/venv/lib/python3.10/site-packages/sqlalchemy/dialects/mysql/mysqldb.py", line 150, in dbapi
      return __import__("MySQLdb")
  ModuleNotFoundError: No module named 'MySQLdb'
### vt  task 73b8998365524231bebe85489c167491  (15 lines, last event see CloudWatch)
full traceback and what preceded it (redacted):
  18:41:37 DEBUG urllib3.connectionpool: Starting new HTTP connection (1): legislature.vermont.gov:80
  18:41:38 DEBUG urllib3.connectionpool: http://legislature.vermont.gov:80 "GET /bill/search/2016 HTTP/1.1" 200 14808
  Traceback (most recent call last):
    File "/app/verify-jurisdiction", line 1522, in <module>
      sys.exit(main())
    File "/app/verify-jurisdiction", line 1401, in main
      results.append(run_gate_a(juris, module_name))
    File "/app/verify-jurisdiction", line 421, in run_gate_a
      f"{len(scraped_sessions)} scraped session(s), {len(active_sessions)} active",
  TypeError: object of type 'generator' has no len()
