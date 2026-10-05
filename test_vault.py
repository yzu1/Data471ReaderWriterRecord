import os
import shutil
from datetime import date
from vault_reader import check_vault, read_vault, search, summarize
from vault_writer import add_record, csv_to_vault, delete_record, update_record

# run from the project folder so the relative paths work no matter where Run is pressed
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# all test files go in test_output/
os.makedirs("test_output", exist_ok=True)
CSV1 = "sample_data/library_1.csv"
CSV2 = "sample_data/library_2.csv"
LIB1 = "test_output/library_1.txt"
LIB2 = "test_output/library_2.txt"
passed = 0
failed = 0


def step(name, test):
    global passed, failed
    try:
        test()
        print("PASS", name)
        passed += 1
    except Exception as e:
        print("FAIL", name, repr(e))
        failed += 1


def ids(songs):
    result = []
    for song in songs:
        result.append(song["song_id"])
    return result


def copy_file(src, dst):
    # copy the bytes so Windows doesn't change \n to \r\n
    shutil.copyfile(src, dst)
    return dst


def edit_file(src, dst, old, new):
    # make a changed copy of a file, old has to be in it exactly once
    with open(src, encoding="utf-8", newline="") as f:
        text = f.read()
    assert text.count(old) == 1, "expected to find " + old + " once"
    with open(dst, "w", encoding="utf-8", newline="") as f:
        f.write(text.replace(old, new))
    return dst


def bad_csv(name, old, new):
    # copy of library_1.csv with one thing broken in it
    return edit_file(CSV1, "test_output/" + name, old, new)


def raises(func, *args):
    # returns the error message, fails if no ValueError happens
    try:
        func(*args)
    except ValueError as e:
        return str(e)
    raise AssertionError(func.__name__ + " should have raised ValueError")


def test_round_trip():
    songs1 = csv_to_vault(CSV1, LIB1, "U00417")
    songs2 = csv_to_vault(CSV2, LIB2, "U00932")
    v1 = read_vault(LIB1)
    v2 = read_vault(LIB2)
    assert len(v1["songs"]) == 15 and len(v2["songs"]) == 20
    assert v1["songs"] == songs1 and v2["songs"] == songs2
    assert v1["listener_id"] == "U00417" and v2["listener_id"] == "U00932"
    assert v1["counts_ok"] and v1["hash_ok"] and v2["counts_ok"] and v2["hash_ok"]
    assert ids(v1["songs"]) == list(range(1, 16))
    assert ids(v2["songs"]) == list(range(1, 21))

    # check one whole song from each file by hand, types included
    assert v1["by_id"][1] == {
        "song_id": 1, "title": "TT", "artist": "TWICE",
        "album": "TWICEcoaster: Lane 1", "genre": "K-Pop", "release_year": 2016,
        "duration_sec": 213, "rating": 5, "plays": 58, "favorite": True,
        "last_played": date(2026, 9, 28),
    }
    assert v2["by_id"][7] == {
        "song_id": 7, "title": "rookie (with SAYAK DAS)", "artist": "Knock2",
        "album": "nolimit", "genre": "EDM", "release_year": 2025,
        "duration_sec": 165, "rating": 3, "plays": 0, "favorite": False,
        "last_played": date(2026, 1, 17),
    }
    # commas, quotes, colons and odd characters should come back the same
    assert v1["by_id"][3]["album"] == "What Is Love?"
    assert v1["by_id"][12]["album"] == "Map of the Soul: Persona"
    assert v2["by_id"][6]["title"] == "crank the bass, play the muzik"
    assert v2["by_id"][20]["artist"] == "PinkPantheress, Ice Spice"
    assert v2["by_id"][20]["title"] == "Boy's a liar Pt. 2"
    assert v2["by_id"][5]["title"] == "dashstar*"
    assert v2["by_id"][12]["album"] == "Dreamin'"
    assert v2["by_id"][14]["title"] == "LV Sandals (feat. Fakemink & Rico Ace)"


def test_index():
    v1 = read_vault(LIB1)
    assert v1["index"] == {
        "TWICE": [1, 2, 3], "STAYC": [4, 5], "NewJeans": [6, 7, 8, 9],
        "BTS": [10, 11, 12], "CORTIS": [13, 14, 15],
    }
    v2 = read_vault(LIB2)
    assert v2["index"] == {
        "ISOxo": [1, 2, 3, 4], "Knock2": [5, 6, 7], "Dom Dolla": [8, 9, 10, 11, 12],
        "EsDeeKid": [13, 14, 15], "PinkPantheress": [16, 17, 18, 19],
        "PinkPantheress, Ice Spice": [20],
    }


