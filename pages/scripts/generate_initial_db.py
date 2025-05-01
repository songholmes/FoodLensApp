import sqlite3
import pandas as pd
import numpy as np
import os


def get_initial_db(db_path):
    con = sqlite3.connect(db_path)

    cur = con.cursor()

    cur.execute("CREATE TABLE movie(title, year, score)")

    res = cur.execute("SELECT name FROM sqlite_master")
    res.fetchone()

    res = cur.execute("SELECT name FROM sqlite_master WHERE name='spam'")
    res.fetchone() is None

    cur.execute("""
        INSERT INTO movie VALUES
            ('Monty Python and the Holy Grail', '1975/01/02', 8.2),
            ('And Now for Something Completely Different', '1971/03/04', 7.5)
    """)

    con.commit()
