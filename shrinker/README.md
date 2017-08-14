# shrinker

Shrink indices.

## Usage

```
$ shrinker.py 127.0.0.1:9300 node-name "logstash-*" 1 0
```

Will shrink all indices on the Elasticsearch cluster accessible to "127.0.0.1:9300"
matching the pattern `logstash-*` (note the quotes) to one shard and one replica. See
[the Shrink Index API docs](https://www.elastic.co/guide/en/elasticsearch/reference/5.5/indices-shrink-index.html)
for more information. In this example, all operations will be processed on the
node called "node-name".

## Note

Indices will be read-only during the shrink operation.
