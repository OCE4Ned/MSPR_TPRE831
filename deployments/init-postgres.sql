CREATE DATABASE airflow;
CREATE USER etl_writer WITH PASSWORD 'xxx';
GRANT CONNECT ON DATABASE industrial_dw TO etl_writer;
GRANT USAGE, CREATE ON SCHEMA public TO etl_writer;
