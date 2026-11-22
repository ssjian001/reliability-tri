"""Safe expression DSL. Grammar: literals like 70[degC], identifiers, arithmetic,
comparisons, boolean operators, and min/max/abs. No attribute access, indexing,
assignment, comprehensions, imports, or arbitrary function calls.
"""
from __future__ import annotations
import math, re
from dataclasses import dataclass
from .errors import ParseError, EvaluationError, MissingInput, DimensionMismatch, UnitError
from .units import Quantity

TOKEN = re.compile(r"\s*(?:(\d+(?:\.\d*)?(?:[eE][+-]?\d+)?)|([A-Za-z_][A-Za-z0-9_]*)|(\[([^\]\s]+)\])|(<=|>=|==|!=|\*\*|[()+\-*/%,<>])|(and\b|or\b|not\b))")
@dataclass(frozen=True)
class Tok: kind: str; value: str; pos: int

class Parser:
    def __init__(self, source: str):
        if not isinstance(source, str) or len(source) > 4096:
            raise ParseError("Expression must be a string of at most 4096 characters")
        self.source=source; self.tokens=[]; p=0
        while p < len(source):
            if source[p:].strip()=="": break
            m=TOKEN.match(source,p)
            if not m: raise ParseError(f"Unexpected character at position {p}: {source[p:p+12]!r}")
            num, ident, unitall, unit, op, word=m.groups()
            if num: self.tokens.append(Tok("NUMBER",num,p))
            elif ident:
                self.tokens.append(Tok("OP",ident,p) if ident in ("and","or","not") else Tok("IDENT",ident,p))
            elif unitall: self.tokens.append(Tok("UNIT",unit,p))
            elif op: self.tokens.append(Tok("OP",op,p))
            elif word: self.tokens.append(Tok("OP",word.strip(),p))
            p=m.end()
            if len(self.tokens) > 512: raise ParseError("Expression exceeds 512-token limit")
        self.tokens.append(Tok("EOF","",len(source))); self.i=0
    def peek(self): return self.tokens[self.i]
    def take(self): t=self.peek(); self.i+=1; return t
    def accept(self,v):
        if self.peek().value==v: return self.take()
        return None
    def expect(self,v):
        t=self.accept(v)
        if not t: raise ParseError(f"Expected {v!r} at position {self.peek().pos}")
        return t
    def parse(self):
        node=self.expr(0)
        if self.peek().kind!="EOF": raise ParseError(f"Unexpected token {self.peek().value!r} at {self.peek().pos}")
        return node
    BP={"or":1,"and":2,"==":3,"!=":3,"<":3,"<=":3,">":3,">=":3,"+":4,"-":4,"*":5,"/":5,"**":6}
    def expr(self,minbp):
        t=self.take()
        if t.kind=="NUMBER":
            node=("number",float(t.value))
            if self.peek().kind=="UNIT": node=("quantity",float(t.value),self.take().value)
        elif t.kind=="IDENT":
            if self.accept("("):
                args=[]
                if not self.accept(")"):
                    while True:
                        args.append(self.expr(0))
                        if self.accept(")"): break
                        self.expect(",")
                if t.value not in ("min","max","abs","lookup_max_id"): raise ParseError(f"Function not allowed: {t.value}")
                node=("call",t.value,args)
            elif t.value == "null": node=("null",)
            else: node=("name",t.value)
        elif t.value in ("+","-","not"):
            node=("unary",t.value,self.expr(7))
        elif t.value=="(":
            node=self.expr(0); self.expect(")")
        else: raise ParseError(f"Unexpected token {t.value!r} at {t.pos}")
        while True:
            op=self.peek().value; bp=self.BP.get(op,-1)
            if bp<minbp: break
            self.take(); rhs=self.expr(bp+ (0 if op=="**" else 1)); node=("binary",op,node,rhs)
        return node

def parse(source: str): return Parser(source).parse()

def _q(v):
    if isinstance(v,bool): raise EvaluationError("Boolean is not a numeric quantity")
    return v if isinstance(v,Quantity) else Quantity.of(v)
