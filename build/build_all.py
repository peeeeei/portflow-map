#!/usr/bin/env python3
"""Build v3 static dashboard JSONs from project-local interim data.

Dependency direction is data/* -> output/portflow_map/data/*.json. This script
does not read any dashboard HTML or prior generated page.
"""

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = ROOT / "data"
PROJ = ROOT.parent.parent
OUT.mkdir(parents=True, exist_ok=True)

ARTIFACTS = {}


def read_csv(path):
    with path.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def fnum(value, digits=2):
    try:
        if value in ("", None):
            return None
        return round(float(value), digits)
    except (TypeError, ValueError):
        return None


def write_json(name, obj, sources, caveats="", definition_id="v3"):
    path = OUT / name
    path.write_text(json.dumps(obj, ensure_ascii=False, allow_nan=False, separators=(",", ":")), encoding="utf-8")
    rows = len(obj) if isinstance(obj, list) else obj.get("row_count", 0) if isinstance(obj, dict) else 0
    date_values = []
    if isinstance(obj, dict):
        for key in ("dates", "months", "years"):
            vals = obj.get(key)
            if vals:
                date_values.extend([str(v) for v in vals])
    ARTIFACTS[name] = {
        "file": name,
        "rows": rows,
        "columns": sorted(obj[0].keys()) if isinstance(obj, list) and obj else [],
        "source_files": [str(s.relative_to(PROJ)) if str(s).startswith(str(PROJ)) else str(s) for s in sources],
        "build_script": "output/portflow_map/build/build_all.py",
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "date_start": min(date_values) if date_values else None,
        "date_end": max(date_values) if date_values else None,
        "gaps": [],
        "caveats": caveats,
        "definition_id": definition_id,
        "bytes": path.stat().st_size,
    }
    print(f"{name:24s} {path.stat().st_size / 1024:8.1f} KB")


def slug(text):
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")