def test_search():
    v1 = read_vault(LIB1)
    assert ids(search(v1, artist="newjeans")) == [6, 7, 8, 9]
    assert ids(search(v1, artist="TWICE", favorites_only=True)) == [1]
    assert ids(search(v1, favorites_only=True)) == [1, 4, 6, 7, 11, 13, 15]
    # played_after means strictly after, so TT (played 2026-09-28) is left out
    assert ids(search(v1, played_after="2026-09-28")) == [4, 6, 13, 15]
    assert ids(search(v1, genre="k-pop")) == list(range(1, 16))
    assert search(v1, genre="EDM") == []
    assert search(v1, artist="Taylor Swift") == []

    v2 = read_vault(LIB2)
    assert ids(search(v2, artist="Dom Dolla")) == [8, 9, 10, 11, 12]
    assert ids(search(v2, genre="EDM")) == [1, 2, 3, 4, 5, 6, 7]
    assert ids(search(v2, genre="house", favorites_only=True)) == [9, 10]
    assert ids(search(v2, genre="EDM", favorites_only=True, played_after="2026-09-20")) == [1, 5]
    # artist search is an exact match on the index, so the collab is its own artist
    assert ids(search(v2, artist="PinkPantheress")) == [16, 17, 18, 19]
    assert ids(search(v2, artist="PinkPantheress, Ice Spice")) == [20]


def test_summary():
    # expected numbers worked out from the CSVs separately
    s1 = summarize(read_vault(LIB1)["songs"])
    assert s1["total_sec"] == 121233  # 33 h 40 min
    assert s1["top_artist"] == "NewJeans" and s1["plays"]["NewJeans"] == 198
    assert s1["favorites"] == 7

    s2 = summarize(read_vault(LIB2)["songs"])
    assert s2["total_sec"] == 105373  # 29 h 16 min
    assert s2["top_artist"] == "Dom Dolla" and s2["plays"]["Dom Dolla"] == 144
    assert s2["favorites"] == 9

    # summary of a search result
    s3 = summarize(search(read_vault(LIB2), artist="Knock2"))
    assert s3["total_sec"] == 172 * 57 + 158 * 22 + 165 * 0
    assert s3["favorites"] == 1

    assert summarize([]) == {"total_sec": 0, "favorites": 0, "plays": {}, "top_artist": None}


def test_add_update_delete():
    path = copy_file(LIB1, "test_output/edit_test.txt")

    add_record(path, {"song_id": 16, "title": "Lullaby", "artist": "CORTIS",
                      "album": "COLOR OUTSIDE THE LINES", "genre": "K-Pop",
                      "release_year": 2025, "duration_sec": 164, "rating": 4,
                      "plays": 0, "favorite": False, "last_played": "2026-10-03"})
    v = read_vault(path)
    assert len(v["songs"]) == 16 and v["counts_ok"] and v["hash_ok"]
    assert v["index"]["CORTIS"] == [13, 14, 15, 16]
    assert v["by_id"][16]["last_played"] == date(2026, 10, 3)

    # a new artist should get its own index line
    add_record(path, {"song_id": 17, "title": "Gnarly", "artist": "KATSEYE",
                      "album": "BEAUTIFUL CHAOS", "genre": "Pop", "release_year": 2025,
                      "duration_sec": 140, "rating": 3, "plays": 2, "favorite": "FALSE",
                      "last_played": "2026-10-04"})
    v = read_vault(path)
    assert v["index"]["KATSEYE"] == [17] and len(v["songs"]) == 17

    update_record(path, 16, {"plays": 5, "favorite": True})
    v = read_vault(path)
    assert v["by_id"][16]["plays"] == 5 and v["by_id"][16]["favorite"] == True
    assert v["hash_ok"]
    # the other songs shouldn't change
    assert v["by_id"][1]["plays"] == 58

    delete_record(path, 16)
    delete_record(path, 17)
    v = read_vault(path)
    assert len(v["songs"]) == 15 and v["counts_ok"] and v["hash_ok"]
    assert v["index"]["CORTIS"] == [13, 14, 15]
    assert "KATSEYE" not in v["index"]
    # after adding and deleting we should be back to the original songs
    assert v["songs"] == read_vault(LIB1)["songs"]

    with open(path, encoding="utf-8") as f:
        text = f.read()
    assert "RECORD_COUNT,15" in text and "RECORDS_WRITTEN,15" in text


