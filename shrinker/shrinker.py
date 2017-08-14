#!/usr/bin/env python

import sys
import re
from pprint import pprint

from elasticsearch import Elasticsearch

endpoint = sys.argv[1]
work_node = sys.argv[2]
pattern = sys.argv[3]
tgt_num_of_shards = int(sys.argv[4])
tgt_num_of_replicas = int(sys.argv[5])

es = Elasticsearch([endpoint], timeout=120)

indices = es.cat.indices(index=pattern, format="json")

open_indices = []
closed_indices = []

for index in indices:
  if index['index'].startswith('shrunk-'):
    continue
  elif index['status'] == 'close':
    closed_indices.append(index['index'])
  else:
    if int(index['pri']) == tgt_num_of_shards:
      continue
    open_indices.append(index['index'])

print("Shrinking the following open indices:")
pprint(open_indices)
print("And closed indices:")
pprint(closed_indices)
print("To %d shards" % (tgt_num_of_shards))

process_indices = open_indices + closed_indices

for index in process_indices:
  if index in closed_indices:
    es.indices.open(index)
    es.cluster.health(index, wait_for_status="yellow")
    i = es.cat.indices(index=index, format="json")
    primary_shards = int(i[0]['pri'])
    print("After opening %s, it had %d shards" % (index, primary_shards))
    if primary_shards == tgt_num_of_shards:
      print("  => skip.")
      es.indices.close(index)
      continue
  else:
    print("Starting work on %s..." % index)

  prepare_settings = {
    'index.routing.allocation.require._name': work_node,
    'index.blocks.write': True
  }
  print("  => put_settings" % index)
  es.indices.put_settings(body=prepare_settings, index=index)
  print("  => waiting to relocate...", end="")
  es.cluster.health(index, wait_for_no_relocating_shards=True, master_timeout=300, timeout=300)
  print(" ok")

  shrunk_index = "shrunk-%s" % index
  shrink_settings = {
    'settings': {
      'index.number_of_replicas': tgt_num_of_replicas,
      'index.number_of_shards': tgt_num_of_shards,
      'index.codec': 'best_compression'
    }
  }
  print("  => shrink")
  es.indices.shrink(index, target=shrunk_index, body=shrink_settings)
  print("  => waiting...", end="")
  es.cluster.health(shrunk_index, wait_for_status="yellow", master_timeout=300, timeout=300)
  print(" ok")

  print("  => shrink done; proceeding with alias")

  es.indices.update_aliases(body={
    'actions': [
      { 'add': { 'index': shrunk_index, 'alias': index } },
      { 'remove_index': { 'index': index } }
    ]
  })

  if index in closed_indices:
    es.indices.close(index)

  print("  => done")