ENTITY_ROWS = [
    ("santos", "Santos port", "Santos", "sea_port", "south", -23.95, -46.33, "Southern export endpoint", None, True, True, False, "Brazil's largest southern sea-port benchmark for soy and corn exports.", "Southern benchmark endpoint; no local low-water shock assigned."),
    ("paranagua", "Paranagua port", "Paranaguá", "sea_port", "south", -25.50, -48.52, "Southern export endpoint", None, True, True, False, "Southern export endpoint and benchmark for producer-price basis comparisons.", "Southern benchmark endpoint; no local low-water shock assigned."),
    ("rio_grande", "Rio Grande port", "Rio Grande", "sea_port", "south", -32.03, -52.08, "Southern export endpoint", None, True, True, False, "Southern comparison port in Rio Grande do Sul.", "Southern benchmark endpoint; no linked water series in the v3 dashboard spine."),
    ("sao_luis", "Sao Luis / Itaqui port", "São Luís / Itaqui", "sea_port", "north", -2.58, -44.37, "Arco Norte sea-port endpoint", None, True, True, False, "Northern export endpoint serving Cerrado grain through road and rail corridors.", "Endpoint layer; not the same as inland water-leg exposure."),
    ("barcarena", "Barcarena / Vila do Conde port", "Barcarena / Vila do Conde", "sea_port", "north", -1.52, -48.75, "Arco Norte sea-port endpoint", None, True, True, False, "Lower Amazon export endpoint receiving barge flows from Tapajos corridors.", "No usable local gauge; do not assign zero shock."),
    ("santarem", "Santarem port", "Santarém", "sea_port", "tapajos", -2.43, -54.70, "Tapajos/Amazon endpoint", "17900000", True, True, False, "Tapajos-Amazon river port and final export endpoint for some northern grain flows.", "Gauge may include lower Amazon/tidal features."),
    ("manaus", "Manaus port", "Manaus", "sea_port", "amazon", -3.14, -60.02, "Amazon mainstem port", "14990000", True, True, False, "Amazon mainstem port and industrial import node with a documented 17.7 m surcharge trigger.", "Important for imports and mainstem operations; not a pure grain export hub."),
    ("itacoatiara", "Itacoatiara port", "Itacoatiara", "sea_port", "madeira", -3.14, -58.44, "Madeira/Amazon endpoint", "16030000", True, True, False, "Downstream Madeira-Amazon endpoint for barge-to-ocean grain logistics.", "Station represents a downstream leg, not Porto Velho conditions."),
    ("belem", "Belem port", "Belém", "sea_port", "north", -1.45, -48.50, "Amazon endpoint", None, True, True, False, "Lower Amazon port in the northern export system.", "Endpoint layer; local gauge not used."),
    ("santana", "Santana port", "Santana", "sea_port", "north", -0.05, -51.18, "Amazon endpoint", None, True, True, False, "Amapa-side Amazon export endpoint.", "Endpoint layer; local gauge not used."),
    ("vitoria", "Vitoria port", "Vitória", "sea_port", "south", -20.32, -40.34, "Southern/eastern endpoint", None, True, True, False, "Eastern seaport used as a comparison endpoint in Comex classifications.", "Not a northern water-leg shock."),
    ("salvador", "Salvador port", "Salvador", "sea_port", "other", -12.97, -38.52, "Other endpoint", None, True, True, False, "Northeast sea port included for port completeness.", "Not central to the grain corridor design."),
    ("sao_francisco_sul", "Sao Francisco do Sul port", "São Francisco do Sul", "sea_port", "south", -26.24, -48.64, "Southern endpoint", None, True, True, False, "Southern grain-relevant export endpoint.", "Comparison endpoint."),
    ("imbituba", "Imbituba port", "Imbituba", "sea_port", "south", -28.23, -48.67, "Southern endpoint", None, True, True, False, "Southern PortWatch/port layer endpoint.", "Comparison endpoint."),
    ("itapoa", "Itapoa port", "Itapoá", "sea_port", "south", -26.12, -48.61, "Southern endpoint", None, True, True, False, "Southern PortWatch endpoint included for completeness.", "Comparison endpoint."),
    ("miritituba", "Miritituba transshipment hub", "Miritituba", "river_hub", "tapajos", -4.28, -55.96, "Barge-loading hub", "17730000", True, True, True, "Barge-loading terminal on the Tapajos where Mato Grosso trucks transfer grain to river barges.", "Hub layer; not a final port_of_export in Trase."),
    ("itaituba", "Itaituba / Tapajos gauge", "Itaituba", "river_hub", "tapajos", -4.27, -55.99, "Tapajos water-leg gauge area", "17730000", True, True, True, "Tapajos river node used to measure the water leg serving Miritituba transshipment.", "Gauge/hub layer; not a meaningful final export endpoint."),
    ("porto_velho", "Porto Velho transshipment hub", "Porto Velho", "river_hub", "madeira", -8.76, -63.90, "Madeira barge-loading hub", "15400000", True, True, True, "Madeira River transshipment hub where western Mato Grosso and Rondonia grain enters barges.", "Hub layer; 4 m rule needs station-datum caveat."),
    ("corumba_ladario", "Corumba / Ladario river complex", "Corumbá / Ladário", "river_hub", "paraguay", -19.01, -57.65, "Paraguay river hub", "66825000", True, True, False, "Upper Paraguay river port complex, hydrologically separate from the Amazon corridors.", "Include Ladario when matching tonnage."),
    ("porto_murtinho", "Porto Murtinho river port", "Porto Murtinho", "river_hub", "paraguay", -21.70, -57.88, "Paraguay river node", None, True, True, False, "Paraguay river node included for corridor completeness.", "Coverage is partial."),
    ("sorriso", "Sorriso producing region", "Sorriso", "producing_region", "tapajos", -12.54, -55.72, "Mato Grosso grain origin", None, False, False, True, "Major Mato Grosso soy and corn municipality, used in freight and price examples.", "Producer-price node, not a port."),
    ("sinop", "Sinop producing region", "Sinop", "producing_region", "tapajos", -11.86, -55.51, "Mato Grosso grain origin", None, False, False, True, "Northern Mato Grosso producing area close to BR-163 routes toward Miritituba.", "Producer-price node, not a port."),
    ("lucas_rio_verde", "Lucas do Rio Verde producing region", "Lucas do Rio Verde", "producing_region", "tapajos", -13.06, -55.91, "Mato Grosso grain origin", None, False, False, True, "Major Mato Grosso grain municipality in the northern-corridor hinterland.", "Producer-price node, not a port."),
    ("rondonopolis", "Rondonopolis rail terminal", "Rondonópolis", "rail_or_road_node", "south", -16.47, -54.64, "Rail and road logistics node", None, False, True, True, "Mato Grosso rail/road logistics node connecting inland grain to southern ports.", "Used as route node, not an export endpoint."),
    ("cascavel", "Cascavel southern benchmark", "Cascavel", "producing_region", "south", -24.96, -53.46, "Southern price benchmark", None, False, False, True, "Parana benchmark market used for same-source CONAB basis comparisons.", "Benchmark market, not a port."),
    ("br364", "BR-364 road corridor", "BR-364", "rail_or_road_node", "madeira", -10.10, -61.30, "Road leg to Madeira", None, False, False, True, "Road corridor linking western Mato Grosso and Rondonia to Porto Velho.", "Hand-authored route representation."),
]


