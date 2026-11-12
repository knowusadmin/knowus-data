import shapely.geometry as sg
from shapely.ops import unary_union
from shapely.validation import make_valid
def rpoly(g):
    """Esri rings -> polygon: clockwise rings are outer rings, counter-clockwise rings are holes of the smallest outer ring holding them."""
    ext=[];hol=[]
    for r in g['rings']:
        if len(r)<4: continue
        lr=sg.LinearRing(r)
        (hol if lr.is_ccw else ext).append(r)
    if not ext: return sg.Polygon()
    EP=[sg.Polygon(r) for r in ext]; H=[[] for _ in ext]
    for h in hol:
        pt=sg.Point(h[0]); best=None
        for j,p in enumerate(EP):
            if p.area>0 and p.covers(pt) and (best is None or p.area<EP[best].area): best=j
        if best is not None: H[best].append(h)
    return make_valid(unary_union([make_valid(sg.Polygon(e,hh)) for e,hh in zip(ext,H)]))
