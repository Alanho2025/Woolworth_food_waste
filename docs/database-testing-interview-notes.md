# Database Testing 面試複習筆記

> 用途：整理 relational database testing 的常見面向，方便面試前複習與口頭回答。
>
> 範圍：一般 database testing；例子以 PostgreSQL 語意說明。這不是目前 project schema 的 implementation specification，也不代表本 repository 已完成所有列出的測試。
>
> 更新日期：2026-08-09

## 先背這段：30 秒回答

Database testing 不只是測 CRUD，而是驗證資料層的 contract 在正常、錯誤、併發、部署和資料量變大時仍然成立。

我通常會看八個面向：**schema 和 migration、data integrity、query correctness、transaction、concurrency、performance、security、recovery**。

原因是很多 bug 只有真實 database engine 才會出現，例如 SQL 語意、constraint、rollback、lock、isolation level、migration 和 query plan。Unit test 可以測 business logic，但重要的資料行為要用和 production 相同的 database 做 integration test。

## 面試時可以用的八個問題

記法是：

> 資料怎麼建？怎麼不壞？怎麼查對？怎麼一起做？怎麼同時做？怎麼跑得快？誰能看？壞了能不能回來？

| 面向 | 通常測什麼 | 為什麼要測 | 常見驗證方式 |
| --- | --- | --- | --- |
| Schema / migration | 從空 database 建立 schema；從舊版本升級；欄位、型別、default、constraint、index 是否正確 | Migration 是部署時會執行的程式。既有資料可能不符合新 constraint，型別轉換也可能失敗 | 建立空 test database，套用全部 migration；再用代表性的舊資料測 upgrade |
| Data integrity | Primary key、foreign key、unique、not null、check、default、cascade | 防止 invalid data 和 orphan data 進入系統；database 是所有寫入來源共用的最後一道 consistency boundary | 測合法資料成功、非法資料被拒絕，以及 delete / update 的 referential action |
| Query / repository | CRUD、filter、join、aggregate、排序、pagination、NULL、soft delete、upsert、idempotency | Mock 不一定能發現實際 SQL 的語意錯誤，例如 join 產生重複列、NULL 比較錯誤或不同 database dialect 的差異 | 使用真實 database 執行 query，驗證結果、row count、排序、狀態和副作用 |
| Transaction / atomicity | 多筆寫入是否全部 commit；中途失敗是否全部 rollback；未 commit 的資料是否對其他 connection 隱藏 | 避免只完成一半的流程，例如 parent 已建立但 child、event 或狀態更新沒有完成 | 在多步操作中刻意注入錯誤，確認最後沒有 partial state |
| Concurrency / isolation | Double claim、lost update、重複 insert race、lock、deadlock、serialization failure、retry | 單執行緒測試可能通過，但真實系統會有多個 request 或 worker 同時操作同一筆資料 | 使用兩個以上獨立 database connections，同時執行操作，驗證最後狀態和衝突處理 |
| Performance | 重要 query 的 latency、index、query plan、join 成本、N+1、大資料量 | Query 在小 fixture 上很快，不代表 production volume 下仍然可接受；index 也會增加寫入成本 | 用 representative data 跑 `EXPLAIN ANALYZE`、benchmark 或 load test |
| Security / permissions | Database role 是否只有需要的 `SELECT`、`INSERT`、`UPDATE`、`DELETE`；tenant isolation；RLS；SQL injection 防護 | Application authorization 出錯時，database permission 可以提供第二層防線，避免不該讀或寫的資料被碰到 | 以不同 role 執行允許和禁止的操作；用惡意輸入測 parameterized query |
| Reliability / recovery | Connection timeout、database unavailable、deadlock、serialization retry、backup restore、啟動 readiness | Database 是有狀態系統；服務恢復後能否保留一致資料，通常比正常情況下能否寫入更重要 | 注入 connection failure，測 retry / error mapping；定期把 backup restore 到乾淨 database 驗證 |

