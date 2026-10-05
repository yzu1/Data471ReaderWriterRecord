import csv
import gzip
import hashlib
from datetime import date

# change these and hit Run
VAULT_FILE = "library_1.txt"
LISTENER_ID = "U00417"
ARTIST = None
GENRE = None
FAVORITES_ONLY = False
PLAYED_AFTER = None  # e.g. "2026-09-01"


def open_file(path, mode):
    # .gz files are compressed
    if path.endswith(".gz"):
        return gzip.open(path, mode + "t", encoding="utf-8", newline="")
    return open(path, mode, encoding="utf-8", newline="")


def convert(text, kind):
    if kind == "int":
        return int(text)
    if kind == "float":
        return float(text)
    if kind == "bool":
        if text.upper() not in ("TRUE", "FALSE"):
            raise ValueError("expected TRUE or FALSE, got " + text)
        return text.upper() == "TRUE"
    if kind == "date":
        return date.fromisoformat(text)
    return text


def make_hash(lines):
    text = "\n".join(lines)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:8].upper()


def read_vault(path):
    with open_file(path, "r") as f:
        lines = f.read().splitlines()

    if len(lines) == 0 or lines[0] != "MYMUSICVAULT":
        raise ValueError("not a MyMusicVault file")

    info = {}
    record_lines = []
    index_lines = []
    section = None
    for line in lines[1:]:
        if line.startswith("---BEGIN"):
            section = line
        elif line.startswith("---END"):
            section = None
        elif section == "---BEGIN RECORDS---":
            record_lines.append(line)
        elif section == "---BEGIN INDEX---":
            index_lines.append(line)
        elif line != "":
            key, value = line.split(",", 1)
            info[key] = value

    # FIELDS looks like song_id:int,title:str,...
    fields = []
    for item in info["FIELDS"].split(","):
        fields.append(item.split(":"))

    songs = []
    by_id = {}
    for row in csv.reader(record_lines):
        song = {}
        for i in range(len(fields)):
            name, kind = fields[i]
            song[name] = convert(row[i], kind)
        songs.append(song)
        by_id[song["song_id"]] = song

    # index lines look like Queen,3;9
    index = {}
    for artist, ids in csv.reader(index_lines):
        index[artist] = []
        for x in ids.split(";"):
            index[artist].append(int(x))

    count = int(info["RECORD_COUNT"])
    written = int(info["RECORDS_WRITTEN"])
    return {
        "listener_id": info["LISTENER_ID"],
        "fields": fields,
        "songs": songs,
        "by_id": by_id,
        "index": index,
        "counts_ok": count == written and count == len(songs),
        "hash_ok": info["HASH"] == make_hash(record_lines),
    }


def check_vault(vault, listener_id):
    print("Magic line OK")
    if vault["listener_id"] != listener_id:
        print("Access denied")
        return False
    print("Access granted")
    if not vault["counts_ok"]:
        print("ERROR: record counts don't match")
        return False
    print("Record counts OK")
    if vault["hash_ok"]:
        print("Integrity OK")
    else:
        print("WARNING: file may be tampered")
    return True


def search(vault, artist=None, genre=None, favorites_only=False, played_after=None):
    songs = vault["songs"]
    if artist:
        # use the index so we don't have to check every song
        ids = []
        for name in vault["index"]:
            if name.lower() == artist.lower():
                ids = vault["index"][name]
        songs = []
        for i in ids:
            songs.append(vault["by_id"][i])

    results = []
    for song in songs:
        if genre and song["genre"].lower() != genre.lower():
            continue
        if favorites_only and not song["favorite"]:
            continue
        if played_after and song["last_played"] <= date.fromisoformat(played_after):
            continue
        results.append(song)
    return results


def summarize(songs):
    # total listening time is length of the song times how many times it was played
    total = 0
    favorites = 0
    plays = {}
    for song in songs:
        total += song["duration_sec"] * song["plays"]
        if song["favorite"]:
            favorites += 1
        plays[song["artist"]] = plays.get(song["artist"], 0) + song["plays"]

    top = None
    if plays:
        top = max(plays, key=plays.get)
    return {"total_sec": total, "favorites": favorites, "plays": plays, "top_artist": top}


if __name__ == "__main__":
    vault = read_vault(VAULT_FILE)
    if check_vault(vault, LISTENER_ID):
        songs = search(vault, ARTIST, GENRE, FAVORITES_ONLY, PLAYED_AFTER)

        names = []
        for field in vault["fields"]:
            names.append(field[0])
        print()
        print(" | ".join(names))
        for song in songs:
            row = []
            for name in names:
                row.append(str(song[name]))
            print(" | ".join(row))

        stats = summarize(songs)
        total = stats["total_sec"]
        print()
        print("Total songs:", len(songs))
        print("Total listening time:", total // 3600, "h", total % 3600 // 60, "min")
        if stats["top_artist"]:
            top = stats["top_artist"]
            print("Top artist by plays:", top, "(" + str(stats["plays"][top]) + " plays)")
        print("Favorites:", stats["favorites"])
