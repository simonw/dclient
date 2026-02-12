# dclient - Datasette CLI Client Demo

*2026-02-12T00:32:10Z*

This demo exercises dclient's new commands against a live Datasette instance with a mutable in-memory database.

## Create a Table

```bash
uv run dclient create-table http://127.0.0.1:8042/demo dogs --column id integer --column name text --column age integer --column breed text --pk id --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTYzMDR9.sS2CL5TE8hnxhyI1sOHvyFTA5d4
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

## Insert Data from CSV

```bash
cat /tmp/dogs.csv | uv run dclient insert http://127.0.0.1:8042/demo dogs - --csv --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTYzMDR9.sS2CL5TE8hnxhyI1sOHvyFTA5d4
```

```output
```

## List Databases

```bash
uv run dclient databases http://127.0.0.1:8042 --table --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTYzMDR9.sS2CL5TE8hnxhyI1sOHvyFTA5d4
```

```output
name     path  is_mutable
-------  ----  ----------
_memory        False     
demo           True      
```

## List Tables

```bash
uv run dclient tables http://127.0.0.1:8042/demo --table --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTYzMDR9.sS2CL5TE8hnxhyI1sOHvyFTA5d4
```

```output
name  rows  columns             
----  ----  --------------------
dogs  5     id, name, age, breed
```

## View Schema

```bash
uv run dclient schema http://127.0.0.1:8042/demo --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTYzMDR9.sS2CL5TE8hnxhyI1sOHvyFTA5d4
```

```output
CREATE TABLE [dogs] (
   [id] INTEGER PRIMARY KEY,
   [name] TEXT,
   [age] INTEGER,
   [breed] TEXT
);
```

## Browse Rows

```bash
uv run dclient rows http://127.0.0.1:8042/demo/dogs --table --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTYzMDR9.sS2CL5TE8hnxhyI1sOHvyFTA5d4
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

Filter to dogs older than 4.

```bash
uv run dclient rows http://127.0.0.1:8042/demo/dogs --table -w age__gt=4 --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTYzMDR9.sS2CL5TE8hnxhyI1sOHvyFTA5d4
```

```output
id  name  age  breed           
--  ----  ---  ----------------
1   Cleo  5    Golden Retriever
3   Fido  7    Labrador        
```

Sort by age descending.

```bash
uv run dclient rows http://127.0.0.1:8042/demo/dogs --table --sort-desc age --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTYzMDR9.sS2CL5TE8hnxhyI1sOHvyFTA5d4
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

Export selected columns as CSV.

```bash
uv run dclient rows http://127.0.0.1:8042/demo/dogs --csv --col name --col breed --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTYzMDR9.sS2CL5TE8hnxhyI1sOHvyFTA5d4
```

```output
id,name,breed
1,Cleo,Golden Retriever
2,Pancakes,Poodle
3,Fido,Labrador
4,Muffin,Corgi
5,Rex,German Shepherd
```

## Get a Single Row by Primary Key

```bash
uv run dclient get http://127.0.0.1:8042/demo/dogs 3 --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTYzMDR9.sS2CL5TE8hnxhyI1sOHvyFTA5d4
```

```output
{
  "id": 3,
  "name": "Fido",
  "age": 7,
  "breed": "Labrador"
}
```

## SQL Queries with Output Formats

```bash
uv run dclient query http://127.0.0.1:8042/demo 'select breed, count(*) as count from dogs group by breed order by count desc' --table --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTYzMDR9.sS2CL5TE8hnxhyI1sOHvyFTA5d4
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

## Update a Row

```bash
uv run dclient update http://127.0.0.1:8042/demo/dogs 3 name=Buddy age=8 --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTYzMDR9.sS2CL5TE8hnxhyI1sOHvyFTA5d4
```

```output
{
  "ok": true
}
```

Verify the update.

```bash
uv run dclient get http://127.0.0.1:8042/demo/dogs 3 --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTYzMDR9.sS2CL5TE8hnxhyI1sOHvyFTA5d4
```

```output
{
  "id": 3,
  "name": "Buddy",
  "age": 8,
  "breed": "Labrador"
}
```

## Upsert (Insert or Update)

```bash
cat /tmp/upsert.json | uv run dclient upsert http://127.0.0.1:8042/demo dogs - --json --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTYzMDR9.sS2CL5TE8hnxhyI1sOHvyFTA5d4
```

```output
```

Cleo's age is now 6, and Luna was added.

```bash
uv run dclient rows http://127.0.0.1:8042/demo/dogs --table --sort id --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTYzMDR9.sS2CL5TE8hnxhyI1sOHvyFTA5d4
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

## Delete a Row

```bash
uv run dclient delete http://127.0.0.1:8042/demo/dogs 4 --yes --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTYzMDR9.sS2CL5TE8hnxhyI1sOHvyFTA5d4
```

```output
{
  "ok": true
}
```

Muffin (id=4) is gone.

```bash
uv run dclient rows http://127.0.0.1:8042/demo/dogs --table --sort id --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTYzMDR9.sS2CL5TE8hnxhyI1sOHvyFTA5d4
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

## Drop a Table

```bash
uv run dclient drop http://127.0.0.1:8042/demo/dogs --yes --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTYzMDR9.sS2CL5TE8hnxhyI1sOHvyFTA5d4
```

```output
{
  "ok": true
}
```

The dogs table no longer exists.

```bash
uv run dclient tables http://127.0.0.1:8042/demo --table --token dstok_eyJhIjoicm9vdCIsInQiOjE3NzA4NTYzMDR9.sS2CL5TE8hnxhyI1sOHvyFTA5d4
```

```output
```
