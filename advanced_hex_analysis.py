
advanced_hex_analysis.py

import os
import numpy as np
import pandas as pd
import geopandas as gpd
import osmnx as ox
import folium
import branca
from shapely.geometry import Point, Polygon
from sklearn.cluster import DBSCAN
from folium.plugins import HeatMap, MarkerCluster

# -----------------------

place_name = "Cairo, Egypt"   
hex_radius_m = 400            
output_folder = "output"
os.makedirs(output_folder, exist_ok=True)

# -----------------------

print("1) Downloading OSM data for:", place_name)

area_gdf = ox.geocode_to_gdf(place_name)
area_geom = area_gdf.geometry.unary_union


tags = {"amenity": True}
raw = ox.features_from_place(place_name, tags)


raw = raw[~raw.geometry.is_empty].copy()
raw_points = raw.copy()
raw_points["geometry"] = raw_points.geometry.centroid  
raw_points = raw_points.set_geometry("geometry").to_crs(epsg=4326)


interest_types = ["school", "university", "hospital", "clinic", "cafe", "restaurant", "bank", "supermarket", "pharmacy"]
amen = raw_points[raw_points['amenity'].isin(interest_types)].copy()
amen = amen.reset_index(drop=True)
print("  -> عدد الخدمات المهتمين بها:", len(amen))

# -----------------------

area_proj = area_gdf.to_crs(epsg=3857)
area_bound = area_proj.geometry.unary_union
minx, miny, maxx, maxy = area_bound.bounds


def make_hexagon(center_x, center_y, r):
    angles = np.linspace(0, 2*np.pi, 7)[:-1]
    pts = [(center_x + r * np.cos(a), center_y + r * np.sin(a)) for a in angles]
    return Polygon(pts)

def make_hex_grid(minx, miny, maxx, maxy, r):
    dx = 1.5 * r
    dy = np.sqrt(3) * r
    hexes = []
    q = 0
    y = miny - dy
    while y < maxy + dy:
        x_offset = (0 if q % 2 == 0 else (0.75 * r))
        x = minx - dx
        while x < maxx + dx:
            hexagon = make_hexagon(x + x_offset, y, r)
            hexes.append(hexagon)
            x += dx
        y += dy
        q += 1
    return hexes

print("2) Building hex grid (projected meters)...")
hex_polys = make_hex_grid(minx, miny, maxx, maxy, hex_radius_m)
hex_gdf = gpd.GeoDataFrame({"geometry": hex_polys}, crs="EPSG:3857")
hex_gdf = hex_gdf[hex_gdf.intersects(area_bound)].copy()
hex_gdf = hex_gdf.reset_index(drop=True)
print("  -> created hex cells:", len(hex_gdf))

# -----------------------

amen_proj = amen.to_crs(epsg=3857)
joined = gpd.sjoin(amen_proj, hex_gdf, how="inner", predicate="within")
counts = joined.groupby("index_right").size().rename("count")
diversity = joined.groupby("index_right")['amenity'].nunique().rename("diversity")

hex_gdf["count"] = hex_gdf.index.map(counts).fillna(0).astype(int)
hex_gdf["diversity"] = hex_gdf.index.map(diversity).fillna(0).astype(int)


hex_gdf["area_m2"] = hex_gdf.geometry.area
hex_gdf["area_km2"] = hex_gdf["area_m2"] / 1e6
hex_gdf["density_per_km2"] = hex_gdf["count"] / hex_gdf["area_km2"].replace({0:np.nan})


d_min, d_max = hex_gdf["density_per_km2"].min(skipna=True), hex_gdf["density_per_km2"].max(skipna=True)
v_min, v_max = hex_gdf["diversity"].min(), hex_gdf["diversity"].max()

def norm(val, mn, mx):
    if np.isnan(val) or mx==mn:
        return 0.0
    return (val - mn) / (mx - mn)

hex_gdf["density_norm"] = hex_gdf["density_per_km2"].apply(lambda x: norm(x, d_min, d_max))
hex_gdf["diversity_norm"] = hex_gdf["diversity"].apply(lambda x: norm(x, v_min, v_max))

hex_gdf["score"] = 0.65 * hex_gdf["density_norm"] + 0.35 * hex_gdf["diversity_norm"]