def test_bad_edits():
    path = copy_file(LIB1, "test_output/bad_edit_test.txt")
    # song_id 1 is TT, so these should all be refused
    raises(add_record, path, dict(read_vault(LIB1)["by_id"][1]))
    raises(update_record, path, 99, {"plays": 1})
    raises(update_record, path, 2, {"song_id": 1})
    raises(update_record, path, 2, {"rating": "five"})
    raises(delete_record, path, 99)
    # nothing should have been written
    assert read_vault(path)["songs"] == read_vault(LIB1)["songs"]


def test_bad_csv():
    # row numbers count the header as row 1, like in Excel
    out = "test_output/should_not_exist.txt"
    message = raises(csv_to_vault, bad_csv("missing.csv", "2,Fancy,TWICE", "2,,TWICE"), out, "U00417")
    assert "row 3" in message and "title" in message

    message = raises(csv_to_vault, bad_csv("bad_bool.csv", "34,FALSE", "34,maybe"), out, "U00417")
    assert "row 3" in message and "favorite" in message

    message = raises(csv_to_vault, bad_csv("bad_date.csv", "2026-09-30", "2026-09-31"), out, "U00417")
    assert "row 5" in message and "last_played" in message

    message = raises(csv_to_vault, bad_csv("bad_int.csv", ",2016,213,", ",2016,3:33,"), out, "U00417")
    assert "row 2" in message and "duration_sec" in message

    message = raises(csv_to_vault, bad_csv("dup_id.csv", "15,FaSHioN", "14,FaSHioN"), out, "U00417")
    assert "row 16" in message and "duplicate" in message

    assert not os.path.exists(out)


def test_tampering():
    # change the plays for TT from 58 to 999
    path = edit_file(LIB1, "test_output/tampered.txt", "K-Pop,2016,213,5,58,", "K-Pop,2016,213,5,999,")
    v = read_vault(path)
    assert v["hash_ok"] == False and v["counts_ok"] == True
    assert v["by_id"][1]["plays"] == 999
    # tampering is only a warning, the file still opens
    assert check_vault(v, "U00417") == True
    # but the writer won't save over it
    raises(add_record, path, {"song_id": 16})


def test_wrong_counts():
    path = edit_file(LIB2, "test_output/wrong_count.txt", "RECORD_COUNT,20", "RECORD_COUNT,21")
    v = read_vault(path)
    assert v["counts_ok"] == False and v["hash_ok"] == True
    assert check_vault(v, "U00932") == False

    # deleting a record line should break the counts and the hash
    path = edit_file(LIB2, "test_output/missing_row.txt",
                     "19,Pain,PinkPantheress,to hell with it,Pop,2021,101,3,9,FALSE,2026-05-04\n", "")
    v = read_vault(path)
    assert len(v["songs"]) == 19
    assert v["counts_ok"] == False and v["hash_ok"] == False


def test_not_a_vault():
    raises(read_vault, CSV1)
    path = edit_file(LIB1, "test_output/no_magic.txt", "MYMUSICVAULT", "MYMUSICVAULT2")
    raises(read_vault, path)


def test_listener_ids():
    v1 = read_vault(LIB1)
    v2 = read_vault(LIB2)
    assert check_vault(v1, "U00417") == True
    assert check_vault(v2, "U00932") == True
    # each listener can't open the other one's library
    assert check_vault(v1, "U00932") == False
    assert check_vault(v2, "U00417") == False
    assert check_vault(v1, "U99999") == False


def test_gzip():
    csv_to_vault(CSV2, LIB2 + ".gz", "U00932")
    v = read_vault(LIB2 + ".gz")
    assert v["songs"] == read_vault(LIB2)["songs"]
    assert v["index"] == read_vault(LIB2)["index"]
    assert v["hash_ok"] and v["counts_ok"]

    # editing should work on a compressed file too
    delete_record(LIB2 + ".gz", 20)
    v = read_vault(LIB2 + ".gz")
    assert len(v["songs"]) == 19 and v["hash_ok"] and v["counts_ok"]

    plain = os.path.getsize(LIB2)
    compressed = os.path.getsize(LIB2 + ".gz")
    print("size without gzip:", plain, "bytes, with gzip:", compressed, "bytes")
    assert compressed < plain


step("write and read back both libraries", test_round_trip)
step("artist index matches the data", test_index)
step("search by artist, genre, favorites and date", test_search)
step("listening time, top artist and favorites", test_summary)
step("add, update and delete a song", test_add_update_delete)
step("bad edits are refused", test_bad_edits)
step("bad CSV rows give the right error", test_bad_csv)
step("tampered file gives a warning", test_tampering)
step("wrong record count is caught", test_wrong_counts)
step("non-vault file is rejected", test_not_a_vault)
step("listener IDs are checked", test_listener_ids)
step("gzip round trip", test_gzip)
print()
print(passed, "passed,", failed, "failed")
