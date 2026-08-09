# FoodFlow database design plan

> 文件狀態：Phase 1–9 schema 與 migration 已完成並通過本機 PostgreSQL 驗證；first delivery slice 仍只做成功路徑，runtime workflow 尚未建立。
> 更新日期：2026-08-09
> 目前已建立 SQLAlchemy model 與 Alembic migration；尚未建立 seed data、API、service、AI 或 UI。
> 產品邊界：KiwiHarvest driver是primary user；系統協助他把verified donor site（Woolworths或community organisation）的可分流食物送到合適的recipient organisation site。Driver確認一般match / route；safety hard block不可override，高風險exception交coordinator，recipient另行accept / decline。

## Plan outcome

這份計畫採用「逐張 table 設計、逐段 relationship 驗證」的方式。每張 table 在進入 migration 前，都必須先完成 field-level data dictionary、relationship contract、代表案例和 constraint test mapping。

計畫的成功結果不是「列出很多 table names」，而是得到一套可以回答以下問題的 approved schema contract：

1. 每個 field 代表什麼 business fact，由誰提供，何時有效。
2. 缺值代表 unknown、not applicable、not yet received 還是 zero。
3. 每個 relationship 的 cardinality、FK owner、optional / required 和 delete behaviour。
4. 哪些資料可以更新，哪些必須留下 snapshot、decision 或 event history。
5. 一筆supply如何從Woolworths或community site經過deterministic feasibility、agent priority、human decision、allocation和route proposal，最後形成driver delivery。
6. Community收到後的剩餘量如何建立linked onward offer，而不改寫原receipt、condition、quantity或custody history。

## Scope

### In scope

- PostgreSQL relational schema 的 field 與 relationship design。
- Woolworths、KiwiHarvest、community donor / recipient organisation、driver / staff、site / location與多角色關係。
- Barcode / food identity、donation batch、donation items。
- Recipient capability、need、availability / capacity snapshot。
- Match candidate、human decision、allocation。
- 一位driver planning session內的bounded agent route priority、route-input snapshot、proposal / approval與point-to-point或簡單多站delivery contract。
- 在required live inputs可用的前提下，保存traffic、road event、weather warning、ETA、source與valid time。
- Source provenance、status history、constraint、migration 和 database tests 的規劃。

### Out of scope

- Consumer-level account、consumer voice request、audio / transcript。
- 全Auckland、多driver / vehicle的global fleet optimisation，以及未經human approval的autonomous rerouting。
- 車輛即時GPS、fleet telemetry、正式driver shift optimiser。
- Provider outage、stale-data fallback、degraded route、active-route refresh / retry policy。
- Decline、failed pickup / delivery、reservation release、manual rematch與其他failure-specific transitions / fields。
- Community收貨後re-offer的exact tables、barter / donation、hop、quantity movement和recall implementation；只保留不阻塞未來的organisation-role / lineage boundary。
- 長期forecasting、reliability model、carbon accounting。
- StoreCentral live integration；在 source contract 未取得前，只規劃 adapter boundary。
- 完整prompt、embedding、chain-of-thought或model-training dataset；MVP只規劃route / match input version、policy / model identifier、reason codes與human decision audit。
- 本輪不建立 seed data、API、service、AI 或 UI；database tables 由 Phase 9 migration 建立。

## Research findings [schema implementation completed; runtime slice pending]

- **Evidence examined:** [`database-design-research.md`](./database-design-research.md)、[`research.md`](./research.md)、[`foodflow-mvp-feature-spec.md`](./foodflow-mvp-feature-spec.md)、兩份Notion原始頁面、repository foundation、現有database / health tests，以及Woolworths / Kai Commitment、GS1、MPI、KiwiHarvest、NZ Food Network、Privacy Commissioner、Auckland City Mission、Business.govt.nz、Google Routes / Route Optimization、NZTA與MetService的主要公開來源。
- **Confirmed current state:** Repository 有 FastAPI `/health`、PostgreSQL connection check、Next.js foundation、Phase 1–8 SQLAlchemy models、Phase 9 Alembic migration，以及以臨時 PostgreSQL schema 驗證 migration 的 backend tests。沒有 seed data 或 runtime workflow service。
- **Gaps:** Current KiwiHarvest partner roster、exact food-condition vocabulary / checkpoints、reservation timing、route planning scope / priority，以及normal live-provider response contract仍未取得。Provider outage / fallback、failure transitions與onward redistribution details已移出first slice。Future StoreCentral sample payload仍未知，但不阻擋structured-form MVP。
- **Weak reasoning:** Barcode不能代表完整donation event；public address不能直接當navigation point；年度throughput不能當live capacity；距離最近不能取代safety、condition、storage、need、capacity、time-window、weather / road risk與traffic-aware ETA。
- **Unsupported assumptions rejected by evidence:** 不能假設所有 food 都有 barcode、barcode就是 donation、所有 public candidates都是 active recipients、organisation只有一個 location、annual throughput就是 current capacity、Highbrook是所有 route origin、最近位置就是最佳 match、StoreCentral alert就是 final approval或 route instruction。
- **Assumption alignment:** Q1–Q8均已`human-aligned`：structured form + optional barcode、driver / coordinator / recipient authority、time-bound capacity、initial single-recipient allocation、agent route / priority、manual rematch、verified / protected location policy，以及safety hard block / manual review。Community可成為supply source並re-offer surplus也已`human-aligned`。
- **Evidence-validated boundaries:** Product / donation分離、organisation / site / typed location分離、recipient capability / need / availability分離、research / operational分離、multi-stagecommunity redistribution存在、每次handoff需traceability、live traffic / road / weather data存在，以及nearest-only假設失敗。
- **Missing requirements for first slice:** Supported quantity units、food taxonomy / condition values、condition checkpoints、success-path reservation timing、route planning horizon與priority order。
- **Ambiguities:** `food` 可指 product master 或一次 donation item；`location` 可指 public address、site centroid、pickup point 或 receiving entrance；`need`、`capability`、`capacity` 的時間語意不同；`driver` 可指 person、role 或 delivery assignee。
- **Contradictions resolved by owner:** Consumer-direct需求不在MVP；不另建scanner；initial item不split；driver確認一般match / route；routeagent納入現在的bounded scope並覆蓋舊feature-page「future」標示。這不授權full-fleet optimisation或autonomous rerouting。
- **Questions that require human answers:** Phase 9 migration scope 沒有新增需要 owner 回答的問題；P1-Q1–Q4 已依目前 owner alignment 進入 schema implementation。runtime failure behavior 與 onward redistribution 仍是 deferred。

