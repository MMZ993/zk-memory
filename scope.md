this is a project that will implement a long term memory system for AI agents

memory will be based on zettle kasten notes system

main "logic" (by logic i mean connections) will be acieved by using relational DB (we can use sqlite for simplicity)

together with notes in relation DB, we need to have a vecotr DB that will hold embedings and IDs (links to table with notes in relation db)

notes should be atomic - because we do embeddings (and probably is better to keep a whole note content as embeding) notes should not be to big - big notes should be split in to multiple notes

so we have notes, links, and i woul propose to have also tags, my proposal for schema is:

tables:
 -  notes
   - id (UUID) primary key
   - title
   - content
   - summary (not sure if needed, and if so, it it should be embeded) - maybe it will complicate our note too much
   - created_at
   - updated_at (not sure yet if we should go with a update way, more about it later)
   - embedding - this will be accually keep in separate db linked via id (UUID)

 - links
   - id 
   - source_id
   - target_id
   - relation_type 
   - description (not sure if needed if we have realation type)

 - tags
  - id 
  - name

 - note_tags (links tags to notes)
  - note_id
  - tag_id 



and this is a base idea, there is also another idea, to do not have a updated, and keep all in DB for a history records (not sure if its really needed), then we can have same note (same title), but with a different created_at, and we will handle with sql queries to get only the newest one - for the embeddings we will probably remove old one from embedings - or remove from a returned results - or mark it as a outdated / change to newest automatically

so this topic is to be discussed

and there is also one more thing, i would like to have a copy of all notes in a form of a markdown files (obsidian compatibile if possible, or wiki js) 

makrdown files are mostly for user - me - i prefer to use vim, grep and fuzzy find for notes

but with markdown files we need a system to keep notes in db and notes in files in sync, i do not have a idea hwo to do it properly