def build_entities():
    entities = []
    for row in ENTITY_ROWS:
        (eid, label, name_pt, etype, corridor, lat, lon, role, station, has_flow,
         has_water, has_price, desc, caveat) = row
        entities.append({
            "id": eid,
            "label_en": label,
            "name_pt": name_pt,
            "entity_type": etype,
            "corridor": corridor,
            "lat": lat,
            "lon": lon,
            "role": role,
            "datasets": [],
            "water_station_id": station,
            "has_water": bool(station),
            "has_flow": bool(has_flow),
            "has_price_link": bool(has_price),
            "water_status": "normal",
            "description_en": desc,
            "caveats": caveat,
        })
    if len(entities) < 25:
        raise SystemExit("entities.json must contain at least 25 entities")
    write_json("entities.json", entities, [], "Hand-authored dashboard entity backbone.")
    write_json("ports.json", [e for e in entities if e["entity_type"] in ("sea_port", "river_hub")], [], "Compatibility port/hub layer.")


def build_routes():
    routes = [
        {"id": "tapajos_truck", "name": "Mato Grosso to Miritituba via BR-163", "corridor": "tapajos", "leg_type": "truck", "distance_km": 1100, "coords": [[-12.54, -55.72], [-11.86, -55.51], [-10.80, -55.10], [-7.50, -56.00], [-4.28, -55.96]], "description": "Truck leg from Sorriso and Sinop through the BR-163 corridor to Miritituba."},
        {"id": "tapajos_barge_barcarena", "name": "Miritituba to Barcarena by Tapajos/Amazon barge", "corridor": "tapajos", "leg_type": "barge", "distance_km": 1000, "coords": [[-4.28, -55.96], [-2.43, -54.70], [-1.52, -48.75]], "description": "River barge leg from Miritituba through Santarem toward Vila do Conde."},
        {"id": "tapajos_barge_santarem", "name": "Miritituba to Santarem by Tapajos barge", "corridor": "tapajos", "leg_type": "barge", "distance_km": 320, "coords": [[-4.28, -55.96], [-2.43, -54.70]], "description": "Tapajos barge leg into Santarem."},
        {"id": "madeira_truck", "name": "Western Mato Grosso / Rondonia to Porto Velho", "corridor": "madeira", "leg_type": "truck", "distance_km": 950, "coords": [[-13.06, -55.91], [-10.1, -61.3], [-8.76, -63.90]], "description": "Road leg to Porto Velho transshipment."},
        {"id": "madeira_barge", "name": "Porto Velho to Itacoatiara/Manaus by Madeira barge", "corridor": "madeira", "leg_type": "barge", "distance_km": 1150, "coords": [[-8.76, -63.90], [-5.8, -61.5], [-3.14, -58.44], [-3.14, -60.02]], "description": "Madeira River barge leg to downstream Amazon endpoints."},
        {"id": "south_rail", "name": "Mato Grosso to Santos/Paranagua via Rondonopolis", "corridor": "south", "leg_type": "rail", "distance_km": 1600, "coords": [[-12.54, -55.72], [-16.47, -54.64], [-22.5, -48.0], [-23.95, -46.33]], "description": "Southern rail/road export comparison route."},
        {"id": "south_paranagua", "name": "Mato Grosso to Paranagua southern route", "corridor": "south", "leg_type": "rail", "distance_km": 1650, "coords": [[-16.47, -54.64], [-22.8, -51.2], [-25.50, -48.52]], "description": "Southern route to Paranagua."},
    ]
    write_json("routes.json", routes, [], "Hand-authored route ribbons for orientation.")


