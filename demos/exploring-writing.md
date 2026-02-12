# Exploring and Writing Data with dclient

*2026-02-12T01:33:47Z*

This demo walks through dclient's data exploration and write commands against a live Datasette instance running on localhost with a mutable in-memory database called `demo`.

## Creating a table

`create-table` creates an empty table with an explicit schema. We define columns and a primary key up front.

```bash
uv run dclient create-table http://127.0.0.1:8042/demo dogs --column id integer --column name text --column age integer --column breed text --pk id --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTk5ODJ9.1KDQjswLBzm5-R-MLmopOIHRZls
```

```output
{
  "ok": true,
  "database": "demo",
  "table": "dogs",
  "table_url": "http://127.0.0.1:8042/demo/dogs",
  "table_api_url": "http://127.0.0.1:8042/demo/dogs.json",
  "schema": "CREATE TABLE [dogs] (\n   [id] INTEGER PRIMARY KEY,\n   [name] TEXT,\n   [age] INTEGER,\n   [breed] TEXT\n)"
}
```

## Inserting rows from CSV

`insert` reads CSV (or TSV, JSON, newline-delimited JSON) from a file or stdin. Here we pipe a CSV file in.

```bash
cat /tmp/dogs.csv | uv run dclient insert http://127.0.0.1:8042/demo dogs - --csv --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTk5ODJ9.1KDQjswLBzm5-R-MLmopOIHRZls
```

```output
```

## Listing databases

`databases` lists every database on the instance. The `--table` flag formats the output as a text table.

```bash
uv run dclient databases http://127.0.0.1:8042 --table --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTk5ODJ9.1KDQjswLBzm5-R-MLmopOIHRZls
```

```output
name     path  is_mutable
-------  ----  ----------
_memory        False     
demo           True      
```

## Listing tables

`tables` shows all tables in a database with row counts and column names.

```bash
uv run dclient tables http://127.0.0.1:8042/demo --table --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTk5ODJ9.1KDQjswLBzm5-R-MLmopOIHRZls
```

```output
name  rows  columns             
----  ----  --------------------
dogs  5     id, name, age, breed
```

## Viewing the schema

`schema` prints the CREATE TABLE SQL for every table in the database.

```bash
uv run dclient schema http://127.0.0.1:8042/demo --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTk5ODJ9.1KDQjswLBzm5-R-MLmopOIHRZls
```

```output
CREATE TABLE [dogs] (
   [id] INTEGER PRIMARY KEY,
   [name] TEXT,
   [age] INTEGER,
   [breed] TEXT
);
```

## Browsing rows

`rows` lets you explore table data without writing SQL. The default output is JSON; `--table` renders a text table.

```bash
uv run dclient rows http://127.0.0.1:8042/demo/dogs --table --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTk5ODJ9.1KDQjswLBzm5-R-MLmopOIHRZls
```

```output
id  name      age  breed           
--  --------  ---  ----------------
1   Cleo      5    Golden Retriever
2   Pancakes  3    Poodle          
3   Fido      7    Labrador        
4   Muffin    2    Corgi           
5   Rex       4    German Shepherd 
```

### Filtering

Use `-w` to filter using Datasette's column operators (`__gt`, `__contains`, `__exact`, etc.).

```bash
uv run dclient rows http://127.0.0.1:8042/demo/dogs --table -w age__gt=4 --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTk5ODJ9.1KDQjswLBzm5-R-MLmopOIHRZls
```

```output
id  name  age  breed           
--  ----  ---  ----------------
1   Cleo  5    Golden Retriever
3   Fido  7    Labrador        
```

### Sorting

`--sort` and `--sort-desc` control row order.

```bash
uv run dclient rows http://127.0.0.1:8042/demo/dogs --table --sort-desc age --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTk5ODJ9.1KDQjswLBzm5-R-MLmopOIHRZls
```

```output
id  name      age  breed           
--  --------  ---  ----------------
3   Fido      7    Labrador        
1   Cleo      5    Golden Retriever
5   Rex       4    German Shepherd 
2   Pancakes  3    Poodle          
4   Muffin    2    Corgi           
```

### Selecting columns

`--col` picks specific columns. Here we also output as CSV, which is handy for piping into other tools.

```bash
uv run dclient rows http://127.0.0.1:8042/demo/dogs --csv --col name --col breed --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTk5ODJ9.1KDQjswLBzm5-R-MLmopOIHRZls
```

```output
id,name,breed
1,Cleo,Golden Retriever
2,Pancakes,Poodle
3,Fido,Labrador
4,Muffin,Corgi
5,Rex,German Shepherd
```

### Limiting results

`--limit` caps the total number of rows returned.

