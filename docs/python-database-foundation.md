# Python 基礎：這個專案如何把 model 變成 PostgreSQL schema

> 文件用途：在開始寫 ETL 前，先理解目前 repository 的 Python、SQLAlchemy 和 Alembic 基礎。
> 
> 讀者假設：會 SQL，但不熟 Python。

## 先記住一件事

這個 repository 有兩個不同的東西：

1. **Python model**：用 Python 描述資料表、欄位、外鍵和限制。
2. **Database migration**：把這些描述轉成真正對 PostgreSQL 執行的 `CREATE TABLE`、`ALTER TABLE` 和 `DROP TABLE`。

Python model 本身不會自動建立資料表。這個專案也沒有在 application startup 呼叫 `Base.metadata.create_all()`。真正建立 schema 的入口是 Alembic migration：

```text
npm run db:migrate
  ↓
uv run alembic upgrade head
  ↓
migrations/env.py 讀取設定並連線 PostgreSQL
  ↓
Alembic 執行 migrations/versions/0cfadf2acb52_*.py 的 upgrade()
  ↓
op.create_table(...) 建立資料表、欄位、FK、index、constraint
  ↓
alembic_version 記錄目前 revision
```

這個流程解釋了為什麼「model 存在」和「database 已經有 table」不是同一件事。

## 目前 repository 的實際狀態

以下是本次檢查已確認的狀態：

| 項目 | 現況 |
| --- | --- |
| Python version | `pyproject.toml` 要求 Python `>=3.12` |
| ORM | SQLAlchemy `>=2.0` |
| PostgreSQL driver | `psycopg[binary]` |
| Migration tool | Alembic `>=1.14,<2` |
| Model tables | 29 張 domain tables |
| Database tables | 30 張，包含 29 張 domain tables + `alembic_version` |
| Current revision | `0cfadf2acb52 (head)` |
| `organisations` rows | 0 |
| `source_records` rows | 0 |
| `donations` rows | 0 |
| Application seed | 尚未建立 |

`alembic current` 已實際回傳 `0cfadf2acb52 (head)`。這代表目前設定的本機 PostgreSQL 已經套用 migration；它只代表 schema 已建立，不代表資料已經填入。

來源：[README.md](../README.md)、[pyproject.toml](../pyproject.toml)、[目前的 migration](../migrations/versions/0cfadf2acb52_create_phase_1_8_schema.py)、[目前的 model 匯出清單](../backend/app/models/__init__.py)。

## Step 1：Python 先做了什麼

### 1. `import` 是把別的檔案帶進目前檔案

在 [`backend/app/database.py`](../backend/app/database.py) 裡：

```python
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from backend.app.config import Settings
```

可以把它讀成：

- 從 `sqlalchemy` 套件拿 `Engine`、`create_engine`、`text`。
- 從 `sqlalchemy.orm` 拿 session 相關工具。
- 從本專案的 `config.py` 拿 `Settings`。

Python 檔案不是一個巨大檔案。`import` 把其他模組的名稱帶進來，讓每個檔案只負責一個概念。

### 2. type annotation 說明「預期的資料型別」

例如：

```python
def create_db_engine(settings: Settings) -> Engine:
    ...
```

這表示：

- `settings` 預期是一個 `Settings` 物件。
- 函式預期回傳 `Engine`。

這主要幫助閱讀、IDE、mypy 和 lint。它本身不會執行 SQL，也不會建立資料表。

這個專案常見的型別寫法包括：

```python
Mapped[UUID]          # 一定有 UUID
Mapped[str]           # 一定有字串
Mapped[str | None]    # 可以是字串，也可以是 NULL
list[Site]            # Site 物件的列表
```

`str | None` 是 Python 3.10 以後的 union syntax。在 database 語境裡通常對應 `nullable=True`，但兩者仍然是不同層次：Python annotation 描述程式預期，SQLAlchemy `nullable` 才會影響資料庫欄位是否允許 `NULL`。

### 3. class 是一個可以建立物件的結構

目前的 `Organisation` 是這樣開始的：

```python
class Organisation(Base):
    __tablename__ = "organisations"
```

可以把它理解成：

- `Organisation` 是 Python 裡代表組織的類別。
- `(Base)` 表示它繼承 SQLAlchemy 的 declarative base。
- `__tablename__` 告訴 SQLAlchemy，這個類別對應 PostgreSQL 的 `organisations` table。