Research結論是「先完成一條正常的donor-to-recipient delivery，再擴充failure與onward redistribution」。已固定的conceptual boundaries不再重問；延後項目不再阻擋first slice。

### Three-loop status summary

| Loop | Result | Plan consequence |
| --- | --- | --- |
| 1 — Repo / Notion / current docs | 確認 current MVP feature boundary、空白 repository，以及 driver-first與 Notion approver wording的矛盾 | 不把文件聲稱當已實作；Gate A、B、E、G需 owner對齊。 |
| 2 — Primary public evidence | 驗證 StoreCentral、barcode coverage、food safety、recipient organisation / site、capacity和 privacy boundary | Gate C、D、F的 conceptual方向可縮小；exact operational contract仍 blocked。 |
| 3 — Counterexample stress tests | No-barcode、mixed lot、wrong public address、stale capacity、direct / cross-dock、partial stop failure和 protected location均擊穿簡化模型 | 不把 recipient FK放 donation；保留 typed locations、snapshots、allocations、ordered stops和 append-only events。 |
| Owner alignment + scope reduction | Q1–Q8已回答；route必須考慮priority / weather / traffic；owner要求first slice只做成功路徑 | Route不以nearest為主；failure / outage與onward implementation延後；P1-Q1–Q4成為唯一first-slice frontier。 |

## Human decision gates

| Gate | 必須回答的問題 | Assumption status | 影響的 table / relationship | 未回答時的處理 |
| --- | --- | --- | --- | --- |
| A — Actor | 誰建立donation、誰approve match / route、誰accept / decline、exception由誰處理？ | Q2-A `human-aligned` | `users`、`organisation_memberships`、`match_decisions`、route decisions、status events | Authority boundary可進field design；auth / login、membership scope與protected-action audit留到Phase 3，不需要先做完整user功能。 |
| B — Source | MVP source、barcode與future StoreCentral邊界是什麼？ | Q1-A `human-aligned`；StoreCentral published flow `evidence-validated` | `import_batches`、`source_records`、`food_products`、`donations` | Structured form + optional barcode可進field design；CSV只作seed / test；future integration fields不得假裝已知。 |
| C — Donation / condition / safety | 哪些lot、date、temperature、condition或unit差異拆line？成功路徑在哪些checkpoints觀測condition？ | Q8-A `human-aligned`；P1-Q1 `unresolved` | `donations`、`donation_items`、condition observations、eligibility decisions | Hard block / manual review方向可固定；condition vocabulary、mandatory fields與checkpoint cardinality等P1-Q1。 |
| D — Recipient state | `capability`、current `need`、remaining `capacity`如何按food / storage lane、quantity / unit、window與validity表示？ | Q3-A `human-aligned` | recipient state tables | Concept contract可進field design；supported units、stale SLA與correction rules需在Phase 6完成。 |
| E — Allocation / reservation | Initial item是否split？成功路徑何時reserve與confirm？ | Q4-A `human-aligned`；P1-Q4 `unresolved` | `allocations`、matching transaction | 一個item同時只可有一個active recipient allocation；first slice不定義timeout / release / failure behavior。 |
| F — Location | Research、operational與protected point如何驗證及揭露？ | Q7-A `human-aligned` | `sites`、`site_locations`、access control | FY25/current都可保留；routing只讀operator-confirmed point；protected exact point限assigned actor並留audit。 |
| G — Agent route | 一位driver的一次planning範圍與可行候選priority policy是什麼？ | Agent route direction `human-aligned`；P1-Q2–Q3 `unresolved` | route planning runs、input snapshots、proposals / decisions、deliveries / stops | First slice假設required live snapshots可用；不凍結provider outage、degraded fallback或active-route refresh behavior。 |
| H — Failure lifecycle（deferred） | Decline、timeout、failed pickup / delivery與manual rematch的exact transitions。 | Q6-A是future direction；first slice明確延後 | Future status events、reason / custody / release relationships | 不阻擋first slice；現在只設計成功事件與可延伸event identity / actor / time boundary，不加failure-specific fields。 |
| I — Onward redistribution（deferred） | Community re-offer的participant、transaction meaning、hop、quantity / lot / custody lineage。 | Requirement direction `human-aligned`；exact behavior延後 | Future onward offers、custody transfers、lineage / quantity movements | Community可作first-slice donor；收到後再re-offer不進first slice table order。 |

