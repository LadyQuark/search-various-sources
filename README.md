## Search and save to JSON
To search all sources for query and get n number of results per source:

```shell
python3 main.py --limit <n>
```

## Search and save to MongoDB
To search all sources for query and get 10 number of results per source:

- Set MongoDB server details in .env
```shell
python3 search_save_mongo.py <file-path> --limit <n>
```