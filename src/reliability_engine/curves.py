from __future__ import annotations
from .units import Quantity
from .errors import EvaluationError, DimensionMismatch

def lookup_curve(x: Quantity, points: list[tuple[Quantity, Quantity]], *, extrapolation: str="error") -> Quantity:
    """Piecewise-linear interpolation. Points must be strictly increasing in x.
    Extrapolation policy: error | clamp | linear.
    """
    if len(points)<2: raise EvaluationError("Curve requires at least two points")
    for px,py in points:
        if px.dimension!=x.dimension: raise DimensionMismatch("Curve X dimension mismatch")
    ys=points[0][1]
    if any(y.dimension!=ys.dimension for _,y in points): raise DimensionMismatch("Curve Y dimension mismatch")
    xs=[p[0].value for p in points]
    if any(xs[i]>=xs[i+1] for i in range(len(xs)-1)): raise EvaluationError("Curve X values must be strictly increasing")
    xv=x.value
    if xv<xs[0] or xv>xs[-1]:
        if extrapolation=="error": raise EvaluationError("CURVE_OUT_OF_RANGE", code="CURVE_OUT_OF_RANGE")
        if extrapolation=="clamp": return points[0][1] if xv<xs[0] else points[-1][1]
        if extrapolation!="linear": raise EvaluationError(f"Unknown extrapolation policy: {extrapolation}")
        i=0 if xv<xs[0] else len(points)-2
    else:
        i=next((j for j in range(len(xs)-1) if xs[j]<=xv<=xs[j+1]),len(xs)-2)
    x0,y0=points[i]; x1,y1=points[i+1]
    ratio=(xv-x0.value)/(x1.value-x0.value)
    return Quantity(y0.value+ratio*(y1.value-y0.value),ys.dimension,ys.display_unit)

class CurveRepository:
    """In-memory immutable 2D curve tables keyed by controlled artifact ID.

    Values are a rectangular grid: z[row_y][column_x]. `log_log_linear` uses
    bilinear interpolation in log(x), log(y), log(z) space. This is an explicit
    approximation policy, not a substitute for validating vendor digitization.
    """
    def __init__(self): self._tables={}
    def register(self, table_id: str, *, x_unit: str, y_unit: str, z_unit: str,
                 x_values: list[float], y_values: list[float], z_values: list[list[float]],
                 interpolation: str="log_log_linear"):
        if not table_id or table_id in self._tables: raise EvaluationError("Curve table ID missing or duplicate")
        if interpolation not in ("linear", "log_log_linear"): raise EvaluationError("Unsupported interpolation method")
        xs=[Quantity.of(v,x_unit) for v in x_values]; ys=[Quantity.of(v,y_unit) for v in y_values]
        zs=[[Quantity.of(v,z_unit) for v in row] for row in z_values]
        if len(xs)<2 or len(ys)<2 or len(zs)!=len(ys) or any(len(r)!=len(xs) for r in zs):
            raise EvaluationError("Curve table must be a rectangular grid with at least 2x2 points")
        if any(xs[i].value>=xs[i+1].value for i in range(len(xs)-1)) or any(ys[i].value>=ys[i+1].value for i in range(len(ys)-1)):
            raise EvaluationError("Curve axes must be strictly increasing")
        if interpolation=="log_log_linear" and any(q.value<=0 for q in xs+ys+[q for row in zs for q in row]):
            raise EvaluationError("Log-log interpolation requires all coordinates and values > 0")
        self._tables[table_id]={"xs":xs,"ys":ys,"zs":zs,"interpolation":interpolation}
    def lookup_max_id(self, table_id, x: Quantity, y: Quantity, *, out_of_bounds="error") -> Quantity:
        if not isinstance(table_id,str) or table_id not in self._tables: raise EvaluationError("CURVE_TABLE_NOT_FOUND", code="CURVE_TABLE_NOT_FOUND")
        t=self._tables[table_id]; xs=t["xs"]; ys=t["ys"]; zs=t["zs"]
        if x.dimension!=xs[0].dimension or y.dimension!=ys[0].dimension: raise DimensionMismatch("Curve query axis dimension mismatch")
        xv,yv=x.value,y.value
        if xv<xs[0].value or xv>xs[-1].value or yv<ys[0].value or yv>ys[-1].value:
            if out_of_bounds=="error": raise EvaluationError("CURVE_OUT_OF_RANGE", code="CURVE_OUT_OF_RANGE")
            if out_of_bounds!="clamp": raise EvaluationError("Invalid curve out-of-bounds policy")
            xv=min(max(xv,xs[0].value),xs[-1].value); yv=min(max(yv,ys[0].value),ys[-1].value)
        ix=_bracket([q.value for q in xs],xv); iy=_bracket([q.value for q in ys],yv)
        x0,x1=xs[ix].value,xs[ix+1].value; y0,y1=ys[iy].value,ys[iy+1].value
        z00,z10=zs[iy][ix].value,zs[iy][ix+1].value
        z01,z11=zs[iy+1][ix].value,zs[iy+1][ix+1].value
        if t["interpolation"]=="log_log_linear":
            import math
            tx=(math.log(xv)-math.log(x0))/(math.log(x1)-math.log(x0)); ty=(math.log(yv)-math.log(y0))/(math.log(y1)-math.log(y0))
            l00,l10,l01,l11=map(math.log,(z00,z10,z01,z11))
            z=math.exp((1-ty)*((1-tx)*l00+tx*l10)+ty*((1-tx)*l01+tx*l11))
        else:
            tx=(xv-x0)/(x1-x0); ty=(yv-y0)/(y1-y0)
            z=(1-ty)*((1-tx)*z00+tx*z10)+ty*((1-tx)*z01+tx*z11)
        return Quantity(z,zs[0][0].dimension,zs[0][0].display_unit)

def _bracket(axis, value):
    if value==axis[-1]: return len(axis)-2
    for i in range(len(axis)-1):
        if axis[i]<=value<=axis[i+1]: return i
    raise EvaluationError("CURVE_OUT_OF_RANGE", code="CURVE_OUT_OF_RANGE")
