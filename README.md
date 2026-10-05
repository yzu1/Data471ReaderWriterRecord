# MyMusicVault

A text file format for storing one listener's music library.

## Files

- `vault_writer.py`: turns a CSV of songs into a vault file. It checks every row (missing
  values, wrong types, duplicate song_ids) before writing, then builds the artist index,
  record counts and hash. It also has add_record, update_record and delete_record for
  editing an existing vault.
- `vault_reader.py`: reads a vault file back into Python with the right types. It checks
  the listener ID, record counts and hash, searches by artist, genre, favorites and date,
  and prints a summary (listening time, top artist, favorites).
- `test_vault.py`: tests the reader and writer on both sample libraries.
- `sample_data/library_1.csv`: 15 K-Pop songs for listener U00417.
- `sample_data/library_2.csv`: 20 EDM, House, Rap and Pop songs for listener U00932.
  Includes titles and artists with commas and apostrophes, and a song with 0 plays.

## Format

```
MYMUSICVAULT
LISTENER_ID,U00417
RECORD_COUNT,15
FIELDS,song_id:int,title:str,artist:str,...,last_played:date
---BEGIN RECORDS---
1,TT,TWICE,TWICEcoaster: Lane 1,K-Pop,2016,213,5,58,TRUE,2026-09-28
2,Fancy,TWICE,Fancy You,K-Pop,2019,213,4,34,FALSE,2026-09-11
...
---END RECORDS---
---BEGIN INDEX---
TWICE,1;2;3
STAYC,4;5
...
---END INDEX---
RECORDS_WRITTEN,15
HASH,366DB481
```

This is the start of `library_1.txt`, made from `sample_data/library_1.csv`. In
`library_2.txt`, values with commas get quoted, for example:

```
6,"crank the bass, play the muzik",Knock2,nolimit,EDM,2025,158,4,22,FALSE,2026-09-12
```

- FIELDS gives the name and type of each column (int, float, str, bool, date).
- Values with commas or quotes are wrapped in quotes.
- The index maps each artist to their song_ids, so artist searches don't scan every song.
- RECORDS_WRITTEN repeats the count, and HASH is the first 8 characters of the SHA-256
  of the record lines. The reader uses both to check the file hasn't been changed.
- The reader also checks the first line and only opens the file for the matching listener ID.

## How to run

Open the project folder in VS Code, then open a script and press Run.

- `vault_writer.py`: set INPUT_CSV, OUTPUT_FILE and LISTENER_ID at the top. End OUTPUT_FILE
  with `.gz` to compress it. The file also has add_record, update_record and delete_record.
- `vault_reader.py`: set VAULT_FILE and LISTENER_ID at the top. ARTIST, GENRE,
  FAVORITES_ONLY and PLAYED_AFTER are optional search filters.
- `test_vault.py`: runs the tests on both sample libraries and prints PASS or FAIL for
  each one. It checks the round trip, the index, searches, the summary numbers, editing,
  bad CSV rows, tampering, record counts, listener IDs and gzip. Output files go in
  `test_output/`.