def build_production():
    pam = read_csv(PROJ / "data/interim/ibge_pam/ibge_pam_mt_soy_corn_municipality_year_long_2004_2024.csv")
    centroids = {r["municipality_code"]: r for r in read_csv(PROJ / "data/interim/crosswalks/ibge_municipality_centroids_min_2026-07-13.csv")}
    by_mun = defaultdict(lambda: {"soy_t": 0.0, "corn_t": 0.0, "municipality": "", "state": ""})
    for r in pam:
        if r["year"] != "2024" or r["variable"] != "production_tonnes":
            continue
        rec = by_mun[r["municipality_code"]]
        rec["municipality"] = r["municipality"]
        rec["state"] = r["state"]
        rec[f"{r['crop']}_t"] += float(r["value"] or 0)
    out = []
    for code, rec in by_mun.items():
        c = centroids.get(code)
        if not c:
            continue
        total = rec["soy_t"] + rec["corn_t"]
        if total <= 0:
            continue
        out.append({"municipality_code": code, "municipality": rec["municipality"], "state": rec["state"], "lat": fnum(c["lat"], 5), "lon": fnum(c["lon"], 5), "soy_t": round(rec["soy_t"], 1), "corn_t": round(rec["corn_t"], 1), "total_t": round(total, 1)})
    out.sort(key=lambda x: -x["total_t"])
    write_json("production.json", out[:90], [PROJ / "data/interim/ibge_pam/ibge_pam_mt_soy_corn_municipality_year_long_2004_2024.csv", PROJ / "data/interim/crosswalks/ibge_municipality_centroids_min_2026-07-13.csv"], "Mato Grosso 2024 soy+corn production centroids; polygon layer deferred.")


def build_municipality_products():
    pam_path = PROJ / "data/interim/ibge_pam/ibge_pam_mt_soy_corn_municipality_year_long_2004_2024.csv"
    centroid_path = PROJ / "data/interim/crosswalks/ibge_municipality_centroids_min_2026-07-13.csv"
    distance_path = PROJ / "data/interim/crosswalks/distance_exposure_all_ibge_municipalities.csv"
    trase_path = PROJ / "data/interim/trase/trase_soy_municipality_exposure_2017_2019.csv"
    centroids = {r["municipality_code"]: r for r in read_csv(centroid_path)}
    distance = {r["municipality_code"]: r for r in read_csv(distance_path)}
    trase = {}
    for r in read_csv(trase_path):
        code = r["municipality_trase_id"].replace("BR-", "")
        trase[code] = r

    production = defaultdict(lambda: {"soy": 0.0, "corn": 0.0, "municipality": "", "state": ""})
    for r in read_csv(pam_path):
        if r["year"] != "2024" or r["variable"] != "production_tonnes" or r["crop"] not in ("soy", "corn"):
            continue
        rec = production[r["municipality_code"]]
        rec["municipality"] = r["municipality"]
        rec["state"] = r["state"]
        rec[r["crop"]] += float(r["value"] or 0)

    rows = []
    for code, prod in production.items():
        c = centroids.get(code)
        d = distance.get(code)
        t = trase.get(code, {})
        if not c:
            continue
        common = {
            "municipality_code": code,
            "municipality": prod["municipality"],
            "state": prod["state"],
            "lat": fnum(c["lat"], 5),
            "lon": fnum(c["lon"], 5),
            "distance_exposure": fnum(d.get("dist_exp") if d else None, 4),
            "distance_diff_km": fnum(d.get("dist_diff_km") if d else None, 1),
            "trase_soy_arco_norte_share": fnum(t.get("arco_norte_broad_share"), 4),
            "trase_soy_south_share": fnum(t.get("south_ports_share"), 4),
            "trase_soy_top_port": t.get("top_port") or "",
            "trase_known_export_volume_2017_2019": fnum(t.get("known_export_volume_2017_2019"), 1),
            "n_known_ports": fnum(t.get("n_known_ports"), 0),
        }
        for product in ("soy", "corn"):
            if prod[product] <= 0:
                continue
            exposure = common["trase_soy_arco_norte_share"] if product == "soy" and common["trase_soy_arco_norte_share"] is not None else common["distance_exposure"]
            exposure_source = "Trase soy endpoint benchmark, 2017-2019" if product == "soy" and common["trase_soy_arco_norte_share"] is not None else "Distance proxy: closer to Miritituba than Rondonopolis"
            rows.append({
                **common,
                "product": product,
                "production_tonnes_2024": round(prod[product], 1),
                "port_exposure": exposure,
                "exposure_source": exposure_source,
            })
        total = prod["soy"] + prod["corn"]
        if total > 0:
            weighted = None
            if common["trase_soy_arco_norte_share"] is not None and common["distance_exposure"] is not None:
                weighted = round((common["trase_soy_arco_norte_share"] * prod["soy"] + common["distance_exposure"] * prod["corn"]) / total, 4)
            rows.append({
                **common,
                "product": "all",
                "production_tonnes_2024": round(total, 1),
                "port_exposure": weighted if weighted is not None else common["distance_exposure"],
                "exposure_source": "Soy uses Trase endpoint benchmark; corn uses distance proxy",
            })
    rows.sort(key=lambda r: (r["product"], -r["production_tonnes_2024"]))
    write_json("municipality_products.json", rows, [pam_path, centroid_path, distance_path, trase_path], "Municipality-level product production and port/corridor exposure. Soy exposure is Trase endpoint benchmark; corn exposure is a distance proxy.")


