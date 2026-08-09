# FoodFlow database design plan（XML-tagged）

> 這是一份新的 plan 文件，不取代 [`database-design-plan.md`](./database-design-plan.md)。XML block 是本文件的 machine-readable plan；Phase 1–8 schema 與 Phase 9 migration 已實作並通過本機 PostgreSQL 驗證，seed、API、service、AI 和 UI 仍未實作。

```xml
<?xml version="1.0" encoding="UTF-8"?>
<database_design_plan version="1.0" status="draft" language="zh-Hant">
  <metadata>
    <project>KiwiHarvest FoodFlow</project>
    <updated_at>2026-08-09</updated_at>
    <document_purpose>用逐張 table、逐段 relationship 的方式設計第一個可完成正常配送流程的 database slice。</document_purpose>
    <implementation_status>Phase 1–8 SQLAlchemy models 與 Phase 9 Alembic migration 已建立；未建立 seed data、API、service、AI 或 UI。</implementation_status>
    <primary_user>KiwiHarvest driver</primary_user>
    <human_control>Driver 確認一般 match 與 route；recipient 另行 accept；food-safety hard block 不可 override。</human_control>
    <evidence_status>Phase 1–8 schema 與 Phase 9 migration 已由 temporary PostgreSQL upgrade / downgrade / drift tests 驗證；future extensions 仍是 Planned 或 deferred。</evidence_status>
  </metadata>

  <goal>
    <statement>建立一個能把 verified donor site 的 food，經過 food facts、recipient feasibility、agent priority、human confirmation、reservation 和 route planning，送到 verified recipient site 的 relational design。</statement>
    <success_path>verified donor listing → food condition → feasible recipients → agent priority → driver confirmation → recipient acceptance → reservation → route proposal → collection → delivery completion</success_path>
    <not_the_goal>第一階段不處理 provider outage、degraded route、failed delivery、retry、manual rematch、full-fleet optimisation 或 community 收貨後的 onward redistribution implementation。</not_the_goal>
  </goal>

  <research_gate status="ready_for_first_slice_plan">
    <evidence_examined>
      <document>docs/database-design-research.md</document>
      <document>docs/research.md</document>
      <document>docs/foodflow-mvp-feature-spec.md</document>
      <document>docs/database-design-plan.md</document>
      <document>Woolworths Notion scenario brief and feature page</document>
      <repository>README.md、backend/app/main.py、backend/app/database.py、backend/tests/test_database.py</repository>
      <external_sources>MPI、FSANZ、NZ Food Network、KiwiHarvest、Google Routes / Route Optimization、NZTA、MetService、PostgreSQL documentation</external_sources>
    </evidence_examined>
    <confirmed_current_state>Repository 已有 Phase 1–8 business tables 的 SQLAlchemy models，以及 Phase 9 Alembic migration；沒有 seed data、runtime workflow service 或 live provider integration。</confirmed_current_state>
    <gaps>Food condition 的 controlled vocabulary、supported quantity units、正常 live-provider response contract，以及各 table 的 exact fields 還要在逐張 table design 時完成。</gaps>
    <weak_reasoning>「最近的 recipient 就是最佳 recipient」不成立；distance 不能取代 food safety、condition、capacity、need、receiving window、weather、road risk 和 traffic-aware ETA。</weak_reasoning>
    <unsupported_assumptions>
      <assumption status="rejected">所有 food 都有 barcode。</assumption>
      <assumption status="rejected">Barcode 本身就是一筆 donation event。</assumption>
      <assumption status="rejected">Public address 就是 driver 可用的 receiving point。</assumption>
      <assumption status="rejected">距離最近的 recipient 一定是最佳選擇。</assumption>
      <assumption status="deferred">Provider 失效時一定可以 fallback 到 static ETA 或 nearest route。</assumption>
    </unsupported_assumptions>
    <assumption_alignment>
      <decision id="Q1" answer="A" status="human-aligned">MVP 使用 platform structured form；barcode optional；CSV 只作 seed / test。</decision>
      <decision id="Q2" answer="A" status="human-aligned">Driver 確認一般 match / route；高風險或 exception 交 coordinator；recipient accept / decline。</decision>
      <decision id="Q3" answer="A" status="human-aligned">Recipient capacity 按 food / storage lane 保存 quantity、unit、receiving window 和 valid_until；food condition 另外保存。</decision>
      <decision id="Q4" answer="A" status="human-aligned">MVP initial donation item 不 split；一個 item 只對一個 recipient 做 active allocation。</decision>
      <decision id="Q5" status="human-aligned">Agent 依 priority 規劃 route，但只提出 proposal，不直接 commit。</decision>
      <decision id="Q6" status="deferred">Failure direction 已知道未來不自動 reroute，但第一階段不定義 failure behavior。</decision>
      <decision id="Q7" answer="A" status="human-aligned">FY25 / current 保留為 research candidates；只有 operator-confirmed point 可 routing；protected exact point 限 assigned actor。</decision>
      <decision id="Q8" answer="A" status="human-aligned">Recall / expired use-by hard block；missing 或 ambiguous critical facts 進 manual review。</decision>
      <decision id="P1-Q1" answer="A" status="human-aligned">Listing、pickup、delivery 都記錄 food condition；需要溫控時記 temperature。</decision>
      <decision id="P1-Q2" answer="A" status="human-aligned">一次替一位 driver 的一個 planning session 排序多筆 jobs，可包含多個 stops；不做全 fleet optimisation。</decision>
      <decision id="P1-Q3" answer="A" status="human-aligned">Hard feasibility → safe deadline / condition risk → recipient need / food fit → community impact → weather / road risk與traffic ETA → travel cost → distance tie-break。</decision>
      <decision id="P1-Q4" answer="A" status="human-aligned">Driver 確認 match 時建立 reservation；recipient accept 後變 confirmed；只有 confirmed allocation 進 route planning。</decision>
    </assumption_alignment>
    <missing_requirements>Exact field dictionary、condition values、quantity unit catalogue、normal provider response fields、table-level constraints 和 transaction boundary。</missing_requirements>
    <ambiguities>condition 的 controlled values、organisation membership fields、route input 的正規化程度，以及 status event 是否共用 table 尚未決定。</ambiguities>
    <contradictions_resolved>原 feature page 把 route optimisation 放在 future；最新 owner direction 將 bounded agent route priority 納入 first slice，但不納入 full-fleet optimisation 或 autonomous rerouting。</contradictions_resolved>
    <questions_that_require_human_answers>目前 first-slice 的四個 Grill Me decision 已回答；後續只剩逐張 table 的 field-level review。</questions_that_require_human_answers>
  </research_gate>

  <scope>
    <in_scope>
      <item>Woolworths、KiwiHarvest、community donor / recipient organisation、driver / staff、site / location 和 organisation roles。</item>
      <item>Structured donation listing、optional barcode、food identity、donation batch、donation items。</item>
      <item>Food condition observations：listing、pickup、delivery。</item>
      <item>Recipient capability、need、availability / capacity snapshot。</item>
      <item>Deterministic feasibility、match candidates、driver confirmation、recipient acceptance、single-recipient allocation。</item>
      <item>一位 driver planning session 的 bounded agent route priority、多站 route proposal 和 human confirmation。</item>
      <item>Traffic、road event、weather、ETA、provider 和 valid time 的正常 input snapshot。</item>
      <item>Collection、delivery completion、planned / approved / actual stop information。</item>
    </in_scope>
    <out_of_scope>
      <item>Consumer account、consumer voice request、audio / transcript。</item>
      <item>Vehicle GPS、fleet telemetry、formal shift optimiser 和 multi-driver global optimisation。</item>
      <item>Provider outage、stale-data fallback、degraded route、active-route refresh、retry 和 replan policy。</item>
      <item>Failed pickup / delivery、reservation release、manual rematch 和 failure-specific transitions / fields。</item>
      <item>Community 收貨後 onward offer 的 exact tables、barter / donation semantics、hop limit、quantity lineage 和 recall implementation。</item>
      <item>完整 prompt、embedding、chain-of-thought 或 model-training dataset。</item>
      <item>本文件階段不建立 database tables。</item>
    </out_of_scope>
  </scope>

  <design_principles>
    <principle id="identity">Organisation、site、typed location 和 external identity 分開；名稱、地址或 barcode 不作 internal primary key。</principle>
    <principle id="source_roles">同一 organisation 可以有 donor、recipient、hub 等不同 role；Woolworths 不是唯一 source。</principle>
    <principle id="food_snapshot">Food product identity 與 donation item snapshot 分開；barcode optional；lot、date、temperature、condition 和 quantity 是當次 operational facts。</principle>
    <principle id="recipient_state">Capability、need、availability snapshot 和 allocation / reservation 分開。</principle>
    <principle id="feasibility_before_priority">先用 deterministic rules 排除不可行候選，再讓 agent 對可行集合排序。</principle>
    <principle id="distance_is_not_primary">Distance 只作低優先 efficiency factor 或 stable tie-breaker。</principle>
    <principle id="proposal_before_commit">Agent 只產生 route / priority proposal；driver 或 coordinator 才能確認。</principle>
    <principle id="time_semantics">所有會影響 match / route 的資料保存 source、observed_at、recorded_at、valid_from / valid_until 和 calculation time。</principle>
    <principle id="history_boundary">第一階段保留 success status-event 的 actor、time 和 aggregate reference；failure-specific events 之後再加，不先猜欄位。</principle>
    <principle id="future_lineage_boundary">Community onward redistribution 保留為 future extension boundary；不能改寫原始 recipient、receipt 或 donation history。</principle>
  </design_principles>

  <route_policy>
    <hard_feasibility>
      <rule>Food safety hard block。</rule>
      <rule>Food condition、storage requirement、recipient capability 和 current capacity 相容。</rule>
      <rule>Recipient acceptance、receiving window、safe deadline 和 verified operational location 可滿足。</rule>
      <rule>Pickup-before-delivery precedence 和 known road passability 可滿足。</rule>
      <rule>Traffic-aware ETA 加 service time 不得超過 safe deadline 或 receiving window。</rule>
    </hard_feasibility>
    <priority_order>
      <step order="1">Safe feasibility and hard blocks</step>
      <step order="2">Earliest safe deadline and food condition / perishability risk</step>
      <step order="3">Confirmed recipient need and food fit</step>
      <step order="4">Community impact</step>
      <step order="5">Weather / road risk and traffic-aware ETA</step>
      <step order="6">Travel time and route cost</step>
      <step order="7">Distance as tie-breaker only</step>
    </priority_order>
    <input_snapshot>
      <field>approved allocations and food facts</field>
      <field>recipient capability, need and availability snapshot</field>
      <field>verified pickup / receiving locations</field>
      <field>planned departure time</field>
      <field>traffic-aware ETA and static ETA</field>
      <field>road events / closures and weather observations / warnings</field>
      <field>provider、source dataset、observed_at、recorded_at、valid_from、valid_until</field>
      <field>policy version、model identifier、input version</field>
    </input_snapshot>
    <first_slice_precondition>Required traffic、road 和 weather input 已由正常 provider response 或 test fixture 提供。Provider outage 和 degraded fallback 不在本階段定義。</first_slice_precondition>
  </route_policy>

  <reservation_policy>
    <step order="1">Driver 確認一般 match。</step>
    <step order="2">建立 allocation reservation。</step>
    <step order="3">Recipient accept 後，reservation 變成 confirmed allocation。</step>
    <step order="4">只有 confirmed allocation 可以進入 route planning。</step>
    <deferred>Timeout、decline、release、failed delivery 和 rematch 的行為不在 first slice。</deferred>
  </reservation_policy>

  <table_design_contract>
    <field name="table_purpose">一張 table 只負責一個主要 business responsibility。</field>
    <field name="field_name">保存 exact PostgreSQL / SQLAlchemy identifier。</field>
    <field name="business_meaning">說明 field 在 KiwiHarvest workflow 代表的事實。</field>
    <field name="data_type">說明 PostgreSQL type、precision、timezone、enum 或 lookup strategy。</field>
    <field name="null_semantics">區分 unknown、not applicable、not received 和 zero。</field>
    <field name="identity">區分 internal id、external id 和 human-readable name。</field>
    <field name="relationship">說明 FK、cardinality、optional / required 和 FK owner。</field>
    <field name="integrity">說明 NOT NULL、UNIQUE、CHECK、FK 和 transaction-level invariant。</field>
    <field name="update_ownership">說明哪個 actor 或 source 可以建立、修正或 supersede。</field>
    <field name="time_semantics">說明 observed、recorded、valid 和 event time。</field>
    <field name="history_behavior">區分 update、snapshot、append-only event 和 deactivate。</field>
    <field name="delete_behavior">預設不 cascade operational history；說明 RESTRICT 或受控 archive。</field>
    <field name="sensitivity">標記 public、operational-only、personal 或 protected。</field>
    <field name="example">提供 neutral valid row 和 boundary case，不冒充 real operator data。</field>
    <field name="evidence_status">標記 Confirmed、Human-aligned、Planned 或 Unknown。</field>
    <definition_of_done>
      <criterion>每個 field 都完成 data dictionary。</criterion>
      <criterion>每個 FK 都說明 parent、child、cardinality 和 delete behavior。</criterion>
      <criterion>至少有 valid row、boundary row 和 relationship case。</criterion>
      <criterion>同一 source record 重送不產生 duplicate。</criterion>
      <criterion>Correction 的 update / snapshot / event behavior 已定義。</criterion>
      <criterion>每個 unresolved field 都對應到一個 decision gate。</criterion>
      <criterion>每個 constraint 都有對應 test。</criterion>
    </definition_of_done>
  </table_design_contract>

  <first_slice_table_order>
    <table order="1" name="organisations" depends_on="none" gate="A,I-deferred">Woolworths、KiwiHarvest 和 community organisation 的 stable identity。</table>
    <table order="2" name="organisation_roles" depends_on="organisations" gate="A">Donor、recipient、hub 和 food-rescue operator roles。</table>
    <table order="3" name="sites" depends_on="organisations" gate="F">Store、branch、warehouse、service site identity。</table>
    <table order="4" name="site_locations" depends_on="sites" gate="F">Public address、map point、pickup / receiving point、precision、verification、visibility。</table>
    <table order="5" name="partner_relationships" depends_on="organisations,sites" gate="A,F">KiwiHarvest 與 donor / recipient / hub 的 operational relationship。</table>
    <table order="6" name="users" depends_on="none" gate="A">Driver、coordinator、recipient staff 等 actor identity；auth implementation 可後置。</table>
    <table order="7" name="organisation_memberships" depends_on="users,organisations" gate="A">User 的 organisation / site role 和有效期間。</table>
    <table order="8" name="import_batches" depends_on="none" gate="B">Structured form、CSV test / seed 和 future integration 的 ingest boundary。</table>
    <table order="9" name="source_records" depends_on="import_batches" gate="B">External identity、source time、raw provenance 和 ingest result。</table>
    <table order="10" name="food_products" depends_on="source_records-optional" gate="B">Optional barcode / GTIN product identity；不作 donation primary key。</table>
    <table order="11" name="donations" depends_on="sites,users,source_records-optional" gate="B,C">一次 Woolworths 或 community donor supply event。</table>
    <table order="12" name="donation_items" depends_on="donations,food_products-optional" gate="C">Food identity snapshot、barcode optional、lot、quantity、unit、storage、date facts。</table>
    <table order="13" name="food_condition_observations" depends_on="donation_items,users" gate="C,P1-Q1">Listing、pickup、delivery 的 condition 和 temperature observations。</table>
    <table order="14" name="donation_status_events" depends_on="donations,users" gate="C">First-slice success events；failure-specific event types deferred。</table>
    <table order="15" name="recipient_capabilities" depends_on="sites" gate="D">Stable food、storage、handling capability。</table>
    <table order="16" name="recipient_needs" depends_on="sites" gate="D,P1-Q3">Time-bounded food need、quantity 和 priority input。</table>
    <table order="17" name="recipient_availability_snapshots" depends_on="sites" gate="D">Food / storage lane 的 quantity、unit、receiving window、valid_until。</table>
    <table order="18" name="match_runs" depends_on="donations,donation_items,recipient-state" gate="C,D">一次 deterministic matching execution 的 input / policy version 和 time。</table>
    <table order="19" name="match_candidates" depends_on="match_runs,sites" gate="G,P1-Q3">Feasibility、排除 reason、agent rank 和 priority reasons。</table>
    <table order="20" name="match_decisions" depends_on="match_candidates,users" gate="A">Driver confirmation、coordinator exception 和 recipient acceptance 的 separate facts。</table>
    <table order="21" name="allocations" depends_on="donation_items,sites,match_decisions" gate="E,P1-Q4">Single-recipient reservation / confirmed allocation / fulfilment。</table>
    <table order="22" name="allocation_status_events" depends_on="allocations,users" gate="E">First-slice reserved、confirmed、fulfilled history；release / failure deferred。</table>
    <table order="23" name="route_planning_runs" depends_on="allocations,users" gate="G,P1-Q2">一位 driver planning session 的 bounded agent planning run。</table>
    <table order="24" name="route_input_snapshots" depends_on="route_planning_runs,recipient-state,site_locations" gate="G">當次 traffic、weather、road、ETA、condition、capacity 和 policy inputs。</table>
    <table order="25" name="route_proposals" depends_on="route_planning_runs,route_input_snapshots" gate="G,P1-Q3">Agent ordered stops、priority reasons、cost components 和 version。</table>
    <table order="26" name="route_decisions" depends_on="route_proposals,users" gate="A,G">Driver confirmation 或 coordinator exception decision。</table>
    <table order="27" name="deliveries" depends_on="route_decisions,users" gate="G">Human-approved driver delivery job 和 committed route version。</table>
    <table order="28" name="delivery_stops" depends_on="deliveries,site_locations" gate="F,G">Approved stop order、planned / actual timestamps、successful stop result。</table>
    <table order="29" name="delivery_allocations" depends_on="deliveries,allocations" gate="E,G">一趟 delivery 與多筆 allocations 的 junction。</table>
    <table order="30" name="delivery_status_events" depends_on="deliveries,users" gate="G">First-slice assigned、started、arrived、collected、delivered history。</table>
  </first_slice_table_order>

  <relationship_baseline>
    <relationship parent="organisations" child="sites" cardinality="1:N" fk_owner="sites.organisation_id">一個 organisation 可有多個 operational sites。</relationship>
    <relationship parent="sites" child="site_locations" cardinality="1:N" fk_owner="site_locations.site_id">Public、operational 和 protected locations 分開。</relationship>
    <relationship parent="users" child="organisations" cardinality="M:N" fk_owner="organisation_memberships">User role 隨 organisation / site scope 和 validity 改變。</relationship>
    <relationship parent="donations" child="donation_items" cardinality="1:N" fk_owner="donation_items.donation_id">一批 donation 可有不同 lot、category、unit 或 temperature lines。</relationship>
    <relationship parent="donation_items" child="food_condition_observations" cardinality="1:N" fk_owner="observation.donation_item_id">Condition 是 time-bounded observations，不是單一永遠正確的欄位。</relationship>
    <relationship parent="sites" child="recipient_state" cardinality="1:N per state type" fk_owner="state.site_id">Capability、need、availability 分開保存。</relationship>
    <relationship parent="match_runs" child="match_candidates" cardinality="1:N" fk_owner="match_candidates.match_run_id">每個 candidate 和排除 reason 都保留。</relationship>
    <relationship parent="match_candidates" child="match_decisions" cardinality="1:0..1" fk_owner="match_decisions.match_candidate_id">Agent recommendation 與 human decision 不互相覆寫。</relationship>
    <relationship parent="donation_items" child="allocations" cardinality="1:N history,1 active recipient" fk_owner="allocations.donation_item_id">Initial item 不 split；reservation / confirmation 的成功路徑由 P1-Q4 定義。</relationship>
    <relationship parent="allocations" child="deliveries" cardinality="M:N" fk_owner="delivery_allocations">一趟 route 可帶多筆已 confirmed allocations。</relationship>
    <relationship parent="route_planning_runs" child="route_proposals" cardinality="1:N" fk_owner="route_proposals.route_planning_run_id">同一 planning run 可留下 proposal version。</relationship>
    <relationship parent="route_proposals" child="route_decisions" cardinality="1:N" fk_owner="route_decisions.route_proposal_id">Agent proposal 不等於 committed route。</relationship>
    <relationship parent="deliveries" child="delivery_stops" cardinality="1:N" fk_owner="delivery_stops.delivery_id">Stop order、planned time 和 actual result 屬於一次 delivery。</relationship>
    <future_relationship parent="recipient_receipt" child="onward_supply_lineage" status="deferred">Community onward redistribution 未來要保留 lot、quantity、custody 和 downstream traceability，不改寫原 donation。</future_relationship>
  </relationship_baseline>

  <representative_case status="planned_example">
    <input>一個 verified Woolworths 或 community donor site 以 structured form 建立 25 kg chilled dairy；pickup window 14:00–16:00，safe deadline 18:00。A 最近但只有 15 kg capacity；B 沒有 chilled storage；C 會因 traffic-aware ETA 超過 deadline；D 較遠但有完整 capacity、urgent need 且能準時抵達。</input>
    <processing>Deterministic rules 排除 A、B、C；agent 依 approved priority policy 排序可行候選；driver 確認 D；recipient D accept；建立 confirmed allocation；route proposal 保存當次 traffic、weather、road 和 ETA inputs。</processing>
    <output>Driver 完成 collection 與 delivery；system 保存 D 的 match decision、reservation、route proposal、ordered stops、condition observations 和 success events。</output>
    <boundary>Distance 沒有直接決定 D；provider outage、failed delivery 和 D 收貨後的 onward re-offer 留在 future extension。</boundary>
  </representative_case>

  <phases>
    <phase id="0" status="completed_for_planning" name="First-slice conventions and decision gates">
      <phase_goal>把已回答的 decisions、deferred boundaries、naming / type conventions 和 table entry gates 固定下來。</phase_goal>
      <affected_components>本文件、database-design-research.md、database-design-plan.md；不修改 code。</affected_components>
      <data_flow>Evidence + owner decisions → evidence status → approved first-slice boundary → table-by-table design gates。</data_flow>
      <pseudocode>for each first-slice decision: record answer; map it to tables and relationships; mark deferred failure / onward behavior as non-blocking; do not freeze unknown exact fields。</pseudocode>
      <edge_cases>Unknown 不等於 zero；future behavior 不等於 current schema；protected location 不進 public seed。</edge_cases>
      <tests>檢查 decisions、gates、table order、deferred list 和 representative case 一致。</tests>
      <completion_criteria>P1-Q1–Q4 已納入；Gates A–G 支援成功路徑；H–I 明確 deferred；不開始 migration。</completion_criteria>
    </phase>

    <phase id="1" status="planned" name="Organisation identity">
      <phase_goal>完成 organisations 與 roles，使 Woolworths、KiwiHarvest 和 community organisation 可用同一 identity model 表示。</phase_goal>
      <affected_components>organisations、organisation_roles、partner_relationships 的 field specifications。</affected_components>
      <data_flow>Source identity → deduplication / review → canonical organisation → valid role assignment。</data_flow>
      <pseudocode>resolve external identity; reuse canonical organisation; attach donor / recipient / hub role with validity; never duplicate identity because display name changed。</pseudocode>
      <edge_cases>同名不同 organisation、rename、同一 organisation 同時 donor / recipient、closed organisation 仍被歷史 record 引用。</edge_cases>
      <tests>External identity uniqueness、multi-role relationship、historical reference 不被 hard delete。</tests>
      <completion_criteria>每個 field 的 source、null、update、history、delete 和 sensitivity semantics 完成。</completion_criteria>
    </phase>

    <phase id="2" status="planned" name="Site and operational location">
      <phase_goal>把 public address、research candidate 和 operator-confirmed pickup / receiving point 分開。</phase_goal>
      <affected_components>sites、site_locations、partner_relationships 的 field specifications。</affected_components>
      <data_flow>Organisation + source location → site identity → typed location → verification / visibility → routing-eligible point。</data_flow>
      <pseudocode>create site; preserve every source point; assign type, precision and verification; expose only approved operational point to routing。</pseudocode>
      <edge_cases>多入口、public office 不等於 receiving bay、approximate point、protected destination、地址更正。</edge_cases>
      <tests>1:N organisation-to-site、1:N site-to-location、unverified point 不可進 navigation query、protected exact point 只對 assigned actor 可見。</tests>
      <completion_criteria>FY25 / current candidates 可以保留，但只有 operator-confirmed point 進 first-slice routing。</completion_criteria>
    </phase>

    <phase id="3" status="planned" name="Actors and memberships">
      <phase_goal>保存 driver、coordinator、recipient responder 和 agent proposal 的責任分離。</phase_goal>
      <affected_components>users、organisation_memberships、actor references in decisions and events。</affected_components>
      <data_flow>Person / system actor → membership / scope → authorised action → actor reference in record。</data_flow>
      <pseudocode>resolve actor category and scope; write actor / assignee / approver separately; keep auth provider details deferred。</pseudocode>
      <edge_cases>同一 user 多 role、driver 尚未有 login、recipient staff 只能回覆自己的 site、歷史 actor 被 deactivated。</edge_cases>
      <tests>Membership validity、actor references、history remains queryable after deactivation。</tests>
      <completion_criteria>不建立只有姓名的 drivers table；auth / login implementation 可後置，但 business authority contract 已保留。</completion_criteria>
    </phase>

    <phase id="4" status="planned" name="Structured source and food identity">
      <phase_goal>讓 structured form 建立 donation，barcode optional，輸入重送不產生 duplicate。</phase_goal>
      <affected_components>import_batches、source_records、food_products、donation item snapshot specifications。</affected_components>
      <data_flow>Form / test CSV → source identity → optional barcode mapping → immutable donation item snapshot。</data_flow>
      <pseudocode>ingest source record; preserve source and recorded times; accept no-barcode item; resolve optional product identity; keep raw provenance。</pseudocode>
      <edge_cases>無 barcode、同 barcode 不同 lot / package、barcode 沒有 quantity 或 date、duplicate submission。</edge_cases>
      <tests>Idempotent source record、no-barcode donation、product master update 不改歷史 item snapshot。</tests>
      <completion_criteria>Structured-form source contract、external identity、raw provenance 和 barcode optional rule 完成。</completion_criteria>
    </phase>

    <phase id="5" status="planned" name="Donation items and condition">
      <phase_goal>保存 donation batch、item facts 和 listing / pickup / delivery condition observations。</phase_goal>
      <affected_components>donations、donation_items、food_condition_observations、donation_status_events。</affected_components>
      <data_flow>Verified donor site → donation batch → item snapshot → condition observations → success status events。</data_flow>
      <pseudocode>validate required food facts; create donation and item; record condition at each selected checkpoint; apply recall / expired use-by hard block; append success event。</pseudocode>
      <edge_cases>Mixed lot、mixed temperature、no barcode、missing critical fact、opened packaging、recall、expired use-by。</edge_cases>
      <tests>quantity &gt; 0、batch 1:N items、condition actor / time、hard block、manual review、atomic listing creation。</tests>
      <completion_criteria>P1-Q1 的 condition checkpoint、controlled values、mandatory fields 和 success-state ownership 完成。</completion_criteria>
    </phase>

    <phase id="6" status="planned" name="Recipient capability, need and availability">
      <phase_goal>區分 recipient 能不能收、現在需要什麼、現在還能收多少。</phase_goal>
      <affected_components>recipient_capabilities、recipient_needs、recipient_availability_snapshots。</affected_components>
      <data_flow>Operator input → capability / need / availability snapshot → freshness and unit check → matching input。</data_flow>
      <pseudocode>load operator-confirmed site; write stable capability; append need and lane-specific capacity snapshot; expose current facts to feasibility evaluation。</pseudocode>
      <edge_cases>Capacity zero vs unknown、chilled / frozen / ambient lanes、unit mismatch、receiving window、snapshot valid_until。</edge_cases>
      <tests>Capability 不被 snapshot update 覆寫；unit / storage lane一致；current capacity 可查詢；protected site 不出現在 public query。</tests>
      <completion_criteria>Q3-A 的 quantity、unit、food / storage lane、receiving window 和 valid_until contract 完成。</completion_criteria>
    </phase>

    <phase id="7" status="planned" name="Matching and confirmed allocation">
      <phase_goal>先排除不可行 recipient，再按 P1-Q3 排序，讓 driver confirmation、recipient acceptance 和 reservation 成功路徑可追蹤。</phase_goal>
      <affected_components>match_runs、match_candidates、match_decisions、allocations、allocation_status_events。</affected_components>
      <data_flow>Donation item + condition + recipient state + verified locations → deterministic feasibility → agent ranking → driver confirmation → reservation → recipient acceptance → confirmed allocation。</data_flow>
      <pseudocode>persist every hard exclusion; rank feasible candidates; store reason components; driver confirms; create reservation; recipient accepts; mark confirmed; allow only confirmed allocation into route planning。</pseudocode>
      <edge_cases>Nearest candidate infeasible、capacity changed before confirmation、candidate repeated、no feasible candidate、same item assigned to two active recipients。</edge_cases>
      <tests>A capacity insufficient、B storage incompatible、C ETA over deadline、D farther but feasible and urgent；agent cannot create allocation directly；single active allocation constraint；reservation and confirmation atomicity。</tests>
      <completion_criteria>P1-Q3 and P1-Q4 完成；每個候選都有可解釋 reason；confirmed allocation 可提供給 route planning。</completion_criteria>
    </phase>

    <phase id="8" status="planned" name="Agent route planning and successful delivery">
      <phase_goal>為一位 driver 的 planning session 產生可審核、多站 route proposal，確認後完成 collection 和 delivery。</phase_goal>
      <affected_components>route_planning_runs、route_input_snapshots、route_proposals、route_decisions、deliveries、delivery_stops、delivery_allocations、delivery_status_events。</affected_components>
      <data_flow>Confirmed allocations + normal live inputs + verified locations → route snapshot → hard route feasibility → agent proposal → driver confirmation → delivery stops → success events。</data_flow>
      <pseudocode>capture route inputs; reject known closure / deadline failure; rank jobs under P1-Q3; save reasons and version; require driver confirmation; create delivery; record planned and actual stop times。</pseudocode>
      <edge_cases>多筆 jobs、direct donor-to-recipient、approved cross-dock、nearest route slower、known closure、traffic delay、weather risk、protected location。</edge_cases>
      <tests>Snapshot contains provider and valid time；known closure / ETA failure deterministic；distance is not first priority；agent proposal cannot commit；planned / approved / actual stop order differs correctly；success events complete。</tests>
      <completion_criteria>P1-Q2 and P1-Q3 完成；一位 driver 的 multi-stop success path 可被完整重建；provider outage 和 failed delivery 不在此 phase。</completion_criteria>
    </phase>

    <phase id="9" status="completed" name="First-slice migration and verification">
      <phase_goal>把已批准的 first-slice table specifications 依 dependency order 轉成 migrations / models / tests。</phase_goal>
      <affected_components>Future migration framework、PostgreSQL、models、database tests、normal success-path fixtures。</affected_components>
      <data_flow>Approved table specs → ordered migrations → constrained schema → neutral fixture → representative success-path queries / transactions → verification。</data_flow>
      <pseudocode>for each approved table: write one migration; migrate fresh database; test constraints and relationship; only then add dependent table; finish with full first-slice scenario。</pseudocode>
      <edge_cases>Migration dependency、duplicate source、concurrent allocation、protected location visibility、dirty test state。Failure behavior remains deferred。</edge_cases>
      <tests>Fresh database upgrade、PK / FK / unique / check、idempotent input、single-recipient allocation、route visibility、success-path integration test。</tests>
      <completion_criteria>Phases 0–8 approved；fresh database建立成功；first-slice relationships、constraints、normal route and successful delivery all pass；deferred extensions不阻擋。</completion_criteria>
    </phase>
  </phases>

  <deferred_extensions>
    <extension id="failure_behavior" status="deferred">Provider outage、stale data、degraded route、failed delivery、release、retry、manual rematch 和 failure-specific fields / events。</extension>
    <extension id="onward_redistribution" status="deferred">Custody receipt、quantity movement、child supply / onward offer、community participant policy、barter / donation semantics、hop limit、recall traversal。</extension>
    <extension id="full_fleet" status="deferred">Vehicle、GPS、driver shift、multi-driver assignment、full Auckland optimisation。</extension>
    <extension id="agent_trace" status="deferred">完整 prompt、embedding、chain-of-thought 和 training dataset；first slice 只保存 input version、model identifier、reason 和 human decision。</extension>
  </deferred_extensions>

  <acceptance_criteria>
    <criterion>First slice 使用 donor / organisation / site model，不把 source 限定成 Woolworths store。</criterion>
    <criterion>Barcode optional；no-barcode food 可以建立 donation item。</criterion>
    <criterion>Food condition 在 P1-Q1 選定的 checkpoints 有 actor、time 和 observation。</criterion>
    <criterion>Capability、need、availability 和 allocation 不混在同一 entity。</criterion>
    <criterion>Initial donation item 不會同時有兩個 active recipient allocations。</criterion>
    <criterion>Deterministic feasibility 在 agent ranking 之前；nearest distance 不能單獨決定 recipient 或 route。</criterion>
    <criterion>Route proposal 使用 provider、traffic、weather、road、ETA 和 valid time snapshot。</criterion>
    <criterion>Agent proposal 不會直接變成 committed route；driver / coordinator decision 可追蹤。</criterion>
    <criterion>Reservation 只有在 driver confirmation 後建立，只有 recipient acceptance 後變 confirmed，confirmed allocation 才進 route planning。</criterion>
    <criterion>一位 driver 的 multi-stop success path 可從 listing 追蹤到 delivery completion。</criterion>
    <criterion>Failure / outage / onward redistribution 不會被 speculative fields 假裝成已完成設計。</criterion>
  </acceptance_criteria>

  <verification>
    <documentation_checks>
      <check>XML block 必須保持 well-formed，所有 tags 正確閉合。</check>
      <check>所有 phase 都有 phase_goal、affected_components、data_flow、pseudocode、edge_cases、tests、completion_criteria。</check>
      <check>Table order 由 parent 到 child；所有 deferred extension 不進 first-slice migration order。</check>
      <check>Local links 指向目前 repository 的 files。</check>
    </documentation_checks>
    <implementation_checks status="completed">Alembic upgrade / downgrade / re-upgrade、database constraints、model drift、route visibility、success-path integration tests、ruff 和 mypy 已在本機完成；live provider integration 尚未開始。</implementation_checks>
    <evidence_boundary>目前已驗證 Phase 1–8 schema 與 Phase 9 migration；尚未建立 seed data、runtime workflow、AI behavior 或 live provider integration。</evidence_boundary>
  </verification>

  <sources>
    <local>docs/database-design-research.md</local>
    <local>docs/database-design-plan.md</local>
    <local>docs/research.md</local>
    <local>docs/foodflow-mvp-feature-spec.md</local>
    <notion>Woolworths NZ Food Waste Diversion Scenario Brief</notion>
    <notion>Woolworths Food Waste Platform Features</notion>
    <external>MPI food donation and food recall guidance</external>
    <external>NZ Food Network Food Hubs and redistribution information</external>
    <external>Google Routes / Route Optimization documentation</external>
    <external>NZTA traffic and road event information</external>
    <external>MetService weather data and warning information</external>
    <database>PostgreSQL constraints、transactions、JSONB、date/time and import documentation</database>
  </sources>
</database_design_plan>
```

證據狀態：除特別標註外，本文件的 repository current state 來自已讀取的文件、程式碼與 tests；第一階段 decisions 是 `human-aligned`；schema implementation、live provider integration 和 deferred extensions 尚未完成。