def evaluate(ast, inputs: dict, functions: dict | None = None):
    try: return _eval(ast,inputs,functions or {})
    except (MissingInput, DimensionMismatch, UnitError, EvaluationError): raise
    except Exception as e: raise EvaluationError(str(e)) from e

def _eval(n,env,functions):
    kind=n[0]
    if kind=="null": return None
    if kind=="number": return Quantity.of(n[1])
    if kind=="quantity": return Quantity.of(n[1],n[2])
    if kind=="name":
        if n[1] not in env: raise MissingInput(f"Missing input: {n[1]}")
        v=env[n[1]]
        if isinstance(v,dict) and "value" in v: return Quantity.of(v["value"],v.get("unit","1"))
        if isinstance(v,(int,float)): return Quantity.of(v)
        if isinstance(v,(bool,Quantity,str)) or v is None: return v
        raise EvaluationError(f"Unsupported input type for {n[1]}")
    if kind=="unary":
        op=n[1]; v=_eval(n[2],env,functions)
        if op=="not":
            if not isinstance(v,bool): raise EvaluationError("not requires boolean")
            return not v
        q=_q(v); return q if op=="+" else Quantity(-q.value,q.dimension,q.display_unit)
    if kind=="call":
        name,args=n[1],[_eval(x,env,functions) for x in n[2]]
        if name=="lookup_max_id":
            if len(args)!=3: raise EvaluationError("lookup_max_id requires table_id, x, y")
            if "lookup_max_id" not in functions: raise EvaluationError("CURVE_REPOSITORY_NOT_CONFIGURED")
            return functions["lookup_max_id"](args[0],_q(args[1]),_q(args[2]))
        if not args: raise EvaluationError(f"{name} requires at least one argument")
        if name=="abs":
            if len(args)!=1: raise EvaluationError("abs requires one argument")
            q=_q(args[0]); return Quantity(abs(q.value),q.dimension,q.display_unit)
        qs=[_q(x) for x in args]
        for q in qs[1:]: qs[0]._same(q)
        chosen=(min if name=="min" else max)(qs,key=lambda x:x.value)
        return chosen
    if kind=="binary":
        op=n[1]; a=_eval(n[2],env,functions)
        if op=="and":
            if not isinstance(a,bool): raise EvaluationError("and requires booleans")
            return a and _bool(_eval(n[3],env,functions))
        if op=="or":
            if not isinstance(a,bool): raise EvaluationError("or requires booleans")
            return a or _bool(_eval(n[3],env,functions))
        b=_eval(n[3],env,functions)
        if op in ("==","!=","<","<=",">",">="):
            if a is None or b is None:
                if op not in ("==", "!="): raise EvaluationError("null supports equality comparison only")
                return (a is b) if op=="==" else (a is not b)
            if isinstance(a,(bool,str)) or isinstance(b,(bool,str)):
                if type(a)!=type(b): raise EvaluationError("Cannot compare incompatible scalar values")
                return {"==":a==b,"!=":a!=b,"<":a<b,"<=":a<=b,">":a>b,">=":a>=b}[op]
            return _q(a).compare(_q(b),op)
        qa,qb=_q(a),_q(b)
        if op=="+": return qa.add(qb)
        if op=="-": return qa.sub(qb)
        if op=="*": return qa.mul(qb)
        if op=="/": return qa.div(qb)
        if op=="**":
            if qb.dimension!="dimensionless" or qb.value not in (-3,-2,-1,0,1,2,3): raise EvaluationError("Exponent must be an integer from -3 to 3")
            if qa.dimension!="dimensionless" and qb.value!=1: raise EvaluationError("Power of dimensional quantities is not supported")
            return Quantity(qa.value**int(qb.value),qa.dimension,qa.display_unit)
    raise EvaluationError(f"Unknown AST node: {kind}")
def _bool(v):
    if not isinstance(v,bool): raise EvaluationError("Boolean operand required")
    return v

def evaluate_expression(source: str, inputs: dict, functions: dict | None = None):
    result=evaluate(parse(source),inputs,functions)
    return result