## Per-table design contract

每張 table 必須先完成一份 data dictionary。未完成以下欄位，不得建立 migration：

| Design item | 必須記錄的內容 |
| --- | --- |
| Table purpose | 只寫一個主要責任；若同時保存 master、snapshot 和 event，應拆分或解釋原因。 |
| Field name | PostgreSQL / SQLAlchemy 使用的 exact identifier。 |
| Business meaning | 這個 field 在 KiwiHarvest / Woolworths workflow 中代表的事實。 |
| Data type | PostgreSQL type、precision、timezone、enum / lookup strategy。 |
| Null semantics | `NULL` 的明確意思；不得讓 unknown 和 zero 共用語意。 |
| Default | Database default、application default 或不得有 default。 |
| Identity | PK、external identity、natural candidate key，以及名稱 / barcode 為何不能當 internal PK。 |
| Relationship | FK target、cardinality、optional / required、FK 所在 table。 |
| Integrity | `NOT NULL`、`UNIQUE`、`CHECK`、FK、transaction-level invariant。 |
| Update ownership | 哪個 actor / source 可以建立、修正或 supersede。 |
| Time semantics | `observed_at`、`recorded_at`、`valid_from`、`valid_until`、event time 的選擇。 |
| History behaviour | 可直接 update、需要新 snapshot、需要 append-only event，或只能 deactivate。 |
| Delete behaviour | `RESTRICT`、受控 archive、或只允許刪除未發布 draft；不得默認 cascade operational history。 |
| Sensitivity | Public、operational-only、personal、protected location。 |
| Example | 一個 neutral valid row 和一個 boundary / invalid case；不得冒充真實 operator data。 |
| Evidence status | `已確認`、`人類已對齊`、`計畫中` 或 `未確認`。 |

### Table definition of done

一張 table 只有在以下條件全部成立時才算設計完成：

1. 每個 field 都填完上方 data dictionary。
2. 每個 FK 都能說明 parent、child、cardinality 和 delete behaviour。
3. 至少有一個 valid row、invalid row 和 relationship case。
4. 已定義 unique / check / FK constraint 的責任邊界。
5. 已說明同一 source record 重送時如何避免 duplicate。
6. 已說明 correction 是 update、new snapshot 還是 compensating event。
7. 已把所有 unresolved field 對應到 human decision gate；不能用任意 nullable 欄位掩蓋問題。
8. 已列出未來 migration test，並能說明它證明哪個 business invariant。

## Proposed table order

下表是計畫中的 dependency order，不代表已批准 schema。每個 phase 仍採一張 migration 一次，先驗證 parent table，再建立 child / junction table。

