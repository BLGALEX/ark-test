from contextlib import asynccontextmanager
from functools import partial
import strawberry
from strawberry.types import Info
from fastapi import FastAPI
from strawberry.fastapi import BaseContext, GraphQLRouter
from databases import Database

from settings import Settings


class Context(BaseContext):
    db: Database

    def __init__(
        self,
        db: Database,
    ) -> None:
        self.db = db


@strawberry.type
class Author:
    id: int
    name: str


@strawberry.type
class Book:
    id: int
    title: str
    author: Author


@strawberry.type
class Query:

    @strawberry.field
    async def books(
        self,
        info: Info[Context, None],
        author_ids: list[int] | None = None,
        search: str | None = None,
        limit: int | None = None,
    ) -> list[Book]:
        query_values = {}

        if author_ids is not None:
            query_values["author_ids"] = tuple(author_ids)

        if search:
            query_values["search"] = f"%{search}%"

        query = """
            SELECT b.id, b.title, a.id, a.name
            FROM books b
            JOIN authors a ON b.author_id = a.id
            """
        if query_values:
            query += "WHERE "
            conditions = []
            for key in query_values.keys():
                if key == "author_ids":
                    conditions.append(f"b.author_id = ANY(:{key})")
                elif key == "search":
                    conditions.append(f"b.title ILIKE :{key}")
            query += " AND ".join(conditions)
        if limit:
            query_values["limit"] = limit
            query += " LIMIT :limit"

        result = await info.context.db.fetch_all(
            query,
            values=query_values,
        )
        return [Book(id=row[0], title=row[1], author=Author(id=row[2], name=row[3])) for row in result]


CONN_TEMPLATE = "postgresql+asyncpg://{user}:{password}@{host}:{port}/{name}"
settings = Settings()  # type: ignore
db = Database(
    CONN_TEMPLATE.format(
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        port=settings.DB_PORT,
        host=settings.DB_SERVER,
        name=settings.DB_NAME,
    ),
)

@asynccontextmanager
async def lifespan(
    app: FastAPI,
    db: Database,
):
    async with db:
        yield
    await db.disconnect()

schema = strawberry.Schema(query=Query)
graphql_app = GraphQLRouter(  # type: ignore
    schema,
    context_getter=partial(Context, db),
)

app = FastAPI(lifespan=partial(lifespan, db=db))
app.include_router(graphql_app, prefix="/graphql")