def build_water():
    monthly_path = PROJ / "data/interim/ana/wl_monthly.csv"
    rows = read_csv(monthly_path)
    series = defaultdict(list)
    station_values = defaultdict(list)
    for r in rows:
        val = fnum(r["mean_level_m"])
        if val is None:
            continue
        station = r["station"]
        series[station].append({"date": r["year_month"], "level_m": val, "min_m": fnum(r["min_level_m"]), "max_m": fnum(r["max_level_m"]), "n_daily_obs": fnum(r["n_daily_obs"], 0), "label": r["label"], "leg": r["leg"], "source": r["source"]})
        station_values[station].append(val)
    out_series = {}
    thresholds = {
        "14990000": {"value_m": 17.7, "label": "Manaus 17.7 m operational surcharge trigger", "type": "official_operational"},
        "15400000": {"value_m": 4.0, "label": "Porto Velho 4.0 m navigation reference; datum caveat", "type": "official_reference"},
    }
    for station, vals in station_values.items():
        vals_sorted = sorted(vals)
        p10 = vals_sorted[int(0.10 * (len(vals_sorted) - 1))]
        p02 = vals_sorted[int(0.02 * (len(vals_sorted) - 1))]
        annual = defaultdict(lambda: {"p10": 0, "p02": 0, "official": 0, "months": 0})
        for rec in series[station]:
            year = rec["date"][:4]
            annual[year]["months"] += 1
            if rec["level_m"] < p10:
                annual[year]["p10"] += 1
            if rec["level_m"] < p02:
                annual[year]["p02"] += 1
            if station in thresholds and rec["level_m"] < thresholds[station]["value_m"]:
                annual[year]["official"] += 1
        out_series[station] = {
            "station": station,
            "label": series[station][0]["label"],
            "leg": series[station][0]["leg"],
            "dates": [r["date"] for r in series[station]],
            "levels": [r["level_m"] for r in series[station]],
            "p10": round(p10, 2),
            "p02": round(p02, 2),
            "official_threshold": thresholds.get(station),
            "annual_months_below": [{"year": int(y), **v} for y, v in sorted(annual.items())],
            "coverage": {"start": series[station][0]["date"], "end": series[station][-1]["date"], "n": len(series[station]), "gaps": []},
        }
    write_json("water.json", {"row_count": sum(len(v["dates"]) for v in out_series.values()), "series": out_series}, [monthly_path], "Monthly water spine from corrected ANA/Porto de Manaus inputs.")


