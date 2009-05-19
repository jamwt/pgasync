#!/bin/sh

echo "Attempting to set up database."
echo "Please make sure you execute this script as 'postgres' or"
echo "whatever you call the PostgreSQL database owner."

echo ""
echo ""

echo -n "Creating database:"
createdb wiki

echo ""
echo -n "Creating user:"
psql -c "create user wiki with password 'wiki'" wiki

echo ""
echo -n "Creating pages table:"
psql -c "create table pages (name varchar(100), contents text)" wiki

echo ""
echo -n "Granting permission to user:"
psql -c "grant select,insert,update on pages to wiki " wiki

echo ""
echo ""

echo "Database is ready."
