"""Rev E.6 reroutes (Gerber coords, Y up) with filleted corners, as Gerber text or KiCad items."""
import math

# name: (layer, polyline, fillet radius)
ROUTES = {
    'F_S0': ('F', [(29.7, 50.0), (31.7, 52.0), (40.861573, 52.0)], 2.0),
    'F_S2': ('F', [(29.7, 30.0), (31.6, 31.9), (31.6, 35.1), (32.5, 36.0), (40.068298, 36.0)], 1.0),
    'B_S1': ('B', [(29.7, 54.0), (31.6, 52.1), (31.6, 48.9), (32.5, 48.0), (46.7, 48.0)], 1.0),
    'B_S3': ('B', [(29.7, 34.0), (31.6, 32.1), (31.6, 28.9), (32.5, 28.0), (51.8, 28.0)], 1.0),
}


def _unit(a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = math.hypot(dx, dy)
    return dx / L, dy / L, L


def fillet(poly, r):
    """-> list of ('L', p0, p1) and ('A', p0, p1, center, cw) in Y-up coords."""
    out = []
    cur = poly[0]
    for i in range(1, len(poly) - 1):
        A, B, C = poly[i - 1], poly[i], poly[i + 1]
        ux, uy, la = _unit(B, A)
        vx, vy, lc = _unit(B, C)
        cos_t = max(-1.0, min(1.0, ux * vx + uy * vy))
        th = math.acos(cos_t)
        t = r / math.tan(th / 2)
        assert t < la / 2 + 1e-6 or i == 1, ('fillet too big', B)
        assert t < lc / 2 + 1e-6 or i == len(poly) - 2, ('fillet too big', B)
        P1 = (B[0] + ux * t, B[1] + uy * t)
        P2 = (B[0] + vx * t, B[1] + vy * t)
        bx, by = ux + vx, uy + vy
        bl = math.hypot(bx, by)
        bx, by = bx / bl, by / bl
        d = r / math.sin(th / 2)
        Ctr = (B[0] + bx * d, B[1] + by * d)
        z = (B[0] - A[0]) * (C[1] - B[1]) - (B[1] - A[1]) * (C[0] - B[0])
        out.append(('L', cur, P1))
        out.append(('A', P1, P2, Ctr, z < 0))   # right turn = clockwise (Y up)
        cur = P2
    out.append(('L', cur, poly[-1]))
    return out


def gerber(name):
    _, poly, r = ROUTES[name]
    els = fillet(poly, r)
    f = lambda v: round(v * 1e6)
    s = ['X%dY%dD02*' % (f(poly[0][0]), f(poly[0][1])), 'G01*']
    for e in els:
        if e[0] == 'L':
            s.append('X%dY%dD01*' % (f(e[2][0]), f(e[2][1])))
        else:
            _, p0, p1, c, cw = e
            s.append('G02*' if cw else 'G03*')
            s.append('X%dY%dI%dJ%dD01*' % (f(p1[0]), f(p1[1]), f(c[0] - p0[0]), f(c[1] - p0[1])))
            s.append('G01*')
    return '\n'.join(s)


def kicad(name, net, uuidf, H=80.0):
    layer, poly, r = ROUTES[name]
    L = 'F.Cu' if layer == 'F' else 'B.Cu'
    out = []
    fy = lambda y: round(H - y, 4)
    for e in fillet(poly, r):
        if e[0] == 'L':
            (x0, y0), (x1, y1) = e[1], e[2]
            if math.hypot(x1 - x0, y1 - y0) < 1e-6:
                continue
            out.append('  (segment (start %g %g) (end %g %g) (width 0.5) (layer "%s") (net %d) (uuid "%s"))\n'
                       % (round(x0, 4), fy(y0), round(x1, 4), fy(y1), L, net, uuidf()))
        else:
            _, p0, p1, c, cw = e
            mx, my = (p0[0] + p1[0]) / 2 - c[0], (p0[1] + p1[1]) / 2 - c[1]
            ml = math.hypot(mx, my)
            rr = math.hypot(p0[0] - c[0], p0[1] - c[1])
            mid = (c[0] + mx / ml * rr, c[1] + my / ml * rr)
            out.append('  (arc (start %g %g) (mid %g %g) (end %g %g) (width 0.5) (layer "%s") (net %d) (uuid "%s"))\n'
                       % (round(p0[0], 4), fy(p0[1]), round(mid[0], 4), fy(mid[1]), round(p1[0], 4), fy(p1[1]), L, net, uuidf()))
    return out
