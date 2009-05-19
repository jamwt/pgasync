#!/bin/sh

# Run as postgresql superuser

psql -c "create user pgasync_testuser with password 'pgasync_testpass'"
createdb -O pgasync_testuser pgasync_testdb
