# Woolworths NZ × KiwiHarvest 食物分流研究

> **狀態：** Research only
> **資料快照日期：** 2026-08-08（Pacific/Auckland）
> **研究範圍：** Woolworths NZ surplus food、Auckland Woolworths 店點、KiwiHarvest FY25 與現行公開 recipient evidence、可供地圖研究的近似配送點、KiwiHarvest 營運地點與 truck parking 證據。
> **文件邊界：** 本文件不定義 implementation plan、database schema 或 AI agent 架構；只整理在設計前必須確認的事實、推論與未知項目。

## 1. Executive finding

1. 這個 problem statement 的主要使用者是 **KiwiHarvest driver／dispatcher**；driver 一般把食物送到 food bank、marae、community service、refuge、education service 或其他 recipient organisation，而不是直接替每位 consumer 規劃配送。KiwiHarvest 官網也明確表示不直接向公眾發放 food parcels。
2. Woolworths 的公開 case study 顯示，現有 StoreCentral 已能掃描無法銷售的商品、檢查 diversion eligibility、提示 Food Recovery Hierarchy、通知 partner 並記錄目的地。尚未公開確認的是 partner 的即時需要與容量、是否接受、實際取貨／交付、失敗後重新分流，以及 driver route。
3. 公開資料支持需要處理 fresh produce、bakery／deli、chilled、frozen、ambient／dry grocery 等 food-handling lanes；但 Woolworths NZ 沒有公開各類 waste 的頻率或比例，因此不能把「KiwiHarvest 可接收的類別」寫成「Woolworths 最常浪費的排名」。
4. Woolworths 官方 Store Locator API 在 AUK 區域回傳 **61 個 supermarket records**。本文件保留全部 61 個店點的官方地址與 GPS，並排除 liquor、pharmacy 的重複 records。
5. KiwiHarvest 公開列出 5 個現行 locations，其中 Auckland region 有 Highbrook／East Tāmaki 與 North Shore／Rosedale 兩個 operational sites。
6. 沒有可靠公開證據能確認每台 Auckland truck 的 home depot、固定 overnight parking bay 或 loading-dock GPS。Highbrook 與 Rosedale 可作為已確認的營運地點；把它們直接當成所有車輛的夜間停放點仍是未確認假設。
7. KiwiHarvest 沒有公開完整、即時的 2026 recipient master list；目前可取得的最完整官方名單是 **FY25 Annual Report 截至 2025-03-31 的 recipient snapshot**。本研究把 FY25 Auckland 名單與現行公開合作案例全部納入近似配送點研究，但不把 FY25 關係誤標成 2026 live relationship。
8. 「近似配送點」只表示可在研究地圖上代表該單位的安全公開點：通常是 current official service site、warehouse、school、church、marae 或 programme address。它不是已驗證的 loading bay、receiving entrance 或當日可收貨承諾；受保護服務只使用 suburb／service-area centroid 或 `protected/unknown`。
9. 公開 annual volume、weekly delivery、warehouse、fridge／freezer 或 NZFN Food Hub 身分只能證明歷史 throughput 或 static capability，不能證明 live capacity。點對點配對前仍需要帶時間戳的 current acceptance、food-type fit、可用容量與 receiving window。

## 2. Evidence examined

### 2.1 Brief 與 feature sources