def build_flows():
    comex_path = PROJ / "data/raw/ComexStat_API/comexstat_grains_port_monthly_2017_2026.csv"
    rows = read_csv(comex_path)
    north = {"Manaus", "Santarem", "Barcarena", "PortoVelho", "Santana", "Belem", "SaoLuis"}
    south = {"Santos", "Paranagua", "RioGrande", "SaoFrancisco", "Vitoria", "Imbituba", "Itapoa"}
    by_month = defaultdict(lambda: defaultdict(float))
    totals = defaultdict(float)
    port_rows = defaultdict(float)
    for r in rows:
        product = "soy" if r["ncm_label"] == "Soja" else "corn" if r["ncm_label"] == "Milho" else "all"
        ym = f"{r['year']}-{r['month'].zfill(2)}"
        port = r["port"]
        kg = float(r["kg"] or 0)
        corr = "north" if port in north else "south" if port in south else "other"
        by_month[(product, ym)][corr] += kg
        totals[(product, ym)] += kg
        port_rows[(product, port)] += kg
    share_rows = []
    for (product, ym), corrvals in sorted(by_month.items()):
        total = totals[(product, ym)] or 1
        row = {"product": product, "date": ym}
        for corr in ("north", "south", "other"):
            row[corr] = round(corrvals[corr] / total * 100, 2)
            row[f"{corr}_kg"] = round(corrvals[corr], 0)
        share_rows.append(row)
    top_ports = [{"product": p, "port": port, "kg": round(kg, 0)} for (p, port), kg in sorted(port_rows.items(), key=lambda x: -x[1])[:40]]

    trase_path = PROJ / "data/interim/trase/trase_soy_annual_municipality_port_exporter_2004_2022.csv"
    trase_rows = [r for r in read_csv(trase_path) if r["year"] in ("2017", "2018", "2019")]
    edge = defaultdict(float)
    exporter_total = defaultdict(float)
    for r in trase_rows:
        exporter_total[r["exporter_group"] or "UNKNOWN"] += float(r["volume"] or 0)
    top_exporters = {k for k, _ in sorted(exporter_total.items(), key=lambda x: -x[1])[:8]}
    state_total = defaultdict(float)
    for r in trase_rows:
        state_total[r["state"]] += float(r["volume"] or 0)
    top_states = {k for k, _ in sorted(state_total.items(), key=lambda x: -x[1])[:8]}
    for r in trase_rows:
        vol = float(r["volume"] or 0)
        state = r["state"] if r["state"] in top_states else "OTHER STATES"
        hub = r["logistics_hub"] or "UNKNOWN HUB"
        port = r["port_of_export"] or "UNKNOWN EXPORT PORT"
        exporter = r["exporter_group"] if r["exporter_group"] in top_exporters else "OTHER EXPORTERS"
        edge[(f"state: {state}", f"hub: {hub}")] += vol
        edge[(f"hub: {hub}", f"export port: {port}")] += vol
        edge[(f"export port: {port}", f"exporter: {exporter}")] += vol
    links = [{"source": s, "target": t, "value": round(v, 1)} for (s, t), v in edge.items() if v > 0]
    write_json("flows.json", {"row_count": len(share_rows) + len(links), "shares": share_rows, "top_ports": top_ports, "sankey_links": links[:160]}, [comex_path, trase_path], "Comex endpoint shares plus Trase hub-aware Sankey. URF/customs caveat still applies.")


