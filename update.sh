sqlite3 /var/lib/printpilot/app.sqlite3 "UPDATE settings SET v = json_set(v, '$.automations.wecom_secret', '3jEHnUDieOkXRQn5lOHjryiU2BnMG0KMHhx70oLV0Ig') WHERE k='app';"