- [Woolworths NZ Food Waste Diversion — Scenario Brief](https://app.notion.com/p/3b56c0b712f880c0b87cc01d2bec2d7f?pvs=204)
- [Woolworths Food Waste Platform Features](https://app.notion.com/p/3b56c0b712f8804b9e66c873d60af1cb?pvs=204)
- [Kai Commitment — Woolworths food waste diversion case study](https://kaicommitment.org.nz/wp-content/uploads/2024/07/Kai-Commitment_Case-Study-Woolworths.pdf)

### 2.2 Current operational and public data

- [Woolworths Store Locator service documentation](https://contact.woolworths.com.au/storelocator/service)
- [Woolworths official NZ Store Locator JSON](https://contact.woolworths.com.au/storelocator/service/corporateinfo/country/nz/division/all/tradinghours/current/weeks/1/json)
- [KiwiHarvest — Supermarkets](https://www.kiwiharvest.org.nz/supermarket)
- [KiwiHarvest — Donate food](https://www.kiwiharvest.org.nz/donatefood)
- [KiwiHarvest — Receive food](https://www.kiwiharvest.org.nz/receive-food)
- [KiwiHarvest — Contact and locations](https://www.kiwiharvest.org.nz/contact-us)
- [KiwiHarvest — Auckland branch](https://www.kiwiharvest.org.nz/auckland-branch)
- [KiwiHarvest — Annual reports](https://www.kiwiharvest.org.nz/annual-reports)
- [KiwiHarvest Annual Report 2025](https://www.kiwiharvest.org.nz/s/2025-KiwiHarvest_AnnualReport-Final.pdf)
- [KiwiHarvest — More Than Food](https://www.kiwiharvest.org.nz/blogs/more-than-food-how-kiwiharvest-empowers-charities-to-change-lives-across-new-zealand)
- [KiwiHarvest — Nourishing Communities](https://www.kiwiharvest.org.nz/blogs/nourishing-communities-the-positive-impact-of-food-support-from-kiwiharvestnbsp)
- [New Zealand Food Network — Food Hubs](https://www.nzfoodnetwork.org.nz/our-food-hubs/)

### 2.3 Food-safety and barcode sources

- [MPI — Donations of food from commercial sources](https://www.mpi.govt.nz/dmsdocument/3783/send)
- [MPI — How to read food labels](https://www.mpi.govt.nz/food-safety-home/how-read-food-labels)
- [MPI — Reducing food waste: tips for businesses](https://www.mpi.govt.nz/food-business/running-a-food-business/reducing-food-waste-tips-for-businesses)
- [MPI — Food packaging rules and guidance](https://www.mpi.govt.nz/food-business/food-packaging-rules-and-guidance)
- [GS1 New Zealand — Woolworths NZ 2D barcodes](https://www.gs1nz.org/member-stories/woolworths-nz-2d-barcodes)

### 2.4 Evidence labels used below

| Label | Meaning |
| --- | --- |
| **Confirmed** | Current official source or supplied brief directly supports the claim. |
| **FY25 snapshot** | KiwiHarvest Annual Report 2025 supports the relationship for the year ended 2025-03-31; it is not a 2026 live confirmation. |
| **Historical** | An older report supports a past relationship or location only. |
| **Inference** | Reasonable conclusion drawn from confirmed facts, but not directly confirmed by the organisation. |
| **Unknown** | Public evidence is absent, stale, conflicting or insufficient for operational use. |

Location labels are separate from relationship labels:

| Location label | Meaning |
| --- | --- |
| **Public approximate point** | A safe, source-backed public point representing the organisation or programme for map research. |
| **Area centroid** | A suburb or service-area point used only because an exact location is protected or no fixed public venue is available. |
| **Protected／unknown** | No coordinate should be published or the public evidence is too weak to select a point. |
| **Operator-confirmed delivery point** | The actual receiving entrance or loading point has been confirmed by the recipient or KiwiHarvest. No public record in this research currently meets this standard. |

### 2.5 Recipient-location research method

1. The KiwiHarvest 2025 Annual Report recipient pages were visually checked, and the Auckland-identifiable FY25 names were transcribed without treating them as a current 2026 roster.
2. Each name was searched against its current official organisation site first. Charities Services, Family Services Directory, Healthpoint, Auckland Council, school／church／marae sites and established foodbank directories were used when the organisation did not publish enough location information.
3. The selected point follows this preference order: current named warehouse or food-service site → current public branch／programme point → current public office → safe programme proxy → suburb／service-area centroid → unknown.
4. Public addresses were converted to WGS84 latitude／longitude with ArcGIS World Geocoding Service, OpenStreetMap Nominatim or a map point embedded by the official source. A coordinate was rejected or downgraded when the geocoder dropped a unit suffix, returned a different street number or only resolved a campus／intersection.
5. Refuge, safe-house and transitional-housing residential addresses were not reverse-searched or reproduced. Only a public network office or coarse published locality is used.
6. Every selected point remains a public approximation. No source search can substitute for recipient confirmation of the receiving entrance, access, time window, storage or live capacity.

## 3. Confirmed current state

### 3.1 Current Woolworths diversion context

The supplied brief and Kai Commitment case study describe the following existing flow:

1. A Woolworths team member identifies an item that can no longer be sold.
2. StoreCentral scans the item and checks diversion eligibility.
3. The system prompts the highest available option in the Food Recovery Hierarchy: people, animals, nutrient recovery, then landfill.
4. A local diversion partner is alerted.
5. The destination is recorded and reported through dashboards or store scorecards.

This confirms scanning, eligibility guidance, partner alerting and reporting. It does **not** confirm that public APIs expose the following operational data:

- partner acceptance or rejection;
- current recipient need and storage capacity;
- actual quantity collected and delivered;
- pickup window, loading time or delivery deadline;
- driver, vehicle, route, truck capacity or overnight parking;
- failed-pickup rerouting;
- StoreCentral product or event integration contract.

GS1 New Zealand separately confirms that Woolworths-brand fresh meat in the North Island has adopted 2D barcodes that can carry batch／lot, best-before／use-by and weight. This evidence is product- and rollout-specific; it does not mean every Woolworths product barcode contains those attributes.

### 3.2 Publicly supported surplus food categories

The table below describes **supported operational categories**, not a Woolworths waste-frequency ranking.

Historical Countdown food-rescue reporting directly mentioned produce, bread, bakery and other perishable groceries. Current Woolworths reporting also recognises fresh produce, meat, chilled and frozen as retail categories, while KiwiHarvest’s current supermarket guidance confirms which broad surplus categories it can collect. Taken together, this supports the operational categories below, but still does not reveal which category is most commonly wasted in 2026.

| Food category | Publicly supported surplus situations | Relevant characteristics | Main handling or matching constraint |
| --- | --- | --- | --- |
| Fresh fruit and vegetables | Overstock, over-ordering, cosmetically imperfect produce, short usable life, damaged outer packaging while food remains fit | Produce type, quantity／weight, maturity, visible spoilage, contamination, cut／uncut state, packaging, usable time window | Fast distribution; some items need chilled storage while others do not |
| Bread and bakery | Short-dated bread, bakery surplus, unopened packaged bakery products | Baked-on／baked-for or best-before date, quantity, allergens, packaging, prepared time | Very short distribution window; date type differs from use-by |
| Deli and ready-to-eat | Unopened deli products, sandwiches, wraps, grab-and-go food prepared safely | Prepared time, use-by, allergens, sealed／opened, previously served, chilled state | Opened, previously served or spoiled food is not accepted; cold chain may be required |
| Chilled dairy, meat and seafood | Short-dated sealed chilled products, overstock or deleted lines | Raw／cooked／ready-to-eat, use-by or best-before, lot／batch, temperature, packaging, weight, recall state | Chilled donation must remain at or below 5°C; raw and ready-to-eat food must remain separated |
| Frozen food | Sealed frozen surplus, overstock, deleted lines or safely frozen eligible meat | Frozen state, evidence of thawing, package integrity, date mark, lot／batch, quantity | Must remain frozen; recipient needs freezer capacity |
| Ambient and dry grocery | Sealed cans, jars, rice, pasta, snacks, beverages and other shelf-stable goods | Best-before／use-by, lot／batch, label, allergens, leakage, rust, swelling, case／pallet quantity | Easier storage, but damaged seals, leaking or swollen containers remain unsafe |

KiwiHarvest states that it can collect ambient, fresh and frozen food, including prepared food, and that matching considers recipient need, storage capacity and service type. Its supermarket guidance accepts short-dated food, deleted lines, overstock, cosmetically imperfect produce and damaged-but-sealed packaging, but rejects opened, previously served or spoiled food.

### 3.3 Food characteristics that the research says matter

Barcode identity and the state of a particular donation are different evidence layers.

| Evidence layer | Characteristics available or required | Why barcode alone is insufficient |
| --- | --- | --- |
| Product identity | GTIN, brand, product name, variant, category, pack size, ingredients, allergens, storage instruction, raw／cooked／ready-to-eat | A conventional retail barcode primarily identifies the trade item; it does not describe the physical condition of a particular unit |
| Lot or date identity | Lot／batch, production or pack date, best-before, use-by, baked-on／baked-for, variable weight | Some GS1 2D barcodes can carry these fields, but coverage is not universal |
| Donation quantity | Units, cases, pallets, actual weight, available quantity | Quantity changes for every donation event and is not implied by GTIN |
| Physical condition | Sealed, opened, damaged outer packaging, leaking, swollen, mouldy, contaminated, previously served, thawed | These are observations of the actual food |
| Food-safety state | Temperature reading and time, cold-chain break, recall check, raw／ready-to-eat separation | These depend on handling events and external recall data |
| Pickup operation | Store, identified time, safe deadline, pickup window, handoff point, loading restriction | These are location and workflow events |
| Recipient suitability | Current need, accepted categories, chilled／frozen capacity, kitchen capability, maximum intake, service area, receiving hours | These belong to the receiving organisation and change over time |

Key confirmed rules:

- **Use-by** is a safety date; food must not be donated after it.
- **Best-before** mainly concerns quality; food may still be eligible only if it remains fit to eat.
- Chilled donated food should remain at or below **5°C**.
- Frozen food should remain frozen.
- Raw food must be separated from cooked or ready-to-eat food.
- Original labels and necessary storage information must remain available.
- Damaged outer packaging is not automatically a rejection if the food remains sealed, but exposed, leaking, badly rusted or swollen packaging is unsafe.
- Recalled food and opened, previously served or spoiled food must not enter the donation flow.

### 3.4 Auckland Woolworths supermarket locations

#### Method and scope

- Source: Woolworths official Store Locator JSON, retrieved 2026-08-08.
- Filter: storeDetail.division equals COUNTDOWN and storeDetail.state equals AUK.
- Result: **61 supermarket records**.
- Excluded: 61 COUNTDOWN_LIQUOR and 20 COUNTDOWN_PHARMACY records, which otherwise duplicate supermarket locations or represent a different operational unit.
- The API still uses the internal division label COUNTDOWN even where the public store name is Woolworths.
- GPS values below are the API latitude and longtitude values. The source itself spells the longitude field “longtitude”.
- Coordinates are address/store centroids at the source precision; they are not loading-bay, service-entry or truck-parking coordinates.
- Postcodes below are displayed as four digits where the API serialises a leading-zero postcode as a number.

| # | Store no. | Store | Address | GPS: latitude, longitude |
| ---: | ---: | --- | --- | --- |
| 1 | 9428 | Auckland Airport Woolworths | Cnr Georgebolt Memorial & Cnr John Goulter Dr, Mangere 2022 | -36.9976, 174.7890 |
| 2 | 9094 | Auckland City Woolworths | 76 Quay Street, Auckland 1010 | -36.8450, 174.7730 |
| 3 | 9177 | Beachlands Woolworths | 129 Beachlands Rd, Beachlands 2018 | -36.8898, 175.0083 |
| 4 | 9145 | Birkenhead Woolworths | Cnr Highbury Pass & Birkenhead Ave, Birkenhead 0626 | -36.8113, 174.7248 |
| 5 | 9141 | Botany Downs Woolworths | Cnr Te Irirangi & Ti Rakau Drives, Botany Downs 2010 | -36.9299, 174.9112 |
| 6 | 9224 | Browns Bay Woolworths | Cnr Anzac & Clyde Rds, Browns Bay 0630 | -36.7175, 174.7474 |
| 7 | 9163 | Glenfield Woolworths | Glenfield Mall, Bentley Ave, Glenfield 0629 | -36.7818, 174.7229 |
| 8 | 9128 | Greenlane Woolworths | 326 Great South Road, Greenlane, Auckland 1051 | -36.8893, 174.7937 |
| 9 | 9171 | Greville Road Woolworths | 65 Greville Road, Pinehill 0632 | -36.7309, 174.7222 |
| 10 | 9068 | Grey Lynn Woolworths | 271 Richmond Rd, Grey Lynn, Auckland 1022 | -36.8546, 174.7318 |
| 11 | 9534 | Helensville Woolworths | 43 Commercial Road, Helensville 0800 | -36.6772, 174.4506 |
| 12 | 9194 | Henderson Woolworths | West City Shopping Centre, 7 Catherine Street, Henderson 0612 | -36.8808, 174.6328 |
| 13 | 9142 | Highland Park Woolworths | 507 Pakuranga Road, Highland Park 2010 | -36.8995, 174.9082 |
| 14 | 9551 | Hobsonville Woolworths | 124 Hobsonville Road, Hobsonville 0618 | -36.7974, 174.6474 |
| 15 | 9243 | Howick Woolworths | 35 Cook St, Howick 2014 | -36.8959, 174.9328 |
| 16 | 9146 | Kelston Woolworths | Cnr Great North & West Coast Road, Glen Eden 0602 | -36.9096, 174.6635 |
| 17 | 9038 | Lincoln Road Woolworths | 185–187 Universal Drive, Henderson 0610 | -36.8569, 174.6314 |
| 18 | 9140 | Lynfield Woolworths | 570 Hillsborough Road, Lynfield 1041 | -36.9256, 174.7231 |
| 19 | 9149 | Lynnmall Woolworths | Lynnmall Shopping Centre, Great North Road, New Lynn 0600 | -36.9073, 174.6843 |
| 20 | 9248 | Mairangi Bay Woolworths | 3 Ramsgate Terrace, Mairangi Bay 0630 | -36.7390, 174.7526 |
| 21 | 9486 | Mangere East Woolworths | 359 Massey Rd, Mangere 2024 | -36.9667, 174.8251 |
| 22 | 9096 | Manukau City Mall Woolworths | Shop 99 Manukau City Centre, Cnr Great South & Wiri Station Rds, Manukau 2104 | -36.9929, 174.8822 |
| 23 | 9161 | Manukau Woolworths | 652 Great South Road, Manukau 2104 | -36.9870, 174.8838 |
| 24 | 9400 | Manurewa Woolworths | 227 Browns Road, Manurewa 2102 | -37.0177, 174.8649 |
| 25 | 9444 | Meadowbank Woolworths | 35–47 St Johns Road, Meadowbank 1072 | -36.8759, 174.8276 |
| 26 | 9458 | Meadowlands Woolworths | Cnr Meadowlands Drive & Whitford Road, Howick 2014 | -36.9135, 174.9290 |
| 27 | 9437 | Metro Albert Street Woolworths | AMP Centre, Ground Floor, Auckland 1010 | -36.8436, 174.7654 |
| 28 | 9283 | Metro Auckland Victoria Street West | 19–25 Victoria Street, Auckland 1010 | -36.8486, 174.7647 |
| 29 | 9435 | Metro Halsey Street | 104 Pakenham Street West, Auckland Central 1010 | -36.8432, 174.7554 |
| 30 | 9249 | Metro Herne Bay | 1 Kelmarna Avenue, Herne Bay 1011 | -36.8465, 174.7335 |
| 31 | 9198 | Milford Woolworths | Milford Shopping Centre, Milford Rd, Milford 0620 | -36.7720, 174.7661 |
| 32 | 9235 | Mount Eden Woolworths | Cnr Valley & Dominion Roads, Mt Eden, Auckland 1024 | -36.8773, 174.7516 |
| 33 | 9034 | Mount Roskill Woolworths | 112 Stoddard Road, Mt Roskill, Auckland 1041 | -36.9042, 174.7270 |
| 34 | 9193 | Mount Wellington Woolworths | Cnr Penrose Rd & Mt Wellington Hway, Mt Wellington 1060 | -36.9094, 174.8372 |
| 35 | 9405 | Newmarket Woolworths | Level 3, Westfield Newmarket, 277 Broadway, Newmarket 1023 | -36.8719, 174.7763 |
| 36 | 9477 | Northcote Woolworths | Pearn Crescent, Northcote 0627 | -36.8003, 174.7448 |
| 37 | 9064 | Northwest Woolworths | 7 Fred Taylor Drive, Northwest Town Centre, Westgate, Massey 0814 | -36.8197, 174.6113 |
| 38 | 9091 | Onehunga Woolworths | Cnr Church St & Selwyn St, Onehunga, Auckland 1061 | -36.9231, 174.7832 |
| 39 | 9061 | Orewa Woolworths | Moenui Avenue, Orewa 0931 | -36.5883, 174.6961 |
| 40 | 9204 | Pakuranga Woolworths | Pakuranga Town Centre, Pakuranga 2010 | -36.9130, 174.8686 |
| 41 | 9144 | Papakura Woolworths | 2 Averill Street, Papakura 2110 | -37.0636, 174.9442 |
| 42 | 9106 | Papatoetoe Woolworths | Hunters Plaza, 217 Great South Rd, Papatoetoe 2025 | -36.9710, 174.8605 |
| 43 | 9057 | Ponsonby Woolworths | 4 Williamson Ave, Ponsonby 1021 | -36.8585, 174.7489 |
| 44 | 9123 | Pt Chevalier Woolworths | 13 Pt Chevalier Road, Point Chevalier, Auckland 1022 | -36.8698, 174.7102 |
| 45 | 9107 | Pukekohe South Woolworths | 186–192 Manukau Rd, Pukekohe 2120 | -37.2106, 174.9113 |
| 46 | 9199 | Pukekohe Woolworths | Cnr Tobin & Seddon Sts, Pukekohe 2120 | -37.1996, 174.9022 |
| 47 | 9014 | Roselands Mall Woolworths | 90–96 Great South Road, Papakura 2110 | -37.0589, 174.9412 |
| 48 | 9504 | Silverdale Woolworths | 40 Hibiscus Coast Highway, Silverdale 0932 | -36.6139, 174.6807 |
| 49 | 9521 | St Johns Woolworths | 130–140 Felton Mathew Avenue, St Johns 1072 | -36.8794, 174.8520 |
| 50 | 9216 | St Lukes Woolworths | Saint Lukes Shopping Centre, Cnr St Lukes Rd & Morningside Dr, Mt Albert, Auckland 1025 | -36.8838, 174.7342 |
| 51 | 9197 | Sunnynook Woolworths | Cnr Sycamore Dr & Sunnynook Rd, Sunnynook 0620 | -36.7590, 174.7408 |
| 52 | 9202 | Takanini Woolworths | 228 Great South Road, Takanini 2112 | -37.0476, 174.9271 |
| 53 | 9237 | Takapuna Woolworths | Barry's Point Road, Takapuna 0622 | -36.7913, 174.7655 |
| 54 | 9206 | Te Atatu South Woolworths | Cnr Edmonton & Te Atatu Roads, Te Atatu South 0610 | -36.8657, 174.6463 |
| 55 | 9451 | Te Atatu Woolworths | 583 Te Atatu Road, Te Atatu Peninsula 0610 | -36.8426, 174.6525 |
| 56 | 9529 | Three Kings Woolworths | 532 Mt Albert Road, Three Kings, Auckland 1042 | -36.9093, 174.7551 |
| 57 | 9464 | Waiata Shores Woolworths | 2 Periko Way, Takanini 2112 | -37.0360, 174.9057 |
| 58 | 9030 | Waiheke Island Woolworths | 13–19 Belgium St, Waiheke Island, Ostend 1081 | -36.7950, 175.0459 |
| 59 | 9533 | Warkworth Woolworths | 20–26 Neville Street, Warkworth 0910 | -36.3995, 174.6643 |
| 60 | 9147 | Westgate Woolworths | Westgate Shopping Centre, Cnr Westgate & Fern Hill Drive, Massey 0614 | -36.8209, 174.6141 |
| 61 | 9242 | Whangaparaoa Woolworths | Cnr Whangaparaoa & Wade Drive, Whangaparaoa 0943 | -36.6365, 174.7466 |

The official API itself contains some spelling and address-quality limitations. For example, Auckland Airport is returned as “Georgebolt Memorial”; this document preserves the source wording instead of silently substituting an unverified address. Before live routing, service entrances and loading restrictions still require store-level confirmation.

### 3.5 Recipient organisation landscape

#### Recipient role matters

The public evidence does not support treating every destination as the same kind of “consumer”.

| Role | Function in the food flow | Examples | Routing implication |
| --- | --- | --- | --- |
| Food rescue operator | Collects surplus food, may sort or cross-dock it, then distributes it onward | KiwiHarvest, Fair Food, Kaibosh | May be a depot or intermediate stop, not the final community destination |
| Bulk distribution hub | Receives pallet or case-scale food and redistributes it to local agencies | NZ Food Network distribution centre and Food Hubs | Suitable for large mixed loads only if current intake and storage capacity are confirmed |
| Frontline food support | Provides food parcels, social supermarket access or emergency support | Auckland City Mission, MUMA, Salvation Army services, Visionwest | Public service address may differ from donor receiving dock |
| Meal or community-kitchen provider | Converts food into meals or distributes ready-to-eat food | Supreme Sikh Society, Vinnies Kitchen, some churches and marae | Needs preparation capability, allergen information and a short safe-use window |
| Residential or specialist service | Supports housing, refugees, women, older people, youth or alternative education | Island Child, ASST, women’s refuges, elderly services | Address may be private; needs, dietary constraints and delivery windows can be sensitive |

KiwiHarvest states that it supports **235 recipient organisations nationwide** and lists food banks, marae, elderly services, women’s refuges and alternative education among recipient types. It does not directly provide food parcels to the public. Its current page also says the Auckland branch is at maximum recipient capacity. This means a public list of charities is not equivalent to a route-ready KiwiHarvest recipient list.

#### Point-to-point recipient scope decision

For the static research map, this document counts **all 54 Auckland-identifiable names in KiwiHarvest’s FY25 recipient list** and **all nine current-public Auckland relationship names** as candidate delivery units. Three current-public names also appear in FY25, producing **60 distinct candidate identities**. Public evidence supports a safe approximate point for 58; Hapori Tautua Collective and The Koha Shed – West Auckland remain `unknown` rather than receiving invented coordinates.

| Point-to-point node set | Count | Location readiness |
| --- | ---: | --- |
| KiwiHarvest Auckland operational branch points | 2 | Highbrook and Rosedale public branch centroids; vehicle assignment unknown |
| Woolworths Auckland-region supermarket points | 61 | Official store centroids; loading entrances unknown |
| Distinct FY25／current-public recipient candidate identities | 60 | 58 have a safe approximate point; 2 remain unknown |
| Operator-confirmed recipient delivery points | 0 | Requires KiwiHarvest or recipient confirmation |

The FY25 source is the [2025 Annual Report](https://www.kiwiharvest.org.nz/s/2025-KiwiHarvest_AnnualReport-Final.pdf), printed pp. 27–28／PDF pp. 29–30. Its reporting period ended **2025-03-31**. Therefore:

- every FY25 row is included as a point-to-point research candidate;
- only a separate current KiwiHarvest source can upgrade the relationship to `current-public`;
- a current organisation website can update the public map point, but does not by itself prove a current KiwiHarvest relationship;
- no row is an operator-confirmed receiving entrance.

Point classes used below:

| Code | Point meaning | Navigation use |
| --- | --- | --- |
| `A` | Current public address or named site | Map display only; entrance unconfirmed |
| `I` | Intersection, campus or multi-unit site | Map display only; lower precision |
| `S` | Suburb／service-area centroid, including protected services | Non-navigable scenario point |
| `H` | Historical, former, proxy or materially ambiguous public point | Non-navigable until re-confirmed |
| `U` | No defensible public point | No route line should be created |

#### Current-public KiwiHarvest Auckland relationships

“Current-public” means a current KiwiHarvest page or a currently published organisation page directly describes the relationship. It does not prove same-day acceptance or an operational delivery address.

| ID | Organisation／unit | Relationship evidence | Selected public approximate point | WGS84 latitude, longitude | Class | Operational caveat |
| --- | --- | --- | --- | --- | --- | --- |
| CUR-01 | Asylum Seekers Support Trust | Current [KiwiHarvest recipient story](https://www.kiwiharvest.org.nz/receive-food); 31,590 kg reported for 2024-04-01–2025-03-31 | [ASST office](https://asst.org.nz/contact-us/), 875 New North Road, Mount Albert 1025 | -36.883540, 174.716225 | A | Official site and Charities Register have conflicting addresses; office is not a confirmed food dock |
| CUR-02 | Island Child Charitable Trust | Current [KiwiHarvest recipient story](https://www.kiwiharvest.org.nz/receive-food); weekly delivery case | Point England suburb centroid; exact transitional-housing site suppressed | -36.883960, 174.864700 | S | Protected, non-navigable; real destination requires controlled data |
| CUR-03 | Good Care Community Trust | Current [Auckland branch testimonial](https://www.kiwiharvest.org.nz/auckland-branch) describes regular food-pallet delivery | [Public office](https://www.goodcarecommunitytrust.co.nz/contact), Suite 4, 129 Great South Road, Papatoetoe 2025 | -36.968729, 174.859629 | A | Pallet relationship is evidenced, but delivery to this office is not |
| CUR-04 | Hapori Tautua Collective | Current [Auckland branch testimonial](https://www.kiwiharvest.org.nz/auckland-branch) describes continued partnership | Unknown | — | U | No independently verifiable public site or locality found |
| CUR-05 | Māngere Budgeting Services Trust／Tātou Social Supermarket | Current [Auckland branch testimonial](https://www.kiwiharvest.org.nz/auckland-branch) and [Tātou page](https://www.mbst.org.nz/tatou-social-supermarket) | [Ōtāhuhu branch](https://www.mbst.org.nz/otahuhu-branch), 33A Walmsley Road, Ōtāhuhu 1061 | -36.948191, 174.834392 | A | Public evidence conflicts with the Māngere branch at 93 Bader Drive; neither is a confirmed KiwiHarvest receiving point |
| CUR-06 | Kootuitui ki Papakura | Current-published [KiwiHarvest impact case](https://www.kiwiharvest.org.nz/blogs/more-than-food-how-kiwiharvest-empowers-charities-to-change-lives-across-new-zealand) describes weekly kai | [Financial Wellbeing office](https://kootuitui.org.nz/contact/), 29 Broadway, Papakura 2110 | -37.062879, 174.943819 | A | Papakura High School is an alternate public office site; the case does not identify which site receives food |
| CUR-07 | We o Tara／Accelerating Aotearoa | [KiwiHarvest case](https://www.kiwiharvest.org.nz/blogs/nourishing-communities-the-positive-impact-of-food-support-from-kiwiharvestnbsp), dated 2024-12-02 | [Public community hub](https://www.healthpoint.co.nz/community-health-and-social-services/social/accelerating-aotearoa/at/40a-lovegrove-crescent-otara-auckland/), 40A Lovegrove Crescent, Ōtara 2023 | -36.959301, 174.877798 | I | Unit number varies across public records; service hours are not receiving hours |
| CUR-08 | Windsor Park Baptist Church | Current [church partnership page](https://www.windsorpark.org.nz/food-support/) and [KiwiHarvest case](https://www.kiwiharvest.org.nz/blogs/nourishing-communities-the-positive-impact-of-food-support-from-kiwiharvestnbsp) | [Church](https://www.windsorpark.org.nz/contact), 550 East Coast Road, Mairangi Bay 0630 | -36.738378, 174.741057 | A | Wednesday public distribution does not identify truck receiving entrance or capacity |
| CUR-09 | Women’s Refuge Auckland network | Current [Auckland branch](https://www.kiwiharvest.org.nz/auckland-branch) distribution statement | [Women’s Refuge Tāmaki Makaurau public office](https://womensrefugetamaki.org.nz/), Level 1, Unit 3, 322 New North Road, Kingsland | -36.868950, 174.751710 | A | This is a public network office, never a proxy for safe houses; all protected deliveries require controlled routing |

MBST has a second plausible public point at Shop 8B, Māngere Town Centre, 93 Bader Drive (`-36.969104, 174.799635`). Kootuitui has a second public office at Papakura High School, Willis Road (`-37.063244, 174.951006`). Both alternatives remain unconfirmed as KiwiHarvest receiving sites.

#### Complete FY25 Auckland candidate roster and approximate points

Every row below is a **FY25-snapshot candidate delivery unit**. `Current status` describes only what could be established from public sources by 2026-08-08; it does not upgrade the KiwiHarvest relationship.

| # | FY25 report name | Selected safe public approximation | WGS84 latitude, longitude | Class | Current-status evidence／note |
| ---: | --- | --- | --- | --- | --- |
| 1 | ATC Vision College - Papakura Campus | Level 4, 34 East Street, Papakura 2110 | -37.064046, 174.941950 | A | Current [Vision College Auckland campus](https://visioncollege.ac.nz/about-us/campuses/auckland/); campus, not receiving entrance |
| 2 | Auckland Women’s Centre - Single Mum’s Group | 4 Warnock Street, Grey Lynn | -36.858923, 174.729809 | A | Current programme is [Solo Mums on Sundays](https://awc.org.nz/classes/single-mums-on-sundays/) |
| 3 | Auckland Women’s Refuge | Level 1, Unit 3, 322 New North Road, Kingsland | -36.868950, 174.751710 | A | Current [Women’s Refuge Tāmaki Makaurau](https://womensrefugetamaki.org.nz/) public office; never a safe-house point |
| 4 | Awataha Marae | 58 Akoranga Drive, Northcote | -36.794950, 174.755950 | A | Current [Awataha Marae](https://www.awataha.co.nz/) public marae site |
| 5 | Baverstock Oaks School | 21 Baverstock Road, Flat Bush | -36.955740, 174.913440 | A | Current [school](https://www.baverstock.school.nz/) campus |
| 6 | Beachhaven Food Bank | Cedar Centre foodbank proxy, 56A Tramway Road, Beach Haven | -36.792710, 174.689710 | H | FY25 entity continuity unconfirmed; [Cedar Centre](https://www.cedarcentre.org.nz/contact) is a current local foodbank, not proven successor |
| 7 | Blue Light Otara | Ormiston Police Station programme point, 50 Ormiston Road, Ōtara | -36.962458, 174.896944 | I | Current [Blue Light branch network](https://bluelight.co.nz/about/blue-light-branches/); not a receiving site |
| 8 | Blue Light Papakura | Blue Light Youth Centre, 159 Dominion Road, Red Hill, Papakura | -37.067630, 174.965564 | A | Current [Blue Light Youth Centre](https://bluelight.co.nz/blue-light-youth-centre/) |
| 9 | C3 Cares Albany | Albany suburb centroid | -36.716670, 174.700000 | S | C3 Cares programme remains visible through [Belong Church](https://belongchurch.org.nz/giving), but no Albany delivery site was verified |
| 10 | CAB Glen Innes Foodbank | 96 Line Road, Glen Innes | -36.878820, 174.857510 | A | Current [Healthpoint service listing](https://kiosk.healthpoint.co.nz/community-health-and-social-services/social/citizens-advice-bureau-cab-glen-innes/); older sources also show 100 Line Road |
| 11 | Church Unlimited Auckland City Campus | Ground Floor, 2A Augustus Terrace, Parnell | -36.850868, 174.776508 | A | Current [foodbank listing](https://www.foodbank.co.nz/church-unlimited-auckland-city) |
| 12 | Everybody Eats Glen Innes | 133 Line Road, Glen Innes | -36.878330, 174.856460 | A | Current [Everybody Eats location](https://everybodyeats.nz/dine-with-us) |
| 13 | Everybody Eats Onehunga | 306 Onehunga Mall, Onehunga | -36.919140, 174.784670 | A | Current [Everybody Eats Onehunga](https://www.everybodyeats.nz/dine-with-us/onehunga-auck) |
| 14 | Feed the Streets (Kai Avondale) | Avondale Community Centre, 99 Rosebank Road | -36.894150, 174.694900 | A | Current [Kai Avondale](https://www.iloveavondale.co.nz/kaiavondale) programme point |
| 15 | Genesis Youth Trust - Glen Innes | Corner Taniwha Street and Line Road, Glen Innes | -36.879000, 174.859000 | I | Current [Genesis contact](https://www.genesis.org.nz/contact); intersection precision |
| 16 | Genesis Youth Trust - Mangere | 92 Bader Drive, Māngere 2022 | -36.967347, 174.798129 | A | Current [Genesis head office](https://www.genesis.org.nz/contact) |
| 17 | Genesis Youth Trust - Manurewa | 169 Great South Road, Manurewa | -37.021088, 174.895370 | H | Current organisation exists, but this [local directory point](https://manurewabusiness.co.nz/listing/genesis-youth-trust/) geocodes to 169A; re-confirm before use |
| 18 | Grandparents raising Grandchildren Trust NZ - Papakura Support Group | Papakura suburb centroid | -37.064265, 174.944667 | S | Current [government service listing](https://www.familyservices.govt.nz/directory/viewprovider.htm?id=24002&pageNumber=165&pageSize=10&searchRegion=2); no fixed public venue |
| 19 | Howick College | 25 Sandspit Road, Cockle Bay | -36.907690, 174.938340 | A | Current [school](https://www.howickcollege.school.nz/contact) campus |
| 20 | Island Child Charitable Trust | Point England suburb centroid | -36.883960, 174.864700 | S | Current [organisation](https://islandchild.org.nz/about-us/) and KiwiHarvest case; protected transitional-housing location |
| 21 | Kootuitui ki Papakura | 29 Broadway, Papakura 2110 | -37.062879, 174.943819 | A | Current [financial wellbeing office](https://kootuitui.org.nz/contact/); actual food site unconfirmed |
| 22 | Mairangi Bay Community Church | 49 Maxwelton Drive, Mairangi Bay | -36.741620, 174.747050 | A | Current [church](https://www.mairangichurch.org.nz/) public address |
| 23 | Mangere Budgeting Services Trust | 33A Walmsley Road, Ōtāhuhu 1061 | -36.948191, 174.834392 | A | Current [MBST branch](https://www.mbst.org.nz/otahuhu-branch) and Tātou candidate; 93 Bader Drive remains an alternate |
| 24 | Manukau City Baptist Church | 9 Lambie Drive, Papatoetoe | -36.985630, 174.870284 | A | Current [church](https://www.citybaptist.org.nz/about-us) public site |
| 25 | Manukau Institute of Technology - SSTS | Gate 11A, 54 Ōtara Road, Ōtara | -36.955402, 174.871392 | I | Current [MIT SSTS](https://www.manukau.ac.nz/about/partnerships/school-of-secondary-tertiary-studies/faqs/) programme site |
| 26 | Manurewa Soup Kitchen | Manurewa suburb centroid | -37.021281, 174.897148 | S | [Auckland Council recorded 2025 activity](https://infocouncil.aucklandcouncil.govt.nz/Open/2025/06/20250619_MR_MIN_12956.htm), but no fixed current venue was verified |
| 27 | North Shore Women’s Centre | Former office, 5 Mayfield Road, Glenfield | -36.778050, 174.722460 | H | [Official closure notice](https://nswomenscentre.org.nz/about-us/) says permanently closed on 2025-11-28 |
| 28 | Onehunga Community Embracing Families and Homeless in Need | St Peter’s Church, 184 Onehunga Mall | -36.922560, 174.784930 | A | Current programme name is Onehunga Embracing Families; [church venue](https://aucklandanglican.org.nz/find-a-church/st-peters-onehunga/) |
| 29 | Otahuhu Maori Wardens | Public district-base proxy, 13 Inverell Avenue, Wiri | -37.001415, 174.885374 | H | Current [regional network](https://maoriwardens.nz/te-taitokerau-tamaki-tamaki-ki-te-tonga/) does not publish an Ōtāhuhu fixed site |
| 30 | Papakura Marae | 29 Hunua Road, Papakura 2110 | -37.070078, 174.959078 | A | Current [Papakura Marae](https://www.papakuramarae.co.nz/) public site |
| 31 | Reconnect Family Services Manukau | 8 Puhinui Road, Manukau 2104 | -36.984557, 174.867670 | H | Current [head-office address](https://reconnect.org.nz/contact-us/), but geocode candidate has unit-number ambiguity |
| 32 | Reconnect Family Services New Lynn | 15 Puriri Street, New Lynn | -36.909320, 174.688550 | A | Current [Reconnect contact](https://reconnect.org.nz/contact-us/) |
| 33 | Ronald McDonald House Auckland | Building 11, 2 Park Road, Grafton | -36.858200, 174.771810 | I | Current [Auckland House](https://rmhc.org.nz/stay-with-us/auckland-house/) hospital-campus point |
| 34 | Roskill South Oasis | 56 Glass Road, Mount Roskill | -36.926500, 174.737500 | A | Current [community-service listing](https://www.adcoss.org.nz/item/roskill-south-oasis/) |
| 35 | Ruapotaka Marae Incorporated Society | Ruapōtaka Marae, 106 Line Road, Glen Innes | -36.879440, 174.856940 | A | Current [marae evidence](https://www.tekaupapa.maori.nz/ruapotaka-marae) |
| 36 | Shine Mt Albert | Mount Albert area centroid | -36.883330, 174.716670 | S | Protected [Shine family-violence service](https://2shine.org.nz/what-we-do/advocacy); not a refuge address |
| 37 | Shine North Shore | North Shore area centroid | -36.800000, 174.750000 | S | Current [Shine advocacy](https://2shine.org.nz/what-we-do/advocacy) mentions North Shore but no separate public office |
| 38 | South Auckland Family Refuge Papatoetoe | Ōtāhuhu suburb centroid | -36.938200, 174.840190 | S | Current [refuge service](https://www.healthpoint.co.nz/community-health-and-social-services/refuge/south-auckland-family-refuge/); protected and non-navigable |
| 39 | St Columba Anglican Church Grey Lynn | 92 Surrey Crescent, Grey Lynn | -36.862710, 174.733680 | A | Current [Anglican parish](https://aucklandanglican.org.nz/find-a-church/st-columba-grey-lynn/) |
| 40 | Strive Community Trust Manurewa | Current office, 294A Massey Road, Māngere | -36.962546, 174.830390 | H | Current [STRIVE office](https://www.strive.org.nz/contact/); no current Manurewa-specific site found |
| 41 | Te Whare Aio - Manurewa Women’s Refuge | Manurewa suburb centroid | -37.018200, 174.880190 | S | Current [refuge service](https://www.healthpoint.co.nz/community-health-and-social-services/refuge/te-whare-aio-maori-womens-refuge/); protected and non-navigable |
| 42 | Te Whare Marama O Mangere Women’s Refuge | Māngere suburb centroid | -36.968070, 174.798750 | H | Historical protected locality; [provider approval revoked](https://gazette.govt.nz/notice/id/2025-go2463) effective 2025-05-05 |
| 43 | Te Whare O Nga Tumanako Women’s Refuge | Te Atatū South suburb centroid | -36.864720, 174.647680 | S | Current [refuge service](https://www.healthpoint.co.nz/community-health-and-social-services/refuge/te-whare-o-nga-tumanako-maori-womens-refuge/); public locality evidence conflicts, so coarse point only |
| 44 | The Koha Shed - West Auckland | Unknown | — | U | FY25 name retained; an older [West Auckland resource guide](https://www.west.org.nz/wp-content/uploads/2021/02/HC2A-Homelessness-Housing-and-Community-Resources-in-West-Auckland-version-3-final-3.2.21.pdf) was too stale to establish a current fixed point |
| 45 | The Otara Kai Village | 120 East Tāmaki Road, Ōtara | -36.962089, 174.873237 | A | Current [Community Builders](https://www.communitybuildersnz.org/our-kaupapa.html) programme point |
| 46 | The Salvation Army Glenfield Foodbank | 4 Kaipatiki Road, Glenfield | -36.781810, 174.720420 | A | Current [North Shore Service Hub](https://www.salvationarmy.org.nz/location/glenfield-community-ministries-north-shore-service-hub/) |
| 47 | The Salvation Army Hibiscus Coast | 32–38 Greenview Lane, Red Beach | -36.607400, 174.689000 | A | Current [Hibiscus Coast Corps](https://www.salvationarmy.org.nz/corps/hibiscus-coast-corps/); public donation point, but commercial receiving unconfirmed |
| 48 | The Salvation Army Manukau Foodbank | 16B Bakerfield Place, Manukau 2104 | -36.989006, 174.884941 | A | Current [Manukau Community Ministries](https://www.salvationarmy.org.nz/location/manukau-community-ministries/) |
| 49 | The Salvation Army Rosedale | 90 Rosedale Road, Albany／Rosedale | -36.735540, 174.725900 | A | Current [Albany Bays Corps](https://www.salvationarmy.org.nz/centres/nz/auckland/albany-bays/albany-bays-corps) foodbank service |
| 50 | Vaka Tautua - Manukau | 12 Lambie Drive, Papatoetoe | -36.986086, 174.871835 | A | Current [South Auckland office](https://www.vakatautua.co.nz/fish-contact-us) |
| 51 | Waitakere College | 42 Rathgar Road, Henderson | -36.867060, 174.618430 | A | Current [school](https://www.waitakerecollege.school.nz/contact-us) campus |
| 52 | Whanau Resource Centre o Pukekohe Charitable Trust | 17 McNally Road, Pukekohe | -37.207313, 174.888014 | A | Current [office and Koha Shed](https://whanauresourcecentre.org.nz/contact/) |
| 53 | Whangaparoa Baptist Church Foodbank | 733 Whangaparaoa Road, Stanmore Bay | -36.636940, 174.748890 | A | Current [WBC Foodbank](https://wbc.org.nz/contact/) public collection point |
| 54 | Women’s Refuge Tamaki Makaurau | Level 1, Unit 3, 322 New North Road, Kingsland | -36.868950, 174.751710 | A | Current public [network office](https://womensrefugetamaki.org.nz/); never a safe-house proxy |

The roster deliberately preserves closed, renamed, proxy and protected cases because the user requested complete FY25 point-to-point coverage. They must remain visually and operationally distinct: `H`, `S` and `U` points should not be sent to a navigation engine as final stops.

#### Current Auckland Food Hub candidate set

The [NZ Food Network directory](https://www.nzfoodnetwork.org.nz/our-food-hubs/) currently displays the following 16 Auckland nodes. These are confirmed NZFN Food Hubs or operator nodes; they are **not automatically confirmed as current KiwiHarvest recipients**.

| Organisation | Publicly evidenced role | Public approximation | WGS84 latitude, longitude | Map status／routing caveat |
| --- | --- | --- | --- | --- |
| [Auckland City Mission – Te Tāpui Atawhai](https://aucklandcitymission.org.nz/support-us/) | Food parcels, housing, health and social support | HomeGround courier address, 195 Federal Street, Auckland Central 1010 | -36.850708, 174.761443 | A; courier address, not confirmed bulk-food receiving dock |
| [BBM Motivation／BBM Foodshare](https://www.thebbmprogram.com/) | Community food support and kitchen | 30 Hobill Avenue, Wiri 2104 | -37.002497, 174.874434 | A; current delivery address and cold-storage intake unconfirmed |
| [Encounter Hope Foundation – The Hope Centre](https://www.foodbank.co.nz/the-hope-centre) | Foodbank and food assistance | 4109 Great North Road, Kelston 0602 | -36.903105, 174.657236 | A; public foodbank point, pallet access unconfirmed |
| [Fair Food](https://www.fairfood.org.nz/) | Food rescue operator and Auckland-wide distributor | Unit 2, 624 Rosebank Road, Avondale 1026 | -36.873654, 174.669423 | A; public warehouse site, exact truck entrance unconfirmed |
| [Grace Foundation](https://www.gracefoundation.co.nz/) | Accommodation, rehabilitation and community support | No verified public street receiving site | — | U; current NZFN role only |
| [Kindness Collective](https://www.kindness.org.nz/) | Food, essentials and social-supermarket support | No verified public Auckland warehouse site | — | U; current NZFN role only |
| [KiwiHarvest – Auckland](https://www.kiwiharvest.org.nz/contact-us) | Food rescue operator／distributor | Unit G/70 Business Parade South, East Tāmaki 2013 | -36.939934, 174.875495 | A; operator depot, not frontline recipient |
| [KiwiHarvest – North Shore](https://www.kiwiharvest.org.nz/contact-us) | Food rescue operator／distributor | 13B Ride Way, Rosedale 0632 | -36.752635, 174.702980 | A; operator branch, not frontline recipient |
| [MUMA／Ngā Whare Waatea Marae](https://www.muma.co.nz/contact) | Marae, foodbank and whānau support | 31 Calthorp Close, Māngere 2025 | -36.960584, 174.802153 | A; marae point, receiving process unconfirmed |
| [Salvation Army Manukau Community Ministries](https://www.salvationarmy.org.nz/location/manukau-community-ministries/) | Food parcels and social support | 16B Bakerfield Place, Manukau 2104 | -36.988732, 174.885428 | A; unit precision and donor entrance unconfirmed |
| [South Auckland Christian Foodbank](https://www.sacfb.org.nz/) | Warehouse-based food support | Māngere purpose-built warehouse; street address not public | — | U; do not reuse stale directory addresses |
| [South Kaipara Good Food](https://skgf.org.nz/kai-rescue/) | Kai Assist, Kai Rescue and regional redistribution | 82 Mill Road, Helensville 0800 | -36.677219, 174.444650 | H; public service／address-for-service point, receiving entrance unconfirmed |
| Salvation Army Northern Region Mission Support Centre | Regional support and distribution | No verified public receiving site | — | U; do not merge with a public-facing Salvation Army foodbank |
| [Supreme Sikh Society of New Zealand](https://www.supremesikhsociety.co.nz/contact/) | Community kitchen and food-parcel distribution | 70 Takanini School Road, Takanini 2112 | -37.035465, 174.922052 | A; food type and pallet acceptance still require confirmation |
| [Vinnies Tāmaki Makaurau](https://vinniestm.org.nz/contact-us/) | Foodbank, rescued-food kitchen and onward distribution | 6A Henderson Place, Onehunga 1061 | -36.919607, 174.804518 | A; kitchen, service and bulk-receiving flows may differ |
| [Visionwest Community Trust](https://visionwest.org.nz/contact-us/) | Food parcels, social supermarket and bulk food support | 97 Glendale Road, Glen Eden 0602 | -36.917848, 174.649092 | A; public site, actual warehouse entrance unconfirmed |

For route research, a blank or public office address must not be silently geocoded into a delivery point. Recipient organisations need to confirm their actual receiving entrance, delivery hours, vehicle access, pallet handling and whether the address can be stored or displayed publicly.

#### Public capability and throughput evidence

Public data can help classify scale and food-handling potential, but **none of the figures below is live remaining capacity**.

| Organisation／network | Dated public evidence | What it supports | What it cannot support |
| --- | --- | --- | --- |
| Asylum Seekers Support Trust | KiwiHarvest reports 31,590 kg received during 2024-04-01–2025-03-31; nearly 7,000 food boxes and more than 1,600 clients | Historical received volume, weekly-box programme and service scale | Current acceptance, spare storage, maximum drop size or receiving window |
| Island Child Charitable Trust | FY25 case reports weekly deliveries, 25,272 kg, about 56,160 meals and meals for about 85 people daily | Historical received volume and regular service pattern | Current free capacity; exact location is additionally protected |
| Good Care Community Trust | Current KiwiHarvest testimonial says regular food-pallet delivery is central to operations | Pallet-scale deliveries have occurred | Pallets per delivery, storage lanes, delivery address or live space |
| Windsor Park Baptist Church | Current public page describes weekly Wednesday 10:30 food distribution | A dated public distribution pattern and frontline service | Driver receiving time, unloading point or quantity accepted |
| Auckland City Mission | Public food-support material reports more than 30,000 food parcels in 2025 | Historical distribution throughput and strong demand | Available capacity or direct KiwiHarvest relationship in 2026 |
| Visionwest | 2023 evidence describes a Whata Manaaki warehouse, large fridge／freezer units, forklift and service of up to 400 whānau per week | Named-site storage and handling capability plus historical service scale | Current spare chilled／frozen space or acceptance of a specific donation |
| Fair Food | Current mission material describes daily supermarket／producer collections and fresh-food redistribution; its kitchen reports regular meal／meal-kit output | Food rescue, fresh-food handling, kitchen and distribution role | Whether it should receive a Woolworths load through KiwiHarvest or its live capacity |
| NZFN Food Hubs | NZFN says 64 hubs can receive bulk palletised food and may handle fresh, frozen, chilled and ambient food; excess can be redistributed when a hub cannot store it | Network-level pallet and storage capability requirements | That every listed hub has space now, or is a KiwiHarvest recipient |

MPI’s donation guidance requires the donor and receiving organisation to agree which foods are useful, what can be safely handled and suitable collection times. Therefore the following must stay `unknown` until an operator supplies a time-stamped confirmation: current acceptance, quantity wanted, ambient／chilled／frozen space, food restrictions, delivery window and unloading constraints.

#### Publicly supported flow, but not a fixed route sequence

KiwiHarvest’s public operating material says food rescue drivers collect surplus food, warehouse teams sort or repack it, and drivers deliver to recipient agencies. Volunteer material also describes collection, sorting and delivery work across its branches. This supports both warehouse handling and recipient delivery, but does not prove that every Woolworths load follows one mandatory sequence.

The research map should therefore permit these scenario edges without claiming which one is standard:

- KiwiHarvest branch → Woolworths store;
- Woolworths store → KiwiHarvest branch for sorting or cross-docking;
- KiwiHarvest branch → recipient approximate point;
- Woolworths store → recipient approximate point, only as an unconfirmed direct-delivery scenario.

Actual route history or KiwiHarvest operating rules are required to decide whether direct delivery is allowed, when cross-docking is mandatory and which branch owns each store or recipient.

### 3.6 KiwiHarvest locations

KiwiHarvest’s current contact page lists five operational locations. GPS values below were address-geocoded through the ArcGIS World Geocoding Service; they are WGS84 address or parcel centroids, not verified entrances, loading bays or parking spaces.

| Branch | Public address | Approximate GPS | Confirmed operational evidence | GPS confidence |
| --- | --- | --- | --- | --- |
| Auckland & HQ — Highbrook | Unit G/70 Business Parade South, East Tāmaki, Auckland 2013 | -36.939934, 174.875495 | Current HQ and Auckland location; volunteer material refers to the Highbrook warehouse | Medium-high for address; not unit entrance |
| North Shore — Rosedale | 13B Ride Way, Rosedale, Auckland 0632 | -36.752635, 174.702980 | Current North Shore branch; older annual reports confirm a Rosedale warehouse | Medium; geocoder resolves 13 rather than unit 13B |
| Dunedin | 759 Kaikorai Valley Road, Burnside, Dunedin 9011 | -45.898286, 170.455869 | Current Dunedin location | Medium-high |
| Invercargill | 12 Benmore Street, Prestonville, Invercargill 9810 | -46.384128, 168.348374 | Current Invercargill branch | Medium-high |
| Queenstown — Frankton | Lot 2, Grant Road, Frankton, Queenstown 9300 | -45.012321, 168.742450 | Current Queenstown depot | Medium-high; geocoder resolves 2 Grant Road rather than the exact lot |

The current Charities Services record also places Kiwi Harvest Limited at 70 Business Parade South, Highbrook, East Tāmaki. This confirms the registered Auckland address but is not a complete branch register.

KiwiHarvest’s Auckland branch page describes a service range from Warkworth to Pōkeno. This is useful regional context, but it does not prove that every Woolworths store within that span is on a current KiwiHarvest route.

### 3.7 Where KiwiHarvest trucks usually park

#### Confirmed evidence

| Evidence | What it confirms | What it does not confirm |
| --- | --- | --- |
| KiwiHarvest contact and volunteer pages identify Highbrook as the Auckland HQ／warehouse | Some Auckland driver-assistant work and warehouse activity starts from Highbrook | It does not identify every vehicle assigned there or a parking bay |
| The North Shore branch is a Rosedale warehouse; a 2025 indexed driver-assistant listing described a route starting there | At least some North Shore operations have used Rosedale as a route origin | The listing is historical／indexed and cannot prove the 2026 assignment of every North Shore vehicle |
| A 2026 JAC case page says a KiwiHarvest Auckland EV truck returns to “base” after its day and charges overnight | At least one EV truck follows a return-to-base overnight charging pattern | The page does not name the base address or charger location |
| KiwiHarvest states that its refrigerated vehicles collect from donors and deliver to recipient agencies | Trucks load or unload at donors, branch facilities and recipients | It does not publish fixed loading-bay coordinates |
| The Queenstown contact instruction says to access the depot through the rear carpark and that there is no parking directly outside | A visitor-access constraint for the Queenstown depot | It is not evidence of Auckland truck parking or overnight fleet storage |

#### Strict conclusion

> **Unknown:** Public evidence does not establish where each Auckland truck or van usually parks overnight. Highbrook and Rosedale are confirmed operational branch locations and plausible route origins, but neither should be recorded as a vehicle’s home depot or parking bay without KiwiHarvest confirmation.

The following remain unknown:

- which vehicles are assigned to Highbrook versus Rosedale;
- whether vehicles move between the two branches;
- whether all vehicles return to a branch, use off-site parking or are taken home by drivers;
- the EV truck’s exact charging address;
- gate, loading dock, refrigerated staging area and parking-bay GPS;
- standard shift start／end times by vehicle and weekday;
- whether Woolworths food always returns to a KiwiHarvest warehouse or can move directly from store to recipient.

### 3.8 Minimum research unit for the point-to-point map

The minimum useful unit is an **organisation–site pair**, not only an organisation name and not only an address. One organisation can operate an office, warehouse, social supermarket, school programme or protected service at different places. Combining them into one point would create false delivery instructions.

This is a research data requirement, not a database schema.

| Field group | Minimum evidence to retain | Why it is needed |
| --- | --- | --- |
| Identity | Official organisation name; FY25 report name; current public name; site／programme name | Prevents renamed organisations and different branches from being merged |
| Relationship | `current-public`, `FY25-snapshot`, `historical-only`, `NZFN-hub`, or `unconfirmed`; source URL; evidence period | Separates a map candidate from a currently verified KiwiHarvest relationship |
| Public map point | Public address or area; latitude; longitude; point type; source; verification date; coordinate precision | Provides a reproducible point for research maps without claiming it is a loading bay |
| Safety | Safe-to-display flag; protected-location flag; permitted precision | Prevents refuge or transitional-housing locations from being exposed |
| Delivery-point status | `operator-confirmed`, `source-confirmed receiving site`, `public approximation`, `area centroid`, `unknown` | Controls whether a point may be used for navigation or only scenario modelling |
| Receiving operation | Receiving days／hours; entrance; contact; appointment; loading bay; vehicle and pallet constraints | A street centroid alone cannot support a real truck stop |
| Food fit | Accepted and excluded food types; minimum shelf life; allergen or preparation constraints; ambient／chilled／frozen handling | Determines whether a recipient can safely use a specific donation |
| Static capability | Public warehouse, kitchen, fridge, freezer or pallet evidence; evidence date and scope | Useful for candidate filtering, but not a live availability value |
| Current state | Current acceptance; requested quantity; live remaining capacity by temperature lane; `as_of` and expiry time | Required for actual matching; must remain unknown when no timed confirmation exists |
| Historical throughput | Value, unit, metric meaning and reporting period | Preserves useful scale evidence without mislabelling it as capacity |

Public approximate points in this document can support **scenario lines on a map**. A point may become a navigation destination only after the recipient or KiwiHarvest confirms the receiving entrance, permitted display level, access instructions and delivery window.

### 3.9 Assumption tests

`Rejected` means the hypothesis cannot be used as a general operational rule. `Accepted with constraints` means it is suitable for research visualisation only under the stated conditions.

| Hypothesis | Public evidence test | Result | Consequence for the map or later matching |
| --- | --- | --- | --- |
| FY25 and current Auckland recipient evidence can all be included as candidate delivery units | FY25 provides named recipient organisations; current organisation and directory sources provide many public service sites. Some programmes still have no defensible public location. | **Accepted with constraints** | Include every name; use service-site points where safe, area centroids for protected locality-level entries and `unknown` where even area-level evidence is absent. Approximate points are not navigation stops. |
| Every Auckland collection route starts at Highbrook, then visits a Woolworths store | KiwiHarvest has both Highbrook and Rosedale operational sites. Public sources do not publish vehicle-to-depot or store-to-branch assignments. | **Rejected** | Highbrook may be a scenario origin, not a confirmed first leg. Preserve both depot candidates and an unknown-origin state. |
| Every route follows depot → Woolworths → KiwiHarvest depot → recipient | Public descriptions show drivers collect, warehouse teams sort／pack and food is delivered to recipient agencies, but do not establish one mandatory sequence for every load. | **Inconclusive** | Research must allow direct store → recipient and cross-dock paths until KiwiHarvest supplies route history or operating rules. |
| A public organisation address is the actual delivery point | Official sources frequently expose an office, school, church, public counter or courier address rather than a receiving bay; some organisations list conflicting addresses. | **Rejected** | Store the point as a public approximation and keep actual entrance, gate and loading access unknown. |
| Every FY25 recipient is still a current 2026 recipient | The 2025 report covers the year ended 2025-03-31. A current 2026 public master list is not available. | **Rejected** | FY25 relationship remains a dated snapshot unless a current KiwiHarvest source separately confirms it. |
| Every Auckland NZFN Food Hub is a KiwiHarvest recipient | NZFN Food Hubs and KiwiHarvest recipient organisations are different network relationships; NZFN lists KiwiHarvest itself as a hub. | **Rejected** | NZFN nodes remain distribution candidates, not automatically KiwiHarvest delivery destinations. |
| Published annual kilograms, meals, parcels or people served equal available capacity | These figures describe historical receipt or throughput. NZFN explicitly notes that a hub may be unable to store a particular bulk donation. | **Rejected** | Keep dated throughput separate; live capacity is unknown without a time-limited recipient confirmation. |
| The geographically nearest recipient is the best match | MPI requires agreement on useful food, safe handling and suitable collection times; the supplied feature brief also requires food type, expiry, storage, capacity and current demand. | **Rejected** | Filter first by safety, food fit, remaining life, current acceptance, receiving window and capacity; use route cost only after feasibility. |
| A public statement of weekly delivery is the current receiving schedule | ASST, Island Child, Kootuitui and Windsor Park have published weekly patterns, but those pages do not expose a current driver appointment or loading window. | **Inconclusive** | Retain a dated reported frequency, not a live receiving slot. |
| A refuge or transitional-housing street address can be used because it appears in a public register | Public availability does not remove safety risk, and the address may identify residents rather than a logistics site. | **Rejected for navigation** | Use protected status or coarse area centroid. The real point must be supplied through access-controlled operational data. |

#### Two-depot geometry test

To test the single-origin assumption, all 61 Woolworths store centroids were compared with the public Highbrook and Rosedale branch centroids using Haversine straight-line distance:

| Scenario metric | Result |
| --- | ---: |
| Stores geometrically nearer Highbrook | 30 |
| Stores geometrically nearer Rosedale | 31 |
| Mean distance if every store is assigned to Highbrook | 17.8 km |
| Mean distance if every store is assigned to Rosedale | 19.5 km |
| Mean distance to the nearer of the two branches | 11.4 km |
| Median distance to the nearer branch | 11.1 km |

The furthest store-to-nearest-branch straight-line cases are Warkworth → Rosedale at 39.4 km, Pukekohe South → Highbrook at 30.3 km, Pukekohe → Highbrook at 29.0 km and Helensville → Rosedale at 24.0 km. Waiheke appears 22.1 km from Highbrook geometrically, but that number is not a usable road route because ferry logistics are omitted.

This test **rejects a convenient single-Highbrook geography assumption**, but does not prove actual depot assignments. It omits roads, traffic, ferries, time windows, vehicle restrictions, shift origins and whether a load travels directly from store to recipient.

## 4. Gaps

1. **No Woolworths NZ waste composition dataset.** Public sources do not disclose store-level quantity, category share, seasonality, reason codes or time-of-day patterns for surplus food.
2. **No public StoreCentral integration contract.** The brief confirms functionality, but not product API, event schema, authentication, barcode coverage or data ownership.
3. **No complete current KiwiHarvest recipient master.** The FY25 report supplies a complete dated report list and current pages identify selected partners, but neither is a live 2026 operational roster.
4. **No live recipient state.** Current need, capacity, cold／frozen storage availability, food restrictions, receiving hours and short-notice acceptance are generally unavailable.
5. **No verified receiving entrances.** This research can create public approximate points, but an organisation’s office, foodbank counter, school, church, postal address and commercial delivery dock may differ.
6. **No current fleet master or telematics.** Vehicle dimensions, payload, refrigeration zones, home depot, driver shift, route history and parking location are not public.
7. **No precise service-time data.** Store loading time, recipient unloading time, traffic buffers and failed-delivery behaviour are unknown.
8. **No partner-specific eligibility matrix.** MPI provides safety constraints and KiwiHarvest provides broad acceptance guidance, but Woolworths and KiwiHarvest’s detailed operating rules are not public.
9. **Protected recipient locations.** Refuges and specialist accommodation may require non-public addresses and access controls.
10. **Two candidate locations remain unresolved.** Hapori Tautua Collective and The Koha Shed – West Auckland have no defensible current public point.
11. **FY25 status changes are material.** North Shore Women’s Centre later closed, Te Whare Marama O Mangere’s provider approval was revoked, and several branch／programme names now resolve only to a proxy or service-area centroid.

## 5. Weak reasoning to avoid

| Weak reasoning | Why it fails |
| --- | --- |
| “KiwiHarvest accepts fresh, chilled and frozen food, therefore these are Woolworths’ most common waste categories.” | Acceptance scope is not waste-frequency evidence |
| “The barcode identifies the product, therefore it provides everything required for matching.” | Barcode does not reliably provide current quantity, condition, temperature, pickup window, store, recipient capacity or delivery deadline |
| “An organisation appears in the NZFN directory, therefore it is a current KiwiHarvest recipient.” | NZFN membership and KiwiHarvest recipient status are separate relationships |
| “An organisation’s public address is its food receiving dock.” | Public, postal, programme and warehouse addresses can differ |
| “A public approximate point is accurate enough for truck navigation.” | It is suitable for research lines and distance scenarios only; entrance, access and safety remain unverified |
| “KiwiHarvest HQ is where all Auckland trucks park.” | HQ is confirmed; fleet assignment and overnight parking are not |
| “The nearest recipient should receive the food.” | Safety, storage, remaining shelf life, current need, capacity, service type and receiving time may outweigh distance |
| “A 2021 recipient list is still current.” | Relationships, sites, programmes and capacities change |
| “Every organisation in the FY25 report is still a current recipient.” | FY25 ended on 2025-03-31 and does not prove 2026 status |
| “A current organisation website upgrades an FY25 relationship to current.” | It confirms the organisation or site exists, not that KiwiHarvest still delivers there |
| “A nearby successor or local foodbank is the same FY25 recipient.” | A proxy point can support regional visualisation only; continuity requires explicit evidence |
| “Store GPS is sufficient for route planning.” | The API coordinate is not necessarily the service entrance, loading area or legal truck access point |

## 6. Unsupported assumptions

The following must not be represented as confirmed facts:

- Woolworths’ five or six supported food categories are ranked by waste volume.
- Every Woolworths item has a 2D barcode containing lot, date and weight.
- StoreCentral can be replaced by a separate barcode-import flow without integration consequences.
- All 61 AUK stores participate in the same KiwiHarvest collection process.
- All listed Food Hubs currently accept Woolworths surplus.
- Every organisation in the FY25 report remains an active KiwiHarvest recipient in 2026.
- Public recipient addresses are valid refrigerated-truck destinations.
- A suburb centroid or public approximate point is safe for turn-by-turn navigation.
- Recipient needs can be entered once and treated as permanent.
- Every Auckland route starts and ends at Highbrook.
- North Shore trucks always park at Rosedale.
- A truck’s “base” in a vehicle case study means Highbrook.
- Driver routes deliver directly to individual consumers.
- Straight-line GPS distance is an adequate proxy for drive time.

## 7. Assumption alignment

| Assumption or decision | Status | Evidence or reason |
| --- | --- | --- |
| The product problem is centred on KiwiHarvest drivers／dispatchers getting food to suitable recipients | **human-aligned** | Confirmed by the user’s problem statement |
| Research must precede schema, implementation planning and AI-agent work | **human-aligned** | Explicit user direction for this phase |
| The operational destination is usually a recipient organisation, not an individual consumer | **evidence-validated** | KiwiHarvest distributes through recipient organisations and does not directly issue public food parcels |
| Auckland-region Store Locator scope contains 61 supermarket records | **evidence-validated** | Official API filtered to COUNTDOWN + AUK; independently re-counted |
| Fresh, bakery／deli, chilled, frozen and ambient／dry are relevant handling categories | **evidence-validated** | KiwiHarvest, MPI and Woolworths category evidence |
| Woolworths-brand North Island fresh meat may expose lot／date／weight through GS1 2D barcode | **evidence-validated** | GS1 New Zealand member story |
| All Woolworths products expose equivalent 2D data | **unresolved** | No coverage data or symbology inventory was found |
| Highbrook and Rosedale are Auckland operational locations | **evidence-validated** | Current KiwiHarvest contact data and branch／warehouse evidence |
| Each Auckland vehicle’s normal home depot and overnight parking | **unresolved** | No public fleet assignment or parking record |
| NZFN Auckland hubs are possible receiving or distribution candidates | **evidence-validated** as candidates | Current NZFN directory confirms hub role, but not KiwiHarvest relationship or live capacity |
| Every FY25 and current-public Auckland recipient name should be included as a candidate unit, with a safe approximate point wherever evidence permits | **human-aligned** | Explicit user direction; protected sites remain coarse and non-navigable, while unsupported locations remain unknown |
| FY25 relationship evidence remains valid as a dated snapshot, not a current relationship | **evidence-validated** | Official 2025 Annual Report covers the year ended 2025-03-31 |
| A public service／programme point can be treated as the actual delivery entrance | **unresolved** | Requires recipient or KiwiHarvest operational confirmation |
| The exact recipient roster for a Woolworths pilot | **unresolved** | Requires KiwiHarvest operational data and partner consent |
| The pilot includes every AUK store, including Warkworth, Pukekohe and Waiheke | **unresolved** | API region scope is not the same as pilot service scope |

## 8. Missing requirements

The brief does not yet specify:

- the pilot’s exact Auckland geographic boundary and participating stores;
- whether StoreCentral remains the system of record;
- how product and donation events would be obtained from Woolworths;
- barcode symbology and attribute coverage by food category;
- Woolworths and KiwiHarvest’s actual donation eligibility rules;
- whether food goes store → recipient, store → KiwiHarvest depot → recipient, or both;
- the current recipient roster and each organisation’s onboarding status;
- the rule for promoting a public approximate point to an operator-confirmed delivery point;
- how current need and capacity are supplied, updated and expired;
- actual receiving address, service entrance, operating hours and contact for each recipient;
- fleet roster, vehicle payload, refrigeration capacity, compartment restrictions and branch assignment;
- driver shift, breaks, depot return, charging and overnight parking rules;
- route optimisation objective and priority order;
- protected-address and personal-data handling;
- acceptance, rejection, pickup, delivery and failed-route evidence;
- data retention, audit and ownership across Woolworths, KiwiHarvest and recipients.

## 9. Ambiguities

1. **“Auckland” scope:** Woolworths’ AUK API region includes outer areas and islands; it may be broader than the intended Auckland urban pilot.
2. **“Recipient”:** This may mean a food rescue operator, distribution hub, frontline agency or the community members ultimately served. These roles cannot share one operational interpretation.
3. **“Common waste food”:** It may mean the most frequent items, the greatest weight, the highest financial loss or the categories most often eligible for donation. Public sources only support category and eligibility research, not ranking.
4. **“GPS location”:** Store centroid, street address, service entrance, loading dock, depot gate and overnight parking bay are different coordinates.
5. **“Need”:** A general preferred-food profile is different from today’s requested quantity and remaining capacity.
6. **“Barcode import”:** It could mean GTIN product-master lookup, lot／date extraction from GS1 2D, or creation of a specific donation event.
7. **“Truck usually parks”:** This could mean shift origin, home depot, overnight bay, charging point or temporary loading location.
8. **“Approximate delivery point”:** In this research it means a safe point for scenario mapping, not proof that a driver may navigate to or unload at that point.

## 10. Contradictions

1. A consumer-direct interpretation conflicts with KiwiHarvest’s published operating model: KiwiHarvest distributes via recipient organisations and does not directly provide public food parcels.
2. Building a new scan-and-import workflow as if no Woolworths process exists conflicts with the brief’s claim that StoreCentral already scans unsellable items and checks diversion eligibility. The unresolved issue is access and integration, not evidence that scanning is absent.
3. Treating current NZFN Food Hubs as a current KiwiHarvest recipient list conflicts with the fact that they are maintained by different organisations for different network relationships.
4. Treating older KiwiHarvest annual-report recipient lists as current conflicts with the absence of a public, complete 2026 roster.
5. The Store Locator API uses the internal division label COUNTDOWN while store names use Woolworths. This is a source-system naming mismatch, not evidence of duplicate supermarket chains.
6. Public directories may count or display hubs differently as they are updated. The visible Auckland list must be timestamped rather than treated as permanent master data.

## 11. Questions that require human answers

### Woolworths

1. Which Auckland stores are in the pilot, and are Warkworth, Pukekohe, Waiheke and metro formats in scope?
2. Is StoreCentral the source of product and donation events, or is a separate scanner expected?
3. What APIs, exports or event feeds are available, and which organisation owns each field?
4. Which product categories and barcode formats carry GTIN, lot, date, weight and recall-relevant data?
5. What is the real store-level surplus breakdown by category, reason, quantity, weekday and time?
6. What are the approved donation eligibility and Food Recovery Hierarchy rules?
7. What is each store’s actual collection point, loading restriction and pickup window?

### KiwiHarvest

1. What is the current Auckland recipient roster, and which recipients may be used in the pilot?
2. Which of the 54 Auckland-identifiable FY25 names remain active KiwiHarvest recipients, and which have exited, closed, moved or changed programme name?
3. What public or protected operational point should replace the unresolved Hapori Tautua Collective and The Koha Shed – West Auckland locations?
4. Which organisations are direct-delivery destinations and which require warehouse cross-docking?
5. What current need, capacity, food restrictions, storage and receiving-hour data can recipients provide?
6. Are Highbrook and Rosedale both daily route origins? Is there another satellite or overflow site?
7. Which vehicle belongs to which branch, and can vehicles be reassigned across branches?
8. Where does each vehicle normally park overnight, and where does the EV truck charge?
9. What are the verified gate, loading-bay and staging GPS coordinates?
10. What are normal shift start／end times, breaks and depot-return rules?
11. Can anonymised historical route／telematics data be supplied for route research?

### Recipient organisations

1. What food categories, date windows, allergens and preparation states can the organisation safely accept?
2. What chilled, frozen and ambient capacity is available now, and when does that capacity expire?
3. What minimum／maximum quantities are useful?
4. What is the actual delivery entrance, vehicle access, contact and receiving window?
5. Can the address be stored and displayed, or is it protected?
6. Who can accept or reject a proposed delivery and confirm final receipt?
7. Does the public approximation in this document identify the right programme／site, or should it be replaced by a different controlled delivery point?

## 12. Research conclusion

The evidence is sufficient to define a **research baseline**, but not yet a route-ready operational dataset:

- Woolworths supply locations are publicly enumerable: 61 AUK supermarket records with official address-level GPS.
- Relevant food-handling categories and safety characteristics are known, but actual Woolworths waste frequency and volume are not.
- The complete recipient research roster contains 60 distinct FY25／current-public candidate identities: 58 have a safe public approximation and two remain location-unknown. These points support point-to-point scenario mapping, but current relationship, live need, capacity and actual delivery entrances remain incomplete.
- KiwiHarvest has two confirmed Auckland operational locations, but vehicle assignment and normal parking remain unknown.

Therefore, the static research map can show 61 Woolworths stores, both KiwiHarvest Auckland branches and 58 recipient approximations while retaining two unresolved candidate units. It must not yet be presented as an executable delivery plan. Promotion from a dotted research point to a navigation stop requires Woolworths operational data, KiwiHarvest fleet／recipient records and recipient confirmation.

## 13. Source register

All sources were checked on 2026-08-08 unless marked historical.

### Woolworths, brief and barcode

- [Scenario Brief](https://app.notion.com/p/3b56c0b712f880c0b87cc01d2bec2d7f?pvs=204)
- [Platform Features](https://app.notion.com/p/3b56c0b712f8804b9e66c873d60af1cb?pvs=204)
- [Kai Commitment Woolworths case study](https://kaicommitment.org.nz/wp-content/uploads/2024/07/Kai-Commitment_Case-Study-Woolworths.pdf)
- [Woolworths Store Locator service documentation](https://contact.woolworths.com.au/storelocator/service)
- [Woolworths official NZ Store Locator JSON](https://contact.woolworths.com.au/storelocator/service/corporateinfo/country/nz/division/all/tradinghours/current/weeks/1/json)
- [GS1 New Zealand — Woolworths NZ 2D barcodes](https://www.gs1nz.org/member-stories/woolworths-nz-2d-barcodes)
- [GS1 New Zealand — Introduction to 2D barcodes](https://www.gs1nz.org/news/introduction-to-2d-barcodes)
- [Countdown Corporate Responsibility Report 2012 — historical food-rescue evidence](https://www.woolworthsgroup.com.au/content/dam/wwg/investors/reports/2012/186062_corporate-responsibility-report-2012.pdf)
- [Woolworths Group H1 2026 report](https://www.woolworthsgroup.com.au/content/dam/wwg/investors/reports/f26/h26/3029540.pdf)

### Food donation and safety

- [KiwiHarvest — Supermarkets](https://www.kiwiharvest.org.nz/supermarket)
- [KiwiHarvest — Donate food](https://www.kiwiharvest.org.nz/donatefood)
- [MPI — Donations of food from commercial sources](https://www.mpi.govt.nz/dmsdocument/3783/send)
- [MPI — Food labels](https://www.mpi.govt.nz/food-safety-home/how-read-food-labels)
- [MPI — Reducing food waste](https://www.mpi.govt.nz/food-business/running-a-food-business/reducing-food-waste-tips-for-businesses)
- [MPI — Packaging rules](https://www.mpi.govt.nz/food-business/food-packaging-rules-and-guidance)

### KiwiHarvest and vehicle operations

- [KiwiHarvest — Contact](https://www.kiwiharvest.org.nz/contact-us)
- [KiwiHarvest — Auckland branch](https://www.kiwiharvest.org.nz/auckland-branch)
- [KiwiHarvest — Volunteer](https://www.kiwiharvest.org.nz/volunteer)
- [KiwiHarvest annual reports](https://www.kiwiharvest.org.nz/annual-reports)
- [KiwiHarvest Annual Report 2025 — FY25 recipient snapshot](https://www.kiwiharvest.org.nz/s/2025-KiwiHarvest_AnnualReport-Final.pdf)
- [KiwiHarvest Annual Report 2021 — historical locations and recipients](https://www.kiwiharvest.org.nz/s/KiwiHarvest_Annual-Report_2021.pdf)
- [KiwiHarvest — Our Family](https://www.kiwiharvest.org.nz/our-family)
- [KiwiHarvest — More Than Food](https://www.kiwiharvest.org.nz/blogs/more-than-food-how-kiwiharvest-empowers-charities-to-change-lives-across-new-zealand)
- [KiwiHarvest — Nourishing Communities](https://www.kiwiharvest.org.nz/blogs/nourishing-communities-the-positive-impact-of-food-support-from-kiwiharvestnbsp)
- [New Zealand Charities Register — Kiwi Harvest Limited](https://register.charities.govt.nz/Charity/CC51036)
- [JAC — KiwiHarvest EV truck](https://jac.co.nz/kiwiharvest/)
- [HelpTank — Highbrook driver-assistant route listing](https://helptank.nz/project/detail/3169)
- [Do Good Jobs — historical indexed North Shore driver-assistant listing](https://jobs.dogoodjobs.co.nz/job/328/food-rescue-driver-assistant-north-shore/)
- [ArcGIS World Geocoding Service](https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer)

### Recipient and food-hub evidence

- [KiwiHarvest — Receive food](https://www.kiwiharvest.org.nz/receive-food)
- [New Zealand Food Network — Food Hubs](https://www.nzfoodnetwork.org.nz/our-food-hubs/)
- [New Zealand Food Network — Contact](https://www.nzfoodnetwork.org.nz/contact/)
- [Foodbank New Zealand directory](https://www.foodbank.co.nz/)
- [Auckland City Mission](https://aucklandcitymission.org.nz/)
- [Auckland City Mission — food support](https://aucklandcitymission.org.nz/get-help/food/)
- [BBM Motivation](https://www.thebbmprogram.com/)
- [Wiri Business Association — historical BBM Foodshare address evidence](https://wiribiz.org.nz/wp-content/uploads/2024/09/Wiri-Link-May-2023.pdf)
- [Encounter Hope Foundation — Foodbank listing](https://www.foodbank.co.nz/the-hope-centre)
- [Fair Food](https://fairfood.org.nz/)
- [Fair Food — mission and handling model](https://www.fairfood.org.nz/our-mission)
- [MUMA](https://www.muma.co.nz/contact)
- [Salvation Army Manukau Community Ministries](https://www.salvationarmy.org.nz/location/manukau-community-ministries/)
- [South Auckland Christian Foodbank](https://www.foodbank.co.nz/south-auckland-christian-foodbank)
- [South Kaipara Good Food](https://skgf.org.nz/kai-rescue/)
- [Supreme Sikh Society of New Zealand](https://www.supremesikhsociety.co.nz/)
- [Vinnies Tāmaki Makaurau](https://vinniestm.org.nz/contact-us/)
- [Visionwest food support](https://visionwest.org.nz/whai-manaaki-kai/)
- [Visionwest — 2023 Whai Manaaki Kai evidence](https://ar23.visionwest.org.nz/whai-manaaki-kai/)
- [Windsor Park food support](https://www.windsorpark.org.nz/food-support/)
- [Island Child Charitable Trust](https://islandchild.org.nz/)
- [Asylum Seekers Support Trust — contact](https://asst.org.nz/contact-us/)
- [Good Care Community Trust — contact](https://www.goodcarecommunitytrust.co.nz/contact)
- [Māngere Budgeting Services Trust — Māngere branch](https://www.mbst.org.nz/mangere-branch)
- [Māngere Budgeting Services Trust — Tātou Social Supermarket](https://www.mbst.org.nz/tatou-social-supermarket)
- [Kootuitui Trust — contact](https://kootuitui.org.nz/contact/)
- [Accelerating Aotearoa／We o Tara — Healthpoint](https://www.healthpoint.co.nz/community-health-and-social-services/social/accelerating-aotearoa/at/40a-lovegrove-crescent-otara-auckland/)
- [Women’s Refuge — Auckland services directory](https://womensrefuge.org.nz/contact-us/find-your-local-refuge/)
- [OpenStreetMap Nominatim](https://nominatim.org/)