def build_prices():
    price_path = PROJ / "data/interim/imea/imea_soy_corn_spot_prices_public.csv"
    rows = read_csv(price_path)
    wanted = {"Sorriso", "Sinop", "Lucas do Rio Verde", "Nova Mutum", "Rondonópolis"}
    by_key = defaultdict(list)
    for r in rows:
        if r["locality_name"] not in wanted or r["price_side"] != "buy":
            continue
        crop = "corn" if r["crop"] == "milho" else "soy" if r["crop"] == "soja" else r["crop"]
        by_key[(crop, r["locality_name"], r["date"][:7])].append(float(r["value"]))
    series = defaultdict(list)
    for (crop, city, ym), vals in by_key.items():
        series[(crop, city)].append({"date": ym, "value": round(sum(vals) / len(vals), 2)})
    out_series = [{"product": crop, "market": city, "dates": [r["date"] for r in sorted(vals, key=lambda x: x["date"])], "values": [r["value"] for r in sorted(vals, key=lambda x: x["date"])]} for (crop, city), vals in sorted(series.items())]

    freight_path = PROJ / "data/raw/IMEA/imea_historical_frete_graos_freight_2014-07-11_2026-07-11.json"
    freight_raw = json.loads(freight_path.read_text(encoding="utf-8"))
    route_names = {("Sorriso", "Miritituba"), ("Sorriso", "Santos")}
    by_route = defaultdict(list)
    for r in freight_raw.get("rows", []):
        pair = (r.get("CidadeNome", ""), r.get("CidadeDestinoNome", ""))
        if pair not in route_names or r.get("valor2") is None:
            continue
        by_route[(pair[0], pair[1], (r.get("Data") or "")[:7])].append(float(r["valor2"]))
    freight_series = defaultdict(list)
    for (origin, dest, ym), vals in by_route.items():
        freight_series[(origin, dest)].append({"date": ym, "value": round(sum(vals) / len(vals), 2)})
    freight_out = [{"route": f"{o} to {d}", "dates": [r["date"] for r in sorted(vals, key=lambda x: x["date"])], "values": [r["value"] for r in sorted(vals, key=lambda x: x["date"])]} for (o, d), vals in sorted(freight_series.items())]

    episodes = [
        {"episode": "2023 low-water window", "product": "corn/soy", "exposed_market": "Sorriso and northern MT", "benchmark": "Southern benchmark pending CONAB merge", "mean_exposed_basis_change": "descriptive pending", "mean_benchmark_change": "descriptive pending", "freight_spread_change": "shown in route chart", "water_condition": "Manaus below 17.7 m in Sep-Nov 2023", "coverage_caveat": "IMEA public city series; causal incidence not claimed"},
        {"episode": "2024 low-water window", "product": "corn/soy", "exposed_market": "Sorriso and northern MT", "benchmark": "Southern benchmark pending CONAB merge", "mean_exposed_basis_change": "descriptive pending", "mean_benchmark_change": "descriptive pending", "freight_spread_change": "shown in route chart", "water_condition": "Manaus low-water exposure repeated in 2024", "coverage_caveat": "Check quote coverage before incidence use"},
    ]
    write_json("prices.json", {"row_count": len(out_series) + len(freight_out) + len(episodes), "prices": out_series, "freight": freight_out, "episodes": episodes, "coffee_note": "Coffee is conditional: Arabica coverage is usable for descriptive comparison; Conillon is sparse."}, [price_path, freight_path], "IMEA public prices and freight; descriptive only.")


def build_event():
    scenes = [
        {"step": 1, "title": "Water level falls", "text": "Descriptively, the Amazon low-water window is visible first in the corrected water-level spine.", "chart": "water"},
        {"step": 2, "title": "Low-water exposure rises", "text": "Descriptively, official markers are shown only where their legal meaning is documented; elsewhere P10/P02 bands are empirical markers.", "chart": "threshold"},
        {"step": 3, "title": "Activity and light-loading adjust", "text": "Descriptively, port calls and tonnage-per-call are mechanism checks rather than causal estimates.", "chart": "flows"},
        {"step": 4, "title": "Freight spread changes", "text": "Descriptively, Sorriso-to-north freight can be compared with Sorriso-to-south freight around the same window.", "chart": "freight"},
        {"step": 5, "title": "Producer prices co-move", "text": "Descriptively, producer-price basis is shown as co-movement; incidence estimates belong to validated empirical outputs.", "chart": "prices"},
    ]
    write_json("event.json", scenes, [], "Narrative scaffold linked to factbook F03.")


def build_manifest():
    manifest = {
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "public_data_only": True,
        "files": ARTIFACTS,
    }
    path = OUT / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, allow_nan=False, indent=2), encoding="utf-8")
    print(f"{'manifest.json':24s} {path.stat().st_size / 1024:8.1f} KB")


def main():
    print("Building portflow-map v3 JSONs")
    build_entities()
    build_routes()
    build_production()
    build_municipality_products()
    build_water()
    build_flows()
    build_prices()
    build_event()
    build_manifest()
    total = sum(p.stat().st_size for p in OUT.glob("*.json"))
    print(f"Total data size: {total / 1024:.1f} KB")
    if total > 15_000_000:
        raise SystemExit("Data directory exceeds 15 MB budget")


if __name__ == "__main__":
    main()
