from __future__ import annotations


Point = tuple[float, float]


def point_in_polygon(point: Point, polygon: list[list[float]]) -> bool:
    lat, lon = point
    inside = False
    j = len(polygon) - 1
    for i in range(len(polygon)):
        lati, loni = polygon[i]
        latj, lonj = polygon[j]
        intersects = ((loni > lon) != (lonj > lon)) and (
            lat < (latj - lati) * (lon - loni) / ((lonj - loni) or 1e-9) + lati
        )
        if intersects:
            inside = not inside
        j = i
    return inside


def route_intersects_polygon(route: list[list[float]], polygon: list[list[float]]) -> bool:
    if any(point_in_polygon((p[0], p[1]), polygon) for p in route):
        return True
    for a, b in zip(route, route[1:]):
        for c, d in zip(polygon, polygon[1:] + polygon[:1]):
            if _segments_intersect((a[0], a[1]), (b[0], b[1]), (c[0], c[1]), (d[0], d[1])):
                return True
    return False


def _segments_intersect(a: Point, b: Point, c: Point, d: Point) -> bool:
    def orient(p: Point, q: Point, r: Point) -> float:
        return (q[1] - p[1]) * (r[0] - q[0]) - (q[0] - p[0]) * (r[1] - q[1])

    o1 = orient(a, b, c)
    o2 = orient(a, b, d)
    o3 = orient(c, d, a)
    o4 = orient(c, d, b)
    return o1 * o2 < 0 and o3 * o4 < 0


def centroid(points: list[list[float]]) -> list[float]:
    return [sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points)]