| Order | Proposed table | Responsibility | Depends on | Current gate |
| ---: | --- | --- | --- | --- |
| 1 | `organisations` | Woolworths、KiwiHarvest與community organisation的穩定identity | — | 可開始field design |
| 2 | `organisation_roles` | 同一organisation可同時是donor、food-rescue operator、hub與recipient | `organisations` | First slice載入operator-verified organisations；onboarding policy延後 |
| 3 | `sites` | 某 organisation 之下的 store、branch、warehouse、service site identity | `organisations` | 可開始 field design |
| 4 | `site_locations` | Public address、map point、pickup / receiving point、precision、verification與visibility | `sites` | 1:N typed location及Q7 policy已對齊；exact reveal audit待Phase 2 |
| 5 | `partner_relationships` | 保存KiwiHarvest與donor / recipient / hub關係、驗證狀態和有效期間 | organisations / sites | Current roster未知；first slice只使用已驗證fixture / operational rows |
| 6 | `users` | Driver、dispatcher、store staff、recipient staff 的 person / account identity | — | Authentication scope 未確認；person identity 可先設計 |
| 7 | `organisation_memberships` | User與organisation / site的role、有效期間和active state | users / organisations | Gate A方向已對齊；auth實作延後 |
| 8 | `import_batches` | 一次structured-form / CSV / future integration ingest boundary | — | Q1已對齊；CSV只作seed / test |
| 9 | `source_records` | External record id、observed / recorded time、raw provenance、ingest result | import batches | MVP manual identity待field design；future StoreCentral mapping未知 |
| 10 | `food_products` | Optional barcode / GTIN product identity和可重用描述 | source records optional | Barcode optional已驗證 |
| 11 | `donations` | Woolworths或community donor的一次first-slice supply event、source site、pickup window、safe deadline、current state | source site / actor / source record | Gates B、C；onward generalisation延後 |
| 12 | `donation_items` | Donation內的food snapshot、lot、quantity、unit、storage / date facts | donation / food product optional | Gate C；food taxonomy未確認 |
| 13 | `food_condition_observations` | First-slice listing / pickup / delivery checkpoints的condition、temperature、observer與time | donation item / actor；後續可連stop | P1-Q1 |
| 14 | `donation_status_events` | First-slice success transition、actor與time | donation / users | Failure-specific types / reason data延後 |
| 15 | `recipient_capabilities` | Site長期可接受的food / storage / handling capability | recipient site | Gate D方向已對齊 |
| 16 | `recipient_needs` | 某段有效期內希望接收的food / quantity / priority | recipient site | Gate D；P1-Q3決定priority使用方式 |
| 17 | `recipient_availability_snapshots` | 某時間點按food / storage lane的remaining capacity、receiving window和expiry | recipient site | Q3已對齊；supported units / stale rule待Phase 6 |
| 18 | `match_runs` | 一次matching execution的target、deterministic input / policy version和time | donation / items | Gates C、D |
| 19 | `match_candidates` | 每個candidate site的eligibility、rank與reason codes | match run / recipient site | Hard feasibility與agent ranking需分欄；P1-Q3 |
| 20 | `match_decisions` | First-slice driver confirmation與recipient acceptance的separate decision facts | candidate / actor | Gate A已對齊；decline / failure decision types延後 |
| 21 | `allocations` | Donation item與recipient site之間的single-recipient reservation / fulfilment | item / site / decision | Q4已對齊；P1-Q4 success timing |
| 22 | `allocation_status_events` | First-slice reserved、confirmed、fulfilled歷史 | allocation / actor | Release / cancel / failure-specific transitions延後 |
| 23 | `route_planning_runs` | 一次bounded agent planning execution、planning horizon、policy / model id與overall status | accepted / reserved allocations；driver | P1-Q2–Q3 |
| 24 | `route_input_snapshots`（exact split待定） | Planning當下的allocation、condition、capacity、location、traffic、road event、weather、ETA、freshness與coverage references | route planning run / source records | Gate G；不可只存最終stop order |
| 25 | `route_proposals` | Agent提出的ordered stops、priority reasons、score / cost components與version | route planning run | Gates G、A；proposal不可直接commit |
| 26 | `route_decisions` | Driver confirmation或coordinator exception decision與time | route proposal / actor | Q2已對齊；failure / degraded decisions延後 |
| 27 | `deliveries` | Human-approved、由driver執行的pickup / delivery job與committed route version | route decision / driver membership | Gate G；不能固定Highbrook |
| 28 | `delivery_stops` | Approved stop order、site location、time window、planned / actual result | delivery / site locations | Gates F、G |
| 29 | `delivery_allocations` | Delivery與allocation的M:N junction，支持一趟多貨／多站 | deliveries / allocations | Gates E、G；不代表initial item split |
| 30 | `delivery_status_events` | First-slice assigned、started、arrived、collected、delivered歷史 | delivery / actor | Failed / cancelled types與reason records延後 |

以上是first-slice conceptual dependency order，不代表30張table都已批准或都必須獨立存在。Condition observation是否獨立table、route-input snapshot如何正規化，以及哪些success events可共用一個設計，會依P1-Q1–Q4逐張判斷。若較簡單設計能保留相同business meaning、FK integrity、history與查詢能力，可以合併；不得只為減少table數量而丟失語意。

`custody_handoffs`、`supply_lineage`、`quantity_movements`、failure reason / provider-health等只列為future extension candidates，不進first-slice dependency order，也不先定義fields。

## Relationship baseline

| Parent / left side | Cardinality | Child / right side | FK / junction owner | Design reason | Status |
| --- | --- | --- | --- | --- | --- |
| `organisations` | 1:N | `sites` | `sites.organisation_id` | 一個 organisation可有多個 store / branch / hub / recipient service site | Concept `evidence-validated`；fields計畫中 |
| `sites` | 1:N | `site_locations` | `site_locations.site_id` | Public point、service entrance和protected operational point不能被視為同一座標 | Concept `evidence-validated`；Q7 policy `human-aligned` |
| `users` | M:N | `organisations` | `organisation_memberships` | 同一 user 可能隨時間有不同 organisation / role | 計畫中；Gate A |
| Verified source site | 1:N | `donations` | `donations.source_site_id` | Woolworths或community site都可建立多次first-slice supply；source role不能由site name推導 | Product scope `human-aligned`；onward relation延後 |
| `donations` | 1:N | `donation_items` | `donation_items.donation_id` | 一批 donation可包含不同 lot、category、unit、temperature或 date mark | Concept `evidence-validated`；Gate C fields未確認 |
| `food_products` | 1:N | `donation_items` | Nullable `donation_items.food_product_id` | Barcode / product master可重用，但 bulk / unknown food仍需 line snapshot | Concept `evidence-validated`；Gate B mapping未確認 |
| Donation item | 1:N | Condition observations | observation的item FK | Condition可能在listing、pickup與delivery改變，不能只放一個可覆寫欄位 | Concept `evidence-validated`；P1-Q1 cardinality |
| Recipient site | 1:N | capability / need / availability | 各 recipient state table 的 `site_id` | Stable capability、time-bound need和live capacity更新頻率不同 | Concept `evidence-validated`；Q3-A `human-aligned` |
| `match_runs` | 1:N | `match_candidates` | `match_candidates.match_run_id` | 一次 matching 需要保存所有候選和被排除原因 | 計畫中 |
| `match_candidates` | 1:0..1 | `match_decisions` | `match_decisions.match_candidate_id` | 同一次candidate不覆寫decision；新planning需new run / candidate | Proposed；Gate A |
| Donation items | M:N over history；最多1個active recipient | Recipient sites | `allocations` | Q4-A禁止initial active split；first-slice reservation timing由P1-Q4決定 | `human-aligned`；P1-Q4 |
| `route_planning_runs` | 1:N | `route_proposals` | `route_proposals.route_planning_run_id` | 同一input run可比較或supersede proposals；舊proposal不被覆寫 | Proposed；Gate G |
| `route_planning_runs` | 1:N | Route input facts / snapshots | snapshot / reference的run FK | 必須重建agent當時看見的traffic、weather、road、capacity與condition | `evidence-validated` boundary；exact normalisation未確認 |
| `route_proposals` | 1:N | `route_decisions` | decision的proposal FK | Agent proposal與driver / coordinator commit不同責任 | Q2 `human-aligned`；failure / degraded gate延後 |
| `deliveries` | M:N | `allocations` | `delivery_allocations` | 一趟可帶多筆allocation；initial item仍不split | Proposed；Gates E、G |
| `deliveries` | 1:N | `delivery_stops` | `delivery_stops.delivery_id` | Approved route order和每站actual result屬於一次delivery execution | Proposed；Gate G |
| Custody receipt / handoff | 1:N | Child supply lineage | Future lineage / quantity-movement FK | Community re-offer必須連回已收到的lot與available quantity，不可改寫原recipient | Future-fixed boundary；not first slice |
| Operational aggregate | 1:N | Dedicated status events | Event table 的 aggregate FK | Current state 不應抹除 actor、reason 和時間歷史 | 計畫中；Gate H |