這不是 Python 自己把 class 變成 table。SQLAlchemy 會讀取繼承自 `Base` 的 classes，將它們登記到 `Base.metadata`；之後 Alembic 才會使用這些 metadata 來比對或產生 migration。

### 4. `with` 是「使用完自動收尾」

`database.py` 的 connection check：

```python
with engine.connect() as connection:
    connection.execute(text("SELECT 1"))
```

`with` 讓 connection 在離開區塊後自動關閉或釋放。這和 SQL 裡的 `SELECT 1` 是兩件事：

- Python `with` 管理資源生命週期。
- SQL `SELECT 1` 只確認 database 接受查詢。

`check_database()` 只讀取資料庫，不會建立 table，也不會寫入資料。[database.py:26-30](../backend/app/database.py#L26-L30)

### 5. function 和 decorator

設定物件由 `get_settings()` 提供：

```python
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
```

`@lru_cache(maxsize=1)` 是 decorator。它會把第一次建立的 `Settings` 暫存起來，後續呼叫直接重用同一份設定。

這裡的目的不是 database migration，而是讓 application 和 Alembic 都使用同一套 `.env` / environment settings。[config.py:7-22](../backend/app/config.py#L7-L22)

## Step 2：SQLAlchemy model 如何描述一張 table

### 1. `DeclarativeBase` 是所有 model 的共同登記處

[`backend/app/models/base.py`](../backend/app/models/base.py) 只有很小一段：

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class used to register FoodFlow tables without creating them implicitly."""
```

這個 `Base` 的作用是建立共同的 SQLAlchemy model registry。每個 model 繼承它之後，SQLAlchemy 就能在 `Base.metadata.tables` 裡看到 table 定義。

`Base.metadata` 是 Python 記憶體裡的 table description，不是 PostgreSQL 裡的 table。只有 migration 或明確的 schema command 執行後，database 才會改變。

### 2. `Mapped` 和 `mapped_column` 把 Python 欄位對應成 database 欄位

`Organisation.id` 的簡化版本是：

```python
id: Mapped[UUID] = mapped_column(
    Uuid(as_uuid=True),
    primary_key=True,
    default=uuid4,
)
```

逐項讀：

| Python / SQLAlchemy 部分 | 意思 |
| --- | --- |
| `id` | Python 物件上的欄位名稱 |
| `Mapped[UUID]` | 這個欄位預期是 UUID |
| `Uuid(as_uuid=True)` | PostgreSQL UUID 型別，讀寫時使用 Python `UUID` |
| `primary_key=True` | 這是 table 的主鍵 |
| `default=uuid4` | 建立 Python 物件時，如果沒有給 id，就呼叫 `uuid4` |

注意 `default=uuid4` 是 Python-side default。它不是 PostgreSQL server default。這個差異在 migration 和直接用 SQL insert 時很重要。

### 3. `nullable` 決定可不可以是 `NULL`

```python
name: Mapped[str] = mapped_column(
    String(200),
    nullable=False,
)
```

這會要求 `name` 有值。對應的 SQL 概念是：

```sql
name VARCHAR(200) NOT NULL
```

如果 Python annotation 是 `Mapped[str | None]`，而 `nullable=True`，就表示「未知或尚未提供」可以用 `NULL` 表示。`NULL` 不等於零，也不等於空字串。

### 4. Python default、server default 和 `onupdate`

目前 model 同時出現三種時間設定：

```python
created_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    default=lambda: datetime.now(UTC),
    server_default=func.now(),
)

updated_at: Mapped[datetime] = mapped_column(
    DateTime(timezone=True),
    default=lambda: datetime.now(UTC),
    onupdate=lambda: datetime.now(UTC),
    server_default=func.now(),
)
```

差異如下：

| 寫法 | 由誰執行 | 用途 |
| --- | --- | --- |
| `default=...` | SQLAlchemy 建立 Python insert 時 | Python ORM 沒有提供值時補值 |
| `server_default=...` | PostgreSQL 執行 `INSERT` 時 | 直接 SQL insert 也有 default |
| `onupdate=...` | SQLAlchemy 更新物件時 | ORM update 時更新時間 |

它們不等於「每次 update database 都自動追蹤所有欄位」。目前程式沒有用 trigger 取代 application/service rule。

### 5. `ForeignKey` 表示 table 之間的連結

`Site` 有：

```python
organisation_id: Mapped[UUID] = mapped_column(
    Uuid(as_uuid=True),
    ForeignKey("organisations.id", ondelete="RESTRICT"),
    nullable=False,
)
```

這表示每個 site 必須指向一筆存在的 organisation。SQL 概念是：

```sql
FOREIGN KEY (organisation_id)
REFERENCES organisations(id)
ON DELETE RESTRICT
```

`RESTRICT` 表示 organisation 還被 site 使用時，不能直接刪掉 organisation。這保護歷史資料不被 parent delete cascade 一起刪除。[site.py:46-56](../backend/app/models/site.py#L46-L56)

### 6. `relationship` 是 Python 物件之間的導航，不是另一個欄位

`Organisation` 有：

```python
sites: Mapped[list["Site"]] = relationship(
    back_populates="organisation",
    passive_deletes=True,
)
```

這讓 Python 可以用 `organisation.sites` 找到關聯 sites。真正的 database 關係仍然由 `Site.organisation_id` 的 foreign key 建立。

可以這樣分辨：

- `organisation_id` 是 database 存的欄位。
- `organisation` / `sites` 是 ORM 提供的物件導航。
- `relationship()` 不會取代 `ForeignKey`。

### 7. `CheckConstraint` 和 `UniqueConstraint` 把規則交給 PostgreSQL

`Organisation` 限制 status：

```python
CheckConstraint(
    "status IN ('active', 'inactive')",
    name="ck_organisations_status",
)
```

它會變成 database check constraint。資料庫因此拒絕 `status = 'unknown'` 的 row，而不是等到 Python query 時才發現。

`ImportBatch` 的 idempotency constraint：

```python
UniqueConstraint(
    "source_system",
    "idempotency_key",
    name="uq_import_batches_source_idempotency",
)
```

它表示同一個 source system 不能用同一個 idempotency key 建立兩個 import batches。這是 ETL 之後會直接依賴的 database guarantee。[source.py:24-63](../backend/app/models/source.py#L24-L63)

## Step 3：為什麼 model 會被 Alembic 看見

這一步很容易被忽略。

`migrations/env.py` 寫的是：

```python
from backend.app.models import Base

target_metadata = Base.metadata
```

而 `backend/app/models/__init__.py` 又 import 了所有 model：

```python
from backend.app.models.organisation import Organisation, OrganisationRole
from backend.app.models.site import Site, SiteLocation
from backend.app.models.source import FoodProduct, ImportBatch, SourceRecord
```

因此執行 Alembic 時，順序是：

1. Python 載入 `migrations/env.py`。
2. `env.py` import `backend.app.models`。
3. `models/__init__.py` import 所有 model modules。
4. 每個 class 繼承 `Base`，並登記到 `Base.metadata`。
5. Alembic 把 `Base.metadata` 放到 `target_metadata`。
6. Alembic 使用 migration file 的 `upgrade()` 對 PostgreSQL 執行 DDL。

如果某個 model file 沒有被 import，它可能不會出現在 `Base.metadata`。這也是為什麼 `models/__init__.py` 不是單純的方便匯出檔；它同時影響 migration 看得到哪些 tables。[env.py:3-14](../migrations/env.py#L3-L14) [models/__init__.py:3-44](../backend/app/models/__init__.py#L3-L44)

## Step 4：Alembic 如何真正建立 schema

### 1. `alembic.ini` 指向 migration 目錄

```ini
[alembic]
script_location = %(here)s/migrations
prepend_sys_path = .
```

`script_location` 告訴 Alembic 去哪裡找 `env.py` 和 version files。`sqlalchemy.url` 在 ini 裡只是一個 placeholder；實際 URL 由 `get_settings().database_url` 提供。[alembic.ini](../alembic.ini) [config.py:12-17](../backend/app/config.py#L12-L17)

### 2. revision file 定義 migration identity

目前唯一 revision 的 header：

```python
revision: str = "0cfadf2acb52"
down_revision: str | Sequence[str] | None = None
```

`revision` 是這個 migration 的 ID。`down_revision = None` 表示它是第一個 migration，沒有 parent revision。

### 3. `upgrade()` 是往前建立 schema

目前 migration 的 `upgrade()` 會呼叫：

```python
op.create_table(
    "import_batches",
    sa.Column("id", sa.Uuid(), nullable=False),
    sa.Column("source_system", sa.String(length=64), nullable=False),
    ...,
)
```

`op.create_table()` 是 Alembic 的 schema operation。它不會建立 Python object；它會在 migration transaction 裡執行 PostgreSQL DDL。

同一個 `upgrade()` 還會建立 foreign keys、check constraints、unique constraints 和 indexes。完整 table creation 順序在 [0cfadf2acb52 migration](../migrations/versions/0cfadf2acb52_create_phase_1_8_schema.py) 裡。

### 4. `downgrade()` 是回退 schema

目前 `downgrade()` 會依相反依賴順序刪除 tables 和 indexes。這是 schema rollback，不是刪除某些 application rows。

```bash
uv run alembic downgrade base
```

回到 `base` 後，這個 migration 建立的 domain tables 會被移除。這個 command 具有破壞性，只應在測試或明確允許的 local database 執行。

### 5. online 和 offline migration

`env.py` 有兩條路：

- `run_migrations_online()`：連線 PostgreSQL，實際執行 migration。
- `run_migrations_offline()`：只產生可執行的 SQL context，不直接建立資料庫連線。

一般的 `npm run db:migrate` 使用 online path。`env.py` 會先從 settings 拿 database URL，再建立 connection。[env.py:16-72](../migrations/env.py#L16-L72)

## 一個完整的小例子：`Organisation` 到 SQL

### Python model 描述

在 [`organisation.py`](../backend/app/models/organisation.py) 中，Python 大致描述了：

```python
class Organisation(Base):
    __tablename__ = "organisations"

    id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="active",
        server_default="active",
    )
```

### Database 的概念結果

這會對應到類似以下的 SQL 結構：

```sql
CREATE TABLE organisations (
    id UUID PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
    CONSTRAINT ck_organisations_status
        CHECK (status IN ('active', 'inactive'))
);
```

這段 SQL 是概念化展示；真正執行的 SQL 由 Alembic migration 產生並執行，應以 [migration file](../migrations/versions/0cfadf2acb52_create_phase_1_8_schema.py) 為準。

### 為什麼只用 Python model 還不夠

如果只改 `organisation.py`：

```text
Python metadata 改變
但 PostgreSQL 不會自動改變
```

要讓 database 改變，還需要：

```text
model change
  ↓
Alembic revision
  ↓
upgrade()
  ↓
PostgreSQL schema change
```

目前 `backend/app/database.py` 明確只建立 engine、session factory 和 connection check；它沒有隱式建立 tables 或執行 migration。[database.py:9-30](../backend/app/database.py#L9-L30)

## Step 5：`Engine`、`Session` 和 migration connection 的差別

### `Engine`

```python
engine = create_engine(settings.database_url, pool_pre_ping=True)
```

`Engine` 是 SQLAlchemy 管理 database connections 的入口。它知道要連哪裡、用哪個 driver，但建立 engine 不代表已經執行 SQL。

### `Connection`

```python
with engine.connect() as connection:
    connection.execute(text("SELECT 1"))
```

`Connection` 是一次可以執行 SQL 的連線。`check_database()` 用它做只讀 health check。

### `Session`

```python
def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )
```

`Session` 用來處理 ORM objects 的讀寫、flush 和 transaction。這個 factory 目前只是準備好 future workflow 使用；它不會自動 migrate schema，也不會自動 insert seed data。[database.py:20-23](../backend/app/database.py#L20-L23)

### migration 的 connection

Alembic 在 `env.py` 裡使用另一條 migration-specific path：

```python
connectable = engine_from_config(
    configuration,
    prefix="sqlalchemy.",
    poolclass=pool.NullPool,
)

with connectable.connect() as connection:
    _run_migrations(connection)
```

它用 connection 執行 DDL。這和 application session 寫一筆 donation 是不同工作。

## Step 6：測試如何證明 schema 真的存在

`backend/tests/conftest.py` 的 `migrated_connection` fixture 會：

1. 建立一個唯一的 PostgreSQL schema name。
2. 設定 `search_path` 到這個 test schema。
3. 呼叫 `command.upgrade(..., "head")`。
4. 在 isolated schema 裡執行 test。
5. 測試結束後 drop 該 schema。

```python
schema_name = f"test_foodflow_{uuid4().hex}"
connection.execute(text(f'CREATE SCHEMA "{schema_name}"'))
connection.execute(text(f'SET search_path TO "{schema_name}"'))
command.upgrade(_alembic_config(connection), "head")
```

這裡的 f-string 只用於建立 test schema identifier。schema name 是程式產生的 UUID，不接受 user input；這是目前 fixture 的安全前提。[conftest.py:24-50](../backend/tests/conftest.py#L24-L50)

`test_migrations.py` 再檢查：

- database table set 是否等於 `Base.metadata.tables` 加上 `alembic_version`；
- partial unique index 是否存在；
- composite foreign key 是否存在；
- check constraint 是否存在；
- stored revision 是否等於 Alembic head。

這證明的是 schema contract，不是 application seed 已經存在，也不是 ETL 已經完成。[test_migrations.py:10-61](../backend/tests/test_migrations.py#L10-L61)

## 你接下來寫 ETL 時，應該先看哪幾個概念

ETL 不應直接跳到 `session.add()`。目前 schema 已經提供一條 provenance-first 的入口：

```text
ImportBatch
  ↓
SourceRecord
  ↓
Organisation / Site / FoodProduct / Donation
```

### `ImportBatch`

代表一次外部來源匯入，例如一個 CSV、一次 structured form submission 或一個 external integration run。`idempotency_key` 防止同一批重跑時重複建立。

### `SourceRecord`

代表來源系統裡的一筆外部 record。它保留：

- `source_system`
- `source_record_type`
- `external_record_id`
- `observed_at`
- `raw_reference`
- `raw_payload`
- `ingest_status`

這些欄位讓 ETL 可以回答：「這筆 canonical data 從哪裡來？哪次 import 帶進來？來源何時看到它？」[source.py:122-190](../backend/app/models/source.py#L122-L190)

### ETL 的最小順序

```text
1. 讀取來源檔案或 API response
2. 建立 ImportBatch
3. 以 source_system + external_record_id 去重 SourceRecord
4. 保存 raw_reference / raw_payload
5. 驗證欄位和來源狀態
6. 將可確認的資料轉成 canonical Organisation / Site / Product / Donation
7. commit transaction
8. 記錄 completed 或 rejected 結果
```

這裡的「可確認」很重要：如果來源沒有提供 recipient capacity，就不要在 ETL 裡偷偷補一個數字。要補 simulated data 時，應在 seed manifest 或 source payload 留下 evidence、assumption rule、range 和 confidence。

## 驗證命令

### 查看目前 migration revision

```bash
uv run alembic current
```

預期會看到目前 database 的 revision，例如：

```text
0cfadf2acb52 (head)
```

### 執行 migration

```bash
npm run db:migrate
```

它實際執行的是 `uv run alembic upgrade head`。[package.json](../package.json#L8-L14)

### 檢查 model 和 migration 是否有 drift

```bash
npm run db:migrate:check
```

這會執行 `uv run alembic check`。它檢查目前 model metadata 和 migration state 是否出現未產生 migration 的差異。

### 執行 migration tests

```bash
uv run pytest backend/tests/test_migrations.py
```

如果要執行全部 backend tests：

```bash
npm run backend:test
```

## 容易混淆的地方

| 容易誤會的說法 | 正確理解 |
| --- | --- |
| `Base` 會建立 PostgreSQL tables | `Base` 只收集 Python model metadata；Alembic 才執行 DDL |
| `create_engine()` 會建立 schema | 它只建立 SQLAlchemy engine |
| `Session` 會自動 migrate | 不會；migration 要明確執行 |
| `Mapped[str]` 就等於 database `VARCHAR` | `Mapped` 是 ORM/type mapping，真正 database 欄位由 `mapped_column` 和 migration 決定 |
| `default=uuid4` 是 PostgreSQL default | 它是 Python-side default；要看 `server_default` 才是 database-side default |
| `nullable=True` 的欄位有資料 | 它只代表允許 NULL，不代表 ETL 已提供值 |
| migration 成功代表有 seed data | migration 只建立 schema；目前核心 tables row count 是 0 |
| model file 被放進 `models/` 就一定會被 Alembic 看見 | 必須被 import，最後進入 `Base.metadata`；目前由 `models/__init__.py` 集中 import |

## 下一頁應該讀什麼

先看 [database design research](database-design-research.md) 理解為什麼要把 source provenance、organisation/site、recipient state 和 operational facts 分開；再看 [database testing interview notes](database-testing-interview-notes.md) 理解哪些 constraint 和 migration behavior 要測。完成這兩頁後，再開始 ETL source mapping。

證據狀態：除特別標註外，本頁基於目前 repository source、migration tests 和本次本機 PostgreSQL read-only verification 已確認。
