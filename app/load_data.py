"""Runs a .cypher file against Neo4j one statement at a time.

Usage:  python load_data.py ../01_constraints.cypher ../02_load_data.cypher
"""
import os
import sys

from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()


def statements(path):
    """Split a .cypher file into statements (comment lines removed)."""
    with open(path, encoding="utf-8") as f:
        lines = [ln for ln in f if not ln.strip().startswith("//")]
    return [s.strip() for s in "".join(lines).split(";") if s.strip()]


def main(files):
    driver = GraphDatabase.driver(
        os.environ["NEO4J_URI"],
        auth=(os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"]),
    )
    db = os.getenv("NEO4J_DATABASE", "neo4j")
    with driver, driver.session(database=db) as session:
        for path in files:
            for i, stmt in enumerate(statements(path), start=1):
                result = session.run(stmt)
                rows = result.data()
                print(f"{os.path.basename(path)} #{i}: ok ({len(rows)} rows returned)")
                for row in rows:
                    print("   ", row)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Usage: python load_data.py file1.cypher [file2.cypher ...]")
    main(sys.argv[1:])