## Representative case used throughout the plan

以下是 neutral design scenario，不是 Woolworths 或 KiwiHarvest 的已確認 operational data：

> 一個verified Woolworths或community donor site在14:00以structured form建立25 kg chilled dairy donation，pickup window是14:00–16:00，safe deadline是18:00。A最近但只剩15 kg capacity；B無chilled storage；C因live congestion會錯過deadline；D較遠、有完整capacity與urgent need，且traffic-aware ETA可按時到達。Agent提出D與route理由，driver確認，D accept，driver完成collection與delivery。

每個 phase 都要能回答與自己相關的部分：

- Identity phase：A、B、C、D是organisation還是site？D之後同時成為recipient與donor如何表示？
- Location phase：公開地址和 driver receiving point 不同時，哪一筆可導航？
- Donation phase：25 kg 是 batch total 還是某一 item quantity？product master 變動是否影響已列出的 donation？
- Recipient phase：A的15 kg是capability、need、availability還是reservation後剩餘值？D的urgent need何時有效？
- Match phase：A、B、C的exclusion reason如何分開保存？D為何在較遠情況仍排名第一？Initial item不split如何由constraint保護？
- Route phase：Static / traffic-aware ETA、weather / road events、freshness、priority reason、agent proposal與driver decision如何分開？
- Delivery phase：Planned / approved / actual stops與condition observations如何追蹤到successful delivery completion？

Failed stop / manual rematch與D之後re-offer剩餘food是下一個slice的代表案例，不是first-slice completion criteria。

## Phase 0 — Close first-slice decisions and conventions [blocked: awaiting P1-Q1–Q4]

- **Phase goal:** 產出可批准的 field template、naming / type conventions、P0 decision ledger，以及每個 unresolved decision 所阻擋的 table list。
- **Affected components:** 本文件、[`database-design-research.md`](./database-design-research.md)、[`foodflow-mvp-feature-spec.md`](./foodflow-mvp-feature-spec.md)；未來 implementation 會影響 `pyproject.toml`、migration framework 和 database tests，但本 phase 不改 code。
- **Data flow:** Existing evidence + owner answers → assumption status (`evidence-validated` / `human-aligned` / `unresolved`) → approved schema conventions → table design entry gates。
- **Pseudocode:** `for each material decision: search evidence; if owner decision, record answer; map answer to affected fields/relationships; keep dependent table blocked until resolved`。
- **Edge cases:** Unknown 不等於 zero；external id 不等於 internal PK；protected location 不進 public seed；source document claim 不等於 implemented contract。
- **Tests:** 用first-slice representative case、bulk/no-barcode與nearest-but-infeasible案例檢查field template；確認每個current question都有owner、evidence或明確deferred標記。
- **Completion criteria:** P1-Q1–Q4關閉；Gates A–G足以支援成功路徑；Gates H–I明確deferred且不阻擋；ID、timestamp、quantity、unit、enum、delete / history conventions已批准。

## Phase 1 — Organisation identity [blocked]

- **Phase goal:** 完成`organisations`，並判斷`organisation_roles`是否需要獨立table；Woolworths、KiwiHarvest與community organisations不再各自建立重複master table，同一organisation可同時是donor / recipient / hub。
- **Affected components:** Planned table specs for `organisations` / `organisation_roles`；未來 proposed model / migration / database tests。
- **Data flow:** Public or operator source identity → deduplication / review → canonical organisation → one or more operational roles。
- **Pseudocode:** `resolve external identity; find active canonical organisation; create or update allowed descriptive fields; append role assignment with validity; never create a new organisation only because display name changed`。
- **Edge cases:** 同名不同organisation、organisation rename、KiwiHarvest同時是food-rescue operator和hub、community organisation先收貨後成為donor、FY25 name與current name不同、closed organisation仍被歷史supply引用。
- **Tests:** Unique external identity；允許相同display name但不同verified identity；有歷史FK的organisation不能hard delete；D在同一identity下由recipient增加donor role，不複製organisation row。
- **Completion criteria:** First slice可載入已由operator驗證的Woolworths與community organisations / sites；所有fields的source / null / update / history定義完成；1:N organisation-to-site FK ownership與role validity批准。Participant onboarding policy延後。