不是每一項都要在每個 pull request 執行。Schema、integrity、query 和 transaction 通常是一般 integration suite；concurrency、performance、backup / restore 則可以放在較專門的測試或 release checks。

## 最重要的理由：為什麼不能只測 application code？

### Unit test 和 mock 能測什麼

Unit test 適合測：

- business rule 和狀態轉換；
- 輸入驗證與錯誤 mapping；
- 不需要 database 的 calculation；
- service 是否呼叫正確的 repository 方法。

這些測試速度快，也容易定位問題。

### Real database integration test 才能確認什麼

Real database test 才能確認：

- SQL 在 production engine 上真的有效；
- migration 能建立正確 schema；
- constraint 真的存在且會拒絕非法資料；
- transaction、rollback、lock 和 isolation 的實際行為；
- ORM 產生的 query 在 join、NULL、aggregate 和 pagination 上得到正確結果；
- index 和 query planner 在代表性資料量下的表現。

如果 production 使用 PostgreSQL，重要的 repository 和 transaction tests 應該使用 PostgreSQL test database，而不是只使用 SQLite、H2 或自製 fake database。替代 database 可能有不同的 SQL dialect、constraint、transaction 或 locking 行為。[Testcontainers 的 PostgreSQL 範例](https://testcontainers.com/guides/replace-h2-with-real-database-for-testing/)就是用 real PostgreSQL 取代 H2 來測 repository。

## 三個面試時很好用的具體例子

### 例子一：transaction rollback

假設一個流程要做三件事：

1. 建立 parent record。
2. 建立 child record。
3. 寫入 audit event。

如果第三步失敗，測試應確認第一和第二步也沒有留下來。這是在測 atomicity，不是只測 API 回傳了 500。

好的 assertion 是：

- response 或 service result 是預期的錯誤；
- parent、child 和 event 都沒有 partial state；
- 下一次 retry 不會因為殘留資料而重複或失敗；
- transaction 結束後，另一個 connection 只看得到完整 commit 的結果。

PostgreSQL 把 transaction 定義成 all-or-nothing operation；如果中途失敗，已執行的步驟不應影響 database。[PostgreSQL Transactions](https://www.postgresql.org/docs/current/tutorial-transactions.html)

### 例子二：兩個 worker 同時 claim 一個 resource

T1 和 T2 同時嘗試 claim 同一筆尚未分配的 resource。預期結果通常是：

- 只有一個成功；
- 另一個收到 conflict、retryable error 或明確的「已被其他人取得」結果；
- 最後資料只有一個 owner；
- 不會產生兩筆 active allocation 或兩個成功 event；
- 測試不靠任意 `sleep` 猜 race timing，而是用 barrier / lock 讓兩個 connection 在指定位置同時前進。

這類測試是為了驗證 isolation、unique constraint、row lock 或 application retry 是否共同守住 invariant。PostgreSQL 文件列出不同 isolation level 可能出現的 nonrepeatable read、phantom read 和 serialization anomaly，也說明 deadlock 可能導致其中一個 transaction 被 abort。[Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html)、[Explicit Locking](https://www.postgresql.org/docs/current/explicit-locking.html)

### 例子三：constraint 的邊界

```sql
price numeric CHECK (price > 0)
```

這個 constraint 可以拒絕負數，但在 PostgreSQL 中，`CHECK` expression 結果是 `TRUE` 或 `NULL` 都會被視為通過。因此如果需求是不允許 `NULL`，還必須另外加 `NOT NULL`。

所以 constraint test 不應只測一個 invalid value，至少要測：

- 合法值可以寫入；
- 負數被拒絕；
- `NULL` 是否按照需求被拒絕；
- duplicate key 被拒絕；
- 不存在的 foreign key 被拒絕；
- parent delete 時的 cascade 或 restrict 行為正確。

這也是為什麼 database test 要測 database 的實際 constraint，而不是只測 application validator。[PostgreSQL Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html)

## 測試應該怎麼分層？

| 測試層 | 主要目的 | 是否使用真實 database |
| --- | --- | --- |
| Unit test | Business rule、狀態轉換、純 calculation、錯誤 mapping | 通常不使用；可以 mock repository |
| Database integration test | Schema、SQL、repository、constraint、transaction、實際資料結果 | 使用和 production 相同的 engine |
| Migration test | Fresh database、upgrade、必要時 downgrade / re-upgrade | 使用真實 database，直接執行 migration |
| Concurrency test | 多 connection 的 race、lock、isolation、retry | 必須使用真實 database 和獨立 sessions |
| Performance test | Query plan、latency、throughput、大資料量 | 使用代表性資料量，通常獨立執行 |
| Operational test | Backup restore、database outage、connection pool、recovery | 在 release 或定期環境執行 |

好的測試策略不是「所有測試都碰 database」，也不是「database 都 mock 掉」，而是讓每個 bug 在最接近它發生的層被驗證。

## 最小可行的 database test suite

如果時間有限，我會按以下順序做：

### P0：每個重要 database project 都應有

1. **Fresh migration**：空 database 可以從頭建立到最新 schema。
2. **Schema integrity**：重要的 PK、FK、unique、not null、check 都有正向和負向案例。
3. **Critical queries**：重要 repository query 在真實 database 上回傳正確 rows、排序、狀態和 aggregate。
4. **Rollback**：每個跨多張 table 的寫入流程都有中途失敗測試。
5. **Test isolation**：測試不依賴執行順序，也不會污染下一個測試。
6. **Migration upgrade**：至少用一個代表性的舊 schema / 舊資料測升級。

### P1：有共享狀態或高流量時補上

1. Double claim、duplicate insert 或 counter update 的 concurrency test。
2. Deadlock / serialization failure 的 retry test。
3. Critical query 的 representative-data `EXPLAIN ANALYZE` 或 latency baseline。
4. Role、tenant isolation 或 Row-Level Security test。
5. Backup restore 和 database outage test。

## 測試 isolation 的常見做法

每個測試應該使用獨立的：

- test database；
- schema；
- transaction；或
- 可可靠 rollback / truncate 的 fixture。

同時要注意：如果測試本身就是在驗證 commit、rollback、trigger、sequence、通知或多 connection visibility，就不能把所有東西包在一個永遠不 commit 的外層 transaction 裡，否則測到的是 test harness，不是 production 行為。

測試資料也應包含 boundary cases：

- 空集合、單筆、多筆；
- duplicate；
- `NULL`；
- 最大長度和最小 / 最大數值；
- 不同 timezone；
- 小數精度；
- 已刪除、已過期、inactive 或 soft-deleted records；
- 兩個 transaction 同時操作同一筆資料。

Django 的官方 test runner 是一個具體例子：它會建立獨立 test database、套用 migrations、執行測試，最後清理 test database；文件也提醒，沒有 isolation 的 database tests 可能單獨通過，但因測試順序而在整套測試中失敗。[Django testing overview](https://docs.djangoproject.com/en/5.2/topics/testing/overview/)

## Performance test 要怎麼答

面試時不要只說「我會測 response time」。比較完整的回答是：

1. 先挑出 user-facing 或高頻率的 critical queries。
2. 使用接近實際資料量和分布的 fixture，而不是只有幾筆資料的 toy database。
3. 用 `EXPLAIN ANALYZE` 看 execution time、實際 row count、scan type、join、sort 和是否使用 index。
4. 設定可解釋的 latency / throughput threshold。
5. 注意 index 的 trade-off：它可以加速讀取，但會增加 insert、update 和儲存成本。
6. 不要把完整 query plan 的每一行都寫死成測試；除非某個 index 或 scan strategy 是明確的 contract，否則應優先驗證結果和合理的效能門檻。

PostgreSQL 官方文件也提醒，`EXPLAIN` 的結果會受資料量、statistics 和環境影響；小資料集上的 plan 不一定能代表大資料集。[Using EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html)、[Indexes](https://www.postgresql.org/docs/current/indexes.html)

## 常見追問的短答

### 「為什麼不全部 mock database？」

因為 mock 只能驗證 application 對 repository 的假設，不能證明 SQL、constraint、transaction、lock、migration 和 query plan 在真實 database 上正確。Mock 適合 unit test，但不能取代 integration test。

### 「為什麼不全部用 SQLite in-memory？」

因為 production database 的 dialect 和行為可能不同。SQLite、H2 或其他替代品可能在型別、foreign key、transaction、locking、JSON、index 或 SQL function 上與 PostgreSQL 不一致。重要的資料行為要用 production engine 驗證。

### 「Database constraint 已經測過了，application validation 還要測嗎？」

要。兩者責任不同：application validation 可以提供較好的 UX 和錯誤訊息；database constraint 則保護最後的資料完整性。兩層都需要，但不要只依賴其中一層。

### 「Migration 要測什麼？」

至少測 fresh install 和 upgrade。若 project 支援 rollback，再測 downgrade / re-upgrade。特別要測既有資料、default、constraint、型別轉換和 migration 順序。

### 「Concurrency test 怎麼避免 flaky？」

使用獨立 connections、barrier、明確 lock point 和可預期的資料狀態，不要用任意 sleep。Assertion 應檢查最後的 invariant，例如只能有一個 owner，而不是依賴哪個 thread 先完成。

### 「測試只要沒有 exception 就算過嗎？」

不算。應該驗證 database 的最後狀態：row count、欄位值、status、relationship、event 數量、是否存在 partial state，以及 retry 後是否仍然 idempotent。

## 不要這樣答

- 只說「測 CRUD」，沒有提到 constraint、transaction 或 concurrency。
- 只說「所有測試都用 mock」，卻沒有 real database integration test。
- 只測 happy path，不測 invalid data、rollback、duplicate 和空資料。
- 用單一 connection 測 concurrency。
- 把小資料集的 query time 當成 production performance 證據。
- 把 PostgreSQL、SQLite、H2 的測試結果當成完全等價。
- 只看 API status code，不檢查 database 最後是否留下 partial state。

## 最後的背誦版

> 我會把 database testing 分成 schema / migration、data integrity、query correctness、transaction、concurrency、performance、security 和 recovery。這些測試的目的，是確保資料不會被寫壞、跨多步驟操作不會留下 partial state、多人同時操作時仍維持 invariant，而且部署和資料量增加後仍然可用。Unit test 可以測 business logic，但 SQL、constraint、transaction、lock 和 migration 要用與 production 相同的 database 做 integration test。測試結果不能只看有沒有 exception，而要檢查最後的資料狀態、錯誤處理和 retry 是否正確。

## 主要參考資料

- [PostgreSQL Constraints](https://www.postgresql.org/docs/current/ddl-constraints.html)
- [PostgreSQL Transactions](https://www.postgresql.org/docs/current/tutorial-transactions.html)
- [PostgreSQL Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html)
- [PostgreSQL Explicit Locking](https://www.postgresql.org/docs/current/explicit-locking.html)
- [PostgreSQL Modifying Tables](https://www.postgresql.org/docs/current/ddl-alter.html)
- [PostgreSQL Indexes](https://www.postgresql.org/docs/current/indexes.html)
- [PostgreSQL Using EXPLAIN](https://www.postgresql.org/docs/current/using-explain.html)
- [PostgreSQL Privileges](https://www.postgresql.org/docs/current/ddl-priv.html)
- [Django testing overview](https://docs.djangoproject.com/en/5.2/topics/testing/overview/)
- [Testcontainers：用 real PostgreSQL 取代 H2 做測試](https://testcontainers.com/guides/replace-h2-with-real-database-for-testing/)

證據狀態：本文的 PostgreSQL 行為以官方文件為依據；測試分層與面試回答結構是一般工程實務整理，不是對所有 database、framework 或公司的正式規範。
