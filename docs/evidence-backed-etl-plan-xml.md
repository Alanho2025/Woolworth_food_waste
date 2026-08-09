# Evidence-backed ETL master plan（XML-tagged）

> 這是 decision-grade master plan，不是 ETL code 或預先寫死的 implementation blueprint。詳細函式、欄位 mapping、FK 順序與 correction instructions，只在各 phase 開始前根據當時 repository 產生 self-contained execution brief。

```xml
<?xml version="1.0" encoding="UTF-8"?>
<evidence_backed_etl_plan version="2.0" status="phase_1_passed_ready_for_phase_2_brief" granularity="decision_grade">
  <metadata>
    <project>KiwiHarvest FoodFlow</project>
    <prepared_at timezone="Pacific/Auckland">2026-08-09</prepared_at>
    <source_of_truth>本 master XML 是唯一 source of truth；phase brief 只是當期衍生執行文件。</source_of_truth>
    <goal>先 ETL 可取得的真實公開資料；拿不到的 operational facts 才用有 evidence、bound、confidence、limitation 與 deterministic seed 的 simulation 補足。</goal>
    <current_boundary>Phase 1 已在 isolated snapshot 與 main gate 通過；real immutable source snapshots 與 reviewed inputs 已存在，沒有 DB／schema mutation，下一步由 Sol 推導 Phase 2 brief，再 dispatch 一個 NEW Luna。</current_boundary>
    <complexity_ceiling>Master plan 只定義 why、what、phase、gate 與 non-goals；how 的細節留給當期 execution brief。</complexity_ceiling>
  </metadata>

  <research_findings>
    <evidence_examined>
      <repository>
        <item>目前 SQLAlchemy models、Alembic revision 0cfadf2acb52、migration tests、database tests、docs/research.md 與 docs/python-database-foundation.md。</item>
        <item>backend/tests/fixtures/synthetic_food_diversion.py 是 test-only fixture，不是 application seed input。</item>
      </repository>
      <runtime>
        <item>已驗證 local Docker PostgreSQL 在唯一 Alembic head；有 29 張 application tables，加 alembic_version。</item>
        <item>檢查時 organisations、source_records、donations 均為 0 rows；alembic check 無 drift，migration tests 3 passed。</item>
      </runtime>
      <external>
        <source id="woolworths-store-locator" href="https://contact.woolworths.com.au/storelocator/service/corporateinfo/country/nz/division/all/tradinghours/current/weeks/1/json" authority="official">Woolworths NZ Store Locator JSON</source>
        <source id="kiwiharvest-contact" href="https://www.kiwiharvest.org.nz/contact-us" authority="official">KiwiHarvest branch evidence</source>
        <source id="kiwiharvest-annual-report-2025" href="https://www.kiwiharvest.org.nz/s/2025-KiwiHarvest_AnnualReport-Final.pdf" authority="official_historical">FY25 recipient evidence</source>
        <source id="kiwiharvest-food-policy" href="https://www.kiwiharvest.org.nz/donatefood" authority="official">Accepted-food scope</source>
        <source id="mpi-food-donation" href="https://www.mpi.govt.nz/dmsdocument/3783/send" authority="government">Food donation safety guidance</source>
        <source id="mpi-food-labels" href="https://www.mpi.govt.nz/food-safety-home/how-read-food-labels" authority="government">Date-mark semantics</source>
        <source id="mpi-recalls" href="https://www.mpi.govt.nz/food-safety-home/food-recalls-and-complaints/recalled-food-products" authority="government">Official recalled-products register</source>
        <source id="gs1-woolworths-2d" href="https://www.gs1nz.org/member-stories/woolworths-nz-2d-barcodes" authority="industry_primary">Woolworths NZ 2D barcode example</source>
      </external>
    </evidence_examined>

    <confirmed_current_state>
      <fact status="runtime-verified">Database 已 migrate，不需要重新設計基礎 schema 才能開始。</fact>
      <fact status="repository-confirmed">ImportBatch 與 SourceRecord 可承載 v1 ingestion envelope；多數 domain tables 沒有 direct source_record_id。</fact>
      <fact status="repository-confirmed">只有 exact、operator_confirmed、operational pickup／receiving locations 可進 route stop。</fact>
      <fact status="research-validated">公開資料可建立 store、branch、recipient candidate reference；無法取得 live donation、capacity、need、entrance、driver、vehicle 或 route event。</fact>
    </confirmed_current_state>

    <gaps>
      <gap>尚無 ETL package、manifest、source snapshot、simulation rules、bundle、loader CLI 或 ETL tests。</gap>
      <gap>沒有 private StoreCentral feed、current pilot roster 或 operator-confirmed operational data。</gap>
      <gap>目前 schema 沒有 data_origin 或 generic provenance column；v1 必須透過現有 SourceRecord.raw_reference／raw_payload、可直接連結的 source_record_id、deterministic IDs 與 bounded bundle／verification artifacts 保持可重建 provenance。若某 entity 的最低 provenance link 無法由現有 schema 與 bounded artifacts 表達，必須停止並另提 schema decision。</gap>
    </gaps>

    <weak_reasoning>
      <item>Evidence-backed simulation 只代表可辯護的 scenario，不代表真實 observation 或統計分布。</item>
      <item>Public address 不能直接升級成 loading bay／receiving entrance。</item>
      <item>Annual throughput 不能直接當某次 donation 或 live recipient capacity。</item>
      <item>只通過 database constraints 不等於 demo behavior 正確；還要測 provenance、time、capacity、human gates、rollback 與 negative paths。</item>
    </weak_reasoning>

    <unsupported_assumptions>
      <item>不得假設所有 Auckland stores 都參與 pilot。</item>
      <item>不得假設 FY25 recipient 名單仍是 current partner。</item>
      <item>不得假設 public coordinate 是可導航入口。</item>
      <item>不得把 simulated actor、approval、route 或 delivery 寫成真實事件。</item>
    </unsupported_assumptions>

    <missing_requirements>
      <item blocking="false_for_local_demo">Production credentials、refresh／CDC、retention、licensing confirmation 和 real operator data 尚未提供。</item>
      <item blocking="false_for_local_demo">沒有真實 quantity／capacity distribution；v1 不宣稱 statistical representativeness。</item>
    </missing_requirements>

    <ambiguities>
      <item>realistic 表示 source-backed identity、evidence-bounded values 與 schema-valid behavior，不表示 current 或 operator-approved。</item>
      <item>recipient candidate 不等於 current onboarded recipient。</item>
      <item>scenario 的 operator_confirmed 只是在 simulated world 成立，不能輸出成 real confirmation。</item>
    </ambiguities>

    <contradictions>
      <item resolution="separate_truth">Real public location 保持 public／unverified；demo 另建明確標 simulation 的 operational row。</item>
      <item resolution="preserve_unknown">Reference data 中拿不到的 capacity／need 保持 unknown；只有 demo subset 可有 evidence-backed simulation。</item>
      <item resolution="do_not_reuse_fixture">現有 synthetic fixture 只借鑑 test pattern，不複製其 IDs、名稱、地址或數值。</item>
    </contradictions>

    <questions_requiring_human_answers blocking="false_for_plan">
      <answer>Local evidence-backed demo 的方向已對齊；production promotion、真實 pilot roster、entrance、fleet 與 capacity 仍需 operator 決定。</answer>
    </questions_requiring_human_answers>

    <assumption_alignment>
      <assumption status="human-aligned">先用真實可取得資料；缺失 operational data 可以 simulation，但必須有 evidence。</assumption>
      <assumption status="human-aligned">Simulation 必須清楚標記，不能混成 real data。</assumption>
      <assumption status="decision-for-v1">使用 reference_catalog 與 realistic_demo 兩個 profiles；realistic_demo 是包含 reference closure 的完整 bundle，不是 delta。</assumption>
      <assumption status="decision-for-v1">v1 不新增 migration；若 provenance 無法安全表達，停止並另提 schema decision。</assumption>
    </assumption_alignment>
  </research_findings>

  <scope>
    <in_scope>Versioned source/evidence contracts、official snapshots、reviewed reference inputs、evidence-backed demo bundle、transactional idempotent loader、verification tests and docs。</in_scope>
    <out_of_scope>Production integrations、real operator claims、schema redesign、frontend/API/agent、route optimiser、scheduler／queue、generic ETL framework、data warehouse、reset／truncate／delete-all。</out_of_scope>
  </scope>

  <data_truth_policy>
    <origin code="observed">Snapshot 直接提供；保存 source、snapshot、time、reference and checksum。</origin>
    <origin code="derived">只作 deterministic transform；保存 source refs、function/version and input checksum。</origin>
    <origin code="evidence_backed_simulation">由 rule 產生；保存 evidence、bound、unit、seed、confidence、limitations and generated value。</origin>
    <origin code="unknown">證據不足時使用 NULL、unknown enum 或省略 row；保存 reason and promotion gate。</origin>
    <provenance_rule>每個 canonical entity 及其 truth-bearing field 都要可由 entity_type、entity_id、data_origin、source_refs and rule_refs 重建；這些 provenance index 可存於 bounded bundle／verification artifacts，schema 有 direct link 時也必須使用 source_record_id；source_system 名稱不能代替 data_origin。若最低 link 無法安全保存，停止而不猜測。</provenance_rule>
    <bundle_integrity>Canonical bundle content checksum 不包含 checksum 自身或 runtime timestamps，避免 circular checksum。ImportBatch.idempotency_key 保存 deterministic replay identity；ImportBatch.external_batch_id 保留 optional source-provided batch identity，不當作 checksum 欄位。Final checksum 保存在 bundle manifest 與 bounded load／verification report artifact；v1 不假設存在 LoadReport table，也不因此新增 schema。</bundle_integrity>
    <simulation_coverage_gate>Phase 0 依當時 schema 建立 exact machine-readable simulated-field inventory；Phase 3 builder 輸出的每個 simulated scalar 必須恰有一個 rule owner，zero missing、extra or duplicate。這份逐欄位清單不預先寫死在 master plan。</simulation_coverage_gate>
    <raw_payload_boundary max_serialized_bytes="65536">SourceRecord.raw_payload 只保存 allowlisted source payload and provenance metadata；禁止 secrets、real credentials、protected exact locations and unbounded snapshots。</raw_payload_boundary>
  </data_truth_policy>

  <profile_policy>
    <profile id="reference_catalog">只含 source-backed identity、dated relationship evidence、public／protected locations；unknown location facts 以 NULL 或省略 row 表示；不含 live state、route-ready locations 或 simulated operations。</profile>
    <profile id="realistic_demo" bundle_mode="full_closure">包含完整 reference closure 加上小型 deterministic operational scenario；local demo database 只載入此 bundle，不先載入 reference_catalog。</profile>
    <recipient_status>FY25-only且沒有 current evidence 的 organisation/site 採 conservative inactive mapping；current-public identity 可 active，但 current recipient role 仍必須有 explicit relationship evidence。</recipient_status>
    <scenario_selection>成功路徑只選 current-public、非 protected、具有可引用 public coordinate 與 current relationship evidence 的 candidate；條件不足則 Phase 3 停止，不偷用 historical／unknown candidate。</scenario_selection>
    <recall_rule>Phase 1 snapshot MPI recall register。Scenario item 只有在 identifiers 可比對且 as-of snapshot deterministic no-match 時才可標 not_recalled；missing／ambiguous data 必須 not_checked 並阻斷成功路徑。No-match 只表示該 snapshot 未列出可比對項目，不能證明產品安全、未來沒有 recall，或其他 register 沒有紀錄。</recall_rule>
    <location_rule>Scenario operational coordinate 必須引用選中 source coordinate、不得 jitter；exact／operator_confirmed 是明確的 scenario assertion，不是 operator evidence。沒有 source coordinate 就不建立 DeliveryStop。</location_rule>
    <quantity_rule>Donation quantity 只受獨立、記錄公式的 historical-scale ceiling 約束，不依賴 capacity；known scenario capacity 之後必須 cover allocation 且不超過同一 ceiling，避免 circular calibration。</quantity_rule>
  </profile_policy>

  <global_acceptance_criteria>
    <criterion id="AC-01">Real／derived／simulation／unknown 可逐 row／field 重建；simulated fields 100 percent rule-owned。</criterion>
    <criterion id="AC-02">reference_catalog 無 route-ready location 或 simulated operational row。</criterion>
    <criterion id="AC-03">realistic_demo 有一條完整 donation → human decisions → allocation → route decision → delivery success path及可查詢 negative path。</criterion>
    <criterion id="AC-04">同一 inputs、as_of、timezone and seed 產生相同 IDs、values and bundle_content_checksum。</criterion>
    <criterion id="AC-05">Dry-run 零 database mutation。</criterion>
    <criterion id="AC-06">同 bundle replay 零新增／更新／刪除。</criterion>
    <criterion id="AC-07">任何 validation／DB failure 全 transaction rollback；concurrent same-bundle load 只存在一份 graph。</criterion>
    <criterion id="AC-08">Known／unknown capacity、barcode／no-barcode、feasible／rejected match、public／scenario location 都有 tests。</criterion>
    <criterion id="AC-09">Source counts、dates、filters and limitations 可見；dated counts 不是永久常數。</criterion>
    <criterion id="AC-10">無 secret、real personal identity、protected exact location 或 oversized raw payload。</criterion>
    <criterion id="AC-11">無未批准 migration、table or column。</criterion>
    <criterion id="AC-12">README and Python database notes 說明 run、inspect and truth boundaries。</criterion>
    <criterion id="AC-13">每 phase 遵守 master → current brief → same Luna correction loop → Sol verification → append-only result → next-phase gate。</criterion>
    <criterion id="AC-14">採 minimum valid implementation；無 unrelated refactor、generic framework、premature abstraction or unjustified dependency。</criterion>
  </global_acceptance_criteria>

  <orchestration_policy status="mandatory">
    <authority>Direct execution prompt／phase brief 只能由本 master plan 和 current repository 衍生；它不能取代、放寬或暗改 master decisions。</authority>
    <roles>
      <sol_main>負責 reasoning、scope／brief definition、read-only inspection／review、重跑 verification、gate decision and user-facing communication；Sol／主線不直接寫入任何 project file，也不直接維護或修改 master XML。</sol_main>
      <luna_worker>只實作當期 brief 與 Sol 發出的 Must-fix correction；在 isolated worktree 寫入所有 project-file changes，包括 execution brief、phase implementation／correction、documentation correction 及 Sol 明確批准的 master-plan result append；不得自行改 master decisions。</luna_worker>
    </roles>
    <before_phase>
      <rule>Sol 重讀當前 phase、global decisions、stop conditions and prior actual results，再 inspect code、models、migration、tests、dependencies、git diff and relevant data files。</rule>
      <rule>Sol 定義只針對當期的 self-contained brief；不得把整份 master plan 丟給 Luna 自行推斷。若 brief 要保存為 project file，由 Luna 在 isolated worktree 依 Sol 的 bounded content 寫入。</rule>
      <brief_required>phase ID／goal、repo evidence、allowed／forbidden files、dependencies／setup、data flow／order、current functions／objects contracts、state／rule ownership、mapped tests、exact verification／outcomes、completion criteria、risks／assumptions／decisions／stop conditions、out-of-scope、write scope and expected files。</brief_required>
    </before_phase>
    <worker_boundary>
      <rule>Luna 在 isolated worktree 寫入，只改 brief 允許的 files；不得 scope expansion、future-phase work、unrelated refactor or自行改寫 master decisions，也不得與主線同時修改同一批 files。Sol／主線不得與 Luna 並行寫入同一批 files。</rule>
      <rule>同一 phase 的所有 correction 使用同一 Luna；phase pass 後關閉，下一 phase 使用新的 Luna and new brief。</rule>
      <handoff>changed files、summary、actual tests／commands／results、remaining risks／failures and master-plan conflicts。</handoff>
    </worker_boundary>
    <sol_review_loop>
      <rule>Sol 打開每個 changed file and full diff，並在 main integration environment 重跑 phase tests／verification。</rule>
      <checks>Schema／FK、provenance、idempotency、concurrency、transaction／rollback、non-destructive behavior、truth boundaries、secrets／protected locations／raw payload、acceptance and completion criteria。</checks>
      <classification>Must-fix 才交回同一 Luna；Optional 不阻擋 phase，也不擴大 implementation scope。Sol 不直接替 Luna 重寫 phase code。</classification>
      <gate>每次 correction 後重新逐檔 review and verify；只有 latest attempt passed 才可開下一 phase。</gate>
    </sol_review_loop>
    <phase_result_contract append_only="true" required_fields="phase_id,attempt_id,status,started_at,completed_at,base_revision,worker,execution_brief_id,execution_brief_path,execution_brief_checksum,worktree_id,worktree_path,worker_write_scope,changed_files,luna_handoff_ref,main_file_inspection,main_diff_ref,tests,verification,schema_check,provenance_check,idempotency_check,concurrency_check,transaction_check,data_truth_check,completion_results,remaining_risks,master_plan_changes,evidence_note">
      <status_values>passed、needs_fix、blocked</status_values>
      <rule>每次 attempt 新增一筆 immutable result；不得覆寫 prior attempt。只有 latest passed result unlocks next phase。</rule>
      <rule>Sol 決定是否通過並提供 exact bounded master-plan result append content；同一 phase 的 Luna 在 isolated worktree 寫入該 append，Sol 隨後逐檔 review／verify，確認後關閉該 Luna。Luna 不得自行新增、刪除或改寫 master decisions。</rule>
    </phase_result_contract>
    <user_communication>Sol 在 phase start、initial review、Must-fix correction、verification completion and gate decision 向 user 提供簡潔證據；不轉貼 Luna 長篇原始輸出。</user_communication>
  </orchestration_policy>

  <anti_overengineering_policy status="hard_rules">
    <rule>Master plan 是 scope ceiling，不代表每個 tag 都要變成 class／service／abstraction。</rule>
    <rule>每 phase 只完成當期 acceptance；不提前做後續 phase。</rule>
    <rule>一處使用的邏輯直接實作；只有實質重複且抽取能降低複雜度才加 helper。</rule>
    <rule>禁止 unrelated refactor、general cleanup、generic ETL framework、plugin／repository／service／factory layering。</rule>
    <rule>不加入 Airflow、Dagster、Spark、pandas、Polars、queue、scheduler or background orchestration。</rule>
    <rule>優先使用現有 Python、Pydantic、httpx、SQLAlchemy、Alembic、PostgreSQL、pytest and argparse。</rule>
    <rule>New migration、runtime dependency or cross-layer abstraction 必須由當期 acceptance 證明必要；否則停止並請 user 決定。</rule>
    <rule>最小實作若正確、清楚、可驗證且符合 brief，就接受；不追加 enterprise hardening。</rule>
  </anti_overengineering_policy>

  <phases>
    <phase id="0" name="Freeze minimal contracts" status="passed">
      <phase_goal>建立剛好足夠的 source、evidence、origin、rule、bundle and scenario control files。</phase_goal>
      <files_likely_to_be_added_or_modified>backend/app/etl/{contracts,manifest}.py；data/etl/{manifests,evidence,rules,reference}/*；focused contract tests。Luna-only：當期 brief and Sol-approved master result append；Sol 只 review／verify。</files_likely_to_be_added_or_modified>
      <dependencies_and_setup_steps>Use existing Python／Pydantic；no DB or network；inspect current schema before fixing exact field inventory。</dependencies_and_setup_steps>
      <affected_components>ETL contracts and versioned control data only。</affected_components>
      <data_flow>Versioned JSON／CSV → strict parse → cross-reference and simulated-field coverage validation。</data_flow>
      <implementation_details>Materialise four origins、origin-specific metadata、source mappings、bundle_id/content-checksum rule、scenario topology-only config and exact simulated-field ownership。No generic framework。</implementation_details>
      <pseudocode>parse; resolve references; compare generated-field inventory to rule targets; calculate deterministic control checksums; fail on gap。</pseudocode>
      <edge_cases>Missing evidence、duplicate owner、unknown target、circular checksum、secret key、scenario config containing generated values。</edge_cases>
      <tests_required>Contract rejection／determinism／coverage tests mapped to AC-01、04、10、14；governance preflight mapped to AC-13。</tests_required>
      <verification_commands_or_observable_outcomes>uv run pytest focused Phase 0 tests；all control files parse with zero unresolved refs／coverage gaps。</verification_commands_or_observable_outcomes>
      <completion_criteria>Downstream phases不需要 invent source、origin、simulated target or checksum semantics。</completion_criteria>
      <risks_assumptions_and_decisions>Risk: contracts become framework；decision: smallest concrete Pydantic models only。</risks_assumptions_and_decisions>
      <explicitly_outside_scope>Network、source parsing、simulation、DB sessions、schema change。</explicitly_outside_scope>
    </phase>

    <phase id="1" name="Extract real-source snapshots" status="passed" depends_on="phase-0">
      <phase_goal>取得 immutable Woolworths and MPI recall snapshots，並建立 reviewed KiwiHarvest reference inputs。</phase_goal>
      <files_likely_to_be_added_or_modified>Explicit extract module；Woolworths／MPI recall adapters；reviewed input files；small fixtures/tests；.gitignore；pyproject.toml and uv.lock only to move existing httpx into runtime。Luna-only：當期 brief and Sol-approved master result append；Sol 只 review／verify。</files_likely_to_be_added_or_modified>
      <dependencies_and_setup_steps>Network only for explicit extract；tests use local fixtures／mock transport；raw snapshots remain ignored。</dependencies_and_setup_steps>
      <affected_components>HTTP boundary、source adapters、local raw artifact directory and reviewed references。</affected_components>
      <data_flow>Official response → bounded immutable snapshot／checksum → source-specific raw records；reviewed research → versioned records。</data_flow>
      <implementation_details>One explicit adapter per source；no general crawler。Snapshot size and SourceRecord 65,536-byte payload limits are separate。Record before／after filters and drift。</implementation_details>
      <pseudocode>fetch explicit sources; validate response; hash and save atomically; parse allowlisted fields; emit report。</pseudocode>
      <edge_cases>Timeout、HTML error、schema drift、duplicate ID、count drift、ambiguous recall identifiers、protected location。</edge_cases>
      <tests_required>Snapshot determinism／failure／no-live-network／PII boundary tests mapped to AC-04、09、10、14；AC-13 governance preflight。</tests_required>
      <verification_commands_or_observable_outcomes>Focused Phase 1 pytest；locked dependency sync；explicit extract reports URLs、times、checksums、bytes and counts；zero DB writes。</verification_commands_or_observable_outcomes>
      <completion_criteria>All real inputs are reproducible, source-linked and safely bounded；no guessed facts。</completion_criteria>
      <risks_assumptions_and_decisions>Public source drift must fail visibly；raw redistribution remains local-only unless licensing is confirmed。</risks_assumptions_and_decisions>
      <explicitly_outside_scope>StoreCentral、auth、scheduled fetch、OCR、general scraping、geocoding。</explicitly_outside_scope>
    </phase>

    <phase id="2" name="Build reference catalog" status="planned" depends_on="phase-1">
      <phase_goal>把 real/reviewed records 轉成 deterministic reference entities，不升級成 live operational truth。</phase_goal>
      <files_likely_to_be_added_or_modified>Minimal normalizer／transform／validator modules and focused reference tests；reviewed inputs only for corrected mapping。Luna-only：當期 brief and Sol-approved master result append；Sol 只 review／verify。</files_likely_to_be_added_or_modified>
      <dependencies_and_setup_steps>Use Phase 1 checksummed artifacts；no database required for pure build tests。</dependencies_and_setup_steps>
      <affected_components>Organisation、Role、Site、public/protected Location、SourceRecord canonical bundle rows。</affected_components>
      <data_flow>Raw records → explicit mapping／normalization → deterministic IDs／provenance → reference_catalog bundle。</data_flow>
      <implementation_details>Preserve FY25 versus current evidence；historical-only status is inactive and dated role ends；identity-only sources do not create current recipient role；all reference locations remain non-operational。</implementation_details>
      <pseudocode>map source keys; create evidence-supported rows; attach provenance; validate dates／locations／duplicates; canonical-sort and checksum。</pseudocode>
      <edge_cases>Rename、alias collision、no location、protected point、dated-only relationship、no current relationship evidence。</edge_cases>
      <tests_required>Reference safety／determinism／status-role semantics／provenance tests mapped to AC-01、02、04、09、10、14；AC-13 governance and scope preflight。</tests_required>
      <verification_commands_or_observable_outcomes>Focused Phase 2 pytest and reference build；report has zero simulated rows and zero route-ready locations。</verification_commands_or_observable_outcomes>
      <completion_criteria>Reference bundle is deterministic, source-backed and cannot be queried as a delivery plan。</completion_criteria>
      <risks_assumptions_and_decisions>Inactive means dated-only reference eligibility, not proof an organisation closed；this limitation must remain visible。</risks_assumptions_and_decisions>
      <explicitly_outside_scope>Current partnership verification、operational address、donation／capacity／route rows。</explicitly_outside_scope>
    </phase>

    <phase id="3" name="Build evidence-backed demo scenario" status="planned" depends_on="phase-2">
      <phase_goal>只補足測試完整 behavior 所需的 unavailable facts，每個值都可追到 rule and evidence。</phase_goal>
      <files_likely_to_be_added_or_modified>Minimal simulation／scenario modules；simulation rules／scenario config；focused rule and bundle tests。Luna-only：當期 brief and Sol-approved master result append；Sol 只 review／verify。</files_likely_to_be_added_or_modified>
      <dependencies_and_setup_steps>Validated reference bundle、frozen as_of／timezone／seed、Phase 0 exact rule inventory and Phase 1 recall snapshot。</dependencies_and_setup_steps>
      <affected_components>Scenario actors、locations、products/items、donations、recipient state、matching／allocation、route／delivery records。</affected_components>
      <data_flow>Reference closure + scenario keys + evidence rules + seed → generated facts → semantic validation → realistic_demo full bundle。</data_flow>
      <implementation_details>Use pseudonymous actors；separate scenario locations；one barcode and one no-barcode path；known and unknown capacity；human approval gates；success and negative paths。Recall no-match and location assertions follow profile policy；route metrics stay unknown without provider evidence。</implementation_details>
      <pseudocode>select eligible source entities; resolve one rule per generated field; build bounded timeline and graph; reject unsupported or unsafe value; canonical-sort and checksum。</pseudocode>
      <edge_cases>No eligible current recipient、not_checked recall、unknown capacity、unsafe deadline、public stop、protected identity、same seed reordered inputs、quantity/capacity cycle。</edge_cases>
      <tests_required>100 percent field-rule coverage、determinism、full graph、negative branches、truth-boundary tests mapped to AC-01、03、04、08、10、14；AC-13 preflight。</tests_required>
      <verification_commands_or_observable_outcomes>Focused Phase 3 pytest and demo build；report separates origins, shows zero coverage gaps and no unsupported fallback value。</verification_commands_or_observable_outcomes>
      <completion_criteria>Scenario is deterministic, schema-valid and useful for behavior tests without claiming real operations。</completion_criteria>
      <risks_assumptions_and_decisions>Aggregate evidence supports only broad bounds；confidence and limitation remain visible。No eligible safe recipient is a stop condition。</risks_assumptions_and_decisions>
      <explicitly_outside_scope>Forecasting、population synthesis、real identity／consent、route recommendation or optimisation benchmark。</explicitly_outside_scope>
    </phase>

    <phase id="4" name="Load safely into PostgreSQL" status="planned" depends_on="phase-3">
      <phase_goal>以 dry-run、single transaction、exact replay and conflict rejection 載入 full bundle。</phase_goal>
      <files_likely_to_be_added_or_modified>Minimal loader／CLI；focused integration／idempotency／rollback／concurrency tests；package scripts if needed。Luna-only：當期 brief and Sol-approved master result append；Sol 只 review／verify。</files_likely_to_be_added_or_modified>
      <dependencies_and_setup_steps>Docker PostgreSQL at expected Alembic head；validate bundle before write；derive current FK order from inspected metadata in the phase brief。</dependencies_and_setup_steps>
      <affected_components>ImportBatch、SourceRecord、current domain tables、session／transaction boundary and CLI。</affected_components>
      <data_flow>Bundle → offline validation → DB preflight → one transaction／FK-safe inserts → batch completion → commit／report。</data_flow>
      <implementation_details>Deterministic IDs；bundle_content_checksum in the bundle manifest and bounded load／verification report artifact；ImportBatch.idempotency_key binds replay identity；identical completed replay is no-op；conflict never overwrites；race loser rollback then checks committed winner；no reset／delete／blanket upsert。</implementation_details>
      <pseudocode>validate; dry-run or begin; acquire batch keys; insert in current FK order; flush; complete batches; commit once; rollback all on error。</pseudocode>
      <edge_cases>Replay、concurrent replay、conflicting ID、stale migration、late FK failure、connection loss、unrelated manual rows。</edge_cases>
      <tests_required>Dry-run／replay／rollback／concurrency／schema tests mapped to AC-05、06、07、11、14；AC-13 preflight。</tests_required>
      <verification_commands_or_observable_outcomes>Focused PostgreSQL tests；dry-run no counts change；first load one graph；second load zero changes；late failure leaves no partial rows。</verification_commands_or_observable_outcomes>
      <completion_criteria>Atomic load、safe replay、clear report and no destructive path。</completion_criteria>
      <risks_assumptions_and_decisions>Existing unrelated rows are preserved；v1 initialise-and-replay is not source sync。</risks_assumptions_and_decisions>
      <explicitly_outside_scope>Refresh／CDC、purge、post-commit rollback、distributed transaction、multi-tenant production load。</explicitly_outside_scope>
    </phase>

    <phase id="5" name="Verify and document" status="planned" depends_on="phase-4">
      <phase_goal>用 read-only queries and tests 證明 provenance、behavior、negative paths and replay，而不是只看 row count。</phase_goal>
      <files_likely_to_be_added_or_modified>Minimal verifier and loaded-profile tests；README.md；docs/python-database-foundation.md。Luna-only：當期 brief and Sol-approved master result append；Sol 只 review／verify。</files_likely_to_be_added_or_modified>
      <dependencies_and_setup_steps>Reference profile 在 fresh reference-only temporary schema 驗證；realistic_demo 在另一個 fresh schema 或只載入 full bundle 的 local demo DB 驗證；兩者使用分離的 verification context，不在同一 DB 依序疊加。</dependencies_and_setup_steps>
      <affected_components>Read-only verification queries、ETL test suite and operator／learning docs。</affected_components>
      <data_flow>Expected bundle checksum + loaded rows → provenance／relationship／lifecycle assertions → JSON report and docs evidence。</data_flow>
      <implementation_details>Reconcile every persisted row；assert reference locations never route-ready；reconstruct success／negative paths；report origin/rule counts without protected payload；record only commands actually run。</implementation_details>
      <pseudocode>query; reconcile IDs/checksums/provenance; assert truth and lifecycle gates; emit pass/fail report。</pseudocode>
      <edge_cases>Wrong DB context、partial manual mutation、orphan mapping、stale docs、duplicate event、expired capacity、public route stop。</edge_cases>
      <tests_required>Loaded provenance／behavior／privacy／docs tests mapped to AC-01、02、03、06、08、10、12；AC-13／14 governance and scope preflight。</tests_required>
      <verification_commands_or_observable_outcomes>Full ETL pytest、alembic check、reference-only verify、demo verify、repository quality gate；zero orphan/conflict and one complete simulated lifecycle。</verification_commands_or_observable_outcomes>
      <completion_criteria>Every AC has executed evidence；reader can distinguish real、derived、simulated and unknown without reading code。</completion_criteria>
      <risks_assumptions_and_decisions>Count-only pass is insufficient；unexecuted command is never recorded as pass。</risks_assumptions_and_decisions>
      <explicitly_outside_scope>Frontend/API E2E、agent evaluation、route optimality、production load or business UAT。</explicitly_outside_scope>
    </phase>
  </phases>

  <test_acceptance_mapping>
    <mapping criterion="AC-01" phases="0,2,3,5" />
    <mapping criterion="AC-02" phases="2,5" />
    <mapping criterion="AC-03" phases="3,5" />
    <mapping criterion="AC-04" phases="0,1,2,3" />
    <mapping criterion="AC-05" phases="4" />
    <mapping criterion="AC-06" phases="4,5" />
    <mapping criterion="AC-07" phases="4" />
    <mapping criterion="AC-08" phases="3,5" />
    <mapping criterion="AC-09" phases="1,2" />
    <mapping criterion="AC-10" phases="0,1,2,3,5" />
    <mapping criterion="AC-11" phases="4,5" />
    <mapping criterion="AC-12" phases="5" />
    <mapping criterion="AC-13" phases="0,1,2,3,4,5" />
    <mapping criterion="AC-14" phases="0,1,2,3,4,5" />
  </test_acceptance_mapping>

  <phase_execution_results append_only="true">
    <phase_result>
      <phase_id>0</phase_id>
      <attempt_id>phase-0-attempt-1-correction-2</attempt_id>
      <status>passed</status>
      <started_at>2026-08-09T19:47:53+12:00</started_at>
      <completed_at>2026-08-10T00:20:40+12:00</completed_at>
      <base_revision>234981319170b43b209fea3371f460c44d3c39a8</base_revision>
      <worker>gpt-5.6-luna；agent_id 019fe65b-f583-7662-a655-f21193f79053；nickname Epicurus</worker>
      <execution_brief_id>phase-0-attempt-1</execution_brief_id>
      <execution_brief_path>docs/etl/execution-briefs/phase-0-attempt-1.md</execution_brief_path>
      <execution_brief_checksum>b2de9bc39c68624220a8fcf3b6acbbb51a6e921935f45f82496d0e5e62ad6658</execution_brief_checksum>
      <worktree_id>kiwiharvest-phase0-attempt1.2o6j71</worktree_id>
      <worktree_path>/private/tmp/kiwiharvest-phase0-attempt1.2o6j71</worktree_path>
      <worker_write_scope>Phase 0 exact 11-file scope：execution brief；backend/app/etl init、contracts、manifest；four control JSON files；backend/tests/etl init and two focused test files。Master write separately limited to this Sol-approved result/status update。</worker_write_scope>
      <changed_files>docs/etl/execution-briefs/phase-0-attempt-1.md；backend/app/etl/__init__.py；backend/app/etl/contracts.py；backend/app/etl/manifest.py；data/etl/manifests/sources.v1.json；data/etl/evidence/evidence-register.v1.json；data/etl/rules/simulation-rules.v1.json；data/etl/reference/demo-scenario.v1.json；backend/tests/etl/__init__.py；backend/tests/etl/test_contracts.py；backend/tests/etl/test_manifest.py；docs/evidence-backed-etl-plan-xml.md result/status update。</changed_files>
      <luna_handoff_ref>agent 019fe65b-f583-7662-a655-f21193f79053；initial implementation handoff；correction submissions 019fe66b-e79e-70f1-800a-d0af1bcca84b and 019fe672-bee9-7590-a84b-50df6bd15358；integration submission 019fe676-5298-7293-946a-7c9a7fc83e0f。</luna_handoff_ref>
      <main_file_inspection>Sol 逐檔檢查 11 files；每輪 correction 後重新檢查 modified contracts、tests and brief；四個 control files、loader and exact scope 再作 semantic／hash verification。</main_file_inspection>
      <main_diff_ref>Isolated baseline existing files changed=0 and missing=0；exact 11 new allowed files；forbidden=0；integration後 snapshot/main SHA-256 11/11 equal。</main_diff_ref>
      <tests>Initial 19 focused tests passed但 adversarial review 找到 provenance gaps；correction 1 reached 32 passed；correction 2 and main gate reached 37 passed in 0.11s。</tests>
      <verification>ruff format --check reported 6 files already formatted；ruff check passed；mypy passed for 3 ETL source files；control smoke reported 5 sources、16 evidence entries、25 rules、257 targets and zero missing／extra／duplicate／unknown-table／missing-evidence；five independent adversarial probes passed。</verification>
      <schema_check>Base.metadata remained 29 tables；Phase 0 rule inventory covers 257 fields in 25 scenario tables exactly once；no model、migration、table or column changed。</schema_check>
      <provenance_check>Four strict origin variants、field-level mixed-origin provenance、actual generated-value equality、unknown sentinel boundary、duplicate canonical-key rejection and exactly-one simulated field rule owner are enforced。</provenance_check>
      <idempotency_check>Not applicable to Phase 0 because no loader or database write exists；deterministic bundle content checksum and UUID5 identity were tested under mapping／record reordering and content change。</idempotency_check>
      <concurrency_check>Not applicable to Phase 0 because no shared state、loader or database transaction exists。</concurrency_check>
      <transaction_check>Not applicable to Phase 0 because all behavior is local parse／validation／checksum with no network or database side effect。</transaction_check>
      <data_truth_check>Raw envelope validation is construction-time fail-closed across payload and metadata；case-insensitive nested secret keys and payloads above 65536 canonical bytes fail；scenario config contains selectors／cases／topology only；real、derived、simulated and unknown boundaries remain explicit。</data_truth_check>
      <completion_results>Passed：downstream phases now have concrete source／evidence／origin／field provenance／simulation ownership／scenario topology／bundle integrity contracts and zero unresolved control references，without a generic ETL framework。</completion_results>
      <remaining_risks>External source availability／terms、actual snapshot parsing、eligible current-public recipient selection、evidence-bounded generated values、database replay／rollback／concurrency and final behavior remain for Phases 1–5。</remaining_risks>
      <master_plan_changes>Root and metadata boundary advanced to Phase 1 readiness；Phase 0 status changed planned to passed；this append-only phase result added；no master decision、scope、stop condition or later phase content changed。</master_plan_changes>
      <evidence_note>Evidence is limited to inspected local files and executed local commands；Phase 0 made no network request and no database mutation。Two Sol Must-fix correction loops are preserved in the execution brief and this result summary。</evidence_note>
    </phase_result>
    <phase_result>
      <phase_id>1</phase_id>
      <attempt_id>phase-1-attempt-1-correction-1</attempt_id>
      <status>passed</status>
      <started_at>2026-08-10T01:29:15+12:00</started_at>
      <completed_at>2026-08-10T01:31:33+12:00</completed_at>
      <base_revision>234981319170b43b209fea3371f460c44d3c39a8</base_revision>
      <worker>gpt-5.6-luna；agent_id 019fe687-9215-7c90-835a-0f7dd1ba3feb；nickname Popper</worker>
      <execution_brief_id>phase-1-attempt-1</execution_brief_id>
      <execution_brief_path>docs/etl/execution-briefs/phase-1-attempt-1.md</execution_brief_path>
      <execution_brief_checksum>095b9137a98e36de4ea7bdc14bd9b8d58cf184efcf670ba86755ce57cfd49808</execution_brief_checksum>
      <worktree_id>kiwiharvest-phase1-attempt1.1wy3vF</worktree_id>
      <worktree_path>/private/tmp/kiwiharvest-phase1-attempt1.1wy3vF</worktree_path>
      <worker_write_scope>Sol-approved Phase 1 correction 1 snapshot scope；integration copied exactly 21 non-ignored project files, six ignored local runtime artifacts, and this bounded master result append。No unrelated dirty or untracked main file was modified。</worker_write_scope>
      <changed_files>docs/etl/execution-briefs/phase-1-attempt-1.md；backend/app/etl/contracts.py；backend/app/etl/extract.py；backend/app/etl/sources/__init__.py；backend/app/etl/sources/woolworths.py；backend/app/etl/sources/mpi_recalls.py；data/etl/manifests/sources.v1.json；data/etl/evidence/evidence-register.v1.json；data/etl/reviewed/kiwiharvest-branches.v1.json；data/etl/reviewed/recipient-candidates.v1.csv；data/etl/reviewed/kiwiharvest-food-policy.v1.json；backend/tests/etl/fixtures/woolworths-minimal.json；backend/tests/etl/fixtures/mpi-recalls-minimal.md；backend/tests/etl/test_extract.py；backend/tests/etl/test_woolworths_source.py；backend/tests/etl/test_mpi_recalls_source.py；backend/tests/etl/test_reviewed_inputs.py；backend/tests/etl/test_manifest.py；.gitignore；pyproject.toml；uv.lock；docs/evidence-backed-etl-plan-xml.md；data/etl/raw/2026-08-09/woolworths-store-locator.json；data/etl/raw/2026-08-09/woolworths-store-locator.records.json；data/etl/raw/2026-08-09/woolworths-store-locator.report.json；data/etl/raw/2026-08-09/mpi-recalled-products.md；data/etl/raw/2026-08-09/mpi-recalled-products.records.json；data/etl/raw/2026-08-09/mpi-recalled-products.report.json</changed_files>
      <luna_handoff_ref>agent 019fe687-9215-7c90-835a-0f7dd1ba3feb；same Luna correction 1 worker Popper；Sol-approved final-gate integration and result-recording dispatch。</luna_handoff_ref>
      <main_file_inspection>Immediately before integration, all 81 phase-start baseline paths matched 81/81. Sol independently inspected the correction files and accepted schema, provenance, truth-boundary, and scope evidence. After integration, the 21 non-ignored files and six ignored artifacts matched the snapshot byte-for-byte。</main_file_inspection>
      <main_diff_ref>Baseline guard passed 81/81 before copying. Snapshot/main SHA-256 comparison passed 21/21 non-ignored files and 6/6 ignored artifacts. Existing unrelated dirty and untracked main paths were preserved; only this master XML result append was additionally changed by the integration task。</main_diff_ref>
      <tests>In snapshot and main: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -p no:cacheprovider backend/tests/etl/test_contracts.py backend/tests/etl/test_manifest.py backend/tests/etl/test_extract.py backend/tests/etl/test_woolworths_source.py backend/tests/etl/test_mpi_recalls_source.py backend/tests/etl/test_reviewed_inputs.py -q` passed 72 tests。</tests>
      <verification>Snapshot and main ruff format checks reported 15 files already formatted；ruff check passed；mypy passed for 7 ETL source files；`UV_CACHE_DIR=/private/tmp/kiwiharvest-phase1-uv-cache uv lock --check` resolved 45 packages。Both live CLI runs exited 0 under Sol's network gate: Woolworths HTTP 200、413 input、142 AUK、61 COUNTDOWN、353689 raw bytes、raw SHA-256 61161f99882fa0a8f8906eb3090f3735fbbaf996f5359bbd5bf361abedff7998、records SHA-256 de02da0a3516e9c56595d4210ac3f8fc1598ca0ba94f2de9a7788f126636415d、missing Content-Type warning、drift=[]；MPI HTTP 200、text/plain、169586 raw bytes、raw SHA-256 ffc3c1a89f4e22952be4102ddeb286cdf3148f5fae08c729e958e6d16b24c4c0、records SHA-256 fdc359115f3670ba4d0af36d94184c3f5856d70572ee6c2ef0ace3636ee7b0e7、660 records、exact year counts、source_last_reviewed=2026-07-23、drift=[]、authority／CC BY attribution present。Main artifact/report coherence passed for both sources；all six raw/records/report files are ignored by git。</verification>
      <schema_check>Passed：no backend/app/models、migrations、model or schema file changed from the phase-start baseline；Phase 1 implementation has no SQLAlchemy/database import, session, or write；no DB/schema mutation occurred in Phase 1。</schema_check>
      <provenance_check>Passed：official canonical authority is separate from MPI Jina retrieval route；exact raw, records, and report paths/checksums/bytes/counts agree；Woolworths missing Content-Type is a visible warning；reviewed FY25/current-public relationship, coordinate, protected, reference-only and route_ready=false boundaries remain explicit。</provenance_check>
      <idempotency_check>Passed：exact replay reuses a coherent artifact set；different raw conflict, partial/incoherent report, aggregate/per-year drift, duplicate, WAF, and shape failures reject without overwrite；atomic temporary-file cleanup is tested。</idempotency_check>
      <concurrency_check>Not applicable as a database concurrency claim：Phase 1 has no shared database state；exclusive local artifact publication prevents target overwrite races。</concurrency_check>
      <transaction_check>Not applicable：Phase 1 performs zero database writes and has no database transaction。</transaction_check>
      <data_truth_check>Passed：live extracted and reviewed inputs only；no simulated operational facts were added；all recipient and branch points are reference-only with route_ready=false；MPI absence/no-match remains insufficient as product safety proof。</data_truth_check>
      <completion_results>Passed：bounded immutable real-source snapshots, deterministic allowlisted records, reviewed KiwiHarvest branch/recipient/policy inputs, exact source-linked reports, runtime dependency lock, offline/live gates, main integration, and ignored local artifacts are complete. No later phase implementation or DB load was performed。</completion_results>
      <remaining_risks>Provider/source drift remains possible；Woolworths may omit Content-Type；MPI depends on Jina Reader conversion and official recall URL shape；public/reference coordinates are not operational entrances or loading bays；raw artifacts remain local-only pending terms review；Phase 2 must preserve all reviewed truth boundaries。</remaining_risks>
      <master_plan_changes>Root status and metadata/current-boundary advanced to Phase 2 readiness；Phase 1 changed from planned to passed；this single append-only Phase 1 result was added；bottom evidence_note was updated；Phase 0 result, Phase 2–5 planned statuses, master decisions, stop conditions, and review loops were preserved unchanged。</master_plan_changes>
      <evidence_note>Sol final gate passed offline and with live provider access；main pre-integration baseline was 81/81；post-integration snapshot/main byte checks were 21/21 plus 6/6 ignored artifacts；main focused tests and validators passed；no DB, schema, migration, model, or later-phase implementation was added。</evidence_note>
    </phase_result>
  </phase_execution_results>

  <stop_conditions>
    <item>Required simulated field has no defensible evidence-bound rule。</item>
    <item>No eligible current-public and safe scenario recipient exists。</item>
    <item>Current schema cannot preserve minimum provenance without migration。</item>
    <item>Source terms forbid planned artifact。</item>
    <item>Loader would need destructive cleanup or overwrite。</item>
    <item>Three full-document review loops or final XML／link／required-field／diff checks have not passed。</item>
  </stop_conditions>

  <three_pass_review execution="strictly_sequential" status="completed">
    <review_rule>每一輪都從頭檢查整份當時最新版的所有 sections、phases、contracts、tests、risks、scope、wording and XML；當輪全部 findings 修完並重新檢查後才開始下一輪。</review_rule>
    <review_loop id="1" status="completed_with_fixes" scope="entire_document">
      <result>修正 profile closure、provenance／transaction gaps、historical/current boundary、negative paths and verification wording。Loop 2 後續確認 Loop 1 的 attribute checker 過淺；該 claim 不再作為 final evidence。</result>
    </review_loop>
    <review_loop id="2" status="completed_with_fixes" scope="entire_latest_document">
      <findings>發現 Sol role wording 仍允許直接寫 master／phase result，六個 phase file 清單也有同樣衝突；field-level provenance、recall no-match limitation、profile verification separation 與 Loop 2 狀態尚未足夠明確。</findings>
      <correction>已改為 Sol 只負責 reasoning、definition、read-only review、verification、gate 和 communication；所有 project-file writes 由同一 phase Luna 在 isolated worktree 執行，master result append 只可依 Sol 的 exact bounded content 寫入並經 Sol review。已補強 field-level provenance、recall 限制、分離 verification contexts，並完成本輪全文與 read-only checks。</correction>
    </review_loop>
    <review_loop id="3" status="completed_with_fixes" scope="entire_latest_document">
      <findings>發現 checksum wording 誤指不存在的 LoadReport 並可能誤用 external_batch_id；每個 phase 多出 phase_results tag；Phase 2 與 Phase 5 phase-local tests 未明示 AC-14；root、review 與 boundary status 仍停在 Loop 2。</findings>
      <correction>已改為使用 ImportBatch.idempotency_key 作 deterministic replay identity，external_batch_id 保留 source identity，checksum 留在 bundle manifest／bounded report artifact；移除六個 phase_results tags；補上 Phase 2 與 Phase 5 的 AC-14 preflight；更新三輪完成、ETL 尚未開始與 Phase 0 brief／新 Luna dispatch 的狀態。已完成從第一行到最後的全文複核與 read-only final document checks。</correction>
      <result>Loop 3 completed with the Must-fix corrections above；沒有開始 ETL implementation、source fetch、seed generation 或 database mutation。</result>
    </review_loop>
  </three_pass_review>

  <evidence_note>
    <verified>Phase 0 and Phase 1 live/offline/main evidence are verified；Phase 0 contract、coverage、provenance、truth-boundary、scope and checksum evidence remains recorded, and Phase 1 passed exact snapshot/main byte comparison, 72 focused tests, validators, reviewed-input checks, coherent reports, and both live source CLI runs。</verified>
    <planned>Phases 2–5 remain planned；no reference/demo bundle or database load exists yet。</planned>
    <next_action>Sol derives the Phase 2 self-contained brief from this master and current repository，then dispatches a NEW Luna；Phase 2 must use the Phase 1 checksummed artifacts without promoting reference facts to operational truth。</next_action>
  </evidence_note>
</evidence_backed_etl_plan>
```
