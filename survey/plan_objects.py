"""Parametric desk and symbol outlines, independent of structural room geometry."""
import math

FREE_ANNOTATIONS = ("desk", "symbol")
HOSTED_ANNOTATIONS = ("door", "window")
DESK_VARIANTS = ("square", "rectangle", "l", "l_equal", "round")
SYMBOL_VARIANTS = ("circle", "x", "plus", "square", "triangle", "diamond", "star", "arrow")


def object_default(kind, density, variant=None):
    variant = variant or ("rectangle" if kind == "desk" else "circle")
    width, height = {"square": (1, 1), "rectangle": (1.6, .8), "l": (1.8, 1.4),
                     "l_equal": (1.6, 1.6), "round": (1.2, 1.2)}[variant] if kind == "desk" else (.4, .4)
    return dict(id="template", kind=kind, variant=variant, cx=width * density / 2, cy=height * density / 2,
                width=width * density, height=height * density, arm=min(.6, min(width, height) / 2) * density,
                angle=0, color="#475569", stroke=2, fill="#e8dbc2" if kind == "desk" else None)


def object_is_round(item):
    return (item["kind"], item["variant"]) in (("desk", "round"), ("symbol", "circle"))


def object_local_vertices(item):
    """Actual corners/cardinal points in a centered, unrotated local frame."""
    variant, kind = item["variant"], item["kind"]
    if object_is_round(item):
        points = [(0, .5), (.5, 0), (1, .5), (.5, 1)]
    elif kind == "desk" and variant in ("l", "l_equal"):
        x, y = item["arm"] / item["width"], item["arm"] / item["height"]
        points = [(0, 0), (1, 0), (1, y), (x, y), (x, 1), (0, 1)]
    elif variant in ("square", "rectangle"):
        points = [(0, 0), (1, 0), (1, 1), (0, 1)]
    elif variant == "triangle":
        points = [(.5, 0), (1, 1), (0, 1)]
    elif variant == "diamond":
        points = [(.5, 0), (1, .5), (.5, 1), (0, .5)]
    elif variant == "star":
        points = [(.5 + (.5 if i % 2 == 0 else .22) * math.cos(-math.pi / 2 + i * math.pi / 5),
                   .5 + (.5 if i % 2 == 0 else .22) * math.sin(-math.pi / 2 + i * math.pi / 5)) for i in range(10)]
    elif variant == "arrow":
        points = [(0, .33), (.55, .33), (.55, 0), (1, .5), (.55, 1), (.55, .67), (0, .67)]
    elif variant == "plus":
        points = [(.35, 0), (.65, 0), (.65, .35), (1, .35), (1, .65), (.65, .65),
                  (.65, 1), (.35, 1), (.35, .65), (0, .65), (0, .35), (.35, .35)]
    else:  # X is a closed silhouette: both outline and fill have a clear meaning.
        points = [(0, .18), (.18, 0), (.5, .32), (.82, 0), (1, .18), (.68, .5),
                  (1, .82), (.82, 1), (.5, .68), (.18, 1), (0, .82), (.32, .5)]
    return [((x - .5) * item["width"], (y - .5) * item["height"]) for x, y in points]


def object_vertices(item):
    angle = 0 if object_is_round(item) else item["angle"]
    cosine, sine = math.cos(math.radians(angle)), math.sin(math.radians(angle))
    if angle % 90 == 0:
        cosine, sine = round(cosine), round(sine)
    return [(item["cx"] + x * cosine - y * sine, item["cy"] + x * sine + y * cosine)
            for x, y in object_local_vertices(item)]


def object_geometry(item):
    points = object_vertices(item)
    return [dict(x1=a[0], y1=a[1], x2=b[0], y2=b[1], color=item["color"])
            for a, b in zip(points, points[1:] + points[:1])]