```bash
uv run dclient rows http://127.0.0.1:8042/demo/dogs --table --limit 2 --sort age --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTk5ODJ9.1KDQjswLBzm5-R-MLmopOIHRZls
```

```output
id  name      age  breed 
--  --------  ---  ------
4   Muffin    2    Corgi 
2   Pancakes  3    Poodle
```

## Fetching a single row

`get` retrieves one row by its primary key.

```bash
uv run dclient get http://127.0.0.1:8042/demo/dogs 3 --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTk5ODJ9.1KDQjswLBzm5-R-MLmopOIHRZls
```

```output
{
  "id": 3,
  "name": "Fido",
  "age": 7,
  "breed": "Labrador"
}
```

## Running SQL queries

`query` executes arbitrary SQL and returns results. Here we use `--table` for a readable summary.

```bash
uv run dclient query http://127.0.0.1:8042/demo 'select breed, count(*) as count from dogs group by breed order by count desc' --table --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTk5ODJ9.1KDQjswLBzm5-R-MLmopOIHRZls
```

```output
breed             count
----------------  -----
Poodle            1    
Labrador          1    
Golden Retriever  1    
German Shepherd   1    
Corgi             1    
```

The same query as newline-delimited JSON, useful for streaming into `jq` or other line-oriented tools.

```bash
uv run dclient query http://127.0.0.1:8042/demo 'select name, age from dogs order by age desc limit 3' --nl --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTk5ODJ9.1KDQjswLBzm5-R-MLmopOIHRZls
```

```output
{"name": "Fido", "age": 7}
{"name": "Cleo", "age": 5}
{"name": "Rex", "age": 4}
```

## Updating a row

`update` modifies a single row by primary key. Pass column=value pairs as arguments. Numeric values are auto-detected.

```bash
uv run dclient update http://127.0.0.1:8042/demo/dogs 3 name=Buddy age=8 --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTk5ODJ9.1KDQjswLBzm5-R-MLmopOIHRZls
```

```output
{
  "ok": true
}
```

Verify the update:

```bash
uv run dclient get http://127.0.0.1:8042/demo/dogs 3 --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTk5ODJ9.1KDQjswLBzm5-R-MLmopOIHRZls
```

```output
{
  "id": 3,
  "name": "Buddy",
  "age": 8,
  "breed": "Labrador"
}
```

## Upserting rows

`upsert` inserts new rows and updates existing ones that match by primary key. Here we update Cleo's age to 6 and add a new dog Luna, all in one call.

```bash
cat /tmp/upsert_dogs.json | uv run dclient upsert http://127.0.0.1:8042/demo dogs - --json --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTk5ODJ9.1KDQjswLBzm5-R-MLmopOIHRZls
```

```output
```

The table now shows Cleo at age 6 and the new row for Luna:

```bash
uv run dclient rows http://127.0.0.1:8042/demo/dogs --table --sort id --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTk5ODJ9.1KDQjswLBzm5-R-MLmopOIHRZls
```

```output
id  name      age  breed           
--  --------  ---  ----------------
1   Cleo      6    Golden Retriever
2   Pancakes  3    Poodle          
3   Buddy     8    Labrador        
4   Muffin    2    Corgi           
5   Rex       4    German Shepherd 
6   Luna      1    Husky           
```

## Deleting a row

`delete` removes a row by primary key. Use `--yes` to skip the confirmation prompt.

```bash
uv run dclient delete http://127.0.0.1:8042/demo/dogs 4 --yes --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTk5ODJ9.1KDQjswLBzm5-R-MLmopOIHRZls
```

```output
{
  "ok": true
}
```

Muffin (id=4) is gone:

```bash
uv run dclient rows http://127.0.0.1:8042/demo/dogs --table --sort id --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTk5ODJ9.1KDQjswLBzm5-R-MLmopOIHRZls
```

```output
id  name      age  breed           
--  --------  ---  ----------------
1   Cleo      6    Golden Retriever
2   Pancakes  3    Poodle          
3   Buddy     8    Labrador        
5   Rex       4    German Shepherd 
6   Luna      1    Husky           
```

## Dropping a table

`drop` removes an entire table. Without `--yes` it shows the row count and asks for confirmation.

```bash
uv run dclient drop http://127.0.0.1:8042/demo/dogs --yes --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTk5ODJ9.1KDQjswLBzm5-R-MLmopOIHRZls
```

```output
{
  "ok": true
}
```

The table is gone:

```bash
uv run dclient tables http://127.0.0.1:8042/demo --json --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTk5ODJ9.1KDQjswLBzm5-R-MLmopOIHRZls
```

```output
[]
```