Phase 1目前標記blocked，因為Phase 0尚未批准ID、external identity、participant boundary、role和delete conventions；不代表必須先做login功能。

## Phase 2 — Site and operational location [blocked]

- **Phase goal:** 完成 `sites`、`site_locations` 和候選 relationship model，使 research point、public address 和 operator-confirmed navigation point可被清楚區分。
- **Affected components:** Planned specs for `sites`、`site_locations`、可能的 `partner_relationships`；未來 store / recipient seed strategy 和 map query tests。
- **Data flow:** Organisation + source location evidence → site identity → one or more typed location records → verification / protection gate → operationally usable location。
- **Pseudocode:** `create site under organisation; record each source point separately; assign location_type and verification_status; expose to routing only when status and precision satisfy operational policy`。
- **Edge cases:** 一個 site 多入口、public office不等於 receiving bay、地址變更、protected refuge location、suburb centroid、duplicate store source records、兩個 unresolved candidate locations。
- **Tests:** Organisation 1:N sites；site 1:N locations；unverified point不能被navigation query選出；protected exact point只向assigned actor揭露；location correction保留舊來源與有效期間。
- **Completion criteria:** Q7-A policy可被field contract表達；每種location type、precision、verification與visibility批准；61 store points、兩個KiwiHarvest branches和recipient approximations可被表示但不被誤標為active delivery point。

## Phase 3 — Users and organisation membership [blocked]

- **Phase goal:** 完成 `users` 和 `organisation_memberships`，把 driver視為 role / membership，並能追溯誰建立、批准或完成 operational action。
- **Affected components:** Planned specs for `users`、`organisation_memberships`；未來 auth boundary、match / delivery actor FKs。
- **Data flow:** Person/account → organisation membership → authorised role at event time → actor reference on donation / decision / delivery event。
- **Pseudocode:** `load active membership at action time; verify role permits action; write business record and actor membership reference in one transaction`。
- **Edge cases:** User離職後歷史仍可追溯、同一人多 role、recipient staff只可 accept自己的 site、driver尚未有 login、shared account不可提供可靠 audit。
- **Tests:** Membership validity period；inactive membership不能執行新 decision；history不因 user deactivation消失；同一 user可有多個 non-overlapping memberships。
- **Completion criteria:** Q2-A authority可被actor / assignee / approver / recipient responder分離表示；organisation / site scope和membership history contract批准；auth / login實作可以後置，不建立只有姓名的獨立`drivers` master table。

## Phase 4 — Source provenance and food identity [blocked]

- **Phase goal:** 完成`import_batches`、`source_records`和`food_products`，以structured form為MVP正式來源、barcode optional、CSV只作seed / test，並保留future StoreCentral adapter boundary。
- **Affected components:** Planned source / food specs；未來 import adapter、unique constraints、fixtures和 idempotency tests。
- **Data flow:** Structured form submission或test CSV → ingest batch / source record identity → validation → optional barcode product identity → immutable supply-item snapshot。
- **Pseudocode:** `upsert by source_system + source_record_id; retain observed_at and recorded_at; resolve optional barcode; preserve raw source reference; reject or review ambiguous mappings`。
- **Edge cases:** 無barcode、同barcode不同包裝、barcode存在但沒有expiry / quantity、manual submission重送、test CSV重跑、source修正先前資料、future StoreCentral與manual entry可能指向同一事件。
- **Tests:** Idempotent re-import；duplicate external key被阻擋；no-barcode food仍可建立 donation item；product rename不改寫historical item snapshot。
- **Completion criteria:** Q1-A落成exactinput / provenance contract；external identity、idempotency與raw reference ownership批准；future StoreCentral unknowns不阻擋MVP，barcode不是eligibility唯一來源。

## Phase 5 — Donation batch and food lines [blocked]

- **Phase goal:** 完成first-slice`donations`、`donation_items`、condition observation與成功路徑lifecycle contract；onward supply generalisation延後。
- **Affected components:** Planned supply、item、condition和status-event specs；未來SQLAlchemy models、one-table-per-migration files與database / state tests；本phase只寫design。
- **Data flow:** Verified donor site + actor/source record → structured supply batch → item snapshots → listing-time condition observation → deterministic safety result → listed / manual-review / hard-block event。
- **Pseudocode:** `validate source site and pickup window; create supply event; add item snapshots with quantity/unit/lot/storage/date facts; append condition observations; apply non-overridable recall/use-by rules; write initial status event atomically`。
- **Edge cases:** Empty donation、mixed temperature / lot、no barcode、opened or damaged packaging、unknown date-mark type、missing critical fact、recall、expired use-by、quantity correction、source site未verified、duplicate submission。
- **Tests:** Supply至少有一個valid item；quantity > 0；recall / expired use-by hard block；missing critical fact進manual review；batch 1:N items；condition observation有actor / time；product master更新不改歷史snapshot；create + initial events原子提交。
- **Completion criteria:** Gates B、C及P1-Q1 resolved；field dictionary、condition vocabulary、success-state ownership與event boundary批准；代表25 kg chilled案例可完整保存。Failure與onward fields不在本phase。