# -----------------------
print("4) Running DBSCAN cluster on cafes to find hotspots...")
cafes = amen_proj[amen_proj['amenity']=='cafe'].copy()
hotspots_gdf = gpd.GeoDataFrame(columns=["geometry","cluster","size"], crs=cafes.crs)
if len(cafes) >= 5:
    coords = np.array([(p.x, p.y) for p in cafes.geometry])
    
    db = DBSCAN(eps=200, min_samples=3).fit(coords)
    labels = db.labels_
    cafes["cluster"] = labels
    clusters = cafes[cafes["cluster"]>=0].dissolve(by="cluster").centroid.reset_index()
    clusters_g = []
    for lbl in cafes['cluster'].unique():
        if lbl < 0: 
            continue
        members = cafes[cafes['cluster']==lbl]
        centroid = members.geometry.unary_union.centroid
        clusters_g.append({"geometry": centroid, "cluster": int(lbl), "size": len(members)})
    if clusters_g:
        hotspots_gdf = gpd.GeoDataFrame(clusters_g, crs=cafes.crs)
print("  -> found hotspots:", len(hotspots_gdf))

# -----------------------

print("5) Exporting geojson files...")
hex_gdf_wgs = hex_gdf.to_crs(epsg=4326)
hex_geojson_path = os.path.join(output_folder, "cairo_hexgrid.geojson")
hex_gdf_wgs.to_file(hex_geojson_path, driver="GeoJSON")

hotspots_geojson_path = os.path.join(output_folder, "hotspots.geojson")
if not hotspots_gdf.empty:
    hotspots_gdf_wgs = hotspots_gdf.to_crs(epsg=4326)
    hotspots_gdf_wgs.to_file(hotspots_geojson_path, driver="GeoJSON")

# -----------------------

print("6) Building interactive map...")
center = [area_gdf.geometry.centroid.iloc[0].y, area_gdf.geometry.centroid.iloc[0].x]
m = folium.Map(location=center, zoom_start=12, tiles="CartoDB positron")


pts = [[pt.y, pt.x] for pt in amen.to_crs(epsg=4326).geometry]
if pts:
    HeatMap(pts, radius=10, blur=15, name="Amenities Heatmap").add_to(m)


colormap = branca.colormap.linear.YlOrRd_09.scale(hex_gdf["score"].min(), hex_gdf["score"].max())
colormap.caption = "Service Score (density + diversity)"
colormap.add_to(m)

hex_geojson = folium.GeoJson(
    hex_gdf_wgs,
    name="Hex Grid (score)",
    style_function=lambda feat: {
        "fillColor": colormap(feat["properties"]["score"]),
        "color": "#444444",
        "weight": 0.5,
        "fillOpacity": 0.7 if feat["properties"]["count"]>0 else 0.1
    },
    tooltip=folium.GeoJsonTooltip(fields=["count","diversity","density_per_km2","score"],
                                  aliases=["Count","Diversity","Density / km2","Score"],
                                  localize=True)
)
hex_geojson.add_to(m)


mc = MarkerCluster(name="Amenities (clustered)").add_to(m)
for idx, row in amen.to_crs(epsg=4326).iterrows():
    popup_text = f"{row.get('amenity','')} - {row.get('name','(no name)')}"
    folium.CircleMarker(location=[row.geometry.y, row.geometry.x],
                        radius=4,
                        popup=popup_text,
                        color=("blue" if row['amenity']=='school' else
                               "brown" if row['amenity']=='cafe' else
                               "green" if row['amenity']=='hospital' else "gray"),
                        fill=True).add_to(mc)


if not hotspots_gdf.empty:
    for _, r in hotspots_gdf.to_crs(epsg=4326).iterrows():
        folium.CircleMarker(location=[r.geometry.y, r.geometry.x],
                            radius=8 + int(r["size"]),
                            color="red",
                            fill=True,
                            fill_opacity=0.9,
                            popup=f"Hotspot cluster #{int(r['cluster'])} (size={int(r['size'])})").add_to(m)


folium.GeoJson(area_gdf.to_crs(epsg=4326), name="Area Boundary", style_function=lambda x: {"color":"black","weight":2,"fillOpacity":0}).add_to(m)


folium.LayerControl(collapsed=False).add_to(m)
map_path = os.path.join(output_folder, "cairo_hex_map.html")
m.save(map_path)

print("Done. Outputs:")
print(" - Interactive map:", map_path)
print(" - Hex GeoJSON:", hex_geojson_path)
if os.path.exists(hotspots_geojson_path):
    print(" - Hotspots GeoJSON:", hotspots_geojson_path)
