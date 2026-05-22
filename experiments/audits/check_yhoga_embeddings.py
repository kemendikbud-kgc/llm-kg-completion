"""Check whether Yhoga upstream Concepts actually have embeddings."""
import os, sys, json
from neo4j import GraphDatabase

# Hard-coded from .mcp.json (this script is for one-off verification only)
URI = 'neo4j+ssc://772674a6.databases.neo4j.io'
USER = '772674a6'
PWD = 'dCFp5Cik9D0JMfo_cL7WenO5K9zDb_w7n3HegK8jeJo'
DB = '772674a6'

driver = GraphDatabase.driver(URI, auth=(USER, PWD))

with driver.session(database=DB) as s:
    # 1. Total counts by label
    print('=== NODE COUNTS BY LABEL ===')
    for r in s.run('MATCH (n) RETURN labels(n)[0] AS label, count(n) AS n ORDER BY n DESC'):
        print(f'  {r["label"]:20} {r["n"]:>6}')

    # 2. Concept-specific: how many have a non-null embedding property
    print('\n=== Concept.embedding COVERAGE ===')
    rows = list(s.run('''
        MATCH (c:Concept)
        WITH c, c.embedding AS emb
        RETURN
          count(c) AS total,
          count(emb) AS with_embedding,
          count(CASE WHEN emb IS NOT NULL AND size(emb) > 0 THEN 1 END) AS with_nonempty,
          collect(DISTINCT CASE WHEN emb IS NOT NULL THEN size(emb) END)[..5] AS dims_sample
    '''))
    if rows:
        r = rows[0]
        print(f'  total Concepts        : {r["total"]}')
        print(f'  with embedding prop   : {r["with_embedding"]}')
        print(f'  with non-empty vector : {r["with_nonempty"]}')
        print(f'  embedding dims observed: {r["dims_sample"]}')

    # 3. Are there model-tag properties? (yours uses last_embed_model)
    print('\n=== Concept.last_embed_model values ===')
    rows = list(s.run('''
        MATCH (c:Concept)
        WITH c.last_embed_model AS model, count(*) AS n
        RETURN model, n ORDER BY n DESC LIMIT 10
    '''))
    if not rows:
        print('  no last_embed_model property on any Concept')
    for r in rows:
        print(f'  {r["model"] or "<null>":40} {r["n"]:>6}')

    # 4. Check ConceptTarget and other potentially-embedded labels
    print('\n=== embedding coverage by label ===')
    for label in ['Concept', 'ConceptTarget', 'Subtopic', 'Chapter', 'Grade']:
        rows = list(s.run(
            f'MATCH (n:{label}) RETURN count(n) AS total, '
            f'count(n.embedding) AS with_emb'
        ))
        if rows:
            r = rows[0]
            print(f'  {label:15} total={r["total"]:>6}  with embedding={r["with_emb"]:>6}')

    # 5. List vector indexes
    print('\n=== VECTOR INDEXES ===')
    for r in s.run('SHOW VECTOR INDEXES'):
        d = dict(r)
        print(f'  name={d.get("name")}  state={d.get("state")}  '
              f'labels={d.get("labelsOrTypes")}  props={d.get("properties")}  '
              f'dim={d.get("options", {}).get("indexConfig", {}).get("vector.dimensions")}  '
              f'sim={d.get("options", {}).get("indexConfig", {}).get("vector.similarity_function")}')

    # 6. Spot-check: sample 3 concepts to see the embedding structure
    print('\n=== SAMPLE Concept (1 record, embedding head + length) ===')
    rows = list(s.run('''
        MATCH (c:Concept) WHERE c.embedding IS NOT NULL
        RETURN c.name AS name, c.grade AS grade,
               size(c.embedding) AS dim,
               c.embedding[..3] AS head
        LIMIT 1
    '''))
    for r in rows:
        print(f'  name={r["name"]!r}  grade={r["grade"]!r}  dim={r["dim"]}  '
              f'head={r["head"]}')

    # 7. SIMILAR_TO edges present? Would indicate completion was already run
    print('\n=== SIMILAR_TO edges ===')
    rows = list(s.run('MATCH ()-[r:SIMILAR_TO]->() RETURN count(r) AS n'))
    print(f'  count: {rows[0]["n"]}')

    # 8. LINTAS_BUKU_* edges?
    print('\n=== LINTAS_BUKU_* edges ===')
    rows = list(s.run('''
        MATCH ()-[r]->() WHERE type(r) STARTS WITH 'LINTAS_BUKU'
        RETURN type(r) AS t, count(r) AS n ORDER BY n DESC
    '''))
    if not rows:
        print('  none — completion not yet replayed')
    for r in rows:
        print(f'  {r["t"]:40} {r["n"]:>6}')

driver.close()