## Phase 6 — Recipient capability, need and availability [blocked]

- **Phase goal:** 完成三種 recipient state table，讓 matching可以分辨「通常能接收」、「目前需要」和「現在仍有 capacity」。
- **Affected components:** Planned specs for `recipient_capabilities`、`recipient_needs`、`recipient_availability_snapshots`；未來 eligibility queries和 stale-state tests。
- **Data flow:** Operator profile / current update → stable capability or time-bounded need / capacity snapshot → freshness check → matching eligibility input。
- **Pseudocode:** `load operator-confirmed site; write capability as versioned rule; append need/capacity snapshot with valid_until; at match time ignore stale snapshot and return unknown rather than zero`。
- **Edge cases:** Capacity unit不相容、capacity為0 vs unknown、snapshot過期、site可收category但今天不收、need大於physical capacity、冷藏與ambient capacity分開、operator correction。
- **Tests:** Capability和snapshot更新互不覆寫；stale snapshot不被當current；unit / storage class一致；protected site data不出現在public query。
- **Completion criteria:** Q3-A的food / storage lane、quantity / unit、receiving window、`valid_until`與updater contract獲批准；supported units、unknown / zero / stale和correction semantics確定；A只有15 kg current capacity可準確表示。

## Phase 7 — Matching decision and allocation [blocked]

- **Phase goal:** 完成deterministic feasibility、agent-ranked candidates、driver / coordinator decision、recipient response與single-recipient allocation，使「為什麼不是最近」和reservation責任可追溯。
- **Affected components:** Planned`match_runs`、`match_candidates`、`match_decisions`、`allocations`與allocation events；未來matching service transaction tests。
- **Data flow:** Supply item + current condition + fresh recipient state + verified locations → deterministic exclusion → agent priority over feasible candidates → driver confirmation / coordinator exception → recipient response → capacity recheck → reservation / allocation events。
- **Pseudocode:** `load versioned facts; persist every hard exclusion; rank only feasible candidates using approved policy; store reason components; request authorised human decision and recipient response; lock/recheck capacity; create one active recipient allocation per item; append events atomically`。
- **Edge cases:** No eligible candidate、nearest site infeasible、capacity在decision前改變、同一candidate重複確認、initial partial allocation被拒、concurrent allocation超賣、need或condition snapshot在planning前不再有效。Decline / timeout / release behavior延後。
- **Tests:** A因15 kg不足、B因無冷藏、C因dynamic ETA超deadline各有不同reason；D雖較遠仍因urgency / need / feasible ETA排序較高；agent不能直接建立allocation；同一item不能有兩個active recipient allocations；成功路徑的reservation / confirmation原子提交。
- **Completion criteria:** Gates A、C、D、E及P1-Q3–Q4 resolved；priority policy、single-recipient constraint、success-path reservation transaction和reason-code contract批准；A/B/C/D結果都有唯一、可查詢解釋。

## Phase 8 — Agent route planning and delivery execution [blocked]

- **Phase goal:** 完成route planning run、live input snapshot、agent proposal、human route decision與delivery execution；distance只作低優先效率因素，driver可取得已批准stops並回報actual result。
- **Affected components:** Planned`route_planning_runs`、route input snapshots / references、`route_proposals`、`route_decisions`、`deliveries`、`delivery_stops`、`delivery_allocations`與delivery events；未來driver API / UI和route tests。
- **Data flow:** Accepted / reserved allocations + current condition / capacity + verified locations + driver planning scope + planned departure → traffic / road / weather snapshot → deterministic route feasibility → agent priority / sequence proposal → driver confirmation或coordinator exception → committed delivery / ordered stops → actual events。
- **Pseudocode:** `require available live input snapshots; capture immutable route inputs; reject known closed roads and deadline/window failures; ask agent to rank feasible jobs and propose stop order under approved policy; persist reasons; require authorised decision; create versioned delivery; record successful actual stops without overwriting proposal`。
- **Edge cases:** Direct donor→recipient、approved cross-dock、multiple allocations、nearest route較慢、known full closure、lane delay、heavy-rain warning、recipient window更新、protected location。Provider outage、stale-data fallback、failed stop與replan延後。
- **Tests:** With required fixtures / normal provider responses，proposal input可重建provider / observed / valid times；known full closure與ETA deadline failure deterministic block；agent proposal不能直接commit；distance不是第一排序欄；navigation只回傳approved point；planned / proposed / approved / actual order與time分開。
- **Completion criteria:** Gates F、G及P1-Q2–Q3 resolved；planning horizon、allowed topology、priority order、normal route-input contract、route version與human decision批准；不需要vehicle GPS、provider-failure policy或full-fleet optimiser也能完成成功的multi-stop案例。

## Future extension — Custody, receipt and onward redistribution [deferred; not a first-slice gate]

