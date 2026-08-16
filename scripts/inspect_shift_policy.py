from app.retrieval.vector_store import _get_cached_chroma_resources

client, col = _get_cached_chroma_resources()
res = col.get(where={"policy_name": "Shift Allowance Policy"})

print(f"Total chunks in Shift Allowance Policy: {len(res['documents'])}")
for i, (doc, meta) in enumerate(zip(res['documents'], res['metadatas'])):
    print(f"\n--- Chunk {i+1} (Page {meta.get('page')}) ---")
    print(doc)
