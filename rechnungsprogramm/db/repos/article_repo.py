from models.article import Article
from db.database import Database


class ArticleRepo:
    def __init__(self, db: Database):
        self.db = db

    def _row_to_article(self, row) -> Article:
        d = {k: row[k] for k in row.keys()}
        d["beguenstigt_35a"] = bool(d.get("beguenstigt_35a", 0))
        return Article(**d)

    def get_all(self) -> list[Article]:
        rows = self.db.execute(
            "SELECT * FROM articles ORDER BY bezeichnung"
        ).fetchall()
        return [self._row_to_article(r) for r in rows]

    def get_by_id(self, article_id: int) -> Article | None:
        row = self.db.execute(
            "SELECT * FROM articles WHERE id = ?", (article_id,)
        ).fetchone()
        return self._row_to_article(row) if row else None

    def create(self, a: Article) -> int:
        cursor = self.db.execute(
            """INSERT INTO articles (bezeichnung, beschreibung, preis, mwst, beguenstigt_35a)
               VALUES (?, ?, ?, ?, ?)""",
            (a.bezeichnung, a.beschreibung, a.preis, a.mwst, int(a.beguenstigt_35a)),
        )
        self.db.commit()
        return cursor.lastrowid

    def update(self, a: Article):
        self.db.execute(
            """UPDATE articles SET bezeichnung=?, beschreibung=?, preis=?, mwst=?,
               beguenstigt_35a=?, updated_at=CURRENT_TIMESTAMP
               WHERE id=?""",
            (a.bezeichnung, a.beschreibung, a.preis, a.mwst, int(a.beguenstigt_35a), a.id),
        )
        self.db.commit()

    def delete(self, article_id: int):
        self.db.execute("DELETE FROM articles WHERE id = ?", (article_id,))
        self.db.commit()