- **Phase goal:** 在first slice完成後，再設計food handoff、receipt、quantity balance與community onward offer lineage，使原donation不被改寫，並可沿lot找到所有downstream recipients。
- **Affected components:** Planned custody handoff / receipt、condition observation、supply lineage / quantity movement與onward supply specs；未來recall、balance與redistribution tests。
- **Data flow:** Completed delivery stop + allocation → recipient receipt / current custodian + condition observation → used / disposed / remaining balance → new linked onward offer → new match / allocation / route cycle。
- **Pseudocode:** `record receipt and condition; calculate available balance from immutable quantity movements; if authorised organisation re-offers an allowed quantity, create child supply linked to parent receipt/lot; rerun safety, match, acceptance and route workflow; never update original recipient or receipt`。
- **Edge cases:** Partial remaining quantity、opened package、temperature excursion、date mark更近、label遺失、re-offer超過balance、multiple hops、recipient同時是donor、recall在onward delivery後發生、barter被誤當donation。
- **Tests:** 未來至少覆蓋20 kg received / 13 kg used只可re-offer最多7 kg；原20 kg → A receipt保持不變；每次handoff都有condition / actor / time；expired use-by / recall不可re-offer；parent lot可查出A與B。
- **Completion criteria:** 另開後續planning round再決定participant、transaction meaning、hop、quantity balance、custody與recall traversal；不屬first-slice completion criteria。

## Phase 9 — First-slice migration and verification [completed]

- **Phase goal:** 把已批准的first-slice table specs逐張轉為migration / model / tests，驗證正常donation-to-delivery relational contract。
- **Affected components:** [`alembic.ini`](../alembic.ini)、[`migrations/env.py`](../migrations/env.py)、[`migrations/versions/0cfadf2acb52_create_phase_1_8_schema.py`](../migrations/versions/0cfadf2acb52_create_phase_1_8_schema.py)、SQLAlchemy model package、`backend/tests`、quality script。
- **Data flow:** Empty PostgreSQL → ordered migrations → constrained schema → neutral fixtures → representative queries / transactions → clean rollback / rebuild驗證。
- **Pseudocode:** `for table in approved_dependency_order: add one migration; run upgrade; execute focused constraint tests; verify relationship query; only then start next table; after final table run end-to-end scenario and quality checks`。
- **Edge cases:** Migration中途失敗、dirty local database、downgrade破壞歷史、model與migration type不一致、test共用狀態、existing empty-table test失效。Operational failure behavior不在本phase。
- **Tests:** `backend/tests/test_migrations.py` 驗證 fresh temporary schema upgrade、FK / check / partial unique index、Alembic drift、downgrade / re-upgrade；既有 backend model tests 改在 Alembic-built schema 上執行；`ruff`、`mypy` 通過。
- **Completion criteria:** Alembic upgrade 建立目前 model registry；downgrade 清除 application tables；second upgrade 成功；`alembic check` 無 model drift；42 個 backend tests 通過；deferred extension 不需完成。

## Acceptance criteria for this plan

- 現況、提案和未確認事項有清楚證據標籤。
- 每張 proposed table都有單一責任、dependency和decision gate。
- 每個核心 relationship都有cardinality、FK / junction owner和設計理由。
- `food_product`與`donation_item`、capability / need / availability、match decision / allocation、delivery / route stop不再被混成同一概念。
- 一張 table只有在field dictionary、relationship contract、代表案例和test mapping完成後才可進migration。
- 所有material unresolved decisions都有明確blocked phase，不會變成任意nullable或JSONB欄位。
- Implementation維持一張migration一次；relationship在parent與child都存在後立即驗證。
- Plan只納入bounded route agent需要的input snapshot、proposal、reason與human decision；沒有把consumer voice、fleet telemetry、full-fleet optimisation或完整model trace塞進first slice。
- Failure / outage與onward redistribution標為deferred，不以speculative fields假裝已設計，也不阻擋成功路徑。

## Verification for the plan document

本文件交付時只做 documentation verification：

1. Markdown structure和local links可讀。
2. 所有phase都有 `Phase goal`、`Affected components`、`Data flow`、`Pseudocode`、`Edge cases`、`Tests`、`Completion criteria`。
3. 所有first-slice未確認table都能追溯到Gates A–G與P1-Q1–Q4；Gates H–I明確deferred。
4. Table order沒有先建立child再建立parent。
5. 本輪只修改 `database-design-research.md` 和本文件；沒有建立或修改 code、migration、seed、API、UI或其他 docs。

## Sources

- [Database design research and scope evidence](./database-design-research.md)
- [Auckland locations, recipient research and assumption alignment](./research.md)
- [Proposed MVP workflow and lifecycle](./foodflow-mvp-feature-spec.md)
- [Woolworths NZ Food Waste Diversion Scenario Brief](https://app.notion.com/p/Woolworths-NZ-Food-Waste-Diversion-Scenario-Brief-3b56c0b712f880c0b87cc01d2bec2d7f?source=copy_link)
- [Woolworths Food Waste Platform Features](https://app.notion.com/p/Woolworths-Food-Waste-Platform-Features-3b56c0b712f8804b9e66c873d60af1cb?source=copy_link)
- [Current empty platform foundation](../README.md)
- [Current PostgreSQL connection boundary](../backend/app/database.py)
- [Current empty-schema test](../backend/tests/test_database.py)

證據狀態：Repository現況為已確認；部分conceptual relationships已由三輪research驗證；Q1–Q8與「first slice只做成功路徑」為`human-aligned`；P1-Q1–Q4仍未回答。Table names、exact fields、constraints與phases仍為計畫中，不得描述為已實作或已驗證。
