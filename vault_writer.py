import csv
from vault_reader import convert, make_hash, open_file, read_vault

# change these and hit Run
INPUT_CSV = "sample_data/library_1.csv"
OUTPUT_FILE = "library_1.txt"  # put .gz on the end to compress it
LISTENER_ID = "U00417"

FIELDS = [
    ["song_id", "int"], ["title", "str"], ["artist", "str"], ["album", "str"],
    ["genre", "str"], ["release_year", "int"], ["duration_sec", "int"],
    ["rating", "int"], ["plays", "int"], ["favorite", "bool"], ["last_played", "date"],
]


def check_song(song, fields, where):
    clean = {}
    for name, kind in fields:
        value = song.get(name)
        if value is None or str(value).strip() == "":
            raise ValueError(where + ": " + name + " is missing")
        try:
            clean[name] = convert(str(value).strip(), kind)
        except ValueError:
            raise ValueError(where + ": " + name + " should be " + kind + ", got " + str(value))
    return clean


def csv_line(values):
    # quote anything with a comma or quote in it (same rule the csv module uses)
    parts = []
    for value in values:
        if "," in value or '"' in value:
            value = '"' + value.replace('"', '""') + '"'
        parts.append(value)
    return ",".join(parts)


def write_vault(path, listener_id, fields, songs):
    record_lines = []
    index = {}
    for song in songs:
        row = []
        for name, kind in fields:
            value = song[name]
            if kind == "bool":
                value = "TRUE" if value else "FALSE"
            row.append(str(value))
        record_lines.append(csv_line(row))

        artist = song["artist"]
        if artist not in index:
            index[artist] = []
        index[artist].append(str(song["song_id"]))

    names = []
    for name, kind in fields:
        names.append(name + ":" + kind)

    lines = ["MYMUSICVAULT", "LISTENER_ID," + listener_id, "RECORD_COUNT," + str(len(songs))]
    lines.append("FIELDS," + ",".join(names))
    lines.append("---BEGIN RECORDS---")
    lines += record_lines
    lines.append("---END RECORDS---")
    lines.append("---BEGIN INDEX---")
    for artist in index:
        lines.append(csv_line([artist, ";".join(index[artist])]))
    lines.append("---END INDEX---")
    lines.append("RECORDS_WRITTEN," + str(len(record_lines)))
    lines.append("HASH," + make_hash(record_lines))

    with open_file(path, "w") as f:
        f.write("\n".join(lines) + "\n")


def csv_to_vault(csv_path, path, listener_id):
    songs = []
    ids = []
    with open(csv_path, encoding="utf-8", newline="") as f:
        row_num = 1  # row 1 is the header
        for row in csv.DictReader(f):
            row_num += 1
            song = check_song(row, FIELDS, "row " + str(row_num))
            if song["song_id"] in ids:
                raise ValueError("row " + str(row_num) + ": duplicate song_id")
            ids.append(song["song_id"])
            songs.append(song)
    write_vault(path, listener_id, FIELDS, songs)
    return songs


def load_for_edit(path):
    # don't rewrite a tampered file, it would get a new valid hash
    vault = read_vault(path)
    if not vault["counts_ok"] or not vault["hash_ok"]:
        raise ValueError("vault looks damaged or tampered, not editing it")
    return vault


def add_record(path, song):
    vault = load_for_edit(path)
    song = check_song(song, vault["fields"], "new song")
    if song["song_id"] in vault["by_id"]:
        raise ValueError("song_id " + str(song["song_id"]) + " already exists")
    vault["songs"].append(song)
    write_vault(path, vault["listener_id"], vault["fields"], vault["songs"])


def update_record(path, song_id, changes):
    vault = load_for_edit(path)
    if song_id not in vault["by_id"]:
        raise ValueError("no song with song_id " + str(song_id))
    songs = vault["songs"]
    for i in range(len(songs)):
        if songs[i]["song_id"] == song_id:
            song = dict(songs[i])
            song.update(changes)
            song = check_song(song, vault["fields"], "song " + str(song_id))
            # changing the id to one that's already used would break the index
            if song["song_id"] != song_id and song["song_id"] in vault["by_id"]:
                raise ValueError("song_id " + str(song["song_id"]) + " already exists")
            songs[i] = song
    write_vault(path, vault["listener_id"], vault["fields"], songs)


def delete_record(path, song_id):
    vault = load_for_edit(path)
    if song_id not in vault["by_id"]:
        raise ValueError("no song with song_id " + str(song_id))
    songs = []
    for song in vault["songs"]:
        if song["song_id"] != song_id:
            songs.append(song)
    write_vault(path, vault["listener_id"], vault["fields"], songs)


if __name__ == "__main__":
    songs = csv_to_vault(INPUT_CSV, OUTPUT_FILE, LISTENER_ID)
    print("Wrote", len(songs), "songs to", OUTPUT_FILE)
