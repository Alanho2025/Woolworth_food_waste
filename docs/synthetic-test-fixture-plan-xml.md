# Synthetic test fixture plan（XML-tagged）

> 這份 plan 以目前 PostgreSQL schema、Alembic test harness 和既有 model tests 為基礎。Phase 10A–10D 的 current-schema fixture 與 tests 已完成；本文件不把尚未存在的 service rule 寫成已完成。

```xml
<?xml version="1.0" encoding="UTF-8"?>
<synthetic_test_fixture_plan version="1.0" status="completed_current_schema_phases" language="zh-Hant">
  <metadata>
    <project>KiwiHarvest FoodFlow</project>
    <updated_at>2026-08-10</updated_at>
    <purpose>建立可重複、可分階段驗證的 PostgreSQL synthetic food-diversion scenario，並測試 database constraints、query semantics、state transitions 和 concurrency。</purpose>
    <test_boundary>只使用 PostgreSQL、Alembic temporary schema 和固定 synthetic payload；不呼叫 live provider，不寫入 production 或 shared development data。</test_boundary>
  </metadata>

  <research_findings status="ready_for_plan">
    <evidence_examined>
      <local>backend/app/models/*.py、backend/tests/conftest.py、backend/tests/test_phase5_to_phase8_models.py、docs/database-design-plan-xml.md。</local>
      <external>GS1 check-digit guidance；New Zealand MPI food transport guidance。</external>
    </evidence_examined>
    <confirmed_current_state>Phase 1–8 SQLAlchemy models 和 Phase 9 Alembic migration 已支持 organisation、site/location、user/membership、source/product、donation/item/condition、recipient state、matching、allocation、route proposal/decision、delivery/stops/events 的基本 persistence graph。</confirmed_current_state>
    <gaps>
      <gap>DonationItem 沒有 canonical food_category，但 recipient state 依 food_category matching。</gap>
      <gap>RoutePlanningRun 沒有 KiwiHarvest origin_site_id / origin_location_id FK。</gap>
      <gap>RouteInputSnapshot 的 immutable 語意目前沒有 database write-once enforcement。</gap>
      <gap>Quantity、decision gate、actor membership、stop semantics、snapshot freshness 等跨表 business rules 尚未由 database enforcement。</gap>
      <gap>一筆 donation 含兩個 items，但目前 allocation 是 item-level；partial completion 沒有明確 donation lifecycle。</gap>
    </gaps>
    <weak_reasoning>只驗證 commit 成功、只用 barcode length、把 unknown 當 zero、直接建立 completed state、或用 live traffic/weather 都不能證明 workflow 正確。</weak_reasoning>
    <unsupported_assumptions>真實 Woolworths product barcode、真實 recipient capacity、真實 KiwiHarvest vehicle position、真實 provider response schema 和真實 operational address 不進 fixture。</unsupported_assumptions>
    <assumption_alignment>
      <assumption status="evidence-validated">Synthetic GTIN-14 00012345600012 具有效 check digit，但不代表真實商品。</assumption>
      <assumption status="evidence-validated">Chilled listing observation 使用 4.00°C；這是 synthetic fact，不是目前 DB policy。</assumption>
      <assumption status="human-aligned">Recipient A 使用 known capacity；Recipient B 使用 unknown capacity。</assumption>
      <assumption status="bounded">Primary success route 只配送 barcode chilled item；no-barcode item 保留為未 allocation edge case。</assumption>
      <assumption status="bounded">KiwiHarvest origin 暫時 freeze 在 route snapshot / proposal payload，first-class origin FK 留待 schema decision。</assumption>
    </assumption_alignment>
    <missing_requirements>固定 scenario clock、item allocation scope、actor identity、snapshot validity window、event order 和 partial donation assertion。</missing_requirements>
    <ambiguities>一個 condition observation 是 base fixture 的 listing observation；成功配送 extension 另外加入 pickup / delivery observations。成功 donation 和成功 selected allocation 分開定義。</ambiguities>
    <contradictions>Allocation 在 route planning 前必須是 confirmed，但成功配送後必須是 fulfilled；兩者以 staged checkpoint 表示。</contradictions>
    <questions_requiring_human_answers>沒有阻擋 test-only fixture 的問題。正式 service 前仍需決定 food_category ownership、partial donation lifecycle 和 route origin FK。</questions_requiring_human_answers>
  </research_findings>

  <scope>
    <in_scope>
      <item>一個 synthetic Woolworths donor organisation 和 store。</item>
      <item>一個 synthetic KiwiHarvest site / route origin。</item>
      <item>兩個 recipient organisations 和 receiving locations。</item>
      <item>一個 driver、一個 recipient responder 和必要 memberships。</item>
      <item>一筆 donation，含一個有效 barcode item 和一個 no-barcode item。</item>
      <item>Recipient capability、need、known / unknown availability。</item>
      <item>Match candidates、human decisions、allocation、route snapshots、proposal、approval、delivery、stops 和 success events。</item>
      <item>Current-schema constraint、query、graph reconstruction 和 allocation race tests。</item>
    </in_scope>
    <out_of_scope>
      <item>Real provider calls、live weather / traffic、real addresses 和 production seed command。</item>
      <item>Matching algorithm、route optimisation service、AI agent runtime 和 API。</item>
      <item>Failure、cancel、release、rematch、onward redistribution 和 vehicle tracking。</item>
      <item>未經 owner decision 的 schema contract redesign。</item>
    </out_of_scope>
  </scope>

  <fixed_scenario>
    <clock utc="2026-08-10T00:00:00Z" timezone="Pacific/Auckland" />
    <identifiers>使用固定 UUID constants；每個 test 仍使用獨立 Alembic schema。</identifiers>
    <synthetic_data_policy>所有名稱、地址、座標、email 和 provider payload 都明確標記 synthetic；email 使用 example.invalid；不保存 password 或 OAuth secret。</synthetic_data_policy>
    <gtin value="00012345600012" type="synthetic_gtin14" />
    <locations>
      <location name="KiwiHarvest synthetic hub" latitude="-36.940000" longitude="174.860000" type="pickup_point" />
      <location name="Woolworths synthetic store" latitude="-36.900000" longitude="174.800000" type="pickup_point" />
      <location name="Recipient A synthetic site" latitude="-36.880000" longitude="174.825000" type="receiving_point" />
      <location name="Recipient B synthetic site" latitude="-36.845000" longitude="174.760000" type="receiving_point" />
    </locations>
    <time_windows>
      <donation pickup_start="2026-08-10T00:45:00Z" pickup_end="2026-08-10T01:30:00Z" safe_deadline="2026-08-10T03:30:00Z" />
      <recipient_a receiving_start="2026-08-10T01:00:00Z" receiving_end="2026-08-10T03:00:00Z" />
    </time_windows>
  </fixed_scenario>

  <fixture_graph>
    <organisations count="4">
      <organisation key="woolworths_donor" role="donor" />
      <organisation key="kiwiharvest_operator" role="food_rescue_operator" />
      <organisation key="recipient_a" role="recipient" />
      <organisation key="recipient_b" role="recipient" />
    </organisations>
    <sites count="4">
      <site key="woolworths_store" type="store" organisation="woolworths_donor" />
      <site key="kiwiharvest_hub" type="warehouse" organisation="kiwiharvest_operator" />
      <site key="recipient_a_site" type="service_site" organisation="recipient_a" />
      <site key="recipient_b_site" type="service_site" organisation="recipient_b" />
    </sites>
    <actors>
      <actor key="driver" role="driver" scope="kiwiharvest_operator" />
      <actor key="recipient_a_responder" role="recipient_responder" scope="recipient_a_site" />
    </actors>
    <source_and_food>
      <import_batch source_system="synthetic_fixture" source_format="structured_form" idempotency_key="synthetic-success-path-v1" status="completed" />
      <source_record type="product" external_id="synthetic-product-yoghurt-001" />
      <source_record type="donation_listing" external_id="synthetic-donation-001" />
      <food_product gtin="00012345600012" name="Synthetic Chilled Yoghurt" />
    </source_and_food>
    <donation status="listed" source_site="woolworths_store" created_by="driver">
      <item key="barcode_chilled_item" line_number="1" quantity="10.000" unit="kg" storage_class="chilled" food_product="synthetic-product-yoghurt-001" gtin_snapshot="00012345600012" packaging="sealed" recall_status="not_recalled" date_mark_type="use_by" date_mark="2026-08-12" />
      <item key="no_barcode_ambient_item" line_number="2" quantity="8.000" unit="kg" storage_class="ambient" food_product="NULL" gtin_snapshot="NULL" packaging="opened" recall_status="not_checked" date_mark_type="none" />
      <condition key="listing_condition" item="barcode_chilled_item" checkpoint="listing" status="acceptable" temperature_celsius="4.00" />
      <status_event type="created" actor="driver" />
      <status_event type="listed" actor="driver" />
    </donation>
    <recipient_state>
      <recipient key="recipient_a_site" food_category="dairy" storage_class="chilled" capacity_status="known" available_quantity="30.000" unit="kg" need_quantity="20.000" need_priority="5" />
      <recipient key="recipient_b_site" food_category="dairy" storage_class="chilled" capacity_status="unknown" available_quantity="NULL" unit="kg" />
    </recipient_state>
  </fixture_graph>

  <state_checkpoints>
    <checkpoint id="listed" current_donation_status="listed" current_allocation_status="none" />
    <checkpoint id="confirmed_allocation" current_allocation_status="confirmed" required_events="reserved,confirmed" route_eligible="true" />
    <checkpoint id="selected_item_completed" current_allocation_status="fulfilled" current_delivery_status="completed" required_events="reserved,confirmed,fulfilled" />
    <partial_donation_rule>Because the no-barcode item is not allocated, the donation aggregate is not marked fully delivered in this first fixture.</partial_donation_rule>
  </state_checkpoints>

  <route_inputs provider="synthetic_fixture" frozen="true">
    <snapshot kind="traffic" coverage="synthetic-kiwiharvest-to-woolworths-to-recipient-a" />
    <snapshot kind="weather" coverage="synthetic-auckland-route" />
    <snapshot kind="road" coverage="synthetic-auckland-route" />
    <snapshot kind="eta" coverage="synthetic-route-legs" />
    <snapshot kind="allocation" coverage="barcode_chilled_item" />
    <snapshot kind="condition" coverage="barcode_chilled_item" />
    <snapshot kind="capacity" coverage="recipient_a_site" />
    <snapshot kind="location" coverage="kiwiharvest_hub,woolworths_store,recipient_a_site" />
    <validity_rule>Every required input has observed_at, recorded_at, valid_from, valid_until and payload; valid_until covers planned departure.</validity_rule>
  </route_inputs>

  <gap_closure>
    <gap id="food_category_bridge" status="deferred_schema_decision">
      <current_fixture_behavior>Use fixture-local classified_food_category in MatchCandidate.reason_components; do not pretend DonationItem already has a category column.</current_fixture_behavior>
      <required_follow_up>Owner decides whether category belongs on FoodProduct, DonationItem, or a separate classification table before matching service implementation.</required_follow_up>
    </gap>
    <gap id="route_origin_fk" status="deferred_schema_decision">
      <current_fixture_behavior>Store KiwiHarvest origin in location snapshot and proposal payload; DeliveryStop starts at donor pickup.</current_fixture_behavior>
      <required_follow_up>Decide whether RoutePlanningRun needs first-class origin site/location references.</required_follow_up>
    </gap>
    <gap id="snapshot_immutability" status="test_contract_only">
      <current_fixture_behavior>Assert fixture workflow does not mutate payload after creation.</current_fixture_behavior>
      <required_follow_up>Production repository or database write-once enforcement remains future work.</required_follow_up>
    </gap>
    <gap id="cross_table_invariants" status="future_service_contract">
      <current_fixture_behavior>Current database tests cover only constraints that exist in PostgreSQL.</current_fixture_behavior>
      <required_follow_up>Service tests must enforce decision gates, quantity lineage, actor scope, stop semantics and snapshot freshness.</required_follow_up>
    </gap>
    <gap id="partial_donation_completion" status="explicit_test_boundary">
      <current_fixture_behavior>Successful delivery is asserted for the selected allocation; donation is not closed while the second item is unallocated.</current_fixture_behavior>
      <required_follow_up>Define item-level completion or partial donation lifecycle before a full-donation success seed exists.</required_follow_up>
    </gap>
  </gap_closure>

  <implementation_files>
    <file path="backend/tests/fixtures/__init__.py" purpose="Fixture package marker" />
    <file path="backend/tests/fixtures/synthetic_food_diversion.py" purpose="Typed deterministic builders and scenario references" />
    <file path="backend/tests/test_synthetic_food_diversion_fixture.py" purpose="Phase 10A listed graph and query semantics" />
    <file path="backend/tests/test_synthetic_food_diversion_matching.py" purpose="Phase 10B matching and allocation checkpoint" />
    <file path="backend/tests/test_synthetic_food_diversion_route.py" purpose="Phase 10C frozen route and successful delivery" />
    <file path="backend/tests/test_synthetic_food_diversion_edges.py" purpose="Phase 10D constraint and semantic edge cases" />
    <file path="backend/tests/test_synthetic_food_diversion_concurrency.py" purpose="Phase 10D active allocation race" />
  </implementation_files>

  <phases>
    <phase id="10A" status="completed" name="Listed synthetic foundation">
      <phase_goal>建立一個可重複的 listed-stage scenario，涵蓋 organisations、sites、locations、actors、source provenance、donation、兩個 items、condition 和 recipient state。</phase_goal>
      <affected_components>backend/tests/fixtures/synthetic_food_diversion.py、backend/tests/test_synthetic_food_diversion_fixture.py、既有 Alembic postgres_session fixture。</affected_components>
      <data_flow>Fixed scenario clock → canonical organisations/sites/locations → actors/memberships → source/product → donation/items → condition/status events → recipient capability/need/availability → graph assertions。</data_flow>
      <pseudocode>build_listed_scenario(session, now): create fixed IDs; insert parent rows first; flush to obtain relationships; insert source and food facts; insert donation with barcode/no-barcode items; insert listing condition and events; insert recipient states; flush; return typed references。</pseudocode>
      <edge_cases>No-barcode item 的 product/GTIN 必須是 NULL；unknown capacity 的 quantity 必須是 NULL；navigation locations 必須是 current exact operator-confirmed operational points；所有 IDs 必須可重建。</edge_cases>
      <tests>完整 graph reconstruction、barcode snapshot、no-barcode semantics、valid GTIN、listing condition、active membership、navigation location query、known/unknown recipient capacity query。</tests>
      <completion_criteria>Phase 10A tests 在 PostgreSQL temporary schema 通過；沒有 live provider；沒有新增未經 owner decision 的 schema 欄位；scenario references 可被後續 Phase 10B–10C 重用。</completion_criteria>
    </phase>
    <phase id="10B" status="completed" name="Matching and confirmed allocation">
      <phase_goal>在 listed fixture 上建立 feasible/manual-review candidates、driver confirmation、recipient acceptance 和 confirmed allocation checkpoint。</phase_goal>
      <affected_components>synthetic_food_diversion.py、test_synthetic_food_diversion_matching.py、matching models/query helpers。</affected_components>
      <data_flow>Barcode item → completed match run → Recipient A feasible / Recipient B manual_review candidates → two human decisions for A → reserved allocation → confirmed allocation + events。</data_flow>
      <pseudocode>confirm_barcode_item_allocation(session, scenario): create run and candidates; assign stable reason_components; persist driver confirmation and recipient acceptance; create reserved allocation; append reserved event; transition to confirmed; append confirmed event。</pseudocode>
      <edge_cases>Unknown capacity 不可 rank；candidate recipient 與 allocation recipient 必須一致；no-barcode item 不得被隱性 allocation；confirmed query 只能返回 A。</edge_cases>
      <tests>Candidate reasons、decision actor、confirmed allocation query、allocation status events、active item uniqueness 和 candidate mismatch rejection。</tests>
      <completion_criteria>Confirmed checkpoint 可獨立建立並通過所有 matching tests；只用目前 schema 已存在的 constraints。</completion_criteria>
    </phase>
    <phase id="10C" status="completed" name="Frozen route and selected-item delivery">
      <phase_goal>從 confirmed allocation 建立 frozen traffic/weather/road/ETA inputs、route proposal、driver approval、delivery、stops 和 successful events。</phase_goal>
      <affected_components>synthetic_food_diversion.py、test_synthetic_food_diversion_route.py、route models/query helpers。</affected_components>
      <data_flow>Confirmed allocation + operational snapshots → selected proposal → approved route decision → assigned delivery → pickup/delivery stops → delivery events → fulfilled allocation。</data_flow>
      <pseudocode>complete_successful_delivery(session, scenario): assert confirmed allocation; create planning run; freeze eight input kinds; create selected proposal with origin payload; approve by driver; create delivery/stops; link allocation; append ordered events; transition delivery completed and allocation fulfilled。</pseudocode>
      <edge_cases>Route origin 目前只在 payload；snapshot validity 必須涵蓋 departure；distance 只能是 tie-breaker；完成一個 item 不得把整個 two-line donation 標成 delivered。</edge_cases>
      <tests>Snapshot completeness/preservation、proposal reason evidence、route approval、stop/location integrity、event order、allocation fulfilled transition、partial donation safety。</tests>
      <completion_criteria>Selected-item delivery graph 可完整重建；route input payload 不被 workflow 改寫；confirmed allocation 在完成後不再出現在 confirmed query。</completion_criteria>
    </phase>
    <phase id="10D" status="completed" name="Constraint, semantic and concurrency edges">
      <phase_goal>驗證 synthetic workflow 在 invalid data、stale state、visibility boundary 和 allocation race 下不會產生錯誤 graph。</phase_goal>
      <affected_components>test_synthetic_food_diversion_edges.py、test_synthetic_food_diversion_concurrency.py、現有 model/query helpers。</affected_components>
      <data_flow>Canonical stage → one controlled mutation or competing transaction → database rejection / query exclusion / single winner → rollback and exact assertion。</data_flow>
      <pseudocode>for each current constraint: build minimum stage; mutate one fact; flush/commit; assert IntegrityError; rollback. For query edges: create current/stale/protected rows; call actual selector; assert exact IDs. For race: reserve same item in two sessions; assert one active allocation。</pseudocode>
      <edge_cases>Invalid decision values、cross-recipient candidate、invalid snapshot validity、duplicate stop sequence、cross-delivery stop、actor reference mismatch、stale/protected capacity、expired membership、two-session allocation race。</edge_cases>
      <tests>Database constraint matrix、query semantic matrix、graph reconstruction、partial completion rule 和 PostgreSQL concurrency test。</tests>
      <completion_criteria>Current-schema edge tests 通過；future service rules 另列 contract，不用 xfail 偽裝成已完成；沒有重複既有單表 tests 而沒有新增整合價值。</completion_criteria>
    </phase>
  </phases>

  <deferred_service_contracts>
    <contract name="food_category_ownership">Donation item 的 category source / classification result 必須可追溯。</contract>
    <contract name="allocation_quantity_lineage">allocated_quantity &lt;= donation_item.quantity 且 unit 相容。</contract>
    <contract name="decision_gates">Recipient acceptance、driver route approval 和 active membership 必須先於下一狀態。</contract>
    <contract name="route_freshness">Traffic、weather、road、ETA 和 operational facts 在 planned departure 時必須仍有效。</contract>
    <contract name="condition_policy">Temperature threshold 和 manual_review / hard_block outcome 等 owner policy 確認後再測。</contract>
    <contract name="partial_donation_lifecycle">所有 item 完成、partial completion、withdrawal 和 full donation status 的規則需另定。</contract>
  </deferred_service_contracts>

  <definition_of_done>
    <criterion>XML plan 的 research findings、gap closure、scope、fixture graph 和 phase fields 完整。</criterion>
    <criterion>Phase 10A fixture builders 和 tests 使用現有 PostgreSQL/Alembic harness。</criterion>
    <criterion>至少一條 listed → confirmed allocation → selected-item completed 的可重建資料鏈。</criterion>
    <criterion>Barcode/no-barcode、known/unknown capacity、condition、locations 和 memberships 都有 assertions。</criterion>
    <criterion>每一個 current database invariant 都有 test 或明確標為 future service contract。</criterion>
    <criterion>沒有把 schema gaps 偷換成已完成功能。</criterion>
  </definition_of_done>
</synthetic_test_fixture_plan>
```
