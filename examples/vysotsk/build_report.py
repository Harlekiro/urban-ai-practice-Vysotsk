#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Сборка одного файла dashboard.html из уже готовых результатов исследования.

Скрипт ТОЛЬКО читает сохранённые файлы из папки data/ и пишет dashboard.html.
Он ничего не скачивает из интернета, не строит графы и не пересчитывает показатели
BlocksNet: все числа уже лежат в GeoJSON, parquet и CSV.

Запуск (Windows, из корня репозитория):

    .\\.venv\\Scripts\\python.exe examples\\vysotsk\\build_report.py

Результат: examples\\vysotsk\\dashboard.html — открыть двойным щелчком в браузере.
"""

import base64
import html
import io
import json
import sys
from pathlib import Path

import folium
import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from branca.colormap import LinearColormap
from folium.plugins import MarkerCluster

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
RESULT_DIR = DATA_DIR / "results"
OUTPUT = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DIR / "dashboard.html"

SUMMARY_FILE = RESULT_DIR / "vysotsk_blocks_summary.geojson"
BOUNDARY_FILE = RAW_DIR / "boundary.geojson"
WATER_FILE = RAW_DIR / "water.geojson"
ROADS_FILE = RAW_DIR / "roads.geojson"
RAILWAYS_FILE = RAW_DIR / "railways.geojson"
STATS_FILE = RESULT_DIR / "travel_time_stats.csv"
PROVISION_REPORT_FILE = RESULT_DIR / "provision_report.csv"
CLUSTERS_FILE = RESULT_DIR / "spacematrix_clusters.csv"
MATRIX_FILES = {
    "walk": DATA_DIR / "accessibility_matrix_walk.parquet",
    "drive": DATA_DIR / "accessibility_matrix_drive.parquet",
}

SERVICES = {
    "school": "Школа",
    "kindergarten": "Детский сад",
    "polyclinic": "Поликлиника",
    "pharmacy": "Аптека",
    "convenience": "Магазин у дома",
    "supermarket": "Супермаркет",
    "playground": "Детская площадка",
    "park": "Парк",
    "bus_stop": "Остановка транспорта",
    "post": "Почта",
    "beach": "Пляж",
    "pier": "Причал",
}

LAND_USE = {
    "residential": "Жилая",
    "business": "Деловая",
    "recreation": "Рекреационная",
    "industrial": "Производственная",
    "transport": "Транспортная",
    "special": "Специальная",
    "agriculture": "Сельскохозяйственная",
    None: "Не задано в OSM",
}

LAND_USE_COLORS = {
    "residential": "#e8b64c",
    "business": "#c060a1",
    "recreation": "#4caf7d",
    "industrial": "#8d8d8d",
    "transport": "#9b7bd4",
    "special": "#d1615a",
    "agriculture": "#a3c76d",
    None: "#dfe3e6",
}

MORPHOTYPE_RU = {
    "low-rise low-density residential": "Малоэтажная низкоплотная жилая",
    "low-rise low-density non-residential": "Малоэтажная низкоплотная нежилая",
    "low-rise low-density mixed-use": "Малоэтажная низкоплотная смешанная",
    "mid-rise low-density mixed-use": "Среднеэтажная низкоплотная смешанная",
    "mid-rise low-density residential": "Среднеэтажная низкоплотная жилая",
    "mid-rise low-density non-residential": "Среднеэтажная низкоплотная нежилая",
    "high-rise low-density mixed-use": "Многоэтажная низкоплотная смешанная",
    "individual residential": "Индивидуальная жилая застройка",
    "low-rise non-residential": "Малоэтажная нежилая",
    "low-rise model": "Малоэтажная модель",
    "mid-rise non-residential": "Среднеэтажная нежилая",
    "mid-rise residential": "Среднеэтажная жилая",
    "high-rise non-residential": "Многоэтажная нежилая",
    "high-rise residential": "Многоэтажная жилая",
    "mid-rise": "Среднеэтажная",
    "mid-rise microdistrict": "Среднеэтажный микрорайон",
    "mid-rise block": "Среднеэтажный квартал",
    "central model": "Центральная модель",
    "high-rise soviet microdistrict": "Советский многоэтажный микрорайон",
    "high-rise modern microdistrict": "Современный многоэтажный микрорайон",
}

MORPHOTYPE_COLORS = ["#2e6f9e", "#e08a3c", "#4caf7d", "#c060a1", "#8d8d8d", "#9b7bd4"]
CATEGORY_COLORS = ["#e8b64c", "#4caf7d", "#c060a1", "#8d8d8d", "#9b7bd4", "#d1615a", "#a3c76d", "#dfe3e6"]

COLUMN_TITLES = {
    "_id": "№ квартала",
    "area_ha": "Площадь квартала, га",
    "residential": "Доля жилой, %",
    "business": "Доля деловой, %",
    "recreation": "Доля рекреационной, %",
    "industrial": "Доля производственной, %",
    "transport": "Доля транспортной, %",
    "special": "Доля специальной, %",
    "agriculture": "Доля сельскохозяйственной, %",
    "land_use": "Код землепользования",
    "land_use_label": "Землепользование",
    "share": "Доля основной категории, %",
    "population": "Население, чел.",
    "footprint_area": "Площадь застройки, м²",
    "build_floor_area": "Площадь этажей, м²",
    "living_area": "Жилая площадь, м²",
    "non_living_area": "Нежилая площадь, м²",
    "buildings": "Зданий, шт.",
    "fsi": "FSI (плотность застройки)",
    "gsi": "GSI (занятость участка)",
    "mxi": "MXI (смешанность)",
    "l": "L (этажность)",
    "osr": "OSR (открытое пространство)",
    "site_area": "Площадь участка, м²",
    "share_living": "Доля жилой застройки",
    "share_non_living": "Доля нежилой застройки",
    "spacematrix_cluster": "Кластер Spacematrix",
    "morphotype_spacematrix": "Морфотип (Spacematrix)",
    "morphotype_strelka": "Морфотип (Strelka)",
    "area_accessibility_walk": "Доступность пешком, мин",
    "area_accessibility_drive": "Доступность на автомобиле, мин",
}


def column_title(column):
    if column in COLUMN_TITLES:
        return COLUMN_TITLES[column]
    if column.endswith("_provision_weak"):
        code = column[: -len("_provision_weak")]
        return f"Обеспеченность (слабая): {SERVICES.get(code, code)}"
    if column.endswith("_capacity"):
        return f"Ёмкость: {SERVICES.get(column[:-9], column[:-9])}"
    if column.endswith("_provision"):
        return f"Обеспеченность: {SERVICES.get(column[:-10], column[:-10])}"
    return column


def human_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} Б"
    if size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.0f} КБ"
    return f"{size_bytes / 1024 ** 2:.1f} МБ"


def fmt_number(value, digits=2, dash="—"):
    if value is None or (isinstance(value, float) and not np.isfinite(value)):
        return dash
    if isinstance(value, (np.integer, int)):
        return f"{int(value):,}".replace(",", " ")
    if isinstance(value, (np.floating, float)):
        text = f"{value:,.{digits}f}".replace(",", " ")
        text = text.rstrip("0").rstrip(".") if "." in text else text
        return text.replace(".", ",")
    return str(value)


def plural(count, one, few, many):
    count = abs(int(count))
    if count % 10 == 1 and count % 100 != 11:
        return one
    if 2 <= count % 10 <= 4 and not 12 <= count % 100 <= 14:
        return few
    return many


def fig_to_base64(fig):
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=130, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return base64.b64encode(buffer.getvalue()).decode("ascii")


def chart_image(fig, caption):
    return f'<figure class="chart"><img src="data:image/png;base64,{fig_to_base64(fig)}" alt="{html.escape(caption)}"><figcaption>{html.escape(caption)}</figcaption></figure>'


def setup_style():
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.titleweight": "bold",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.25,
            "grid.linestyle": "-",
            "figure.facecolor": "white",
        }
    )


# ----------------------------------------------------------------------------------
# Чтение файлов
# ----------------------------------------------------------------------------------


def read_geo(path, simplify=None, columns=None):
    if not path.exists():
        return None
    layer = gpd.read_file(path)
    if layer.crs is None:
        return None
    layer = layer.to_crs("EPSG:4326")
    if columns is not None:
        keep = [c for c in columns if c in layer.columns]
        layer = layer[[*keep, layer.geometry.name]]
    if simplify:
        layer = layer.copy()
        layer[layer.geometry.name] = layer.geometry.simplify(simplify, preserve_topology=True)
    return layer


def load_data():
    if not SUMMARY_FILE.exists():
        print("Не найден главный файл результатов:")
        print("  ", SUMMARY_FILE)
        print("Сначала выполните ноутбук vysotsk_study.ipynb до конца.")
        raise SystemExit(1)

    summary = gpd.read_file(SUMMARY_FILE).to_crs("EPSG:4326")
    summary["_id"] = summary["_id"].astype(int)
    metric = summary.to_crs("EPSG:32635")
    summary["area_ha"] = (metric.area / 10_000).round(3)
    summary["land_use_label"] = summary["land_use_label"].fillna("Не задано в OSM")

    boundary = read_geo(BOUNDARY_FILE)
    water = read_geo(WATER_FILE, simplify=0.00015, columns=[])
    roads = read_geo(ROADS_FILE, simplify=0.00008, columns=[])
    railways = read_geo(RAILWAYS_FILE, simplify=0.00008, columns=[])

    services = {}
    for path in sorted(RAW_DIR.glob("service_*.geojson")):
        code = path.stem.replace("service_", "")
        layer = read_geo(path, columns=[])
        if layer is not None and len(layer):
            services[code] = layer

    stats = pd.read_csv(STATS_FILE, encoding="utf-8-sig") if STATS_FILE.exists() else None
    report = pd.read_csv(PROVISION_REPORT_FILE, encoding="utf-8-sig") if PROVISION_REPORT_FILE.exists() else None
    clusters = pd.read_csv(CLUSTERS_FILE, encoding="utf-8-sig") if CLUSTERS_FILE.exists() else None
    matrices = {}
    for mode, path in MATRIX_FILES.items():
        if path.exists():
            matrices[mode] = pd.read_parquet(path)

    return summary, boundary, water, roads, railways, services, stats, matrices, report, clusters


# ----------------------------------------------------------------------------------
# Графики
# ----------------------------------------------------------------------------------


def chart_accessibility(summary):
    walk = summary["area_accessibility_walk"].dropna()
    drive = summary["area_accessibility_drive"].dropna()
    if walk.empty and drive.empty:
        return ""

    top = max([walk.max() if not walk.empty else 0, drive.max() if not drive.empty else 0])
    bins = np.linspace(0, top + 5, 36)

    fig, ax = plt.subplots(figsize=(9.2, 4.1))
    if not walk.empty:
        ax.hist(walk, bins=bins, color="#2e6f9e", alpha=0.68, label=f"Пешком (медиана {walk.median():.0f} мин)")
        ax.axvline(walk.median(), color="#1f4f73", linewidth=1.6, linestyle="--")
    if not drive.empty:
        ax.hist(drive, bins=bins, color="#e08a3c", alpha=0.62, label=f"На автомобиле (медиана {drive.median():.0f} мин)")
        ax.axvline(drive.median(), color="#a45c1c", linewidth=1.6, linestyle="--")
    ax.set_xlabel("Среднее время до всех остальных кварталов, минут")
    ax.set_ylabel("Кварталов")
    ax.set_title("Территориальная доступность кварталов")
    ax.legend(frameon=False)
    fig.tight_layout()
    return chart_image(fig, "Распределение среднего времени в пути от квартала до всех остальных кварталов поселения.")


def chart_reachability(matrices):
    if not matrices:
        return ""
    thresholds = [15, 30, 45, 60, 90]
    shares = {}
    for mode, matrix in matrices.items():
        values = matrix.to_numpy(dtype=float)
        finite = np.isfinite(values)
        shares[mode] = [
            100 * float((values[finite] <= threshold).sum()) / max(int(finite.sum()), 1) for threshold in thresholds
        ]

    fig, ax = plt.subplots(figsize=(9.2, 3.9))
    positions = np.arange(len(thresholds))
    width = 0.38
    modes = [("walk", "Пешком", "#2e6f9e"), ("drive", "На автомобиле", "#e08a3c")]
    for shift, (mode, label, color) in zip([-width / 2, width / 2], modes):
        if mode not in shares:
            continue
        bars = ax.bar(positions + shift, shares[mode], width, color=color, alpha=0.85, label=label)
        for bar, value in zip(bars, shares[mode]):
            ax.text(bar.get_x() + bar.get_width() / 2, value + 1.2, f"{value:.0f}%", ha="center", fontsize=8)

    ax.set_xticks(positions)
    ax.set_xticklabels([f"до {t} мин" for t in thresholds])
    ax.set_ylim(0, 105)
    ax.set_ylabel("Доля пар кварталов, %")
    ax.set_title("Какая часть пар «квартал — квартал» достижима за указанное время")
    ax.legend(frameon=False, ncol=2)
    fig.tight_layout()
    return chart_image(fig, "Рассчитано по сохранённым матрицам времени в пути (255 × 255 пар, включая диагональ).")


def chart_population(summary):
    populated = summary[summary["population"] > 0].nlargest(15, "population")
    if populated.empty:
        return ""

    fig, ax = plt.subplots(figsize=(9.2, 4.4))
    identifiers = populated["_id"].astype(int).tolist()
    values = populated["population"].to_numpy(dtype=float)
    labels = [f"квартал {identifier}" for identifier in identifiers]
    bars = ax.barh(labels[::-1], values[::-1], color="#2e6f9e", alpha=0.85)
    for bar, value in zip(bars, values[::-1]):
        ax.text(value + 4, bar.get_y() + bar.get_height() / 2, f"{value:.0f}", va="center", fontsize=8)
    ax.set_xlabel("Население, человек")
    ax.set_title("15 кварталов с наибольшим населением")
    fig.tight_layout()
    return chart_image(fig, "Население восстановлено по жилой площади зданий и нормативу обеспеченности жильём.")


def chart_provision(summary):
    provision_columns = [c for c in summary.columns if c.endswith("_provision")]
    populated = summary[summary["population"] > 0]
    rows = []
    for column in provision_columns:
        code = column[: -len("_provision")]
        values = populated[column].dropna()
        if values.empty:
            continue
        rows.append((SERVICES.get(code, code), 100 * float((values >= 1).sum()) / len(values), float(values.median())))
    if not rows:
        return ""

    rows.sort(key=lambda item: item[1])
    names = [row[0] for row in rows]
    shares = [row[1] for row in rows]
    colors = ["#c0392b" if value < 50 else "#e08a3c" if value < 80 else "#2e8b57" for value in shares]

    fig, ax = plt.subplots(figsize=(9.2, 4.6))
    bars = ax.barh(names, shares, color=colors, alpha=0.88)
    for bar, value in zip(bars, shares):
        ax.text(min(value + 1.5, 99), bar.get_y() + bar.get_height() / 2, f"{value:.0f}%", va="center", fontsize=8)
    ax.axvline(80, color="#555555", linewidth=1, linestyle="--")
    ax.text(81, len(names) - 0.55, "ориентир 80%", fontsize=8, color="#555555")
    ax.set_xlim(0, 105)
    ax.set_xlabel("Доля населённых кварталов с обеспеченностью не ниже нормы, %")
    ax.set_title("Обеспеченность услугами (среди кварталов с населением)")
    fig.tight_layout()
    return chart_image(fig, "Обеспеченность — отношение фактической ёмкости услуг к нормативной для населения квартала.")


def chart_morphotypes(summary):
    developed = summary[summary["morphotype_spacematrix"].notna()]
    if developed.empty:
        return ""

    counts = developed["morphotype_spacematrix"].value_counts()
    labels = [MORPHOTYPE_RU.get(name, name) for name in counts.index]

    fig, ax = plt.subplots(figsize=(9.2, 4.0))
    bars = ax.barh(labels[::-1], counts.to_numpy()[::-1], color="#4caf7d", alpha=0.85)
    for bar, value in zip(bars, counts.to_numpy()[::-1]):
        ax.text(value + 0.3, bar.get_y() + bar.get_height() / 2, f"{value}", va="center", fontsize=8)
    ax.set_xlabel("Кварталов")
    ax.set_title("Морфотипы застройки (Spacematrix)")
    fig.tight_layout()
    return chart_image(fig, "Морфотипы определены только для кварталов с застройкой; пустые кварталы в график не входят.")


def chart_strelka(summary):
    developed = summary[summary["morphotype_strelka"].notna()]
    if developed.empty:
        return ""

    counts = developed["morphotype_strelka"].value_counts()
    labels = [MORPHOTYPE_RU.get(name, name) for name in counts.index]

    fig, ax = plt.subplots(figsize=(9.2, 4.0))
    bars = ax.barh(labels[::-1], counts.to_numpy()[::-1], color="#2e6f9e", alpha=0.85)
    for bar, value in zip(bars, counts.to_numpy()[::-1]):
        ax.text(value + 0.3, bar.get_y() + bar.get_height() / 2, f"{value}", va="center", fontsize=8)
    ax.set_xlabel("Кварталов")
    ax.set_title("Морфотипы застройки (Strelka)")
    fig.tight_layout()
    return chart_image(fig, "Классификация Strelka по этажности, плотности и доле жилой застройки.")


def chart_spacematrix(summary):
    developed = summary[(summary["fsi"] > 0) & summary["morphotype_spacematrix"].notna()]
    if developed.empty:
        return ""

    fig, ax = plt.subplots(figsize=(6.4, 4.6))
    categories = list(developed["morphotype_spacematrix"].value_counts().index)
    for index, category in enumerate(categories):
        part = developed[developed["morphotype_spacematrix"] == category]
        ax.scatter(
            part["gsi"],
            part["fsi"],
            s=28 + part["population"].fillna(0) / 12,
            color=MORPHOTYPE_COLORS[index % len(MORPHOTYPE_COLORS)],
            alpha=0.8,
            edgecolor="white",
            linewidth=0.4,
            label=MORPHOTYPE_RU.get(category, category),
        )
    ax.set_xlabel("GSI — доля застроенной площади")
    ax.set_ylabel("FSI — плотность застройки")
    ax.set_title("Поле Spacematrix: GSI и FSI застроенных кварталов")
    ax.legend(frameon=False, fontsize=7, loc="upper right")
    fig.tight_layout()
    return chart_image(fig, "Размер точки — население квартала. Классическая диаграмма Spacematrix.")


def chart_landuse(summary):
    metric = summary.assign(_area_m2=summary.to_crs("EPSG:32635").area)
    areas = metric.groupby("land_use_label")["_area_m2"].sum() / 1e6
    if areas.empty:
        return ""

    areas = areas.sort_values(ascending=True)
    colors = [LAND_USE_COLORS.get(name, "#b0b0b0") for name in areas.index]
    fig, ax = plt.subplots(figsize=(9.2, 3.8))
    bars = ax.barh([LAND_USE.get(name, name) for name in areas.index], areas.to_numpy(), color=colors, alpha=0.9)
    for bar, value in zip(bars, areas.to_numpy()):
        ax.text(value + 0.3, bar.get_y() + bar.get_height() / 2, f"{value:.1f}", va="center", fontsize=8)
    ax.set_xlabel("Площадь кварталов, кв. км")
    ax.set_title("Землепользование по площади кварталов")
    fig.tight_layout()
    return chart_image(fig, "Категория квартала определена по преобладающему виду использования из OSM.")


# ----------------------------------------------------------------------------------
# Карта
# ----------------------------------------------------------------------------------


def add_value_layer(
    map_object, summary, column, name, tooltip_title, cmap_name, digits=1, caption=None, vmin=None, vmax=None
):
    values = pd.to_numeric(summary[column], errors="coerce")
    finite = values[np.isfinite(values)]
    if finite.empty:
        return None

    low = float(finite.min()) if vmin is None else float(vmin)
    high = float(finite.max()) if vmax is None else float(vmax)
    if high <= low:
        high = low + 1
    colormap = plt.get_cmap(cmap_name)
    normalizer = matplotlib.colors.Normalize(vmin=low, vmax=high)

    prepared = summary[["_id", column, summary.geometry.name]].copy()
    prepared["_value"] = values.to_numpy()
    prepared["_tip"] = [
        "нет данных" if not np.isfinite(value) else fmt_number(value, digits) for value in values.to_numpy()
    ]
    feature_collection = json.loads(prepared.to_json())

    def style(feature):
        value = feature["properties"].get("_value")
        if value is None or not np.isfinite(value):
            return {"fillColor": "#d9d9d9", "color": "#8a8a8a", "weight": 0.4, "fillOpacity": 0.5}
        return {
            "fillColor": matplotlib.colors.to_hex(colormap(normalizer(value))),
            "color": "#6b6b6b",
            "weight": 0.35,
            "fillOpacity": 0.78,
        }

    folium.GeoJson(
        feature_collection,
        name=name,
        style_function=style,
        tooltip=folium.GeoJsonTooltip(fields=["_id", "_tip"], aliases=["№ квартала", tooltip_title], localize=True),
        highlight_function=lambda feature: {"weight": 1.6, "color": "#111111", "fillOpacity": 0.85},
    ).add_to(map_object)

    if caption:
        LinearColormap(
            colors=[
                matplotlib.colors.to_hex(colormap(normalizer(low))),
                matplotlib.colors.to_hex(colormap(normalizer(high))),
            ],
            vmin=low,
            vmax=high,
            caption=caption,
        ).add_to(map_object)
    return low, high


def add_category_layer(map_object, summary, column, name, colors, title):
    categories = list(dict.fromkeys(summary[column].tolist()))
    color_map = {value: colors[index % len(colors)] for index, value in enumerate(categories)}

    prepared = summary[["_id", column, summary.geometry.name]].copy()
    prepared["_color"] = prepared[column].map(color_map)
    prepared["_label"] = prepared[column].map(lambda value: LAND_USE.get(value, MORPHOTYPE_RU.get(value, str(value))))
    feature_collection = json.loads(prepared.to_json())

    def style(feature):
        return {
            "fillColor": feature["properties"].get("_color", "#dddddd"),
            "color": "#6b6b6b",
            "weight": 0.35,
            "fillOpacity": 0.82,
        }

    folium.GeoJson(
        feature_collection,
        name=name,
        style_function=style,
        tooltip=folium.GeoJsonTooltip(fields=["_id", "_label"], aliases=["№ квартала", title], localize=True),
        highlight_function=lambda feature: {"weight": 1.6, "color": "#111111"},
    ).add_to(map_object)


def build_map(summary, boundary, water, roads, railways, services):
    # Для карты геометрия слегка упрощается (4 м): файл становится в разы легче, а на экране
    # разница не видна. Все расчёты и таблицы используют полную геометрию.
    map_summary = summary.copy()
    map_summary[map_summary.geometry.name] = map_summary.geometry.simplify(0.00004, preserve_topology=True)

    centroid = map_summary.to_crs("EPSG:32635").centroid.to_crs("EPSG:4326")
    center = [float(centroid.y.mean()), float(centroid.x.mean())]
    map_object = folium.Map(location=center, zoom_start=11, tiles="OpenStreetMap", control_scale=True)

    if boundary is not None and len(boundary):
        folium.GeoJson(
            boundary,
            name="Граница поселения",
            style_function=lambda feature: {
                "fill": False,
                "color": "#1f3b57",
                "weight": 2.4,
                "dashArray": "6,4",
            },
        ).add_to(map_object)

    if water is not None and len(water):
        folium.GeoJson(
            json.loads(water[["geometry"]].to_json()),
            name="Вода",
            style_function=lambda feature: {
                "fillColor": "#a9cce3",
                "color": "#8fbfdd",
                "weight": 0.3,
                "fillOpacity": 0.85,
            },
        ).add_to(map_object)

    if railways is not None and len(railways):
        folium.GeoJson(
            json.loads(railways[["geometry"]].to_json()),
            name="Железные дороги",
            style_function=lambda feature: {"color": "#8b5a2b", "weight": 1.6, "dashArray": "7,5"},
        ).add_to(map_object)

    if roads is not None and len(roads):
        folium.GeoJson(
            json.loads(roads[["geometry"]].to_json()),
            name="Улицы и дороги",
            style_function=lambda feature: {"color": "#9e9e9e", "weight": 0.9, "opacity": 0.8},
        ).add_to(map_object)

    add_value_layer(map_object, map_summary,
        "area_accessibility_walk",
        "Доступность пешком",
        "Пешком, мин",
        "YlGnBu",
        1,
        caption="Доступность пешком, мин",
    )
    add_value_layer(map_object, map_summary,
        "area_accessibility_drive",
        "Доступность на автомобиле",
        "На авто, мин",
        "YlOrRd",
        1,
    )
    add_value_layer(map_object, map_summary, "population", "Население квартала", "Население, чел.", "BuPu", 0)
    add_value_layer(map_object, map_summary, "fsi", "Плотность застройки (FSI)", "FSI", "Greens", 3)
    add_value_layer(map_object, map_summary, "gsi", "Занятость участка (GSI)", "GSI", "Oranges", 3)

    add_category_layer(map_object, map_summary,
        "land_use_label",
        "Землепользование",
        CATEGORY_COLORS,
        "Землепользование",
    )

    morph = map_summary.copy()
    morph["morphotype_spacematrix"] = morph["morphotype_spacematrix"].fillna("нет застройки")
    add_category_layer(
        map_object,
        morph,
        "morphotype_spacematrix",
        "Морфотипы (Spacematrix)",
        MORPHOTYPE_COLORS,
        "Морфотип",
    )

    strelka = map_summary.copy()
    strelka["morphotype_strelka"] = strelka["morphotype_strelka"].fillna("нет застройки")
    add_category_layer(
        map_object,
        strelka,
        "morphotype_strelka",
        "Морфотипы (Strelka)",
        MORPHOTYPE_COLORS,
        "Морфотип",
    )

    provision_columns = [c for c in map_summary.columns if c.endswith("_provision")]
    if provision_columns:
        first = provision_columns[0]
        code = first[: -len("_provision")]
        add_value_layer(
            map_object,
            map_summary,
            first,
            f"Обеспеченность: {SERVICES.get(code, code)}",
            "Обеспеченность",
            "RdYlGn",
            2,
            vmin=0,
            vmax=1,
        )

    if services:
        cluster = MarkerCluster(name="Услуги (точки OSM)").add_to(map_object)
        for code, layer in services.items():
            label = SERVICES.get(code, code)
            points = layer.copy()
            points["geometry"] = points.geometry.representative_point()
            for row in points.itertuples():
                folium.CircleMarker(
                    location=[row.geometry.y, row.geometry.x],
                    radius=4,
                    color="#7a3b00",
                    weight=0.8,
                    fill=True,
                    fillColor="#ff9f43",
                    fillOpacity=0.9,
                    popup=f"{label}",
                    tooltip=label,
                ).add_to(cluster)

    folium.LayerControl(collapsed=False, position="topright").add_to(map_object)
    return map_object


# ----------------------------------------------------------------------------------
# Таблицы и выводы
# ----------------------------------------------------------------------------------


def frame_to_html(frame, table_id, sortable=True):
    css_class = "data-table sortable" if sortable else "data-table"
    return frame.to_html(
        classes=css_class,
        index=False,
        border=0,
        escape=True,
        na_rep="—",
        justify="left",
        table_id=table_id,
    )


def services_table(summary, services, report=None):
    provision_columns = {c[: -len("_provision")]: c for c in summary.columns if c.endswith("_provision")}
    capacity_columns = {c[: -len("_capacity")]: c for c in summary.columns if c.endswith("_capacity")}
    populated = summary[summary["population"] > 0]

    extras = {}
    if report is not None and "сервис" in report.columns:
        for _, row in report.iterrows():
            extras[row["сервис"]] = row

    rows = []
    for code, label in SERVICES.items():
        count = len(services[code]) if code in services else 0
        capacity = float(summary[capacity_columns[code]].sum()) if code in capacity_columns else None
        column = provision_columns.get(code)
        if column:
            values = populated[column].dropna()
            share = 100 * float((values >= 1).sum()) / len(values) if len(values) else None
            median = float(values.median()) if len(values) else None
        else:
            share, median = None, None

        item = extras.get(code)
        rows.append(
            {
                "Услуга": label,
                "Объектов в OSM": count,
                "Суммарная ёмкость": capacity,
                "Норматив на 1000 жителей": item["норматив на 1000 жителей"] if item is not None else None,
                "Радиус, мин": item["радиус, мин"] if item is not None else None,
                "Кварталов с нормой, %": share,
                "Медиана обеспеченности": median,
                "Обеспеченность (слабая)": item["обеспеченность (слабая)"] if item is not None else None,
                "Связей": item["связей"] if item is not None else None,
                "Статус": (
                    "нет данных в OSM"
                    if count == 0
                    else "дефицит"
                    if median is not None and median < 1
                    else "в норме"
                ),
            }
        )

    frame = pd.DataFrame(rows)
    for column, digits in [
        ("Суммарная ёмкость", 0),
        ("Норматив на 1000 жителей", 0),
        ("Радиус, мин", 0),
        ("Кварталов с нормой, %", 0),
        ("Медиана обеспеченности", 2),
        ("Обеспеченность (слабая)", 2),
        ("Связей", 0),
    ]:
        frame[column] = frame[column].map(lambda value, digits=digits: fmt_number(value, digits))
    return frame_to_html(frame, "services-table")


def clusters_table(clusters):
    if clusters is None or clusters.empty:
        return ""

    frame = clusters.copy()
    if "cluster" in frame.columns:
        frame["cluster"] = frame["cluster"].astype(int)
    keep = [c for c in ["cluster", "morphotype", "кварталов", "fsi", "gsi", "mxi", "l", "osr"] if c in frame.columns]
    frame = frame[keep].rename(
        columns={
            "cluster": "Кластер",
            "morphotype": "Морфотип",
            "кварталов": "Кварталов",
            "fsi": "FSI",
            "gsi": "GSI",
            "mxi": "MXI",
            "l": "L",
            "osr": "OSR",
        }
    )
    frame["Морфотип"] = frame["Морфотип"].map(lambda value: MORPHOTYPE_RU.get(value, value))
    for column in ["FSI", "GSI", "MXI", "L", "OSR"]:
        if column in frame.columns:
            frame[column] = frame[column].map(lambda value: fmt_number(value, 3))
    return frame_to_html(frame, "clusters-table")


def landuse_table(summary):
    metric = summary.assign(_area_m2=summary.to_crs("EPSG:32635").area)
    grouped = metric.groupby("land_use_label").agg(blocks=("_area_m2", "size"), area_m2=("_area_m2", "sum"))
    grouped["area_km2"] = grouped.pop("area_m2") / 1e6
    grouped = grouped.sort_values("area_km2", ascending=False)
    total = grouped["area_km2"].sum()

    frame = grouped.reset_index()
    frame["land_use_label"] = frame["land_use_label"].map(lambda value: LAND_USE.get(value, value))
    frame["Доля площади, %"] = 100 * frame["area_km2"] / total if total else 0
    frame = frame.rename(
        columns={"land_use_label": "Категория", "blocks": "Кварталов", "area_km2": "Площадь, кв. км"}
    )
    frame["Площадь, кв. км"] = frame["Площадь, кв. км"].map(lambda value: fmt_number(value, 2))
    frame["Доля площади, %"] = frame["Доля площади, %"].map(lambda value: fmt_number(value, 1))
    return frame_to_html(frame, "landuse-table")


def morphotypes_table(summary):
    frame = summary[summary["morphotype_spacematrix"].notna()]
    counts = frame["morphotype_spacematrix"].value_counts().rename_axis("Морфотип").reset_index(name="Кварталов")
    counts["Морфотип"] = counts["Морфотип"].map(lambda value: MORPHOTYPE_RU.get(value, value))
    return frame_to_html(counts, "morphotypes-table")


def accessibility_table(summary, stats):
    rows = []
    for mode, label, column in [
        ("walk", "Пешком", "area_accessibility_walk"),
        ("drive", "На автомобиле", "area_accessibility_drive"),
    ]:
        values = summary[column].dropna()
        if values.empty:
            continue
        rows.append(
            {
                "Режим": label,
                "Минимум, мин": values.min(),
                "Медиана, мин": values.median(),
                "Среднее, мин": values.mean(),
                "Максимум, мин": values.max(),
            }
        )

    frame = pd.DataFrame(rows)
    if stats is not None and "не достижимо" in stats.columns:
        mapping = {}
        for mode, flag in zip(stats["режим"], stats["не достижимо"]):
            mapping["Пешком" if "пеш" in str(mode).lower() else "На автомобиле"] = flag
        frame["Недостижимых пар"] = frame["Режим"].map(mapping)

    for column in ["Минимум, мин", "Медиана, мин", "Среднее, мин", "Максимум, мин"]:
        frame[column] = frame[column].map(lambda value: fmt_number(value, 1))
    return frame_to_html(frame, "accessibility-table")


def full_table(summary):
    frame = summary.drop(columns=[c for c in ["geometry"] if c in summary.columns]).copy()
    first = [column for column in ["_id", "area_ha", "land_use_label"] if column in frame.columns]
    frame = frame[first + [column for column in frame.columns if column not in first]]
    frame = frame.rename(columns={column: column_title(column) for column in frame.columns})
    for column in frame.columns:
        if frame[column].dtype == object:
            continue
        frame[column] = frame[column].map(lambda value: fmt_number(value, 3))
    frame = frame.astype(object).where(pd.notna(frame), "—")
    return frame_to_html(frame, "full-table")


def build_conclusions(summary, stats, matrices, services):
    populated = summary[summary["population"] > 0]
    developed = summary[summary["fsi"] > 0]
    boundary_area = None
    if BOUNDARY_FILE.exists():
        boundary = gpd.read_file(BOUNDARY_FILE).to_crs("EPSG:32635")
        boundary_area = float(boundary.area.sum() / 1e6)

    walk = summary["area_accessibility_walk"].dropna()
    drive = summary["area_accessibility_drive"].dropna()

    points = []
    total_blocks = len(summary)
    points.append(
        f"В границах поселения выделено <b>{total_blocks}</b> {plural(total_blocks, 'квартал', 'квартала', 'кварталов')} "
        f"общей площадью <b>{fmt_number(summary['area_ha'].sum() / 100, 2)} кв. км</b>; население — "
        f"<b>{fmt_number(summary['population'].sum(), 0)}</b> "
        f"{plural(summary['population'].sum(), 'человек', 'человека', 'человек')}, "
        f"оно проживает лишь в <b>{len(populated)}</b> из {total_blocks} кварталов."
    )
    if boundary_area:
        points.append(
            f"Площадь территории вместе с акваторией — <b>{fmt_number(boundary_area, 2)} кв. км</b>, поэтому кварталы "
            f"занимают <b>{100 * summary['area_ha'].sum() / 100 / boundary_area:.0f}%</b> этой площади: "
            "остальное приходится на воду и полосу отвода железной дороги."
        )
    if not walk.empty and not drive.empty:
        walk30 = share_within(matrices.get("walk"), 30)
        drive30 = share_within(matrices.get("drive"), 30)
        sentence = (
            f"Средняя доступность территории: медиана <b>{walk.median():.0f} мин пешком</b> и "
            f"<b>{drive.median():.0f} мин на автомобиле</b> до всех остальных кварталов."
        )
        if np.isfinite(walk30) and np.isfinite(drive30):
            sentence += (
                f" Быстрее 30 минут пешком достижимо <b>{walk30:.0f}%</b> пар кварталов, "
                f"на автомобиле — <b>{drive30:.0f}%</b>."
            )
        points.append(sentence)

    provision_columns = [c for c in summary.columns if c.endswith("_provision")]
    deficit, normal, missing = [], [], []
    for column in provision_columns:
        code = column[: -len("_provision")]
        values = populated[column].dropna()
        if values.empty:
            continue
        (normal if values.median() >= 1 else deficit).append((SERVICES.get(code, code), values.median(), 100 * float((values >= 1).sum()) / len(values)))
    for code, label in SERVICES.items():
        if code not in services:
            missing.append(label)

    if deficit:
        deficit.sort(key=lambda item: item[1])
        text = ", ".join(f"{name} (норма у {share:.0f}% кварталов)" for name, _, share in deficit)
        points.append(f"<b>Дефицит услуг:</b> {text}. Это главные точки приложения усилий.")
    if normal:
        text = ", ".join(name for name, _, _ in normal)
        points.append(f"<b>В пределах нормы</b> по медиане обеспеченности: {text}.")
    if missing:
        points.append(
            "<b>Не вошли в расчёт:</b> "
            + ", ".join(missing)
            + " — в данных OpenStreetMap объектов этого типа не нашлось. "
            "Это ограничение исходных данных, а не вывод об отсутствии услуги."
        )

    if len(developed):
        top = developed["morphotype_spacematrix"].value_counts()
        top_name = MORPHOTYPE_RU.get(top.index[0], top.index[0])
        rest = len(summary) - len(developed)
        points.append(
            f"Застройка есть только в <b>{len(developed)}</b> "
            f"{plural(len(developed), 'квартале', 'кварталах', 'кварталах')}. Преобладающий морфотип — "
            f"<b>{top_name}</b> ({int(top.iloc[0])} {plural(int(top.iloc[0]), 'квартал', 'квартала', 'кварталов')}). "
            f"Остальные {rest} {plural(rest, 'квартал', 'квартала', 'кварталов')} — "
            "лес, острова и открытые территории без зданий."
        )

    unset = int((summary["land_use_label"] == "Не задано в OSM").sum())
    points.append(
        f"У <b>{unset}</b> {plural(unset, 'квартала', 'кварталов', 'кварталов')} категория землепользования "
        "в OSM не указана — для них показатели обеспеченности и морфотипов считаются только по фактической застройке."
    )
    points.append(
        "Обеспеченность считается по ёмкости объектов, а доступность — по времени в пути; "
        "это разные измерения, и их стоит читать вместе. В таблице услуг приведены обе оценки: "
        "сильная (с учётом конкуренции жителей за объект) и слабая (спрос, закрытый и за пределами радиуса)."
    )
    return points


def share_within(matrix, threshold):
    if matrix is None:
        return float("nan")
    values = matrix.to_numpy(dtype=float)
    finite = np.isfinite(values)
    if not finite.any():
        return float("nan")
    return 100 * float((values[finite] <= threshold).sum()) / int(finite.sum())


# ----------------------------------------------------------------------------------
# HTML
# ----------------------------------------------------------------------------------


CSS = """
:root {
  --ink: #1c2733;
  --muted: #5d6b78;
  --line: #dde3e8;
  --accent: #2e6f9e;
  --accent-2: #e08a3c;
  --bg: #f6f8fa;
  --card: #ffffff;
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: "Segoe UI", "Inter", system-ui, -apple-system, sans-serif;
  color: var(--ink);
  background: var(--bg);
  line-height: 1.55;
}
.wrap { max-width: 1240px; margin: 0 auto; padding: 0 22px 60px; }
header.top {
  background: linear-gradient(135deg, #14324b 0%, #2e6f9e 100%);
  color: #ffffff;
  padding: 34px 22px 30px;
  margin-bottom: 26px;
}
header.top .inner { max-width: 1240px; margin: 0 auto; }
header.top h1 { margin: 0 0 6px; font-size: 30px; letter-spacing: -0.4px; }
header.top p { margin: 4px 0 0; opacity: 0.9; max-width: 900px; }
header.top .meta { margin-top: 14px; font-size: 13px; opacity: 0.85; }
h2 { font-size: 22px; margin: 38px 0 12px; letter-spacing: -0.3px; }
h2 .num { color: var(--accent); font-weight: 700; margin-right: 8px; }
h3 { font-size: 16px; margin: 22px 0 8px; }
p.lead { color: var(--muted); margin-top: -4px; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin: 18px 0 8px; }
.card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 14px 16px;
}
.card .label { font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px; color: var(--muted); }
.card .value { font-size: 26px; font-weight: 700; margin-top: 4px; color: var(--accent); }
.card .hint { font-size: 12px; color: var(--muted); margin-top: 2px; }
.panel {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 16px 18px;
  margin: 14px 0;
}
.map-frame {
  width: 100%;
  height: 620px;
  border: 0;
  border-radius: 12px;
  background: #e8eef2;
}
.map-note { font-size: 13px; color: var(--muted); margin-top: 10px; }
.chart { margin: 0; }
.chart img { width: 100%; height: auto; border-radius: 8px; }
.chart figcaption { font-size: 12px; color: var(--muted); margin-top: 6px; }
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 900px) { .grid-2 { grid-template-columns: 1fr; } }
.table-scroll { overflow: auto; max-height: 460px; border: 1px solid var(--line); border-radius: 10px; }
table.data-table { border-collapse: collapse; width: 100%; font-size: 13px; background: #fff; }
table.data-table th, table.data-table td { padding: 7px 10px; border-bottom: 1px solid var(--line); text-align: left; white-space: nowrap; }
table.data-table thead th {
  position: sticky; top: 0; background: #eef3f7; z-index: 1; cursor: pointer;
  font-size: 12px; text-transform: uppercase; letter-spacing: 0.3px; color: #33475b;
}
table.data-table thead th::after { content: ""; }
table.data-table tbody tr:nth-child(even) { background: #fbfcfd; }
table.data-table tbody tr:hover { background: #eef6fc; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 999px; font-size: 12px; font-weight: 600; }
.badge.ok { background: #e3f4ea; color: #1e6b3a; }
.badge.warn { background: #fdf0df; color: #9a5b13; }
.badge.bad { background: #fbe6e4; color: #a12318; }
ul.conclusions { padding-left: 20px; }
ul.conclusions li { margin: 8px 0; }
details { margin-top: 12px; }
details summary { cursor: pointer; font-weight: 600; color: var(--accent); padding: 6px 0; }
.toolbar { display: flex; gap: 12px; align-items: center; margin-bottom: 10px; flex-wrap: wrap; }
.toolbar input {
  padding: 8px 12px; border: 1px solid var(--line); border-radius: 8px; font-size: 14px; min-width: 280px;
}
.toolbar .hint { font-size: 12px; color: var(--muted); }
footer { margin-top: 40px; padding-top: 18px; border-top: 1px solid var(--line); color: var(--muted); font-size: 13px; }
code { background: #eef3f7; padding: 1px 6px; border-radius: 5px; font-size: 13px; }
@media print {
  header.top { background: #14324b !important; -webkit-print-color-adjust: exact; }
  .map-frame { height: 480px; }
  .table-scroll { max-height: none; }
}
"""

JS = """
(function () {
  function cellValue(cell) {
    var text = cell.innerText.trim().replace(/\\s/g, "").replace(",", ".");
    var number = parseFloat(text);
    return isNaN(number) ? cell.innerText.trim().toLowerCase() : number;
  }
  document.querySelectorAll("table.sortable thead th").forEach(function (header, index) {
    header.addEventListener("click", function () {
      var table = header.closest("table");
      var body = table.tBodies[0];
      var rows = Array.from(body.rows);
      var ascending = header.dataset.order !== "asc";
      header.dataset.order = ascending ? "asc" : "desc";
      rows.sort(function (a, b) {
        var left = cellValue(a.cells[index]);
        var right = cellValue(b.cells[index]);
        if (left < right) return ascending ? -1 : 1;
        if (left > right) return ascending ? 1 : -1;
        return 0;
      });
      rows.forEach(function (row) { body.appendChild(row); });
    });
  });

  var filter = document.getElementById("table-filter");
  if (filter) {
    filter.addEventListener("input", function () {
      var needle = filter.value.trim().toLowerCase();
      var table = document.getElementById("full-table");
      if (!table) return;
      Array.from(table.tBodies[0].rows).forEach(function (row) {
        row.style.display = row.innerText.toLowerCase().indexOf(needle) === -1 ? "none" : "";
      });
    });
  }
})();
"""


def build_html(summary, stats, matrices, services, map_object, report=None, clusters=None):
    populated = summary[summary["population"] > 0]
    walk = summary["area_accessibility_walk"].dropna()
    drive = summary["area_accessibility_drive"].dropna()

    provision_columns = [c for c in summary.columns if c.endswith("_provision")]
    deficit_count = 0
    for column in provision_columns:
        values = populated[column].dropna()
        if len(values) and values.median() < 1:
            deficit_count += 1

    cards = [
        ("Население", fmt_number(summary["population"].sum(), 0), "человек"),
        ("Кварталов", fmt_number(len(summary), 0), "единиц анализа"),
        ("Застроенных кварталов", fmt_number(int((summary["fsi"] > 0).sum()), 0), "есть здания"),
        ("Площадь кварталов", fmt_number(summary["area_ha"].sum() / 100, 2), "кв. км"),
        ("Доступность пешком", f"{walk.median():.0f}" if not walk.empty else "—", "минут (медиана)"),
        ("Доступность на авто", f"{drive.median():.0f}" if not drive.empty else "—", "минут (медиана)"),
        ("Услуг в расчёте", f"{len([c for c in SERVICES if c in services])}", "из 12 типов"),
        ("Услуг с дефицитом", f"{deficit_count}", "медиана ниже нормы"),
    ]
    cards_html = "".join(
        f'<div class="card"><div class="label">{html.escape(label)}</div>'
        f'<div class="value">{html.escape(value)}</div><div class="hint">{html.escape(hint)}</div></div>'
        for label, value, hint in cards
    )

    map_html = map_object.get_root().render()
    map_frame = f'<iframe class="map-frame" srcdoc="{html.escape(map_html, quote=True)}" loading="lazy"></iframe>'

    conclusions = build_conclusions(summary, stats, matrices, services)
    conclusions_html = "".join(f"<li>{point}</li>" for point in conclusions)

    provision_mode_note = ""
    if report is not None and "граф" in report.columns and len(report):
        value = str(report["граф"].iloc[0])
        label = "пешком" if value == "walk" else "на автомобиле"
        provision_mode_note = f" Расчёт выполнен по графу «{label}»."

    charts_access = chart_accessibility(summary)
    charts_reach = chart_reachability(matrices)
    charts_population = chart_population(summary)
    charts_provision = chart_provision(summary)
    charts_morph = chart_morphotypes(summary)
    charts_strelka = chart_strelka(summary)
    charts_spacematrix = chart_spacematrix(summary)
    charts_landuse = chart_landuse(summary)

    tables = {
        "services": services_table(summary, services, report),
        "landuse": landuse_table(summary),
        "morphotypes": morphotypes_table(summary),
        "clusters": clusters_table(clusters),
        "accessibility": accessibility_table(summary, stats),
        "full": full_table(summary),
    }

    generated = pd.Timestamp.now().strftime("%d.%m.%Y %H:%M")

    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Высоцкое городское поселение — дашборд исследования</title>
<style>{CSS}</style>
</head>
<body>
<header class="top">
  <div class="inner">
    <h1>Высоцкое городское поселение</h1>
    <p>BlocksNet-исследование: кварталы, застройка, услуги и транспортная доступность.
    Все показатели посчитаны заранее в ноутбуке; эта страница только читает готовые файлы.</p>
    <div class="meta">Собрано: {generated} · Источник данных: OpenStreetMap · Система координат расчётов: UTM 35N (EPSG:32635)</div>
  </div>
</header>

<div class="wrap">

  <div class="cards">{cards_html}</div>

  <h2><span class="num">1</span>Карта</h2>
  <p class="lead">Переключайте слои в правом верхнем углу карты. Наведите курсор на квартал, чтобы увидеть его номер и значение.</p>
  <div class="panel">
    {map_frame}
    <div class="map-note">
      Слои: доступность пешком и на автомобиле, население, плотность застройки (FSI), занятость участка (GSI),
      землепользование, морфотипы Spacematrix и Strelka, обеспеченность услугами, точки услуг, граница поселения,
      вода, улицы и железные дороги.
      Шкала «Доступность пешком» показана отдельной линейкой внизу карты; для остальных слоёв действует правило
      «чем темнее — тем больше значение».
    </div>
  </div>

  <h2><span class="num">2</span>Транспортная доступность</h2>
  <p class="lead">Доступность — среднее время в пути от квартала до всех остальных кварталов поселения. Это характеристика
  компактности территории, а не время до конкретной услуги.</p>
  <div class="panel">{charts_access}</div>
  <div class="panel">{charts_reach}</div>
  <div class="panel">
    <h3>Сводка по режимам передвижения</h3>
    <div class="table-scroll">{tables['accessibility']}</div>
  </div>

  <h2><span class="num">3</span>Услуги и обеспеченность</h2>
  <p class="lead">Обеспеченность сравнивает фактическую ёмкость объектов с нормативной для населения квартала.
  100% — норма выполнена.{provision_mode_note}</p>
  <div class="panel">{charts_provision}</div>
  <div class="panel">
    <h3>Все типы услуг</h3>
    <div class="table-scroll">{tables['services']}</div>
    <p class="map-note">«Нет данных в OSM» означает, что объектов этого типа не нашлось в исходных данных;
    показатель для них не рассчитывался. «Сильная» обеспеченность учитывает конкуренцию жителей за сервис,
    «слабая» дополнительно засчитывает спрос, закрытый за пределами радиуса доступности.</p>
  </div>

  <h2><span class="num">4</span>Застройка и морфотипы</h2>
  <div class="panel">{charts_morph}</div>
  <div class="panel">{charts_strelka}</div>
  <div class="panel">{charts_spacematrix}</div>
  <div class="panel">
    <h3>Морфотипы по кварталам</h3>
    <div class="table-scroll">{tables['morphotypes']}</div>
  </div>
  <div class="panel">
    <h3>Центры кластеров Spacematrix</h3>
    <p class="map-note">Средние значения показателей по каждому кластеру — по ним BlocksNet присваивает
    морфотип. Таблица соответствует <code>spacematrix_clusters.csv</code>.</p>
    <div class="table-scroll">{tables['clusters']}</div>
  </div>

  <h2><span class="num">5</span>Население и землепользование</h2>
  <div class="panel">{charts_population}</div>
  <div class="panel">{charts_landuse}</div>
  <div class="panel">
    <h3>Землепользование</h3>
    <div class="table-scroll">{tables['landuse']}</div>
  </div>

  <h2><span class="num">6</span>Выводы</h2>
  <div class="panel">
    <ul class="conclusions">{conclusions_html}</ul>
  </div>

  <h2><span class="num">7</span>Все показатели по кварталам</h2>
  <div class="panel">
    <div class="toolbar">
      <input id="table-filter" type="search" placeholder="Фильтр: номер квартала, категория, морфотип…">
      <span class="hint">Щелчок по заголовку сортирует столбец. Таблица прокручивается.</span>
    </div>
    <div class="table-scroll" style="max-height: 560px;">{tables['full']}</div>
  </div>

  <footer>
    <p><b>Как обновить отчёт.</b> Данные уже лежат в <code>examples/vysotsk/data</code>. Если в ноутбуке что-то
    пересчитано, выполните в PowerShell из корня репозитория:</p>
    <p><code>.\\.venv\\Scripts\\python.exe examples\\vysotsk\\build_report.py</code></p>
    <p>Скрипт ничего не скачивает и не пересчитывает: он читает готовые GeoJSON, parquet и CSV и заново собирает
    этот файл.</p>
  </footer>

</div>
<script>{JS}</script>
</body>
</html>
"""


def main():
    setup_style()
    print("Читаю готовые результаты…")
    summary, boundary, water, roads, railways, services, stats, matrices, report, clusters = load_data()
    print(f"  кварталов: {len(summary)} | услуг с точками: {len(services)} | матрицы: {', '.join(matrices) or 'нет'}")
    print(f"  отчёт по услугам: {'есть' if report is not None else 'нет'} | центры кластеров: {'есть' if clusters is not None else 'нет'}")

    print("Собираю карту…")
    map_object = build_map(summary, boundary, water, roads, railways, services)

    print("Собираю страницу…")
    page = build_html(summary, stats, matrices, services, map_object, report, clusters)
    OUTPUT.write_text(page, encoding="utf-8")

    print(f"Готово: {OUTPUT}")
    print(f"Размер файла: {human_size(OUTPUT.stat().st_size)}")
    print("Откройте файл двойным щелчком в браузере.")


if __name__ == "__main__":
    main()

